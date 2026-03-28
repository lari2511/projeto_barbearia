#!/usr/bin/env python3
"""
Script para adicionar coluna perfil_aprovado na tabela usuarios
"""

from app.database import engine
from sqlalchemy import text

def adicionar_colunas_perfil_aprovado():
    """Adiciona colunas perfil_aprovado e perfil_aprovado_em na tabela usuarios"""
    try:
        with engine.connect() as conn:
            # Verificar se coluna já existe
            result = conn.execute(text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name='usuarios' AND column_name='perfil_aprovado'
            """))
            
            if result.fetchone():
                print("✅ Colunas 'perfil_aprovado' já existem na tabela usuarios")
                return
            
            # Adicionar coluna perfil_aprovado
            conn.execute(text("""
                ALTER TABLE usuarios 
                ADD COLUMN perfil_aprovado BOOLEAN DEFAULT FALSE
            """))
            
            # Adicionar coluna perfil_aprovado_em
            conn.execute(text("""
                ALTER TABLE usuarios 
                ADD COLUMN perfil_aprovado_em TIMESTAMP NULL
            """))
            
            conn.commit()
            
            print("✅ Colunas 'perfil_aprovado' e 'perfil_aprovado_em' adicionadas com sucesso!")
            print("📋 Barbeiros e clientes agora precisam de aprovação do admin para usar o app")
            
    except Exception as e:
        print(f"❌ Erro ao adicionar colunas: {e}")
        raise

if __name__ == "__main__":
    print("\n🔧 Adicionando coluna perfil_aprovado à tabela usuarios...\n")
    adicionar_colunas_perfil_aprovado()
    print("\n✨ Migração concluída!")
