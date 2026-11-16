"""
GET /api/v1/barbeiro/agendamentos/meus: lista os agendamentos do freelancer logado.

Regressão: a chamada interna passava a sessão do banco no lugar do token e a rota
respondia 500 ('Session' object has no attribute 'rsplit').

    .venv/Scripts/python -m pytest test_agendamentos_meus.py -v
"""

import os
import tempfile

_DB = os.path.join(tempfile.mkdtemp(prefix="bm_ag_meus_"), "teste.db")
os.environ["DATABASE_URL"] = f"sqlite:///{_DB}"

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.database import Base, engine, init_db  # noqa: E402
from app.main import app  # noqa: E402
from test_anuncio_vagas import _usuario  # noqa: E402

URL = "/api/v1/barbeiro/agendamentos/meus"


@pytest.fixture()
def http():
    Base.metadata.drop_all(bind=engine)
    init_db()
    return TestClient(app)


def test_freelancer_lista_os_proprios_agendamentos(http):
    _, headers = _usuario("barbeiro", "free@t.com")
    r = http.get(URL, headers=headers)
    assert r.status_code == 200, r.text
    assert r.json() == []


def test_quem_nao_e_freelancer_recebe_403(http):
    _, headers = _usuario("cliente", "cli@t.com")
    assert http.get(URL, headers=headers).status_code == 403
