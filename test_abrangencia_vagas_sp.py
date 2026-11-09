"""
Abrangência da vaga de diária: o município de São Paulo inteiro, sem raio em km.

- Só barbearia dentro do limite oficial da capital (IBGE) anuncia; Guarulhos, Osasco, ABC etc. não.
- Todo freelancer aprovado, de qualquer região, ONLINE ou OFFLINE, com ou sem posição, é avisado e vê.
- Candidatura sem limite de distância/ETA (continua exigindo radar ligado e taxa em dia).
- Vaga relâmpago e as demais regras de proximidade não mudam.

SQLite temporário, sem chamadas externas.

    python -m pytest test_abrangencia_vagas_sp.py -v
"""

import os
import tempfile
from datetime import datetime, timedelta

_DB = os.path.join(tempfile.mkdtemp(prefix="bm_vagas_sp_"), "teste.db")
os.environ["DATABASE_URL"] = f"sqlite:///{_DB}"

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app import models, routes_on_demand  # noqa: E402
from app.database import Base, SessionLocal, engine, init_db  # noqa: E402
from app.main import app  # noqa: E402
from app.routes import create_access_token  # noqa: E402
from app.sao_paulo_capital import bairro_do_endereco, esta_na_capital, localizar_na_capital  # noqa: E402

BASE = "/api/v1/on-demand/cadeiras-acionadas"

# Pontos reais (latitude, longitude).
ZONA_LESTE = (-23.5453, -46.4742)        # Itaquera
ZONA_SUL = (-23.6534, -46.7086)          # Santo Amaro
ZONA_NORTE = (-23.5025, -46.6253)        # Santana
ZONA_OESTE = (-23.5614, -46.6823)        # Pinheiros
CENTRO = (-23.5503, -46.6339)            # Praça da Sé
EXTREMO_SUL = (-23.9056, -46.7048)       # Marsilac (Parelheiros)
EXTREMO_NORTE = (-23.4049, -46.7539)     # Perus
EXTREMO_LESTE = (-23.5826, -46.4093)     # Cidade Tiradentes

GUARULHOS = (-23.4628, -46.5333)
OSASCO = (-23.5329, -46.7920)
SANTO_ANDRE = (-23.6639, -46.5383)
SAO_BERNARDO = (-23.6914, -46.5646)


@pytest.fixture(autouse=True)
def sem_rota_externa(monkeypatch):
    # ETA pela distancia (40 km/h), sem OSRM.
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


def _barbearia(local, email="dono@x.com", pagas=1, endereco="Rua A, 100"):
    dono_id, headers = _usuario("barbearia", email)
    db = SessionLocal()
    try:
        b = models.Barbearia(
            usuario_id=dono_id, nome=f"Barbearia {email}", endereco=endereco, latitude=local[0], longitude=local[1],
        )
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


def _freelancer(email, local, online=True, radar=True, **extras):
    """
    local=None: freelancer sem posicao conhecida.
    online: status ONLINE/OFFLINE (online_regiao) e radar do painel juntos.
    radar=False: nunca abriu o painel (sem linha no radar).
    """
    lat, lon = local if local else (None, None)
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
    r = http.post(f"{BASE}/anunciar", json={"percentual_freelancer": 50, "quantidade": quantidade}, headers=loja["headers"])
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
    return {v["id"]: v for v in r.json()}


# ---------------------------------------------------------------- limite do municipio

@pytest.mark.parametrize("local, regiao", [
    (ZONA_LESTE, "Zona Leste"),
    (ZONA_SUL, "Zona Sul"),
    (ZONA_NORTE, "Zona Norte"),
    (ZONA_OESTE, "Zona Oeste"),
    (CENTRO, "Centro"),
    (EXTREMO_SUL, "Zona Sul"),
    (EXTREMO_NORTE, "Zona Norte"),
    (EXTREMO_LESTE, "Zona Leste"),
])
def test_ponto_da_capital_recebe_a_regiao_oficial(local, regiao):
    assert localizar_na_capital(*local)["regiao"] == regiao


@pytest.mark.parametrize("local", [
    GUARULHOS, OSASCO, SANTO_ANDRE, SAO_BERNARDO,
    (-23.6229, -46.5548),  # Sao Caetano do Sul
    (-23.6861, -46.6228),  # Diadema
    (-23.6019, -46.7526),  # Taboao da Serra
    (-22.9068, -43.1729),  # Rio de Janeiro
], ids=["guarulhos", "osasco", "santo_andre", "sao_bernardo", "sao_caetano", "diadema", "taboao", "rio"])
def test_municipio_vizinho_fica_fora(local):
    assert not esta_na_capital(*local)
    assert localizar_na_capital(*local) is None


@pytest.mark.parametrize("local", [(None, None), (None, -46.6), ("abc", "def")])
def test_sem_coordenadas_fica_fora(local):
    assert localizar_na_capital(*local) is None


# ---------------------------------------------------------------- freelancer de qualquer regiao

@pytest.mark.parametrize("barbearia_em, freelancer_em", [
    (ZONA_SUL, ZONA_LESTE),
    (ZONA_NORTE, ZONA_SUL),
    (ZONA_LESTE, ZONA_OESTE),
    (CENTRO, EXTREMO_NORTE),
    (EXTREMO_SUL, EXTREMO_NORTE),   # ~55 km em linha reta
    (EXTREMO_LESTE, ZONA_OESTE),
], ids=["leste_para_sul", "sul_para_norte", "oeste_para_leste", "norte_para_centro",
        "extremo_norte_para_extremo_sul", "oeste_para_extremo_leste"])
def test_freelancer_de_outra_regiao_e_avisado_ve_e_se_candidata(http, barbearia_em, freelancer_em):
    loja = _barbearia(barbearia_em)
    fid, headers = _freelancer("f@x.com", freelancer_em)

    vaga_id = _anunciar(http, loja)[0]

    assert fid in _avisados(vaga_id)
    assert vaga_id in _vagas_visiveis(http, headers)
    r = http.post(f"{BASE}/{vaga_id}/candidatar-se", headers=headers)
    assert r.status_code == 200, r.text

    db = SessionLocal()
    try:
        assert db.query(models.CadeiraAcionadaCandidatura).filter_by(vaga_id=vaga_id, barbeiro_id=fid).count() == 1
    finally:
        db.close()


def test_um_anuncio_alcanca_freelancers_de_todas_as_regioes(http):
    loja = _barbearia(ZONA_SUL)
    todos = {
        _freelancer("leste@x.com", ZONA_LESTE)[0],
        _freelancer("norte@x.com", ZONA_NORTE, online=False)[0],
        _freelancer("oeste@x.com", ZONA_OESTE)[0],
        _freelancer("centro@x.com", CENTRO, online=False, radar=False)[0],
        _freelancer("perus@x.com", EXTREMO_NORTE)[0],
        _freelancer("guarulhos@x.com", GUARULHOS)[0],   # mora fora, trabalha na capital
        _freelancer("sem_gps@x.com", None)[0],
    }

    vaga_id = _anunciar(http, loja)[0]

    assert _avisados(vaga_id) == todos


def test_freelancer_ve_as_vagas_de_todas_as_regioes_da_capital(http):
    lojas = {
        regiao: _barbearia(local, email=f"{regiao}@x.com")
        for regiao, local in {
            "Zona Leste": ZONA_LESTE, "Zona Sul": ZONA_SUL, "Zona Norte": ZONA_NORTE,
            "Zona Oeste": ZONA_OESTE, "Centro": CENTRO,
        }.items()
    }
    _, headers = _freelancer("f@x.com", ZONA_LESTE)

    vaga_por_regiao = {regiao: _anunciar(http, loja)[0] for regiao, loja in lojas.items()}

    visiveis = _vagas_visiveis(http, headers)
    for regiao, vaga_id in vaga_por_regiao.items():
        assert vaga_id in visiveis
        assert visiveis[vaga_id]["barbearia_regiao"] == regiao


@pytest.mark.parametrize("online", [True, False], ids=["online", "offline"])
def test_freelancer_sem_localizacao_e_avisado_e_ve(http, online):
    loja = _barbearia(ZONA_NORTE)
    fid, headers = _freelancer("f@x.com", None, online=online, radar=online)

    vaga_id = _anunciar(http, loja)[0]

    assert fid in _avisados(vaga_id)
    vaga = _vagas_visiveis(http, headers)[vaga_id]
    assert vaga["eta_min_usuario_atual"] is None


def test_freelancer_sem_localizacao_com_radar_ligado_se_candidata(http):
    loja = _barbearia(ZONA_OESTE)
    _, headers = _freelancer("f@x.com", None, online=True)
    vaga_id = _anunciar(http, loja)[0]

    r = http.post(f"{BASE}/{vaga_id}/candidatar-se", headers=headers)

    assert r.status_code == 200, r.text


def test_vaga_mostra_endereco_regiao_e_subprefeitura(http):
    loja = _barbearia(ZONA_SUL, endereco="Av. Santo Amaro, 5000")
    _, headers = _freelancer("f@x.com", ZONA_NORTE)

    vaga_id = _anunciar(http, loja)[0]

    vaga = _vagas_visiveis(http, headers)[vaga_id]
    assert vaga["barbearia_regiao"] == "Zona Sul"
    assert vaga["barbearia_subprefeitura"] == "Santo Amaro"
    assert vaga["barbearia_endereco"] == "Av. Santo Amaro, 5000"
    assert vaga["raio_km"] is None
    assert vaga["eta_min_usuario_atual"] > 10  # Norte -> Sul: longe, e mesmo assim aparece


ARTUR_ALVIM = (-23.5408, -46.4848)  # distrito Artur Alvim, dentro da subprefeitura da Penha


def test_vaga_mostra_o_bairro_do_endereco_e_nao_a_subprefeitura(http):
    loja = _barbearia(
        ARTUR_ALVIM, endereco="Rua Doutor Campos Moura, 120, Artur Alvim, São Paulo/SP"
    )
    _, headers = _freelancer("f@x.com", ZONA_SUL)

    vaga_id = _anunciar(http, loja)[0]
    vaga = _vagas_visiveis(http, headers)[vaga_id]

    assert vaga["barbearia_regiao"] == "Zona Leste"
    assert vaga["barbearia_subprefeitura"] == "Penha"
    assert vaga["barbearia_bairro"] == "Artur Alvim"


def test_vaga_sem_bairro_no_endereco_nao_inventa_bairro(http):
    loja = _barbearia(ZONA_SUL, endereco="Av. Santo Amaro, 5000")
    _, headers = _freelancer("f@x.com", ZONA_NORTE)

    vaga_id = _anunciar(http, loja)[0]
    vaga = _vagas_visiveis(http, headers)[vaga_id]

    assert vaga["barbearia_regiao"] == "Zona Sul"
    assert vaga["barbearia_bairro"] is None


@pytest.mark.parametrize("endereco, bairro", [
    ("Rua A, 120, Artur Alvim, São Paulo/SP", "Artur Alvim"),          # endereco pelo CEP, com numero
    ("Rua A, Artur Alvim, São Paulo/SP", "Artur Alvim"),               # cadastro, sem numero
    ("Rua A, 120 - Artur Alvim, São Paulo - SP", "Artur Alvim"),       # digitado com hifen
    ("Rua A, 120, São Paulo/SP", None),                                # CEP sem bairro
    ("Rua A, São Paulo/SP", None),
    ("Av. Santo Amaro, 5000", None),
    ("120, Rua A, Artur Alvim, Penha, São Paulo, SP, 03590-000, Brasil", None),  # GPS (Nominatim)
    ("Lat -23.540800, Lon -46.484800", None),
    ("", None),
    (None, None),
])
def test_bairro_do_endereco(endereco, bairro):
    assert bairro_do_endereco(endereco) == bairro


def test_aviso_diz_a_regiao_da_vaga(http):
    loja = _barbearia(ZONA_LESTE)
    fid, _ = _freelancer("f@x.com", ZONA_SUL)

    vaga_id = _anunciar(http, loja)[0]

    db = SessionLocal()
    try:
        aviso = db.query(models.Notificacao).filter_by(usuario_id=fid, referencia_id=vaga_id).one()
        assert "Zona Leste" in aviso.mensagem and "Itaquera" in aviso.mensagem
    finally:
        db.close()


def test_vaga_gravada_sem_raio_mesmo_se_o_dono_mandar_um(http):
    loja = _barbearia(CENTRO)
    r = http.post(f"{BASE}/anunciar", json={"percentual_freelancer": 50, "quantidade": 1, "raio_km": 2}, headers=loja["headers"])
    assert r.status_code == 201, r.text
    vaga = next(v for v in r.json()["vagas"] if v["id"] == r.json()["publicadas"][0])
    assert vaga["raio_km"] is None
    assert vaga["barbearia_regiao"] == "Centro"


# ---------------------------------------------------------------- fora da capital

@pytest.mark.parametrize("local", [GUARULHOS, OSASCO, SANTO_ANDRE, SAO_BERNARDO],
                         ids=["guarulhos", "osasco", "santo_andre", "sao_bernardo"])
def test_barbearia_de_municipio_vizinho_nao_anuncia(http, local):
    loja = _barbearia(local)
    fid, _ = _freelancer("f@x.com", ZONA_LESTE)

    r = http.post(f"{BASE}/anunciar", json={"percentual_freelancer": 50, "quantidade": 1}, headers=loja["headers"])

    assert r.status_code == 400
    assert "município de São Paulo" in r.json()["detail"]
    db = SessionLocal()
    try:
        assert db.query(models.CadeiraAcionada).count() == 0
        assert db.query(models.Notificacao).filter_by(usuario_id=fid).count() == 0
    finally:
        db.close()


def test_barbearia_sem_coordenadas_nao_anuncia(http):
    loja = _barbearia((None, None))
    r = http.post(f"{BASE}/anunciar", json={"percentual_freelancer": 50, "quantidade": 1}, headers=loja["headers"])
    assert r.status_code == 400
    assert "endereço" in r.json()["detail"]


def test_vaga_antiga_de_fora_da_capital_nao_aparece_nem_aceita_candidatura(http):
    """Vaga de diaria gravada antes da regra (ou direto no banco) por barbearia de Guarulhos."""
    loja = _barbearia(GUARULHOS)
    _, headers = _freelancer("f@x.com", ZONA_LESTE)
    db = SessionLocal()
    try:
        cadeira = db.query(models.Cadeira).filter_by(barbearia_id=loja["id"]).first()
        vaga = models.CadeiraAcionada(
            barbearia_id=loja["id"], cadeira_id=cadeira.id, status="disponivel", raio_km=8.0,
            tipo_servico="vaga_diaria", expira_em=datetime.utcnow() + timedelta(hours=5),
        )
        db.add(vaga)
        db.commit()
        vaga_id = vaga.id
    finally:
        db.close()

    assert vaga_id not in _vagas_visiveis(http, headers)
    assert http.post(f"{BASE}/{vaga_id}/candidatar-se", headers=headers).status_code == 400


# ---------------------------------------------------------------- regras que continuam

@pytest.mark.parametrize("extras", [
    {"perfil_aprovado": False},
    {"bloqueado_por_admin": True},
    {"cadastro_pendente": True},
], ids=["cadastro_em_analise", "bloqueado_pelo_adm", "cadastro_incompleto"])
def test_freelancer_nao_elegivel_nao_recebe(http, extras):
    loja = _barbearia(ZONA_SUL)
    fid, _ = _freelancer("f@x.com", ZONA_SUL, **extras)

    vaga_id = _anunciar(http, loja)[0]

    assert fid not in _avisados(vaga_id)


def test_cliente_e_dono_nao_recebem_nem_veem_vaga_de_diaria(http):
    loja = _barbearia(ZONA_SUL)
    cliente_id, cliente_headers = _usuario("cliente", "c@x.com", latitude=ZONA_SUL[0], longitude=ZONA_SUL[1])
    outra_loja_id, _ = _usuario("barbearia", "outra@x.com")

    vaga_id = _anunciar(http, loja)[0]

    assert cliente_id not in _avisados(vaga_id)
    assert outra_loja_id not in _avisados(vaga_id)
    assert vaga_id not in _vagas_visiveis(http, cliente_headers)


def test_candidatura_continua_exigindo_radar_ligado(http):
    loja = _barbearia(ZONA_SUL)
    _, offline = _freelancer("f@x.com", ZONA_SUL, online=False)
    vaga_id = _anunciar(http, loja)[0]

    r = http.post(f"{BASE}/{vaga_id}/candidatar-se", headers=offline)

    assert r.status_code == 400 and "online" in r.json()["detail"].lower()


def test_push_sai_para_todo_freelancer_com_token(http, monkeypatch):
    enviados = []
    monkeypatch.setattr(
        routes_on_demand, "enviar_notificacao_novo_chamado",
        lambda **kwargs: enviados.append(kwargs["token_dispositivo"]),
    )
    loja = _barbearia(ZONA_SUL)
    _freelancer("a@x.com", ZONA_LESTE, online=False, device_token="tok-leste")
    _freelancer("b@x.com", EXTREMO_NORTE, online=True, device_token="tok-perus")

    _anunciar(http, loja)

    assert sorted(enviados) == ["tok-leste", "tok-perus"]


def _vaga_relampago(http, loja, raio_km=5):
    db = SessionLocal()
    try:
        cadeira_id = db.query(models.Cadeira).filter(models.Cadeira.barbearia_id == loja["id"]).first().id
    finally:
        db.close()
    r = http.post(f"{BASE}/acionar", json={"cadeira_id": cadeira_id, "raio_km": raio_km, "expira_em_minutos": 10},
                  headers=loja["headers"])
    assert r.status_code == 201, r.text
    return r.json()


def test_vaga_relampago_continua_com_raio_e_radar(http):
    """Vaga relampago nao mudou: so radar ligado dentro do raio pedido."""
    loja = _barbearia(ZONA_SUL)
    perto_online, _ = _freelancer("a@x.com", (ZONA_SUL[0] + 0.01, ZONA_SUL[1]), online=True)  # ~1,1 km
    perto_offline, _ = _freelancer("b@x.com", (ZONA_SUL[0] + 0.01, ZONA_SUL[1]), online=False)
    longe_online, _ = _freelancer("c@x.com", ZONA_NORTE, online=True)

    vaga = _vaga_relampago(http, loja)

    assert _avisados(vaga["id"]) == {perto_online}
    assert vaga["raio_km"] == 5
    assert vaga.get("barbearia_regiao") is None
    assert longe_online not in _avisados(vaga["id"])
    assert perto_offline not in _avisados(vaga["id"])


def test_vaga_relampago_continua_limitada_a_10_min(http):
    loja = _barbearia(ZONA_SUL)
    _, longe = _freelancer("c@x.com", ZONA_NORTE, online=True)
    _, perto = _freelancer("a@x.com", (ZONA_SUL[0] + 0.01, ZONA_SUL[1]), online=True)

    vaga = _vaga_relampago(http, loja)

    assert vaga["id"] not in _vagas_visiveis(http, longe)
    r = http.post(f"{BASE}/{vaga['id']}/candidatar-se", headers=longe)
    assert r.status_code == 400 and "10 min" in r.json()["detail"]
    assert http.post(f"{BASE}/{vaga['id']}/candidatar-se", headers=perto).status_code == 200


# ---------------------------------------------------------------- distancia na lista de candidatos

def test_lista_de_candidatos_mostra_distancia_sem_limite(http):
    from app.routes_on_demand import calcular_distancia_haversine

    loja = _barbearia(EXTREMO_SUL)
    _, perto = _freelancer("perto@x.com", ZONA_SUL)
    _, longe = _freelancer("longe@x.com", EXTREMO_NORTE)   # ~55 km
    _, sem_gps = _freelancer("semgps@x.com", None)
    vaga_id = _anunciar(http, loja)[0]
    for headers in (perto, longe, sem_gps):
        assert http.post(f"{BASE}/{vaga_id}/candidatar-se", headers=headers).status_code == 200

    r = http.get(f"{BASE}/{vaga_id}/candidatos", headers=loja["headers"])

    assert r.status_code == 200, r.text
    por_nome = {c["nome"]: c["distancia_km"] for c in r.json()}
    assert por_nome["perto"] == round(calcular_distancia_haversine(*EXTREMO_SUL, *ZONA_SUL), 1)
    assert por_nome["longe"] == round(calcular_distancia_haversine(*EXTREMO_SUL, *EXTREMO_NORTE), 1)
    assert por_nome["longe"] > 50
    assert por_nome["semgps"] is None


def test_distancia_usa_posicao_do_radar_antes_da_do_perfil(http):
    loja = _barbearia(CENTRO)
    fid, headers = _freelancer("f@x.com", CENTRO)
    vaga_id = _anunciar(http, loja)[0]
    assert http.post(f"{BASE}/{vaga_id}/candidatar-se", headers=headers).status_code == 200
    db = SessionLocal()
    try:
        radar = db.query(models.RadarFreelancer).filter_by(freelancer_id=fid).first()
        radar.latitude, radar.longitude = EXTREMO_LESTE
        db.commit()
    finally:
        db.close()

    [candidato] = http.get(f"{BASE}/{vaga_id}/candidatos", headers=loja["headers"]).json()

    assert candidato["distancia_km"] > 20
