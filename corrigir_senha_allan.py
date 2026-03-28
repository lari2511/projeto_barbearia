#!/usr/bin/env python3
"""
Recria a conta do Allan com o hash correto
"""

import sqlite3
from passlib.context import CryptContext

# Usar o MESMO contexto do backend
pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")

# Gerar novo hash com argon2
nouvelle_senha = "senha123"
nova_senha_hash = pwd_context.hash(nouvelle_senha)

print(f"Nova senha: {nouvelle_senha}")
print(f"Novo hash (argon2): {nova_senha_hash[:50]}...")

# Atualizar no banco
conn = sqlite3.connect('barbearia.db')
cursor = conn.cursor()

cursor.execute(
    "UPDATE usuarios SET senha_hash = ? WHERE email = 'allansiqueira06@gmail.com'",
    (nova_senha_hash,)
)

conn.commit()
print(f"\n✅ Senha atualizada no banco!")

# Verificar
cursor.execute("SELECT email, senha_hash FROM usuarios WHERE email = 'allansiqueira06@gmail.com'")
usuario = cursor.fetchone()
if usuario:
    email, hash_check = usuario
    resultado = pwd_context.verify("senha123", hash_check)
    print(f"✅ Verificação de senha: {resultado}")
    print(f"✅ Pronto para logar com: {email} / {nouvelle_senha}")

conn.close()
