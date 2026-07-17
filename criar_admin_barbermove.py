#!/usr/bin/env python3
"""
Script para criar admin barbermove2024@gmail.com
"""

from app.database import SessionLocal
from app.models import Usuario
from app.routes import get_password_hash

db = SessionLocal()

try:
    # Verifica se já existe
    admin = db.query(Usuario).filter(Usuario.email == "barbermove2024@gmail.com").first()
    
    if admin:
        # Atualizar senha e configurações
        admin.senha_hash = get_password_hash("Senha@123")
        admin.tipo = "admin"
        admin.nome = "Admin BarberMove"
        admin.email_verificado = True
        admin.perfil_aprovado = True
        admin.disponivel = True
        db.add(admin)
        print(f"🔄 Admin barbermove2024@gmail.com atualizado com sucesso!")
    else:
        # Criar novo admin
        novo_admin = Usuario(
            email="barbermove2024@gmail.com",
            nome="Admin BarberMove",
            senha_hash=get_password_hash("Senha@123"),
            tipo="admin",
            email_verificado=True,
            perfil_aprovado=True,
            disponivel=True
        )
        
        db.add(novo_admin)
        print("✅ Admin barbermove2024@gmail.com criado com sucesso!")
    
    db.commit()
    
    print("\n" + "=" * 50)
    print("📧 Email: barbermove2024@gmail.com")
    print("🔐 Senha: Senha@123")
    print("👤 Tipo: Administrador")
    print("\n🔗 Acesse em: http://localhost:5173")
    print("=" * 50 + "\n")
    
finally:
    db.close()
