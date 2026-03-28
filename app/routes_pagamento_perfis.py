from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import func
from sqlalchemy.orm import Session

from .database import get_db
from .models import (
    ConfiguracaoRepasseUsuario,
    ConfiguracaoSplitPagamento,
    ContaPagamentoUsuario,
    TipoTransacao,
    TransacaoFinanceira,
    Usuario,
)
from .routes import get_current_user

router = APIRouter(prefix="/api/v1/pagamentos-config", tags=["pagamentos-config"])


def _normalizar_split_fixo_50(cfg: ConfiguracaoSplitPagamento) -> bool:
    alterado = False
    if abs((cfg.percentual_barbeiro or 0.0) - 40.0) > 0.0001:
        cfg.percentual_barbeiro = 40.0
        alterado = True
    if abs((cfg.percentual_barbearia or 0.0) - 50.0) > 0.0001:
        cfg.percentual_barbearia = 50.0
        alterado = True
    if abs((cfg.percentual_barbermove or 0.0) - 10.0) > 0.0001:
        cfg.percentual_barbermove = 10.0
        alterado = True
    return alterado


def _exigir_recebedor_repasse(current_user: Usuario) -> None:
    if current_user.tipo not in {"barbeiro", "barbearia"}:
        raise HTTPException(
            status_code=403,
            detail="Apenas barbeiros e barbearias podem acessar configuracoes de recebimento",
        )


class ContaPagamentoPayload(BaseModel):
    chave_pix: Optional[str] = None
    banco: Optional[str] = None
    agencia: Optional[str] = None
    conta: Optional[str] = None
    tipo_conta: Optional[str] = "corrente"
    titular_nome: Optional[str] = None
    titular_documento: Optional[str] = None
    frequencia_repasse: Optional[str] = "semanal"  # diario | semanal | mensal
    dia_semana_repasse: Optional[int] = 1
    dia_mes_repasse: Optional[int] = 5


class SplitConfigPayload(BaseModel):
    percentual_barbeiro: float
    percentual_barbearia: float
    percentual_barbermove: float
    deposito_nome: Optional[str] = None
    deposito_chave_pix: Optional[str] = None
    deposito_banco: Optional[str] = None
    deposito_agencia: Optional[str] = None
    deposito_conta: Optional[str] = None
    recebedor_plataforma_id: Optional[int] = None


def _obter_ou_criar_config(db: Session) -> ConfiguracaoSplitPagamento:
    cfg = db.query(ConfiguracaoSplitPagamento).order_by(ConfiguracaoSplitPagamento.id.asc()).first()
    if cfg:
        if _normalizar_split_fixo_50(cfg):
            cfg.atualizado_em = datetime.utcnow()
            db.commit()
            db.refresh(cfg)
        return cfg

    admin = db.query(Usuario).filter(Usuario.tipo == "admin").order_by(Usuario.id.asc()).first()
    cfg = ConfiguracaoSplitPagamento(
        percentual_barbeiro=40.0,
        percentual_barbearia=50.0,
        percentual_barbermove=10.0,
        recebedor_plataforma_id=admin.id if admin else None,
    )
    db.add(cfg)
    db.commit()
    db.refresh(cfg)
    return cfg


def _normalizar_frequencia_repasse(frequencia: Optional[str]) -> str:
    valor = (frequencia or "semanal").strip().lower()
    if valor not in {"diario", "semanal", "mensal"}:
        return "semanal"
    return valor


def _obter_ou_criar_repasse(db: Session, usuario_id: int) -> ConfiguracaoRepasseUsuario:
    cfg = db.query(ConfiguracaoRepasseUsuario).filter(
        ConfiguracaoRepasseUsuario.usuario_id == usuario_id
    ).first()
    if cfg:
        return cfg

    cfg = ConfiguracaoRepasseUsuario(
        usuario_id=usuario_id,
        frequencia_repasse="semanal",
        dia_semana_repasse=1,
        dia_mes_repasse=5,
    )
    db.add(cfg)
    db.commit()
    db.refresh(cfg)
    return cfg


def _calcular_proximo_repasse(frequencia: str, dia_semana: int, dia_mes: int) -> datetime:
    agora = datetime.utcnow()

    if frequencia == "diario":
        proximo = (agora + timedelta(days=1)).replace(hour=9, minute=0, second=0, microsecond=0)
        return proximo

    if frequencia == "semanal":
        dia_semana = max(0, min(6, int(dia_semana or 1)))
        dias = (dia_semana - agora.weekday()) % 7
        if dias == 0:
            dias = 7
        proximo = (agora + timedelta(days=dias)).replace(hour=9, minute=0, second=0, microsecond=0)
        return proximo

    dia_mes = max(1, min(28, int(dia_mes or 5)))
    ano = agora.year
    mes = agora.month
    if agora.day >= dia_mes:
        if mes == 12:
            mes = 1
            ano += 1
        else:
            mes += 1
    proximo = datetime(ano, mes, dia_mes, 9, 0, 0)
    return proximo


@router.get("/conta")
def obter_conta_pagamento(
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    _exigir_recebedor_repasse(current_user)

    conta = db.query(ContaPagamentoUsuario).filter(
        ContaPagamentoUsuario.usuario_id == current_user.id
    ).first()
    repasse = _obter_ou_criar_repasse(db, current_user.id)

    if not conta:
        return {
            "usuario_id": current_user.id,
            "chave_pix": None,
            "banco": None,
            "agencia": None,
            "conta": None,
            "tipo_conta": "corrente",
            "titular_nome": current_user.nome,
            "titular_documento": current_user.cpf if current_user.tipo != "barbearia" else current_user.cnpj,
            "frequencia_repasse": repasse.frequencia_repasse,
            "dia_semana_repasse": repasse.dia_semana_repasse,
            "dia_mes_repasse": repasse.dia_mes_repasse,
            "ativo": True,
        }

    return {
        "usuario_id": conta.usuario_id,
        "chave_pix": conta.chave_pix,
        "banco": conta.banco,
        "agencia": conta.agencia,
        "conta": conta.conta,
        "tipo_conta": conta.tipo_conta,
        "titular_nome": conta.titular_nome,
        "titular_documento": conta.titular_documento,
        "frequencia_repasse": repasse.frequencia_repasse,
        "dia_semana_repasse": repasse.dia_semana_repasse,
        "dia_mes_repasse": repasse.dia_mes_repasse,
        "ativo": conta.ativo,
    }


@router.put("/conta")
def salvar_conta_pagamento(
    payload: ContaPagamentoPayload,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    _exigir_recebedor_repasse(current_user)

    conta = db.query(ContaPagamentoUsuario).filter(
        ContaPagamentoUsuario.usuario_id == current_user.id
    ).first()
    repasse = _obter_ou_criar_repasse(db, current_user.id)

    if not conta:
        conta = ContaPagamentoUsuario(usuario_id=current_user.id)
        db.add(conta)

    conta.chave_pix = payload.chave_pix
    conta.banco = payload.banco
    conta.agencia = payload.agencia
    conta.conta = payload.conta
    conta.tipo_conta = payload.tipo_conta or "corrente"
    conta.titular_nome = payload.titular_nome or current_user.nome
    conta.titular_documento = payload.titular_documento
    conta.ativo = True
    conta.atualizado_em = datetime.utcnow()

    repasse.frequencia_repasse = _normalizar_frequencia_repasse(payload.frequencia_repasse)
    repasse.dia_semana_repasse = max(0, min(6, int(payload.dia_semana_repasse or 1)))
    repasse.dia_mes_repasse = max(1, min(28, int(payload.dia_mes_repasse or 5)))
    repasse.ativo = True
    repasse.atualizado_em = datetime.utcnow()

    db.commit()
    db.refresh(conta)

    return {
        "message": "Conta de pagamento atualizada com sucesso",
        "conta": {
            "usuario_id": conta.usuario_id,
            "chave_pix": conta.chave_pix,
            "banco": conta.banco,
            "agencia": conta.agencia,
            "conta": conta.conta,
            "tipo_conta": conta.tipo_conta,
            "titular_nome": conta.titular_nome,
            "titular_documento": conta.titular_documento,
            "frequencia_repasse": repasse.frequencia_repasse,
            "dia_semana_repasse": repasse.dia_semana_repasse,
            "dia_mes_repasse": repasse.dia_mes_repasse,
            "ativo": conta.ativo,
        },
    }


@router.get("/resumo")
def obter_resumo_pagamento(
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    _exigir_recebedor_repasse(current_user)

    repasse = _obter_ou_criar_repasse(db, current_user.id)
    frequencia = _normalizar_frequencia_repasse(repasse.frequencia_repasse)

    tipo_comissao = (
        TipoTransacao.COMISSAO_BARBEARIA.value
        if current_user.tipo == "barbearia"
        else TipoTransacao.COMISSAO_FREELANCER.value
    )

    saldo_disponivel = db.query(
        func.coalesce(func.sum(TransacaoFinanceira.valor), 0.0)
    ).filter(
        TransacaoFinanceira.recebedor_id == current_user.id,
        TransacaoFinanceira.tipo == tipo_comissao,
        TransacaoFinanceira.status_repasse == "concluido",
    ).scalar() or 0.0

    periodo_inicio = datetime.utcnow() - timedelta(days=7)
    if frequencia == "diario":
        periodo_inicio = datetime.utcnow() - timedelta(days=1)
    elif frequencia == "mensal":
        periodo_inicio = datetime.utcnow() - timedelta(days=30)

    valor_periodo = db.query(
        func.coalesce(func.sum(TransacaoFinanceira.valor), 0.0)
    ).filter(
        TransacaoFinanceira.recebedor_id == current_user.id,
        TransacaoFinanceira.tipo == tipo_comissao,
        TransacaoFinanceira.status_repasse == "concluido",
        TransacaoFinanceira.data_transacao >= periodo_inicio,
    ).scalar() or 0.0

    proximo_repasse = _calcular_proximo_repasse(
        frequencia,
        repasse.dia_semana_repasse,
        repasse.dia_mes_repasse,
    )

    return {
        "usuario_id": current_user.id,
        "frequencia_repasse": frequencia,
        "dia_semana_repasse": repasse.dia_semana_repasse,
        "dia_mes_repasse": repasse.dia_mes_repasse,
        "saldo_disponivel": round(float(saldo_disponivel), 2),
        "valor_estimado_periodo": round(float(valor_periodo), 2),
        "proximo_repasse_em": proximo_repasse.isoformat(),
    }


@router.get("/split")
def obter_split_config(
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    cfg = _obter_ou_criar_config(db)
    total = (cfg.percentual_barbeiro or 0) + (cfg.percentual_barbearia or 0) + (cfg.percentual_barbermove or 0)

    return {
        "percentual_barbeiro": cfg.percentual_barbeiro,
        "percentual_barbearia": cfg.percentual_barbearia,
        "percentual_barbermove": cfg.percentual_barbermove,
        "percentual_total": round(total, 4),
        "recebedor_plataforma_id": cfg.recebedor_plataforma_id,
        "deposito_nome": cfg.deposito_nome,
        "deposito_chave_pix": cfg.deposito_chave_pix,
        "deposito_banco": cfg.deposito_banco,
        "deposito_agencia": cfg.deposito_agencia,
        "deposito_conta": cfg.deposito_conta,
    }


@router.put("/split")
def salvar_split_config(
    payload: SplitConfigPayload,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    if current_user.tipo != "admin":
        raise HTTPException(status_code=403, detail="Apenas admin pode alterar split e deposito")

    if abs(payload.percentual_barbearia - 50.0) > 0.0001:
        raise HTTPException(status_code=400, detail="O percentual da barbearia deve ser 50%")

    total = payload.percentual_barbeiro + payload.percentual_barbearia + payload.percentual_barbermove
    if abs(total - 100.0) > 0.0001:
        raise HTTPException(status_code=400, detail="A soma dos percentuais deve ser 100")

    if payload.percentual_barbeiro < 0 or payload.percentual_barbearia < 0 or payload.percentual_barbermove < 0:
        raise HTTPException(status_code=400, detail="Percentuais nao podem ser negativos")

    cfg = _obter_ou_criar_config(db)
    cfg.percentual_barbeiro = payload.percentual_barbeiro
    cfg.percentual_barbearia = payload.percentual_barbearia
    cfg.percentual_barbermove = payload.percentual_barbermove
    cfg.deposito_nome = payload.deposito_nome
    cfg.deposito_chave_pix = payload.deposito_chave_pix
    cfg.deposito_banco = payload.deposito_banco
    cfg.deposito_agencia = payload.deposito_agencia
    cfg.deposito_conta = payload.deposito_conta
    cfg.recebedor_plataforma_id = payload.recebedor_plataforma_id or current_user.id
    cfg.atualizado_por_id = current_user.id
    cfg.atualizado_em = datetime.utcnow()

    db.commit()
    db.refresh(cfg)

    return {
        "message": "Configuracao de split atualizada com sucesso",
        "split": {
            "percentual_barbeiro": cfg.percentual_barbeiro,
            "percentual_barbearia": cfg.percentual_barbearia,
            "percentual_barbermove": cfg.percentual_barbermove,
            "recebedor_plataforma_id": cfg.recebedor_plataforma_id,
            "deposito_nome": cfg.deposito_nome,
            "deposito_chave_pix": cfg.deposito_chave_pix,
            "deposito_banco": cfg.deposito_banco,
            "deposito_agencia": cfg.deposito_agencia,
            "deposito_conta": cfg.deposito_conta,
        },
    }
