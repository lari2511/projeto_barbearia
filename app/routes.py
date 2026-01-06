# --- ARQUIVO: app/routes.py ---
# Responsável pelos endpoints de autenticação e negócio

import os
import secrets
from dotenv import load_dotenv

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import timedelta
from passlib.context import CryptContext
from datetime import datetime
from jose import JWTError, jwt

from . import models, schemas
from .database import get_db
from .email_utils import send_email

# Carrega variáveis do arquivo .env
load_dotenv()

router = APIRouter()

# --- Configuração de Segurança ---
SECRET_KEY = os.getenv("SECRET_KEY", "INSEGURO_MUDE_ISSO_AGORA")
ALGORITHM = os.getenv("ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_DAYS = int(os.getenv("ACCESS_TOKEN_EXPIRE_DAYS", "7"))
REQUIRE_EMAIL_VERIFIED = os.getenv("REQUIRE_EMAIL_VERIFIED", "0") == "1"
VERIFICATION_LINK_BASE = os.getenv(
    "VERIFICATION_LINK_BASE",
    "http://localhost:8000/api/v1/email/verificar?token=",
)

pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")

from fastapi.security import OAuth2PasswordBearer
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# --- Funções Auxiliares ---

def calcular_split_pagamento(valor_total: float) -> dict:
    """
    Calcula o split de pagamento baseado em 15% plataforma, 45% freelancer, 40% dono.
    
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
    comissao_plataforma = round(valor_total * 0.15, 2)
    valor_freelancer = round(valor_total * 0.45, 2)
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
    
    # Procura por conflitos com agendamentos do mesmo barbeiro
    conflito = db.query(models.Chamado).filter(
        and_(
            models.Chamado.barbeiro_id == barbeiro_id,
            models.Chamado.status != models.StatusAgendamento.CANCELADO.value,  # Ignora cancelados
            
            # Lógica mágica de sobreposição:
            # Se o novo agendamento começa antes do fim do existente AND termina depois do início
            models.Chamado.data_hora_inicio < fim,
            models.Chamado.data_hora_fim > inicio
        )
    ).first()
    
    # Se achou conflito, retorna False (não disponível)
    if conflito:
        return False
    return True  # Está livre!

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(days=ACCESS_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


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
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Credenciais inválidas",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: int = int(payload.get("sub"))
        if user_id is None:
            raise credentials_exception
    except (JWTError, ValueError):
        raise credentials_exception
    
    user = db.query(models.Usuario).filter(models.Usuario.id == user_id).first()
    if user is None:
        raise credentials_exception
    return user

# --- ENDPOINTS DE CADASTRO ---

@router.post("/clientes/", response_model=schemas.UsuarioPublic)
def cadastrar_cliente(cliente: schemas.ClienteCreate, db: Session = Depends(get_db)):
    """Cadastrar novo cliente"""
    usuario_existente = db.query(models.Usuario).filter(models.Usuario.email == cliente.email).first()
    if usuario_existente:
        raise HTTPException(status_code=400, detail="Email já cadastrado")
    
    token_verificacao = secrets.token_urlsafe(32)
    novo_usuario = models.Usuario(
        email=cliente.email,
        nome=cliente.nome,
        senha_hash=get_password_hash(cliente.senha),
        telefone=cliente.telefone,
        cpf=cliente.cpf,
        tipo="cliente",
        token_verificacao=token_verificacao,
    )
    db.add(novo_usuario)
    db.commit()
    db.refresh(novo_usuario)
    dispatch_verification_email(novo_usuario)
    return novo_usuario

@router.post("/barbeiros/", response_model=schemas.UsuarioPublic)
def cadastrar_barbeiro(barbeiro: schemas.BarbeiroCreate, db: Session = Depends(get_db)):
    """Cadastrar novo barbeiro"""
    usuario_existente = db.query(models.Usuario).filter(models.Usuario.email == barbeiro.email).first()
    if usuario_existente:
        raise HTTPException(status_code=400, detail="Email já cadastrado")
    
    token_verificacao = secrets.token_urlsafe(32)
    novo_usuario = models.Usuario(
        email=barbeiro.email,
        nome=barbeiro.nome,
        senha_hash=get_password_hash(barbeiro.senha),
        telefone=barbeiro.telefone,
        cpf=barbeiro.cpf,
        tipo="barbeiro",
        token_verificacao=token_verificacao,
    )
    db.add(novo_usuario)
    db.commit()
    db.refresh(novo_usuario)
    dispatch_verification_email(novo_usuario)
    return novo_usuario

@router.post("/barbearias/")
def cadastrar_barbearia(barbearia: schemas.BarbeariaCreate, db: Session = Depends(get_db)):
    """Cadastrar nova barbearia e vincular usuário/barbearia"""
    usuario_existente = db.query(models.Usuario).filter(models.Usuario.email == barbearia.email).first()
    if usuario_existente:
        raise HTTPException(status_code=400, detail="Email já cadastrado")

    token_verificacao = secrets.token_urlsafe(32)
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

    dispatch_verification_email(novo_usuario)

    return {"usuario": novo_usuario, "barbearia": nova_barbearia}

# --- ENDPOINTS DE LOGIN ---

@router.post("/login/cliente/")
def login_cliente(dados: schemas.Login, db: Session = Depends(get_db)):
    """Login para cliente"""
    usuario = db.query(models.Usuario).filter(
        models.Usuario.email == dados.email,
        models.Usuario.tipo == "cliente"
    ).first()
    
    if not usuario or not verify_password(dados.senha, usuario.senha_hash):
        raise HTTPException(status_code=401, detail="Email ou senha incorretos")

    if REQUIRE_EMAIL_VERIFIED and not usuario.email_verificado:
        raise HTTPException(
            status_code=403,
            detail="Email não verificado. Verifique sua caixa de entrada ou reenvie o link.",
        )

    if REQUIRE_EMAIL_VERIFIED and not usuario.email_verificado:
        raise HTTPException(
            status_code=403,
            detail="Email não verificado. Verifique sua caixa de entrada ou reenvie o link.",
        )

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
def login_barbeiro(dados: schemas.Login, db: Session = Depends(get_db)):
    """Login para barbeiro"""
    usuario = db.query(models.Usuario).filter(
        models.Usuario.email == dados.email,
        models.Usuario.tipo == "barbeiro"
    ).first()
    
    if not usuario or not verify_password(dados.senha, usuario.senha_hash):
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
def login_barbearia(dados: schemas.Login, db: Session = Depends(get_db)):
    """Login para barbearia"""
    print(f"🔍 LOGIN BARBEARIA - Email: {dados.email}")
    
    usuario = db.query(models.Usuario).filter(
        models.Usuario.email == dados.email,
        models.Usuario.tipo == "barbearia"
    ).first()
    
    if not usuario:
        print(f"❌ Usuário não encontrado: {dados.email}")
        raise HTTPException(status_code=401, detail="Email ou senha incorretos")
    
    print(f"✅ Usuário encontrado: {usuario.nome} (tipo: {usuario.tipo})")
    senha_ok = verify_password(dados.senha, usuario.senha_hash)
    print(f"🔐 Senha válida: {senha_ok}")
    
    if not senha_ok:
        print(f"❌ Senha incorreta para {dados.email}")
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
        raise HTTPException(status_code=404, detail="Barbearia não encontrada")
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
    
    # ✅ GUARDIÃO 1: Validar data/hora do agendamento
    if not chamado.data_hora_inicio:
        raise HTTPException(status_code=400, detail="Data e hora de início obrigatórias")
    
    # Calcular hora de término baseado na duração do serviço
    # Se não tiver duração, usa 30 minutos como padrão
    duracao_minutos = servico.duracao_minutos if hasattr(servico, 'duracao_minutos') and servico.duracao_minutos else 30
    hora_fim = chamado.data_hora_inicio + timedelta(minutes=duracao_minutos)
    
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
                detail="Poxa! Esse horário já foi reservado por outro cliente. Que tal tentar outro horário?"
            )
    
    # Calcular split do pagamento (snapshot financeiro)
    split = calcular_split_pagamento(servico.valor)
    
    novo_chamado = models.Chamado(
        cliente_id=user.id,
        barbeiro_id=chamado.barbeiro_id,  # Usar o barbeiro selecionado pelo cliente
        servico_id=chamado.servico_id,
        barbearia_id=chamado.barbearia_id,
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
        tipo="chamado"
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

@router.get("/chamados/abertos")
def listar_chamados_abertos(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    """Listar chamados abertos (para barbeiros)"""
    user = get_current_user(token=token, db=db)
    if user.tipo != "barbeiro":
        raise HTTPException(status_code=403, detail="Apenas barbeiros podem ver chamados abertos")
    # Buscar chamados PENDENTE que são para este barbeiro
    chamados = db.query(models.Chamado).filter(
        models.Chamado.status == models.StatusAgendamento.PENDENTE.value,
        models.Chamado.barbeiro_id == user.id
    ).all()
    
    resultado = []
    for c in chamados:
        cliente = db.query(models.Usuario).filter(models.Usuario.id == c.cliente_id).first()
        servico = db.query(models.Servico).filter(models.Servico.id == c.servico_id).first()
        barbearia = db.query(models.Barbearia).filter(models.Barbearia.id == c.barbearia_id).first()
        
        resultado.append({
            "id": c.id,
            "nome_cliente": cliente.nome if cliente else "Desconhecido",
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
        
        resultado.append({
            "id": c.id,
            "descricao": servico.nome if servico else "Serviço",
            "valor": servico.valor if servico else 0,
            "nome_barbearia": barbearia.nome if barbearia else "Barbearia",
            "endereco": barbearia.endereco if barbearia else "Não informado",
            "status": c.status
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
        
        resultado.append({
            "id": chamado.id,
            "cliente_nome": cliente.nome if cliente else "Desconhecido",
            "cliente_telefone": cliente.telefone if cliente else "",
            "servico": servico.nome if servico else "Serviço",
            "valor": servico.valor if servico else 0,
            "status": chamado.status,
            "data_agendamento": chamado.data_agendamento.isoformat() if chamado.data_agendamento else None,
            "criado_em": chamado.criado_em.isoformat(),
            "barbearia_nome": barbearia.nome if barbearia else "Barbearia"
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
    
    status_anterior = chamado.status
    chamado.barbeiro_id = user.id
    chamado.status = models.StatusAgendamento.CONFIRMADO.value  # Usar Enum
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
        tipo="chamado"
    )
    db.add(notificacao)
    db.commit()
    
    return {"id": chamado.id, "status": chamado.status}

@router.put("/chamados/{id}/barbearia/aceitar")
def barbearia_aceitar_chamado(id: int, token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    """Barbearia confirma disponibilidade de cadeira para o agendamento"""
    user = get_current_user(token=token, db=db)
    if user.tipo != "barbearia":
        raise HTTPException(status_code=403, detail="Apenas barbearias podem confirmar disponibilidade")
    
    chamado = db.query(models.Chamado).filter(models.Chamado.id == id).first()
    if not chamado:
        raise HTTPException(status_code=404, detail="Chamado não encontrado")
    
    # Verificar se o chamado é desta barbearia
    barbearia = db.query(models.Barbearia).filter(models.Barbearia.usuario_id == user.id).first()
    if not barbearia or chamado.barbearia_id != barbearia.id:
        raise HTTPException(status_code=403, detail="Este agendamento não é da sua barbearia")
    
    if chamado.status != models.StatusAgendamento.CONFIRMADO.value:
        raise HTTPException(status_code=400, detail="Apenas agendamentos confirmados pelo barbeiro podem ser aceitos")
    
    status_anterior = chamado.status
    chamado.status = models.StatusAgendamento.CONCLUIDO.value  # Marca como aceito pela barbearia
    db.commit()
    db.refresh(chamado)
    
    # Criar histórico
    historico = models.ChamadoHistorico(
        chamado_id=chamado.id,
        status_anterior=status_anterior,
        status_novo=models.StatusAgendamento.CONCLUIDO.value,
        usuario_id=user.id,
        observacao=f"Cadeira confirmada por {barbearia.nome}"
    )
    db.add(historico)
    
    # Notificar cliente
    notificacao = models.Notificacao(
        usuario_id=chamado.cliente_id,
        titulo="Cadeira Confirmada",
        mensagem=f"A barbearia {barbearia.nome} confirmou sua cadeira!",
        tipo="chamado"
    )
    db.add(notificacao)
    
    # Notificar barbeiro
    if chamado.barbeiro_id:
        notificacao_barbeiro = models.Notificacao(
            usuario_id=chamado.barbeiro_id,
            titulo="Cadeira Confirmada",
            mensagem=f"A barbearia {barbearia.nome} confirmou o agendamento!",
            tipo="chamado"
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
    
    chamado = db.query(models.Chamado).filter(models.Chamado.id == id).first()
    if not chamado:
        raise HTTPException(status_code=404, detail="Chamado não encontrado")
    
    # Verificar se o chamado é desta barbearia
    barbearia = db.query(models.Barbearia).filter(models.Barbearia.usuario_id == user.id).first()
    if not barbearia or chamado.barbearia_id != barbearia.id:
        raise HTTPException(status_code=403, detail="Este agendamento não é da sua barbearia")
    
    status_anterior = chamado.status
    chamado.status = models.StatusAgendamento.CANCELADO.value  # Marca como cancelado
    db.commit()
    db.refresh(chamado)
    
    # Criar histórico
    historico = models.ChamadoHistorico(
        chamado_id=chamado.id,
        status_anterior=status_anterior,
        status_novo=models.StatusAgendamento.CANCELADO.value,
        usuario_id=user.id,
        observacao=f"Recusado por {barbearia.nome} - sem cadeira disponível"
    )
    db.add(historico)
    
    # Notificar cliente
    notificacao = models.Notificacao(
        usuario_id=chamado.cliente_id,
        titulo="Agendamento Cancelado",
        mensagem=f"A barbearia {barbearia.nome} não tem cadeira disponível neste horário",
        tipo="chamado"
    )
    db.add(notificacao)
    
    # Notificar barbeiro
    if chamado.barbeiro_id:
        notificacao_barbeiro = models.Notificacao(
            usuario_id=chamado.barbeiro_id,
            titulo="Agendamento Cancelado",
            mensagem=f"A barbearia {barbearia.nome} cancelou o agendamento",
            tipo="chamado"
        )
        db.add(notificacao_barbeiro)
    
    db.commit()
    
    return {"id": chamado.id, "status": chamado.status}

@router.put("/chamados/{id}/finalizar")
def finalizar_chamado(id: int, token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    """Finalizar um chamado"""
    user = get_current_user(token=token, db=db)
    if user.tipo not in ("barbeiro", "barbearia"):
        raise HTTPException(status_code=403, detail="Apenas barbeiro/barbearia podem finalizar")
    
    chamado = db.query(models.Chamado).filter(models.Chamado.id == id).first()
    if not chamado:
        raise HTTPException(status_code=404, detail="Chamado não encontrado")
    
    status_anterior = chamado.status
    chamado.status = models.StatusAgendamento.CONCLUIDO.value  # Usar Enum
    chamado.concluido_em = datetime.utcnow()
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
        tipo="chamado"
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
    
    barbeiros = db.query(models.Usuario).filter(
        models.Usuario.tipo == "barbeiro",
        models.Usuario.latitude.isnot(None),
        models.Usuario.longitude.isnot(None)
    ).all()
    
    # Filtrar por distância
    barbeiros_proximos = []
    for b in barbeiros:
        distancia = haversine(longitude, latitude, b.longitude, b.latitude)
        if distancia <= raio_km:
            barbeiros_proximos.append({
                "id": b.id,
                "nome": b.nome,
                "telefone": b.telefone,
                "endereco": b.endereco,
                "latitude": b.latitude,
                "longitude": b.longitude,
                "distancia_km": round(distancia, 2),
                "documento_verificado": b.documento_verificado
            })
    
    # Ordenar por distância
    barbeiros_proximos.sort(key=lambda x: x["distancia_km"])
    
    return barbeiros_proximos

@router.get("/barbeiros/todos")
def listar_todos_barbeiros(db: Session = Depends(get_db)):
    """Listar todos os barbeiros cadastrados"""
    barbeiros = db.query(models.Usuario).filter(
        models.Usuario.tipo == "barbeiro"
    ).all()
    
    return [
        {
            "id": b.id,
            "nome": b.nome,
            "telefone": b.telefone,
            "endereco": b.endereco,
            "documento_verificado": b.documento_verificado
        }
        for b in barbeiros
    ]

@router.get("/barbeiro/{barbeiro_id}/barbearias")
def listar_barbearias_do_barbeiro(barbeiro_id: int, db: Session = Depends(get_db)):
    """Listar barbearias onde um barbeiro específico atende"""
    # Por enquanto retorna todas as barbearias
    # TODO: Implementar relacionamento barbeiro-barbearias
    barbearias = db.query(models.Barbearia).all()
    return [
        {
            "id": b.id,
            "nome": b.nome,
            "endereco": b.endereco,
            "telefone": b.telefone,
            "cadeira_livre": b.cadeira_livre
        }
        for b in barbearias
    ]

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
        
        result.append({
            "id": ag.id,
            "nome_cliente": cliente.nome if cliente else "Cliente",
            "nome_barbeiro": barbeiro.nome if barbeiro else "Aguardando",
            "descricao": servico.nome if servico else "Serviço",
            "data_hora_inicio": ag.data_hora_inicio,
            "status": ag.status
        })
    
    return result

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
