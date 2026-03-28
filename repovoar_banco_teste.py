#!/usr/bin/env python3
# Repovoar banco com dados de teste

from app.database import SessionLocal
from app import models
from passlib.context import CryptContext
from datetime import datetime, timedelta

db = SessionLocal()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

try:
    # ========== CLIENTES ==========
    clientes = [
        ('Cliente Um', 'cliente1@test.com'),
        ('Cliente Dois', 'cliente2@test.com'),
    ]
    
    for nome, email in clientes:
        cliente = models.Usuario(
            email=email,
            senha=pwd_context.hash('senha123'),
            nome=nome,
            tipo='cliente',
            telefone='11999999999',
            latitude=-23.5505,
            longitude=-46.6333,
            email_verificado=True,
            criado_em=datetime.now()
        )
        db.add(cliente)
    
    # ========== BARBEIROS ==========
    barbeiros = [
        ('Barbeiro Premium', 'barbeiro1@test.com'),
        ('Barbeiro Expert', 'barbeiro2@test.com'),
    ]
    
    for nome, email in barbeiros:
        barbeiro = models.Usuario(
            email=email,
            senha=pwd_context.hash('senha123'),
            nome=nome,
            tipo='barbeiro',
            telefone='11999999999',
            latitude=-23.5505,
            longitude=-46.6333,
            email_verificado=True,
            criado_em=datetime.now()
        )
        db.add(barbeiro)
    
    db.commit()
    
    # ========== BARBEARIAS ==========
    barbearias = [
        ('Barbearia São Paulo', 'barbearia1@test.com', -23.5505, -46.6333),
        ('Barbearia Centro', 'barbearia2@test.com', -23.5500, -46.6330),
    ]
    
    for nome, email, lat, lon in barbearias:
        barbearia = models.Barbearia(
            nome=nome,
            email=email,
            senha=pwd_context.hash('senha123'),
            telefone='11999999999',
            endereco='Rua Teste, 123 - São Paulo, SP',
            latitude=lat,
            longitude=lon,
            email_verificado=True,
            criado_em=datetime.now()
        )
        db.add(barbearia)
    
    db.commit()
    
    # ========== SERVIÇOS ==========
    barbearia = db.query(models.Barbearia).first()
    servicos = [
        ('Corte Normal', 'Corte de cabelo padrão', 'corte', 50.0, 30),
        ('Barba', 'Aparagem de barba', 'barba', 30.0, 20),
        ('Corte + Barba', 'Corte + aparagem de barba', 'combo', 70.0, 50),
    ]
    
    for nome, desc, cat, valor, duracao in servicos:
        servico = models.Servico(
            barbearia_id=barbearia.id,
            nome=nome,
            descricao=desc,
            categoria=cat,
            valor=valor,
            duracao_minutos=duracao,
            ativo=True,
            criado_em=datetime.now()
        )
        db.add(servico)
    
    db.commit()
    
    # ========== CADEIRAS ==========
    for i in range(1, 4):
        cadeira = models.Cadeira(
            barbearia_id=barbearia.id,
            numero=i,
            ativa=True,
            criado_em=datetime.now()
        )
        db.add(cadeira)
    
    db.commit()
    
    print("✅ Banco repopulado com sucesso!")
    print("\n📊 Dados criados:")
    print(f"  - {db.query(models.Usuario).count()} usuários (clientes + barbeiros + allan)")
    print(f"  - {db.query(models.Barbearia).count()} barbearias")
    print(f"  - {db.query(models.Servico).count()} serviços")
    print(f"  - {db.query(models.Cadeira).count()} cadeiras")
    
except Exception as e:
    print(f"❌ Erro: {e}")
    db.rollback()
finally:
    db.close()
