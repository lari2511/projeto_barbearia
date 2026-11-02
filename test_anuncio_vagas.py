"""
Anúncio de vagas pela tela inicial do dono: limite por cadeiras pagas (inclusive bloqueadas),
vagas independentes, seleção sem desbloqueio, chat privado e bloqueio dos chamados.

SQLite temporário, sem chamadas externas.

    .venv/Scripts/python -m pytest test_anuncio_vagas.py -v
"""

import os
import tempfile
import threading
from datetime import datetime, timedelta

_DB = os.path.join(tempfile.mkdtemp(prefix="bm_vagas_"), "teste.db")
os.environ["DATABASE_URL"] = f"sqlite:///{_DB}"

import pytest  # noqa: E402
from fastapi import HTTPException  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app import models, routes_on_demand, vagas as regras_vagas  # noqa: E402
from app.database import Base, SessionLocal, engine, init_db  # noqa: E402
from app.main import app  # noqa: E402
from app.routes import create_access_token  # noqa: E402
from app.routes_assinaturas import aplicar_contratacao_cadeiras, aplicar_pagamento_mensalidade, mensalidade_devida  # noqa: E402

BASE = "/api/v1/on-demand/cadeiras-acionadas"
LAT, LON = -23.55, -46.63


@pytest.fixture(autouse=True)
def sem_rota_externa(monkeypatch):
    monkeypatch.setattr(routes_on_demand, "_calcular_eta_osrm_minutos", lambda *a, **k: 3)


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


def _barbearia(email, pagas, linhas=None, status=models.StatusCadeira.BLOQUEADA, assinatura="ativa", vencida=False):
    """Dono com `pagas` cadeiras na assinatura e `linhas` cadeiras cadastradas (padrão: iguais)."""
    dono_id, headers = _usuario("barbearia", email)
    db = SessionLocal()
    try:
        b = models.Barbearia(usuario_id=dono_id, nome=f"Barbearia {email}", endereco="Rua A", latitude=LAT, longitude=LON)
        db.add(b)
        db.flush()
        for numero in range(1, (pagas if linhas is None else linhas) + 1):
            db.add(models.Cadeira(barbearia_id=b.id, numero=numero, status=status))
        if pagas:
            venc = datetime.now() + (timedelta(days=-1) if vencida else timedelta(days=30))
            db.add(models.AssinaturaBarbearia(
                barbearia_id=b.id, quantidade_cadeiras=pagas, valor_mensalidade=50.0, dia_vencimento=10,
                proximo_vencimento=venc, status=assinatura,
            ))
        servico = models.Servico(barbearia_id=b.id, nome="Corte", categoria="corte", valor=50.0, duracao_minutos=30, ativo=True)
        db.add(servico)
        db.commit()
        return {"id": b.id, "dono_id": dono_id, "headers": headers, "servico_id": servico.id}
    finally:
        db.close()


def _freelancer(email):
    fid, headers = _usuario("barbeiro", email, latitude=LAT, longitude=LON, online_regiao=True, disponivel=True)
    db = SessionLocal()
    try:
        db.add(models.RadarFreelancer(freelancer_id=fid, is_online=True, em_atendimento=False, latitude=LAT, longitude=LON))
        db.commit()
    finally:
        db.close()
    return fid, headers


def _cadeiras(barbearia_id):
    db = SessionLocal()
    try:
        return [
            (c.id, c.status, c.freelancer_id)
            for c in db.query(models.Cadeira).filter(models.Cadeira.barbearia_id == barbearia_id).order_by(models.Cadeira.numero)
        ]
    finally:
        db.close()


def _resumo(http, loja):
    r = http.get(f"{BASE}/resumo", headers=loja["headers"])
    assert r.status_code == 200, r.text
    return r.json()


def _anunciar(http, loja, quantidade):
    return http.post(f"{BASE}/anunciar", json={"quantidade": quantidade}, headers=loja["headers"])


def _publicar(http, loja, quantidade):
    r = _anunciar(http, loja, quantidade)
    assert r.status_code == 201, r.text
    return r.json()["publicadas"]


def _selecionar(http, loja, vaga_id, freelancer):
    fid, headers = freelancer
    assert http.post(f"{BASE}/{vaga_id}/candidatar-se", headers=headers).status_code == 200
    r = http.post(f"{BASE}/{vaga_id}/escolher-freelancer", json={"barbeiro_id": fid}, headers=loja["headers"])
    assert r.status_code == 200, r.text


def _chamar(http, loja, cliente_headers, barbeiro_id=None, cadeira_id=None):
    return http.post("/api/v1/chamados", headers=cliente_headers, json={
        "servico_id": loja["servico_id"],
        "barbearia_id": loja["id"],
        "barbeiro_id": barbeiro_id,
        "cadeira_id": cadeira_id,
        "data_hora_inicio": datetime.utcnow().isoformat(),
        "cliente_latitude": LAT,
        "cliente_longitude": LON,
    })


# Itens 1 a 4 da especificação
@pytest.mark.parametrize("pagas", [1, 2, 3, 5])
def test_anuncia_ate_o_limite_com_cadeiras_bloqueadas(http, pagas):
    loja = _barbearia("dono@t.com", pagas)
    assert _resumo(http, loja)["vagas_disponiveis_para_anunciar"] == pagas

    assert len(_publicar(http, loja, pagas)) == pagas

    resumo = _resumo(http, loja)
    assert resumo["vagas_anunciadas"] == pagas
    assert resumo["vagas_disponiveis_para_anunciar"] == 0
    assert _anunciar(http, loja, 1).status_code == 409
    assert all(status == models.StatusCadeira.BLOQUEADA for _, status, _f in _cadeiras(loja["id"]))


# Item 7
def test_vagas_ja_publicadas_entram_no_limite(http):
    loja = _barbearia("dono@t.com", 3)
    _publicar(http, loja, 2)
    assert _resumo(http, loja)["vagas_disponiveis_para_anunciar"] == 1
    assert _anunciar(http, loja, 2).status_code == 409
    assert len(_publicar(http, loja, 1)) == 1


# Item 8: API direta, inclusive o endpoint antigo por cadeira
@pytest.mark.parametrize("quantidade", [0, -1])
def test_api_recusa_quantidade_invalida(http, quantidade):
    loja = _barbearia("dono@t.com", 2)
    assert _anunciar(http, loja, quantidade).status_code == 422
    assert _resumo(http, loja)["vagas_anunciadas"] == 0


def test_api_recusa_acima_do_limite_sem_publicar_nada(http):
    loja = _barbearia("dono@t.com", 2)
    assert _anunciar(http, loja, 3).status_code == 409
    assert _resumo(http, loja)["vagas_anunciadas"] == 0


def test_endpoint_antigo_acionar_respeita_o_limite(http):
    loja = _barbearia("dono@t.com", 1, status=models.StatusCadeira.DISPONIVEL)
    cadeira_id = _cadeiras(loja["id"])[0][0]
    body = {"cadeira_id": cadeira_id, "raio_km": 5, "expira_em_minutos": 10}
    assert http.post(f"{BASE}/acionar", json=body, headers=loja["headers"]).status_code == 201
    assert http.post(f"{BASE}/acionar", json=body, headers=loja["headers"]).status_code == 409
    assert _anunciar(http, loja, 1).status_code == 409


def test_endpoint_antigo_recusa_cadeira_de_outra_barbearia(http):
    loja = _barbearia("dono@t.com", 1)
    outra = _barbearia("outro@t.com", 1)
    body = {"cadeira_id": _cadeiras(outra["id"])[0][0], "raio_km": 5, "expira_em_minutos": 10}
    assert http.post(f"{BASE}/acionar", json=body, headers=loja["headers"]).status_code == 404


@pytest.mark.parametrize("kwargs", [
    {"pagas": 0, "linhas": 3},
    {"pagas": 3, "vencida": True},
    {"pagas": 3, "assinatura": "inadimplente"},
])
def test_sem_pagamento_valido_nao_anuncia(http, kwargs):
    loja = _barbearia("dono@t.com", **kwargs)
    assert _resumo(http, loja)["cadeiras_pagas"] == 0
    assert _anunciar(http, loja, 1).status_code == 402


def test_cadeira_cadastrada_alem_das_pagas_nao_aumenta_o_limite(http):
    loja = _barbearia("dono@t.com", 2, linhas=5)
    assert _resumo(http, loja)["vagas_disponiveis_para_anunciar"] == 2
    assert _anunciar(http, loja, 3).status_code == 409


def test_anuncio_nunca_cria_cadeira(http):
    loja = _barbearia("dono@t.com", 3, linhas=0)
    assert _resumo(http, loja)["vagas_disponiveis_para_anunciar"] == 0
    assert _anunciar(http, loja, 1).status_code == 409
    assert _cadeiras(loja["id"]) == []


def test_cadeira_com_freelancer_nao_entra_no_anuncio(http):
    loja = _barbearia("dono@t.com", 3, status=models.StatusCadeira.DISPONIVEL)
    fid, _ = _freelancer("fre@t.com")
    db = SessionLocal()
    try:
        cadeira = db.query(models.Cadeira).filter(models.Cadeira.barbearia_id == loja["id"]).first()
        cadeira.status = models.StatusCadeira.OCUPADA
        cadeira.freelancer_id = fid
        db.commit()
    finally:
        db.close()
    assert _resumo(http, loja)["vagas_disponiveis_para_anunciar"] == 2


def test_anuncios_simultaneos_nao_ultrapassam_o_limite(http):
    loja = _barbearia("dono@t.com", 3)
    resultados = []
    largada = threading.Barrier(6)

    def anunciar():
        db = SessionLocal()
        try:
            barbearia = db.query(models.Barbearia).filter(models.Barbearia.id == loja["id"]).first()
            db.rollback()
            largada.wait()
            cadeira = regras_vagas.reservar_cadeiras(db, barbearia, 1)[0]
            db.add(models.CadeiraAcionada(
                barbearia_id=loja["id"], cadeira_id=cadeira.id, status=regras_vagas.STATUS_ABERTA, raio_km=5.0,
            ))
            db.commit()
            resultados.append("ok")
        except HTTPException as erro:
            db.rollback()
            resultados.append(erro.status_code)
        finally:
            db.close()

    threads = [threading.Thread(target=anunciar) for _ in range(6)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert sorted(map(str, resultados)) == ["409", "409", "409", "ok", "ok", "ok"]
    resumo = _resumo(http, loja)
    assert resumo["vagas_anunciadas"] == 3
    assert len({v["cadeira_id"] for v in resumo["vagas"]}) == 3


# Itens 9 e 10
def test_cada_vaga_e_real_e_tem_candidaturas_independentes(http):
    loja = _barbearia("dono@t.com", 3)
    a, b, c = _publicar(http, loja, 3)
    fre1, fre2 = _freelancer("f1@t.com"), _freelancer("f2@t.com")
    assert len({a, b, c}) == 3

    assert http.post(f"{BASE}/{a}/candidatar-se", headers=fre1[1]).status_code == 200
    assert http.post(f"{BASE}/{b}/candidatar-se", headers=fre2[1]).status_code == 200

    candidatos = lambda vaga: [
        x["freelancer_id"] for x in http.get(f"{BASE}/{vaga}/candidatos", headers=loja["headers"]).json()
    ]
    assert candidatos(a) == [fre1[0]]
    assert candidatos(b) == [fre2[0]]
    assert candidatos(c) == []

    db = SessionLocal()
    try:
        vagas = db.query(models.CadeiraAcionada).filter(models.CadeiraAcionada.id.in_([a, b, c])).all()
        assert all(v.tipo_servico == regras_vagas.TIPO_VAGA_DIARIA and v.expira_em > datetime.utcnow() for v in vagas)
    finally:
        db.close()


def test_freelancer_ve_vaga_de_cadeira_bloqueada(http):
    loja = _barbearia("dono@t.com", 1)
    vaga = _publicar(http, loja, 1)[0]
    _, headers = _freelancer("f1@t.com")
    assert [v["id"] for v in http.get(f"{BASE}/ativas", headers=headers).json()] == [vaga]


def test_perfil_do_freelancer_traz_o_tempo_de_experiencia_cadastrado(http):
    com_tempo, _ = _usuario("barbeiro", "com@t.com", tempo_experiencia="2 anos")
    sem_tempo, _ = _usuario("barbeiro", "sem@t.com")
    assert http.get(f"/api/v1/usuario/{com_tempo}").json()["tempo_experiencia"] == "2 anos"
    assert http.get(f"/api/v1/usuario/{sem_tempo}").json()["tempo_experiencia"] is None


def test_freelancer_altera_o_tempo_de_experiencia_no_proprio_perfil(http):
    fid, headers = _usuario("barbeiro", "f@t.com", tempo_experiencia="Menos de 1 ano")
    for opcao in ("1 ano", "2 anos", "3 anos", "4 anos ou mais"):
        assert http.patch("/api/v1/usuarios/me", json={"tempo_experiencia": opcao}, headers=headers).status_code == 200
        assert http.get(f"/api/v1/usuario/{fid}").json()["tempo_experiencia"] == opcao

    for invalido in ("9 anos", "", None, "5 anos ou mais"):
        assert http.patch("/api/v1/usuarios/me", json={"tempo_experiencia": invalido}, headers=headers).status_code == 400
    assert http.get(f"/api/v1/usuario/{fid}").json()["tempo_experiencia"] == "4 anos ou mais"

    # Outros campos do perfil não mexem no tempo.
    assert http.patch("/api/v1/usuarios/me", json={"nome": "Outro Nome"}, headers=headers).status_code == 200
    assert http.get(f"/api/v1/usuario/{fid}").json()["tempo_experiencia"] == "4 anos ou mais"


def test_so_freelancer_altera_tempo_de_experiencia(http):
    for tipo, email in (("cliente", "c@t.com"), ("barbearia", "b@t.com")):
        uid, headers = _usuario(tipo, email)
        assert http.patch("/api/v1/usuarios/me", json={"tempo_experiencia": "2 anos"}, headers=headers).status_code == 403
        db = SessionLocal()
        try:
            assert db.get(models.Usuario, uid).tempo_experiencia is None
        finally:
            db.close()


def test_perfil_da_barbearia_traz_endereco_completo_e_cep_cadastrados(http):
    loja = _barbearia("dono@t.com", 1)
    db = SessionLocal()
    try:
        b = db.get(models.Barbearia, loja["id"])
        b.endereco, b.cep = "Rua A, 99, Centro, São Paulo/SP", "01305000"
        db.commit()
    finally:
        db.close()
    perfil = http.get(f"/api/v1/usuario/{loja['dono_id']}").json()
    assert perfil["endereco"] == "Rua A, 99, Centro, São Paulo/SP"
    assert perfil["cep"] == "01305000"

    fid, _ = _usuario("barbeiro", "f@t.com")
    assert http.get(f"/api/v1/usuario/{fid}").json()["cep"] is None


def test_telefone_do_freelancer_nao_vai_para_o_proprietario(http):
    fid, f_headers = _usuario("barbeiro", "f@t.com", telefone="11911112222", tempo_experiencia="2 anos")
    _, dono_headers = _usuario("barbearia", "d@t.com")
    _, cliente_headers = _usuario("cliente", "c@t.com")
    url = f"/api/v1/usuario/{fid}"

    perfil_dono = http.get(url, headers=dono_headers).json()
    assert perfil_dono["telefone"] is None
    assert "11911112222" not in http.get(url, headers=dono_headers).text
    assert perfil_dono["tempo_experiencia"] == "2 anos"
    # Sem token (ou com token invalido) nao serve de atalho para pegar o numero.
    assert http.get(url).json()["telefone"] is None
    assert http.get(url, headers={"Authorization": "Bearer invalido"}).json()["telefone"] is None

    assert http.get(url, headers=cliente_headers).json()["telefone"] == "11911112222"
    assert http.get(url, headers=f_headers).json()["telefone"] == "11911112222"
    db = SessionLocal()
    try:
        assert db.get(models.Usuario, fid).telefone == "11911112222"
    finally:
        db.close()


def test_telefone_de_barbearia_e_cliente_segue_igual_no_perfil(http):
    dono_id, dono_headers = _usuario("barbearia", "d@t.com", telefone="11933334444")
    cliente_id, _ = _usuario("cliente", "c@t.com", telefone="11955556666")
    _, f_headers = _usuario("barbeiro", "f@t.com")
    assert http.get(f"/api/v1/usuario/{dono_id}", headers=f_headers).json()["telefone"] == "11933334444"
    assert http.get(f"/api/v1/usuario/{dono_id}").json()["telefone"] == "11933334444"
    assert http.get(f"/api/v1/usuario/{cliente_id}", headers=dono_headers).json()["telefone"] == "11955556666"


def _loja_com_ids_de_cadeira_altos(http):
    """Duas cadeiras (numeros 1 e 2) com ids altos, como quando outras barbearias ja cadastraram antes."""
    outra = _barbearia("outra@t.com", 10)
    loja = _barbearia("dono@t.com", 2)
    db = SessionLocal()
    try:
        linhas = db.query(models.Cadeira).filter(models.Cadeira.barbearia_id == loja["id"]).order_by(models.Cadeira.numero).all()
        ids = [c.id for c in linhas]
        assert [c.numero for c in linhas] == [1, 2] and min(ids) > 2 and outra["id"] != loja["id"]
    finally:
        db.close()
    return loja, ids


def test_vaga_mostra_o_numero_da_cadeira_e_nao_o_id(http):
    loja, ids = _loja_com_ids_de_cadeira_altos(http)
    _, headers = _freelancer("f1@t.com")
    _publicar(http, loja, 2)

    ativas = http.get(f"{BASE}/ativas", headers=headers).json()
    assert sorted(v["cadeira_numero"] for v in ativas) == [1, 2]
    assert sorted(v["cadeira_id"] for v in ativas) == ids
    assert all(v["cadeira_numero"] != v["cadeira_id"] for v in ativas)

    resumo = http.get(f"{BASE}/resumo", headers=loja["headers"]).json()
    assert [(v["cadeira_id"], v["cadeira_numero"]) for v in resumo["vagas"]] == [(ids[0], 1), (ids[1], 2)]


def test_anuncios_repetidos_nao_aumentam_a_numeracao_nem_duplicam_cadeira(http):
    loja, ids = _loja_com_ids_de_cadeira_altos(http)
    _, headers = _freelancer("f1@t.com")
    db = SessionLocal()
    try:
        total_de_cadeiras = db.query(models.Cadeira).count()
    finally:
        db.close()

    for _ in range(6):
        primeira = _publicar(http, loja, 1)[0]
        segunda = _publicar(http, loja, 1)[0]
        ativas = {v["id"]: v for v in http.get(f"{BASE}/ativas", headers=headers).json()}
        # Cadeira 1 tem vaga ativa: a proxima usa a 2. Nunca a mesma cadeira em duas vagas.
        assert (ativas[primeira]["cadeira_numero"], ativas[segunda]["cadeira_numero"]) == (1, 2)
        assert ativas[primeira]["cadeira_id"] != ativas[segunda]["cadeira_id"]
        # Sem cadeira livre, nao ha terceira vaga nem numero inexistente.
        extra = http.post(f"{BASE}/anunciar", json={"quantidade": 1}, headers=loja["headers"])
        assert extra.status_code == 409
        for vaga in (primeira, segunda):
            assert http.post(f"{BASE}/{vaga}/cancelar", headers=loja["headers"]).status_code == 200

    db = SessionLocal()
    try:
        assert db.query(models.Cadeira).count() == total_de_cadeiras
        assert db.query(models.AssinaturaBarbearia).filter_by(barbearia_id=loja["id"]).one().quantidade_cadeiras == 2
    finally:
        db.close()


def test_numero_da_cadeira_e_fixo_mesmo_com_outra_cadeira_removida(http):
    loja, ids = _loja_com_ids_de_cadeira_altos(http)
    db = SessionLocal()
    try:
        db.delete(db.get(models.Cadeira, ids[0]))
        db.commit()
    finally:
        db.close()
    resumo = http.get(f"{BASE}/resumo", headers=loja["headers"]).json()
    assert [c["numero"] for c in resumo["cadeiras_livres"]] == [2]
    vaga = _publicar(http, loja, 1)[0]
    _, headers = _freelancer("f1@t.com")
    assert http.get(f"{BASE}/ativas", headers=headers).json()[0]["cadeira_numero"] == 2
    resumo = http.get(f"{BASE}/resumo", headers=loja["headers"]).json()
    assert [(v["id"], v["cadeira_numero"]) for v in resumo["vagas"]] == [(vaga, 2)]


def _rotas_que_listam_freelancers(http, headers, barbearia_id):
    return {
        "todos": http.get("/api/v1/barbeiros/todos", headers=headers),
        "alias": http.get("/api/v1/freelancer/todos", headers=headers),
        "proximos": http.get("/api/v1/barbeiros/proximos", params={"latitude": LAT, "longitude": LON}, headers=headers),
        "proximos_post": http.post("/api/v1/barbeiros/proximos", json={"latitude": LAT, "longitude": LON, "raio_km": 10}, headers=headers),
        "presentes": http.get(f"/api/v1/barbearia/{barbearia_id}/barbeiros-presentes", headers=headers),
        "priorizados": http.get(f"/api/v1/barbearia/{barbearia_id}/barbeiros-priorizados", params={"latitude": LAT, "longitude": LON}, headers=headers),
    }


def test_listas_de_freelancers_so_entregam_telefone_a_quem_pode(http):
    loja = _barbearia("dono@t.com", 1)
    fid, f_headers = _freelancer("f1@t.com")
    # presentes/priorizados precisam do freelancer presente; as demais, online e aprovado.
    db = SessionLocal()
    try:
        u = db.get(models.Usuario, fid)
        u.telefone, u.disponivel, u.documento_verificado = "11911112222", True, True
        u.presente_em_local, u.barbearia_atual_id = True, loja["id"]
        db.commit()
    finally:
        db.close()
    _, cliente_headers = _usuario("cliente", "c@t.com")

    for nome, r in _rotas_que_listam_freelancers(http, loja["headers"], loja["id"]).items():
        assert r.status_code == 200, nome
        assert "11911112222" not in r.text, f"dono: {nome}"
    for nome, r in _rotas_que_listam_freelancers(http, {}, loja["id"]).items():
        assert r.status_code == 200, nome
        assert "11911112222" not in r.text, f"sem login: {nome}"
    para_cliente = _rotas_que_listam_freelancers(http, cliente_headers, loja["id"])
    for nome in ("todos", "alias", "presentes"):
        assert "11911112222" in para_cliente[nome].text, f"cliente: {nome}"
    # A lista segue trazendo o freelancer para o dono, so sem o numero.
    do_dono = http.get("/api/v1/barbeiros/todos", headers=loja["headers"]).json()
    assert [b["id"] for b in do_dono] == [fid] and do_dono[0]["telefone"] is None


def test_email_do_perfil_so_para_o_proprio_usuario(http):
    fid, f_headers = _usuario("barbeiro", "f@t.com")
    _, dono_headers = _usuario("barbearia", "d@t.com")
    _, cliente_headers = _usuario("cliente", "c@t.com")
    url = f"/api/v1/usuario/{fid}"
    assert http.get(url, headers=f_headers).json()["email"] == "f@t.com"
    for headers in ({}, dono_headers, cliente_headers):
        r = http.get(url, headers=headers)
        assert r.json()["email"] is None and "f@t.com" not in r.text


def test_telefone_de_cliente_nao_sai_sem_login(http):
    cid, _ = _usuario("cliente", "c@t.com", telefone="11955556666")
    _, f_headers = _usuario("barbeiro", "f@t.com")
    assert http.get(f"/api/v1/usuario/{cid}").json()["telefone"] is None
    assert http.get(f"/api/v1/usuario/{cid}", headers=f_headers).json()["telefone"] == "11955556666"


def test_vaga_informa_o_dono_para_abrir_o_perfil_e_os_mesmos_servicos(http):
    loja = _barbearia("dono@t.com", 1)
    _publicar(http, loja, 1)
    _, headers = _freelancer("f1@t.com")
    vaga = http.get(f"{BASE}/ativas", headers=headers).json()[0]
    assert vaga["barbearia_usuario_id"] == loja["dono_id"]

    perfil = http.get(f"/api/v1/usuario/{vaga['barbearia_usuario_id']}", headers=headers).json()
    assert perfil["barbearia_id"] == loja["id"]
    do_perfil = http.get(f"/api/v1/barbearias/{perfil['barbearia_id']}/servicos").json()["servicos"]
    do_cliente = http.get(f"/api/v1/barbearia/{loja['id']}/servicos", headers=headers).json()
    assert [(s["id"], s["valor"]) for s in do_perfil] == [(s["id"], s["valor"]) for s in do_cliente] == [(loja["servico_id"], 50.0)]


# Item 11
def test_dono_cancela_vaga_e_libera_o_limite(http):
    loja = _barbearia("dono@t.com", 1)
    vaga = _publicar(http, loja, 1)[0]
    assert http.post(f"{BASE}/{vaga}/cancelar", headers=loja["headers"]).status_code == 200
    resumo = _resumo(http, loja)
    assert resumo["vagas_anunciadas"] == 0
    assert resumo["vagas_disponiveis_para_anunciar"] == 1


def test_dono_dispensa_escolhido_antes_do_desbloqueio(http):
    loja = _barbearia("dono@t.com", 1)
    vaga = _publicar(http, loja, 1)[0]
    fre = _freelancer("f1@t.com")
    _selecionar(http, loja, vaga, fre)

    assert http.post(f"{BASE}/{vaga}/cancelar", headers=loja["headers"]).status_code == 200
    assert _resumo(http, loja)["vagas_disponiveis_para_anunciar"] == 1
    assert http.get("/api/v1/vagas/minhas-selecoes", headers=fre[1]).json() == []
    assert http.post(f"/api/v1/vagas/{vaga}/chat", json={"mensagem": "oi"}, headers=fre[1]).status_code == 409


def test_vaga_de_outra_barbearia_nao_pode_ser_administrada(http):
    loja = _barbearia("dono@t.com", 1)
    outra = _barbearia("outro@t.com", 1)
    vaga = _publicar(http, loja, 1)[0]
    assert http.post(f"{BASE}/{vaga}/cancelar", headers=outra["headers"]).status_code == 403
    assert http.get(f"{BASE}/{vaga}/candidatos", headers=outra["headers"]).status_code == 403


# Itens 12 e 13
def test_selecao_libera_chat_so_para_os_dois_e_nao_desbloqueia(http):
    loja = _barbearia("dono@t.com", 2)
    outra = _barbearia("outro@t.com", 1)
    vaga, vaga2 = _publicar(http, loja, 2)
    escolhido, nao_escolhido = _freelancer("f1@t.com"), _freelancer("f2@t.com")
    _, cliente = _usuario("cliente", "cli@t.com")
    chat = f"/api/v1/vagas/{vaga}/chat"

    assert http.post(f"{BASE}/{vaga}/candidatar-se", headers=nao_escolhido[1]).status_code == 200
    assert http.get(chat, headers=loja["headers"]).status_code == 403  # sem seleção não há chat
    assert http.get(chat, headers=escolhido[1]).status_code == 403

    _selecionar(http, loja, vaga, escolhido)

    assert all(status == models.StatusCadeira.BLOQUEADA for _, status, _f in _cadeiras(loja["id"]))
    assert all(f is None for _, _s, f in _cadeiras(loja["id"]))
    db = SessionLocal()
    try:
        fre = db.query(models.Usuario).filter(models.Usuario.id == escolhido[0]).first()
        assert not fre.presente_em_local  # status do freelancer só muda no desbloqueio
        assert fre.barbearia_atual_id is None
    finally:
        db.close()

    assert http.post(chat, json={"mensagem": "Chego às 10h"}, headers=escolhido[1]).status_code == 201
    assert http.post(chat, json={"mensagem": "Combinado"}, headers=loja["headers"]).status_code == 201
    assert [m["mensagem"] for m in http.get(chat, headers=loja["headers"]).json()["mensagens"]] == ["Chego às 10h", "Combinado"]

    for intruso in (nao_escolhido[1], cliente, outra["headers"]):
        assert http.get(chat, headers=intruso).status_code == 403
        assert http.post(chat, json={"mensagem": "x"}, headers=intruso).status_code == 403
        assert http.post(f"{chat}/marcar-lidas", headers=intruso).status_code == 403

    # A conversa é da vaga: a outra vaga da mesma barbearia segue sem chat.
    assert http.get(f"/api/v1/vagas/{vaga2}/chat", headers=loja["headers"]).status_code == 403


def test_nao_lidas_e_notificacao_do_chat(http):
    loja = _barbearia("dono@t.com", 1)
    vaga = _publicar(http, loja, 1)[0]
    fre = _freelancer("f1@t.com")
    _selecionar(http, loja, vaga, fre)
    chat = f"/api/v1/vagas/{vaga}/chat"

    for texto in ("a", "b"):
        http.post(chat, json={"mensagem": texto}, headers=fre[1])
    assert _resumo(http, loja)["vagas"][0]["nao_lidas"] == 2

    db = SessionLocal()
    try:
        avisos = db.query(models.Notificacao).filter(
            models.Notificacao.usuario_id == loja["dono_id"], models.Notificacao.tipo == "vaga_chat"
        ).count()
        assert avisos == 1
    finally:
        db.close()

    assert http.post(f"{chat}/marcar-lidas", headers=loja["headers"]).json()["marcadas"] == 2
    assert _resumo(http, loja)["vagas"][0]["nao_lidas"] == 0
    assert http.get("/api/v1/vagas/minhas-selecoes", headers=fre[1]).json()[0]["id"] == vaga


def test_mesmo_freelancer_nao_e_escolhido_duas_vezes(http):
    loja = _barbearia("dono@t.com", 2)
    a, b = _publicar(http, loja, 2)
    fre = _freelancer("f1@t.com")
    _selecionar(http, loja, a, fre)
    assert http.post(f"{BASE}/{b}/candidatar-se", headers=fre[1]).status_code == 200
    r = http.post(f"{BASE}/{b}/escolher-freelancer", json={"barbeiro_id": fre[0]}, headers=loja["headers"])
    assert r.status_code == 409


def test_vaga_selecionada_continua_ocupando_a_cadeira(http):
    loja = _barbearia("dono@t.com", 1)
    vaga = _publicar(http, loja, 1)[0]
    _selecionar(http, loja, vaga, _freelancer("f1@t.com"))
    resumo = _resumo(http, loja)
    assert resumo["vagas_anunciadas"] == 1
    assert resumo["vagas_disponiveis_para_anunciar"] == 0
    assert resumo["vagas"][0]["status"] == regras_vagas.STATUS_AGUARDANDO_DESBLOQUEIO


# Item 14
def test_cliente_nao_chama_nem_ve_cadeira_bloqueada(http):
    loja = _barbearia("dono@t.com", 2)
    vaga = _publicar(http, loja, 1)[0]
    fre = _freelancer("f1@t.com")
    _selecionar(http, loja, vaga, fre)
    _, cliente = _usuario("cliente", "cli@t.com", latitude=LAT, longitude=LON)
    cadeira_id = _cadeiras(loja["id"])[0][0]

    assert http.get(f"{BASE}/ativas", headers=cliente).json() == []
    assert _chamar(http, loja, cliente).status_code == 400
    assert _chamar(http, loja, cliente, cadeira_id=cadeira_id).status_code == 400
    assert _chamar(http, loja, cliente, barbeiro_id=fre[0]).status_code == 400
    db = SessionLocal()
    try:
        assert db.query(models.Chamado).count() == 0
    finally:
        db.close()


def test_cliente_nao_reserva_vaga_diaria_nem_de_cadeira_bloqueada(http):
    loja = _barbearia("dono@t.com", 2)
    diaria = _publicar(http, loja, 1)[0]
    _, cliente = _usuario("cliente", "cli@t.com", latitude=LAT, longitude=LON)
    assert http.post(f"{BASE}/{diaria}/aceitar-cliente", headers=cliente).status_code == 409

    bloqueada = next(c for c in _cadeiras(loja["id"]) if c[0] not in {v["cadeira_id"] for v in _resumo(http, loja)["vagas"]})
    body = {"cadeira_id": bloqueada[0], "raio_km": 5, "expira_em_minutos": 10}
    relampago = http.post(f"{BASE}/acionar", json=body, headers=loja["headers"]).json()["id"]
    assert http.post(f"{BASE}/{relampago}/aceitar-cliente", headers=cliente).status_code == 409


def test_freelancer_nao_aceita_chamado_em_cadeira_bloqueada(http):
    loja = _barbearia("dono@t.com", 1, status=models.StatusCadeira.DISPONIVEL)
    cadeira_id = _cadeiras(loja["id"])[0][0]
    fre_id, fre_headers = _freelancer("f1@t.com")
    _, cliente = _usuario("cliente", "cli@t.com", latitude=LAT, longitude=LON)
    criado = _chamar(http, loja, cliente, barbeiro_id=fre_id, cadeira_id=cadeira_id)
    assert criado.status_code == 200, criado.text

    assert http.put(f"/api/v1/cadeiras/{cadeira_id}/bloquear", headers=loja["headers"]).status_code == 200
    aceite = http.put(f"/api/v1/chamados/{criado.json()['id']}/aceitar", headers=fre_headers)
    assert aceite.status_code == 400, aceite.text
    assert "não está mais disponível" in aceite.json()["detail"]


@pytest.mark.parametrize("caminho", ["presenca", "acionar"])
def test_rotas_antigas_nao_contornam_o_bloqueio(http, caminho):
    loja = _barbearia("dono@t.com", 1)
    cadeira_id = _cadeiras(loja["id"])[0][0]
    fre_id, _ = _freelancer("f1@t.com")
    if caminho == "presenca":
        r = http.post("/api/v1/cadeiras/presenca", json={"cadeira_id": cadeira_id, "freelancer_id": fre_id}, headers=loja["headers"])
    else:
        r = http.post(f"/api/v1/cadeiras/{cadeira_id}/acionar", headers=loja["headers"])
    assert r.status_code == 400, r.text
    assert _cadeiras(loja["id"])[0][1] == models.StatusCadeira.BLOQUEADA


# Item 15
def test_desbloqueio_manual_restaura_o_funcionamento(http):
    loja = _barbearia("dono@t.com", 1)
    vaga = _publicar(http, loja, 1)[0]
    fre = _freelancer("f1@t.com")
    _selecionar(http, loja, vaga, fre)
    _, cliente = _usuario("cliente", "cli@t.com", latitude=LAT, longitude=LON)
    cadeira_id = _cadeiras(loja["id"])[0][0]

    assert _chamar(http, loja, cliente, barbeiro_id=fre[0]).status_code == 400

    r = http.put(f"/api/v1/cadeiras/{cadeira_id}/desbloquear", headers=loja["headers"])
    assert r.status_code == 200, r.text
    assert "assumiu a cadeira" in r.json()["message"]

    assert _cadeiras(loja["id"])[0] == (cadeira_id, models.StatusCadeira.OCUPADA, fre[0])
    db = SessionLocal()
    try:
        u = db.query(models.Usuario).filter(models.Usuario.id == fre[0]).first()
        assert u.presente_em_local and u.barbearia_atual_id == loja["id"]
    finally:
        db.close()
    resumo = _resumo(http, loja)
    assert resumo["vagas"][0]["status"] == regras_vagas.STATUS_OCUPADA
    assert resumo["vagas_disponiveis_para_anunciar"] == 0

    chamado = _chamar(http, loja, cliente, barbeiro_id=fre[0])
    assert chamado.status_code == 200, chamado.text
    db = SessionLocal()
    try:
        assert db.query(models.Chamado).filter(models.Chamado.id == chamado.json()["id"]).first().cadeira_id == cadeira_id
    finally:
        db.close()
    assert http.put(f"/api/v1/chamados/{chamado.json()['id']}/aceitar", headers=fre[1]).status_code == 200


def test_desbloqueio_sem_selecao_so_libera_a_cadeira(http):
    loja = _barbearia("dono@t.com", 1)
    _publicar(http, loja, 1)
    cadeira_id = _cadeiras(loja["id"])[0][0]
    assert http.put(f"/api/v1/cadeiras/{cadeira_id}/desbloquear", headers=loja["headers"]).status_code == 200
    assert _cadeiras(loja["id"])[0] == (cadeira_id, models.StatusCadeira.DISPONIVEL, None)


def test_desbloqueio_com_escolhido_indisponivel_nao_trava_a_cadeira(http):
    loja = _barbearia("dono@t.com", 1)
    vaga = _publicar(http, loja, 1)[0]
    fre = _freelancer("f1@t.com")
    _selecionar(http, loja, vaga, fre)
    db = SessionLocal()
    try:
        db.query(models.Usuario).filter(models.Usuario.id == fre[0]).update({"em_atendimento": True})
        db.commit()
    finally:
        db.close()
    cadeira_id = _cadeiras(loja["id"])[0][0]

    r = http.put(f"/api/v1/cadeiras/{cadeira_id}/desbloquear", headers=loja["headers"])
    assert r.status_code == 200
    assert "indisponível" in r.json()["message"]
    assert _cadeiras(loja["id"])[0] == (cadeira_id, models.StatusCadeira.DISPONIVEL, None)
    assert _resumo(http, loja)["vagas_anunciadas"] == 0


def test_selecao_em_cadeira_livre_mantem_o_comportamento_antigo(http):
    loja = _barbearia("dono@t.com", 1, status=models.StatusCadeira.DISPONIVEL)
    cadeira_id = _cadeiras(loja["id"])[0][0]
    corpo = {"cadeira_id": cadeira_id, "raio_km": 5, "expira_em_minutos": 10}
    vaga = http.post(f"{BASE}/acionar", json=corpo, headers=loja["headers"]).json()["id"]
    fre = _freelancer("f1@t.com")
    _selecionar(http, loja, vaga, fre)
    assert _cadeiras(loja["id"])[0] == (cadeira_id, models.StatusCadeira.OCUPADA, fre[0])


# Item 16
def test_chat_dos_chamados_segue_separado(http):
    loja = _barbearia("dono@t.com", 1, status=models.StatusCadeira.DISPONIVEL)
    cadeira_id = _cadeiras(loja["id"])[0][0]
    fre_id, fre_headers = _freelancer("f1@t.com")
    _, cliente = _usuario("cliente", "cli@t.com", latitude=LAT, longitude=LON)
    chamado = _chamar(http, loja, cliente, barbeiro_id=fre_id, cadeira_id=cadeira_id).json()

    for headers, texto in ((cliente, "cliente"), (fre_headers, "freelancer"), (loja["headers"], "dono")):
        r = http.post("/api/v1/chat/mensagem", json={"chamado_id": chamado["id"], "mensagem": texto}, headers=headers)
        assert r.status_code == 200, r.text
    r = http.get(f"/api/v1/chat/{chamado['id']}/mensagens", headers=cliente)
    assert [m["mensagem"] for m in r.json()] == ["cliente", "freelancer", "dono"]

    db = SessionLocal()
    try:
        assert db.query(models.MensagemVaga).count() == 0
    finally:
        db.close()


# ---------- Cadeira paga entra no limite, com ciclo próprio por cadeira ----------

def _contratar_mais_uma(loja, primeira_vencida):
    """Assinatura de 1 cadeira (vencida ou em dia) + compra confirmada de mais 1, como no Pix."""
    db = SessionLocal()
    try:
        assinatura = db.query(models.AssinaturaBarbearia).filter_by(barbearia_id=loja["id"]).first()
        venc = datetime.now() + (timedelta(days=-22) if primeira_vencida else timedelta(days=20))
        assinatura.proximo_vencimento = venc
        db.add(models.CadeiraContratada(
            assinatura_id=assinatura.id, barbearia_id=loja["id"], numero_referencia=1,
            origem_contratacao="adicional", valor_mensal=47.9,
            data_contratacao=venc - timedelta(days=30), data_proxima_cobranca=venc, ativa=True,
        ))
        db.flush()
        aplicar_contratacao_cadeiras(db, db.get(models.Barbearia, loja["id"]), 2, "pix")
        db.commit()
    finally:
        db.close()


def test_duas_cadeiras_pagas_anunciam_duas_vagas_simultaneas(http):
    loja = _barbearia("duas@t.com", 1)
    _contratar_mais_uma(loja, primeira_vencida=False)

    assert len(_cadeiras(loja["id"])) == 2
    resumo = _resumo(http, loja)
    assert (resumo["cadeiras_pagas"], resumo["vagas_disponiveis_para_anunciar"], resumo["cadeiras_vencidas"]) == (2, 2, 0)

    r = _anunciar(http, loja, 2)
    assert r.status_code == 201, r.text
    resumo = _resumo(http, loja)
    assert resumo["vagas_anunciadas"] == 2
    assert len({v["cadeira_id"] for v in resumo["vagas"]}) == 2
    assert _anunciar(http, loja, 1).status_code == 409
    assert len(_cadeiras(loja["id"])) == 2


def test_cadeira_vencida_nao_invalida_a_recem_paga(http):
    loja = _barbearia("mista@t.com", 1)
    _contratar_mais_uma(loja, primeira_vencida=True)

    resumo = _resumo(http, loja)
    assert (resumo["cadeiras_pagas"], resumo["vagas_disponiveis_para_anunciar"], resumo["cadeiras_vencidas"]) == (1, 1, 1)
    assert _anunciar(http, loja, 2).status_code == 409
    assert _anunciar(http, loja, 1).status_code == 201


def test_pagar_a_mensalidade_vencida_libera_as_duas_vagas(http):
    loja = _barbearia("quita@t.com", 1)
    _contratar_mais_uma(loja, primeira_vencida=True)
    db = SessionLocal()
    try:
        barbearia = db.get(models.Barbearia, loja["id"])
        assinatura = db.query(models.AssinaturaBarbearia).filter_by(barbearia_id=loja["id"]).first()
        aplicar_pagamento_mensalidade(db, barbearia, assinatura, "pix")
        db.commit()
    finally:
        db.close()

    resumo = _resumo(http, loja)
    assert (resumo["cadeiras_pagas"], resumo["cadeiras_vencidas"]) == (2, 0)
    assert _anunciar(http, loja, 2).status_code == 201


def test_perfil_de_teste_conta_a_cadeira_gratis_sem_somar_a_vencida(http, monkeypatch):
    monkeypatch.setenv("TEST_BARBERSHOP_EMAILS", "perfilteste@t.com")
    loja = _barbearia("perfilteste@t.com", 1)
    _contratar_mais_uma(loja, primeira_vencida=True)
    assert _resumo(http, loja)["cadeiras_pagas"] == 1


@pytest.mark.parametrize("status_assinatura", ["suspensa", "cancelada", "inadimplente"])
def test_assinatura_sem_validade_nao_conta_cadeira_em_dia(http, status_assinatura):
    loja = _barbearia(f"{status_assinatura}@t.com", 1)
    _contratar_mais_uma(loja, primeira_vencida=True)
    db = SessionLocal()
    try:
        db.query(models.AssinaturaBarbearia).filter_by(barbearia_id=loja["id"]).update({"status": status_assinatura})
        db.commit()
    finally:
        db.close()
    assert _resumo(http, loja)["cadeiras_pagas"] == 0


def test_status_vencida_ainda_conta_a_cadeira_em_dia(http):
    loja = _barbearia("statusvencida@t.com", 1)
    _contratar_mais_uma(loja, primeira_vencida=True)
    db = SessionLocal()
    try:
        db.query(models.AssinaturaBarbearia).filter_by(barbearia_id=loja["id"]).update({"status": "vencida"})
        db.commit()
    finally:
        db.close()
    assert _resumo(http, loja)["cadeiras_pagas"] == 1


# ---------- Mensalidade cobra só o que venceu ----------

def _pagar_mensalidade(loja):
    db = SessionLocal()
    try:
        barbearia = db.get(models.Barbearia, loja["id"])
        assinatura = db.query(models.AssinaturaBarbearia).filter_by(barbearia_id=loja["id"]).first()
        aplicar_pagamento_mensalidade(db, barbearia, assinatura, "pix")
        db.commit()
    finally:
        db.close()


def _devida_e_datas(loja):
    db = SessionLocal()
    try:
        assinatura = db.query(models.AssinaturaBarbearia).filter_by(barbearia_id=loja["id"]).first()
        contratadas = db.query(models.CadeiraContratada).filter_by(assinatura_id=assinatura.id).order_by(models.CadeiraContratada.numero_referencia)
        return mensalidade_devida(db, assinatura), [c.data_proxima_cobranca for c in contratadas], assinatura.valor_mensalidade
    finally:
        db.close()


def test_mensalidade_cobra_so_a_cadeira_vencida_e_a_fatura_registra_o_mesmo(http):
    loja = _barbearia("cobra@t.com", 1)
    _contratar_mais_uma(loja, primeira_vencida=True)

    devida, datas, mensal = _devida_e_datas(loja)
    assert devida == (47.9, 1)
    assert mensal == round(47.9 + 37.9, 2)

    _pagar_mensalidade(loja)

    _, novas_datas, mensal_depois = _devida_e_datas(loja)
    assert novas_datas[0] > datas[0] and novas_datas[1] == datas[1]
    assert mensal_depois == mensal
    db = SessionLocal()
    try:
        fatura = db.query(models.FaturaAssinatura).order_by(models.FaturaAssinatura.id.desc()).first()
        assert (fatura.valor_fatura, fatura.quantidade_cadeiras) == (47.9, 1)
    finally:
        db.close()


def test_mensalidade_sem_nada_vencido_antecipa_o_total(http):
    loja = _barbearia("antecipa@t.com", 1)
    _contratar_mais_uma(loja, primeira_vencida=False)
    assert _devida_e_datas(loja)[0] == (round(47.9 + 37.9, 2), 2)


def test_mensalidade_de_assinatura_sem_cadeiras_contratadas_cobra_o_total(http):
    loja = _barbearia("legado@t.com", 2, vencida=True)
    assert _devida_e_datas(loja)[0] == (50.0, 2)


# ---------- Dono escolhe a cadeira da vaga ----------

def test_resumo_lista_cadeiras_livres_com_situacao_de_bloqueio(http):
    loja = _barbearia("lista@t.com", 2)
    ids = [c[0] for c in _cadeiras(loja["id"])]
    db = SessionLocal()
    try:
        db.query(models.Cadeira).filter_by(id=ids[1]).update({"status": models.StatusCadeira.DISPONIVEL})
        db.commit()
    finally:
        db.close()

    assert _resumo(http, loja)["cadeiras_livres"] == [
        {"id": ids[0], "numero": 1, "bloqueada": True},
        {"id": ids[1], "numero": 2, "bloqueada": False},
    ]


def test_dono_anuncia_na_cadeira_escolhida_mesmo_com_outra_bloqueada(http):
    loja = _barbearia("escolhe@t.com", 2)
    ids = [c[0] for c in _cadeiras(loja["id"])]
    db = SessionLocal()
    try:
        db.query(models.Cadeira).filter_by(id=ids[1]).update({"status": models.StatusCadeira.DISPONIVEL})
        db.commit()
    finally:
        db.close()

    r = http.post(f"{BASE}/anunciar", json={"cadeira_ids": [ids[1]]}, headers=loja["headers"])
    assert r.status_code == 201, r.text
    assert [v["cadeira_id"] for v in r.json()["vagas"]] == [ids[1]]
    assert [c["id"] for c in r.json()["cadeiras_livres"]] == [ids[0]]


def test_escolher_as_duas_cadeiras_publica_duas_vagas(http):
    loja = _barbearia("ambas@t.com", 2)
    ids = [c[0] for c in _cadeiras(loja["id"])]
    r = http.post(f"{BASE}/anunciar", json={"cadeira_ids": ids}, headers=loja["headers"])
    assert r.status_code == 201, r.text
    assert sorted(v["cadeira_id"] for v in r.json()["vagas"]) == sorted(ids)
    assert r.json()["cadeiras_livres"] == []


def test_cadeira_repetida_vira_uma_vaga_so(http):
    loja = _barbearia("repetida@t.com", 2)
    ids = [c[0] for c in _cadeiras(loja["id"])]
    r = http.post(f"{BASE}/anunciar", json={"cadeira_ids": [ids[0], ids[0]]}, headers=loja["headers"])
    assert r.status_code == 201, r.text
    assert len(r.json()["publicadas"]) == 1


def test_escolha_invalida_nao_publica_nada(http):
    loja = _barbearia("invalida@t.com", 2)
    outra = _barbearia("alheia@t.com", 1)
    ids = [c[0] for c in _cadeiras(loja["id"])]
    alheia = _cadeiras(outra["id"])[0][0]

    assert http.post(f"{BASE}/anunciar", json={"cadeira_ids": [ids[0], alheia]}, headers=loja["headers"]).status_code == 404
    assert _resumo(http, loja)["vagas_anunciadas"] == 0

    assert http.post(f"{BASE}/anunciar", json={"cadeira_ids": [ids[0]]}, headers=loja["headers"]).status_code == 201
    assert http.post(f"{BASE}/anunciar", json={"cadeira_ids": [ids[0], ids[1]]}, headers=loja["headers"]).status_code == 409
    assert _resumo(http, loja)["vagas_anunciadas"] == 1


def test_escolha_acima_das_pagas_e_recusada(http):
    loja = _barbearia("acima@t.com", 1, linhas=2)
    ids = [c[0] for c in _cadeiras(loja["id"])]
    assert http.post(f"{BASE}/anunciar", json={"cadeira_ids": ids}, headers=loja["headers"]).status_code == 409
    assert _resumo(http, loja)["vagas_anunciadas"] == 0


def test_anunciar_sem_cadeira_nem_quantidade_e_recusado(http):
    loja = _barbearia("vazio@t.com", 1)
    assert http.post(f"{BASE}/anunciar", json={}, headers=loja["headers"]).status_code == 400
    assert http.post(f"{BASE}/anunciar", json={"cadeira_ids": []}, headers=loja["headers"]).status_code == 422
