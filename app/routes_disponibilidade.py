# --- ARQUIVO: app/routes_disponibilidade.py ---
# Rotas para disponibilidade imediata (modo "Uber")

from datetime import datetime, timedelta
import math
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from . import models, schemas
from .database import get_db
from .routes import get_current_user

router = APIRouter()


def _parse_datetime(value: Optional[str], default: datetime) -> datetime:
    if not value:
        return default
    try:
        return datetime.fromisoformat(value)
    except Exception:
        raise HTTPException(status_code=400, detail="Data/hora inválida. Use ISO 8601.")


def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    # Distância aproximada em km
    R = 6371
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi/2)**2 + math.cos(phi1)*math.cos(phi2)*math.sin(dlambda/2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    return R * c


@router.post("/disponibilidade/abrir", response_model=schemas.DisponibilidadeResponse)
def abrir_disponibilidade(
    payload: schemas.DisponibilidadeCreate,
    current_user: models.Usuario = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Abre uma janela de disponibilidade imediata para barbeiro ou barbearia."""
    if current_user.tipo not in ("barbeiro", "barbearia"):
        raise HTTPException(status_code=403, detail="Apenas barbeiro ou barbearia podem abrir disponibilidade")

    agora = datetime.utcnow()
    inicio = _parse_datetime(payload.inicio, agora)
    fim = _parse_datetime(payload.fim, agora + timedelta(hours=2))

    if fim <= inicio:
        raise HTTPException(status_code=400, detail="Fim deve ser depois do início")

    if payload.raio_km <= 0:
        raise HTTPException(status_code=400, detail="Raio deve ser maior que zero")

    disp = models.Disponibilidade(
        usuario_id=current_user.id,
        inicio=inicio,
        fim=fim,
        raio_km=payload.raio_km,
        ativo=True,
    )
    db.add(disp)
    db.commit()
    db.refresh(disp)

    return schemas.DisponibilidadeResponse(
        id=disp.id,
        usuario_id=current_user.id,
        inicio=disp.inicio,
        fim=disp.fim,
        raio_km=disp.raio_km,
        ativo=disp.ativo,
        criado_em=disp.criado_em,
        nome=current_user.nome,
        tipo=current_user.tipo,
        latitude=current_user.latitude,
        longitude=current_user.longitude,
    )


@router.post("/disponibilidade/fechar")
def fechar_disponibilidade(
    current_user: models.Usuario = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Fecha as disponibilidades ativas do usuário."""
    atualizadas = db.query(models.Disponibilidade).filter(
        models.Disponibilidade.usuario_id == current_user.id,
        models.Disponibilidade.ativo == True,
    ).update({"ativo": False})
    db.commit()
    return {"fechadas": atualizadas}


@router.get("/disponibilidade/disponiveis", response_model=List[schemas.DisponibilidadeResponse])
def listar_disponiveis(
    lat: float = Query(..., description="Latitude do cliente"),
    lon: float = Query(..., description="Longitude do cliente"),
    janela_horas: float = Query(2.0, description="Janela futura em horas"),
    db: Session = Depends(get_db),
):
    """
    Lista profissionais/barbearias disponíveis agora ou até a janela futura.
    Filtra por raio definido pelo profissional e distância ao cliente.
    """
    agora = datetime.utcnow()
    limite = agora + timedelta(hours=janela_horas)

    disponibilidades = (
        db.query(models.Disponibilidade, models.Usuario)
        .join(models.Usuario, models.Usuario.id == models.Disponibilidade.usuario_id)
        .filter(
            models.Disponibilidade.ativo == True,
            models.Disponibilidade.inicio <= limite,
            models.Disponibilidade.fim >= agora,
            models.Usuario.tipo.in_(["barbeiro", "barbearia"]),
            models.Usuario.latitude.isnot(None),
            models.Usuario.longitude.isnot(None),
        )
        .all()
    )

    resultados = []
    for disp, user in disponibilidades:
        dist = _haversine_km(lat, lon, user.latitude, user.longitude)
        if dist <= disp.raio_km:
            resultados.append(
                schemas.DisponibilidadeResponse(
                    id=disp.id,
                    usuario_id=user.id,
                    inicio=disp.inicio,
                    fim=disp.fim,
                    raio_km=disp.raio_km,
                    ativo=disp.ativo,
                    criado_em=disp.criado_em,
                    nome=user.nome,
                    tipo=user.tipo,
                    latitude=user.latitude,
                    longitude=user.longitude,
                    distancia_km=round(dist, 2),
                )
            )

    # Ordenar por distância
    resultados.sort(key=lambda r: r.distancia_km if r.distancia_km is not None else 9999)
    return resultados
