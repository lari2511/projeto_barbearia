#!/usr/bin/env python3
"""
Script rápido para criar admin - sem interação
"""

from app.database import SessionLocal
from app.models import Usuario
from app.routes import get_password_hash

db = SessionLocal()

try:
    # Verifica se já existe
    admin = db.query(Usuario).filter(Usuario.email == "admin@barbermove.com").first()
    
    if admin:
        print(f"✅ Admin já existe: {admin.email}")
    else:
        # Criar novo admin
        novo_admin = Usuario(
            email="admin@barbermove.com",
            nome="Administrador",
            senha_hash=get_password_hash("Senha@123"),
            tipo="admin",
            email_verificado=True,
            perfil_aprovado=True,
            disponivel=True
        )
        
        db.add(novo_admin)
        db.commit()
        
        print("\n" + "=" * 50)
        print("✅ ADMIN CRIADO COM SUCESSO!")
        print("=" * 50)
        print("\n📧 Email: admin@barbermove.com")
        print("🔐 Senha: Senha@123")
        print("\n🔗 Acesse em: http://localhost:5173")
        print("\n")
        
finally:
    db.close()
