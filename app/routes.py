# --- ARQUIVO: app/routes.py ---
# Responsável pelos endpoints de autenticação e negócio

import os
import secrets
import math
import json
from dotenv import load_dotenv
from urllib.request import urlopen

from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks, Request
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_, func, case
from datetime import timedelta
from passlib.context import CryptContext
from passlib.exc import UnknownHashError
from datetime import datetime
from jose import JWTError, jwt
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel

from . import models, schemas
from .database import get_db
from .email_utils import send_email
from .email_send import send_verification_email
from . import firebase_config
from .realtime import broadcast_event

# Carrega variáveis do arquivo .env
load_dotenv()


def env_bool(key: str, default: bool = False) -> bool:
    val = os.getenv(key)
    if val is None:
        return default
    return str(val).strip().lower() in {"1", "true", "yes", "on"}


def normalize_email(value: str) -> str:
    return (value or "").strip().lower()

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
            models.Chamado.status.in_([
                models.StatusAgendamento.CONFIRMADO.value,
                models.StatusAgendamento.EM_ATENDIMENTO.value,
            ]),
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


def _contar_chamados_ativos_fila(db: Session, barbeiro_id: int, barbearia_id: int) -> int:
    return db.query(models.Chamado).filter(
        models.Chamado.barbeiro_id == barbeiro_id,
        models.Chamado.barbearia_id == barbearia_id,
        models.Chamado.status.in_([
            models.StatusAgendamento.PENDENTE.value,
            models.StatusAgendamento.CONFIRMADO.value,
            models.StatusAgendamento.EM_ATENDIMENTO.value,
        ])
    ).count()


def _buscar_proximo_chamado_fila(db: Session, barbeiro_id: int, barbearia_id: int, exclude_id: int = None):
    query = db.query(models.Chamado).filter(
        models.Chamado.barbeiro_id == barbeiro_id,
        models.Chamado.barbearia_id == barbearia_id,
        models.Chamado.status.in_([
            models.StatusAgendamento.PENDENTE.value,
            models.StatusAgendamento.CONFIRMADO.value,
        ])
    )
    if exclude_id is not None:
        query = query.filter(models.Chamado.id != exclude_id)
    return query.order_by(models.Chamado.criado_em.asc(), models.Chamado.id.asc()).first()


def haversine(lon1: float, lat1: float, lon2: float, lat2: float) -> float:
    """
    Calcula distância em km entre dois pontos (lat/lon) usando a fórmula de Haversine.
    
    Args:
        lon1: Longitude do primeiro ponto
        lat1: Latitude do primeiro ponto
        lon2: Longitude do segundo ponto
        lat2: Latitude do segundo ponto
        
    Returns:
        Distância em quilômetros
    """
    lon1, lat1, lon2, lat2 = map(math.radians, [lon1, lat1, lon2, lat2])
    dlon = lon2 - lon1
    dlat = lat2 - lat1
    a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
    c = 2 * math.asin(math.sqrt(a))
    km = 6371 * c
    return km


def _calcular_taxa_cancelamento(chamado: models.Chamado, barbeiro: models.Usuario | None) -> tuple[float, int, str]:
    """
    Calcula a taxa de cancelamento conforme as regras:
    1. Se cancelar ANTES do barbeiro aceitar (status PENDENTE): taxa = 0
    2. Se freelancer está PRESENTE na barbearia: taxa = 8.00 (sempre)
    3. Se tempo desde match <= 5 min: taxa = 0
    4. Se tempo desde match > 5 min: taxa = 8.00
    """
    janela_gratuita_minutos = 5
    taxa_padrao = 8.0

    # ✅ REGRA 1: Se ainda está pendente (barbeiro não aceitou), cancelamento é grátis
    if chamado.status == models.StatusAgendamento.PENDENTE.value:
        return 0.0, 0, "Cancelamento antes da confirmação do barbeiro"

    # ✅ REGRA 2: Se freelancer está PRESENTE na barbearia, taxa é sempre 8.00
    if barbeiro and barbeiro.presente_em_local and barbeiro.barbearia_atual_id == chamado.barbearia_id:
        return taxa_padrao, 0, "Freelancer presente na barbearia - taxa aplicada"

    # ✅ REGRA 3 & 4: Calcular tempo desde o match (horario_match)
    # Se não há horario_match, usar aprovado_barbeiro_em como fallback (compatibilidade)
    referencia_inicio = chamado.horario_match or chamado.aprovado_barbeiro_em or chamado.criado_em or datetime.utcnow()
    diferenca_minutos = max(0, int((datetime.utcnow() - referencia_inicio).total_seconds() // 60))

    if diferenca_minutos > janela_gratuita_minutos:
        return taxa_padrao, diferenca_minutos, "Cancelamento fora da janela gratuita de 5 minutos - taxa aplicada"

    return 0.0, diferenca_minutos, "Cancelamento dentro da janela gratuita de 5 minutos"


def _iniciar_atendimento_chamado(db: Session, chamado: models.Chamado, barbeiro: models.Usuario):
    """Inicia atendimento de um chamado da fila e atualiza barbeiro/cadeira."""
    agora = datetime.now()

    servico = db.query(models.Servico).filter(models.Servico.id == chamado.servico_id).first()
    duracao_minutos = servico.duracao_minutos if (servico and servico.duracao_minutos) else 30

    chamado.status = models.StatusAgendamento.EM_ATENDIMENTO.value
    chamado.data_hora_inicio = agora
    chamado.data_hora_fim = agora + timedelta(minutes=duracao_minutos)

    barber = db.query(models.Usuario).filter(models.Usuario.id == barbeiro.id).first()
    if barber:
        barber.disponivel = False
        barber.em_atendimento = True
        barber.ocupado_ate = chamado.data_hora_fim

    cadeira = None
    if chamado.cadeira_id:
        cadeira = db.query(models.Cadeira).filter(models.Cadeira.id == chamado.cadeira_id).first()
        if cadeira:
            cadeira.status = models.StatusCadeira.OCUPADA
            cadeira.freelancer_id = barbeiro.id
            cadeira.chamado_id = chamado.id
            cadeira.ocupada_em = agora

    return servico, chamado, cadeira, agora


def _finalizar_chamado_e_avancar_fila(db: Session, chamado: models.Chamado, barbeiro: models.Usuario):
    status_anterior = chamado.status
    chamado.status = models.StatusAgendamento.CONCLUIDO.value
    chamado.data_hora_fim = datetime.now()

    cadeira_liberada_id = chamado.cadeira_id
    if cadeira_liberada_id:
        cadeira = db.query(models.Cadeira).filter(models.Cadeira.id == cadeira_liberada_id).first()
        if cadeira:
            cadeira.status = models.StatusCadeira.DISPONIVEL
            cadeira.freelancer_id = None
            cadeira.chamado_id = None
            cadeira.liberada_em = datetime.now()

    barber = db.query(models.Usuario).filter(models.Usuario.id == barbeiro.id).first()
    if barber:
        barber.disponivel = True
        barber.em_atendimento = False
        barber.ocupado_ate = None

    proximo = _buscar_proximo_chamado_fila(db, barbeiro.id, chamado.barbearia_id, exclude_id=chamado.id)
    if proximo:
        if not proximo.cadeira_id and cadeira_liberada_id:
            proximo.cadeira_id = cadeira_liberada_id
        servico_proximo, _, cadeira_proxima, agora = _iniciar_atendimento_chamado(db, proximo, barbeiro)
        db.add(models.ChamadoHistorico(
            chamado_id=proximo.id,
            status_anterior=proximo.status,
            status_novo=models.StatusAgendamento.EM_ATENDIMENTO.value,
            usuario_id=barbeiro.id,
            observacao=f"Fila avançou automaticamente após finalização de {chamado.id}"
        ))
        db.add(models.Notificacao(
            usuario_id=proximo.cliente_id,
            titulo="Seu atendimento começou",
            mensagem=f"O barbeiro {barbeiro.nome} começou seu atendimento agora.",
            tipo="chamado",
            referencia_id=proximo.id
        ))
        return {
            "status_anterior": status_anterior,
            "proximo": proximo,
            "servico_proximo": servico_proximo,
            "cadeira_proxima": cadeira_proxima,
            "agora": agora,
            "barbeiro": barber,
            "cadeira_liberada_id": cadeira_liberada_id,
        }

    return {
        "status_anterior": status_anterior,
        "proximo": None,
        "barbeiro": barber,
        "cadeira_liberada_id": cadeira_liberada_id,
    }


def calcular_distancia_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    # Calcula distância em km entre dois pontos via Haversine.
    # Se alguma coordenada estiver ausente ou inválida, retorna 0.0 para evitar resultados errôneos.
    try:
        if lat1 is None or lon1 is None or lat2 is None or lon2 is None:
            return 0.0

        # Valores não numéricos devem ser tratados
        lat1 = float(lat1); lon1 = float(lon1); lat2 = float(lat2); lon2 = float(lon2)
    except Exception:
        return 0.0

    raio_terra_km = 6371.0

    lat1_rad = math.radians(lat1)
    lon1_rad = math.radians(lon1)
    lat2_rad = math.radians(lat2)
    lon2_rad = math.radians(lon2)

    delta_lat = lat2_rad - lat1_rad
    delta_lon = lon2_rad - lon1_rad

    a = (
        math.sin(delta_lat / 2) ** 2
        + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(delta_lon / 2) ** 2
    )
    c = 2 * math.asin(math.sqrt(a))
    return round(raio_terra_km * c, 3)


def estimar_tempo_minutos(distancia_km: float, velocidade_media_kmh: float = 30.0) -> int:
    # Estima ETA em minutos com velocidade média urbana.
    if distancia_km <= 0:
        return 0
    if velocidade_media_kmh <= 0:
        velocidade_media_kmh = 30.0
    return max(1, int(round((distancia_km / velocidade_media_kmh) * 60)))


class AtualizarPosicaoTrackingRequest(BaseModel):
    latitude: float
    longitude: float


class AtualizarLocalizacaoCompatRequest(BaseModel):
    latitude: float
    longitude: float
    chamado_id: int | None = None


def _calcular_eta_osrm_minutos(
    origem_lat: float,
    origem_lon: float,
    destino_lat: float,
    destino_lon: float,
) -> int | None:
    """Calcula ETA via OSRM público; retorna None em falha para usar fallback."""
    try:
        url = (
            "http://router.project-osrm.org/route/v1/driving/"
            f"{origem_lon},{origem_lat};{destino_lon},{destino_lat}?overview=false"
        )
        with urlopen(url, timeout=2.5) as response:
            payload = json.loads(response.read().decode("utf-8"))

        routes = payload.get("routes") if isinstance(payload, dict) else None
        if not routes:
            return None

        duration_seconds = routes[0].get("duration")
        if duration_seconds is None:
            return None

        return max(1, int(round(float(duration_seconds) / 60.0)))
    except Exception:
        return None


def _calcular_distancia_eta(
    origem_lat: float,
    origem_lon: float,
    destino_lat: float,
    destino_lon: float,
) -> tuple[float, int]:
    distancia_km = calcular_distancia_km(origem_lat, origem_lon, destino_lat, destino_lon)
    eta_osrm = _calcular_eta_osrm_minutos(origem_lat, origem_lon, destino_lat, destino_lon)
    if eta_osrm is not None:
        return distancia_km, eta_osrm
    return distancia_km, estimar_tempo_minutos(distancia_km, velocidade_media_kmh=40.0)


def _buscar_chamado_para_tracking(db: Session, chamado_id: int) -> models.Chamado:
    chamado = db.query(models.Chamado).filter(models.Chamado.id == chamado_id).first()
    if not chamado:
        raise HTTPException(status_code=404, detail="Chamado não encontrado")
    return chamado


def _normalizar_status_chamado(status: str | None) -> str:
    return str(status or "").strip().lower()


def _tracking_ativo_por_status(status: str | None) -> bool:
    return _normalizar_status_chamado(status) in {"confirmado", "aceito"}


def _validar_acesso_tracking(db: Session, user: models.Usuario, chamado: models.Chamado) -> None:
    if user.tipo == "cliente" and chamado.cliente_id == user.id:
        return
    if user.tipo == "barbeiro" and chamado.barbeiro_id == user.id:
        return
    if user.tipo == "barbearia":
        barbearia = db.query(models.Barbearia).filter(
            models.Barbearia.id == chamado.barbearia_id,
            models.Barbearia.usuario_id == user.id,
        ).first()
        if barbearia:
            return
    raise HTTPException(status_code=403, detail="Sem permissão para acessar o tracking deste chamado")


def _obter_ou_criar_agendamento_ativo(db: Session, chamado: models.Chamado) -> models.AgendamentoAtivo:
    ativo = db.query(models.AgendamentoAtivo).filter(
        models.AgendamentoAtivo.chamado_id == chamado.id
    ).first()

    cliente = db.query(models.Usuario).filter(models.Usuario.id == chamado.cliente_id).first()
    barbeiro = db.query(models.Usuario).filter(models.Usuario.id == chamado.barbeiro_id).first() if chamado.barbeiro_id else None

    if not ativo:
        ativo = models.AgendamentoAtivo(
            chamado_id=chamado.id,
            cliente_id=chamado.cliente_id,
            barbearia_id=chamado.barbearia_id,
            barbeiro_id=chamado.barbeiro_id,
            cliente_lat=cliente.latitude if cliente else None,
            cliente_lon=cliente.longitude if cliente else None,
            barbeiro_lat=barbeiro.latitude if barbeiro else None,
            barbeiro_lon=barbeiro.longitude if barbeiro else None,
            cliente_localizacao_em=datetime.utcnow() if cliente and cliente.latitude is not None and cliente.longitude is not None else None,
            barbeiro_localizacao_em=datetime.utcnow() if barbeiro and barbeiro.latitude is not None and barbeiro.longitude is not None else None,
        )
        db.add(ativo)
        db.flush()
    else:
        ativo.cliente_id = chamado.cliente_id
        ativo.barbearia_id = chamado.barbearia_id
        ativo.barbeiro_id = chamado.barbeiro_id

    return ativo


def _montar_payload_tracking(db: Session, chamado: models.Chamado, ativo: models.AgendamentoAtivo) -> dict:
    barbearia = db.query(models.Barbearia).filter(models.Barbearia.id == chamado.barbearia_id).first()
    cliente = db.query(models.Usuario).filter(models.Usuario.id == chamado.cliente_id).first()
    barbeiro = db.query(models.Usuario).filter(models.Usuario.id == chamado.barbeiro_id).first() if chamado.barbeiro_id else None

    cliente_lat = ativo.cliente_lat if ativo.cliente_lat is not None else (cliente.latitude if cliente else None)
    cliente_lon = ativo.cliente_lon if ativo.cliente_lon is not None else (cliente.longitude if cliente else None)
    barbeiro_lat = ativo.barbeiro_lat if ativo.barbeiro_lat is not None else (barbeiro.latitude if barbeiro else None)
    barbeiro_lon = ativo.barbeiro_lon if ativo.barbeiro_lon is not None else (barbeiro.longitude if barbeiro else None)

    cliente_distancia = None
    cliente_eta = None
    barbeiro_distancia = None
    barbeiro_eta = None

    if barbearia and barbearia.latitude is not None and barbearia.longitude is not None:
        if cliente_lat is not None and cliente_lon is not None:
            cliente_distancia, cliente_eta = _calcular_distancia_eta(
                cliente_lat,
                cliente_lon,
                barbearia.latitude,
                barbearia.longitude,
            )

        if barbeiro_lat is not None and barbeiro_lon is not None:
            barbeiro_distancia, barbeiro_eta = _calcular_distancia_eta(
                barbeiro_lat,
                barbeiro_lon,
                barbearia.latitude,
                barbearia.longitude,
            )

    return {
        "chamado_id": chamado.id,
        "status": chamado.status,
        "mostrar_mapa": _tracking_ativo_por_status(chamado.status),
        "cliente_chegou": bool(getattr(chamado, "cliente_chegou", False)),
        "barbeiro_chegou": bool(getattr(chamado, "barbeiro_chegou", False)),
        "barbearia": {
            "id": barbearia.id if barbearia else chamado.barbearia_id,
            "nome": barbearia.nome if barbearia else None,
            "endereco": barbearia.endereco if barbearia else None,
            "telefone": barbearia.telefone if barbearia else None,
            "latitude": barbearia.latitude if barbearia else None,
            "longitude": barbearia.longitude if barbearia else None,
        },
        "coordenadas_cliente": {
            "lat": cliente_lat,
            "lon": cliente_lon,
            "atualizado_em": ativo.cliente_localizacao_em.isoformat() if ativo.cliente_localizacao_em else None,
        },
        "coordenadas_barbeiro": {
            "lat": barbeiro_lat,
            "lon": barbeiro_lon,
            "atualizado_em": ativo.barbeiro_localizacao_em.isoformat() if ativo.barbeiro_localizacao_em else None,
        },
        "cliente_distancia_ate_barbearia_km": cliente_distancia,
        "cliente_eta_ate_barbearia_min": cliente_eta,
        "freelancer_distancia_ate_barbearia_km": barbeiro_distancia,
        "freelancer_eta_ate_barbearia_min": barbeiro_eta,
        "atualizado_em": datetime.utcnow().isoformat(),
    }

def _esta_na_janela_liberacao_antecipada(barbeiro: models.Usuario, agora: datetime | None = None, janela_min: int = 10) -> bool:
    if not barbeiro:
        return False

    ocupado_ate = getattr(barbeiro, 'ocupado_ate', None)
    if not ocupado_ate:
        return False

    referencia = agora or datetime.now()
    if ocupado_ate <= referencia:
        return False

    minutos_restantes = (ocupado_ate - referencia).total_seconds() / 60
    return minutos_restantes <= janela_min

def esta_em_servico_agora(db: Session, barbeiro_id: int) -> bool:
    # Verifica se o barbeiro está em um serviço ATIVO no momento.
    from datetime import datetime
    from sqlalchemy import and_
    
    agora = datetime.now()
    
    # Verifica se o barbeiro tem ocupado_ate definido e ainda não passou.
    # Regra de negócio: na janela final (<=10 min) ele já pode receber próximo chamado.
    barbeiro = db.query(models.Usuario).filter(models.Usuario.id == barbeiro_id).first()
    if barbeiro and barbeiro.ocupado_ate:
        if barbeiro.ocupado_ate > agora:
            if _esta_na_janela_liberacao_antecipada(barbeiro, agora=agora, janela_min=10):
                return False
            return True  # Ainda está ocupado
    
    # Procura por agendamento ativo no momento (apenas CONFIRMADO)
    servico_ativo = db.query(models.Chamado).filter(
        models.Chamado.barbeiro_id == barbeiro_id,
        models.Chamado.status == models.StatusAgendamento.CONFIRMADO.value,
        models.Chamado.data_hora_inicio <= agora,
        models.Chamado.data_hora_fim >= agora
    ).first()
    
    return servico_ativo is not None


@router.get("/barbeiro/{barbeiro_id}/pode-receber-chamado")
def pode_receber_chamado(barbeiro_id: int, db: Session = Depends(get_db)):
    """Verifica se um barbeiro pode receber novo chamado imediatamente.

    Regras:
    - Se `ocupado_ate` não estiver definido ou já passou -> disponível
    - Se `ocupado_ate` definido e faltar 10 minutos ou menos -> disponível (liberação antecipada)
    - Caso contrário -> não disponível e retorna minutos restantes até permitir
    """
    barbeiro = db.query(models.Usuario).filter(models.Usuario.id == barbeiro_id).first()
    agora = datetime.now()
    if not barbeiro:
        raise HTTPException(status_code=404, detail="Barbeiro não encontrado")

    ocupado_ate = getattr(barbeiro, 'ocupado_ate', None)
    if not ocupado_ate:
        return {"disponivel": True}

    if ocupado_ate <= agora:
        # Já passou
        return {"disponivel": True}

    minutos_restantes = (ocupado_ate - agora).total_seconds() / 60
    if minutos_restantes <= 10:
        return {
            "disponivel": True,
            "aviso": f"Finalizando corte em {int(round(minutos_restantes))} min. Já pode aceitar o próximo."
        }

    return {
        "disponivel": False,
        "minutos_para_liberar": int(math.ceil(minutos_restantes - 10))
    }

def verify_password(plain_password: str, hashed_password: str) -> bool:
    if not hashed_password:
        return False
    try:
        # Trunca para 72 bytes (limite do bcrypt) antes de verificar
        if len(plain_password.encode('utf-8')) > 72:
            plain_password = plain_password.encode('utf-8')[:72].decode('utf-8', errors='ignore')
        return pwd_context.verify(plain_password, hashed_password)
    except (UnknownHashError, ValueError):
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
    # Token JWT específico para verificação de e-mail (válido por 24h)
    expire = datetime.now() + timedelta(hours=EMAIL_TOKEN_EXPIRE_HOURS)
    # Colocamos um 'type' para diferenciar de tokens de login
    to_encode = {"sub": email, "exp": expire, "type": "email_verification"}
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def verify_email_token(token: str) -> str | None:
    # Retorna o email se o token for válido.
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
    # Send email verification link if SMTP is configured.
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
    print(f"get_current_user - Token recebido: {token[:50]}...")
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Credenciais inválidas",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: int = int(payload.get("sub"))
        print(f"Token decodificado - User ID: {user_id}")
        if user_id is None:
            raise credentials_exception
    except (JWTError, ValueError) as e:
        print(f"Erro ao decodificar token: {e}")
        raise credentials_exception
    
    user = db.query(models.Usuario).filter(models.Usuario.id == user_id).first()
    if user is None:
        print(f"Usuário não encontrado: ID {user_id}")
        raise credentials_exception
    print(f"Usuário autenticado: {user.email} (tipo: {user.tipo})")
    return user

# --- ENDPOINTS DE CADASTRO ---

@router.post("/clientes/", response_model=schemas.RegistroResponse)
def cadastrar_cliente(
    cliente: schemas.ClienteCreate, 
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    # Cadastrar novo cliente; envia e-mail de verificação automaticamente.
    email_normalizado = normalize_email(cliente.email)
    usuario_existente = db.query(models.Usuario).filter(
        func.lower(models.Usuario.email) == email_normalizado
    ).first()
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
    token_verificacao = create_email_verification_token(email_normalizado)
    
    novo_usuario = models.Usuario(
        email=email_normalizado,
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
    # Enviar push para o cliente informando conclusão (se disponível)
    try:
        cliente = db.query(models.Usuario).filter(models.Usuario.id == chamado.cliente_id).first()
        if cliente and getattr(cliente, 'device_token', None) and firebase_config.FIREBASE_DISPONIVEL:
            try:
                msg = firebase_config.messaging.Message(
                    notification=firebase_config.messaging.Notification(
                        title="Serviço Concluído",
                        body="Seu serviço foi concluído! Não esqueça de avaliar."
                    ),
                    data={"tipo": "chamado_concluido", "chamado_id": str(chamado.id)},
                    token=cliente.device_token
                )
                firebase_config.messaging.send(msg)
            except Exception:
                pass
    except Exception:
        pass
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
    # Cadastrar novo barbeiro; envia e-mail de verificação automaticamente.
    email_normalizado = normalize_email(barbeiro.email)
    usuario_existente = db.query(models.Usuario).filter(
        func.lower(models.Usuario.email) == email_normalizado
    ).first()
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
    token_verificacao = create_email_verification_token(email_normalizado)
    
    novo_usuario = models.Usuario(
        email=email_normalizado,
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
    # Cadastrar nova barbearia e vincular usuário/barbearia.
    email_normalizado = normalize_email(barbearia.email)
    usuario_existente = db.query(models.Usuario).filter(
        func.lower(models.Usuario.email) == email_normalizado
    ).first()
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
    token_verificacao = create_email_verification_token(email_normalizado)
    
    novo_usuario = models.Usuario(
        email=email_normalizado,
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
    # Login para cliente.
    email = normalize_email(form_data.username)
    senha = form_data.password
    
    usuario = db.query(models.Usuario).filter(
        func.lower(models.Usuario.email) == email,
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
    # Login para barbeiro.
    email = normalize_email(form_data.username)
    senha = form_data.password
    
    usuario = db.query(models.Usuario).filter(
        func.lower(models.Usuario.email) == email,
        models.Usuario.tipo == "barbeiro"
    ).first()
    
    if not usuario or not verify_password(senha, usuario.senha_hash):
        raise HTTPException(status_code=401, detail="Email ou senha incorretos")

    if REQUIRE_EMAIL_VERIFIED and not usuario.email_verificado:
        raise HTTPException(
            status_code=403,
            detail="Email não verificado. Verifique sua caixa de entrada ou reenvie o link.",
        )

    if not usuario.perfil_aprovado:
        raise HTTPException(
            status_code=403,
            detail="Perfil em análise pela equipe. Aguarde aprovação do administrador.",
        )
    
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
    # Login para barbearia.
    email = normalize_email(form_data.username)
    senha = form_data.password
    
    print(f"🔍 LOGIN BARBEARIA - Email: {email}")
    
    usuario = db.query(models.Usuario).filter(
        func.lower(models.Usuario.email) == email,
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

    if REQUIRE_EMAIL_VERIFIED and not usuario.email_verificado:
        raise HTTPException(
            status_code=403,
            detail="Email não verificado. Verifique sua caixa de entrada ou reenvie o link.",
        )

    if not usuario.perfil_aprovado:
        raise HTTPException(
            status_code=403,
            detail="Perfil em análise pela equipe. Aguarde aprovação do administrador.",
        )
    
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
    # Login para admin.
    email = normalize_email(form_data.username)
    senha = form_data.password
    
    usuario = db.query(models.Usuario).filter(
        func.lower(models.Usuario.email) == email,
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
    # Listar todas as barbearias cadastradas.
    barbearias = db.query(models.Barbearia).all()
    return barbearias

@router.get("/barbearia/{id}/servicos")
def listar_servicos_barbearia(id: int, db: Session = Depends(get_db)):
    # Listar serviços de uma barbearia específica.
    servicos = db.query(models.Servico).filter(models.Servico.barbearia_id == id).all()
    return servicos




@router.get("/barbearia/minha")
def obter_minha_barbearia(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    # Retorna a barbearia vinculada ao usuário autenticado.
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
    # Criar novo chamado (agendamento).
    # Validar token e obter usuário
    user = get_current_user(token=token, db=db)
    
    # Buscar serviço e barbearia
    servico = db.query(models.Servico).filter(models.Servico.id == chamado.servico_id).first()
    barbearia = db.query(models.Barbearia).filter(models.Barbearia.id == chamado.barbearia_id).first()
    
    if not servico or not barbearia:
        raise HTTPException(status_code=404, detail="Serviço ou barbearia não encontrados")

    if servico.barbearia_id != barbearia.id:
        raise HTTPException(status_code=400, detail="Serviço não pertence a essa barbearia")

    if chamado.cliente_latitude is None or chamado.cliente_longitude is None:
        raise HTTPException(
            status_code=400,
            detail="A localização é obrigatória para realizar um chamado em tempo real."
        )

    user.latitude = chamado.cliente_latitude
    user.longitude = chamado.cliente_longitude
    print(f"[criar_chamado] cliente coords: {chamado.cliente_latitude},{chamado.cliente_longitude}")

    # Validação defensiva: evita criação para barbeiro diferente do selecionado na UI.
    if chamado.barbeiro_id and chamado.barbeiro_selecionado_id and chamado.barbeiro_id != chamado.barbeiro_selecionado_id:
        raise HTTPException(
            status_code=400,
            detail="Conflito no barbeiro selecionado. Atualize a tela e tente novamente."
        )

    if chamado.barbeiro_id:
        ativos = _contar_chamados_ativos_fila(db, chamado.barbeiro_id, chamado.barbearia_id)
        if ativos >= 2:
            raise HTTPException(
                status_code=400,
                detail="Este freelancer já está com 1 cliente em atendimento e 1 na fila. Tente novamente depois."
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
            
            if freelancer_perfil and getattr(freelancer_perfil, 'status_pausado', False):
                raise HTTPException(
                    status_code=400,
                    detail="Barbeiro está com atendimentos pausados no momento."
                )

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

    print(f"[criar_chamado] barbearia coords: {barbearia.latitude},{barbearia.longitude}")
    if barbearia.latitude == 0.0 and barbearia.longitude == 0.0:
        print("[criar_chamado] Atenção: barbearia tem coordenadas 0.0,0.0 - verifique cadastro")

    if barbearia.latitude is None or barbearia.longitude is None:
        raise HTTPException(
            status_code=400,
            detail="A barbearia não possui localização cadastrada"
        )

    distancia_cliente_km = haversine(
        chamado.cliente_longitude,
        chamado.cliente_latitude,
        barbearia.longitude,
        barbearia.latitude,
    )
    tempo_estimado_minutos_cliente = int((distancia_cliente_km / 40) * 60)
    enforce_distance_limit = env_bool("ENFORCE_DISTANCE_LIMIT", True)
    if enforce_distance_limit and tempo_estimado_minutos_cliente > 10:
        raise HTTPException(
            status_code=400,
            detail=f"Você está a aproximadamente {tempo_estimado_minutos_cliente} minutos da barbearia. Para chamar agora, fique a no máximo 10 minutos de distância."
        )
    
    # ✅ GUARDIÃO 2: Verificar se horário está disponível para o barbeiro
    # Nota: Apenas verifica se barbeiro foi especificado
    if chamado.barbeiro_id:
        # Primeiro, verificar ocupação direta do barbeiro (ocupado_ate)
        barbeiro_check = db.query(models.Usuario).filter(models.Usuario.id == chamado.barbeiro_id).first()
        agora = datetime.now()
        if barbeiro_check and getattr(barbeiro_check, 'ocupado_ate', None):
            try:
                if barbeiro_check.ocupado_ate > agora:
                    minutos_restantes = (barbeiro_check.ocupado_ate - chamado.data_hora_inicio).total_seconds() / 60
                    # Se faltar 10 minutos ou menos, permitimos criar chamado (liberação antecipada)
                    if minutos_restantes <= 10:
                        pass  # permitir, o chamado ficará na fila e será aceito quando possível
                    else:
                        raise HTTPException(
                            status_code=400,
                            detail=f"Barbeiro ainda ocupado por aproximadamente {int(math.ceil(minutos_restantes))} minutos. Tente novamente mais tarde."
                        )
            except Exception:
                # qualquer problema com cálculo, prosseguir para validação padrão
                pass

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
            models.Chamado.status.in_([
                models.StatusAgendamento.CONFIRMADO.value,
                models.StatusAgendamento.EM_ATENDIMENTO.value,
            ]),
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

    # Enviar push via Firebase para o barbeiro (se aplicável) e registrar notificação
    try:
        if novo_chamado.barbeiro_id:
            barbeiro = db.query(models.Usuario).filter(models.Usuario.id == novo_chamado.barbeiro_id).first()
            if barbeiro:
                # Criar notificação para barbeiro no banco
                notif_bar = models.Notificacao(
                    usuario_id=barbeiro.id,
                    titulo="Novo Chamado!",
                    mensagem=f"{user.nome} solicitou {servico.nome}",
                    tipo="novo_chamado",
                    referencia_id=novo_chamado.id
                )
                db.add(notif_bar)
                db.commit()

                # Enviar push se Firebase estiver configurado e houver device_token
                try:
                    token = getattr(barbeiro, 'device_token', None)
                    nome_barb = barbearia.nome if barbearia else None
                    if token:
                        firebase_config.enviar_notificacao_novo_chamado(token, user.nome, servico.nome, nome_barb)
                except Exception:
                    pass

        # Enviar push de confirmação para o cliente (quem criou o chamado)
        try:
            token_cli = getattr(user, 'device_token', None)
            if token_cli and firebase_config.FIREBASE_DISPONIVEL:
                # enviar notificação simples informando criação
                mensagem = firebase_config.messaging.Message(
                    notification=firebase_config.messaging.Notification(
                        title="Chamado criado",
                        body=f"Seu chamado para {servico.nome} foi criado com sucesso"
                    ),
                    data={"tipo": "chamado_criado", "chamado_id": str(novo_chamado.id)},
                    token=token_cli
                )
                try:
                    firebase_config.messaging.send(mensagem)
                except Exception:
                    pass
        except Exception:
            pass
    except Exception:
        # Não falhar a criação do chamado se notificação falhar
        pass
    
    return {
        "id": novo_chamado.id,
        "status": novo_chamado.status,
        "cliente_id": novo_chamado.cliente_id,
        "servico_id": novo_chamado.servico_id,
        "descricao": servico.nome,
        "valor": novo_chamado.valor_total if novo_chamado.valor_total is not None else servico.valor,
        "valor_total": novo_chamado.valor_total,
        "data_hora_inicio": novo_chamado.data_hora_inicio.isoformat() if novo_chamado.data_hora_inicio else None,
        "data_hora_fim": novo_chamado.data_hora_fim.isoformat() if novo_chamado.data_hora_fim else None,
        "cliente_latitude": chamado.cliente_latitude,
        "cliente_longitude": chamado.cliente_longitude,
        "rastreamento_ativo": True
    }

@router.get("/chamados/debug-abertos")
def debug_chamados_abertos(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    # DEBUG: Ver por que chamados nao aparecem.
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
    # Listar chamados abertos (para barbeiros).
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

    resultado = []
    for c in chamados_encontrados:
        servico = db.query(models.Servico).filter(models.Servico.id == c.servico_id).first()

        if c.barbeiro_id == user.id:
            deve_incluir = True
        elif user.presente_em_local and user.barbearia_atual_id:
            deve_incluir = True
        else:
            deve_incluir = not tipos_especialidade or (servico and servico.categoria in tipos_especialidade)

        if not deve_incluir:
            continue

        cliente = db.query(models.Usuario).filter(models.Usuario.id == c.cliente_id).first()
        barbearia = db.query(models.Barbearia).filter(models.Barbearia.id == c.barbearia_id).first()

        resultado.append({
            "id": c.id,
            "cliente_id": c.cliente_id,
            "barbeiro_id": c.barbeiro_id,
            "barbearia_id": c.barbearia_id,
            "servico_id": c.servico_id,
            "nome_cliente": cliente.nome if cliente else "Desconhecido",
            "cliente_telefone": cliente.telefone if cliente else "",
            "cliente_email": cliente.email if cliente else "",
            "cliente_latitude": cliente.latitude if cliente else None,
            "cliente_longitude": cliente.longitude if cliente else None,
            "descricao": servico.nome if servico else "Serviço",
            "valor": servico.valor if servico else 0,
            "endereco": cliente.endereco if cliente else "Não informado",
            "nome_barbearia": barbearia.nome if barbearia else "Barbearia",
            "endereco_barbearia": barbearia.endereco if barbearia else "",
            "barbearia_latitude": barbearia.latitude if barbearia else None,
            "barbearia_longitude": barbearia.longitude if barbearia else None,
            "barbearia_telefone": barbearia.telefone if barbearia else "",
            "status": c.status,
            "data_hora_inicio": c.data_hora_inicio.isoformat() if c.data_hora_inicio else None,
            "data_hora_fim": c.data_hora_fim.isoformat() if c.data_hora_fim else None,
        })

    return resultado

@router.get("/barbeiro/{barbeiro_id}/agendamentos")
def listar_agendamentos_barbeiro(barbeiro_id: int, db: Session = Depends(get_db)):
    # Lista todos os agendamentos de um barbeiro específico.
    
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
        cadeira = db.query(models.Cadeira).filter(models.Cadeira.id == chamado.cadeira_id).first() if chamado.cadeira_id else None

        duracao_minutos = (servico.duracao_minutos if servico and servico.duracao_minutos else 30)
        inicio_base = chamado.data_hora_inicio or chamado.data_agendamento or chamado.criado_em
        data_hora_fim_resolvida = chamado.data_hora_fim
        if not data_hora_fim_resolvida and inicio_base:
            data_hora_fim_resolvida = inicio_base + timedelta(minutes=duracao_minutos)
        
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
            "cadeira_id": chamado.cadeira_id,
            "cadeira_numero": cadeira.numero if cadeira else None,
            "data_hora_inicio": chamado.data_hora_inicio.isoformat() if chamado.data_hora_inicio else None,
            "duracao_minutos": duracao_minutos,
            "data_agendamento": chamado.data_agendamento.isoformat() if chamado.data_agendamento else None,
            "criado_em": chamado.criado_em.isoformat() if chamado.criado_em else None,
            "data_hora_fim": data_hora_fim_resolvida.isoformat() if data_hora_fim_resolvida else None,
            "barbearia_nome": barbearia.nome if barbearia else "Barbearia",
            "barbearia_endereco": barbearia.endereco if barbearia else "",
            "barbearia_latitude": barbearia.latitude if barbearia else None,
            "barbearia_longitude": barbearia.longitude if barbearia else None,
            "barbearia_telefone": barbearia.telefone if barbearia else "",
            "cliente_latitude": cliente.latitude if cliente else None,
            "cliente_longitude": cliente.longitude if cliente else None,
            "cliente_endereco": cliente.endereco if cliente else "",
            "avaliado": ja_avaliado
        })
    
    return resultado

@router.get("/barbeiro/agendamentos/meus")
def listar_meus_agendamentos(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    # Lista agendamentos do barbeiro autenticado (versão protegida por token).
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
    # Filtra agendamentos de um barbeiro por status, data, etc.
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
    # Atualiza o status do freelancer para controlar conflito de agenda.
    # Status possíveis: offline, online_region, present_local.
    # Se o status for present_local, barbearia_id é obrigatório.
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
    barbearia = None
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
        "present_local": f"PRESENTE EM {barbearia.nome if barbearia else 'BARBEARIA'}"
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
    # Atualiza a disponibilidade do barbeiro para aparecer nas proximidades.
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
    # Barbeiro sai da barbearia atual e muda seu status para OFFLINE.
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
    # Barbeiro aceita um chamado.
    user = get_current_user(token=token, db=db)
    if user.tipo != "barbeiro":
        raise HTTPException(status_code=403, detail="Apenas barbeiros podem aceitar chamados")

    carteira = db.query(models.CarteiraBarbeiro).filter(
        models.CarteiraBarbeiro.barbeiro_id == user.id
    ).first()
    if carteira:
        saldo = float(carteira.saldo or 0.0)
        limite = float(carteira.limite_negativo if carteira.limite_negativo is not None else -50.0)
        if saldo <= limite:
            raise HTTPException(
                status_code=403,
                detail=f"Carteira bloqueada por saldo devedor (R$ {saldo:.2f}). Quite a fatura para voltar a aceitar chamados.",
            )
    
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
            tipos_especialidade_normalizados = [str(tipo).strip().lower() for tipo in tipos_especialidade if tipo]
            categoria_servico = str(servico.categoria or '').strip().lower()

            # Compatibilidade:
            # - Se não há especialidades cadastradas, permite aceite.
            # - Categoria 'outros' não bloqueia aceite por especialidade.
            if (
                tipos_especialidade_normalizados
                and categoria_servico
                and categoria_servico != 'outros'
                and categoria_servico not in tipos_especialidade_normalizados
            ):
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
                models.Chamado.status.in_([
                    models.StatusAgendamento.CONFIRMADO.value,
                    models.StatusAgendamento.EM_ATENDIMENTO.value,
                ]),
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
    else:
        # Se o chamado não veio com cadeira definida, tenta alocar automaticamente
        # uma cadeira disponível da barbearia sem conflito de horário.
        cadeiras_disponiveis = db.query(models.Cadeira).filter(
            models.Cadeira.barbearia_id == chamado.barbearia_id,
            models.Cadeira.status == models.StatusCadeira.DISPONIVEL
        ).order_by(models.Cadeira.numero.asc()).all()

        cadeira_alocada = None
        for cadeira_candidata in cadeiras_disponiveis:
            if chamado.data_hora_inicio and chamado.data_hora_fim:
                conflito = db.query(models.Chamado).filter(
                    models.Chamado.cadeira_id == cadeira_candidata.id,
                    models.Chamado.status.in_([
                        models.StatusAgendamento.CONFIRMADO.value,
                        models.StatusAgendamento.EM_ATENDIMENTO.value,
                    ]),
                    models.Chamado.id != id,
                    models.Chamado.data_hora_inicio < chamado.data_hora_fim,
                    models.Chamado.data_hora_fim > chamado.data_hora_inicio
                ).first()
                if conflito:
                    continue

            cadeira_alocada = cadeira_candidata
            break

        if not cadeira_alocada:
            raise HTTPException(
                status_code=400,
                detail="Nenhuma cadeira disponível na barbearia para este horário."
            )

        chamado.cadeira_id = cadeira_alocada.id
    
    status_anterior = chamado.status
    chamado.barbeiro_id = user.id
    chamado.status = models.StatusAgendamento.CONFIRMADO.value  # Usar Enum
    chamado.observacao = None  # Limpar observação quando barbeiro aceita
    chamado.cliente_chegou = False
    chamado.barbeiro_chegou = False
    chamado.aprovado_barbeiro = True
    chamado.aprovado_barbeiro_em = datetime.utcnow()
    chamado.horario_match = datetime.utcnow()  # ✅ Iniciar contagem de 5 minutos para cancelamento

    # ✅ BLOQUEAR CADEIRA ASSOCIADA AO CHAMADO AO ACEITAR
    if chamado.cadeira_id:
        cadeira_aceita = db.query(models.Cadeira).filter(models.Cadeira.id == chamado.cadeira_id).first()
        if cadeira_aceita:
            cadeira_aceita.status = models.StatusCadeira.OCUPADA
            cadeira_aceita.freelancer_id = user.id
            cadeira_aceita.chamado_id = chamado.id
            cadeira_aceita.ocupada_em = datetime.now()
    
    # ✅ MARCAR BARBEIRO COMO RESERVADO PARA ESTA FILA
    if not barbeiro:
        raise HTTPException(status_code=500, detail="Erro ao recuperar dados do barbeiro")
    
    barbeiro.disponivel = False
    barbeiro.em_atendimento = False
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

    # Enviar push FCM para o cliente (se disponível)
    try:
        cliente = db.query(models.Usuario).filter(models.Usuario.id == chamado.cliente_id).first()
        if cliente and getattr(cliente, 'device_token', None) and firebase_config.FIREBASE_DISPONIVEL:
            try:
                msg = firebase_config.messaging.Message(
                    notification=firebase_config.messaging.Notification(
                        title="Chamado Aceito",
                        body=f"O barbeiro {user.nome} aceitou seu chamado."
                    ),
                    data={"tipo": "chamado_aceito", "chamado_id": str(chamado.id)},
                    token=cliente.device_token
                )
                firebase_config.messaging.send(msg)
            except Exception:
                pass
    except Exception:
        pass

    cadeira_reservada = None
    if chamado.cadeira_id:
        cadeira_reservada = db.query(models.Cadeira).filter(
            models.Cadeira.id == chamado.cadeira_id
        ).first()
    
    return {
        "id": chamado.id,
        "status": chamado.status,
        "data_hora_inicio": chamado.data_hora_inicio.isoformat() if chamado.data_hora_inicio else None,
        "data_hora_fim": chamado.data_hora_fim.isoformat() if chamado.data_hora_fim else None,
        "cadeira": {
            "id": cadeira_reservada.id,
            "numero": cadeira_reservada.numero,
            "status": cadeira_reservada.status,
        } if cadeira_reservada else None
    }


@router.put("/chamados/{id}/chegar")
async def chegar_chamado(id: int, token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    """Registra chegada do cliente/barbeiro e muda para em_atendimento somente quando ambos confirmarem."""
    user = get_current_user(token=token, db=db)
    if user.tipo not in {"cliente", "barbeiro"}:
        raise HTTPException(status_code=403, detail="Apenas cliente ou barbeiro podem marcar chegada")

    chamado = db.query(models.Chamado).filter(models.Chamado.id == id).first()
    if not chamado:
        raise HTTPException(status_code=404, detail="Chamado não encontrado")

    if user.tipo == "cliente" and chamado.cliente_id != user.id:
        raise HTTPException(status_code=403, detail="Você não está associado a este chamado")
    if user.tipo == "barbeiro" and chamado.barbeiro_id != user.id:
        raise HTTPException(status_code=403, detail="Você não está associado a este chamado")

    status_normalizado = _normalizar_status_chamado(chamado.status)
    if status_normalizado in {models.StatusAgendamento.CANCELADO.value, models.StatusAgendamento.CONCLUIDO.value}:
        raise HTTPException(status_code=400, detail="Chamado já finalizado")

    if status_normalizado not in {"aceito", models.StatusAgendamento.CONFIRMADO.value, models.StatusAgendamento.EM_ATENDIMENTO.value}:
        raise HTTPException(status_code=400, detail="Chegada só pode ser confirmada quando o chamado estiver confirmado")

    barbeiro = db.query(models.Usuario).filter(models.Usuario.id == chamado.barbeiro_id).first() if chamado.barbeiro_id else None
    barbeiro_ja_presente_na_barbearia = bool(
        barbeiro
        and barbeiro.presente_em_local
        and barbeiro.barbearia_atual_id
        and chamado.barbearia_id
        and int(barbeiro.barbearia_atual_id) == int(chamado.barbearia_id)
    )

    # Se o barbeiro já está marcado como presente na barbearia do chamado,
    # considera a chegada dele automaticamente para não exigir confirmação manual.
    if barbeiro_ja_presente_na_barbearia:
        chamado.barbeiro_chegou = True

    if user.tipo == "cliente":
        chamado.cliente_chegou = True
    else:
        chamado.barbeiro_chegou = True

    chamado.horario_chegada = datetime.utcnow()

    cliente_chegou = bool(getattr(chamado, "cliente_chegou", False))
    barbeiro_chegou = bool(getattr(chamado, "barbeiro_chegou", False))
    status_anterior = chamado.status
    virou_em_atendimento = False

    if cliente_chegou and barbeiro_chegou and status_normalizado != models.StatusAgendamento.EM_ATENDIMENTO.value:
        agora_inicio = datetime.utcnow()
        servico = db.query(models.Servico).filter(models.Servico.id == chamado.servico_id).first() if chamado.servico_id else None
        duracao_minutos = int(getattr(servico, 'duracao_minutos', None) or 30)

        chamado.status = models.StatusAgendamento.EM_ATENDIMENTO.value
        chamado.data_hora_inicio = agora_inicio
        chamado.data_hora_fim = agora_inicio + timedelta(minutes=duracao_minutos)
        virou_em_atendimento = True

        if barbeiro:
            barbeiro.disponivel = False
            barbeiro.em_atendimento = True
            barbeiro.ocupado_ate = chamado.data_hora_fim

        db.add(models.ChamadoHistorico(
            chamado_id=chamado.id,
            status_anterior=status_anterior,
            status_novo=chamado.status,
            usuario_id=user.id,
            observacao='Cliente e barbeiro confirmaram chegada. Atendimento iniciado.'
        ))

        db.add(models.Notificacao(
            usuario_id=chamado.cliente_id,
            titulo="Atendimento iniciado",
            mensagem="Cliente e barbeiro confirmaram chegada. O serviço foi iniciado.",
            tipo="chamado",
            referencia_id=chamado.id
        ))
        if chamado.barbeiro_id:
            db.add(models.Notificacao(
                usuario_id=chamado.barbeiro_id,
                titulo="Atendimento iniciado",
                mensagem="Cliente e barbeiro confirmaram chegada. O serviço foi iniciado.",
                tipo="chamado",
                referencia_id=chamado.id
            ))

    db.commit()
    db.refresh(chamado)

    payload_tracking = None
    if chamado.status in {models.StatusAgendamento.CONFIRMADO.value, models.StatusAgendamento.EM_ATENDIMENTO.value}:
        try:
            ativo = _obter_ou_criar_agendamento_ativo(db, chamado)
            db.commit()
            db.refresh(ativo)
            payload_tracking = _montar_payload_tracking(db, chamado, ativo)
        except Exception:
            payload_tracking = None

    if virou_em_atendimento:
        await broadcast_event(
            "chamado_em_atendimento",
            chamado_id=chamado.id,
            status=chamado.status,
            tracking=payload_tracking,
        )
    else:
        await broadcast_event(
            "chamado_chegada_atualizada",
            chamado_id=chamado.id,
            status=chamado.status,
            cliente_chegou=bool(getattr(chamado, "cliente_chegou", False)),
            barbeiro_chegou=bool(getattr(chamado, "barbeiro_chegou", False)),
            tracking=payload_tracking,
        )

    return {
        "id": chamado.id,
        "status": chamado.status,
        "cliente_chegou": bool(getattr(chamado, "cliente_chegou", False)),
        "barbeiro_chegou": bool(getattr(chamado, "barbeiro_chegou", False)),
        "horario_chegada": chamado.horario_chegada.isoformat() if chamado.horario_chegada else None,
        "tracking": payload_tracking,
        "message": "Chegada registrada" if not virou_em_atendimento else "Ambos chegaram. Atendimento iniciado"
    }


@router.put("/chamados/{id}/cancelar")
def cancelar_chamado_cliente(id: int, token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    # Cliente cancela o chamado com regra de janela grátis.
    user = get_current_user(token=token, db=db)
    if user.tipo != "cliente":
        raise HTTPException(status_code=403, detail="Apenas clientes podem cancelar este chamado")

    chamado = db.query(models.Chamado).filter(models.Chamado.id == id).first()
    if not chamado:
        raise HTTPException(status_code=404, detail="Chamado não encontrado")

    if chamado.cliente_id != user.id:
        raise HTTPException(status_code=403, detail="Você não pode cancelar um chamado de outro cliente")

    status_normalizado = (chamado.status or "").strip().lower()
    if status_normalizado in {models.StatusAgendamento.CONCLUIDO.value, models.StatusAgendamento.CANCELADO.value}:
        raise HTTPException(status_code=400, detail="Este chamado já foi finalizado")

    if status_normalizado == models.StatusAgendamento.EM_ATENDIMENTO.value:
        raise HTTPException(status_code=400, detail="O atendimento já foi iniciado e não pode ser cancelado por aqui")

    barbeiro = db.query(models.Usuario).filter(models.Usuario.id == chamado.barbeiro_id).first() if chamado.barbeiro_id else None
    valor_taxa, tempo_cancelamento_minutos, motivo_regra = _calcular_taxa_cancelamento(chamado, barbeiro)

    status_anterior = chamado.status
    chamado.status = models.StatusAgendamento.CANCELADO.value
    chamado.cancelado_em = datetime.utcnow()
    chamado.tempo_cancelamento_minutos = tempo_cancelamento_minutos
    chamado.valor_taxa_cancelamento = valor_taxa
    chamado.motivo_cancelamento = motivo_regra
    chamado.observacao = motivo_regra

    if chamado.cadeira_id:
        cadeira = db.query(models.Cadeira).filter(models.Cadeira.id == chamado.cadeira_id).first()
        if cadeira and cadeira.chamado_id == chamado.id:
            cadeira.status = models.StatusCadeira.DISPONIVEL
            cadeira.freelancer_id = None
            cadeira.chamado_id = None
            cadeira.liberada_em = datetime.utcnow()

    if barbeiro:
        barbeiro.disponivel = True
        barbeiro.em_atendimento = False
        barbeiro.ocupado_ate = None

    db.add(models.ChamadoHistorico(
        chamado_id=chamado.id,
        status_anterior=status_anterior,
        status_novo=models.StatusAgendamento.CANCELADO.value,
        usuario_id=user.id,
        observacao=f"Cancelado pelo cliente. {motivo_regra}. Taxa: R$ {valor_taxa:.2f}"
    ))

    mensagem_taxa = "sem taxa" if valor_taxa == 0 else f"com taxa de R$ {valor_taxa:.2f}"
    db.add(models.Notificacao(
        usuario_id=user.id,
        titulo="Chamado cancelado",
        mensagem=f"Seu chamado foi cancelado {mensagem_taxa}. {motivo_regra}.",
        tipo="chamado",
        referencia_id=chamado.id
    ))

    if barbeiro:
        db.add(models.Notificacao(
            usuario_id=barbeiro.id,
            titulo="Chamado cancelado pelo cliente",
            mensagem=f"O cliente cancelou o chamado {chamado.id}. {motivo_regra}.",
            tipo="chamado",
            referencia_id=chamado.id
        ))

    db.commit()
    db.refresh(chamado)

    # Enviar push FCM para o barbeiro e cliente sobre cancelamento
    try:
        if firebase_config.FIREBASE_DISPONIVEL:
            if barbeiro and getattr(barbeiro, 'device_token', None):
                try:
                    msg = firebase_config.messaging.Message(
                        notification=firebase_config.messaging.Notification(
                            title="Chamado Cancelado",
                            body=f"O cliente cancelou o chamado {chamado.id}."
                        ),
                        data={"tipo": "chamado_cancelado", "chamado_id": str(chamado.id)},
                        token=barbeiro.device_token
                    )
                    firebase_config.messaging.send(msg)
                except Exception:
                    pass

            # Também notificar o cliente por push (confirmação)
            try:
                user_token = getattr(user, 'device_token', None)
                if user_token:
                    msgc = firebase_config.messaging.Message(
                        notification=firebase_config.messaging.Notification(
                            title="Chamado Cancelado",
                            body=f"Seu chamado {chamado.id} foi cancelado {mensagem_taxa}."
                        ),
                        data={"tipo": "chamado_cancelado", "chamado_id": str(chamado.id)},
                        token=user_token
                    )
                    firebase_config.messaging.send(msgc)
            except Exception:
                pass
    except Exception:
        pass

    return {
        "id": chamado.id,
        "status": chamado.status,
        "valor_taxa_cancelamento": valor_taxa,
        "tempo_cancelamento_minutos": tempo_cancelamento_minutos,
        "motivo_cancelamento": motivo_regra,
        "cancelado_em": chamado.cancelado_em.isoformat() if chamado.cancelado_em else None,
        "message": "Chamado cancelado com sucesso"
    }


@router.put("/chamados/{id}/iniciar-corte")
def iniciar_corte(id: int, token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    # Inicia o corte quando o cliente senta na cadeira.
    user = get_current_user(token=token, db=db)
    if user.tipo != "barbeiro":
        raise HTTPException(status_code=403, detail="Apenas barbeiros podem iniciar cortes")

    chamado = db.query(models.Chamado).filter(models.Chamado.id == id).first()
    if not chamado:
        raise HTTPException(status_code=404, detail="Chamado não encontrado")

    if chamado.barbeiro_id != user.id:
        raise HTTPException(status_code=403, detail="Este chamado não pertence a você")

    if chamado.status not in {models.StatusAgendamento.CONFIRMADO.value, models.StatusAgendamento.PENDENTE.value}:
        raise HTTPException(status_code=400, detail="Este chamado não está pronto para iniciar")

    servico = db.query(models.Servico).filter(models.Servico.id == chamado.servico_id).first()
    if not servico:
        raise HTTPException(status_code=404, detail="Serviço não encontrado")

    agora = datetime.now()
    duracao_minutos = servico.duracao_minutos if servico.duracao_minutos else 30
    status_anterior = chamado.status
    chamado.status = models.StatusAgendamento.EM_ATENDIMENTO.value
    chamado.data_hora_inicio = agora
    chamado.data_hora_fim = agora + timedelta(minutes=duracao_minutos)

    barbeiro = db.query(models.Usuario).filter(models.Usuario.id == user.id).first()
    if barbeiro:
        barbeiro.disponivel = False
        barbeiro.em_atendimento = True
        barbeiro.ocupado_ate = chamado.data_hora_fim

    if chamado.cadeira_id:
        cadeira = db.query(models.Cadeira).filter(models.Cadeira.id == chamado.cadeira_id).first()
        if cadeira:
            cadeira.status = models.StatusCadeira.OCUPADA
            cadeira.freelancer_id = user.id
            cadeira.chamado_id = chamado.id
            cadeira.ocupada_em = agora

    db.commit()
    db.refresh(chamado)

    db.add(models.ChamadoHistorico(
        chamado_id=chamado.id,
        status_anterior=status_anterior,
        status_novo=models.StatusAgendamento.EM_ATENDIMENTO.value,
        usuario_id=user.id,
        observacao=f"Atendimento iniciado por {user.nome}"
    ))
    db.add(models.Notificacao(
        usuario_id=chamado.cliente_id,
        titulo="Atendimento iniciado",
        mensagem=f"O barbeiro {user.nome} começou seu atendimento.",
        tipo="chamado",
        referencia_id=chamado.id
    ))
    # Enviar push para o cliente informando início
    try:
        cliente = db.query(models.Usuario).filter(models.Usuario.id == chamado.cliente_id).first()
        if cliente and getattr(cliente, 'device_token', None) and firebase_config.FIREBASE_DISPONIVEL:
            try:
                msg = firebase_config.messaging.Message(
                    notification=firebase_config.messaging.Notification(
                        title="Atendimento Iniciado",
                        body=f"O barbeiro {user.nome} iniciou seu atendimento."
                    ),
                    data={"tipo": "atendimento_iniciado", "chamado_id": str(chamado.id)},
                    token=cliente.device_token
                )
                firebase_config.messaging.send(msg)
            except Exception:
                pass
    except Exception:
        pass
    db.commit()

    return {
        "id": chamado.id,
        "status": chamado.status,
        "data_hora_inicio": chamado.data_hora_inicio.isoformat() if chamado.data_hora_inicio else None,
        "data_hora_fim": chamado.data_hora_fim.isoformat() if chamado.data_hora_fim else None,
        "duracao_minutos": duracao_minutos,
        "message": "Atendimento iniciado"
    }

@router.put("/chamados/{id}/rejeitar")
def rejeitar_chamado(id: int, token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    # Barbeiro rejeita um chamado.
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
    # Enviar push para o cliente informando recusa (se disponível)
    try:
        cliente = db.query(models.Usuario).filter(models.Usuario.id == chamado.cliente_id).first()
        if cliente and getattr(cliente, 'device_token', None) and firebase_config.FIREBASE_DISPONIVEL:
            try:
                msg = firebase_config.messaging.Message(
                    notification=firebase_config.messaging.Notification(
                        title="Agendamento Recusado",
                        body=f"O barbeiro {user.nome} recusou seu agendamento."
                    ),
                    data={"tipo": "chamado_rejeitado", "chamado_id": str(chamado.id)},
                    token=cliente.device_token
                )
                firebase_config.messaging.send(msg)
            except Exception:
                pass
    except Exception:
        pass

    return {"id": chamado.id, "status": chamado.status}

@router.put("/chamados/{id}/finalizar")
def finalizar_servico_manualmente(id: int, token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    # Barbeiro finaliza o serviço manualmente antes do tempo previsto.
    # Libera o barbeiro para aceitar novos chamados imediatamente.
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
    
    resultado = _finalizar_chamado_e_avancar_fila(db, chamado, barbeiro)
    db.add(models.ChamadoHistorico(
        chamado_id=chamado.id,
        status_anterior=resultado["status_anterior"],
        status_novo=models.StatusAgendamento.CONCLUIDO.value,
        usuario_id=user.id,
        observacao=f"Finalizado manualmente por {user.nome}"
    ))
    db.add(models.Notificacao(
        usuario_id=chamado.cliente_id,
        titulo="Serviço Concluído",
        mensagem=f"O barbeiro {user.nome} finalizou seu atendimento!",
        tipo="chamado",
        referencia_id=chamado.id
    ))
    db.commit()

    # Enviar push para o cliente informando conclusão (se disponível)
    try:
        cliente = db.query(models.Usuario).filter(models.Usuario.id == chamado.cliente_id).first()
        if cliente and getattr(cliente, 'device_token', None) and firebase_config.FIREBASE_DISPONIVEL:
            try:
                msg = firebase_config.messaging.Message(
                    notification=firebase_config.messaging.Notification(
                        title="Serviço Concluído",
                        body=f"O barbeiro {user.nome} finalizou seu atendimento!"
                    ),
                    data={"tipo": "chamado_concluido", "chamado_id": str(chamado.id)},
                    token=cliente.device_token
                )
                firebase_config.messaging.send(msg)
            except Exception:
                pass
    except Exception:
        pass

    if resultado["proximo"]:
        return {
            "id": chamado.id,
            "status": chamado.status,
            "message": "Serviço finalizado! Próximo cliente já foi iniciado.",
            "barbeiro": {
                "disponivel": False,
                "em_atendimento": True,
                "ocupado_ate": resultado["barbeiro"].ocupado_ate.isoformat() if resultado["barbeiro"].ocupado_ate else None
            },
            "proximo_chamado": {
                "id": resultado["proximo"].id,
                "status": resultado["proximo"].status,
                "data_hora_inicio": resultado["proximo"].data_hora_inicio.isoformat() if resultado["proximo"].data_hora_inicio else None,
                "data_hora_fim": resultado["proximo"].data_hora_fim.isoformat() if resultado["proximo"].data_hora_fim else None,
            }
        }

    return {
        "id": chamado.id,
        "status": chamado.status,
        "message": "Serviço finalizado! Você está disponível para novos chamados.",
        "barbeiro": {
            "disponivel": resultado["barbeiro"].disponivel,
            "em_atendimento": resultado["barbeiro"].em_atendimento,
            "ocupado_ate": None
        }
    }

@router.put("/chamados/{id}/barbearia/aceitar")
def barbearia_aceitar_chamado(id: int, token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    # BLOQUEADO: Apenas o freelancer pode aceitar agendamentos.
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
    # Barbearia recusa o agendamento (sem cadeira disponível).
    user = get_current_user(token=token, db=db)
    if user.tipo != "barbearia":
        raise HTTPException(status_code=403, detail="Apenas barbearias podem recusar agendamentos")

    raise HTTPException(status_code=403, detail="Barbearia não pode recusar agendamentos")

@router.put("/chamados/{id}/finalizar")
def finalizar_chamado(id: int, token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    # Finalizar um chamado - APENAS FREELANCER.
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
    # Lista barbeiros próximos à localização do cliente.
    # Usa fórmula de Haversine para calcular distância.
    # Filtros: aprovados, disponíveis e com coordenadas válidas.
    from math import radians, cos, sin, asin, sqrt
    
    def haversine(lon1, lat1, lon2, lat2):
        # Calcula distância em km entre dois pontos (lat/lon).
        lon1, lat1, lon2, lat2 = map(radians, [lon1, lat1, lon2, lat2])
        dlon = lon2 - lon1
        dlat = lat2 - lat1
        a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
        c = 2 * asin(sqrt(a))
        km = 6371 * c
        return km
    
    # ✅ GUARDIÃO: Apenas barbeiros aprovados e aptos a receber.
    # Inclui também quem está na janela final (<=10 min) para liberar o próximo atendimento.
    agora_filtro = datetime.now()
    limite_liberacao = agora_filtro + timedelta(minutes=10)
    barbeiros = db.query(models.Usuario).filter(
        models.Usuario.tipo == "barbeiro",
        models.Usuario.perfil_aprovado == True,  # Apenas aprovados
        models.Usuario.latitude.isnot(None),
        models.Usuario.longitude.isnot(None),
        or_(
            models.Usuario.disponivel == True,
            and_(
                models.Usuario.ocupado_ate.isnot(None),
                models.Usuario.ocupado_ate > agora_filtro,
                models.Usuario.ocupado_ate <= limite_liberacao
            )
        )
    ).all()
    
    # Filtrar por distância E verificar se está em serviço
    barbeiros_proximos = []
    for b in barbeiros:
        distancia = haversine(longitude, latitude, b.longitude, b.latitude)
        if distancia <= raio_km:
            na_janela_liberacao = _esta_na_janela_liberacao_antecipada(b, agora=agora_filtro, janela_min=10)
            disponivel_real = (b.disponivel and not esta_em_servico_agora(db, b.id)) or na_janela_liberacao
            online_regiao_real = bool(b.online_regiao) or na_janela_liberacao
            
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
                "online_regiao": online_regiao_real,
                "pode_receber_chamado_agora": bool(b.presente_em_local and b.barbearia_atual_id),
                "liberacao_antecipada": na_janela_liberacao,
            })
    
    # Ordenar por distância
    barbeiros_proximos.sort(key=lambda x: x["distancia_km"])
    
    return barbeiros_proximos

@router.get("/barbeiros/todos")
def listar_todos_barbeiros(db: Session = Depends(get_db)):
    # Listar todos os barbeiros cadastrados, incluindo os presentes em barbearias.
    # ✅ INCLUIR barbeiros presentes - eles também podem receber agendamentos
    barbeiros = db.query(models.Usuario).filter(
        models.Usuario.tipo == "barbeiro"
    ).all()
    
    resultado = []
    for b in barbeiros:
        na_janela_liberacao = _esta_na_janela_liberacao_antecipada(b, janela_min=10)
        disponivel_real = (b.disponivel and not esta_em_servico_agora(db, b.id)) or na_janela_liberacao
        online_regiao_real = bool(b.online_regiao) or na_janela_liberacao
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
            "online_regiao": online_regiao_real,
            "pode_receber_chamado_agora": bool(b.presente_em_local and b.barbearia_atual_id),
            "liberacao_antecipada": na_janela_liberacao,
            "foto_perfil": b.foto_perfil,
            "latitude": b.latitude,
            "longitude": b.longitude
        })
    
    return resultado


@router.get("/freelancer/todos")
def listar_todos_freelancers_alias(db: Session = Depends(get_db)):
    # Alias legada para manter compatibilidade com clientes antigos.
    return listar_todos_barbeiros(db=db)


@router.get("/barbeiro/{barbeiro_id}/disponibilidade-imediata")
def verificar_disponibilidade_imediata_barbeiro(barbeiro_id: int, db: Session = Depends(get_db)):
    # Alias para integrações externas: presença real = presente_em_local + barbearia_atual_id.
    barbeiro = db.query(models.Usuario).filter(
        models.Usuario.id == barbeiro_id,
        models.Usuario.tipo == "barbeiro"
    ).first()

    if not barbeiro:
        raise HTTPException(status_code=404, detail="Barbeiro não encontrado")

    pode_receber_chamado_agora = bool(barbeiro.presente_em_local and barbeiro.barbearia_atual_id)

    return {
        "barbeiro_id": barbeiro.id,
        "nome": barbeiro.nome,
        "pode_receber_chamado_agora": pode_receber_chamado_agora,
        "presente_em_local": bool(barbeiro.presente_em_local),
        "barbearia_id": barbeiro.barbearia_atual_id
    }

@router.get("/barbeiro/{barbeiro_id}/barbearias")
def listar_barbearias_do_barbeiro(barbeiro_id: int, db: Session = Depends(get_db)):
    # Listar barbearias onde um barbeiro específico atende.
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
    # Listar agendamentos confirmados de uma barbearia.
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
        barbearia_usuario = db.query(models.Usuario).filter(models.Usuario.id == user.id).first()

        cliente_distancia = None
        cliente_eta = None
        freelancer_distancia = None
        freelancer_eta = None

        if barbearia_usuario and barbearia_usuario.latitude and barbearia_usuario.longitude:
            if cliente and cliente.latitude and cliente.longitude:
                cliente_distancia = calcular_distancia_km(
                    cliente.latitude,
                    cliente.longitude,
                    barbearia_usuario.latitude,
                    barbearia_usuario.longitude
                )
                cliente_eta = max(1, int(round(cliente_distancia * 4)))

            if barbeiro and barbeiro.latitude and barbeiro.longitude:
                freelancer_distancia = calcular_distancia_km(
                    barbeiro.latitude,
                    barbeiro.longitude,
                    barbearia_usuario.latitude,
                    barbearia_usuario.longitude
                )
                freelancer_eta = max(1, int(round(freelancer_distancia * 4)))
        
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
            "cliente_distancia_ate_barbearia_km": cliente_distancia,
            "cliente_eta_ate_barbearia_min": cliente_eta,
            "freelancer_distancia_ate_barbearia_km": freelancer_distancia,
            "freelancer_eta_ate_barbearia_min": freelancer_eta,
            "avaliado": ja_avaliado
        })
    
    return result


@router.get("/cliente/meus_pedidos")
def listar_meus_pedidos_cliente(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    # Lista os chamados/agendamentos do cliente autenticado.
    user = get_current_user(token=token, db=db)

    if user.tipo != "cliente":
        raise HTTPException(status_code=403, detail="Apenas clientes podem acessar este endpoint")

    chamados = db.query(models.Chamado).filter(
        models.Chamado.cliente_id == user.id
    ).order_by(models.Chamado.criado_em.desc(), models.Chamado.id.desc()).all()

    chamados_ids = [ch.id for ch in chamados]
    pagamentos_por_chamado = {}
    if chamados_ids:
        pagamentos = db.query(models.Pagamento).filter(models.Pagamento.chamado_id.in_(chamados_ids)).all()
        pagamentos_por_chamado = {pag.chamado_id: pag for pag in pagamentos}

    resultado = []
    for chamado in chamados:
        pagamento = pagamentos_por_chamado.get(chamado.id)
        barbearia = db.query(models.Barbearia).filter(models.Barbearia.id == chamado.barbearia_id).first()
        barbeiro = db.query(models.Usuario).filter(models.Usuario.id == chamado.barbeiro_id).first() if chamado.barbeiro_id else None
        servico = db.query(models.Servico).filter(models.Servico.id == chamado.servico_id).first()
        cadeira = db.query(models.Cadeira).filter(models.Cadeira.id == chamado.cadeira_id).first() if chamado.cadeira_id else None

        cliente_distancia = None
        cliente_eta = None
        freelancer_distancia = None
        freelancer_eta = None

        if barbearia and barbearia.latitude is not None and barbearia.longitude is not None:
            if user.latitude is not None and user.longitude is not None:
                cliente_distancia = calcular_distancia_km(
                    user.latitude,
                    user.longitude,
                    barbearia.latitude,
                    barbearia.longitude,
                )
                cliente_eta = max(1, int(round(cliente_distancia * 4))) if cliente_distancia > 0 else 0

            if barbeiro and barbeiro.latitude is not None and barbeiro.longitude is not None:
                freelancer_distancia = calcular_distancia_km(
                    barbeiro.latitude,
                    barbeiro.longitude,
                    barbearia.latitude,
                    barbearia.longitude,
                )
                freelancer_eta = max(1, int(round(freelancer_distancia * 4))) if freelancer_distancia > 0 else 0

        resultado.append({
            "id": chamado.id,
            "cliente_id": chamado.cliente_id,
            "barbeiro_id": chamado.barbeiro_id,
            "barbearia_id": chamado.barbearia_id,
            "servico_id": chamado.servico_id,
            "servico_nome": servico.nome if servico else None,
            "descricao": servico.nome if servico else None,
            "valor": servico.valor if servico else 0,
            "status": chamado.status,
            "cadeira_id": chamado.cadeira_id,
            "cadeira_numero": cadeira.numero if cadeira else None,
            "data_hora_inicio": chamado.data_hora_inicio.isoformat() if chamado.data_hora_inicio else None,
            "data_agendamento": chamado.data_agendamento.isoformat() if chamado.data_agendamento else None,
            "aprovado_barbeiro": chamado.aprovado_barbeiro,
            "aprovado_barbeiro_em": chamado.aprovado_barbeiro_em.isoformat() if chamado.aprovado_barbeiro_em else None,
            "barbeiro_presente_em_local": bool(barbeiro.presente_em_local) if barbeiro else False,
            "barbeiro_barbearia_atual_id": barbeiro.barbearia_atual_id if barbeiro else None,
            "criado_em": chamado.criado_em.isoformat() if chamado.criado_em else None,
            "barbearia_nome": barbearia.nome if barbearia else "Barbearia",
            "barbearia_endereco": barbearia.endereco if barbearia else None,
            "barbearia_latitude": barbearia.latitude if barbearia else None,
            "barbearia_longitude": barbearia.longitude if barbearia else None,
            "barbeiro_nome": barbeiro.nome if barbeiro else None,
            "cliente_latitude": user.latitude,
            "cliente_longitude": user.longitude,
            "barbeiro_latitude": barbeiro.latitude if barbeiro else None,
            "barbeiro_longitude": barbeiro.longitude if barbeiro else None,
            "cliente_distancia_ate_barbearia_km": cliente_distancia,
            "cliente_eta_ate_barbearia_min": cliente_eta,
            "freelancer_distancia_ate_barbearia_km": freelancer_distancia,
            "freelancer_eta_ate_barbearia_min": freelancer_eta,
            "avaliado": False,
            "pagamento_id": pagamento.id if pagamento else None,
            "pagamento_concluido": bool(pagamento and pagamento.pago_em),
            "pagamento_pago_em": pagamento.pago_em.isoformat() if pagamento and pagamento.pago_em else None,
        })

    return resultado


@router.get("/tracking/chamados/{chamado_id}/eta")
async def obter_eta_tracking_chamado(
    chamado_id: int,
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
):
    """Retorna snapshot de tracking e ETA para cliente/barbeiro/barbearia do chamado."""
    user = get_current_user(token=token, db=db)
    chamado = _buscar_chamado_para_tracking(db, chamado_id)
    _validar_acesso_tracking(db, user, chamado)

    ativo = _obter_ou_criar_agendamento_ativo(db, chamado)
    db.commit()
    db.refresh(ativo)

    return _montar_payload_tracking(db, chamado, ativo)


@router.patch("/tracking/chamados/{chamado_id}/posicao-cliente")
async def atualizar_posicao_cliente_tracking(
    chamado_id: int,
    payload: AtualizarPosicaoTrackingRequest,
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
):
    """Atualiza posição GPS do cliente no chamado ativo e propaga evento em websocket."""
    user = get_current_user(token=token, db=db)
    chamado = _buscar_chamado_para_tracking(db, chamado_id)

    if user.tipo != "cliente" or chamado.cliente_id != user.id:
        raise HTTPException(status_code=403, detail="Apenas o cliente do chamado pode atualizar essa posição")

    if not _tracking_ativo_por_status(chamado.status):
        raise HTTPException(status_code=409, detail="Tracking desativado para o status atual do chamado")

    ativo = _obter_ou_criar_agendamento_ativo(db, chamado)
    # AUDITORIA: logar coordenadas recebidas e atuais para diagnóstico de GPS
    try:
        print('\n=== AUDITORIA GPS: posicao-cliente ===')
        print(f'Chamado: {chamado_id} | Usuario: {user.id}')
        print(f'Coordenadas recebidas -> lat: {payload.latitude}, lon: {payload.longitude}')
        print(f'Coordenadas ativas no DB -> cliente_lat: {ativo.cliente_lat}, cliente_lon: {ativo.cliente_lon}')
    except Exception:
        pass
    ativo.cliente_lat = payload.latitude
    ativo.cliente_lon = payload.longitude
    ativo.cliente_localizacao_em = datetime.utcnow()

    user.latitude = payload.latitude
    user.longitude = payload.longitude

    db.commit()
    db.refresh(ativo)

    tracking = _montar_payload_tracking(db, chamado, ativo)
    await broadcast_event("tracking_update", chamado_id=chamado.id, source="cliente", tracking=tracking)
    return {"status": "ok", "tracking": tracking}


@router.patch("/tracking/chamados/{chamado_id}/posicao-barbeiro")
async def atualizar_posicao_barbeiro_tracking(
    chamado_id: int,
    payload: AtualizarPosicaoTrackingRequest,
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
):
    """Atualiza posição GPS do barbeiro no chamado ativo e propaga evento em websocket."""
    user = get_current_user(token=token, db=db)
    chamado = _buscar_chamado_para_tracking(db, chamado_id)

    if user.tipo != "barbeiro" or chamado.barbeiro_id != user.id:
        raise HTTPException(status_code=403, detail="Apenas o barbeiro do chamado pode atualizar essa posição")

    if not _tracking_ativo_por_status(chamado.status):
        raise HTTPException(status_code=409, detail="Tracking desativado para o status atual do chamado")

    ativo = _obter_ou_criar_agendamento_ativo(db, chamado)
    # AUDITORIA: logar coordenadas recebidas e atuais para diagnóstico de GPS
    try:
        print('\n=== AUDITORIA GPS: posicao-barbeiro ===')
        print(f'Chamado: {chamado_id} | Usuario: {user.id}')
        print(f'Coordenadas recebidas -> lat: {payload.latitude}, lon: {payload.longitude}')
        print(f'Coordenadas ativas no DB -> barbeiro_lat: {ativo.barbeiro_lat}, barbeiro_lon: {ativo.barbeiro_lon}')
    except Exception:
        pass
    ativo.barbeiro_lat = payload.latitude
    ativo.barbeiro_lon = payload.longitude
    ativo.barbeiro_localizacao_em = datetime.utcnow()

    user.latitude = payload.latitude
    user.longitude = payload.longitude

    db.commit()
    db.refresh(ativo)

    tracking = _montar_payload_tracking(db, chamado, ativo)
    await broadcast_event("tracking_update", chamado_id=chamado.id, source="barbeiro", tracking=tracking)
    return {"status": "ok", "tracking": tracking}


@router.post("/atualizar-localizacao")
async def atualizar_localizacao_compat(
    payload: AtualizarLocalizacaoCompatRequest,
    token: str = Depends(oauth2_scheme),
    http_request: Request = None,
    db: Session = Depends(get_db),
):
    """
    Endpoint legado de localização.

    Mantém compatibilidade com clients antigos e, quando `chamado_id` é enviado,
    atualiza também o snapshot de tracking do chamado.
    """
    user = get_current_user(token=token, db=db)
    # DEBUG: registrar headers e payload para diagnosticar GPS
    try:
        print('\n=== [DEBUG] POST /api/v1/atualizar-localizacao (compat) ===')
        if http_request is not None:
            print('Headers:', dict(http_request.headers))
        print('Has token:', bool(token))
        try:
            print('Payload:', payload.dict())
        except Exception:
            print('Payload (repr):', repr(payload))
    except Exception:
        pass
    user.latitude = payload.latitude
    user.longitude = payload.longitude

    tracking = None
    if payload.chamado_id is not None:
        chamado = _buscar_chamado_para_tracking(db, payload.chamado_id)
        _validar_acesso_tracking(db, user, chamado)

        if not _tracking_ativo_por_status(chamado.status):
            raise HTTPException(status_code=409, detail="Tracking desativado para o status atual do chamado")

        ativo = _obter_ou_criar_agendamento_ativo(db, chamado)

        agora = datetime.utcnow()
        if user.tipo == "cliente" and chamado.cliente_id == user.id:
            ativo.cliente_lat = payload.latitude
            ativo.cliente_lon = payload.longitude
            ativo.cliente_localizacao_em = agora
        elif user.tipo == "barbeiro" and chamado.barbeiro_id == user.id:
            ativo.barbeiro_lat = payload.latitude
            ativo.barbeiro_lon = payload.longitude
            ativo.barbeiro_localizacao_em = agora

        db.commit()
        db.refresh(ativo)
        tracking = _montar_payload_tracking(db, chamado, ativo)
        await broadcast_event("tracking_update", chamado_id=chamado.id, source=user.tipo, tracking=tracking)
    else:
        db.commit()

    return {
        "status": "localização atualizada",
        "usuario_id": user.id,
        "latitude": user.latitude,
        "longitude": user.longitude,
        "tracking": tracking,
    }


@router.get("/barbearia/{barbearia_id}/barbeiros-presentes")
def listar_barbeiros_presentes(
    barbearia_id: int,
    db: Session = Depends(get_db)
):
    # Lista barbeiros que estão presentes fisicamente na barbearia.
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


@router.get("/barbearia/{barbearia_id}/barbeiros-priorizados")
def listar_barbeiros_priorizados_barbearia(
    barbearia_id: int,
    latitude: float | None = None,
    longitude: float | None = None,
    raio_km: float = 10.0,
    incluir_indisponiveis: bool = False,
    db: Session = Depends(get_db),
):
    """
    Lista barbeiros para uma barbearia com prioridade:
    1) Profissionais da casa (presentes na barbearia)
    2) Freelancers online na região
    """
    barbearia = db.query(models.Barbearia).filter(models.Barbearia.id == barbearia_id).first()
    if not barbearia:
        raise HTTPException(status_code=404, detail="Barbearia não encontrada")

    criterio_profissional_da_casa = and_(
        models.Usuario.presente_em_local == True,
        models.Usuario.barbearia_atual_id == barbearia_id,
    )

    prioridade_sql = case((criterio_profissional_da_casa, 1), else_=2)

    barbeiros = db.query(models.Usuario).filter(
        models.Usuario.tipo == 'barbeiro',
        models.Usuario.perfil_aprovado == True,
        or_(
            criterio_profissional_da_casa,
            models.Usuario.online_regiao == True,
        )
    ).order_by(
        prioridade_sql.asc(),
        func.lower(models.Usuario.nome).asc()
    ).all()

    usar_filtro_distancia = latitude is not None and longitude is not None

    resultado = []
    for barbeiro in barbeiros:
        na_janela_liberacao = _esta_na_janela_liberacao_antecipada(barbeiro, janela_min=10)
        online_regiao_real = bool(barbeiro.online_regiao) or na_janela_liberacao
        profissional_da_casa = bool(
            barbeiro.presente_em_local and
            barbeiro.barbearia_atual_id == barbearia_id
        )

        if not profissional_da_casa and not online_regiao_real:
            continue

        distancia_km = None
        if usar_filtro_distancia:
            if barbeiro.latitude is None or barbeiro.longitude is None:
                if not profissional_da_casa:
                    continue
            else:
                distancia_km = calcular_distancia_km(latitude, longitude, barbeiro.latitude, barbeiro.longitude)
                if distancia_km is not None and distancia_km > raio_km and not profissional_da_casa:
                    continue

        disponivel_real = (bool(barbeiro.disponivel) and not esta_em_servico_agora(db, barbeiro.id)) or na_janela_liberacao
        if not incluir_indisponiveis and not disponivel_real:
            continue

        resultado.append({
            "id": barbeiro.id,
            "nome": barbeiro.nome,
            "telefone": barbeiro.telefone,
            "endereco": barbeiro.endereco,
            "foto_perfil": barbeiro.foto_perfil,
            "latitude": barbeiro.latitude,
            "longitude": barbeiro.longitude,
            "distancia_km": round(distancia_km, 2) if distancia_km is not None else None,
            "tempo_estimado_minutos": max(1, int(round((distancia_km / 40) * 60))) if distancia_km is not None else None,
            "disponivel": disponivel_real,
            "presente_em_local": bool(barbeiro.presente_em_local),
            "barbearia_atual_id": barbeiro.barbearia_atual_id,
            "barbearia_atual_nome": barbearia.nome if profissional_da_casa else None,
            "online_regiao": online_regiao_real,
            "profissional_da_casa": profissional_da_casa,
            "origem": "casa" if profissional_da_casa else "freelancer",
            "prioridade": 1 if profissional_da_casa else 2,
            "pode_receber_chamado_agora": bool(profissional_da_casa),
            "liberacao_antecipada": na_janela_liberacao,
        })

    resultado.sort(key=lambda item: (
        item.get("prioridade", 2),
        item.get("distancia_km") if item.get("distancia_km") is not None else float('inf'),
        str(item.get("nome") or '').lower()
    ))

    return {
        "barbearia_id": barbearia_id,
        "barbearia_nome": barbearia.nome,
        "total": len(resultado),
        "barbeiros": resultado,
    }


# --- ENDPOINTS DE BARBEARIA ---

@router.put("/barbearia/cadeira")
def atualizar_status_cadeira(livre: bool, token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    # Atualizar status da cadeira (livre/ocupada).
    user = get_current_user(token=token, db=db)
    
    user.cadeira_livre = livre
    db.commit()
    db.refresh(user)
    
    return {"cadeira_livre": user.cadeira_livre}

@router.post("/barbearia/servicos")
def criar_servico(servico: schemas.ServicoCreate, token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    # Criar novo serviço na barbearia.
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
    # Retorna o saldo disponível do usuário (apenas para barbeiros).
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
