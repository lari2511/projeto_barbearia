#!/usr/bin/env python3
"""
Listar todos os usuários do banco
"""

from app.database import SessionLocal
from app import models

db = SessionLocal()

print("\n👥 USUÁRIOS NO BANCO DE DADOS:\n")
print("=" * 80)

usuarios = db.query(models.Usuario).all()
for u in usuarios:
    print(f"\n🔹 ID: {u.id}")
    print(f"   Nome: {u.nome}")
    print(f"   Email: {u.email}")
    print(f"   Tipo: {u.tipo}")
    print(f"   Telefone: {u.telefone or 'N/A'}")
    if u.tipo == "cliente":
        print(f"   CPF: {u.cpf or 'N/A'}")
    elif u.tipo == "barbeiro":
        print(f"   CPF: {u.cpf or 'N/A'}")
    elif u.tipo == "barbearia":
        print(f"   CNPJ: {u.cnpj or 'N/A'}")
    print("-" * 80)

print(f"\n✅ Total: {len(usuarios)} usuários\n")

# Listar barbearias
print("\n🏪 BARBEARIAS NO BANCO:\n")
print("=" * 80)

barbearias = db.query(models.Barbearia).all()
for b in barbearias:
    usuario = db.query(models.Usuario).filter(models.Usuario.id == b.usuario_id).first()
    print(f"\n🏪 ID: {b.id}")
    print(f"   Nome: {b.nome}")
    print(f"   Endereço: {b.endereco}")
    print(f"   Usuário ID: {b.usuario_id}")
    if usuario:
        print(f"   Login: {usuario.email}")
    print("-" * 80)

print(f"\n✅ Total: {len(barbearias)} barbearias\n")

db.close()
