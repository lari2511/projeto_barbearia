"""
Script para corrigir o email não verificado do allansiqueira
"""
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.models import Usuario

# Configurar conexão com banco de dados
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://postgres:postgres@localhost/barbermovie_db"
)

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def fix_email_allansiqueira():
    """Marca o email do allansiqueira como verificado"""
    db = SessionLocal()
    try:
        # Procurar o usuário
        user = db.query(Usuario).filter(
            Usuario.email.ilike("allansiqueira%")
        ).first()
        
        if not user:
            print("❌ Usuário 'allansiqueira' não encontrado!")
            return
        
        print(f"✓ Usuário encontrado: {user.email}")
        print(f"  Email verificado (antes): {user.email_verificado}")
        
        # Atualizar para verificado
        user.email_verificado = True
        db.commit()
        
        print(f"  Email verificado (depois): {user.email_verificado}")
        print("✅ Email marcado como verificado com sucesso!")
        
    except Exception as e:
        print(f"❌ Erro ao atualizar: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    fix_email_allansiqueira()
