"""
ARQUIVO: app/routes_transacoes.py
Endpoints para rastreamento de transações financeiras (Cortes, Transações, Assinaturas)

RESPONSABILIDADE:
- Registrar cortes (serviços realizados)
- Contabilizar split de pagamento (40% freelancer, 50% barbearia, 10% plataforma)
- Gerar faturas de assinatura
- Auditoria de todas as movimentações de dinheiro
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from .database import get_db
from .models import (
    Usuario, Corte, TransacaoFinanceira, AssinaturaBarbearia, 
    FaturaAssinatura, Servico, Barbearia, TipoTransacao, ConfiguracaoSplitPagamento
)
from .routes import get_current_user
from pydantic import BaseModel
from typing import List, Optional

router = APIRouter(prefix="/api/v1/transacoes", tags=["transacoes"])


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
    if abs(total - 100.0) > 0.0001 or abs((cfg.percentual_barbearia or 0) - 50.0) > 0.0001:
        admin = db.query(Usuario).filter(Usuario.tipo == "admin").order_by(Usuario.id.asc()).first()
        return {
            "barbeiro": 40.0,
            "barbearia": 50.0,
            "barbermove": 10.0,
            "recebedor_plataforma_id": admin.id if admin else 1,
        }

    if cfg.recebedor_plataforma_id:
        recebedor_id = cfg.recebedor_plataforma_id
    else:
        admin = db.query(Usuario).filter(Usuario.tipo == "admin").order_by(Usuario.id.asc()).first()
        recebedor_id = admin.id if admin else 1

    return {
        "barbeiro": float(cfg.percentual_barbeiro),
        "barbearia": float(cfg.percentual_barbearia),
        "barbermove": float(cfg.percentual_barbermove),
        "recebedor_plataforma_id": recebedor_id,
    }


# ==========================================
# SCHEMAS (Pydantic)
# ==========================================

class CorteCreate(BaseModel):
    cliente_id: int
    freelancer_id: int
    barbearia_id: int
    servico_id: Optional[int] = None
    chamado_id: Optional[int] = None
    valor_total: float
    metodo_pagamento: str  # PIX, CARTAO, DINHEIRO


class CorteResponse(BaseModel):
    id: int
    cliente_id: int
    freelancer_id: int
    barbearia_id: int
    valor_total: float
    metodo_pagamento: str
    status_pagamento: str
    data_criacao: datetime
    
    class Config:
        from_attributes = True


class TransacaoResponse(BaseModel):
    id: int
    corte_id: Optional[int]
    recebedor_id: int
    tipo: str
    valor: float
    percentual: float
    status_repasse: str
    data_transacao: datetime
    
    class Config:
        from_attributes = True


class ExtratoBarbeiroResponse(BaseModel):
    """Formatado para o frontend - extrato de transações"""
    id: int
    data: str  # formatado como DD/MM/YYYY
    valor: float
    tipo: str
    status: str
    corte_id: Optional[int]


class ExtratoCompleto(BaseModel):
    """Resposta completa com saldo e extrato"""
    saldo_disponivel: float
    extrato: List[ExtratoBarbeiroResponse]


class SaldoBarbeiroResponse(BaseModel):
    """Resumo de saldo disponível para saque"""
    saldo_total: float  # Soma de todas as comissões
    saldo_bloqueado: float  # Saques em processamento
    saldo_disponivel: float  # Pronto para sacar


# ==========================================
# ENDPOINTS
# ==========================================

@router.post("/cortes", response_model=CorteResponse)
async def criar_corte(
    corte: CorteCreate,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    """
    Criar um novo corte (serviço realizado) e gerar transações automáticas.
    
     FLUXO:
     1. Cria registro em CORTES
     2. Gera 3 transações automáticas em TRANSACOES_FINANCEIRAS.
         Regra padrão: 40% freelancer, 50% barbearia, 10% plataforma.
    """
    
    # ✅ Validar que o usuário é admin ou a barbearia pertence a ele
    if current_user.tipo not in ['admin', 'barbearia']:
        raise HTTPException(status_code=403, detail="Apenas admin ou barbearia podem criar cortes")
    
    # Criar o corte
    novo_corte = Corte(
        cliente_id=corte.cliente_id,
        freelancer_id=corte.freelancer_id,
        barbearia_id=corte.barbearia_id,
        servico_id=corte.servico_id,
        chamado_id=corte.chamado_id,
        valor_total=corte.valor_total,
        metodo_pagamento=corte.metodo_pagamento,
        status_pagamento="aprovado",
        data_conclusao=datetime.utcnow()
    )
    db.add(novo_corte)
    db.flush()  # Para obter o ID antes de criar transações
    
    # === GERAR TRANSAÇÕES AUTOMÁTICAS ===
    # Split configurável: barbeiro + barbearia + BarberMove (admin).
    split_cfg = _resolver_split_config(db)
    barbearia_obj = db.query(Barbearia).filter(Barbearia.id == corte.barbearia_id).first()
    recebedor_barbearia_id = barbearia_obj.usuario_id if barbearia_obj else corte.barbearia_id
    valor_barbeiro = round(corte.valor_total * (split_cfg["barbeiro"] / 100.0), 2)
    valor_barbearia = round(corte.valor_total * (split_cfg["barbearia"] / 100.0), 2)
    valor_barbermove = round(corte.valor_total - valor_barbeiro - valor_barbearia, 2)

    splits = [
        {
            "recebedor_id": corte.freelancer_id,
            "tipo": TipoTransacao.COMISSAO_FREELANCER.value,
            "percentual": split_cfg["barbeiro"],
            "valor": valor_barbeiro,
            "status_repasse": "concluido",
            "data_repasse": datetime.utcnow(),
            "motivo_falha": None,
        },
        {
            "recebedor_id": recebedor_barbearia_id,
            "tipo": TipoTransacao.COMISSAO_BARBEARIA.value,
            "percentual": split_cfg["barbearia"],
            "valor": valor_barbearia,
            "status_repasse": "concluido",
            "data_repasse": datetime.utcnow(),
            "motivo_falha": None,
        },
        {
            "recebedor_id": split_cfg["recebedor_plataforma_id"],
            "tipo": TipoTransacao.TAXA_PLATAFORMA.value,
            "percentual": split_cfg["barbermove"],
            "valor": valor_barbermove,
            "status_repasse": "concluido",
            "data_repasse": datetime.utcnow(),
            "motivo_falha": None,
        },
    ]
    
    for split in splits:
        transacao = TransacaoFinanceira(
            corte_id=novo_corte.id,
            recebedor_id=split["recebedor_id"],
            tipo=split["tipo"],
            valor=split["valor"],
            percentual=split["percentual"],
            status_repasse=split["status_repasse"],
            data_repasse=split["data_repasse"],
            motivo_falha=split["motivo_falha"],
        )
        db.add(transacao)
    
    db.commit()
    db.refresh(novo_corte)
    
    return novo_corte


@router.get("/historico", response_model=List[TransacaoResponse])
async def listar_historico_transacoes(
    tipo: Optional[str] = Query(None),
    limite: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    """
    Listar histórico de transações do usuário logado.
    
    Filtra transações onde current_user é o recebedor.
    """
    
    query = db.query(TransacaoFinanceira).filter(
        TransacaoFinanceira.recebedor_id == current_user.id
    ).order_by(TransacaoFinanceira.data_transacao.desc()).limit(limite)
    
    if tipo:
        query = query.filter(TransacaoFinanceira.tipo == tipo)
    
    transacoes = query.all()
    return transacoes


@router.get("/extrato/{recebedor_id}", response_model=ExtratoCompleto)
async def obter_extrato_financeiro(
    recebedor_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    """
    Obter extrato completo com saldo disponível para o frontend.
    
    ✅ SEGURANÇA: Cada usuário só consegue ver seu próprio extrato
    (a menos que seja admin)
    
    Frontend chama: GET /api/v1/transacoes/extrato/{recebedor_id}
    Resposta: { saldo_disponivel: 1050.00, extrato: [...] }
    """
    
    # ✅ Verificar permissão: só pode ver seu próprio extrato ou ser admin
    if current_user.tipo != 'admin' and current_user.id != recebedor_id:
        raise HTTPException(status_code=403, detail="Acesso negado")
    
    # Buscar transações do recebedor (ultimas 30)
    transacoes = db.query(TransacaoFinanceira).filter(
        TransacaoFinanceira.recebedor_id == recebedor_id
    ).order_by(TransacaoFinanceira.data_transacao.desc()).limit(30).all()
    
    if not transacoes:
        return ExtratoCompleto(saldo_disponivel=0.0, extrato=[])
    
    # ✅ Calcular saldo total: SÓ transações concluídas
    saldo_total = sum(
        t.valor for t in transacoes 
        if t.status_repasse == "concluido"
    )
    
    # ✅ Formatar extrato para o frontend
    extrato_formatado = []
    for t in transacoes:
        extrato_formatado.append(
            ExtratoBarbeiroResponse(
                id=t.id,
                data=t.data_transacao.strftime("%d/%m/%Y"),
                valor=t.valor,
                tipo=t.tipo,
                status=t.status_repasse,
                corte_id=t.corte_id
            )
        )
    
    return ExtratoCompleto(
        saldo_disponivel=round(saldo_total, 2),
        extrato=extrato_formatado
    )


@router.get("/saldo", response_model=SaldoBarbeiroResponse)
async def obter_saldo(
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    """
    Obter saldo disponível para saque do barbeiro.
    
    CÁLCULO:
    - Saldo total: Soma de todas as COMISSAO_FREELANCER concluídas
    - Saldo bloqueado: Saques em processamento
    - Saldo disponível: Total - Bloqueado
    """
    
    # Apenas barbeiros têm saldo para saque
    if current_user.tipo != 'barbeiro':
        return SaldoBarbeiroResponse(
            saldo_total=0.0,
            saldo_bloqueado=0.0,
            saldo_disponivel=0.0
        )
    
    # Calcular saldo total (comissões concluídas)
    saldo_total_query = db.query(
        db.func.coalesce(
            db.func.sum(TransacaoFinanceira.valor), 
            0.0
        )
    ).filter(
        TransacaoFinanceira.recebedor_id == current_user.id,
        TransacaoFinanceira.tipo == TipoTransacao.COMISSAO_FREELANCER.value,
        TransacaoFinanceira.status_repasse.in_(["concluido", "pendente"])
    ).scalar()
    
    # TODO: Calcular saldo bloqueado (saques em processamento)
    # Por enquanto, retornar tudo como disponível
    saldo_disponivel = saldo_total_query
    
    return SaldoBarbeiroResponse(
        saldo_total=float(saldo_total_query),
        saldo_bloqueado=0.0,
        saldo_disponivel=float(saldo_disponivel)
    )


@router.get("/cortes", response_model=List[CorteResponse])
async def listar_cortes(
    cliente_id: Optional[int] = Query(None),
    freelancer_id: Optional[int] = Query(None),
    barbearia_id: Optional[int] = Query(None),
    limite: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    """
    Listar cortes com filtros.
    
    ✅ ADMIN: pode ver todos os cortes
    ✅ BARBEIRO: pode ver cortes onde é freelancer
    ✅ BARBEARIA: pode ver cortes da sua barbearia
    ✅ CLIENTE: pode ver cortes dele como cliente
    """
    
    query = db.query(Corte)
    
    # Aplicar filtros baseado em role
    if current_user.tipo == 'barbeiro':
        query = query.filter(Corte.freelancer_id == current_user.id)
    elif current_user.tipo == 'barbearia':
        query = query.filter(Corte.barbearia_id == current_user.id)
    elif current_user.tipo == 'cliente':
        query = query.filter(Corte.cliente_id == current_user.id)
    # admin pode ver tudo
    
    # Filtros adicionais
    if cliente_id:
        query = query.filter(Corte.cliente_id == cliente_id)
    if freelancer_id:
        query = query.filter(Corte.freelancer_id == freelancer_id)
    if barbearia_id:
        query = query.filter(Corte.barbearia_id == barbearia_id)
    
    cortes = query.order_by(Corte.data_criacao.desc()).limit(limite).all()
    return cortes


@router.get("/assinaturas/{barbearia_id}")
async def obter_assinatura(
    barbearia_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    """
    Obter detalhes da assinatura de uma barbearia.
    
    ✅ ADMIN: pode ver qualquer assinatura
    ✅ BARBEARIA: pode ver só a sua assinatura
    """
    
    # Verificar permissão
    if current_user.tipo == 'barbearia' and current_user.id != barbearia_id:
        raise HTTPException(status_code=403, detail="Acesso negado")
    
    assinatura = db.query(AssinaturaBarbearia).filter(
        AssinaturaBarbearia.barbearia_id == barbearia_id
    ).first()
    
    if not assinatura:
        raise HTTPException(status_code=404, detail="Assinatura não encontrada")
    
    return {
        "id": assinatura.id,
        "barbearia_id": assinatura.barbearia_id,
        "quantidade_cadeiras": assinatura.quantidade_cadeiras,
        "valor_mensalidade": assinatura.valor_mensalidade,
        "economia_mensal": assinatura.economia_mensal,
        "status": assinatura.status,
        "proximo_vencimento": assinatura.proximo_vencimento.isoformat() if assinatura.proximo_vencimento else None
    }


@router.get("/faturas/{barbearia_id}")
async def listar_faturas_assinatura(
    barbearia_id: int,
    limite: int = Query(12, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    """
    Listar faturas de assinatura de uma barbearia.
    
    ✅ ADMIN: pode ver qualquer fatura
    ✅ BARBEARIA: pode ver só suas faturas
    """
    
    # Verificar permissão
    if current_user.tipo == 'barbearia' and current_user.id != barbearia_id:
        raise HTTPException(status_code=403, detail="Acesso negado")
    
    # Obter assinatura primeiro
    assinatura = db.query(AssinaturaBarbearia).filter(
        AssinaturaBarbearia.barbearia_id == barbearia_id
    ).first()
    
    if not assinatura:
        raise HTTPException(status_code=404, detail="Assinatura não encontrada")
    
    # Listar faturas
    faturas = db.query(FaturaAssinatura).filter(
        FaturaAssinatura.assinatura_id == assinatura.id
    ).order_by(FaturaAssinatura.data_inicio_periodo.desc()).limit(limite).all()
    
    return [
        {
            "id": f.id,
            "mes_referencia": f.mes_referencia,
            "valor_fatura": f.valor_fatura,
            "quantidade_cadeiras": f.quantidade_cadeiras,
            "data_vencimento": f.data_vencimento.isoformat(),
            "data_pagamento": f.data_pagamento.isoformat() if f.data_pagamento else None,
            "status": f.status
        }
        for f in faturas
    ]


@router.post("/processar-saque/{saque_id}")
async def processar_saque_como_admin(
    saque_id: int,
    status: str,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    """
    ⚠️ APENAS ADMIN: Processar um saque pendente como concluído.
    
    Cria uma TransacaoFinanceira do tipo SAQUE_PROCESSADO.
    """
    
    if current_user.tipo != 'admin':
        raise HTTPException(status_code=403, detail="Apenas admin")
    
    if status not in ['concluido', 'falhou']:
        raise HTTPException(status_code=400, detail="Status inválido")
    
    # TODO: Implementar lógica de processamento de saque
    # Por enquanto, apenas um endpoint stub
    
    return {"mensagem": f"Saque {saque_id} processado como {status}"}
