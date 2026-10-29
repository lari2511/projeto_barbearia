"""
Termos de Uso / Política de Privacidade: leitura, situação do usuário, aceite e recusa.

Leitura é pública (o cadastro mostra os documentos antes de a conta existir).
Situação, aceite, recusa e histórico usam o usuário autenticado; data/hora vêm do servidor.
"""

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.routes import get_current_user
from app.termos import documentos as docs
from app.termos import regras
from app.termos.middleware import esquecer_usuario

router = APIRouter(prefix="/api/v1/termos", tags=["Termos e Privacidade"])


class ItemAceite(BaseModel):
    codigo: str
    versao: str
    confirmado: bool = False


class AceiteEntrada(BaseModel):
    aceites: List[ItemAceite]
    data_nascimento: Optional[str] = None  # só freelancer (AAAA-MM-DD)


@router.get("/documentos")
def listar_documentos(perfil: str, incluir_rascunhos: bool = False):
    """
    Documentos publicados do perfil (cliente | freelancer | proprietario, ou o tipo de usuário).
    incluir_rascunhos=true lista também as versões em elaboração (revisão jurídica); elas nunca
    são exigidas nem podem ser aceitas.
    """
    perfil_normalizado = docs.normalizar_perfil(perfil)
    if not perfil_normalizado:
        raise HTTPException(status_code=400, detail="Perfil inválido")

    vigentes = [v.resumo() for v in docs.documentos_vigentes(perfil_normalizado)]
    rascunhos = []
    if incluir_rascunhos:
        codigos_vigentes = {(v["codigo"], v["versao"]) for v in vigentes}
        rascunhos = [
            v.resumo() for v in docs.VERSOES
            if perfil_normalizado in v.perfis and v.estado == docs.RASCUNHO
            and (v.codigo, v.versao) not in codigos_vigentes
        ]
    return {"perfil": perfil_normalizado, "documentos": vigentes, "rascunhos": rascunhos}


@router.get("/documentos/{codigo}")
def ler_documento(codigo: str, versao: Optional[str] = None):
    """Texto completo. Sem versão: a publicada atual ou, se não houver, o rascunho mais recente."""
    documento = docs.buscar(codigo, versao)
    if not documento:
        raise HTTPException(status_code=404, detail="Documento não encontrado")
    return {**documento.resumo(), "conteudo": documento.conteudo, "sha256": documento.sha256}


@router.get("/situacao")
def minha_situacao(db: Session = Depends(get_db), usuario=Depends(get_current_user)):
    return regras.situacao(db, usuario)


@router.post("/aceitar")
def aceitar(dados: AceiteEntrada, db: Session = Depends(get_db), usuario=Depends(get_current_user)):
    situacao = regras.registrar_aceite(
        db, usuario, [item.model_dump() for item in dados.aceites], dados.data_nascimento
    )
    esquecer_usuario(usuario.id)
    return situacao


@router.post("/recusar")
def recusar(db: Session = Depends(get_db), usuario=Depends(get_current_user)):
    situacao = regras.registrar_recusa(db, usuario)
    esquecer_usuario(usuario.id)
    return situacao


@router.get("/historico")
def meu_historico(db: Session = Depends(get_db), usuario=Depends(get_current_user)):
    return {"decisoes": regras.historico(db, usuario)}
