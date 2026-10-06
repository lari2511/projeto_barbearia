"""Estados, métodos e finalidades das cobranças."""

import enum


class StatusCobranca(str, enum.Enum):
    AGUARDANDO_PAGAMENTO = "AGUARDANDO_PAGAMENTO"
    PAGO = "PAGO"
    CANCELADO = "CANCELADO"
    EXPIRADO = "EXPIRADO"
    REJEITADO = "REJEITADO"
    ESTORNADO = "ESTORNADO"  # devolvido depois de pago; não desfaz a liberação automaticamente


class MetodoPagamento(str, enum.Enum):
    PIX = "PIX"


# Nesta versão só Pix. Outros métodos entram aqui + um provedor que os suporte.
METODOS_HABILITADOS = {MetodoPagamento.PIX}


class Finalidade(str, enum.Enum):
    ASSINATURA_CADEIRAS = "ASSINATURA_CADEIRAS"      # dono contrata/aumenta cadeiras
    MENSALIDADE_BARBEARIA = "MENSALIDADE_BARBEARIA"  # dono renova a mensalidade
    TAXA_FREELANCER = "TAXA_FREELANCER"              # freelancer paga a taxa BarberMove (fechamento diário)


# Status do Mercado Pago -> status da cobrança.
# https://www.mercadopago.com.br/developers/pt/reference/payments/_payments_id/get
def status_de_mercadopago(status: str, status_detail: str = "") -> StatusCobranca:
    status = (status or "").lower()
    if status == "approved":
        return StatusCobranca.PAGO
    if status in ("pending", "in_process", "authorized", "in_mediation"):
        return StatusCobranca.AGUARDANDO_PAGAMENTO
    if status == "rejected":
        return StatusCobranca.REJEITADO
    if status == "cancelled":
        return StatusCobranca.EXPIRADO if (status_detail or "").lower() == "expired" else StatusCobranca.CANCELADO
    if status in ("refunded", "charged_back"):
        return StatusCobranca.ESTORNADO
    return StatusCobranca.AGUARDANDO_PAGAMENTO
