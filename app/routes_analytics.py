"""
Rotas para Analytics e Histórico de Avaliações
Dashboard com estatísticas de reviews, ratings e análise de reputação
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import Optional, List
from pydantic import BaseModel
from datetime import datetime, timedelta

from app.database import get_db
from app.models import Usuario, Freelancer, Barbearia, AvaliacaoFreelancer, AvaliacaoBarbearia
from app.routes import get_current_user

router = APIRouter(prefix="/api/v1/analytics", tags=["Analytics"])

# ============================================================================
# SCHEMAS
# ============================================================================

class AvaliacaoDetalhada(BaseModel):
    id: int
    avaliador_nome: str
    nota: int
    comentario: Optional[str]
    criado_em: datetime
    tipo: str  # freelancer, barbearia
    
    class Config:
        from_attributes = True

class EstatisticasAvaliacao(BaseModel):
    media_notas: float
    total_avaliacoes: int
    distribuicao_notas: dict  # {5: 10, 4: 8, 3: 2, 2: 1, 1: 0}
    avaliacoes_ultimo_mes: int
    tendencia: str  # "subindo", "estavel", "caindo"
    
class AvaliacaoResumo(BaseModel):
    id: int
    media: float
    total: int
    distribuicao: dict

# ============================================================================
# ENDPOINTS PARA BARBEIRO
# ============================================================================

@router.get("/barbeiro/minhas-avaliacoes", response_model=List[AvaliacaoDetalhada])
def listar_minhas_avaliacoes(
    limite: int = 50,
    offset: int = 0,
    db: Session = Depends(get_db),
    usuario = Depends(get_current_user)
):
    """Lista todas as avaliações recebidas pelo barbeiro"""
    if usuario.tipo != "barbeiro":
        raise HTTPException(status_code=403, detail="Apenas barbeiros podem acessar")

    freelancer = db.query(Freelancer).filter(Freelancer.usuario_id == usuario.id).first()
    if not freelancer:
        return []
    
    avaliacoes = db.query(
        AvaliacaoFreelancer,
        Usuario.nome.label("avaliador_nome")
    ).join(
        Usuario, AvaliacaoFreelancer.avaliador_id == Usuario.id
    ).filter(
        AvaliacaoFreelancer.freelancer_id == freelancer.id
    ).order_by(
        AvaliacaoFreelancer.criado_em.desc()
    ).offset(offset).limit(limite).all()

    return [
        {
            "id": av.id,
            "avaliador_nome": avaliador_nome or "Usuário",
            "nota": av.nota,
            "comentario": av.comentario,
            "criado_em": av.criado_em,
            "tipo": "freelancer"
        }
        for av, avaliador_nome in avaliacoes
    ]

@router.get("/barbeiro/estatisticas", response_model=EstatisticasAvaliacao)
def obter_estatisticas_barbeiro(
    db: Session = Depends(get_db),
    usuario = Depends(get_current_user)
):
    """Obtém estatísticas completas de avaliações do barbeiro"""
    if usuario.tipo != "barbeiro":
        raise HTTPException(status_code=403, detail="Apenas barbeiros podem acessar")

    freelancer = db.query(Freelancer).filter(Freelancer.usuario_id == usuario.id).first()
    if not freelancer:
        return {
            "media_notas": 0,
            "total_avaliacoes": 0,
            "distribuicao_notas": {1: 0, 2: 0, 3: 0, 4: 0, 5: 0},
            "avaliacoes_ultimo_mes": 0,
            "tendencia": "estavel"
        }
    
    # Total e média
    resultado = db.query(
        func.avg(AvaliacaoFreelancer.nota).label('media'),
        func.count(AvaliacaoFreelancer.id).label('total')
    ).filter(AvaliacaoFreelancer.freelancer_id == freelancer.id).first()
    
    media = float(resultado.media) if resultado.media else 0
    total = resultado.total or 0
    
    # Distribuição de notas
    distribuicao_query = db.query(
        AvaliacaoFreelancer.nota,
        func.count(AvaliacaoFreelancer.id).label('count')
    ).filter(AvaliacaoFreelancer.freelancer_id == freelancer.id).group_by(AvaliacaoFreelancer.nota).all()
    
    distribuicao = {
        1: 0, 2: 0, 3: 0, 4: 0, 5: 0
    }
    for nota, count in distribuicao_query:
        distribuicao[nota] = count
    
    # Avaliações do último mês
    mes_passado = datetime.utcnow() - timedelta(days=30)
    avaliacoes_mes = db.query(AvaliacaoFreelancer).filter(
        AvaliacaoFreelancer.freelancer_id == freelancer.id,
        AvaliacaoFreelancer.criado_em >= mes_passado
    ).count()
    
    # Determinar tendência
    mes_anterior = mes_passado - timedelta(days=30)
    avaliacoes_mes_anterior = db.query(AvaliacaoFreelancer).filter(
        AvaliacaoFreelancer.freelancer_id == freelancer.id,
        AvaliacaoFreelancer.criado_em >= mes_anterior,
        AvaliacaoFreelancer.criado_em < mes_passado
    ).count()
    
    if avaliacoes_mes > avaliacoes_mes_anterior * 1.2:
        tendencia = "subindo"
    elif avaliacoes_mes < avaliacoes_mes_anterior * 0.8:
        tendencia = "caindo"
    else:
        tendencia = "estavel"
    
    return {
        "media_notas": media,
        "total_avaliacoes": total,
        "distribuicao_notas": distribuicao,
        "avaliacoes_ultimo_mes": avaliacoes_mes,
        "tendencia": tendencia
    }

@router.get("/barbeiro/resumo")
def obter_resumo_barbeiro(
    db: Session = Depends(get_db),
    usuario = Depends(get_current_user)
):
    """Resumo rápido da reputação do barbeiro"""
    if usuario.tipo != "barbeiro":
        raise HTTPException(status_code=403, detail="Apenas barbeiros podem acessar")

    freelancer = db.query(Freelancer).filter(Freelancer.usuario_id == usuario.id).first()
    if not freelancer:
        return {
            "media": 0,
            "total": 0,
            "cinco_estrelas": 0,
            "percentual_5_estrelas": 0
        }
    
    resultado = db.query(
        func.avg(AvaliacaoFreelancer.nota).label('media'),
        func.count(AvaliacaoFreelancer.id).label('total')
    ).filter(AvaliacaoFreelancer.freelancer_id == freelancer.id).first()
    
    media = float(resultado.media) if resultado.media else 0
    total = resultado.total or 0
    
    # Número de 5 estrelas
    cinco_estrelas = db.query(AvaliacaoFreelancer).filter(
        AvaliacaoFreelancer.freelancer_id == freelancer.id,
        AvaliacaoFreelancer.nota == 5
    ).count()
    
    return {
        "media": round(media, 1),
        "total": total,
        "cinco_estrelas": cinco_estrelas,
        "percentual_5_estrelas": round((cinco_estrelas / total * 100) if total > 0 else 0, 1)
    }

# ============================================================================
# ENDPOINTS PARA BARBEARIA
# ============================================================================

@router.get("/barbearia/minhas-avaliacoes", response_model=List[AvaliacaoDetalhada])
def listar_minhas_avaliacoes_barbearia(
    limite: int = 50,
    offset: int = 0,
    db: Session = Depends(get_db),
    usuario = Depends(get_current_user)
):
    """Lista todas as avaliações recebidas pela barbearia"""
    if usuario.tipo != "barbearia":
        raise HTTPException(status_code=403, detail="Apenas barbearias podem acessar")

    barbearia = db.query(Barbearia).filter(Barbearia.usuario_id == usuario.id).first()
    if not barbearia:
        return []
    
    avaliacoes = db.query(
        AvaliacaoBarbearia,
        Usuario.nome.label("avaliador_nome")
    ).join(
        Usuario, AvaliacaoBarbearia.avaliador_id == Usuario.id
    ).filter(
        AvaliacaoBarbearia.barbearia_id == barbearia.id
    ).order_by(
        AvaliacaoBarbearia.criado_em.desc()
    ).offset(offset).limit(limite).all()

    return [
        {
            "id": av.id,
            "avaliador_nome": avaliador_nome or "Usuário",
            "nota": av.nota,
            "comentario": av.comentario,
            "criado_em": av.criado_em,
            "tipo": "barbearia"
        }
        for av, avaliador_nome in avaliacoes
    ]

@router.get("/barbearia/estatisticas", response_model=EstatisticasAvaliacao)
def obter_estatisticas_barbearia(
    db: Session = Depends(get_db),
    usuario = Depends(get_current_user)
):
    """Obtém estatísticas completas de avaliações da barbearia"""
    if usuario.tipo != "barbearia":
        raise HTTPException(status_code=403, detail="Apenas barbearias podem acessar")

    barbearia = db.query(Barbearia).filter(Barbearia.usuario_id == usuario.id).first()
    if not barbearia:
        return {
            "media_notas": 0,
            "total_avaliacoes": 0,
            "distribuicao_notas": {1: 0, 2: 0, 3: 0, 4: 0, 5: 0},
            "avaliacoes_ultimo_mes": 0,
            "tendencia": "estavel"
        }
    
    resultado = db.query(
        func.avg(AvaliacaoBarbearia.nota).label('media'),
        func.count(AvaliacaoBarbearia.id).label('total')
    ).filter(AvaliacaoBarbearia.barbearia_id == barbearia.id).first()
    
    media = float(resultado.media) if resultado.media else 0
    total = resultado.total or 0
    
    # Distribuição de notas
    distribuicao_query = db.query(
        AvaliacaoBarbearia.nota,
        func.count(AvaliacaoBarbearia.id).label('count')
    ).filter(AvaliacaoBarbearia.barbearia_id == barbearia.id).group_by(AvaliacaoBarbearia.nota).all()
    
    distribuicao = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}
    for nota, count in distribuicao_query:
        distribuicao[nota] = count
    
    # Avaliações do último mês
    mes_passado = datetime.utcnow() - timedelta(days=30)
    avaliacoes_mes = db.query(AvaliacaoBarbearia).filter(
        AvaliacaoBarbearia.barbearia_id == barbearia.id,
        AvaliacaoBarbearia.criado_em >= mes_passado
    ).count()
    
    # Tendência
    mes_anterior = mes_passado - timedelta(days=30)
    avaliacoes_mes_anterior = db.query(AvaliacaoBarbearia).filter(
        AvaliacaoBarbearia.barbearia_id == barbearia.id,
        AvaliacaoBarbearia.criado_em >= mes_anterior,
        AvaliacaoBarbearia.criado_em < mes_passado
    ).count()
    
    if avaliacoes_mes > avaliacoes_mes_anterior * 1.2:
        tendencia = "subindo"
    elif avaliacoes_mes < avaliacoes_mes_anterior * 0.8:
        tendencia = "caindo"
    else:
        tendencia = "estavel"
    
    return {
        "media_notas": media,
        "total_avaliacoes": total,
        "distribuicao_notas": distribuicao,
        "avaliacoes_ultimo_mes": avaliacoes_mes,
        "tendencia": tendencia
    }

@router.get("/barbearia/resumo")
def obter_resumo_barbearia(
    db: Session = Depends(get_db),
    usuario = Depends(get_current_user)
):
    """Resumo rápido da reputação da barbearia"""
    if usuario.tipo != "barbearia":
        raise HTTPException(status_code=403, detail="Apenas barbearias podem acessar")

    barbearia = db.query(Barbearia).filter(Barbearia.usuario_id == usuario.id).first()
    if not barbearia:
        return {
            "media": 0,
            "total": 0,
            "cinco_estrelas": 0,
            "percentual_5_estrelas": 0
        }
    
    resultado = db.query(
        func.avg(AvaliacaoBarbearia.nota).label('media'),
        func.count(AvaliacaoBarbearia.id).label('total')
    ).filter(AvaliacaoBarbearia.barbearia_id == barbearia.id).first()
    
    media = float(resultado.media) if resultado.media else 0
    total = resultado.total or 0
    
    cinco_estrelas = db.query(AvaliacaoBarbearia).filter(
        AvaliacaoBarbearia.barbearia_id == barbearia.id,
        AvaliacaoBarbearia.nota == 5
    ).count()
    
    return {
        "media": round(media, 1),
        "total": total,
        "cinco_estrelas": cinco_estrelas,
        "percentual_5_estrelas": round((cinco_estrelas / total * 100) if total > 0 else 0, 1)
    }
