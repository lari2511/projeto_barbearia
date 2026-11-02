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
