#!/usr/bin/env python3
"""
Script para forçar aprovação de usuário
"""

from app.database import SessionLocal
from app.models import Usuario

db = SessionLocal()

try:
    # Encontrar o cliente
    cliente = db.query(Usuario).filter(Usuario.tipo == "cliente").first()
    
    if not cliente:
        print("❌ Nenhum cliente encontrado")
    else:
        print(f"\n📋 Cliente encontrado: {cliente.email}")
        print(f"   Nome: {cliente.nome}")
        print(f"   Verificado: {cliente.email_verificado}")
        print(f"   Aprovado: {cliente.perfil_aprovado}")
        
        # Forçar aprovação
        cliente.perfil_aprovado = True
        cliente.email_verificado = True
        db.commit()
        
        print("\n✅ CLIENTE APROVADO!")
        print("\n🔄 Faça logout e login novamente para atualizar")
        
finally:
    db.close()
