"""
Blindagem de segurança/LGPD (2026-11-08): IDOR, documentos privados, painel só do ADM,
SECRET_KEY obrigatória, limite de tentativas, logs limpos, exclusão de conta, CORS,
refresh token com rotação e dados pessoais criptografados em repouso.

SQLite temporário, sem chamadas externas.

    .venv/Scripts/python -m pytest test_seguranca_lgpd.py -v
"""

import logging
import os
import tempfile
import time
from datetime import datetime, timedelta
from pathlib import Path

_DB = os.path.join(tempfile.mkdtemp(prefix="bm_seg_"), "teste.db")
os.environ["DATABASE_URL"] = f"sqlite:///{_DB}"
os.environ.setdefault("DADOS_CRIPTO_KEY", "ab" * 64)

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import text  # noqa: E402

from app import models, seguranca  # noqa: E402
from app.database import Base, SessionLocal, engine, init_db  # noqa: E402
from app.limite_requisicoes import limpar_limites  # noqa: E402
from app.main import app  # noqa: E402
from app.routes import create_access_token, get_password_hash  # noqa: E402

V1 = "/api/v1"
SENHA = "Senha@123"
REFRESH = {"X-Suporta-Refresh": "1"}


@pytest.fixture()
def cena():
    limpar_limites()
    Base.metadata.drop_all(bind=engine)
    init_db()
    db = SessionLocal()
    try:
        def usuario(tipo, email, **extras):
            u = models.Usuario(
                nome=email.split("@")[0], email=email, senha_hash=get_password_hash(SENHA), tipo=tipo,
                perfil_aprovado=True, email_verificado=True, latitude=-23.55, longitude=-46.63, **extras,
            )
            db.add(u)
            db.flush()
            return u

        adm = usuario("admin", "adm@t.com")
        cliente = usuario("cliente", "cli@t.com", telefone="11966660006", cpf="39053344705")
        dono = usuario("barbearia", "dono@t.com", telefone="11922220002")
        loja = models.Barbearia(usuario_id=dono.id, nome="Loja", endereco="Rua A", latitude=-23.55, longitude=-46.63,
                                telefone="1133330003")
        db.add(loja)
        db.flush()
        servico = models.Servico(barbearia_id=loja.id, nome="Corte", categoria="corte", valor=50.0, duracao_minutos=30, ativo=True)
        db.add(servico)
        free = usuario("barbeiro", "free@t.com", telefone="11911110001",
                       documento_frente_url="/uploads/documentos/teste-frente.jpg",
                       selfie_documento_url="/uploads/documentos/teste-selfie.jpg")
        db.flush()
        chamado = models.Chamado(
            cliente_id=cliente.id, barbeiro_id=free.id, barbearia_id=loja.id, servico_id=servico.id,
            status="concluido", valor_original=50.0, valor_final=50.0,
            data_hora_inicio=datetime.utcnow(), data_hora_fim=datetime.utcnow() + timedelta(minutes=30),
        )
        db.add(chamado)
        db.add(models.ContaPagamentoUsuario(usuario_id=free.id, chave_pix="free@pix.com", titular_documento="39053344705"))
        db.commit()

        def headers(u):
            return {"Authorization": f"Bearer {create_access_token({'sub': str(u.id), 'tipo': u.tipo})}"}

        return {
            "http": TestClient(app, raise_server_exceptions=False),
            "ids": {"adm": adm.id, "cliente": cliente.id, "dono": dono.id, "free": free.id,
                    "loja": loja.id, "chamado": chamado.id, "servico": servico.id},
            "h": {"adm": headers(adm), "cliente": headers(cliente), "dono": headers(dono), "free": headers(free)},
        }
    finally:
        db.close()


@pytest.fixture()
def arquivos_documento():
    pasta = Path("uploads/documentos")
    pasta.mkdir(parents=True, exist_ok=True)
    criados = []
    for nome in ("teste-frente.jpg", "teste-selfie.jpg"):
        (pasta / nome).write_bytes(b"\xff\xd8 imagem de teste")
        criados.append(pasta / nome)
    yield
    for c in criados:
        c.unlink(missing_ok=True)


def _login(http, tipo, email, senha=SENHA, headers=None):
    return http.post(f"{V1}/login/{tipo}/", data={"username": email, "password": senha}, headers=headers or {})


# --- 1. IDOR: agenda do freelancer ---------------------------------------------------------

def test_agenda_do_freelancer_exige_login_e_dono(cena):
    http, ids, h = cena["http"], cena["ids"], cena["h"]
    url = f"{V1}/barbeiro/{ids['free']}/agendamentos"
    assert http.get(url).status_code == 401
    assert http.get(url, headers=h["cliente"]).status_code == 403
    assert http.get(url, headers=h["dono"]).status_code == 403
    r = http.get(url, headers=h["free"])
    assert r.status_code == 200 and len(r.json()) == 1
    assert http.get(url, headers=h["adm"]).status_code == 200


# --- 2. Documentos privados ----------------------------------------------------------------

def test_documento_nao_e_publico_e_adm_abre_por_link_assinado(cena, arquivos_documento):
    http, ids, h = cena["http"], cena["ids"], cena["h"]
    assert http.get("/uploads/documentos/teste-frente.jpg").status_code == 404

    det = http.get(f"/admin/api/usuario/{ids['free']}", headers=h["adm"])
    assert det.status_code == 200
    link = det.json()["documento_frente"]
    assert link.startswith(f"{V1}/documentos/arquivo/teste-frente.jpg?exp=")
    r = http.get(link)
    assert r.status_code == 200 and r.content.startswith(b"\xff\xd8")

    # assinatura adulterada, outro arquivo com a mesma assinatura, link vencido
    assert http.get(link[:-2] + "xx").status_code == 403
    assert http.get(link.replace("teste-frente", "teste-selfie")).status_code == 403
    exp = int(time.time()) - 10
    vencido = f"{V1}/documentos/arquivo/teste-frente.jpg?exp={exp}&sig={seguranca._assinatura('teste-frente.jpg', exp)}"
    assert http.get(vencido).status_code == 403


def test_barbearia_nao_lista_nem_aprova_documentos(cena):
    http, ids, h = cena["http"], cena["ids"], cena["h"]
    assert http.get(f"{V1}/documentos/pendentes", headers=h["dono"]).status_code == 403
    r = http.post(f"{V1}/documentos/verificar", json={"usuario_id": ids["free"], "aprovado": True}, headers=h["dono"])
    assert r.status_code == 403


# --- 3. Painel ADM só para ADM -------------------------------------------------------------

@pytest.mark.parametrize("metodo,rota", [
    ("get", "/admin/api/pendentes"), ("get", "/admin/api/aprovados"), ("get", "/admin/api/estatisticas"),
    ("get", "/admin/api/usuario/{free}"), ("post", "/admin/api/aprovar/{free}"), ("get", "/admin/api/buscar?q=a"),
])
def test_barbearia_nao_usa_o_painel_adm(cena, metodo, rota):
    http, ids, h = cena["http"], cena["ids"], cena["h"]
    r = getattr(http, metodo)(rota.format(free=ids["free"]), headers=h["dono"])
    assert r.status_code == 403


# --- 4. SECRET_KEY -------------------------------------------------------------------------

def test_secret_key_fraca_derruba_o_startup_em_producao(monkeypatch):
    monkeypatch.setenv("RAILWAY_ENVIRONMENT", "production")
    for ruim in ("", "INSEGURO_MUDE_ISSO_AGORA", "curta"):
        monkeypatch.setenv("SECRET_KEY", ruim)
        with pytest.raises(RuntimeError):
            seguranca.carregar_secret_key()
    monkeypatch.setenv("SECRET_KEY", "f" * 64)
    assert seguranca.carregar_secret_key() == "f" * 64


# --- 5. Limite de tentativas ---------------------------------------------------------------

def test_login_bloqueia_forca_bruta_por_email(cena):
    http = cena["http"]
    for _ in range(10):
        assert _login(http, "cliente", "cli@t.com", "errada").status_code == 401
    r = _login(http, "cliente", "cli@t.com", SENHA)
    assert r.status_code == 429 and "Retry-After" in r.headers
    # outro e-mail segue entrando
    assert _login(http, "barbearia", "dono@t.com").status_code == 200


def test_reset_de_senha_limita_pedidos_por_email(cena):
    http = cena["http"]
    for _ in range(3):
        assert http.post(f"{V1}/senha/solicitar-reset", json={"email": "cli@t.com"}).status_code == 200
    assert http.post(f"{V1}/senha/solicitar-reset", json={"email": "cli@t.com"}).status_code == 429


# --- 6. Logs limpos ------------------------------------------------------------------------

def test_reset_de_senha_nao_loga_link_nem_email(cena, caplog, capsys):
    caplog.set_level(logging.INFO)
    cena["http"].post(f"{V1}/senha/solicitar-reset", json={"email": "cli@t.com"})
    saida = caplog.text + capsys.readouterr().out
    assert "reset_token=" not in saida and "cli@t.com" not in saida


def test_requisicao_autenticada_nao_loga_token(cena, capsys):
    h = cena["h"]["cliente"]
    cena["http"].get(f"{V1}/usuarios/perfil-completo", headers=h)
    token = h["Authorization"].split()[1]
    assert token[:30] not in capsys.readouterr().out


# --- 7. Exclusão de conta ------------------------------------------------------------------

def test_excluir_conta_anonimiza_e_bloqueia_acesso(cena):
    http, ids, h = cena["http"], cena["ids"], cena["h"]
    url = f"{V1}/conta/excluir"
    assert http.post(url, json={"senha": SENHA, "confirmacao": "sim"}, headers=h["free"]).status_code == 400
    assert http.post(url, json={"senha": "errada", "confirmacao": "EXCLUIR"}, headers=h["free"]).status_code == 400

    r = http.post(url, json={"senha": SENHA, "confirmacao": "EXCLUIR"}, headers=h["free"])
    assert r.status_code == 200, r.text

    db = SessionLocal()
    try:
        u = db.get(models.Usuario, ids["free"])
        assert u.excluido_em is not None and u.nome == "Usuário excluído"
        assert u.email.endswith("@excluido.invalid") and u.telefone is None and u.documento_frente_url is None
        conta = db.query(models.ContaPagamentoUsuario).filter_by(usuario_id=ids["free"]).one()
        assert conta.chave_pix is None and conta.titular_documento is None
        # histórico preservado
        assert db.get(models.Chamado, ids["chamado"]).barbeiro_id == ids["free"]
    finally:
        db.close()

    assert http.get(f"{V1}/usuarios/perfil-completo", headers=h["free"]).status_code == 401
    assert _login(http, "barbeiro", "free@t.com").status_code == 401


def test_excluir_conta_com_atendimento_em_aberto_e_recusado(cena):
    http, ids, h = cena["http"], cena["ids"], cena["h"]
    db = SessionLocal()
    try:
        db.get(models.Chamado, ids["chamado"]).status = "confirmado"
        db.commit()
    finally:
        db.close()
    r = http.post(f"{V1}/conta/excluir", json={"senha": SENHA, "confirmacao": "EXCLUIR"}, headers=h["cliente"])
    assert r.status_code == 409


# --- 8. CORS -------------------------------------------------------------------------------

def test_cors_recusa_tunel_publico(cena):
    http = cena["http"]
    pre = {"Access-Control-Request-Method": "GET"}
    r = http.options(f"{V1}/teste", headers={"Origin": "https://qualquer.loca.lt", **pre})
    assert r.headers.get("access-control-allow-origin") is None
    r = http.options(f"{V1}/teste", headers={"Origin": "http://localhost", **pre})
    assert r.headers.get("access-control-allow-origin") == "http://localhost"


# --- 9. Refresh token ----------------------------------------------------------------------

def test_login_sem_cabecalho_mantem_formato_antigo(cena):
    r = _login(cena["http"], "cliente", "cli@t.com")
    assert r.status_code == 200 and r.json()["refresh_token"] is None


def test_refresh_com_rotacao_e_deteccao_de_reuso(cena):
    http = cena["http"]
    r = _login(http, "cliente", "cli@t.com", headers=REFRESH)
    assert r.status_code == 200
    corpo = r.json()
    assert corpo["refresh_token"] and corpo["expires_in"] == 3600
    assert http.get(f"{V1}/usuarios/perfil-completo", headers={"Authorization": f"Bearer {corpo['access_token']}"}).status_code == 200

    r1 = http.post(f"{V1}/auth/refresh", json={"refresh_token": corpo["refresh_token"]})
    assert r1.status_code == 200
    novo = r1.json()["refresh_token"]
    assert novo != corpo["refresh_token"]

    # reuso do antigo: derruba a família, inclusive o novo
    assert http.post(f"{V1}/auth/refresh", json={"refresh_token": corpo["refresh_token"]}).status_code == 401
    assert http.post(f"{V1}/auth/refresh", json={"refresh_token": novo}).status_code == 401


def test_logout_revoga_refresh(cena):
    http = cena["http"]
    rt = _login(http, "cliente", "cli@t.com", headers=REFRESH).json()["refresh_token"]
    assert http.post(f"{V1}/auth/logout", json={"refresh_token": rt}).status_code == 200
    assert http.post(f"{V1}/auth/refresh", json={"refresh_token": rt}).status_code == 401


def test_cadastro_rapido_tambem_entrega_refresh(cena):
    r = cena["http"].post(f"{V1}/cadastro-rapido/", json={"tipo": "cliente", "email": "novo@t.com", "senha": SENHA},
                          headers=REFRESH)
    assert r.status_code == 200, r.text
    assert r.json()["refresh_token"]


def test_sessao_antiga_migra_uma_vez(cena):
    from jose import jwt
    http, ids = cena["http"], cena["ids"]
    antigo = jwt.encode({"sub": str(ids["cliente"]), "tipo": "cliente", "exp": datetime.utcnow() + timedelta(days=7)},
                        seguranca.SECRET_KEY, algorithm="HS256")
    r = http.post(f"{V1}/auth/sessao", headers={"Authorization": f"Bearer {antigo}"})
    assert r.status_code == 200 and r.json()["refresh_token"]
    # token novo (com iat) não pode virar refresh por esse caminho
    assert http.post(f"{V1}/auth/sessao", headers=cena["h"]["cliente"]).status_code == 400


def test_reset_de_senha_revoga_sessoes(cena):
    from app.routes_senha import _gerar_token_reset
    http = cena["http"]
    rt = _login(http, "cliente", "cli@t.com", headers=REFRESH).json()["refresh_token"]
    r = http.post(f"{V1}/senha/confirmar-reset", json={"token": _gerar_token_reset("cli@t.com"), "nova_senha": "Outra@123"})
    assert r.status_code == 200, r.text
    assert http.post(f"{V1}/auth/refresh", json={"refresh_token": rt}).status_code == 401


# --- 11. Criptografia em repouso -----------------------------------------------------------

def test_dados_pessoais_ficam_cifrados_no_banco(cena):
    ids = cena["ids"]
    with engine.connect() as c:
        tel, cpf = c.execute(text("SELECT telefone, cpf FROM usuarios WHERE id = :i"), {"i": ids["cliente"]}).one()
        pix = c.execute(text("SELECT chave_pix FROM contas_pagamento_usuarios")).scalar_one()
    assert tel.startswith("enc1:") and cpf.startswith("enc1:") and pix.startswith("enc1:")
    assert "11966660006" not in tel

    db = SessionLocal()
    try:
        u = db.query(models.Usuario).filter(models.Usuario.cpf == "39053344705").one()  # igualdade segue funcionando
        assert u.id == ids["cliente"] and u.telefone == "11966660006"
    finally:
        db.close()


def test_cadastro_recusa_cpf_duplicado_com_cpf_cifrado(cena):
    r = cena["http"].post(f"{V1}/clientes/", json={
        "nome": "Outro", "email": "outro@t.com", "senha": SENHA, "cpf": "39053344705", "telefone": "11900000000",
    })
    assert r.status_code == 400 and "CPF" in r.text


def test_migracao_cifra_valores_antigos_em_texto_aberto(cena):
    from app.cripto_campos import criptografar_dados_existentes
    ids = cena["ids"]
    with engine.begin() as c:
        c.execute(text("UPDATE usuarios SET telefone = '11977770007' WHERE id = :i"), {"i": ids["dono"]})
    db = SessionLocal()
    try:
        assert db.get(models.Usuario, ids["dono"]).telefone == "11977770007"  # legado ainda legível
    finally:
        db.close()
    criptografar_dados_existentes(engine)
    with engine.connect() as c:
        bruto = c.execute(text("SELECT telefone FROM usuarios WHERE id = :i"), {"i": ids["dono"]}).scalar_one()
    assert bruto.startswith("enc1:")
