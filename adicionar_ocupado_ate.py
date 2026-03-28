"""
Adiciona colunas ocupado_ate e em_atendimento à tabela usuarios
Permite bloqueio automático durante atendimento
"""
import sqlite3
from datetime import datetime

def adicionar_colunas():
    conn = sqlite3.connect('barbearia.db')
    cursor = conn.cursor()
    
    try:
        # Verificar se as colunas já existem
        cursor.execute("PRAGMA table_info(usuarios)")
        colunas = [col[1] for col in cursor.fetchall()]
        
        if 'ocupado_ate' not in colunas:
            print("⏳ Adicionando coluna 'ocupado_ate' à tabela usuarios...")
            cursor.execute("""
                ALTER TABLE usuarios 
                ADD COLUMN ocupado_ate TIMESTAMP NULL
            """)
            conn.commit()
            print("✅ Coluna 'ocupado_ate' adicionada com sucesso!")
            
            # Criar índice para performance
            print("📊 Criando índice para ocupado_ate...")
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_usuarios_ocupado_ate 
                ON usuarios(ocupado_ate)
            """)
            conn.commit()
            print("✅ Índice criado com sucesso!")
        else:
            print("ℹ️  Coluna 'ocupado_ate' já existe na tabela usuarios")
        
        if 'em_atendimento' not in colunas:
            print("⏳ Adicionando coluna 'em_atendimento' à tabela usuarios...")
            cursor.execute("""
                ALTER TABLE usuarios 
                ADD COLUMN em_atendimento BOOLEAN DEFAULT 0
            """)
            conn.commit()
            print("✅ Coluna 'em_atendimento' adicionada com sucesso!")
        else:
            print("ℹ️  Coluna 'em_atendimento' já existe na tabela usuarios")
        
        # Verificar estrutura final
        cursor.execute("PRAGMA table_info(usuarios)")
        print("\n📋 Estrutura da tabela usuarios:")
        for col in cursor.fetchall():
            if 'ocupado' in col[1] or 'disponivel' in col[1] or 'atendimento' in col[1]:
                print(f"  - {col[1]}: {col[2]}")
        
    except Exception as e:
        print(f"❌ Erro ao adicionar colunas: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    print("🔧 Migração: Adicionar colunas de controle de disponibilidade")
    print("=" * 50)
    adicionar_colunas()
    print("=" * 50)
    print("✅ Migração concluída!")

