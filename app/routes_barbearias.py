"""
Rotas para Barbearias - BarberMovie
Endpoints para listagem de barbearias próximas com filtro de aprovação
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
from typing import List
from datetime import datetime
from math import radians, sin, cos, sqrt, atan2

from app.database import get_db
from app.models import Usuario, Barbearia, Cadeira, StatusCadeira
from app.routes import get_current_user

router = APIRouter(prefix="/api/v1/barbearias", tags=["Barbearias"])


@router.get("/proximas")
def listar_barbearias_proximas(
    db: Session = Depends(get_db),
    usuario_atual = Depends(get_current_user),
    raio_km: float = 10.0
):
    """
    Lista barbearias próximas e aprovadas para clientes/barbeiros
    Filtro: apenas barbearias aprovadas (perfil_aprovado = True)
    Proximidade: até `raio_km` de distância (padrão: 10km)
    """
    
    # Validar que não é admin ou barbearia
    if usuario_atual.tipo not in ["cliente", "barbeiro"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Apenas clientes e barbeiros podem listar barbearias"
        )
    
    # Se usuario não tem localização, retornar lista vazia
    if not usuario_atual.latitude or not usuario_atual.longitude:
        return {
            "erro": "Localização não informada",
            "mensagem": "Por favor, configure sua localização no perfil",
            "barbearias": []
        }
    
    # Buscar todas as barbearias aprovadas
    barbearias_usuarios = db.query(Usuario).filter(
        Usuario.tipo == "barbearia",
        Usuario.perfil_aprovado == True
    ).all()
    
    barbearias_proximas = []
    
    for user in barbearias_usuarios:
        barbearia = db.query(Barbearia).filter(
            Barbearia.usuario_id == user.id
        ).first()

        if barbearia and user.latitude and user.longitude:
            cadeira_disponivel = db.query(Cadeira).filter(
                Cadeira.barbearia_id == barbearia.id,
                or_(
                    Cadeira.status == StatusCadeira.DISPONIVEL,
                    and_(
                        Cadeira.status == StatusCadeira.OCUPADA,
                        Cadeira.freelancer_id.is_(None)
                    )
                )
            ).first()

            # Calcular distância usando Haversine
            lat1, lon1 = radians(usuario_atual.latitude), radians(usuario_atual.longitude)
            lat2, lon2 = radians(user.latitude), radians(user.longitude)
            
            dlat = lat2 - lat1
            dlon = lon2 - lon1
            
            a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
            c = 2 * atan2(sqrt(a), sqrt(1-a))
            distancia_km = 6371 * c  # Raio da Terra em km
            
            # Apenas adicionar se está dentro do raio
            if distancia_km <= raio_km:
                barbearias_proximas.append({
                    "id": barbearia.id,
                    "usuario_id": user.id,
                    "nome": user.nome,
                    "email": user.email,
                    "telefone": user.telefone,
                    "endereco": barbearia.endereco,
                    "cidade": getattr(barbearia, "cidade", None),
                    "bairro": getattr(barbearia, "bairro", None),
                    "latitude": user.latitude,
                    "longitude": user.longitude,
                    "distancia_km": round(distancia_km, 2),
                    "logo_url": getattr(barbearia, "logo_url", None),
                    "descricao": getattr(barbearia, "descricao", None),
                    "categoria": getattr(barbearia, "categoria", None),
                    "criado_em": user.criado_em,
                    "aprovado_em": user.perfil_aprovado_em,
                    "cadeira_disponivel": cadeira_disponivel is not None
                })
    
    # Ordenar por distância (mais próximos primeiro)
    barbearias_proximas.sort(key=lambda x: x["distancia_km"])
    
    return {
        "total": len(barbearias_proximas),
        "raio_km": raio_km,
        "localizacao": {
            "latitude": usuario_atual.latitude,
            "longitude": usuario_atual.longitude
        },
        "barbearias": barbearias_proximas
    }


@router.get("/todas-aprovadas")
def listar_todas_barbearias_aprovadas(
    db: Session = Depends(get_db),
    usuario_atual = Depends(get_current_user)
):
    """
    Lista TODAS as barbearias aprovadas sem filtro de proximidade
    Útil para busca global
    """
    
    if usuario_atual.tipo not in ["cliente", "barbeiro"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Apenas clientes e barbeiros podem listar barbearias"
        )
    
    # Buscar todas as barbearias aprovadas
    barbearias_usuarios = db.query(Usuario).filter(
        Usuario.tipo == "barbearia",
        Usuario.perfil_aprovado == True
    ).all()
    
    barbearias = []
    for user in barbearias_usuarios:
        barbearia = db.query(Barbearia).filter(
            Barbearia.usuario_id == user.id
        ).first()
        
        if barbearia:
            cadeira_disponivel = db.query(Cadeira).filter(
                Cadeira.barbearia_id == barbearia.id,
                or_(
                    Cadeira.status == StatusCadeira.DISPONIVEL,
                    and_(
                        Cadeira.status == StatusCadeira.OCUPADA,
                        Cadeira.freelancer_id.is_(None)
                    )
                )
            ).first()

            # Calcular distância se ambas têm localização
            distancia_km = None
            if usuario_atual.latitude and usuario_atual.longitude and user.latitude and user.longitude:
                lat1, lon1 = radians(usuario_atual.latitude), radians(usuario_atual.longitude)
                lat2, lon2 = radians(user.latitude), radians(user.longitude)
                
                dlat = lat2 - lat1
                dlon = lon2 - lon1
                
                a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
                c = 2 * atan2(sqrt(a), sqrt(1-a))
                distancia_km = round(6371 * c, 2)
            
            barbearias.append({
                "id": barbearia.id,
                "usuario_id": user.id,
                "nome": user.nome,
                "email": user.email,
                "telefone": user.telefone,
                "endereco": barbearia.endereco,
                "cidade": getattr(barbearia, "cidade", None),
                "bairro": getattr(barbearia, "bairro", None),
                "latitude": user.latitude,
                "longitude": user.longitude,
                "distancia_km": distancia_km,
                "logo_url": getattr(barbearia, "logo_url", None),
                "descricao": getattr(barbearia, "descricao", None),
                "categoria": getattr(barbearia, "categoria", None),
                "criado_em": user.criado_em,
                "aprovado_em": user.perfil_aprovado_em,
                "cadeira_disponivel": cadeira_disponivel is not None
            })
    
    # Ordenar por distância se disponível
    if usuario_atual.latitude and usuario_atual.longitude:
        barbearias.sort(key=lambda x: x["distancia_km"] if x["distancia_km"] else float('inf'))
    
    return {
        "total": len(barbearias),
        "barbearias": barbearias
    }


@router.get("/{barbearia_id}")
def obter_detalhes_barbearia(
    barbearia_id: int,
    db: Session = Depends(get_db),
    usuario_atual = Depends(get_current_user)
):
    """
    Obtém detalhes de uma barbearia específica
    Verifica se está aprovada antes de retornar
    """
    
    barbearia = db.query(Barbearia).filter(
        Barbearia.id == barbearia_id
    ).first()
    
    if not barbearia:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Barbearia não encontrada"
        )
    
    user = barbearia.usuario
    
    # Verificar se está aprovada
    if not user.perfil_aprovado:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Barbearia não está aprovada"
        )
    
    # Calcular distância
    distancia_km = None
    if usuario_atual.latitude and usuario_atual.longitude and user.latitude and user.longitude:
        lat1, lon1 = radians(usuario_atual.latitude), radians(usuario_atual.longitude)
        lat2, lon2 = radians(user.latitude), radians(user.longitude)
        
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        
        a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
        c = 2 * atan2(sqrt(a), sqrt(1-a))
        distancia_km = round(6371 * c, 2)
    
    return {
        "id": barbearia.id,
        "usuario_id": user.id,
        "nome": user.nome,
        "email": user.email,
        "telefone": user.telefone,
        "endereco": barbearia.endereco,
        "cidade": getattr(barbearia, "cidade", None),
        "bairro": getattr(barbearia, "bairro", None),
        "distancia_km": distancia_km,
        "latitude": user.latitude,
        "longitude": user.longitude,
        "logo_url": getattr(barbearia, "logo_url", None),
        "descricao": getattr(barbearia, "descricao", None),
        "categoria": getattr(barbearia, "categoria", None),
        "criado_em": user.criado_em,
        "aprovado_em": user.perfil_aprovado_em
    }
