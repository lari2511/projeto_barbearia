"""
Interesse de clientes em atendimento - BarberMove.

Quando um cliente abre o perfil de uma barbearia sem nenhuma cadeira
disponivel, registra 1 demonstracao de interesse (somente contagem
agregada). Nao cria solicitacao, chamado ou qualquer acao real - o dono
so fica sabendo pelo sino de notificacoes (ver routes_notificacoes.py),
nunca por um painel de estatisticas separado.
"""

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import and_, or_
from sqlalchemy.orm import Session

from app.database import get_db
from app.firebase_config import enviar_notificacao_novo_chamado
from app.models import Barbearia, Cadeira, InteresseAtendimento, Notificacao, StatusCadeira, Usuario
from app.pagamento_diario import freelancer_bloqueado
from app.routes import get_current_user
from app.routes_notificacoes import criar_ou_atualizar_notificacao_interesse

router = APIRouter(prefix="/api/v1/interesse-atendimento", tags=["Interesse de Atendimento"])


@router.post("/freelancer/{freelancer_id}")
def registrar_interesse_em_freelancer(
    freelancer_id: int,
    db: Session = Depends(get_db),
    usuario_atual: Usuario = Depends(get_current_user),
):
    """
    Cliente abriu o perfil de um freelancer com taxa pendente: avisa o freelancer pelo sino.
    So informativo, nunca cria chamado. No maximo um aviso por cliente por dia.
    """
    if usuario_atual.tipo != "cliente":
        return {"registrado": False}

    freelancer = db.query(Usuario).filter(Usuario.id == freelancer_id, Usuario.tipo == "barbeiro").first()
    if not freelancer:
        raise HTTPException(status_code=404, detail="Freelancer nao encontrado")
    if not freelancer_bloqueado(db, freelancer.id):
        return {"registrado": False}

    inicio_dia = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    ja_avisado = db.query(Notificacao).filter(
        Notificacao.usuario_id == freelancer.id,
        Notificacao.tipo == "interesse_cliente",
        Notificacao.referencia_id == usuario_atual.id,
        Notificacao.criado_em >= inicio_dia,
    ).first()
    if ja_avisado:
        return {"registrado": False}

    titulo = "Um cliente quer marcar um corte com você"
    mensagem = "Um cliente demonstrou interesse em marcar um corte. Quite a taxa pendente para voltar a receber chamados."
    db.add(Notificacao(
        usuario_id=freelancer.id,
        titulo=titulo,
        mensagem=mensagem,
        tipo="interesse_cliente",
        referencia_id=usuario_atual.id,
    ))
    db.commit()

    if freelancer.device_token:
        enviar_notificacao_novo_chamado(
            token_dispositivo=freelancer.device_token,
            nome_cliente="BarberMove",
            nome_servico="Interesse de cliente",
            title=titulo,
            body=mensagem,
        )
    return {"registrado": True}


@router.post("/{barbearia_id}")
def registrar_interesse(
    barbearia_id: int,
    db: Session = Depends(get_db),
    usuario_atual: Usuario = Depends(get_current_user),
):
    """
    Registra 1 demonstracao de interesse do cliente numa barbearia, somente
    se ela nao tiver nenhuma cadeira disponivel agora (verificado aqui, nunca
    confiando no que o app enviar).
    """
    if usuario_atual.tipo != "cliente":
        return {"registrado": False}

    barbearia = db.query(Barbearia).filter(Barbearia.id == barbearia_id).first()
    if not barbearia:
        raise HTTPException(status_code=404, detail="Barbearia nao encontrada")

    tem_cadeira_disponivel = (
        db.query(Cadeira)
        .filter(
            Cadeira.barbearia_id == barbearia.id,
            or_(
                Cadeira.status == StatusCadeira.DISPONIVEL,
                and_(
                    Cadeira.status == StatusCadeira.OCUPADA,
                    Cadeira.freelancer_id.is_(None),
                ),
            ),
        )
        .first()
        is not None
    )
    if tem_cadeira_disponivel:
        return {"registrado": False}

    db.add(InteresseAtendimento(barbearia_id=barbearia.id, cliente_id=usuario_atual.id))
    db.commit()

    inicio_dia = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    total_hoje = db.query(InteresseAtendimento).filter(
        InteresseAtendimento.barbearia_id == barbearia.id,
        InteresseAtendimento.criado_em >= inicio_dia,
    ).count()

    criar_ou_atualizar_notificacao_interesse(barbearia.usuario_id, total_hoje, db=db)

    return {"registrado": True, "total_hoje": total_hoje}
