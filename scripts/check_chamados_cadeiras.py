import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from app.database import SessionLocal
from app import models

db = SessionLocal()
chamados = db.query(models.Chamado).order_by(models.Chamado.criado_em.desc()).limit(20).all()
for c in chamados:
    cliente = db.query(models.Usuario).filter(models.Usuario.id == c.cliente_id).first()
    cadeira = db.query(models.Cadeira).filter(models.Cadeira.id == c.cadeira_id).first() if c.cadeira_id else None
    print(f"Chamado {c.id} - cliente: {cliente.nome if cliente else c.cliente_id} - status: {c.status} - cadeira_id: {c.cadeira_id} - cadeira_numero: {cadeira.numero if cadeira else None}")

db.close()
