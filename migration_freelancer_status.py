"""
Migração: Sistema de Status do Freelancer
Adiciona campos necessários para o sistema de 3 status (OFFLINE, ONLINE, PRESENTE)
e cria tabela de bloqueios barbearia-freelancer
"""

import sys
from app.database import engine, SessionLocal
from app.models import Base, Usuario, BarbeariaFreelancer
from sqlalchemy import text

def migrate():
    db = SessionLocal()
    try:
        print("🔧 Iniciando migração do sistema de status freelancer...")
        
        # 1. Adicionar campos na tabela usuarios (se não existirem)
        print("\n1️⃣ Adicionando campos 'online_regiao' e 'barbearia_atual_id' na tabela usuarios...")
        
        # Usar uma conexão direta para DDL
        with engine.connect() as conn:
            try:
                # Testa se a coluna online_regiao existe
                conn.execute(text("SELECT online_regiao FROM usuarios LIMIT 1"))
                print("   ✅ Campo 'online_regiao' já existe")
            except:
                conn.rollback()
                # Adiciona se não existir
                conn.execute(text("ALTER TABLE usuarios ADD COLUMN online_regiao BOOLEAN DEFAULT FALSE"))
                conn.commit()
                print("   ✅ Campo 'online_regiao' adicionado")
            
            try:
                # Testa se a coluna barbearia_atual_id existe
                conn.execute(text("SELECT barbearia_atual_id FROM usuarios LIMIT 1"))
                print("   ✅ Campo 'barbearia_atual_id' já existe")
            except:
                conn.rollback()
                conn.execute(text("ALTER TABLE usuarios ADD COLUMN barbearia_atual_id INTEGER REFERENCES barbearias(id)"))
                conn.commit()
                print("   ✅ Campo 'barbearia_atual_id' adicionado")
        
        # 2. Criar tabela barbearia_freelancer (se não existir)
        print("\n2️⃣ Criando tabela 'barbearia_freelancer'...")
        Base.metadata.create_all(bind=engine, tables=[BarbeariaFreelancer.__table__])
        print("   ✅ Tabela 'barbearia_freelancer' criada")
        
        # 3. Normalizar dados existentes (garantir consistência)
        print("\n3️⃣ Normalizando dados existentes...")
        # Garantir que barbeiros com presente_em_local=true tenham online_regiao=false
        db.execute(text("""
            UPDATE usuarios 
            SET online_regiao = FALSE 
            WHERE presente_em_local = TRUE AND tipo = 'barbeiro'
        """))
        db.commit()
        print("   ✅ Dados normalizados")
        
        print("\n✅ Migração concluída com sucesso!")
        print("\n📋 CAMPOS ADICIONADOS:")
        print("   • usuarios.online_regiao (Boolean) - Freelancer online no marketplace")
        print("   • usuarios.barbearia_atual_id (Integer FK) - Barbearia onde está presente")
        print("\n📋 TABELA CRIADA:")
        print("   • barbearia_freelancer - Controle de bloqueios")
        
    except Exception as e:
        print(f"\n❌ Erro durante a migração: {e}")
        db.rollback()
        sys.exit(1)
    finally:
        db.close()

if __name__ == "__main__":
    migrate()
