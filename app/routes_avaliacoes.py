"""
Rotas para Avaliacoes - BarberMove (Etapa 6)

Relacoes permitidas (e somente estas):
  Cliente    -> Freelancer   (vinculada a um atendimento concluido)
  Cliente    -> Barbearia    (vinculada a um atendimento concluido)
  Freelancer -> Barbearia    (avaliacao de relacao, sem chamado)
  Barbearia  -> Freelancer   (avaliacao de relacao, sem chamado)

Nao existe avaliacao de cliente (ninguem avalia o cliente).

Fonte unica: models.AvaliacaoFreelancer / models.AvaliacaoBarbearia.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from app.database import get_db
from app.models import (
    Chamado, Usuario, Freelancer, Barbearia, Pagamento,
    AvaliacaoFreelancer, AvaliacaoBarbearia, StatusAgendamento
)
from app.schemas import (
    AvaliacaoCreate,
    AvaliacaoFreelancerResponse,
    AvaliacaoBarbeariaResponse,
)
from app.routes import get_current_user
from app.avaliacoes_service import (
    resumo_freelancer,
    resumo_barbearia,
    atualizar_flag_negativas_freelancer,
)

router = APIRouter(prefix="/api/v1/avaliacoes", tags=["Avaliacoes"])


def _chamado_concluido(db: Session, chamado_id: int) -> Chamado:
    chamado = db.query(Chamado).filter(Chamado.id == chamado_id).first()
    if not chamado:
        raise HTTPException(status_code=404, detail="Chamado nao encontrado")
    if str(chamado.status).lower() not in ("concluido", "concluído",
                                           StatusAgendamento.CONCLUIDO.value):
        raise HTTPException(status_code=400, detail="Atendimento ainda nao foi concluido")
    return chamado


def _resolver_freelancer(db: Session, freelancer_id: int) -> Freelancer:
    freelancer = db.query(Freelancer).filter(Freelancer.id == freelancer_id).first()
    if not freelancer:
        # Compatibilidade: algumas telas enviam o usuario_id do barbeiro.
        freelancer = db.query(Freelancer).filter(
            Freelancer.usuario_id == freelancer_id
        ).first()
    if not freelancer:
        raise HTTPException(status_code=404, detail="Freelancer nao encontrado")
    return freelancer


def _resolver_barbearia(db: Session, barbearia_id: int) -> Barbearia:
    barbearia = db.query(Barbearia).filter(Barbearia.id == barbearia_id).first()
    if not barbearia:
        # Compatibilidade: algumas telas enviam o usuario_id do dono.
        barbearia = db.query(Barbearia).filter(
            Barbearia.usuario_id == barbearia_id
        ).first()
    if not barbearia:
        raise HTTPException(status_code=404, detail="Barbearia nao encontrada")
    return barbearia


# ==========================================================================
# CLIENTE / BARBEARIA  ->  FREELANCER
# ==========================================================================

@router.post("/freelancer/{freelancer_id}", response_model=dict)
def avaliar_freelancer(
    freelancer_id: int,
    dados: AvaliacaoCreate,
    db: Session = Depends(get_db),
    usuario_atual: Usuario = Depends(get_current_user),
):
    """
    Avalia um freelancer.
      - Cliente: exige `chamado_id` de um atendimento concluido do qual participou.
      - Barbearia (dono): avaliacao de relacao, `chamado_id` opcional. Quando ausente,
        a avaliacao fica vinculada a (barbearia, freelancer) e pode ser atualizada.
    """
    freelancer = _resolver_freelancer(db, freelancer_id)

    if dados.nota is None or dados.nota < 1 or dados.nota > 5:
        raise HTTPException(status_code=400, detail="Nota deve ser entre 1 e 5")

    chamado = None
    tipo_avaliador = None

    if dados.chamado_id:
        chamado = _chamado_concluido(db, dados.chamado_id)
        if usuario_atual.id == chamado.cliente_id:
            tipo_avaliador = "cliente"
        else:
            dono = db.query(Barbearia).filter(
                Barbearia.id == chamado.barbearia_id,
                Barbearia.usuario_id == usuario_atual.id,
            ).first()
            if not dono:
                raise HTTPException(
                    status_code=403,
                    detail="Voce nao participou deste atendimento",
                )
            tipo_avaliador = "barbearia"
        # o freelancer avaliado precisa ser o do chamado
        if chamado.barbeiro_id != freelancer.usuario_id:
            raise HTTPException(
                status_code=400,
                detail="Este freelancer nao atendeu este chamado",
            )
    else:
        # Sem chamado: apenas o dono de uma barbearia pode avaliar (relacao)
        if usuario_atual.tipo != "barbearia":
            raise HTTPException(
                status_code=400,
                detail="Avaliacao de cliente exige um atendimento concluido",
            )
        dono = db.query(Barbearia).filter(
            Barbearia.usuario_id == usuario_atual.id
        ).first()
        if not dono:
            raise HTTPException(status_code=403, detail="Barbearia nao encontrada")
        tipo_avaliador = "barbearia"

    # ---- dedupe / upsert -------------------------------------------------
    q = db.query(AvaliacaoFreelancer).filter(
        AvaliacaoFreelancer.freelancer_id == freelancer.id,
        AvaliacaoFreelancer.avaliador_id == usuario_atual.id,
    )
    if dados.chamado_id:
        q = q.filter(AvaliacaoFreelancer.chamado_id == dados.chamado_id)
    else:
        q = q.filter(AvaliacaoFreelancer.chamado_id.is_(None))
    existente = q.first()

    if existente and dados.chamado_id:
        raise HTTPException(
            status_code=400,
            detail="Voce ja avaliou este freelancer neste atendimento",
        )

    if existente:
        existente.nota = dados.nota
        existente.comentario = dados.comentario
        avaliacao = existente
    else:
        avaliacao = AvaliacaoFreelancer(
            freelancer_id=freelancer.id,
            avaliador_id=usuario_atual.id,
            chamado_id=dados.chamado_id,
            nota=dados.nota,
            comentario=dados.comentario,
            foto_corte_url=dados.foto_corte_url,
            tempo_real_servico_min=dados.tempo_real_servico_min,
            tipo_avaliador=tipo_avaliador,
        )
        db.add(avaliacao)

    db.flush()
    atualizar_flag_negativas_freelancer(db, freelancer.usuario_id)
    db.commit()
    db.refresh(avaliacao)

    resumo = resumo_freelancer(db, freelancer.id)
    return {
        "message": "Avaliacao registrada com sucesso!",
        "avaliacao_id": avaliacao.id,
        "atualizada": bool(existente),
        "media": resumo["media"],
        "total": resumo["total"],
    }


# ==========================================================================
# CLIENTE / FREELANCER  ->  BARBEARIA
# ==========================================================================

@router.post("/barbearia/{barbearia_id}", response_model=dict)
def avaliar_barbearia(
    barbearia_id: int,
    dados: AvaliacaoCreate,
    db: Session = Depends(get_db),
    usuario_atual: Usuario = Depends(get_current_user),
):
    """
    Avalia uma barbearia.
      - Cliente: exige `chamado_id` de um atendimento concluido do qual participou.
      - Freelancer: avaliacao de relacao, `chamado_id` opcional. Quando ausente,
        fica vinculada a (freelancer, barbearia) e pode ser atualizada.
    """
    barbearia = _resolver_barbearia(db, barbearia_id)

    if dados.nota is None or dados.nota < 1 or dados.nota > 5:
        raise HTTPException(status_code=400, detail="Nota deve ser entre 1 e 5")

    if dados.chamado_id:
        chamado = _chamado_concluido(db, dados.chamado_id)
        if usuario_atual.id == chamado.cliente_id:
            tipo_avaliador = "cliente"
        elif usuario_atual.id == chamado.barbeiro_id:
            tipo_avaliador = "freelancer"
        else:
            raise HTTPException(
                status_code=403,
                detail="Voce nao participou deste atendimento",
            )
        if chamado.barbearia_id != barbearia.id:
            raise HTTPException(
                status_code=400,
                detail="Este atendimento nao foi nesta barbearia",
            )
    else:
        if usuario_atual.tipo != "barbeiro":
            raise HTTPException(
                status_code=400,
                detail="Avaliacao de cliente exige um atendimento concluido",
            )
        tipo_avaliador = "freelancer"

    # ---- dedupe / upsert -------------------------------------------------
    q = db.query(AvaliacaoBarbearia).filter(
        AvaliacaoBarbearia.barbearia_id == barbearia.id,
        AvaliacaoBarbearia.avaliador_id == usuario_atual.id,
    )
    if dados.chamado_id:
        q = q.filter(AvaliacaoBarbearia.chamado_id == dados.chamado_id)
    else:
        q = q.filter(AvaliacaoBarbearia.chamado_id.is_(None))
    existente = q.first()

    if existente and dados.chamado_id:
        raise HTTPException(
            status_code=400,
            detail="Voce ja avaliou esta barbearia neste atendimento",
        )

    if existente:
        existente.nota = dados.nota
        existente.comentario = dados.comentario
        avaliacao = existente
    else:
        avaliacao = AvaliacaoBarbearia(
            barbearia_id=barbearia.id,
            avaliador_id=usuario_atual.id,
            chamado_id=dados.chamado_id,
            nota=dados.nota,
            comentario=dados.comentario,
            tipo_avaliador=tipo_avaliador,
        )
        db.add(avaliacao)

    db.commit()
    db.refresh(avaliacao)

    resumo = resumo_barbearia(db, barbearia.id)
    return {
        "message": "Avaliacao registrada com sucesso!",
        "avaliacao_id": avaliacao.id,
        "atualizada": bool(existente),
        "media": resumo["media"],
        "total": resumo["total"],
    }


# ==========================================================================
# CLIENTE - pendencias de avaliacao (dispara o fluxo pos-pagamento)
# ==========================================================================

@router.get("/pendentes-cliente", response_model=list)
def pendentes_cliente(
    db: Session = Depends(get_db),
    usuario_atual: Usuario = Depends(get_current_user),
):
    """
    Lista os atendimentos do cliente ja concluidos e pagos, com o estado de
    cada uma das duas avaliacoes (freelancer e barbearia).
    """
    chamados = db.query(Chamado).filter(
        Chamado.cliente_id == usuario_atual.id,
        Chamado.status.in_([
            StatusAgendamento.CONCLUIDO.value, "concluido", "concluído",
        ]),
    ).order_by(Chamado.id.desc()).all()

    resultado = []
    for chamado in chamados:
        pagamento = db.query(Pagamento).filter(
            Pagamento.chamado_id == chamado.id
        ).first()
        pago = bool(pagamento and pagamento.pago_em)
        if not pago:
            continue

        barbeiro = db.query(Usuario).filter(Usuario.id == chamado.barbeiro_id).first()
        freelancer = db.query(Freelancer).filter(
            Freelancer.usuario_id == chamado.barbeiro_id
        ).first()
        barbearia = db.query(Barbearia).filter(
            Barbearia.id == chamado.barbearia_id
        ).first()
        dono = db.query(Usuario).filter(
            Usuario.id == barbearia.usuario_id
        ).first() if barbearia else None

        aval_free = db.query(AvaliacaoFreelancer).filter(
            AvaliacaoFreelancer.chamado_id == chamado.id,
            AvaliacaoFreelancer.avaliador_id == usuario_atual.id,
        ).first()
        aval_barb = db.query(AvaliacaoBarbearia).filter(
            AvaliacaoBarbearia.chamado_id == chamado.id,
            AvaliacaoBarbearia.avaliador_id == usuario_atual.id,
        ).first()

        resultado.append({
            "chamado_id": chamado.id,
            "concluido_em": chamado.concluido_em.isoformat() if chamado.concluido_em else None,
            "freelancer_id": freelancer.id if freelancer else None,
            "freelancer_usuario_id": chamado.barbeiro_id,
            "freelancer_nome": barbeiro.nome if barbeiro else "Freelancer",
            "freelancer_foto": barbeiro.foto_perfil if barbeiro else None,
            "barbearia_id": barbearia.id if barbearia else None,
            "barbearia_nome": barbearia.nome if barbearia else "Barbearia",
            "barbearia_foto": dono.foto_perfil if dono else None,
            "avaliacao_freelancer_enviada": bool(aval_free),
            "avaliacao_barbearia_enviada": bool(aval_barb),
        })

    return resultado


# ==========================================================================
# LISTAGENS / RESUMOS
# ==========================================================================

@router.get("/freelancer/{freelancer_id}/resumo", response_model=dict)
def resumo_do_freelancer(freelancer_id: int, db: Session = Depends(get_db)):
    freelancer = _resolver_freelancer(db, freelancer_id)
    return resumo_freelancer(db, freelancer.id)


@router.get("/barbearia/{barbearia_id}/resumo", response_model=dict)
def resumo_da_barbearia(barbearia_id: int, db: Session = Depends(get_db)):
    barbearia = _resolver_barbearia(db, barbearia_id)
    return resumo_barbearia(db, barbearia.id)


@router.get("/freelancer/{freelancer_id}/recebidas", response_model=List[AvaliacaoFreelancerResponse])
def listar_avaliacoes_freelancer(
    freelancer_id: int,
    limite: int = 10,
    db: Session = Depends(get_db),
):
    """Lista avaliacoes recebidas por um freelancer (por Freelancer.id ou usuario_id)."""
    freelancer = _resolver_freelancer(db, freelancer_id)
    avaliacoes = db.query(
        AvaliacaoFreelancer,
        Usuario.nome.label("avaliador_nome"),
        Usuario.foto_perfil.label("avaliador_foto"),
    ).join(Usuario, AvaliacaoFreelancer.avaliador_id == Usuario.id).filter(
        AvaliacaoFreelancer.freelancer_id == freelancer.id,
        AvaliacaoFreelancer.bloqueada_por_admin.isnot(True),
    ).order_by(AvaliacaoFreelancer.criado_em.desc()).limit(limite).all()

    return [{
        "id": av.id,
        "nota": av.nota,
        "comentario": av.comentario,
        "tipo_avaliador": av.tipo_avaliador,
        "foto_corte_url": av.foto_corte_url,
        "tempo_real_servico_min": av.tempo_real_servico_min,
        "criado_em": av.criado_em,
        "avaliador_nome": nome,
        "avaliador_foto": foto,
    } for av, nome, foto in avaliacoes]


@router.get("/barbearia/{barbearia_id}/recebidas", response_model=List[AvaliacaoBarbeariaResponse])
def listar_avaliacoes_barbearia(
    barbearia_id: int,
    limite: int = 10,
    db: Session = Depends(get_db),
):
    """Lista avaliacoes recebidas por uma barbearia (por Barbearia.id ou usuario_id)."""
    barbearia = _resolver_barbearia(db, barbearia_id)
    avaliacoes = db.query(
        AvaliacaoBarbearia,
        Usuario.nome.label("avaliador_nome"),
        Usuario.foto_perfil.label("avaliador_foto"),
    ).join(Usuario, AvaliacaoBarbearia.avaliador_id == Usuario.id).filter(
        AvaliacaoBarbearia.barbearia_id == barbearia.id,
        AvaliacaoBarbearia.bloqueada_por_admin.isnot(True),
    ).order_by(AvaliacaoBarbearia.criado_em.desc()).limit(limite).all()

    return [{
        "id": av.id,
        "nota": av.nota,
        "comentario": av.comentario,
        "tipo_avaliador": av.tipo_avaliador,
        "criado_em": av.criado_em,
        "avaliador_nome": nome,
        "avaliador_foto": foto,
    } for av, nome, foto in avaliacoes]


@router.get("/minhas-avaliacoes-recebidas", response_model=dict)
def minhas_avaliacoes_recebidas(
    db: Session = Depends(get_db),
    usuario_atual: Usuario = Depends(get_current_user),
):
    """Avaliacoes recebidas pelo usuario logado (freelancer e/ou barbearia)."""
    resultado = {
        "como_freelancer": [],
        "como_barbearia": [],
        "media_freelancer": None,
        "media_barbearia": None,
    }

    freelancer = db.query(Freelancer).filter(
        Freelancer.usuario_id == usuario_atual.id
    ).first()
    if freelancer:
        linhas = db.query(
            AvaliacaoFreelancer,
            Usuario.nome.label("avaliador_nome"),
            Usuario.foto_perfil.label("avaliador_foto"),
        ).join(Usuario, AvaliacaoFreelancer.avaliador_id == Usuario.id).filter(
            AvaliacaoFreelancer.freelancer_id == freelancer.id,
            AvaliacaoFreelancer.bloqueada_por_admin.isnot(True),
        ).order_by(AvaliacaoFreelancer.criado_em.desc()).all()
        for av, nome, foto in linhas:
            resultado["como_freelancer"].append({
                "id": av.id, "nota": av.nota, "comentario": av.comentario,
                "tipo_avaliador": av.tipo_avaliador,
                "foto_corte_url": av.foto_corte_url,
                "tempo_real_servico_min": av.tempo_real_servico_min,
                "criado_em": av.criado_em,
                "avaliador_nome": nome, "avaliador_foto": foto,
            })
        resultado["media_freelancer"] = resumo_freelancer(db, freelancer.id)["media"] or None

    barbearia = db.query(Barbearia).filter(
        Barbearia.usuario_id == usuario_atual.id
    ).first()
    if barbearia:
        linhas = db.query(
            AvaliacaoBarbearia,
            Usuario.nome.label("avaliador_nome"),
            Usuario.foto_perfil.label("avaliador_foto"),
        ).join(Usuario, AvaliacaoBarbearia.avaliador_id == Usuario.id).filter(
            AvaliacaoBarbearia.barbearia_id == barbearia.id,
            AvaliacaoBarbearia.bloqueada_por_admin.isnot(True),
        ).order_by(AvaliacaoBarbearia.criado_em.desc()).all()
        for av, nome, foto in linhas:
            resultado["como_barbearia"].append({
                "id": av.id, "nota": av.nota, "comentario": av.comentario,
                "tipo_avaliador": av.tipo_avaliador, "criado_em": av.criado_em,
                "avaliador_nome": nome, "avaliador_foto": foto,
            })
        resultado["media_barbearia"] = resumo_barbearia(db, barbearia.id)["media"] or None

    return resultado
