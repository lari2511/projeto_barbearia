# --- ARQUIVO: app/seguranca.py ---
# Utilitários de segurança compartilhados: chave do JWT, links assinados para
# arquivos privados (documentos) e mascaramento de dados em logs.

import base64
import hashlib
import hmac
import logging
import os
import secrets
import time
from urllib.parse import quote

from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

# Valor que existia como padrão no código; nunca pode ser aceito como chave real.
_CHAVE_INSEGURA_ANTIGA = "INSEGURO_MUDE_ISSO_AGORA"


def _em_producao() -> bool:
    # Railway define estas variáveis em todo deploy.
    return bool(os.getenv("RAILWAY_ENVIRONMENT") or os.getenv("RAILWAY_ENVIRONMENT_NAME"))


def carregar_secret_key() -> str:
    """Lê SECRET_KEY do ambiente. Em produção, sem chave forte o servidor não sobe."""
    chave = (os.getenv("SECRET_KEY") or "").strip()
    if chave and chave != _CHAVE_INSEGURA_ANTIGA and len(chave) >= 32:
        return chave
    if _em_producao():
        raise RuntimeError(
            "SECRET_KEY ausente ou fraca (mínimo 32 caracteres). "
            "Gere com `openssl rand -hex 32` e configure no Railway."
        )
    # Desenvolvimento: chave aleatória por processo (tokens não sobrevivem a um restart).
    logger.warning("SECRET_KEY ausente/fraca: usando chave temporária só para desenvolvimento.")
    return chave if chave and chave != _CHAVE_INSEGURA_ANTIGA else secrets.token_hex(32)


SECRET_KEY = carregar_secret_key()


# --- Documentos (RG/CNH/selfie): servidos só por link assinado e temporário ---

PREFIXO_DOCUMENTOS = "/uploads/documentos/"
VALIDADE_LINK_DOCUMENTO_SEGUNDOS = 15 * 60


def _assinatura(nome_arquivo: str, expira_em: int) -> str:
    msg = f"documento:{nome_arquivo}:{expira_em}".encode()
    dig = hmac.new(SECRET_KEY.encode(), msg, hashlib.sha256).digest()
    return base64.urlsafe_b64encode(dig).decode().rstrip("=")


def nome_arquivo_documento(url: str | None) -> str | None:
    """Extrai o nome do arquivo de uma URL /uploads/documentos/... (relativa ou absoluta)."""
    if not url:
        return None
    pos = url.find(PREFIXO_DOCUMENTOS)
    if pos < 0:
        return None
    nome = url[pos + len(PREFIXO_DOCUMENTOS):].split("?", 1)[0]
    if not nome or "/" in nome or "\\" in nome or ".." in nome:
        return None
    return nome


def url_documento_assinada(url: str | None) -> str | None:
    """Converte a URL gravada no banco num link temporário para o ADM ver o arquivo.

    URLs que não são do diretório de documentos (ex.: data: URI antigas) voltam como estão.
    """
    nome = nome_arquivo_documento(url)
    if not nome:
        return url
    expira_em = int(time.time()) + VALIDADE_LINK_DOCUMENTO_SEGUNDOS
    return (
        f"/api/v1/documentos/arquivo/{quote(nome)}"
        f"?exp={expira_em}&sig={_assinatura(nome, expira_em)}"
    )


def assinatura_documento_valida(nome_arquivo: str, exp: int, sig: str) -> bool:
    if exp < int(time.time()):
        return False
    return hmac.compare_digest(_assinatura(nome_arquivo, exp), sig or "")


# --- Mascaramento para logs ---

def mascarar_email(email: str | None) -> str:
    if not email or "@" not in email:
        return "***"
    usuario, dominio = email.split("@", 1)
    return f"{usuario[:2]}***@{dominio}"
