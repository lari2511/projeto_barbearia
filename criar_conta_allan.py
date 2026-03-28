#!/usr/bin/env python3
# Script para criar conta para allansiqueira06

from app.database import SessionLocal, init_db, Base, engine
from app import models
from passlib.context import CryptContext
from datetime import datetime

# Inicializar banco
Base.metadata.create_all(bind=engine)

db = SessionLocal()

# Hash de senha
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

try:
    # Criar usuário cliente
    usuario = models.Usuario(
        email='allansiqueira06@gmail.com',
        senha=pwd_context.hash('senha123'),
        nome='Allan Siqueira',
        tipo='cliente',
        telefone='11999999999',
        latitude=-23.5505,
        longitude=-46.6333,
        email_verificado=True,
        criado_em=datetime.now()
    )
    db.add(usuario)
    db.commit()
    
    print("✅ Conta criada com sucesso!")
    print(f"📧 Email: allansiqueira06@gmail.com")
    print(f"🔐 Senha: senha123")
    print(f"👤 Nome: Allan Siqueira")
    print(f"📍 Tipo: Cliente")
    
except Exception as e:
    print(f"❌ Erro ao criar: {e}")
finally:
    db.close()
