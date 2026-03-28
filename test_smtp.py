#!/usr/bin/env python3
"""
Script de teste rápido para verificação de email SMTP
Testa a conexão e envio de email real
"""

import asyncio
import os
import sys
from dotenv import load_dotenv

# Carrega variáveis de ambiente
load_dotenv()

# Importa as funções do projeto
from app.email import send_verification_email
from app.routes import create_email_verification_token

async def test_smtp_connection():
    """Testa a conexão SMTP"""
    print("\n" + "="*60)
    print("🧪 TESTE DE SMTP - BarberMove")
    print("="*60)
    
    # 1. Verificar configuração
    print("\n1️⃣ Verificando configuração do .env...")
    mail_username = os.getenv("MAIL_USERNAME")
    mail_password = os.getenv("MAIL_PASSWORD", "***oculta***")
    mail_from = os.getenv("MAIL_FROM")
    mail_server = os.getenv("MAIL_SERVER")
    mail_port = os.getenv("MAIL_PORT")
    
    if not all([mail_username, mail_from, mail_server, mail_port]):
        print("❌ Erro: .env não configurado corretamente!")
        print(f"   MAIL_USERNAME: {mail_username}")
        print(f"   MAIL_FROM: {mail_from}")
        print(f"   MAIL_SERVER: {mail_server}")
        print(f"   MAIL_PORT: {mail_port}")
        return False
    
    print(f"✅ Configuração OK!")
    print(f"   Username: {mail_username}")
    print(f"   From: {mail_from}")
    print(f"   Server: {mail_server}:{mail_port}")
    
    # 2. Gerar token
    print("\n2️⃣ Gerando token de verificação...")
    test_email = "teste@example.com"
    token = create_email_verification_token(test_email)
    print(f"✅ Token gerado: {token[:30]}...")
    
    # 3. Tentar enviar email
    print("\n3️⃣ Tentando enviar email de teste...")
    print(f"   Para: {test_email}")
    print(f"   Nome: João Silva")
    
    try:
        await send_verification_email(
            email_to=test_email,
            token_verification=token,
            user_name="João Silva"
        )
        print("✅ Email enviado com sucesso!")
        return True
        
    except Exception as e:
        print(f"❌ Erro ao enviar email:")
        print(f"   {type(e).__name__}: {str(e)}")
        print("\n💡 Dicas:")
        print("   - Se usar Gmail: Gerou a 'Senha de App'?")
        print("   - Se usar Resend: A chave API começa com 're_'?")
        print("   - Verifique MAIL_SERVER e MAIL_PORT no .env")
        return False


async def test_email_real():
    """Testa enviando para um email real"""
    print("\n" + "="*60)
    print("📧 TESTE COM EMAIL REAL")
    print("="*60)
    
    email_teste = input("\nDigite um email para testar: ").strip()
    
    if not email_teste or "@" not in email_teste:
        print("❌ Email inválido!")
        return
    
    print(f"\n⏳ Enviando para {email_teste}...")
    
    token = create_email_verification_token(email_teste)
    
    try:
        await send_verification_email(
            email_to=email_teste,
            token_verification=token,
            user_name="Teste BarberMove"
        )
        print(f"✅ Email enviado com sucesso para {email_teste}!")
        print("\n💡 Verifique sua caixa de entrada (incluindo spam)")
        print("   O email vem de: " + os.getenv("MAIL_FROM"))
        
    except Exception as e:
        print(f"❌ Erro: {str(e)}")


async def main():
    """Função principal"""
    # Teste 1: Configuração e conexão
    resultado = await test_smtp_connection()
    
    if resultado:
        print("\n✅ Teste básico passou!")
        
        # Perguntar se quer testar com email real
        continuar = input("\nDeseja enviar um email de teste real? (s/n): ").lower()
        if continuar == "s":
            await test_email_real()
    else:
        print("\n❌ Falha no teste básico. Verifique sua configuração.")
        sys.exit(1)
    
    print("\n" + "="*60)
    print("✅ Testes concluídos!")
    print("="*60)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n❌ Teste cancelado pelo usuário")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Erro fatal: {str(e)}")
        sys.exit(1)
