#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Script para recriar o banco de dados completamente
"""

import os
from app.database import engine, Base
from app import models

print("Deletando banco de dados antigo...")
if os.path.exists("barbearia.db"):
    os.remove("barbearia.db")
    print("[OK] Banco deletado")

print("\nCriando novas tabelas...")
Base.metadata.create_all(bind=engine)
print("[OK] Tabelas criadas com sucesso!")

print("\nVerificando tabelas...")
inspector = __import__('sqlalchemy').inspect(engine)
tables = inspector.get_table_names()
print(f"[OK] Total de tabelas: {len(tables)}")
for table in sorted(tables)[:5]:
    print(f"    - {table}")

print("\n[SUCESSO] Banco de dados recriado!")
