"""
O que cada finalidade cobra (preparar) e o que libera depois do pagamento confirmado (aplicar).

`preparar` roda na criação da cobrança e NÃO altera nada no sistema.
`aplicar` roda uma única vez, quando o provedor confirma a aprovação. Não faz commit.
"""

import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Callable, Dict, Optional

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app import models
from app.cobrancas.constantes import Finalidade

logger = logging.getLogger(__name__)


@dataclass
class Preparo:
    valor: float
    descricao: str
    referencia: dict
    chave_referencia: str


@dataclass
class Efeito:
    preparar: Callable[[Session, models.Usuario, dict], Preparo]
    aplicar: Callable[[Session, models.Cobranca, dict], Optional[str]]  # retorna observação


def _barbearia_do_dono(db: Session, usuario: models.Usuario) -> models.Barbearia:
    if usuario.tipo != "barbearia":
        raise HTTPException(status_code=403, detail="Apenas donos de barbearia podem pagar o plano")
    barbearia = db.query(models.Barbearia).filter(models.Barbearia.usuario_id == usuario.id).first()
    if not barbearia:
        raise HTTPException(status_code=404, detail="Barbearia não encontrada")
    return barbearia


def _cadeiras_ativas_atuais(db: Session, barbearia_id: int):
    """(assinatura, quantidade ativa) com o mesmo critério de /assinaturas/contratar (inclui legado)."""
    from app.routes_assinaturas import _resumo_ativo_cadeiras

    assinatura = db.query(models.AssinaturaBarbearia).filter(
        models.AssinaturaBarbearia.barbearia_id == barbearia_id
    ).first()
    if not assinatura:
        return None, 0
    ativas = len(_resumo_ativo_cadeiras(db, assinatura.id))
    if ativas == 0 and (assinatura.quantidade_cadeiras or 0) > 0:
        ativas = assinatura.quantidade_cadeiras
    return assinatura, ativas


# ============================================================
# PROPRIETÁRIO - CONTRATAR/AUMENTAR CADEIRAS
# ============================================================

def _preparar_assinatura_cadeiras(db: Session, usuario: models.Usuario, dados: dict) -> Preparo:
    from app.routes_assinaturas import (
        _barbearia_tem_historico_contratacao,
        calcular_precos_cadeiras_adicionais,
        calcular_precos_compra_inicial,
    )

    barbearia = _barbearia_do_dono(db, usuario)
    try:
        quantidade = int(dados.get("cadeiras_ativas") or 0)
    except (TypeError, ValueError):
        quantidade = 0
    if quantidade < 1 or quantidade > 20:
        raise HTTPException(status_code=400, detail="Número de cadeiras deve estar entre 1 e 20")

    assinatura, atuais = _cadeiras_ativas_atuais(db, barbearia.id)
    novas = quantidade - atuais
    if novas <= 0:
        raise HTTPException(status_code=400, detail="Não há cadeiras novas para pagar nesta contratação")

    if assinatura is None and not _barbearia_tem_historico_contratacao(db, barbearia.id):
        precos = calcular_precos_compra_inicial(novas)
    else:
        precos = calcular_precos_cadeiras_adicionais(novas)
    valor = round(sum(precos), 2)

    return Preparo(
        valor=valor,
        descricao=f"BarberMove - {novas} cadeira(s) - {barbearia.nome or 'Barbearia'}",
        referencia={"barbearia_id": barbearia.id, "cadeiras_atuais": atuais,
                    "cadeiras_novas": novas, "cadeiras_ativas": quantidade},
        chave_referencia=f"cadeiras:{barbearia.id}:{atuais}->{quantidade}",
    )


def _aplicar_assinatura_cadeiras(db: Session, cobranca: models.Cobranca, ref: dict) -> Optional[str]:
    from app.routes_assinaturas import aplicar_contratacao_cadeiras

    barbearia = db.query(models.Barbearia).filter(models.Barbearia.id == ref["barbearia_id"]).first()
    if not barbearia:
        return "Barbearia não encontrada na liberação"
    # Libera as cadeiras pagas sobre o que estiver ativo agora (nunca reduz).
    _, atuais_agora = _cadeiras_ativas_atuais(db, barbearia.id)
    alvo = atuais_agora + int(ref["cadeiras_novas"])
    aplicar_contratacao_cadeiras(db, barbearia, alvo, "pix")
    obs = None
    if atuais_agora != ref.get("cadeiras_atuais"):
        obs = f"Cadeiras ativas mudaram entre a cobrança ({ref.get('cadeiras_atuais')}) e o pagamento ({atuais_agora})"
        logger.warning("[cobrancas] %s: %s", cobranca.identificador, obs)
    return obs


# ============================================================
# PROPRIETÁRIO - MENSALIDADE
# ============================================================

def _preparar_mensalidade(db: Session, usuario: models.Usuario, dados: dict) -> Preparo:
    barbearia = _barbearia_do_dono(db, usuario)
    assinatura = db.query(models.AssinaturaBarbearia).filter(
        models.AssinaturaBarbearia.barbearia_id == barbearia.id
    ).first()
    if not assinatura:
        raise HTTPException(status_code=404, detail="Nenhuma assinatura encontrada. Contrate uma assinatura primeiro.")
    valor = round(float(assinatura.valor_mensalidade or 0.0), 2)
    if valor <= 0:
        raise HTTPException(status_code=400, detail="Assinatura sem valor de mensalidade")
    venc = assinatura.proximo_vencimento.date().isoformat() if assinatura.proximo_vencimento else "sem-vencimento"
    return Preparo(
        valor=valor,
        descricao=f"BarberMove - mensalidade {assinatura.quantidade_cadeiras or 0} cadeira(s)",
        referencia={"barbearia_id": barbearia.id, "assinatura_id": assinatura.id, "vencimento": venc},
        chave_referencia=f"mensalidade:{assinatura.id}:{venc}",
    )


def _aplicar_mensalidade(db: Session, cobranca: models.Cobranca, ref: dict) -> Optional[str]:
    from app.routes_assinaturas import aplicar_pagamento_mensalidade

    barbearia = db.query(models.Barbearia).filter(models.Barbearia.id == ref["barbearia_id"]).first()
    assinatura = db.query(models.AssinaturaBarbearia).filter(
        models.AssinaturaBarbearia.id == ref["assinatura_id"]
    ).first()
    if not barbearia or not assinatura:
        return "Barbearia/assinatura não encontrada na liberação"
    aplicar_pagamento_mensalidade(db, barbearia, assinatura, "pix")
    return None


# ============================================================
# FREELANCER - TAXA BARBERMOVE (fechamento diário)
# ============================================================

def _preparar_taxa_freelancer(db: Session, usuario: models.Usuario, dados: dict) -> Preparo:
    from app import pagamento_diario

    if usuario.tipo != "barbeiro":
        raise HTTPException(status_code=403, detail="Apenas freelancers pagam a taxa BarberMove")
    abertos = pagamento_diario.fechamentos_abertos(db, usuario.id)
    if not abertos:
        raise HTTPException(status_code=400, detail="Nenhuma taxa em aberto")
    ids = sorted(f.id for f in abertos)
    valor = round(sum(float(f.valor_devido or 0.0) for f in abertos), 2)
    if valor <= 0:
        raise HTTPException(status_code=400, detail="Nenhuma taxa em aberto")
    dias = ", ".join(f.data_referencia.strftime("%d/%m") for f in abertos)
    return Preparo(
        valor=valor,
        descricao=f"BarberMove - taxa do freelancer ({dias})",
        referencia={"fechamento_ids": ids},
        chave_referencia="taxa:" + ",".join(str(i) for i in ids),
    )


def _aplicar_taxa_freelancer(db: Session, cobranca: models.Cobranca, ref: dict) -> Optional[str]:
    from app import pagamento_diario
    from app.routes_freelancer import _obter_ou_criar_carteira, _registrar_movimentacao

    fechamentos = db.query(models.FechamentoDiarioFreelancer).filter(
        models.FechamentoDiarioFreelancer.id.in_(ref.get("fechamento_ids") or []),
        models.FechamentoDiarioFreelancer.freelancer_id == cobranca.usuario_id,
    ).all()
    agora = datetime.utcnow()
    ja_quitados = []
    for f in fechamentos:
        if f.status not in pagamento_diario.STATUS_ABERTOS:
            ja_quitados.append(f.data_referencia.strftime("%d/%m"))
            continue
        carteira = _obter_ou_criar_carteira(db, f.freelancer_id)
        _registrar_movimentacao(
            db,
            carteira=carteira,
            tipo="quitacao_debito_pix",
            descricao=f"Taxa BarberMove ({f.data_referencia.strftime('%d/%m/%Y')}) paga via Pix (Mercado Pago)",
            valor=round(float(f.valor_devido or 0.0), 2),
            chamado_id=None,
        )
        f.status = "confirmado"
        f.pagamento_informado_em = f.pagamento_informado_em or agora
        f.decidido_em = agora
        f.decidido_por_id = None  # confirmação automática pelo provedor
    if ja_quitados:
        obs = f"Fechamento(s) {', '.join(ja_quitados)} já estavam confirmados antes do Pix; não creditados de novo"
        logger.warning("[cobrancas] %s: %s", cobranca.identificador, obs)
        return obs
    return None


EFEITOS: Dict[str, Efeito] = {
    Finalidade.ASSINATURA_CADEIRAS.value: Efeito(_preparar_assinatura_cadeiras, _aplicar_assinatura_cadeiras),
    Finalidade.MENSALIDADE_BARBEARIA.value: Efeito(_preparar_mensalidade, _aplicar_mensalidade),
    Finalidade.TAXA_FREELANCER.value: Efeito(_preparar_taxa_freelancer, _aplicar_taxa_freelancer),
}
