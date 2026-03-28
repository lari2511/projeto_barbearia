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

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
import math

from app.database import get_db
from app.routes import get_current_user
from app.models import Usuario, RadarFreelancer, SolicitacaoBarbeiro, NotificacaoBarbeiro, Barbearia
from app.firebase_config import enviar_notificacao_novo_chamado

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
    
    class Config:
        from_attributes = True


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
    current_user: Usuario = Depends(get_current_user)
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
    current_user: Usuario = Depends(get_current_user)
):
    """
    Cliente (ou barbearia) solicita um barbeiro agora.
    
    Fluxo:
    1. Cria registro de SolicitacaoBarbeiro
    2. Busca barbeiros próximos
    3. Envia notificações push para todos eles
    4. Aguarda respostas
    5. Primeiro a aceitar ganha o serviço
    
    Args:
        request: SolicitarBarbeiroRequest com localização e detalhes
        db: Sessão do banco de dados
        current_user: Usuário autenticado (cliente)
    
    Returns:
        SolicitacaoBarbeiroResponse com ID da solicitação
    """
    
    # Criar solicitação
    solicitacao = SolicitacaoBarbeiro(
        cliente_id=current_user.id,
        latitude=request.latitude,
        longitude=request.longitude,
        endereco=request.endereco,
        raio_km=request.raio_km,
        tipo_servico=request.tipo_servico,
        observacoes=request.observacoes,
        valor_oferta=request.valor_oferta,
        status="aguardando_resposta"
    )
    
    db.add(solicitacao)
    db.commit()
    db.refresh(solicitacao)
    
    # Buscar barbeiros próximos para notificar
    barbeiros_proximos = db.query(RadarFreelancer).filter(
        RadarFreelancer.is_online == True,
        RadarFreelancer.em_atendimento == False,
        RadarFreelancer.latitude.isnot(None),
        RadarFreelancer.longitude.isnot(None)
    ).all()
    
    # Filtrar por raio e enviar notificações
    barbeiros_notificados = 0
    
    for radar in barbeiros_proximos:
        distancia = calcular_distancia_haversine(
            request.latitude, request.longitude,
            radar.latitude, radar.longitude
        )
        
        if distancia <= request.raio_km:
            # Criar registro de notificação
            notif = NotificacaoBarbeiro(
                barbeiro_id=radar.freelancer_id,
                solicitacao_id=solicitacao.id,
                distancia_km=distancia
            )
            db.add(notif)
            
            # Enviar notificação push
            barbeiro = db.query(Usuario).filter(Usuario.id == radar.freelancer_id).first()
            
            if barbeiro and barbeiro.device_token:
                mensagem_notif = f"Nova solicitação a {distancia} km"
                enviar_notificacao_novo_chamado(
                    token_dispositivo=barbeiro.device_token,
                    nome_cliente=current_user.nome,
                    nome_servico=request.tipo_servico or "Serviço",
                    nome_barbearia="Próximo a você"
                )
                barbeiros_notificados += 1
    
    db.commit()
    
    print(f"🔔 Solicitação #{solicitacao.id} enviada para {barbeiros_notificados} barbeiros")
    
    return SolicitacaoBarbeiroResponse.from_orm(solicitacao)


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
