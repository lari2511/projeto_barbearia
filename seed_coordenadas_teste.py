#!/usr/bin/env python
"""Criar dados de teste com coordenadas para validar mapa"""
from app.database import SessionLocal
from app import models
from datetime import datetime

db = SessionLocal()

try:
    # Procurar um chamado CONFIRMADO
    chamado = db.query(models.Chamado).filter(
        models.Chamado.status == models.StatusAgendamento.CONFIRMADO.value
    ).first()
    
    if not chamado:
        print("❌ Nenhum chamado CONFIRMADO encontrado")
        db.close()
        exit(1)
    
    print(f"✓ Chamado: id={chamado.id}, status={chamado.status}")
    
    # Verificar se já há AgendamentoAtivo
    ativo = db.query(models.AgendamentoAtivo).filter(
        models.AgendamentoAtivo.chamado_id == chamado.id
    ).first()
    
    if ativo:
        print(f"✓ AgendamentoAtivo já existe: {ativo.id}")
        # Atualizar coordenadas
        ativo.cliente_lat = -23.5493
        ativo.cliente_lon = -46.4951
        ativo.barbeiro_lat = -23.5495
        ativo.barbeiro_lon = -46.4950
    else:
        # Criar novo AgendamentoAtivo
        ativo = models.AgendamentoAtivo(
            chamado_id=chamado.id,
            cliente_lat=-23.5493,
            cliente_lon=-46.4951,
            barbeiro_lat=-23.5495,
            barbeiro_lon=-46.4950,
        )
        print(f"✓ Criando AgendamentoAtivo novo")
    
    db.add(ativo)
    db.commit()
    db.refresh(ativo)
    
    print(f"\n✓ Coordenadas atualizadas:")
    print(f"  Cliente: ({ativo.cliente_lat}, {ativo.cliente_lon})")
    print(f"  Barbeiro: ({ativo.barbeiro_lat}, {ativo.barbeiro_lon})")
    
finally:
    db.close()
