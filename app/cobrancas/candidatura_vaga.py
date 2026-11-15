"""
Taxa de candidatura a vaga de diária (finalidade CANDIDATURA_VAGA): R$ 3,00 por candidatura.

Fluxo:
1. Freelancer toca em "Candidatar-se" -> POST /on-demand/cadeiras-acionadas/{id}/candidatar-se.
   Com a taxa ativa e sem crédito, a API responde 402 e NADA é registrado.
2. O app gera o Pix em POST /api/v1/cobrancas/pix/candidatura-vaga (mesmo módulo de cobranças
   dos outros pagamentos). Antes de cobrar, todas as regras da candidatura são validadas.
3. O Mercado Pago confirma (webhook / consulta / conciliação) -> `aplicar` cria a candidatura,
   uma única vez, e o dono é avisado. Antes disso o dono não vê candidatura nenhuma.
4. Pago, mas a candidatura não pôde ser concluída (vaga fechou, falha ao gravar): o valor vira
   CRÉDITO (CandidaturaPaga.status=CREDITO) e a próxima candidatura usa o crédito sem novo Pix.

Liga/desliga: TAXA_CANDIDATURA_VAGA_ATIVA=1 no ambiente (e o Pix do Mercado Pago configurado).
Desligada, a candidatura funciona exatamente como antes.

A gratuidade dos 30 dias (etapa 2) entra em `exige_pagamento`.
"""

import logging
import os
from datetime import datetime
from typing import Optional

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app import models

logger = logging.getLogger(__name__)

VALOR_CANDIDATURA = 3.00

CONCLUIDA = "CONCLUIDA"
CREDITO = "CREDITO"

MENSAGEM_PAGAMENTO_NECESSARIO = (
    "Para se candidatar a esta vaga de diária, pague a taxa de candidatura de R$ 3,00 via Pix. "
    "A candidatura é enviada assim que o pagamento for confirmado."
)

# Avisos (push + websocket) gerados dentro da transação; a rota emite depois do commit.
_CHAVE_AVISOS = "avisos_candidatura_paga"


def taxa_ativa() -> bool:
    from app.cobrancas.provedores import pix_disponivel

    ligada = (os.getenv("TAXA_CANDIDATURA_VAGA_ATIVA") or "").strip().lower() in ("1", "true", "sim", "on")
    return ligada and pix_disponivel()


def exige_pagamento(db: Session, usuario: models.Usuario, vaga: models.CadeiraAcionada) -> bool:
    """Esta candidatura precisa da taxa? Só vaga de diária, com a cobrança ligada."""
    from app.vagas import TIPO_VAGA_DIARIA

    return taxa_ativa() and vaga.tipo_servico == TIPO_VAGA_DIARIA


def credito_disponivel(db: Session, freelancer_id: int, travar: bool = False) -> Optional[models.CandidaturaPaga]:
    q = db.query(models.CandidaturaPaga).filter(
        models.CandidaturaPaga.freelancer_id == freelancer_id,
        models.CandidaturaPaga.status == CREDITO,
    ).order_by(models.CandidaturaPaga.id)
    if travar:
        q = q.with_for_update()
    return q.first()


def consumir_credito(credito: models.CandidaturaPaga, vaga_id: int, candidatura_id: int) -> None:
    """Usa o crédito de um Pix já pago nesta candidatura. Não faz commit."""
    credito.status = CONCLUIDA
    credito.vaga_utilizada_id = vaga_id
    credito.candidatura_id = candidatura_id
    credito.concluida_em = datetime.utcnow()
    logger.info("[candidatura_vaga] crédito %s (cobranca %s) usado na vaga %s pelo freelancer %s",
                credito.id, credito.cobranca_id, vaga_id, credito.freelancer_id)


# ============================================================
# EFEITO DA COBRANÇA
# ============================================================

def preparar(db: Session, usuario: models.Usuario, dados: dict):
    from app.cobrancas.efeitos import Preparo
    from app.routes_on_demand import candidatura_existente, validar_candidatura

    try:
        vaga_id = int(dados.get("vaga_id"))
    except (TypeError, ValueError):
        raise HTTPException(status_code=400, detail="Vaga inválida")

    # Mesmas regras da candidatura: não se cobra de quem não poderia se candidatar.
    vaga, barbearia, _ = validar_candidatura(db, usuario, vaga_id)
    if candidatura_existente(db, vaga.id, usuario.id):
        raise HTTPException(status_code=409, detail="Você já se candidatou a esta vaga.")
    if not exige_pagamento(db, usuario, vaga):
        raise HTTPException(status_code=400, detail="Esta candidatura não tem taxa. Toque em Candidatar-se.")
    if credito_disponivel(db, usuario.id):
        raise HTTPException(
            status_code=409,
            detail="Você já tem uma candidatura paga guardada como crédito. Toque em Candidatar-se para usá-la.",
        )

    return Preparo(
        valor=VALOR_CANDIDATURA,
        descricao=f"BarberMove - candidatura à vaga de diária - {barbearia.nome or 'Barbearia'}",
        referencia={"vaga_id": vaga.id, "barbearia_id": barbearia.id},
        chave_referencia=f"candidatura:{vaga.id}:{usuario.id}",
    )


def _motivo_vaga_indisponivel(db: Session, freelancer: models.Usuario, vaga: Optional[models.CadeiraAcionada]):
    from app.routes_on_demand import candidatura_existente

    if not vaga or (vaga.convidado_id is not None and vaga.convidado_id != freelancer.id):
        return "A vaga não foi encontrada"
    if vaga.status != "disponivel" or (vaga.expira_em is not None and vaga.expira_em <= datetime.utcnow()):
        return "A vaga não estava mais disponível quando o pagamento foi confirmado"
    if candidatura_existente(db, vaga.id, freelancer.id):
        return "Você já tinha candidatura nesta vaga"
    return None


def aplicar(db: Session, cobranca: models.Cobranca, ref: dict) -> Optional[str]:
    """
    Pix aprovado: registra a candidatura (ou guarda o crédito). Roda uma vez por cobrança
    (liberado_em, linha travada); cobranca_id único em candidaturas_pagas reforça isso.
    """
    from app.routes_on_demand import registrar_candidatura

    if db.query(models.CandidaturaPaga.id).filter(models.CandidaturaPaga.cobranca_id == cobranca.id).first():
        return "Pagamento já registrado anteriormente; nada aplicado de novo"

    vaga_id = int(ref.get("vaga_id") or 0)
    registro = models.CandidaturaPaga(
        cobranca_id=cobranca.id,
        freelancer_id=cobranca.usuario_id,
        vaga_id=vaga_id,
        valor=round(float(cobranca.valor or 0.0), 2),
        status=CREDITO,
    )
    db.add(registro)
    db.flush()

    freelancer = db.query(models.Usuario).filter(models.Usuario.id == cobranca.usuario_id).first()
    vaga = db.query(models.CadeiraAcionada).filter(models.CadeiraAcionada.id == vaga_id).first()
    barbearia = (
        db.query(models.Barbearia).filter(models.Barbearia.id == vaga.barbearia_id).first() if vaga else None
    )

    motivo = "Freelancer não encontrado" if not freelancer else _motivo_vaga_indisponivel(db, freelancer, vaga)
    if not motivo and not barbearia:
        motivo = "A barbearia da vaga não foi encontrada"

    if not motivo:
        try:
            with db.begin_nested():
                candidatura = registrar_candidatura(db, freelancer, vaga, barbearia)
            registro.status = CONCLUIDA
            registro.vaga_utilizada_id = vaga.id
            registro.candidatura_id = candidatura.id
            registro.concluida_em = datetime.utcnow()
            db.add(models.Notificacao(
                usuario_id=freelancer.id,
                titulo="Pagamento confirmado: candidatura enviada ✅",
                mensagem=f"Sua candidatura à vaga de diária da {barbearia.nome or 'barbearia'} foi enviada ao proprietário.",
                tipo="vaga_candidatura_paga",
                referencia_id=vaga.id,
            ))
            db.info.setdefault(_CHAVE_AVISOS, []).append({
                "freelancer_id": freelancer.id,
                "freelancer_nome": freelancer.nome,
                "barbearia_id": barbearia.id,
                "vaga_id": vaga.id,
            })
            logger.info("[candidatura_vaga] %s: candidatura %s registrada (vaga %s, freelancer %s)",
                        cobranca.identificador, candidatura.id, vaga.id, freelancer.id)
            return None
        except Exception:
            logger.exception("[candidatura_vaga] %s: falha ao registrar a candidatura; valor vira crédito",
                             cobranca.identificador)
            motivo = "Não foi possível concluir a candidatura"

    registro.observacao = motivo
    if freelancer:
        db.add(models.Notificacao(
            usuario_id=freelancer.id,
            titulo="Pagamento confirmado: crédito guardado",
            mensagem=(
                f"{motivo}. Os R$ {f'{registro.valor:.2f}'.replace('.', ',')} ficaram como crédito: "
                "sua próxima candidatura a uma vaga de diária não será cobrada."
            ),
            tipo="vaga_credito_candidatura",
            referencia_id=vaga_id or None,
        ))
    logger.warning("[candidatura_vaga] %s: %s (vaga %s); crédito guardado para o freelancer %s",
                   cobranca.identificador, motivo, vaga_id, cobranca.usuario_id)
    return f"{motivo}; valor guardado como crédito de candidatura"


# ============================================================
# AVISOS DEPOIS DO COMMIT
# ============================================================

def _retirar_avisos(db: Session) -> list:
    return db.info.pop(_CHAVE_AVISOS, None) or []


async def emitir_avisos(db: Session) -> None:
    """Push + websocket para o dono, das candidaturas liberadas nesta sessão (já commitadas)."""
    from app.realtime import broadcast_event
    from app.routes_on_demand import avisar_dono_por_push

    for aviso in _retirar_avisos(db):
        try:
            barbearia = db.query(models.Barbearia).filter(models.Barbearia.id == aviso["barbearia_id"]).first()
            if barbearia:
                avisar_dono_por_push(db, aviso["freelancer_nome"], barbearia)
            await broadcast_event(
                "cadeira_acionada_candidatura",
                autor_id=aviso["freelancer_id"],
                vaga_id=aviso["vaga_id"],
                barbearia_id=aviso["barbearia_id"],
            )
        except Exception as exc:  # aviso é extra: o dono também recebe a notificação no sino
            logger.warning("[candidatura_vaga] aviso da vaga %s falhou: %s", aviso.get("vaga_id"), exc)


def emitir_avisos_em_thread(db: Session) -> None:
    """Para rotas síncronas (rodam em thread do anyio). Fora disso, só descarta os avisos."""
    if not db.info.get(_CHAVE_AVISOS):
        return
    try:
        import anyio.from_thread

        anyio.from_thread.run(emitir_avisos, db)
    except Exception as exc:
        _retirar_avisos(db)
        logger.debug("[candidatura_vaga] avisos não emitidos fora do loop: %s", exc)
