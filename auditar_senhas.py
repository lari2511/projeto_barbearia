#!/usr/bin/env python3
"""
Audita os hashes de senha dos usuarios.

Uso (no shell do Railway, onde o Postgres e alcancavel):
    python auditar_senhas.py                  # lista contas com hash faltando/invalido
    python auditar_senhas.py EMAIL            # detalha uma conta
    python auditar_senhas.py EMAIL SENHA      # testa se SENHA bate na conta

Nao altera nada. So leitura.
"""
import sys

from app.database import SessionLocal
from app import models
from app.routes import verify_password, pwd_context


def _identifica(h):
    if not h:
        return "SEM HASH (None/vazio)"
    try:
        return pwd_context.identify(h) or "formato desconhecido"
    except Exception as e:  # noqa: BLE001
        return f"invalido ({e})"


def geral(db):
    users = db.query(models.Usuario).order_by(models.Usuario.id).all()
    ruins = []
    for u in users:
        esquema = _identifica(u.senha_hash)
        if esquema in ("SEM HASH (None/vazio)", "formato desconhecido") or esquema.startswith("invalido"):
            ruins.append((u.id, u.email, u.tipo, esquema))
    print(f"total de usuarios: {len(users)}")
    if not ruins:
        print("nenhuma conta com hash faltando/invalido.")
        return
    print(f"contas que NUNCA vao conseguir logar ({len(ruins)}):")
    for r in ruins:
        print("  id=%s  %s  (%s)  -> %s" % r)


def detalha(db, email, senha=None):
    email = email.strip().lower()
    u = (
        db.query(models.Usuario)
        .filter(models.Usuario.email == email)
        .first()
    )
    if not u:
        print(f"nenhuma conta com email {email!r}")
        return
    print(f"id={u.id}  email={u.email}  tipo={u.tipo}")
    print(f"email_verificado={u.email_verificado}  perfil_aprovado={u.perfil_aprovado}")
    print(f"hash: {_identifica(u.senha_hash)}")
    if senha is not None:
        try:
            print(f"verify_password({senha!r}) -> {verify_password(senha, u.senha_hash)}")
        except Exception as e:  # noqa: BLE001
            print(f"erro ao verificar: {e}")


def main():
    db = SessionLocal()
    try:
        if len(sys.argv) == 1:
            geral(db)
        elif len(sys.argv) == 2:
            detalha(db, sys.argv[1])
        else:
            detalha(db, sys.argv[1], sys.argv[2])
    finally:
        db.close()


if __name__ == "__main__":
    main()
