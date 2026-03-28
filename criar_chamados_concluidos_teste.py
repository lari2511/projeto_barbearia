"""
Script para criar chamados de teste com status CONCLUÍDO
"""
from app.database import SessionLocal
from app import models
from datetime import datetime

db = SessionLocal()

# IDs de teste
barbearia_id = 2
cliente_id = 1
barbeiro_id = 2

# Buscar um serviço de teste ou criar
servico = db.query(models.Servico).filter(
    models.Servico.barbearia_id == barbearia_id
).first()

if not servico:
    print("Criando serviço de teste...")
    servico = models.Servico(
        barbearia_id=barbearia_id,
        nome="Corte Simples",
        categoria="corte",
        valor=50.0
    )
    db.add(servico)
    db.commit()

servico_id = servico.id
print(f"Usando serviço ID: {servico_id}")
print("Criando chamados de teste com status CONCLUÍDO...")

# Criar alguns chamados já concluídos
chamados_teste = [
    {
        "barbearia_id": barbearia_id,
        "cliente_id": cliente_id,
        "barbeiro_id": barbeiro_id,
        "servico_id": servico_id,
        "status": "concluido",
        "observacao": "Corte Simples",
        "criado_em": datetime.now(),
        "concluido_em": datetime.now()
    },
    {
        "barbearia_id": barbearia_id,
        "cliente_id": cliente_id,
        "barbeiro_id": barbeiro_id,
        "servico_id": servico_id,
        "status": "concluido",
        "observacao": "Barba",
        "criado_em": datetime.now(),
        "concluido_em": datetime.now()
    },
    {
        "barbearia_id": barbearia_id,
        "cliente_id": cliente_id,
        "barbeiro_id": barbeiro_id,
        "servico_id": servico_id,
        "status": "concluido",
        "observacao": "Corte + Barba",
        "criado_em": datetime.now(),
        "concluido_em": datetime.now()
    }
]

for chamado_data in chamados_teste:
    chamado = models.Chamado(**chamado_data)
    db.add(chamado)
    print(f"  ✅ Chamado criado: {chamado_data['observacao']}")

db.commit()
print("\n✅ Todos os chamados foram criados com sucesso!")
print(f"Total: {len(chamados_teste)} chamados")

db.close()
