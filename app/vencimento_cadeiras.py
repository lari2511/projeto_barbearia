"""
Validade de cada cadeira contratada: um mês de calendário, no horário de São Paulo.

Regras (fonte única; o app só exibe):
- Contratação: vale da confirmação do pagamento até o mesmo dia/horário do mês seguinte.
  31/01 -> 28/02 (29/02 em ano bissexto); 30/01 -> 28/02; 20/11 -> 20/12.
- Cada cadeira tem o próprio período: contratar outra não mexe nas que já existem.
- Renovar antes do vencimento: +1 mês sobre o vencimento atual (nada do que já foi pago se perde).
- Renovar depois do vencimento: novo mês contado a partir da confirmação do novo pagamento.
- Renovar uma cadeira não altera o vencimento das outras.

O banco guarda UTC sem fuso (o servidor do Railway roda em UTC). O mês é somado no relógio de
São Paulo e convertido de volta para UTC: assim uma contratação às 22h de SP (01h UTC do dia
seguinte) não cai num "dia" diferente na conta do mês.
"""

import calendar
from datetime import datetime, timedelta, timezone
from typing import Iterable, List, Optional

from sqlalchemy.orm import Session

from app import models

try:
    from zoneinfo import ZoneInfo
    TZ_SP = ZoneInfo("America/Sao_Paulo")
except Exception:  # sem base de fusos (Windows): Brasil não tem horário de verão desde 2019
    TZ_SP = timezone(timedelta(hours=-3), "BRT")
DIAS_AVISO_VENCIMENTO = 5

STATUS_ATIVA = "ativa"
STATUS_PROXIMA = "proxima_do_vencimento"
STATUS_VENCIDA = "vencida"
STATUS_CANCELADA = "cancelada"

EVENTO_CONTRATACAO = "contratacao"
EVENTO_RENOVACAO_ANTECIPADA = "renovacao_antecipada"
EVENTO_RENOVACAO_APOS_VENCIMENTO = "renovacao_apos_vencimento"
EVENTO_CANCELAMENTO = "cancelamento"


def agora_utc() -> datetime:
    """Instante atual em UTC sem fuso (o formato do banco). Não depende do relógio do celular."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


def para_sp(utc_naive: datetime) -> datetime:
    return utc_naive.replace(tzinfo=timezone.utc).astimezone(TZ_SP)


def para_utc_naive(dt_sp: datetime) -> datetime:
    return dt_sp.astimezone(timezone.utc).replace(tzinfo=None)


def somar_um_mes(base_utc: datetime, dia_ancora: Optional[int] = None) -> datetime:
    """
    base + 1 mês de calendário, contado em São Paulo. `dia_ancora` mantém o dia do ciclo
    (ex.: contratada dia 31 -> 28/02 -> 31/03); sem ele, usa o dia de `base` em SP.
    Mesmo horário; mês curto usa o último dia.
    """
    base_sp = para_sp(base_utc)
    ano, mes = base_sp.year, base_sp.month + 1
    if mes > 12:
        ano, mes = ano + 1, 1
    dia = min(max(int(dia_ancora or base_sp.day), 1), calendar.monthrange(ano, mes)[1])
    novo_sp = datetime(ano, mes, dia, base_sp.hour, base_sp.minute, base_sp.second,
                       base_sp.microsecond, tzinfo=TZ_SP)
    return para_utc_naive(novo_sp)


def dia_ancora(cadeira: models.CadeiraContratada) -> int:
    """Dia (em SP) em que o ciclo desta cadeira vira: início do período atual ou a contratação."""
    return para_sp(cadeira.data_inicio_periodo or cadeira.data_contratacao).day


def esta_em_dia(cadeira: models.CadeiraContratada, agora: Optional[datetime] = None) -> bool:
    """Mesmo critério usado no limite de cadeiras (app/vagas.py): vale até o vencimento, inclusive."""
    return cadeira.data_proxima_cobranca >= (agora or agora_utc())


def status_cadeira(cadeira: models.CadeiraContratada, agora: Optional[datetime] = None) -> str:
    agora = agora or agora_utc()
    if not cadeira.ativa:
        return STATUS_CANCELADA
    if not esta_em_dia(cadeira, agora):
        return STATUS_VENCIDA
    if cadeira.data_proxima_cobranca <= agora + timedelta(days=DIAS_AVISO_VENCIMENTO):
        return STATUS_PROXIMA
    return STATUS_ATIVA


def registrar_historico(
    db: Session,
    cadeira: models.CadeiraContratada,
    evento: str,
    *,
    vencimento_anterior: Optional[datetime] = None,
    vencimento_novo: Optional[datetime] = None,
    valor: Optional[float] = None,
    metodo_pagamento: Optional[str] = None,
    detalhe: Optional[str] = None,
) -> None:
    """Uma linha no histórico da cadeira (a cadeira precisa ter id: faça flush antes). Não faz commit."""
    db.add(models.HistoricoCadeiraContratada(
        cadeira_contratada_id=cadeira.id,
        barbearia_id=cadeira.barbearia_id,
        evento=evento,
        valor=round(float(valor), 2) if valor is not None else None,
        vencimento_anterior=vencimento_anterior,
        vencimento_novo=vencimento_novo,
        metodo_pagamento=metodo_pagamento,
        detalhe=detalhe,
    ))


def renovar_cadeira(
    db: Session,
    cadeira: models.CadeiraContratada,
    agora: datetime,
    metodo_pagamento: Optional[str] = None,
) -> datetime:
    """Renova UMA cadeira por um mês (pagamento confirmado em `agora`). Não faz commit."""
    anterior = cadeira.data_proxima_cobranca
    if esta_em_dia(cadeira, agora):
        # Antecipada: soma ao vencimento atual, sem perder nenhum dia já pago.
        novo = somar_um_mes(anterior, dia_ancora(cadeira))
        evento = EVENTO_RENOVACAO_ANTECIPADA
    else:
        # Vencida: o novo mês começa na confirmação deste pagamento.
        cadeira.data_inicio_periodo = agora
        novo = somar_um_mes(agora)
        evento = EVENTO_RENOVACAO_APOS_VENCIMENTO
    cadeira.data_proxima_cobranca = novo
    registrar_historico(
        db, cadeira, evento,
        vencimento_anterior=anterior, vencimento_novo=novo,
        valor=cadeira.valor_mensal, metodo_pagamento=metodo_pagamento,
    )
    return novo


def cadeiras_a_renovar(cadeiras_ativas: Iterable[models.CadeiraContratada], agora: datetime) -> List[models.CadeiraContratada]:
    """O que a mensalidade cobre: as cadeiras vencidas; sem nenhuma vencida, todas (antecipação)."""
    ativas = list(cadeiras_ativas)
    vencidas = [c for c in ativas if not esta_em_dia(c, agora)]
    return vencidas or ativas


def cadeiras_em_dia(db: Session, assinatura_id: int, agora: Optional[datetime] = None) -> int:
    return db.query(models.CadeiraContratada).filter(
        models.CadeiraContratada.assinatura_id == assinatura_id,
        models.CadeiraContratada.ativa.is_(True),
        models.CadeiraContratada.data_proxima_cobranca >= (agora or agora_utc()),
    ).count()


def cadeiras_contratadas_ativas(db: Session, assinatura_id: int) -> int:
    return db.query(models.CadeiraContratada).filter(
        models.CadeiraContratada.assinatura_id == assinatura_id,
        models.CadeiraContratada.ativa.is_(True),
    ).count()
