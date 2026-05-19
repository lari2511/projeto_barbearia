from app.database import SessionLocal
from app import models

db = SessionLocal()

# Adicionar coordenadas para o cliente (ID 3 - lari.nascimento20148@gmail.com)
cliente = db.query(models.Usuario).filter(models.Usuario.id == 3).first()
if cliente:
    cliente.latitude = -23.5515
    cliente.longitude = -46.6343
    db.commit()
    print(f'✓ Coordenadas adicionadas para cliente {cliente.nome}: ({cliente.latitude}, {cliente.longitude})')
else:
    print('✗ Cliente ID 3 não encontrado')

# Adicionar coordenadas para a barbearia (ID 1 - Allan Siqueira)
barbearia = db.query(models.Barbearia).filter(models.Barbearia.id == 1).first()
if barbearia:
    barbearia.latitude = -23.5505
    barbearia.longitude = -46.6333
    db.commit()
    print(f'✓ Coordenadas adicionadas para barbearia {barbearia.nome}: ({barbearia.latitude}, {barbearia.longitude})')
else:
    print('✗ Barbearia ID 1 não encontrada')
