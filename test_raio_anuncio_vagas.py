"""
Alcance do anúncio de vaga de diária: 8 km da barbearia, freelancers ONLINE e OFFLINE.

SQLite temporário, sem chamadas externas.

    .venv/Scripts/python -m pytest test_raio_anuncio_vagas.py -v
"""

import math
import os
import tempfile
from datetime import datetime, timedelta

_DB = os.path.join(tempfile.mkdtemp(prefix="bm_raio_vagas_"), "teste.db")
os.environ["DATABASE_URL"] = f"sqlite:///{_DB}"

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app import models, routes_on_demand, vagas as regras_vagas  # noqa: E402
from app.database import Base, SessionLocal, engine, init_db  # noqa: E402
from app.main import app  # noqa: E402
from app.routes import create_access_token  # noqa: E402

BASE = "/api/v1/on-demand/cadeiras-acionadas"
LAT, LON = -23.5494, -46.4951
KM_POR_GRAU = 6371.0 * math.pi / 180.0


@pytest.fixture(autouse=True)
def sem_rota_externa(monkeypatch):
    # ETA pela distancia (40 km/h), sem OSRM: 4 km da 6 min, 8 km da 12 min.
    monkeypatch.setattr(routes_on_demand, "_calcular_eta_osrm_minutos", lambda *a, **k: None)


@pytest.fixture()
def http():
    Base.metadata.drop_all(bind=engine)
    init_db()
    return TestClient(app)


def _usuario(tipo, email, **extras):
    db = SessionLocal()
    try:
        extras.setdefault("perfil_aprovado", True)
        u = models.Usuario(nome=email.split("@")[0], email=email, senha_hash="x", tipo=tipo, **extras)
        db.add(u)
        db.commit()
        db.refresh(u)
        return u.id, {"Authorization": f"Bearer {create_access_token({'sub': str(u.id), 'tipo': tipo})}"}
    finally:
        db.close()


def _barbearia(email="dono@x.com", pagas=1):
    dono_id, headers = _usuario("barbearia", email)
    db = SessionLocal()
    try:
        b = models.Barbearia(usuario_id=dono_id, nome="Barbearia Raio", endereco="Rua A", latitude=LAT, longitude=LON)
        db.add(b)
        db.flush()
        for numero in range(1, pagas + 1):
            db.add(models.Cadeira(barbearia_id=b.id, numero=numero, status=models.StatusCadeira.BLOQUEADA))
        db.add(models.AssinaturaBarbearia(
            barbearia_id=b.id, quantidade_cadeiras=pagas, valor_mensalidade=50.0, dia_vencimento=10,
            proximo_vencimento=datetime.now() + timedelta(days=30), status="ativa",
        ))
        db.commit()
        return {"id": b.id, "headers": headers}
    finally:
        db.close()


def _ao_norte(km):
    """Ponto a `km` em linha reta ao norte da barbearia."""
    return LAT + km / KM_POR_GRAU, LON


def _freelancer(email, km, online=True, radar=True, **extras):
    """
    online: o status ONLINE/OFFLINE do freelancer (online_regiao) e o radar do painel juntos.
    radar=False: nunca abriu o painel (sem linha no radar), so a posicao do perfil.
    """
    lat, lon = _ao_norte(km)
    fid, headers = _usuario(
        "barbeiro", email, latitude=lat, longitude=lon, online_regiao=online, disponivel=online, **extras
    )
    if radar:
        db = SessionLocal()
        try:
            db.add(models.RadarFreelancer(
                freelancer_id=fid, is_online=online, em_atendimento=False, latitude=lat, longitude=lon,
            ))
            db.commit()
        finally:
            db.close()
    return fid, headers


def _anunciar(http, loja, quantidade=1):
    r = http.post(f"{BASE}/anunciar", json={"quantidade": quantidade}, headers=loja["headers"])
    assert r.status_code == 201, r.text
    return r.json()["publicadas"]


def _avisados(vaga_id):
    db = SessionLocal()
    try:
        return {
            n.usuario_id
            for n in db.query(models.Notificacao).filter(
                models.Notificacao.tipo == "vaga_disponivel",
                models.Notificacao.referencia_id == vaga_id,
            )
        }
    finally:
        db.close()


def _vagas_visiveis(http, headers):
    r = http.get(f"{BASE}/ativas", headers=headers)
    assert r.status_code == 200, r.text
    return {v["id"] for v in r.json()}


def test_raio_do_anuncio_e_8_km():
    assert regras_vagas.RAIO_ANUNCIO_VAGA_KM == 8.0


@pytest.mark.parametrize("km", [2, 4, 6, 7.9, 8])
@pytest.mark.parametrize("online", [True, False], ids=["online", "offline"])
def test_freelancer_ate_8_km_recebe_o_anuncio(http, km, online):
    loja = _barbearia()
    fid, headers = _freelancer("f@x.com", km, online=online)

    vaga_id = _anunciar(http, loja)[0]

    assert fid in _avisados(vaga_id)
    # Avisado tambem consegue abrir e consultar a vaga no app.
    assert vaga_id in _vagas_visiveis(http, headers)


@pytest.mark.parametrize("km", [8.01, 8.5, 12])
@pytest.mark.parametrize("online", [True, False], ids=["online", "offline"])
def test_freelancer_acima_de_8_km_nao_recebe(http, km, online):
    loja = _barbearia()
    fid, headers = _freelancer("f@x.com", km, online=online)

    vaga_id = _anunciar(http, loja)[0]

    assert fid not in _avisados(vaga_id)
    assert vaga_id not in _vagas_visiveis(http, headers)


def test_mesmo_anuncio_alcanca_todos_os_cenarios_juntos(http):
    loja = _barbearia()
    dentro = {
        "2km": _freelancer("a@x.com", 2)[0],
        "4km_offline": _freelancer("b@x.com", 4, online=False)[0],
        "6km": _freelancer("c@x.com", 6)[0],
        "7.9km_offline": _freelancer("d@x.com", 7.9, online=False)[0],
        "8km": _freelancer("e@x.com", 8)[0],
    }
    fora = _freelancer("g@x.com", 9)[0]

    vaga_id = _anunciar(http, loja)[0]

    assert _avisados(vaga_id) == set(dentro.values())
    assert fora not in _avisados(vaga_id)


def test_caso_real_status_online_com_radar_desligado_recebe(http):
    """
    Causa do teste de 04/11: o freelancer estava ONLINE no app (online_regiao), mas o
    radar do painel estava desligado (logout / app fechado) e o aviso so olhava o radar.
    """
    loja = _barbearia()
    fid, _ = _freelancer("f@x.com", 4, online=False)
    db = SessionLocal()
    try:
        db.query(models.Usuario).filter(models.Usuario.id == fid).update({"online_regiao": True})
        db.commit()
    finally:
        db.close()

    vaga_id = _anunciar(http, loja)[0]

    assert fid in _avisados(vaga_id)


def test_sem_radar_usa_a_posicao_do_perfil(http):
    loja = _barbearia()
    fid, headers = _freelancer("f@x.com", 5, online=False, radar=False)

    vaga_id = _anunciar(http, loja)[0]

    assert fid in _avisados(vaga_id)
    assert vaga_id in _vagas_visiveis(http, headers)


def test_freelancer_em_atendimento_tambem_e_avisado(http):
    loja = _barbearia()
    fid, _ = _freelancer("f@x.com", 3)
    db = SessionLocal()
    try:
        db.query(models.RadarFreelancer).filter(models.RadarFreelancer.freelancer_id == fid).update(
            {"em_atendimento": True, "ocupado_ate": datetime.now() + timedelta(hours=1)}
        )
        db.commit()
    finally:
        db.close()

    vaga_id = _anunciar(http, loja)[0]

    assert fid in _avisados(vaga_id)


@pytest.mark.parametrize("extras", [
    {"perfil_aprovado": False},
    {"bloqueado_por_admin": True},
    {"cadastro_pendente": True},
], ids=["cadastro_em_analise", "bloqueado_pelo_adm", "cadastro_incompleto"])
def test_freelancer_nao_elegivel_nao_recebe(http, extras):
    loja = _barbearia()
    fid, _ = _freelancer("f@x.com", 2, **extras)

    vaga_id = _anunciar(http, loja)[0]

    assert fid not in _avisados(vaga_id)


def test_freelancer_sem_localizacao_nao_recebe(http):
    loja = _barbearia()
    fid, _ = _usuario("barbeiro", "f@x.com", online_regiao=True)

    vaga_id = _anunciar(http, loja)[0]

    assert fid not in _avisados(vaga_id)


def test_cliente_e_dono_nao_recebem_aviso_de_vaga(http):
    loja = _barbearia()
    cliente_id, _ = _usuario("cliente", "c@x.com", latitude=LAT, longitude=LON)
    outra_loja_id, _ = _usuario("barbearia", "outra@x.com", latitude=LAT, longitude=LON)

    vaga_id = _anunciar(http, loja)[0]

    assert cliente_id not in _avisados(vaga_id)
    assert outra_loja_id not in _avisados(vaga_id)


def test_vaga_gravada_com_raio_de_8_km_mesmo_se_o_dono_mandar_outro(http):
    loja = _barbearia()
    r = http.post(f"{BASE}/anunciar", json={"quantidade": 1, "raio_km": 2}, headers=loja["headers"])
    assert r.status_code == 201, r.text
    vaga = next(v for v in r.json()["vagas"] if v["id"] == r.json()["publicadas"][0])
    assert vaga["raio_km"] == 8.0


def test_push_sai_para_quem_tem_token_inclusive_offline(http, monkeypatch):
    enviados = []
    monkeypatch.setattr(
        routes_on_demand, "enviar_notificacao_novo_chamado",
        lambda **kwargs: enviados.append(kwargs["token_dispositivo"]),
    )
    loja = _barbearia()
    _freelancer("a@x.com", 6, online=False, device_token="tok-offline")
    _freelancer("b@x.com", 3, online=True, device_token="tok-online")
    _freelancer("c@x.com", 10, online=True, device_token="tok-longe")

    _anunciar(http, loja)

    assert sorted(enviados) == ["tok-offline", "tok-online"]


def test_candidatura_mantem_as_regras_atuais(http):
    """Ser avisado nao muda a candidatura: continua exigindo radar ligado e ETA de ate 10 min."""
    loja = _barbearia()
    _, offline_perto = _freelancer("a@x.com", 2, online=False)
    _, online_longe = _freelancer("b@x.com", 7.9, online=True)  # 12 min a 40 km/h
    _, online_perto = _freelancer("c@x.com", 2, online=True)

    vaga_id = _anunciar(http, loja)[0]

    r = http.post(f"{BASE}/{vaga_id}/candidatar-se", headers=offline_perto)
    assert r.status_code == 400 and "online" in r.json()["detail"].lower()
    r = http.post(f"{BASE}/{vaga_id}/candidatar-se", headers=online_longe)
    assert r.status_code == 400 and "10 min" in r.json()["detail"]
    assert http.post(f"{BASE}/{vaga_id}/candidatar-se", headers=online_perto).status_code == 200


def test_vaga_relampago_continua_so_para_radar_ligado(http):
    """O endpoint antigo de vaga relampago nao foi alterado: so radar ligado no raio pedido."""
    loja = _barbearia()
    online_id, _ = _freelancer("a@x.com", 2, online=True)
    offline_id, _ = _freelancer("b@x.com", 2, online=False)
    db = SessionLocal()
    try:
        cadeira_id = db.query(models.Cadeira).filter(models.Cadeira.barbearia_id == loja["id"]).first().id
    finally:
        db.close()

    r = http.post(f"{BASE}/acionar", json={"cadeira_id": cadeira_id, "raio_km": 5, "expira_em_minutos": 10},
                  headers=loja["headers"])
    assert r.status_code == 201, r.text

    assert _avisados(r.json()["id"]) == {online_id}
