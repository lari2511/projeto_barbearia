"""
Modalidades BARBEARIA x A DOMICÍLIO (setor cliente).

- A DOMICÍLIO lista só freelancers (nunca barbearias), por distância, que ligaram
  "Atendo a domicílio" e têm serviço a domicílio ativo.
- O chamado domiciliar persiste modalidade + endereço, sem barbearia/cadeira/dono.
- Aceite, chegada no endereço, atendimento e conclusão usam o fluxo de sempre.
- O fluxo da barbearia continua igual.

SQLite temporário, sem chamadas externas.

    venv/Scripts/python -m pytest test_atendimento_domicilio.py -v
"""

import os
import tempfile
from datetime import datetime, timedelta

_DB = os.path.join(tempfile.mkdtemp(prefix="bm_domicilio_"), "teste.db")
os.environ["DATABASE_URL"] = f"sqlite:///{_DB}"

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app import models, routes, routes_interesse, routes_on_demand  # noqa: E402
from app.database import Base, SessionLocal, engine, init_db  # noqa: E402
from app.main import app  # noqa: E402
from app.routes import create_access_token  # noqa: E402

V1 = "/api/v1"
LAT, LON = -23.55, -46.63          # endereço do cliente
PERTO = (-23.552, -46.632)         # ~300 m
LONGE = (-23.60, -46.70)           # ~9 km
FORA = (-23.90, -46.90)            # > 15 km
ENDERECO = "Rua das Flores, 123 - apto 4"


@pytest.fixture(autouse=True)
def sem_rede(monkeypatch):
    monkeypatch.setattr(routes_on_demand, "_calcular_eta_osrm_minutos", lambda *a, **k: 3)
    monkeypatch.setattr(routes, "_calcular_eta_osrm_minutos", lambda *a, **k: 3)
    monkeypatch.setattr(routes_on_demand, "enviar_notificacao_novo_chamado", lambda *a, **k: True)
    monkeypatch.setattr(routes_interesse, "enviar_notificacao_novo_chamado", lambda *a, **k: True)


@pytest.fixture()
def http():
    Base.metadata.drop_all(bind=engine)
    init_db()
    return TestClient(app)


def _usuario(tipo, email, **extras):
    db = SessionLocal()
    try:
        u = models.Usuario(nome=email.split("@")[0], email=email, senha_hash="x", tipo=tipo, perfil_aprovado=True, **extras)
        db.add(u)
        db.commit()
        db.refresh(u)
        return u.id, {"Authorization": f"Bearer {create_access_token({'sub': str(u.id), 'tipo': tipo})}"}
    finally:
        db.close()


def _freelancer(http, email, pos, servico=True, ligar=True, **extras):
    dados = {"online_regiao": True, "disponivel": True}
    dados.update(extras)
    fid, headers = _usuario("barbeiro", email, latitude=pos[0], longitude=pos[1], **dados)
    servico_id = None
    if servico:
        r = http.post(f"{V1}/domicilio/meus-servicos", json={
            "nome": "Corte em casa", "categoria": "corte", "valor": 80.0, "duracao_minutos": 40,
        }, headers=headers)
        assert r.status_code == 200, r.text
        servico_id = r.json()["id"]
    if ligar:
        r = http.put(f"{V1}/domicilio/atendimento", json={"atende_domicilio": True}, headers=headers)
        assert r.status_code == 200, r.text
    return fid, headers, servico_id


def _barbearia(email="dono@t.com"):
    dono_id, headers = _usuario("barbearia", email)
    db = SessionLocal()
    try:
        b = models.Barbearia(usuario_id=dono_id, nome="Barbearia Central", endereco="Rua A", latitude=LAT, longitude=LON)
        db.add(b)
        db.flush()
        cadeira = models.Cadeira(barbearia_id=b.id, numero=1, status=models.StatusCadeira.DISPONIVEL)
        db.add(cadeira)
        servico = models.Servico(barbearia_id=b.id, nome="Corte", categoria="corte", valor=50.0, duracao_minutos=30, ativo=True)
        db.add(servico)
        db.commit()
        return {"id": b.id, "headers": headers, "servico_id": servico.id, "cadeira_id": cadeira.id}
    finally:
        db.close()


def _pedir_domicilio(http, cliente, fid, servico_id, **extras):
    corpo = {
        "modalidade": "ATENDIMENTO_DOMICILIAR",
        "servico_id": servico_id,
        "barbeiro_id": fid, "barbeiro_selecionado_id": fid,
        "data_hora_inicio": datetime.utcnow().isoformat(),
        "cliente_latitude": LAT, "cliente_longitude": LON,
        "endereco_atendimento": ENDERECO,
    }
    corpo.update(extras)
    return http.post(f"{V1}/chamados", json=corpo, headers=cliente)


def _chamado(chamado_id):
    db = SessionLocal()
    try:
        return db.get(models.Chamado, chamado_id)
    finally:
        db.close()


# ---------------------------------------------------------------- listagem

def test_domicilio_lista_so_freelancers_elegiveis_por_distancia(http):
    _barbearia()  # existe barbearia perto, mas não pode aparecer
    longe, _, _ = _freelancer(http, "longe@t.com", LONGE)
    perto, _, _ = _freelancer(http, "perto@t.com", PERTO)
    _freelancer(http, "fora@t.com", FORA)                                 # fora do raio
    _freelancer(http, "sem_optin@t.com", PERTO, ligar=False)              # não atende a domicílio
    _freelancer(http, "offline@t.com", PERTO, ligar=True, online_regiao=False, disponivel=False)
    presente, _, _ = _freelancer(http, "presente@t.com", PERTO)
    db = SessionLocal()
    try:
        u = db.get(models.Usuario, presente)
        u.presente_em_local = True
        db.commit()
    finally:
        db.close()

    _, cliente = _usuario("cliente", "c@t.com", latitude=LAT, longitude=LON)
    r = http.get(f"{V1}/domicilio/freelancers-proximos", params={"latitude": LAT, "longitude": LON}, headers=cliente)
    assert r.status_code == 200, r.text
    lista = r.json()["freelancers"]
    assert [f["id"] for f in lista] == [perto, longe]          # ordenado pela menor distância
    assert all("latitude" not in f and "longitude" not in f for f in lista)  # sem coordenada de pessoa
    assert lista[0]["disponivel"] is True and lista[0]["a_partir_de"] == 80.0
    assert all("barbearia" not in str(k) for f in lista for k in f)          # nenhuma barbearia


def test_sem_localizacao_retorna_vazio(http):
    _, cliente = _usuario("cliente", "c@t.com")
    r = http.get(f"{V1}/domicilio/freelancers-proximos", headers=cliente)
    assert r.json() == {"freelancers": [], "erro": "localizacao_indisponivel"}


def test_ligar_domicilio_exige_servico(http):
    _, headers, _ = _freelancer(http, "f@t.com", PERTO, servico=False, ligar=False)
    r = http.put(f"{V1}/domicilio/atendimento", json={"atende_domicilio": True}, headers=headers)
    assert r.status_code == 400


def test_servicos_do_freelancer_para_o_cliente(http):
    fid, _, sid = _freelancer(http, "f@t.com", PERTO)
    _, cliente = _usuario("cliente", "c@t.com", latitude=LAT, longitude=LON)
    r = http.get(f"{V1}/domicilio/freelancer/{fid}/servicos", headers=cliente)
    assert r.status_code == 200
    assert [s["id"] for s in r.json()["servicos"]] == [sid]


# ---------------------------------------------------------------- criação

def test_cria_chamado_domiciliar_sem_barbearia(http):
    fid, _, sid = _freelancer(http, "f@t.com", PERTO)
    _, cliente = _usuario("cliente", "c@t.com", latitude=LAT, longitude=LON)
    r = _pedir_domicilio(http, cliente, fid, sid)
    assert r.status_code == 200, r.text
    assert r.json()["modalidade"] == "ATENDIMENTO_DOMICILIAR"
    c = _chamado(r.json()["id"])
    assert c.modalidade == models.MODALIDADE_DOMICILIAR
    assert c.barbearia_id is None and c.cadeira_id is None
    assert c.endereco_atendimento == ENDERECO
    assert (c.latitude_atendimento, c.longitude_atendimento) == (LAT, LON)
    assert c.valor_total == 80.0 and c.comissao_plataforma == 8.0
    assert c.valor_freelancer == 72.0 and c.valor_dono == 0.0


def test_domicilio_exige_endereco(http):
    fid, _, sid = _freelancer(http, "f@t.com", PERTO)
    _, cliente = _usuario("cliente", "c@t.com", latitude=LAT, longitude=LON)
    r = _pedir_domicilio(http, cliente, fid, sid, endereco_atendimento="  ")
    assert r.status_code == 400
    assert "endereço" in r.json()["detail"]


def test_domicilio_nao_aceita_servico_de_barbearia_nem_barbearia(http):
    loja = _barbearia()
    fid, _, sid = _freelancer(http, "f@t.com", PERTO)
    _, cliente = _usuario("cliente", "c@t.com", latitude=LAT, longitude=LON)
    assert _pedir_domicilio(http, cliente, fid, loja["servico_id"]).status_code == 400
    assert _pedir_domicilio(http, cliente, fid, sid, barbearia_id=loja["id"]).status_code == 400


def test_domicilio_sem_optin_ou_presente_e_recusado(http):
    fid, headers, sid = _freelancer(http, "f@t.com", PERTO)
    _, cliente = _usuario("cliente", "c@t.com", latitude=LAT, longitude=LON)
    http.put(f"{V1}/domicilio/atendimento", json={"atende_domicilio": False}, headers=headers)
    assert _pedir_domicilio(http, cliente, fid, sid).status_code == 400

    http.put(f"{V1}/domicilio/atendimento", json={"atende_domicilio": True}, headers=headers)
    db = SessionLocal()
    try:
        db.get(models.Usuario, fid).presente_em_local = True
        db.commit()
    finally:
        db.close()
    assert _pedir_domicilio(http, cliente, fid, sid).status_code == 400


def test_domicilio_sem_fila_de_espera(http):
    fid, _, sid = _freelancer(http, "f@t.com", PERTO)
    _, c1 = _usuario("cliente", "c1@t.com", latitude=LAT, longitude=LON)
    _, c2 = _usuario("cliente", "c2@t.com", latitude=LAT, longitude=LON)
    assert _pedir_domicilio(http, c1, fid, sid).status_code == 200
    r = _pedir_domicilio(http, c2, fid, sid)
    assert r.status_code == 400
    assert "andamento" in r.json()["detail"]


def test_varios_servicos_no_mesmo_pedido(http):
    fid, headers, sid = _freelancer(http, "f@t.com", PERTO)
    sid2 = http.post(f"{V1}/domicilio/meus-servicos", json={
        "nome": "Barba em casa", "categoria": "barba", "valor": 40.0, "duracao_minutos": 20,
    }, headers=headers).json()["id"]
    _, cliente = _usuario("cliente", "c@t.com", latitude=LAT, longitude=LON)
    primeiro = _pedir_domicilio(http, cliente, fid, sid).json()["id"]
    r = _pedir_domicilio(http, cliente, fid, sid2, grupo_id=primeiro,
                         data_hora_inicio=(datetime.utcnow() + timedelta(minutes=40)).isoformat())
    assert r.status_code == 200, r.text
    assert _chamado(primeiro).grupo_id == primeiro
    assert _chamado(r.json()["id"]).grupo_id == primeiro


# ---------------------------------------------------------------- ciclo completo

def test_fluxo_completo_domicilio(http):
    loja = _barbearia()
    fid, freela, sid = _freelancer(http, "f@t.com", PERTO)
    _, cliente = _usuario("cliente", "c@t.com", latitude=LAT, longitude=LON)
    cid = _pedir_domicilio(http, cliente, fid, sid).json()["id"]

    # freelancer vê o chamado com o endereço do cliente no lugar da barbearia
    abertos = http.get(f"{V1}/chamados/abertos", headers=freela).json()
    card = next(c for c in abertos if c["id"] == cid)
    assert card["modalidade"] == "ATENDIMENTO_DOMICILIAR"
    assert card["endereco_barbearia"] == ENDERECO
    assert (card["barbearia_latitude"], card["barbearia_longitude"]) == (LAT, LON)

    r = http.put(f"{V1}/chamados/{cid}/aceitar", headers=freela)
    assert r.status_code == 200, r.text
    c = _chamado(cid)
    assert c.status == "confirmado" and c.cadeira_id is None and c.cliente_chegou is True

    # rastreamento aponta para o endereço do cliente
    eta = http.get(f"{V1}/tracking/chamados/{cid}/eta", headers=cliente).json()
    assert eta["modalidade"] == "ATENDIMENTO_DOMICILIAR"
    assert eta["barbearia"]["endereco"] == ENDERECO

    # longe do endereço não confirma chegada
    assert http.put(f"{V1}/chamados/{cid}/chegar", headers=freela).status_code == 400
    db = SessionLocal()
    try:
        u = db.get(models.Usuario, fid)
        u.latitude, u.longitude = LAT + 0.0005, LON
        db.commit()
    finally:
        db.close()
    r = http.put(f"{V1}/chamados/{cid}/chegar", headers=freela)
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "em_atendimento"

    db = SessionLocal()
    try:
        u = db.get(models.Usuario, fid)
        assert not u.presente_em_local and u.barbearia_atual_id is None   # não vira presença em barbearia
    finally:
        db.close()

    r = http.put(f"{V1}/chamados/{cid}/finalizar", headers=freela)
    assert r.status_code == 200, r.text
    assert _chamado(cid).status == "concluido"

    # cadeira da barbearia intocada
    db = SessionLocal()
    try:
        assert db.get(models.Cadeira, loja["cadeira_id"]).status == models.StatusCadeira.DISPONIVEL
    finally:
        db.close()

    pedidos = http.get(f"{V1}/cliente/meus_pedidos", headers=cliente).json()
    pedido = next(p for p in pedidos if p["id"] == cid)
    assert pedido["modalidade"] == "ATENDIMENTO_DOMICILIAR"
    assert pedido["endereco_atendimento"] == ENDERECO
    assert pedido["barbearia_nome"] is None
    assert pedido["avaliacao_barbearia_enviada"] is True       # não pede avaliação de barbearia

    pend = http.get(f"{V1}/avaliacoes/pendentes-cliente", headers=cliente).json()
    item = next(p for p in pend if p["chamado_id"] == cid)
    assert item["avaliacao_barbearia_enviada"] is True and item["avaliacao_freelancer_enviada"] is False


# ---------------------------------------------------------------- barbearia preservada

def test_fluxo_barbearia_continua_igual(http):
    loja = _barbearia()
    fid, _ = _usuario("barbeiro", "b@t.com", latitude=LAT, longitude=LON, online_regiao=True, disponivel=True)
    _, cliente = _usuario("cliente", "c@t.com", latitude=LAT, longitude=LON)
    corpo = {
        "barbearia_id": loja["id"], "servico_id": loja["servico_id"],
        "barbeiro_id": fid, "barbeiro_selecionado_id": fid,
        "data_hora_inicio": datetime.utcnow().isoformat(),
        "cliente_latitude": LAT, "cliente_longitude": LON,
    }
    r = http.post(f"{V1}/chamados", json=corpo, headers=cliente)
    assert r.status_code == 200, r.text
    c = _chamado(r.json()["id"])
    assert c.modalidade == models.MODALIDADE_BARBEARIA and c.barbearia_id == loja["id"]
    assert c.valor_dono == 25.0   # split da barbearia inalterado

    sem_barbearia = dict(corpo)
    sem_barbearia.pop("barbearia_id")
    assert http.post(f"{V1}/chamados", json=sem_barbearia, headers=cliente).status_code == 400


def test_freelancer_em_domicilio_nao_entra_na_fila_da_barbearia(http):
    loja = _barbearia()
    fid, _, sid = _freelancer(http, "f@t.com", PERTO)
    _, c1 = _usuario("cliente", "c1@t.com", latitude=LAT, longitude=LON)
    _, c2 = _usuario("cliente", "c2@t.com", latitude=LAT, longitude=LON)
    assert _pedir_domicilio(http, c1, fid, sid).status_code == 200
    r = http.post(f"{V1}/chamados", json={
        "barbearia_id": loja["id"], "servico_id": loja["servico_id"],
        "barbeiro_id": fid, "barbeiro_selecionado_id": fid,
        "data_hora_inicio": datetime.utcnow().isoformat(),
        "cliente_latitude": LAT, "cliente_longitude": LON,
    }, headers=c2)
    assert r.status_code == 400
    assert "domicílio" in r.json()["detail"]


# ---------------------------------------------------------------- valores a cobrar a domicílio

def _valores(http, headers, itens):
    return http.put(f"{V1}/domicilio/valores", json={"itens": itens}, headers=headers)


def test_valores_a_domicilio_cadastrar_alterar_remover(http):
    fid, headers, _ = _freelancer(http, "f@t.com", PERTO, servico=False, ligar=False)
    r = http.get(f"{V1}/domicilio/valores", headers=headers)
    assert r.status_code == 200
    modelos = {i["nome"]: i for i in r.json()["itens"]}
    assert "Corte Masculino" in modelos and modelos["Corte Masculino"]["valor"] is None

    r = _valores(http, headers, [
        {"nome": "Corte Masculino", "categoria": "corte", "valor": 50, "duracao_minutos": 30},
        {"nome": "Barba Completa", "categoria": "barba", "valor": 30, "duracao_minutos": 20},
    ])
    assert r.status_code == 200, r.text
    itens = {i["nome"]: i for i in r.json()["itens"]}
    assert itens["Corte Masculino"]["valor"] == 50 and itens["Barba Completa"]["valor"] == 30

    # sem chamados: altera no lugar
    corte_id = itens["Corte Masculino"]["servico_id"]
    itens = {i["nome"]: i for i in _valores(http, headers, [
        {"nome": "Corte Masculino", "categoria": "corte", "valor": 55, "duracao_minutos": 30},
        {"nome": "Barba Completa", "categoria": "barba", "valor": None, "duracao_minutos": 20},
    ]).json()["itens"]}
    assert itens["Corte Masculino"]["servico_id"] == corte_id and itens["Corte Masculino"]["valor"] == 55
    assert itens["Barba Completa"]["valor"] is None          # vazio = não oferece mais


def test_preco_fica_preso_ao_chamado(http):
    fid, headers, _ = _freelancer(http, "f@t.com", PERTO, servico=False, ligar=False)
    sid = {i["nome"]: i for i in _valores(http, headers, [
        {"nome": "Corte Masculino", "categoria": "corte", "valor": 50, "duracao_minutos": 30},
    ]).json()["itens"]}["Corte Masculino"]["servico_id"]
    http.put(f"{V1}/domicilio/atendimento", json={"atende_domicilio": True}, headers=headers)
    _, cliente = _usuario("cliente", "c@t.com", latitude=LAT, longitude=LON)
    cid = _pedir_domicilio(http, cliente, fid, sid).json()["id"]

    # freelancer muda o preço depois do pedido
    novo = {i["nome"]: i for i in _valores(http, headers, [
        {"nome": "Corte Masculino", "categoria": "corte", "valor": 70, "duracao_minutos": 30},
    ]).json()["itens"]}["Corte Masculino"]
    assert novo["valor"] == 70 and novo["servico_id"] != sid

    c = _chamado(cid)
    assert c.servico_id == sid and c.valor_total == 50.0
    pedido = next(p for p in http.get(f"{V1}/cliente/meus_pedidos", headers=cliente).json() if p["id"] == cid)
    assert pedido["valor"] == 50

    # cliente vê o preço novo; o id antigo não serve mais para pedido novo
    servicos = http.get(f"{V1}/domicilio/freelancer/{fid}/servicos", headers=cliente).json()["servicos"]
    assert [(s["id"], s["valor"]) for s in servicos] == [(novo["servico_id"], 70)]


def test_precos_domicilio_nao_aparecem_na_barbearia(http):
    loja = _barbearia()
    fid, headers, _ = _freelancer(http, "f@t.com", PERTO)
    nomes = [s["nome"] for s in http.get(f"{V1}/barbearia/{loja['id']}/servicos", headers=headers).json()]
    assert nomes == ["Corte"]
    # proprietário não vê os preços particulares do freelancer
    assert http.get(f"{V1}/domicilio/freelancer/{fid}/servicos", headers=loja["headers"]).status_code == 403
