from fastapi import APIRouter
from fastapi.responses import HTMLResponse, PlainTextResponse
import os

router = APIRouter()

@router.get("/termos-de-uso", response_class=HTMLResponse)
async def get_termos_de_uso():
    """Retorna os termos de uso em HTML"""
    try:
        with open("TERMOS_DE_USO.md", "r", encoding="utf-8") as f:
            content = f.read()
        
        # Converter markdown básico para HTML
        html_content = f"""
        <!DOCTYPE html>
        <html lang="pt-BR">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Termos de Uso - BarberMove</title>
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
                    padding: 40px;
                    border-radius: 8px;
                    box-shadow: 0 2px 10px rgba(0,0,0,0.1);
                }}
                h1 {{ color: #1a1a1a; font-size: 2em; margin-bottom: 0.5em; }}
                h2 {{ color: #2a2a2a; font-size: 1.5em; margin-top: 1.5em; border-bottom: 2px solid #f97316; padding-bottom: 0.3em; }}
                h3 {{ color: #3a3a3a; font-size: 1.2em; margin-top: 1em; }}
                ul, ol {{ padding-left: 20px; }}
                li {{ margin: 0.5em 0; }}
                strong {{ color: #f97316; }}
                .highlight {{
                    background: #fff3cd;
                    border-left: 4px solid #ffc107;
                    padding: 15px;
                    margin: 20px 0;
                }}
                .important {{
                    background: #f8d7da;
                    border-left: 4px solid #dc3545;
                    padding: 15px;
                    margin: 20px 0;
                }}
                .contact {{
                    background: #d1ecf1;
                    border-left: 4px solid #0dcaf0;
                    padding: 20px;
                    margin: 30px 0;
                    border-radius: 4px;
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <pre style="white-space: pre-wrap; font-family: inherit;">{content}</pre>
            </div>
        </body>
        </html>
        """
        return HTMLResponse(content=html_content)
    except FileNotFoundError:
        return HTMLResponse(content="<h1>Termos de uso não encontrados</h1>", status_code=404)


@router.get("/politica-privacidade", response_class=HTMLResponse)
async def get_politica_privacidade():
    """Retorna a política de privacidade em HTML"""
    try:
        with open("POLITICA_PRIVACIDADE.md", "r", encoding="utf-8") as f:
            content = f.read()
        
        html_content = f"""
        <!DOCTYPE html>
        <html lang="pt-BR">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Política de Privacidade - BarberMove</title>
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
                    padding: 40px;
                    border-radius: 8px;
                    box-shadow: 0 2px 10px rgba(0,0,0,0.1);
                }}
                h1 {{ color: #1a1a1a; font-size: 2em; margin-bottom: 0.5em; }}
                h2 {{ color: #2a2a2a; font-size: 1.5em; margin-top: 1.5em; border-bottom: 2px solid #0d6efd; padding-bottom: 0.3em; }}
                h3 {{ color: #3a3a3a; font-size: 1.2em; margin-top: 1em; }}
                ul, ol {{ padding-left: 20px; }}
                li {{ margin: 0.5em 0; }}
                strong {{ color: #0d6efd; }}
                .highlight {{
                    background: #e7f3ff;
                    border-left: 4px solid #0d6efd;
                    padding: 15px;
                    margin: 20px 0;
                }}
                .important {{
                    background: #f8d7da;
                    border-left: 4px solid #dc3545;
                    padding: 15px;
                    margin: 20px 0;
                }}
                .contact {{
                    background: #d1ecf1;
                    border-left: 4px solid #0dcaf0;
                    padding: 20px;
                    margin: 30px 0;
                    border-radius: 4px;
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <pre style="white-space: pre-wrap; font-family: inherit;">{content}</pre>
            </div>
        </body>
        </html>
        """
        return HTMLResponse(content=html_content)
    except FileNotFoundError:
        return HTMLResponse(content="<h1>Política de privacidade não encontrada</h1>", status_code=404)


@router.get("/termos-de-uso/texto", response_class=PlainTextResponse)
async def get_termos_texto():
    """Retorna os termos de uso em texto puro"""
    try:
        with open("TERMOS_DE_USO.md", "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        return PlainTextResponse(content="Termos de uso não encontrados", status_code=404)


@router.get("/politica-privacidade/texto", response_class=PlainTextResponse)
async def get_privacidade_texto():
    """Retorna a política de privacidade em texto puro"""
    try:
        with open("POLITICA_PRIVACIDADE.md", "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        return PlainTextResponse(content="Política de privacidade não encontrada", status_code=404)
