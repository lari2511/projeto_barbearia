#!/usr/bin/env python3
"""
Script completo: Criar banco + usuário barbearia
"""
import os
from app.database import engine, Base, SessionLocal
from app import models
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")

# 1. Apagar banco antigo
db_path = "C:/projeto_barbearia/barbearia.db"
if os.path.exists(db_path):
    os.remove(db_path)
    print("🗑️  Banco antigo removido")

# 2. Criar tabelas
Base.metadata.create_all(bind=engine)
print("✅ Tabelas criadas")

# 3. Criar usuário barbearia
db = SessionLocal()

usuario = models.Usuario(
    nome="Teste Barbearia",
    email="teste@teste.com",
    senha_hash=pwd_context.hash("123456"),
    tipo="barbearia",
    telefone="11999999999",
    cnpj="12345678000100",
    latitude=-23.550520,
    longitude=-46.633308
)
db.add(usuario)
db.commit()
db.refresh(usuario)

print(f"✅ Usuário criado: {usuario.email} (ID: {usuario.id})")

# 4. Criar barbearia
barbearia = models.Barbearia(
    nome="Teste Barbearia",
    endereco="Rua Teste, 999",
    telefone="11999999999",
    usuario_id=usuario.id,
    latitude=-23.550520,
    longitude=-46.633308
)
db.add(barbearia)
db.commit()

print(f"✅ Barbearia criada: {barbearia.nome} (ID: {barbearia.id})")

# 5. Verificar
total = db.query(models.Usuario).count()
print(f"\n📊 Total usuários no banco: {total}")

todos = db.query(models.Usuario).all()
for u in todos:
    print(f"   - Email: {u.email} | Tipo: {u.tipo} | ID: {u.id}")

db.close()

print("\n" + "="*60)
print("🎯 CREDENCIAIS PARA LOGIN:")
print("   Email: teste@teste.com")
print("   Senha: 123456")
print("="*60 + "\n")
