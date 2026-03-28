# --- ARQUIVO: app/routes_mensalidade.py ---
# Rotas para calcular e gerenciar mensalidades progressivas das barbearias

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Dict

from .database import get_db
from .models import Usuario, Cadeira
from .routes import get_current_user, oauth2_scheme

router = APIRouter(prefix="/api/v1/mensalidade", tags=["Mensalidade"])

# ============ SCHEMAS ============
class MensalidadeCalculoResponse(BaseModel):
    quantidade_cadeiras: int
    detalhamento: List[Dict]  # Lista com preço de cada cadeira
    total_mensal: float
    economia_total: float  # Comparado se todas fossem R$47,90

class MensalidadeStatusResponse(BaseModel):
    quantidade_cadeiras: int
    total_mensal: float
    proxima_cadeira_preco: float
    economias_projetos: Dict  # Economia ao adicionar próximas cadeiras

# ============ CONSTANTES ============
PRECOS_FIXOS = {
    1: 47.90,
    2: 37.90,
    3: 27.90,
    4: 20.90,
    5: 17.90
}

VALOR_MINIMO = 17.90

# ============ FUNÇÕES DE CÁLCULO ============

def calcular_preco_cadeira(numero_cadeira: int) -> float:
    """
    Retorna o preço de uma cadeira específica
    
    Args:
        numero_cadeira: Número da cadeira (1-indexed)
    
    Returns:
        float: Preço da cadeira
    """
    if numero_cadeira <= 0:
        raise ValueError("Número de cadeira deve ser >= 1")
    
    if numero_cadeira in PRECOS_FIXOS:
        return PRECOS_FIXOS[numero_cadeira]
    else:
        return VALOR_MINIMO


def calcular_mensalidade_total(quantidade_cadeiras: int) -> tuple:
    """
    Calcula a mensalidade total para uma quantidade de cadeiras
    
    Args:
        quantidade_cadeiras: Quantidade de cadeiras
    
    Returns:
        tuple: (total, detalhamento, economia_total)
    """
    if quantidade_cadeiras <= 0:
        raise ValueError("Quantidade de cadeiras deve ser >= 1")
    
    total = 0
    detalhamento = []
    
    for i in range(1, quantidade_cadeiras + 1):
        preco = calcular_preco_cadeira(i)
        total += preco
        detalhamento.append({
            "cadeira": i,
            "preco": preco
        })
    
    # Economia: se todas as cadeiras fossem R$47,90
    valor_sem_desconto = quantidade_cadeiras * 47.90
    economia = valor_sem_desconto - total
    
    return total, detalhamento, economia


# ============ ENDPOINTS ============

@router.get("/calcular")
def calcular_mensalidade(
    quantidade_cadeiras: int,
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
):
    """
    Calcula a mensalidade para um número específico de cadeiras
    """
    user = get_current_user(token=token, db=db)
    
    if quantidade_cadeiras < 1:
        raise HTTPException(status_code=400, detail="Quantidade de cadeiras deve ser >= 1")
    
    try:
        total, detalhamento, economia = calcular_mensalidade_total(quantidade_cadeiras)
        
        return MensalidadeCalculoResponse(
            quantidade_cadeiras=quantidade_cadeiras,
            detalhamento=detalhamento,
            total_mensal=round(total, 2),
            economia_total=round(economia, 2)
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/barbearia/{barbearia_id}")
def get_mensalidade_barbearia(
    barbearia_id: int,
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
):
    """
    Retorna a mensalidade atual de uma barbearia baseado no número de cadeiras
    """
    user = get_current_user(token=token, db=db)
    
    # Verificar se o usuário é a barbearia ou admin
    if user.tipo != "barbearia" and user.id != barbearia_id:
        raise HTTPException(status_code=403, detail="Você não tem acesso a essa barbearia")
    
    # Contar cadeiras ativas da barbearia
    quantidade_cadeiras = db.query(Cadeira).filter(
        Cadeira.barbearia_id == barbearia_id,
        Cadeira.status != "inativa"
    ).count()
    
    if quantidade_cadeiras == 0:
        quantidade_cadeiras = 1  # Mínimo 1 cadeira
    
    try:
        total, _, economia = calcular_mensalidade_total(quantidade_cadeiras)
        
        # Calcular preço da próxima cadeira
        proxima_cadeira_numero = quantidade_cadeiras + 1
        proxima_cadeira_preco = calcular_preco_cadeira(proxima_cadeira_numero)
        
        # Projetar economias ao adicionar próximas cadeiras
        economias_projetos = {}
        for i in range(1, 6):  # Próximas 5 cadeiras
            futura_qtd = quantidade_cadeiras + i
            futura_total, _, futura_economia = calcular_mensalidade_total(futura_qtd)
            incremento_custo = futura_total - total
            economias_projetos[f"+{i}_cadeira(s)"] = {
                "new_total": round(futura_total, 2),
                "incremento_custo": round(incremento_custo, 2),
                "economia_acumulada": round(futura_economia, 2)
            }
        
        return MensalidadeStatusResponse(
            quantidade_cadeiras=quantidade_cadeiras,
            total_mensal=round(total, 2),
            proxima_cadeira_preco=proxima_cadeira_preco,
            economias_projetos=economias_projetos
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/tabela")
def get_tabela_precos(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
):
    """
    Retorna a tabela completa de preços e valores totais
    """
    user = get_current_user(token=token, db=db)
    
    tabela = []
    for qtd in range(1, 11):
        total, detalhamento, economia = calcular_mensalidade_total(qtd)
        tabela.append({
            "quantidade_cadeiras": qtd,
            "total_mensal": round(total, 2),
            "economia_vs_uniforme": round(economia, 2)
        })
    
    return {
        "tabela": tabela,
        "valor_primeira_cadeira": 47.90,
        "valor_minimo_piso": 17.90,
        "notas": "A partir da 6ª cadeira, o valor piso de R$17,90 é aplicado"
    }


@router.get("/simulador")
def simulador_mensalidade(
    quantidade_cadeiras_atual: int,
    quantidade_cadeiras_nova: int,
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
):
    """
    Simula o custo ao expandir de X para Y cadeiras
    """
    user = get_current_user(token=token, db=db)
    
    if quantidade_cadeiras_atual < 1 or quantidade_cadeiras_nova < 1:
        raise HTTPException(status_code=400, detail="Quantidades devem ser >= 1")
    
    if quantidade_cadeiras_nova <= quantidade_cadeiras_atual:
        raise HTTPException(status_code=400, detail="Nova quantidade deve ser maior que a atual")
    
    try:
        atual_total, _, _ = calcular_mensalidade_total(quantidade_cadeiras_atual)
        nova_total, novo_detalhamento, nova_economia = calcular_mensalidade_total(quantidade_cadeiras_nova)
        
        incremento = nova_total - atual_total
        alteracao_percentual = (incremento / atual_total * 100) if atual_total > 0 else 0
        
        return {
            "status_atual": {
                "quantidade_cadeiras": quantidade_cadeiras_atual,
                "total_mensal": round(atual_total, 2)
            },
            "status_novo": {
                "quantidade_cadeiras": quantidade_cadeiras_nova,
                "total_mensal": round(nova_total, 2),
                "detalhamento": novo_detalhamento,
                "economia_total": round(nova_economia, 2)
            },
            "impacto_financeiro": {
                "incremento_mensal": round(incremento, 2),
                "alteracao_percentual": round(alteracao_percentual, 2),
                "incremento_anual": round(incremento * 12, 2)
            }
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
