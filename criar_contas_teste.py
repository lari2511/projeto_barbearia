#!/usr/bin/env python3
"""
Script para criar contas de teste
"""

from app.database import SessionLocal
from app import models
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)

def criar_contas():
    db = SessionLocal()
    
    contas = [
        {"email": "cliente@test.com", "nome": "Cliente Teste", "tipo": "cliente", "senha": "senha123"},
        {"email": "barbeiro@test.com", "nome": "Barbeiro Teste", "tipo": "barbeiro", "senha": "senha123", "endereco": "Rua X, 123"},
        {"email": "barbearia@test.com", "nome": "Barbearia Teste", "tipo": "barbearia", "senha": "senha123", "endereco": "Av. Y, 456"},
    ]
    
    for conta in contas:
        # Verificar se já existe
        existe = db.query(models.Usuario).filter(
            models.Usuario.email == conta["email"]
        ).first()
        
        if existe:
            existe.senha_hash = get_password_hash(conta["senha"])
            existe.nome = conta["nome"]
            existe.tipo = conta["tipo"]
            existe.endereco = conta.get("endereco", "Endereço não informado")
            existe.email_verificado = True
            existe.perfil_aprovado = True
            db.add(existe)
            print(f"🔄 {conta['email']} atualizado com sucesso")
            continue
        
        # Criar usuario
        usuario = models.Usuario(
            nome=conta["nome"],
            email=conta["email"],
            senha_hash=get_password_hash(conta["senha"]),
            tipo=conta["tipo"],
            endereco=conta.get("endereco", "Endereço não informado"),
            email_verificado=True,  # Marcar como verificado para facilitar testes
            perfil_aprovado=True,   # Marcar como aprovado para facilitar testes
        )
        db.add(usuario)
        db.flush()
        
        print(f"✅ {conta['email']} criado com sucesso")
    
    db.commit()
    db.close()

if __name__ == "__main__":
    criar_contas()
