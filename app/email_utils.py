import os
import smtplib
import ssl
from email.message import EmailMessage
from typing import Optional

import requests

SMTP_HOST = os.getenv("SMTP_HOST") or os.getenv("MAIL_SERVER")
SMTP_PORT = int(os.getenv("SMTP_PORT") or os.getenv("MAIL_PORT") or "587")
SMTP_USER = os.getenv("SMTP_USER") or os.getenv("MAIL_USERNAME")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD") or os.getenv("MAIL_PASSWORD")
SMTP_FROM = os.getenv("SMTP_FROM") or os.getenv("MAIL_FROM") or SMTP_USER


def _env_bool(*keys: str, default: bool = False) -> bool:
    for key in keys:
        raw = os.getenv(key)
        if raw is None:
            continue
        return str(raw).strip().lower() in {"1", "true", "t", "yes", "y", "on"}
    return default


SMTP_USE_TLS = _env_bool("SMTP_USE_TLS", "MAIL_STARTTLS", default=True)
SMTP_USE_SSL = _env_bool("MAIL_SSL_TLS", default=False)
SMTP_TIMEOUT = int(os.getenv("SMTP_TIMEOUT") or os.getenv("MAIL_TIMEOUT") or "20")


def _send_via_brevo_api(to_email: str, subject: str, html_body: str, text_body: str) -> bool:
    api_key = os.getenv("BREVO_API_KEY") or os.getenv("SENDINBLUE_API_KEY")
    sender_email = os.getenv("BREVO_SENDER_EMAIL") or SMTP_FROM or SMTP_USER
    sender_name = os.getenv("BREVO_SENDER_NAME") or os.getenv("MAIL_FROM_NAME") or "BarberMove"

    if not api_key or not sender_email:
        return False

    payload = {
        "sender": {"name": sender_name, "email": sender_email},
        "to": [{"email": to_email}],
        "subject": subject,
        "htmlContent": html_body,
        "textContent": text_body,
    }

    try:
        response = requests.post(
            "https://api.brevo.com/v3/smtp/email",
            json=payload,
            headers={"api-key": api_key, "Content-Type": "application/json"},
            timeout=20,
        )
        if response.status_code in (200, 201, 202):
            print(f"✅ [BREVO API] Email enviado para {to_email}")
            return True

        print(f"❌ [BREVO API] Falha no envio para {to_email}: HTTP {response.status_code}")
        return False
    except Exception as exc:  # noqa: BLE001
        print(f"❌ [BREVO API] Excecao ao enviar para {to_email}: {type(exc).__name__}: {exc}")
        return False


def _send_via_resend_api(to_email: str, subject: str, html_body: str, text_body: str) -> bool:
    api_key = os.getenv("RESEND_API_KEY")
    from_email = os.getenv("RESEND_FROM") or SMTP_FROM or "onboarding@resend.dev"
    if not api_key:
        return False

    payload = {
        "from": from_email,
        "to": [to_email],
        "subject": subject,
        "html": html_body,
        "text": text_body,
    }

    try:
        response = requests.post(
            "https://api.resend.com/emails",
            json=payload,
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            timeout=20,
        )
        if response.status_code in (200, 201, 202):
            print(f"✅ [RESEND API] Email enviado para {to_email}")
            return True

        print(f"❌ [RESEND API] Falha no envio para {to_email}: HTTP {response.status_code}")
        return False
    except Exception as exc:  # noqa: BLE001
        print(f"❌ [RESEND API] Excecao ao enviar para {to_email}: {type(exc).__name__}: {exc}")
        return False


def send_email(subject: str, to_email: str, html_body: str, text_body: Optional[str] = None) -> bool:
    """Send email via API providers first, then fallback to SMTP."""
    text_fallback = text_body or html_body

    if _send_via_brevo_api(to_email=to_email, subject=subject, html_body=html_body, text_body=text_fallback):
        return True

    if _send_via_resend_api(to_email=to_email, subject=subject, html_body=html_body, text_body=text_fallback):
        return True

    if not SMTP_HOST or not SMTP_USER or not SMTP_PASSWORD:
        print(f"⚠️ SMTP não configurado; email NÃO enviado para {to_email}.")
        print(f"📧 Assunto: {subject}")
        print(f"📝 Corpo: {html_body[:200]}...")
        return False

    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = SMTP_FROM or SMTP_USER
    message["To"] = to_email
    message.set_content(text_fallback, subtype="plain")
    message.add_alternative(html_body, subtype="html")

    try:
        print(f"📤 Tentando enviar email para {to_email} via {SMTP_HOST}:{SMTP_PORT}...")

        if SMTP_USE_SSL:
            context = ssl.create_default_context()
            with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT, timeout=SMTP_TIMEOUT, context=context) as server:
                server.login(SMTP_USER, SMTP_PASSWORD)
                server.send_message(message)
        else:
            with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=SMTP_TIMEOUT) as server:
                if SMTP_USE_TLS:
                    context = ssl.create_default_context()
                    server.starttls(context=context)
                server.login(SMTP_USER, SMTP_PASSWORD)
                server.send_message(message)
        
        print(f"✅ Email enviado com sucesso para {to_email}!")
        return True
    except Exception as exc:  # noqa: BLE001
        print(f"❌ Erro ao enviar email para {to_email}: {type(exc).__name__}: {exc}")
        return False

