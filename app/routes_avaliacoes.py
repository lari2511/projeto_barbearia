"""
Rotas para Avaliações - BarberMovie
Sistema de avaliações mútuas (cliente ↔ freelancer ↔ barbearia)
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from sqlalchemy import func

from app.database import get_db
from app.models import (
    Chamado, Usuario, Freelancer, Barbearia,
    AvaliacaoFreelancer, AvaliacaoBarbearia, StatusAgendamento
)
from app.schemas import (
    AvaliacaoCreate,
    AvaliacaoFreelancerResponse,
    AvaliacaoBarbeariaResponse
)
from app.routes import get_current_user

router = APIRouter(prefix="/api/v1/avaliacoes", tags=["Avaliações"])


@router.post("/freelancer/{freelancer_id}", response_model=dict)
def avaliar_freelancer(
    freelancer_id: int,
    dados: AvaliacaoCreate,
    db: Session = Depends(get_db),
    usuario_atual = Depends(get_current_user)
):
    """
    Avalia um freelancer (cliente ou barbearia pode avaliar)
    """
    # Verificar se o chamado existe e está concluído
    chamado = db.query(Chamado).filter(
        Chamado.id == dados.chamado_id,
        Chamado.status == StatusAgendamento.CONCLUIDO
    ).first()
    
    if not chamado:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chamado não encontrado ou não concluído"
        )
    
    # Verificar se usuário atual é cliente ou dono da barbearia
    freelancer = db.query(Freelancer).filter(Freelancer.id == freelancer_id).first()
    if not freelancer:
        # Compatibilidade: algumas integrações enviam usuario_id do barbeiro em vez de Freelancer.id.
        freelancer = db.query(Freelancer).filter(Freelancer.usuario_id == freelancer_id).first()
    if not freelancer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Freelancer não encontrado"
        )
    
    # Verificar se o usuário tem permissão para avaliar
    if usuario_atual.id != chamado.cliente_id:
        # Se não é cliente, verificar se é dono da barbearia
        barbearia = db.query(Barbearia).filter(
            Barbearia.id == chamado.barbearia_id,
            Barbearia.usuario_id == usuario_atual.id
        ).first()
        
        if not barbearia:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Você não tem permissão para avaliar este freelancer"
            )
        
        tipo_avaliador = "barbearia"
    else:
        tipo_avaliador = "cliente"
    
    # Verificar se já avaliou
    avaliacao_existente = db.query(AvaliacaoFreelancer).filter(
        AvaliacaoFreelancer.chamado_id == dados.chamado_id,
        AvaliacaoFreelancer.avaliador_id == usuario_atual.id,
        AvaliacaoFreelancer.freelancer_id == freelancer_id
    ).first()
    
    if avaliacao_existente:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Você já avaliou este freelancer para este atendimento"
        )
    
    # Criar avaliação
    avaliacao = AvaliacaoFreelancer(
        freelancer_id=freelancer_id,
        avaliador_id=usuario_atual.id,
        chamado_id=dados.chamado_id,
        nota=dados.nota,
        comentario=dados.comentario,
        foto_corte_url=dados.foto_corte_url,  # Novo campo
        tempo_real_servico_min=dados.tempo_real_servico_min,  # Novo campo
        tipo_avaliador=tipo_avaliador
    )
    db.add(avaliacao)
    db.commit()
    db.refresh(avaliacao)
    
    # Calcular nova média
    media = db.query(func.avg(AvaliacaoFreelancer.nota)).filter(
        AvaliacaoFreelancer.freelancer_id == freelancer_id
    ).scalar()
    
    return {
        "message": "Avaliação enviada com sucesso!",
        "avaliacao_id": avaliacao.id,
        "nova_media": round(media, 1) if media else 0
    }


@router.post("/barbearia/{barbearia_id}", response_model=dict)
def avaliar_barbearia(
    barbearia_id: int,
    dados: AvaliacaoCreate,
    db: Session = Depends(get_db),
    usuario_atual = Depends(get_current_user)
):
    """
    Avalia uma barbearia (cliente ou freelancer pode avaliar)
    """
    # Verificar se o chamado existe e está concluído
    chamado = db.query(Chamado).filter(
        Chamado.id == dados.chamado_id,
        Chamado.status == StatusAgendamento.CONCLUIDO
    ).first()
    
    if not chamado:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chamado não encontrado ou não concluído"
        )
    
    # Verificar se barbearia existe
    barbearia = db.query(Barbearia).filter(Barbearia.id == barbearia_id).first()
    if not barbearia:
        # Compatibilidade: algumas integrações enviam usuario_id do dono em vez de Barbearia.id.
        barbearia = db.query(Barbearia).filter(Barbearia.usuario_id == barbearia_id).first()
    if not barbearia:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Barbearia não encontrada"
        )
    
    # Verificar se o usuário tem permissão para avaliar
    if usuario_atual.id == chamado.cliente_id:
        tipo_avaliador = "cliente"
    elif usuario_atual.id == chamado.barbeiro_id:
        tipo_avaliador = "freelancer"
    else:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Você não tem permissão para avaliar esta barbearia"
        )
    
    # Verificar se já avaliou
    avaliacao_existente = db.query(AvaliacaoBarbearia).filter(
        AvaliacaoBarbearia.chamado_id == dados.chamado_id,
        AvaliacaoBarbearia.avaliador_id == usuario_atual.id,
        AvaliacaoBarbearia.barbearia_id == barbearia_id
    ).first()
    
    if avaliacao_existente:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Você já avaliou esta barbearia para este atendimento"
        )
    
    # Criar avaliação
    avaliacao = AvaliacaoBarbearia(
        barbearia_id=barbearia_id,
        avaliador_id=usuario_atual.id,
        chamado_id=dados.chamado_id,
        nota=dados.nota,
        comentario=dados.comentario,
        tipo_avaliador=tipo_avaliador
    )
    db.add(avaliacao)
    db.commit()
    db.refresh(avaliacao)
    
    # Calcular nova média
    media = db.query(func.avg(AvaliacaoBarbearia.nota)).filter(
        AvaliacaoBarbearia.barbearia_id == barbearia_id
    ).scalar()
    
    return {
        "message": "Avaliação enviada com sucesso!",
        "avaliacao_id": avaliacao.id,
        "nova_media": round(media, 1) if media else 0
    }


@router.get("/freelancer/{freelancer_id}/recebidas", response_model=List[AvaliacaoFreelancerResponse])
def listar_avaliacoes_freelancer(
    freelancer_id: int,
    limite: int = 10,
    db: Session = Depends(get_db)
):
    """Lista avaliações recebidas por um freelancer"""
    avaliacoes = db.query(
        AvaliacaoFreelancer,
        Usuario.nome.label("avaliador_nome"),
        Usuario.foto_perfil.label("avaliador_foto")
    ).join(Usuario, AvaliacaoFreelancer.avaliador_id == Usuario.id).filter(
        AvaliacaoFreelancer.freelancer_id == freelancer_id
    ).order_by(AvaliacaoFreelancer.criado_em.desc()).limit(limite).all()
    
    resultado = []
    for av, nome, foto in avaliacoes:
        resultado.append({
            "id": av.id,
            "nota": av.nota,
            "comentario": av.comentario,
            "tipo_avaliador": av.tipo_avaliador,
            "foto_corte_url": av.foto_corte_url,
            "tempo_real_servico_min": av.tempo_real_servico_min,
            "criado_em": av.criado_em,
            "avaliador_nome": nome,
            "avaliador_foto": foto
        })
    
    return resultado


@router.get("/barbearia/{barbearia_id}/recebidas", response_model=List[AvaliacaoBarbeariaResponse])
def listar_avaliacoes_barbearia(
    barbearia_id: int,
    limite: int = 10,
    db: Session = Depends(get_db)
):
    """Lista avaliações recebidas por uma barbearia"""
    avaliacoes = db.query(
        AvaliacaoBarbearia,
        Usuario.nome.label("avaliador_nome"),
        Usuario.foto_perfil.label("avaliador_foto")
    ).join(Usuario, AvaliacaoBarbearia.avaliador_id == Usuario.id).filter(
        AvaliacaoBarbearia.barbearia_id == barbearia_id
    ).order_by(AvaliacaoBarbearia.criado_em.desc()).limit(limite).all()
    
    resultado = []
    for av, nome, foto in avaliacoes:
        resultado.append({
            "id": av.id,
            "nota": av.nota,
            "comentario": av.comentario,
            "tipo_avaliador": av.tipo_avaliador,
            "criado_em": av.criado_em,
            "avaliador_nome": nome,
            "avaliador_foto": foto
        })
    
    return resultado


@router.get("/minhas-avaliacoes-recebidas", response_model=dict)
def minhas_avaliacoes_recebidas(
    db: Session = Depends(get_db),
    usuario_atual = Depends(get_current_user)
):
    """
    Retorna todas as avaliações recebidas pelo usuário logado
    (funciona para freelancer e barbearia)
    """
    resultado = {
        "como_freelancer": [],
        "como_barbearia": [],
        "media_freelancer": None,
        "media_barbearia": None
    }
    
    # Verificar se é freelancer
    freelancer = db.query(Freelancer).filter(
        Freelancer.usuario_id == usuario_atual.id
    ).first()
    
    if freelancer:
        avaliacoes_freelancer = db.query(
            AvaliacaoFreelancer,
            Usuario.nome.label("avaliador_nome"),
            Usuario.foto_perfil.label("avaliador_foto")
        ).join(Usuario, AvaliacaoFreelancer.avaliador_id == Usuario.id).filter(
            AvaliacaoFreelancer.freelancer_id == freelancer.id
        ).order_by(AvaliacaoFreelancer.criado_em.desc()).all()
        
        for av, nome, foto in avaliacoes_freelancer:
            resultado["como_freelancer"].append({
                "id": av.id,
                "nota": av.nota,
                "comentario": av.comentario,
                "tipo_avaliador": av.tipo_avaliador,
                "foto_corte_url": av.foto_corte_url,
                "tempo_real_servico_min": av.tempo_real_servico_min,
                "criado_em": av.criado_em,
                "avaliador_nome": nome,
                "avaliador_foto": foto
            })
        
        media = db.query(func.avg(AvaliacaoFreelancer.nota)).filter(
            AvaliacaoFreelancer.freelancer_id == freelancer.id
        ).scalar()
        resultado["media_freelancer"] = round(media, 1) if media else None
    
    # Verificar se é barbearia
    barbearia = db.query(Barbearia).filter(
        Barbearia.usuario_id == usuario_atual.id
    ).first()
    
    if barbearia:
        avaliacoes_barbearia = db.query(
            AvaliacaoBarbearia,
            Usuario.nome.label("avaliador_nome"),
            Usuario.foto_perfil.label("avaliador_foto")
        ).join(Usuario, AvaliacaoBarbearia.avaliador_id == Usuario.id).filter(
            AvaliacaoBarbearia.barbearia_id == barbearia.id
        ).order_by(AvaliacaoBarbearia.criado_em.desc()).all()
        
        for av, nome, foto in avaliacoes_barbearia:
            resultado["como_barbearia"].append({
                "id": av.id,
                "nota": av.nota,
                "comentario": av.comentario,
                "tipo_avaliador": av.tipo_avaliador,
                "criado_em": av.criado_em,
                "avaliador_nome": nome,
                "avaliador_foto": foto
            })
        
        media = db.query(func.avg(AvaliacaoBarbearia.nota)).filter(
            AvaliacaoBarbearia.barbearia_id == barbearia.id
        ).scalar()
        resultado["media_barbearia"] = round(media, 1) if media else None
    
    return resultado

