"""
Telefone de freelancer e de proprietário: só o próprio usuário e o ADM recebem.

Além dos casos diretos, percorre TODAS as rotas GET da aplicação com cada perfil procurando
os números, para pegar vazamento em qualquer resposta (inclusive objeto do banco devolvido
inteiro). SQLite temporário, sem chamadas externas.

    .venv/Scripts/python -m pytest test_privacidade_telefones.py -v
"""

import os
import re
import tempfile
from datetime import datetime, timedelta

_DB = os.path.join(tempfile.mkdtemp(prefix="bm_tel_"), "teste.db")
os.environ["DATABASE_URL"] = f"sqlite:///{_DB}"

import pytest  # noqa: E402
from fastapi.routing import APIRoute  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app import models, routes_on_demand  # noqa: E402
from app.database import Base, SessionLocal, engine, init_db  # noqa: E402
from app.main import app  # noqa: E402
from app.routes import create_access_token  # noqa: E402

V1 = "/api/v1"
LAT, LON = -23.55, -46.63
FONE_FREE = "11911110001"
FONE_DONO = "11922220002"
FONE_LOJA = "11933330003"
FONE_OUTRO = "11944440004"


@pytest.fixture(autouse=True)
def sem_rede(monkeypatch):
    monkeypatch.setattr(routes_on_demand, "_calcular_eta_osrm_minutos", lambda *a, **k: 3)


@pytest.fixture()
def cena():
    Base.metadata.drop_all(bind=engine)
    init_db()
    db = SessionLocal()
    try:
        def usuario(tipo, email, telefone, **extras):
            u = models.Usuario(
                nome=email.split("@")[0], email=email, senha_hash="x", tipo=tipo, perfil_aprovado=True,
                telefone=telefone, latitude=LAT, longitude=LON, **extras,
            )
            db.add(u)
            db.flush()
            return u

        adm = usuario("admin", "adm@t.com", "11955550005")
        cliente = usuario("cliente", "cli@t.com", "11966660006")
        dono = usuario("barbearia", "dono@t.com", FONE_DONO)
        loja = models.Barbearia(usuario_id=dono.id, nome="Loja", endereco="Rua A", latitude=LAT, longitude=LON, telefone=FONE_LOJA)
        db.add(loja)
        db.flush()
        cadeira = models.Cadeira(barbearia_id=loja.id, numero=1, status=models.StatusCadeira.DISPONIVEL)
        db.add(cadeira)
        servico = models.Servico(barbearia_id=loja.id, nome="Corte", categoria="corte", valor=50.0, duracao_minutos=30, ativo=True)
        db.add(servico)
        db.flush()
        free = usuario(
            "barbeiro", "free@t.com", FONE_FREE, online_regiao=True, disponivel=True, documento_verificado=True,
            presente_em_local=True, barbearia_atual_id=loja.id,
        )
        outro = usuario("barbeiro", "outro@t.com", FONE_OUTRO, online_regiao=True, disponivel=True, documento_verificado=True)
        db.add(models.RadarFreelancer(freelancer_id=free.id, is_online=True, em_atendimento=False, latitude=LAT, longitude=LON))
        chamado = models.Chamado(
            cliente_id=cliente.id, barbeiro_id=free.id, barbearia_id=loja.id, servico_id=servico.id,
            cadeira_id=cadeira.id, status="confirmado", valor_original=50.0, valor_final=50.0,
            data_hora_inicio=datetime.utcnow(), data_hora_fim=datetime.utcnow() + timedelta(minutes=30),
        )
        db.add(chamado)
        db.flush()
        vaga = models.CadeiraAcionada(
            barbearia_id=loja.id, cadeira_id=cadeira.id, status="disponivel", raio_km=5.0, tipo_servico="vaga_diaria",
            expira_em=datetime.utcnow() + timedelta(hours=8),
        )
        db.add(vaga)
        db.flush()
        db.add(models.CadeiraAcionadaCandidatura(vaga_id=vaga.id, barbeiro_id=free.id))
        db.commit()

        def headers(u):
            return {"Authorization": f"Bearer {create_access_token({'sub': str(u.id), 'tipo': u.tipo})}"}

        return {
            "http": TestClient(app, raise_server_exceptions=False),
            "ids": {"adm": adm.id, "cliente": cliente.id, "dono": dono.id, "free": free.id, "outro": outro.id,
                    "loja": loja.id, "cadeira": cadeira.id, "chamado": chamado.id, "vaga": vaga.id, "servico": servico.id},
            "h": {"adm": headers(adm), "cliente": headers(cliente), "dono": headers(dono), "free": headers(free), "anonimo": {}},
        }
    finally:
        db.close()


def _valor_do_parametro(nome_parametro, rota, ids, alvo_usuario):
    nome = nome_parametro.lower()
    if "barbearia" in nome:
        return ids["loja"]
    if "cadeira" in nome:
        return ids["cadeira"]
    if "vaga" in nome:
        return ids["vaga"]
    if "chamado" in nome or "agendamento" in nome:
        return ids["chamado"]
    if "servico" in nome:
        return ids["servico"]
    if "barbeiro" in nome or "freelancer" in nome:
        return ids["free"]
    if "usuario" in nome or "user" in nome or "dono" in nome:
        return alvo_usuario
    if nome == "id":
        if "barbearia" in rota and "chamados" not in rota:
            return ids["loja"]
        if "usuario" in rota:
            return alvo_usuario
        return ids["chamado"]
    return alvo_usuario


def _rotas_get():
    for rota in app.routes:
        if isinstance(rota, APIRoute) and "GET" in rota.methods:
            yield rota.path


QUERY = {"latitude": LAT, "longitude": LON, "lat": LAT, "lon": LON, "lng": LON, "raio_km": 50, "incluir_indisponiveis": True,
         "q": "a", "termo": "a", "tipo": "barbeiro", "limite": 50}


def _varrer(cena, perfil, proibidos, alvos):
    """Chama cada GET com o token do perfil e devolve [(rota, status, numero)] de cada vazamento."""
    vazamentos, respondidas = [], 0
    for caminho in _rotas_get():
        for alvo in alvos:
            nomes = re.findall(r"{([^}:]+)(?::[^}]*)?}", caminho)
            url = caminho
            for nome in nomes:
                url = re.sub(r"{" + nome + r"(?::[^}]*)?}", str(_valor_do_parametro(nome, caminho, cena["ids"], alvo)), url)
            r = cena["http"].get(url, params=QUERY, headers=cena["h"][perfil])
            if r.status_code == 200:
                respondidas += 1
            for numero in proibidos:
                if numero in r.text:
                    vazamentos.append((caminho, r.status_code, numero))
            if not nomes:
                break
    return vazamentos, respondidas


@pytest.mark.parametrize("perfil, proibidos", [
    ("cliente", [FONE_FREE, FONE_OUTRO, FONE_DONO, FONE_LOJA]),
    ("free", [FONE_OUTRO, FONE_DONO, FONE_LOJA]),
    ("dono", [FONE_FREE, FONE_OUTRO]),
    ("anonimo", [FONE_FREE, FONE_OUTRO, FONE_DONO, FONE_LOJA]),
])
def test_nenhuma_rota_get_entrega_numero_a_quem_nao_pode(cena, perfil, proibidos):
    ids = cena["ids"]
    vazamentos, respondidas = _varrer(cena, perfil, proibidos, [ids["free"], ids["outro"], ids["dono"]])
    assert vazamentos == []
    # Garante que a varredura realmente exercitou rotas, e não só recebeu erros.
    assert respondidas > (15 if perfil == "anonimo" else 40), respondidas


def test_o_rastreador_detectaria_um_vazamento(cena):
    """Controle: o ADM pode ver os números; se a varredura não os achasse aqui, ela não provaria nada."""
    ids = cena["ids"]
    vazamentos, _ = _varrer(cena, "adm", [FONE_FREE, FONE_DONO], [ids["free"], ids["dono"]])
    achados = {numero for _, _, numero in vazamentos}
    assert achados == {FONE_FREE, FONE_DONO}


def _perfil(cena, usuario, perfil):
    return cena["http"].get(f"{V1}/usuario/{cena['ids'][usuario]}", headers=cena["h"][perfil]).json()


def test_cliente_nao_recebe_telefone_de_freelancer_nem_de_proprietario(cena):
    assert _perfil(cena, "free", "cliente")["telefone"] is None
    assert _perfil(cena, "dono", "cliente")["telefone"] is None


def test_freelancer_nao_recebe_telefone_do_proprietario(cena):
    assert _perfil(cena, "dono", "free")["telefone"] is None


def test_proprietario_nao_recebe_telefone_do_freelancer(cena):
    assert _perfil(cena, "free", "dono")["telefone"] is None


def test_cada_um_ve_o_proprio_e_o_banco_segue_intacto(cena):
    assert _perfil(cena, "free", "free")["telefone"] == FONE_FREE
    assert _perfil(cena, "dono", "dono")["telefone"] == FONE_DONO
    db = SessionLocal()
    try:
        assert db.get(models.Usuario, cena["ids"]["free"]).telefone == FONE_FREE
        assert db.get(models.Usuario, cena["ids"]["dono"]).telefone == FONE_DONO
        assert db.get(models.Barbearia, cena["ids"]["loja"]).telefone == FONE_LOJA
    finally:
        db.close()


def test_adm_continua_vendo_os_contatos(cena):
    http, ids, adm = cena["http"], cena["ids"], cena["h"]["adm"]
    assert http.get(f"/admin/api/usuario/{ids['free']}", headers=adm).json()["telefone"] == FONE_FREE
    assert http.get(f"/admin/api/usuario/{ids['dono']}", headers=adm).json()["telefone"] == FONE_DONO
    assert http.get(f"{V1}/usuario/{ids['free']}", headers=adm).json()["telefone"] == FONE_FREE
    assert http.get(f"{V1}/usuario/{ids['dono']}", headers=adm).json()["telefone"] == FONE_DONO


def test_proprietario_nao_usa_rotas_do_painel_adm_para_pegar_numeros(cena):
    http, ids, dono = cena["http"], cena["ids"], cena["h"]["dono"]
    r = http.get(f"/admin/api/usuario/{ids['free']}", headers=dono)
    assert r.status_code == 200 and FONE_FREE not in r.text
    assert r.json()["nome"] == "free" and r.json()["telefone"] is None


def test_chat_do_chamado_continua_funcionando(cena):
    http, ids = cena["http"], cena["ids"]
    chamado = ids["chamado"]
    r = http.post(f"{V1}/chat/mensagem", json={"chamado_id": chamado, "mensagem": "Estou a caminho"}, headers=cena["h"]["cliente"])
    assert r.status_code == 200, r.text
    r = http.post(f"{V1}/chat/mensagem", json={"chamado_id": chamado, "mensagem": "Combinado"}, headers=cena["h"]["free"])
    assert r.status_code == 200, r.text
    r = http.get(f"{V1}/chat/{chamado}/mensagens", headers=cena["h"]["free"])
    assert r.status_code == 200 and "Estou a caminho" in r.text and "Combinado" in r.text
    assert FONE_FREE not in http.get(f"{V1}/chat/{chamado}/mensagens", headers=cena["h"]["cliente"]).text


def test_chat_entre_proprietario_e_freelancer_continua_funcionando(cena):
    http, ids = cena["http"], cena["ids"]
    db = SessionLocal()
    try:
        vaga = db.get(models.CadeiraAcionada, ids["vaga"])
        vaga.status, vaga.barbeiro_id = "ocupada_por_barbeiro", ids["free"]
        db.commit()
    finally:
        db.close()
    base = f"/api/v1/vagas/{ids['vaga']}/chat"
    assert http.post(base, json={"mensagem": "Chego às 9h"}, headers=cena["h"]["free"]).status_code == 201
    assert http.post(base, json={"mensagem": "Pode vir"}, headers=cena["h"]["dono"]).status_code == 201
    r = http.get(base, headers=cena["h"]["dono"])
    assert r.status_code == 200 and "Chego às 9h" in r.text and "Pode vir" in r.text
    assert FONE_FREE not in r.text
    assert FONE_DONO not in http.get(base, headers=cena["h"]["free"]).text
