"""
Páginas públicas (HTML e texto puro) dos Termos de Uso e da Política de Privacidade.

O texto vem do catálogo app/termos/documentos.py (o mesmo que o app mostra e que o usuário
aceita). Sem versão publicada, mostra o rascunho mais recente com o aviso de que está em revisão.
"""

import html

from fastapi import APIRouter
from fastapi.responses import HTMLResponse, PlainTextResponse

from app.termos import documentos as docs

router = APIRouter()

_CODIGO_TERMOS = {
    "cliente": "termos-cliente",
    "freelancer": "termos-freelancer",
    "proprietario": "termos-proprietario",
}


def _documento(codigo: str):
    return docs.versao_atual(codigo) or docs.ultima_versao(codigo)


def _codigo_termos(perfil: str) -> str:
    return _CODIGO_TERMOS.get(docs.normalizar_perfil(perfil) or "cliente", "termos-cliente")


def _pagina(documento, cor: str) -> HTMLResponse:
    if not documento:
        return HTMLResponse(content="<h1>Documento não encontrado</h1>", status_code=404)
    aviso = ""
    if documento.estado != docs.PUBLICADO:
        aviso = '<div class="aviso">RASCUNHO EM REVISÃO: este texto ainda não está publicado.</div>'
    titulo = html.escape(documento.titulo)
    conteudo = html.escape(documento.conteudo)
    return HTMLResponse(content=f"""
        <!DOCTYPE html>
        <html lang="pt-BR">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>{titulo} - BarberMove</title>
            <style>
                body {{
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
                    line-height: 1.6;
                    color: #333;
                    max-width: 800px;
                    margin: 0 auto;
                    padding: 20px;
                    background: #f5f5f5;
                }}
                .container {{
                    background: white;
                    padding: 24px;
                    border-radius: 8px;
                    box-shadow: 0 2px 10px rgba(0,0,0,0.1);
                    border-top: 4px solid {cor};
                }}
                .meta {{ color: #666; font-size: 0.9em; }}
                .aviso {{
                    background: #fff3cd;
                    border-left: 4px solid #ffc107;
                    padding: 12px;
                    margin-bottom: 16px;
                    font-weight: bold;
                }}
            </style>
        </head>
        <body>
            <div class="container">
                {aviso}
                <p class="meta">Versão {html.escape(documento.versao)} · vigente desde {documento.vigente_desde.strftime('%d/%m/%Y')}</p>
                <pre style="white-space: pre-wrap; font-family: inherit;">{conteudo}</pre>
            </div>
        </body>
        </html>
        """)


@router.get("/termos-de-uso", response_class=HTMLResponse)
async def get_termos_de_uso(perfil: str = "cliente"):
    """Termos de Uso do perfil (cliente | freelancer | proprietario) em HTML"""
    return _pagina(_documento(_codigo_termos(perfil)), "#f97316")


@router.get("/politica-privacidade", response_class=HTMLResponse)
async def get_politica_privacidade():
    """Política de Privacidade em HTML"""
    return _pagina(_documento("politica-privacidade"), "#0d6efd")


@router.get("/termos-de-uso/texto", response_class=PlainTextResponse)
async def get_termos_texto(perfil: str = "cliente"):
    """Termos de Uso em texto puro"""
    documento = _documento(_codigo_termos(perfil))
    if not documento:
        return PlainTextResponse(content="Termos de uso não encontrados", status_code=404)
    return documento.conteudo


@router.get("/politica-privacidade/texto", response_class=PlainTextResponse)
async def get_privacidade_texto():
    """Política de privacidade em texto puro"""
    documento = _documento("politica-privacidade")
    if not documento:
        return PlainTextResponse(content="Política de privacidade não encontrada", status_code=404)
    return documento.conteudo
