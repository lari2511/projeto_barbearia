#!/usr/bin/env python3
"""
Atualizar senha do usuário teste@teste.com
"""
from app.database import SessionLocal
from app import models
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")

db = SessionLocal()

# Buscar usuário
usuario = db.query(models.Usuario).filter(models.Usuario.email == "teste@teste.com").first()

if usuario:
    # Atualizar senha
    usuario.senha_hash = pwd_context.hash("123456")
    db.commit()
    print(f"✅ Senha atualizada para: teste@teste.com")
else:
    print("❌ Usuário não encontrado")

db.close()

print("\n" + "="*60)
print("🎯 CREDENCIAIS PARA LOGIN:")
print("   Email: teste@teste.com")
print("   Senha: 123456")
print("="*60 + "\n")
