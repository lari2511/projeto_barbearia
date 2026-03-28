"""
Rotas para gerenciar preços customizados dos barbeiros
Permite que cada barbeiro personalize os valores dos serviços
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import Optional
from pydantic import BaseModel
from datetime import datetime

from app.database import get_db
from app.models import Usuario, Servico, PrecoCustomizado
from app.routes import get_current_user

router = APIRouter(prefix="/api/v1/precos", tags=["Preços"])

# ============================================================================
# SCHEMAS
# ============================================================================

class PrecoCustomizadoUpdate(BaseModel):
    valor_novo: float
    descricao_motivo: Optional[str] = None

class PrecoCustomizadoResponse(BaseModel):
    id: int
    barbeiro_id: int
    servico_id: int
    servico_nome: str
    preco_original: float
    preco_customizado: float
    desconto_percentual: float
    ativo: bool
    criado_em: datetime
    
    class Config:
        from_attributes = True

# ============================================================================
# ENDPOINTS
# ============================================================================

@router.get("/meus-precos", response_model=list[PrecoCustomizadoResponse])
def listar_meus_precos(
    db: Session = Depends(get_db),
    usuario = Depends(get_current_user)
):
    """Lista preços customizados do barbeiro logado"""
    if usuario.tipo != "barbeiro":
        raise HTTPException(status_code=403, detail="Apenas barbeiros podem acessar")
    
    precos = db.query(PrecoCustomizado).filter(
        PrecoCustomizado.barbeiro_id == usuario.id,
        PrecoCustomizado.ativo == True
    ).all()
    
    return precos

@router.post("/customizar/{servico_id}")
def customizar_preco(
    servico_id: int,
    dados: PrecoCustomizadoUpdate,
    db: Session = Depends(get_db),
    usuario = Depends(get_current_user)
):
    """Cria ou atualiza preço customizado para um serviço"""
    if usuario.tipo != "barbeiro":
        raise HTTPException(status_code=403, detail="Apenas barbeiros podem acessar")
    
    # Verificar se serviço existe
    servico = db.query(Servico).filter(Servico.id == servico_id).first()
    if not servico:
        raise HTTPException(status_code=404, detail="Serviço não encontrado")
    
    # Verificar se já existe preço customizado
    preco_existente = db.query(PrecoCustomizado).filter(
        PrecoCustomizado.barbeiro_id == usuario.id,
        PrecoCustomizado.servico_id == servico_id
    ).first()
    
    if preco_existente:
        preco_existente.preco_customizado = dados.valor_novo
        preco_existente.desconto_percentual = ((servico.valor - dados.valor_novo) / servico.valor) * 100 if servico.valor > 0 else 0
    else:
        desconto = ((servico.valor - dados.valor_novo) / servico.valor) * 100 if servico.valor > 0 else 0
        preco_existente = PrecoCustomizado(
            barbeiro_id=usuario.id,
            servico_id=servico_id,
            preco_original=servico.valor,
            preco_customizado=dados.valor_novo,
            desconto_percentual=desconto,
            ativo=True
        )
        db.add(preco_existente)
    
    db.commit()
    db.refresh(preco_existente)
    
    return {
        "status": "ok",
        "preco_id": preco_existente.id,
        "valor_novo": dados.valor_novo,
        "desconto_percentual": preco_existente.desconto_percentual
    }

@router.delete("/{preco_id}")
def remover_preco_customizado(
    preco_id: int,
    db: Session = Depends(get_db),
    usuario = Depends(get_current_user)
):
    """Remove customização de preço (volta para o padrão)"""
    if usuario.tipo != "barbeiro":
        raise HTTPException(status_code=403, detail="Apenas barbeiros podem acessar")
    
    preco = db.query(PrecoCustomizado).filter(
        PrecoCustomizado.id == preco_id,
        PrecoCustomizado.barbeiro_id == usuario.id
    ).first()
    
    if not preco:
        raise HTTPException(status_code=404, detail="Preço customizado não encontrado")
    
    preco.ativo = False
    db.commit()
    
    return {"status": "ok", "mensagem": "Preço customizado removido"}

@router.get("/servico/{servico_id}")
def obter_preco_customizado(
    servico_id: int,
    barbeiro_id: Optional[int] = None,
    db: Session = Depends(get_db),
    usuario = Depends(get_current_user)
):
    """Obtém preço customizado de um barbeiro para um serviço"""
    if not barbeiro_id:
        barbeiro_id = usuario.id
    
    preco = db.query(PrecoCustomizado).filter(
        PrecoCustomizado.barbeiro_id == barbeiro_id,
        PrecoCustomizado.servico_id == servico_id,
        PrecoCustomizado.ativo == True
    ).first()
    
    if not preco:
        # Retornar preço original do serviço
        servico = db.query(Servico).filter(Servico.id == servico_id).first()
        if not servico:
            raise HTTPException(status_code=404, detail="Serviço não encontrado")
        return {
            "servico_id": servico_id,
            "preco": servico.valor,
            "customizado": False
        }
    
    return {
        "servico_id": servico_id,
        "preco": preco.preco_customizado,
        "preco_original": preco.preco_original,
        "desconto_percentual": preco.desconto_percentual,
        "customizado": True
    }

@router.post("/listar-todos-servicos")
def listar_todos_servicos_para_customize(
    db: Session = Depends(get_db),
    usuario = Depends(get_current_user)
):
    """Lista todos os serviços disponíveis para customização com seus preços"""
    if usuario.tipo != "barbeiro":
        raise HTTPException(status_code=403, detail="Apenas barbeiros podem acessar")
    
    servicos = db.query(Servico).all()
    
    resultado = []
    for servico in servicos:
        # Buscar preço customizado se existir
        preco_custom = db.query(PrecoCustomizado).filter(
            PrecoCustomizado.barbeiro_id == usuario.id,
            PrecoCustomizado.servico_id == servico.id,
            PrecoCustomizado.ativo == True
        ).first()
        
        resultado.append({
            "id": servico.id,
            "nome": servico.nome,
            "preco_original": servico.valor,
            "preco_customizado": preco_custom.preco_customizado if preco_custom else None,
            "desconto_percentual": preco_custom.desconto_percentual if preco_custom else 0,
            "tem_customizacao": preco_custom is not None
        })
    
    return resultado
