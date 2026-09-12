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
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy.orm import Session
from typing import List, Optional

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
from app.routes import get_current_user, SECRET_KEY, ALGORITHM
from app.avaliacoes_service import (
    resumo_freelancer,
    resumo_barbearia,
    atualizar_flag_negativas_freelancer,
)
from app.routes_notificacoes import criar_notificacao_avaliacao_freelancer

router = APIRouter(prefix="/api/v1/avaliacoes", tags=["Avaliacoes"])

# Auth opcional: usada apenas para decidir QUAIS avaliacoes de freelancer sao
# visiveis (separacao cliente/barbearia/freelancer/admin, ver _tipos_avaliacao_visiveis).
# Nao exige login: sem token, o pedido e tratado como "cliente" (visao publica).
_oauth2_scheme_opcional = OAuth2PasswordBearer(tokenUrl="/api/v1/login/cliente/", auto_error=False)


def _usuario_opcional(
    token: Optional[str] = Depends(_oauth2_scheme_opcional),
    db: Session = Depends(get_db),
) -> Optional[Usuario]:
    if not token:
        return None
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = int(payload.get("sub"))
    except (JWTError, ValueError, TypeError):
        return None
    return db.query(Usuario).filter(Usuario.id == user_id).first()


def _tipos_avaliacao_freelancer_visiveis(usuario_atual: Optional[Usuario], freelancer: Freelancer) -> list:
    """
    Separacao das avaliacoes de freelancer (avaliacao profissional):
      - Sem login / cliente: somente avaliacoes de clientes.
      - Barbearia (qualquer dono): clientes + profissionais (barbearia -> freelancer).
      - O proprio freelancer avaliado: clientes + profissionais.
      - Admin: clientes + profissionais (moderacao tem endpoints proprios em admin_avaliacoes).
    Cliente nunca ve avaliacao profissional, nem pela interface nem por este endpoint.
    """
    if usuario_atual is None:
        return ["cliente"]
    tipo = getattr(usuario_atual, "tipo", None)
    if tipo in ("barbearia", "admin"):
        return ["cliente", "barbearia"]
    if tipo == "barbeiro" and freelancer.usuario_id == usuario_atual.id:
        return ["cliente", "barbearia"]
    return ["cliente"]


def _tipos_avaliacao_barbearia_visiveis(usuario_atual: Optional[Usuario], barbearia: Barbearia) -> list:
    """
    Separacao das avaliacoes de barbearia (cliente -> barbearia e
    freelancer -> barbearia):
      - Sem login / cliente: somente avaliacoes de clientes.
      - Freelancer (qualquer): clientes + freelancers.
      - O proprio dono da barbearia avaliada: clientes + freelancers.
      - Admin: clientes + freelancers.
    Cliente nunca ve avaliacao de freelancer sobre a barbearia, nem pela
    interface nem por este endpoint.
    """
    if usuario_atual is None:
        return ["cliente"]
    tipo = getattr(usuario_atual, "tipo", None)
    if tipo in ("barbeiro", "admin"):
        return ["cliente", "freelancer"]
    if tipo == "barbearia" and barbearia.usuario_id == usuario_atual.id:
        return ["cliente", "freelancer"]
    return ["cliente"]


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
        # O cadastro de barbeiro (tipo "barbeiro") nao cria automaticamente a
        # linha em `freelancers` (isso so acontece em POST /freelancer/cadastro,
        # que o app hoje nao chama) — por isso um barbeiro que ja atendeu de
        # verdade pode nao ter Freelancer ainda. Cria o registro minimo aqui
        # em vez de bloquear a avaliacao com "Freelancer nao encontrado".
        usuario_barbeiro = db.query(Usuario).filter(
            Usuario.id == freelancer_id, Usuario.tipo == "barbeiro"
        ).first()
        if usuario_barbeiro:
            freelancer = Freelancer(
                usuario_id=usuario_barbeiro.id,
                tempo_experiencia_anos=0,
            )
            db.add(freelancer)
            db.flush()
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

    if tipo_avaliador == "barbearia":
        criar_notificacao_avaliacao_freelancer(freelancer.usuario_id, dados.nota, db=db)

    # Media/total refletem somente o mesmo tipo da avaliacao enviada agora
    # (cliente ou proprietario), nunca uma mistura dos dois.
    resumo = resumo_freelancer(db, freelancer.id, tipos=[tipo_avaliador])
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

    # Media/total refletem somente o mesmo tipo da avaliacao enviada agora
    # (cliente ou freelancer), nunca uma mistura dos dois.
    resumo = resumo_barbearia(db, barbearia.id, tipos=[tipo_avaliador])
    return {
        "message": "Avaliacao registrada com sucesso!",
        "avaliacao_id": avaliacao.id,
        "atualizada": bool(existente),
        "media": resumo["media"],
        "total": resumo["total"],
    }


# ==========================================================================
# CLIENTE - pendencias de avaliacao (disponivel assim que o atendimento e
# concluido; pagamento e avaliacao sao acoes independentes)
# ==========================================================================

@router.get("/pendentes-cliente", response_model=list)
def pendentes_cliente(
    db: Session = Depends(get_db),
    usuario_atual: Usuario = Depends(get_current_user),
):
    """
    Lista os atendimentos concluidos do cliente, com o estado de cada uma das
    duas avaliacoes (freelancer e barbearia). Independe do pagamento estar
    concluido: o cliente pode avaliar assim que o atendimento e finalizado,
    o pagamento e uma acao separada (ver `pagamento_concluido`).
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
            "pagamento_concluido": bool(pagamento and pagamento.pago_em),
        })

    return resultado


# ==========================================================================
# LISTAGENS / RESUMOS
# ==========================================================================

@router.get("/freelancer/{freelancer_id}/resumo", response_model=dict)
def resumo_do_freelancer(
    freelancer_id: int,
    db: Session = Depends(get_db),
    usuario_atual: Optional[Usuario] = Depends(_usuario_opcional),
):
    """
    Media/total de avaliacoes do freelancer. Nunca mistura as duas notas:
    `media`/`total` sao sempre da avaliacao de cliente; `media_barbearia`/
    `total_barbearia` (avaliacao profissional do proprietario) so aparecem
    para quem pode ve-la (ver _tipos_avaliacao_freelancer_visiveis).
    """
    freelancer = _resolver_freelancer(db, freelancer_id)
    tipos_visiveis = _tipos_avaliacao_freelancer_visiveis(usuario_atual, freelancer)
    resumo = resumo_freelancer(db, freelancer.id, tipos=["cliente"])
    if "barbearia" in tipos_visiveis:
        resumo_profissional = resumo_freelancer(db, freelancer.id, tipos=["barbearia"])
        resumo["media_barbearia"] = resumo_profissional["media"]
        resumo["total_barbearia"] = resumo_profissional["total"]
    return resumo


@router.get("/barbearia/{barbearia_id}/resumo", response_model=dict)
def resumo_da_barbearia(
    barbearia_id: int,
    db: Session = Depends(get_db),
    usuario_atual: Optional[Usuario] = Depends(_usuario_opcional),
):
    """
    Media/total de avaliacoes da barbearia. Nunca mistura as duas notas:
    `media`/`total` sao sempre da avaliacao de cliente; `media_freelancer`/
    `total_freelancer` (avaliacao profissional freelancer -> barbearia) so
    aparecem para quem pode ve-la (ver _tipos_avaliacao_barbearia_visiveis).
    """
    barbearia = _resolver_barbearia(db, barbearia_id)
    tipos_visiveis = _tipos_avaliacao_barbearia_visiveis(usuario_atual, barbearia)
    resumo = resumo_barbearia(db, barbearia.id, tipos=["cliente"])
    if "freelancer" in tipos_visiveis:
        resumo_profissional = resumo_barbearia(db, barbearia.id, tipos=["freelancer"])
        resumo["media_freelancer"] = resumo_profissional["media"]
        resumo["total_freelancer"] = resumo_profissional["total"]
    return resumo


@router.get("/freelancer/{freelancer_id}/recebidas", response_model=List[AvaliacaoFreelancerResponse])
def listar_avaliacoes_freelancer(
    freelancer_id: int,
    limite: int = 10,
    db: Session = Depends(get_db),
    usuario_atual: Optional[Usuario] = Depends(_usuario_opcional),
):
    """
    Lista avaliacoes recebidas por um freelancer (por Freelancer.id ou usuario_id).

    Separacao (etapa avaliacao profissional): cliente/publico ve somente
    avaliacoes tipo "cliente"; a propria barbearia, o freelancer avaliado e o
    admin tambem veem as avaliacoes profissionais ("barbearia").
    """
    freelancer = _resolver_freelancer(db, freelancer_id)
    tipos_visiveis = _tipos_avaliacao_freelancer_visiveis(usuario_atual, freelancer)
    avaliacoes = db.query(
        AvaliacaoFreelancer,
        Usuario.nome.label("avaliador_nome"),
        Usuario.foto_perfil.label("avaliador_foto"),
    ).join(Usuario, AvaliacaoFreelancer.avaliador_id == Usuario.id).filter(
        AvaliacaoFreelancer.freelancer_id == freelancer.id,
        AvaliacaoFreelancer.bloqueada_por_admin.isnot(True),
        AvaliacaoFreelancer.tipo_avaliador.in_(tipos_visiveis),
    ).order_by(AvaliacaoFreelancer.criado_em.desc()).limit(limite).all()

    return [{
        "id": av.id,
        "nota": av.nota,
        "comentario": av.comentario,
        "tipo_avaliador": av.tipo_avaliador,
        "foto_corte_url": av.foto_corte_url,
        "tempo_real_servico_min": av.tempo_real_servico_min,
        "criado_em": av.criado_em,
        "avaliador_id": av.avaliador_id,
        "avaliador_nome": nome,
        "avaliador_foto": foto,
    } for av, nome, foto in avaliacoes]


@router.get("/barbearia/{barbearia_id}/recebidas", response_model=List[AvaliacaoBarbeariaResponse])
def listar_avaliacoes_barbearia(
    barbearia_id: int,
    limite: int = 10,
    db: Session = Depends(get_db),
    usuario_atual: Optional[Usuario] = Depends(_usuario_opcional),
):
    """
    Lista avaliacoes recebidas por uma barbearia (por Barbearia.id ou usuario_id).

    Separacao: cliente/publico ve somente avaliacoes tipo "cliente"; o
    proprio dono da barbearia, qualquer freelancer e o admin tambem veem as
    avaliacoes profissionais ("freelancer").
    """
    barbearia = _resolver_barbearia(db, barbearia_id)
    tipos_visiveis = _tipos_avaliacao_barbearia_visiveis(usuario_atual, barbearia)
    avaliacoes = db.query(
        AvaliacaoBarbearia,
        Usuario.nome.label("avaliador_nome"),
        Usuario.foto_perfil.label("avaliador_foto"),
    ).join(Usuario, AvaliacaoBarbearia.avaliador_id == Usuario.id).filter(
        AvaliacaoBarbearia.barbearia_id == barbearia.id,
        AvaliacaoBarbearia.bloqueada_por_admin.isnot(True),
        AvaliacaoBarbearia.tipo_avaliador.in_(tipos_visiveis),
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
        "media_freelancer_barbearia": None,
        "media_barbearia": None,
        "media_barbearia_freelancer": None,
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
        # Nao misturar as duas notas: media de cliente e media de proprietario
        # (avaliacao profissional) sao contadas em separado.
        resultado["media_freelancer"] = resumo_freelancer(db, freelancer.id, tipos=["cliente"])["media"] or None
        resultado["media_freelancer_barbearia"] = resumo_freelancer(db, freelancer.id, tipos=["barbearia"])["media"] or None

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
        # Nao misturar as duas notas: media de cliente e media de freelancer
        # (avaliacao profissional sobre a barbearia) sao contadas em separado.
        resultado["media_barbearia"] = resumo_barbearia(db, barbearia.id, tipos=["cliente"])["media"] or None
        resultado["media_barbearia_freelancer"] = resumo_barbearia(db, barbearia.id, tipos=["freelancer"])["media"] or None

    return resultado
