"""
Migração: Adicionar campos de bloqueio na tabela barbearias
- bloqueada (Boolean): Indica se a barbearia está bloqueada
- motivo_bloqueio (String): Motivo do bloqueio
- bloqueada_em (DateTime): Quando foi bloqueada

Execução: python adicionar_campos_bloqueio_barbearia.py
"""
import sqlite3
from datetime import datetime

def migrar():
    conn = sqlite3.connect('barbearia.db')
    cursor = conn.cursor()
    
    try:
        # Verificar se as colunas já existem
        cursor.execute("PRAGMA table_info(barbearias)")
        colunas_existentes = [col[1] for col in cursor.fetchall()]
        
        # Adicionar coluna bloqueada
        if 'bloqueada' not in colunas_existentes:
            print("Adicionando coluna 'bloqueada'...")
            cursor.execute("""
                ALTER TABLE barbearias 
                ADD COLUMN bloqueada BOOLEAN DEFAULT 0
            """)
            # Criar índice para performance
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_barbearias_bloqueada 
                ON barbearias(bloqueada)
            """)
            print("✓ Coluna 'bloqueada' adicionada com sucesso")
        else:
            print("⊘ Coluna 'bloqueada' já existe")
        
        # Adicionar coluna motivo_bloqueio
        if 'motivo_bloqueio' not in colunas_existentes:
            print("Adicionando coluna 'motivo_bloqueio'...")
            cursor.execute("""
                ALTER TABLE barbearias 
                ADD COLUMN motivo_bloqueio TEXT
            """)
            print("✓ Coluna 'motivo_bloqueio' adicionada com sucesso")
        else:
            print("⊘ Coluna 'motivo_bloqueio' já existe")
        
        # Adicionar coluna bloqueada_em
        if 'bloqueada_em' not in colunas_existentes:
            print("Adicionando coluna 'bloqueada_em'...")
            cursor.execute("""
                ALTER TABLE barbearias 
                ADD COLUMN bloqueada_em TIMESTAMP
            """)
            print("✓ Coluna 'bloqueada_em' adicionada com sucesso")
        else:
            print("⊘ Coluna 'bloqueada_em' já existe")
        
        conn.commit()
        print("\n✅ Migração concluída com sucesso!")
        
        # Mostrar resumo da tabela
        cursor.execute("PRAGMA table_info(barbearias)")
        print("\n📋 Estrutura atual da tabela 'barbearias':")
        for col in cursor.fetchall():
            print(f"  - {col[1]} ({col[2]})")
        
    except Exception as e:
        print(f"\n❌ Erro na migração: {e}")
        conn.rollback()
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    print("🔧 Iniciando migração de campos de bloqueio...")
    migrar()
