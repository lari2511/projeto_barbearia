# --- ARQUIVO: app/email.py ---
# Módulo de envio de e-mail usando fastapi-mail

import os
from fastapi_mail import FastMail, MessageSchema, ConnectionConfig, MessageType
from pydantic import EmailStr
from dotenv import load_dotenv
from pathlib import Path
from typing import Optional

load_dotenv()


def env_bool(key: str, default: bool = False) -> bool:
    """Parseia booleanos do .env de forma robusta."""
    val = os.getenv(key)
    if val is None:
        return default
    return val.strip().lower() in {"1", "true", "t", "yes", "y", "on"}


def _first_env(*keys: str, default: str = "") -> str:
    for key in keys:
        value = os.getenv(key)
        if value:
            return value.strip()
    return default


def _looks_local_url(value: str) -> bool:
    lowered = (value or "").strip().lower()
    return any(token in lowered for token in ("localhost", "127.0.0.1", "0.0.0.0"))


def _resolve_public_api_base(default: str = "http://localhost:8000") -> str:
    api_url = _first_env("PUBLIC_API_URL", "API_URL")
    if api_url:
        return api_url.rstrip("/")

    railway_domain = _first_env("RAILWAY_PUBLIC_DOMAIN", "RAILWAY_STATIC_URL")
    if railway_domain:
        return f"https://{railway_domain.rstrip('/')}"

    return default


# Configuração usando as variáveis do .env (Resend usa STARTTLS na porta 587)
conf = ConnectionConfig(
    MAIL_USERNAME=_first_env("MAIL_USERNAME", "SMTP_USER"),
    MAIL_PASSWORD=_first_env("MAIL_PASSWORD", "SMTP_PASSWORD"),
    MAIL_FROM=_first_env("MAIL_FROM", "SMTP_FROM", "MAIL_USERNAME", "SMTP_USER"),
    MAIL_FROM_NAME=os.getenv("MAIL_FROM_NAME", "BarberMove"),
    MAIL_PORT=int(_first_env("MAIL_PORT", "SMTP_PORT", default="587")),
    MAIL_SERVER=_first_env("MAIL_SERVER", "SMTP_HOST"),
    MAIL_STARTTLS=env_bool("MAIL_STARTTLS", True),
    MAIL_SSL_TLS=env_bool("MAIL_SSL_TLS", False),
    USE_CREDENTIALS=env_bool("USE_CREDENTIALS", True),
    VALIDATE_CERTS=env_bool("VALIDATE_CERTS", True),
    TEMPLATE_FOLDER=Path(__file__).parent / 'templates',
)

fm = FastMail(conf)


def _build_verification_link(token_verification: str) -> str:
    verification_link_base = os.getenv("VERIFICATION_LINK_BASE", "").strip()
    public_api_base = _resolve_public_api_base()

    if verification_link_base and not (_looks_local_url(verification_link_base) and public_api_base != "http://localhost:8000"):
        if "{token}" in verification_link_base:
            return verification_link_base.format(token=token_verification)
        if verification_link_base.endswith("token="):
            return f"{verification_link_base}{token_verification}"
        return f"{verification_link_base.rstrip('/')}/api/v1/email/verificar?token={token_verification}"

    return f"{public_api_base.rstrip('/')}/api/v1/email/verificar?token={token_verification}"

async def send_verification_email(email_to: EmailStr, token_verification: str, user_name: str = "Usuário"):
    """Envia o e-mail de verificação com logs verbosos para debug."""
    # Link aponta direto para a API que processa a verificação.
    verify_link = _build_verification_link(token_verification)

    template_body = {
        "link": verify_link,
        "user_name": user_name,
        "app_name": "BarberMove",
        "support_email": "suporte@barbermovie.com",
    }

    message = MessageSchema(
        subject="BarberMove - Confirme seu cadastro",
        recipients=[email_to],
        template_body=template_body,
        subtype=MessageType.html,
    )

    print(f"--- [DEBUG E-MAIL] Iniciando envio para: {email_to} ---")
    print(f"--- [DEBUG E-MAIL] Link de verificação: {verify_link}")
    try:
        await fm.send_message(message, template_name="verification.html")
        print(f"--- [DEBUG E-MAIL] Sucesso! E-mail enviado para {email_to} ---")
        return True
    except Exception as e:
        print("\n--- [DEBUG E-MAIL] ERRO CRÍTICO ---")
        print(f"Não foi possível enviar o e-mail para {email_to}")
        print(f"Erro: {e}")
        print("Tentar fallback SMTP simples...")
        print("------------------------------------\n")

        try:
            from .email_utils import send_email

            html_body = (
                f"<p>Olá, {user_name}!</p>"
                f"<p>Confirme seu email para ativar a conta.</p>"
                f"<p><a href='{verify_link}'>Verificar email</a></p>"
                f"<p>Ou copie e cole no navegador: {verify_link}</p>"
            )
            text_body = (
                f"Olá, {user_name}!\n"
                "Confirme seu email para ativar a conta.\n"
                f"Link: {verify_link}\n"
            )
            return send_email(
                subject="BarberMove - Confirme seu cadastro",
                to_email=email_to,
                html_body=html_body,
                text_body=text_body,
            )
        except Exception as fallback_error:  # noqa: BLE001
            print(f"❌ Fallback SMTP simples também falhou: {fallback_error}")
            return False


async def send_welcome_email(email_to: EmailStr, user_name: str = "Usuário"):
    """
    Envia um e-mail de boas-vindas após verificação.
    
    Args:
        email_to: Email do destinatário
        user_name: Nome do usuário
    """
    template_body = {
        "user_name": user_name,
        "app_name": "BarberMove",
        "login_url": f"{os.getenv('FRONTEND_URL', 'http://localhost:5173')}/login",
    }

    message = MessageSchema(
        subject="Bem-vindo ao BarberMove!",
        recipients=[email_to],
        template_body=template_body,
        subtype=MessageType.html
    )

    try:
        print(f"📧 Enviando boas-vindas para {email_to}...")
        await fm.send_message(message, template_name="welcome.html")
        print(f"✅ Email de boas-vindas enviado para {email_to}!")
        return True
    except Exception as e:
        print(f"❌ Erro ao enviar email de boas-vindas para {email_to}: {str(e)}")
        try:
            from .email_utils import send_email

            html_body = (
                f"<p>Olá, {user_name}!</p>"
                "<p>Seu cadastro no BarberMove foi concluído.</p>"
            )
            text_body = f"Olá, {user_name}! Seu cadastro no BarberMove foi concluído."
            return send_email(
                subject="Bem-vindo ao BarberMove!",
                to_email=email_to,
                html_body=html_body,
                text_body=text_body,
            )
        except Exception:
            return False


async def send_perfil_awaiting_approval_email(email_to: EmailStr, user_name: str = "Usuário", user_type: str = "barbeiro"):
    """
    Envia email informando que o perfil está aguardando avaliação.
    
    Args:
        email_to: Email do destinatário
        user_name: Nome do usuário
        user_type: Tipo de usuário (barbeiro, barbearia)
    """
    tipo_label = "barbeiro" if user_type == "barbeiro" else "barbearia"
    
    template_body = {
        "user_name": user_name,
        "user_type": tipo_label,
        "app_name": "BarberMove",
        "support_email": "suporte@barbermovie.com",
    }

    message = MessageSchema(
        subject=f"BarberMove - Seu perfil de {tipo_label} está em avaliação",
        recipients=[email_to],
        template_body=template_body,
        subtype=MessageType.html
    )

    try:
        print(f"📧 Enviando email de avaliação pendente para {email_to}...")
        await fm.send_message(message, template_name="awaiting_approval.html")
        print(f"✅ Email de avaliação enviado para {email_to}!")
        return True
    except Exception as e:
        print(f"❌ Erro ao enviar email de avaliação para {email_to}: {str(e)}")
        try:
            from .email_utils import send_email

            html_body = (
                f"<p>Olá, {user_name}!</p>"
                f"<p>Seu perfil de {tipo_label} está em avaliação.</p>"
            )
            text_body = f"Olá, {user_name}! Seu perfil de {tipo_label} está em avaliação."
            return send_email(
                subject=f"BarberMove - Seu perfil de {tipo_label} está em avaliação",
                to_email=email_to,
                html_body=html_body,
                text_body=text_body,
            )
        except Exception:
            return False


async def send_perfil_approved_email(email_to: EmailStr, user_name: str = "Usuário", user_type: str = "barbeiro"):
    """
    Envia email confirmando aprovação do perfil.
    
    Args:
        email_to: Email do destinatário
        user_name: Nome do usuário
        user_type: Tipo de usuário (barbeiro, barbearia)
    """
    tipo_label = "barbeiro" if user_type == "barbeiro" else "barbearia"
    
    template_body = {
        "user_name": user_name,
        "user_type": tipo_label,
        "app_name": "BarberMove",
        "login_url": f"{os.getenv('FRONTEND_URL', 'http://localhost:5173')}",
        "support_email": "suporte@barbermovie.com",
    }

    message = MessageSchema(
        subject=f"🎉 BarberMove - Seu perfil de {tipo_label} foi aprovado!",
        recipients=[email_to],
        template_body=template_body,
        subtype=MessageType.html
    )

    try:
        print(f"📧 Enviando email de aprovação para {email_to}...")
        await fm.send_message(message, template_name="profile_approved.html")
        print(f"✅ Email de aprovação enviado para {email_to}!")
        return True
    except Exception as e:
        print(f"❌ Erro ao enviar email de aprovação para {email_to}: {str(e)}")
        try:
            from .email_utils import send_email

            html_body = (
                f"<p>Olá, {user_name}!</p>"
                f"<p>Seu perfil de {tipo_label} foi aprovado.</p>"
            )
            text_body = f"Olá, {user_name}! Seu perfil de {tipo_label} foi aprovado."
            return send_email(
                subject=f"🎉 BarberMove - Seu perfil de {tipo_label} foi aprovado!",
                to_email=email_to,
                html_body=html_body,
                text_body=text_body,
            )
        except Exception:
            return False
