#!/usr/bin/env python3
"""
Criar usuário barbearia simples para teste
"""

from app.database import SessionLocal
from app import models
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")

db = SessionLocal()

# Verificar se já existe
existe = db.query(models.Usuario).filter(models.Usuario.email == "teste@barbearia.com").first()

if existe:
    print("⚠️  Usuário já existe, atualizando senha...")
    existe.senha_hash = pwd_context.hash("123456")
    db.commit()
    usuario_id = existe.id
else:
    # Criar novo
    usuario = models.Usuario(
        nome="Barbearia Teste",
        email="teste@barbearia.com",
        senha_hash=pwd_context.hash("123456"),
        tipo="barbearia",
        telefone="11988887777",
        cnpj="12345678000199",
        latitude=-23.550520,
        longitude=-46.633308
    )
    db.add(usuario)
    db.commit()
    db.refresh(usuario)
    usuario_id = usuario.id
    print(f"✅ Usuário criado: {usuario.nome} (ID: {usuario.id})")

# Criar ou atualizar barbearia
barbearia = db.query(models.Barbearia).filter(models.Barbearia.usuario_id == usuario_id).first()

if not barbearia:
    barbearia = models.Barbearia(
        nome="Barbearia Teste",
        endereco="Rua Teste, 456",
        telefone="11988887777",
        usuario_id=usuario_id,
        latitude=-23.550520,
        longitude=-46.633308
    )
    db.add(barbearia)
    db.commit()
    print(f"✅ Barbearia criada: {barbearia.nome} (ID: {barbearia.id})")

print("\n📧 CREDENCIAIS DE LOGIN:")
print("   Email: teste@barbearia.com")
print("   Senha: 123456")
print("   Tipo: barbearia\n")

db.close()
