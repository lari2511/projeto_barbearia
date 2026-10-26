"""
Pagamento diário do freelancer (horário oficial: America/Sao_Paulo).

- 21:00  fechamento do dia: registra quanto cada freelancer deve (saldo devedor da carteira)
         e notifica o freelancer do valor a pagar. Com o Mercado Pago ativo, o próprio job
         gera (ou reaproveita) o Pix da taxa, que o painel do freelancer mostra direto.
- 21:00-22:00  prazo para pagar via Pix; o freelancer trabalha normalmente.
- 22:00  se o pagamento do dia não foi confirmado, o freelancer é colocado
         OFFLINE e fica travado (não consegue ficar online/presente nem assumir atividades).
- Pix aprovado no Mercado Pago (webhook, ou a conciliação deste job) -> fechamento confirmado
  sem ADM e o controle do status volta ao freelancer (não liga online).
- Fluxo antigo (sem Mercado Pago): ADM SIM registra a quitação; ADM NÃO mantém bloqueado.

O bloqueio é derivado de `FechamentoDiarioFreelancer` (status != confirmado e prazo vencido),
então as travas valem mesmo que o job das 22:00 atrase.
"""

import asyncio
import logging
from datetime import date, datetime, time, timedelta, timezone
from typing import List, Optional

from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError
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
        # Atendimentos considerados no valor (débito de 10% em dinheiro / crédito de pagamentos no app)
        "movimentacoes": [
            {"chamado_id": m.chamado_id, "tipo": m.tipo, "descricao": m.descricao, "valor": round(float(m.valor), 2)}
            for m in sorted(f.movimentacoes or [], key=lambda m: m.id)
        ],
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
    from app.cobrancas.provedores import pix_disponivel

    data_txt = f.data_referencia.strftime("%d/%m")
    if f.status in ("aguardando_confirmacao", "recusado") and pix_disponivel():
        return (f"Status bloqueado: o pagamento do dia {data_txt} (R$ {f.valor_devido:.2f}) "
                "ainda não foi confirmado pelo Mercado Pago. Pague o Pix do seu painel; "
                "a liberação é automática.")
    if f.status == "aguardando_confirmacao":
        return (f"Status bloqueado: o pagamento do dia {data_txt} (R$ {f.valor_devido:.2f}) "
                "está aguardando confirmação do ADM.")
    if f.status == "recusado":
        return (f"Status bloqueado: o pagamento do dia {data_txt} (R$ {f.valor_devido:.2f}) "
                "não foi confirmado pelo ADM.")
    return (f"Status bloqueado: pagamento do dia {data_txt} (R$ {f.valor_devido:.2f}) "
            "não realizado até as 22:00.")


def freelancer_bloqueado(db: Session, freelancer_id: Optional[int]) -> bool:
    return bool(freelancer_id) and fechamento_bloqueante(db, freelancer_id) is not None


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
    Registra o valor devido do dia para cada freelancer com saldo devedor na carteira
    e avisa o freelancer do valor a pagar.
    Idempotente (1 fechamento por freelancer/dia, garantido pela uq_fechamento_freelancer_data;
    a notificação vai no mesmo commit, então também sai uma só). Não mexe na carteira.
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

        fechamento = models.FechamentoDiarioFreelancer(
            freelancer_id=carteira.barbeiro_id,
            data_referencia=data_ref,
            valor_devido=valor,
            status="pendente",
        )
        db.add(fechamento)
        try:
            db.flush()
            # Registra quais atendimentos/movimentações compõem o valor (as que ainda não
            # entraram em nenhum fechamento). Quitações não entram: só abatem o saldo.
            db.query(models.HistoricoMovimentacaoFinanceira).filter(
                models.HistoricoMovimentacaoFinanceira.barbeiro_id == carteira.barbeiro_id,
                models.HistoricoMovimentacaoFinanceira.fechamento_id.is_(None),
                ~models.HistoricoMovimentacaoFinanceira.tipo.like("quitacao%"),
            ).update({models.HistoricoMovimentacaoFinanceira.fechamento_id: fechamento.id},
                     synchronize_session=False)
            db.add(models.Notificacao(
                usuario_id=carteira.barbeiro_id,
                titulo="💰 Taxa BarberMove do dia",
                mensagem=(f"Valor a pagar referente a {data_ref.strftime('%d/%m')}: R$ {valor:.2f}. "
                          f"Pague via Pix até as {HORA_LIMITE_PAGAMENTO.strftime('%H:%M')} para continuar "
                          "podendo ficar online/presente. O QR Code e o Pix Copia e Cola estão no seu painel."),
                tipo="pagamento_diario",
                referencia_id=fechamento.id,
            ))
            db.commit()
        except IntegrityError:
            # Outra instância (ex.: durante um deploy) criou o fechamento deste dia primeiro.
            db.rollback()
            continue
        criados += 1
        logger.info("[pagamento_diario] fechamento %s criado e notificado: freelancer %s R$ %.2f",
                    data_ref, carteira.barbeiro_id, valor)

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


def aplicar_bloqueios_vencidos(db: Session, agora: Optional[datetime] = None,
                               registrar_resumo: bool = False) -> List[models.Usuario]:
    """Garante OFFLINE para todo freelancer com pagamento vencido e não confirmado."""
    agora = agora or agora_sp()
    abertos = db.query(models.FechamentoDiarioFreelancer).filter(
        models.FechamentoDiarioFreelancer.status.in_(STATUS_ABERTOS),
        models.FechamentoDiarioFreelancer.data_referencia <= agora.date(),
    ).all()
    ids = {f.freelancer_id for f in abertos if agora >= prazo_pagamento(f.data_referencia)}
    if registrar_resumo:
        logger.info("[pagamento_diario] rotina 22:00 (%s): %s freelancer(s) com taxa vencida e restritos: %s",
                    agora.date(), len(ids), sorted(ids))
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
# PIX DA TAXA (Mercado Pago)
# ============================================================

# Falha ao gerar o Pix de um freelancer: nova tentativa só depois deste intervalo.
INTERVALO_RETENTATIVA_PIX = timedelta(minutes=10)
# Fallback do webhook: cobrança em aberto é consultada no Mercado Pago com esta frequência.
INTERVALO_CONCILIACAO = timedelta(minutes=5)

_falhas_pix = {}  # freelancer_id -> datetime UTC da última falha (por processo)


def cobranca_pix_em_aberto(db: Session, freelancer_id: int, abertos=None):
    """Pix ainda válido que cobra exatamente os fechamentos em aberto, ou None. Só leitura."""
    from app.cobrancas.constantes import Finalidade, StatusCobranca
    from app.cobrancas.efeitos import chave_taxa_freelancer
    from app.cobrancas.servico import MARGEM_REUSO

    abertos = fechamentos_abertos(db, freelancer_id) if abertos is None else abertos
    if not abertos:
        return None
    valor = round(sum(float(f.valor_devido or 0.0) for f in abertos), 2)
    limite = datetime.utcnow() + MARGEM_REUSO
    candidatas = db.query(models.Cobranca).filter(
        models.Cobranca.usuario_id == freelancer_id,
        models.Cobranca.finalidade == Finalidade.TAXA_FREELANCER.value,
        models.Cobranca.status == StatusCobranca.AGUARDANDO_PAGAMENTO.value,
        models.Cobranca.chave_referencia == chave_taxa_freelancer(f.id for f in abertos),
    ).order_by(models.Cobranca.id.desc()).all()
    for c in candidatas:
        if (c.pix_copia_cola and abs(float(c.valor) - valor) < 0.005
                and (c.expira_em is None or c.expira_em > limite)):
            return c
    return None


def garantir_pix_das_taxas(db: Session) -> dict:
    """
    Todo freelancer com taxa em aberto fica com um Pix válido disponível no painel.
    Reaproveita o existente (nada é chamado no Mercado Pago); só gera quando não há
    um válido. Duas instâncias ao mesmo tempo são serializadas pelo lock do usuário
    em criar_cobranca_pix, que reaproveita o Pix criado pela outra.
    """
    from app.cobrancas import servico
    from app.cobrancas.constantes import Finalidade
    from app.cobrancas.provedores import pix_disponivel

    contagem = {"verificados": 0, "gerados": 0, "reutilizados": 0, "falhas": 0}
    if not pix_disponivel():
        return contagem

    ids = [r[0] for r in db.query(models.FechamentoDiarioFreelancer.freelancer_id).filter(
        models.FechamentoDiarioFreelancer.status.in_(STATUS_ABERTOS),
    ).distinct().all()]
    agora_utc = datetime.utcnow()
    for freelancer_id in ids:
        contagem["verificados"] += 1
        if cobranca_pix_em_aberto(db, freelancer_id):
            contagem["reutilizados"] += 1
            continue
        falhou_em = _falhas_pix.get(freelancer_id)
        if falhou_em and agora_utc - falhou_em < INTERVALO_RETENTATIVA_PIX:
            continue
        usuario = db.query(models.Usuario).filter(models.Usuario.id == freelancer_id).first()
        if not usuario:
            continue
        try:
            c = servico.criar_cobranca_pix(db, usuario, Finalidade.TAXA_FREELANCER.value)
        except Exception as exc:
            db.rollback()
            _falhas_pix[freelancer_id] = agora_utc
            contagem["falhas"] += 1
            logger.error("[pagamento_diario] falha ao gerar Pix da taxa do freelancer %s "
                         "(nova tentativa em %s min): %s", freelancer_id,
                         int(INTERVALO_RETENTATIVA_PIX.total_seconds() // 60), getattr(exc, "detail", exc))
            continue
        _falhas_pix.pop(freelancer_id, None)
        contagem["gerados"] += 1
        logger.info("[pagamento_diario] Pix da taxa disponível: freelancer %s cobranca %s mp=%s R$ %.2f",
                    freelancer_id, c.identificador, c.provedor_pagamento_id, c.valor)
    return contagem


def conciliar_pix_em_aberto(db: Session) -> int:
    """
    Consulta no Mercado Pago os Pix ainda pagáveis (caso o webhook não chegue), de todas as
    finalidades: taxa do freelancer, cadeiras e mensalidade da barbearia.
    A aprovação segue o mesmo caminho do webhook (aplicar_pagamento_do_provedor).
    """
    from app.cobrancas import servico
    from app.cobrancas.constantes import StatusCobranca
    from app.cobrancas.provedores import pix_disponivel

    if not pix_disponivel():
        return 0
    limite = datetime.utcnow() - INTERVALO_CONCILIACAO
    pendentes = [c for c in servico.cobrancas_para_conciliar(db, limite) if c.criado_em < limite]
    pagas = 0
    for c in pendentes:
        identificador = c.identificador
        try:
            c = servico.conciliar(db, c)
        except Exception as exc:
            db.rollback()
            logger.warning("[pagamento_diario] conciliação da cobranca %s falhou: %s", identificador, exc)
            continue
        if c.status == StatusCobranca.PAGO.value:
            pagas += 1
            logger.info("[pagamento_diario] conciliação: cobranca %s (%s) aprovada no MP (usuario %s)",
                        c.identificador, c.finalidade, c.usuario_id)
    return pagas


# ============================================================
# JOB EM BACKGROUND
# ============================================================

INTERVALO_JOB_SEGUNDOS = 30

# Datas em que o resumo de cada rotina já foi para o log (por processo).
_resumo_logado = {"21h": None, "22h": None}


def _ciclo_job() -> list:
    from app.database import SessionLocal

    db = SessionLocal()
    try:
        agora = agora_sp()
        hoje = agora.date()
        if agora.time() >= HORA_FECHAMENTO:
            criados = gerar_fechamentos_do_dia(db, hoje)
            if criados:
                logger.info("[pagamento_diario] fechamento %s: %s freelancer(s) com valor devido", hoje, criados)
        pix = garantir_pix_das_taxas(db)
        if agora.time() >= HORA_FECHAMENTO and _resumo_logado["21h"] != hoje:
            _resumo_logado["21h"] = hoje
            devedores = db.query(models.CarteiraBarbeiro).filter(models.CarteiraBarbeiro.saldo < 0).count()
            logger.info("[pagamento_diario] rotina 21:00 (%s) executada: %s carteira(s) devedora(s) verificada(s), "
                        "%s fechamento(s) criado(s); Pix: %s com taxa em aberto, %s gerado(s), %s reutilizado(s), "
                        "%s falha(s)", hoje, devedores, criados, pix["verificados"], pix["gerados"],
                        pix["reutilizados"], pix["falhas"])
        conciliar_pix_em_aberto(db)
        resumo_22h = agora.time() >= HORA_LIMITE_PAGAMENTO and _resumo_logado["22h"] != hoje
        if resumo_22h:
            _resumo_logado["22h"] = hoje
        alterados = aplicar_bloqueios_vencidos(db, agora, registrar_resumo=resumo_22h)
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
    from app.cobrancas.servico import serializar as serializar_cobranca

    agora = agora_sp()
    abertos = fechamentos_abertos(db, freelancer_id)
    bloqueante = fechamento_bloqueante(db, freelancer_id, agora)
    cobranca = cobranca_pix_em_aberto(db, freelancer_id, abertos)
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
        # Pix gerado pelo job das 21:00 (ou pelo botão): o painel mostra sem gerar outro.
        "cobranca_pix": serializar_cobranca(cobranca) if cobranca else None,
    }


def informar_pagamento_antecipado(db: Session, freelancer_id: int) -> models.FechamentoDiarioFreelancer:
    """
    Freelancer informa pagamento do saldo devedor antes do fechamento das 21:00.
    Nada é creditado: vira o fechamento do dia já 'aguardando_confirmacao' para o ADM
    (o job das 21:00 não cria outro). Sem commit.
    """
    carteira = db.query(models.CarteiraBarbeiro).filter(models.CarteiraBarbeiro.barbeiro_id == freelancer_id).first()
    valor = round(-float(carteira.saldo or 0.0), 2) if carteira else 0.0
    if valor <= 0:
        raise HTTPException(status_code=400, detail="Não há saldo devedor para pagar")

    hoje = agora_sp().date()
    ja_fechado = db.query(models.FechamentoDiarioFreelancer.id).filter(
        models.FechamentoDiarioFreelancer.freelancer_id == freelancer_id,
        models.FechamentoDiarioFreelancer.data_referencia == hoje,
    ).first()
    if ja_fechado:
        raise HTTPException(status_code=400, detail=(
            f"O pagamento de hoje já foi registrado. O saldo restante (R$ {valor:.2f}) entra no "
            f"fechamento de amanhã às {HORA_FECHAMENTO.strftime('%H:%M')}."))

    fechamento = models.FechamentoDiarioFreelancer(
        freelancer_id=freelancer_id,
        data_referencia=hoje,
        valor_devido=valor,
        status="aguardando_confirmacao",
        pagamento_informado_em=datetime.utcnow(),
    )
    db.add(fechamento)
    return fechamento


def informar_pagamento(db: Session, freelancer_id: int) -> List[models.FechamentoDiarioFreelancer]:
    """Freelancer informa que pagou via Pix: fechamentos em aberto vão para o ADM confirmar. Sem commit."""
    pagaveis = [f for f in fechamentos_abertos(db, freelancer_id) if f.status in ("pendente", "recusado")]
    for f in pagaveis:
        f.status = "aguardando_confirmacao"
        f.pagamento_informado_em = datetime.utcnow()
        f.decidido_em = None
        f.decidido_por_id = None
    return pagaveis
