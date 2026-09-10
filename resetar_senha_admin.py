#!/usr/bin/env python3
"""
Reset / garante o acesso da ADM ao painel web (/admin).

Uso:
    python resetar_senha_admin.py                      # usa email/senha padrao
    python resetar_senha_admin.py EMAIL SENHA          # valores customizados

- Se a ADM ja existe: apenas troca a senha (o gap do criar_admin_quick.py era
  justamente NAO resetar quando o usuario ja existia).
- Se nao existe: cria com tipo="admin", email_verificado=True, perfil_aprovado=True.
- No fim confere o login com a mesma funcao verify_password usada pela API.
"""
import sys

from app.database import SessionLocal
from app import models
from app.routes import get_password_hash, verify_password

EMAIL_PADRAO = "admin@barbermove.com"
SENHA_PADRAO = "Senha@123"


def main() -> None:
    email = (sys.argv[1] if len(sys.argv) > 1 else EMAIL_PADRAO).strip().lower()
    senha = sys.argv[2] if len(sys.argv) > 2 else SENHA_PADRAO

    if len(senha) < 6:
        print("❌ A senha precisa ter pelo menos 6 caracteres.")
        sys.exit(1)

    db = SessionLocal()
    try:
        usuario = (
            db.query(models.Usuario)
            .filter(models.Usuario.email == email)
            .first()
        )

        if usuario is None:
            usuario = models.Usuario(
                email=email,
                nome="Administrador",
                senha_hash=get_password_hash(senha),
                tipo="admin",
                email_verificado=True,
                perfil_aprovado=True,
            )
            db.add(usuario)
            acao = "criada"
        else:
            usuario.senha_hash = get_password_hash(senha)
            # Garante que o registro nao caiu em nenhuma trava.
            usuario.tipo = "admin"
            usuario.email_verificado = True
            usuario.perfil_aprovado = True
            acao = "atualizada"

        db.commit()
        db.refresh(usuario)

        ok = verify_password(senha, usuario.senha_hash)
        print("=" * 56)
        print(f"✅ Conta ADM {acao}")
        print(f"   Email: {usuario.email}")
        print(f"   Senha: {senha}")
        print(f"   tipo={usuario.tipo}  id={usuario.id}")
        print(f"   verify_password -> {ok}")
        print("=" * 56)
        print("Login em: <API_URL>/admin  (endpoint POST /api/v1/login/admin/)")

        if not ok:
            print("⚠️  verify_password retornou False - investigar backend de hash.")
            sys.exit(2)
    finally:
        db.close()


if __name__ == "__main__":
    main()
