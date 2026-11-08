# --- ARQUIVO: app/sessoes.py ---
# Sessão com token de acesso curto + refresh token com rotação.
#
# - Token de acesso (JWT): 60 min (ACCESS_TOKEN_EXPIRE_MINUTES) para clientes que enviam
#   o cabeçalho `X-Suporta-Refresh: 1`. Quem não envia (front antigo ainda em cache)
#   continua recebendo o token longo de antes (ACCESS_TOKEN_EXPIRE_DAYS), sem refresh.
# - Refresh token: valor aleatório opaco (não é JWT), guardado no banco só como SHA-256.
#   Cada uso troca por um novo (rotação). Usar de novo um token já trocado = vazamento:
#   a família inteira (aquele login) é revogada e o usuário precisa entrar de novo.

import hashlib
import os
import secrets
import uuid
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from pydantic import BaseModel
from sqlalchemy.orm import Session

from . import models
from .database import get_db
from .limite_requisicoes import ip_do_cliente, registrar_tentativa
from .seguranca import SECRET_KEY

ALGORITHM = os.getenv("ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_DAYS = int(os.getenv("ACCESS_TOKEN_EXPIRE_DAYS", "7"))
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60"))
REFRESH_TOKEN_EXPIRE_DAYS = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "30"))
CABECALHO_SUPORTA_REFRESH = "x-suporta-refresh"

router = APIRouter(prefix="/api/v1/auth", tags=["Sessão"])
_oauth2 = OAuth2PasswordBearer(tokenUrl="/api/v1/login/cliente/")


def _agora() -> datetime:
    return datetime.utcnow()


def _hash(valor: str) -> str:
    return hashlib.sha256(valor.encode()).hexdigest()


def gerar_access_token(usuario: models.Usuario, curto: bool) -> str:
    agora = _agora()
    validade = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES) if curto else timedelta(days=ACCESS_TOKEN_EXPIRE_DAYS)
    # `iat` marca tokens emitidos por esta versão (os antigos não têm): ver /auth/sessao.
    return jwt.encode(
        {"sub": str(usuario.id), "tipo": usuario.tipo, "iat": agora, "exp": agora + validade},
        SECRET_KEY,
        algorithm=ALGORITHM,
    )


def _novo_refresh(db: Session, usuario_id: int, familia: str) -> str:
    valor = secrets.token_urlsafe(48)
    db.add(models.RefreshToken(
        usuario_id=usuario_id,
        token_hash=_hash(valor),
        familia=familia,
        criado_em=_agora(),
        expira_em=_agora() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS),
    ))
    return valor


def cliente_suporta_refresh(request: Request | None) -> bool:
    return bool(request is not None and request.headers.get(CABECALHO_SUPORTA_REFRESH) == "1")


def emitir_sessao(db: Session, usuario: models.Usuario, request: Request | None) -> dict:
    """Tokens de um login/cadastro novo. Faz commit do refresh token quando houver."""
    if not cliente_suporta_refresh(request):
        return {"access_token": gerar_access_token(usuario, curto=False)}
    refresh = _novo_refresh(db, usuario.id, str(uuid.uuid4()))
    db.commit()
    return {
        "access_token": gerar_access_token(usuario, curto=True),
        "refresh_token": refresh,
        "expires_in": ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    }


def revogar_sessoes_do_usuario(db: Session, usuario_id: int) -> None:
    db.query(models.RefreshToken).filter(
        models.RefreshToken.usuario_id == usuario_id,
        models.RefreshToken.revogado_em.is_(None),
    ).update({models.RefreshToken.revogado_em: _agora()}, synchronize_session=False)


def _usuario_ativo(db: Session, usuario_id: int) -> models.Usuario | None:
    usuario = db.query(models.Usuario).filter(models.Usuario.id == usuario_id).first()
    if usuario is None or getattr(usuario, "excluido_em", None) is not None:
        return None
    return usuario


class RefreshRequest(BaseModel):
    refresh_token: str


_SESSAO_EXPIRADA = HTTPException(status_code=401, detail="Sessão expirada. Entre novamente.")


@router.post("/refresh")
def renovar_sessao(dados: RefreshRequest, request: Request, db: Session = Depends(get_db)):
    """Troca um refresh token válido por um par novo (o antigo deixa de valer)."""
    registrar_tentativa(f"refresh:ip:{ip_do_cliente(request)}", 120, 5 * 60)
    registro = db.query(models.RefreshToken).filter(
        models.RefreshToken.token_hash == _hash(dados.refresh_token or "")
    ).first()
    if registro is None:
        raise _SESSAO_EXPIRADA

    if registro.revogado_em is not None or registro.expira_em < _agora():
        raise _SESSAO_EXPIRADA

    if registro.usado_em is not None:
        # Reuso: alguém tem uma cópia do token. Derruba aquele login inteiro.
        db.query(models.RefreshToken).filter(
            models.RefreshToken.familia == registro.familia,
            models.RefreshToken.revogado_em.is_(None),
        ).update({models.RefreshToken.revogado_em: _agora()}, synchronize_session=False)
        db.commit()
        raise _SESSAO_EXPIRADA

    usuario = _usuario_ativo(db, registro.usuario_id)
    if usuario is None:
        raise _SESSAO_EXPIRADA

    registro.usado_em = _agora()
    novo = _novo_refresh(db, usuario.id, registro.familia)
    db.commit()
    return {
        "access_token": gerar_access_token(usuario, curto=True),
        "refresh_token": novo,
        "token_type": "bearer",
        "expires_in": ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    }


@router.post("/sessao")
def migrar_sessao_antiga(request: Request, token: str = Depends(_oauth2), db: Session = Depends(get_db)):
    """Transição: quem já estava logado (token de 7 dias, sem refresh) ganha um refresh token
    sem precisar entrar de novo. Só vale para tokens emitidos antes desta versão (sem `iat`);
    some sozinho quando o último deles vencer.
    """
    registrar_tentativa(f"sessao:ip:{ip_do_cliente(request)}", 30, 5 * 60)
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        usuario_id = int(payload.get("sub"))
    except (JWTError, ValueError, TypeError):
        raise _SESSAO_EXPIRADA
    if "iat" in payload:
        raise HTTPException(status_code=400, detail="Sessão já está no formato novo.")
    usuario = _usuario_ativo(db, usuario_id)
    if usuario is None:
        raise _SESSAO_EXPIRADA
    refresh = _novo_refresh(db, usuario.id, str(uuid.uuid4()))
    db.commit()
    return {
        "access_token": gerar_access_token(usuario, curto=True),
        "refresh_token": refresh,
        "token_type": "bearer",
        "expires_in": ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    }


@router.post("/logout")
def encerrar_sessao(dados: RefreshRequest, db: Session = Depends(get_db)):
    """Revoga o login deste aparelho (a família do refresh token). Sempre 200."""
    registro = db.query(models.RefreshToken).filter(
        models.RefreshToken.token_hash == _hash(dados.refresh_token or "")
    ).first()
    if registro is not None:
        db.query(models.RefreshToken).filter(
            models.RefreshToken.familia == registro.familia,
            models.RefreshToken.revogado_em.is_(None),
        ).update({models.RefreshToken.revogado_em: _agora()}, synchronize_session=False)
        db.commit()
    return {"ok": True}
