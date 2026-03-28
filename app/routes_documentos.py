# --- ARQUIVO: app/routes_documentos.py ---
# Endpoints para validação de documentos

from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from sqlalchemy.orm import Session
from datetime import datetime
import os
import uuid
from pathlib import Path

from . import models, schemas
from .database import get_db
from .routes import get_current_user

router = APIRouter()

# Diretório para armazenar documentos
DOCUMENTS_DIR = Path("uploads/documentos")
DOCUMENTS_DIR.mkdir(parents=True, exist_ok=True)


@router.post("/upload-files", status_code=status.HTTP_200_OK)
async def upload_documento_files(
    documento_frente: UploadFile = File(...),
    documento_verso: UploadFile = File(...),
    selfie_documento: UploadFile = File(...),
    current_user: models.Usuario = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Upload de documentos como arquivos (RG/CNH frente, verso e selfie).
    """
    try:
        # Salvar arquivo frente
        frente_filename = f"{uuid.uuid4()}-{documento_frente.filename}"
        frente_path = DOCUMENTS_DIR / frente_filename
        with open(frente_path, "wb") as f:
            f.write(await documento_frente.read())
        frente_url = f"/uploads/documentos/{frente_filename}"
        
        # Salvar arquivo verso
        verso_filename = f"{uuid.uuid4()}-{documento_verso.filename}"
        verso_path = DOCUMENTS_DIR / verso_filename
        with open(verso_path, "wb") as f:
            f.write(await documento_verso.read())
        verso_url = f"/uploads/documentos/{verso_filename}"
        
        # Salvar arquivo selfie
        selfie_filename = f"{uuid.uuid4()}-{selfie_documento.filename}"
        selfie_path = DOCUMENTS_DIR / selfie_filename
        with open(selfie_path, "wb") as f:
            f.write(await selfie_documento.read())
        selfie_url = f"/uploads/documentos/{selfie_filename}"
        
        # Atualizar usuário com URLs dos documentos
        current_user.documento_frente_url = frente_url
        current_user.documento_verso_url = verso_url
        current_user.selfie_documento_url = selfie_url
        current_user.documento_verificado = False
        current_user.documento_rejeitado_motivo = None
        
        db.commit()
        db.refresh(current_user)
        
        return {
            "message": "Documentos enviados com sucesso! Aguarde a verificação.",
            "status": "aguardando_verificacao",
            "documento_frente_url": frente_url,
            "documento_verso_url": verso_url,
            "selfie_documento_url": selfie_url,
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao fazer upload dos documentos: {str(e)}"
        )


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
    Admin e barbearias podem verificar documentos.
    """
    # Admin e barbearias podem verificar documentos
    if current_user.tipo not in ["barbearia", "admin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Apenas admins e barbearias podem verificar documentos"
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
        usuario.documento_verificado_em = datetime.now()
        usuario.documento_rejeitado_motivo = None
        # Marcar o perfil como aprovado para barbeiro/barbearia
        if usuario.tipo in ['barbeiro', 'barbearia']:
            usuario.perfil_aprovado = True
            usuario.perfil_aprovado_em = datetime.now()
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

@router.get("/admin/pendentes", status_code=status.HTTP_200_OK)
def listar_documentos_pendentes_admin(
    current_user: models.Usuario = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Lista todos os usuários com documentos pendentes de verificação.
    Apenas admins podem acessar.
    """
    if current_user.tipo != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Apenas admins podem listar documentos pendentes"
        )
    
    # Busca usuários com documentos enviados mas não verificados
    # Inclui: barbeiro e barbearia com documentos, ainda não verificados
    usuarios_pendentes = db.query(models.Usuario).filter(
        models.Usuario.documento_frente_url.isnot(None),
        models.Usuario.documento_verificado == False,
        models.Usuario.tipo.in_(['barbeiro', 'barbearia'])
    ).all()
    
    return {
        "total": len(usuarios_pendentes),
        "usuarios": [
            {
                "id": u.id,
                "nome": u.nome,
                "email": u.email,
                "tipo": u.tipo,
                "cpf": u.cpf,
                "documento_frente_url": u.documento_frente_url,
                "documento_verso_url": u.documento_verso_url,
                "selfie_documento_url": u.selfie_documento_url,
                "documento_verificado": u.documento_verificado,
                "documento_rejeitado_motivo": u.documento_rejeitado_motivo,
            }
            for u in usuarios_pendentes
        ]
    }


@router.get("/admin/todos", status_code=status.HTTP_200_OK)
def listar_todos_documentos_admin(
    current_user: models.Usuario = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Lista TODOS os usuários com documentos (pendentes, aprovados e rejeitados).
    Apenas admins podem acessar.
    """
    if current_user.tipo != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Apenas admins podem listar documentos"
        )
    
    # Busca TODOS os usuários com documentos (barbeiro e barbearia)
    usuarios_todos = db.query(models.Usuario).filter(
        models.Usuario.documento_frente_url.isnot(None),
        models.Usuario.tipo.in_(['barbeiro', 'barbearia'])
    ).all()
    
    return {
        "total": len(usuarios_todos),
        "usuarios": [
            {
                "id": u.id,
                "nome": u.nome,
                "email": u.email,
                "tipo": u.tipo,
                "cpf": u.cpf,
                "documento_frente_url": u.documento_frente_url,
                "documento_verso_url": u.documento_verso_url,
                "selfie_documento_url": u.selfie_documento_url,
                "documento_verificado": u.documento_verificado,
                "documento_rejeitado_motivo": u.documento_rejeitado_motivo,
                "perfil_aprovado": u.perfil_aprovado,
            }
            for u in usuarios_todos
        ]
    }