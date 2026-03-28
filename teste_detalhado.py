#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Teste para verificar se o banco novo está acessível
"""
import sqlite3
import sys

print("1. Testando conexão SQLite pura...", flush=True)
try:
    conn = sqlite3.connect("barbearia.db")
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tabelas = cursor.fetchall()
    print(f"   ✅ Conectado! Tabelas: {[t[0] for t in tabelas]}", flush=True)
    conn.close()
except Exception as e:
    print(f"   ❌ ERRO: {e}", flush=True)
    sys.exit(1)

print("\n2. Testando import de sqlalchemy...", flush=True)
try:
    from sqlalchemy import create_engine
    print("   ✅ SQLAlchemy importado", flush=True)
except Exception as e:
    print(f"   ❌ ERRO: {e}", flush=True)
    sys.exit(1)

print("\n3. Testando criação de engine SQLite...", flush=True)
try:
    engine = create_engine("sqlite:///./barbearia.db", connect_args={"check_same_thread": False})
    print("   ✅ Engine criado", flush=True)
except Exception as e:
    print(f"   ❌ ERRO: {e}", flush=True)
    sys.exit(1)

print("\n4. Testando conexão via engine...", flush=True)
try:
    with engine.connect() as conn:
        result = conn.execute("SELECT 1")
        print(f"   ✅ Query funcionou: {result.fetchone()}", flush=True)
except Exception as e:
    print(f"   ❌ ERRO: {e}", flush=True)
    sys.exit(1)

print("\n5. Testando import de app.models...", flush=True)
try:
    from app import models
    print("   ✅ Models importado", flush=True)
except Exception as e:
    print(f"   ❌ ERRO ao importar models: {e}", flush=True)
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\n6. Testando import de app.database SessionLocal...", flush=True)
try:
    from app.database import SessionLocal
    print("   ✅ SessionLocal importado", flush=True)
except Exception as e:
    print(f"   ❌ ERRO ao importar SessionLocal: {e}", flush=True)
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\n7. Testando criação de sessão...", flush=True)
try:
    db = SessionLocal()
    print("   ✅ Sessão criada", flush=True)
    db.close()
except Exception as e:
    print(f"   ❌ ERRO ao criar sessão: {e}", flush=True)
    sys.exit(1)

print("\n✅ TODOS OS TESTES PASSARAM!")
print("   Backend deveria funcionar agora!")
