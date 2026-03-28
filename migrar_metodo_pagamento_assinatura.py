"""Migração: adiciona coluna metodo_pagamento_preferido em assinaturas_barbearia."""
import sqlite3

conn = sqlite3.connect("barbearia.db")
cur = conn.cursor()

try:
    cur.execute("PRAGMA table_info(assinaturas_barbearia)")
    colunas = [row[1] for row in cur.fetchall()]

    if "metodo_pagamento_preferido" not in colunas:
        cur.execute(
            "ALTER TABLE assinaturas_barbearia ADD COLUMN metodo_pagamento_preferido TEXT"
        )
        conn.commit()
        print("OK: coluna metodo_pagamento_preferido adicionada")
    else:
        print("OK: coluna metodo_pagamento_preferido ja existe")
except Exception as exc:
    print(f"ERRO: {exc}")
    raise
finally:
    conn.close()
