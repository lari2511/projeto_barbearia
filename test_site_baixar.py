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


PAGINAS_INTERNAS = ["freelancer", "proprietario", "financeiro", "perguntas"]


def test_paginas_institucionais_abrem_sem_login():
    for pagina in PAGINAS_INTERNAS:
        resposta = client.get(f"/baixar/{pagina}")
        assert resposta.status_code == 200, pagina
        assert resposta.headers["content-type"].startswith("text/html")
        assert 'href="/baixar/site.css"' in resposta.text


def test_estilo_compartilhado_e_lista_fechada():
    assert client.get("/baixar/site.css").headers["content-type"].startswith("text/css")
    assert client.get("/baixar/inexistente").status_code == 404
    assert client.get("/baixar/..%2Fmain.py").status_code == 404


def test_links_internos_do_site_existem():
    import re

    for caminho in ["/baixar"] + [f"/baixar/{p}" for p in PAGINAS_INTERNAS]:
        html = client.get(caminho).text
        ids_por_pagina = {}
        for href in set(re.findall(r'href="(/baixar[^"]*)"', html)):
            alvo, _, ancora = href.partition("#")
            alvo = alvo or caminho
            resposta = client.get(alvo)
            assert resposta.status_code == 200, f"{caminho} -> {href}"
            if ancora:
                ids = ids_por_pagina.setdefault(alvo, set(re.findall(r'id="([^"]+)"', resposta.text)))
                assert ancora in ids, f"{caminho} -> {href} (âncora)"
