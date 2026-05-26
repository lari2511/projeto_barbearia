"""
ARQUIVO: app/firebase_config.py
Configuração do Firebase Cloud Messaging (FCM) para notificações push
"""

import os
from dotenv import load_dotenv
from datetime import datetime
from typing import Optional

load_dotenv()

# Firebase é importado com try/except porque pode não estar instalado ainda
try:
    import firebase_admin
    from firebase_admin import credentials, messaging
    FIREBASE_DISPONIVEL = True
except ImportError:
    FIREBASE_DISPONIVEL = False
    print("Aviso: firebase-admin não está instalado.")
    print("   Execute: pip install firebase-admin")
    print("   Notificações push não funcionarão sem essa dependência.")

# Caminho para o arquivo JSON de credenciais do Firebase
FIREBASE_CREDENTIALS_PATH = os.getenv("FIREBASE_CREDENTIALS_PATH", "firebase-credentials.json")

# Inicializar Firebase uma única vez (evita múltiplas inicializações)
if FIREBASE_DISPONIVEL:
    try:
        if not firebase_admin._apps:
            cred = credentials.Certificate(FIREBASE_CREDENTIALS_PATH)
            firebase_admin.initialize_app(cred)
        print("Firebase inicializado com sucesso")
    except Exception as e:
        FIREBASE_DISPONIVEL = False
        print(f"Aviso: Firebase não inicializado. {e}")
        print("   Notificações push não funcionarão sem configuração adequada do Firebase.")


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
