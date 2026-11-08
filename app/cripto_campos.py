# --- ARQUIVO: app/cripto_campos.py ---
# Criptografia em repouso de dados pessoais (CPF, CNPJ, RG, telefone, chave Pix, conta).
#
# Usa AES-256-SIV (cryptography): criptografia DETERMINÍSTICA e autenticada. O mesmo valor
# vira sempre o mesmo texto cifrado, então `filter(Usuario.cpf == x)` e o UNIQUE do CPF
# continuam funcionando sem mudar nenhuma rota. O custo: quem lê o banco percebe quando
# dois registros têm o mesmo valor (mas não qual é). Busca parcial (LIKE) não funciona —
# hoje nenhuma rota faz isso nessas colunas.
#
# Chave: variável DADOS_CRIPTO_KEY com 128 caracteres hex (64 bytes) — `openssl rand -hex 64`.
# ATENÇÃO: perder a chave = perder esses dados. Guardar cópia fora do Railway.
#
# Sem a chave, o tipo funciona como String normal (grava aberto) e avisa no log. Valores
# antigos em texto aberto continuam legíveis; `criptografar_dados_existentes` converte
# todos no startup assim que a chave existir.

import base64
import logging
import os

from cryptography.hazmat.primitives.ciphers.aead import AESSIV
from sqlalchemy import String, text
from sqlalchemy.types import TypeDecorator

logger = logging.getLogger(__name__)

PREFIXO = "enc1:"

# (tabela, coluna) cifradas — usado pela migração dos valores antigos
COLUNAS_CRIPTOGRAFADAS = [
    ("usuarios", "telefone"),
    ("usuarios", "cpf"),
    ("usuarios", "cnpj"),
    ("usuarios", "rg"),
    ("barbearias", "telefone"),
    ("contas_pagamento_usuarios", "chave_pix"),
    ("contas_pagamento_usuarios", "agencia"),
    ("contas_pagamento_usuarios", "conta"),
    ("contas_pagamento_usuarios", "titular_documento"),
    ("saques", "agencia"),
    ("saques", "conta"),
]

_cifra: AESSIV | None = None
_avisou_sem_chave = False


def _carregar_cifra() -> AESSIV | None:
    global _cifra
    if _cifra is not None:
        return _cifra
    bruto = (os.getenv("DADOS_CRIPTO_KEY") or "").strip()
    if not bruto:
        return None
    try:
        chave = bytes.fromhex(bruto)
    except ValueError:
        raise RuntimeError("DADOS_CRIPTO_KEY inválida: use 128 caracteres hex (openssl rand -hex 64).")
    if len(chave) != 64:
        raise RuntimeError("DADOS_CRIPTO_KEY precisa ter 64 bytes (128 caracteres hex).")
    _cifra = AESSIV(chave)
    return _cifra


def criptografia_ativa() -> bool:
    return _carregar_cifra() is not None


def cifrar(valor: str | None) -> str | None:
    global _avisou_sem_chave
    if valor is None or valor == "" or str(valor).startswith(PREFIXO):
        return valor
    cifra = _carregar_cifra()
    if cifra is None:
        if not _avisou_sem_chave:
            logger.warning("DADOS_CRIPTO_KEY ausente: dados pessoais estão sendo gravados SEM criptografia.")
            _avisou_sem_chave = True
        return valor
    dado = cifra.encrypt(str(valor).encode("utf-8"), None)
    return PREFIXO + base64.urlsafe_b64encode(dado).decode().rstrip("=")


def decifrar(valor: str | None) -> str | None:
    if valor is None or not str(valor).startswith(PREFIXO):
        return valor  # vazio ou valor antigo ainda em texto aberto
    cifra = _carregar_cifra()
    if cifra is None:
        logger.error("Há dados criptografados no banco mas DADOS_CRIPTO_KEY não está configurada.")
        return None
    corpo = valor[len(PREFIXO):]
    corpo += "=" * (-len(corpo) % 4)
    try:
        return cifra.decrypt(base64.urlsafe_b64decode(corpo), None).decode("utf-8")
    except Exception:
        logger.error("Falha ao decifrar um campo (chave errada ou dado corrompido).")
        return None


class CampoCriptografado(TypeDecorator):
    """String gravada cifrada no banco e devolvida aberta para o código."""
    impl = String
    cache_ok = True

    def process_bind_param(self, value, dialect):
        return cifrar(value)

    def process_result_value(self, value, dialect):
        return decifrar(value)


def criptografar_dados_existentes(engine) -> None:
    """Converte valores ainda em texto aberto. Idempotente; roda no startup."""
    if not criptografia_ativa():
        return
    from sqlalchemy import inspect

    inspetor = inspect(engine)
    tabelas = set(inspetor.get_table_names())
    total = 0
    for tabela, coluna in COLUNAS_CRIPTOGRAFADAS:
        if tabela not in tabelas or coluna not in {c["name"] for c in inspetor.get_columns(tabela)}:
            continue
        with engine.begin() as conn:
            linhas = conn.execute(
                text(f"SELECT id, {coluna} FROM {tabela} WHERE {coluna} IS NOT NULL AND {coluna} <> '' "
                     f"AND {coluna} NOT LIKE :prefixo"),
                {"prefixo": PREFIXO + "%"},
            ).all()
            for id_, valor in linhas:
                conn.execute(
                    text(f"UPDATE {tabela} SET {coluna} = :valor WHERE id = :id"),
                    {"valor": cifrar(valor), "id": id_},
                )
            total += len(linhas)
    if total:
        logger.info("[migracao] %s valor(es) de dados pessoais criptografados", total)
