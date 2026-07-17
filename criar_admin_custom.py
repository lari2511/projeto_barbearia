#!/usr/bin/env python3
"""
Script para criar admin com credenciais específicas
"""

from app.database import SessionLocal
from app.models import Usuario
from app.routes import get_password_hash

db = SessionLocal()

try:
    # Verifica se já existe
    admin = db.query(Usuario).filter(Usuario.email == "barbermove2024@gmail.com").first()
    
    if admin:
        print(f"⚠️  Admin já existe: {admin.email}")
        print("   Deletando...")
        db.delete(admin)
        db.commit()
    
    # Criar novo admin com credenciais personalizadas
    novo_admin = Usuario(
        email="barbermove2024@gmail.com",
        nome="BarberMove Admin",
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
    print("\n📧 Email: barbermove2024@gmail.com")
    print("🔐 Senha: Senha@123")
    print("\n🔗 Acesse em: http://localhost:5173")
    print("\n")
    
finally:
    db.close()
