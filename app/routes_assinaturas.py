"""
Rotas de gerenciamento de assinaturas das barbearias
Sistema de cobrança por cadeira com desconto progressivo
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from typing import Optional
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
    precos_base = [47.90, 37.90, 27.90, 20.90, 17.90]
    preco_minimo = 17.90
    
    total = 0
    breakdown = []
    
    for i in range(num_cadeiras):
        if i < len(precos_base):
            preco = precos_base[i]
        else:
            preco = preco_minimo
        
        total += preco
        breakdown.append(preco)
    
    # Calcular economia (comparando com o preço da 1ª cadeira)
    preco_sem_desconto = num_cadeiras * 47.90
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
    
    # Calcular valores
    calculo = calcular_valor_assinatura(dados.cadeiras_ativas)
    
    # Verificar se já tem assinatura
    assinatura = db.query(models.AssinaturaBarbearia).filter(
        models.AssinaturaBarbearia.barbearia_id == barbearia.id
    ).first()
    
    if assinatura:
        # Atualizar assinatura existente
        assinatura.quantidade_cadeiras = dados.cadeiras_ativas
        assinatura.valor_mensalidade = calculo["valor_total"]
        assinatura.valor_por_cadeira = json.dumps(calculo["breakdown"])
        assinatura.economia_mensal = calculo["economia"]
        assinatura.metodo_pagamento_preferido = metodo_pagamento
        assinatura.ultima_atualizacao = datetime.now()
        
        # Se estava suspensa/cancelada, reativar
        if assinatura.status in ["suspensa", "cancelada", "inadimplente"]:
            assinatura.status = "ativa"
            assinatura.motivo_suspensao = None
            
        db.commit()
        db.refresh(assinatura)
        
        return serializar_assinatura(assinatura)
    else:
        # Criar nova assinatura
        proximo_vencimento = datetime.now() + timedelta(days=30)
        
        nova_assinatura = models.AssinaturaBarbearia(
            barbearia_id=barbearia.id,
            quantidade_cadeiras=dados.cadeiras_ativas,
            valor_mensalidade=calculo["valor_total"],
            valor_por_cadeira=json.dumps(calculo["breakdown"]),
            economia_mensal=calculo["economia"],
            metodo_pagamento_preferido=metodo_pagamento,
            dia_vencimento=10,
            proximo_vencimento=proximo_vencimento,
            status="ativa"
        )
        
        db.add(nova_assinatura)
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

    # Calcular novo vencimento mensal por mês de calendário.
    novo_vencimento = _calcular_novo_vencimento_assinatura(assinatura, hoje)

    # Atualizar assinatura
    assinatura.proximo_vencimento = novo_vencimento
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

