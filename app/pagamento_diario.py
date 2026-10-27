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

Às 21:00 a comissão de cada atendimento concluído no dia entra na carteira pela regra oficial
(routes_pagamentos._aplicar_movimentacao_financeira_carteira: 10% de débito do atendimento pago
fora do app). Antes ela só era lançada pelo checkout do cliente, que o app não abre — por isso
nenhuma carteira ficava devedora e o fechamento não tinha o que cobrar.

Cada rotina fica registrada em `ExecucaoPagamentoDiario` (uma linha por dia/rotina), que também
trava a execução entre instâncias e permite retomar uma execução perdida, parcial ou interrompida.
"""

import asyncio
import logging
import os
import socket
from datetime import date, datetime, time, timedelta, timezone
from typing import List, Optional

from fastapi import HTTPException
from sqlalchemy import and_, exists, func, or_
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

# Fechamento gerado com atraso (servidor fora do ar às 21:00): o freelancer ainda tem esta
# janela para pagar antes de ficar restrito, em vez de ser bloqueado na hora.
JANELA_MINIMA_PAGAMENTO = timedelta(hours=1)
TOLERANCIA_FECHAMENTO_NO_HORARIO = timedelta(minutes=15)

# Atendimentos concluídos a partir deste dia (São Paulo) têm a comissão lançada pelo fechamento.
# Os anteriores não são cobrados retroativamente. Ajustável sem deploy pela variável de ambiente.
COMISSAO_AUTOMATICA_DESDE = date.fromisoformat(os.getenv("COMISSAO_AUTOMATICA_DESDE", "2026-10-28"))
# Movimentações que já representam a comissão/ganho de um atendimento (nunca lançar outra).
TIPOS_MOV_ATENDIMENTO = ("debito_taxa_dinheiro", "credito_ganho_app")


def agora_sp() -> datetime:
    return datetime.now(TZ_SP)


def fechamento_em(data_ref: date) -> datetime:
    return datetime.combine(data_ref, HORA_FECHAMENTO, tzinfo=TZ_SP)


def prazo_pagamento(data_ref: date) -> datetime:
    return datetime.combine(data_ref, HORA_LIMITE_PAGAMENTO, tzinfo=TZ_SP)


def _utc_naive(dt: datetime) -> datetime:
    return dt.astimezone(timezone.utc).replace(tzinfo=None)


def _sp_de_utc_naive(dt: datetime) -> datetime:
    return dt.replace(tzinfo=timezone.utc).astimezone(TZ_SP)


def prazo_do_fechamento(f: models.FechamentoDiarioFreelancer) -> datetime:
    """22:00 do dia; se o fechamento saiu atrasado, pelo menos JANELA_MINIMA_PAGAMENTO depois dele."""
    prazo = prazo_pagamento(f.data_referencia)
    if f.fechado_em:
        fechado = _sp_de_utc_naive(f.fechado_em)
        if fechado > fechamento_em(f.data_referencia) + TOLERANCIA_FECHAMENTO_NO_HORARIO:
            prazo = max(prazo, fechado + JANELA_MINIMA_PAGAMENTO)
    return prazo


def data_fechamento_vigente(agora: datetime) -> date:
    """Último dia cujo fechamento (21:00) já deveria ter acontecido."""
    hoje = agora.date()
    return hoje if agora.time() >= HORA_FECHAMENTO else hoje - timedelta(days=1)


def serializar_fechamento(f: models.FechamentoDiarioFreelancer, agora: Optional[datetime] = None) -> dict:
    agora = agora or agora_sp()
    prazo = prazo_do_fechamento(f)
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
        if agora >= prazo_do_fechamento(f):
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
            f"não realizado até as {prazo_do_fechamento(f).strftime('%H:%M')}.")


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

def atendimentos_sem_comissao(db: Session, data_ref: date) -> List[models.Chamado]:
    """
    Atendimentos concluídos até o fechamento (21:00) de data_ref que ainda não têm comissão
    nem ganho lançado na carteira. Inclui dias anteriores que tenham ficado de fora (recuperação),
    a partir de COMISSAO_AUTOMATICA_DESDE. Cancelados não entram (status != concluido); cliente
    próprio do freelancer também não (OrigemCliente.PROPRIO não gera comissão).
    """
    inicio = _utc_naive(datetime.combine(COMISSAO_AUTOMATICA_DESDE, time(0, 0), tzinfo=TZ_SP))
    ate = _utc_naive(fechamento_em(data_ref))
    concluido_em = func.coalesce(models.Chamado.concluido_em, models.Chamado.data_hora_fim)
    ja_lancado = exists().where(and_(
        models.HistoricoMovimentacaoFinanceira.chamado_id == models.Chamado.id,
        models.HistoricoMovimentacaoFinanceira.tipo.in_(TIPOS_MOV_ATENDIMENTO),
    ))
    return db.query(models.Chamado).filter(
        models.Chamado.status == models.StatusAgendamento.CONCLUIDO.value,
        models.Chamado.barbeiro_id.isnot(None),
        concluido_em >= inicio,
        concluido_em < ate,
        or_(models.Chamado.origem_cliente.is_(None),
            models.Chamado.origem_cliente != models.OrigemCliente.PROPRIO.value),
        ~ja_lancado,
    ).order_by(models.Chamado.barbeiro_id, models.Chamado.id).all()


def registrar_comissoes_do_fechamento(db: Session, data_ref: date, erros: Optional[list] = None) -> dict:
    """
    Lança na carteira a comissão de cada atendimento elegível (regra oficial, sem cálculo próprio).
    Commit por freelancer: uma falha não desfaz o que já foi lançado para os outros.
    Idempotente: o atendimento com comissão lançada não volta na consulta.
    """
    from app.routes_pagamentos import _aplicar_movimentacao_financeira_carteira

    erros = erros if erros is not None else []
    contagem = {"atendimentos": 0, "comissoes": 0, "valor_servicos": 0.0, "valor_comissoes": 0.0,
                "freelancers": set()}
    por_freelancer = {}
    for chamado in atendimentos_sem_comissao(db, data_ref):
        por_freelancer.setdefault(chamado.barbeiro_id, []).append(chamado)

    for freelancer_id, chamados in por_freelancer.items():
        parcial = {"atendimentos": 0, "comissoes": 0, "valor_servicos": 0.0, "valor_comissoes": 0.0}
        try:
            for chamado in chamados:
                valor = float(chamado.valor_total or chamado.valor_final or 0.0)
                if valor <= 0:
                    continue
                mov = _aplicar_movimentacao_financeira_carteira(
                    db, chamado=chamado, metodo_pagamento="dinheiro", valor_total=valor)
                db.flush()
                if mov is None:
                    continue
                parcial["atendimentos"] += 1
                parcial["comissoes"] += 1
                parcial["valor_servicos"] += valor
                parcial["valor_comissoes"] += -float(mov.valor)
            db.commit()
        except Exception as exc:
            db.rollback()
            erros.append(f"comissão do freelancer {freelancer_id}: {exc}")
            logger.exception("[pagamento_diario] falha ao lançar comissões do freelancer %s", freelancer_id)
            continue
        for k, v in parcial.items():
            contagem[k] += v
        contagem["freelancers"].add(freelancer_id)
        if parcial["comissoes"]:
            logger.info("[pagamento_diario] comissões %s: freelancer %s, %s atendimento(s), "
                        "R$ %.2f em serviços, R$ %.2f de comissão", data_ref, freelancer_id,
                        parcial["atendimentos"], parcial["valor_servicos"], parcial["valor_comissoes"])
    contagem["valor_servicos"] = round(contagem["valor_servicos"], 2)
    contagem["valor_comissoes"] = round(contagem["valor_comissoes"], 2)
    return contagem


def gerar_fechamentos_do_dia(db: Session, data_ref: date, agora: Optional[datetime] = None,
                             erros: Optional[list] = None) -> dict:
    """
    Registra o valor devido do dia para cada freelancer com saldo devedor na carteira
    e avisa o freelancer do valor a pagar.
    Idempotente (1 fechamento por freelancer/dia, garantido pela uq_fechamento_freelancer_data;
    a notificação vai no mesmo commit, então também sai uma só). Não mexe na carteira.
    O que já está em fechamentos anteriores ainda abertos não é cobrado de novo.
    """
    agora = agora or agora_sp()
    erros = erros if erros is not None else []
    contagem = {"analisados": 0, "criados": 0, "freelancers": set()}
    carteiras = db.query(models.CarteiraBarbeiro).filter(models.CarteiraBarbeiro.saldo < 0).all()
    for carteira in carteiras:
        contagem["analisados"] += 1
        contagem["freelancers"].add(carteira.barbeiro_id)
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
            fechado_em=_utc_naive(agora),
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
                          f"Pague via Pix até as {prazo_do_fechamento(fechamento).strftime('%H:%M')} para continuar "
                          "podendo ficar online/presente. O QR Code e o Pix Copia e Cola estão no seu painel."),
                tipo="pagamento_diario",
                referencia_id=fechamento.id,
            ))
            db.commit()
        except IntegrityError:
            # Outra instância (ex.: durante um deploy) criou o fechamento deste dia primeiro.
            db.rollback()
            continue
        except Exception as exc:
            db.rollback()
            erros.append(f"fechamento do freelancer {carteira.barbeiro_id}: {exc}")
            logger.exception("[pagamento_diario] falha ao criar fechamento %s do freelancer %s",
                             data_ref, carteira.barbeiro_id)
            continue
        contagem["criados"] += 1
        logger.info("[pagamento_diario] fechamento %s criado e notificado: freelancer %s R$ %.2f",
                    data_ref, carteira.barbeiro_id, valor)

    return contagem


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


def freelancers_com_taxa_vencida(db: Session, agora: Optional[datetime] = None) -> set:
    agora = agora or agora_sp()
    abertos = db.query(models.FechamentoDiarioFreelancer).filter(
        models.FechamentoDiarioFreelancer.status.in_(STATUS_ABERTOS),
        models.FechamentoDiarioFreelancer.data_referencia <= agora.date(),
    ).all()
    return {f.freelancer_id for f in abertos if agora >= prazo_do_fechamento(f)}


def aplicar_bloqueios_vencidos(db: Session, agora: Optional[datetime] = None,
                               ids: Optional[set] = None) -> List[models.Usuario]:
    """Garante OFFLINE para todo freelancer com pagamento vencido e não confirmado."""
    ids = freelancers_com_taxa_vencida(db, agora) if ids is None else ids
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

ROTINA_FECHAMENTO = "fechamento_21h"
ROTINA_BLOQUEIO = "bloqueio_22h"
# Execução 'em_execucao' sem atualização há mais que isso: o processo morreu; outro retoma.
EXECUCAO_TRAVADA_APOS = timedelta(minutes=10)
# Execução 'parcial'/'falhou' é tentada de novo depois deste intervalo.
INTERVALO_RETENTATIVA_EXECUCAO = timedelta(minutes=5)
INSTANCIA = os.getenv("RAILWAY_DEPLOYMENT_ID") or f"{socket.gethostname()}:{os.getpid()}"


def _reivindicar_execucao(db: Session, data_ref: date, rotina: str, agora: datetime):
    """
    Marca a rotina do dia como 'em_execucao' para esta instância, ou None se não deve rodar agora
    (já concluída, outra instância rodando, ou aguardando o intervalo de nova tentativa).
    A troca de status é um UPDATE condicional: duas instâncias nunca rodam a mesma rotina juntas.
    """
    Execucao = models.ExecucaoPagamentoDiario
    agora_utc = _utc_naive(agora)
    ex = db.query(Execucao).filter(Execucao.data_referencia == data_ref, Execucao.rotina == rotina).first()
    if ex is None:
        ex = Execucao(data_referencia=data_ref, rotina=rotina, fuso_horario="America/Sao_Paulo",
                      status="em_execucao", tentativas=1, instancia=INSTANCIA,
                      iniciado_em=agora_utc, atualizado_em=agora_utc)
        db.add(ex)
        try:
            db.commit()
        except IntegrityError:
            db.rollback()  # outra instância criou primeiro e está rodando
            return None
        return ex
    if ex.status == "concluido":
        return None
    reivindicadas = db.query(Execucao).filter(
        Execucao.id == ex.id,
        Execucao.status != "concluido",
        or_(
            and_(Execucao.status == "em_execucao", Execucao.atualizado_em < agora_utc - EXECUCAO_TRAVADA_APOS),
            and_(Execucao.status.in_(("parcial", "falhou")),
                 Execucao.atualizado_em < agora_utc - INTERVALO_RETENTATIVA_EXECUCAO),
        ),
    ).update({
        Execucao.status: "em_execucao",
        Execucao.instancia: INSTANCIA,
        Execucao.atualizado_em: agora_utc,
        Execucao.tentativas: Execucao.tentativas + 1,
    }, synchronize_session=False)
    db.commit()
    if reivindicadas != 1:
        return None
    db.refresh(ex)
    return ex


def _finalizar_execucao(db: Session, ex, status: str, erros: list, agora: datetime, **contadores) -> None:
    """Grava o resultado da tentativa. Contadores de trabalho feito somam entre tentativas."""
    agora_utc = _utc_naive(agora)
    ex = db.query(models.ExecucaoPagamentoDiario).filter(models.ExecucaoPagamentoDiario.id == ex.id).one()
    for campo in ("atendimentos_contabilizados", "comissoes_calculadas", "fechamentos_criados", "pix_criados"):
        setattr(ex, campo, int(getattr(ex, campo) or 0) + int(contadores.get(campo, 0)))
    ex.valor_comissoes = round(float(ex.valor_comissoes or 0.0) + float(contadores.get("valor_comissoes", 0.0)), 2)
    for campo in ("freelancers_analisados", "pix_reutilizados", "freelancers_bloqueados"):
        if campo in contadores:
            setattr(ex, campo, int(contadores[campo]))
    ex.status = status
    ex.atualizado_em = agora_utc
    ex.concluido_em = agora_utc if status == "concluido" else None
    if erros:
        historico = (ex.erros + "\n") if ex.erros else ""
        ex.erros = (historico + f"tentativa {ex.tentativas}: " + " | ".join(erros))[-4000:]
    db.commit()


def executar_fechamento_diario(db: Session, data_ref: date, agora: datetime):
    """Rotina das 21:00 de data_ref: comissões -> fechamentos -> Pix. Retorna a execução, ou None."""
    from app.cobrancas.provedores import pix_disponivel

    ex = _reivindicar_execucao(db, data_ref, ROTINA_FECHAMENTO, agora)
    if ex is None:
        return None
    erros = []
    contadores = {}
    status = "concluido"
    try:
        com = registrar_comissoes_do_fechamento(db, data_ref, erros)
        fech = gerar_fechamentos_do_dia(db, data_ref, agora, erros)
        pix = garantir_pix_das_taxas(db)
        sem_pix = []
        if pix_disponivel():
            sem_pix = [fid for fid in {f.freelancer_id for f in db.query(models.FechamentoDiarioFreelancer).filter(
                models.FechamentoDiarioFreelancer.status.in_(STATUS_ABERTOS)).all()}
                if not cobranca_pix_em_aberto(db, fid)]
        if sem_pix:
            erros.append(f"{len(sem_pix)} freelancer(s) com taxa em aberto ainda sem Pix: {sorted(sem_pix)}")
        contadores = dict(
            freelancers_analisados=len(com["freelancers"] | fech["freelancers"]),
            atendimentos_contabilizados=com["atendimentos"],
            comissoes_calculadas=com["comissoes"],
            valor_comissoes=com["valor_comissoes"],
            fechamentos_criados=fech["criados"],
            pix_criados=pix["gerados"],
            pix_reutilizados=pix["reutilizados"],
        )
        if erros:
            status = "parcial"
    except Exception as exc:
        db.rollback()
        status = "falhou"
        erros.append(f"erro inesperado: {exc}")
        logger.exception("[pagamento_diario] rotina 21:00 (%s) falhou", data_ref)
    _finalizar_execucao(db, ex, status, erros, agora, **contadores)
    logger.info("[pagamento_diario] rotina 21:00 (%s) %s (tentativa %s): %s freelancer(s) analisado(s), "
                "%s atendimento(s), %s comissão(ões) R$ %.2f, %s fechamento(s) criado(s); Pix: %s gerado(s), "
                "%s reutilizado(s)%s", data_ref, status, ex.tentativas,
                contadores.get("freelancers_analisados", 0), contadores.get("atendimentos_contabilizados", 0),
                contadores.get("comissoes_calculadas", 0), contadores.get("valor_comissoes", 0.0),
                contadores.get("fechamentos_criados", 0), contadores.get("pix_criados", 0),
                contadores.get("pix_reutilizados", 0), f"; erros: {' | '.join(erros)}" if erros else "")
    return ex


def executar_bloqueio_diario(db: Session, data_ref: date, agora: datetime, ids_vencidos: set):
    """Registro da rotina das 22:00 de data_ref (a restrição em si é aplicada em todo ciclo)."""
    fechamento = db.query(models.ExecucaoPagamentoDiario).filter(
        models.ExecucaoPagamentoDiario.data_referencia == data_ref,
        models.ExecucaoPagamentoDiario.rotina == ROTINA_FECHAMENTO,
    ).first()
    # Só depois que o fechamento do dia rodou; senão o 0 bloqueado seria falso.
    if not fechamento or fechamento.status not in ("concluido", "parcial"):
        return None
    ex = _reivindicar_execucao(db, data_ref, ROTINA_BLOQUEIO, agora)
    if ex is None:
        return None
    _finalizar_execucao(db, ex, "concluido", [], agora,
                        freelancers_analisados=len(ids_vencidos), freelancers_bloqueados=len(ids_vencidos))
    logger.info("[pagamento_diario] rotina 22:00 (%s) concluido: %s freelancer(s) com taxa vencida e restritos: %s",
                data_ref, len(ids_vencidos), sorted(ids_vencidos))
    return ex


def _ciclo_job(db: Optional[Session] = None, agora: Optional[datetime] = None) -> list:
    from app.database import SessionLocal

    sessao_propria = db is None
    db = db if db is not None else SessionLocal()
    try:
        agora = agora or agora_sp()
        data_ref = data_fechamento_vigente(agora)
        if executar_fechamento_diario(db, data_ref, agora) is None:
            # Fora da rotina: mantém os Pix das taxas em aberto (retentativa de falhas).
            garantir_pix_das_taxas(db)
        conciliar_pix_em_aberto(db)
        ids_vencidos = freelancers_com_taxa_vencida(db, agora)
        # 22:00, ou o prazo estendido de um fechamento que saiu atrasado
        prazos = [prazo_do_fechamento(f) for f in db.query(models.FechamentoDiarioFreelancer).filter(
            models.FechamentoDiarioFreelancer.data_referencia == data_ref).all()]
        if agora >= max([prazo_pagamento(data_ref)] + prazos):
            executar_bloqueio_diario(db, data_ref, agora, ids_vencidos)
        alterados = aplicar_bloqueios_vencidos(db, agora, ids_vencidos)
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
        if sessao_propria:
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
