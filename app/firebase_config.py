"""
ARQUIVO: app/firebase_config.py
Configuração do Firebase Cloud Messaging (FCM) para notificações push
"""

import os
import json
import logging
from dotenv import load_dotenv
from datetime import datetime
from typing import Optional

load_dotenv()
logger = logging.getLogger(__name__)

def _env_bool(key: str, default: bool = False) -> bool:
    raw = os.getenv(key)
    if raw is None:
        return default
    return str(raw).strip().lower() in {"1", "true", "yes", "on"}


# Mantemos Firebase desativado por padrao para evitar ruído em ambientes
# que nao usam FCM. Para ativar, defina FIREBASE_ENABLED=1.
FIREBASE_ENABLED = _env_bool("FIREBASE_ENABLED", default=False)
FIREBASE_DISPONIVEL = False

# Caminho para o arquivo JSON de credenciais do Firebase
FIREBASE_CREDENTIALS_PATH = os.getenv("FIREBASE_CREDENTIALS_PATH", "firebase-credentials.json")
FIREBASE_CREDENTIALS_JSON = os.getenv("FIREBASE_CREDENTIALS_JSON", "").strip()
FIREBASE_STATUS_MENSAGEM = "Firebase desabilitado por configuracao (FIREBASE_ENABLED=0)"


def _resolver_credenciais_firebase():
    """Resolve credenciais por JSON inline (Railway) ou caminho de arquivo."""
    if FIREBASE_CREDENTIALS_JSON:
        payload = FIREBASE_CREDENTIALS_JSON
        try:
            # Permite JSON enviado com aspas/escapes na variavel
            payload = payload.replace("\\n", "\n")
            info = json.loads(payload)
            return credentials.Certificate(info), "FIREBASE_CREDENTIALS_JSON"
        except Exception as exc:
            raise RuntimeError(f"FIREBASE_CREDENTIALS_JSON invalido: {exc}") from exc

    if os.path.exists(FIREBASE_CREDENTIALS_PATH):
        return credentials.Certificate(FIREBASE_CREDENTIALS_PATH), "FIREBASE_CREDENTIALS_PATH"

    raise RuntimeError(
        "Credenciais ausentes. Defina FIREBASE_CREDENTIALS_JSON ou FIREBASE_CREDENTIALS_PATH"
    )

# Inicializar Firebase uma única vez (evita múltiplas inicializações)
if FIREBASE_ENABLED:
    try:
        import firebase_admin
        from firebase_admin import credentials, messaging

        if not firebase_admin._apps:
            cred, origem = _resolver_credenciais_firebase()
            firebase_admin.initialize_app(cred)
            FIREBASE_STATUS_MENSAGEM = f"Firebase inicializado com sucesso via {origem}"
        else:
            FIREBASE_STATUS_MENSAGEM = "Firebase ja inicializado"

        FIREBASE_DISPONIVEL = True
        logger.info(FIREBASE_STATUS_MENSAGEM)
    except ImportError:
        FIREBASE_DISPONIVEL = False
        FIREBASE_STATUS_MENSAGEM = "Firebase habilitado, mas firebase-admin nao esta instalado"
        logger.warning(FIREBASE_STATUS_MENSAGEM)
    except Exception as e:
        FIREBASE_DISPONIVEL = False
        FIREBASE_STATUS_MENSAGEM = f"Firebase nao inicializado: {e}"
        logger.warning(FIREBASE_STATUS_MENSAGEM)


def obter_status_firebase() -> tuple[bool, str]:
    return FIREBASE_DISPONIVEL, FIREBASE_STATUS_MENSAGEM


def _formatar_moeda(valor: float) -> str:
    """Helper simples para formatar valores em moeda brasileira"""
    return f"R$ {valor:.2f}"


def enviar_notificacao_pagamento(
    token_dispositivo: str,
    nome_cliente: str,
    valor: float,
    nome_barbeiro: str = None
) -> bool:
    """
    Enviar notificação push quando um pagamento é confirmado.
    
    Args:
        token_dispositivo: Device token do barbeiro (salvo no banco de dados)
        nome_cliente: Nome do cliente que fez o pagamento
        valor: Valor do pagamento (para mostrar no aviso)
        nome_barbeiro: Nome do barbeiro (opcional, para logs)
    
    Returns:
        True se enviado com sucesso, False caso contrário
    """
    
    if not FIREBASE_DISPONIVEL:
        print(f"Firebase não está disponível")
        return False
    
    if not token_dispositivo:
        print(f"Nenhum device token para enviar notificação")
        return False
    
    valor_formatado = _formatar_moeda(valor)
    
    try:
        mensagem = messaging.Message(
            notification=messaging.Notification(
                title="💰 Pagamento Confirmado!",
                body=f"{nome_cliente} pagou {valor_formatado}. Você pode iniciar o atendimento!"
            ),
            # Dados adicionais que o app pode processar
            data={
                "tipo": "pagamento_confirmado",
                "cliente_nome": nome_cliente,
                "valor": str(valor),
                "timestamp": datetime.utcnow().isoformat()
            },
            token=token_dispositivo,
        )
        
        resposta = messaging.send(mensagem)
        print(f"Notificação enviada: {resposta}")
        return True
    except Exception as e:
        print(f"Falha ao enviar notificação: {e}")
        return False


def enviar_notificacao_saque_processado(
    token_dispositivo: str,
    valor: float,
    nome_barbeiro: str = None
) -> bool:
    """
    Notificar barbeiro quando um saque é processado.
    
    Args:
        token_dispositivo: Device token do barbeiro
        valor: Valor do saque
        nome_barbeiro: Nome do barbeiro (para logs)
    
    Returns:
        True/False
    """
    
    if not FIREBASE_DISPONIVEL:
        print(f"Firebase não está disponível")
        return False
    
    if not token_dispositivo:
        print(f"Nenhum device token para notificação de saque")
        return False
    
    valor_formatado = _formatar_moeda(valor)
    
    try:
        mensagem = messaging.Message(
            notification=messaging.Notification(
                title="🏦 Saque Processado!",
                body=f"Seu saque de {valor_formatado} foi processado. Você receberá em até 2 dias úteis."
            ),
            data={
                "tipo": "saque_processado",
                "valor": str(valor),
                "timestamp": datetime.utcnow().isoformat()
            },
            token=token_dispositivo,
        )
        
        resposta = messaging.send(mensagem)
        print(f"Notificação de saque enviada: {resposta}")
        return True
    except Exception as e:
        print(f"Falha ao notificar saque: {e}")
        return False


def enviar_notificacao_novo_chamado(
    token_dispositivo: str,
    nome_cliente: str,
    nome_servico: str,
    nome_barbearia: str = None
) -> bool:
    """
    Notificar barbeiro quando um novo chamado o procura.
    
    Args:
        token_dispositivo: Device token do barbeiro
        nome_cliente: Nome do cliente que solicitou
        nome_servico: Nome do serviço
        nome_barbearia: Nome da barbearia
    
    Returns:
        True/False
    """
    
    if not FIREBASE_DISPONIVEL:
        print(f"Firebase não está disponível")
        return False
    
    if not token_dispositivo:
        return False
    
    try:
        mensagem = messaging.Message(
            notification=messaging.Notification(
                title="📞 Novo Chamado!",
                body=f"{nome_cliente} solicitou {nome_servico} em {nome_barbearia or 'sua barbearia'}"
            ),
            data={
                "tipo": "novo_chamado",
                "cliente_nome": nome_cliente,
                "servico": nome_servico,
                "timestamp": datetime.utcnow().isoformat()
            },
            token=token_dispositivo,
        )
        
        resposta = messaging.send(mensagem)
        print(f"Notificação de chamado enviada: {resposta}")
        return True
    except Exception as e:
        print(f"Falha ao notificar chamado: {e}")
        return False


def enviar_notificacao_agendamento_aprovado(
    token_dispositivo: str,
    nome_cliente: str,
    data_horario: str
) -> bool:
    """
    Notificar cliente quando seu agendamento é aprovado.
    
    Args:
        token_dispositivo: Device token do cliente
        nome_cliente: Nome do cliente
        data_horario: Data e horário do agendamento
    
    Returns:
        True/False
    """
    
    if not FIREBASE_DISPONIVEL:
        print(f"Firebase não está disponível")
        return False
    
    if not token_dispositivo:
        return False
    
    try:
        mensagem = messaging.Message(
            notification=messaging.Notification(
                title="✅ Agendamento Confirmado!",
                body=f"Seu agendamento está confirmado para {data_horario}"
            ),
            data={
                "tipo": "agendamento_aprovado",
                "data_horario": data_horario,
                "timestamp": datetime.utcnow().isoformat()
            },
            token=token_dispositivo,
        )
        
        resposta = messaging.send(mensagem)
        print(f"Notificação de aprovação enviada: {resposta}")
        return True
    except Exception as e:
        print(f"Falha ao notificar aprovação: {e}")
        return False
