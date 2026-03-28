"""
Script para adicionar colunas faltantes nas tabelas existentes
"""

from sqlalchemy import text
from app.database import engine

def adicionar_colunas():
    """Adiciona colunas que faltaram na migração automática"""
    
    with engine.connect() as conn:
        print("🔧 Adicionando colunas faltantes...")
        
        # Adicionar coluna origem_cliente na tabela chamados
        try:
            conn.execute(text("""
                ALTER TABLE chamados 
                ADD COLUMN origem_cliente VARCHAR DEFAULT 'app'
            """))
            conn.commit()
            print("  ✅ chamados.origem_cliente adicionada")
        except Exception as e:
            conn.rollback()
            if "already exists" in str(e) or "duplicate" in str(e).lower():
                print("  ⏭️  chamados.origem_cliente já existe")
            else:
                print(f"  ❌ Erro ao adicionar chamados.origem_cliente: {e}")
        
        # Adicionar coluna status_online na tabela barbearias
        try:
            conn.execute(text("""
                ALTER TABLE barbearias 
                ADD COLUMN status_online BOOLEAN DEFAULT TRUE
            """))
            conn.commit()
            print("  ✅ barbearias.status_online adicionada")
        except Exception as e:
            conn.rollback()
            if "already exists" in str(e) or "duplicate" in str(e).lower():
                print("  ⏭️  barbearias.status_online já existe")
            else:
                print(f"  ❌ Erro ao adicionar barbearias.status_online: {e}")

        # Colunas de aprovação na tabela chamados
        try:
            conn.execute(text("""
                ALTER TABLE chamados 
                ADD COLUMN aprovado_barbeiro BOOLEAN DEFAULT FALSE
            """))
            conn.commit()
            print("  ✅ chamados.aprovado_barbeiro adicionada")
        except Exception as e:
            conn.rollback()
            if "already exists" in str(e) or "duplicate" in str(e).lower():
                print("  ⏭️  chamados.aprovado_barbeiro já existe")
            else:
                print(f"  ❌ Erro ao adicionar chamados.aprovado_barbeiro: {e}")

        try:
            conn.execute(text("""
                ALTER TABLE chamados 
                ADD COLUMN aprovado_barbearia BOOLEAN DEFAULT FALSE
            """))
            conn.commit()
            print("  ✅ chamados.aprovado_barbearia adicionada")
        except Exception as e:
            conn.rollback()
            if "already exists" in str(e) or "duplicate" in str(e).lower():
                print("  ⏭️  chamados.aprovado_barbearia já existe")
            else:
                print(f"  ❌ Erro ao adicionar chamados.aprovado_barbearia: {e}")

        try:
            conn.execute(text("""
                ALTER TABLE chamados 
                ADD COLUMN aprovado_barbeiro_em TIMESTAMP NULL DEFAULT NULL
            """))
            conn.commit()
            print("  ✅ chamados.aprovado_barbeiro_em adicionada")
        except Exception as e:
            conn.rollback()
            if "already exists" in str(e) or "duplicate" in str(e).lower():
                print("  ⏭️  chamados.aprovado_barbeiro_em já existe")
            else:
                print(f"  ❌ Erro ao adicionar chamados.aprovado_barbeiro_em: {e}")

        try:
            conn.execute(text("""
                ALTER TABLE chamados 
                ADD COLUMN aprovado_barbearia_em TIMESTAMP NULL DEFAULT NULL
            """))
            conn.commit()
            print("  ✅ chamados.aprovado_barbearia_em adicionada")
        except Exception as e:
            conn.rollback()
            if "already exists" in str(e) or "duplicate" in str(e).lower():
                print("  ⏭️  chamados.aprovado_barbearia_em já existe")
            else:
                print(f"  ❌ Erro ao adicionar chamados.aprovado_barbearia_em: {e}")

        # Colunas de acionamento na tabela cadeiras
        try:
            conn.execute(text("""
                ALTER TABLE cadeiras 
                ADD COLUMN acionada_em TIMESTAMP NULL DEFAULT NULL
            """))
            conn.commit()
            print("  ✅ cadeiras.acionada_em adicionada")
        except Exception as e:
            conn.rollback()
            if "already exists" in str(e) or "duplicate" in str(e).lower():
                print("  ⏭️  cadeiras.acionada_em já existe")
            else:
                print(f"  ❌ Erro ao adicionar cadeiras.acionada_em: {e}")

        try:
            conn.execute(text("""
                ALTER TABLE cadeiras 
                ADD COLUMN acionada_por_id INTEGER REFERENCES usuarios(id) ON DELETE SET NULL
            """))
            conn.commit()
            print("  ✅ cadeiras.acionada_por_id adicionada")
        except Exception as e:
            conn.rollback()
            if "already exists" in str(e) or "duplicate" in str(e).lower():
                print("  ⏭️  cadeiras.acionada_por_id já existe")
            else:
                print(f"  ❌ Erro ao adicionar cadeiras.acionada_por_id: {e}")

        try:
            conn.execute(text("""
                ALTER TABLE cadeiras 
                ADD COLUMN chamado_id INTEGER REFERENCES chamados(id) ON DELETE SET NULL
            """))
            conn.commit()
            print("  ✅ cadeiras.chamado_id adicionada")
        except Exception as e:
            conn.rollback()
            if "already exists" in str(e) or "duplicate" in str(e).lower():
                print("  ⏭️  cadeiras.chamado_id já existe")
            else:
                print(f"  ❌ Erro ao adicionar cadeiras.chamado_id: {e}")
        
        print("\n✨ Processo concluído!")


if __name__ == "__main__":
    print("=" * 60)
    print("ADICIONAR COLUNAS FALTANTES")
    print("=" * 60)
    print()
    
    adicionar_colunas()
