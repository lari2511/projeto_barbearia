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


# Configuração usando as variáveis do .env (Resend usa STARTTLS na porta 587)
conf = ConnectionConfig(
    MAIL_USERNAME=os.getenv("MAIL_USERNAME"),
    MAIL_PASSWORD=os.getenv("MAIL_PASSWORD"),
    MAIL_FROM=os.getenv("MAIL_FROM"),
    MAIL_FROM_NAME=os.getenv("MAIL_FROM_NAME", "BarberMove"),
    MAIL_PORT=int(os.getenv("MAIL_PORT", 587)),
    MAIL_SERVER=os.getenv("MAIL_SERVER"),
    MAIL_STARTTLS=env_bool("MAIL_STARTTLS", True),
    MAIL_SSL_TLS=env_bool("MAIL_SSL_TLS", False),
    USE_CREDENTIALS=env_bool("USE_CREDENTIALS", True),
    VALIDATE_CERTS=env_bool("VALIDATE_CERTS", True),
    TEMPLATE_FOLDER=Path(__file__).parent / 'templates',
)

fm = FastMail(conf)

async def send_verification_email(email_to: EmailStr, token_verification: str, user_name: str = "Usuário"):
    """Envia o e-mail de verificação com logs verbosos para debug."""
    # Link aponta direto para a API que processa a verificação
    api_url = os.getenv("API_URL", "http://localhost:8000")
    verify_link = f"{api_url}/api/v1/email/verificar?token={token_verification}"

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
        print("------------------------------------\n")
        raise


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
        return False
