# --- ARQUIVO: app/routes_pagamentos.py ---
# Rotas para gerenciamento de pagamentos

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import Optional
from datetime import datetime
import qrcode
import io
import base64
from pydantic import BaseModel

from .database import get_db
from .models import Pagamento, Chamado, Usuario, StatusAgendamento
from .routes import get_current_user

router = APIRouter(tags=["Pagamentos"])

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
    
    # Verificar se o chamado está confirmado
    if chamado.status != StatusAgendamento.CONFIRMADO:
        raise HTTPException(status_code=400, detail="Chamado precisa estar confirmado")
    
    # Verificar se já existe pagamento
    pagamento_existente = db.query(Pagamento).filter(Pagamento.chamado_id == dados.chamado_id).first()
    if pagamento_existente:
        raise HTTPException(status_code=400, detail="Pagamento já existe para este chamado")
    
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
    
    # Marcar como pago
    pagamento.pago_em = datetime.utcnow()
    
    # Atualizar status do chamado para concluído
    chamado.status = StatusAgendamento.CONCLUIDO
    chamado.concluido_em = datetime.utcnow()
    
    db.commit()
    
    return {"message": "Pagamento confirmado com sucesso", "metodo": dados.metodo}


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
