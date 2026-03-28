"""
--- ARQUIVO: app/routes_assinatura.py ---
Rotas para gerenciamento de assinaturas e cálculo de mensalidades progressivas
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Dict, Optional
from datetime import datetime
from pydantic import BaseModel

from .database import get_db
from .models import Barbearia, Usuario, Assinatura
from .routes import get_current_user

router = APIRouter(prefix="/api/v1/assinatura", tags=["Assinatura"])

# =====================================================================
# CONSTANTES PARA CÁLCULO DE MENSALIDADE PROGRESSIVA
# =====================================================================

PRECOS_CADEIRAS = [
    47.90,  # 1ª cadeira
    37.90,  # 2ª cadeira
    27.90,  # 3ª cadeira
    20.90,  # 4ª cadeira
    17.90   # 5ª cadeira
]

VALOR_MINIMO_APOS_QUINTA = 17.90  # 6ª cadeira em diante (PISO FIXO)


# =====================================================================
# FUNÇÕES DE CÁLCULO
# =====================================================================

def calcular_mensalidade_progressiva(quantidade_cadeiras: int) -> float:
    """
    Calcula mensalidade com preços progressivos (decrescentes) por cadeira.
    
    🔹 Estrutura:
    - 1ª a 5ª cadeira: valores fixos da tabela PRECOS_CADEIRAS
    - 6ª em diante: valor mínimo de R$ 17,90
    
    Args:
        quantidade_cadeiras: Número de cadeiras (mínimo 1)
    
    Returns:
        float: Valor total da mensalidade
    """
    if quantidade_cadeiras < 1:
        return 0.0
    
    total = 0.0
    for i in range(1, quantidade_cadeiras + 1):
        if i <= 5:
            valor_cadeira = PRECOS_CADEIRAS[i - 1]
        else:
            valor_cadeira = VALOR_MINIMO_APOS_QUINTA
        
        # SAFEGUARD: Garante que nunca fica abaixo do mínimo
        valor_cadeira = max(valor_cadeira, VALOR_MINIMO_APOS_QUINTA)
        total += valor_cadeira
    
    return round(total, 2)


def obter_valor_cadeira(posicao: int) -> float:
    """
    Retorna o valor de uma cadeira específica pela sua posição.
    
    Args:
        posicao: Posição da cadeira (1 = primeira, 2 = segunda, etc.)
    
    Returns:
        float: Valor individual da cadeira naquela posição
    """
    if posicao < 1:
        return 0.0
    
    if posicao <= 5:
        return max(PRECOS_CADEIRAS[posicao - 1], VALOR_MINIMO_APOS_QUINTA)
    else:
        return VALOR_MINIMO_APOS_QUINTA


def gerar_breakdown_cadeiras(quantidade: int) -> List[Dict]:
    """
    Gera array com breakdown detalhado de cada cadeira.
    
    Args:
        quantidade: Número total de cadeiras
    
    Returns:
        List[Dict]: Array com posição, valor individual e total acumulado de cada cadeira
    
    Exemplo:
        >>> gerar_breakdown_cadeiras(3)
        [
            {"posicao": 1, "valor_individual": 47.90, "acumulado": 47.90},
            {"posicao": 2, "valor_individual": 37.90, "acumulado": 85.80},
            {"posicao": 3, "valor_individual": 27.90, "acumulado": 113.70}
        ]
    """
    breakdown = []
    acumulado = 0.0
    
    for i in range(1, quantidade + 1):
        valor_individual = obter_valor_cadeira(i)
        acumulado += valor_individual
        breakdown.append({
            "posicao": i,
            "valor_individual": round(valor_individual, 2),
            "acumulado": round(acumulado, 2)
        })
    
    return breakdown


# =====================================================================
# SCHEMAS
# =====================================================================

class CalcularMensalidadeRequest(BaseModel):
    """Request para calcular mensalidade"""
    quantidade_cadeiras: int


class CadeiraMensalidadeInfo(BaseModel):
    """Info de uma cadeira no breakdown"""
    posicao: int
    valor_individual: float
    acumulado: float


class CalcularMensalidadeResponse(BaseModel):
    """Response com cálculo da mensalidade"""
    quantidade_cadeiras: int
    valor_mensal: float
    valor_primeira_cadeira: float
    valor_minimo_apos_quinta: float
    breakdown: List[CadeiraMensalidadeInfo]


class AssinaturaBarbearia(BaseModel):
    """Modelo de assinatura de barbearia"""
    barbearia_id: int
    quantidade_cadeiras: int
    valor_mensal: float
    ativa: bool = True
    criada_em: datetime

    class Config:
        from_attributes = True


# =====================================================================
# ENDPOINTS
# =====================================================================

@router.post("/calcular", response_model=CalcularMensalidadeResponse)
def calcular_mensalidade(
    dados: CalcularMensalidadeRequest
):
    """
    Calcula a mensalidade progressiva para uma quantidade de cadeiras.
    ⚠️ Endpoint PÚBLICO - sem autenticação necessária (apenas cálculo).
    
    Retorna:
    - valor_mensal: Valor total da mensalidade
    - breakdown: Detalhamento cadeira por cadeira
    
    Exemplos:
    ```json
    POST /api/v1/assinatura/calcular
    {
        "quantidade_cadeiras": 3
    }
    
    Response:
    {
        "quantidade_cadeiras": 3,
        "valor_mensal": 113.70,
        "valor_primeira_cadeira": 47.90,
        "valor_minimo_apos_quinta": 17.90,
        "breakdown": [
            {"posicao": 1, "valor_individual": 47.90, "acumulado": 47.90},
            {"posicao": 2, "valor_individual": 37.90, "acumulado": 85.80},
            {"posicao": 3, "valor_individual": 27.90, "acumulado": 113.70}
        ]
    }
    ```
    """
    # Validar entrada
    if dados.quantidade_cadeiras < 1:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Quantidade de cadeiras deve ser no mínimo 1"
        )
    
    if dados.quantidade_cadeiras > 50:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Quantidade de cadeiras não pode exceder 50"
        )
    
    # Calcular
    valor_mensal = calcular_mensalidade_progressiva(dados.quantidade_cadeiras)
    breakdown = gerar_breakdown_cadeiras(dados.quantidade_cadeiras)
    
    return CalcularMensalidadeResponse(
        quantidade_cadeiras=dados.quantidade_cadeiras,
        valor_mensal=valor_mensal,
        valor_primeira_cadeira=PRECOS_CADEIRAS[0],
        valor_minimo_apos_quinta=VALOR_MINIMO_APOS_QUINTA,
        breakdown=breakdown
    )


@router.post("/ativar")
def ativar_assinatura_barbearia(
    barbearia_id: int,
    quantidade_cadeiras: int,
    db: Session = Depends(get_db),
    usuario_atual: Usuario = Depends(get_current_user)
):
    """
    Ativa uma assinatura para uma barbearia.
    Apenas dono/admin da barbearia pode ativar.
    
    Cria ou atualiza registro de Assinatura com:
    - quantidade_cadeiras
    - valor_mensal calculado
    - status ativa
    """
    # Verificar se barbearia existe
    barbearia = db.query(Barbearia).filter(Barbearia.id == barbearia_id).first()
    if not barbearia:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Barbearia {barbearia_id} não encontrada"
        )
    
    # Verificar permissão (dono da barbearia ou admin)
    if barbearia.usuario_id != usuario_atual.id and usuario_atual.tipo != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Apenas o dono da barbearia pode ativar assinatura"
        )
    
    # Validar quantidade
    if quantidade_cadeiras < 1 or quantidade_cadeiras > 50:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Quantidade de cadeiras deve estar entre 1 e 50"
        )
    
    # Calcular valor mensal
    valor_mensal = calcular_mensalidade_progressiva(quantidade_cadeiras)
    
    # Buscar ou criar assinatura
    assinatura = db.query(Assinatura).filter(Assinatura.barbearia_id == barbearia_id).first()
    
    if assinatura:
        # Atualizar existente
        assinatura.quantidade_cadeiras = quantidade_cadeiras
        assinatura.valor_mensal = valor_mensal
        assinatura.ativa = True
        assinatura.atualizada_em = datetime.now()
    else:
        # Criar nova
        assinatura = Assinatura(
            barbearia_id=barbearia_id,
            quantidade_cadeiras=quantidade_cadeiras,
            valor_mensal=valor_mensal,
            ativa=True,
            criada_em=datetime.now()
        )
        db.add(assinatura)
    
    db.commit()
    db.refresh(assinatura)
    
    return {
        "message": "Assinatura ativada com sucesso",
        "barbearia_id": barbearia_id,
        "quantidade_cadeiras": quantidade_cadeiras,
        "valor_mensal": valor_mensal
    }


@router.get("/barbearia/{barbearia_id}")
def obter_assinatura_barbearia(
    barbearia_id: int,
    db: Session = Depends(get_db),
    usuario_atual: Usuario = Depends(get_current_user)
):
    """
    Obtém os detalhes da assinatura de uma barbearia.
    """
    # Verificar se barbearia existe
    barbearia = db.query(Barbearia).filter(Barbearia.id == barbearia_id).first()
    if not barbearia:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Barbearia {barbearia_id} não encontrada"
        )
    
    # Buscar assinatura
    assinatura = db.query(Assinatura).filter(Assinatura.barbearia_id == barbearia_id).first()
    
    if not assinatura:
        return {"message": "Barbearia não possui assinatura ativa"}
    
    # Gerar breakdown
    breakdown = gerar_breakdown_cadeiras(assinatura.quantidade_cadeiras)
    
    return {
        "barbearia_id": barbearia_id,
        "quantidade_cadeiras": assinatura.quantidade_cadeiras,
        "valor_mensal": assinatura.valor_mensal,
        "ativa": assinatura.ativa,
        "criada_em": assinatura.criada_em,
        "breakdown": breakdown
    }


@router.get("/tabela-precos")
def obter_tabela_precos(
    ate_cadeiras: int = 10
):
    """
    Retorna a tabela de preços progressiva completa.
    ⚠️ Endpoint PÚBLICO - sem autenticação necessária.
    Útil para exibir em UI de configuração.
    
    Query params:
    - ate_cadeiras: Até qual quantidade mostrar na tabela (default 10, máx 50)
    """
    if ate_cadeiras < 1 or ate_cadeiras > 50:
        ate_cadeiras = 10
    
    tabela = []
    for i in range(1, ate_cadeiras + 1):
        valor_individual = obter_valor_cadeira(i)
        total_acumulado = calcular_mensalidade_progressiva(i)
        tabela.append({
            "cadeiras": i,
            "valor_individual": round(valor_individual, 2),
            "valor_total_mensal": round(total_acumulado, 2)
        })
    
    return {
        "tabela_precos": tabela,
        "valor_primeira_cadeira": PRECOS_CADEIRAS[0],
        "valor_minimo_apos_quinta": VALOR_MINIMO_APOS_QUINTA
    }
