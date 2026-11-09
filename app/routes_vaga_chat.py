"""
Chat privado da vaga de cadeira: só o dono da barbearia e o freelancer escolhido.

Não tem relação com o chat dos chamados (MensagemChat / routes_extras.py). O acesso é sempre
resolvido pelo token, e o aviso em tempo real leva só os ids, porque o texto é privado.
"""

from datetime import datetime

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from pydantic import BaseModel, field_validator
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Barbearia, CadeiraAcionada, MensagemVaga, Notificacao, Usuario
from app.realtime import broadcast_event
from app.routes import get_current_user
from app.vagas import (
    STATUS_AGUARDANDO_DESBLOQUEIO,
    STATUS_OCUPADA,
    cadeira_esta_bloqueada,
    vagas_ativas,
)

router = APIRouter(prefix="/api/v1/vagas", tags=["Chat da vaga"])

TAMANHO_MAXIMO_MENSAGEM = 2000
TIPO_NOTIFICACAO = "vaga_chat"
STATUS_COM_CHAT_ABERTO = (STATUS_AGUARDANDO_DESBLOQUEIO, STATUS_OCUPADA)


class EnviarMensagem(BaseModel):
    mensagem: str

    @field_validator("mensagem")
    @classmethod
    def validar_mensagem(cls, valor: str) -> str:
        valor = valor.strip()
        if not valor:
            raise ValueError("Escreva uma mensagem")
        if len(valor) > TAMANHO_MAXIMO_MENSAGEM:
            raise ValueError(f"A mensagem pode ter no máximo {TAMANHO_MAXIMO_MENSAGEM} caracteres")
        return valor


def _vaga_da_conversa(db: Session, vaga_id: int, usuario: Usuario) -> tuple:
    """Devolve (vaga, id do outro participante). Antes da escolha a conversa não existe."""
    vaga = db.query(CadeiraAcionada).filter(CadeiraAcionada.id == vaga_id).first()
    if not vaga:
        raise HTTPException(status_code=404, detail="Vaga não encontrada")

    barbearia = db.query(Barbearia).filter(Barbearia.id == vaga.barbearia_id).first()
    dono_id = barbearia.usuario_id if barbearia else None
    if usuario.id not in (dono_id, vaga.barbeiro_id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Você não participa desta conversa")
    if not vaga.barbeiro_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="O chat é liberado quando o freelancer é escolhido")

    return vaga, (vaga.barbeiro_id if usuario.id == dono_id else dono_id)


def _serializar(mensagem: MensagemVaga, usuario_id: int) -> dict:
    return {
        "id": mensagem.id,
        "vaga_id": mensagem.vaga_id,
        "minha": mensagem.remetente_id == usuario_id,
        "mensagem": mensagem.mensagem,
        "lida": mensagem.lida,
        "criado_em": mensagem.criado_em.isoformat() if mensagem.criado_em else None,
    }


def nao_lidas_por_vaga(db: Session, vaga_ids: list, usuario_id: int) -> dict:
    if not vaga_ids:
        return {}
    linhas = (
        db.query(MensagemVaga.vaga_id, func.count(MensagemVaga.id))
        .filter(
            MensagemVaga.vaga_id.in_(vaga_ids),
            MensagemVaga.remetente_id != usuario_id,
            MensagemVaga.lida.is_(False),
        )
        .group_by(MensagemVaga.vaga_id)
        .all()
    )
    return dict(linhas)


@router.get("/minhas-selecoes")
def minhas_selecoes(db: Session = Depends(get_db), usuario: Usuario = Depends(get_current_user)):
    """Vagas em andamento para as quais este freelancer foi escolhido."""
    if usuario.tipo != "barbeiro":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Apenas freelancers têm vagas selecionadas")

    barbearia_ids = [
        linha[0]
        for linha in db.query(CadeiraAcionada.barbearia_id)
        .filter(
            CadeiraAcionada.barbeiro_id == usuario.id,
            CadeiraAcionada.status.in_(STATUS_COM_CHAT_ABERTO),
        )
        .distinct()
        .all()
    ]
    vagas = [
        vaga
        for barbearia_id in barbearia_ids
        for vaga in vagas_ativas(db, barbearia_id)
        if vaga.barbeiro_id == usuario.id
    ]
    nao_lidas = nao_lidas_por_vaga(db, [vaga.id for vaga in vagas], usuario.id)
    return [
        {
            "id": vaga.id,
            "barbearia_id": vaga.barbearia_id,
            "barbearia_nome": vaga.barbearia.nome if vaga.barbearia else "Barbearia",
            "status": vaga.status,
            "cadeira_bloqueada": cadeira_esta_bloqueada(vaga.cadeira),
            "percentual_freelancer": vaga.percentual_freelancer,
            "nao_lidas": nao_lidas.get(vaga.id, 0),
        }
        for vaga in vagas
    ]


@router.get("/{vaga_id}/chat")
def conversa_da_vaga(vaga_id: int, db: Session = Depends(get_db), usuario: Usuario = Depends(get_current_user)):
    vaga, _ = _vaga_da_conversa(db, vaga_id, usuario)
    mensagens = (
        db.query(MensagemVaga)
        .filter(MensagemVaga.vaga_id == vaga.id)
        .order_by(MensagemVaga.criado_em.asc(), MensagemVaga.id.asc())
        .all()
    )
    return {
        "vaga_id": vaga.id,
        "aberta": vaga.status in STATUS_COM_CHAT_ABERTO,
        "mensagens": [_serializar(m, usuario.id) for m in mensagens],
    }


@router.post("/{vaga_id}/chat", status_code=status.HTTP_201_CREATED)
def enviar_mensagem_da_vaga(
    vaga_id: int,
    dados: EnviarMensagem,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(get_current_user),
):
    vaga, destinatario_id = _vaga_da_conversa(db, vaga_id, usuario)
    if vaga.status not in STATUS_COM_CHAT_ABERTO:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Esta vaga foi encerrada e a conversa não aceita novas mensagens")

    mensagem = MensagemVaga(vaga_id=vaga.id, remetente_id=usuario.id, mensagem=dados.mensagem)
    db.add(mensagem)

    # Uma notificação por conversa: o sino não acumula uma linha por mensagem.
    ja_avisado = (
        db.query(Notificacao.id)
        .filter(
            Notificacao.usuario_id == destinatario_id,
            Notificacao.tipo == TIPO_NOTIFICACAO,
            Notificacao.referencia_id == vaga.id,
            Notificacao.lido.is_(False),
        )
        .first()
    )
    if destinatario_id and not ja_avisado:
        db.add(Notificacao(
            usuario_id=destinatario_id,
            titulo="Nova mensagem sobre a vaga 💬",
            mensagem=f"{usuario.nome} enviou uma mensagem no chat da vaga.",
            tipo=TIPO_NOTIFICACAO,
            referencia_id=vaga.id,
        ))

    db.commit()
    db.refresh(mensagem)

    if destinatario_id:
        background_tasks.add_task(
            broadcast_event,
            "vaga_chat_mensagem",
            destinatario_id=destinatario_id,
            vaga_id=vaga.id,
            mensagem_id=mensagem.id,
        )
    return _serializar(mensagem, usuario.id)


@router.post("/{vaga_id}/chat/marcar-lidas")
def marcar_lidas(vaga_id: int, db: Session = Depends(get_db), usuario: Usuario = Depends(get_current_user)):
    vaga, _ = _vaga_da_conversa(db, vaga_id, usuario)
    marcadas = (
        db.query(MensagemVaga)
        .filter(
            MensagemVaga.vaga_id == vaga.id,
            MensagemVaga.remetente_id != usuario.id,
            MensagemVaga.lida.is_(False),
        )
        .update({"lida": True, "lida_em": datetime.utcnow()}, synchronize_session=False)
    )
    (
        db.query(Notificacao)
        .filter(
            Notificacao.usuario_id == usuario.id,
            Notificacao.tipo == TIPO_NOTIFICACAO,
            Notificacao.referencia_id == vaga.id,
            Notificacao.lido.is_(False),
        )
        .update({"lido": True}, synchronize_session=False)
    )
    db.commit()
    return {"marcadas": marcadas}
