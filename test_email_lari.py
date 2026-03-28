#!/usr/bin/env python3
"""
Teste de envio de email para lari.nascimento20148@gmail.com
"""

import asyncio
import os
from dotenv import load_dotenv

# Carrega variáveis de ambiente
load_dotenv()

# Importa as funções do projeto
from app.email import send_verification_email
from app.routes import create_email_verification_token

async def test_email_lari():
    """Testa envio de email para Larissa"""
    print("\n" + "="*60)
    print("📧 TESTE DE EMAIL - BarberMove")
    print("="*60)
    
    email_destino = "lari.nascimento20148@gmail.com"
    
    print(f"\n📨 Destinatário: {email_destino}")
    print(f"📮 Remetente: {os.getenv('MAIL_FROM')}")
    print(f"🔧 Servidor: {os.getenv('MAIL_SERVER')}:{os.getenv('MAIL_PORT')}")
    
    # Gerar token
    print(f"\n⏳ Gerando token de verificação...")
    token = create_email_verification_token(email_destino)
    print(f"✅ Token gerado: {token[:30]}...")
    
    # Enviar email
    print(f"\n📤 Enviando email de boas-vindas...")
    
    try:
        await send_verification_email(
            email_to=email_destino,
            token_verification=token,
            user_name="Larissa Nascimento"
        )
        
        print("\n" + "="*60)
        print("✅ EMAIL ENVIADO COM SUCESSO!")
        print("="*60)
        print(f"\n📬 Verifique a caixa de entrada de: {email_destino}")
        print("   ⚠️ Se não aparecer, verifique a pasta SPAM/Lixo Eletrônico")
        print(f"   📧 Remetente: {os.getenv('MAIL_FROM')}")
        print("   📝 Assunto: Bem-vindo ao BarberMove - Verifique seu email")
        print("\n🔗 Link de verificação gerado e incluído no email!")
        
        return True
        
    except Exception as e:
        print("\n" + "="*60)
        print("❌ ERRO AO ENVIAR EMAIL")
        print("="*60)
        print(f"\n🔴 Tipo: {type(e).__name__}")
        print(f"🔴 Mensagem: {str(e)}")
        
        print("\n💡 Possíveis soluções:")
        print("   1. Verifique se a senha de app está correta no .env")
        print("   2. Certifique-se que a conta Gmail permite apps menos seguros")
        print("   3. Verifique sua conexão com a internet")
        print("   4. Teste com outro email de destino")
        
        return False

if __name__ == "__main__":
    print("\n🚀 Iniciando teste de envio de email...")
    resultado = asyncio.run(test_email_lari())
    
    if resultado:
        print("\n✨ Teste concluído com sucesso!")
    else:
        print("\n⚠️ Teste falhou - verifique os erros acima")
