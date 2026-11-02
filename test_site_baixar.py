"""
Site público de download (/baixar): responde sem login e não ocupa a raiz, que o app abre no WebView.

    .venv/Scripts/python -m pytest test_site_baixar.py -v
"""

import os
import tempfile

_DB = os.path.join(tempfile.mkdtemp(prefix="bm_site_"), "teste.db")
os.environ["DATABASE_URL"] = f"sqlite:///{_DB}"

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402

client = TestClient(app)


def test_pagina_abre_sem_login_e_aponta_para_o_apk():
    resposta = client.get("/baixar")
    assert resposta.status_code == 200
    assert resposta.headers["content-type"].startswith("text/html")
    assert 'href="/apk/latest"' in resposta.text


def test_head_funciona_para_previa_de_link():
    assert client.head("/baixar").status_code == 200


def test_raiz_continua_sendo_o_app():
    assert "Baixar o BarberMove" not in client.get("/").text
