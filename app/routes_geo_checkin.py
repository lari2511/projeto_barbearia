"""
Sistema de Check-in Automático por Geolocalização
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import and_
from datetime import datetime, timedelta
from pydantic import BaseModel
from typing import Optional
import math

from .database import get_db
from .models import Usuario, Barbearia, Chamado, Cadeira, StatusAgendamento, StatusCadeira
from .routes import get_current_user, oauth2_scheme

router = APIRouter(prefix="/api/v1/geo", tags=["Geolocalização"])


class LocalizacaoAtual(BaseModel):
    latitude: float
    longitude: float


def calcular_distancia(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calcula distância em metros entre duas coordenadas usando fórmula de Haversine
    """
    R = 6371000  # Raio da Terra em metros
    
    lat1_rad = math.radians(lat1)
    lat2_rad = math.radians(lat2)
    delta_lat = math.radians(lat2 - lat1)
    delta_lon = math.radians(lon2 - lon1)
    
    a = (math.sin(delta_lat / 2) ** 2 +
         math.cos(lat1_rad) * math.cos(lat2_rad) *
         math.sin(delta_lon / 2) ** 2)
    
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    
    distancia = R * c
    return distancia


@router.post("/check-proximity")
def verificar_proximidade_e_checkin(
    localizacao: LocalizacaoAtual,
    db: Session = Depends(get_db),
    usuario_atual = Depends(get_current_user)
):
    """
    Verifica se barbeiro está próximo de barbearia com agendamento ativo
    e faz check-in automático alocando cadeira
    """
    # 1. Verificar se é barbeiro
    if usuario_atual.tipo != 'barbeiro':
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Apenas barbeiros podem fazer check-in automático"
        )
    
    # 2. Buscar agendamentos CONFIRMADOS do barbeiro para hoje
    hoje = datetime.utcnow().date()
    amanha = hoje + timedelta(days=1)
    
    agendamentos = db.query(Chamado).filter(
        and_(
            Chamado.barbeiro_id == usuario_atual.id,
            Chamado.status == StatusAgendamento.CONFIRMADO.value,
            Chamado.data_hora_inicio >= datetime.combine(hoje, datetime.min.time()),
            Chamado.data_hora_inicio < datetime.combine(amanha, datetime.min.time())
        )
    ).all()
    
    if not agendamentos:
        return {
            "proximo": False,
            "mensagem": "Nenhum agendamento confirmado para hoje",
            "agendamentos_proximos": []
        }
    
    # 3. Verificar proximidade com cada barbearia
    checkins_realizados = []
    barbearias_proximas = []
    
    for agendamento in agendamentos:
        barbearia = db.query(Barbearia).filter(
            Barbearia.id == agendamento.barbearia_id
        ).first()
        
        if not barbearia or not barbearia.latitude or not barbearia.longitude:
            continue
        
        # Calcular distância
        distancia = calcular_distancia(
            localizacao.latitude,
            localizacao.longitude,
            barbearia.latitude,
            barbearia.longitude
        )
        
        # Raio de 100 metros para check-in automático
        RAIO_CHECKIN = 100  # metros
        
        if distancia <= RAIO_CHECKIN:
            # 4. Barbeiro está próximo! Fazer check-in automático
            
            # Verificar se já fez check-in (já tem cadeira alocada)
            cadeira_existente = db.query(Cadeira).filter(
                and_(
                    Cadeira.chamado_id == agendamento.id,
                    Cadeira.freelancer_id == usuario_atual.id,
                    Cadeira.status == StatusCadeira.OCUPADA
                )
            ).first()
            
            if cadeira_existente:
                # Já está em uma cadeira
                barbearias_proximas.append({
                    "barbearia": barbearia.nome,
                    "distancia": round(distancia, 1),
                    "ja_checkin": True,
                    "cadeira_numero": cadeira_existente.numero,
                    "status": "Você já está na cadeira"
                })
                continue
            
            # Buscar cadeira disponível ou criar uma
            cadeira = db.query(Cadeira).filter(
                and_(
                    Cadeira.barbearia_id == barbearia.id,
                    Cadeira.status == StatusCadeira.DISPONIVEL
                )
            ).first()
            
            if not cadeira:
                # Criar nova cadeira
                numero_max = db.query(Cadeira).filter(
                    Cadeira.barbearia_id == barbearia.id
                ).count()
                
                cadeira = Cadeira(
                    barbearia_id=barbearia.id,
                    numero=numero_max + 1,
                    status=StatusCadeira.DISPONIVEL
                )
                db.add(cadeira)
                db.flush()
            
            # 5. Alocar cadeira para o agendamento
            cadeira.freelancer_id = usuario_atual.id
            cadeira.chamado_id = agendamento.id
            cadeira.status = StatusCadeira.OCUPADA
            cadeira.ocupada_em = datetime.utcnow()
            
            # 6. Marcar barbeiro como presente
            usuario_atual.presente_em_local = True
            usuario_atual.barbearia_atual_id = barbearia.id
            usuario_atual.horario_chegada = datetime.utcnow()
            
            db.commit()
            db.refresh(cadeira)
            
            checkins_realizados.append({
                "barbearia": barbearia.nome,
                "cadeira_numero": cadeira.numero,
                "distancia": round(distancia, 1),
                "cliente": agendamento.cliente.nome if agendamento.cliente else "Cliente não identificado",
                "horario_servico": agendamento.data_hora_inicio.strftime("%H:%M")
            })
        else:
            # Ainda não está próximo o suficiente
            barbearias_proximas.append({
                "barbearia": barbearia.nome,
                "distancia": round(distancia, 1),
                "necessario": RAIO_CHECKIN,
                "status": f"Você está a {round(distancia, 1)}m. Aproxime-se mais {round(distancia - RAIO_CHECKIN, 1)}m."
            })
    
    if checkins_realizados:
        return {
            "checkin_automatico": True,
            "mensagem": "✅ Check-in automático realizado!",
            "checkins": checkins_realizados
        }
    
    if barbearias_proximas:
        return {
            "proximo": True,
            "mensagem": "Você está próximo, mas ainda não no raio de check-in",
            "barbearias": barbearias_proximas
        }
    
    return {
        "proximo": False,
        "mensagem": "Nenhum agendamento próximo encontrado",
        "agendamentos_proximos": []
    }


@router.post("/checkout")
def fazer_checkout(
    db: Session = Depends(get_db),
    usuario_atual = Depends(get_current_user)
):
    """
    Libera a cadeira quando barbeiro sai/termina serviço
    """
    if usuario_atual.tipo != 'barbeiro':
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Apenas barbeiros podem fazer checkout"
        )
    
    # Buscar cadeira ocupada pelo barbeiro
    cadeiras = db.query(Cadeira).filter(
        and_(
            Cadeira.freelancer_id == usuario_atual.id,
            Cadeira.status == StatusCadeira.OCUPADA
        )
    ).all()
    
    if not cadeiras:
        return {
            "checkout": False,
            "mensagem": "Você não está em nenhuma cadeira no momento"
        }
    
    cadeiras_liberadas = []
    
    for cadeira in cadeiras:
        # Liberar cadeira
        cadeira.status = StatusCadeira.DISPONIVEL
        cadeira.freelancer_id = None
        cadeira.chamado_id = None
        cadeira.liberada_em = datetime.utcnow()
        
        barbearia = cadeira.barbearia
        cadeiras_liberadas.append({
            "barbearia": barbearia.nome if barbearia else "Desconhecida",
            "cadeira_numero": cadeira.numero
        })
    
    # Atualizar status do barbeiro
    usuario_atual.presente_em_local = False
    usuario_atual.barbearia_atual_id = None
    usuario_atual.horario_saida = datetime.utcnow()
    
    db.commit()
    
    return {
        "checkout": True,
        "mensagem": "✅ Checkout realizado com sucesso!",
        "cadeiras_liberadas": cadeiras_liberadas
    }
