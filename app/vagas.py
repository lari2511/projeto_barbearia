"""
Regras de anúncio de vagas de cadeira (CadeiraAcionada).

Toda vaga fica presa a uma cadeira da barbearia. O limite vem da assinatura (nunca do app):
só há vaga enquanto houver cadeira cadastrada e paga, sem vaga ativa e sem freelancer. Anunciar nunca cria cadeira. Cadeira bloqueada
conta normalmente: anunciar ou escolher freelancer nunca a desbloqueia. Quando a escolha
acontece com a cadeira bloqueada, a vaga fica em "aguardando_desbloqueio" e o freelancer só
assume a cadeira no desbloqueio manual do dono (concluir_selecao_no_desbloqueio).
"""

from datetime import datetime, time, timedelta
from typing import List, Optional

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models import (
    AssinaturaBarbearia,
    Barbearia,
    Cadeira,
    CadeiraAcionada,
    Notificacao,
    StatusCadeira,
    Usuario,
)
from app.pagamento_diario import TZ_SP, _utc_naive, agora_sp, fechamento_bloqueante
from app.plan_policy import merge_with_free_test_limit
from app.routes_cadeiras import _assinatura_ativa_e_limite

TIPO_VAGA_DIARIA = "vaga_diaria"

STATUS_ABERTA = "disponivel"
STATUS_AGUARDANDO_DESBLOQUEIO = "aguardando_desbloqueio"
STATUS_OCUPADA = "ocupada_por_barbeiro"
STATUS_RESERVADA_CLIENTE = "reservada_por_cliente"
STATUS_CANCELADA = "cancelada"


def barbearia_do_dono(db: Session, usuario_id: int) -> Optional[Barbearia]:
    return db.query(Barbearia).filter(Barbearia.usuario_id == usuario_id).order_by(Barbearia.id.asc()).first()


def fim_do_dia_utc() -> datetime:
    """Meia-noite seguinte em Brasília, no formato do banco (UTC sem fuso)."""
    amanha = agora_sp().date() + timedelta(days=1)
    return _utc_naive(datetime.combine(amanha, time.min, tzinfo=TZ_SP))


def cadeira_esta_bloqueada(cadeira: Optional[Cadeira]) -> bool:
    return bool(cadeira) and cadeira.status == StatusCadeira.BLOQUEADA


def cadeiras_pagas(db: Session, barbearia: Barbearia) -> int:
    """Cadeiras com pagamento válido: assinatura ativa, em dia e barbearia sem bloqueio financeiro."""
    if barbearia.bloqueada:
        return 0
    assinatura = db.query(AssinaturaBarbearia).filter(AssinaturaBarbearia.barbearia_id == barbearia.id).first()
    ativa, quantidade = _assinatura_ativa_e_limite(assinatura)
    dono = db.query(Usuario).filter(Usuario.id == barbearia.usuario_id).first()
    return merge_with_free_test_limit(quantidade if ativa else 0, usuario=dono, barbearia=barbearia)


def vagas_ativas(db: Session, barbearia_id: int) -> List[CadeiraAcionada]:
    """Vagas que ainda ocupam uma cadeira da barbearia, da mais recente para a mais antiga."""
    agora = datetime.utcnow()
    vagas = (
        db.query(CadeiraAcionada)
        .filter(
            CadeiraAcionada.barbearia_id == barbearia_id,
            CadeiraAcionada.status.in_([
                STATUS_ABERTA,
                STATUS_AGUARDANDO_DESBLOQUEIO,
                STATUS_OCUPADA,
                STATUS_RESERVADA_CLIENTE,
            ]),
        )
        .order_by(CadeiraAcionada.criado_em.desc(), CadeiraAcionada.id.desc())
        .all()
    )

    ativas = []
    freelancers_contados = set()
    for vaga in vagas:
        if vaga.status in (STATUS_ABERTA, STATUS_AGUARDANDO_DESBLOQUEIO):
            ativas.append(vaga)
        elif vaga.status == STATUS_RESERVADA_CLIENTE:
            if vaga.limite_chegada and vaga.limite_chegada > agora:
                ativas.append(vaga)
        elif vaga.barbeiro_id and vaga.barbeiro_id not in freelancers_contados:
            # ocupada_por_barbeiro nunca muda de status: vale enquanto o freelancer continuar
            # na cadeira ou presente na barbearia (concluir um atendimento libera a linha da
            # cadeira, mas ele continua lá).
            freelancer = vaga.barbeiro
            na_cadeira = bool(vaga.cadeira) and vaga.cadeira.freelancer_id == vaga.barbeiro_id
            presente = bool(freelancer) and freelancer.presente_em_local and freelancer.barbearia_atual_id == barbearia_id
            if na_cadeira or presente:
                freelancers_contados.add(vaga.barbeiro_id)
                ativas.append(vaga)
    return ativas


def _cadeiras_da_barbearia(db: Session, barbearia_id: int) -> List[Cadeira]:
    return (
        db.query(Cadeira)
        .filter(Cadeira.barbearia_id == barbearia_id)
        .order_by(Cadeira.numero.asc(), Cadeira.id.asc())
        .all()
    )


def limites_de_anuncio(db: Session, barbearia: Barbearia) -> dict:
    pagas = cadeiras_pagas(db, barbearia)
    ativas = vagas_ativas(db, barbearia.id)
    cadeiras = _cadeiras_da_barbearia(db, barbearia.id)
    ids_com_vaga = {vaga.cadeira_id for vaga in ativas if vaga.cadeira_id}
    livres = [
        cadeira for cadeira in cadeiras
        if cadeira.id not in ids_com_vaga and cadeira.freelancer_id is None and cadeira.chamado_id is None
    ]
    return {
        "cadeiras_pagas": pagas,
        "ativas": ativas,
        "cadeiras": cadeiras,
        "livres": livres,
        "disponiveis": max(0, min(len(livres), pagas - len(ativas))),
    }


def travar_barbearia(db: Session, barbearia_id: int) -> None:
    """
    Serializa até o commit quem altera as vagas da barbearia. É um UPDATE sem efeito porque
    trava a linha no Postgres e a escrita no SQLite (lá o FOR UPDATE é ignorado).
    """
    db.query(Barbearia).filter(Barbearia.id == barbearia_id).update(
        {Barbearia.nome: Barbearia.nome},
        synchronize_session=False,
    )
    db.expire_all()


def reservar_cadeiras(
    db: Session,
    barbearia: Barbearia,
    quantidade: int,
    cadeira_id: Optional[int] = None,
) -> List[Optional[Cadeira]]:
    """
    Valida o limite já sob a trava e devolve uma cadeira para cada vaga. O chamador cria as
    vagas e faz o commit, liberando a trava. Cadeiras bloqueadas vêm primeiro, para não
    tirar de quem está atendendo uma cadeira que já está em uso.
    """
    travar_barbearia(db, barbearia.id)
    limites = limites_de_anuncio(db, barbearia)

    if limites["cadeiras_pagas"] <= 0:
        raise HTTPException(
            status_code=402,
            detail="Nenhuma cadeira com pagamento válido. Regularize a assinatura para anunciar vagas.",
        )
    if quantidade > limites["disponiveis"]:
        raise HTTPException(
            status_code=409,
            detail=(
                f"Você tem {limites['cadeiras_pagas']} cadeira(s) paga(s) e pode anunciar "
                f"mais {limites['disponiveis']} vaga(s) agora."
            ),
        )

    livres = limites["livres"]
    if cadeira_id is not None:
        cadeira = next((c for c in limites["cadeiras"] if c.id == cadeira_id), None)
        if not cadeira:
            raise HTTPException(status_code=404, detail="Cadeira não encontrada")
        if cadeira not in livres:
            raise HTTPException(status_code=409, detail="Esta cadeira já está em uso ou com vaga anunciada")
        return [cadeira]

    livres = sorted(livres, key=lambda c: (c.status != StatusCadeira.BLOQUEADA, c.numero, c.id))
    return livres[:quantidade]


def aplicar_freelancer_na_cadeira(db: Session, vaga: CadeiraAcionada, freelancer_id: int) -> Optional[Usuario]:
    """Freelancer assume a cadeira da vaga: fica presente na barbearia e sai do "disponível na região"."""
    if vaga.cadeira_id:
        cadeira = db.query(Cadeira).filter(Cadeira.id == vaga.cadeira_id).first()
        if cadeira:
            cadeira.status = StatusCadeira.OCUPADA
            cadeira.freelancer_id = freelancer_id
            cadeira.ocupada_em = datetime.utcnow()
            cadeira.liberada_em = None

    freelancer = db.query(Usuario).filter(Usuario.id == freelancer_id).first()
    if freelancer:
        freelancer.presente_em_local = True
        freelancer.online_regiao = False
        freelancer.disponivel = True
        freelancer.barbearia_atual_id = vaga.barbearia_id
        freelancer.horario_chegada = datetime.utcnow()
        freelancer.saida_pendente = None
    return freelancer


def concluir_selecao_no_desbloqueio(db: Session, cadeira: Cadeira) -> Optional[dict]:
    """
    Chamado depois que o dono desbloqueia a cadeira (já DISPONIVEL e ainda sem commit). Se há
    freelancer escolhido aguardando, ele assume a cadeira agora. Se não puder mais assumir, a
    cadeira segue livre e a vaga é encerrada, para o desbloqueio nunca ficar preso.
    """
    vaga = (
        db.query(CadeiraAcionada)
        .filter(
            CadeiraAcionada.cadeira_id == cadeira.id,
            CadeiraAcionada.status == STATUS_AGUARDANDO_DESBLOQUEIO,
        )
        .first()
    )
    if not vaga:
        return None

    freelancer = db.query(Usuario).filter(Usuario.id == vaga.barbeiro_id).first()
    em_outro_local = bool(freelancer) and freelancer.presente_em_local and freelancer.barbearia_atual_id != vaga.barbearia_id
    indisponivel = (
        not freelancer
        or em_outro_local
        or bool(freelancer.em_atendimento)
        or bool(fechamento_bloqueante(db, freelancer.id))
    )
    barbearia_nome = vaga.barbearia.nome if vaga.barbearia else "A barbearia"
    vaga.atualizado_em = datetime.utcnow()

    if indisponivel:
        vaga.status = STATUS_CANCELADA
        if freelancer:
            db.add(Notificacao(
                usuario_id=freelancer.id,
                titulo="Vaga de cadeira encerrada",
                mensagem=f"{barbearia_nome} liberou a cadeira, mas você estava indisponível e a vaga foi encerrada.",
                tipo="vaga_encerrada",
                referencia_id=vaga.id,
            ))
        return {"freelancer_id": vaga.barbeiro_id, "assumiu": False, "nome": freelancer.nome if freelancer else None}

    vaga.status = STATUS_OCUPADA
    aplicar_freelancer_na_cadeira(db, vaga, freelancer.id)
    db.add(Notificacao(
        usuario_id=freelancer.id,
        titulo="Cadeira liberada para você 💈",
        mensagem=f"{barbearia_nome} desbloqueou a cadeira. Você já pode receber chamados.",
        tipo="vaga_cadeira_liberada",
        referencia_id=vaga.id,
    ))
    return {"freelancer_id": freelancer.id, "assumiu": True, "nome": freelancer.nome}
