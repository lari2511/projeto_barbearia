from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from sqlalchemy import func
from pydantic import BaseModel
from datetime import datetime, timedelta
from jose import jwt, JWTError
import os

from .database import get_db
from . import models
from .email_utils import send_email

router = APIRouter(prefix="/api/v1", tags=["senha"])

SECRET_KEY = os.getenv("SECRET_KEY", "INSEGURO_MUDE_ISSO_AGORA")
ALGORITHM = "HS256"
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:5173")


def normalize_email(value: str) -> str:
    return (value or "").strip().lower()


class SolicitarResetRequest(BaseModel):
    email: str


class ConfirmarResetRequest(BaseModel):
    token: str
    nova_senha: str


def _gerar_token_reset(email: str) -> str:
    expire = datetime.utcnow() + timedelta(hours=2)
    return jwt.encode({"sub": email, "exp": expire, "type": "password_reset"}, SECRET_KEY, algorithm=ALGORITHM)


def _verificar_token_reset(token: str) -> str | None:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        if payload.get("type") != "password_reset":
            return None
        return payload.get("sub")
    except JWTError:
        return None


@router.post("/senha/solicitar-reset")
def solicitar_reset(dados: SolicitarResetRequest, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    email = normalize_email(dados.email)
    usuario = db.query(models.Usuario).filter(func.lower(models.Usuario.email) == email).first()

    # Sempre retorna 200 para não revelar se email existe
    if not usuario:
        return {"mensagem": "Se o email existir, você receberá as instruções."}

    token = _gerar_token_reset(usuario.email)
    link = f"{FRONTEND_URL}?reset_token={token}"

    html = f"""
    <h2>Redefinir senha - BarberMove</h2>
    <p>Olá, <b>{usuario.nome}</b>!</p>
    <p>Clique no botão abaixo para criar uma nova senha:</p>
    <a href="{link}" style="background:#f97316;color:white;padding:12px 24px;border-radius:8px;text-decoration:none;font-weight:bold;">
        Redefinir Senha
    </a>
    <p>O link expira em 2 horas.</p>
    <p>Se não foi você, ignore este email.</p>
    """

    background_tasks.add_task(
        send_email,
        subject="Redefinir senha - BarberMove",
        to_email=usuario.email,
        html_body=html,
        text_body=f"Acesse: {link}"
    )

    # Mostra o token no terminal para testes sem SMTP
    print(f"\n[RESET SENHA] Token para {usuario.email}:\n{link}\n")

    return {"mensagem": "Se o email existir, você receberá as instruções."}


@router.post("/senha/confirmar-reset")
def confirmar_reset(dados: ConfirmarResetRequest, db: Session = Depends(get_db)):
    email = _verificar_token_reset(dados.token)
    if not email:
        raise HTTPException(status_code=400, detail="Token inválido ou expirado.")

    if len(dados.nova_senha) < 6:
        raise HTTPException(status_code=400, detail="A senha deve ter pelo menos 6 caracteres.")

    email_normalizado = normalize_email(email)
    usuario = db.query(models.Usuario).filter(func.lower(models.Usuario.email) == email_normalizado).first()
    if not usuario:
        raise HTTPException(status_code=404, detail="Usuário não encontrado.")

    from .routes import get_password_hash
    usuario.senha_hash = get_password_hash(dados.nova_senha)
    db.commit()

    return {"mensagem": "Senha redefinida com sucesso! Faça login com a nova senha."}
