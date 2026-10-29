"""
Termos de Uso / Política de Privacidade: aceite obrigatório, versões, recusa, idade do
freelancer, bloqueio da API e estrutura da barbearia.

SQLite temporário; os documentos são "publicados" só dentro dos testes (monkeypatch do
catálogo). Nenhuma chamada externa.

    .venv/Scripts/python -m pytest test_termos_aceite.py -v
"""

import os
import tempfile
from dataclasses import replace
from datetime import date, datetime, timedelta

_DB = os.path.join(tempfile.mkdtemp(prefix="bm_termos_"), "teste.db")
os.environ["DATABASE_URL"] = f"sqlite:///{_DB}"

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app import models  # noqa: E402
from app.database import Base, SessionLocal, engine, init_db  # noqa: E402
from app.main import app  # noqa: E402
from app.routes import create_access_token  # noqa: E402
from app.termos import documentos as docs  # noqa: E402
from app.termos import middleware  # noqa: E402

ROTA_PROTEGIDA = "/api/v1/notificacoes/"  # decodifica o token por conta própria
ROTA_PROTEGIDA_2 = "/api/v1/barbearia/{id}/condicoes-estrutura"  # usa get_current_user


def _publicar(monkeypatch, versoes):
    monkeypatch.setattr(docs, "VERSOES", versoes)
    middleware._liberados.clear()


def _todos_publicados():
    return [replace(v, estado=docs.PUBLICADO) for v in docs.VERSOES]


@pytest.fixture()
def cliente_http():
    Base.metadata.drop_all(bind=engine)
    init_db()
    middleware._liberados.clear()
    return TestClient(app)  # sem "with": o job em background não sobe durante o teste


@pytest.fixture()
def publicados(monkeypatch):
    _publicar(monkeypatch, _todos_publicados())


def _nascimento(anos, dias=0):
    hoje = date.today()
    try:
        d = hoje.replace(year=hoje.year - anos)
    except ValueError:  # 29/02
        d = hoje.replace(year=hoje.year - anos, day=28)
    return (d + timedelta(days=dias)).isoformat()


def cadastrar(http, tipo, email, **extra):
    r = http.post("/api/v1/cadastro-rapido/", json={"email": email, "senha": "123456", "tipo": tipo, **extra})
    return r


def auth(token):
    return {"Authorization": f"Bearer {token}"}


def token_de(r):
    assert r.status_code == 200, r.text
    return r.json()["access_token"]


def aceitar_tudo(http, token, perfil, **extra):
    lista = http.get("/api/v1/termos/documentos", params={"perfil": perfil}).json()["documentos"]
    aceites = [{"codigo": d["codigo"], "versao": d["versao"], "confirmado": True} for d in lista]
    return http.post("/api/v1/termos/aceitar", headers=auth(token), json={"aceites": aceites, **extra})


def usuario_id(token):
    from jose import jwt
    from app.routes import ALGORITHM, SECRET_KEY
    return int(jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])["sub"])


# ------------------------------------------------------------------ catálogo

def test_catalogo_consistente():
    vistos = set()
    for v in docs.VERSOES:
        assert (v.codigo, v.versao) not in vistos
        vistos.add((v.codigo, v.versao))
        assert v.conteudo.strip(), v.arquivo
        assert v.estado in (docs.RASCUNHO, docs.PUBLICADO)
        assert set(v.perfis) <= set(docs.PERFIS)
    for perfil in docs.PERFIS:
        tipos = {v.tipo for v in docs.VERSOES if perfil in v.perfis}
        assert tipos == {docs.TERMOS_USO, docs.POLITICA_PRIVACIDADE}


def test_publicado_nao_pode_ter_pendencia_de_definicao():
    """Trava de publicação: texto com [A DEFINIR ...] não pode ir para PUBLICADO."""
    for v in docs.VERSOES:
        if v.estado == docs.PUBLICADO:
            assert docs.MARCADOR_PENDENTE not in v.conteudo, f"{v.arquivo} publicado com pendência"


def test_textos_trazem_regras_obrigatorias():
    freela = docs.buscar("termos-freelancer").conteudo
    dono = docs.buscar("termos-proprietario").conteudo
    cliente = docs.buscar("termos-cliente").conteudo
    for texto in (freela, dono):
        assert "50%" in texto and "40%" in texto and "10%" in texto
        assert "gilete" in texto and "capa de corte" in texto and "secador" in texto
        assert "clientes de porta" in texto.lower()
    assert "18 anos completos" in freela
    assert "Kids" in cliente
    assert "R$ 47,90" in dono and "R$ 17,90" in dono


# ------------------------------------------------------------------ rascunho não bloqueia

def test_rascunho_nao_exige_nada(cliente_http):
    token = token_de(cadastrar(cliente_http, "cliente", "c0@teste.dev"))
    s = cliente_http.get("/api/v1/termos/situacao", headers=auth(token)).json()
    assert s["liberado"] is True and s["pendentes"] == []
    assert cliente_http.get(ROTA_PROTEGIDA, headers=auth(token)).status_code == 200
    # leitura do rascunho continua disponível (revisão jurídica)
    r = cliente_http.get("/api/v1/termos/documentos/termos-cliente")
    assert r.status_code == 200 and r.json()["estado"] == docs.RASCUNHO
    assert cliente_http.get("/api/v1/termos/documentos", params={"perfil": "cliente"}).json()["documentos"] == []
    # ninguém consegue aceitar rascunho
    r = cliente_http.post("/api/v1/termos/aceitar", headers=auth(token),
                          json={"aceites": [{"codigo": "termos-cliente", "versao": "1.0", "confirmado": True}]})
    assert r.status_code == 200
    db = SessionLocal()
    assert db.query(models.AceiteDocumento).count() == 0
    db.close()


# ------------------------------------------------------------------ cliente

def test_cliente_cadastro_e_aceite(cliente_http, publicados):
    token = token_de(cadastrar(cliente_http, "cliente", "c1@teste.dev"))
    s = cliente_http.get("/api/v1/termos/situacao", headers=auth(token)).json()
    assert not s["liberado"]
    assert {p["codigo"] for p in s["pendentes"]} == {"termos-cliente", "politica-privacidade"}

    # bloqueado na API (rota com decodificação própria e rota com get_current_user)
    r = cliente_http.get(ROTA_PROTEGIDA, headers=auth(token))
    assert r.status_code == 428 and r.json()["codigo"] == "TERMOS_PENDENTES"
    assert cliente_http.post("/api/v1/cadastro/completar", headers=auth(token),
                             json={"nome": "Ana", "telefone": "11999990000"}).status_code == 428

    # só um documento confirmado: recusado
    lista = cliente_http.get("/api/v1/termos/documentos", params={"perfil": "cliente"}).json()["documentos"]
    um = [{"codigo": lista[0]["codigo"], "versao": lista[0]["versao"], "confirmado": True}]
    assert cliente_http.post("/api/v1/termos/aceitar", headers=auth(token), json={"aceites": um}).status_code == 400
    # caixa desmarcada não vale
    desmarcado = [{"codigo": d["codigo"], "versao": d["versao"], "confirmado": False} for d in lista]
    assert cliente_http.post("/api/v1/termos/aceitar", headers=auth(token),
                             json={"aceites": desmarcado}).status_code == 400

    antes = datetime.utcnow()
    r = aceitar_tudo(cliente_http, token, "cliente")
    assert r.status_code == 200 and r.json()["liberado"] is True
    assert cliente_http.get(ROTA_PROTEGIDA, headers=auth(token)).status_code == 200

    db = SessionLocal()
    regs = db.query(models.AceiteDocumento).filter(models.AceiteDocumento.usuario_id == usuario_id(token)).all()
    assert {(a.documento_codigo, a.versao, a.perfil, a.decisao) for a in regs} == {
        ("termos-cliente", "1.0", "cliente", "aceito"), ("politica-privacidade", "1.0", "cliente", "aceito")}
    for a in regs:
        assert antes - timedelta(seconds=1) <= a.registrado_em <= datetime.utcnow() + timedelta(seconds=1)
        assert a.conteudo_sha256 == docs.buscar(a.documento_codigo, a.versao).sha256
        assert a.confirmacao.startswith("Li e")
    db.close()

    hist = cliente_http.get("/api/v1/termos/historico", headers=auth(token)).json()["decisoes"]
    assert len(hist) == 2 and all(h["vigente"] for h in hist)


def test_aceite_vigente_nao_e_pedido_de_novo(cliente_http, publicados):
    token = token_de(cadastrar(cliente_http, "cliente", "c2@teste.dev"))
    assert aceitar_tudo(cliente_http, token, "cliente").json()["liberado"]
    # novo login = novo token do mesmo usuário; cache vazio (outro processo)
    middleware._liberados.clear()
    r = cliente_http.post("/api/v1/login/cliente/", data={"username": "c2@teste.dev", "password": "123456"})
    assert r.status_code == 200, r.text
    novo = r.json()["access_token"]
    s = cliente_http.get("/api/v1/termos/situacao", headers=auth(novo)).json()
    assert s["liberado"] and s["pendentes"] == []
    assert cliente_http.get(ROTA_PROTEGIDA, headers=auth(novo)).status_code == 200


def test_versao_desatualizada_no_aceite(cliente_http, publicados):
    token = token_de(cadastrar(cliente_http, "cliente", "c3@teste.dev"))
    r = cliente_http.post("/api/v1/termos/aceitar", headers=auth(token), json={"aceites": [
        {"codigo": "termos-cliente", "versao": "0.9", "confirmado": True},
        {"codigo": "politica-privacidade", "versao": "1.0", "confirmado": True}]})
    assert r.status_code == 409


# ------------------------------------------------------------------ freelancer

def test_freelancer_menor_nao_cria_conta(cliente_http, publicados):
    assert cadastrar(cliente_http, "barbeiro", "f0@teste.dev").status_code == 400  # sem data
    r = cadastrar(cliente_http, "barbeiro", "f1@teste.dev", data_nascimento=_nascimento(18, dias=1))  # faz 18 amanhã
    assert r.status_code == 403 and "18 anos" in r.json()["detail"]
    db = SessionLocal()
    assert db.query(models.Usuario).filter(models.Usuario.email == "f1@teste.dev").first() is None
    db.close()
    # rota antiga de cadastro de barbeiro também barra
    r = cliente_http.post("/api/v1/barbeiros/", json={
        "email": "f2@teste.dev", "senha": "123456", "nome": "Menor", "cpf": "52998224725",
        "data_nascimento": _nascimento(16)})
    assert r.status_code == 403, r.text


def test_freelancer_cadastro_e_aceite(cliente_http, publicados):
    token = token_de(cadastrar(cliente_http, "barbeiro", "f3@teste.dev", data_nascimento=_nascimento(18)))
    s = cliente_http.get("/api/v1/termos/situacao", headers=auth(token)).json()
    assert {p["codigo"] for p in s["pendentes"]} == {"termos-freelancer", "politica-privacidade"}
    assert s["exige_data_nascimento"] is False  # já informada no cadastro
    assert cliente_http.get(ROTA_PROTEGIDA, headers=auth(token)).status_code == 428
    assert aceitar_tudo(cliente_http, token, "freelancer").json()["liberado"]
    assert cliente_http.get(ROTA_PROTEGIDA, headers=auth(token)).status_code == 200
    db = SessionLocal()
    u = db.query(models.Usuario).filter(models.Usuario.email == "f3@teste.dev").first()
    assert u.data_nascimento.isoformat() == _nascimento(18)
    db.close()


def test_freelancer_existente_sem_data_de_nascimento(cliente_http, publicados):
    db = SessionLocal()
    u = models.Usuario(nome="Antigo", email="f4@teste.dev", tipo="barbeiro", senha_hash="x", perfil_aprovado=True)
    db.add(u)
    db.commit()
    token = create_access_token({"sub": str(u.id)})
    db.close()

    s = cliente_http.get("/api/v1/termos/situacao", headers=auth(token)).json()
    assert s["exige_data_nascimento"] is True and not s["liberado"]
    assert aceitar_tudo(cliente_http, token, "freelancer").status_code == 400  # sem data
    r = aceitar_tudo(cliente_http, token, "freelancer", data_nascimento=_nascimento(17))
    assert r.status_code == 403
    db = SessionLocal()
    assert db.get(models.Usuario, u.id).data_nascimento is None  # data de menor não fica gravada
    assert db.query(models.AceiteDocumento).count() == 0
    db.close()
    assert cliente_http.get(ROTA_PROTEGIDA, headers=auth(token)).status_code == 428

    assert aceitar_tudo(cliente_http, token, "freelancer", data_nascimento=_nascimento(30)).json()["liberado"]
    assert cliente_http.get(ROTA_PROTEGIDA, headers=auth(token)).status_code == 200


def test_completar_cadastro_freelancer_exige_maioridade(cliente_http):
    db = SessionLocal()
    u = models.Usuario(nome="x", email="f5@teste.dev", tipo="barbeiro", senha_hash="x", cadastro_pendente=True)
    db.add(u)
    db.commit()
    token = create_access_token({"sub": str(u.id)})
    db.close()
    corpo = {"nome": "Fulano", "tempo_experiencia": "2 anos"}
    assert cliente_http.post("/api/v1/cadastro/completar", headers=auth(token), json=corpo).status_code == 400
    r = cliente_http.post("/api/v1/cadastro/completar", headers=auth(token),
                          json={**corpo, "data_nascimento": _nascimento(15)})
    assert r.status_code == 403


# ------------------------------------------------------------------ proprietário

def test_proprietario_cadastro_e_aceite(cliente_http, publicados):
    token = token_de(cadastrar(cliente_http, "barbearia", "d1@teste.dev"))
    s = cliente_http.get("/api/v1/termos/situacao", headers=auth(token)).json()
    assert {p["codigo"] for p in s["pendentes"]} == {"termos-proprietario", "politica-privacidade"}
    # leitura dos próprios dados continua liberada; o resto não
    assert cliente_http.get("/api/v1/barbearia/minha", headers=auth(token)).status_code != 428
    assert cliente_http.put("/api/v1/barbearia/condicoes-estrutura", headers=auth(token),
                            json={"secador_disponivel": True}).status_code == 428
    assert aceitar_tudo(cliente_http, token, "proprietario").json()["liberado"]
    assert cliente_http.put("/api/v1/barbearia/condicoes-estrutura", headers=auth(token),
                            json={"secador_disponivel": True}).status_code == 200


# ------------------------------------------------------------------ recusa

def test_recusa_mantem_bloqueio_sem_apagar_conta(cliente_http, publicados):
    token = token_de(cadastrar(cliente_http, "cliente", "r1@teste.dev"))
    s = cliente_http.post("/api/v1/termos/recusar", headers=auth(token)).json()
    assert s["recusou"] is True and not s["liberado"]
    assert cliente_http.get(ROTA_PROTEGIDA, headers=auth(token)).status_code == 428
    # continua podendo ler os documentos e a situação
    assert cliente_http.get("/api/v1/termos/documentos/termos-cliente").status_code == 200
    assert cliente_http.get("/api/v1/termos/situacao", headers=auth(token)).status_code == 200
    db = SessionLocal()
    assert db.query(models.Usuario).filter(models.Usuario.email == "r1@teste.dev").count() == 1
    assert {a.decisao for a in db.query(models.AceiteDocumento).all()} == {"recusado"}
    db.close()
    # muda de ideia e aceita
    assert aceitar_tudo(cliente_http, token, "cliente").json()["liberado"]


# ------------------------------------------------------------------ versões

def test_nova_versao_exige_novo_aceite(cliente_http, monkeypatch, publicados):
    token = token_de(cadastrar(cliente_http, "cliente", "v1@teste.dev"))
    assert aceitar_tudo(cliente_http, token, "cliente").json()["liberado"]
    assert cliente_http.get(ROTA_PROTEGIDA, headers=auth(token)).status_code == 200

    v1 = docs.buscar("termos-cliente", "1.0")
    # 1.1 sem exigir novo aceite: continua liberado
    _publicar(monkeypatch, docs.VERSOES + [replace(v1, versao="1.1", exige_novo_aceite=False)])
    assert cliente_http.get(ROTA_PROTEGIDA, headers=auth(token)).status_code == 200

    # 2.0 exige novo aceite: bloqueia até aceitar a 2.0
    _publicar(monkeypatch, docs.VERSOES + [replace(v1, versao="2.0")])
    s = cliente_http.get("/api/v1/termos/situacao", headers=auth(token)).json()
    assert [(p["codigo"], p["versao"]) for p in s["pendentes"]] == [("termos-cliente", "2.0")]
    assert cliente_http.get(ROTA_PROTEGIDA, headers=auth(token)).status_code == 428
    assert aceitar_tudo(cliente_http, token, "cliente").json()["liberado"]
    hist = cliente_http.get("/api/v1/termos/historico", headers=auth(token)).json()["decisoes"]
    vigentes = {(h["documento_codigo"], h["versao"]) for h in hist if h["vigente"]}
    assert vigentes == {("termos-cliente", "2.0"), ("politica-privacidade", "1.0")}

    # versão com vigência futura ainda não vale
    _publicar(monkeypatch, docs.VERSOES + [replace(v1, versao="3.0", vigente_desde=date.today() + timedelta(days=5))])
    assert cliente_http.get(ROTA_PROTEGIDA, headers=auth(token)).status_code == 200


# ------------------------------------------------------------------ contornos

def test_contornos_pela_api(cliente_http, publicados):
    token = token_de(cadastrar(cliente_http, "cliente", "x1@teste.dev"))
    # token adulterado / ausente: a rota decide (401), não o middleware
    assert cliente_http.get(ROTA_PROTEGIDA, headers=auth(token + "x")).status_code == 401
    # a resposta 428 inclui CORS para o app Capacitor
    r = cliente_http.get(ROTA_PROTEGIDA, headers={**auth(token), "Origin": "capacitor://localhost"})
    assert r.status_code == 428 and r.headers.get("access-control-allow-origin") == "capacitor://localhost"
    # aceitar documento de outro perfil não libera o próprio
    lista = cliente_http.get("/api/v1/termos/documentos", params={"perfil": "freelancer"}).json()["documentos"]
    outro = [{"codigo": d["codigo"], "versao": d["versao"], "confirmado": True} for d in lista]
    assert cliente_http.post("/api/v1/termos/aceitar", headers=auth(token), json={"aceites": outro}).status_code == 400
    assert cliente_http.get(ROTA_PROTEGIDA, headers=auth(token)).status_code == 428


def test_admin_nao_e_bloqueado(cliente_http, publicados):
    db = SessionLocal()
    u = models.Usuario(nome="Adm", email="adm@teste.dev", tipo="admin", senha_hash="x")
    db.add(u)
    db.commit()
    token = create_access_token({"sub": str(u.id)})
    db.close()
    assert cliente_http.get(ROTA_PROTEGIDA, headers=auth(token)).status_code == 200


# ------------------------------------------------------------------ estrutura da barbearia

def test_estrutura_da_barbearia(cliente_http):
    dono = token_de(cadastrar(cliente_http, "barbearia", "d2@teste.dev"))
    freela = token_de(cadastrar(cliente_http, "barbeiro", "f6@teste.dev", data_nascimento=_nascimento(25)))
    cliente = token_de(cadastrar(cliente_http, "cliente", "c9@teste.dev"))
    db = SessionLocal()
    barbearia_id = db.query(models.Barbearia).first().id
    db.close()
    url = ROTA_PROTEGIDA_2.format(id=barbearia_id)

    inicial = cliente_http.get(url, headers=auth(freela)).json()
    assert inicial["secador_disponivel"] is None  # nada vem marcado sem o dono confirmar
    assert inicial["observacoes"] is None

    r = cliente_http.put("/api/v1/barbearia/condicoes-estrutura", headers=auth(dono), json={
        "secador_disponivel": False, "cadeira_disponivel": True, "espelho_disponivel": True,
        "outros_recursos": "  Lavatório  ", "observacoes": "Estacionamento na rua"})
    assert r.status_code == 200
    visto = cliente_http.get(url, headers=auth(freela)).json()
    assert visto["secador_disponivel"] is False and visto["cadeira_disponivel"] is True
    assert visto["bancada_disponivel"] is None
    assert visto["outros_recursos"] == "Lavatório" and visto["observacoes"] == "Estacionamento na rua"

    # atualização e limpeza do texto
    cliente_http.put("/api/v1/barbearia/condicoes-estrutura", headers=auth(dono),
                     json={"secador_disponivel": True, "observacoes": ""})
    visto = cliente_http.get(url, headers=auth(freela)).json()
    assert visto["secador_disponivel"] is True and visto["observacoes"] is None
    assert visto["outros_recursos"] == "Lavatório"  # campo não enviado fica como estava

    assert cliente_http.put("/api/v1/barbearia/condicoes-estrutura", headers=auth(dono),
                            json={"observacoes": "x" * 1001}).status_code == 400
    assert cliente_http.get(url, headers=auth(cliente)).status_code == 403
    assert cliente_http.put("/api/v1/barbearia/condicoes-estrutura", headers=auth(freela),
                            json={"secador_disponivel": True}).status_code == 403


# ------------------------------------------------------------------ financeiro intacto

def test_regras_financeiras_preservadas():
    from app.routes import calcular_split_pagamento
    from app.routes_assinaturas import calcular_precos_por_posicao

    split = calcular_split_pagamento(100.0)
    assert (split["comissao_plataforma"], split["valor_freelancer"], split["valor_dono"]) == (10.0, 40.0, 50.0)
    assert calcular_precos_por_posicao(0, 6) == [47.9, 37.9, 30.9, 23.9, 19.9, 17.9]
    assert calcular_precos_por_posicao(5, 2) == [17.9, 17.9]
