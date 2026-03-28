#!/usr/bin/env python3
"""
Teste de envio de email - BarberMove
"""
import asyncio
import os
import sys
from dotenv import load_dotenv

load_dotenv()

from app.email_simples import enviar_verificacao
from app.routes import create_email_verification_token

async def main():
    print("\n" + "="*60)
    print("📧 TESTE DE ENVIO DE EMAIL - BARBERMOVE")
    print("="*60)
    
    # Verificar configuração
    print("\n📋 CONFIGURAÇÃO ATUAL:")
    print(f"   📧 Remetente: {os.getenv('MAIL_FROM')}")
    print(f"   🔐 Senha: {'*' * len(os.getenv('MAIL_PASSWORD', ''))} ({len(os.getenv('MAIL_PASSWORD', ''))} chars)")
    print(f"   🌐 Servidor: {os.getenv('MAIL_SERVER')}:{os.getenv('MAIL_PORT')}")
    print(f"   🔒 STARTTLS: {os.getenv('MAIL_STARTTLS')}")
    
    # Solicitar email de destino
    print("\n" + "="*60)
    email_destino = input("📨 Digite o email para TESTAR (ou Enter para padrão): ").strip()
    
    if not email_destino:
        email_destino = "lari.nascimento20148@gmail.com"
        print(f"   ✓ Usando padrão: {email_destino}")
    
    # Validar email básico
    if "@" not in email_destino or "." not in email_destino:
        print("❌ Email inválido!")
        return
    
    print(f"\n📬 Destinatário: {email_destino}")
    
    # Confirmar envio
    print("\n" + "="*60)
    confirmar = input("⚡ Enviar email agora? (s/N): ").strip().lower()
    
    if confirmar != 's':
        print("❌ Cancelado pelo usuário")
        return
    
    # Gerar token
    print("\n⏳ Gerando token de verificação...")
    try:
        token = create_email_verification_token(email_destino)
        print(f"   ✅ Token gerado: {token[:40]}...")
    except Exception as e:
        print(f"   ❌ Erro ao gerar token: {e}")
        return
    
    # Enviar email
    print("\n⏳ Enviando email...")
    print("   (isso pode levar alguns segundos)")
    
    try:
        await enviar_verificacao(email_destino, token)
        
        print("\n" + "="*60)
        print("✅ EMAIL ENVIADO COM SUCESSO!")
        print("="*60)
        print(f"\n📬 Verifique a caixa de entrada de: {email_destino}")
        print("📁 Não se esqueça de verificar SPAM/LIXO ELETRÔNICO")
        print(f"\n🔗 Link de verificação:")
        print(f"   http://localhost:8000/api/v1/email/verificar?token={token}")
        print("\n" + "="*60)
        
    except Exception as e:
        print("\n" + "="*60)
        print("❌ ERRO AO ENVIAR EMAIL")
        print("="*60)
        print(f"\n🔴 Detalhes: {str(e)}")
        print("\n💡 POSSÍVEIS SOLUÇÕES:")
        print("\n1️⃣ Gmail:")
        print("   • Acesse: https://myaccount.google.com/apppasswords")
        print("   • Crie uma 'Senha de app' (16 caracteres)")
        print("   • Atualize MAIL_PASSWORD no .env")
        print("   • A senha NÃO é a senha normal da conta!")
        
        print("\n2️⃣ Verificação em 2 etapas:")
        print("   • Ative em: https://myaccount.google.com/security")
        print("   • Necessário para gerar senhas de app")
        
        print("\n3️⃣ Outlook/Hotmail:")
        print("   • Use: smtp-mail.outlook.com")
        print("   • Porta: 587")
        print("   • Pode precisar de senha de app também")
        
        print("\n4️⃣ Outras opções:")
        print("   • SendGrid (gratuito até 100/dia)")
        print("   • Mailgun (gratuito até 5000/mês)")
        print("   • SMTP2GO")
        
        print("\n" + "="*60)
        return 1
    
    return 0

if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code or 0)
    except KeyboardInterrupt:
        print("\n\n❌ Teste cancelado pelo usuário")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Erro inesperado: {e}")
        sys.exit(1)
