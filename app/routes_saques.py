# --- ARQUIVO: app/routes_saques.py ---
# Rotas para gerenciar saques de barbeiros

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func
from pydantic import BaseModel
from datetime import datetime
from typing import Optional

from .database import get_db
from .models import Usuario, Saque, TransacaoFinanceira, TipoTransacao
from .routes import get_current_user

router = APIRouter(prefix="/saques", tags=["Saques"])


def _calcular_saldo_barbeiro(db: Session, usuario_id: int):
    saldo_total = db.query(
        func.coalesce(func.sum(TransacaoFinanceira.valor), 0.0)
    ).filter(
        TransacaoFinanceira.recebedor_id == usuario_id,
        TransacaoFinanceira.tipo == TipoTransacao.COMISSAO_FREELANCER.value,
        TransacaoFinanceira.status_repasse == "concluido",
    ).scalar() or 0.0

    saldo_bloqueado = db.query(
        func.coalesce(func.sum(Saque.valor), 0.0)
    ).filter(
        Saque.usuario_id == usuario_id,
        Saque.status.in_(["pendente", "processando"]),
    ).scalar() or 0.0

    saldo_disponivel = max(float(saldo_total) - float(saldo_bloqueado), 0.0)
    return {
        "saldo_total": round(float(saldo_total), 2),
        "saldo_bloqueado": round(float(saldo_bloqueado), 2),
        "saldo_disponivel": round(float(saldo_disponivel), 2),
    }

# ============ SCHEMAS ============
class SaqueRequest(BaseModel):
    valor: float
    banco: str
    agencia: str
    conta: str
    tipo_conta: str = "corrente"

class SaqueResponse(BaseModel):
    id: int
    usuario_id: int
    valor: float
    valor_liquido: float
    taxa: float
    status: str
    banco: str
    agencia: str
    conta: str
    tipo_conta: str
    criado_em: datetime
    processado_em: Optional[datetime] = None

    class Config:
        from_attributes = True

# ============ ENDPOINTS ============

@router.post("/solicitar")
def solicitar_saque(
    dados: SaqueRequest,
    current_user: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Barbeiro solicita um saque
    """
    # Validações
    if current_user.tipo != "barbeiro":
        raise HTTPException(
            status_code=403,
            detail="Apenas barbeiros podem solicitar saques"
        )
    
    if dados.valor <= 0:
        raise HTTPException(
            status_code=400,
            detail="Valor de saque deve ser maior que zero"
        )
    
    saldos = _calcular_saldo_barbeiro(db, current_user.id)
    if dados.valor > saldos["saldo_disponivel"]:
        raise HTTPException(
            status_code=400,
            detail=f"Saldo insuficiente. Disponível: R$ {saldos['saldo_disponivel']:.2f}"
        )

    # Calcular com taxa de 10%
    taxa = dados.valor * 0.10
    valor_liquido = dados.valor - taxa
    
    # Criar saque
    novo_saque = Saque(
        usuario_id=current_user.id,
        valor=dados.valor,
        valor_liquido=valor_liquido,
        taxa=taxa,
        status="pendente",
        banco=dados.banco,
        agencia=dados.agencia,
        conta=dados.conta,
        tipo_conta=dados.tipo_conta,
        criado_em=datetime.utcnow()
    )
    
    db.add(novo_saque)
    db.commit()
    db.refresh(novo_saque)
    
    return {
        "success": True,
        "message": "Saque solicitado com sucesso! Você receberá em 1-2 dias úteis",
        "saque": {
            "id": novo_saque.id,
            "valor": novo_saque.valor,
            "valor_liquido": novo_saque.valor_liquido,
            "taxa": novo_saque.taxa,
            "status": novo_saque.status
        }
    }

@router.get("/historico")
def listar_saques(
    current_user: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Lista histórico de saques do barbeiro"""
    if current_user.tipo != "barbeiro":
        raise HTTPException(
            status_code=403,
            detail="Apenas barbeiros podem acessar saques"
        )
    
    saques = db.query(Saque).filter(
        Saque.usuario_id == current_user.id
    ).order_by(Saque.criado_em.desc()).all()
    
    return [
        {
            "id": s.id,
            "valor": s.valor,
            "valor_liquido": s.valor_liquido,
            "taxa": s.taxa,
            "status": s.status,
            "banco": s.banco,
            "conta": s.conta,
            "criado_em": s.criado_em.isoformat() if s.criado_em else None,
            "processado_em": s.processado_em.isoformat() if s.processado_em else None
        }
        for s in saques
    ]

@router.get("/saldo")
def obter_saldo(
    current_user: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Retorna saldo disponível do barbeiro"""
    if current_user.tipo != "barbeiro":
        raise HTTPException(
            status_code=403,
            detail="Apenas barbeiros podem verificar saldo"
        )
    
    return _calcular_saldo_barbeiro(db, current_user.id)
