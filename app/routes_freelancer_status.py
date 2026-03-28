"""
ENDPOINTS: Sistema de Status do Freelancer
Gerencia os 3 status (OFFLINE, ONLINE, PRESENTE) e bloqueios
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app import models
from app.routes import get_current_user
from pydantic import BaseModel
from datetime import datetime
from typing import Optional, List
import asyncio
from app.realtime import broadcast_event

router = APIRouter(prefix="/api/v1", tags=["Freelancer Status"])

# ============================================================
# SCHEMAS
# ============================================================

class AlterarStatusRequest(BaseModel):
    status: str  # 'offline', 'online', 'presente'
    barbearia_id: Optional[int] = None  # Obrigatório apenas para 'presente'

class BloquearFreelancerRequest(BaseModel):
    freelancer_id: int
    motivo: str

class AvaliarFreelancerRequest(BaseModel):
    freelancer_id: int
    chamado_id: int
    nota: int  # 1-5
    comentario: Optional[str] = None

# ============================================================
# ENDPOINTS - CONTROLE DE STATUS (FREELANCER + DONO)
# ============================================================

@router.post("/freelancer/{freelancer_id}/alterar-status")
def alterar_status_freelancer(
    freelancer_id: int,
    request: AlterarStatusRequest,
    current_user: models.Usuario = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Altera o status do freelancer entre OFFLINE, ONLINE ou PRESENTE.
    Pode ser chamado pelo próprio freelancer ou pelo dono da barbearia (controle duplo).
    """
    # Buscar freelancer
    freelancer = db.query(models.Usuario).filter(
        models.Usuario.id == freelancer_id,
        models.Usuario.tipo == "barbeiro"
    ).first()
    
    if not freelancer:
        raise HTTPException(status_code=404, detail="Freelancer não encontrado")
    
    # Verificar permissão
    is_proprio_freelancer = current_user.id == freelancer_id
    is_dono_barbearia = current_user.tipo == "barbearia"
    
    if not is_proprio_freelancer and not is_dono_barbearia:
        raise HTTPException(
            status_code=403,
            detail="Apenas o freelancer ou o dono da barbearia podem alterar o status"
        )
    
    # Se é o dono alterando, validar que o freelancer está na barbearia dele
    if is_dono_barbearia and request.status == "presente":
        if not request.barbearia_id:
            raise HTTPException(status_code=400, detail="barbearia_id é obrigatório para status 'presente'")
        
        # Verificar se a barbearia pertence ao dono
        barbearia = db.query(models.Barbearia).filter(
            models.Barbearia.id == request.barbearia_id,
            models.Barbearia.usuario_id == current_user.id
        ).first()
        
        if not barbearia:
            raise HTTPException(status_code=403, detail="Você não é dono desta barbearia")
        
        # Verificar se o freelancer está bloqueado nesta barbearia
        bloqueio = db.query(models.BarbeariaFreelancer).filter(
            models.BarbeariaFreelancer.barbearia_id == request.barbearia_id,
            models.BarbeariaFreelancer.freelancer_id == freelancer_id,
            models.BarbeariaFreelancer.bloqueado == True
        ).first()
        
        if bloqueio:
            raise HTTPException(
                status_code=403,
                detail=f"Este freelancer está bloqueado nesta barbearia. Motivo: {bloqueio.motivo}"
            )
        
        # Verificar cadeiras disponíveis
        total_cadeiras = db.query(models.Cadeira).filter(
            models.Cadeira.barbearia_id == request.barbearia_id
        ).count()
        
        freelancers_presentes = db.query(models.Usuario).filter(
            models.Usuario.barbearia_atual_id == request.barbearia_id,
            models.Usuario.presente_em_local == True,
            models.Usuario.id != freelancer_id  # Não contar ele mesmo
        ).count()
        
        if freelancers_presentes >= total_cadeiras:
            raise HTTPException(
                status_code=400,
                detail=f"Não há cadeiras disponíveis. {freelancers_presentes}/{total_cadeiras} ocupadas"
            )
    
    # ============================================================
    # APLICAR O STATUS
    # ============================================================
    
    if request.status == "offline":
        # OFFLINE: Não trabalha
        freelancer.presente_em_local = False
        freelancer.online_regiao = False
        freelancer.disponivel = False
        freelancer.barbearia_atual_id = None
        
    elif request.status == "online":
        # ONLINE: Marketplace aberto
        freelancer.presente_em_local = False
        freelancer.online_regiao = True
        freelancer.disponivel = True
        freelancer.barbearia_atual_id = None
        
    elif request.status == "presente":
        # PRESENTE: Exclusividade da unidade
        if not request.barbearia_id:
            raise HTTPException(status_code=400, detail="barbearia_id é obrigatório para status 'presente'")
        
        # Se é o freelancer alterando, validar que não está bloqueado
        if is_proprio_freelancer:
            bloqueio = db.query(models.BarbeariaFreelancer).filter(
                models.BarbeariaFreelancer.barbearia_id == request.barbearia_id,
                models.BarbeariaFreelancer.freelancer_id == freelancer_id,
                models.BarbeariaFreelancer.bloqueado == True
            ).first()
            
            if bloqueio:
                raise HTTPException(
                    status_code=403,
                    detail=f"Você está bloqueado nesta barbearia. Motivo: {bloqueio.motivo}"
                )
            
            # Verificar cadeiras disponíveis
            barbearia = db.query(models.Barbearia).filter(
                models.Barbearia.id == request.barbearia_id
            ).first()
            
            if not barbearia:
                raise HTTPException(status_code=404, detail="Barbearia não encontrada")
            
            total_cadeiras = db.query(models.Cadeira).filter(
                models.Cadeira.barbearia_id == request.barbearia_id
            ).count()
            
            freelancers_presentes = db.query(models.Usuario).filter(
                models.Usuario.barbearia_atual_id == request.barbearia_id,
                models.Usuario.presente_em_local == True,
                models.Usuario.id != freelancer_id
            ).count()
            
            if freelancers_presentes >= total_cadeiras:
                raise HTTPException(
                    status_code=400,
                    detail=f"Não há cadeiras disponíveis. {freelancers_presentes}/{total_cadeiras} ocupadas"
                )
        
        freelancer.presente_em_local = True
        freelancer.online_regiao = False
        # Presente no local também significa disponível para solicitações da barbearia.
        freelancer.disponivel = True
        freelancer.barbearia_atual_id = request.barbearia_id
        freelancer.horario_chegada = datetime.utcnow()
        
    else:
        raise HTTPException(status_code=400, detail="Status inválido. Use: offline, online ou presente")
    
    db.commit()
    db.refresh(freelancer)

    try:
        asyncio.create_task(
            broadcast_event(
                "freelancer_status_changed",
                freelancer_id=freelancer.id,
                barbearia_id=freelancer.barbearia_atual_id,
                presente_em_local=freelancer.presente_em_local,
                online_regiao=freelancer.online_regiao,
                disponivel=freelancer.disponivel,
            )
        )
    except Exception:
        pass
    
    # Preparar resposta
    response = {
        "id": freelancer.id,
        "nome": freelancer.nome,
        "status_atual": request.status,
        "presente_em_local": freelancer.presente_em_local,
        "online_regiao": freelancer.online_regiao,
        "disponivel": freelancer.disponivel,
        "barbearia_atual_id": freelancer.barbearia_atual_id
    }
    
    # Se estiver presente, incluir nome da barbearia
    if freelancer.barbearia_atual_id:
        barbearia = db.query(models.Barbearia).filter(
            models.Barbearia.id == freelancer.barbearia_atual_id
        ).first()
        if barbearia:
            response["barbearia_atual_nome"] = barbearia.nome
    
    return response


@router.get("/freelancer/{freelancer_id}/status")
def obter_status_freelancer(
    freelancer_id: int,
    db: Session = Depends(get_db)
):
    """
    Retorna o status atual do freelancer (para exibição no cliente)
    """
    freelancer = db.query(models.Usuario).filter(
        models.Usuario.id == freelancer_id,
        models.Usuario.tipo == "barbeiro"
    ).first()
    
    if not freelancer:
        raise HTTPException(status_code=404, detail="Freelancer não encontrado")
    
    # Determinar o status
    if freelancer.presente_em_local and freelancer.barbearia_atual_id:
        status_texto = "presente"
        barbearia = db.query(models.Barbearia).filter(
            models.Barbearia.id == freelancer.barbearia_atual_id
        ).first()
        barbearia_nome = barbearia.nome if barbearia else None
    elif freelancer.online_regiao:
        status_texto = "online"
        barbearia_nome = None
    else:
        status_texto = "offline"
        barbearia_nome = None
    
    return {
        "id": freelancer.id,
        "nome": freelancer.nome,
        "status": status_texto,
        "status_exibicao": {
            "offline": "Offline",
            "online": "Online na Região",
            "presente": f"Presente na Barbearia {barbearia_nome}" if barbearia_nome else "Presente"
        }[status_texto],
        "barbearia_atual_id": freelancer.barbearia_atual_id,
        "barbearia_atual_nome": barbearia_nome,
        "pode_agendar": status_texto != "offline"
    }


# ============================================================
# ENDPOINTS - BLOQUEIO DE FREELANCER (APENAS DONO)
# ============================================================

@router.post("/barbearia/{barbearia_id}/bloquear-freelancer")
def bloquear_freelancer(
    barbearia_id: int,
    request: BloquearFreelancerRequest,
    current_user: models.Usuario = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Bloqueia um freelancer de trabalhar nesta barbearia.
    Apenas o dono da barbearia pode bloquear.
    """
    # Verificar se é o dono da barbearia
    barbearia = db.query(models.Barbearia).filter(
        models.Barbearia.id == barbearia_id,
        models.Barbearia.usuario_id == current_user.id
    ).first()
    
    if not barbearia:
        raise HTTPException(status_code=403, detail="Você não é dono desta barbearia")
    
    # Verificar se o freelancer existe
    freelancer = db.query(models.Usuario).filter(
        models.Usuario.id == request.freelancer_id,
        models.Usuario.tipo == "barbeiro"
    ).first()
    
    if not freelancer:
        raise HTTPException(status_code=404, detail="Freelancer não encontrado")
    
    # Verificar se já existe um relacionamento
    relacionamento = db.query(models.BarbeariaFreelancer).filter(
        models.BarbeariaFreelancer.barbearia_id == barbearia_id,
        models.BarbeariaFreelancer.freelancer_id == request.freelancer_id
    ).first()
    
    if relacionamento:
        # Atualizar bloqueio
        relacionamento.bloqueado = True
        relacionamento.motivo = request.motivo
        relacionamento.data_bloqueio = datetime.utcnow()
    else:
        # Criar novo relacionamento com bloqueio
        relacionamento = models.BarbeariaFreelancer(
            barbearia_id=barbearia_id,
            freelancer_id=request.freelancer_id,
            bloqueado=True,
            motivo=request.motivo,
            data_bloqueio=datetime.utcnow()
        )
        db.add(relacionamento)
    
    # Se o freelancer está presente nesta barbearia, remover
    if freelancer.barbearia_atual_id == barbearia_id:
        freelancer.presente_em_local = False
        freelancer.barbearia_atual_id = None
        freelancer.online_regiao = False
        freelancer.disponivel = False
    
    db.commit()

    try:
        asyncio.create_task(
            broadcast_event(
                "freelancer_status_changed",
                freelancer_id=freelancer.id,
                barbearia_id=barbearia_id,
                presente_em_local=freelancer.presente_em_local,
                online_regiao=freelancer.online_regiao,
                disponivel=freelancer.disponivel,
            )
        )
    except Exception:
        pass
    
    return {
        "message": "Freelancer bloqueado com sucesso",
        "freelancer_id": request.freelancer_id,
        "freelancer_nome": freelancer.nome,
        "barbearia_id": barbearia_id,
        "motivo": request.motivo,
        "data_bloqueio": relacionamento.data_bloqueio
    }


@router.post("/barbearia/{barbearia_id}/desbloquear-freelancer/{freelancer_id}")
def desbloquear_freelancer(
    barbearia_id: int,
    freelancer_id: int,
    current_user: models.Usuario = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Desbloqueia um freelancer para trabalhar nesta barbearia.
    Apenas o dono da barbearia pode desbloquear.
    """
    # Verificar se é o dono da barbearia
    barbearia = db.query(models.Barbearia).filter(
        models.Barbearia.id == barbearia_id,
        models.Barbearia.usuario_id == current_user.id
    ).first()
    
    if not barbearia:
        raise HTTPException(status_code=403, detail="Você não é dono desta barbearia")
    
    # Buscar relacionamento
    relacionamento = db.query(models.BarbeariaFreelancer).filter(
        models.BarbeariaFreelancer.barbearia_id == barbearia_id,
        models.BarbeariaFreelancer.freelancer_id == freelancer_id
    ).first()
    
    if not relacionamento:
        raise HTTPException(status_code=404, detail="Relacionamento não encontrado")
    
    relacionamento.bloqueado = False
    relacionamento.motivo = None
    relacionamento.data_bloqueio = None
    
    db.commit()
    
    return {
        "message": "Freelancer desbloqueado com sucesso",
        "freelancer_id": freelancer_id,
        "barbearia_id": barbearia_id
    }


@router.get("/barbearia/{barbearia_id}/freelancers-bloqueados")
def listar_freelancers_bloqueados(
    barbearia_id: int,
    current_user: models.Usuario = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Lista todos os freelancers bloqueados nesta barbearia.
    Apenas o dono pode visualizar.
    """
    # Verificar se é o dono da barbearia
    barbearia = db.query(models.Barbearia).filter(
        models.Barbearia.id == barbearia_id,
        models.Barbearia.usuario_id == current_user.id
    ).first()
    
    if not barbearia:
        raise HTTPException(status_code=403, detail="Você não é dono desta barbearia")
    
    # Buscar bloqueios
    bloqueios = db.query(models.BarbeariaFreelancer).filter(
        models.BarbeariaFreelancer.barbearia_id == barbearia_id,
        models.BarbeariaFreelancer.bloqueado == True
    ).all()
    
    resultado = []
    for bloq in bloqueios:
        freelancer = db.query(models.Usuario).filter(
            models.Usuario.id == bloq.freelancer_id
        ).first()
        
        if freelancer:
            resultado.append({
                "freelancer_id": freelancer.id,
                "freelancer_nome": freelancer.nome,
                "freelancer_email": freelancer.email,
                "motivo": bloq.motivo,
                "data_bloqueio": bloq.data_bloqueio
            })
    
    return resultado


# ============================================================
# ENDPOINT - AVALIAÇÃO DO DONO PARA FREELANCER
# ============================================================

@router.post("/barbearia/{barbearia_id}/avaliar-freelancer")
def avaliar_freelancer(
    barbearia_id: int,
    request: AvaliarFreelancerRequest,
    current_user: models.Usuario = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Permite ao dono da barbearia avaliar o freelancer após atendimento concluído.
    """
    # Verificar se é o dono da barbearia
    barbearia = db.query(models.Barbearia).filter(
        models.Barbearia.id == barbearia_id,
        models.Barbearia.usuario_id == current_user.id
    ).first()
    
    if not barbearia:
        raise HTTPException(status_code=403, detail="Você não é dono desta barbearia")
    
    # Verificar se o chamado existe e foi concluído
    chamado = db.query(models.Chamado).filter(
        models.Chamado.id == request.chamado_id,
        models.Chamado.barbearia_id == barbearia_id,
        models.Chamado.barbeiro_id == request.freelancer_id,
        models.Chamado.status == models.StatusAgendamento.CONCLUIDO
    ).first()
    
    if not chamado:
        raise HTTPException(
            status_code=404,
            detail="Chamado não encontrado ou não foi concluído"
        )
    
    # Verificar se já avaliou esse atendimento
    avaliacao_existente = db.query(models.AvaliacaoBarbearia).filter(
        models.AvaliacaoBarbearia.chamado_id == request.chamado_id,
        models.AvaliacaoBarbearia.avaliador_id == current_user.id,
        models.AvaliacaoBarbearia.tipo_avaliador == "barbearia"
    ).first()
    
    if avaliacao_existente:
        raise HTTPException(status_code=400, detail="Você já avaliou este atendimento")
    
    # Validar nota
    if request.nota < 1 or request.nota > 5:
        raise HTTPException(status_code=400, detail="Nota deve ser entre 1 e 5")
    
    # Criar avaliação
    avaliacao = models.AvaliacaoBarbearia(
        barbearia_id=barbearia_id,
        avaliador_id=current_user.id,
        chamado_id=request.chamado_id,
        nota=request.nota,
        comentario=request.comentario,
        tipo_avaliador="barbearia"  # Dono da barbearia avaliando freelancer
    )
    
    db.add(avaliacao)
    db.commit()
    db.refresh(avaliacao)
    
    # ✅ AUTO-FLAGGING: Se nota ≤ 2, incrementar contador de avaliações ruins
    if request.nota <= 2:
        freelancer_usuario = db.query(models.Usuario).filter(
            models.Usuario.id == request.freelancer_id
        ).first()
        if freelancer_usuario:
            freelancer_usuario.total_avaliacoes_negativas += 1
            # Se já tem 3+ avaliações ruins, flagging automático
            if freelancer_usuario.total_avaliacoes_negativas >= 3:
                # Contar media
                todas_avaliacoes = db.query(models.AvaliacaoFreelancer).filter(
                    models.AvaliacaoFreelancer.freelancer_id == request.freelancer_id
                ).all()
                if todas_avaliacoes:
                    media = sum([av.nota for av in todas_avaliacoes]) / len(todas_avaliacoes)
                    freelancer_usuario.media_avaliacoes_negativas = media
            db.commit()
    
    return {
        "message": "Avaliação registrada com sucesso",
        "avaliacao_id": avaliacao.id,
        "freelancer_id": request.freelancer_id,
        "nota": request.nota,
        "comentario": request.comentario
    }
