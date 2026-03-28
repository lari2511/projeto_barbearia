"""Teste do endpoint barbeiros próximos"""
import sys
sys.path.append('.')

from app.database import SessionLocal
from app import models
from sqlalchemy import or_
from datetime import datetime

db = SessionLocal()

try:
    print("=== Testando query com or_() ===\n")
    
    agora_filtro = datetime.now()
    print(f"Data/hora atual: {agora_filtro}\n")
    
    barbeiros = db.query(models.Usuario).filter(
        models.Usuario.tipo == "barbeiro",
        models.Usuario.perfil_aprovado == True,
        models.Usuario.disponivel == True,
        models.Usuario.latitude.isnot(None),
        models.Usuario.longitude.isnot(None),
        or_(
            models.Usuario.ocupado_ate.is_(None),
            models.Usuario.ocupado_ate <= agora_filtro
        )
    ).all()
    
    print(f"✅ Query executada com sucesso!")
    print(f"📊 Encontrados: {len(barbeiros)} barbeiro(s)\n")
    
    for b in barbeiros:
        print(f"Barbeiro: {b.nome} ({b.email})")
        print(f"  Lat/Lon: {b.latitude}, {b.longitude}")
        print(f"  Disponível: {b.disponivel}")
        print(f"  Ocupado até: {b.ocupado_ate}\n")
        
except Exception as e:
    print(f"❌ Erro: {type(e).__name__}: {e}")
    import traceback
    traceback.print_exc()
finally:
    db.close()
