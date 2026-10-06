"""
Cobranças via Pix (Mercado Pago).

Fluxo: app pede a cobrança -> backend cria o Pix no Mercado Pago -> app mostra o
Pix Copia e Cola e acompanha o status -> Mercado Pago notifica o webhook ->
backend consulta o pagamento na API e, se aprovado, libera (uma única vez).

Copiar o Pix ou abrir a tela NÃO muda nada: só a aprovação consultada no provedor.
"""

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app import models
from app.cobrancas import servico
from app.cobrancas.constantes import Finalidade, METODOS_HABILITADOS
from app.cobrancas.provedores import (
    ErroProvedor,
    ProvedorNaoConfigurado,
    pix_disponivel,
    validar_assinatura_webhook,
)
from app.database import get_db
from app.routes import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/cobrancas", tags=["Cobranças Pix"])


class CobrancaCadeirasRequest(BaseModel):
    cadeiras_ativas: int


def _criar(db: Session, usuario, finalidade: Finalidade, dados: Optional[dict] = None) -> dict:
    try:
        c = servico.criar_cobranca_pix(db, usuario, finalidade.value, dados)
    except ProvedorNaoConfigurado:
        raise HTTPException(status_code=503, detail="Pagamento via Pix ainda não está disponível.")
    except ErroProvedor as exc:
        logger.error("[cobrancas] falha ao criar Pix (%s) usuario=%s: %s", finalidade.value, usuario.id, exc)
        raise HTTPException(status_code=502, detail="Não foi possível gerar o Pix agora. Tente novamente.")
    return servico.serializar(c)


@router.get("/config")
def configuracao_pagamentos():
    """O app usa para saber se o Pix já está ativo (credenciais configuradas no backend)."""
    return {
        "pix_disponivel": pix_disponivel(),
        "metodos": sorted(m.value for m in METODOS_HABILITADOS),
    }


@router.post("/pix/assinatura-cadeiras")
def criar_pix_assinatura_cadeiras(
    dados: CobrancaCadeirasRequest,
    db: Session = Depends(get_db),
    usuario_atual=Depends(get_current_user),
):
    """Proprietário: cobrança das cadeiras novas. As cadeiras só são liberadas após o pagamento aprovado."""
    return _criar(db, usuario_atual, Finalidade.ASSINATURA_CADEIRAS, {"cadeiras_ativas": dados.cadeiras_ativas})


@router.post("/pix/mensalidade")
def criar_pix_mensalidade(
    db: Session = Depends(get_db),
    usuario_atual=Depends(get_current_user),
):
    """Proprietário: cobrança da mensalidade. Renova/desbloqueia só após o pagamento aprovado."""
    return _criar(db, usuario_atual, Finalidade.MENSALIDADE_BARBEARIA)


@router.post("/pix/taxa-freelancer")
def criar_pix_taxa_freelancer(
    db: Session = Depends(get_db),
    usuario_atual=Depends(get_current_user),
):
    """Freelancer: cobrança da taxa BarberMove em aberto. Fica PAGA só após o pagamento aprovado."""
    return _criar(db, usuario_atual, Finalidade.TAXA_FREELANCER)


@router.get("/{identificador}")
def consultar_cobranca(
    identificador: str,
    db: Session = Depends(get_db),
    usuario_atual=Depends(get_current_user),
):
    """Status da cobrança. Enquanto aguarda, consulta o provedor (caso a notificação atrase)."""
    c = db.query(models.Cobranca).filter(models.Cobranca.identificador == identificador).first()
    if not c or c.usuario_id != usuario_atual.id:
        raise HTTPException(status_code=404, detail="Cobrança não encontrada")
    try:
        c = servico.sincronizar(db, c)
    except (ProvedorNaoConfigurado, ErroProvedor) as exc:
        logger.warning("[cobrancas] consulta %s falhou: %s", identificador, exc)
    return servico.serializar(c)


@router.post("/webhook/mercadopago")
async def webhook_mercadopago(request: Request, db: Session = Depends(get_db)):
    """
    Notificação do Mercado Pago. Aceita o formato Webhooks (?data.id=..&type=payment)
    e o legado IPN (?topic=payment&id=..). O status nunca é lido do corpo: o pagamento
    é sempre consultado na API do Mercado Pago.
    """
    params = request.query_params
    try:
        corpo = await request.json()
    except Exception:
        corpo = {}
    if not isinstance(corpo, dict):
        corpo = {}

    tipo = params.get("type") or params.get("topic") or corpo.get("type") or corpo.get("topic")
    data_id = params.get("data.id") or (corpo.get("data") or {}).get("id") or params.get("id")

    if not validar_assinatura_webhook(
        x_signature=request.headers.get("x-signature"),
        x_request_id=request.headers.get("x-request-id"),
        data_id=params.get("data.id") or data_id,
    ):
        logger.warning("[cobrancas] webhook com assinatura inválida (data.id=%s)", data_id)
        raise HTTPException(status_code=401, detail="Assinatura inválida")

    if tipo != "payment" or not data_id:
        return {"ok": True, "ignorado": True}

    try:
        c = servico.processar_notificacao(db, str(data_id))
    except ProvedorNaoConfigurado:
        logger.error("[cobrancas] webhook recebido sem MERCADOPAGO_ACCESS_TOKEN configurado")
        raise HTTPException(status_code=503, detail="Provedor não configurado")
    except ErroProvedor as exc:
        # 5xx faz o Mercado Pago reenviar a notificação depois.
        logger.error("[cobrancas] webhook: falha ao consultar pagamento %s: %s", data_id, exc)
        raise HTTPException(status_code=502, detail="Falha ao consultar o pagamento")

    return {"ok": True, "cobranca": c.identificador if c else None, "status": c.status if c else None}
