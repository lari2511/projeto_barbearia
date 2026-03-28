"""
ARQUIVO: app/routes_firebase.py
Rotas para gerenciar FCM tokens e configuração de notificações push
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import datetime
from pydantic import BaseModel
from typing import Optional

from app.database import get_db
from app.routes import get_current_user
from app.models import Usuario
from app.firebase_config import FIREBASE_DISPONIVEL

router = APIRouter(prefix="/api/v1/firebase", tags=["firebase"])


class RegistrarTokenRequest(BaseModel):
    """Payload para registrar o device token do usuário"""
    device_token: str
    tipo_dispositivo: Optional[str] = "mobile"  # mobile, web, etc


class RenovarTokenRequest(BaseModel):
    """Payload para renovar token quando Firebase gera um novo"""
    token_antigo: str
    token_novo: str


class FirebaseStatusResponse(BaseModel):
    """Resposta do status do Firebase"""
    disponivel: bool
    mensagem: str


@router.post("/registrar-token", status_code=201)
async def registrar_device_token(
    request: RegistrarTokenRequest,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    """
    Registra o device token (FCM) do usuário para receber notificações push.
    
    Este endpoint é chamado automaticamente após o login do barbeiro/cliente.
    O React Native envia o token único do aparelho para que o backend possa
    enviar notificações via Firebase Cloud Messaging.
    
    Args:
        request: RegistrarTokenRequest com device_token
        db: Sessão do banco de dados
        current_user: Usuário autenticado
    
    Returns:
        {
            "sucesso": true,
            "mensagem": "Token registrado com sucesso",
            "usuario_id": 123,
            "device_token": "exJhbGc..."
        }
    """
    
    try:
        # Atualizar o token no banco de dados
        current_user.device_token = request.device_token
        current_user.device_token_atualizado_em = datetime.utcnow()
        
        db.commit()
        db.refresh(current_user)
        
        print(f"✅ Token registrado para usuário {current_user.nome} (ID: {current_user.id})")
        
        return {
            "sucesso": True,
            "mensagem": "Token registrado com sucesso",
            "usuario_id": current_user.id,
            "device_token": request.device_token[:20] + "..." if len(request.device_token) > 20 else request.device_token
        }
    
    except Exception as e:
        db.rollback()
        print(f"❌ Erro ao registrar token: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao registrar token: {str(e)}"
        )


@router.post("/renovar-token", status_code=200)
async def renovar_device_token(
    request: RenovarTokenRequest,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    """
    Renovar o device token quando o Firebase gera um novo.
    
    Quando o usuário desinstala/reinstala o app ou o Firebase renovar o token,
    essa rota atualiza o banco com o novo código.
    
    Args:
        request: RenovarTokenRequest com token_antigo e token_novo
        db: Sessão do banco de dados
        current_user: Usuário autenticado
    
    Returns:
        {
            "sucesso": true,
            "mensagem": "Token renovado com sucesso",
            "usuario_id": 123
        }
    """
    
    try:
        # Verificar se o token antigo corresponde ao que está no banco
        if current_user.device_token != request.token_antigo:
            print(f"⚠️ Tentativa de renovar token desatualizado para usuário {current_user.id}")
            # Ainda assim, atualizamos com o novo token (pode ter sido mudança recente)
        
        # Atualizar com o novo token
        current_user.device_token = request.token_novo
        current_user.device_token_atualizado_em = datetime.utcnow()
        
        db.commit()
        db.refresh(current_user)
        
        print(f"✅ Token renovado para usuário {current_user.nome} (ID: {current_user.id})")
        
        return {
            "sucesso": True,
            "mensagem": "Token renovado com sucesso",
            "usuario_id": current_user.id
        }
    
    except Exception as e:
        db.rollback()
        print(f"❌ Erro ao renovar token: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao renovar token: {str(e)}"
        )


@router.get("/status", response_model=FirebaseStatusResponse)
async def verificar_status_firebase():
    """
    Verificar se o Firebase está configurado e funcionando.
    
    O React Native pode chamar esse endpoint para confirmar se notificações
    estão disponíveis antes de pedir permissão ao usuário.
    
    Returns:
        {
            "disponivel": true ou false,
            "mensagem": Descrição do status
        }
    """
    
    if FIREBASE_DISPONIVEL:
        return FirebaseStatusResponse(
            disponivel=True,
            mensagem="Firebase Cloud Messaging está configurado e pronto para enviar notificações"
        )
    else:
        return FirebaseStatusResponse(
            disponivel=False,
            mensagem="Firebase Cloud Messaging não está configurado. Notificações push não funcionarão."
        )


@router.post("/teste-notificacao", status_code=200)
async def enviar_teste_notificacao(
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    """
    Enviar uma notificação de teste para o próprio usuário.
    
    Útil para testar se as notificações estão funcionando no React Native
    depois de registrar o device token.
    
    Args:
        db: Sessão do banco de dados
        current_user: Usuário autenticado
    
    Returns:
        {
            "sucesso": true ou false,
            "mensagem": Descrição do resultado
        }
    """
    
    if not FIREBASE_DISPONIVEL:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Firebase não está configurado"
        )
    
    if not current_user.device_token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Você não tem um device token registrado. Faça login novamente para registrar."
        )
    
    try:
        from app.firebase_config import messaging
        
        mensagem = messaging.Message(
            notification=messaging.Notification(
                title="🧪 Teste de Notificação",
                body="Se você está vendo isso, as notificações estão funcionando!"
            ),
            data={
                "tipo": "teste_notificacao",
                "timestamp": datetime.utcnow().isoformat()
            },
            token=current_user.device_token,
        )
        
        resposta = messaging.send(mensagem)
        print(f"✅ Notificação de teste enviada: {resposta}")
        
        return {
            "sucesso": True,
            "mensagem": "Notificação de teste enviada com sucesso! Verifique seu celular."
        }
    
    except Exception as e:
        print(f"❌ Erro ao enviar notificação de teste: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao enviar notificação: {str(e)}"
        )
