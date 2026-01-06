import os
import smtplib
import ssl
from email.message import EmailMessage
from typing import Optional

SMTP_HOST = os.getenv("SMTP_HOST")
SMTP_PORT = int(os.getenv("SMTP_PORT") or "587")
SMTP_USER = os.getenv("SMTP_USER")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")
SMTP_FROM = os.getenv("SMTP_FROM", SMTP_USER)
SMTP_USE_TLS = os.getenv("SMTP_USE_TLS", "1") == "1"


def send_email(subject: str, to_email: str, html_body: str, text_body: Optional[str] = None) -> bool:
    """Send email via configured SMTP. Returns True on success."""
    if not SMTP_HOST or not SMTP_USER or not SMTP_PASSWORD:
        print("SMTP não configurado; email não enviado.")
        return False

    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = SMTP_FROM or SMTP_USER
    message["To"] = to_email
    message.set_content(text_body or html_body, subtype="plain")
    message.add_alternative(html_body, subtype="html")

    try:
        context = ssl.create_default_context()
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
            if SMTP_USE_TLS:
                server.starttls(context=context)
            server.login(SMTP_USER, SMTP_PASSWORD)
            server.send_message(message)
        return True
    except Exception as exc:  # noqa: BLE001
        print(f"Erro ao enviar email: {exc}")
        return False
