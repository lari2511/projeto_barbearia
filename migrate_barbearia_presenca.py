"""
Migração: Adicionar campos de presença à tabela barbearias
Data: 17 de fevereiro de 2026
"""

from app.database import SessionLocal, engine
from sqlalchemy import text

def adicionar_campos_presenca_barbearias():
    """Adiciona campos presente_em_local e horario_chegada à tabela barbearias"""
    
    connection = engine.connect()
    transaction = connection.begin()
    
    try:
        # Adicionar coluna presente_em_local
        try:
            print("🔧 Adicionando coluna 'presente_em_local'...")
            connection.execute(text("""
                ALTER TABLE barbearias 
                ADD COLUMN presente_em_local BOOLEAN DEFAULT FALSE
            """))
            print("✅ Coluna 'presente_em_local' adicionada")
        except Exception as e:
            if "already exists" in str(e) or "duplicate" in str(e).lower():
                print("✅ Coluna 'presente_em_local' já existe")
            else:
                raise
        
        # Adicionar coluna horario_chegada
        try:
            print("🔧 Adicionando coluna 'horario_chegada'...")
            connection.execute(text("""
                ALTER TABLE barbearias 
                ADD COLUMN horario_chegada TIMESTAMP NULL
            """))
            print("✅ Coluna 'horario_chegada' adicionada")
        except Exception as e:
            if "already exists" in str(e) or "duplicate" in str(e).lower():
                print("✅ Coluna 'horario_chegada' já existe")
            else:
                raise
        
        transaction.commit()
        print("\n✅ Migração concluída com sucesso!")
        
    except Exception as e:
        transaction.rollback()
        print(f"❌ Erro na migração: {e}")
        raise
    finally:
        connection.close()


if __name__ == "__main__":
    adicionar_campos_presenca_barbearias()
