#!/usr/bin/env python3
"""
Script para popular o banco de dados com dados de teste
"""

from app.database import SessionLocal
from app import models
from passlib.context import CryptContext

# Usar contexto de criptografia igual ao das rotas
pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")

def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)

def seed_database():
    db = SessionLocal()
    
    # Verificar se barbearia já existe
    barbearia_existe = db.query(models.Usuario).filter(
        models.Usuario.email == "barbearia1@test.com"
    ).first()
    
    if not barbearia_existe:
        # Criar usuario tipo barbearia
        barbearia_usuario = models.Usuario(
            nome="Barbearia Downtown",
            email="barbearia1@test.com",
            senha_hash=get_password_hash("senha123"),
            tipo="barbearia",
            endereco="Rua Principal, 100"
        )
        db.add(barbearia_usuario)
        db.flush()
        
        # Criar registro de barbearia
        barbearia = models.Barbearia(
            usuario_id=barbearia_usuario.id,
            nome="Barbearia Downtown",
            endereco="Rua Principal, 100",
            telefone="11987654321",
            cadeira_livre=True
        )
        db.add(barbearia)
        db.commit()
        db.refresh(barbearia)
        
        # Adicionar serviços
        servicos = [
            models.Servico(nome="Corte Simples", categoria="corte", valor=30.0, duracao_minutos=30, barbearia_id=barbearia.id),
            models.Servico(nome="Corte Degradê", categoria="corte", valor=40.0, duracao_minutos=45, barbearia_id=barbearia.id),
            models.Servico(nome="Barba Completa", categoria="barba", valor=25.0, duracao_minutos=20, barbearia_id=barbearia.id),
            models.Servico(nome="Combo (Corte + Barba)", categoria="combo", valor=55.0, duracao_minutos=60, barbearia_id=barbearia.id),
        ]
        
        for servico in servicos:
            db.add(servico)
        
        db.commit()
        
        print(f"✅ Barbearia criada: {barbearia.nome}")
        print(f"   - Email: {barbearia_usuario.email}")
        print(f"   - Senha: senha123")
        print(f"   - {len(servicos)} serviços adicionados")
    else:
        print("⚠️  Barbearia já existe")
    
    db.close()

if __name__ == "__main__":
    seed_database()