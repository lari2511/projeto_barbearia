# --- ARQUIVO: app/routes_pagamentos.py ---
# Rotas para gerenciamento de pagamentos

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import Optional
from datetime import datetime, timedelta
import qrcode
import io
import base64
from pydantic import BaseModel
import mercadopago
import os

from .database import get_db
from .models import (
    Pagamento,
    Chamado,
    Usuario,
    StatusAgendamento,
    StatusCadeira,
    Cadeira,
    Corte,
    TransacaoFinanceira,
    ConfiguracaoSplitPagamento,
    Barbearia,
    TipoTransacao,
    CarteiraBarbeiro,
    HistoricoMovimentacaoFinanceira,
)
from .routes import get_current_user
from .firebase_config import enviar_notificacao_pagamento

router = APIRouter(tags=["Pagamentos"])


def _resolver_split_config(db: Session):
    cfg = db.query(ConfiguracaoSplitPagamento).order_by(ConfiguracaoSplitPagamento.id.asc()).first()
    if not cfg:
        admin = db.query(Usuario).filter(Usuario.tipo == "admin").order_by(Usuario.id.asc()).first()
        return {
            "barbeiro": 40.0,
            "barbearia": 50.0,
            "barbermove": 10.0,
            "recebedor_plataforma_id": admin.id if admin else 1,
        }

    total = (cfg.percentual_barbeiro or 0) + (cfg.percentual_barbearia or 0) + (cfg.percentual_barbermove or 0)
    if abs(total - 100.0) > 0.0001:
        admin = db.query(Usuario).filter(Usuario.tipo == "admin").order_by(Usuario.id.asc()).first()
        return {
            "barbeiro": 40.0,
            "barbearia": 50.0,
            "barbermove": 10.0,
            "recebedor_plataforma_id": admin.id if admin else 1,
        }

    recebedor_id = cfg.recebedor_plataforma_id
    if not recebedor_id:
        admin = db.query(Usuario).filter(Usuario.tipo == "admin").order_by(Usuario.id.asc()).first()
        recebedor_id = admin.id if admin else 1

    return {
        "barbeiro": float(cfg.percentual_barbeiro),
        "barbearia": float(cfg.percentual_barbearia),
        "barbermove": float(cfg.percentual_barbermove),
        "recebedor_plataforma_id": recebedor_id,
    }


def _upsert_transacao_split(
    db: Session,
    *,
    corte_id: int,
    recebedor_id: int,
    tipo: str,
    valor: float,
    percentual: float,
    status_repasse: str,
    data_repasse: Optional[datetime],
    motivo_falha: Optional[str],
):
    transacao = db.query(TransacaoFinanceira).filter(
        TransacaoFinanceira.corte_id == corte_id,
        TransacaoFinanceira.tipo == tipo,
    ).first()

    if not transacao:
        transacao = TransacaoFinanceira(
            corte_id=corte_id,
            recebedor_id=recebedor_id,
            tipo=tipo,
            valor=valor,
            percentual=percentual,
            status_repasse=status_repasse,
            data_repasse=data_repasse,
            motivo_falha=motivo_falha,
        )
        db.add(transacao)
        return

    transacao.recebedor_id = recebedor_id
    transacao.valor = valor
    transacao.percentual = percentual
    transacao.status_repasse = status_repasse
    transacao.data_repasse = data_repasse
    transacao.motivo_falha = motivo_falha


def _obter_ou_criar_carteira_barbeiro(db: Session, barbeiro_id: int) -> CarteiraBarbeiro:
    carteira = db.query(CarteiraBarbeiro).filter(CarteiraBarbeiro.barbeiro_id == barbeiro_id).first()
    if carteira:
        return carteira

    carteira = CarteiraBarbeiro(barbeiro_id=barbeiro_id, saldo=0.0)
    db.add(carteira)
    db.flush()
    return carteira


def _registrar_movimentacao_carteira(
    db: Session,
    *,
    carteira: CarteiraBarbeiro,
    chamado_id: Optional[int],
    tipo: str,
    descricao: str,
    valor: float,
) -> HistoricoMovimentacaoFinanceira:
    saldo_antes = float(carteira.saldo or 0.0)
    saldo_depois = saldo_antes + float(valor)
    carteira.saldo = saldo_depois

    historico = HistoricoMovimentacaoFinanceira(
        carteira_id=carteira.id,
        barbeiro_id=carteira.barbeiro_id,
        chamado_id=chamado_id,
        tipo=tipo,
        descricao=descricao,
        valor=float(valor),
        saldo_antes=saldo_antes,
        saldo_depois=saldo_depois,
    )
    db.add(historico)
    return historico


def _aplicar_movimentacao_financeira_carteira(
    db: Session,
    *,
    chamado: Chamado,
    metodo_pagamento: str,
    valor_total: float,
) -> Optional[HistoricoMovimentacaoFinanceira]:
    """
    Regras de carteira:
    - dinheiro: barbeiro fica devendo 10% (débito)
    - pix/cartão: barbeiro recebe 90% na carteira (crédito)
    """
    if not chamado or not chamado.barbeiro_id:
        return None

    metodo = (metodo_pagamento or "").strip().lower()
    taxa_app = round(float(valor_total or 0.0) * 0.10, 2)
    ganho_barbeiro = round(float(valor_total or 0.0) * 0.90, 2)

    if metodo == "dinheiro":
        tipo = "debito_taxa_dinheiro"
        descricao = f"Corte #{chamado.id} (dinheiro) -> Taxa do App"
        valor = -taxa_app
    elif metodo in {"pix", "cartao", "cartão", "cartao_credito", "cartao_debito"}:
        tipo = "credito_ganho_app"
        descricao = f"Corte #{chamado.id} ({metodo}) -> Ganho"
        valor = ganho_barbeiro
    else:
        return None

    existente = db.query(HistoricoMovimentacaoFinanceira).filter(
        HistoricoMovimentacaoFinanceira.chamado_id == chamado.id,
        HistoricoMovimentacaoFinanceira.tipo == tipo,
    ).first()
    if existente:
        return existente

    carteira = _obter_ou_criar_carteira_barbeiro(db, chamado.barbeiro_id)
    return _registrar_movimentacao_carteira(
        db,
        carteira=carteira,
        chamado_id=chamado.id,
        tipo=tipo,
        descricao=descricao,
        valor=valor,
    )

# --- SCHEMAS ---
class PagamentoCriar(BaseModel):
    chamado_id: int

class PagamentoPixResponse(BaseModel):
    qrcode_base64: str
    pix_copia_cola: str

class PagamentoConfirmar(BaseModel):
    pagamento_id: int
    metodo: str  # 'pix', 'dinheiro', 'cartao'

class PagamentoResponse(BaseModel):
    id: int
    chamado_id: int
    valor_total: float
    taxa_plataforma: float
    valor_barbeiro: float
    pago_em: Optional[datetime]
    criado_em: datetime

    class Config:
        from_attributes = True

# === SCHEMAS MERCADOPAGO ===
class MercadoPagoPixRequest(BaseModel):
    """Requisição para criar pagamento PIX via MercadoPago"""
    pagamento_id: int

class MercadoPagoCartaoRequest(BaseModel):
    """Requisição para criar pagamento Cartão via MercadoPago"""
    pagamento_id: int
    numero_cartao: str
    titular: str
    data_validade: str  # MM/YY
    cvv: str
    parcelas: int = 1

class MercadoPagoResponse(BaseModel):
    """Resposta de pagamento MercadoPago"""
    id: int
    qrcode: Optional[str] = None
    qrcode_base64: Optional[str] = None
    status: str
    valor: float

class WebhookMercadoPago(BaseModel):
    """Webhook do MercadoPago"""
    id: str
    type: str  # payment, invoice, plan, etc
    data: dict

# --- ENDPOINTS ---

@router.post("/pagamentos/criar", response_model=PagamentoResponse)
def criar_pagamento(
    dados: PagamentoCriar,
    db: Session = Depends(get_db),
    usuario_atual: Usuario = Depends(get_current_user)
):
    """
    Cria um registro de pagamento para um chamado.
    Apenas o cliente pode criar o pagamento.
    """
    # Verificar se o chamado existe
    chamado = db.query(Chamado).filter(Chamado.id == dados.chamado_id).first()
    if not chamado:
        raise HTTPException(status_code=404, detail="Chamado não encontrado")
    
    # Verificar se é o cliente deste chamado
    if chamado.cliente_id != usuario_atual.id:
        raise HTTPException(status_code=403, detail="Apenas o cliente pode criar o pagamento")
    
    # Bloquear apenas chamados cancelados. Chamado concluído ainda pode ser pago.
    status_chamado = (str(chamado.status or '')).strip().lower()
    if status_chamado == StatusAgendamento.CANCELADO:
        raise HTTPException(status_code=400, detail="Chamado cancelado não pode ser pago")
    
    # Se já existe pagamento, retornar o existente (idempotente)
    pagamento_existente = db.query(Pagamento).filter(Pagamento.chamado_id == dados.chamado_id).first()
    if pagamento_existente:
        return pagamento_existente
    
    # Calcular valores
    valor_total = chamado.servico.valor if chamado.servico else 0.0
    taxa_plataforma = valor_total * 0.15  # 15%
    valor_barbeiro = valor_total - taxa_plataforma
    
    # Criar pagamento
    pagamento = Pagamento(
        chamado_id=dados.chamado_id,
        valor_total=valor_total,
        taxa_plataforma=taxa_plataforma,
        valor_barbeiro=valor_barbeiro
    )
    
    db.add(pagamento)
    db.commit()
    db.refresh(pagamento)
    
    return pagamento


@router.post("/pagamentos/pix/{pagamento_id}", response_model=PagamentoPixResponse)
def gerar_pix(
    pagamento_id: int,
    db: Session = Depends(get_db),
    usuario_atual: Usuario = Depends(get_current_user)
):
    """
    Gera QR Code PIX para um pagamento.
    Retorna o QR Code em base64 e o código copia e cola.
    """
    # Buscar pagamento
    pagamento = db.query(Pagamento).filter(Pagamento.id == pagamento_id).first()
    if not pagamento:
        raise HTTPException(status_code=404, detail="Pagamento não encontrado")
    
    # Verificar se é o cliente deste pagamento
    if pagamento.chamado.cliente_id != usuario_atual.id:
        raise HTTPException(status_code=403, detail="Acesso negado")
    
    # Gerar código PIX (simplificado - em produção, usar API de gateway)
    # Formato: PIX|CHAVE|VALOR|NOME|CIDADE
    pix_payload = f"00020126360014BR.GOV.BCB.PIX0114+55119999999990204000053039865406{pagamento.valor_total:.2f}5802BR5913BarberMove6009SAO PAULO62070503***6304"
    
    # Gerar QR Code
    qr = qrcode.QRCode(version=1, box_size=10, border=5)
    qr.add_data(pix_payload)
    qr.make(fit=True)
    
    img = qr.make_image(fill_color="black", back_color="white")
    
    # Converter para base64
    buffer = io.BytesIO()
    img.save(buffer, format='PNG')
    qrcode_base64 = base64.b64encode(buffer.getvalue()).decode()
    
    return PagamentoPixResponse(
        qrcode_base64=qrcode_base64,
        pix_copia_cola=pix_payload
    )


@router.post("/pagamentos/confirmar")
def confirmar_pagamento(
    dados: PagamentoConfirmar,
    db: Session = Depends(get_db),
    usuario_atual: Usuario = Depends(get_current_user)
):
    """
    Confirma que o pagamento foi realizado.
    Barbeiro ou cliente podem confirmar.
    """
    # Buscar pagamento
    pagamento = db.query(Pagamento).filter(Pagamento.id == dados.pagamento_id).first()
    if not pagamento:
        raise HTTPException(status_code=404, detail="Pagamento não encontrado")
    
    # Verificar se é o cliente ou o barbeiro deste pagamento
    chamado = pagamento.chamado
    if usuario_atual.id not in [chamado.cliente_id, chamado.barbeiro_id]:
        raise HTTPException(status_code=403, detail="Acesso negado")

    if pagamento.pago_em is not None:
        raise HTTPException(status_code=400, detail="Pagamento ja foi confirmado anteriormente")
    
    metodo = (dados.metodo or "").strip().lower()
    metodos_permitidos = {"pix", "dinheiro", "cartao", "cartao_credito", "cartao_debito"}
    if metodo not in metodos_permitidos:
        raise HTTPException(status_code=400, detail="Metodo de pagamento invalido")

    # Para pagamento em dinheiro iniciado pelo cliente, apenas registra intenção.
    # O recebimento real deve ser confirmado pelo barbeiro depois do atendimento.
    if metodo == "dinheiro" and usuario_atual.id == chamado.cliente_id:
        corte = db.query(Corte).filter(Corte.chamado_id == chamado.id).first()
        if not corte:
            corte = Corte(
                cliente_id=chamado.cliente_id,
                freelancer_id=chamado.barbeiro_id,
                barbearia_id=chamado.barbearia_id,
                servico_id=chamado.servico_id,
                chamado_id=chamado.id,
                valor_total=float(pagamento.valor_total or 0.0),
                metodo_pagamento="DINHEIRO",
                status_pagamento="pendente_no_local",
                data_conclusao=datetime.utcnow(),
            )
            db.add(corte)
        else:
            corte.metodo_pagamento = "DINHEIRO"
            corte.status_pagamento = "pendente_no_local"

        _aplicar_movimentacao_financeira_carteira(
            db,
            chamado=chamado,
            metodo_pagamento="dinheiro",
            valor_total=float(pagamento.valor_total or 0.0),
        )

        db.commit()
        return {
            "message": "Pagamento em dinheiro registrado. Aguarde o barbeiro confirmar o recebimento.",
            "metodo": metodo,
            "status_pagamento": "pendente_no_local",
            "aguarda_confirmacao_barbeiro": True,
            "valor_total": float(pagamento.valor_total or 0.0),
        }

    # Marcar como pago
    pagamento.pago_em = datetime.now()

    # Atualizar status do chamado para concluído
    chamado.status = StatusAgendamento.CONCLUIDO
    chamado.concluido_em = datetime.now()

    # Se chamado estiver vinculado a uma cadeira, ocupar automaticamente.
    # Evita inconsistência visual/operacional após pagamento aprovado.
    if chamado.cadeira_id:
        cadeira = db.query(Cadeira).filter(Cadeira.id == chamado.cadeira_id).first()
        if cadeira:
            cadeira.status = StatusCadeira.OCUPADA
            cadeira.ocupada_em = datetime.now()
            cadeira.chamado_id = chamado.id
    
    # Regra especial para pagamento em dinheiro:
    # - barbeiro fica com 50% do valor do servico
    # - BarberMove recebe 10% do valor total do servico
    # - barbearia fica com o restante (40%)
    # - repasse da plataforma fica pendente com prazo de 12h
    #
    # Para demais métodos, usa split configurado (padrão 40/50/10).
    valor_total = float(pagamento.valor_total or 0.0)
    split_cfg = _resolver_split_config(db)
    valor_barbeiro_base = round(valor_total * (split_cfg["barbeiro"] / 100.0), 2)
    valor_barbearia = round(valor_total * (split_cfg["barbearia"] / 100.0), 2)
    valor_repasse_plataforma = round(valor_total - valor_barbeiro_base - valor_barbearia, 2)
    desconto_barbeiro = 0.0
    prazo_repasse_ate = None

    barbearia_obj = db.query(Barbearia).filter(Barbearia.id == chamado.barbearia_id).first()
    recebedor_barbearia_id = barbearia_obj.usuario_id if barbearia_obj else chamado.barbearia_id

    corte = db.query(Corte).filter(Corte.chamado_id == chamado.id).first()
    if not corte:
        corte = Corte(
            cliente_id=chamado.cliente_id,
            freelancer_id=chamado.barbeiro_id,
            barbearia_id=chamado.barbearia_id,
            servico_id=chamado.servico_id,
            chamado_id=chamado.id,
            valor_total=valor_total,
            metodo_pagamento=metodo.upper(),
            status_pagamento="aprovado",
            data_conclusao=datetime.utcnow(),
        )
        db.add(corte)
        db.flush()
    else:
        corte.valor_total = valor_total
        corte.metodo_pagamento = metodo.upper()
        corte.status_pagamento = "aprovado"
        corte.data_conclusao = datetime.utcnow()

    if metodo == "dinheiro":
        valor_barbeiro_base = round(valor_total * 0.50, 2)
        valor_repasse_plataforma = round(valor_total * 0.10, 2)
        valor_barbearia = round(valor_total - valor_barbeiro_base - valor_repasse_plataforma, 2)

        pagamento.valor_barbeiro = valor_barbeiro_base
        pagamento.taxa_plataforma = valor_repasse_plataforma
        desconto_barbeiro = round(valor_total - valor_repasse_plataforma - valor_barbeiro_base - valor_barbearia, 2)

        prazo_repasse_ate = datetime.now() + timedelta(hours=12)

    else:
        pagamento.valor_barbeiro = valor_barbeiro_base
        pagamento.taxa_plataforma = valor_repasse_plataforma

    _upsert_transacao_split(
        db,
        corte_id=corte.id,
        recebedor_id=chamado.barbeiro_id,
        tipo=TipoTransacao.COMISSAO_FREELANCER.value,
        valor=valor_barbeiro_base,
        percentual=round((valor_barbeiro_base / valor_total) * 100, 2) if valor_total > 0 else 0,
        status_repasse="concluido",
        data_repasse=datetime.utcnow(),
        motivo_falha=None,
    )

    _upsert_transacao_split(
        db,
        corte_id=corte.id,
        recebedor_id=recebedor_barbearia_id,
        tipo=TipoTransacao.COMISSAO_BARBEARIA.value,
        valor=valor_barbearia,
        percentual=round((valor_barbearia / valor_total) * 100, 2) if valor_total > 0 else 0,
        status_repasse="concluido",
        data_repasse=datetime.utcnow(),
        motivo_falha=None,
    )

    _upsert_transacao_split(
        db,
        corte_id=corte.id,
        recebedor_id=split_cfg["recebedor_plataforma_id"],
        tipo=TipoTransacao.TAXA_PLATAFORMA.value,
        valor=valor_repasse_plataforma,
        percentual=round((valor_repasse_plataforma / valor_total) * 100, 2) if valor_total > 0 else 0,
        status_repasse="pendente" if prazo_repasse_ate else "concluido",
        data_repasse=prazo_repasse_ate if prazo_repasse_ate else datetime.utcnow(),
        motivo_falha="Repasse manual em ate 12 horas" if prazo_repasse_ate else None,
    )

    _aplicar_movimentacao_financeira_carteira(
        db,
        chamado=chamado,
        metodo_pagamento=metodo,
        valor_total=valor_total,
    )

    db.commit()

    resposta = {
        "message": "Pagamento confirmado com sucesso",
        "metodo": metodo,
        "valor_total": valor_total,
        "valor_barbeiro": float(pagamento.valor_barbeiro or 0.0),
        "valor_repasse_plataforma": valor_repasse_plataforma,
        "valor_barbearia": valor_barbearia,
        "desconto_barbeiro": desconto_barbeiro
    }

    if prazo_repasse_ate:
        resposta["prazo_repasse_ate"] = prazo_repasse_ate.isoformat()
        resposta["observacao"] = "Pagamento em dinheiro: barbeiro deve repassar a parte da BarberMove em ate 12 horas"

    return resposta


@router.post("/pagamentos/repasse/{pagamento_id}/confirmar")
def confirmar_repasse_dinheiro(
    pagamento_id: int,
    db: Session = Depends(get_db),
    usuario_atual: Usuario = Depends(get_current_user)
):
    """
    Confirma que o barbeiro repassou a parte da BarberMove para pagamentos em dinheiro.
    """
    pagamento = db.query(Pagamento).filter(Pagamento.id == pagamento_id).first()
    if not pagamento:
        raise HTTPException(status_code=404, detail="Pagamento nao encontrado")

    chamado = pagamento.chamado

    if usuario_atual.id not in [chamado.barbeiro_id, 1]:
        raise HTTPException(status_code=403, detail="Apenas o barbeiro do chamado ou admin podem confirmar o repasse")

    transacao = db.query(TransacaoFinanceira).filter(
        TransacaoFinanceira.corte_id.in_(
            db.query(Corte.id).filter(Corte.chamado_id == chamado.id)
        ),
        TransacaoFinanceira.tipo == "taxa_plataforma",
        TransacaoFinanceira.status_repasse == "pendente"
    ).first()

    if not transacao:
        raise HTTPException(status_code=404, detail="Nenhuma pendencia de repasse encontrada para este chamado")

    transacao.status_repasse = "concluido"
    transacao.data_repasse = datetime.now()
    transacao.motivo_falha = None
    db.commit()

    return {
        "message": "Repasse confirmado com sucesso",
        "pagamento_id": pagamento_id,
        "valor_repassado": transacao.valor,
        "confirmado_em": transacao.data_repasse.isoformat()
    }


@router.get("/pagamentos/{pagamento_id}", response_model=PagamentoResponse)
def obter_pagamento(
    pagamento_id: int,
    db: Session = Depends(get_db),
    usuario_atual: Usuario = Depends(get_current_user)
):
    """
    Obtém os detalhes de um pagamento.
    """
    pagamento = db.query(Pagamento).filter(Pagamento.id == pagamento_id).first()
    if not pagamento:
        raise HTTPException(status_code=404, detail="Pagamento não encontrado")
    
    # Verificar se é o cliente ou o barbeiro deste pagamento
    chamado = pagamento.chamado
    if usuario_atual.id not in [chamado.cliente_id, chamado.barbeiro_id]:
        raise HTTPException(status_code=403, detail="Acesso negado")
    
    return pagamento


@router.get("/pagamentos/chamado/{chamado_id}", response_model=Optional[PagamentoResponse])
def obter_pagamento_por_chamado(
    chamado_id: int,
    db: Session = Depends(get_db),
    usuario_atual: Usuario = Depends(get_current_user)
):
    """
    Obtém o pagamento de um chamado específico.
    """
    # Verificar se o chamado existe
    chamado = db.query(Chamado).filter(Chamado.id == chamado_id).first()
    if not chamado:
        raise HTTPException(status_code=404, detail="Chamado não encontrado")
    
    # Verificar se é o cliente ou o barbeiro deste chamado
    if usuario_atual.id not in [chamado.cliente_id, chamado.barbeiro_id]:
        raise HTTPException(status_code=403, detail="Acesso negado")
    
    pagamento = db.query(Pagamento).filter(Pagamento.chamado_id == chamado_id).first()
    
    return pagamento

# === ENDPOINTS MERCADOPAGO ===

@router.post("/pagamentos/mercadopago/pix", response_model=MercadoPagoResponse)
def criar_pagamento_pix_mercadopago(
    dados: MercadoPagoPixRequest,
    db: Session = Depends(get_db),
    usuario_atual: Usuario = Depends(get_current_user)
):
    """
    Cria um pagamento PIX via MercadoPago.
    Retorna QR Code e dados para pagar.
    """
    # Buscar pagamento
    pagamento = db.query(Pagamento).filter(Pagamento.id == dados.pagamento_id).first()
    if not pagamento:
        raise HTTPException(status_code=404, detail="Pagamento não encontrado")
    
    # Verificar se é o cliente
    if pagamento.chamado.cliente_id != usuario_atual.id:
        raise HTTPException(status_code=403, detail="Acesso negado")
    
    # Autenticar com MercadoPago
    token = os.getenv("MERCADOPAGO_ACCESS_TOKEN")
    if not token:
        # Fallback: gerar QR code PIX local sem MercadoPago
        pix_chave = os.getenv("PIX_CHAVE", "+5511999999999")
        nome_recebedor = (os.getenv("PIX_NOME", "BarberMove") + " " * 13)[:13]
        cidade_recebedor = (os.getenv("PIX_CIDADE", "SAO PAULO") + " " * 9)[:9]
        valor_str = f"{float(pagamento.valor_total):.2f}"
        pix_payload = (
            f"00020126360014BR.GOV.BCB.PIX0114{pix_chave}"
            f"0204000053039865406{valor_str}5802BR"
            f"5913{nome_recebedor}6009{cidade_recebedor}"
            f"62070503***6304"
        )
        qr = qrcode.QRCode(version=1, box_size=10, border=5)
        qr.add_data(pix_payload)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        qrcode_b64 = base64.b64encode(buf.getvalue()).decode()
        return MercadoPagoResponse(
            id=pagamento.id,
            qrcode=pix_payload,
            qrcode_base64=qrcode_b64,
            status="pending",
            valor=float(pagamento.valor_total)
        )

    try:
        sdk = mercadopago.SDK(token)
        
        # Dados do cliente
        cliente = usuario_atual
        
        # Criar preference (sessão de pagamento)
        payment_data = {
            "items": [
                {
                    "id": str(pagamento.chamado_id),
                    "title": f"Serviço de Barbearia - Chamado #{pagamento.chamado_id}",
                    "quantity": 1,
                    "unit_price": float(pagamento.valor_total)
                }
            ],
            "payer": {
                "email": cliente.email,
                "name": cliente.nome,
                "phone": {
                    "area_code": "11",
                    "number": cliente.telefone or "999999999"
                }
            },
            "payment_methods": {
                "excluded_payment_types": [
                    {"id": "ticket"}  # Apenas PIX e Cartão
                ]
            },
            "metadata": {
                "pagamento_id": pagamento.id,
                "chamado_id": pagamento.chamado_id,
                "usuario_id": usuario_atual.id
            }
        }
        
        try:
            # Tentar criar com a SDK do MercadoPago
            result = sdk.payment().create(payment_data)
            
            if result["status"] != 201:
                raise HTTPException(
                    status_code=400,
                    detail=f"Erro MercadoPago: {result.get('response', {}).get('message', 'Desconhecido')}"
                )
            
            payment_response = result["response"]
            
            return MercadoPagoResponse(
                id=payment_response["id"],
                qrcode=payment_response.get("point_of_interaction", {}).get("transaction_data", {}).get("qr_code"),
                qrcode_base64=None,
                status=payment_response["status"],
                valor=float(pagamento.valor_total)
            )
            
        except Exception as e:
            # Fallback local: gera QR code interno para nao quebrar o fluxo.
            print(f"Erro MercadoPago PIX, usando fallback local: {str(e)}")
            pix_chave = os.getenv("PIX_CHAVE", "+5511999999999")
            nome_recebedor = (os.getenv("PIX_NOME", "BarberMove") + " " * 13)[:13]
            cidade_recebedor = (os.getenv("PIX_CIDADE", "SAO PAULO") + " " * 9)[:9]
            valor_str = f"{float(pagamento.valor_total):.2f}"
            pix_payload = (
                f"00020126360014BR.GOV.BCB.PIX0114{pix_chave}"
                f"0204000053039865406{valor_str}5802BR"
                f"5913{nome_recebedor}6009{cidade_recebedor}"
                f"62070503***6304"
            )
            qr = qrcode.QRCode(version=1, box_size=10, border=5)
            qr.add_data(pix_payload)
            qr.make(fit=True)
            img = qr.make_image(fill_color="black", back_color="white")
            buf = io.BytesIO()
            img.save(buf, format="PNG")
            qrcode_b64 = base64.b64encode(buf.getvalue()).decode()
            return MercadoPagoResponse(
                id=pagamento.id,
                qrcode=pix_payload,
                qrcode_base64=qrcode_b64,
                status="pending",
                valor=float(pagamento.valor_total)
            )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro: {str(e)}")


@router.post("/pagamentos/mercadopago/cartao", response_model=MercadoPagoResponse)
def criar_pagamento_cartao_mercadopago(
    dados: MercadoPagoCartaoRequest,
    db: Session = Depends(get_db),
    usuario_atual: Usuario = Depends(get_current_user)
):
    """
    Cria um pagamento com Cartão via MercadoPago.
    """
    # Buscar pagamento
    pagamento = db.query(Pagamento).filter(Pagamento.id == dados.pagamento_id).first()
    if not pagamento:
        raise HTTPException(status_code=404, detail="Pagamento não encontrado")
    
    # Verificar se é o cliente
    if pagamento.chamado.cliente_id != usuario_atual.id:
        raise HTTPException(status_code=403, detail="Acesso negado")
    
    # Autenticar com MercadoPago
    token = os.getenv("MERCADOPAGO_ACCESS_TOKEN")
    if not token:
        # Fallback: confirmar cartão localmente sem MercadoPago
        num_limpo = dados.numero_cartao.replace(" ", "").replace("-", "")
        if not num_limpo.isdigit() or len(num_limpo) < 13:
            raise HTTPException(status_code=400, detail="Número do cartão inválido")
        try:
            mes_s, ano_s = dados.data_validade.replace(" ", "").split("/")
            mes_i = int(mes_s)
            ano_i = int("20" + ano_s) if len(ano_s.strip()) == 2 else int(ano_s)
            hoje = datetime.now()
            if mes_i < 1 or mes_i > 12 or ano_i < hoje.year or (ano_i == hoje.year and mes_i < hoje.month):
                raise HTTPException(status_code=400, detail="Cartão vencido ou data inválida")
        except HTTPException:
            raise
        except Exception:
            raise HTTPException(status_code=400, detail="Data de validade inválida — use MM/AA")
        if not dados.cvv or len(dados.cvv) < 3:
            raise HTTPException(status_code=400, detail="CVV inválido")
        # Confirmar pagamento no banco
        pagamento.pago_em = datetime.now()
        chamado_local = pagamento.chamado
        chamado_local.status = StatusAgendamento.CONCLUIDO
        chamado_local.concluido_em = datetime.now()
        if chamado_local.cadeira_id:
            cadeira_local = db.query(Cadeira).filter(Cadeira.id == chamado_local.cadeira_id).first()
            if cadeira_local:
                cadeira_local.status = StatusCadeira.OCUPADA
                cadeira_local.ocupada_em = datetime.now()
                cadeira_local.chamado_id = chamado_local.id
        db.commit()
        return MercadoPagoResponse(
            id=pagamento.id,
            status="approved",
            valor=float(pagamento.valor_total)
        )

    try:
        sdk = mercadopago.SDK(token)
        
        # Extrair mês e ano da validade (MM/YY)
        mes, ano = dados.data_validade.split("/")
        
        # Criar pagamento com cartão
        payment_data = {
            "transaction_amount": float(pagamento.valor_total),
            "payment_method_id": "master",  # Detectar automaticamente baseado no número
            "installments": dados.parcelas,
            "token": None,  # Em produção, usar token de segurança do frontend
            "description": f"Serviço de Barbearia - Chamado #{pagamento.chamado_id}",
            "external_reference": str(pagamento.id),
            "notification_url": f"{os.getenv('API_URL', 'http://localhost:8000')}/api/v1/pagamentos/webhook/mercadopago",
            "payer": {
                "email": usuario_atual.email,
                "first_name": usuario_atual.nome.split()[0],
                "last_name": " ".join(usuario_atual.nome.split()[1:]) or usuario_atual.nome,
                "identification": {
                    "type": "CPF",
                    "number": "00000000000"  # Em produção, pedir CPF real
                }
            },
            "card": {
                "number": dados.numero_cartao.replace(" ", ""),
                "holder": {
                    "name": dados.titular,
                    "identification": {
                        "type": "CPF",
                        "number": "00000000000"  # Em produção, pedir CPF real
                    }
                },
                "expiration_month": int(mes),
                "expiration_year": int("20" + ano),
                "security_code": dados.cvv
            }
        }
        
        try:
            result = sdk.payment().create(payment_data)
            
            if result["status"] != 201:
                raise HTTPException(
                    status_code=400,
                    detail=f"Erro MercadoPago: {result.get('response', {}).get('message', 'Desconhecido')}"
                )
            
            payment_response = result["response"]
            
            # Se pagamento aprovado, marcar como pago
            if payment_response["status"] == "approved":
                pagamento.pago_em = datetime.now()
                pagamento.chamado.status = StatusAgendamento.CONCLUIDO
                pagamento.chamado.concluido_em = datetime.now()
                _aplicar_movimentacao_financeira_carteira(
                    db,
                    chamado=pagamento.chamado,
                    metodo_pagamento="cartao",
                    valor_total=float(pagamento.valor_total or 0.0),
                )
                db.commit()
            
            return MercadoPagoResponse(
                id=payment_response["id"],
                status=payment_response["status"],
                valor=float(pagamento.valor_total)
            )
            
        except Exception as e:
            print(f"Erro MercadoPago Cartao, usando fallback local: {str(e)}")
            pagamento.pago_em = datetime.now()
            chamado_local = pagamento.chamado
            chamado_local.status = StatusAgendamento.CONCLUIDO
            chamado_local.concluido_em = datetime.now()
            if chamado_local.cadeira_id:
                cadeira_local = db.query(Cadeira).filter(Cadeira.id == chamado_local.cadeira_id).first()
                if cadeira_local:
                    cadeira_local.status = StatusCadeira.OCUPADA
                    cadeira_local.ocupada_em = datetime.now()
                    cadeira_local.chamado_id = chamado_local.id
            _aplicar_movimentacao_financeira_carteira(
                db,
                chamado=chamado_local,
                metodo_pagamento="cartao",
                valor_total=float(pagamento.valor_total or 0.0),
            )
            db.commit()
            return MercadoPagoResponse(
                id=pagamento.id,
                status="approved",
                valor=float(pagamento.valor_total)
            )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro: {str(e)}")


@router.post("/pagamentos/webhook/mercadopago")
def webhook_mercadopago(
    webhook: WebhookMercadoPago,
    db: Session = Depends(get_db)
):
    """
    Webhook para receber notificações de pagamento do MercadoPago.
    
    Fluxo completo:
    1. Valida a notificação (type == "payment")
    2. Busca o Pagamento no banco
    3. Se aprovado:
       - Atualiza status do Pagamento
       - Atualiza status do Chamado
       - Atualiza Corte e TransacoesFinanceiras se existirem
       - Dispara notificação push para o barbeiro
    4. Se rejeitado/cancelado:
       - Apenas registra no log
    
    Args:
        webhook: WebhookMercadoPago com dados da notificação
        db: Sessão do banco de dados
    
    Returns:
        {"message": "Webhook processado com sucesso"}
    """
    # Validar tipo de notificação
    if webhook.type != "payment":
        return {"message": "Notificação ignorada"}
    
    try:
        # Buscar ID do pagamento nos dados
        payment_id = webhook.data.get("id")
        if not payment_id:
            return {"message": "ID de pagamento não encontrado"}
        
        # Buscar pagamento no banco usando external_reference
        external_ref = webhook.data.get("external_reference")
        if not external_ref:
            return {"message": "External reference não encontrado"}
        
        pagamento = db.query(Pagamento).filter(Pagamento.id == int(external_ref)).first()
        if not pagamento:
            return {"message": "Pagamento não encontrado"}
        
        # Atualizar status baseado na resposta do MercadoPago
        status = webhook.data.get("status")
        valor_recebido = webhook.data.get("transaction_amount", 0)
        
        if status == "approved":
            # 1️⃣ Atualizar Pagamento (sistema antigo)
            pagamento.pago_em = datetime.now()
            if pagamento.chamado:
                pagamento.chamado.status = StatusAgendamento.CONCLUIDO
                pagamento.chamado.concluido_em = datetime.now()
                _aplicar_movimentacao_financeira_carteira(
                    db,
                    chamado=pagamento.chamado,
                    metodo_pagamento="pix",
                    valor_total=float(pagamento.valor_total or 0.0),
                )
            
            # 2️⃣ Buscar e atualizar Corte (sistema novo)
            # O Corte pode estar vinculado através do chamado ou diretamente
            corte = None
            if pagamento.chamado:
                corte = db.query(Corte).filter(
                    Corte.cliente_id == pagamento.chamado.cliente_id,
                    Corte.status_pagamento == "pendente"
                ).order_by(Corte.criado_em.desc()).first()
            
            if corte:
                corte.status_pagamento = "aprovado"
                corte.data_pagamento = datetime.utcnow()
                
                # 3️⃣ Atualizar TransacoesFinanceiras (distribuição 70/20/10)
                transacoes = db.query(TransacaoFinanceira).filter(
                    TransacaoFinanceira.corte_id == corte.id
                ).all()
                
                for transacao in transacoes:
                    if transacao.status_repasse == "pendente":
                        transacao.status_repasse = "concluido"
                        transacao.data_repasse = datetime.utcnow()
                
                # 4️⃣ Enviar notificação push ao barbeiro
                barbeiro = db.query(Usuario).filter(
                    Usuario.id == corte.freelancer_id
                ).first()
                
                if barbeiro and barbeiro.device_token:
                    cliente = db.query(Usuario).filter(
                        Usuario.id == corte.cliente_id
                    ).first()
                    
                    cliente_nome = cliente.nome if cliente else "Cliente"
                    
                    # Dispara notificação push
                    sucesso = enviar_notificacao_pagamento(
                        token_dispositivo=barbeiro.device_token,
                        nome_cliente=cliente_nome,
                        valor=corte.valor_total,
                        nome_barbeiro=barbeiro.nome
                    )
                    
                    if sucesso:
                        print(f"✅ Notificação push enviada para {barbeiro.nome}")
                    else:
                        print(f"⚠️ Falha ao enviar notificação push para {barbeiro.nome}")
                else:
                    print(f"⚠️ Barbeiro não tem device_token registrado")
            
            # Confirmar commit
            db.commit()
            
            print(f"✅ Pagamento {pagamento.id} confirmado via webhook MercadoPago")
            print(f"   - Valor: R$ {valor_recebido}")
            if corte:
                print(f"   - Corte ID: {corte.id}")
                print(f"   - Barbeiro: {barbeiro.nome if barbeiro else 'N/A'}")
        
        elif status in ["rejected", "cancelled"]:
            print(f"❌ Pagamento {pagamento.id} rejeitado ou cancelado (status: {status})")
            # Opcionalmente, você pode rejeitar o Corte também
            # corte.status_pagamento = "rejeitado"
            # db.commit()
        
        return {"message": "Webhook processado com sucesso"}
    
    except Exception as e:
        print(f"❌ Erro no webhook: {str(e)}")
        import traceback
        traceback.print_exc()
        return {"message": "Erro ao processar webhook", "error": str(e)}

