"""
ARQUIVO: app/routes_on_demand.py
Sistema On-Demand com geolocalização em tempo real (estilo Uber)

Este módulo implementa:
1. Radar de barbeiros online
2. Busca por proximidade usando Haversine
3. Solicitação instantânea de barbeiros
4. Notificações push para barbeiros próximos
5. Matching automático entre cliente e profissional
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query, Request
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime, timedelta
import math
import json
from urllib.request import urlopen

from app.database import get_db
from app.routes import get_current_user
from app.models import Usuario, RadarFreelancer, SolicitacaoBarbeiro, NotificacaoBarbeiro, RequestView, Barbearia, CadeiraAcionada, CadeiraAcionadaCandidatura, Cadeira, StatusCadeira, Notificacao
from app.firebase_config import enviar_notificacao_novo_chamado
from app.realtime import broadcast_event
from app.routes_vaga_chat import nao_lidas_por_vaga
from app.sao_paulo_capital import bairro_do_endereco, esta_na_capital, localizar_na_capital
from app.vagas import (
    STATUS_ABERTA,
    STATUS_AGUARDANDO_DESBLOQUEIO,
    STATUS_CANCELADA,
    STATUS_OCUPADA,
    TIPO_VAGA_DIARIA,
    aplicar_freelancer_na_cadeira,
    cadeira_esta_bloqueada,
    fim_do_dia_utc,
    cadeiras_vencidas,
    limites_de_anuncio,
    reservar_cadeiras,
    travar_barbearia,
)

router = APIRouter(prefix="/api/v1/on-demand", tags=["on-demand"])

# ============================================================================
# 🔧 UTILIDADES
# ============================================================================

def calcular_distancia_haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calcula a distância entre dois pontos na Terra usando a fórmula de Haversine.
    
    Fórmula:
    d = 2r * arcsin(√(sin²(Δφ/2) + cos(φ1)cos(φ2)sin²(Δλ/2)))
    
    Onde:
    - φ = latitude
    - λ = longitude
    - r = raio da Terra (6371 km)
    - Δφ e Δλ são as diferenças
    
    Args:
        lat1, lon1: Coordenadas do ponto 1 (cliente/barbearia)
        lat2, lon2: Coordenadas do ponto 2 (barbeiro)
    
    Returns:
        Distância em quilômetros
    """
    
    R = 6371.0  # Raio da Terra em quilômetros
    
    # Converter graus para radianos
    lat1_rad = math.radians(lat1)
    lon1_rad = math.radians(lon1)
    lat2_rad = math.radians(lat2)
    lon2_rad = math.radians(lon2)
    
    # Diferenças
    dlat = lat2_rad - lat1_rad
    dlon = lon2_rad - lon1_rad
    
    # Haversine
    a = math.sin(dlat / 2)**2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon / 2)**2
    c = 2 * math.asin(math.sqrt(a))
    
    distancia = R * c
    return round(distancia, 2)


def _radar_elegivel_para_novo_clause(agora: datetime = None):
    """Condicao SQLAlchemy: freelancer livre OU dentro da janela de liberacao
    antecipada (<=10 min pra terminar o atendimento atual). Espelha
    _esta_na_janela_liberacao_antecipada usada no fluxo classico (routes.py),
    aplicada aqui em RadarFreelancer.ocupado_ate pra manter os dois sistemas
    de disponibilidade sincronizados."""
    referencia = agora or datetime.now()
    limite = referencia + timedelta(minutes=10)
    return or_(
        RadarFreelancer.em_atendimento == False,
        and_(
            RadarFreelancer.ocupado_ate.isnot(None),
            RadarFreelancer.ocupado_ate > referencia,
            RadarFreelancer.ocupado_ate <= limite,
        )
    )


# ============================================================================
# 📊 SCHEMAS (Pydantic)
# ============================================================================

class AtualizarLocalizacaoRequest(BaseModel):
    """Payload para atualizar localização de barbeiro"""
    latitude: float
    longitude: float


class AtualizarStatusRequest(BaseModel):
    """Payload para mudar status do barbeiro (online/offline)"""
    is_online: bool


class SolicitarBarbeiroRequest(BaseModel):
    """Payload para solicitar um barbeiro"""
    latitude: float
    longitude: float
    endereco: Optional[str] = None
    raio_km: float = 5.0  # Raio de busca em km
    tipo_servico: Optional[str] = None  # "corte", "barba", "combo"
    observacoes: Optional[str] = None
    valor_oferta: Optional[float] = None


class BarbeiroProximoResponse(BaseModel):
    """Resposta com informação de barbeiro próximo"""
    barbeiro_id: int
    nome: str
    avaliacao: Optional[float] = None
    distancia_km: float
    tempo_estimado_min: int  # Estimativa em minutos (distância / velocidade média)
    
    class Config:
        from_attributes = True


class SolicitacaoBarbeiroResponse(BaseModel):
    """Resposta de uma solicitação de barbeiro"""
    id: int
    status: str
    cliente_id: int
    barbeiro_aceito_id: Optional[int] = None
    latitude: float
    longitude: float
    endereco: Optional[str] = None
    tipo_servico: Optional[str] = None
    valor_oferta: Optional[float] = None
    criado_em: datetime
    aceito_em: Optional[datetime] = None
    views_count: int = 0
    flow_status: str = "WAITING_FOR_FREELANCER"
    visualizadores: List[dict] = []
    
    class Config:
        from_attributes = True


class VisualizadorSolicitacaoResponse(BaseModel):
    freelancer_id: int
    nome: str
    foto_perfil: Optional[str] = None
    viewed_at: datetime


def _flow_status_solicitacao(status: Optional[str]) -> str:
    status_normalizado = (status or "").strip().lower()
    if status_normalizado == "aceito":
        return "FREELANCER_ACCEPTED"
    if status_normalizado in {"aguardando_resposta", "pendente", "waiting_for_freelancer"}:
        return "WAITING_FOR_FREELANCER"
    if status_normalizado:
        return status_normalizado.upper()
    return "WAITING_FOR_FREELANCER"


def _registrar_visualizacao_solicitacao(db: Session, solicitacao_id: int, freelancer_id: int) -> None:
    visualizacao = db.query(RequestView).filter(
        RequestView.request_id == solicitacao_id,
        RequestView.freelancer_id == freelancer_id,
    ).first()

    agora = datetime.utcnow()
    if visualizacao:
        visualizacao.viewed_at = agora
        return

    db.add(RequestView(
        request_id=solicitacao_id,
        freelancer_id=freelancer_id,
        viewed_at=agora,
    ))


def _serializar_solicitacao_com_views(db: Session, solicitacao: SolicitacaoBarbeiro) -> SolicitacaoBarbeiroResponse:
    visualizacoes = (
        db.query(RequestView, Usuario)
        .join(Usuario, Usuario.id == RequestView.freelancer_id)
        .filter(RequestView.request_id == solicitacao.id)
        .order_by(RequestView.viewed_at.desc())
        .all()
    )

    visualizadores = [
        VisualizadorSolicitacaoResponse(
            freelancer_id=freelancer.id,
            nome=freelancer.nome,
            foto_perfil=getattr(freelancer, "foto_perfil", None),
            viewed_at=request_view.viewed_at,
        ).dict()
        for request_view, freelancer in visualizacoes[:5]
    ]

    return SolicitacaoBarbeiroResponse(
        id=solicitacao.id,
        status=solicitacao.status,
        cliente_id=solicitacao.cliente_id,
        barbeiro_aceito_id=solicitacao.barbeiro_aceito_id,
        latitude=solicitacao.latitude,
        longitude=solicitacao.longitude,
        endereco=solicitacao.endereco,
        tipo_servico=solicitacao.tipo_servico,
        observacoes=solicitacao.observacoes,
        valor_oferta=solicitacao.valor_oferta,
        criado_em=solicitacao.criado_em,
        aceito_em=solicitacao.aceito_em,
        views_count=len(visualizacoes),
        flow_status=_flow_status_solicitacao(solicitacao.status),
        visualizadores=visualizadores,
    )


class RadarFreelancerResponse(BaseModel):
    """Status atual do radar do barbeiro"""
    freelancer_id: int
    is_online: bool
    em_atendimento: bool
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    localizacao_atualizada_em: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class AcionarCadeiraRequest(BaseModel):
    cadeira_id: Optional[int] = None
    raio_km: float = 5.0
    tipo_servico: Optional[str] = None
    valor_oferta: Optional[float] = None
    observacoes: Optional[str] = None
    expira_em_minutos: int = 10


class AnunciarVagasRequest(BaseModel):
    # Cadeiras escolhidas pelo dono; sem elas, o backend escolhe `quantidade` cadeiras livres.
    # Sem raio: a vaga de diaria vale para a capital inteira (ver app/vagas.py).
    cadeira_ids: Optional[List[int]] = Field(default=None, min_length=1)
    quantidade: Optional[int] = Field(default=None, ge=1)
    # Percentual de cada servico realizado que vai para o freelancer. Sem padrao: o dono digita.
    percentual_freelancer: float = Field(..., ge=0, le=100, allow_inf_nan=False)


class CadeiraAcionadaResponse(BaseModel):
    id: int
    barbearia_id: int
    cadeira_id: Optional[int] = None
    cadeira_numero: Optional[int] = None
    status: str
    barbeiro_id: Optional[int] = None
    cliente_id: Optional[int] = None
    # None na vaga de diaria (vale para a capital inteira).
    raio_km: Optional[float] = None
    tipo_servico: Optional[str] = None
    valor_oferta: Optional[float] = None
    observacoes: Optional[str] = None
    barbearia_nome: Optional[str] = None
    barbearia_usuario_id: Optional[int] = None
    barbearia_latitude: Optional[float] = None
    barbearia_longitude: Optional[float] = None
    # So na vaga de diaria: onde fica a oportunidade, para o freelancer decidir antes de se candidatar.
    barbearia_endereco: Optional[str] = None
    barbearia_regiao: Optional[str] = None
    barbearia_subprefeitura: Optional[str] = None
    barbearia_bairro: Optional[str] = None
    percentual_freelancer: Optional[float] = None
    eta_min_usuario_atual: Optional[int] = None
    limite_chegada: Optional[datetime] = None
    expira_em: Optional[datetime] = None
    criado_em: datetime
    atualizado_em: datetime

    class Config:
        from_attributes = True


class CandidatoCadeiraAcionadaResponse(BaseModel):
    id: int
    freelancer_id: int
    nome: str
    foto_perfil: Optional[str] = None
    criado_em: datetime
    # So informativo, sem limite: distancia em linha reta entre o freelancer e a barbearia.
    # None quando falta a posicao de um dos dois.
    distancia_km: Optional[float] = None


class EscolherFreelancerRequest(BaseModel):
    barbeiro_id: int


def _calcular_eta_osrm_minutos(origem_lat: float, origem_lon: float, destino_lat: float, destino_lon: float) -> Optional[int]:
    """Calcula ETA via OSRM publico com fallback para modelo local."""
    try:
        url = (
            "https://router.project-osrm.org/route/v1/driving/"
            f"{origem_lon},{origem_lat};{destino_lon},{destino_lat}?overview=false"
        )
        with urlopen(url, timeout=3) as response:
            payload = json.loads(response.read().decode("utf-8"))

        routes = payload.get("routes") or []
        if not routes:
            return None

        duration_seconds = routes[0].get("duration")
        if duration_seconds is None:
            return None

        return max(1, int(round(float(duration_seconds) / 60.0)))
    except Exception:
        return None


def _estimar_eta_minutos_por_distancia(distancia_km: float, velocidade_media_kmh: float = 40.0) -> int:
    if distancia_km is None:
        return 0
    horas = distancia_km / velocidade_media_kmh
    return max(1, int(round(horas * 60.0)))


def _calcular_eta_minutos(origem_lat: float, origem_lon: float, destino_lat: float, destino_lon: float) -> int:
    eta_osrm = _calcular_eta_osrm_minutos(origem_lat, origem_lon, destino_lat, destino_lon)
    if eta_osrm is not None:
        return eta_osrm

    distancia_km = calcular_distancia_haversine(origem_lat, origem_lon, destino_lat, destino_lon)
    return _estimar_eta_minutos_por_distancia(distancia_km)


def _expirar_vagas_vencidas(db: Session) -> None:
    agora = datetime.utcnow()
    vagas = db.query(CadeiraAcionada).filter(
        CadeiraAcionada.status == "disponivel",
        CadeiraAcionada.expira_em.isnot(None),
        CadeiraAcionada.expira_em <= agora,
    ).all()

    if not vagas:
        return

    for vaga in vagas:
        vaga.status = "expirada"
        vaga.atualizado_em = agora

    db.commit()


def _serializar_cadeira_acionada(vaga: CadeiraAcionada, eta_min_usuario_atual: Optional[int] = None) -> dict:
    barbearia = vaga.barbearia
    local_diaria = {}
    if vaga.tipo_servico == TIPO_VAGA_DIARIA and barbearia:
        local = localizar_na_capital(barbearia.latitude, barbearia.longitude) or {}
        local_diaria = {
            "barbearia_endereco": barbearia.endereco,
            "barbearia_regiao": local.get("regiao"),
            "barbearia_subprefeitura": local.get("subprefeitura"),
            # Bairro do endereco cadastrado (a subprefeitura nao e bairro: Artur Alvim fica na Penha).
            "barbearia_bairro": bairro_do_endereco(barbearia.endereco),
        }
    return {
        **local_diaria,
        "id": vaga.id,
        "barbearia_id": vaga.barbearia_id,
        "cadeira_id": vaga.cadeira_id,
        # Numero que identifica a cadeira na barbearia; cadeira_id e o id global da tabela.
        "cadeira_numero": vaga.cadeira.numero if vaga.cadeira else None,
        "status": vaga.status,
        "barbeiro_id": vaga.barbeiro_id,
        "cliente_id": vaga.cliente_id,
        "raio_km": None if vaga.tipo_servico == TIPO_VAGA_DIARIA else vaga.raio_km,
        "tipo_servico": vaga.tipo_servico,
        "valor_oferta": vaga.valor_oferta,
        "percentual_freelancer": vaga.percentual_freelancer,
        "observacoes": vaga.observacoes,
        "barbearia_nome": barbearia.nome if barbearia else None,
        "barbearia_usuario_id": barbearia.usuario_id if barbearia else None,
        "barbearia_latitude": barbearia.latitude if barbearia else None,
        "barbearia_longitude": barbearia.longitude if barbearia else None,
        "eta_min_usuario_atual": eta_min_usuario_atual,
        "limite_chegada": vaga.limite_chegada,
        "expira_em": vaga.expira_em,
        "criado_em": vaga.criado_em,
        "atualizado_em": vaga.atualizado_em,
    }


# ============================================================================
# 🟢 ENDPOINTS
# ============================================================================

@router.post("/ligar-radar", response_model=RadarFreelancerResponse, status_code=200)
async def ligar_radar_barbeiro(
    request: AtualizarStatusRequest,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    """
    Barbeiro clica o botão "Ficar Online" e ativa seu radar.
    
    Quando `is_online = true`, o barbeiro passa a receber notificações
    de solicitações de clientes próximos.
    
    Args:
        request: AtualizarStatusRequest com is_online (true/false)
        db: Sessão do banco de dados
        current_user: Usuário autenticado
    
    Returns:
        RadarFreelancerResponse com status atual
    """
    
    # Pagamento diário vencido e não confirmado pelo ADM: radar travado em offline.
    from app.pagamento_diario import fechamento_bloqueante
    if request.is_online and fechamento_bloqueante(db, current_user.id):
        request.is_online = False

    # Buscar ou criar o radar para este barbeiro
    radar = db.query(RadarFreelancer).filter(
        RadarFreelancer.freelancer_id == current_user.id
    ).first()
    
    if not radar:
        radar = RadarFreelancer(
            freelancer_id=current_user.id,
            latitude=current_user.latitude,
            longitude=current_user.longitude,
            is_online=request.is_online
        )
        db.add(radar)
    else:
        radar.is_online = request.is_online
    
    radar.atualizado_em = datetime.utcnow()
    db.commit()
    db.refresh(radar)
    
    status_msg = "online ✅" if request.is_online else "offline ❌"
    print(f"📡 Barbeiro {current_user.nome} está {status_msg}")
    
    return RadarFreelancerResponse.from_orm(radar)


@router.post("/atualizar-localizacao", response_model=RadarFreelancerResponse, status_code=200)
async def atualizar_localizacao_barbeiro(
    request: AtualizarLocalizacaoRequest,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
    http_request: Request = None
):
    """
    Atualizar localização do barbeiro em tempo real via GPS.
    
    O React Native chama esse endpoint sempre que a localização muda,
    mantendo o backend sempre sincronizado com a posição do profissional.
    
    Args:
        request: AtualizarLocalizacaoRequest com latitude e longitude
        db: Sessão do banco de dados
        current_user: Usuário autenticado
    
    Returns:
        RadarFreelancerResponse com localização atualizada
    """
    
    # Segurança: não logar cabeçalhos (Authorization) nem payload com coordenadas.

    # Buscar ou criar o radar
    radar = db.query(RadarFreelancer).filter(
        RadarFreelancer.freelancer_id == current_user.id
    ).first()
    
    if not radar:
        radar = RadarFreelancer(
            freelancer_id=current_user.id,
            latitude=request.latitude,
            longitude=request.longitude,
            localizacao_atualizada_em=datetime.utcnow()
        )
        db.add(radar)
    else:
        radar.latitude = request.latitude
        radar.longitude = request.longitude
        radar.localizacao_atualizada_em = datetime.utcnow()
    
    # Também atualizar no usuário principal (para compatibilidade)
    current_user.latitude = request.latitude
    current_user.longitude = request.longitude
    
    db.commit()
    db.refresh(radar)
    
    print(f"📍 Localização atualizada: usuario_id={current_user.id}")
    
    return RadarFreelancerResponse.from_orm(radar)


@router.get("/barbeiros-proximos", response_model=List[BarbeiroProximoResponse], status_code=200)
async def buscar_barbeiros_proximos(
    latitude: float = Query(..., description="Latitude do cliente/barbearia"),
    longitude: float = Query(..., description="Longitude do cliente/barbearia"),
    raio_km: float = Query(5.0, description="Raio de busca em km"),
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    """
    Buscar barbeiros online próximos ao cliente usando Haversine.
    
    Retorna lista de barbeiros ordenados por distância.
    Este endpoint é chamado pelo cliente antes de fazer uma solicitação,
    para mostrar quem está disponível perto dele.
    
    Exemplo de output:
    [
        {
            "barbeiro_id": 10,
            "nome": "João Silva",
            "avaliacao": 4.8,
            "distancia_km": 2.3,
            "tempo_estimado_min": 8
        },
        ...
    ]
    
    Args:
        latitude, longitude: Coordenadas do cliente
        raio_km: Raio máximo de busca em km (default 5)
        db: Sessão do banco de dados
        current_user: Usuário autenticado
    
    Returns:
        List[BarbeiroProximoResponse]: Barbeiros próximos ordenados por distância
    """
    
    # Buscar todos os barbeiros online
    barbeiros_online = db.query(RadarFreelancer).filter(
        RadarFreelancer.is_online == True,
        _radar_elegivel_para_novo_clause(),
        RadarFreelancer.latitude.isnot(None),
        RadarFreelancer.longitude.isnot(None)
    ).all()
    
    if not barbeiros_online:
        return []
    
    # Calcular distância para cada barbeiro e filtrar por raio
    barbeiros_proximos = []
    
    for radar in barbeiros_online:
        distancia = calcular_distancia_haversine(
            latitude, longitude,
            radar.latitude, radar.longitude
        )
        
        # Filtrar apenas se está dentro do raio
        if distancia <= raio_km:
            barbeiro = db.query(Usuario).filter(Usuario.id == radar.freelancer_id).first()
            
            if barbeiro:
                # Estimativa: 1 km = 4 minutos (velocidade média em áreas urbanas)
                tempo_estimado = max(1, int(distancia * 4))
                
                barbeiros_proximos.append({
                    "barbeiro_id": barbeiro.id,
                    "nome": barbeiro.nome,
                    "avaliacao": 4.5,  # TODO: buscar de verdade da tabela de avaliações
                    "distancia_km": distancia,
                    "tempo_estimado_min": tempo_estimado
                })
    
    # Ordenar por distância (mais próximo primeiro)
    barbeiros_proximos.sort(key=lambda x: x["distancia_km"])
    
    print(f"🔍 Encontrados {len(barbeiros_proximos)} barbeiros próximos")
    
    return barbeiros_proximos


@router.post("/solicitar-barbeiro", response_model=SolicitacaoBarbeiroResponse, status_code=201)
async def solicitar_barbeiro(
    request: SolicitarBarbeiroRequest,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    """
    Cliente (ou barbearia) solicita um barbeiro agora.
    """
    barbearia_id_origem = None
    nome_barbearia_origem = "Próximo a você"
    if current_user.tipo == "barbearia":
        barbearia_origem = db.query(Barbearia).filter(Barbearia.usuario_id == current_user.id).order_by(Barbearia.id.asc()).first()
        if barbearia_origem:
            barbearia_id_origem = barbearia_origem.id
            nome_barbearia_origem = barbearia_origem.nome or nome_barbearia_origem

    solicitacao = SolicitacaoBarbeiro(
        cliente_id=current_user.id,
        barbearia_id=barbearia_id_origem,
        latitude=request.latitude,
        longitude=request.longitude,
        endereco=request.endereco,
        raio_km=request.raio_km,
        tipo_servico=request.tipo_servico,
        observacoes=request.observacoes,
        valor_oferta=request.valor_oferta,
        status="aguardando_resposta",
    )

    db.add(solicitacao)
    db.commit()
    db.refresh(solicitacao)

    barbeiros_proximos = db.query(RadarFreelancer).filter(
        RadarFreelancer.is_online == True,
        _radar_elegivel_para_novo_clause(),
        RadarFreelancer.latitude.isnot(None),
        RadarFreelancer.longitude.isnot(None),
    ).all()

    barbeiros_notificados = 0

    for radar in barbeiros_proximos:
        distancia = calcular_distancia_haversine(
            request.latitude,
            request.longitude,
            radar.latitude,
            radar.longitude,
        )

        if distancia <= request.raio_km:
            db.add(
                NotificacaoBarbeiro(
                    barbeiro_id=radar.freelancer_id,
                    solicitacao_id=solicitacao.id,
                    distancia_km=distancia,
                )
            )
            _registrar_visualizacao_solicitacao(db, solicitacao.id, radar.freelancer_id)

            barbeiro = db.query(Usuario).filter(Usuario.id == radar.freelancer_id).first()
            if barbeiro and barbeiro.device_token:
                enviar_notificacao_novo_chamado(
                    token_dispositivo=barbeiro.device_token,
                    nome_cliente=current_user.nome,
                    nome_servico=request.tipo_servico or "Serviço",
                    nome_barbearia=nome_barbearia_origem,
                )
                barbeiros_notificados += 1

    db.commit()
    db.refresh(solicitacao)

    print(f"🔔 Solicitação #{solicitacao.id} enviada para {barbeiros_notificados} barbeiros")
    return _serializar_solicitacao_com_views(db, solicitacao)


@router.get("/solicitacoes/{solicitacao_id}/visualizacoes", response_model=SolicitacaoBarbeiroResponse, status_code=200)
async def obter_visualizacoes_solicitacao(
    solicitacao_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    solicitacao = db.query(SolicitacaoBarbeiro).filter(SolicitacaoBarbeiro.id == solicitacao_id).first()
    if not solicitacao:
        raise HTTPException(status_code=404, detail="Solicitação não encontrada")

    if current_user.id != solicitacao.cliente_id and current_user.id != solicitacao.barbeiro_aceito_id:
        raise HTTPException(status_code=403, detail="Você não tem acesso a esta solicitação")

    return _serializar_solicitacao_com_views(db, solicitacao)


@router.post("/solicitacoes/{solicitacao_id}/visualizar", response_model=SolicitacaoBarbeiroResponse, status_code=200)
async def registrar_visualizacao_solicitacao(
    solicitacao_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    solicitacao = db.query(SolicitacaoBarbeiro).filter(SolicitacaoBarbeiro.id == solicitacao_id).first()
    if not solicitacao:
        raise HTTPException(status_code=404, detail="Solicitação não encontrada")

    if current_user.tipo != "barbeiro":
        raise HTTPException(status_code=403, detail="Apenas freelancers podem registrar visualização")

    _registrar_visualizacao_solicitacao(db, solicitacao.id, current_user.id)
    db.commit()
    db.refresh(solicitacao)
    return _serializar_solicitacao_com_views(db, solicitacao)


@router.post("/aceitar-solicitacao/{solicitacao_id}", status_code=200)
async def barbeiro_aceitar_solicitacao(
    solicitacao_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    """
    Barbeiro aceita uma solicitação On-Demand.
    
    Fluxo:
    1. Barbeiro clica "Aceitar" na notificação
    2. Status muda para "aceito"
    3. Barbeiro é marcado como "em_atendimento"
    4. Notificação é enviada para o cliente confirmando
    5. Outros barbeiros são automaticamente rejeitados
    
    Args:
        solicitacao_id: ID da solicitação
        db: Sessão do banco de dados
        current_user: Usuário autenticado (barbeiro)
    
    Returns:
        {
            "sucesso": true,
            "solicitacao_id": 123,
            "cliente_id": 456,
            "mensagem": "Solicitação aceita! É hora de trabalhar"
        }
    """

    from app.pagamento_diario import exigir_freelancer_liberado
    exigir_freelancer_liberado(db, current_user.id)
    
    # Buscar solicitação
    solicitacao = db.query(SolicitacaoBarbeiro).filter(
        SolicitacaoBarbeiro.id == solicitacao_id
    ).first()
    
    if not solicitacao:
        raise HTTPException(status_code=404, detail="Solicitação não encontrada")
    
    # Verificar se ainda está aguardando resposta
    if solicitacao.status != "aguardando_resposta":
        raise HTTPException(
            status_code=400,
            detail=f"Esta solicitação já foi {solicitacao.status}"
        )
    
    # Atualizar solicitação
    solicitacao.barbeiro_aceito_id = current_user.id
    solicitacao.status = "aceito"
    solicitacao.aceito_em = datetime.utcnow()
    
    # Marcar barbeiro como em atendimento
    radar = db.query(RadarFreelancer).filter(
        RadarFreelancer.freelancer_id == current_user.id
    ).first()
    
    if radar:
        radar.em_atendimento = True
        radar.cliente_atendimento_id = solicitacao.cliente_id
        radar.barbearia_atendimento_id = solicitacao.barbearia_id
        # SolicitacaoBarbeiro nao tem servico_id/duracao vinculada (so tipo_servico
        # em texto livre), entao usamos o mesmo fallback de 30 min do fluxo classico
        # so pra alimentar a janela de liberacao antecipada (_radar_elegivel_para_novo_clause).
        radar.ocupado_ate = datetime.now() + timedelta(minutes=30)

    db.commit()
    
    # Notificar cliente que barbeiro foi encontrado
    cliente = db.query(Usuario).filter(Usuario.id == solicitacao.cliente_id).first()
    if cliente and cliente.device_token:
        enviar_notificacao_novo_chamado(
            token_dispositivo=cliente.device_token,
            nome_cliente="Barbeiro encontrado!",
            nome_servico=f"{current_user.nome} está a caminho",
            nome_barbearia="",
            title="📍 O barbeiro está a caminho do seu local.",
            body="Fique pronto: ele chega em breve para começar seu atendimento."
        )
    
    print(f"✅ Barbeiro {current_user.nome} aceitou solicitação #{solicitacao_id}")
    
    return {
        "sucesso": True,
        "solicitacao_id": solicitacao.id,
        "cliente_id": solicitacao.cliente_id,
        "barbeiro_id": current_user.id,
        "mensagem": "Solicitação aceita! O barbeiro está a caminho do seu local."
    }


@router.post("/terminar-atendimento", status_code=200)
async def terminar_atendimento(
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    """
    Barbeiro termina o atendimento e volta a estar disponível.
    
    Isso libera o barbeiro para aceitar novas solicitações.
    
    Args:
        db: Sessão do banco de dados
        current_user: Usuário autenticado (barbeiro)
    
    Returns:
        {
            "sucesso": true,
            "mensagem": "Atendimento finalizado. Você está disponível novamente!"
        }
    """
    
    radar = db.query(RadarFreelancer).filter(
        RadarFreelancer.freelancer_id == current_user.id
    ).first()
    
    if not radar:
        raise HTTPException(status_code=404, detail="Radar do barbeiro não encontrado")
    
    # Buscar solicitação ativa
    if radar.cliente_atendimento_id:
        solicitacao = db.query(SolicitacaoBarbeiro).filter(
            SolicitacaoBarbeiro.cliente_id == radar.cliente_atendimento_id,
            SolicitacaoBarbeiro.status == "aceito"
        ).first()
        
        if solicitacao:
            solicitacao.status = "concluido"
            solicitacao.concluido_em = datetime.utcnow()
    
    # Liberar barbeiro
    radar.em_atendimento = False
    radar.cliente_atendimento_id = None
    radar.barbearia_atendimento_id = None
    radar.ocupado_ate = None
    
    db.commit()
    
    print(f"🏁 Barbeiro {current_user.nome} terminou atendimento")
    
    return {
        "sucesso": True,
        "mensagem": "Atendimento finalizado. Você está disponível para novas solicitações!"
    }


@router.get("/status-meu-radar", response_model=RadarFreelancerResponse, status_code=200)
async def obter_status_radar(
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    """
    Obter o status atual do radar do barbeiro.
    
    Usado pela tela do barbeiro para mostrar em tempo real seu status:
    - Online/Offline
    - Em atendimento ou disponível
    - Localização atual
    
    Args:
        db: Sessão do banco de dados
        current_user: Usuário autenticado (barbeiro)
    
    Returns:
        RadarFreelancerResponse com status atual
    """
    
    radar = db.query(RadarFreelancer).filter(
        RadarFreelancer.freelancer_id == current_user.id
    ).first()
    
    if not radar:
        # Se não existe, criar um
        radar = RadarFreelancer(
            freelancer_id=current_user.id,
            is_online=False,
            latitude=current_user.latitude,
            longitude=current_user.longitude
        )
        db.add(radar)
        db.commit()
        db.refresh(radar)
    
    return RadarFreelancerResponse.from_orm(radar)


def _posicao_do_freelancer(db: Session, freelancer_id: int) -> tuple:
    """Ultima posicao conhecida: a do radar (mesmo desligado) ou a salva no perfil."""
    radar = db.query(RadarFreelancer).filter(RadarFreelancer.freelancer_id == freelancer_id).first()
    if radar and radar.latitude is not None and radar.longitude is not None:
        return radar.latitude, radar.longitude
    usuario = db.query(Usuario).filter(Usuario.id == freelancer_id).first()
    return (usuario.latitude, usuario.longitude) if usuario else (None, None)


def _dentro_do_raio(distancia_km: float, raio_km: float) -> bool:
    """Inclui quem esta exatamente na borda (1 mm de folga para o arredondamento do haversine)."""
    return distancia_km <= raio_km + 1e-6


def _freelancers_elegiveis_para_aviso_de_vaga(db: Session) -> List[int]:
    """
    Ids de todo freelancer aprovado e nao bloqueado pelo ADM, de qualquer regiao e com ou
    sem posicao conhecida: a vaga de diaria vale para a capital inteira, sem raio.

    Nao olha `radar.is_online`: ele so indica que o painel esta aberto no celular (liga ao
    abrir, desliga no logout) e nao e o status ONLINE/OFFLINE escolhido pelo freelancer.
    """
    linhas = db.query(Usuario.id).filter(
        Usuario.tipo == "barbeiro",
        Usuario.perfil_aprovado == True,  # noqa: E712
        Usuario.bloqueado_por_admin.isnot(True),
        Usuario.cadastro_pendente.isnot(True),
    ).all()
    return [freelancer_id for (freelancer_id,) in linhas]


def _avisar_freelancers_da_vaga(
    db: Session,
    barbearia: Barbearia,
    vaga: CadeiraAcionada,
    raio_km: Optional[float],
    autor_id: int,
    nome_servico: str,
    mensagem: str,
    todos_os_elegiveis: bool = False,
) -> List[int]:
    """
    Avisa os freelancers (sino + push) e devolve os ids avisados.

    todos_os_elegiveis=False (vaga relampago): so quem esta com o radar ligado, livre e
    dentro de `raio_km`.
    todos_os_elegiveis=True (anuncio de vaga de diaria): todo freelancer aprovado, de
    qualquer regiao, ONLINE ou OFFLINE, ocupado ou com taxa pendente, sem raio. O aviso so
    informa a oportunidade; a candidatura continua com as regras dela.
    """
    if todos_os_elegiveis:
        destinos = _freelancers_elegiveis_para_aviso_de_vaga(db)
    else:
        barbeiros_online = db.query(RadarFreelancer).filter(
            RadarFreelancer.is_online == True,
            _radar_elegivel_para_novo_clause(),
            RadarFreelancer.latitude.isnot(None),
            RadarFreelancer.longitude.isnot(None),
        ).all()
        destinos = [
            radar.freelancer_id
            for radar in barbeiros_online
            if _dentro_do_raio(
                calcular_distancia_haversine(barbearia.latitude, barbearia.longitude, radar.latitude, radar.longitude),
                raio_km,
            )
        ]

    avisados = []
    for freelancer_id in destinos:
        barbeiro = db.query(Usuario).filter(Usuario.id == freelancer_id).first()
        # Quem anunciou a vaga nao e notificado do proprio anuncio.
        if not barbeiro or barbeiro.id == autor_id:
            continue

        # Fica registrada no sino de notificacoes do freelancer, alem do push
        # (push exige device_token e pode nao chegar; a notificacao no sino
        # fica disponivel de qualquer forma).
        db.add(Notificacao(
            usuario_id=barbeiro.id,
            titulo="Nova vaga de cadeira disponível 💈",
            mensagem=mensagem,
            tipo="vaga_disponivel",
            referencia_id=vaga.id,
        ))
        avisados.append(barbeiro.id)

        if barbeiro.device_token:
            enviar_notificacao_novo_chamado(
                token_dispositivo=barbeiro.device_token,
                nome_cliente="BarberMove",
                nome_servico=nome_servico,
                nome_barbearia=barbearia.nome,
            )

    db.commit()
    return avisados


def _barbearia_do_dono(db: Session, current_user: Usuario) -> Barbearia:
    if current_user.tipo != "barbearia":
        raise HTTPException(status_code=403, detail="Apenas barbearias podem anunciar vagas")

    barbearia = db.query(Barbearia).filter(Barbearia.usuario_id == current_user.id).order_by(Barbearia.id.asc()).first()
    if not barbearia:
        raise HTTPException(status_code=404, detail="Barbearia nao encontrada")
    return barbearia


def _resumo_de_vagas(db: Session, barbearia: Barbearia, usuario_id: int) -> dict:
    limites = limites_de_anuncio(db, barbearia)
    ativas = limites["ativas"]
    numero_cadeira = {cadeira.id: cadeira.numero for cadeira in limites["cadeiras"]}
    nao_lidas = nao_lidas_por_vaga(db, [vaga.id for vaga in ativas], usuario_id)

    vagas = []
    for vaga in sorted(ativas, key=lambda item: (numero_cadeira.get(item.cadeira_id, 9999), item.id)):
        total_candidatos = db.query(CadeiraAcionadaCandidatura).filter(
            CadeiraAcionadaCandidatura.vaga_id == vaga.id
        ).count()
        vagas.append({
            **_serializar_cadeira_acionada(vaga),
            "cadeira_bloqueada": cadeira_esta_bloqueada(vaga.cadeira),
            "barbeiro_nome": vaga.barbeiro.nome if vaga.barbeiro else None,
            "total_candidatos": total_candidatos,
            "nao_lidas": nao_lidas.get(vaga.id, 0),
        })

    return {
        "cadeiras_pagas": limites["cadeiras_pagas"],
        "cadeiras_vencidas": cadeiras_vencidas(db, barbearia),
        "vagas_anunciadas": len(ativas),
        "vagas_disponiveis_para_anunciar": limites["disponiveis"],
        "cadeiras_livres": [
            {
                "id": cadeira.id,
                "numero": cadeira.numero,
                "bloqueada": cadeira_esta_bloqueada(cadeira),
            }
            for cadeira in limites["livres"]
        ],
        "vagas": vagas,
    }


@router.get("/cadeiras-acionadas/resumo", status_code=200)
async def resumo_de_vagas(
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    """Limite de vagas pelas cadeiras pagas e vagas ativas, para a tela inicial do dono."""
    barbearia = _barbearia_do_dono(db, current_user)
    _expirar_vagas_vencidas(db)
    return _resumo_de_vagas(db, barbearia, current_user.id)


@router.post("/cadeiras-acionadas/anunciar", status_code=201)
async def anunciar_vagas(
    request: AnunciarVagasRequest,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    """
    Publica a quantidade pedida de vagas diarias, cada uma com a propria cadeira e as proprias
    candidaturas. Podem ser cadeiras bloqueadas; o status delas nao muda aqui.
    """
    if not request.cadeira_ids and not request.quantidade:
        raise HTTPException(status_code=400, detail="Escolha ao menos uma cadeira para anunciar")

    barbearia = _barbearia_do_dono(db, current_user)
    if barbearia.latitude is None or barbearia.longitude is None:
        raise HTTPException(
            status_code=400,
            detail="Não encontramos a localização da sua barbearia. Confira o endereço e o CEP no perfil.",
        )
    # Vaga de diaria vale para a capital inteira; barbearia de municipio vizinho nao anuncia.
    local = localizar_na_capital(barbearia.latitude, barbearia.longitude)
    if not local:
        raise HTTPException(
            status_code=400,
            detail="As vagas de diária atendem apenas barbearias no município de São Paulo (capital).",
        )

    _expirar_vagas_vencidas(db)

    if request.cadeira_ids:
        cadeiras = reservar_cadeiras(db, barbearia, len(set(request.cadeira_ids)), cadeira_ids=request.cadeira_ids)
    else:
        cadeiras = reservar_cadeiras(db, barbearia, request.quantidade)
    expira_em = fim_do_dia_utc()
    vagas = [
        CadeiraAcionada(
            barbearia_id=barbearia.id,
            cadeira_id=cadeira.id,
            status=STATUS_ABERTA,
            # Sem raio: a coluna recebe o default, que a vaga de diaria ignora (sai None na API).
            tipo_servico=TIPO_VAGA_DIARIA,
            percentual_freelancer=round(request.percentual_freelancer, 2),
            expira_em=expira_em,
        )
        for cadeira in cadeiras
    ]
    db.add_all(vagas)
    db.commit()

    avisados = _avisar_freelancers_da_vaga(
        db,
        barbearia,
        vagas[0],
        None,
        current_user.id,
        nome_servico="Vaga de cadeira",
        todos_os_elegiveis=True,
        mensagem=(
            f"{barbearia.nome} anunciou {len(vagas)} vagas de cadeira na {local['regiao']} ({local['subprefeitura']})."
            if len(vagas) > 1
            else f"{barbearia.nome} anunciou uma vaga de cadeira na {local['regiao']} ({local['subprefeitura']})."
        ),
    )

    # Vaga diaria e so para freelancers: nao entra no broadcast geral, que chega aos clientes.
    # Um evento por freelancer basta; as demais vagas chegam na proxima atualizacao do painel.
    for freelancer_id in avisados:
        await broadcast_event(
            "cadeira_acionada_aberta",
            destinatario_id=freelancer_id,
            vaga=_serializar_cadeira_acionada(vagas[0]),
        )

    return {
        "publicadas": [vaga.id for vaga in vagas],
        **_resumo_de_vagas(db, barbearia, current_user.id),
    }


@router.post("/cadeiras-acionadas/acionar", response_model=CadeiraAcionadaResponse, status_code=201)
async def acionar_cadeira_relampago(
    request: AcionarCadeiraRequest,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    """Barbearia aciona cadeira para disputa em tempo real entre barbeiros e clientes proximos."""
    if current_user.tipo != "barbearia":
        raise HTTPException(status_code=403, detail="Apenas barbearias podem acionar cadeira")

    barbearia = db.query(Barbearia).filter(Barbearia.usuario_id == current_user.id).order_by(Barbearia.id.asc()).first()
    if not barbearia:
        raise HTTPException(status_code=404, detail="Barbearia nao encontrada")

    if barbearia.latitude is None or barbearia.longitude is None:
        raise HTTPException(status_code=400, detail="Barbearia sem coordenadas para validar ETA")

    if request.raio_km <= 0:
        raise HTTPException(status_code=400, detail="Raio deve ser maior que zero")

    if request.expira_em_minutos <= 0:
        raise HTTPException(status_code=400, detail="expira_em_minutos deve ser maior que zero")

    _expirar_vagas_vencidas(db)

    cadeira = reservar_cadeiras(db, barbearia, 1, cadeira_id=request.cadeira_id)[0]
    cadeira_bloqueada = cadeira_esta_bloqueada(cadeira)

    vaga = CadeiraAcionada(
        barbearia_id=barbearia.id,
        cadeira_id=cadeira.id,
        status="disponivel",
        raio_km=float(request.raio_km),
        tipo_servico=request.tipo_servico,
        valor_oferta=request.valor_oferta,
        observacoes=request.observacoes,
        expira_em=datetime.utcnow() + timedelta(minutes=request.expira_em_minutos),
    )

    db.add(vaga)
    db.commit()
    db.refresh(vaga)

    # Frente A: notificar barbeiros online no raio configurado
    avisados = _avisar_freelancers_da_vaga(
        db,
        barbearia,
        vaga,
        request.raio_km,
        current_user.id,
        nome_servico=request.tipo_servico or "Vaga relampago",
        mensagem=f"{barbearia.nome} anunciou uma vaga de cadeira perto de você.",
    )

    if cadeira_bloqueada:
        # Cadeira bloqueada nao recebe cliente: o evento vai so para os freelancers avisados.
        for freelancer_id in avisados:
            await broadcast_event(
                "cadeira_acionada_aberta",
                destinatario_id=freelancer_id,
                vaga=_serializar_cadeira_acionada(vaga),
            )
    else:
        await broadcast_event(
            "cadeira_acionada_aberta",
            autor_id=current_user.id,
            vaga=_serializar_cadeira_acionada(vaga),
        )

    return _serializar_cadeira_acionada(vaga)


@router.get("/cadeiras-acionadas/ativas", response_model=List[CadeiraAcionadaResponse], status_code=200)
async def listar_cadeiras_acionadas_ativas(
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    """
    Vagas que o usuario atual pode ver. Vaga de diaria: a capital inteira, sem raio, so para
    freelancer. Vaga relampago: radar ligado (ou cliente) com ETA <= 10 min.
    """
    _expirar_vagas_vencidas(db)

    vagas = db.query(CadeiraAcionada).filter(
        CadeiraAcionada.status == "disponivel"
    ).order_by(CadeiraAcionada.criado_em.desc()).all()

    if not vagas:
        return []

    from app.pagamento_diario import freelancer_bloqueado
    com_taxa_pendente = current_user.tipo == "barbeiro" and freelancer_bloqueado(db, current_user.id)

    resultado = []
    # Vaga diaria fica aberta o dia todo e a barbearia pode ter varias: uma rota por barbearia basta.
    eta_por_barbearia = {}

    def _eta_ate(barbearia_alvo, origem_lat, origem_lon):
        if barbearia_alvo.id not in eta_por_barbearia:
            eta_por_barbearia[barbearia_alvo.id] = _calcular_eta_minutos(
                origem_lat,
                origem_lon,
                barbearia_alvo.latitude,
                barbearia_alvo.longitude,
            )
        return eta_por_barbearia[barbearia_alvo.id]

    for vaga in vagas:
        barbearia = db.query(Barbearia).filter(Barbearia.id == vaga.barbearia_id).first()
        if not barbearia or barbearia.latitude is None or barbearia.longitude is None:
            continue

        if current_user.tipo == "barbeiro" and (com_taxa_pendente or vaga.tipo_servico == TIPO_VAGA_DIARIA):
            # Vaga de diaria: vale para a capital inteira. Qualquer freelancer ve todas, de
            # qualquer regiao, ONLINE ou OFFLINE, com ou sem posicao (com taxa pendente, so
            # essas). Nao ha raio; o ETA so informa, quando a posicao e conhecida.
            if vaga.tipo_servico != TIPO_VAGA_DIARIA:
                continue
            if not esta_na_capital(barbearia.latitude, barbearia.longitude):
                continue
            eta_min = None
            origem_lat, origem_lon = _posicao_do_freelancer(db, current_user.id)
            if origem_lat is not None and origem_lon is not None:
                distancia_km = calcular_distancia_haversine(barbearia.latitude, barbearia.longitude, origem_lat, origem_lon)
                eta_min = _estimar_eta_minutos_por_distancia(distancia_km)
        elif current_user.tipo == "barbeiro":
            radar = db.query(RadarFreelancer).filter(
                RadarFreelancer.freelancer_id == current_user.id,
                RadarFreelancer.is_online == True,
                _radar_elegivel_para_novo_clause(),
            ).first()
            if not radar:
                continue

            eta_min = None
            # Prioriza a posição em tempo real do radar para não depender de
            # coordenadas antigas salvas no perfil do usuário.
            origem_lat = radar.latitude if radar.latitude is not None else current_user.latitude
            origem_lon = radar.longitude if radar.longitude is not None else current_user.longitude

            if origem_lat is not None and origem_lon is not None:
                eta_min = _eta_ate(barbearia, origem_lat, origem_lon)
                if eta_min > 10:
                    continue
        elif current_user.tipo == "cliente":
            # Vaga diaria e para freelancers, e cadeira bloqueada nao recebe cliente.
            if vaga.tipo_servico == TIPO_VAGA_DIARIA or cadeira_esta_bloqueada(vaga.cadeira):
                continue

            if current_user.latitude is None or current_user.longitude is None:
                continue

            eta_min = _eta_ate(barbearia, current_user.latitude, current_user.longitude)
            if eta_min > 10:
                continue
        else:
            continue

        resultado.append(_serializar_cadeira_acionada(vaga, eta_min_usuario_atual=eta_min))

    return resultado


@router.get("/cadeiras-acionadas/minhas", response_model=List[CadeiraAcionadaResponse], status_code=200)
async def listar_cadeiras_acionadas_minhas(
    limite: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    """Lista vagas relampago da barbearia autenticada para monitoramento no painel."""
    if current_user.tipo != "barbearia":
        raise HTTPException(status_code=403, detail="Apenas barbearias podem visualizar suas vagas")

    barbearia = db.query(Barbearia).filter(Barbearia.usuario_id == current_user.id).order_by(Barbearia.id.asc()).first()
    if not barbearia:
        raise HTTPException(status_code=404, detail="Barbearia nao encontrada")

    _expirar_vagas_vencidas(db)

    vagas = db.query(CadeiraAcionada).filter(
        CadeiraAcionada.barbearia_id == barbearia.id,
    ).order_by(CadeiraAcionada.criado_em.desc()).limit(limite).all()

    return [_serializar_cadeira_acionada(vaga) for vaga in vagas]


@router.post("/cadeiras-acionadas/{vaga_id}/cancelar", response_model=CadeiraAcionadaResponse, status_code=200)
async def cancelar_cadeira_acionada(
    vaga_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    """Barbearia cancela vaga ainda disponivel ou dispensa o escolhido antes do desbloqueio."""
    if current_user.tipo != "barbearia":
        raise HTTPException(status_code=403, detail="Apenas barbearias podem cancelar vaga")

    barbearia = db.query(Barbearia).filter(Barbearia.usuario_id == current_user.id).order_by(Barbearia.id.asc()).first()
    if not barbearia:
        raise HTTPException(status_code=404, detail="Barbearia nao encontrada")

    vaga = db.query(CadeiraAcionada).filter(CadeiraAcionada.id == vaga_id).first()
    if not vaga:
        raise HTTPException(status_code=404, detail="Vaga nao encontrada")

    if vaga.barbearia_id != barbearia.id:
        raise HTTPException(status_code=403, detail="Vaga nao pertence a esta barbearia")

    if vaga.status not in (STATUS_ABERTA, STATUS_AGUARDANDO_DESBLOQUEIO):
        raise HTTPException(status_code=409, detail=f"Vaga nao pode ser cancelada (status: {vaga.status})")

    if vaga.status == STATUS_AGUARDANDO_DESBLOQUEIO and vaga.barbeiro_id:
        db.add(Notificacao(
            usuario_id=vaga.barbeiro_id,
            titulo="Vaga de cadeira cancelada",
            mensagem=f"{barbearia.nome} cancelou a vaga para a qual você tinha sido escolhido.",
            tipo="vaga_encerrada",
            referencia_id=vaga.id,
        ))

    vaga.status = STATUS_CANCELADA
    vaga.atualizado_em = datetime.utcnow()
    db.commit()
    db.refresh(vaga)

    await broadcast_event(
        "cadeira_acionada_fechada",
        autor_id=current_user.id,
        vaga=_serializar_cadeira_acionada(vaga),
        accepted_by="barbearia",
    )

    return _serializar_cadeira_acionada(vaga)


@router.post("/cadeiras-acionadas/{vaga_id}/candidatar-se", response_model=CadeiraAcionadaResponse, status_code=200)
async def candidatar_se_cadeira_acionada(
    vaga_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    """
    Barbeiro manifesta interesse na vaga (candidatura). Nao assume a cadeira,
    nao muda o status da vaga e nao altera presente_em_local - so registra o
    interesse pra barbearia escolher depois (ver escolher_freelancer_cadeira_acionada).
    """
    if current_user.tipo != "barbeiro":
        raise HTTPException(status_code=403, detail="Apenas barbeiros podem se candidatar a essa vaga")

    from app.pagamento_diario import MENSAGEM_TAXA_PENDENTE, freelancer_bloqueado
    if freelancer_bloqueado(db, current_user.id):
        raise HTTPException(status_code=403, detail=MENSAGEM_TAXA_PENDENTE)

    _expirar_vagas_vencidas(db)

    vaga = db.query(CadeiraAcionada).filter(CadeiraAcionada.id == vaga_id).first()
    if not vaga:
        raise HTTPException(status_code=404, detail="Vaga nao encontrada")
    vaga_diaria = vaga.tipo_servico == TIPO_VAGA_DIARIA

    # Vaga de diaria vale para a capital inteira: nao pede localizacao do freelancer.
    if not vaga_diaria and (current_user.latitude is None or current_user.longitude is None):
        raise HTTPException(status_code=400, detail="Localizacao obrigatoria para se candidatar a vaga")

    radar = db.query(RadarFreelancer).filter(
        RadarFreelancer.freelancer_id == current_user.id,
        RadarFreelancer.is_online == True,
        _radar_elegivel_para_novo_clause(),
    ).first()
    if not radar:
        raise HTTPException(status_code=400, detail="Fique online no radar para se candidatar a vaga")

    if vaga.status != "disponivel":
        raise HTTPException(status_code=409, detail=f"Vaga indisponivel (status: {vaga.status})")

    barbearia = db.query(Barbearia).filter(Barbearia.id == vaga.barbearia_id).first()
    if not barbearia or barbearia.latitude is None or barbearia.longitude is None:
        raise HTTPException(status_code=400, detail="Barbearia sem coordenadas para validar ETA")

    if vaga_diaria:
        # Sem limite de distancia/ETA: freelancer de qualquer regiao se candidata a qualquer
        # vaga da capital. O ETA so acompanha a resposta, quando a posicao e conhecida.
        if not esta_na_capital(barbearia.latitude, barbearia.longitude):
            raise HTTPException(
                status_code=400,
                detail="As vagas de diária atendem apenas barbearias no município de São Paulo (capital).",
            )
        eta_min = None
        origem_lat, origem_lon = _posicao_do_freelancer(db, current_user.id)
        if origem_lat is not None and origem_lon is not None:
            eta_min = _estimar_eta_minutos_por_distancia(
                calcular_distancia_haversine(barbearia.latitude, barbearia.longitude, origem_lat, origem_lon)
            )
    else:
        eta_min = _calcular_eta_minutos(
            current_user.latitude,
            current_user.longitude,
            barbearia.latitude,
            barbearia.longitude,
        )
        if eta_min > 10:
            raise HTTPException(status_code=400, detail="Voce esta muito longe desta barbearia (limite maximo de 10 min)")

    candidatura = db.query(CadeiraAcionadaCandidatura).filter(
        CadeiraAcionadaCandidatura.vaga_id == vaga_id,
        CadeiraAcionadaCandidatura.barbeiro_id == current_user.id,
    ).first()
    if not candidatura:
        db.add(CadeiraAcionadaCandidatura(vaga_id=vaga_id, barbeiro_id=current_user.id))

        if barbearia.usuario_id:
            db.add(Notificacao(
                usuario_id=barbearia.usuario_id,
                titulo="Novo candidato para vaga de cadeira 💈",
                mensagem=f"{current_user.nome} se candidatou para a vaga de cadeira.",
                tipo="vaga_candidatura",
                referencia_id=vaga.id,
            ))

        db.commit()

        dono = db.query(Usuario).filter(Usuario.id == barbearia.usuario_id).first() if barbearia.usuario_id else None
        if dono and dono.device_token:
            enviar_notificacao_novo_chamado(
                token_dispositivo=dono.device_token,
                nome_cliente=current_user.nome,
                nome_servico="se candidatou para sua vaga de cadeira",
                nome_barbearia=barbearia.nome,
                title="Novo candidato para vaga de cadeira 💈",
                body=f"{current_user.nome} quer assumir a cadeira anunciada.",
            )

        await broadcast_event(
            "cadeira_acionada_candidatura",
            autor_id=current_user.id,
            vaga_id=vaga.id,
            barbearia_id=vaga.barbearia_id,
        )

    return _serializar_cadeira_acionada(vaga, eta_min_usuario_atual=eta_min)


@router.get("/cadeiras-acionadas/{vaga_id}/candidatos", response_model=List[CandidatoCadeiraAcionadaResponse], status_code=200)
async def listar_candidatos_cadeira_acionada(
    vaga_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    """Barbearia visualiza os freelancers candidatos aquela vaga de cadeira."""
    if current_user.tipo != "barbearia":
        raise HTTPException(status_code=403, detail="Apenas barbearias podem ver os candidatos da vaga")

    barbearia = db.query(Barbearia).filter(Barbearia.usuario_id == current_user.id).order_by(Barbearia.id.asc()).first()
    if not barbearia:
        raise HTTPException(status_code=404, detail="Barbearia nao encontrada")

    vaga = db.query(CadeiraAcionada).filter(CadeiraAcionada.id == vaga_id).first()
    if not vaga:
        raise HTTPException(status_code=404, detail="Vaga nao encontrada")
    if vaga.barbearia_id != barbearia.id:
        raise HTTPException(status_code=403, detail="Vaga nao pertence a esta barbearia")

    candidaturas = (
        db.query(CadeiraAcionadaCandidatura, Usuario)
        .join(Usuario, Usuario.id == CadeiraAcionadaCandidatura.barbeiro_id)
        .filter(CadeiraAcionadaCandidatura.vaga_id == vaga_id)
        .order_by(CadeiraAcionadaCandidatura.criado_em.asc())
        .all()
    )

    def _distancia_ate_barbearia(freelancer_id: int) -> Optional[float]:
        # Apenas exibicao na lista de candidatos: nao filtra nem limita nada.
        if barbearia.latitude is None or barbearia.longitude is None:
            return None
        lat, lon = _posicao_do_freelancer(db, freelancer_id)
        if lat is None or lon is None:
            return None
        return round(calcular_distancia_haversine(barbearia.latitude, barbearia.longitude, lat, lon), 1)

    return [
        CandidatoCadeiraAcionadaResponse(
            id=candidatura.id,
            freelancer_id=freelancer.id,
            nome=freelancer.nome,
            foto_perfil=getattr(freelancer, "foto_perfil", None),
            criado_em=candidatura.criado_em,
            distancia_km=_distancia_ate_barbearia(freelancer.id),
        )
        for candidatura, freelancer in candidaturas
    ]


@router.post("/cadeiras-acionadas/{vaga_id}/escolher-freelancer", response_model=CadeiraAcionadaResponse, status_code=200)
async def escolher_freelancer_cadeira_acionada(
    vaga_id: int,
    request: EscolherFreelancerRequest,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    """
    Barbearia escolhe, entre os candidatos, quem assume a vaga de cadeira.
    So a partir daqui o freelancer escolhido assume a cadeira e fica
    PRESENTE_NA_BARBEARIA (mesmo comportamento que ja existia em "assumir
    cadeira" - so o gatilho passou a ser a escolha da barbearia, nao mais o
    primeiro aceite do freelancer).
    """
    if current_user.tipo != "barbearia":
        raise HTTPException(status_code=403, detail="Apenas barbearias podem escolher o freelancer da vaga")

    barbearia = db.query(Barbearia).filter(Barbearia.usuario_id == current_user.id).order_by(Barbearia.id.asc()).first()
    if not barbearia:
        raise HTTPException(status_code=404, detail="Barbearia nao encontrada")

    _expirar_vagas_vencidas(db)

    vaga = db.query(CadeiraAcionada).filter(CadeiraAcionada.id == vaga_id).first()
    if not vaga:
        raise HTTPException(status_code=404, detail="Vaga nao encontrada")
    if vaga.barbearia_id != barbearia.id:
        raise HTTPException(status_code=403, detail="Vaga nao pertence a esta barbearia")
    if vaga.status != "disponivel":
        raise HTTPException(status_code=409, detail=f"Vaga indisponivel (status: {vaga.status})")

    # A cadeira nao pode mudar de mao nem o freelancer ser escolhido duas vezes em paralelo.
    travar_barbearia(db, barbearia.id)
    cadeira_da_vaga = db.query(Cadeira).filter(Cadeira.id == vaga.cadeira_id).first() if vaga.cadeira_id else None
    if cadeira_da_vaga and cadeira_da_vaga.freelancer_id not in (None, request.barbeiro_id):
        raise HTTPException(status_code=409, detail="Esta cadeira ja esta com outro freelancer")

    ja_escolhido = db.query(CadeiraAcionada).filter(
        CadeiraAcionada.barbeiro_id == request.barbeiro_id,
        CadeiraAcionada.status == STATUS_AGUARDANDO_DESBLOQUEIO,
    ).first()
    if ja_escolhido:
        raise HTTPException(status_code=409, detail="Este freelancer ja foi escolhido para outra vaga")

    # Cadeira bloqueada continua bloqueada: o freelancer so assume no desbloqueio manual.
    aguardando_desbloqueio = cadeira_esta_bloqueada(cadeira_da_vaga)

    from app.pagamento_diario import fechamento_bloqueante
    if fechamento_bloqueante(db, request.barbeiro_id):
        raise HTTPException(status_code=409, detail="Este freelancer está indisponível no momento")

    candidatura_escolhida = db.query(CadeiraAcionadaCandidatura).filter(
        CadeiraAcionadaCandidatura.vaga_id == vaga_id,
        CadeiraAcionadaCandidatura.barbeiro_id == request.barbeiro_id,
    ).first()
    if not candidatura_escolhida:
        raise HTTPException(status_code=404, detail="Este freelancer nao se candidatou a esta vaga")

    atualizado = db.query(CadeiraAcionada).filter(
        CadeiraAcionada.id == vaga_id,
        CadeiraAcionada.status == "disponivel",
    ).update(
        {
            CadeiraAcionada.status: STATUS_AGUARDANDO_DESBLOQUEIO if aguardando_desbloqueio else STATUS_OCUPADA,
            CadeiraAcionada.barbeiro_id: request.barbeiro_id,
            CadeiraAcionada.cliente_id: None,
            CadeiraAcionada.limite_chegada: None if aguardando_desbloqueio else datetime.utcnow() + timedelta(minutes=10),
            CadeiraAcionada.atualizado_em: datetime.utcnow(),
        },
        synchronize_session=False,
    )

    if atualizado == 0:
        raise HTTPException(status_code=409, detail="Esta vaga acabou de deixar de estar disponivel")

    # Freelancer escolhido: mesmo comportamento ja existente de "assumir cadeira"
    # (Etapa 7 - fixa o local de atendimento, sai do "disponivel na regiao").
    if aguardando_desbloqueio:
        usuario_escolhido = db.query(Usuario).filter(Usuario.id == request.barbeiro_id).first()
    else:
        usuario_escolhido = aplicar_freelancer_na_cadeira(db, vaga, request.barbeiro_id)

    db.add(Notificacao(
        usuario_id=request.barbeiro_id,
        titulo="Você foi escolhido para a vaga! 🎉",
        mensagem=(
            f"{barbearia.nome} escolheu você para a vaga. Combine pelo chat da vaga; a cadeira será liberada quando você chegar."
            if aguardando_desbloqueio
            else f"{barbearia.nome} escolheu você para a vaga de cadeira anunciada."
        ),
        tipo="vaga_escolhido",
        referencia_id=vaga.id,
    ))

    # Demais candidatos: vaga preenchida por outro freelancer.
    outros_candidatos = db.query(CadeiraAcionadaCandidatura, Usuario).join(
        Usuario, Usuario.id == CadeiraAcionadaCandidatura.barbeiro_id
    ).filter(
        CadeiraAcionadaCandidatura.vaga_id == vaga_id,
        CadeiraAcionadaCandidatura.barbeiro_id != request.barbeiro_id,
    ).all()

    for _candidatura, freelancer_nao_escolhido in outros_candidatos:
        db.add(Notificacao(
            usuario_id=freelancer_nao_escolhido.id,
            titulo="Vaga de cadeira preenchida",
            mensagem=f"{barbearia.nome} escolheu outro freelancer para a vaga anunciada.",
            tipo="vaga_nao_escolhido",
            referencia_id=vaga.id,
        ))

    db.commit()
    vaga = db.query(CadeiraAcionada).filter(CadeiraAcionada.id == vaga_id).first()

    if usuario_escolhido and usuario_escolhido.device_token:
        enviar_notificacao_novo_chamado(
            token_dispositivo=usuario_escolhido.device_token,
            nome_cliente="Você foi escolhido!",
            nome_servico=f"{barbearia.nome} selecionou você para a vaga",
            nome_barbearia=barbearia.nome,
            title="Você foi escolhido para a vaga! 🎉",
            body=(
                "Combine a chegada pelo chat da vaga."
                if aguardando_desbloqueio
                else "Dirija-se a barbearia para assumir a cadeira."
            ),
        )

    for _candidatura, freelancer_nao_escolhido in outros_candidatos:
        if freelancer_nao_escolhido.device_token:
            enviar_notificacao_novo_chamado(
                token_dispositivo=freelancer_nao_escolhido.device_token,
                nome_cliente="Vaga preenchida",
                nome_servico="outro freelancer foi escolhido para a vaga",
                nome_barbearia=barbearia.nome,
                title="Vaga de cadeira preenchida",
                body=f"{barbearia.nome} escolheu outro freelancer para a vaga anunciada.",
            )

    await broadcast_event(
        "cadeira_acionada_fechada",
        autor_id=current_user.id,
        vaga=_serializar_cadeira_acionada(vaga),
        accepted_by="barbearia_escolheu",
    )
    if usuario_escolhido and not aguardando_desbloqueio:
        await broadcast_event(
            "freelancer_status_changed",
            autor_id=current_user.id,
            freelancer_id=usuario_escolhido.id,
            barbearia_id=usuario_escolhido.barbearia_atual_id,
            presente_em_local=True,
            online_regiao=False,
            disponivel=True,
            saida_pendente=None,
        )

    return _serializar_cadeira_acionada(vaga)


@router.post("/cadeiras-acionadas/{vaga_id}/aceitar-cliente", response_model=CadeiraAcionadaResponse, status_code=200)
async def aceitar_cadeira_acionada_como_cliente(
    vaga_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    """Cliente tenta reservar a vaga relampago. Primeiro aceite valido e ETA <= 10 min vence."""
    if current_user.tipo != "cliente":
        raise HTTPException(status_code=403, detail="Apenas clientes podem reservar essa vaga")

    if current_user.latitude is None or current_user.longitude is None:
        raise HTTPException(status_code=400, detail="Localizacao obrigatoria para reservar a vaga")

    _expirar_vagas_vencidas(db)

    vaga = db.query(CadeiraAcionada).filter(CadeiraAcionada.id == vaga_id).first()
    if not vaga:
        raise HTTPException(status_code=404, detail="Vaga nao encontrada")

    if vaga.status != "disponivel":
        raise HTTPException(status_code=409, detail=f"Vaga indisponivel (status: {vaga.status})")

    if vaga.tipo_servico == TIPO_VAGA_DIARIA or cadeira_esta_bloqueada(vaga.cadeira):
        raise HTTPException(status_code=409, detail="Esta vaga nao esta aberta para clientes")

    barbearia = db.query(Barbearia).filter(Barbearia.id == vaga.barbearia_id).first()
    if not barbearia or barbearia.latitude is None or barbearia.longitude is None:
        raise HTTPException(status_code=400, detail="Barbearia sem coordenadas para validar ETA")

    eta_min = _calcular_eta_minutos(
        current_user.latitude,
        current_user.longitude,
        barbearia.latitude,
        barbearia.longitude,
    )
    if eta_min > 10:
        raise HTTPException(status_code=400, detail="Voce esta muito longe desta barbearia (limite maximo de 10 min)")

    atualizado = db.query(CadeiraAcionada).filter(
        CadeiraAcionada.id == vaga_id,
        CadeiraAcionada.status == "disponivel",
    ).update(
        {
            CadeiraAcionada.status: "reservada_por_cliente",
            CadeiraAcionada.cliente_id: current_user.id,
            CadeiraAcionada.barbeiro_id: None,
            CadeiraAcionada.limite_chegada: datetime.utcnow() + timedelta(minutes=10),
            CadeiraAcionada.atualizado_em: datetime.utcnow(),
        },
        synchronize_session=False,
    )

    if atualizado == 0:
        raise HTTPException(status_code=409, detail="Outro usuario aceitou esta vaga primeiro")

    db.commit()
    vaga = db.query(CadeiraAcionada).filter(CadeiraAcionada.id == vaga_id).first()

    await broadcast_event(
        "cadeira_acionada_fechada",
        autor_id=current_user.id,
        vaga=_serializar_cadeira_acionada(vaga, eta_min_usuario_atual=eta_min),
        accepted_by="cliente",
    )

    return _serializar_cadeira_acionada(vaga, eta_min_usuario_atual=eta_min)
