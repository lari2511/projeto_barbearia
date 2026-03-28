"""
Rotas para gerenciar notificações push
Sistema de notificações em tempo real para barbeiros quando há novos chamados
"""

from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.orm import Session
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr

from app.database import get_db
from app.models import Usuario, Chamado, Notificacao
from app.routes import get_current_user

router = APIRouter(prefix="/api/v1/notificacoes", tags=["Notificações"])

# ============================================================================
# SCHEMAS
# ============================================================================

class NotificacaoResponse(BaseModel):
    id: int
    titulo: str
    mensagem: str
    tipo: str  # "novo_chamado", "chamado_aceito", "chamado_recusado", etc
    lido: bool
    criado_em: datetime
    
    class Config:
        from_attributes = True

class CriarNotificacaoRequest(BaseModel):
    usuario_id: int
    titulo: str
    mensagem: str
    tipo: str
    referencia_id: Optional[int] = None  # chamado_id, agendamento_id, etc

# ============================================================================
# ENDPOINTS
# ============================================================================

@router.get("/", response_model=list[NotificacaoResponse])
def listar_notificacoes(
    nao_lidas_apenas: bool = False,
    limite: int = 20,
    db: Session = Depends(get_db),
    usuario = Depends(get_current_user)
):
    """Lista notificações do usuário"""
    query = db.query(Notificacao).filter(Notificacao.usuario_id == usuario.id)
    
    if nao_lidas_apenas:
        query = query.filter(Notificacao.lido == False)
    
    notificacoes = query.order_by(Notificacao.criado_em.desc()).limit(limite).all()
    return notificacoes

@router.post("/{notificacao_id}/marcar-lida")
def marcar_notificacao_lida(
    notificacao_id: int,
    db: Session = Depends(get_db),
    usuario = Depends(get_current_user)
):
    """Marca uma notificação como lida"""
    notificacao = db.query(Notificacao).filter(
        Notificacao.id == notificacao_id,
        Notificacao.usuario_id == usuario.id
    ).first()
    
    if not notificacao:
        raise HTTPException(status_code=404, detail="Notificação não encontrada")
    
    notificacao.lido = True
    db.commit()
    
    return {"status": "ok"}

@router.post("/marcar-todas-lidas")
def marcar_todas_lidas(
    db: Session = Depends(get_db),
    usuario = Depends(get_current_user)
):
    """Marca todas as notificações como lidas"""
    db.query(Notificacao).filter(
        Notificacao.usuario_id == usuario.id,
        Notificacao.lido == False
    ).update({Notificacao.lido: True})
    
    db.commit()
    return {"status": "ok"}

@router.delete("/{notificacao_id}")
def deletar_notificacao(
    notificacao_id: int,
    db: Session = Depends(get_db),
    usuario = Depends(get_current_user)
):
    """Deleta uma notificação"""
    notificacao = db.query(Notificacao).filter(
        Notificacao.id == notificacao_id,
        Notificacao.usuario_id == usuario.id
    ).first()
    
    if not notificacao:
        raise HTTPException(status_code=404, detail="Notificação não encontrada")
    
    db.delete(notificacao)
    db.commit()
    
    return {"status": "ok"}

@router.get("/nao-lidas/count")
def contar_nao_lidas(
    db: Session = Depends(get_db),
    usuario = Depends(get_current_user)
):
    """Conta notificações não lidas"""
    count = db.query(Notificacao).filter(
        Notificacao.usuario_id == usuario.id,
        Notificacao.lido == False
    ).count()
    
    return {"nao_lidas": count}

# ============================================================================
# FUNÇÕES AUXILIARES PARA CRIAR NOTIFICAÇÕES
# ============================================================================

def criar_notificacao_novo_chamado(
    barbeiro_id: int,
    chamado_id: int,
    cliente_nome: str,
    servico_nome: str,
    db: Session = None
):
    """Cria notificação quando um novo chamado é feito"""
    if db is None:
        from app.database import SessionLocal
        db = SessionLocal()
    
    notif = Notificacao(
        usuario_id=barbeiro_id,
        titulo="Novo Chamado! 📞",
        mensagem=f"{cliente_nome} pediu {servico_nome}",
        tipo="novo_chamado",
        referencia_id=chamado_id
    )
    db.add(notif)
    db.commit()
    return notif

def criar_notificacao_chamado_aceito(
    cliente_id: int,
    chamado_id: int,
    barbeiro_nome: str,
    db: Session = None
):
    """Cria notificação quando barbeiro aceita chamado"""
    if db is None:
        from app.database import SessionLocal
        db = SessionLocal()
    
    notif = Notificacao(
        usuario_id=cliente_id,
        titulo="Chamado Aceito! ✅",
        mensagem=f"{barbeiro_nome} aceitou seu agendamento",
        tipo="chamado_aceito",
        referencia_id=chamado_id
    )
    db.add(notif)
    db.commit()
    return notif

def criar_notificacao_chamado_rejeitado(
    cliente_id: int,
    chamado_id: int,
    barbeiro_nome: str,
    db: Session = None
):
    """Cria notificação quando barbeiro rejeita chamado"""
    if db is None:
        from app.database import SessionLocal
        db = SessionLocal()
    
    notif = Notificacao(
        usuario_id=cliente_id,
        titulo="Chamado Rejeitado",
        mensagem=f"{barbeiro_nome} rejeitou seu agendamento",
        tipo="chamado_rejeitado",
        referencia_id=chamado_id
    )
    db.add(notif)
    db.commit()
    return notif

def criar_notificacao_perfil_aprovado(
    usuario_id: int,
    db: Session = None
):
    """Cria notificação quando perfil é aprovado"""
    if db is None:
        from app.database import SessionLocal
        db = SessionLocal()
    
    notif = Notificacao(
        usuario_id=usuario_id,
        titulo="Perfil Aprovado! 🎉",
        mensagem="Sua conta foi aprovada e está pronta para usar",
        tipo="perfil_aprovado",
        referencia_id=usuario_id
    )
    db.add(notif)
    db.commit()
    return notif
