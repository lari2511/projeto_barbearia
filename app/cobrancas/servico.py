"""
Ciclo de vida da cobrança.

Regras:
- Criar a cobrança não libera nada (status AGUARDANDO_PAGAMENTO).
- PAGO só vem da API do provedor (consulta direta com o Access Token do backend).
  O corpo de uma notificação nunca é usado como prova de pagamento.
- O efeito (liberação) roda uma única vez por cobrança (`liberado_em`), com a linha travada.
- Uma cobrança em aberto com a mesma finalidade/referência é reaproveitada em vez de duplicada.
"""

import json
import logging
import os
import uuid
from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy.orm import Session

from app import models
from app.cobrancas.constantes import (
    METODOS_HABILITADOS,
    MetodoPagamento,
    StatusCobranca,
    status_de_mercadopago,
)
from app.cobrancas.efeitos import EFEITOS
from app.cobrancas.provedores import PagamentoProvedor, obter_provedor

logger = logging.getLogger(__name__)

AGUARDANDO = StatusCobranca.AGUARDANDO_PAGAMENTO.value
INTERVALO_MIN_CONSULTA = timedelta(seconds=5)
# Margem para reaproveitar um Pix em aberto (não entregar um que expira em segundos).
MARGEM_REUSO = timedelta(minutes=2)
# Se o provedor nunca avisar, considera expirado localmente depois desta folga.
FOLGA_EXPIRACAO_LOCAL = timedelta(minutes=15)


def _minutos_expiracao() -> int:
    try:
        return max(5, min(int(os.getenv("PIX_EXPIRACAO_MINUTOS", "30")), 24 * 60))
    except ValueError:
        return 30


def serializar(c: models.Cobranca) -> dict:
    def iso(dt):
        return dt.isoformat() + "Z" if dt else None

    return {
        "identificador": c.identificador,
        "finalidade": c.finalidade,
        "descricao": c.descricao,
        "valor": round(float(c.valor or 0.0), 2),
        "metodo": c.metodo,
        "status": c.status,
        "pix_copia_cola": c.pix_copia_cola if c.status == AGUARDANDO else None,
        "qr_code_base64": c.qr_code_base64 if c.status == AGUARDANDO else None,
        "ticket_url": c.ticket_url if c.status == AGUARDANDO else None,
        "expira_em": iso(c.expira_em),
        "pago_em": iso(c.pago_em),
        "liberado": c.liberado_em is not None,
        "criado_em": iso(c.criado_em),
    }


def _cancelar_local(c: models.Cobranca, motivo: str) -> None:
    """Cancela uma cobrança em aberto; tenta cancelar no provedor também (melhor esforço)."""
    c.status = StatusCobranca.CANCELADO.value
    c.observacao = motivo
    if c.provedor_pagamento_id:
        try:
            obter_provedor().cancelar(c.provedor_pagamento_id)
        except Exception as exc:  # se o Pix antigo for pago mesmo assim, a aprovação ainda é honrada
            logger.warning("[cobrancas] não cancelou %s no provedor: %s", c.identificador, exc)


def criar_cobranca_pix(db: Session, usuario: models.Usuario, finalidade: str, dados: Optional[dict] = None) -> models.Cobranca:
    """Cria (ou reaproveita) a cobrança Pix. Lança ProvedorNaoConfigurado / ErroProvedor / HTTPException."""
    if MetodoPagamento.PIX not in METODOS_HABILITADOS:
        raise RuntimeError("Pix desabilitado")
    efeito = EFEITOS[finalidade]
    provedor = obter_provedor()  # falha cedo se não houver credencial

    # Serializa criações do mesmo usuário (Postgres); evita 2 cobranças em cliques simultâneos.
    db.query(models.Usuario).filter(models.Usuario.id == usuario.id).with_for_update().first()

    preparo = efeito.preparar(db, usuario, dados or {})
    agora = datetime.utcnow()

    em_aberto = db.query(models.Cobranca).filter(
        models.Cobranca.usuario_id == usuario.id,
        models.Cobranca.finalidade == finalidade,
        models.Cobranca.status == AGUARDANDO,
    ).all()
    for c in em_aberto:
        mesma = (
            c.chave_referencia == preparo.chave_referencia
            and abs(float(c.valor) - preparo.valor) < 0.005
            and c.pix_copia_cola
            and (c.expira_em is None or c.expira_em > agora + MARGEM_REUSO)
        )
        if mesma:
            db.commit()
            return c
        _cancelar_local(c, "Substituída por nova cobrança")

    cobranca = models.Cobranca(
        identificador=uuid.uuid4().hex,
        usuario_id=usuario.id,
        finalidade=finalidade,
        referencia=json.dumps(preparo.referencia),
        chave_referencia=preparo.chave_referencia,
        descricao=preparo.descricao,
        valor=preparo.valor,
        metodo=MetodoPagamento.PIX.value,
        provedor=provedor.nome,
        status=AGUARDANDO,
        expira_em=agora + timedelta(minutes=_minutos_expiracao()),
    )
    db.add(cobranca)
    db.flush()

    try:
        pagamento = provedor.criar_pix(
            identificador=cobranca.identificador,
            valor=cobranca.valor,
            descricao=cobranca.descricao,
            email_pagador=usuario.email,
            expira_em=cobranca.expira_em,
        )
    except Exception:
        db.rollback()
        raise

    cobranca.provedor_pagamento_id = pagamento.provedor_pagamento_id
    cobranca.pix_copia_cola = pagamento.pix_copia_cola
    cobranca.qr_code_base64 = pagamento.qr_code_base64
    cobranca.ticket_url = pagamento.ticket_url
    cobranca.status_provedor = pagamento.status
    cobranca.status_detalhe_provedor = pagamento.status_detalhe
    if pagamento.expira_em:
        cobranca.expira_em = pagamento.expira_em
    db.commit()
    db.refresh(cobranca)
    logger.info("[cobrancas] criada %s (%s) R$ %.2f usuario=%s", cobranca.identificador,
                finalidade, cobranca.valor, usuario.id)
    return cobranca


def aplicar_pagamento_do_provedor(db: Session, cobranca_id: int, pagamento: PagamentoProvedor) -> models.Cobranca:
    """Atualiza a cobrança com o status consultado no provedor e libera (uma vez) se aprovado. Faz commit."""
    c = db.query(models.Cobranca).filter(models.Cobranca.id == cobranca_id).with_for_update().one()
    agora = datetime.utcnow()

    if pagamento.referencia_externa and pagamento.referencia_externa != c.identificador:
        logger.error("[cobrancas] pagamento %s não pertence à cobrança %s (external_reference=%s)",
                     pagamento.provedor_pagamento_id, c.identificador, pagamento.referencia_externa)
        db.rollback()
        return c

    novo = status_de_mercadopago(pagamento.status, pagamento.status_detalhe)
    c.status_provedor = pagamento.status
    c.status_detalhe_provedor = pagamento.status_detalhe
    c.ultima_consulta_em = agora
    if not c.provedor_pagamento_id:
        c.provedor_pagamento_id = pagamento.provedor_pagamento_id

    try:
        if novo == StatusCobranca.PAGO:
            # Aprovação real vence qualquer estado local (ex.: Pix antigo cancelado localmente e pago mesmo assim).
            if c.status != StatusCobranca.PAGO.value:
                c.status = StatusCobranca.PAGO.value
                c.pago_em = pagamento.aprovado_em or agora
            if c.liberado_em is None:
                if pagamento.valor + 0.005 < float(c.valor):
                    c.observacao = f"Valor pago ({pagamento.valor:.2f}) menor que o cobrado ({c.valor:.2f}); não liberado"
                    logger.error("[cobrancas] %s: %s", c.identificador, c.observacao)
                else:
                    obs = EFEITOS[c.finalidade].aplicar(db, c, json.loads(c.referencia or "{}"))
                    c.liberado_em = agora
                    if obs:
                        c.observacao = obs
                    logger.info("[cobrancas] %s PAGO e liberado (%s)", c.identificador, c.finalidade)
        elif c.status == StatusCobranca.PAGO.value:
            if novo == StatusCobranca.ESTORNADO:
                c.status = StatusCobranca.ESTORNADO.value
                logger.warning("[cobrancas] %s ESTORNADO no provedor após liberação; revisar manualmente",
                               c.identificador)
            # nunca volta de PAGO para aguardando/cancelado
        elif c.status != StatusCobranca.ESTORNADO.value:
            if novo == StatusCobranca.AGUARDANDO_PAGAMENTO and c.status != AGUARDANDO:
                pass  # cancelada/expirada localmente: só sai disso com aprovação
            else:
                c.status = novo.value
                if (c.status == AGUARDANDO and c.expira_em
                        and agora > c.expira_em + FOLGA_EXPIRACAO_LOCAL):
                    c.status = StatusCobranca.EXPIRADO.value
        db.commit()
    except Exception:
        db.rollback()
        raise
    db.refresh(c)
    return c


def sincronizar(db: Session, c: models.Cobranca, forcar: bool = False) -> models.Cobranca:
    """Consulta o provedor para cobranças em aberto (fallback caso a notificação não chegue)."""
    if c.status != AGUARDANDO or not c.provedor_pagamento_id:
        return c
    agora = datetime.utcnow()
    if not forcar and c.ultima_consulta_em and agora - c.ultima_consulta_em < INTERVALO_MIN_CONSULTA:
        return c
    pagamento = obter_provedor().consultar(c.provedor_pagamento_id)
    return aplicar_pagamento_do_provedor(db, c.id, pagamento)


def processar_notificacao(db: Session, provedor_pagamento_id: str) -> Optional[models.Cobranca]:
    """Notificação do provedor: só traz o id; o status vem da consulta autenticada à API."""
    pagamento = obter_provedor().consultar(str(provedor_pagamento_id))
    c = db.query(models.Cobranca).filter(
        models.Cobranca.provedor_pagamento_id == pagamento.provedor_pagamento_id
    ).first()
    if not c and pagamento.referencia_externa:
        c = db.query(models.Cobranca).filter(
            models.Cobranca.identificador == pagamento.referencia_externa
        ).first()
    if not c:
        return None  # pagamento que não é uma cobrança deste módulo
    return aplicar_pagamento_do_provedor(db, c.id, pagamento)
