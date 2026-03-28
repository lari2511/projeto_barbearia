"""
Email simples com FastAPI-Mail
Sem templates, sem complexidade
"""
import os
from fastapi_mail import FastMail, MessageSchema, ConnectionConfig, MessageType
from dotenv import load_dotenv

load_dotenv()

# Configuração SMTP
conf = ConnectionConfig(
    MAIL_USERNAME=os.getenv("MAIL_USERNAME"),
    MAIL_PASSWORD=os.getenv("MAIL_PASSWORD"),
    MAIL_FROM=os.getenv("MAIL_FROM"),
    MAIL_FROM_NAME=os.getenv("MAIL_FROM_NAME", "BarberMove"),
    MAIL_PORT=int(os.getenv("MAIL_PORT", 587)),
    MAIL_SERVER=os.getenv("MAIL_SERVER"),
    MAIL_STARTTLS=os.getenv("MAIL_STARTTLS", "True") == "True",
    MAIL_SSL_TLS=os.getenv("MAIL_SSL_TLS", "False") == "True",
    USE_CREDENTIALS=True,
    VALIDATE_CERTS=True
)

fm = FastMail(conf)


async def enviar_verificacao(email: str, token: str):
    """Envia email de verificação simples"""
    link = f"http://localhost:8000/api/v1/email/verificar?token={token}"
    
    html = f"""
    <html>
        <body style="font-family: Arial; padding: 20px;">
            <h2>Bem-vindo ao BarberMove!</h2>
            <p>Clique no link abaixo para confirmar seu email:</p>
            <p><a href="{link}" style="background-color: #007bff; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px; display: inline-block;">
                Confirmar Email
            </a></p>
            <p>Ou copie: {link}</p>
            <p style="color: #999; font-size: 12px;">Link expira em 24 horas</p>
        </body>
    </html>
    """
    
    message = MessageSchema(
        subject="BarberMove - Confirme seu cadastro",
        recipients=[email],
        body=html,
        subtype=MessageType.html
    )
    
    await fm.send_message(message)
    print(f"✅ Email enviado para {email}")
