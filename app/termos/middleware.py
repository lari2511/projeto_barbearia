"""
Bloqueio da API para quem não tem aceite vigente dos documentos do seu perfil.

Fica no nível ASGI para valer em todas as rotas, inclusive as que decodificam o token por
conta própria (não depende de cada rota usar get_current_user). Só age em requisições com
Bearer válido de usuário não-admin; sem token, token inválido ou rota liberada, segue normal
(a rota decide o 401). Resposta: 428 com codigo TERMOS_PENDENTES (403 já significa
"bloqueio financeiro" no app).
"""

import logging
import time
from typing import Optional

from starlette.concurrency import run_in_threadpool
from starlette.responses import JSONResponse

logger = logging.getLogger(__name__)

CODIGO_BLOQUEIO = "TERMOS_PENDENTES"

# Rotas que continuam acessíveis sem aceite: ler/aceitar/recusar os documentos, ver os
# próprios dados, push e diagnósticos. Sair da conta é só no app (não há rota de logout).
PREFIXOS_LIBERADOS = (
    "/api/v1/termos",  # inclui /api/v1/termos-de-uso (texto legado)
    "/api/v1/politica-privacidade",
    "/api/v1/firebase/",
    "/api/v1/notificacoes/frontend-",
)
LEITURAS_LIBERADAS = (
    "/api/v1/usuarios/me",
    "/api/v1/usuarios/perfil-completo",
    "/api/v1/barbearia/minha",
)

# Usuários liberados ficam em cache por pouco tempo para não consultar o banco a cada request.
# Novo aceite limpa o cache do usuário; nova versão publicada chega com o deploy (processo novo).
CACHE_LIBERADOS_SEGUNDOS = 60
_liberados: dict = {}


def esquecer_usuario(usuario_id: int) -> None:
    _liberados.pop(usuario_id, None)


def _rota_liberada(metodo: str, caminho: str) -> bool:
    if caminho.startswith(PREFIXOS_LIBERADOS):
        return True
    return metodo == "GET" and caminho.rstrip("/") in LEITURAS_LIBERADAS


def _usuario_do_token(headers) -> Optional[int]:
    from jose import JWTError, jwt

    from app.routes import ALGORITHM, SECRET_KEY

    autorizacao = ""
    for nome, valor in headers:
        if nome == b"authorization":
            autorizacao = valor.decode("latin-1")
            break
    if not autorizacao.lower().startswith("bearer "):
        return None
    try:
        payload = jwt.decode(autorizacao[7:].strip(), SECRET_KEY, algorithms=[ALGORITHM])
        return int(payload.get("sub"))
    except (JWTError, TypeError, ValueError):
        return None


def _situacao_bloqueio(usuario_id: int) -> Optional[dict]:
    from app import models
    from app.database import SessionLocal
    from app.termos import regras

    db = SessionLocal()
    try:
        usuario = db.query(models.Usuario).filter(models.Usuario.id == usuario_id).first()
        if not usuario:
            return None
        situacao = regras.situacao(db, usuario)
        return None if situacao["liberado"] else situacao
    finally:
        db.close()


class ExigirAceiteTermosMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http" or scope["method"] == "OPTIONS" or _rota_liberada(scope["method"], scope["path"]):
            await self.app(scope, receive, send)
            return

        usuario_id = _usuario_do_token(scope.get("headers") or [])
        if usuario_id is None or _liberados.get(usuario_id, 0) > time.monotonic():
            await self.app(scope, receive, send)
            return

        try:
            bloqueio = await run_in_threadpool(_situacao_bloqueio, usuario_id)
        except Exception:
            # Falha ao consultar não pode derrubar o app inteiro: registra e deixa a rota responder.
            logger.exception("[termos] falha ao verificar aceite do usuario %s", usuario_id)
            await self.app(scope, receive, send)
            return

        if bloqueio is None:
            _liberados[usuario_id] = time.monotonic() + CACHE_LIBERADOS_SEGUNDOS
            await self.app(scope, receive, send)
            return

        resposta = JSONResponse(
            status_code=428,
            content={
                "detail": "Aceite os Termos de Uso e a Política de Privacidade para continuar.",
                "codigo": CODIGO_BLOQUEIO,
                "situacao": bloqueio,
            },
        )
        await resposta(scope, receive, send)
