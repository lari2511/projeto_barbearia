"""
Criar tabela de assinaturas se não existir
"""
import sqlite3

def criar_tabela_assinaturas():
    conn = sqlite3.connect('barbearia.db')
    cursor = conn.cursor()
    
    try:
        print("=== Criando tabela de assinaturas ===\n")
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS assinaturas_barbearia (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                barbearia_id INTEGER UNIQUE NOT NULL,
                quantidade_cadeiras INTEGER NOT NULL DEFAULT 1,
                valor_mensalidade REAL NOT NULL,
                valor_por_cadeira TEXT,
                economia_mensal REAL DEFAULT 0.0,
                dia_vencimento INTEGER NOT NULL DEFAULT 10,
                proximo_vencimento TIMESTAMP NOT NULL,
                status TEXT NOT NULL DEFAULT 'ativa',
                motivo_suspensao TEXT,
                ultima_atualizacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                cancelado_em TIMESTAMP,
                FOREIGN KEY (barbearia_id) REFERENCES barbearias(id)
            )
        """)
        
        conn.commit()
        print("✅ Tabela assinaturas_barbearia criada/verificada!")
        
        # Verificar estrutura
        cursor.execute("PRAGMA table_info(assinaturas_barbearia)")
        colunas = cursor.fetchall()
        print("\n📋 Estrutura da tabela:")
        for col in colunas:
            print(f"  - {col[1]}: {col[2]}")
        
        # Verificar assinaturas existentes
        cursor.execute("SELECT COUNT(*) FROM assinaturas_barbearia")
        total = cursor.fetchone()[0]
        print(f"\n📊 Total de assinaturas: {total}")
        
    except Exception as e:
        print(f"❌ Erro: {e}")
        import traceback
        traceback.print_exc()
    finally:
        conn.close()

if __name__ == "__main__":
    criar_tabela_assinaturas()
