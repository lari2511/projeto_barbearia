"""
Freelancer com taxa pendente: segue visível e informado, mas não consegue trabalhar.

Pendência = fechamento em aberto com prazo vencido (pagamento_diario.fechamento_bloqueante).
SQLite temporário, sem chamadas externas.

    .venv/Scripts/python -m pytest test_taxa_pendente_freelancer.py -v
"""

import os
import tempfile
from datetime import date, datetime, timedelta

_DB = os.path.join(tempfile.mkdtemp(prefix="bm_taxa_"), "teste.db")
os.environ["DATABASE_URL"] = f"sqlite:///{_DB}"

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app import models, routes_interesse, routes_on_demand  # noqa: E402
from app import pagamento_diario as pd  # noqa: E402
from app.database import Base, SessionLocal, engine, init_db  # noqa: E402
from app.main import app  # noqa: E402
from app.routes import create_access_token  # noqa: E402

V1 = "/api/v1"
BASE = f"{V1}/on-demand/cadeiras-acionadas"
LAT, LON = -23.55, -46.63
MENSAGEM = "Você precisa quitar a taxa pendente do BarberMove para voltar a utilizar as funcionalidades de trabalho."


@pytest.fixture(autouse=True)
def sem_rede(monkeypatch):
    monkeypatch.setattr(routes_on_demand, "_calcular_eta_osrm_minutos", lambda *a, **k: 3)
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


def _barbearia(email="dono@t.com", cadeiras=2):
    dono_id, headers = _usuario("barbearia", email)
    db = SessionLocal()
    try:
        b = models.Barbearia(usuario_id=dono_id, nome=f"Barbearia {email}", endereco="Rua A", latitude=LAT, longitude=LON)
        db.add(b)
        db.flush()
        for numero in range(1, cadeiras + 1):
            db.add(models.Cadeira(barbearia_id=b.id, numero=numero, status=models.StatusCadeira.DISPONIVEL))
        db.add(models.AssinaturaBarbearia(
            barbearia_id=b.id, quantidade_cadeiras=cadeiras, valor_mensalidade=50.0, dia_vencimento=10,
            proximo_vencimento=datetime.now() + timedelta(days=30), status="ativa",
        ))
        servico = models.Servico(barbearia_id=b.id, nome="Corte", categoria="corte", valor=50.0, duracao_minutos=30, ativo=True)
        db.add(servico)
        db.commit()
        return {"id": b.id, "dono_id": dono_id, "headers": headers, "servico_id": servico.id}
    finally:
        db.close()


def _freelancer(email, online=False):
    fid, headers = _usuario(
        "barbeiro", email, latitude=LAT, longitude=LON, online_regiao=online, disponivel=online, telefone=None,
    )
    db = SessionLocal()
    try:
        db.add(models.RadarFreelancer(freelancer_id=fid, is_online=online, em_atendimento=False, latitude=LAT, longitude=LON))
        db.commit()
    finally:
        db.close()
    return fid, headers


def _dever_taxa(freelancer_id, status="pendente"):
    db = SessionLocal()
    try:
        ontem = pd.agora_sp().date() - timedelta(days=2)
        f = models.FechamentoDiarioFreelancer(
            freelancer_id=freelancer_id, data_referencia=ontem, valor_devido=12.5, status=status,
            fechado_em=datetime.utcnow() - timedelta(days=2),  # prazo já vencido
        )
        db.add(f)
        db.commit()
        return f.id
    finally:
        db.close()


def _quitar(fechamento_id):
    """Mesmo resultado do mecanismo financeiro existente: o fechamento fica confirmado."""
    db = SessionLocal()
    try:
        db.get(models.FechamentoDiarioFreelancer, fechamento_id).status = "confirmado"
        db.commit()
    finally:
        db.close()


def _chamado(loja, cliente_id, freelancer_id, status="confirmado"):
    db = SessionLocal()
    try:
        c = models.Chamado(
            cliente_id=cliente_id, barbeiro_id=freelancer_id, barbearia_id=loja["id"], servico_id=loja["servico_id"],
            status=status, valor_original=50.0, valor_final=50.0, data_hora_inicio=datetime.utcnow(),
        )
        db.add(c)
        db.commit()
        return c.id
    finally:
        db.close()


def _status_chamado(chamado_id):
    db = SessionLocal()
    try:
        return db.get(models.Chamado, chamado_id).status
    finally:
        db.close()


def _notificacoes(usuario_id, tipo):
    db = SessionLocal()
    try:
        return db.query(models.Notificacao).filter_by(usuario_id=usuario_id, tipo=tipo).count()
    finally:
        db.close()


def _contar(modelo):
    db = SessionLocal()
    try:
        return db.query(modelo).count()
    finally:
        db.close()


def _campos_usuario(usuario_id):
    db = SessionLocal()
    try:
        u = db.get(models.Usuario, usuario_id)
        return {"disponivel": u.disponivel, "online": u.online_regiao, "presente": u.presente_em_local}
    finally:
        db.close()


# 1. Busca de profissionais
def test_aparece_na_busca_de_clientes_sem_indicar_disponibilidade(http):
    fid, _ = _freelancer("f@t.com")
    outro, _ = _freelancer("outro@t.com")  # offline sem débito: segue fora da busca por proximidade
    _dever_taxa(fid)
    _, cliente = _usuario("cliente", "c@t.com")

    proximos = http.get(f"{V1}/barbeiros/proximos", params={"latitude": LAT, "longitude": LON}, headers=cliente).json()
    assert [b["id"] for b in proximos] == [fid]
    assert proximos[0]["indisponivel"] is True
    assert proximos[0]["nome"] == "f"
    assert proximos[0]["disponivel"] is False and proximos[0]["online_regiao"] is False

    todos = {b["id"]: b for b in http.get(f"{V1}/barbeiros/todos", headers=cliente).json()}
    assert todos[fid]["indisponivel"] is True and todos[fid]["disponivel"] is False
    assert todos[outro]["indisponivel"] is False


def test_aparece_na_lista_da_barbearia_depois_dos_disponiveis(http):
    loja = _barbearia()
    devedor, _ = _freelancer("a_devedor@t.com")
    online, _ = _freelancer("z_online@t.com", online=True)
    offline, _ = _freelancer("m_offline@t.com")
    _dever_taxa(devedor)
    _, cliente = _usuario("cliente", "c@t.com")
    url = f"{V1}/barbearia/{loja['id']}/barbeiros-priorizados"
    lista = http.get(url, params={"latitude": LAT, "longitude": LON}, headers=cliente).json()["barbeiros"]
    assert [b["id"] for b in lista] == [online, devedor]
    assert [b["indisponivel"] for b in lista] == [False, True]
    assert lista[1]["disponivel"] is False and lista[1]["pode_receber_chamado_agora"] is False
    assert offline not in [b["id"] for b in lista]
    # Fora do raio do cliente, não entra.
    longe = http.get(url, params={"latitude": -3.0, "longitude": -60.0}, headers=cliente).json()["barbeiros"]
    assert devedor not in [b["id"] for b in longe]


def test_cliente_nao_descobre_que_o_motivo_e_financeiro(http):
    fid, _ = _freelancer("f@t.com")
    _dever_taxa(fid)
    _, cliente = _usuario("cliente", "c@t.com")
    for rota in (f"{V1}/usuario/{fid}", f"{V1}/barbeiros/todos"):
        texto = http.get(rota, headers=cliente).text.lower()
        assert "taxa" not in texto and "debito" not in texto and "pagamento" not in texto


# 2. Perfil
def test_perfil_abre_como_indisponivel(http):
    fid, _ = _freelancer("f@t.com", online=True)
    _dever_taxa(fid)
    _, cliente = _usuario("cliente", "c@t.com")
    r = http.get(f"{V1}/usuario/{fid}", headers=cliente)
    assert r.status_code == 200
    perfil = r.json()
    assert perfil["indisponivel"] is True and perfil["disponivel"] is False and perfil["online_regiao"] is False
    assert perfil["nome"] == "f"


# Sem contato direto enquanto houver taxa: o atendimento não pode ser combinado por fora.
def test_telefone_nao_sai_com_taxa_pendente_nem_depois_de_quitar(http):
    loja = _barbearia()
    fid, f_headers = _freelancer("f@t.com")
    db = SessionLocal()
    try:
        db.get(models.Usuario, fid).telefone = "11911112222"
        db.commit()
    finally:
        db.close()
    fechamento = _dever_taxa(fid)
    _, cliente = _usuario("cliente", "c@t.com")
    rotas = (
        (f"{V1}/usuario/{fid}", {}),
        (f"{V1}/barbeiros/todos", {}),
        (f"{V1}/barbeiros/proximos", {"latitude": LAT, "longitude": LON}),
        (f"{V1}/barbearia/{loja['id']}/barbeiros-priorizados", {"latitude": LAT, "longitude": LON}),
    )
    for rota, params in rotas:
        r = http.get(rota, params=params, headers=cliente)
        assert r.status_code == 200 and "11911112222" not in r.text, rota
    # O próprio freelancer continua vendo o número e o cadastro é preservado.
    assert http.get(f"{V1}/usuario/{fid}", headers=f_headers).json()["telefone"] == "11911112222"
    db = SessionLocal()
    try:
        assert db.get(models.Usuario, fid).telefone == "11911112222"
    finally:
        db.close()

    _quitar(fechamento)
    assert http.get(f"{V1}/usuario/{fid}", headers=cliente).json()["telefone"] is None
    assert http.get(f"{V1}/usuario/{fid}", headers=f_headers).json()["telefone"] == "11911112222"


# 3. Interesse
def test_interesse_notifica_sem_criar_chamado(http):
    fid, _ = _freelancer("f@t.com")
    _dever_taxa(fid)
    _, cliente = _usuario("cliente", "c@t.com")
    _, outro_cliente = _usuario("cliente", "c2@t.com")
    chamados = _contar(models.Chamado)
    solicitacoes = _contar(models.SolicitacaoBarbeiro)

    url = f"{V1}/interesse-atendimento/freelancer/{fid}"
    assert http.post(url, headers=cliente).json()["registrado"] is True
    assert _notificacoes(fid, "interesse_cliente") == 1
    # Reabrir o perfil no mesmo dia não gera spam; outro cliente gera novo aviso.
    assert http.post(url, headers=cliente).json()["registrado"] is False
    assert _notificacoes(fid, "interesse_cliente") == 1
    assert http.post(url, headers=outro_cliente).json()["registrado"] is True
    assert _notificacoes(fid, "interesse_cliente") == 2

    assert _contar(models.Chamado) == chamados
    assert _contar(models.SolicitacaoBarbeiro) == solicitacoes

    db = SessionLocal()
    try:
        n = db.query(models.Notificacao).filter_by(usuario_id=fid, tipo="interesse_cliente").first()
        assert "interesse em marcar um corte" in n.mensagem
    finally:
        db.close()


def test_interesse_nao_notifica_sem_debito_nem_por_quem_nao_e_cliente(http):
    fid, f_headers = _freelancer("f@t.com")
    _, cliente = _usuario("cliente", "c@t.com")
    url = f"{V1}/interesse-atendimento/freelancer/{fid}"
    assert http.post(url, headers=cliente).json()["registrado"] is False
    _dever_taxa(fid)
    assert http.post(url, headers=f_headers).json()["registrado"] is False
    assert _notificacoes(fid, "interesse_cliente") == 0


# 4 e 5. Vagas de diária
def test_recebe_notificacao_e_ve_a_vaga_de_diaria_mesmo_offline(http):
    loja = _barbearia()
    fid, headers = _freelancer("f@t.com")
    _dever_taxa(fid)
    assert http.post(f"{BASE}/anunciar", json={"quantidade": 1}, headers=loja["headers"]).status_code == 201

    assert _notificacoes(fid, "vaga_disponivel") == 1
    ativas = http.get(f"{BASE}/ativas", headers=headers).json()
    assert len(ativas) == 1
    assert ativas[0]["barbearia_nome"] == "Barbearia dono@t.com"
    assert ativas[0]["tipo_servico"] == "vaga_diaria"
    assert ativas[0]["cadeira_numero"] == 1
    assert ativas[0]["barbearia_usuario_id"] == loja["dono_id"]


def test_com_debito_longe_do_raio_nao_recebe_nem_ve(http):
    loja = _barbearia()
    fid, headers = _freelancer("f@t.com")
    db = SessionLocal()
    try:
        radar = db.query(models.RadarFreelancer).filter_by(freelancer_id=fid).one()
        radar.latitude, radar.longitude = -22.0, -43.0
        db.commit()
    finally:
        db.close()
    _dever_taxa(fid)
    http.post(f"{BASE}/anunciar", json={"quantidade": 1}, headers=loja["headers"])
    assert _notificacoes(fid, "vaga_disponivel") == 0
    assert http.get(f"{BASE}/ativas", headers=headers).json() == []


def test_com_debito_nao_ve_vaga_relampago(http):
    loja = _barbearia()
    fid, headers = _freelancer("f@t.com")
    _dever_taxa(fid)
    assert http.post(f"{BASE}/acionar", json={"raio_km": 5, "expira_em_minutos": 10}, headers=loja["headers"]).status_code == 201
    assert _notificacoes(fid, "vaga_disponivel") == 0
    assert http.get(f"{BASE}/ativas", headers=headers).json() == []


# 6. Candidatura
def test_nao_consegue_se_candidatar_e_recebe_a_mensagem(http):
    loja = _barbearia()
    fid, headers = _freelancer("f@t.com")
    _dever_taxa(fid)
    vaga = http.post(f"{BASE}/anunciar", json={"quantidade": 1}, headers=loja["headers"]).json()
    vaga_id = http.get(f"{BASE}/ativas", headers=headers).json()[0]["id"]
    assert vaga is not None

    r = http.post(f"{BASE}/{vaga_id}/candidatar-se", headers=headers)
    assert r.status_code == 403
    assert r.json()["detail"] == MENSAGEM
    assert _contar(models.CadeiraAcionadaCandidatura) == 0
    assert _notificacoes(loja["dono_id"], "vaga_candidatura") == 0


# 7. Online
@pytest.mark.parametrize("chamada", [
    ("post", "/api/v1/on-demand/ligar-radar", {"latitude": LAT, "longitude": LON, "is_online": True}),
    ("put", "/api/v1/barbeiro/status", {"status": "online_region"}),
    ("put", "/api/v1/barbeiro/disponibilidade", {"disponivel": True}),
    ("patch", "/api/v1/usuarios/me", {"disponivel": True}),
    ("patch", "/api/v1/usuarios/me/presenca", {"presente_em_local": True}),
])
def test_nao_consegue_ficar_online_por_nenhuma_rota(http, chamada):
    fid, headers = _freelancer("f@t.com")
    _dever_taxa(fid)
    metodo, rota, corpo = chamada
    getattr(http, metodo)(rota, json=corpo, headers=headers)

    assert _campos_usuario(fid) == {"disponivel": False, "online": False, "presente": False}
    db = SessionLocal()
    try:
        assert db.query(models.RadarFreelancer).filter_by(freelancer_id=fid).one().is_online is False
    finally:
        db.close()


def test_status_online_do_freelancer_e_recusado_com_403(http):
    fid, headers = _freelancer("f@t.com")
    _dever_taxa(fid)
    assert http.post(f"{V1}/freelancer/{fid}/alterar-status", json={"status": "online"}, headers=headers).status_code in (400, 403)
    assert _campos_usuario(fid)["online"] is False


# 8. Chamados
def test_cliente_nao_consegue_criar_chamado_efetivo(http):
    loja = _barbearia()
    fid, _ = _freelancer("f@t.com")
    _dever_taxa(fid)
    _, cliente = _usuario("cliente", "c@t.com", latitude=LAT, longitude=LON)
    antes = _contar(models.Chamado)
    r = http.post(f"{V1}/chamados", json={
        "barbearia_id": loja["id"], "servico_id": loja["servico_id"], "barbeiro_id": fid,
        "data_hora_inicio": (datetime.utcnow() + timedelta(minutes=30)).isoformat(),
    }, headers=cliente)
    assert r.status_code >= 400
    assert _contar(models.Chamado) == antes


def test_nao_consegue_aceitar_chamado(http):
    loja = _barbearia()
    fid, headers = _freelancer("f@t.com")
    cid, _ = _usuario("cliente", "c@t.com")
    chamado = _chamado(loja, cid, fid, status="pendente")
    _dever_taxa(fid)
    assert http.put(f"{V1}/chamados/{chamado}/aceitar", headers=headers).status_code == 403
    assert _status_chamado(chamado) == "pendente"


def test_chamado_direcionado_pela_barbearia_e_recusado(http):
    loja = _barbearia()
    fid, _ = _freelancer("f@t.com")
    db = SessionLocal()
    try:
        cadastro = models.Freelancer(usuario_id=fid, tempo_experiencia_anos=1)
        for campo, valor in (("nome", "f"), ("cpf", "11111111111"), ("telefone", "11900000000"), ("email", "f@t.com")):
            if hasattr(models.Freelancer, campo):
                setattr(cadastro, campo, valor)
        db.add(cadastro)
        db.commit()
        cadastro_id = cadastro.id
    finally:
        db.close()
    _dever_taxa(fid)
    antes = _contar(models.Chamado)
    r = http.post(f"{V1}/freelancer/solicitar", json={"freelancer_id": cadastro_id}, headers=loja["headers"])
    assert r.status_code == 409
    assert _contar(models.Chamado) == antes


# 9. Atendimento e diária
def test_nao_consegue_iniciar_atendimento(http):
    loja = _barbearia()
    fid, headers = _freelancer("f@t.com")
    cid, _ = _usuario("cliente", "c@t.com")
    chamado = _chamado(loja, cid, fid)
    _dever_taxa(fid)
    assert http.put(f"{V1}/chamados/{chamado}/iniciar-corte", headers=headers).status_code == 403
    assert http.put(f"{V1}/chamados/{chamado}/chegar", headers=headers).status_code == 403
    assert _status_chamado(chamado) == "confirmado"
    assert _campos_usuario(fid)["presente"] is False


def test_chegada_de_ambos_nao_inicia_atendimento_com_taxa_pendente(http):
    loja = _barbearia()
    fid, _ = _freelancer("f@t.com")
    cid, cliente = _usuario("cliente", "c@t.com", latitude=LAT, longitude=LON)
    chamado = _chamado(loja, cid, fid)
    db = SessionLocal()
    try:
        db.get(models.Chamado, chamado).barbeiro_chegou = True
        db.commit()
    finally:
        db.close()
    _dever_taxa(fid)
    assert http.put(f"{V1}/chamados/{chamado}/chegar", headers=cliente).status_code == 200
    assert _status_chamado(chamado) == "confirmado"


def test_conclui_o_atual_mas_a_fila_nao_inicia_o_proximo(http):
    loja = _barbearia()
    fid, headers = _freelancer("f@t.com")
    cid, _ = _usuario("cliente", "c@t.com")
    cid2, _ = _usuario("cliente", "c2@t.com")
    atual = _chamado(loja, cid, fid, status="em_atendimento")
    proximo = _chamado(loja, cid2, fid)
    _dever_taxa(fid)
    assert http.put(f"{V1}/chamados/{atual}/finalizar", headers=headers).status_code == 200
    assert _status_chamado(atual) == "concluido"
    assert _status_chamado(proximo) == "confirmado"
    assert _notificacoes(cid2, "chamado") >= 1
    db = SessionLocal()
    try:
        u = db.get(models.Usuario, fid)
        assert u.em_atendimento is False and u.disponivel is False
    finally:
        db.close()


def test_dono_nao_consegue_escolher_quem_tem_taxa_pendente(http):
    loja = _barbearia()
    fid, headers = _freelancer("f@t.com", online=True)
    http.post(f"{BASE}/anunciar", json={"quantidade": 1}, headers=loja["headers"])
    vaga_id = http.get(f"{BASE}/ativas", headers=headers).json()[0]["id"]
    assert http.post(f"{BASE}/{vaga_id}/candidatar-se", headers=headers).status_code == 200

    # Candidatou-se antes de a taxa vencer; depois disso não pode assumir a diária.
    _dever_taxa(fid)
    r = http.post(f"{BASE}/{vaga_id}/escolher-freelancer", json={"barbeiro_id": fid}, headers=loja["headers"])
    assert r.status_code >= 400
    assert _campos_usuario(fid)["presente"] is False
    db = SessionLocal()
    try:
        assert db.get(models.CadeiraAcionada, vaga_id).status == "disponivel"
    finally:
        db.close()


# 10. Liberação
def test_pagamento_confirmado_retira_as_restricoes_automaticamente(http):
    loja = _barbearia()
    fid, headers = _freelancer("f@t.com")
    fechamento = _dever_taxa(fid)
    _, cliente = _usuario("cliente", "c@t.com")
    assert http.post(f"{V1}/on-demand/ligar-radar", json={"latitude": LAT, "longitude": LON, "is_online": True}, headers=headers).json()["is_online"] is False
    assert http.get(f"{V1}/usuario/{fid}", headers=cliente).json()["indisponivel"] is True

    _quitar(fechamento)

    assert http.get(f"{V1}/usuario/{fid}", headers=cliente).json()["indisponivel"] is False
    assert http.post(f"{V1}/on-demand/ligar-radar", json={"latitude": LAT, "longitude": LON, "is_online": True}, headers=headers).json()["is_online"] is True
    http.post(f"{BASE}/anunciar", json={"quantidade": 1}, headers=loja["headers"])
    vaga_id = http.get(f"{BASE}/ativas", headers=headers).json()[0]["id"]
    assert http.post(f"{BASE}/{vaga_id}/candidatar-se", headers=headers).status_code == 200
    # Nenhum aviso de interesse depois de quitar.
    assert http.post(f"{V1}/interesse-atendimento/freelancer/{fid}", headers=cliente).json()["registrado"] is False


# Dentro do prazo não há restrição: só o fechamento vencido bloqueia.
def test_taxa_dentro_do_prazo_nao_restringe(http):
    fid, headers = _freelancer("f@t.com")
    db = SessionLocal()
    try:
        amanha = pd.agora_sp().date() + timedelta(days=1)
        db.add(models.FechamentoDiarioFreelancer(freelancer_id=fid, data_referencia=amanha, valor_devido=5.0, status="pendente"))
        db.commit()
    finally:
        db.close()
    _, cliente = _usuario("cliente", "c@t.com")
    assert http.get(f"{V1}/usuario/{fid}", headers=cliente).json()["indisponivel"] is False
    assert http.post(f"{V1}/on-demand/ligar-radar", json={"latitude": LAT, "longitude": LON, "is_online": True}, headers=headers).json()["is_online"] is True


# 11. Sem débito segue igual
def test_freelancer_sem_debito_continua_normal(http):
    loja = _barbearia()
    fid, headers = _freelancer("f@t.com", online=True)
    offline, off_headers = _freelancer("off@t.com")
    cid, cliente = _usuario("cliente", "c@t.com")

    http.post(f"{BASE}/anunciar", json={"quantidade": 1}, headers=loja["headers"])
    assert _notificacoes(fid, "vaga_disponivel") == 1
    # Offline sem débito continua sem aviso e sem lista, como antes.
    assert _notificacoes(offline, "vaga_disponivel") == 0
    assert http.get(f"{BASE}/ativas", headers=off_headers).json() == []
    ativas = http.get(f"{BASE}/ativas", headers=headers).json()
    assert http.post(f"{BASE}/{ativas[0]['id']}/candidatar-se", headers=headers).status_code == 200

    assert http.get(f"{V1}/usuario/{fid}", headers=cliente).json()["indisponivel"] is False
    lista = http.get(f"{V1}/barbeiros/proximos", params={"latitude": LAT, "longitude": LON}, headers=cliente).json()
    assert [b["id"] for b in lista] == [fid] and lista[0]["indisponivel"] is False

    chamado = _chamado(loja, cid, fid)
    assert http.put(f"{V1}/chamados/{chamado}/iniciar-corte", headers=headers).status_code == 200
    assert _status_chamado(chamado) == "em_atendimento"
    prox = _chamado(loja, cid, fid)
    assert http.put(f"{V1}/chamados/{chamado}/finalizar", headers=headers).status_code == 200
    # Sem débito, a fila continua avançando sozinha.
    assert _status_chamado(prox) == "em_atendimento"
