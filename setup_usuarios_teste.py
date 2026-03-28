#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Setup teste: Criar usuários de teste no banco de dados"""

from app.database import SessionLocal, init_db
from app.models import Usuario
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_senha(senha):
    return pwd_context.hash(senha)

def criar_usuarios_teste():
    """Cria usuários de teste para os testes funcionarem"""
    
    # Inicializar banco (cria tabelas se não existirem)
    init_db()
    
    # Criar sessão
    db = SessionLocal()
    
    try:
        # Verificar se já existem
        barbeiro_existe = db.query(Usuario).filter_by(email="barbeiro@teste.com").first()
        cliente_existe = db.query(Usuario).filter_by(email="cliente@teste.com").first()
        
        if not barbeiro_existe:
            # Criar barbeiro
            barbeiro = Usuario(
                email="barbeiro@teste.com",
                nome="Joao Barbeiro",
                tipo="barbeiro",
                telefone="11999999999",
                cpf="12345678901",
                senha_hash=hash_senha("123456"),
                email_verificado=True,
                perfil_aprovado=True,
                disponivel=True,
                online_regiao=True
            )
            db.add(barbeiro)
            db.commit()
            print("[OK] Barbeiro criado: barbeiro@teste.com / 123456")
        else:
            print("[AVISO] Barbeiro ja existe")
        
        if not cliente_existe:
            # Criar cliente
            cliente = Usuario(
                email="cliente@teste.com",
                nome="Maria Cliente",
                tipo="cliente",
                telefone="11988888888",
                cpf="98765432109",
                senha_hash=hash_senha("123456"),
                email_verificado=True,
                perfil_aprovado=True,
                latitude=-23.5505,
                longitude=-46.6333
            )
            db.add(cliente)
            db.commit()
            print("[OK] Cliente criado: cliente@teste.com / 123456")
        else:
            print("[AVISO] Cliente ja existe")
        
        print("\n[SUCESSO] Usuarios de teste prontos!")
        return True
        
    except Exception as e:
        print(f"[ERRO] Erro ao criar usuarios: {e}")
        import traceback
        traceback.print_exc()
        db.rollback()
        return False
    finally:
        db.close()

if __name__ == "__main__":
    criar_usuarios_teste()
