import sqlite3

conn = sqlite3.connect('projeto_barbearia.db')
conn.row_factory = sqlite3.Row
cursor = conn.cursor()

print('=== TABELAS ===')
cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
tables = cursor.fetchall()
if not tables:
    print('NENHUMA TABELA!')
else:
    for row in tables:
        print(f'- {row[0]}')

print('\n=== ESTRUTURA DO DB ===')
for row in tables:
    table_name = row[0]
    print(f'\nTabela: {table_name}')
    cursor.execute(f'PRAGMA table_info({table_name})')
    cols = cursor.fetchall()
    for col in cols[:5]:  # Mostrar apenas 5 primeiras colunas
        print(f'  - {col[1]} ({col[2]})')

conn.close()

