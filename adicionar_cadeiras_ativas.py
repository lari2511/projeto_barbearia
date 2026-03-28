"""Adicionar coluna cadeiras_ativas à tabela de assinaturas"""
import sqlite3

conn = sqlite3.connect('barbearia.db')
cursor = conn.cursor()

try:
    # Ver estrutura atual
    cursor.execute("PRAGMA table_info(assinaturas_barbearia)")
    colunas = cursor.fetchall()
    print("Estrutura atual da tabela assinaturas_barbearia:")
    for col in colunas:
        print(f"  - {col[1]} ({col[2]})")
    
    # Adicionar coluna cadeiras_ativas
    cursor.execute("""
        ALTER TABLE assinaturas_barbearia 
        ADD COLUMN cadeiras_ativas INTEGER DEFAULT 0
    """)
    
    conn.commit()
    print("\n✅ Coluna 'cadeiras_ativas' adicionada com sucesso!")
    
except sqlite3.OperationalError as e:
    if "duplicate column name" in str(e).lower():
        print("ℹ️ Coluna 'cadeiras_ativas' já existe")
    else:
        print(f"❌ Erro: {e}")
finally:
    conn.close()
