#!/usr/bin/env python3
"""
Recriar dados de teste completos
"""

from app.database import SessionLocal
from app import models
from passlib.context import CryptContext
from datetime import datetime, timedelta

pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")

def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)

def criar_dados_teste():
    db = SessionLocal()
    
    # 1. Criar cliente LARISSA
    cliente = db.query(models.Usuario).filter(models.Usuario.email == "larissa@test.com").first()
    if not cliente:
        cliente = models.Usuario(
            nome="LARISSA NASCIMENTO ROCHA",
            email="larissa@test.com",
            senha_hash=get_password_hash("123456"),
            tipo="cliente",
            telefone="11987654321",
            cpf="12345678901",
            latitude=-23.550520,
            longitude=-46.633308
        )
        db.add(cliente)
        db.commit()
        db.refresh(cliente)
        print(f"✅ Cliente criada: {cliente.nome} (ID: {cliente.id})")
    
    # 2. Criar barbeiro Allan
    barbeiro = db.query(models.Usuario).filter(models.Usuario.email == "allansiqueira067@gmail.com").first()
    if not barbeiro:
        barbeiro = models.Usuario(
            nome="Allan ",
            email="allansiqueira067@gmail.com",
            senha_hash=get_password_hash("123456"),
            tipo="barbeiro",
            telefone="11999999999",
            cpf="98765432100",
            latitude=-23.550520,
            longitude=-46.633308
        )
        db.add(barbeiro)
        db.commit()
        db.refresh(barbeiro)
        print(f"✅ Barbeiro criado: {barbeiro.nome} (ID: {barbeiro.id})")
    
    # 3. Criar barbearia Allan
    usuario_barbearia = db.query(models.Usuario).filter(models.Usuario.email == "allansiqueira06@gmail.com").first()
    if not usuario_barbearia:
        usuario_barbearia = models.Usuario(
            nome="Allan",
            email="allansiqueira06@gmail.com",
            senha_hash=get_password_hash("123456"),
            tipo="barbearia",
            telefone="11888888888",
            cnpj="12345678000190",
            latitude=-23.550520,
            longitude=-46.633308
        )
        db.add(usuario_barbearia)
        db.commit()
        db.refresh(usuario_barbearia)
        print(f"✅ Usuário Barbearia criado: {usuario_barbearia.nome} (ID: {usuario_barbearia.id})")
    
    # 4. Criar loja Barbearia
    barbearia = db.query(models.Barbearia).filter(models.Barbearia.usuario_id == usuario_barbearia.id).first()
    if not barbearia:
        barbearia = models.Barbearia(
            nome="Allan",
            endereco="Rua Teste, 123",
            telefone="11888888888",
            usuario_id=usuario_barbearia.id,
            latitude=-23.550520,
            longitude=-46.633308
        )
        db.add(barbearia)
        db.commit()
        db.refresh(barbearia)
        print(f"✅ Barbearia criada: {barbearia.nome} (ID: {barbearia.id})")
    
    # 5. Criar serviços
    servico_barba = db.query(models.Servico).filter(
        models.Servico.barbearia_id == barbearia.id,
        models.Servico.nome == "Barba "
    ).first()
    
    if not servico_barba:
        servico_barba = models.Servico(
            nome="Barba ",
            descricao="Barba completa",
            valor=30.0,
            barbearia_id=barbearia.id,
            categoria="barba",
            duracao_minutos=30
        )
        db.add(servico_barba)
        db.commit()
        db.refresh(servico_barba)
        print(f"✅ Serviço criado: {servico_barba.nome} (ID: {servico_barba.id})")
    
    servico_sombrancelha = db.query(models.Servico).filter(
        models.Servico.barbearia_id == barbearia.id,
        models.Servico.nome == "Sombrancelha"
    ).first()
    
    if not servico_sombrancelha:
        servico_sombrancelha = models.Servico(
            nome="Sombrancelha",
            descricao="Sombrancelha",
            valor=30.0,
            barbearia_id=barbearia.id,
            categoria="sombrancelha",
            duracao_minutos=15
        )
        db.add(servico_sombrancelha)
        db.commit()
        db.refresh(servico_sombrancelha)
        print(f"✅ Serviço criado: {servico_sombrancelha.nome} (ID: {servico_sombrancelha.id})")
    
    # 6. Criar 5 agendamentos
    print("\n📋 Criando agendamentos...")
    
    # Apagar agendamentos antigos
    db.query(models.Chamado).delete()
    db.commit()
    
    # Agendamentos 1-4: PENDENTE (sem barbeiro)
    for i in range(1, 5):
        servico = servico_barba if i < 4 else servico_sombrancelha
        hora_inicio = datetime.now() + timedelta(hours=i)
        
        chamado = models.Chamado(
            cliente_id=cliente.id,
            servico_id=servico.id,
            barbearia_id=barbearia.id,
            barbeiro_id=None,
            status="pendente",
            data_hora_inicio=hora_inicio,
            data_hora_fim=hora_inicio + timedelta(minutes=servico.duracao_minutos),
            criado_em=datetime.now()
        )
        db.add(chamado)
    
    # Agendamento 5: CONFIRMADO (com barbeiro Allan)
    hora_inicio = datetime.now() + timedelta(hours=5)
    chamado_confirmado = models.Chamado(
        cliente_id=cliente.id,
        servico_id=servico_barba.id,
        barbearia_id=barbearia.id,
        barbeiro_id=barbeiro.id,
        status="confirmado",
        data_hora_inicio=hora_inicio,
        data_hora_fim=hora_inicio + timedelta(minutes=servico_barba.duracao_minutos),
        criado_em=datetime.now()
    )
    db.add(chamado_confirmado)
    
    db.commit()
    
    print("✅ 5 agendamentos criados:")
    print("   - IDs 1-4: Status PENDENTE (sem barbeiro)")
    print("   - ID 5: Status CONFIRMADO (barbeiro: Allan)")
    
    db.close()

if __name__ == "__main__":
    criar_dados_teste()
    print("\n✅ Dados de teste criados com sucesso!")
