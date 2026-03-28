import sqlite3

conn = sqlite3.connect('barbearia.db')
cursor = conn.cursor()

tables = cursor.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()

print("📊 TABELAS NO BANCO DE DADOS (barbearia.db):")
if tables:
    for table in tables:
        print(f"  ✓ {table[0]}")
    print(f"\n✅ Total: {len(tables)} tabelas")
else:
    print("  ❌ NENHUMA TABELA!")

conn.close()
