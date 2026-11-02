"""
Contagem de cadeiras por barbearia: cada estabelecimento vê só as próprias, e cadastro,
pagamento e bloqueio são contados de forma independente.

SQLite temporário, sem chamadas externas.

    .venv/Scripts/python -m pytest test_contagem_cadeiras.py -v
"""

import os
import tempfile
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta

_DB = os.path.join(tempfile.mkdtemp(prefix="bm_contagem_"), "teste.db")
os.environ["DATABASE_URL"] = f"sqlite:///{_DB}"

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app import models  # noqa: E402
from app.database import Base, SessionLocal, engine, init_db  # noqa: E402
from app.main import app  # noqa: E402
from app.routes import create_access_token  # noqa: E402
from app.routes_assinaturas import aplicar_contratacao_cadeiras  # noqa: E402

RESUMO = "/api/v1/cadeiras/resumo"
BLOQUEADA = models.StatusCadeira.BLOQUEADA
DISPONIVEL = models.StatusCadeira.DISPONIVEL


@pytest.fixture()
def http():
    Base.metadata.drop_all(bind=engine)
    init_db()
    return TestClient(app)


def _loja(email, status_cadeiras=(), pagas=0, status_assinatura="ativa"):
    db = SessionLocal()
    try:
        dono = models.Usuario(nome=email, email=email, senha_hash="x", tipo="barbearia", perfil_aprovado=True)
        db.add(dono)
        db.flush()
        loja = models.Barbearia(usuario_id=dono.id, nome=f"Loja {email}", endereco="Rua A")
        db.add(loja)
        db.flush()
        for numero, status in enumerate(status_cadeiras, start=1):
            db.add(models.Cadeira(barbearia_id=loja.id, numero=numero, status=status))
        if pagas:
            db.add(models.AssinaturaBarbearia(
                barbearia_id=loja.id, quantidade_cadeiras=pagas, valor_mensalidade=50.0, dia_vencimento=10,
                proximo_vencimento=datetime.now() + timedelta(days=30), status=status_assinatura,
            ))
        db.commit()
        token = create_access_token({"sub": str(dono.id), "tipo": "barbearia"})
        return {"id": loja.id, "dono_id": dono.id, "headers": {"Authorization": f"Bearer {token}"}}
    finally:
        db.close()


def _resumo(http, loja):
    r = http.get(RESUMO, headers=loja["headers"])
    assert r.status_code == 200, r.text
    return r.json()


def _contar(dados):
    return dados["cadastradas"], dados["pagas"], dados["desbloqueadas"], dados["bloqueadas"]


def test_cinco_cadeiras_retorna_cinco_e_zero_retorna_zero(http):  # itens 1 e 2
    cinco = _loja("a@t.com", [DISPONIVEL] * 5, pagas=5)
    zero = _loja("b@t.com")
    assert _contar(_resumo(http, cinco)) == (5, 5, 5, 0)
    assert _contar(_resumo(http, zero)) == (0, 0, 0, 0)
    assert _resumo(http, zero)["barbearia_id"] == zero["id"]
    assert len(http.get(f"/api/v1/cadeiras/barbearia/{cinco['id']}").json()) == 5
    assert http.get(f"/api/v1/cadeiras/barbearia/{zero['id']}").json() == []


def test_id_de_usuario_diferente_do_id_da_barbearia_nao_mistura(http):  # item 3
    # A barbearia nº N não é o usuário nº N: um usuário extra desalinha os dois ids.
    db = SessionLocal()
    db.add(models.Usuario(nome="x", email="x@t.com", senha_hash="x", tipo="cliente"))
    db.commit()
    db.close()
    a = _loja("a@t.com", [DISPONIVEL] * 5, pagas=5)
    b = _loja("b@t.com")
    assert a["id"] != a["dono_id"]
    assert b["id"] == a["dono_id"]  # o id da loja B coincide com o id do dono da A
    assert _contar(_resumo(http, b)) == (0, 0, 0, 0)
    assert _contar(_resumo(http, a)) == (5, 5, 5, 0)


def test_bloqueadas_e_pagas_nao_desbloqueadas_continuam_na_contagem(http):  # itens 5 e 6
    loja = _loja("a@t.com", [BLOQUEADA] * 3 + [DISPONIVEL] * 2, pagas=5)
    assert _contar(_resumo(http, loja)) == (5, 5, 2, 3)


def test_pagas_e_cadastradas_sao_contagens_separadas(http):
    so_paga = _loja("a@t.com", pagas=5)
    so_cadastrada = _loja("b@t.com", [DISPONIVEL] * 2)
    inadimplente = _loja("c@t.com", [DISPONIVEL], pagas=1, status_assinatura="inadimplente")
    assert _contar(_resumo(http, so_paga)) == (0, 5, 0, 0)
    assert _contar(_resumo(http, so_cadastrada)) == (2, 0, 2, 0)
    assert _contar(_resumo(http, inadimplente)) == (1, 0, 1, 0)


def test_pagamento_de_uma_barbearia_nao_conta_para_outra(http):  # item 7
    a = _loja("a@t.com", [DISPONIVEL] * 3, pagas=3)
    b = _loja("b@t.com", [DISPONIVEL])
    assert _resumo(http, a)["pagas"] == 3
    assert _resumo(http, b)["pagas"] == 0
    r = http.get(f"/api/v1/on-demand/cadeiras-acionadas/resumo", headers=b["headers"])
    assert r.json()["cadeiras_pagas"] == 0


def test_consultas_simultaneas_sao_independentes(http):  # item 8
    lojas = [(_loja(f"l{n}@t.com", [DISPONIVEL] * n), n) for n in range(6)]

    def consultar(par):
        loja, esperado = par
        return all(
            http.get(RESUMO, headers=loja["headers"]).json()["cadastradas"] == esperado
            for _ in range(5)
        )

    with ThreadPoolExecutor(max_workers=6) as executor:
        assert all(executor.map(consultar, lojas))


def test_nova_cadeira_so_atualiza_a_propria_barbearia(http):  # item 9
    a = _loja("a@t.com", [DISPONIVEL])
    b = _loja("b@t.com", [DISPONIVEL] * 2)
    assert http.post("/api/v1/cadeiras/", json={"numero": 2}, headers=a["headers"]).status_code == 200
    assert _resumo(http, a)["cadastradas"] == 2
    assert _resumo(http, b)["cadastradas"] == 2


def test_contratacao_cria_cadeiras_so_na_propria_e_alteracao_nao_afeta_outra(http):  # item 10
    a = _loja("a@t.com")
    b = _loja("b@t.com", [BLOQUEADA, DISPONIVEL], pagas=2)
    db = SessionLocal()
    try:
        loja_a = db.query(models.Barbearia).filter(models.Barbearia.id == a["id"]).first()
        aplicar_contratacao_cadeiras(db, loja_a, 5, "pix")
        db.commit()
        assert _contar(_resumo(http, a)) == (5, 5, 5, 0)
        assert _contar(_resumo(http, b)) == (2, 2, 1, 1)

        aplicar_contratacao_cadeiras(db, loja_a, 2, "pix")
        db.commit()
        assert _resumo(http, a)["pagas"] == 2
        assert _resumo(http, a)["cadastradas"] == 5  # reduzir o plano não apaga cadeira
        assert _contar(_resumo(http, b)) == (2, 2, 1, 1)
    finally:
        db.close()


def test_contratacao_nao_duplica_cadeira_ja_cadastrada(http):
    loja = _loja("a@t.com", [BLOQUEADA] * 3)
    db = SessionLocal()
    try:
        aplicar_contratacao_cadeiras(db, db.query(models.Barbearia).get(loja["id"]), 3, "pix")
        db.commit()
    finally:
        db.close()
    assert _contar(_resumo(http, loja)) == (3, 3, 0, 3)  # bloqueio preservado


def test_dono_com_duas_linhas_sempre_ve_a_mesma_barbearia(http):
    a = _loja("a@t.com", [DISPONIVEL] * 5, pagas=5)
    db = SessionLocal()
    try:
        duplicada = models.Barbearia(usuario_id=a["dono_id"], nome="Duplicada", endereco="")
        db.add(duplicada)
        db.commit()
    finally:
        db.close()
    assert _resumo(http, a)["barbearia_id"] == a["id"]
    assert http.get("/api/v1/barbearia/minha", headers=a["headers"]).json()["id"] == a["id"]
    assert http.get("/api/v1/on-demand/cadeiras-acionadas/resumo", headers=a["headers"]).json()["cadeiras_pagas"] == 5


def test_uma_barbearia_nao_le_mensalidade_nem_assinatura_de_outra(http):
    a = _loja("a@t.com", [DISPONIVEL] * 5, pagas=5)
    b = _loja("b@t.com")
    assert http.get(f"/api/v1/mensalidade/barbearia/{a['id']}", headers=b["headers"]).status_code == 403
    assert http.get(f"/api/v1/assinatura/barbearia/{a['id']}", headers=b["headers"]).status_code == 403


def test_mensalidade_informa_zero_real(http):
    zero = _loja("a@t.com")
    r = http.get(f"/api/v1/mensalidade/barbearia/{zero['id']}", headers=zero["headers"])
    assert r.status_code == 200, r.text
    assert r.json()["quantidade_cadeiras"] == 0


def test_compra_confirmada_acrescenta_a_cadeira_as_existentes(http):
    # Mesmo cenário da Nhocuné Style: 5 cadeiras cadastradas e 1 contratada.
    loja = _loja("a@t.com", [BLOQUEADA] * 5, pagas=1)
    outra = _loja("b@t.com", [DISPONIVEL] * 2, pagas=2)
    antes = http.get(f"/api/v1/cadeiras/barbearia/{loja['id']}").json()
    db = SessionLocal()
    try:
        barbearia = db.get(models.Barbearia, loja["id"])
        aplicar_contratacao_cadeiras(db, barbearia, 1, "pix")  # sem compra nova, nada muda
        db.commit()
        assert _resumo(http, loja)["cadastradas"] == 5

        aplicar_contratacao_cadeiras(db, barbearia, 2, "pix")
        db.commit()
    finally:
        db.close()
    depois = http.get(f"/api/v1/cadeiras/barbearia/{loja['id']}").json()
    assert len(depois) == 6
    assert [c["id"] for c in depois][:5] == [c["id"] for c in antes]  # as 5 anteriores preservadas
    assert all(c["status"] == BLOQUEADA for c in depois[:5])
    assert depois[5]["status"] == DISPONIVEL
    assert _resumo(http, outra)["cadastradas"] == 2


def test_barbearia_cancelada_sem_cadeiras_fica_zerada_e_pode_contratar_de_novo(http):
    # Estado da Lavras depois da correção de dados.
    loja = _loja("a@t.com", pagas=5, status_assinatura="cancelada")
    db = SessionLocal()
    try:
        assinatura = db.query(models.AssinaturaBarbearia).filter_by(barbearia_id=loja["id"]).one()
        assinatura.quantidade_cadeiras = 0
        assinatura.valor_mensalidade = 0
        db.commit()
        assert _contar(_resumo(http, loja)) == (0, 0, 0, 0)
        assert http.post("/api/v1/on-demand/cadeiras-acionadas/anunciar", json={"quantidade": 1}, headers=loja["headers"]).status_code in (400, 402)

        aplicar_contratacao_cadeiras(db, db.get(models.Barbearia, loja["id"]), 1, "pix")
        db.commit()
    finally:
        db.close()
    assert _contar(_resumo(http, loja)) == (1, 1, 1, 0)
