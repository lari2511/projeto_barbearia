"""
Alteração de serviço pelo freelancer (com confirmação do cliente).

Atendimento com mais de um serviço (vários chamados com o mesmo grupo_id, ou um
serviço da categoria "combo"): o freelancer pode pedir para trocar os serviços
(ex.: Corte + Barba -> Corte). O pedido NÃO altera nada no atendimento; só quando o
CLIENTE confirma é que:
- chamados do grupo cujo serviço saiu são cancelados (motivo registrado);
- chamados cujo serviço foi trocado recebem o novo servico_id (e o snapshot de valor).
Pagamento e taxa de 10% já são calculados por chamado a partir do serviço, então o
novo valor passa a valer automaticamente. Recusa / sem resposta: nada muda.
"""

from datetime import datetime, timedelta
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app import models
from app.database import get_db
from app.routes import get_current_user, calcular_split_pagamento, _duracao_servico_min, _calcular_fim_grupo

router = APIRouter(prefix="/api/v1", tags=["Alteração de serviço"])

CANCELADO = models.StatusAgendamento.CANCELADO.value
CONCLUIDO = models.StatusAgendamento.CONCLUIDO.value
EM_ATENDIMENTO = models.StatusAgendamento.EM_ATENDIMENTO.value
STATUS_ATIVOS = ("pendente", "aceito", "confirmado", EM_ATENDIMENTO)


class SolicitarAlteracaoRequest(BaseModel):
    servico_ids: List[int]


class ResponderAlteracaoRequest(BaseModel):
    confirmar: bool


# ============================================================
# HELPERS
# ============================================================

def _membros_grupo(db: Session, chamado: models.Chamado) -> List[models.Chamado]:
    """Chamados do atendimento (grupo), sem os cancelados."""
    if chamado.grupo_id:
        membros = db.query(models.Chamado).filter(models.Chamado.grupo_id == chamado.grupo_id).all()
    else:
        membros = [chamado]
    return [m for m in membros if str(m.status or "").lower() != CANCELADO]


def _nome(db: Session, servico_id) -> str:
    s = db.query(models.Servico).filter(models.Servico.id == servico_id).first()
    return s.nome if s else "Serviço"


def _descricao(db: Session, servico_ids) -> str:
    return " + ".join(_nome(db, sid) for sid in servico_ids)


def _tem_mais_de_um_servico(db: Session, membros: List[models.Chamado]) -> bool:
    if len(membros) > 1:
        return True
    if len(membros) == 1:
        s = db.query(models.Servico).filter(models.Servico.id == membros[0].servico_id).first()
        return bool(s and str(s.categoria or "").lower() == "combo")
    return False


def _planejar(membros: List[models.Chamado], novos_ids: List[int]):
    """
    Decide o que acontece com cada chamado ativo para chegar em `novos_ids`.
    Retorna (plano, erro): plano = [(chamado, novo_servico_id | None=cancelar)].
    Serviços já concluídos precisam continuar na lista (já foram realizados).
    O chamado em atendimento nunca é cancelado: é trocado se o serviço dele saiu.
    """
    restantes = list(novos_ids)
    for m in membros:
        if str(m.status or "").lower() == CONCLUIDO:
            if m.servico_id not in restantes:
                return None, "Um serviço já concluído não pode sair do atendimento."
            restantes.remove(m.servico_id)

    ativos = [m for m in membros if str(m.status or "").lower() in STATUS_ATIVOS]
    ativos.sort(key=lambda m: (0 if str(m.status or "").lower() == EM_ATENDIMENTO else 1, m.id))
    if not ativos:
        return None, "Este atendimento já foi finalizado."
    if len(restantes) > len(ativos):
        return None, "Não é possível adicionar serviços ao atendimento, apenas alterar os já agendados."
    if not restantes and any(str(m.status or "").lower() == EM_ATENDIMENTO for m in ativos):
        return None, "Selecione o serviço que está sendo realizado."

    decisao = {}
    for m in ativos:
        if m.servico_id in restantes:
            decisao[m.id] = m.servico_id
            restantes.remove(m.servico_id)
    for m in ativos:
        if m.id in decisao:
            continue
        decisao[m.id] = restantes.pop(0) if restantes else None

    return [(m, decisao[m.id]) for m in ativos], None


def _serializar(db: Session, alt: models.AlteracaoServicoAtendimento) -> dict:
    return {
        "id": alt.id,
        "chamado_id": alt.chamado_id,
        "grupo_id": alt.grupo_id,
        "status": alt.status,
        "servicos_originais": alt.servicos_originais,
        "servicos_novos": alt.servicos_novos,
        "valor_original": alt.valor_original,
        "valor_novo": alt.valor_novo,
        "mensagem": f"Seu atendimento foi alterado de {alt.servicos_originais} para {alt.servicos_novos}.",
        "criado_em": alt.criado_em.isoformat() + "Z" if alt.criado_em else None,
    }


def _pendente_do_atendimento(db: Session, chamado: models.Chamado):
    q = db.query(models.AlteracaoServicoAtendimento).filter(models.AlteracaoServicoAtendimento.status == "pendente")
    if chamado.grupo_id:
        q = q.filter(models.AlteracaoServicoAtendimento.grupo_id == chamado.grupo_id)
    else:
        q = q.filter(models.AlteracaoServicoAtendimento.chamado_id == chamado.id)
    return q.order_by(models.AlteracaoServicoAtendimento.id.desc()).first()


# ============================================================
# FREELANCER
# ============================================================

@router.get("/chamados/{chamado_id}/alteracao-servico")
def obter_alteracao_servico(
    chamado_id: int,
    db: Session = Depends(get_db),
    usuario=Depends(get_current_user),
):
    """Opções de serviço + pedido pendente (visão do freelancer do atendimento)."""
    chamado = db.query(models.Chamado).filter(models.Chamado.id == chamado_id).first()
    if not chamado:
        raise HTTPException(status_code=404, detail="Chamado não encontrado")
    if chamado.barbeiro_id != usuario.id:
        raise HTTPException(status_code=403, detail="Apenas o freelancer do atendimento")

    membros = _membros_grupo(db, chamado)
    servicos = db.query(models.Servico).filter(
        models.Servico.barbearia_id == chamado.barbearia_id,
        models.Servico.ativo == True,
    ).order_by(models.Servico.nome.asc()).all()
    concluidos = [m.servico_id for m in membros if str(m.status or "").lower() == CONCLUIDO]
    pendente = _pendente_do_atendimento(db, chamado)

    return {
        "pode_alterar": _tem_mais_de_um_servico(db, membros)
        and any(str(m.status or "").lower() in STATUS_ATIVOS for m in membros),
        "servicos_atuais_ids": [m.servico_id for m in membros],
        "servicos_atuais": _descricao(db, [m.servico_id for m in membros]),
        "servicos_concluidos_ids": concluidos,
        "max_servicos": len(membros),
        "opcoes": [
            {"id": s.id, "nome": s.nome, "valor": float(s.valor or 0), "duracao_minutos": s.duracao_minutos}
            for s in servicos
        ],
        "pendente": _serializar(db, pendente) if pendente else None,
    }


@router.post("/chamados/{chamado_id}/alteracao-servico")
def solicitar_alteracao_servico(
    chamado_id: int,
    dados: SolicitarAlteracaoRequest,
    db: Session = Depends(get_db),
    usuario=Depends(get_current_user),
):
    """Freelancer pede a alteração. Nada muda no atendimento até o cliente confirmar."""
    chamado = db.query(models.Chamado).filter(models.Chamado.id == chamado_id).first()
    if not chamado:
        raise HTTPException(status_code=404, detail="Chamado não encontrado")
    if chamado.barbeiro_id != usuario.id:
        raise HTTPException(status_code=403, detail="Apenas o freelancer do atendimento pode alterar o serviço")

    membros = _membros_grupo(db, chamado)
    if not _tem_mais_de_um_servico(db, membros):
        raise HTTPException(status_code=400, detail="A alteração só vale para atendimentos com mais de um serviço")

    novos_ids = [int(i) for i in dict.fromkeys(dados.servico_ids or [])]
    if not novos_ids:
        raise HTTPException(status_code=400, detail="Selecione ao menos um serviço")
    validos = {
        s.id for s in db.query(models.Servico).filter(
            models.Servico.id.in_(novos_ids),
            models.Servico.barbearia_id == chamado.barbearia_id,
        ).all()
    }
    if len(validos) != len(novos_ids):
        raise HTTPException(status_code=400, detail="Serviço inválido para esta barbearia")

    atuais_ids = [m.servico_id for m in membros]
    if sorted(atuais_ids) == sorted(novos_ids):
        raise HTTPException(status_code=400, detail="Selecione serviços diferentes dos atuais")

    plano, erro = _planejar(membros, novos_ids)
    if erro:
        raise HTTPException(status_code=400, detail=erro)

    # Um pedido por vez: um novo pedido substitui o anterior ainda sem resposta.
    anterior = _pendente_do_atendimento(db, chamado)
    if anterior:
        anterior.status = "expirada"
        anterior.respondido_em = datetime.utcnow()

    def _valor(ids):
        return round(sum(float(db.query(models.Servico).get(i).valor or 0) for i in ids), 2)

    alt = models.AlteracaoServicoAtendimento(
        chamado_id=chamado.id,
        grupo_id=chamado.grupo_id,
        cliente_id=chamado.cliente_id,
        barbeiro_id=usuario.id,
        servicos_originais=_descricao(db, atuais_ids),
        servicos_novos=_descricao(db, novos_ids),
        servicos_novos_ids=",".join(str(i) for i in novos_ids),
        valor_original=_valor(atuais_ids),
        valor_novo=_valor(novos_ids),
        status="pendente",
    )
    db.add(alt)
    db.flush()

    db.add(models.Notificacao(
        usuario_id=chamado.cliente_id,
        titulo="Alteração no atendimento",
        mensagem=f"Seu atendimento foi alterado de {alt.servicos_originais} para {alt.servicos_novos}. Confirme ou recuse.",
        tipo="alteracao_servico",
        referencia_id=chamado.id,
    ))
    db.commit()
    db.refresh(alt)
    return {"message": "Alteração enviada para o cliente confirmar", "alteracao": _serializar(db, alt)}


# ============================================================
# CLIENTE
# ============================================================

@router.get("/cliente/alteracoes-servico/pendentes")
def listar_alteracoes_pendentes_cliente(
    db: Session = Depends(get_db),
    usuario=Depends(get_current_user),
):
    alts = db.query(models.AlteracaoServicoAtendimento).filter(
        models.AlteracaoServicoAtendimento.cliente_id == usuario.id,
        models.AlteracaoServicoAtendimento.status == "pendente",
    ).order_by(models.AlteracaoServicoAtendimento.id.desc()).all()
    return [_serializar(db, a) for a in alts]


@router.post("/alteracoes-servico/{alteracao_id}/responder")
def responder_alteracao_servico(
    alteracao_id: int,
    dados: ResponderAlteracaoRequest,
    db: Session = Depends(get_db),
    usuario=Depends(get_current_user),
):
    alt = db.query(models.AlteracaoServicoAtendimento).filter(
        models.AlteracaoServicoAtendimento.id == alteracao_id
    ).first()
    if not alt:
        raise HTTPException(status_code=404, detail="Alteração não encontrada")
    if alt.cliente_id != usuario.id:
        raise HTTPException(status_code=403, detail="Apenas o cliente do atendimento pode responder")
    if alt.status != "pendente":
        raise HTTPException(status_code=400, detail="Esta alteração não está mais pendente")

    agora = datetime.utcnow()

    if not dados.confirmar:
        # Recusa: mantém serviços, combo, valor e taxa originais.
        alt.status = "recusada"
        alt.respondido_em = agora
        db.add(models.Notificacao(
            usuario_id=alt.barbeiro_id,
            titulo="Alteração recusada",
            mensagem=f"O cliente recusou a alteração para {alt.servicos_novos}. O atendimento segue como {alt.servicos_originais}.",
            tipo="alteracao_servico_recusada",
            referencia_id=alt.chamado_id,
        ))
        db.commit()
        return {"message": "Alteração recusada. O atendimento continua como agendado.", "alteracao": _serializar(db, alt)}

    chamado = db.query(models.Chamado).filter(models.Chamado.id == alt.chamado_id).first()
    membros = _membros_grupo(db, chamado) if chamado else []
    novos_ids = [int(x) for x in alt.servicos_novos_ids.split(",") if x]
    plano, erro = _planejar(membros, novos_ids) if chamado else (None, "Atendimento não encontrado")
    if erro:
        alt.status = "expirada"
        alt.respondido_em = agora
        db.commit()
        raise HTTPException(status_code=409, detail=f"Não foi possível aplicar a alteração: {erro}")

    # Aplica oficialmente.
    em_atendimento = None
    for membro, novo_servico_id in plano:
        if novo_servico_id is None:
            membro.status = CANCELADO
            membro.cancelado_em = agora
            membro.motivo_cancelamento = (
                f"Serviço removido na alteração confirmada pelo cliente ({alt.servicos_originais} -> {alt.servicos_novos})"
            )
            continue
        if novo_servico_id != membro.servico_id:
            dur_antiga = _duracao_servico_min(db, membro.servico_id)
            servico = db.query(models.Servico).filter(models.Servico.id == novo_servico_id).first()
            split = calcular_split_pagamento(servico.valor)
            membro.servico_id = novo_servico_id
            membro.valor_total = split["valor_total"]
            membro.comissao_plataforma = split["comissao_plataforma"]
            membro.valor_freelancer = split["valor_freelancer"]
            membro.valor_dono = split["valor_dono"]
            membro.valor_final = servico.valor
            if str(membro.status or "").lower() == EM_ATENDIMENTO and membro.data_hora_fim:
                # mantém pausas já aplicadas: só ajusta pela diferença de duração
                membro.data_hora_fim = membro.data_hora_fim + timedelta(
                    minutes=_duracao_servico_min(db, novo_servico_id) - dur_antiga
                )
        if str(membro.status or "").lower() == EM_ATENDIMENTO:
            em_atendimento = membro

    # Reescalona os que ainda vão acontecer (sequenciais, como no grupo original).
    pendentes = [m for m, sid in plano if sid is not None and str(m.status or "").lower() != EM_ATENDIMENTO]
    if pendentes:
        cursor = em_atendimento.data_hora_fim if em_atendimento and em_atendimento.data_hora_fim else pendentes[0].data_hora_inicio
        if cursor:
            for m in sorted(pendentes, key=lambda x: x.id):
                dur = _duracao_servico_min(db, m.servico_id)
                m.data_hora_inicio = cursor
                m.data_hora_fim = cursor + timedelta(minutes=dur)
                cursor = m.data_hora_fim

    db.flush()
    if em_atendimento:
        barbeiro = db.query(models.Usuario).filter(models.Usuario.id == em_atendimento.barbeiro_id).first()
        if barbeiro and barbeiro.ocupado_ate:
            barbeiro.ocupado_ate = _calcular_fim_grupo(db, em_atendimento)

    alt.status = "confirmada"
    alt.respondido_em = agora
    db.add(models.Notificacao(
        usuario_id=alt.barbeiro_id,
        titulo="Alteração confirmada",
        mensagem=f"O cliente confirmou: atendimento alterado de {alt.servicos_originais} para {alt.servicos_novos}.",
        tipo="alteracao_servico_confirmada",
        referencia_id=alt.chamado_id,
    ))
    db.commit()
    return {"message": "Alteração confirmada", "alteracao": _serializar(db, alt)}
