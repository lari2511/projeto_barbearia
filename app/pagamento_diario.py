"""
Pagamento diário do freelancer (horário oficial: America/Sao_Paulo).

- 21:00  fechamento do dia: registra quanto cada freelancer deve (saldo devedor da carteira).
- 21:00-22:00  prazo para pagar via Pix; o freelancer trabalha normalmente.
- 22:00  se o pagamento do dia não foi confirmado pelo ADM, o freelancer é colocado
         OFFLINE e fica travado (não consegue ficar online/presente nem assumir atividades).
- ADM SIM -> registra a quitação na carteira e devolve o controle do status (não liga online).
- ADM NÃO -> continua bloqueado; o freelancer pode informar o pagamento de novo.

O bloqueio é derivado de `FechamentoDiarioFreelancer` (status != confirmado e prazo vencido),
então as travas valem mesmo que o job das 22:00 atrase.
"""

import asyncio
import logging
from datetime import date, datetime, time, timedelta, timezone
from typing import List, Optional

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app import models

logger = logging.getLogger(__name__)

try:
    from zoneinfo import ZoneInfo
    TZ_SP = ZoneInfo("America/Sao_Paulo")
except Exception:  # sem base de fusos: Brasil não tem horário de verão desde 2019
    TZ_SP = timezone(timedelta(hours=-3), "BRT")

HORA_FECHAMENTO = time(21, 0)
HORA_LIMITE_PAGAMENTO = time(22, 0)

STATUS_ABERTOS = ("pendente", "aguardando_confirmacao", "recusado")


def agora_sp() -> datetime:
    return datetime.now(TZ_SP)


def fechamento_em(data_ref: date) -> datetime:
    return datetime.combine(data_ref, HORA_FECHAMENTO, tzinfo=TZ_SP)


def prazo_pagamento(data_ref: date) -> datetime:
    return datetime.combine(data_ref, HORA_LIMITE_PAGAMENTO, tzinfo=TZ_SP)


def serializar_fechamento(f: models.FechamentoDiarioFreelancer, agora: Optional[datetime] = None) -> dict:
    agora = agora or agora_sp()
    prazo = prazo_pagamento(f.data_referencia)
    return {
        "id": f.id,
        "freelancer_id": f.freelancer_id,
        "data_referencia": f.data_referencia.isoformat(),
        "valor_devido": round(float(f.valor_devido or 0.0), 2),
        "status": f.status,
        "fechamento_em": fechamento_em(f.data_referencia).isoformat(),
        "prazo_pagamento": prazo.isoformat(),
        "prazo_vencido": agora >= prazo,
        "pagamento_informado_em": f.pagamento_informado_em.isoformat() + "Z" if f.pagamento_informado_em else None,
        "decidido_em": f.decidido_em.isoformat() + "Z" if f.decidido_em else None,
    }


# ============================================================
# CONSULTAS
# ============================================================

def fechamentos_abertos(db: Session, freelancer_id: int) -> List[models.FechamentoDiarioFreelancer]:
    return db.query(models.FechamentoDiarioFreelancer).filter(
        models.FechamentoDiarioFreelancer.freelancer_id == freelancer_id,
        models.FechamentoDiarioFreelancer.status.in_(STATUS_ABERTOS),
    ).order_by(models.FechamentoDiarioFreelancer.data_referencia.asc()).all()


def fechamento_bloqueante(db: Session, freelancer_id: int, agora: Optional[datetime] = None):
    """Fechamento em aberto com prazo (22:00) vencido, ou None se o freelancer está liberado."""
    agora = agora or agora_sp()
    for f in fechamentos_abertos(db, freelancer_id):
        if agora >= prazo_pagamento(f.data_referencia):
            return f
    return None


def mensagem_bloqueio(f: models.FechamentoDiarioFreelancer) -> str:
    data_txt = f.data_referencia.strftime("%d/%m")
    if f.status == "aguardando_confirmacao":
        return (f"Status bloqueado: o pagamento do dia {data_txt} (R$ {f.valor_devido:.2f}) "
                "está aguardando confirmação do ADM.")
    if f.status == "recusado":
        return (f"Status bloqueado: o pagamento do dia {data_txt} (R$ {f.valor_devido:.2f}) "
                "não foi confirmado pelo ADM.")
    return (f"Status bloqueado: pagamento do dia {data_txt} (R$ {f.valor_devido:.2f}) "
            "não realizado até as 22:00.")


def exigir_freelancer_liberado(db: Session, freelancer_id: int) -> None:
    """Trava usada nos pontos em que o freelancer tenta ficar ativo ou assumir nova atividade."""
    f = fechamento_bloqueante(db, freelancer_id)
    if f:
        raise HTTPException(status_code=403, detail=mensagem_bloqueio(f))


# ============================================================
# 21:00 - FECHAMENTO
# ============================================================

def gerar_fechamentos_do_dia(db: Session, data_ref: date) -> int:
    """
    Registra o valor devido do dia para cada freelancer com saldo devedor na carteira.
    Idempotente (1 fechamento por freelancer/dia). Não mexe na carteira.
    O que já está em fechamentos anteriores ainda abertos não é cobrado de novo.
    """
    criados = 0
    carteiras = db.query(models.CarteiraBarbeiro).filter(models.CarteiraBarbeiro.saldo < 0).all()
    for carteira in carteiras:
        existente = db.query(models.FechamentoDiarioFreelancer.id).filter(
            models.FechamentoDiarioFreelancer.freelancer_id == carteira.barbeiro_id,
            models.FechamentoDiarioFreelancer.data_referencia == data_ref,
        ).first()
        if existente:
            continue

        ja_cobrado = sum(float(f.valor_devido or 0.0) for f in fechamentos_abertos(db, carteira.barbeiro_id))
        valor = round(-float(carteira.saldo or 0.0) - ja_cobrado, 2)
        if valor <= 0:
            continue

        db.add(models.FechamentoDiarioFreelancer(
            freelancer_id=carteira.barbeiro_id,
            data_referencia=data_ref,
            valor_devido=valor,
            status="pendente",
        ))
        criados += 1

    if criados:
        db.commit()
    return criados


# ============================================================
# 22:00 - BLOQUEIO (OFFLINE)
# ============================================================

def aplicar_offline_por_bloqueio(db: Session, freelancer: models.Usuario) -> bool:
    """
    Coloca o freelancer OFFLINE sem mexer em atendimentos em andamento.
    Se estiver presente com fila pendente, usa a saída pendente da Etapa 7
    (para de receber novos chamados e sai sozinho ao concluir a fila).
    Não faz commit. Retorna True se alterou algo.
    """
    from app.routes_freelancer_status import contar_atendimentos_ativos, liberar_cadeira_do_freelancer

    alterou = False
    esta_presente = bool(freelancer.presente_em_local and freelancer.barbearia_atual_id)

    if esta_presente and contar_atendimentos_ativos(db, freelancer.id, freelancer.barbearia_atual_id) > 0:
        if freelancer.saida_pendente != "offline" or freelancer.disponivel:
            freelancer.saida_pendente = "offline"
            freelancer.disponivel = False
            alterou = True
    elif esta_presente or freelancer.online_regiao or freelancer.disponivel or freelancer.presente_em_local:
        if esta_presente:
            liberar_cadeira_do_freelancer(db, freelancer.id, freelancer.barbearia_atual_id)
        freelancer.presente_em_local = False
        freelancer.barbearia_atual_id = None
        freelancer.horario_chegada = None
        freelancer.saida_pendente = None
        freelancer.online_regiao = False
        freelancer.disponivel = False
        alterou = True

    radar = db.query(models.RadarFreelancer).filter(
        models.RadarFreelancer.freelancer_id == freelancer.id,
        models.RadarFreelancer.is_online == True,
    ).first()
    if radar:
        radar.is_online = False
        radar.atualizado_em = datetime.utcnow()
        alterou = True

    return alterou


def aplicar_bloqueios_vencidos(db: Session, agora: Optional[datetime] = None) -> List[models.Usuario]:
    """Garante OFFLINE para todo freelancer com pagamento vencido e não confirmado."""
    agora = agora or agora_sp()
    abertos = db.query(models.FechamentoDiarioFreelancer).filter(
        models.FechamentoDiarioFreelancer.status.in_(STATUS_ABERTOS),
        models.FechamentoDiarioFreelancer.data_referencia <= agora.date(),
    ).all()
    ids = {f.freelancer_id for f in abertos if agora >= prazo_pagamento(f.data_referencia)}
    if not ids:
        return []

    alterados = []
    for freelancer in db.query(models.Usuario).filter(models.Usuario.id.in_(ids)).all():
        if aplicar_offline_por_bloqueio(db, freelancer):
            alterados.append(freelancer)
    if alterados:
        db.commit()
        for u in alterados:
            logger.info("[pagamento_diario] freelancer %s colocado OFFLINE (pagamento diario vencido)", u.id)
    return alterados


# ============================================================
# JOB EM BACKGROUND
# ============================================================

INTERVALO_JOB_SEGUNDOS = 30


def _ciclo_job() -> list:
    from app.database import SessionLocal

    db = SessionLocal()
    try:
        agora = agora_sp()
        if agora.time() >= HORA_FECHAMENTO:
            criados = gerar_fechamentos_do_dia(db, agora.date())
            if criados:
                logger.info("[pagamento_diario] fechamento %s: %s freelancer(s) com valor devido", agora.date(), criados)
        alterados = aplicar_bloqueios_vencidos(db, agora)
        return [
            dict(
                freelancer_id=u.id,
                barbearia_id=u.barbearia_atual_id,
                presente_em_local=u.presente_em_local,
                online_regiao=u.online_regiao,
                disponivel=u.disponivel,
                saida_pendente=u.saida_pendente,
            )
            for u in alterados
        ]
    finally:
        db.close()


async def loop_pagamento_diario():
    from app.realtime import broadcast_event

    while True:
        try:
            eventos = await asyncio.to_thread(_ciclo_job)
            for ev in eventos:
                try:
                    await broadcast_event("freelancer_status_changed", **ev)
                except Exception:
                    pass
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("[pagamento_diario] erro no ciclo do job")
        await asyncio.sleep(INTERVALO_JOB_SEGUNDOS)


def resumo_pagamento_diario(db: Session, freelancer_id: int) -> dict:
    """Situação do pagamento diário para a tela do freelancer."""
    agora = agora_sp()
    abertos = fechamentos_abertos(db, freelancer_id)
    bloqueante = fechamento_bloqueante(db, freelancer_id, agora)
    hoje = db.query(models.FechamentoDiarioFreelancer).filter(
        models.FechamentoDiarioFreelancer.freelancer_id == freelancer_id,
        models.FechamentoDiarioFreelancer.data_referencia == agora.date(),
    ).first()
    return {
        "horario_sp": agora.isoformat(),
        "hora_fechamento": HORA_FECHAMENTO.strftime("%H:%M"),
        "hora_limite_pagamento": HORA_LIMITE_PAGAMENTO.strftime("%H:%M"),
        "bloqueado": bool(bloqueante),
        "mensagem_bloqueio": mensagem_bloqueio(bloqueante) if bloqueante else None,
        "valor_em_aberto": round(sum(float(f.valor_devido or 0.0) for f in abertos), 2),
        "pode_pagar": any(f.status in ("pendente", "recusado") for f in abertos),
        "aguardando_confirmacao": any(f.status == "aguardando_confirmacao" for f in abertos),
        "fechamentos_abertos": [serializar_fechamento(f, agora) for f in abertos],
        "fechamento_hoje": serializar_fechamento(hoje, agora) if hoje else None,
    }


def informar_pagamento(db: Session, freelancer_id: int) -> List[models.FechamentoDiarioFreelancer]:
    """Freelancer informa que pagou via Pix: fechamentos em aberto vão para o ADM confirmar. Sem commit."""
    pagaveis = [f for f in fechamentos_abertos(db, freelancer_id) if f.status in ("pendente", "recusado")]
    for f in pagaveis:
        f.status = "aguardando_confirmacao"
        f.pagamento_informado_em = datetime.utcnow()
        f.decidido_em = None
        f.decidido_por_id = None
    return pagaveis
