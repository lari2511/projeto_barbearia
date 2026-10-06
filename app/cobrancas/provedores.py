"""
Provedores de pagamento.

A regra de negócio (app/cobrancas/servico.py) só conhece a interface
`ProvedorPagamento`; para incluir outro provedor/método basta implementar a
mesma interface. Hoje existe apenas Mercado Pago com Pix.

Credenciais ficam SOMENTE no backend, em variáveis de ambiente:
- MERCADOPAGO_ACCESS_TOKEN      Access Token da aplicação (TEST-... ou APP_USR-...)
- MERCADOPAGO_WEBHOOK_SECRET    "Assinatura secreta" das notificações (opcional, recomendado)
- MERCADOPAGO_NOTIFICATION_URL  URL pública do webhook; se vazia usa API_URL + rota padrão
- PIX_EXPIRACAO_MINUTOS         validade do Pix (padrão 30)
"""

import hashlib
import hmac
import logging
import os
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Optional

import requests

logger = logging.getLogger(__name__)

MP_API_BASE = "https://api.mercadopago.com"
ROTA_WEBHOOK = "/api/v1/cobrancas/webhook/mercadopago"
TIMEOUT_SEGUNDOS = 15


class ProvedorNaoConfigurado(Exception):
    """Credenciais do provedor ausentes: cobrança via Pix indisponível."""


class ErroProvedor(Exception):
    """Falha de comunicação ou resposta inválida do provedor."""


@dataclass
class PagamentoProvedor:
    """Visão normalizada de um pagamento no provedor."""
    provedor_pagamento_id: str
    status: str
    status_detalhe: str = ""
    valor: float = 0.0
    referencia_externa: Optional[str] = None
    pix_copia_cola: Optional[str] = None
    qr_code_base64: Optional[str] = None
    ticket_url: Optional[str] = None
    expira_em: Optional[datetime] = None  # UTC naive
    aprovado_em: Optional[datetime] = None  # UTC naive
    bruto: dict = field(default_factory=dict, repr=False)


class ProvedorPagamento:
    nome = "base"

    def criar_pix(self, *, identificador: str, valor: float, descricao: str,
                  email_pagador: str, expira_em: datetime) -> PagamentoProvedor:
        raise NotImplementedError

    def consultar(self, provedor_pagamento_id: str) -> PagamentoProvedor:
        raise NotImplementedError

    def cancelar(self, provedor_pagamento_id: str) -> None:
        raise NotImplementedError


def _parse_data_mp(valor: Optional[str]) -> Optional[datetime]:
    if not valor:
        return None
    try:
        dt = datetime.fromisoformat(valor.replace("Z", "+00:00"))
    except ValueError:
        return None
    if dt.tzinfo is not None:
        dt = dt.astimezone(timezone.utc).replace(tzinfo=None)
    return dt


class MercadoPagoPix(ProvedorPagamento):
    nome = "mercadopago"

    def __init__(self, access_token: str):
        if not access_token:
            raise ProvedorNaoConfigurado("MERCADOPAGO_ACCESS_TOKEN não configurado")
        self._token = access_token

    def _headers(self, idempotency_key: Optional[str] = None) -> dict:
        h = {"Authorization": f"Bearer {self._token}", "Content-Type": "application/json"}
        if idempotency_key:
            h["X-Idempotency-Key"] = idempotency_key
        return h

    def _requisicao(self, metodo: str, caminho: str, **kwargs) -> dict:
        try:
            resp = requests.request(metodo, f"{MP_API_BASE}{caminho}", timeout=TIMEOUT_SEGUNDOS, **kwargs)
        except requests.RequestException as exc:
            raise ErroProvedor(f"Falha de comunicação com o Mercado Pago: {exc}") from exc
        if resp.status_code >= 400:
            # Não loga headers (contêm o token).
            logger.warning("[mercadopago] %s %s -> %s %s", metodo, caminho, resp.status_code, resp.text[:500])
            raise ErroProvedor(f"Mercado Pago respondeu {resp.status_code}")
        try:
            return resp.json()
        except ValueError as exc:
            raise ErroProvedor("Resposta inválida do Mercado Pago") from exc

    @staticmethod
    def _normalizar(dados: dict) -> PagamentoProvedor:
        tx = ((dados.get("point_of_interaction") or {}).get("transaction_data") or {})
        return PagamentoProvedor(
            provedor_pagamento_id=str(dados.get("id")),
            status=dados.get("status") or "",
            status_detalhe=dados.get("status_detail") or "",
            valor=float(dados.get("transaction_amount") or 0.0),
            referencia_externa=dados.get("external_reference"),
            pix_copia_cola=tx.get("qr_code"),
            qr_code_base64=tx.get("qr_code_base64"),
            ticket_url=tx.get("ticket_url"),
            expira_em=_parse_data_mp(dados.get("date_of_expiration")),
            aprovado_em=_parse_data_mp(dados.get("date_approved")),
            bruto=dados,
        )

    def criar_pix(self, *, identificador, valor, descricao, email_pagador, expira_em) -> PagamentoProvedor:
        corpo = {
            "transaction_amount": round(float(valor), 2),
            "description": descricao[:200],
            "payment_method_id": "pix",
            "external_reference": identificador,
            "payer": {"email": email_pagador},
            # MP exige data com offset: 2026-10-06T21:30:00.000-03:00
            "date_of_expiration": expira_em.replace(tzinfo=timezone.utc)
                .astimezone(timezone(timedelta(hours=-3)))
                .isoformat(timespec="milliseconds"),
        }
        url_notificacao = url_webhook()
        if url_notificacao:
            corpo["notification_url"] = url_notificacao
        # Mesma chave de idempotência = o MP devolve o mesmo pagamento em vez de criar outro.
        dados = self._requisicao("POST", "/v1/payments", json=corpo, headers=self._headers(identificador))
        pagamento = self._normalizar(dados)
        if not pagamento.pix_copia_cola:
            raise ErroProvedor("Mercado Pago não retornou o Pix Copia e Cola")
        return pagamento

    def consultar(self, provedor_pagamento_id: str) -> PagamentoProvedor:
        dados = self._requisicao("GET", f"/v1/payments/{provedor_pagamento_id}", headers=self._headers())
        return self._normalizar(dados)

    def cancelar(self, provedor_pagamento_id: str) -> None:
        self._requisicao("PUT", f"/v1/payments/{provedor_pagamento_id}",
                         json={"status": "cancelled"}, headers=self._headers())


def url_webhook() -> Optional[str]:
    explicita = (os.getenv("MERCADOPAGO_NOTIFICATION_URL") or "").strip()
    if explicita:
        return explicita
    base = (os.getenv("API_URL") or "").strip().rstrip("/")
    # O MP só aceita URL pública https; localhost não recebe notificação.
    if base.startswith("https://"):
        return f"{base}{ROTA_WEBHOOK}"
    return None


# Permite trocar o provedor em testes sem tocar em variáveis de ambiente.
_provedor_forcado: Optional[ProvedorPagamento] = None


def definir_provedor_para_testes(provedor: Optional[ProvedorPagamento]) -> None:
    global _provedor_forcado
    _provedor_forcado = provedor


def obter_provedor() -> ProvedorPagamento:
    if _provedor_forcado is not None:
        return _provedor_forcado
    return MercadoPagoPix((os.getenv("MERCADOPAGO_ACCESS_TOKEN") or "").strip())


def pix_disponivel() -> bool:
    try:
        obter_provedor()
        return True
    except ProvedorNaoConfigurado:
        return False


def validar_assinatura_webhook(*, x_signature: Optional[str], x_request_id: Optional[str],
                               data_id: Optional[str]) -> bool:
    """
    Valida o header x-signature do Mercado Pago (HMAC-SHA256 com a assinatura secreta).
    Sem MERCADOPAGO_WEBHOOK_SECRET configurado, retorna True: mesmo assim nenhuma
    notificação é tratada como verdade — o status é sempre consultado na API do MP.
    """
    segredo = (os.getenv("MERCADOPAGO_WEBHOOK_SECRET") or "").strip()
    if not segredo:
        return True
    if not x_signature:
        return False

    partes = {}
    for item in x_signature.split(","):
        chave, _, valor = item.strip().partition("=")
        partes[chave.strip()] = valor.strip()
    ts, v1 = partes.get("ts"), partes.get("v1")
    if not ts or not v1:
        return False

    manifesto = ""
    if data_id:
        did = str(data_id)
        manifesto += f"id:{did.lower() if did.isalnum() else did};"
    if x_request_id:
        manifesto += f"request-id:{x_request_id};"
    manifesto += f"ts:{ts};"
    esperado = hmac.new(segredo.encode(), manifesto.encode(), hashlib.sha256).hexdigest()
    return hmac.compare_digest(esperado, v1)
