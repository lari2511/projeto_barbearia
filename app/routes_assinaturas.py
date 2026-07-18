"""
Rotas de gerenciamento de assinaturas das barbearias
Sistema de cobrança por cadeira com desconto progressivo
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from typing import Optional, List
from pydantic import BaseModel
import calendar
import json
import qrcode
import io
import base64

from app.database import get_db
from app import models
from app.routes import get_current_user, oauth2_scheme

router = APIRouter(prefix="/assinaturas", tags=["Assinaturas"])

PRECO_CADEIRA_CHEIO = 47.90
PRECOS_PROGRESSIVOS_INICIAIS = [47.90, 37.90, 27.90, 20.90, 17.90]
PRECO_PROGRESSIVO_MINIMO = 17.90


class AssinaturaCreate(BaseModel):
    cadeiras_ativas: int
    metodo_pagamento: Optional[str] = "pix"


class AssinaturaResponse(BaseModel):
    id: int
    barbearia_id: int
    cadeiras_ativas: int
    valor_mensal: float
    status: str
    proximo_vencimento: datetime
    metodo_pagamento: Optional[str] = None
    
    class Config:
        from_attributes = True


class CadeiraContratadaItemResponse(BaseModel):
    cadeira_contratada_id: int
    numero_referencia: int
    origem: str
    valor_individual: float
    data_contratacao: datetime
    data_proxima_cobranca: datetime
    ativa: bool


class PainelCadeirasResponse(BaseModel):
    barbearia_id: int
    total_cadeiras_ativas: int
    valor_total_mensal: float
    cadeiras: List[CadeiraContratadaItemResponse]


class AssinaturaRenovar(BaseModel):
    metodo_pagamento: Optional[str] = None
    confirmar_pix: Optional[bool] = False
    numero_cartao: Optional[str] = None
    titular: Optional[str] = None
    validade: Optional[str] = None
    cvv: Optional[str] = None


class AssinaturaPixResponse(BaseModel):
    qrcode_base64: str
    pix_copia_cola: str
    valor: float
    vencimento_referencia: datetime


def normalizar_metodo_pagamento(metodo: Optional[str]) -> str:
    metodo_normalizado = (metodo or "pix").strip().lower()
    permitidos = {"pix", "cartao", "cartao_credito", "cartao_debito", "dinheiro"}
    if metodo_normalizado not in permitidos:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Metodo de pagamento invalido. Use: pix, cartao, cartao_credito, cartao_debito ou dinheiro"
        )
    return metodo_normalizado


def calcular_proxima_cobranca_individual(data_base: datetime, dia_preferido: Optional[int] = None) -> datetime:
    """Calcula a próxima cobrança no mesmo dia do mês seguinte (com ajuste de mês curto)."""
    dia = dia_preferido or data_base.day
    return _proximo_vencimento_mensal(data_base, dia)


def _preco_progressivo_por_posicao(posicao: int) -> float:
    if posicao <= 0:
        raise ValueError("Posição da cadeira deve ser maior que zero")

    if posicao <= len(PRECOS_PROGRESSIVOS_INICIAIS):
        return PRECOS_PROGRESSIVOS_INICIAIS[posicao - 1]

    return PRECO_PROGRESSIVO_MINIMO


def calcular_precos_compra_inicial(quantidade: int) -> List[float]:
    if quantidade <= 0:
        return []
    return [round(_preco_progressivo_por_posicao(i), 2) for i in range(1, quantidade + 1)]


def calcular_precos_cadeiras_adicionais(quantidade: int) -> List[float]:
    if quantidade <= 0:
        return []
    return [round(PRECO_CADEIRA_CHEIO, 2) for _ in range(quantidade)]


def _serializar_cadeira_contratada(cadeira: models.CadeiraContratada) -> dict:
    origem = "Compra Inicial" if cadeira.origem_contratacao == models.OrigemContratacaoCadeira.COMPRA_INICIAL.value else "Adicional"
    return {
        "cadeira_contratada_id": cadeira.id,
        "numero_referencia": cadeira.numero_referencia,
        "origem": origem,
        "valor_individual": round(float(cadeira.valor_mensal or 0), 2),
        "data_contratacao": cadeira.data_contratacao,
        "data_proxima_cobranca": cadeira.data_proxima_cobranca,
        "ativa": bool(cadeira.ativa),
    }


def _barbearia_tem_historico_contratacao(db: Session, barbearia_id: int) -> bool:
    total_historico = db.query(models.CadeiraContratada).filter(
        models.CadeiraContratada.barbearia_id == barbearia_id
    ).count()

    if total_historico > 0:
        return True

    assinatura_existente = db.query(models.AssinaturaBarbearia).filter(
        models.AssinaturaBarbearia.barbearia_id == barbearia_id
    ).first()

    return bool(assinatura_existente and (assinatura_existente.quantidade_cadeiras or 0) > 0)


def _proximo_numero_referencia(db: Session, barbearia_id: int) -> int:
    ultimo = db.query(models.CadeiraContratada).filter(
        models.CadeiraContratada.barbearia_id == barbearia_id
    ).order_by(models.CadeiraContratada.numero_referencia.desc()).first()

    return (ultimo.numero_referencia + 1) if ultimo else 1


def _resumo_ativo_cadeiras(db: Session, assinatura_id: int) -> List[models.CadeiraContratada]:
    return db.query(models.CadeiraContratada).filter(
        models.CadeiraContratada.assinatura_id == assinatura_id,
        models.CadeiraContratada.ativa.is_(True),
    ).order_by(models.CadeiraContratada.numero_referencia.asc()).all()


def _sincronizar_totais_assinatura(
    assinatura: models.AssinaturaBarbearia,
    cadeiras_ativas: List[models.CadeiraContratada],
    referencia: datetime,
):
    breakdown = [round(float(c.valor_mensal or 0), 2) for c in cadeiras_ativas]
    total = round(sum(breakdown), 2)
    economia = round((len(breakdown) * PRECO_CADEIRA_CHEIO) - total, 2) if breakdown else 0.0

    assinatura.quantidade_cadeiras = len(cadeiras_ativas)
    assinatura.valor_mensalidade = total
    assinatura.valor_por_cadeira = json.dumps(breakdown)
    assinatura.economia_mensal = economia
    assinatura.ultima_atualizacao = referencia

    if cadeiras_ativas:
        assinatura.dia_vencimento = cadeiras_ativas[0].data_contratacao.day
        assinatura.proximo_vencimento = min(cadeiras_ativas, key=lambda c: c.data_proxima_cobranca).data_proxima_cobranca
    else:
        assinatura.proximo_vencimento = referencia + timedelta(days=30)


def _registrar_cadeiras(
    db: Session,
    assinatura: models.AssinaturaBarbearia,
    quantidade: int,
    origem: str,
    precos: List[float],
    data_contratacao: datetime,
):
    numero_ref = _proximo_numero_referencia(db, assinatura.barbearia_id)
    for i in range(quantidade):
        data_proxima = calcular_proxima_cobranca_individual(data_contratacao)
        db.add(models.CadeiraContratada(
            assinatura_id=assinatura.id,
            barbearia_id=assinatura.barbearia_id,
            numero_referencia=numero_ref + i,
            origem_contratacao=origem,
            valor_mensal=precos[i],
            data_contratacao=data_contratacao,
            data_proxima_cobranca=data_proxima,
            ativa=True,
        ))


def _avancar_ciclo_cobranca_cadeiras(
    cadeiras_ativas: List[models.CadeiraContratada],
    referencia: datetime,
    apenas_vencidas: bool = False,
) -> int:
    """Avança a próxima cobrança de cada cadeira em um mês de calendário."""
    atualizadas = 0
    for cadeira in cadeiras_ativas:
        if apenas_vencidas and cadeira.data_proxima_cobranca > referencia:
            continue

        base = cadeira.data_proxima_cobranca or cadeira.data_contratacao or referencia
        cadeira.data_proxima_cobranca = calcular_proxima_cobranca_individual(base, cadeira.data_contratacao.day)
        atualizadas += 1

    return atualizadas


def serializar_assinatura(assinatura: models.AssinaturaBarbearia) -> dict:
    return {
        "id": assinatura.id,
        "barbearia_id": assinatura.barbearia_id,
        "cadeiras_ativas": assinatura.quantidade_cadeiras,
        "valor_mensal": assinatura.valor_mensalidade,
        "status": assinatura.status,
        "proximo_vencimento": assinatura.proximo_vencimento,
        "metodo_pagamento": assinatura.metodo_pagamento_preferido or "pix"
    }


def _proximo_vencimento_mensal(base: datetime, dia_preferido: int) -> datetime:
    """Calcula o próximo vencimento avançando 1 mês de calendário.

    Mantém o dia preferido quando possível (ex.: 10 de cada mês) e ajusta
    automaticamente para o último dia em meses mais curtos.
    """
    ano = base.year
    mes = base.month + 1
    if mes > 12:
        mes = 1
        ano += 1

    ultimo_dia_mes = calendar.monthrange(ano, mes)[1]
    dia = min(max(dia_preferido, 1), ultimo_dia_mes)

    return base.replace(year=ano, month=mes, day=dia)


def _calcular_novo_vencimento_assinatura(assinatura: models.AssinaturaBarbearia, referencia: datetime) -> datetime:
    """Define o novo vencimento mensal com base no ciclo atual da assinatura."""
    dia_vencimento = assinatura.dia_vencimento or referencia.day
    # Regra retroativa: cada pagamento avanca exatamente 1 ciclo mensal a partir
    # do ultimo vencimento conhecido. Se nao houver vencimento anterior, usa agora.
    base = assinatura.proximo_vencimento or referencia
    return _proximo_vencimento_mensal(base, dia_vencimento)


def _normalizar_vencimento_adiantado(assinatura: models.AssinaturaBarbearia, referencia: datetime) -> bool:
    """Evita assinaturas com vencimento muito à frente por confirmações repetidas.

    Em plano mensal, o limite saudável é no máximo o próximo ciclo mensal.
    Retorna True quando houve ajuste.
    """
    dia_vencimento = assinatura.dia_vencimento or referencia.day
    limite = _proximo_vencimento_mensal(referencia, dia_vencimento)
    if assinatura.proximo_vencimento and assinatura.proximo_vencimento > limite:
        assinatura.proximo_vencimento = limite
        assinatura.ultima_atualizacao = referencia
        return True
    return False


def calcular_valor_assinatura(num_cadeiras: int):
    """
    Calcula o valor total da assinatura baseado na tabela progressiva
    
    Tabela de preços:
    - 1ª cadeira: R$ 47,90
    - 2ª cadeira: R$ 37,90
    - 3ª cadeira: R$ 27,90
    - 4ª cadeira: R$ 20,90
    - 5ª cadeira: R$ 17,90
    - 6ª em diante: R$ 17,90 (piso mínimo)
    """
    breakdown = calcular_precos_compra_inicial(num_cadeiras)
    total = sum(breakdown)
    
    # Calcular economia (comparando com o preço da 1ª cadeira)
    preco_sem_desconto = num_cadeiras * PRECO_CADEIRA_CHEIO
    economia = preco_sem_desconto - total if num_cadeiras > 1 else 0
    
    return {
        "valor_total": round(total, 2),
        "breakdown": breakdown,
        "economia": round(economia, 2)
    }


@router.get("/minha", response_model=AssinaturaResponse)
def obter_minha_assinatura(
    db: Session = Depends(get_db),
    usuario_atual = Depends(get_current_user)
):
    """Retorna a assinatura da barbearia do usuário logado"""
    if usuario_atual.tipo != "barbearia":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Apenas donos de barbearia podem acessar assinaturas"
        )
    
    # Buscar a barbearia do usuário
    barbearia = db.query(models.Barbearia).filter(
        models.Barbearia.usuario_id == usuario_atual.id
    ).first()
    
    if not barbearia:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Barbearia não encontrada"
        )
    
    # Buscar assinatura
    assinatura = db.query(models.AssinaturaBarbearia).filter(
        models.AssinaturaBarbearia.barbearia_id == barbearia.id
    ).first()
    
    if not assinatura:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Nenhuma assinatura encontrada. Contrate uma assinatura para começar."
        )
    
    return serializar_assinatura(assinatura)


@router.post("/contratar", response_model=AssinaturaResponse)
def contratar_ou_atualizar_assinatura(
    dados: AssinaturaCreate,
    db: Session = Depends(get_db),
    usuario_atual = Depends(get_current_user)
):
    """
    Contrata ou atualiza a assinatura da barbearia
    Calcula automaticamente o valor baseado no número de cadeiras
    """
    if usuario_atual.tipo != "barbearia":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Apenas donos de barbearia podem contratar assinaturas"
        )
    
    # Validar número de cadeiras
    if dados.cadeiras_ativas < 1 or dados.cadeiras_ativas > 20:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Número de cadeiras deve estar entre 1 e 20"
        )

    metodo_pagamento = normalizar_metodo_pagamento(dados.metodo_pagamento)
    
    # Buscar a barbearia do usuário
    barbearia = db.query(models.Barbearia).filter(
        models.Barbearia.usuario_id == usuario_atual.id
    ).first()
    
    if not barbearia:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Barbearia não encontrada"
        )
    
    # Verificar se já tem assinatura
    assinatura = db.query(models.AssinaturaBarbearia).filter(
        models.AssinaturaBarbearia.barbearia_id == barbearia.id
    ).first()

    agora = datetime.now()

    if assinatura:
        cadeiras_ativas = _resumo_ativo_cadeiras(db, assinatura.id)
        quantidade_atual = len(cadeiras_ativas)

        if quantidade_atual == 0 and (assinatura.quantidade_cadeiras or 0) > 0:
            # Migração compatível: assinaturas antigas sem histórico de cadeira.
            precos_legado = calcular_precos_cadeiras_adicionais(assinatura.quantidade_cadeiras)
            _registrar_cadeiras(
                db=db,
                assinatura=assinatura,
                quantidade=assinatura.quantidade_cadeiras,
                origem=models.OrigemContratacaoCadeira.ADICIONAL.value,
                precos=precos_legado,
                data_contratacao=assinatura.criado_em or agora,
            )
            db.flush()
            cadeiras_ativas = _resumo_ativo_cadeiras(db, assinatura.id)
            quantidade_atual = len(cadeiras_ativas)

        if dados.cadeiras_ativas > quantidade_atual:
            quantidade_novas = dados.cadeiras_ativas - quantidade_atual
            precos_novas = calcular_precos_cadeiras_adicionais(quantidade_novas)
            _registrar_cadeiras(
                db=db,
                assinatura=assinatura,
                quantidade=quantidade_novas,
                origem=models.OrigemContratacaoCadeira.ADICIONAL.value,
                precos=precos_novas,
                data_contratacao=agora,
            )

        if dados.cadeiras_ativas < quantidade_atual:
            quantidade_retirar = quantidade_atual - dados.cadeiras_ativas
            cadeiras_para_desativar = db.query(models.CadeiraContratada).filter(
                models.CadeiraContratada.assinatura_id == assinatura.id,
                models.CadeiraContratada.ativa.is_(True),
            ).order_by(models.CadeiraContratada.numero_referencia.desc()).limit(quantidade_retirar).all()

            for cadeira in cadeiras_para_desativar:
                cadeira.ativa = False
                cadeira.cancelada_em = agora

        cadeiras_ativas = _resumo_ativo_cadeiras(db, assinatura.id)
        _sincronizar_totais_assinatura(assinatura, cadeiras_ativas, agora)
        assinatura.metodo_pagamento_preferido = metodo_pagamento

        # Se estava suspensa/cancelada, reativar
        if assinatura.status in ["suspensa", "cancelada", "inadimplente"]:
            assinatura.status = "ativa"
            assinatura.motivo_suspensao = None

        db.commit()
        db.refresh(assinatura)

        return serializar_assinatura(assinatura)
    else:
        primeira_compra = not _barbearia_tem_historico_contratacao(db, barbearia.id)
        precos = (
            calcular_precos_compra_inicial(dados.cadeiras_ativas)
            if primeira_compra else
            calcular_precos_cadeiras_adicionais(dados.cadeiras_ativas)
        )

        nova_assinatura = models.AssinaturaBarbearia(
            barbearia_id=barbearia.id,
            quantidade_cadeiras=0,
            valor_mensalidade=0,
            valor_por_cadeira=json.dumps([]),
            economia_mensal=0,
            metodo_pagamento_preferido=metodo_pagamento,
            dia_vencimento=agora.day,
            proximo_vencimento=calcular_proxima_cobranca_individual(agora),
            status="ativa"
        )

        db.add(nova_assinatura)
        db.flush()

        _registrar_cadeiras(
            db=db,
            assinatura=nova_assinatura,
            quantidade=dados.cadeiras_ativas,
            origem=(
                models.OrigemContratacaoCadeira.COMPRA_INICIAL.value
                if primeira_compra
                else models.OrigemContratacaoCadeira.ADICIONAL.value
            ),
            precos=precos,
            data_contratacao=agora,
        )

        cadeiras_ativas = _resumo_ativo_cadeiras(db, nova_assinatura.id)
        _sincronizar_totais_assinatura(nova_assinatura, cadeiras_ativas, agora)

        db.commit()
        db.refresh(nova_assinatura)

        return serializar_assinatura(nova_assinatura)


@router.get("/minha-assinatura", response_model=AssinaturaResponse)
def obter_minha_assinatura_alias(
    db: Session = Depends(get_db),
    usuario_atual = Depends(get_current_user)
):
    """Alias para compatibilidade com o frontend novo."""
    return obter_minha_assinatura(db=db, usuario_atual=usuario_atual)


@router.get("/painel-cadeiras", response_model=PainelCadeirasResponse)
def obter_painel_cadeiras(
    db: Session = Depends(get_db),
    usuario_atual = Depends(get_current_user)
):
    """Retorna o detalhamento das cadeiras contratadas para o painel da barbearia."""
    if usuario_atual.tipo != "barbearia":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Apenas donos de barbearia podem acessar o painel de cadeiras"
        )

    barbearia = db.query(models.Barbearia).filter(
        models.Barbearia.usuario_id == usuario_atual.id
    ).first()

    if not barbearia:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Barbearia não encontrada"
        )

    assinatura = db.query(models.AssinaturaBarbearia).filter(
        models.AssinaturaBarbearia.barbearia_id == barbearia.id
    ).first()

    if not assinatura:
        return {
            "barbearia_id": barbearia.id,
            "total_cadeiras_ativas": 0,
            "valor_total_mensal": 0.0,
            "cadeiras": [],
        }

    cadeiras_ativas = _resumo_ativo_cadeiras(db, assinatura.id)
    _sincronizar_totais_assinatura(assinatura, cadeiras_ativas, datetime.now())
    db.commit()
    db.refresh(assinatura)

    return {
        "barbearia_id": barbearia.id,
        "total_cadeiras_ativas": len(cadeiras_ativas),
        "valor_total_mensal": round(assinatura.valor_mensalidade or 0, 2),
        "cadeiras": [_serializar_cadeira_contratada(c) for c in cadeiras_ativas],
    }


@router.post("/criar", response_model=AssinaturaResponse)
def criar_assinatura_alias(
    dados: AssinaturaCreate,
    db: Session = Depends(get_db),
    usuario_atual = Depends(get_current_user)
):
    """Alias para compatibilidade com o frontend novo."""
    return contratar_ou_atualizar_assinatura(dados=dados, db=db, usuario_atual=usuario_atual)


@router.post("/renovar", response_model=AssinaturaResponse)
def renovar_assinatura(
    dados: AssinaturaRenovar = AssinaturaRenovar(),
    db: Session = Depends(get_db),
    usuario_atual = Depends(get_current_user)
):
    """Renova assinatura por mais 30 dias, mantendo/atualizando metodo de pagamento."""
    if usuario_atual.tipo != "barbearia":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Apenas donos de barbearia podem renovar assinaturas"
        )

    barbearia = db.query(models.Barbearia).filter(
        models.Barbearia.usuario_id == usuario_atual.id
    ).first()

    if not barbearia:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Barbearia não encontrada"
        )

    assinatura = db.query(models.AssinaturaBarbearia).filter(
        models.AssinaturaBarbearia.barbearia_id == barbearia.id
    ).first()

    if not assinatura:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Nenhuma assinatura encontrada para renovar"
        )

    agora = datetime.now()
    cadeiras_ativas = _resumo_ativo_cadeiras(db, assinatura.id)
    if cadeiras_ativas:
        _avancar_ciclo_cobranca_cadeiras(cadeiras_ativas, agora)
        _sincronizar_totais_assinatura(assinatura, cadeiras_ativas, agora)
    else:
        assinatura.proximo_vencimento = _calcular_novo_vencimento_assinatura(assinatura, agora)

    assinatura.status = "ativa"
    assinatura.motivo_suspensao = None
    assinatura.ultima_atualizacao = agora

    if dados.metodo_pagamento:
        assinatura.metodo_pagamento_preferido = normalizar_metodo_pagamento(dados.metodo_pagamento)

    db.commit()
    db.refresh(assinatura)
    return serializar_assinatura(assinatura)


@router.post("/cancelar")
def cancelar_assinatura(
    db: Session = Depends(get_db),
    usuario_atual = Depends(get_current_user)
):
    """Cancela a assinatura da barbearia"""
    if usuario_atual.tipo != "barbearia":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Apenas donos de barbearia podem cancelar assinaturas"
        )
    
    # Buscar a barbearia do usuário
    barbearia = db.query(models.Barbearia).filter(
        models.Barbearia.usuario_id == usuario_atual.id
    ).first()
    
    if not barbearia:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Barbearia não encontrada"
        )
    
    # Buscar assinatura
    assinatura = db.query(models.AssinaturaBarbearia).filter(
        models.AssinaturaBarbearia.barbearia_id == barbearia.id
    ).first()
    
    if not assinatura:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Nenhuma assinatura encontrada"
        )
    
    # Marcar como cancelada
    assinatura.status = "cancelada"
    assinatura.cancelado_em = datetime.now()
    assinatura.motivo_suspensao = "Cancelamento solicitado pelo usuário"
    
    db.commit()
    
    return {
        "success": True,
        "message": "Assinatura cancelada com sucesso"
    }


@router.get("/calcular")
def simular_preco(cadeiras: int = 1):
    """
    Endpoint público para simular o preço antes de contratar
    Útil para a tela de assinatura mostrar valores em tempo real
    """
    if cadeiras < 1 or cadeiras > 20:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Número de cadeiras deve estar entre 1 e 20"
        )
    
    return calcular_valor_assinatura(cadeiras)


@router.get("/verificar-limite-cadeiras")
def verificar_limite_cadeiras(
    db: Session = Depends(get_db),
    usuario_atual = Depends(get_current_user)
):
    """
    Verifica quantas cadeiras a barbearia pode ter baseado na assinatura
    e quantas estão atualmente ocupadas
    """
    if usuario_atual.tipo != "barbearia":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Apenas donos de barbearia podem verificar limites"
        )
    
    # Buscar a barbearia do usuário
    barbearia = db.query(models.Barbearia).filter(
        models.Barbearia.usuario_id == usuario_atual.id
    ).first()
    
    if not barbearia:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Barbearia não encontrada"
        )
    
    # Buscar assinatura
    assinatura = db.query(models.AssinaturaBarbearia).filter(
        models.AssinaturaBarbearia.barbearia_id == barbearia.id
    ).first()
    
    cadeiras_contratadas = assinatura.quantidade_cadeiras if assinatura else 0
    
    # Contar cadeiras ocupadas
    cadeiras_ocupadas = db.query(models.Cadeira).filter(
        models.Cadeira.barbearia_id == barbearia.id,
        models.Cadeira.status == models.StatusCadeira.OCUPADA
    ).count()
    
    # Contar total de cadeiras cadastradas
    total_cadastradas = db.query(models.Cadeira).filter(
        models.Cadeira.barbearia_id == barbearia.id
    ).count()
    
    return {
        "cadeiras_contratadas": cadeiras_contratadas,
        "cadeiras_ocupadas": cadeiras_ocupadas,
        "cadeiras_disponiveis": max(0, cadeiras_contratadas - cadeiras_ocupadas),
        "total_cadastradas": total_cadastradas,
        "pode_adicionar": cadeiras_ocupadas < cadeiras_contratadas,
        "status_assinatura": assinatura.status if assinatura else "sem_assinatura"
    }


@router.post("/pagar-mensalidade")
def pagar_mensalidade(
    dados: AssinaturaRenovar,
    db: Session = Depends(get_db),
    usuario_atual = Depends(get_current_user)
):
    """
    Registra pagamento da mensalidade e desbloqueia a barbearia automaticamente.
    
    Este endpoint:
    1. Renova a assinatura por 30 dias
    2. Desbloqueia a barbearia se estava bloqueada
    3. Atualiza status para ativa
    4. Registra o método de pagamento usado
    """
    if usuario_atual.tipo != "barbearia":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Apenas donos de barbearia podem pagar mensalidades"
        )

    # Buscar barbearia
    barbearia = db.query(models.Barbearia).filter(
        models.Barbearia.usuario_id == usuario_atual.id
    ).first()

    if not barbearia:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Barbearia não encontrada"
        )

    # Buscar assinatura
    assinatura = db.query(models.AssinaturaBarbearia).filter(
        models.AssinaturaBarbearia.barbearia_id == barbearia.id
    ).first()

    if not assinatura:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Nenhuma assinatura encontrada. Contrate uma assinatura primeiro."
        )

    metodo_pagamento = normalizar_metodo_pagamento(dados.metodo_pagamento)
    hoje = datetime.now()

    # Auto-correção para casos legados de vencimento adiantado em excesso.
    _normalizar_vencimento_adiantado(assinatura, hoje)

    vencimento_referencia = assinatura.proximo_vencimento or datetime.now()
    cadeiras_ativas = _resumo_ativo_cadeiras(db, assinatura.id)

    # Exigir confirmacao explicita do PIX para evitar pagamento "automatico" sem etapa de QR
    if metodo_pagamento == "pix" and not dados.confirmar_pix:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Para PIX, gere o QR Code em /assinaturas/pagar-mensalidade/pix e envie confirmar_pix=true para concluir"
        )

    # Validar dados de cartao antes de confirmar pagamento da mensalidade
    if metodo_pagamento in {"cartao", "cartao_credito", "cartao_debito"}:
        if not all([dados.numero_cartao, dados.titular, dados.validade, dados.cvv]):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Para cartao, informe numero_cartao, titular, validade e cvv"
            )

        numero_limpo = "".join(ch for ch in dados.numero_cartao if ch.isdigit())
        cvv_limpo = "".join(ch for ch in dados.cvv if ch.isdigit())
        if len(numero_limpo) < 13 or len(numero_limpo) > 19:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Numero do cartao invalido"
            )
        if len(cvv_limpo) not in {3, 4}:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="CVV invalido"
            )

    # Avança somente cadeiras vencidas para respeitar ciclos individuais.
    atualizadas = _avancar_ciclo_cobranca_cadeiras(cadeiras_ativas, hoje, apenas_vencidas=True)
    if atualizadas == 0 and cadeiras_ativas:
        # Segurança operacional: se nenhuma venceu, ainda assim permite antecipar 1 ciclo.
        _avancar_ciclo_cobranca_cadeiras(cadeiras_ativas, hoje, apenas_vencidas=False)

    _sincronizar_totais_assinatura(assinatura, cadeiras_ativas, hoje)
    novo_vencimento = assinatura.proximo_vencimento

    # Atualizar assinatura
    assinatura.status = "ativa"
    assinatura.motivo_suspensao = None
    assinatura.ultima_atualizacao = hoje

    assinatura.metodo_pagamento_preferido = metodo_pagamento

    # DESBLOQUEAR BARBEARIA AUTOMATICAMENTE
    if barbearia.bloqueada:
        barbearia.bloqueada = False
        barbearia.motivo_bloqueio = None
        barbearia.bloqueada_em = None

    # Criar registro de fatura paga
    fatura = models.FaturaAssinatura(
        assinatura_id=assinatura.id,
        mes_referencia=hoje.strftime("%Y-%m"),
        data_inicio_periodo=vencimento_referencia,
        data_fim_periodo=novo_vencimento,
        valor_fatura=assinatura.valor_mensalidade,
        quantidade_cadeiras=assinatura.quantidade_cadeiras,
        descricao_cobrada=f"Mensalidade {assinatura.quantidade_cadeiras} cadeira(s)",
        status="pago",
        data_vencimento=vencimento_referencia,
        data_pagamento=hoje,
        metodo_pagamento=assinatura.metodo_pagamento_preferido or "pix"
    )
    db.add(fatura)

    db.commit()
    db.refresh(assinatura)
    db.refresh(barbearia)

    return {
        "success": True,
        "message": "Pagamento confirmado! Barbearia desbloqueada com sucesso.",
        "assinatura": serializar_assinatura(assinatura),
        "desbloqueada": not barbearia.bloqueada,
        "proximo_vencimento": novo_vencimento.isoformat()
    }


@router.post("/pagar-mensalidade/pix", response_model=AssinaturaPixResponse)
def gerar_pix_mensalidade(
    db: Session = Depends(get_db),
    usuario_atual = Depends(get_current_user)
):
    """Gera QR Code PIX para pagamento da mensalidade da barbearia."""
    if usuario_atual.tipo != "barbearia":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Apenas donos de barbearia podem gerar PIX da mensalidade"
        )

    barbearia = db.query(models.Barbearia).filter(
        models.Barbearia.usuario_id == usuario_atual.id
    ).first()
    if not barbearia:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Barbearia nao encontrada"
        )

    assinatura = db.query(models.AssinaturaBarbearia).filter(
        models.AssinaturaBarbearia.barbearia_id == barbearia.id
    ).first()
    if not assinatura:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Nenhuma assinatura encontrada"
        )

    valor = assinatura.valor_mensalidade
    identificador = f"BARBEARMOVE-{barbearia.id}-{datetime.now().strftime('%Y%m%d%H%M%S')}"
    pix_payload = (
        f"00020126360014BR.GOV.BCB.PIX0114+5511999999999"
        f"5204000053039865406{valor:.2f}5802BR"
        f"5913BARBERMOVE6009SAO PAULO"
        f"62190515{identificador[:15]}6304"
    )

    qr = qrcode.QRCode(version=1, box_size=10, border=5)
    qr.add_data(pix_payload)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")

    return AssinaturaPixResponse(
        qrcode_base64=base64.b64encode(buffer.getvalue()).decode(),
        pix_copia_cola=pix_payload,
        valor=valor,
        vencimento_referencia=assinatura.proximo_vencimento or datetime.now()
    )


@router.get("/status")
def verificar_status_assinatura(
    db: Session = Depends(get_db),
    usuario_atual = Depends(get_current_user)
):
    """
    Verifica o status atual da assinatura e se a barbearia está bloqueada.
    
    Retorna informações completas sobre:
    - Status da assinatura (ativa, inadimplente, vencida)
    - Se a barbearia está bloqueada
    - Motivo do bloqueio (se houver)
    - Dias até o vencimento
    - Valor da mensalidade
    """
    if usuario_atual.tipo != "barbearia":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Apenas donos de barbearia podem verificar status"
        )

    # Buscar barbearia
    barbearia = db.query(models.Barbearia).filter(
        models.Barbearia.usuario_id == usuario_atual.id
    ).first()

    if not barbearia:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Barbearia não encontrada"
        )

    # Buscar assinatura
    assinatura = db.query(models.AssinaturaBarbearia).filter(
        models.AssinaturaBarbearia.barbearia_id == barbearia.id
    ).first()

    if not assinatura:
        return {
            "tem_assinatura": False,
            "bloqueada": barbearia.bloqueada,
            "motivo_bloqueio": barbearia.motivo_bloqueio,
            "status": "sem_assinatura",
            "mensagem": "Você precisa contratar uma assinatura para usar o app."
        }

    # Calcular dias até vencimento
    hoje = datetime.now()

    # Auto-correção para exibições incoerentes (ex.: 103+ dias em plano mensal)
    if _normalizar_vencimento_adiantado(assinatura, hoje):
        db.commit()
        db.refresh(assinatura)

    dias_vencimento = (assinatura.proximo_vencimento - hoje).days

    # Verificar se está vencida
    vencida = assinatura.proximo_vencimento < hoje

    return {
        "tem_assinatura": True,
        "bloqueada": barbearia.bloqueada,
        "motivo_bloqueio": barbearia.motivo_bloqueio,
        "bloqueada_em": barbearia.bloqueada_em.isoformat() if barbearia.bloqueada_em else None,
        "status": assinatura.status,
        "vencida": vencida,
        "dias_vencimento": dias_vencimento,
        "proximo_vencimento": assinatura.proximo_vencimento.isoformat(),
        "valor_mensalidade": assinatura.valor_mensalidade,
        "cadeiras_ativas": assinatura.quantidade_cadeiras,
        "metodo_pagamento": assinatura.metodo_pagamento_preferido,
        "mensagem": _gerar_mensagem_status(barbearia, assinatura, dias_vencimento, vencida)
    }


def _gerar_mensagem_status(barbearia, assinatura, dias_vencimento, vencida):
    """Gera mensagem apropriada baseada no status"""
    if barbearia.bloqueada:
        return f"⛔ Sua barbearia está bloqueada. {barbearia.motivo_bloqueio}"
    
    if vencida:
        return f"⚠️ Sua assinatura venceu! Complete o pagamento de R$ {assinatura.valor_mensalidade:.2f} para continuar."
    
    if dias_vencimento <= 3:
        return f"⚠️ Sua assinatura vence em {dias_vencimento} dia(s). Pague antes para evitar bloqueio."
    
    if dias_vencimento <= 7:
        return f"📅 Sua assinatura vence em {dias_vencimento} dias."
    
    return f"✅ Sua assinatura está ativa. Próximo vencimento em {dias_vencimento} dias."

