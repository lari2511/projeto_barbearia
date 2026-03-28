from app.database import SessionLocal
from app import models
from datetime import datetime

db = SessionLocal()

# Serviços padrão de barbearia
servicos_teste = [
    {"nome": "Corte Masculino", "descricao": "Corte clássico de cabelo", "categoria": "corte", "valor": 35.00, "duracao_minutos": 30, "barbearia_id": 1},
    {"nome": "Barba Completa", "descricao": "Barba com navalha e acabamento", "categoria": "barba", "valor": 25.00, "duracao_minutos": 20, "barbearia_id": 1},
    {"nome": "Corte + Barba", "descricao": "Corte e barba completa", "categoria": "combo", "valor": 50.00, "duracao_minutos": 45, "barbearia_id": 1},
    {"nome": "Cabelo + Barba Degradê", "descricao": "Corte degradê com barba", "categoria": "combo", "valor": 60.00, "duracao_minutos": 50, "barbearia_id": 1},
    {"nome": "Hidratação Capilar", "descricao": "Tratamento de hidratação para cabelo", "categoria": "tratamento", "valor": 40.00, "duracao_minutos": 30, "barbearia_id": 1},
]

for serv in servicos_teste:
    novo_servico = models.Servico(
        nome=serv["nome"],
        descricao=serv["descricao"],
        categoria=serv["categoria"],
        valor=serv["valor"],
        duracao_minutos=serv["duracao_minutos"],
        barbearia_id=serv["barbearia_id"]
    )
    db.add(novo_servico)

db.commit()
print(f"✅ {len(servicos_teste)} serviços criados com sucesso!")

# Verificar
servicos = db.query(models.Servico).all()
for s in servicos:
    print(f"  - {s.nome}: R$ {s.valor}")

db.close()
