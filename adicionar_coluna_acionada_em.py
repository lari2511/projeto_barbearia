#!/usr/bin/env python3
"""
Script para adicionar coluna acionada_em na tabela cadeiras
"""

from app.database import engine
from sqlalchemy import text

def adicionar_coluna_acionada_em():
    """Adiciona coluna acionada_em na tabela cadeiras"""
    try:
        with engine.connect() as conn:
            # Verificar se coluna já existe
            result = conn.execute(text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name='cadeiras' AND column_name='acionada_em'
            """))
            
            if result.fetchone():
                print("✅ Coluna 'acionada_em' já existe na tabela cadeiras")
                return
            
            # Adicionar coluna
            conn.execute(text("""
                ALTER TABLE cadeiras 
                ADD COLUMN acionada_em TIMESTAMP NULL
            """))
            conn.commit()
            
            print("✅ Coluna 'acionada_em' adicionada com sucesso à tabela cadeiras!")
            print("📋 Barbeiros agora podem ver cadeiras acionadas próximas a eles")
            
    except Exception as e:
        print(f"❌ Erro ao adicionar coluna: {e}")
        raise

if __name__ == "__main__":
    print("\n🔧 Adicionando coluna acionada_em à tabela cadeiras...\n")
    adicionar_coluna_acionada_em()
    print("\n✨ Migração concluída!")
