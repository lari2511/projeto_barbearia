"""
Script para testar e demonstrar o fluxo de verificação de email
"""
import os
import sys
import jwt
from datetime import datetime, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.models import Usuario

# Configurar encoding UTF-8
if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

# ==================== CONFIGURAÇÃO ====================

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://postgres:postgres@localhost/barbermovie_db"
)

SECRET_KEY = os.getenv("SECRET_KEY", "INSEGURO_MUDE_ISSO_AGORA")
ALGORITHM = "HS256"
EMAIL_TOKEN_EXPIRE_HOURS = 24

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# ==================== FUNÇÕES ====================

def create_email_verification_token(email: str) -> str:
    """Gera token JWT para verificação de email (24h)"""
    expire = datetime.now() + timedelta(hours=EMAIL_TOKEN_EXPIRE_HOURS)
    to_encode = {
        "sub": email,
        "exp": expire,
        "type": "email_verification"
    }
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def verify_email_token(token: str) -> str | None:
    """Decodifica e valida token JWT"""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        token_type: str = payload.get("type")
        
        if email is None or token_type != "email_verification":
            return None
        return email
    except jwt.ExpiredSignatureError:
        return None
    except jwt.JWTError:
        return None

def mostrar_info_token(token: str):
    """Mostra informações do token JWT"""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        print(f"  📧 Email: {payload.get('sub')}")
        print(f"  🔑 Tipo: {payload.get('type')}")
        
        exp = payload.get('exp')
        exp_datetime = datetime.fromtimestamp(exp)
        agora = datetime.now()
        tempo_restante = exp_datetime - agora
        
        print(f"  ⏱️  Expira em: {exp_datetime.strftime('%d/%m/%Y %H:%M:%S')}")
        print(f"  ⏲️  Tempo restante: {tempo_restante.total_seconds() / 3600:.1f} horas")
        
    except jwt.ExpiredSignatureError:
        print("  ❌ Token EXPIRADO")
    except jwt.JWTError as e:
        print(f"  ❌ Erro ao decodificar: {e}")

def testar_usuario(email: str):
    """Testa fluxo completo de um usuário"""
    db = SessionLocal()
    
    try:
        print(f"\n{'='*70}")
        print(f"🧪 TESTANDO: {email}")
        print(f"{'='*70}\n")
        
        # 1. Procurar usuário
        user = db.query(Usuario).filter(Usuario.email.ilike(email)).first()
        
        if not user:
            print(f"❌ Usuário '{email}' não encontrado!")
            return
        
        print(f"✅ Usuário encontrado: {user.nome}")
        print(f"   Email: {user.email}")
        print(f"   Tipo: {user.tipo}")
        print(f"   Criado em: {user.criado_em.strftime('%d/%m/%Y %H:%M:%S')}")
        
        # 2. Status de verificação
        print(f"\n📊 STATUS ATUAL:")
        print(f"   Email Verificado: {'✅ SIM' if user.email_verificado else '❌ NÃO'}")
        
        if user.token_verificacao:
            print(f"\n🔐 TOKEN ARMAZENADO:")
            print(f"   {user.token_verificacao[:50]}...")
            print(f"\n📋 INFORMAÇÕES DO TOKEN:")
            mostrar_info_token(user.token_verificacao)
        else:
            print(f"   Token: Não há token (email já verificado)")
        
        # 3. Gerar novo token para exemplo
        print(f"\n🆕 NOVO TOKEN GERADO (para referência):")
        novo_token = create_email_verification_token(user.email)
        print(f"   {novo_token[:50]}...")
        print(f"\n📋 INFORMAÇÕES DO NOVO TOKEN:")
        mostrar_info_token(novo_token)
        
        # 4. Simular verificação
        print(f"\n🔍 SIMULANDO CLIQUE NO LINK:")
        if user.token_verificacao:
            email_decoded = verify_email_token(user.token_verificacao)
            if email_decoded:
                print(f"   ✅ Token válido!")
                print(f"   📧 Email extraído: {email_decoded}")
                print(f"   ✨ Será marcado como verificado!")
            else:
                print(f"   ❌ Token inválido ou expirado!")
        else:
            print(f"   ⚠️  Sem token - email já foi verificado")
        
        # 5. Mostrar link de teste
        print(f"\n🔗 LINK PARA TESTAR:")
        if user.token_verificacao:
            print(f"   GET http://localhost:8000/api/v1/email/verificar?token={user.token_verificacao}")
        else:
            print(f"   ⚠️  Sem token disponível")
        
    finally:
        db.close()

# ==================== MAIN ====================

if __name__ == "__main__":
    print("\n🔐 TESTE DE FLUXO DE VERIFICAÇÃO DE EMAIL")
    print("=" * 70)
    
    # Testar alguns emails
    emails_teste = [
        "allansiqueira06@gmail.com",
        "%"  # Isso vai listar todos os usuários
    ]
    
    db = SessionLocal()
    
    try:
        usuarios = db.query(Usuario).limit(5).all()
        
        if not usuarios:
            print("\n❌ Nenhum usuário encontrado no banco de dados!")
        else:
            print(f"\n📋 ENCONTRADOS {len(usuarios)} USUÁRIOS:\n")
            
            for i, user in enumerate(usuarios, 1):
                print(f"{i}. {user.nome} ({user.email}) - {'✅ Verificado' if user.email_verificado else '❌ Pendente'}")
            
            # Testar cada um
            for user in usuarios:
                testar_usuario(user.email)
    
    finally:
        db.close()
    
    print(f"\n{'='*70}")
    print("✅ Teste concluído!")
    print(f"{'='*70}\n")
