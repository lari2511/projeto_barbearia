#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Teste direto do SQLAlchemy sem importar app.database
"""
print("Teste 1: Import SQLAlchemy...", flush=True)
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
print("  OK", flush=True)

print("Teste 2: Criar engine...", flush=True)
engine = create_engine("sqlite:///./barbearia.db", connect_args={"check_same_thread": False})
print("  OK", flush=True)

print("Teste 3: Criar SessionLocal...", flush=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
print("  OK", flush=True)

print("Teste 4: Criar sessão...", flush=True)
db = SessionLocal()
print("  OK", flush=True)

print("Teste 5: Executar query...", flush=True)
result = db.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = [r[0] for r in result.fetchall()]
print(f"  Tabelas: {tables}", flush=True)

db.close()
print("\n✅ SUCESSO! SQLAlchemy está funcionando normalmente.")
