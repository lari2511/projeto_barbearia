"""
Helpers compartilhados do sistema de avaliacoes (Etapa 6).

Fonte unica de verdade: models.AvaliacaoFreelancer e models.AvaliacaoBarbearia.
A tabela generica models.Avaliacao ficou legada e nao recebe mais escrita.
"""

from sqlalchemy import func
from sqlalchemy.orm import Session

from app import models


def _visivel_freelancer():
    return models.AvaliacaoFreelancer.bloqueada_por_admin.isnot(True)


def _visivel_barbearia():
    return models.AvaliacaoBarbearia.bloqueada_por_admin.isnot(True)


def resumo_freelancer(db: Session, freelancer_id: int) -> dict:
    """Media e total de avaliacoes visiveis de um freelancer (por Freelancer.id)."""
    media = db.query(func.avg(models.AvaliacaoFreelancer.nota)).filter(
        models.AvaliacaoFreelancer.freelancer_id == freelancer_id,
        _visivel_freelancer(),
    ).scalar()
    total = db.query(func.count(models.AvaliacaoFreelancer.id)).filter(
        models.AvaliacaoFreelancer.freelancer_id == freelancer_id,
        _visivel_freelancer(),
    ).scalar()
    return {"media": round(float(media), 1) if media else 0, "total": int(total or 0)}


def resumo_barbearia(db: Session, barbearia_id: int) -> dict:
    """Media e total de avaliacoes visiveis de uma barbearia (por Barbearia.id)."""
    media = db.query(func.avg(models.AvaliacaoBarbearia.nota)).filter(
        models.AvaliacaoBarbearia.barbearia_id == barbearia_id,
        _visivel_barbearia(),
    ).scalar()
    total = db.query(func.count(models.AvaliacaoBarbearia.id)).filter(
        models.AvaliacaoBarbearia.barbearia_id == barbearia_id,
        _visivel_barbearia(),
    ).scalar()
    return {"media": round(float(media), 1) if media else 0, "total": int(total or 0)}


def resumo_por_usuario(db: Session, usuario_id: int) -> dict:
    """
    Resolve um usuario para o resumo de avaliacoes adequado ao seu papel:
    - barbeiro/freelancer -> avaliacoes recebidas como freelancer
    - barbearia (dono)    -> avaliacoes recebidas como barbearia
    """
    freelancer = db.query(models.Freelancer).filter(
        models.Freelancer.usuario_id == usuario_id
    ).first()
    if freelancer:
        return resumo_freelancer(db, freelancer.id)

    barbearia = db.query(models.Barbearia).filter(
        models.Barbearia.usuario_id == usuario_id
    ).first()
    if barbearia:
        return resumo_barbearia(db, barbearia.id)

    return {"media": 0, "total": 0}


def atualizar_flag_negativas_freelancer(db: Session, freelancer_usuario_id: int) -> None:
    """
    Mantem os contadores de avaliacoes negativas do Usuario do freelancer,
    usados pelo painel admin de moderacao. Nao faz commit.
    """
    freelancer = db.query(models.Freelancer).filter(
        models.Freelancer.usuario_id == freelancer_usuario_id
    ).first()
    if not freelancer:
        return

    usuario = db.query(models.Usuario).filter(
        models.Usuario.id == freelancer_usuario_id
    ).first()
    if not usuario:
        return

    negativas = db.query(func.count(models.AvaliacaoFreelancer.id)).filter(
        models.AvaliacaoFreelancer.freelancer_id == freelancer.id,
        models.AvaliacaoFreelancer.nota <= 2,
    ).scalar() or 0

    media = db.query(func.avg(models.AvaliacaoFreelancer.nota)).filter(
        models.AvaliacaoFreelancer.freelancer_id == freelancer.id,
    ).scalar()

    usuario.total_avaliacoes_negativas = int(negativas)
    usuario.media_avaliacoes_negativas = round(float(media), 2) if media else 0
