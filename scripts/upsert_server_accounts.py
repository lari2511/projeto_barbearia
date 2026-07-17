#!/usr/bin/env python3
"""
Cria/atualiza contas no PostgreSQL remoto (servidor) usando TARGET_DATABASE_URL.

Contas padrao:
- Admin: barbermove2024@gmail.com / Senha@123
- Cliente: lari.nascimento20148@gmail.com / senha123
- Barbeiro: larissavideos2018@gmail.com / senha123
- Barbearia: allansiqueira06@gmail.com / senha123

Uso:
  1) Defina TARGET_DATABASE_URL no terminal
  2) python scripts/upsert_server_accounts.py

Obs: se DATABASE_URL nao estiver definida, o script copia de TARGET_DATABASE_URL.
"""

from __future__ import annotations

import os
from dataclasses import dataclass

from passlib.context import CryptContext


@dataclass
class Account:
    email: str
    nome: str
    tipo: str
    senha: str
    email_verificado: bool = True
    perfil_aprovado: bool = True


def ensure_database_url() -> None:
    target = os.getenv("TARGET_DATABASE_URL", "").strip()
    current = os.getenv("DATABASE_URL", "").strip()

    if not current and target:
        os.environ["DATABASE_URL"] = target
        current = target

    if not current:
        raise SystemExit(
            "DATABASE_URL/TARGET_DATABASE_URL nao definida. Configure TARGET_DATABASE_URL antes de executar."
        )

    if "postgresql" not in current.lower():
        raise SystemExit("A URL de banco precisa ser PostgreSQL para este script.")


def normalize_email(value: str) -> str:
    return value.strip().lower()


def main() -> None:
    ensure_database_url()

    from app.database import SessionLocal
    from app.models import Usuario

    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

    accounts = [
        Account(
            email="barbermove2024@gmail.com",
            nome="BarberMove Admin",
            tipo="admin",
            senha="Senha@123",
            email_verificado=True,
            perfil_aprovado=True,
        ),
        Account(
            email="lari.nascimento20148@gmail.com",
            nome="Lari Nascimento",
            tipo="cliente",
            senha="senha123",
        ),
        Account(
            email="larissavideos2018@gmail.com",
            nome="Lari",
            tipo="barbeiro",
            senha="senha123",
        ),
        Account(
            email="allansiqueira06@gmail.com",
            nome="Allan Siqueira",
            tipo="barbearia",
            senha="senha123",
        ),
    ]

    db = SessionLocal()
    try:
        for account in accounts:
            email = normalize_email(account.email)
            user = db.query(Usuario).filter(Usuario.email == email).first()

            if user:
                user.nome = account.nome
                user.tipo = account.tipo
                user.senha_hash = pwd_context.hash(account.senha)
                user.email_verificado = account.email_verificado
                user.perfil_aprovado = account.perfil_aprovado
                db.add(user)
                print(f"updated: {email} ({account.tipo})")
            else:
                user = Usuario(
                    email=email,
                    nome=account.nome,
                    tipo=account.tipo,
                    senha_hash=pwd_context.hash(account.senha),
                    email_verificado=account.email_verificado,
                    perfil_aprovado=account.perfil_aprovado,
                )
                db.add(user)
                print(f"created: {email} ({account.tipo})")

        db.commit()
        print("done")
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
