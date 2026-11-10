"""
Cadeado do proprietário sobre o freelancer PRESENTE: presente não é o mesmo que
disponível para clientes do app. O cadeado nasce fechado; o dono abre/fecha.

SQLite temporário, sem chamadas externas.

    .venv/Scripts/python -m pytest test_cadeado_clientes_app.py -v
"""

import os
import tempfile
from datetime import datetime, timedelta

_DB = os.path.join(tempfile.mkdtemp(prefix="bm_cadeado_"), "teste.db")
os.environ["DATABASE_URL"] = f"sqlite:///{_DB}"

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app import models, routes_interesse, routes_on_demand  # noqa: E402
from app.database import Base, SessionLocal, engine, init_db  # noqa: E402
from app.main import app  # noqa: E402
from app.routes import create_access_token  # noqa: E402

V1 = "/api/v1"
LAT, LON = -23.55, -46.63


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
        ids = []
        for numero in range(1, cadeiras + 1):
            c = models.Cadeira(barbearia_id=b.id, numero=numero, status=models.StatusCadeira.DISPONIVEL)
            db.add(c)
            db.flush()
            ids.append(c.id)
        db.add(models.AssinaturaBarbearia(
            barbearia_id=b.id, quantidade_cadeiras=cadeiras, valor_mensalidade=50.0, dia_vencimento=10,
            proximo_vencimento=datetime.now() + timedelta(days=30), status="ativa",
        ))
        servico = models.Servico(barbearia_id=b.id, nome="Corte", categoria="corte", valor=50.0, duracao_minutos=30, ativo=True)
        db.add(servico)
        db.commit()
        return {"id": b.id, "dono_id": dono_id, "headers": headers, "servico_id": servico.id, "cadeiras": ids}
    finally:
        db.close()


def _freelancer_presente(loja, email="f@t.com"):
    """Freelancer presente e ocupando a cadeira 1 (como fica após o dono registrar a presença)."""
    fid, headers = _usuario("barbeiro", email, latitude=LAT, longitude=LON, telefone=None)
    db = SessionLocal()
    try:
        db.add(models.RadarFreelancer(freelancer_id=fid, is_online=False, em_atendimento=False, latitude=LAT, longitude=LON))
        f = db.get(models.Usuario, fid)
        f.presente_em_local = True
        f.barbearia_atual_id = loja["id"]
        f.online_regiao = False
        f.disponivel = True
        cadeira = db.get(models.Cadeira, loja["cadeiras"][0])
        cadeira.status = models.StatusCadeira.OCUPADA
        cadeira.freelancer_id = fid
        cadeira.ocupada_em = datetime.utcnow()
        db.commit()
    finally:
        db.close()
    return fid, headers


def _cadeado(http, loja, fid, liberado):
    return http.put(f"{V1}/cadeiras/clientes-app/{fid}", json={"liberado": liberado}, headers=loja["headers"])


def _criar_chamado(http, loja, fid, cliente):
    return http.post(f"{V1}/chamados", json={
        "barbearia_id": loja["id"], "servico_id": loja["servico_id"],
        "barbeiro_id": fid, "barbeiro_selecionado_id": fid,
        "data_hora_inicio": datetime.utcnow().isoformat(),
        "cliente_latitude": LAT, "cliente_longitude": LON,
    }, headers=cliente)


def _cadeira_do_dono(http, loja):
    r = http.get(f"{V1}/cadeiras/barbearia/{loja['id']}", headers=loja["headers"])
    assert r.status_code == 200
    return next(c for c in r.json() if c["id"] == loja["cadeiras"][0])


def _contar_chamados():
    db = SessionLocal()
    try:
        return db.query(models.Chamado).count()
    finally:
        db.close()


def test_cadeado_nasce_fechado_e_cadeira_segue_ocupada(http):
    loja = _barbearia()
    fid, _ = _freelancer_presente(loja)
    cadeira = _cadeira_do_dono(http, loja)
    assert cadeira["status"] == "ocupada"
    assert cadeira["freelancer_id"] == fid
    assert cadeira["clientes_app_liberado"] is False


def test_cadeira_livre_nao_tem_cadeado_de_freelancer(http):
    loja = _barbearia()
    r = http.get(f"{V1}/cadeiras/barbearia/{loja['id']}", headers=loja["headers"])
    assert all(c["clientes_app_liberado"] is None for c in r.json())


def test_fechado_cliente_nao_cria_chamado(http):
    loja = _barbearia()
    fid, _ = _freelancer_presente(loja)
    _, cliente = _usuario("cliente", "c@t.com", latitude=LAT, longitude=LON)
    antes = _contar_chamados()
    r = _criar_chamado(http, loja, fid, cliente)
    assert r.status_code == 400
    assert "presencialmente" in r.json()["detail"]
    assert _contar_chamados() == antes


def test_fechado_some_das_listas_do_cliente(http):
    loja = _barbearia()
    fid, _ = _freelancer_presente(loja)
    priorizados = http.get(f"{V1}/barbearia/{loja['id']}/barbeiros-priorizados").json()["barbeiros"]
    assert fid not in [b["id"] for b in priorizados]
    proximos = http.get(f"{V1}/barbeiros/proximos", params={"latitude": LAT, "longitude": LON, "raio_km": 10}).json()
    assert fid not in [b["id"] for b in proximos]
    todos = {b["id"]: b for b in http.get(f"{V1}/barbeiros/todos").json()}
    assert todos[fid]["clientes_app_liberado"] is False
    assert todos[fid]["pode_receber_chamado_agora"] is False
    # o painel do dono continua vendo a presença real
    assert todos[fid]["presente_em_local"] is True


def test_liberar_permite_cliente_ver_e_chamar(http):
    loja = _barbearia()
    fid, _ = _freelancer_presente(loja)
    r = _cadeado(http, loja, fid, True)
    assert r.status_code == 200, r.text
    assert _cadeira_do_dono(http, loja)["clientes_app_liberado"] is True

    priorizados = http.get(f"{V1}/barbearia/{loja['id']}/barbeiros-priorizados").json()["barbeiros"]
    casa = next(b for b in priorizados if b["id"] == fid)
    assert casa["profissional_da_casa"] is True
    todos = {b["id"]: b for b in http.get(f"{V1}/barbeiros/todos").json()}
    assert todos[fid]["pode_receber_chamado_agora"] is True

    _, cliente = _usuario("cliente", "c@t.com", latitude=LAT, longitude=LON)
    r = _criar_chamado(http, loja, fid, cliente)
    assert r.status_code == 200, r.text


def test_bloquear_de_novo_mantem_presenca_e_atendimento_em_curso(http):
    loja = _barbearia()
    fid, _ = _freelancer_presente(loja)
    _cadeado(http, loja, fid, True)
    _, cliente = _usuario("cliente", "c@t.com", latitude=LAT, longitude=LON)
    chamado_id = _criar_chamado(http, loja, fid, cliente).json()["id"]

    assert _cadeado(http, loja, fid, False).status_code == 200

    db = SessionLocal()
    try:
        f = db.get(models.Usuario, fid)
        assert f.presente_em_local is True and f.barbearia_atual_id == loja["id"]
        assert db.get(models.Chamado, chamado_id).status != "cancelado"
        assert db.get(models.Cadeira, loja["cadeiras"][0]).status == models.StatusCadeira.OCUPADA
    finally:
        db.close()

    _, outro = _usuario("cliente", "c2@t.com", latitude=LAT, longitude=LON)
    assert _criar_chamado(http, loja, fid, outro).status_code == 400


def test_liberacao_sobrevive_a_cadeira_ser_liberada_pelo_atendimento(http):
    """Os chamados liberam/reocupam a cadeira a cada atendimento; o cadeado não pode se perder."""
    loja = _barbearia()
    fid, _ = _freelancer_presente(loja)
    _cadeado(http, loja, fid, True)
    db = SessionLocal()
    try:
        c = db.get(models.Cadeira, loja["cadeiras"][0])
        c.status = models.StatusCadeira.DISPONIVEL
        c.freelancer_id = None
        db.commit()
        c.status = models.StatusCadeira.OCUPADA
        c.freelancer_id = fid
        db.commit()
    finally:
        db.close()
    assert _cadeira_do_dono(http, loja)["clientes_app_liberado"] is True


def test_sair_da_barbearia_fecha_o_cadeado(http):
    loja = _barbearia()
    fid, headers = _freelancer_presente(loja)
    _cadeado(http, loja, fid, True)
    r = http.post(f"{V1}/freelancer/{fid}/alterar-status", json={"status": "offline"}, headers=headers)
    assert r.status_code == 200, r.text
    db = SessionLocal()
    try:
        f = db.get(models.Usuario, fid)
        assert f.clientes_app_liberado_barbearia_id is None
        # voltando a ficar presente, nasce fechado de novo
        f.presente_em_local = True
        f.barbearia_atual_id = loja["id"]
        db.commit()
        assert models.freelancer_bloqueado_para_clientes_app(f) is True
    finally:
        db.close()


def test_fora_da_presenca_nada_muda(http):
    """Freelancer ONLINE na região (não presente) não depende do cadeado."""
    loja = _barbearia()
    fid, _ = _usuario("barbeiro", "on@t.com", latitude=LAT, longitude=LON, online_regiao=True, disponivel=True)
    db = SessionLocal()
    try:
        assert models.freelancer_bloqueado_para_clientes_app(db.get(models.Usuario, fid)) is False
    finally:
        db.close()
    priorizados = http.get(f"{V1}/barbearia/{loja['id']}/barbeiros-priorizados").json()["barbeiros"]
    assert fid in [b["id"] for b in priorizados]


def test_so_o_dono_da_barbearia_atual_controla(http):
    loja = _barbearia()
    outra = _barbearia("outro@t.com")
    fid, headers = _freelancer_presente(loja)
    assert _cadeado(http, outra, fid, True).status_code == 400
    assert http.put(f"{V1}/cadeiras/clientes-app/{fid}", json={"liberado": True}, headers=headers).status_code == 403
    assert _cadeira_do_dono(http, loja)["clientes_app_liberado"] is False


def test_fechado_nao_aceita_chamado_aberto(http):
    loja = _barbearia()
    fid, headers = _freelancer_presente(loja)
    cid, _ = _usuario("cliente", "c@t.com")
    db = SessionLocal()
    try:
        c = models.Chamado(
            cliente_id=cid, barbearia_id=loja["id"], servico_id=loja["servico_id"], barbeiro_id=None,
            status="pendente", data_hora_inicio=datetime.utcnow(), data_hora_fim=datetime.utcnow() + timedelta(minutes=30),
        )
        db.add(c)
        db.commit()
        chamado_id = c.id
    finally:
        db.close()
    abertos = http.get(f"{V1}/chamados/abertos", headers=headers).json()
    assert chamado_id not in [c["id"] for c in abertos]
    assert http.put(f"{V1}/chamados/{chamado_id}/aceitar", headers=headers).status_code == 400


# ---- Home do cliente: "Freelancer X presente na barbearia" ----

def _home(http, cliente):
    r = http.get(f"{V1}/barbearias/proximas?raio_km=5", headers=cliente)
    assert r.status_code == 200
    return r.json()["barbearias"][0]


def test_home_cliente_mostra_freelancer_so_com_cadeado_aberto(http):
    loja = _barbearia(cadeiras=1)
    _, cliente = _usuario("cliente", "c@t.com", latitude=LAT, longitude=LON)

    # Sem ninguém presente: nenhum profissional anunciado.
    assert _home(http, cliente)["freelancers_presentes_liberados"] == []

    # Presente mas cadeado fechado: segue "Sem cadeira no momento".
    fid, _ = _freelancer_presente(loja, email="aislan silva@t.com")
    item = _home(http, cliente)
    assert item["freelancers_presentes_liberados"] == []
    assert item["cadeira_disponivel"] is False

    # Dono abre o cadeado: aparece o primeiro nome.
    assert _cadeado(http, loja, fid, True).status_code == 200
    assert _home(http, cliente)["freelancers_presentes_liberados"] == ["aislan"]

    # Dono fecha de novo: some.
    assert _cadeado(http, loja, fid, False).status_code == 200
    assert _home(http, cliente)["freelancers_presentes_liberados"] == []


def test_home_cliente_esconde_freelancer_que_saiu(http):
    loja = _barbearia(cadeiras=1)
    _, cliente = _usuario("cliente", "c@t.com", latitude=LAT, longitude=LON)
    fid, _ = _freelancer_presente(loja)
    assert _cadeado(http, loja, fid, True).status_code == 200
    db = SessionLocal()
    try:
        db.get(models.Usuario, fid).presente_em_local = False
        db.commit()
    finally:
        db.close()
    assert _home(http, cliente)["freelancers_presentes_liberados"] == []


def test_home_cliente_esconde_freelancer_com_taxa_pendente(http, monkeypatch):
    from app import pagamento_diario
    loja = _barbearia(cadeiras=1)
    _, cliente = _usuario("cliente", "c@t.com", latitude=LAT, longitude=LON)
    fid, _ = _freelancer_presente(loja)
    assert _cadeado(http, loja, fid, True).status_code == 200
    monkeypatch.setattr(pagamento_diario, "freelancers_com_taxa_vencida", lambda db, agora=None: {fid})
    assert _home(http, cliente)["freelancers_presentes_liberados"] == []
