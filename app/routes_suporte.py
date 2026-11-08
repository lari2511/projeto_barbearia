"""
Atendimento por chat entre usuários (cliente, freelancer, proprietário) e o ADM.

Cada usuário tem uma única conversa permanente. As rotas do usuário nunca recebem id de
conversa (sempre resolvem pelo token), e o perfil vem de `usuario.tipo`, nunca do cliente HTTP.
As rotas do painel exigem tipo "admin" (verificar_somente_admin).
"""

from datetime import datetime
from typing import Literal, Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from pydantic import BaseModel, field_validator
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.admin_routes import verificar_somente_admin
from app.database import get_db
from app.models import Barbearia, ChamadoSuporte, MensagemSuporte, Notificacao, Usuario
from app.realtime import broadcast_event
from app.routes import get_current_user

router_usuario = APIRouter(prefix="/api/v1/suporte", tags=["Suporte"])
router_admin = APIRouter(prefix="/admin/api/suporte", tags=["Suporte (ADM)"])

PERFIS_SUPORTE = ("cliente", "barbeiro", "barbearia")
REMETENTE_ADM = "admin"
TAMANHO_MAXIMO_MENSAGEM = 2000
TIPO_NOTIFICACAO = "suporte_resposta"


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


def _usuario_com_perfil(usuario: Usuario = Depends(get_current_user)) -> Usuario:
    if usuario.tipo not in PERFIS_SUPORTE:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Perfil sem acesso ao chat de suporte",
        )
    return usuario


def _iso(valor: Optional[datetime]) -> Optional[str]:
    return valor.isoformat() if valor else None


def _serializar_mensagem(m: MensagemSuporte) -> dict:
    return {
        "id": m.id,
        "do_adm": m.remetente_tipo == REMETENTE_ADM,
        "remetente_tipo": m.remetente_tipo,
        "mensagem": m.mensagem,
        "lida": m.lida,
        "lida_em": _iso(m.lida_em),
        "criado_em": _iso(m.criado_em),
    }


def _mensagens_da_conversa(db: Session, chamado_id: int) -> list:
    mensagens = (
        db.query(MensagemSuporte)
        .filter(MensagemSuporte.chamado_suporte_id == chamado_id)
        .order_by(MensagemSuporte.criado_em.asc(), MensagemSuporte.id.asc())
        .all()
    )
    return [_serializar_mensagem(m) for m in mensagens]


def _adicionar_mensagem(
    db: Session,
    chamado: ChamadoSuporte,
    remetente: Usuario,
    remetente_tipo: str,
    texto: str,
) -> MensagemSuporte:
    agora = datetime.utcnow()
    mensagem = MensagemSuporte(
        chamado_suporte_id=chamado.id,
        remetente_id=remetente.id,
        remetente_tipo=remetente_tipo,
        mensagem=texto,
        criado_em=agora,
    )
    db.add(mensagem)
    chamado.ultima_mensagem_em = agora
    return mensagem


def _obter_ou_criar_conversa(db: Session, usuario: Usuario) -> ChamadoSuporte:
    chamado = db.query(ChamadoSuporte).filter(ChamadoSuporte.usuario_id == usuario.id).first()
    if chamado:
        return chamado
    try:
        chamado = ChamadoSuporte(usuario_id=usuario.id, tipo_perfil=usuario.tipo)
        db.add(chamado)
        db.flush()
        return chamado
    except IntegrityError:
        db.rollback()
        return db.query(ChamadoSuporte).filter(ChamadoSuporte.usuario_id == usuario.id).one()


async def _avisar(destinatarios: list, chamado_id: int, mensagem_id: int) -> None:
    for destinatario_id in destinatarios:
        await broadcast_event(
            "suporte_mensagem",
            destinatario_id=destinatario_id,
            chamado_suporte_id=chamado_id,
            mensagem_id=mensagem_id,
        )


@router_usuario.get("/minha-conversa")
def minha_conversa(db: Session = Depends(get_db), usuario: Usuario = Depends(_usuario_com_perfil)):
    chamado = db.query(ChamadoSuporte).filter(ChamadoSuporte.usuario_id == usuario.id).first()
    return {
        "chamado_id": chamado.id if chamado else None,
        "mensagens": _mensagens_da_conversa(db, chamado.id) if chamado else [],
    }


@router_usuario.get("/nao-lidas")
def nao_lidas_usuario(db: Session = Depends(get_db), usuario: Usuario = Depends(_usuario_com_perfil)):
    total = (
        db.query(func.count(MensagemSuporte.id))
        .join(ChamadoSuporte, MensagemSuporte.chamado_suporte_id == ChamadoSuporte.id)
        .filter(
            ChamadoSuporte.usuario_id == usuario.id,
            MensagemSuporte.remetente_tipo == REMETENTE_ADM,
            MensagemSuporte.lida.is_(False),
        )
        .scalar()
    )
    return {"nao_lidas": total or 0}


@router_usuario.post("/mensagens", status_code=status.HTTP_201_CREATED)
def enviar_mensagem_usuario(
    dados: EnviarMensagem,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(_usuario_com_perfil),
):
    chamado = _obter_ou_criar_conversa(db, usuario)
    mensagem = _adicionar_mensagem(db, chamado, usuario, usuario.tipo, dados.mensagem)
    db.commit()
    db.refresh(mensagem)

    admins = [linha.id for linha in db.query(Usuario.id).filter(Usuario.tipo == "admin").all()]
    background_tasks.add_task(_avisar, admins, chamado.id, mensagem.id)
    return _serializar_mensagem(mensagem)


@router_usuario.post("/marcar-lidas")
def marcar_lidas_usuario(db: Session = Depends(get_db), usuario: Usuario = Depends(_usuario_com_perfil)):
    chamado = db.query(ChamadoSuporte).filter(ChamadoSuporte.usuario_id == usuario.id).first()
    if not chamado:
        return {"marcadas": 0}
    marcadas = (
        db.query(MensagemSuporte)
        .filter(
            MensagemSuporte.chamado_suporte_id == chamado.id,
            MensagemSuporte.remetente_tipo == REMETENTE_ADM,
            MensagemSuporte.lida.is_(False),
        )
        .update({"lida": True, "lida_em": datetime.utcnow()}, synchronize_session=False)
    )
    (
        db.query(Notificacao)
        .filter(
            Notificacao.usuario_id == usuario.id,
            Notificacao.tipo == TIPO_NOTIFICACAO,
            Notificacao.lido.is_(False),
        )
        .update({"lido": True}, synchronize_session=False)
    )
    db.commit()
    return {"marcadas": marcadas}


def _conversa_ou_404(db: Session, chamado_id: int) -> ChamadoSuporte:
    chamado = db.query(ChamadoSuporte).filter(ChamadoSuporte.id == chamado_id).first()
    if not chamado:
        raise HTTPException(status_code=404, detail="Conversa não encontrada")
    return chamado


def _nao_lidas_por_conversa(db: Session) -> dict:
    linhas = (
        db.query(MensagemSuporte.chamado_suporte_id, func.count(MensagemSuporte.id))
        .filter(MensagemSuporte.remetente_tipo != REMETENTE_ADM, MensagemSuporte.lida.is_(False))
        .group_by(MensagemSuporte.chamado_suporte_id)
        .all()
    )
    return dict(linhas)


def _nomes_barbearias(db: Session, usuario_ids: list) -> dict:
    if not usuario_ids:
        return {}
    linhas = (
        db.query(Barbearia.usuario_id, Barbearia.nome)
        .filter(Barbearia.usuario_id.in_(usuario_ids))
        .all()
    )
    return dict(linhas)


@router_admin.get("/resumo")
def resumo_suporte(db: Session = Depends(get_db), admin: Usuario = Depends(verificar_somente_admin)):
    setores = {
        perfil: {"conversas": 0, "conversas_nao_lidas": 0, "mensagens_nao_lidas": 0}
        for perfil in PERFIS_SUPORTE
    }
    nao_lidas = _nao_lidas_por_conversa(db)
    for chamado_id, perfil in db.query(ChamadoSuporte.id, ChamadoSuporte.tipo_perfil).all():
        setor = setores.get(perfil)
        if setor is None:
            continue
        setor["conversas"] += 1
        qtd = nao_lidas.get(chamado_id, 0)
        if qtd:
            setor["conversas_nao_lidas"] += 1
            setor["mensagens_nao_lidas"] += qtd
    return {
        "setores": setores,
        "total_nao_lidas": sum(s["mensagens_nao_lidas"] for s in setores.values()),
    }


@router_admin.get("/conversas")
def listar_conversas(
    tipo: Literal["cliente", "barbeiro", "barbearia"],
    db: Session = Depends(get_db),
    admin: Usuario = Depends(verificar_somente_admin),
):
    ultima_mensagem = (
        select(MensagemSuporte.mensagem)
        .where(MensagemSuporte.chamado_suporte_id == ChamadoSuporte.id)
        .order_by(MensagemSuporte.criado_em.desc(), MensagemSuporte.id.desc())
        .limit(1)
        .correlate(ChamadoSuporte)
        .scalar_subquery()
    )
    linhas = (
        db.query(ChamadoSuporte, Usuario, ultima_mensagem)
        .join(Usuario, ChamadoSuporte.usuario_id == Usuario.id)
        .filter(ChamadoSuporte.tipo_perfil == tipo)
        .all()
    )
    nao_lidas = _nao_lidas_por_conversa(db)
    barbearias = _nomes_barbearias(db, [u.id for _, u, _ in linhas]) if tipo == "barbearia" else {}
    itens = [
        {
            "id": chamado.id,
            "usuario_id": usuario.id,
            "nome": usuario.nome,
            "email": usuario.email,
            "nome_barbearia": barbearias.get(usuario.id),
            "tipo_perfil": chamado.tipo_perfil,
            "nao_lidas": nao_lidas.get(chamado.id, 0),
            "ultima_mensagem": ultima,
            "ultima_mensagem_em": _iso(chamado.ultima_mensagem_em),
        }
        for chamado, usuario, ultima in linhas
    ]
    itens.sort(key=lambda i: i["ultima_mensagem_em"] or "", reverse=True)
    itens.sort(key=lambda i: i["nao_lidas"] == 0)
    return itens


@router_admin.get("/conversas/{chamado_id}")
def obter_conversa(
    chamado_id: int,
    db: Session = Depends(get_db),
    admin: Usuario = Depends(verificar_somente_admin),
):
    chamado = _conversa_ou_404(db, chamado_id)
    usuario = chamado.usuario
    return {
        "id": chamado.id,
        "usuario_id": usuario.id,
        "nome": usuario.nome,
        "email": usuario.email,
        "telefone": usuario.telefone,
        "nome_barbearia": _nomes_barbearias(db, [usuario.id]).get(usuario.id) if chamado.tipo_perfil == "barbearia" else None,
        "tipo_perfil": chamado.tipo_perfil,
        "mensagens": _mensagens_da_conversa(db, chamado.id),
    }


@router_admin.post("/conversas/{chamado_id}/mensagens", status_code=status.HTTP_201_CREATED)
def responder_conversa(
    chamado_id: int,
    dados: EnviarMensagem,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    admin: Usuario = Depends(verificar_somente_admin),
):
    chamado = _conversa_ou_404(db, chamado_id)
    mensagem = _adicionar_mensagem(db, chamado, admin, REMETENTE_ADM, dados.mensagem)
    ja_avisado = (
        db.query(Notificacao.id)
        .filter(
            Notificacao.usuario_id == chamado.usuario_id,
            Notificacao.tipo == TIPO_NOTIFICACAO,
            Notificacao.lido.is_(False),
        )
        .first()
    )
    if not ja_avisado:
        db.add(
            Notificacao(
                usuario_id=chamado.usuario_id,
                titulo="Resposta do ADM",
                mensagem="O ADM respondeu sua mensagem. Abra Perfil > Falar com o ADM.",
                tipo=TIPO_NOTIFICACAO,
                referencia_id=chamado.id,
            )
        )
    db.commit()
    db.refresh(mensagem)

    background_tasks.add_task(_avisar, [chamado.usuario_id], chamado.id, mensagem.id)
    return _serializar_mensagem(mensagem)


@router_admin.post("/conversas/{chamado_id}/marcar-lidas")
def marcar_lidas_admin(
    chamado_id: int,
    db: Session = Depends(get_db),
    admin: Usuario = Depends(verificar_somente_admin),
):
    chamado = _conversa_ou_404(db, chamado_id)
    marcadas = (
        db.query(MensagemSuporte)
        .filter(
            MensagemSuporte.chamado_suporte_id == chamado.id,
            MensagemSuporte.remetente_tipo != REMETENTE_ADM,
            MensagemSuporte.lida.is_(False),
        )
        .update({"lida": True, "lida_em": datetime.utcnow()}, synchronize_session=False)
    )
    db.commit()
    return {"marcadas": marcadas}

