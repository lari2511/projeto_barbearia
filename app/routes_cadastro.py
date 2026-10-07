"""
Cadastro rápido: só e-mail + senha, entra direto no app.

Os demais dados do perfil (nome, telefone, documentos, endereço da barbearia,
fotos do freelancer) são completados dentro do app em POST /cadastro/completar.
Enquanto `cadastro_pendente` for True:
- cliente usa o app normalmente (só vê o convite para completar);
- freelancer não entra na fila de análise do ADM (continua não aprovado);
- barbearia fica fora da busca (perfil_aprovado=False) até completar.
"""

from datetime import datetime

from fastapi import APIRouter, Body, Depends, HTTPException
from pydantic import ValidationError
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app import models, schemas
from app.database import get_db
from app.routes import create_access_token, get_current_user, get_password_hash, normalize_email

router = APIRouter(prefix="/api/v1", tags=["Cadastro"])

EMAIL_JA_CADASTRADO = "Este e-mail já está cadastrado."
MIN_FOTOS_PORTFOLIO = 1


@router.post("/cadastro-rapido/", response_model=schemas.RegistroResponse)
def cadastro_rapido(dados: schemas.CadastroRapido, db: Session = Depends(get_db)):
    email = normalize_email(dados.email)
    if db.query(models.Usuario.id).filter(func.lower(models.Usuario.email) == email).first():
        raise HTTPException(status_code=400, detail=EMAIL_JA_CADASTRADO)

    agora = datetime.now()
    usuario = models.Usuario(
        email=email,
        # Nome provisório até completar o perfil (várias telas exibem o nome).
        nome=email.split("@")[0],
        senha_hash=get_password_hash(dados.senha),
        tipo=dados.tipo,
        email_verificado=True,
        cadastro_pendente=True,
        # Cliente não passa por análise; freelancer vai para análise do ADM ao completar;
        # barbearia só aparece na busca depois de completar.
        perfil_aprovado=dados.tipo == "cliente",
        perfil_aprovado_em=agora if dados.tipo == "cliente" else None,
    )
    db.add(usuario)
    try:
        db.flush()
        if dados.tipo == "barbearia":
            db.add(models.Barbearia(usuario_id=usuario.id, nome="Minha Barbearia", endereco=""))
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail=EMAIL_JA_CADASTRADO)
    db.refresh(usuario)

    token = create_access_token(data={"sub": str(usuario.id), "tipo": usuario.tipo})
    return schemas.RegistroResponse(
        usuario=schemas.UsuarioPublic.model_validate(usuario),
        access_token=token,
        token_type="bearer",
    )


def _validar(schema, payload: dict):
    try:
        return schema(**payload)
    except ValidationError as exc:
        erro = exc.errors()[0] if exc.errors() else {}
        msg = str(erro.get("msg") or "Dados inválidos").replace("Value error, ", "")
        raise HTTPException(status_code=400, detail=msg)


def _exigir_unico(db: Session, usuario_id: int, campo, valor, mensagem: str):
    if valor and db.query(models.Usuario.id).filter(campo == valor, models.Usuario.id != usuario_id).first():
        raise HTTPException(status_code=400, detail=mensagem)


@router.post("/cadastro/completar")
def completar_cadastro(
    payload: dict = Body(...),
    db: Session = Depends(get_db),
    usuario_atual=Depends(get_current_user),
):
    u = db.query(models.Usuario).filter(models.Usuario.id == usuario_atual.id).first()

    if u.tipo == "cliente":
        dados = _validar(schemas.CompletarCliente, payload)
    elif u.tipo == "barbeiro":
        dados = _validar(schemas.CompletarFreelancer, payload)
    elif u.tipo == "barbearia":
        dados = _validar(schemas.CompletarBarbearia, payload)
    else:
        raise HTTPException(status_code=403, detail="Tipo de usuário sem cadastro a completar")

    telefone = getattr(dados, "telefone", None)
    _exigir_unico(db, u.id, models.Usuario.telefone, telefone, "Telefone já cadastrado")
    cpf = getattr(dados, "cpf", None)
    cnpj = getattr(dados, "cnpj", None)
    _exigir_unico(db, u.id, models.Usuario.cpf, cpf, "CPF já cadastrado")
    _exigir_unico(db, u.id, models.Usuario.cnpj, cnpj, "CNPJ já cadastrado")

    if u.tipo == "barbeiro":
        from app.admin_routes import _qtd_fotos

        if _qtd_fotos(db, u) < MIN_FOTOS_PORTFOLIO:
            raise HTTPException(status_code=400, detail="Adicione pelo menos 1 foto dos seus trabalhos")

    u.nome = dados.nome
    if telefone:
        u.telefone = telefone
    if u.tipo == "barbeiro":
        # Fica EM ANÁLISE (perfil_aprovado=False) até o ADM aprovar.
        u.tempo_experiencia = dados.tempo_experiencia
    elif u.tipo == "barbearia":
        u.cpf = cpf
        u.cnpj = cnpj
        u.endereco = dados.endereco
        barbearia = db.query(models.Barbearia).filter(models.Barbearia.usuario_id == u.id).first()
        if not barbearia:
            barbearia = models.Barbearia(usuario_id=u.id)
            db.add(barbearia)
        barbearia.nome = dados.nome_barbearia
        barbearia.endereco = dados.endereco
        barbearia.telefone = dados.telefone
        barbearia.cep = dados.cep
        if not u.perfil_aprovado:
            u.perfil_aprovado = True
            u.perfil_aprovado_em = datetime.now()

    u.cadastro_pendente = False
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="CPF, CNPJ ou telefone já cadastrado")

    return {
        "message": "Cadastro completo",
        "cadastro_pendente": False,
        "tipo": u.tipo,
        "perfil_aprovado": bool(u.perfil_aprovado),
    }
