#!/usr/bin/env python3
import sqlite3
import requests
from app.database import SessionLocal
from app import models

# 1️⃣ Verificar se tem dados no banco
print("=" * 60)
print("1️⃣  VERIFICANDO BANCO DE DADOS")
print("=" * 60)

conn = sqlite3.connect('barbearia.db')
cursor = conn.cursor()

cursor.execute("SELECT COUNT(*) FROM usuarios")
total_usuarios = cursor.fetchone()[0]
print(f"Total de usuários: {total_usuarios}")

cursor.execute("SELECT email, tipo FROM usuarios WHERE email = 'allansiqueira06@gmail.com'")
allan = cursor.fetchone()
if allan:
    print(f"✅ Allan encontrado: {allan}")
else:
    print("❌ Allan NÃO encontrado no banco")

conn.close()

# 2️⃣ Testar login via curl
print("\n" + "=" * 60)
print("2️⃣  TESTANDO LOGIN VIA API")
print("=" * 60)

try:
    res = requests.post(
        'http://localhost:8000/api/v1/login/cliente/',
        data={'username': 'allansiqueira06@gmail.com', 'password': 'senha123'},
        timeout=5
    )
    print(f"Status: {res.status_code}")
    print(f"Response: {res.text}")
except Exception as e:
    print(f"❌ Erro na requisição: {e}")

print("\n✅ Teste concluído")
