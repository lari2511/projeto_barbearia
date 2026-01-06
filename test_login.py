#!/usr/bin/env python3
"""
Testar login da barbearia
"""

import requests
from app.database import SessionLocal
from app import models
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")

# Verificar senha no banco
db = SessionLocal()
user = db.query(models.Usuario).filter(models.Usuario.email == "allansiqueira06@gmail.com").first()

if user:
    print(f"\n✅ Usuário encontrado:")
    print(f"   Email: {user.email}")
    print(f"   Nome: {user.nome}")
    print(f"   Tipo: {user.tipo}")
    print(f"   Senha Hash: {user.senha_hash[:50]}...")
    
    # Testar verificação de senha
    senha_correta = pwd_context.verify("123456", user.senha_hash)
    print(f"\n🔐 Verificação senha '123456': {'✅ VÁLIDA' if senha_correta else '❌ INVÁLIDA'}")
    
    # Testar login via API
    print("\n📡 Testando login via API...")
    response = requests.post(
        "http://192.168.15.5:8000/api/v1/login/barbearia/",
        json={"email": "allansiqueira06@gmail.com", "senha": "123456"}
    )
    
    print(f"   Status: {response.status_code}")
    print(f"   Response: {response.text}")
    
else:
    print("❌ Usuário não encontrado!")

db.close()
