"""
Sistema de Aprovações Bidirecional
- Barbeiro aprova o agendamento
- Barbearia (dono) aprova o agendamento  
- Só após ambos aprovarem, o status muda para CONFIRMADO
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from jose import JWTError, jwt
from . import models, schemas, database
from .database import get_db
from .dependencies import verificar_barbearia_ativa
from fastapi.security import OAuth2PasswordBearer
import os
from dotenv import load_dotenv

load_dotenv()

router = APIRouter()

# Configurações de JWT
SECRET_KEY = os.getenv("SECRET_KEY", "INSEGURO_MUDE_ISSO_AGORA")
ALGORITHM = "HS256"
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/login/cliente/")

def verify_token(token: str) -> dict:
    """Verifica e decodifica o token JWT"""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        sub: str = payload.get("sub")
        if sub is None:
            raise HTTPException(status_code=401, detail="Token inválido")
        return payload
    except JWTError:
        raise HTTPException(status_code=401, detail="Token inválido ou expirado")

@router.post("/chamados/{chamado_id}/aprovacao-barbeiro")
def aprovar_como_barbeiro(chamado_id: int, db: Session = Depends(get_db), token: str = Depends(oauth2_scheme)):
    """
    Barbeiro aprova o agendamento
    """
    # Obter ID do barbeiro do token
    try:
        payload = verify_token(token)
        barbeiro_id = int(payload.get("sub"))
    except:
        raise HTTPException(status_code=401, detail="Token inválido")
    
    # Buscar chamado
    chamado = db.query(models.Chamado).filter(models.Chamado.id == chamado_id).first()
    if not chamado:
        raise HTTPException(status_code=404, detail="Agendamento não encontrado")
    
    # Verificar se o usuário é o barbeiro designado
    if chamado.barbeiro_id != barbeiro_id:
        raise HTTPException(status_code=403, detail="Apenas o barbeiro designado pode aprovar")
    
    # Marcar como aprovado pelo barbeiro
    chamado.aprovado_barbeiro = True
    chamado.aprovado_barbeiro_em = datetime.utcnow()
    
    # Se ambos aprovaram, mudar status para CONFIRMADO e bloquear cadeira
    if chamado.aprovado_barbearia:
        chamado.status = models.StatusAgendamento.CONFIRMADO
        
        # Bloquear a cadeira para este chamado
        cadeira = db.query(models.Cadeira).filter(
            models.Cadeira.barbearia_id == chamado.barbearia_id,
            models.Cadeira.status == models.StatusCadeira.DISPONIVEL
        ).first()
        
        if cadeira:
            cadeira.status = models.StatusCadeira.BLOQUEADA
            cadeira.chamado_id = chamado.id
    
    db.commit()
    db.refresh(chamado)
    
    return {
        "status": "Barbeiro aprovou com sucesso",
        "chamado_id": chamado.id,
        "aprovado_barbeiro": chamado.aprovado_barbeiro,
        "aprovado_barbearia": chamado.aprovado_barbearia,
        "status_chamado": chamado.status
    }

@router.post("/chamados/{chamado_id}/aprovacao-barbearia")
def aprovar_como_barbearia(chamado_id: int, db: Session = Depends(get_db), token: str = Depends(oauth2_scheme)):
    """
    Dono da barbearia aprova o agendamento
    """
    # Obter ID do usuário do token
    try:
        payload = verify_token(token)
        usuario_id = int(payload.get("sub"))
    except:
        raise HTTPException(status_code=401, detail="Token inválido")
    
    # Buscar chamado
    chamado = db.query(models.Chamado).filter(models.Chamado.id == chamado_id).first()
    if not chamado:
        raise HTTPException(status_code=404, detail="Agendamento não encontrado")
    
    # Verificar se o usuário é o dono da barbearia
    barbearia = db.query(models.Barbearia).filter(
        models.Barbearia.id == chamado.barbearia_id
    ).first()
    
    if not barbearia or barbearia.usuario_id != usuario_id:
        raise HTTPException(status_code=403, detail="Apenas o dono da barbearia pode aprovar")
    
    # Marcar como aprovado pela barbearia
    chamado.aprovado_barbearia = True
    chamado.aprovado_barbearia_em = datetime.utcnow()
    
    # Se ambos aprovaram, mudar status para CONFIRMADO e bloquear cadeira
    if chamado.aprovado_barbeiro:
        chamado.status = models.StatusAgendamento.CONFIRMADO
        
        # Bloquear a cadeira para este chamado
        cadeira = db.query(models.Cadeira).filter(
            models.Cadeira.barbearia_id == chamado.barbearia_id,
            models.Cadeira.status == models.StatusCadeira.DISPONIVEL
        ).first()
        
        if cadeira:
            cadeira.status = models.StatusCadeira.BLOQUEADA
            cadeira.chamado_id = chamado.id
    
    db.commit()
    db.refresh(chamado)
    
    return {
        "status": "Barbearia aprovou com sucesso",
        "chamado_id": chamado.id,
        "aprovado_barbeiro": chamado.aprovado_barbeiro,
        "aprovado_barbearia": chamado.aprovado_barbearia,
        "status_chamado": chamado.status
    }

@router.post("/chamados/{chamado_id}/rejeitar-barbeiro")
def rejeitar_como_barbeiro(
    chamado_id: int, 
    motivo: str = "Indisponível",
    sugerir_horario: str = None,
    db: Session = Depends(get_db), 
    token: str = Depends(oauth2_scheme)
):
    """
    Barbeiro rejeita o agendamento e pode sugerir outro horário
    """
    try:
        payload = verify_token(token)
        barbeiro_id = int(payload.get("sub"))
    except:
        raise HTTPException(status_code=401, detail="Token inválido")
    
    chamado = db.query(models.Chamado).filter(models.Chamado.id == chamado_id).first()
    if not chamado:
        raise HTTPException(status_code=404, detail="Agendamento não encontrado")
    
    if chamado.barbeiro_id != barbeiro_id:
        raise HTTPException(status_code=403, detail="Apenas o barbeiro designado pode rejeitar")
    
    # Cancelar o agendamento
    chamado.status = models.StatusAgendamento.CANCELADO
    chamado.observacao = f"Rejeitado pelo barbeiro: {motivo}"
    
    # Registrar no histórico
    historico = models.ChamadoHistorico(
        chamado_id=chamado.id,
        status_anterior=models.StatusAgendamento.PENDENTE,
        status_novo=models.StatusAgendamento.CANCELADO,
        usuario_id=barbeiro_id,
        observacao=f"Rejeitado: {motivo}. Horário sugerido: {sugerir_horario}"
    )
    db.add(historico)
    db.commit()
    db.refresh(chamado)
    
    return {
        "status": "Agendamento rejeitado",
        "chamado_id": chamado.id,
        "motivo": motivo,
        "horario_sugerido": sugerir_horario
    }

@router.get("/chamados/{chamado_id}/horarios-alternativos")
def sugerir_horarios_alternativos(
    chamado_id: int,
    db: Session = Depends(get_db),
    token: str = Depends(oauth2_scheme)
):
    """
    Sugerir horários alternativos quando um agendamento é rejeitado
    """
    chamado = db.query(models.Chamado).filter(models.Chamado.id == chamado_id).first()
    if not chamado:
        raise HTTPException(status_code=404, detail="Agendamento não encontrado")
    
    # Listar agendamentos confirmados para ver quais horários estão ocupados
    agendamentos_confirmados = db.query(models.Chamado).filter(
        models.Chamado.barbearia_id == chamado.barbearia_id,
        models.Chamado.data_hora_inicio >= chamado.data_hora_inicio,
        models.Chamado.status == models.StatusAgendamento.CONFIRMADO
    ).all()
    
    horarios_ocupados = [
        {
            "inicio": agend.data_hora_inicio.isoformat(),
            "fim": agend.data_hora_fim.isoformat()
        }
        for agend in agendamentos_confirmados
    ]
    
    # Sugerir slots de 30 minutos nos próximos 7 dias
    from datetime import timedelta
    data_original = chamado.data_hora_inicio
    horarios_disponiveis = []
    
    for dia_offset in range(1, 8):  # Próximos 7 dias
        data_teste = data_original.replace(day=data_original.day + dia_offset)
        
        # Verificar horários das 8h às 18h
        for hora in range(8, 18):
            hora_teste = data_teste.replace(hour=hora, minute=0, second=0)
            hora_fim = hora_teste + timedelta(minutes=30)
            
            # Verificar se está disponível
            disponivel = True
            for ocupado in horarios_ocupados:
                ocupado_inicio = datetime.fromisoformat(ocupado["inicio"])
                ocupado_fim = datetime.fromisoformat(ocupado["fim"])
                
                # Verificar sobreposição
                if (hora_teste < ocupado_fim) and (hora_fim > ocupado_inicio):
                    disponivel = False
                    break
            
            if disponivel:
                horarios_disponiveis.append({
                    "data_hora": hora_teste.isoformat(),
                    "data_hora_fim": hora_fim.isoformat()
                })
    
    return {
        "horarios_ocupados": horarios_ocupados,
        "horarios_disponiveis": horarios_disponiveis[:5]  # Retornar até 5 sugestões
    }

@router.post("/cadeiras/{cadeira_id}/liberar")
def liberar_cadeira(
    cadeira_id: int,
    motivo: str = "Serviço concluído",
    db: Session = Depends(get_db),
    token: str = Depends(oauth2_scheme)
):
    """
    Liberar uma cadeira após o serviço ser concluído
    """
    try:
        payload = verify_token(token)
        usuario_id = int(payload.get("sub"))
    except:
        raise HTTPException(status_code=401, detail="Token inválido")
    
    cadeira = db.query(models.Cadeira).filter(models.Cadeira.id == cadeira_id).first()
    if not cadeira:
        raise HTTPException(status_code=404, detail="Cadeira não encontrada")
    
    # Verificar permissão: apenas dono da barbearia
    barbearia = db.query(models.Barbearia).filter(
        models.Barbearia.id == cadeira.barbearia_id
    ).first()
    
    if not barbearia or barbearia.usuario_id != usuario_id:
        raise HTTPException(status_code=403, detail="Apenas o dono da barbearia pode liberar cadeira")
    
    # Liberar cadeira
    chamado_id = cadeira.chamado_id
    cadeira.status = models.StatusCadeira.DISPONIVEL
    cadeira.chamado_id = None
    
    # Marcar chamado como concluído
    if chamado_id:
        chamado = db.query(models.Chamado).filter(models.Chamado.id == chamado_id).first()
        if chamado:
            chamado.status = models.StatusAgendamento.CONCLUIDO
            chamado.concluido_em = datetime.utcnow()
    
    db.commit()
    db.refresh(cadeira)
    
    return {
        "status": "Cadeira liberada com sucesso",
        "cadeira_id": cadeira.id,
        "nova_status": cadeira.status,
        "motivo": motivo
    }

@router.get("/barbearia/{barbearia_id}/cadeiras-status")
def listar_status_cadeiras(
    barbearia_id: int,
    db: Session = Depends(get_db),
    token: str = Depends(oauth2_scheme)
):
    """
    Listar status de todas as cadeiras de uma barbearia
    """
    cadeiras = db.query(models.Cadeira).filter(
        models.Cadeira.barbearia_id == barbearia_id
    ).all()
    
    return {
        "barbearia_id": barbearia_id,
        "cadeiras": [
            {
                "id": cadeira.id,
                "numero": cadeira.numero,
                "status": cadeira.status,
                "chamado_id": cadeira.chamado_id,
                "acionada_em": cadeira.acionada_em
            }
            for cadeira in cadeiras
        ]
    }
