"""
Chat de suporte usuário <-> ADM: fluxo dos três perfis, separação por setor, permissões,
leitura, entrega em tempo real e recusa de cadastro com conversa.

SQLite temporário, sem chamadas externas.

    .venv/Scripts/python -m pytest test_suporte_chat.py -v
"""

import os
import tempfile

_DB = os.path.join(tempfile.mkdtemp(prefix="bm_suporte_"), "teste.db")
os.environ["DATABASE_URL"] = f"sqlite:///{_DB}"

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import event  # noqa: E402

from app import models  # noqa: E402
from app.database import Base, SessionLocal, engine, init_db  # noqa: E402
from app.main import app  # noqa: E402
from app.routes import create_access_token  # noqa: E402

USUARIO = "/api/v1/suporte"
ADM = "/admin/api/suporte"


@pytest.fixture()
def http():
    Base.metadata.drop_all(bind=engine)
    init_db()
    return TestClient(app)


def _criar(tipo, email, nome=None, aprovado=True):
    db = SessionLocal()
    try:
        u = models.Usuario(nome=nome or email.split("@")[0], email=email, senha_hash="x", tipo=tipo, perfil_aprovado=aprovado)
        db.add(u)
        db.commit()
        db.refresh(u)
        token = create_access_token({"sub": str(u.id), "tipo": tipo})
        return u.id, {"Authorization": f"Bearer {token}"}
    finally:
        db.close()


@pytest.fixture()
def pessoas(http):
    return {
        "adm": _criar("admin", "adm@t.com"),
        "cliente": _criar("cliente", "cli@t.com"),
        "cliente2": _criar("cliente", "cli2@t.com"),
        "freelancer": _criar("barbeiro", "fre@t.com"),
        "freelancer2": _criar("barbeiro", "fre2@t.com"),
        "dono": _criar("barbearia", "dono@t.com"),
        "dono2": _criar("barbearia", "dono2@t.com"),
    }


def _enviar(http, headers, texto):
    r = http.post(f"{USUARIO}/mensagens", json={"mensagem": texto}, headers=headers)
    assert r.status_code == 201, r.text
    return r.json()


@pytest.mark.parametrize(
    "pessoa,setor,outros",
    [
        ("cliente", "cliente", ("barbeiro", "barbearia")),
        ("freelancer", "barbeiro", ("cliente", "barbearia")),
        ("dono", "barbearia", ("cliente", "barbeiro")),
    ],
)
def test_fluxo_completo_por_perfil(http, pessoas, pessoa, setor, outros):
    usuario_id, h = pessoas[pessoa]
    _, h_adm = pessoas["adm"]

    assert http.get(f"{USUARIO}/minha-conversa", headers=h).json() == {"chamado_id": None, "mensagens": []}

    _enviar(http, h, "Preciso de ajuda")

    # Só no setor do perfil, identificado pela autenticação.
    lista = http.get(f"{ADM}/conversas", params={"tipo": setor}, headers=h_adm).json()
    assert [c["usuario_id"] for c in lista] == [usuario_id]
    assert lista[0]["nao_lidas"] == 1 and lista[0]["ultima_mensagem"] == "Preciso de ajuda"
    for outro in outros:
        assert http.get(f"{ADM}/conversas", params={"tipo": outro}, headers=h_adm).json() == []

    resumo = http.get(f"{ADM}/resumo", headers=h_adm).json()
    assert resumo["total_nao_lidas"] == 1
    assert resumo["setores"][setor] == {"conversas": 1, "conversas_nao_lidas": 1, "mensagens_nao_lidas": 1}

    chamado_id = lista[0]["id"]
    conversa = http.get(f"{ADM}/conversas/{chamado_id}", headers=h_adm).json()
    assert conversa["tipo_perfil"] == setor and conversa["nome"]
    assert conversa["mensagens"][0]["criado_em"]

    # Ler no painel zera a contagem e o usuário vê que foi lida.
    assert http.post(f"{ADM}/conversas/{chamado_id}/marcar-lidas", headers=h_adm).json()["marcadas"] == 1
    assert http.get(f"{ADM}/resumo", headers=h_adm).json()["total_nao_lidas"] == 0
    assert http.get(f"{USUARIO}/minha-conversa", headers=h).json()["mensagens"][0]["lida"] is True

    # A resposta volta para o usuário, com contagem e aviso no sino.
    r = http.post(f"{ADM}/conversas/{chamado_id}/mensagens", json={"mensagem": "Olá!"}, headers=h_adm)
    assert r.status_code == 201
    assert http.get(f"{USUARIO}/nao-lidas", headers=h).json()["nao_lidas"] == 1
    mensagens = http.get(f"{USUARIO}/minha-conversa", headers=h).json()["mensagens"]
    assert [(m["mensagem"], m["do_adm"]) for m in mensagens] == [("Preciso de ajuda", False), ("Olá!", True)]

    sino = http.get("/api/v1/notificacoes/", params={"nao_lidas_apenas": True}, headers=h).json()
    assert [n["tipo"] for n in sino] == ["suporte_resposta"]

    http.post(f"{USUARIO}/marcar-lidas", headers=h)
    assert http.get(f"{USUARIO}/nao-lidas", headers=h).json()["nao_lidas"] == 0
    assert http.get("/api/v1/notificacoes/", params={"nao_lidas_apenas": True}, headers=h).json() == []
    assert http.get(f"{ADM}/conversas/{chamado_id}", headers=h_adm).json()["mensagens"][1]["lida"] is True


def test_nova_mensagem_continua_a_mesma_conversa(http, pessoas):
    _, h = pessoas["cliente"]
    a = http.post(f"{USUARIO}/mensagens", json={"mensagem": "um"}, headers=h)
    b = http.post(f"{USUARIO}/mensagens", json={"mensagem": "dois"}, headers=h)
    assert a.status_code == b.status_code == 201

    db = SessionLocal()
    try:
        assert db.query(models.ChamadoSuporte).count() == 1
    finally:
        db.close()
    assert [m["mensagem"] for m in http.get(f"{USUARIO}/minha-conversa", headers=h).json()["mensagens"]] == ["um", "dois"]


def test_varias_respostas_geram_um_aviso_no_sino(http, pessoas):
    _, h = pessoas["cliente"]
    _, h_adm = pessoas["adm"]
    _enviar(http, h, "oi")
    chamado_id = http.get(f"{ADM}/conversas", params={"tipo": "cliente"}, headers=h_adm).json()[0]["id"]
    for texto in ("a", "b", "c"):
        http.post(f"{ADM}/conversas/{chamado_id}/mensagens", json={"mensagem": texto}, headers=h_adm)
    assert http.get(f"{USUARIO}/nao-lidas", headers=h).json()["nao_lidas"] == 3
    assert len(http.get("/api/v1/notificacoes/", params={"nao_lidas_apenas": True}, headers=h).json()) == 1


@pytest.mark.parametrize("pessoa,outra", [("cliente", "cliente2"), ("freelancer", "freelancer2"), ("dono", "dono2")])
def test_usuario_so_ve_a_propria_conversa(http, pessoas, pessoa, outra):
    _, h_a = pessoas[pessoa]
    _, h_b = pessoas[outra]
    _, h_adm = pessoas["adm"]
    _enviar(http, h_a, "segredo de A")
    _enviar(http, h_b, "segredo de B")

    assert [m["mensagem"] for m in http.get(f"{USUARIO}/minha-conversa", headers=h_a).json()["mensagens"]] == ["segredo de A"]
    assert [m["mensagem"] for m in http.get(f"{USUARIO}/minha-conversa", headers=h_b).json()["mensagens"]] == ["segredo de B"]

    # A resposta para A não conta nem aparece para B.
    conversas = http.get(f"{ADM}/conversas", params={"tipo": {"cliente": "cliente", "freelancer": "barbeiro", "dono": "barbearia"}[pessoa]}, headers=h_adm).json()
    id_a = next(c["id"] for c in conversas if c["usuario_id"] == pessoas[pessoa][0])
    http.post(f"{ADM}/conversas/{id_a}/mensagens", json={"mensagem": "resposta para A"}, headers=h_adm)
    assert http.get(f"{USUARIO}/nao-lidas", headers=h_b).json()["nao_lidas"] == 0
    assert http.get(f"{USUARIO}/nao-lidas", headers=h_a).json()["nao_lidas"] == 1


@pytest.mark.parametrize("pessoa", ["cliente", "freelancer", "dono"])
def test_nao_adm_e_barrado_em_todas_as_rotas_do_painel(http, pessoas, pessoa):
    _, h_a = pessoas["cliente2"]
    _enviar(http, h_a, "oi")
    _, h = pessoas[pessoa]
    chamadas = [
        ("get", f"{ADM}/resumo", {}),
        ("get", f"{ADM}/conversas?tipo=cliente", {}),
        ("get", f"{ADM}/conversas/1", {}),
        ("post", f"{ADM}/conversas/1/marcar-lidas", {}),
        ("post", f"{ADM}/conversas/1/mensagens", {"json": {"mensagem": "invadindo"}}),
    ]
    for metodo, url, extra in chamadas:
        assert getattr(http, metodo)(url, headers=h, **extra).status_code == 403, url
    assert len(http.get(f"{USUARIO}/minha-conversa", headers=h_a).json()["mensagens"]) == 1


def test_sem_token_e_barrado(http):
    assert http.get(f"{USUARIO}/minha-conversa").status_code == 401
    assert http.post(f"{USUARIO}/mensagens", json={"mensagem": "x"}).status_code == 401
    assert http.get(f"{ADM}/resumo").status_code == 401


def test_perfil_vem_do_token_e_nao_do_corpo(http, pessoas):
    uid, h = pessoas["cliente"]
    _, h_adm = pessoas["adm"]
    r = http.post(f"{USUARIO}/mensagens", json={"mensagem": "oi", "tipo_perfil": "barbearia", "remetente_tipo": "admin", "usuario_id": 999}, headers=h)
    assert r.status_code == 201 and r.json()["do_adm"] is False
    assert http.get(f"{ADM}/conversas", params={"tipo": "barbearia"}, headers=h_adm).json() == []
    assert http.get(f"{ADM}/conversas", params={"tipo": "cliente"}, headers=h_adm).json()[0]["usuario_id"] == uid


def test_adm_nao_abre_conversa_como_usuario(http, pessoas):
    _, h_adm = pessoas["adm"]
    assert http.post(f"{USUARIO}/mensagens", json={"mensagem": "x"}, headers=h_adm).status_code == 403


@pytest.mark.parametrize("texto", ["", "    ", "x" * 2001])
def test_mensagem_invalida_nao_e_salva(http, pessoas, texto):
    _, h = pessoas["cliente"]
    assert http.post(f"{USUARIO}/mensagens", json={"mensagem": texto}, headers=h).status_code == 422
    assert http.get(f"{USUARIO}/minha-conversa", headers=h).json()["mensagens"] == []


def test_setor_invalido_e_conversa_inexistente(http, pessoas):
    _, h_adm = pessoas["adm"]
    assert http.get(f"{ADM}/conversas", params={"tipo": "admin"}, headers=h_adm).status_code == 422
    assert http.get(f"{ADM}/conversas/999", headers=h_adm).status_code == 404
    assert http.post(f"{ADM}/conversas/999/mensagens", json={"mensagem": "x"}, headers=h_adm).status_code == 404


def _autenticar(ws, headers):
    ws.send_json({"tipo": "auth", "token": headers["Authorization"].split(" ")[1]})
    # O ping só é respondido depois que o servidor processou a autenticação acima.
    ws.send_text("ping")
    assert ws.receive_text() == "pong"


def test_aviso_em_tempo_real_so_para_o_destinatario(pessoas):
    _, h_cliente = pessoas["cliente"]
    _, h_outro = pessoas["cliente2"]
    _, h_adm = pessoas["adm"]

    with TestClient(app) as http:
        with http.websocket_connect("/ws/notificacoes") as anonimo, \
                http.websocket_connect("/ws/notificacoes") as ws_outro, \
                http.websocket_connect("/ws/notificacoes") as ws_cliente, \
                http.websocket_connect("/ws/notificacoes") as ws_adm:
            _autenticar(ws_outro, h_outro)
            _autenticar(ws_cliente, h_cliente)
            _autenticar(ws_adm, h_adm)

            enviada = _enviar(http, h_cliente, "conteudo privado")
            aviso_adm = ws_adm.receive_json()
            assert aviso_adm["type"] == "suporte_mensagem" and aviso_adm["mensagem_id"] == enviada["id"]
            assert "conteudo privado" not in str(aviso_adm)

            chamado_id = aviso_adm["chamado_suporte_id"]
            resposta = http.post(f"{ADM}/conversas/{chamado_id}/mensagens", json={"mensagem": "ok"}, headers=h_adm).json()
            assert ws_cliente.receive_json()["mensagem_id"] == resposta["id"]

            # Nada chegou aos demais: o próximo quadro de cada um é o pong do ping enviado agora.
            for ws in (anonimo, ws_outro):
                ws.send_text("ping")
                assert ws.receive_text() == "pong"


@pytest.fixture()
def chaves_estrangeiras():
    # Como no Postgres de produção; o SQLite não confere FK por padrão. Só aqui, pois atrapalharia o drop_all.
    def ligar(conexao, _):
        conexao.execute("PRAGMA foreign_keys=ON")

    event.listen(engine, "connect", ligar)
    engine.dispose()
    yield
    event.remove(engine, "connect", ligar)
    engine.dispose()


def test_recusar_cadastro_com_conversa_apaga_tudo(http, pessoas, chaves_estrangeiras):
    uid, h = _criar("barbeiro", "pendente@t.com", aprovado=False)
    _, h_adm = pessoas["adm"]
    _enviar(http, h, "Quando sai minha análise?")
    chamado_id = http.get(f"{ADM}/conversas", params={"tipo": "barbeiro"}, headers=h_adm).json()[0]["id"]
    http.post(f"{ADM}/conversas/{chamado_id}/mensagens", json={"mensagem": "Em breve"}, headers=h_adm)

    r = http.post(f"/admin/api/rejeitar/{uid}", headers=h_adm)
    assert r.status_code == 200, r.text

    db = SessionLocal()
    try:
        assert db.query(models.Usuario).filter(models.Usuario.id == uid).first() is None
        assert db.query(models.ChamadoSuporte).count() == 0
        assert db.query(models.MensagemSuporte).count() == 0
    finally:
        db.close()


def test_painel_contem_a_area_de_atendimento(http):
    html = http.get("/admin/").text
    for trecho in ("ATENDIMENTO", "CHAMADOS DE CLIENTES", "CHAMADOS DE FREELANCERS", "CHAMADOS DE PROPRIETÁRIOS"):
        assert trecho in html
