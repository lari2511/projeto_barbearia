# --- ARQUIVO: app/routes_documentos.py ---
# Endpoints para validação de documentos

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import datetime

from . import models, schemas
from .database import get_db
from .routes import get_current_user

router = APIRouter()


@router.post("/upload", status_code=status.HTTP_200_OK)
def upload_documento(
    documento: schemas.DocumentoUpload,
    current_user: models.Usuario = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Upload de documentos (RG/CNH frente, verso e selfie).
    Cliente ou barbeiro envia os documentos para verificação.
    """
    # Atualiza os dados do usuário
    current_user.rg = documento.rg
    current_user.documento_frente_url = documento.documento_frente_url
    current_user.documento_verso_url = documento.documento_verso_url
    current_user.selfie_documento_url = documento.selfie_documento_url
    current_user.documento_verificado = False  # Aguardando verificação
    current_user.documento_rejeitado_motivo = None  # Limpa rejeição anterior
    
    db.commit()
    db.refresh(current_user)
    
    return {
        "message": "Documentos enviados com sucesso! Aguarde a verificação.",
        "status": "aguardando_verificacao"
    }


@router.get("/status", response_model=schemas.DocumentoResponse)
def status_documento(
    current_user: models.Usuario = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Verifica o status de verificação dos documentos do usuário atual.
    """
    return current_user


@router.post("/verificar", status_code=status.HTTP_200_OK)
def verificar_documento(
    verificacao: schemas.DocumentoVerificar,
    current_user: models.Usuario = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Admin/Barbearia verifica e aprova ou rejeita documentos.
    Apenas barbearias podem verificar documentos.
    """
    # Somente barbearias podem verificar documentos
    if current_user.tipo != "barbearia":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Apenas barbearias podem verificar documentos"
        )
    
    # Busca o usuário a ser verificado
    usuario = db.query(models.Usuario).filter(
        models.Usuario.id == verificacao.usuario_id
    ).first()
    
    if not usuario:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuário não encontrado"
        )
    
    # Verifica se há documentos enviados
    if not usuario.documento_frente_url or not usuario.selfie_documento_url:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Usuário não enviou documentos completos"
        )
    
    # Atualiza o status de verificação
    if verificacao.aprovado:
        usuario.documento_verificado = True
        usuario.documento_verificado_em = datetime.utcnow()
        usuario.documento_rejeitado_motivo = None
        message = "Documento aprovado com sucesso!"
    else:
        usuario.documento_verificado = False
        usuario.documento_rejeitado_motivo = verificacao.motivo_rejeicao or "Documento rejeitado"
        message = "Documento rejeitado."
    
    db.commit()
    db.refresh(usuario)
    
    return {
        "message": message,
        "usuario_id": usuario.id,
        "verificado": usuario.documento_verificado,
        "motivo_rejeicao": usuario.documento_rejeitado_motivo
    }


@router.get("/pendentes", status_code=status.HTTP_200_OK)
def listar_documentos_pendentes(
    current_user: models.Usuario = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Lista todos os usuários com documentos pendentes de verificação.
    Apenas barbearias podem acessar.
    """
    if current_user.tipo != "barbearia":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Apenas barbearias podem listar documentos pendentes"
        )
    
    # Busca usuários com documentos enviados mas não verificados
    usuarios_pendentes = db.query(models.Usuario).filter(
        models.Usuario.documento_frente_url.isnot(None),
        models.Usuario.documento_verificado == False,
        models.Usuario.documento_rejeitado_motivo.is_(None)
    ).all()
    
    return {
        "total": len(usuarios_pendentes),
        "usuarios": [
            {
                "id": u.id,
                "nome": u.nome,
                "email": u.email,
                "tipo": u.tipo,
                "rg": u.rg,
                "documento_frente_url": u.documento_frente_url,
                "documento_verso_url": u.documento_verso_url,
                "selfie_documento_url": u.selfie_documento_url,
            }
            for u in usuarios_pendentes
        ]
    }
