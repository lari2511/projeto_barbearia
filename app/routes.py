# --- ARQUIVO: app/routes.py ---
# Responsável pelos endpoints de autenticação e negócio

import os
import secrets
from dotenv import load_dotenv

from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_, func
from datetime import timedelta
from passlib.context import CryptContext
from passlib.exc import UnknownHashError
from datetime import datetime
from jose import JWTError, jwt
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm

from . import models, schemas
from .database import get_db
from .email_utils import send_email
from .email_send import send_verification_email

# Carrega variáveis do arquivo .env
load_dotenv()

router = APIRouter()

# Endpoint de teste
@router.get("/teste")
def teste():
    """Endpoint de teste"""
    return {"status": "ok", "mensagem": "API está funcionando"}

# --- Configuração de Segurança ---
SECRET_KEY = os.getenv("SECRET_KEY", "INSEGURO_MUDE_ISSO_AGORA")
ALGORITHM = os.getenv("ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_DAYS = int(os.getenv("ACCESS_TOKEN_EXPIRE_DAYS", "7"))
REQUIRE_EMAIL_VERIFIED = os.getenv("REQUIRE_EMAIL_VERIFIED", "0") == "1"
VERIFICATION_LINK_BASE = os.getenv(
    "VERIFICATION_LINK_BASE",
    "http://localhost:8000/api/v1/email/verificar?token=",
)

pwd_context = CryptContext(schemes=["argon2", "bcrypt"], deprecated="auto")

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/login/cliente/")

# --- Funções Auxiliares ---

def calcular_split_pagamento(valor_total: float) -> dict:
    """
    Calcula o split de pagamento baseado em 10% plataforma, 40% freelancer, 50% dono.
    
    Exemplo:
        valor_total=100.00 → 
        {
            'valor_total': 100.00,
            'comissao_plataforma': 15.00,
            'valor_freelancer': 45.00,
            'valor_dono': 40.00
        }
    
    Args:
        valor_total: Valor completo do serviço
        
    Returns:
        Dict com breakdown do pagamento (sem erros de arredondamento)
    """
    comissao_plataforma = round(valor_total * 0.10, 2)
    valor_freelancer = round(valor_total * 0.40, 2)
    valor_dono = round(valor_total - comissao_plataforma - valor_freelancer, 2)
    
    return {
        'valor_total': valor_total,
        'comissao_plataforma': comissao_plataforma,
        'valor_freelancer': valor_freelancer,
        'valor_dono': valor_dono
    }

def is_horario_disponivel(db: Session, barbeiro_id: int, inicio: datetime, fim: datetime) -> bool:
    """
    Verifica se um barbeiro está disponível em um determinado horário.
    
    Procura por conflitos com agendamentos não-cancelados.
    Usa lógica de sobreposição de intervalos:
    - novo_inicio < agendamento_existente_fim AND
    - novo_fim > agendamento_existente_inicio
    
    Args:
        db: Sessão do banco de dados
        barbeiro_id: ID do barbeiro
        inicio: Data/hora de início do novo agendamento
        fim: Data/hora de término do novo agendamento
        
    Returns:
        True se está disponível, False se tem conflito
    """
    from sqlalchemy import and_
    
    # Procura por conflitos reais com atendimentos já confirmados.
    # Chamados pendentes/cancelados ou legados sem horário completo
    # não devem bloquear novo agendamento.
    conflito = db.query(models.Chamado).filter(
        and_(
            models.Chamado.barbeiro_id == barbeiro_id,
            models.Chamado.status == models.StatusAgendamento.CONFIRMADO.value,
            models.Chamado.data_hora_inicio.isnot(None),
            models.Chamado.data_hora_fim.isnot(None),
            and_(
                # Lógica de sobreposição:
                models.Chamado.data_hora_inicio < fim,
                models.Chamado.data_hora_fim > inicio
            )
        )
    ).first()
    
    return conflito is None

def esta_em_servico_agora(db: Session, barbeiro_id: int) -> bool:
    """
    Verifica se o barbeiro está em um serviço ATIVO no momento.
    
    Considera em serviço se há um agendamento confirmado
    onde o horário atual está entre data_hora_inicio e data_hora_fim.
    
    Args:
        db: Sessão do banco de dados
        barbeiro_id: ID do barbeiro
        
    Returns:
        True se está em serviço ativo, False caso contrário
    """
    from datetime import datetime
    from sqlalchemy import and_
    
    agora = datetime.now()
    
    # Verifica se o barbeiro tem ocupado_ate definido e ainda não passou
    barbeiro = db.query(models.Usuario).filter(models.Usuario.id == barbeiro_id).first()
    if barbeiro and barbeiro.ocupado_ate:
        if barbeiro.ocupado_ate > agora:
            return True  # Ainda está ocupado
    
    # Procura por agendamento ativo no momento (apenas CONFIRMADO)
    servico_ativo = db.query(models.Chamado).filter(
        models.Chamado.barbeiro_id == barbeiro_id,
        models.Chamado.status == models.StatusAgendamento.CONFIRMADO.value,
        models.Chamado.data_hora_inicio <= agora,
        models.Chamado.data_hora_fim >= agora
    ).first()
    
    return servico_ativo is not None

def verify_password(plain_password: str, hashed_password: str) -> bool:
    if not hashed_password:
        return False
    try:
        return pwd_context.verify(plain_password, hashed_password)
    except UnknownHashError:
        return False

def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now() + expires_delta
    else:
        expire = datetime.now() + timedelta(days=ACCESS_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

# --- Funções de Verificação de E-mail ---

EMAIL_TOKEN_EXPIRE_HOURS = 24

def create_email_verification_token(email: str) -> str:
    """Gera um token JWT específico para verificação de e-mail (válido por 24h)"""
    expire = datetime.now() + timedelta(hours=EMAIL_TOKEN_EXPIRE_HOURS)
    # Colocamos um 'type' para diferenciar de tokens de login
    to_encode = {"sub": email, "exp": expire, "type": "email_verification"}
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def verify_email_token(token: str) -> str | None:
    """
    Verifica e decodifica o token de e-mail.
    Retorna o email se válido, None caso contrário.
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        token_type: str = payload.get("type")
        if email is None or token_type != "email_verification":
            return None
        return email
    except JWTError:
        return None


def dispatch_verification_email(user: models.Usuario) -> None:
    """Send email verification link if SMTP is configured."""
    if not user.token_verificacao:
        return

    verification_url = f"{VERIFICATION_LINK_BASE}{user.token_verificacao}"
    html_body = (
        f"<p>Olá, {user.nome}!</p>"
        f"<p>Confirme seu email para ativar a conta.</p>"
        f"<p><a href='{verification_url}'>Verificar email</a></p>"
        f"<p>Ou copie e cole no navegador: {verification_url}</p>"
    )
    text_body = (
        f"Olá, {user.nome}!\n"
        "Confirme seu email para ativar a conta.\n"
        f"Link: {verification_url}\n"
    )
    send_email(
        subject="Verifique seu email - BarberMove",
        to_email=user.email,
        html_body=html_body,
        text_body=text_body,
    )

def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    print(f"🔐 get_current_user - Token recebido: {token[:50]}...")
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Credenciais inválidas",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: int = int(payload.get("sub"))
        print(f"📋 Token decodificado - User ID: {user_id}")
        if user_id is None:
            raise credentials_exception
    except (JWTError, ValueError) as e:
        print(f"❌ Erro ao decodificar token: {e}")
        raise credentials_exception
    
    user = db.query(models.Usuario).filter(models.Usuario.id == user_id).first()
    if user is None:
        print(f"❌ Usuário não encontrado: ID {user_id}")
        raise credentials_exception
    print(f"✅ Usuário autenticado: {user.email} (tipo: {user.tipo})")
    return user

# --- ENDPOINTS DE CADASTRO ---

@router.post("/clientes/", response_model=schemas.RegistroResponse)
def cadastrar_cliente(
    cliente: schemas.ClienteCreate, 
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    Cadastrar novo cliente
    
    Após o registro, um e-mail de verificação será enviado automaticamente.
    """
    usuario_existente = db.query(models.Usuario).filter(models.Usuario.email == cliente.email).first()
    if usuario_existente:
        raise HTTPException(status_code=400, detail="Email já cadastrado")
    
    # Verificar se CPF já está em uso
    cpf_existente = db.query(models.Usuario).filter(models.Usuario.cpf == cliente.cpf).first()
    if cpf_existente:
        raise HTTPException(status_code=400, detail="CPF já cadastrado")
    
    # Verificar se telefone já está em uso
    if cliente.telefone:
        telefone_existente = db.query(models.Usuario).filter(models.Usuario.telefone == cliente.telefone).first()
        if telefone_existente:
            raise HTTPException(status_code=400, detail="Telefone já cadastrado")
    
    # Gerar token de verificação JWT
    token_verificacao = create_email_verification_token(cliente.email)
    
    novo_usuario = models.Usuario(
        email=cliente.email,
        nome=cliente.nome,
        senha_hash=get_password_hash(cliente.senha),
        telefone=cliente.telefone,
        cpf=cliente.cpf,
        tipo="cliente",
        token_verificacao=token_verificacao,
        email_verificado=False,  # Inicia como não verificado
        perfil_aprovado=True,  # Clientes não precisam de validação - aprovacao automática
    )
    db.add(novo_usuario)
    db.commit()
    db.refresh(novo_usuario)
    
    # Enviar e-mail de verificação em background (não bloqueia a resposta)
    background_tasks.add_task(
        send_verification_email, 
        novo_usuario.email, 
        token_verificacao,
        novo_usuario.nome
    )
    
    # Gerar token de acesso
    access_token = create_access_token(data={"sub": str(novo_usuario.id), "tipo": novo_usuario.tipo})
    
    usuario_serializado = schemas.UsuarioPublic.model_validate(novo_usuario)
    return schemas.RegistroResponse(
        usuario=usuario_serializado,
        access_token=access_token,
        token_type="bearer"
    )


@router.post("/barbeiros/", response_model=schemas.RegistroResponse)
def cadastrar_barbeiro(
    barbeiro: schemas.BarbeiroCreate, 
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    Cadastrar novo barbeiro
    
    Após o registro, um e-mail de verificação será enviado automaticamente.
    """
    usuario_existente = db.query(models.Usuario).filter(models.Usuario.email == barbeiro.email).first()
    if usuario_existente:
        raise HTTPException(status_code=400, detail="Email já cadastrado")
    
    # Verificar se CPF já está em uso
    cpf_existente = db.query(models.Usuario).filter(models.Usuario.cpf == barbeiro.cpf).first()
    if cpf_existente:
        raise HTTPException(status_code=400, detail="CPF já cadastrado")
    
    # Verificar se telefone já está em uso
    if barbeiro.telefone:
        telefone_existente = db.query(models.Usuario).filter(models.Usuario.telefone == barbeiro.telefone).first()
        if telefone_existente:
            raise HTTPException(status_code=400, detail="Telefone já cadastrado")
    
    # Gerar token de verificação JWT
    token_verificacao = create_email_verification_token(barbeiro.email)
    
    novo_usuario = models.Usuario(
        email=barbeiro.email,
        nome=barbeiro.nome,
        senha_hash=get_password_hash(barbeiro.senha),
        telefone=barbeiro.telefone,
        cpf=barbeiro.cpf,
        tipo="barbeiro",
        token_verificacao=token_verificacao,
        email_verificado=False,  # Inicia como não verificado
    )
    db.add(novo_usuario)
    db.commit()
    db.refresh(novo_usuario)
    
    # Enviar e-mail de verificação em background (não bloqueia a resposta)
    background_tasks.add_task(
        send_verification_email, 
        novo_usuario.email, 
        token_verificacao,
        novo_usuario.nome
    )
    
    # Enviar email de avaliação pendente em background
    # from .email import send_perfil_awaiting_approval_email
    # Temporariamente comentado para testes
    # background_tasks.add_task(
    #     send_perfil_awaiting_approval_email,
    #     novo_usuario.email,
    #     novo_usuario.nome,
    #     "barbeiro"
    # )
    
    # Gerar token de acesso para upload de documentos
    access_token = create_access_token(data={"sub": str(novo_usuario.id), "tipo": novo_usuario.tipo})
    
    usuario_serializado = schemas.UsuarioPublic.model_validate(novo_usuario)
    return schemas.RegistroResponse(
        usuario=usuario_serializado,
        access_token=access_token,
        token_type="bearer"
    )

@router.post("/barbearias/", response_model=schemas.RegistroResponse)
def cadastrar_barbearia(
    barbearia: schemas.BarbeariaCreate, 
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    Cadastrar nova barbearia e vincular usuário/barbearia
    
    Após o registro, um e-mail de verificação será enviado automaticamente.
    """
    usuario_existente = db.query(models.Usuario).filter(models.Usuario.email == barbearia.email).first()
    if usuario_existente:
        raise HTTPException(status_code=400, detail="Email já cadastrado")
    
    # Verificar se CPF já está em uso
    cpf_existente = db.query(models.Usuario).filter(models.Usuario.cpf == barbearia.cpf).first()
    if cpf_existente:
        raise HTTPException(status_code=400, detail="CPF já cadastrado")
    
    # Verificar se telefone já está em uso
    if barbearia.telefone:
        telefone_existente = db.query(models.Usuario).filter(models.Usuario.telefone == barbearia.telefone).first()
        if telefone_existente:
            raise HTTPException(status_code=400, detail="Telefone já cadastrado")
    
    # Verificar se CNPJ já está em uso
    if barbearia.cnpj:
        cnpj_existente = db.query(models.Usuario).filter(models.Usuario.cnpj == barbearia.cnpj).first()
        if cnpj_existente:
            raise HTTPException(status_code=400, detail="CNPJ já cadastrado")

    # Gerar token de verificação JWT
    token_verificacao = create_email_verification_token(barbearia.email)
    
    novo_usuario = models.Usuario(
        email=barbearia.email,
        nome=barbearia.nome,
        endereco=barbearia.endereco,
        telefone=barbearia.telefone,
        cpf=barbearia.cpf,
        cnpj=barbearia.cnpj,
        senha_hash=get_password_hash(barbearia.senha),
        tipo="barbearia",
        token_verificacao=token_verificacao,
        email_verificado=False,  # Inicia como não verificado
    )
    db.add(novo_usuario)
    db.commit()
    db.refresh(novo_usuario)

    nova_barbearia = models.Barbearia(
        usuario_id=novo_usuario.id,
        nome=barbearia.nome,
        endereco=barbearia.endereco,
        telefone=barbearia.telefone,
        cep=barbearia.cep,
    )
    db.add(nova_barbearia)
    db.commit()
    db.refresh(nova_barbearia)

    # Enviar e-mail de verificação em background (não bloqueia a resposta)
    background_tasks.add_task(
        send_verification_email, 
        novo_usuario.email, 
        token_verificacao,
        novo_usuario.nome
    )
    
    # Enviar email de avaliação pendente em background
    # from .email import send_perfil_awaiting_approval_email
    # Temporariamente comentado para testes
    # background_tasks.add_task(
    #     send_perfil_awaiting_approval_email,
    #     novo_usuario.email,
    #     novo_usuario.nome,
    #     "barbearia"
    # )
    
    # Gerar token de acesso para upload de documentos
    access_token = create_access_token(data={"sub": str(novo_usuario.id), "tipo": novo_usuario.tipo})

    usuario_serializado = schemas.UsuarioPublic.model_validate(novo_usuario)
    return schemas.RegistroResponse(
        usuario=usuario_serializado,
        access_token=access_token,
        token_type="bearer"
    )

# --- ENDPOINTS DE LOGIN ---

@router.post("/login/cliente/")
def login_cliente(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    """Login para cliente"""
    email = form_data.username
    senha = form_data.password
    
    usuario = db.query(models.Usuario).filter(
        models.Usuario.email == email,
        models.Usuario.tipo == "cliente"
    ).first()
    
    if not usuario or not verify_password(senha, usuario.senha_hash):
        raise HTTPException(status_code=401, detail="Email ou senha incorretos")

    if REQUIRE_EMAIL_VERIFIED and not usuario.email_verificado:
        raise HTTPException(
            status_code=403,
            detail="Email não verificado. Verifique sua caixa de entrada ou reenvie o link.",
        )
    
    access_token = create_access_token(data={"sub": str(usuario.id), "tipo": usuario.tipo})
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user_id": usuario.id,
        "tipo": usuario.tipo,
        "mensagem": f"Bem-vindo, {usuario.nome}!"
    }

@router.post("/login/barbeiro/")
def login_barbeiro(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    """Login para barbeiro"""
    email = form_data.username
    senha = form_data.password
    
    usuario = db.query(models.Usuario).filter(
        models.Usuario.email == email,
        models.Usuario.tipo == "barbeiro"
    ).first()
    
    if not usuario or not verify_password(senha, usuario.senha_hash):
        raise HTTPException(status_code=401, detail="Email ou senha incorretos")
    
    access_token = create_access_token(data={"sub": str(usuario.id), "tipo": usuario.tipo})
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user_id": usuario.id,
        "tipo": usuario.tipo,
        "mensagem": f"Bem-vindo, {usuario.nome}!"
    }

@router.post("/login/barbearia/")
def login_barbearia(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    """Login para barbearia"""
    email = form_data.username
    senha = form_data.password
    
    print(f"🔍 LOGIN BARBEARIA - Email: {email}")
    
    usuario = db.query(models.Usuario).filter(
        models.Usuario.email == email,
        models.Usuario.tipo == "barbearia"
    ).first()
    
    if not usuario:
        print(f"❌ Usuário não encontrado: {email}")
        raise HTTPException(status_code=401, detail="Email ou senha incorretos")
    
    print(f"✅ Usuário encontrado: {usuario.nome} (tipo: {usuario.tipo})")
    senha_ok = verify_password(senha, usuario.senha_hash)
    print(f"🔐 Senha válida: {senha_ok}")
    
    if not senha_ok:
        print(f"❌ Senha incorreta para {email}")
        raise HTTPException(status_code=401, detail="Email ou senha incorretos")
    
    access_token = create_access_token(data={"sub": str(usuario.id), "tipo": usuario.tipo})
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user_id": usuario.id,
        "tipo": usuario.tipo,
        "mensagem": f"Bem-vindo, {usuario.nome}!"
    }

@router.post("/login/admin/")
def login_admin(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    """Login para admin"""
    email = form_data.username
    senha = form_data.password
    
    usuario = db.query(models.Usuario).filter(
        models.Usuario.email == email,
        models.Usuario.tipo == "admin"
    ).first()
    
    if not usuario or not verify_password(senha, usuario.senha_hash):
        raise HTTPException(status_code=401, detail="Email ou senha incorretos")
    
    access_token = create_access_token(data={"sub": str(usuario.id), "tipo": usuario.tipo})
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user_id": usuario.id,
        "tipo": usuario.tipo,
        "mensagem": f"Bem-vindo, {usuario.nome}!"
    }

# --- ENDPOINTS DE BUSCA ---

@router.get("/barbearias/todas")
def listar_todas_barbearias(db: Session = Depends(get_db)):
    """Listar todas as barbearias cadastradas"""
    barbearias = db.query(models.Barbearia).all()
    return barbearias

@router.get("/barbearia/{id}/servicos")
def listar_servicos_barbearia(id: int, db: Session = Depends(get_db)):
    """Listar serviços de uma barbearia específica"""
    servicos = db.query(models.Servico).filter(models.Servico.barbearia_id == id).all()
    return servicos




@router.get("/barbearia/minha")
def obter_minha_barbearia(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    """Retorna a barbearia vinculada ao usuário autenticado"""
    user = get_current_user(token=token, db=db)
    if user.tipo != "barbearia":
        raise HTTPException(status_code=403, detail="Apenas barbearias")
    barbearia = db.query(models.Barbearia).filter(models.Barbearia.usuario_id == user.id).first()
    if not barbearia:
        barbearia = models.Barbearia(
            usuario_id=user.id,
            nome=user.nome or "Minha Barbearia",
            endereco=user.endereco or "",
            telefone=user.telefone,
            status_online=True
        )
        db.add(barbearia)
        db.commit()
        db.refresh(barbearia)
    return barbearia

# --- ENDPOINTS DE CHAMADOS ---

@router.post("/chamados")
def criar_chamado(chamado: schemas.ChamadoCreate, token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    """Criar novo chamado (agendamento)"""
    # Validar token e obter usuário
    user = get_current_user(token=token, db=db)
    
    # Buscar serviço e barbearia
    servico = db.query(models.Servico).filter(models.Servico.id == chamado.servico_id).first()
    barbearia = db.query(models.Barbearia).filter(models.Barbearia.id == chamado.barbearia_id).first()
    
    if not servico or not barbearia:
        raise HTTPException(status_code=404, detail="Serviço ou barbearia não encontrados")

    if servico.barbearia_id != barbearia.id:
        raise HTTPException(status_code=400, detail="Serviço não pertence a essa barbearia")

    # Validação defensiva: evita criação para barbeiro diferente do selecionado na UI.
    if chamado.barbeiro_id and chamado.barbeiro_selecionado_id and chamado.barbeiro_id != chamado.barbeiro_selecionado_id:
        raise HTTPException(
            status_code=400,
            detail="Conflito no barbeiro selecionado. Atualize a tela e tente novamente."
        )
    
    # ✅ GUARDIÃO 1: Validar data/hora do agendamento
    if not chamado.data_hora_inicio:
        raise HTTPException(status_code=400, detail="Data e hora de início obrigatórias")
    
    # Calcular hora de término baseado na duração do serviço
    # Se não tiver duração, usa 30 minutos como padrão
    duracao_minutos = servico.duracao_minutos if hasattr(servico, 'duracao_minutos') and servico.duracao_minutos else 30
    hora_fim = chamado.data_hora_inicio + timedelta(minutes=duracao_minutos)
    
    # ✅ GUARDIÃO: Validar status do freelancer (barbeiro)
    if chamado.barbeiro_id:
        barbeiro = db.query(models.Usuario).filter(models.Usuario.id == chamado.barbeiro_id).first()
        if barbeiro:
            # Regra 1: Freelancer OFFLINE não pode receber chamados
            barbeiro_offline = bool(getattr(barbeiro, "offline", False))
            if barbeiro_offline:
                raise HTTPException(
                    status_code=400,
                    detail="Barbeiro está OFFLINE. Não pode receber chamados."
                )
            
            # Regra 2: Freelancer PRESENT_LOCAL só pode receber de uma barbearia específica
            if barbeiro.presente_em_local and barbeiro.barbearia_atual_id:
                if barbeiro.barbearia_atual_id != barbearia.id:
                    nome_barbearia = db.query(models.Barbearia).filter(
                        models.Barbearia.id == barbeiro.barbearia_atual_id
                    ).first()
                    raise HTTPException(
                        status_code=400,
                        detail=f"Barbeiro está PRESENTE em {nome_barbearia.nome if nome_barbearia else 'outra barbearia'}. Não pode receber chamados de outro local."
                    )
            
            # Regra 3: Validar especialidade do barbeiro para o serviço
            freelancer_perfil = db.query(models.Freelancer).filter(
                models.Freelancer.usuario_id == barbeiro.id
            ).first()
            
            if freelancer_perfil:
                especialidades = db.query(models.EspecialidadeFreelancer).filter(
                    models.EspecialidadeFreelancer.freelancer_id == freelancer_perfil.id
                ).all()
                tipos_especialidade = [esp.tipo for esp in especialidades]
                
                # Se tem especialidades cadastradas, validar que tem a necessária
                if tipos_especialidade and servico.categoria not in tipos_especialidade:
                    raise HTTPException(
                        status_code=403,
                        detail=f"Barbeiro não possui a especialidade em '{servico.categoria}' necessária para este serviço. Suas especialidades: {', '.join(tipos_especialidade)}."
                    )
    
    # ✅ GUARDIÃO 2: Verificar se horário está disponível para o barbeiro
    # Nota: Apenas verifica se barbeiro foi especificado
    if chamado.barbeiro_id:
        disponivel = is_horario_disponivel(
            db,
            chamado.barbeiro_id,
            chamado.data_hora_inicio,
            hora_fim
        )
        
        if not disponivel:
            raise HTTPException(
                status_code=400,
                detail="Barbeiro ja tem um corte aceito nesse horario. Tente outro horario."
            )
    
    cadeira_id = None

    if chamado.cadeira_id:
        cadeira = db.query(models.Cadeira).filter(
            models.Cadeira.id == chamado.cadeira_id,
            models.Cadeira.barbearia_id == barbearia.id
        ).first()
        if not cadeira:
            raise HTTPException(status_code=404, detail="Cadeira não encontrada")
        
        # ✅ GUARDIÃO: Cadeira DEVE estar DISPONÍVEL para aceitar agendamento
        if cadeira.status != models.StatusCadeira.DISPONIVEL:
            raise HTTPException(
                status_code=400, 
                detail=f"Cadeira {cadeira.numero} não está disponível (Status: {cadeira.status}). Solicite ao dono liberar a cadeira."
            )
        
        # ✅ GUARDIÃO: Verificar se cadeira já tem agendamento CONFIRMADO nesse período
        conflito = db.query(models.Chamado).filter(
            models.Chamado.cadeira_id == cadeira.id,
            models.Chamado.status == models.StatusAgendamento.CONFIRMADO.value,
            models.Chamado.data_hora_inicio < hora_fim,  # Agendamento começa antes do fim
            models.Chamado.data_hora_fim > chamado.data_hora_inicio  # Agendamento termina depois do início
        ).first()
        
        if conflito:
            horario_conflito = f"{conflito.data_hora_inicio.strftime('%H:%M')} às {conflito.data_hora_fim.strftime('%H:%M')}"
            raise HTTPException(
                status_code=400,
                detail=f"Cadeira {cadeira.numero} já possui agendamento confirmado de {horario_conflito}. Escolha outro horário ou outra cadeira."
            )
        
        if cadeira.status == models.StatusCadeira.OCUPADA and cadeira.freelancer_id and cadeira.freelancer_id != chamado.barbeiro_id:
            nome = cadeira.freelancer.nome if cadeira.freelancer else "Freelancer"
            raise HTTPException(status_code=400, detail=f"BRB ocupada por {nome}")
        cadeira_id = cadeira.id

    if chamado.barbeiro_id and not cadeira_id:
        ocupadas = db.query(models.Cadeira).filter(
            models.Cadeira.barbearia_id == barbearia.id,
            models.Cadeira.status == models.StatusCadeira.OCUPADA,
            models.Cadeira.freelancer_id.isnot(None)
        ).all()

        cadeira_do_freelancer = next((c for c in ocupadas if c.freelancer_id == chamado.barbeiro_id), None)
        if cadeira_do_freelancer:
            cadeira_id = cadeira_do_freelancer.id
        else:
            cadeira_livre = db.query(models.Cadeira).filter(
                models.Cadeira.barbearia_id == barbearia.id,
                models.Cadeira.status == models.StatusCadeira.DISPONIVEL
            ).first()
            if not cadeira_livre and ocupadas:
                nome = ocupadas[0].freelancer.nome if ocupadas[0].freelancer else "Freelancer"
                raise HTTPException(status_code=400, detail=f"BRB ocupada por {nome}")

    # Calcular split do pagamento (snapshot financeiro)
    split = calcular_split_pagamento(servico.valor)
    
    novo_chamado = models.Chamado(
        cliente_id=user.id,
        barbeiro_id=chamado.barbeiro_id,  # Usar o barbeiro selecionado pelo cliente
        servico_id=chamado.servico_id,
        barbearia_id=chamado.barbearia_id,
        cadeira_id=cadeira_id,
        data_hora_inicio=chamado.data_hora_inicio,  # Novo campo
        data_hora_fim=hora_fim,  # Usar hora calculada
        status=models.StatusAgendamento.PENDENTE.value,  # Usar Enum
        valor_total=split['valor_total'],  # Novo campo
        comissao_plataforma=split['comissao_plataforma'],  # Novo campo
        valor_freelancer=split['valor_freelancer'],  # Novo campo
        valor_dono=split['valor_dono'],  # Novo campo
        valor_original=servico.valor,  # Manter para compatibilidade
        valor_final=servico.valor  # Manter para compatibilidade
    )
    db.add(novo_chamado)
    db.commit()
    db.refresh(novo_chamado)
    
    # Criar histórico
    historico = models.ChamadoHistorico(
        chamado_id=novo_chamado.id,
        status_novo="ABERTO",
        usuario_id=user.id,
        observacao="Chamado criado"
    )
    db.add(historico)
    
    # Criar notificação
    notificacao = models.Notificacao(
        usuario_id=user.id,
        titulo="Chamado Criado",
        mensagem=f"Seu chamado para {servico.nome} foi criado!",
        tipo="chamado",
        referencia_id=novo_chamado.id
    )
    db.add(notificacao)
    db.commit()
    
    return {
        "id": novo_chamado.id,
        "status": novo_chamado.status,
        "cliente_id": novo_chamado.cliente_id,
        "servico_id": novo_chamado.servico_id,
        "descricao": servico.nome,
        "valor": servico.valor
    }

@router.get("/chamados/debug-abertos")
def debug_chamados_abertos(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    """DEBUG: Ver por que chamados nao aparecem"""
    user = get_current_user(token=token, db=db)
    if user.tipo != "barbeiro":
        raise HTTPException(status_code=403, detail="Apenas barbeiros podem ver chamados abertos")
    
    debug = {
        "user_id": user.id,
        "user_nome": user.nome,
        "presente_em_local": user.presente_em_local,
        "barbearia_atual_id": user.barbearia_atual_id
    }
    
    # Passo 1: Chamados pendentes
    query = db.query(models.Chamado).filter(
        models.Chamado.status == models.StatusAgendamento.PENDENTE.value,
        (models.Chamado.barbeiro_id == None) | (models.Chamado.barbeiro_id == user.id)
    )
    chamados_encontrados = query.all()
    
    debug["chamados_pendentes_encontrados"] = len(chamados_encontrados)
    debug["chamados_ids"] = [c.id for c in chamados_encontrados]
    
    # Passo 2: Freelancer
    freelancer_perfil = db.query(models.Freelancer).filter(
        models.Freelancer.usuario_id == user.id
    ).first()
    
    debug["freelancer_existe"] = freelancer_perfil is not None
    if freelancer_perfil:
        debug["freelancer_id"] = freelancer_perfil.id
        
        especialidades = db.query(models.EspecialidadeFreelancer).filter(
            models.EspecialidadeFreelancer.freelancer_id == freelancer_perfil.id
        ).all()
        debug["especialidades"] = [esp.tipo for esp in especialidades]
    else:
        debug["especialidades"] = []
    
    return debug

@router.get("/chamados/abertos")
def listar_chamados_abertos(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db), debug: str = None):
    """Listar chamados abertos (para barbeiros)"""
    user = get_current_user(token=token, db=db)
    if user.tipo != "barbeiro":
        raise HTTPException(status_code=403, detail="Apenas barbeiros podem ver chamados abertos")
    
    # 🔒 REGRA: Se PRESENTE_LOCAL, só mostra chamados da barbearia selecionada
    query = db.query(models.Chamado).filter(
        models.Chamado.status == models.StatusAgendamento.PENDENTE.value,
        (models.Chamado.barbeiro_id == None) | (models.Chamado.barbeiro_id == user.id)
    )
    
    # Se está PRESENTE em uma barbearia, filtrar só chamados daquela barbearia
    if user.presente_em_local and user.barbearia_atual_id:
        query = query.filter(
            or_(
                models.Chamado.barbearia_id == user.barbearia_atual_id,
                models.Chamado.barbeiro_id == user.id
            )
        )
    
    chamados_encontrados = query.all()
    
    if debug == "1" or debug == "true":
        return {
            "debug": True,
            "user_id": user.id,
            "chamados_encontrados_count": len(chamados_encontrados),
            "chamados_ids": [c.id for c in chamados_encontrados],
            "user_presente_em_local": user.presente_em_local
        }
    
    # 🎯 FILTRO: Validar especialidade do freelancer
    freelancer_perfil = db.query(models.Freelancer).filter(
        models.Freelancer.usuario_id == user.id
    ).first()
    
    tipos_especialidade = []
    if freelancer_perfil:
        especialidades = db.query(models.EspecialidadeFreelancer).filter(
            models.EspecialidadeFreelancer.freelancer_id == freelancer_perfil.id
        ).all()
        tipos_especialidade = [esp.tipo for esp in especialidades]
    
    # Filtrar chamados por especialidade apenas fora do modo "presente no local".
    # Quando o barbeiro está presente em uma barbearia específica, ele deve ver
    # todas as solicitações pendentes daquela unidade.
    chamados = []
    for c in chamados_encontrados:
        servico = db.query(models.Servico).filter(models.Servico.id == c.servico_id).first()

        # Chamados já direcionados a este barbeiro devem sempre aparecer para
        # ele aceitar/recusar, independentemente de filtros complementares.
        if c.barbeiro_id == user.id:
            chamados.append(c)
            continue

        if user.presente_em_local and user.barbearia_atual_id:
            chamados.append(c)
            continue

        # Se não tem especialidades cadastradas, mostra todos (compatibilidade).
        # Se tem, filtra só os que correspondem à especialidade.
        if not tipos_especialidade or (servico and servico.categoria in tipos_especialidade):
            chamados.append(c)
        else:
            continue  # Pula este chamado - freelancer não tem especialidade
    
    resultado = []
    for c in chamados:
        cliente = db.query(models.Usuario).filter(models.Usuario.id == c.cliente_id).first()
        servico = db.query(models.Servico).filter(models.Servico.id == c.servico_id).first()
        barbearia = db.query(models.Barbearia).filter(models.Barbearia.id == c.barbearia_id).first()
        
        resultado.append({
            "id": c.id,
            "cliente_id": c.cliente_id,
            "nome_cliente": cliente.nome if cliente else "Desconhecido",
            "cliente_telefone": cliente.telefone if cliente else "",
            "cliente_email": cliente.email if cliente else "",
            "descricao": servico.nome if servico else "Serviço",
            "valor": servico.valor if servico else 0,
            "endereco": cliente.endereco if cliente else "Não informado",
            "nome_barbearia": barbearia.nome if barbearia else "Barbearia",
            "endereco_barbearia": barbearia.endereco if barbearia else "",
            "data_hora_inicio": c.data_hora_inicio.isoformat() if c.data_hora_inicio else None,
            "status": c.status
        })
    
    return resultado

@router.get("/cliente/meus_pedidos")
def listar_meus_pedidos(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    """Listar meus pedidos (para cliente)"""
    user = get_current_user(token=token, db=db)
    
    chamados = db.query(models.Chamado).filter(models.Chamado.cliente_id == user.id).all()
    
    resultado = []
    for c in chamados:
        servico = db.query(models.Servico).filter(models.Servico.id == c.servico_id).first()
        barbearia = db.query(models.Barbearia).filter(models.Barbearia.id == c.barbearia_id).first()
        barbeiro = db.query(models.Usuario).filter(models.Usuario.id == c.barbeiro_id).first() if c.barbeiro_id else None
        
        ja_avaliado_generico = db.query(models.Avaliacao).filter(
            models.Avaliacao.chamado_id == c.id,
            models.Avaliacao.avaliador_id == user.id
        ).first() is not None

        # Avaliacao de freelancer pode estar salva com freelancer_id = usuario_id
        # (fluxo legado) ou freelancer_id = freelancers.id (fluxo atual).
        ja_avaliou_freelancer_direto = db.query(models.AvaliacaoFreelancer).filter(
            models.AvaliacaoFreelancer.chamado_id == c.id,
            models.AvaliacaoFreelancer.avaliador_id == user.id,
            models.AvaliacaoFreelancer.freelancer_id == c.barbeiro_id,
        ).first() is not None

        freelancer_rel = db.query(models.Freelancer).filter(
            models.Freelancer.usuario_id == c.barbeiro_id
        ).first() if c.barbeiro_id else None

        ja_avaliou_freelancer_rel = False
        if freelancer_rel:
            ja_avaliou_freelancer_rel = db.query(models.AvaliacaoFreelancer).filter(
                models.AvaliacaoFreelancer.chamado_id == c.id,
                models.AvaliacaoFreelancer.avaliador_id == user.id,
                models.AvaliacaoFreelancer.freelancer_id == freelancer_rel.id,
            ).first() is not None

        ja_avaliou_freelancer = ja_avaliou_freelancer_direto or ja_avaliou_freelancer_rel

        ja_avaliou_barbearia = db.query(models.AvaliacaoBarbearia).filter(
            models.AvaliacaoBarbearia.chamado_id == c.id,
            models.AvaliacaoBarbearia.avaliador_id == user.id,
            models.AvaliacaoBarbearia.barbearia_id == c.barbearia_id,
        ).first() is not None

        ja_avaliado = ja_avaliado_generico or ja_avaliou_freelancer or ja_avaliou_barbearia

        resultado.append({
            "id": c.id,
            "cliente_id": c.cliente_id,
            "barbeiro_id": c.barbeiro_id,
            "barbearia_id": c.barbearia_id,
            "barbearia_usuario_id": barbearia.usuario_id if barbearia else None,
            "servico_id": c.servico_id,
            "descricao": servico.nome if servico else "Serviço",
            "servico_nome": servico.nome if servico else "Serviço",
            "valor": servico.valor if servico else 0,
            "nome_barbearia": barbearia.nome if barbearia else "Barbearia",
            "barbeiro_nome": barbeiro.nome if barbeiro else "Barbeiro",
            "endereco": barbearia.endereco if barbearia else "Não informado",
            "status": c.status,
            "data_hora_inicio": c.data_hora_inicio.isoformat() if c.data_hora_inicio else None,
            "avaliado": ja_avaliado,
            "avaliado_freelancer": ja_avaliou_freelancer,
            "avaliado_barbearia": ja_avaliou_barbearia
        })
    
    return resultado

@router.get("/barbeiro/{barbeiro_id}/agendamentos")
def listar_agendamentos_barbeiro(barbeiro_id: int, db: Session = Depends(get_db)):
    """
    Lista todos os agendamentos de um barbeiro específico.
    
    JSON de entrada: 
    - GET /api/v1/barbeiro/{barbeiro_id}/agendamentos
    
    Retorna lista com:
    - id: ID do agendamento
    - cliente_nome: Nome do cliente
    - servico: Nome do serviço
    - valor: Valor do serviço
    - status: Status (ABERTO, ACEITO, CONCLUÍDO)
    - data_agendamento: Data/hora do agendamento
    - barbearia_nome: Nome da barbearia
    """
    
    barbeiro = db.query(models.Usuario).filter(models.Usuario.id == barbeiro_id).first()
    if not barbeiro:
        raise HTTPException(status_code=404, detail="Barbeiro não encontrado")
    
    if barbeiro.tipo != "barbeiro":
        raise HTTPException(status_code=400, detail="Usuário não é um barbeiro")
    
    # Buscar todos os chamados do barbeiro (aceitos ou em andamento)
    chamados = db.query(models.Chamado).filter(
        models.Chamado.barbeiro_id == barbeiro_id
    ).order_by(models.Chamado.data_agendamento.desc()).all()
    
    resultado = []
    for chamado in chamados:
        cliente = db.query(models.Usuario).filter(models.Usuario.id == chamado.cliente_id).first()
        servico = db.query(models.Servico).filter(models.Servico.id == chamado.servico_id).first()
        barbearia = db.query(models.Barbearia).filter(models.Barbearia.id == chamado.barbearia_id).first()
        
        ja_avaliado = db.query(models.Avaliacao).filter(
            models.Avaliacao.chamado_id == chamado.id,
            models.Avaliacao.avaliador_id == barbeiro_id
        ).first() is not None

        resultado.append({
            "id": chamado.id,
            "cliente_id": chamado.cliente_id,
            "barbearia_id": chamado.barbearia_id,
            "cliente_nome": cliente.nome if cliente else "Desconhecido",
            "cliente_telefone": cliente.telefone if cliente else "",
            "servico": servico.nome if servico else "Serviço",
            "servico_nome": servico.nome if servico else "Serviço",
            "descricao": servico.nome if servico else "Serviço",
            "valor": servico.valor if servico else 0,
            "status": chamado.status,
            "data_hora_inicio": chamado.data_hora_inicio.isoformat() if chamado.data_hora_inicio else None,
            "data_agendamento": chamado.data_agendamento.isoformat() if chamado.data_agendamento else None,
            "criado_em": chamado.criado_em.isoformat() if chamado.criado_em else None,
            "barbearia_nome": barbearia.nome if barbearia else "Barbearia",
            "avaliado": ja_avaliado
        })
    
    return resultado

@router.get("/barbeiro/agendamentos/meus")
def listar_meus_agendamentos(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    """
    Lista agendamentos do barbeiro autenticado (versão protegida por token).
    """
    user = get_current_user(token=token, db=db)
    
    if user.tipo != "barbeiro":
        raise HTTPException(status_code=403, detail="Apenas barbeiros podem acessar este endpoint")
    
    # Chamada interna ao endpoint acima
    return listar_agendamentos_barbeiro(user.id, db)

@router.post("/barbeiro/{barbeiro_id}/agendamentos/filtrar")
def filtrar_agendamentos_barbeiro(
    barbeiro_id: int,
    filtro: dict = None,
    db: Session = Depends(get_db)
):
    """
    Filtra agendamentos de um barbeiro por status, data, etc.
    
    JSON de entrada:
    {
        "status": "ACEITO",  # opcional: ABERTO, ACEITO, CONCLUÍDO
        "data_inicio": "2025-01-01",  # opcional
        "data_fim": "2025-01-31"  # opcional
    }
    """
    
    barbeiro = db.query(models.Usuario).filter(models.Usuario.id == barbeiro_id).first()
    if not barbeiro or barbeiro.tipo != "barbeiro":
        raise HTTPException(status_code=404, detail="Barbeiro não encontrado")
    
    query = db.query(models.Chamado).filter(models.Chamado.barbeiro_id == barbeiro_id)
    
    # Aplicar filtros se fornecidos
    if filtro:
        if filtro.get("status"):
            query = query.filter(models.Chamado.status == filtro["status"])
        
        if filtro.get("data_inicio"):
            from datetime import datetime
            data_inicio = datetime.fromisoformat(filtro["data_inicio"])
            query = query.filter(models.Chamado.data_agendamento >= data_inicio)
        
        if filtro.get("data_fim"):
            from datetime import datetime
            data_fim = datetime.fromisoformat(filtro["data_fim"])
            query = query.filter(models.Chamado.data_agendamento <= data_fim)
    
    chamados = query.order_by(models.Chamado.data_agendamento.desc()).all()
    
    resultado = []
    for chamado in chamados:
        cliente = db.query(models.Usuario).filter(models.Usuario.id == chamado.cliente_id).first()
        servico = db.query(models.Servico).filter(models.Servico.id == chamado.servico_id).first()
        barbearia = db.query(models.Barbearia).filter(models.Barbearia.id == chamado.barbearia_id).first()
        
        resultado.append({
            "id": chamado.id,
            "cliente_nome": cliente.nome if cliente else "Desconhecido",
            "servico": servico.nome if servico else "Serviço",
            "valor": servico.valor if servico else 0,
            "status": chamado.status,
            "data_agendamento": chamado.data_agendamento.isoformat() if chamado.data_agendamento else None,
            "barbearia_nome": barbearia.nome if barbearia else "Barbearia"
        })
    
    return resultado


@router.put("/barbeiro/status")
def atualizar_status_freelancer(
    dados: schemas.AtualizarStatusFreelancer,
    token: str = Depends(oauth2_scheme), 
    db: Session = Depends(get_db)
):
    """
    ✅ SISTEMA DE STATUS DO FREELANCER
    
    Atualiza o status do freelancer para controlar conflito de agenda.
    
    Status possíveis:
    - "offline": Não pode receber chamados, não aparece em buscas
    - "online_region": Pode receber chamados de qualquer barbearia da região
    - "present_local": Presente em uma barbearia específica, só recebe chamados dela
    
    JSON de entrada:
    {
        "status": "online_region"  // ou "offline" ou "present_local"
        "barbearia_id": 1  // Obrigatório se status = "present_local"
    }
    """
    user = get_current_user(token=token, db=db)
    
    if user.tipo != "barbeiro":
        raise HTTPException(status_code=403, detail="Apenas barbeiros podem acessar este endpoint")
    
    # Validar status
    status_valido = dados.status.lower()
    if status_valido not in ["offline", "online_region", "present_local"]:
        raise HTTPException(
            status_code=400, 
            detail="Status inválido. Use: 'offline', 'online_region' ou 'present_local'"
        )
    
    # Validar barbearia_id se status = present_local
    if status_valido == "present_local":
        if not dados.barbearia_id:
            raise HTTPException(
                status_code=400,
                detail="barbearia_id é obrigatório quando status = 'present_local'"
            )
        
        barbearia = db.query(models.Barbearia).filter(
            models.Barbearia.id == dados.barbearia_id
        ).first()
        
        if not barbearia:
            raise HTTPException(status_code=404, detail="Barbearia não encontrada")
    
    # Atualizar status no banco
    usuario = db.query(models.Usuario).filter(models.Usuario.id == user.id).first()
    if not usuario:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")
    
    # Reset de todos os status para a lógica correta
    usuario.offline = False
    usuario.presente_em_local = False
    usuario.online_regiao = False
    usuario.barbearia_atual_id = None
    usuario.horario_chegada = None
    
    # Definir o novo status
    if status_valido == "offline":
        usuario.offline = True
        usuario.disponivel = False
    
    elif status_valido == "online_region":
        usuario.online_regiao = True
        usuario.disponivel = True
    
    elif status_valido == "present_local":
        usuario.presente_em_local = True
        usuario.barbearia_atual_id = dados.barbearia_id
        usuario.horario_chegada = datetime.utcnow()
        usuario.disponivel = True
    
    db.commit()
    db.refresh(usuario)
    
    # Mapear status para resposta legível
    status_map = {
        "offline": "OFFLINE",
        "online_region": "ONLINE_REGIÃO",
        "present_local": f"PRESENTE EM {barbearia.nome if status_valido == 'present_local' else ''}"
    }
    
    return {
        "success": True,
        "message": f"Status atualizado para {status_map[status_valido]}",
        "status": status_valido,
        "offline": usuario.offline,
        "online_regiao": usuario.online_regiao,
        "presente_em_local": usuario.presente_em_local,
        "barbearia_atual_id": usuario.barbearia_atual_id,
        "horario_chegada": usuario.horario_chegada
    }


@router.put("/barbeiro/disponibilidade")
def atualizar_disponibilidade(
    dados: dict,
    token: str = Depends(oauth2_scheme), 
    db: Session = Depends(get_db)
):
    """
    Atualiza a disponibilidade do barbeiro para aparecer nas proximidades.
    
    JSON de entrada:
    {
        "disponivel": true ou false
    }
    """
    user = get_current_user(token=token, db=db)
    
    if user.tipo != "barbeiro":
        raise HTTPException(status_code=403, detail="Apenas barbeiros podem acessar este endpoint")
    
    usuario = db.query(models.Usuario).filter(models.Usuario.id == user.id).first()
    if not usuario:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")
    
    usuario.disponivel = dados.get("disponivel", False)
    db.commit()
    
    return {
        "success": True,
        "message": "Disponibilidade atualizada com sucesso",
        "disponivel": usuario.disponivel
    }


@router.post("/barbeiro/sair-barbearia")
def sair_da_barbearia(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
):
    """
    Barbeiro sai da barbearia atual.
    Desvincula o barbeiro da barbearia e muda seu status para OFFLINE.
    """
    user = get_current_user(token=token, db=db)
    
    if user.tipo != "barbeiro":
        raise HTTPException(status_code=403, detail="Apenas barbeiros podem acessar este endpoint")
    
    usuario = db.query(models.Usuario).filter(models.Usuario.id == user.id).first()
    if not usuario:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")
    
    # Se não está em nenhuma barbearia, retornar erro
    if not usuario.barbearia_atual_id:
        raise HTTPException(
            status_code=400,
            detail="Você não está em nenhuma barbearia no momento"
        )
    
    # Desvincula da barbearia e vai para OFFLINE
    barbearia_nome = "a barbearia"
    if usuario.barbearia_atual_id:
        barbearia = db.query(models.Barbearia).filter(
            models.Barbearia.id == usuario.barbearia_atual_id
        ).first()
        if barbearia:
            barbearia_nome = barbearia.nome
    
    usuario.barbearia_atual_id = None
    usuario.presente_em_local = False
    usuario.online_regiao = False
    usuario.offline = True
    usuario.disponivel = False
    usuario.horario_chegada = None
    
    db.commit()
    db.refresh(usuario)
    
    return {
        "success": True,
        "message": f"Você saiu de {barbearia_nome}. Status: OFFLINE",
        "status": "offline",
        "barbearia_atual_id": None,
        "presente_em_local": False,
        "offline": True
    }

    chamados = db.query(models.Chamado).filter(models.Chamado.barbeiro_id == user.id).all()
    
    resultado = []
    for c in chamados:
        servico = db.query(models.Servico).filter(models.Servico.id == c.servico_id).first()
        cliente = db.query(models.Usuario).filter(models.Usuario.id == c.cliente_id).first()
        
        resultado.append({
            "id": c.id,
            "descricao": servico.nome if servico else "Serviço",
            "valor": servico.valor if servico else 0,
            "nome_cliente": cliente.nome if cliente else "Desconhecido",
            "endereco": cliente.endereco if cliente else "Não informado",
            "status": c.status
        })
    
    return resultado

# --- ENDPOINTS ADICIONAIS (ACEITAR/FINALIZAR CHAMADO) ---

@router.put("/chamados/{id}/aceitar")
def aceitar_chamado(id: int, token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    """Barbeiro aceita um chamado"""
    user = get_current_user(token=token, db=db)
    if user.tipo != "barbeiro":
        raise HTTPException(status_code=403, detail="Apenas barbeiros podem aceitar chamados")
    
    chamado = db.query(models.Chamado).filter(models.Chamado.id == id).first()
    if not chamado:
        raise HTTPException(status_code=404, detail="Chamado não encontrado")
    
    # ✅ GUARDIÃO: Validar status do freelancer
    barbeiro = db.query(models.Usuario).filter(models.Usuario.id == user.id).first()
    if barbeiro:
        # Regra: Freelancer PRESENTE só pode aceitar de uma barbearia específica
        if barbeiro.presente_em_local and barbeiro.barbearia_atual_id:
            if barbeiro.barbearia_atual_id != chamado.barbearia_id:
                nome_barbearia = db.query(models.Barbearia).filter(
                    models.Barbearia.id == barbeiro.barbearia_atual_id
                ).first()
                raise HTTPException(
                    status_code=400,
                    detail=f"Você está PRESENTE em {nome_barbearia.nome if nome_barbearia else 'outra barbearia'}. Não pode aceitar chamados de outro local."
                )
    
    # ✅ VALIDAÇÃO: Verificar especialidade do freelancer para o serviço
    servico = db.query(models.Servico).filter(models.Servico.id == chamado.servico_id).first()
    if servico:
        # Buscar o perfil de freelancer do usuário
        freelancer_perfil = db.query(models.Freelancer).filter(
            models.Freelancer.usuario_id == user.id
        ).first()
        
        if freelancer_perfil:
            # Buscar especialidades do freelancer
            especialidades_freelancer = db.query(models.EspecialidadeFreelancer).filter(
                models.EspecialidadeFreelancer.freelancer_id == freelancer_perfil.id
            ).all()
            
            tipos_especialidade = [esp.tipo for esp in especialidades_freelancer]
            
            # Validar se tem a especialidade requerida (usar categoria do serviço)
            if servico.categoria not in tipos_especialidade:
                raise HTTPException(
                    status_code=403,
                    detail=f"Você não possui a especialidade em '{servico.categoria}' necessária para este serviço. Suas especialidades: {', '.join(tipos_especialidade) if tipos_especialidade else 'nenhuma cadastrada'}. Atualize seu perfil!"
                )
    
    # ✅ GUARDIÃO: Se tem cadeira associada, verificar se está DISPONÍVEL
    if chamado.cadeira_id:
        cadeira = db.query(models.Cadeira).filter(models.Cadeira.id == chamado.cadeira_id).first()
        if cadeira and cadeira.status != models.StatusCadeira.DISPONIVEL:
            raise HTTPException(
                status_code=400,
                detail=f"Cadeira {cadeira.numero} não está mais disponível (Status: {cadeira.status}). Solicite ao dono liberar novamente."
            )
        
        # ✅ Verificar conflitos de horário na cadeira
        if chamado.data_hora_inicio and chamado.data_hora_fim:
            conflito = db.query(models.Chamado).filter(
                models.Chamado.cadeira_id == chamado.cadeira_id,
                models.Chamado.status == models.StatusAgendamento.CONFIRMADO.value,
                models.Chamado.id != id,  # Não contar o próprio agendamento
                models.Chamado.data_hora_inicio < chamado.data_hora_fim,
                models.Chamado.data_hora_fim > chamado.data_hora_inicio
            ).first()
            
            if conflito:
                horario_conflito = f"{conflito.data_hora_inicio.strftime('%H:%M')} às {conflito.data_hora_fim.strftime('%H:%M')}"
                raise HTTPException(
                    status_code=400,
                    detail=f"Cadeira {cadeira.numero} já possui agendamento confirmado de {horario_conflito}. Não é possível aceitar este agendamento."
                )
    
    # ✅ CALCULAR HORÁRIOS DO SERVIÇO (baseado na duração do serviço)
    agora = datetime.now()
    duracao_minutos = servico.duracao_minutos if servico else 40  # Default 40min
    
    # Se já tem horário agendado, respeita. Senão, começa AGORA
    if not chamado.data_hora_inicio:
        chamado.data_hora_inicio = agora
    if not chamado.data_hora_fim:
        chamado.data_hora_fim = chamado.data_hora_inicio + timedelta(minutes=duracao_minutos)
    
    status_anterior = chamado.status
    chamado.barbeiro_id = user.id
    chamado.status = models.StatusAgendamento.CONFIRMADO.value  # Usar Enum
    chamado.observacao = None  # Limpar observação quando barbeiro aceita

    # ✅ BLOQUEAR CADEIRA ASSOCIADA AO CHAMADO AO ACEITAR
    if chamado.cadeira_id:
        cadeira_aceita = db.query(models.Cadeira).filter(models.Cadeira.id == chamado.cadeira_id).first()
        if cadeira_aceita:
            cadeira_aceita.status = models.StatusCadeira.OCUPADA
            cadeira_aceita.freelancer_id = user.id
            cadeira_aceita.chamado_id = chamado.id
            cadeira_aceita.ocupada_em = datetime.now()
    
    # ✅ MARCAR BARBEIRO COMO INDISPONÍVEL até o fim do serviço
    if not barbeiro:
        raise HTTPException(status_code=500, detail="Erro ao recuperar dados do barbeiro")
    
    barbeiro.disponivel = False
    barbeiro.em_atendimento = True
    barbeiro.ocupado_ate = chamado.data_hora_fim
    
    db.commit()
    db.refresh(chamado)
    
    # Criar histórico
    historico = models.ChamadoHistorico(
        chamado_id=chamado.id,
        status_anterior=status_anterior,
        status_novo=models.StatusAgendamento.CONFIRMADO.value,
        usuario_id=user.id,
        observacao=f"Aceito por {user.nome}"
    )
    db.add(historico)
    
    # Notificar cliente
    notificacao = models.Notificacao(
        usuario_id=chamado.cliente_id,
        titulo="Chamado Aceito",
        mensagem=f"O barbeiro {user.nome} aceitou seu chamado!",
        tipo="chamado",
        referencia_id=chamado.id
    )
    db.add(notificacao)
    db.commit()
    
    return {"id": chamado.id, "status": chamado.status}

@router.put("/chamados/{id}/rejeitar")
def rejeitar_chamado(id: int, token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    """Barbeiro rejeita um chamado"""
    user = get_current_user(token=token, db=db)
    if user.tipo != "barbeiro":
        raise HTTPException(status_code=403, detail="Apenas barbeiros podem rejeitar chamados")
    
    chamado = db.query(models.Chamado).filter(models.Chamado.id == id).first()
    if not chamado:
        raise HTTPException(status_code=404, detail="Chamado não encontrado")
    
    status_anterior = chamado.status
    chamado.status = models.StatusAgendamento.CANCELADO.value
    chamado.barbeiro_id = None  # Remove o barbeiro associado
    db.commit()
    db.refresh(chamado)
    
    # Criar histórico
    historico = models.ChamadoHistorico(
        chamado_id=chamado.id,
        status_anterior=status_anterior,
        status_novo=models.StatusAgendamento.CANCELADO.value,
        usuario_id=user.id,
        observacao=f"Recusado por {user.nome}"
    )
    db.add(historico)
    
    # Notificar cliente
    notificacao = models.Notificacao(
        usuario_id=chamado.cliente_id,
        titulo="Agendamento Recusado",
        mensagem=f"O barbeiro {user.nome} recusou seu agendamento. Tente outro horário ou profissional.",
        tipo="chamado",
        referencia_id=chamado.id
    )
    db.add(notificacao)
    db.commit()
    
    return {"id": chamado.id, "status": chamado.status}

@router.put("/chamados/{id}/finalizar")
def finalizar_servico_manualmente(id: int, token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    """
    Barbeiro finaliza o serviço manualmente antes do tempo previsto.
    Libera o barbeiro para aceitar novos chamados imediatamente.
    """
    user = get_current_user(token=token, db=db)
    if user.tipo != "barbeiro":
        raise HTTPException(status_code=403, detail="Apenas barbeiros podem finalizar serviços")
    
    chamado = db.query(models.Chamado).filter(models.Chamado.id == id).first()
    if not chamado:
        raise HTTPException(status_code=404, detail="Chamado não encontrado")
    
    if chamado.barbeiro_id != user.id:
        raise HTTPException(status_code=403, detail="Este chamado não pertence a você")
    
    # Buscar barbeiro
    barbeiro = db.query(models.Usuario).filter(models.Usuario.id == user.id).first()
    
    # ✅ LIBERAR BARBEIRO IMEDIATAMENTE
    barbeiro.disponivel = True
    barbeiro.em_atendimento = False
    barbeiro.ocupado_ate = None

    # ✅ LIBERAR CADEIRA(S) IMEDIATAMENTE
    # Fluxo principal: cadeira vinculada no chamado
    if chamado.cadeira_id:
        cadeira_do_chamado = db.query(models.Cadeira).filter(
            models.Cadeira.id == chamado.cadeira_id
        ).first()
        if cadeira_do_chamado:
            cadeira_do_chamado.status = models.StatusCadeira.DISPONIVEL
            cadeira_do_chamado.freelancer_id = None
            cadeira_do_chamado.chamado_id = None
            cadeira_do_chamado.liberada_em = datetime.now()

    # Fluxo legado/fallback: cadeira ocupada pelo freelancer sem chamada vinculada corretamente
    cadeiras_ocupadas = db.query(models.Cadeira).filter(
        models.Cadeira.freelancer_id == user.id,
        models.Cadeira.status == models.StatusCadeira.OCUPADA
    ).all()
    for cadeira in cadeiras_ocupadas:
        cadeira.status = models.StatusCadeira.DISPONIVEL
        cadeira.freelancer_id = None
        if cadeira.chamado_id == chamado.id:
            cadeira.chamado_id = None
        cadeira.liberada_em = datetime.now()
    
    # Atualizar status do chamado para CONCLUIDO
    status_anterior = chamado.status
    chamado.status = models.StatusAgendamento.CONCLUIDO.value
    chamado.data_hora_fim = datetime.now()  # Atualiza hora de fim real
    
    db.commit()
    db.refresh(chamado)
    db.refresh(barbeiro)
    
    # Criar histórico
    historico = models.ChamadoHistorico(
        chamado_id=chamado.id,
        status_anterior=status_anterior,
        status_novo=models.StatusAgendamento.CONCLUIDO.value,
        usuario_id=user.id,
        observacao=f"Finalizado manualmente por {user.nome}"
    )
    db.add(historico)
    
    # Notificar cliente
    notificacao = models.Notificacao(
        usuario_id=chamado.cliente_id,
        titulo="Serviço Concluído",
        mensagem=f"O barbeiro {user.nome} finalizou seu atendimento!",
        tipo="chamado",
        referencia_id=chamado.id
    )
    db.add(notificacao)
    db.commit()
    
    return {
        "id": chamado.id,
        "status": chamado.status,
        "message": "Serviço finalizado! Você está disponível para novos chamados.",
        "barbeiro": {
            "disponivel": barbeiro.disponivel,
            "em_atendimento": barbeiro.em_atendimento,
            "ocupado_ate": None
        }
    }

@router.put("/chamados/{id}/barbearia/aceitar")
def barbearia_aceitar_chamado(id: int, token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    """❌ BLOQUEADO: Apenas o freelancer pode aceitar agendamentos"""
    user = get_current_user(token=token, db=db)
    if user.tipo != "barbearia":
        raise HTTPException(status_code=403, detail="Apenas barbearias podem confirmar disponibilidade")
    
    # ❌ REGRA: Apenas o freelancer pode aceitar agendamentos
    raise HTTPException(
        status_code=403,
        detail="Apenas o freelancer pode aceitar agendamentos. O dono da barbearia não pode aceitar/recusar."
    )
    
    # Notificar cliente
    notificacao = models.Notificacao(
        usuario_id=chamado.cliente_id,
        titulo="Cadeira Confirmada",
        mensagem=f"A barbearia {barbearia.nome} confirmou sua cadeira!",
        tipo="chamado",
        referencia_id=chamado.id
    )
    db.add(notificacao)
    
    # Notificar barbeiro
    if chamado.barbeiro_id:
        notificacao_barbeiro = models.Notificacao(
            usuario_id=chamado.barbeiro_id,
            titulo="Cadeira Confirmada",
            mensagem=f"A barbearia {barbearia.nome} confirmou o agendamento!",
            tipo="chamado",
            referencia_id=chamado.id
        )
        db.add(notificacao_barbeiro)
    
    db.commit()
    
    return {"id": chamado.id, "status": chamado.status}

@router.put("/chamados/{id}/barbearia/recusar")
def barbearia_recusar_chamado(id: int, token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    """Barbearia recusa o agendamento (sem cadeira disponível)"""
    user = get_current_user(token=token, db=db)
    if user.tipo != "barbearia":
        raise HTTPException(status_code=403, detail="Apenas barbearias podem recusar agendamentos")

    raise HTTPException(status_code=403, detail="Barbearia não pode recusar agendamentos")

@router.put("/chamados/{id}/finalizar")
def finalizar_chamado(id: int, token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    """Finalizar um chamado - APENAS FREELANCER"""
    user = get_current_user(token=token, db=db)
    
    # ❌ REGRA: Apenas freelancer (barbeiro) pode finalizar
    if user.tipo != "barbeiro":
        raise HTTPException(
            status_code=403,
            detail="Apenas o freelancer pode finalizar o atendimento. O dono da barbearia não pode finalizar."
        )
    
    chamado = db.query(models.Chamado).filter(models.Chamado.id == id).first()
    if not chamado:
        raise HTTPException(status_code=404, detail="Chamado não encontrado")
    
    # Verificar se é o barbeiro deste chamado
    if chamado.barbeiro_id != user.id:
        raise HTTPException(status_code=403, detail="Este agendamento não é seu")
    
    status_anterior = chamado.status
    chamado.status = models.StatusAgendamento.CONCLUIDO.value  # Usar Enum
    chamado.concluido_em = datetime.now()

    # Manter consistência de status do barbeiro após conclusão
    barbeiro = db.query(models.Usuario).filter(models.Usuario.id == user.id).first()
    if barbeiro:
        barbeiro.disponivel = True
        barbeiro.em_atendimento = False
        barbeiro.ocupado_ate = None

    # ✅ LIBERAR CADEIRA ASSOCIADA APÓS CONCLUSÃO
    if chamado.cadeira_id:
        cadeira_concluida = db.query(models.Cadeira).filter(models.Cadeira.id == chamado.cadeira_id).first()
        if cadeira_concluida and cadeira_concluida.chamado_id == chamado.id:
            cadeira_concluida.status = models.StatusCadeira.DISPONIVEL
            cadeira_concluida.freelancer_id = None
            cadeira_concluida.chamado_id = None
            cadeira_concluida.liberada_em = datetime.now()

    db.commit()
    db.refresh(chamado)
    
    # Criar histórico
    historico = models.ChamadoHistorico(
        chamado_id=chamado.id,
        status_anterior=status_anterior,
        status_novo=models.StatusAgendamento.CONCLUIDO.value,
        usuario_id=user.id,
        observacao="Serviço concluído"
    )
    db.add(historico)
    
    # Notificar cliente
    notificacao = models.Notificacao(
        usuario_id=chamado.cliente_id,
        titulo="Serviço Concluído",
        mensagem="Seu serviço foi concluído! Não esqueça de avaliar.",
        tipo="chamado",
        referencia_id=chamado.id
    )
    db.add(notificacao)
    
    # Adicionar pontos de fidelidade ao cliente
    pontos = db.query(models.PontosFidelidade).filter(models.PontosFidelidade.usuario_id == chamado.cliente_id).first()
    if not pontos:
        pontos = models.PontosFidelidade(usuario_id=chamado.cliente_id, pontos=50)
        db.add(pontos)
    else:
        pontos.pontos += 50
        if pontos.pontos >= 1000:
            pontos.nivel = "PLATINA"
        elif pontos.pontos >= 500:
            pontos.nivel = "OURO"
        elif pontos.pontos >= 200:
            pontos.nivel = "PRATA"
    
    db.commit()
    
    return {"id": chamado.id, "status": chamado.status}

# --- ENDPOINTS DE BARBEIROS ---

@router.get("/barbeiros/proximos")
def listar_barbeiros_proximos(
    latitude: float,
    longitude: float,
    raio_km: float = 10.0,
    db: Session = Depends(get_db)
):
    """
    Listar barbeiros próximos à localização do cliente
    
    Usa fórmula de Haversine para calcular distância
    
    ✅ FILTROS:
    - perfil_aprovado = True (apenas barbeiros aprovados)
    - disponivel = True (apenas barbeiros disponíveis)
    - latitude/longitude não nulas
    """
    from math import radians, cos, sin, asin, sqrt
    
    def haversine(lon1, lat1, lon2, lat2):
        """Calcula distância em km entre dois pontos (lat/lon)"""
        lon1, lat1, lon2, lat2 = map(radians, [lon1, lat1, lon2, lat2])
        dlon = lon2 - lon1
        dlat = lat2 - lat1
        a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
        c = 2 * asin(sqrt(a))
        km = 6371 * c
        return km
    
    # ✅ GUARDIÃO: Apenas barbeiros APROVADOS e DISPONÍVEIS
    # ✅ INCLUINDO barbeiros presentes em barbearias (podem receber agendamentos)
    agora_filtro = datetime.now()
    barbeiros = db.query(models.Usuario).filter(
        models.Usuario.tipo == "barbeiro",
        models.Usuario.perfil_aprovado == True,  # Apenas aprovados
        models.Usuario.disponivel == True,  # Apenas disponíveis (flag manual)
        models.Usuario.latitude.isnot(None),
        models.Usuario.longitude.isnot(None),
        # ✅ NÃO está ocupado OU já passou do horário de ocupação
        or_(
            models.Usuario.ocupado_ate.is_(None),
            models.Usuario.ocupado_ate <= agora_filtro
        )
    ).all()
    
    # Filtrar por distância E verificar se está em serviço
    barbeiros_proximos = []
    for b in barbeiros:
        distancia = haversine(longitude, latitude, b.longitude, b.latitude)
        if distancia <= raio_km:
            # ✅ Calcula disponibilidade REAL: flag do banco AND não está em serviço ativo
            disponivel_real = b.disponivel and not esta_em_servico_agora(db, b.id)
            
            # Calcular tempo estimado: velocidade média 40 km/h em zona urbana
            tempo_minutos = int((distancia / 40) * 60)
            
            # ✅ Buscar nome da barbearia se presente em local
            barbearia_nome = None
            if b.barbearia_atual_id:
                barbearia = db.query(models.Barbearia).filter(models.Barbearia.id == b.barbearia_atual_id).first()
                if barbearia:
                    barbearia_nome = barbearia.nome
            
            barbeiros_proximos.append({
                "id": b.id,
                "nome": b.nome,
                "telefone": b.telefone,
                "endereco": b.endereco,
                "latitude": b.latitude,
                "longitude": b.longitude,
                "distancia_km": round(distancia, 2),
                "tempo_estimado_minutos": tempo_minutos,
                "documento_verificado": b.documento_verificado,
                "disponivel": disponivel_real,  # ✅ Disponibilidade dinâmica
                "foto_perfil": b.foto_perfil,
                "presente_em_local": b.presente_em_local or False,
                "barbearia_atual_id": b.barbearia_atual_id,
                "barbearia_atual_nome": barbearia_nome,
                "online_regiao": b.online_regiao or False
            })
    
    # Ordenar por distância
    barbeiros_proximos.sort(key=lambda x: x["distancia_km"])
    
    return barbeiros_proximos

@router.get("/barbeiros/todos")
def listar_todos_barbeiros(db: Session = Depends(get_db)):
    """Listar todos os barbeiros cadastrados (INCLUINDO os presentes em barbearias)"""
    # ✅ INCLUIR barbeiros presentes - eles também podem receber agendamentos
    barbeiros = db.query(models.Usuario).filter(
        models.Usuario.tipo == "barbeiro"
    ).all()
    
    resultado = []
    for b in barbeiros:
        # ✅ Calcula disponibilidade REAL: flag do banco AND não está em serviço ativo
        disponivel_real = b.disponivel and not esta_em_servico_agora(db, b.id)
        barbearia_nome = None
        if b.barbearia_atual_id:
            barbearia = db.query(models.Barbearia).filter(models.Barbearia.id == b.barbearia_atual_id).first()
            if barbearia:
                barbearia_nome = barbearia.nome
        
        resultado.append({
            "id": b.id,
            "nome": b.nome,
            "telefone": b.telefone,
            "endereco": b.endereco,
            "documento_verificado": b.documento_verificado,
            "disponivel": disponivel_real,  # ✅ Disponibilidade dinâmica
            "presente_em_local": b.presente_em_local or False,
            "barbearia_atual_id": b.barbearia_atual_id,
            "barbearia_atual_nome": barbearia_nome,
            "online_regiao": b.online_regiao or False,
            "foto_perfil": b.foto_perfil,
            "latitude": b.latitude,
            "longitude": b.longitude
        })
    
    return resultado


@router.get("/freelancer/todos")
def listar_todos_freelancers_alias(db: Session = Depends(get_db)):
    """Alias legada para manter compatibilidade com clientes antigos."""
    return listar_todos_barbeiros(db=db)

@router.get("/barbeiro/{barbeiro_id}/barbearias")
def listar_barbearias_do_barbeiro(barbeiro_id: int, db: Session = Depends(get_db)):
    """Listar barbearias onde um barbeiro específico atende"""
    barbeiro = db.query(models.Usuario).filter(
        models.Usuario.id == barbeiro_id,
        models.Usuario.tipo == "barbeiro"
    ).first()
    if not barbeiro:
        raise HTTPException(status_code=404, detail="Barbeiro não encontrado")

    # Quando o barbeiro está presente em um local específico, deve aparecer
    # ao menos essa barbearia para permitir o agendamento direto.
    if barbeiro.presente_em_local and barbeiro.barbearia_atual_id:
        barbearia_atual = db.query(models.Barbearia).filter(
            models.Barbearia.id == barbeiro.barbearia_atual_id
        ).first()
        if barbearia_atual:
            cadeira_disponivel = db.query(models.Cadeira).filter(
                models.Cadeira.barbearia_id == barbearia_atual.id,
                or_(
                    models.Cadeira.status == models.StatusCadeira.DISPONIVEL,
                    and_(
                        models.Cadeira.status == models.StatusCadeira.OCUPADA,
                        models.Cadeira.freelancer_id.is_(None)
                    )
                )
            ).first()

            return [{
                "id": barbearia_atual.id,
                "usuario_id": barbearia_atual.usuario_id,
                "nome": barbearia_atual.nome,
                "endereco": barbearia_atual.endereco,
                "telefone": barbearia_atual.telefone,
                "cadeira_livre": cadeira_disponivel is not None,
                "cadeira_disponivel": cadeira_disponivel is not None
            }]

    # Por enquanto retorna todas as barbearias com cadeira disponível
    # TODO: Implementar relacionamento barbeiro-barbearias
    barbearias = db.query(models.Barbearia).all()
    resultado = []
    for b in barbearias:
        cadeira_disponivel = db.query(models.Cadeira).filter(
            models.Cadeira.barbearia_id == b.id,
            or_(
                models.Cadeira.status == models.StatusCadeira.DISPONIVEL,
                and_(
                    models.Cadeira.status == models.StatusCadeira.OCUPADA,
                    models.Cadeira.freelancer_id.is_(None)
                )
            )
        ).first()

        if not cadeira_disponivel:
            continue

        resultado.append({
            "id": b.id,
            "usuario_id": b.usuario_id,
            "nome": b.nome,
            "endereco": b.endereco,
            "telefone": b.telefone,
            "cadeira_livre": True,
            "cadeira_disponivel": True
        })

    return resultado

@router.get("/barbearia/{barbearia_id}/agendamentos")
def listar_agendamentos_barbearia(
    barbearia_id: int,
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
):
    """Listar agendamentos confirmados de uma barbearia"""
    user = get_current_user(token=token, db=db)
    
    # Verificar se é dono da barbearia
    barbearia = db.query(models.Barbearia).filter(
        models.Barbearia.id == barbearia_id,
        models.Barbearia.usuario_id == user.id
    ).first()
    
    if not barbearia:
        raise HTTPException(status_code=403, detail="Acesso negado")
    
    # Buscar agendamentos confirmados e pendentes
    agendamentos = db.query(models.Chamado).filter(
        models.Chamado.barbearia_id == barbearia_id,
        models.Chamado.status.in_([
            models.StatusAgendamento.CONFIRMADO.value,
            models.StatusAgendamento.PENDENTE.value,
            models.StatusAgendamento.CONCLUIDO.value
        ])
    ).order_by(models.Chamado.data_hora_inicio).all()
    
    result = []
    for ag in agendamentos:
        cliente = db.query(models.Usuario).filter(models.Usuario.id == ag.cliente_id).first()
        barbeiro = db.query(models.Usuario).filter(models.Usuario.id == ag.barbeiro_id).first() if ag.barbeiro_id else None
        servico = db.query(models.Servico).filter(models.Servico.id == ag.servico_id).first()
        
        ja_avaliado = db.query(models.Avaliacao).filter(
            models.Avaliacao.chamado_id == ag.id,
            models.Avaliacao.avaliador_id == user.id
        ).first() is not None

        result.append({
            "id": ag.id,
            "cliente_id": ag.cliente_id,
            "barbeiro_id": ag.barbeiro_id,
            "barbearia_id": ag.barbearia_id,
            "nome_cliente": cliente.nome if cliente else "Cliente",
            "nome_barbeiro": barbeiro.nome if barbeiro else "Aguardando",
            "descricao": servico.nome if servico else "Serviço",
            "data_hora_inicio": ag.data_hora_inicio,
            "status": ag.status,
            "avaliado": ja_avaliado
        })
    
    return result


@router.get("/barbearia/{barbearia_id}/barbeiros-presentes")
def listar_barbeiros_presentes(
    barbearia_id: int,
    db: Session = Depends(get_db)
):
    """Lista barbeiros que estão presentes fisicamente na barbearia"""
    # Buscar todos os barbeiros que estão presentes nesta barbearia
    barbeiros_presentes = db.query(models.Usuario).filter(
        models.Usuario.tipo == 'barbeiro',
        models.Usuario.presente_em_local == True,
        models.Usuario.barbearia_atual_id == barbearia_id
    ).all()
    
    resultado = []
    
    for barbeiro in barbeiros_presentes:
        # Buscar cadeira que o barbeiro está usando
        cadeira = db.query(models.Cadeira).filter(
            models.Cadeira.freelancer_id == barbeiro.id,
            models.Cadeira.barbearia_id == barbearia_id,
            models.Cadeira.status == models.StatusCadeira.OCUPADA
        ).first()
        
        # Buscar serviço/agendamento ativo
        chamado_ativo = None
        if cadeira and cadeira.chamado_id:
            chamado_ativo = db.query(models.Chamado).filter(
                models.Chamado.id == cadeira.chamado_id
            ).first()

        # Proteção contra inconsistência: se a cadeira ficou ocupada com chamado
        # já concluído/cancelado, libera automaticamente para não travar a UI.
        if cadeira and chamado_ativo and chamado_ativo.status in [
            models.StatusAgendamento.CONCLUIDO.value,
            models.StatusAgendamento.CANCELADO.value,
        ]:
            cadeira.status = models.StatusCadeira.DISPONIVEL
            cadeira.freelancer_id = None
            cadeira.chamado_id = None
            cadeira.liberada_em = datetime.now()
            db.commit()
            chamado_ativo = None
            cadeira = None
        
        # Calcular tempo presente
        tempo_presente = None
        if barbeiro.horario_chegada:
            delta = datetime.utcnow() - barbeiro.horario_chegada
            horas = int(delta.total_seconds() // 3600)
            minutos = int((delta.total_seconds() % 3600) // 60)
            tempo_presente = f"{horas}h {minutos}min" if horas > 0 else f"{minutos}min"
        
        resultado.append({
            "id": barbeiro.id,
            "nome": barbeiro.nome,
            "telefone": barbeiro.telefone,
            "foto_perfil": barbeiro.foto_perfil,
            "cadeira_numero": cadeira.numero if cadeira else None,
            "horario_chegada": barbeiro.horario_chegada,
            "tempo_presente": tempo_presente,
            "atendendo_cliente": chamado_ativo.cliente.nome if chamado_ativo and chamado_ativo.cliente else None,
            "servico": chamado_ativo.servico.nome if chamado_ativo and chamado_ativo.servico else None,
            "disponivel": barbeiro.disponivel and not chamado_ativo
        })
    
    return resultado


# --- ENDPOINTS DE BARBEARIA ---

@router.put("/barbearia/cadeira")
def atualizar_status_cadeira(livre: bool, token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    """Atualizar status da cadeira (livre/ocupada)"""
    user = get_current_user(token=token, db=db)
    
    user.cadeira_livre = livre
    db.commit()
    db.refresh(user)
    
    return {"cadeira_livre": user.cadeira_livre}

@router.post("/barbearia/servicos")
def criar_servico(servico: schemas.ServicoCreate, token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    """Criar novo serviço na barbearia"""
    user = get_current_user(token=token, db=db)
    
    barbearia = db.query(models.Barbearia).filter(models.Barbearia.usuario_id == user.id).first()
    if not barbearia:
        raise HTTPException(status_code=404, detail="Barbearia não encontrada para este usuário")

    novo_servico = models.Servico(
        nome=servico.nome,
        valor=servico.valor,
        barbearia_id=barbearia.id
    )
    db.add(novo_servico)
    db.commit()
    db.refresh(novo_servico)
    
    return novo_servico

@router.get("/usuarios/saldo")
def get_usuario_saldo(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    """Retorna o saldo disponível do usuário (apenas para barbeiros)"""
    user = get_current_user(token=token, db=db)
    
    if user.tipo != "barbeiro":
        raise HTTPException(status_code=403, detail="Apenas barbeiros podem consultar saldo")
    
    saldo_total = db.query(
        func.coalesce(func.sum(models.TransacaoFinanceira.valor), 0.0)
    ).filter(
        models.TransacaoFinanceira.recebedor_id == user.id,
        models.TransacaoFinanceira.tipo == models.TipoTransacao.COMISSAO_FREELANCER.value,
        models.TransacaoFinanceira.status_repasse == "concluido",
    ).scalar() or 0.0

    saldo_bloqueado = db.query(
        func.coalesce(func.sum(models.Saque.valor), 0.0)
    ).filter(
        models.Saque.usuario_id == user.id,
        models.Saque.status.in_(["pendente", "processando"]),
    ).scalar() or 0.0

    saldo_disponivel = max(float(saldo_total) - float(saldo_bloqueado), 0.0)
    
    return {
        "saldo_total": saldo_total,
        "saldo_bloqueado": saldo_bloqueado,
        "saldo_disponivel": saldo_disponivel,
        "usuario_id": user.id,
        "tipo": user.tipo
    }
