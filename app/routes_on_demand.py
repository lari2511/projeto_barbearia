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
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime, timedelta
import math
import json
from urllib.request import urlopen

from app.database import get_db
from app.routes import get_current_user
from app.models import Usuario, RadarFreelancer, SolicitacaoBarbeiro, NotificacaoBarbeiro, RequestView, Barbearia, CadeiraAcionada
from app.firebase_config import enviar_notificacao_novo_chamado
from app.realtime import broadcast_event

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


class CadeiraAcionadaResponse(BaseModel):
    id: int
    barbearia_id: int
    cadeira_id: Optional[int] = None
    status: str
    barbeiro_id: Optional[int] = None
    cliente_id: Optional[int] = None
    raio_km: float
    tipo_servico: Optional[str] = None
    valor_oferta: Optional[float] = None
    observacoes: Optional[str] = None
    barbearia_nome: Optional[str] = None
    barbearia_latitude: Optional[float] = None
    barbearia_longitude: Optional[float] = None
    eta_min_usuario_atual: Optional[int] = None
    limite_chegada: Optional[datetime] = None
    expira_em: Optional[datetime] = None
    criado_em: datetime
    atualizado_em: datetime

    class Config:
        from_attributes = True


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
    return {
        "id": vaga.id,
        "barbearia_id": vaga.barbearia_id,
        "cadeira_id": vaga.cadeira_id,
        "status": vaga.status,
        "barbeiro_id": vaga.barbeiro_id,
        "cliente_id": vaga.cliente_id,
        "raio_km": vaga.raio_km,
        "tipo_servico": vaga.tipo_servico,
        "valor_oferta": vaga.valor_oferta,
        "observacoes": vaga.observacoes,
        "barbearia_nome": barbearia.nome if barbearia else None,
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
    
    # DEBUG: logar headers/payload para diagnosticar coordenadas
    try:
        print('\n=== [DEBUG] POST /api/v1/on-demand/atualizar-localizacao ===')
        if http_request is not None:
            print('Headers:', dict(http_request.headers))
        try:
            print('Payload:', request.dict())
        except Exception:
            print('Payload (repr):', repr(request))
    except Exception:
        pass

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
    
    print(f"📍 Localização atualizada: {current_user.nome} @ ({request.latitude}, {request.longitude})")
    
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
        RadarFreelancer.em_atendimento == False,
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
        barbearia_origem = db.query(Barbearia).filter(Barbearia.usuario_id == current_user.id).first()
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
        RadarFreelancer.em_atendimento == False,
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
    
    db.commit()
    
    # Notificar cliente que barbeiro foi encontrado
    cliente = db.query(Usuario).filter(Usuario.id == solicitacao.cliente_id).first()
    if cliente and cliente.device_token:
        enviar_notificacao_novo_chamado(
            token_dispositivo=cliente.device_token,
            nome_cliente="Barbeiro encontrado!",
            nome_servico=f"{current_user.nome} está a caminho",
            nome_barbearia=""
        )
    
    print(f"✅ Barbeiro {current_user.nome} aceitou solicitação #{solicitacao_id}")
    
    return {
        "sucesso": True,
        "solicitacao_id": solicitacao.id,
        "cliente_id": solicitacao.cliente_id,
        "barbeiro_id": current_user.id,
        "mensagem": f"Solicitação aceita! Você está a caminho de {cliente.nome if cliente else 'seu cliente'}"
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


@router.post("/cadeiras-acionadas/acionar", response_model=CadeiraAcionadaResponse, status_code=201)
async def acionar_cadeira_relampago(
    request: AcionarCadeiraRequest,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    """Barbearia aciona cadeira para disputa em tempo real entre barbeiros e clientes proximos."""
    if current_user.tipo != "barbearia":
        raise HTTPException(status_code=403, detail="Apenas barbearias podem acionar cadeira")

    barbearia = db.query(Barbearia).filter(Barbearia.usuario_id == current_user.id).first()
    if not barbearia:
        raise HTTPException(status_code=404, detail="Barbearia nao encontrada")

    if barbearia.latitude is None or barbearia.longitude is None:
        raise HTTPException(status_code=400, detail="Barbearia sem coordenadas para validar ETA")

    if request.raio_km <= 0:
        raise HTTPException(status_code=400, detail="Raio deve ser maior que zero")

    if request.expira_em_minutos <= 0:
        raise HTTPException(status_code=400, detail="expira_em_minutos deve ser maior que zero")

    vaga = CadeiraAcionada(
        barbearia_id=barbearia.id,
        cadeira_id=request.cadeira_id,
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
    barbeiros_online = db.query(RadarFreelancer).filter(
        RadarFreelancer.is_online == True,
        RadarFreelancer.em_atendimento == False,
        RadarFreelancer.latitude.isnot(None),
        RadarFreelancer.longitude.isnot(None),
    ).all()

    for radar in barbeiros_online:
        distancia = calcular_distancia_haversine(
            barbearia.latitude,
            barbearia.longitude,
            radar.latitude,
            radar.longitude,
        )
        if distancia > request.raio_km:
            continue

        barbeiro = db.query(Usuario).filter(Usuario.id == radar.freelancer_id).first()
        if barbeiro and barbeiro.device_token:
            enviar_notificacao_novo_chamado(
                token_dispositivo=barbeiro.device_token,
                nome_cliente="BarberMove",
                nome_servico=request.tipo_servico or "Vaga relampago",
                nome_barbearia=barbearia.nome,
            )

    await broadcast_event(
        "cadeira_acionada_aberta",
        vaga=_serializar_cadeira_acionada(vaga),
    )

    return _serializar_cadeira_acionada(vaga)


@router.get("/cadeiras-acionadas/ativas", response_model=List[CadeiraAcionadaResponse], status_code=200)
async def listar_cadeiras_acionadas_ativas(
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    """Lista vagas acionadas que o usuario atual pode visualizar com filtro de ETA <= 10 min."""
    _expirar_vagas_vencidas(db)

    vagas = db.query(CadeiraAcionada).filter(
        CadeiraAcionada.status == "disponivel"
    ).order_by(CadeiraAcionada.criado_em.desc()).all()

    if not vagas:
        return []

    resultado = []
    for vaga in vagas:
        barbearia = db.query(Barbearia).filter(Barbearia.id == vaga.barbearia_id).first()
        if not barbearia or barbearia.latitude is None or barbearia.longitude is None:
            continue

        if current_user.tipo == "barbeiro":
            radar = db.query(RadarFreelancer).filter(
                RadarFreelancer.freelancer_id == current_user.id,
                RadarFreelancer.is_online == True,
                RadarFreelancer.em_atendimento == False,
            ).first()
            if not radar:
                continue

            eta_min = None
            # Prioriza a posição em tempo real do radar para não depender de
            # coordenadas antigas salvas no perfil do usuário.
            origem_lat = radar.latitude if radar.latitude is not None else current_user.latitude
            origem_lon = radar.longitude if radar.longitude is not None else current_user.longitude

            if origem_lat is not None and origem_lon is not None:
                eta_min = _calcular_eta_minutos(
                    origem_lat,
                    origem_lon,
                    barbearia.latitude,
                    barbearia.longitude,
                )
                if eta_min > 10:
                    continue
        elif current_user.tipo == "cliente":
            if current_user.latitude is None or current_user.longitude is None:
                continue

            eta_min = _calcular_eta_minutos(
                current_user.latitude,
                current_user.longitude,
                barbearia.latitude,
                barbearia.longitude,
            )
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

    barbearia = db.query(Barbearia).filter(Barbearia.usuario_id == current_user.id).first()
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
    """Barbearia cancela vaga relampago ainda disponivel."""
    if current_user.tipo != "barbearia":
        raise HTTPException(status_code=403, detail="Apenas barbearias podem cancelar vaga")

    barbearia = db.query(Barbearia).filter(Barbearia.usuario_id == current_user.id).first()
    if not barbearia:
        raise HTTPException(status_code=404, detail="Barbearia nao encontrada")

    vaga = db.query(CadeiraAcionada).filter(CadeiraAcionada.id == vaga_id).first()
    if not vaga:
        raise HTTPException(status_code=404, detail="Vaga nao encontrada")

    if vaga.barbearia_id != barbearia.id:
        raise HTTPException(status_code=403, detail="Vaga nao pertence a esta barbearia")

    if vaga.status != "disponivel":
        raise HTTPException(status_code=409, detail=f"Vaga nao pode ser cancelada (status: {vaga.status})")

    vaga.status = "cancelada"
    vaga.atualizado_em = datetime.utcnow()
    db.commit()
    db.refresh(vaga)

    await broadcast_event(
        "cadeira_acionada_fechada",
        vaga=_serializar_cadeira_acionada(vaga),
        accepted_by="barbearia",
    )

    return _serializar_cadeira_acionada(vaga)


@router.post("/cadeiras-acionadas/{vaga_id}/aceitar-barbeiro", response_model=CadeiraAcionadaResponse, status_code=200)
async def aceitar_cadeira_acionada_como_barbeiro(
    vaga_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    """Barbeiro tenta assumir a cadeira. Primeiro aceite valido e ETA <= 10 min vence."""
    if current_user.tipo != "barbeiro":
        raise HTTPException(status_code=403, detail="Apenas barbeiros podem aceitar essa vaga")

    if current_user.latitude is None or current_user.longitude is None:
        raise HTTPException(status_code=400, detail="Localizacao obrigatoria para aceitar a vaga")

    radar = db.query(RadarFreelancer).filter(
        RadarFreelancer.freelancer_id == current_user.id,
        RadarFreelancer.is_online == True,
        RadarFreelancer.em_atendimento == False,
    ).first()
    if not radar:
        raise HTTPException(status_code=400, detail="Fique online no radar para aceitar a vaga")

    _expirar_vagas_vencidas(db)

    vaga = db.query(CadeiraAcionada).filter(CadeiraAcionada.id == vaga_id).first()
    if not vaga:
        raise HTTPException(status_code=404, detail="Vaga nao encontrada")

    if vaga.status != "disponivel":
        raise HTTPException(status_code=409, detail=f"Vaga indisponivel (status: {vaga.status})")

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
            CadeiraAcionada.status: "ocupada_por_barbeiro",
            CadeiraAcionada.barbeiro_id: current_user.id,
            CadeiraAcionada.cliente_id: None,
            CadeiraAcionada.limite_chegada: datetime.utcnow() + timedelta(minutes=10),
            CadeiraAcionada.atualizado_em: datetime.utcnow(),
        },
        synchronize_session=False,
    )

    if atualizado == 0:
        raise HTTPException(status_code=409, detail="Outro usuario aceitou esta vaga primeiro")

    # Ao assumir a vaga relampago, o barbeiro passa a ser considerado
    # presente no local da barbearia vinculada.
    usuario_db = db.query(Usuario).filter(Usuario.id == current_user.id).first()
    if usuario_db:
        usuario_db.presente_em_local = True
        usuario_db.barbearia_atual_id = vaga.barbearia_id
        usuario_db.horario_chegada = datetime.utcnow()

    db.commit()
    vaga = db.query(CadeiraAcionada).filter(CadeiraAcionada.id == vaga_id).first()

    await broadcast_event(
        "cadeira_acionada_fechada",
        vaga=_serializar_cadeira_acionada(vaga, eta_min_usuario_atual=eta_min),
        accepted_by="barbeiro",
    )

    return _serializar_cadeira_acionada(vaga, eta_min_usuario_atual=eta_min)


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
        vaga=_serializar_cadeira_acionada(vaga, eta_min_usuario_atual=eta_min),
        accepted_by="cliente",
    )

    return _serializar_cadeira_acionada(vaga, eta_min_usuario_atual=eta_min)
