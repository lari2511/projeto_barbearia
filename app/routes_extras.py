# --- ARQUIVO: app/routes_extras.py ---
# Rotas para funcionalidades extras (avaliações, favoritos, cupons, etc)

import os
import secrets
import math
import requests
from datetime import datetime, timedelta
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_
from pydantic import BaseModel
from .realtime import broadcast_event
from . import models

from . import models, schemas
from .database import get_db
from .email_utils import send_email
from .email_send import send_verification_email, send_welcome_email
from .routes import get_current_user, oauth2_scheme, get_password_hash, create_email_verification_token, verify_email_token
from fastapi import Body

router = APIRouter()


class ConfigurarEnderecoBarbeariaRequest(BaseModel):
    endereco_texto: str


class ConfigurarEnderecoPorGpsRequest(BaseModel):
    latitude: float
    longitude: float


def _geocodificar_endereco_nominatim(endereco_texto: str) -> tuple[float, float, str]:
    endereco_limpo = (endereco_texto or '').strip()
    if not endereco_limpo:
        raise HTTPException(status_code=400, detail='Endereço é obrigatório')

    resposta = requests.get(
        'https://nominatim.openstreetmap.org/search',
        params={
            'q': endereco_limpo,
            'format': 'json',
            'limit': 1,
            'addressdetails': 1,
        },
        headers={'User-Agent': 'BarberMoveApp/1.0 (+https://barbermove.local)'} ,
        timeout=15,
    )
    resposta.raise_for_status()
    dados = resposta.json()

    if not dados:
        raise HTTPException(status_code=400, detail='Endereço não encontrado. Verifique os dados e tente novamente.')

    try:
        lat = float(dados[0]['lat'])
        lon = float(dados[0]['lon'])
    except Exception as exc:
        raise HTTPException(status_code=400, detail='Não foi possível ler as coordenadas retornadas pelo geocoder.') from exc

    return lat, lon, endereco_limpo


def _salvar_endereco_barbearia(db: Session, barbearia: models.Barbearia, endereco_texto: str) -> dict:
    lat, lon, endereco_normalizado = _geocodificar_endereco_nominatim(endereco_texto)

    barbearia.latitude = lat
    barbearia.longitude = lon
    barbearia.endereco = endereco_normalizado
    db.add(barbearia)
    db.commit()
    db.refresh(barbearia)

    return {
        'status': 'Endereço atualizado com sucesso',
        'barbearia_id': barbearia.id,
        'nome': barbearia.nome,
        'endereco': barbearia.endereco,
        'coordenadas': [barbearia.latitude, barbearia.longitude],
    }


def _reverse_geocode_nominatim(lat: float, lon: float) -> str:
    try:
        resposta = requests.get(
            'https://nominatim.openstreetmap.org/reverse',
            params={
                'lat': float(lat),
                'lon': float(lon),
                'format': 'json',
                'addressdetails': 1,
            },
            headers={'User-Agent': 'BarberMoveApp/1.0 (+https://barbermove.local)'},
            timeout=15,
        )
        resposta.raise_for_status()
        dados = resposta.json()
        display = dados.get('display_name') or ''
        if not display:
            raise HTTPException(status_code=400, detail='Não foi possível obter endereço a partir das coordenadas')
        return display
    except requests.HTTPError:
        raise
    except Exception as exc:
        raise HTTPException(status_code=400, detail='Erro no reverse geocoding') from exc


@router.patch('/barbearia/{barbearia_id}/configurar-endereco')
def configurar_endereco_barbearia(barbearia_id: int, payload: ConfigurarEnderecoBarbeariaRequest = Body(...), token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    user = get_current_user(token=token, db=db)
    if user.tipo != 'barbearia':
        raise HTTPException(status_code=403, detail='Apenas a barbearia pode configurar o endereço')

    barbearia = db.query(models.Barbearia).filter(
        models.Barbearia.id == barbearia_id,
        models.Barbearia.usuario_id == user.id,
    ).first()
    if not barbearia:
        raise HTTPException(status_code=404, detail='Barbearia não encontrada ou acesso negado')

    return _salvar_endereco_barbearia(db, barbearia, payload.endereco_texto)


@router.patch('/barbearia/minha/configurar-endereco')
def configurar_endereco_minha_barbearia(payload: ConfigurarEnderecoBarbeariaRequest = Body(...), token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    user = get_current_user(token=token, db=db)
    if user.tipo != 'barbearia':
        raise HTTPException(status_code=403, detail='Apenas a barbearia pode configurar o endereço')

    barbearia = db.query(models.Barbearia).filter(models.Barbearia.usuario_id == user.id).first()
    if not barbearia:
        raise HTTPException(status_code=404, detail='Sua barbearia não foi encontrada')

    return _salvar_endereco_barbearia(db, barbearia, payload.endereco_texto)


def _haversine_km(lat1, lon1, lat2, lon2) -> float:
    try:
        if lat1 is None or lon1 is None or lat2 is None or lon2 is None:
            return 0.0
        lat1 = float(lat1); lon1 = float(lon1); lat2 = float(lat2); lon2 = float(lon2)
    except Exception:
        return 0.0

    R = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat/2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon/2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    return round(R * c, 3)


@router.get('/debug/rastreamento/{chamado_id}', response_model=dict)
def debug_rastreamento(chamado_id: int, db: Session = Depends(get_db)):
    """Retorna coordenadas atuais do agendamento ativo para debug e calcula a distância.

    Útil para inspecionar se o cliente/barbeiro/barbearia estão com coordenadas corretas.
    """
    ativo = db.query(models.AgendamentoAtivo).filter(models.AgendamentoAtivo.chamado_id == chamado_id).first()
    if not ativo:
        raise HTTPException(status_code=404, detail='Agendamento ativo não encontrado')

    # Buscar barbearia e barbeiro para inspeção
    barbearia = db.query(models.Barbearia).filter(models.Barbearia.id == ativo.barbearia_id).first()
    barbeiro = db.query(models.Usuario).filter(models.Usuario.id == ativo.barbeiro_id).first() if ativo.barbeiro_id else None

    distancia_cliente_barbeiro = _haversine_km(ativo.cliente_lat, ativo.cliente_lon, ativo.barbeiro_lat, ativo.barbeiro_lon)
    distancia_cliente_barbearia = _haversine_km(ativo.cliente_lat, ativo.cliente_lon, barbearia.latitude if barbearia else None, barbearia.longitude if barbearia else None)

    return {
        'coordenadas': {
            'cliente': [ativo.cliente_lat, ativo.cliente_lon],
            'barbeiro': [ativo.barbeiro_lat, ativo.barbeiro_lon],
            'barbearia': [barbearia.latitude if barbearia else None, barbearia.longitude if barbearia else None]
        },
        'distancias_km': {
            'cliente_barbeiro': distancia_cliente_barbeiro,
            'cliente_barbearia': distancia_cliente_barbearia
        }
    }


class SincronizarLocalizacaoRequest(BaseModel):
    barbearia_id: int
    chamado_id: int | None = None
    latitude: float | None = None
    longitude: float | None = None


@router.post('/debug/sincronizar-localizacao', response_model=dict)
def sincronizar_localizacao(payload: SincronizarLocalizacaoRequest = Body(...), db: Session = Depends(get_db)):
    """Força valores de latitude/longitude para testes: atualiza barbearia e (opcional) agendamento ativo do cliente.

    Use com cuidado — apenas para debugging em ambiente de desenvolvimento.
    """
    # Recuperar coordenada de teste: usar fornecida ou a coordenada da barbearia (se existir)
    lat = payload.latitude
    lon = payload.longitude

    barbearia = db.query(models.Barbearia).filter(models.Barbearia.id == payload.barbearia_id).first()
    if not barbearia:
        raise HTTPException(status_code=404, detail='Barbearia não encontrada')

    if lat is None or lon is None:
        # Se não foi enviado, usar coordenada atual da barbearia (se estiver definida)
        if barbearia.latitude is None or barbearia.longitude is None:
            raise HTTPException(status_code=400, detail='Latitude/longitude de teste obrigatórias quando barbearia não possui coordenada')
        lat = barbearia.latitude
        lon = barbearia.longitude

    # Atualizar barbearia
    barbearia.latitude = float(lat)
    barbearia.longitude = float(lon)
    db.add(barbearia)

    resultado = {'barbearia': {'id': barbearia.id, 'latitude': barbearia.latitude, 'longitude': barbearia.longitude}}

    # Atualizar agendamento ativo (se informado)
    if payload.chamado_id:
        ativo = db.query(models.AgendamentoAtivo).filter(models.AgendamentoAtivo.chamado_id == payload.chamado_id).first()
        if not ativo:
            raise HTTPException(status_code=404, detail='Agendamento ativo não encontrado')
        ativo.cliente_lat = float(lat)
        ativo.cliente_lon = float(lon)
        ativo.cliente_localizacao_em = datetime.utcnow()
        db.add(ativo)
        resultado['agendamento_ativo'] = {'chamado_id': ativo.chamado_id, 'cliente_lat': ativo.cliente_lat, 'cliente_lon': ativo.cliente_lon}

    db.commit()
    return {'status': 'sincronizado', 'detalhes': resultado}


@router.patch('/barbearia/minha/configurar-endereco-por-gps')
def configurar_endereco_minha_barbearia_por_gps(payload: ConfigurarEnderecoPorGpsRequest = Body(...), token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    user = get_current_user(token=token, db=db)
    if user.tipo != 'barbearia':
        raise HTTPException(status_code=403, detail='Apenas a barbearia pode configurar o endereço')

    barbearia = db.query(models.Barbearia).filter(models.Barbearia.usuario_id == user.id).first()
    if not barbearia:
        raise HTTPException(status_code=404, detail='Sua barbearia não foi encontrada')

    lat = payload.latitude
    lon = payload.longitude
    # Reverse geocode to human-readable address
    endereco_normalizado = _reverse_geocode_nominatim(lat, lon)

    barbearia.latitude = float(lat)
    barbearia.longitude = float(lon)
    barbearia.endereco = endereco_normalizado
    db.add(barbearia)
    db.commit()
    db.refresh(barbearia)

    return {
        'status': 'Endereço atualizado via GPS',
        'barbearia_id': barbearia.id,
        'nome': barbearia.nome,
        'endereco': barbearia.endereco,
        'coordenadas': [barbearia.latitude, barbearia.longitude],
    }


@router.get('/agendamento/{agendamento_id}/status-rastreamento', response_model=dict)
def obter_status_rastreamento(agendamento_id: int, db: Session = Depends(get_db)):
    """Retorna se o mapa de rastreamento pode ser mostrado e coordenadas mínimas quando disponível.

    - Se o agendamento estiver em `PENDENTE`, retorna `mostrar_mapa: False`.
    - Senão, retorna `mostrar_mapa: True` e as coordenadas do `AgendamentoAtivo` (se existirem) ou da barbearia.
    """
    chamado = db.query(models.Chamado).filter(models.Chamado.id == agendamento_id).first()
    if not chamado:
        raise HTTPException(status_code=404, detail='Agendamento não encontrado')

    # Não permitir mapa quando ainda pendente
    if chamado.status == models.StatusAgendamento.PENDENTE.value:
        return {"mostrar_mapa": False, "status": chamado.status}

    # Tentar obter snapshot ativo
    ativo = db.query(models.AgendamentoAtivo).filter(models.AgendamentoAtivo.chamado_id == agendamento_id).first()
    # Buscar coordenadas da barbearia como fallback
    barbearia = None
    if chamado.barbearia_id:
        barbearia = db.query(models.Barbearia).filter(models.Barbearia.id == chamado.barbearia_id).first()

    result = {"mostrar_mapa": True, "status": chamado.status}

    if ativo:
        result.update({
            "cliente_lat": ativo.cliente_lat,
            "cliente_lon": ativo.cliente_lon,
            "barbeiro_lat": ativo.barbeiro_lat,
            "barbeiro_lon": ativo.barbeiro_lon,
        })
    elif barbearia:
        result.update({
            "barbearia_lat": barbearia.latitude,
            "barbearia_lon": barbearia.longitude,
        })

    return result


@router.patch('/agendamento/{agendamento_id}/aceitar', response_model=dict)
async def aceitar_agendamento(agendamento_id: int, db: Session = Depends(get_db), token: str = Depends(oauth2_scheme)):
    """Barbeiro aceita o agendamento: altera status e notifica via WebSocket.

    Observações:
    - Usa `StatusAgendamento.CONFIRMADO` como sinal de aceite para liberar o mapa.
    - Define `horario_match` quando disponível.
    """
    # verificar token e permissões
    user = get_current_user(token=token, db=db)
    usuario_id = user.id

    chamado = db.query(models.Chamado).filter(models.Chamado.id == agendamento_id).first()
    if not chamado:
        raise HTTPException(status_code=404, detail='Agendamento não encontrado')

    # Checar se o usuário é o barbeiro designado ou se não há barbeiro definido ainda
    if chamado.barbeiro_id and chamado.barbeiro_id != usuario_id:
        raise HTTPException(status_code=403, detail='Apenas o barbeiro designado pode aceitar este chamado')

    # Atualiza status para aceito (libera rastreamento)
    chamado.status = 'aceito'
    chamado.horario_match = datetime.utcnow()
    if hasattr(chamado, 'aceito_em'):
        chamado.aceito_em = datetime.utcnow()
    db.add(chamado)
    db.commit()
    db.refresh(chamado)

    # Notificar front-ends conectados via WebSocket
    await broadcast_event('chamado_aceito', chamado_id=chamado.id, status=chamado.status)

    return {"status": "Serviço aceito com sucesso", "chamado_id": chamado.id, "novo_status": chamado.status}

# Templates para páginas HTML
templates = Jinja2Templates(directory="app/templates")


def _looks_local_url(value: str) -> bool:
    lowered = (value or "").strip().lower()
    return any(token in lowered for token in ("localhost", "127.0.0.1", "0.0.0.0"))


def _resolve_public_api_base(default: str = "http://localhost:8000") -> str:
    api_url = (os.getenv("PUBLIC_API_URL") or os.getenv("API_URL") or "").strip()
    if api_url:
        return api_url.rstrip("/")

    railway_domain = (os.getenv("RAILWAY_PUBLIC_DOMAIN") or os.getenv("RAILWAY_STATIC_URL") or "").strip()
    if railway_domain:
        return f"https://{railway_domain.rstrip('/')}"

    return default

VERIFICATION_LINK_BASE = os.getenv(
    "VERIFICATION_LINK_BASE",
    f"{_resolve_public_api_base()}/api/v1/email/verificar?token=",
)
if _looks_local_url(VERIFICATION_LINK_BASE):
    resolved_public_api_base = _resolve_public_api_base()
    if resolved_public_api_base != "http://localhost:8000":
        VERIFICATION_LINK_BASE = f"{resolved_public_api_base}/api/v1/email/verificar?token="
RESET_PASSWORD_LINK_BASE = os.getenv(
    "RESET_PASSWORD_LINK_BASE",
    "http://localhost:5173/resetar-senha?token=",
)
DEBUG_EMAIL_TOKENS = os.getenv("DEBUG_EMAIL_TOKENS", "0") == "1"

# ==================== AVALIAÇÕES ====================

@router.post("/avaliacoes/criar", response_model=dict)
def criar_avaliacao_bidirecional(
    avaliacao: schemas.AvaliacaoCreate, 
    token: str = Depends(oauth2_scheme), 
    db: Session = Depends(get_db)
):
    """
    Sistema unificado de avaliações bidirecionais.
    
    ✅ CLIENTE avalia:
    - BARBEIRO (após serviço concluído)
    - BARBEARIA (após serviço concluído)
    
    ✅ BARBEIRO avalia:
    - CLIENTE (após serviço concluído)
    - BARBEARIA (após trabalho realizado)
    
    ✅ BARBEARIA avalia:
    - CLIENTE (após serviço concluído)
    - BARBEIRO (após trabalho realizado)
    """
    user = get_current_user(token=token, db=db)
    
    # Buscar o chamado
    chamado = db.query(models.Chamado).filter(models.Chamado.id == avaliacao.chamado_id).first()
    if not chamado:
        raise HTTPException(status_code=404, detail="Chamado não encontrado")
    
    # Validar que apenas participantes do chamado podem avaliar
    eh_cliente = chamado.cliente_id == user.id
    eh_barbeiro = chamado.barbeiro_id == user.id
    eh_barbearia = chamado.barbearia_id and db.query(models.Barbearia).filter(
        models.Barbearia.id == chamado.barbearia_id,
        models.Barbearia.usuario_id == user.id
    ).first() is not None
    
    if not (eh_cliente or eh_barbeiro or eh_barbearia):
        raise HTTPException(
            status_code=403, 
            detail="Apenas participantes do agendamento podem avaliar"
        )
    
    # Obter usuário a ser avaliado
    if not avaliacao.avaliado_id:
        raise HTTPException(status_code=400, detail="avaliado_id é obrigatório")
    
    avaliado = db.query(models.Usuario).filter(models.Usuario.id == avaliacao.avaliado_id).first()
    if not avaliado:
        raise HTTPException(status_code=404, detail="Usuário a avaliar não encontrado")
    
    # Impedir autoavaliação
    if user.id == avaliacao.avaliado_id:
        raise HTTPException(status_code=400, detail="Você não pode avaliar a si mesmo")
    
    # Validar permissões específicas
    if eh_cliente:
        # Cliente pode avaliar barbeiro ou barbearia
        if avaliado.tipo not in ["barbeiro", "barbearia"]:
            raise HTTPException(
                status_code=403, 
                detail="Cliente só pode avaliar barbeiro ou barbearia"
            )
        if avaliado.tipo == "barbeiro" and avaliado.id != chamado.barbeiro_id:
            raise HTTPException(status_code=403, detail="Barbeiro não é participante deste chamado")
        if avaliado.tipo == "barbearia" and avaliado.id != db.query(models.Barbearia).filter(
            models.Barbearia.id == chamado.barbearia_id
        ).first().usuario_id:
            raise HTTPException(status_code=403, detail="Barbearia não é participante deste chamado")
    
    elif eh_barbeiro:
        # Barbeiro pode avaliar cliente ou barbearia
        if avaliado.tipo not in ["cliente", "barbearia"]:
            raise HTTPException(
                status_code=403, 
                detail="Barbeiro só pode avaliar cliente ou barbearia"
            )
        if avaliado.tipo == "cliente" and avaliado.id != chamado.cliente_id:
            raise HTTPException(status_code=403, detail="Cliente não é participante deste chamado")
        if avaliado.tipo == "barbearia" and avaliado.id != db.query(models.Barbearia).filter(
            models.Barbearia.id == chamado.barbearia_id
        ).first().usuario_id:
            raise HTTPException(status_code=403, detail="Barbearia não é participante deste chamado")
    
    elif eh_barbearia:
        # Barbearia pode avaliar cliente ou barbeiro
        if avaliado.tipo not in ["cliente", "barbeiro"]:
            raise HTTPException(
                status_code=403, 
                detail="Barbearia só pode avaliar cliente ou barbeiro"
            )
        if avaliado.tipo == "cliente" and avaliado.id != chamado.cliente_id:
            raise HTTPException(status_code=403, detail="Cliente não é participante deste chamado")
        if avaliado.tipo == "barbeiro" and avaliado.id != chamado.barbeiro_id:
            raise HTTPException(status_code=403, detail="Barbeiro não é participante deste chamado")
    
    # Verificar duplicação de avaliação
    avaliacao_existente = db.query(models.Avaliacao).filter(
        and_(
            models.Avaliacao.chamado_id == avaliacao.chamado_id,
            models.Avaliacao.avaliador_id == user.id,
            models.Avaliacao.avaliado_id == avaliacao.avaliado_id
        )
    ).first()
    if avaliacao_existente:
        raise HTTPException(status_code=400, detail="Você já avaliou este usuário neste chamado")
    
    # Criar avaliação
    nova_avaliacao = models.Avaliacao(
        chamado_id=avaliacao.chamado_id,
        avaliador_id=user.id,
        avaliado_id=avaliacao.avaliado_id,
        nota=avaliacao.nota,
        comentario=avaliacao.comentario
    )
    db.add(nova_avaliacao)
    
    # Adicionar pontos de fidelidade para o avaliador (cliente ganha pontos)
    if eh_cliente:
        pontos = db.query(models.PontosFidelidade).filter(
            models.PontosFidelidade.usuario_id == user.id
        ).first()
        if not pontos:
            pontos = models.PontosFidelidade(usuario_id=user.id, pontos=10)
            db.add(pontos)
        else:
            pontos.pontos += 10
            # Atualizar nível
            if pontos.pontos >= 1000:
                pontos.nivel = "PLATINA"
            elif pontos.pontos >= 500:
                pontos.nivel = "OURO"
            elif pontos.pontos >= 200:
                pontos.nivel = "PRATA"
    
    db.commit()
    db.refresh(nova_avaliacao)
    
    return {
        "id": nova_avaliacao.id,
        "nota": nova_avaliacao.nota,
        "comentario": nova_avaliacao.comentario,
        "avaliador_tipo": user.tipo,
        "avaliado_tipo": avaliado.tipo,
        "criado_em": nova_avaliacao.criado_em
    }


@router.post("/avaliacoes/", response_model=schemas.AvaliacaoResponse)
def criar_avaliacao(avaliacao: schemas.AvaliacaoCreate, token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    """Cliente avalia barbeiro/barbearia após serviço concluído (LEGADO - usar /avaliacoes/criar)"""
    user = get_current_user(token=token, db=db)
    
    # Verificar se chamado existe e foi concluído
    chamado = db.query(models.Chamado).filter(models.Chamado.id == avaliacao.chamado_id).first()
    if not chamado:
        raise HTTPException(status_code=404, detail="Chamado não encontrado")
    
    if chamado.status != "CONCLUÍDO":
        raise HTTPException(status_code=400, detail="Só pode avaliar chamados concluídos")
    
    if chamado.cliente_id != user.id:
        raise HTTPException(status_code=403, detail="Apenas o cliente pode avaliar")
    
    # Verificar se já avaliou
    avaliacao_existente = db.query(models.Avaliacao).filter(
        and_(models.Avaliacao.chamado_id == avaliacao.chamado_id,
             models.Avaliacao.avaliador_id == user.id)
    ).first()
    if avaliacao_existente:
        raise HTTPException(status_code=400, detail="Você já avaliou este serviço")
    
    nova_avaliacao = models.Avaliacao(
        chamado_id=avaliacao.chamado_id,
        avaliador_id=user.id,
        avaliado_id=avaliacao.avaliado_id,
        nota=avaliacao.nota,
        comentario=avaliacao.comentario
    )
    db.add(nova_avaliacao)
    
    # Adicionar pontos de fidelidade
    pontos = db.query(models.PontosFidelidade).filter(models.PontosFidelidade.usuario_id == user.id).first()
    if not pontos:
        pontos = models.PontosFidelidade(usuario_id=user.id, pontos=10)
        db.add(pontos)
    else:
        pontos.pontos += 10
        # Atualizar nível
        if pontos.pontos >= 1000:
            pontos.nivel = "PLATINA"
        elif pontos.pontos >= 500:
            pontos.nivel = "OURO"
        elif pontos.pontos >= 200:
            pontos.nivel = "PRATA"
    
    db.commit()
    db.refresh(nova_avaliacao)
    return nova_avaliacao


@router.get("/usuario/{usuario_id}/avaliacoes", response_model=List[schemas.AvaliacaoResponse])
def listar_avaliacoes_usuario(usuario_id: int, db: Session = Depends(get_db)):
    """Listar todas as avaliações de um barbeiro/barbearia"""
    avaliacoes = db.query(models.Avaliacao).filter(models.Avaliacao.avaliado_id == usuario_id).all()
    return avaliacoes


@router.get("/usuario/{usuario_id}/media_avaliacao")
def media_avaliacao_usuario(usuario_id: int, db: Session = Depends(get_db)):
    """Obter média de avaliações de um usuário"""
    media = db.query(func.avg(models.Avaliacao.nota)).filter(models.Avaliacao.avaliado_id == usuario_id).scalar()
    total = db.query(func.count(models.Avaliacao.id)).filter(models.Avaliacao.avaliado_id == usuario_id).scalar()
    
    return {
        "media": round(media, 2) if media else 0,
        "total_avaliacoes": total or 0
    }


@router.get("/usuario/{usuario_id}/fotos", response_model=List[schemas.FotoResponse])
def listar_fotos_usuario(usuario_id: int, db: Session = Depends(get_db)):
    """Listar fotos de um barbeiro/barbearia"""
    fotos = db.query(models.Foto).filter(models.Foto.usuario_id == usuario_id).all()
    return fotos


@router.get("/usuario/{usuario_id}")
def obter_usuario_publico(usuario_id: int, db: Session = Depends(get_db)):
    """Retorna dados publicos de um usuario para exibicao de perfil."""
    usuario = db.query(models.Usuario).filter(models.Usuario.id == usuario_id).first()
    if not usuario:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")

    fotos = db.query(models.Foto).filter(models.Foto.usuario_id == usuario.id).all()

    barbearia_atual_nome = None
    if usuario.barbearia_atual_id:
        barbearia = db.query(models.Barbearia).filter(
            models.Barbearia.id == usuario.barbearia_atual_id
        ).first()
        if barbearia:
            barbearia_atual_nome = barbearia.nome

    return {
        "id": usuario.id,
        "nome": usuario.nome,
        "tipo": usuario.tipo,
        "telefone": usuario.telefone,
        "endereco": usuario.endereco,
        "email": usuario.email,
        "foto_perfil": usuario.foto_perfil,
        "disponivel": usuario.disponivel,
        "presente_em_local": usuario.presente_em_local or False,
        "online_regiao": usuario.online_regiao or False,
        "barbearia_atual_id": usuario.barbearia_atual_id,
        "barbearia_atual_nome": barbearia_atual_nome,
        "portfolio_fotos": [f.url for f in fotos if f.url]
    }


# ==================== FAVORITOS ====================

@router.post("/favoritos/", response_model=schemas.FavoritoResponse)
def adicionar_favorito(favorito: schemas.FavoritoCreate, token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    """Adicionar barbeiro/barbearia aos favoritos"""
    user = get_current_user(token=token, db=db)
    
    # Verificar se já está nos favoritos
    favorito_existente = db.query(models.Favorito).filter(
        and_(models.Favorito.usuario_id == user.id,
             models.Favorito.favorito_id == favorito.favorito_id)
    ).first()
    
    if favorito_existente:
        raise HTTPException(status_code=400, detail="Já está nos favoritos")
    
    novo_favorito = models.Favorito(
        usuario_id=user.id,
        favorito_id=favorito.favorito_id
    )
    db.add(novo_favorito)
    db.commit()
    db.refresh(novo_favorito)
    return novo_favorito


@router.get("/favoritos/", response_model=List[schemas.FavoritoResponse])
def listar_favoritos(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    """Listar favoritos do usuário"""
    user = get_current_user(token=token, db=db)
    favoritos = db.query(models.Favorito).filter(models.Favorito.usuario_id == user.id).all()
    return favoritos


@router.delete("/favoritos/{favorito_id}")
def remover_favorito(favorito_id: int, token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    """Remover dos favoritos"""
    user = get_current_user(token=token, db=db)
    
    favorito = db.query(models.Favorito).filter(
        and_(models.Favorito.usuario_id == user.id,
             models.Favorito.favorito_id == favorito_id)
    ).first()
    
    if not favorito:
        raise HTTPException(status_code=404, detail="Favorito não encontrado")
    
    db.delete(favorito)
    db.commit()
    return {"detail": "Removido dos favoritos"}


# ==================== CUPONS ====================

@router.post("/cupons/", response_model=schemas.CupomResponse)
def criar_cupom(cupom: schemas.CupomCreate, token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    """Criar cupom de desconto (apenas admin/barbearia)"""
    user = get_current_user(token=token, db=db)
    
    if user.tipo not in ("barbearia",):
        raise HTTPException(status_code=403, detail="Apenas barbearias podem criar cupons")
    
    # Verificar se cupom já existe
    cupom_existente = db.query(models.Cupom).filter(models.Cupom.codigo == cupom.codigo.upper()).first()
    if cupom_existente:
        raise HTTPException(status_code=400, detail="Código de cupom já existe")
    
    valido_ate = None
    if cupom.valido_ate:
        valido_ate = datetime.fromisoformat(cupom.valido_ate)
    
    novo_cupom = models.Cupom(
        codigo=cupom.codigo.upper(),
        desconto_percentual=cupom.desconto_percentual,
        desconto_fixo=cupom.desconto_fixo,
        valido_ate=valido_ate,
        uso_maximo=cupom.uso_maximo
    )
    db.add(novo_cupom)
    db.commit()
    db.refresh(novo_cupom)
    return novo_cupom


@router.post("/cupons/validar")
def validar_cupom(cupom: schemas.CupomValidar, db: Session = Depends(get_db)):
    """Validar se cupom é válido"""
    cupom_db = db.query(models.Cupom).filter(models.Cupom.codigo == cupom.codigo.upper()).first()
    
    if not cupom_db:
        raise HTTPException(status_code=404, detail="Cupom não encontrado")
    
    if not cupom_db.ativo:
        raise HTTPException(status_code=400, detail="Cupom inativo")
    
    if cupom_db.valido_ate and cupom_db.valido_ate < datetime.now():
        raise HTTPException(status_code=400, detail="Cupom expirado")
    
    if cupom_db.uso_maximo and cupom_db.uso_atual >= cupom_db.uso_maximo:
        raise HTTPException(status_code=400, detail="Cupom esgotado")
    
    return {
        "valido": True,
        "desconto_percentual": cupom_db.desconto_percentual,
        "desconto_fixo": cupom_db.desconto_fixo
    }


@router.get("/cupons/", response_model=List[schemas.CupomResponse])
def listar_cupons(db: Session = Depends(get_db)):
    """Listar cupons ativos"""
    cupons = db.query(models.Cupom).filter(
        and_(models.Cupom.ativo == True,
             or_(models.Cupom.valido_ate == None, models.Cupom.valido_ate > datetime.now()))
    ).all()
    return cupons


# ==================== PONTOS DE FIDELIDADE ====================

@router.get("/fidelidade/", response_model=schemas.PontosFidelidadeResponse)
def consultar_pontos(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    """Consultar pontos de fidelidade do cliente"""
    user = get_current_user(token=token, db=db)
    
    pontos = db.query(models.PontosFidelidade).filter(models.PontosFidelidade.usuario_id == user.id).first()
    if not pontos:
        # Criar registro de pontos
        pontos = models.PontosFidelidade(usuario_id=user.id)
        db.add(pontos)
        db.commit()
        db.refresh(pontos)
    
    return pontos


# ==================== FOTOS ====================

@router.post("/fotos/", response_model=schemas.FotoResponse)
def adicionar_foto(foto: schemas.FotoCreate, token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    """Adicionar foto de serviço (barbeiro/barbearia)"""
    user = get_current_user(token=token, db=db)
    
    nova_foto = models.Foto(
        usuario_id=user.id,
        servico_id=foto.servico_id,
        url=foto.url,
        descricao=foto.descricao
    )
    db.add(nova_foto)
    db.commit()
    db.refresh(nova_foto)
    return nova_foto


# ==================== GEOLOCALIZAÇÃO ====================

def calcular_distancia(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calcular distância em km usando fórmula de Haversine"""
    R = 6371  # Raio da Terra em km
    
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    
    a = (math.sin(dlat / 2) ** 2 +
         math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) *
         math.sin(dlon / 2) ** 2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    
    return R * c


@router.post("/barbeiros/proximos")
def buscar_barbeiros_proximos(localizacao: schemas.BarbeariasProximasRequest, db: Session = Depends(get_db)):
    """Buscar barbeiros próximos à localização do cliente"""
    barbeiros = db.query(models.Usuario).filter(
        and_(
            models.Usuario.tipo == "barbeiro",
            models.Usuario.latitude != None,
            models.Usuario.longitude != None
        )
    ).all()
    
    barbeiros_com_distancia = []
    for barbeiro in barbeiros:
        distancia = calcular_distancia(
            localizacao.latitude,
            localizacao.longitude,
            barbeiro.latitude,
            barbeiro.longitude
        )
        
        if distancia <= localizacao.raio_km:
            barbeiros_com_distancia.append({
                "id": barbeiro.id,
                "tipo": "barbeiro",
                "nome": barbeiro.nome,
                "endereco": barbeiro.endereco or "Atende em barbearias parceiras",
                "distancia_km": round(distancia, 2),
                "telefone": barbeiro.telefone,
                "usuario_id": barbeiro.id
            })
    
    # Ordenar por distância (mais próximos primeiro)
    barbeiros_com_distancia.sort(key=lambda x: x["distancia_km"])
    
    return barbeiros_com_distancia


@router.get("/barbeiro/{barbeiro_id}/barbearias", operation_id="listar_barbearias_do_barbeiro_extras")
def listar_barbearias_do_barbeiro(barbeiro_id: int, db: Session = Depends(get_db)):
    """Listar barbearias onde o barbeiro pode atender (parceiras ou todas próximas)"""
    # Verificar se barbeiro existe
    barbeiro = db.query(models.Usuario).filter(
        models.Usuario.id == barbeiro_id,
        models.Usuario.tipo == "barbeiro"
    ).first()
    
    if not barbeiro:
        raise HTTPException(status_code=404, detail="Barbeiro não encontrado")
    
    # Por enquanto, retornar todas as barbearias cadastradas
    # TODO: Futuramente, implementar sistema de "barbearias parceiras" do barbeiro
    barbearias = db.query(models.Barbearia).filter(
        and_(
            models.Barbearia.latitude != None,
            models.Barbearia.longitude != None
        )
    ).all()
    
    # Se barbeiro tem localização, ordenar por proximidade
    if barbeiro.latitude and barbeiro.longitude:
        barbearias_com_distancia = []
        for barbearia in barbearias:
            cadeira_disponivel = db.query(models.Cadeira).filter(
                models.Cadeira.barbearia_id == barbearia.id,
                models.Cadeira.status == models.StatusCadeira.DISPONIVEL
            ).first()
            if not cadeira_disponivel:
                continue

            distancia = calcular_distancia(
                barbeiro.latitude,
                barbeiro.longitude,
                barbearia.latitude,
                barbearia.longitude
            )
            barbearias_com_distancia.append({
                "id": barbearia.id,
                "nome": barbearia.nome,
                "endereco": barbearia.endereco,
                "telefone": barbearia.telefone,
                "distancia_km": round(distancia, 2),
                "cadeira_livre": True,
                "cadeira_disponivel": True
            })
        
        barbearias_com_distancia.sort(key=lambda x: x["distancia_km"])
        return barbearias_com_distancia
    else:
        # Sem geolocalização do barbeiro, retornar todas com cadeira disponível
        resultado = []
        for b in barbearias:
            cadeira_disponivel = db.query(models.Cadeira).filter(
                models.Cadeira.barbearia_id == b.id,
                models.Cadeira.status == models.StatusCadeira.DISPONIVEL
            ).first()
            if not cadeira_disponivel:
                continue
            resultado.append({
                "id": b.id,
                "nome": b.nome,
                "endereco": b.endereco,
                "telefone": b.telefone,
                "cadeira_livre": True,
                "cadeira_disponivel": True
            })
        return resultado


@router.post("/profissionais/proximos")
def buscar_profissionais_proximos(localizacao: schemas.BarbeariasProximasRequest, db: Session = Depends(get_db)):
    """Buscar barbearias E barbeiros próximos à localização do cliente"""
    profissionais = []
    
    # 1. Buscar BARBEARIAS próximas
    barbearias = db.query(models.Barbearia).filter(
        and_(models.Barbearia.latitude != None,
             models.Barbearia.longitude != None)
    ).all()
    
    for barbearia in barbearias:
        distancia = calcular_distancia(
            localizacao.latitude,
            localizacao.longitude,
            barbearia.latitude,
            barbearia.longitude
        )
        
        if distancia <= localizacao.raio_km:
            profissionais.append({
                "id": barbearia.id,
                "tipo": "barbearia",
                "nome": barbearia.nome,
                "endereco": barbearia.endereco,
                "distancia_km": round(distancia, 2),
                "cadeira_livre": barbearia.cadeira_livre,
                "usuario_id": barbearia.usuario_id
            })
    
    # 2. Buscar BARBEIROS autônomos próximos
    barbeiros = db.query(models.Usuario).filter(
        and_(
            models.Usuario.tipo == "barbeiro",
            models.Usuario.latitude != None,
            models.Usuario.longitude != None
        )
    ).all()
    
    for barbeiro in barbeiros:
        distancia = calcular_distancia(
            localizacao.latitude,
            localizacao.longitude,
            barbeiro.latitude,
            barbeiro.longitude
        )
        
        if distancia <= localizacao.raio_km:
            profissionais.append({
                "id": barbeiro.id,
                "tipo": "barbeiro",
                "nome": barbeiro.nome,
                "endereco": barbeiro.endereco or "Atendimento em domicílio",
                "distancia_km": round(distancia, 2),
                "cadeira_livre": True,  # Barbeiros autônomos geralmente disponíveis
                "usuario_id": barbeiro.id
            })
    
    # Ordenar por distância (mais próximos primeiro)
    profissionais.sort(key=lambda x: x["distancia_km"])
    
    return profissionais


@router.post("/barbearias/proximas")
def buscar_barbearias_proximas(localizacao: schemas.BarbeariasProximasRequest, db: Session = Depends(get_db)):
    """Buscar barbearias próximas à localização do cliente (compatibilidade)"""
    barbearias = db.query(models.Barbearia).filter(
        and_(models.Barbearia.latitude != None,
             models.Barbearia.longitude != None)
    ).all()
    
    barbearias_com_distancia = []
    for barbearia in barbearias:
        distancia = calcular_distancia(
            localizacao.latitude,
            localizacao.longitude,
            barbearia.latitude,
            barbearia.longitude
        )
        
        if distancia <= localizacao.raio_km:
            barbearias_com_distancia.append({
                "id": barbearia.id,
                "nome": barbearia.nome,
                "endereco": barbearia.endereco,
                "distancia_km": round(distancia, 2),
                "cadeira_livre": barbearia.cadeira_livre
            })
    
    # Ordenar por distância
    barbearias_com_distancia.sort(key=lambda x: x["distancia_km"])
    
    return barbearias_com_distancia


# ==================== AGENDAMENTO FUTURO ====================

@router.post("/chamados/agendar")
def agendar_chamado_futuro(agendamento: schemas.AgendamentoFuturo, token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    """Agendamento por horário desativado: o fluxo agora é apenas chamado imediato."""
    user = get_current_user(token=token, db=db)
    
    if user.tipo != "cliente":
        raise HTTPException(status_code=403, detail="Apenas clientes podem agendar")

    raise HTTPException(
        status_code=400,
        detail="Agendamento por horário não está disponível. Use apenas 'Chamar agora'."
    )
    
    # Verificar se serviço existe
    servico = db.query(models.Servico).filter(models.Servico.id == agendamento.servico_id).first()
    if not servico:
        raise HTTPException(status_code=404, detail="Serviço não encontrado")
    
    data_agendamento = datetime.fromisoformat(agendamento.data_agendamento)
    
    novo_chamado = models.Chamado(
        cliente_id=user.id,
        servico_id=agendamento.servico_id,
        barbearia_id=agendamento.barbearia_id,
        status="AGENDADO",
        data_agendamento=data_agendamento,
        valor_original=servico.valor,
        valor_final=servico.valor
    )
    
    db.add(novo_chamado)
    
    # Criar histórico
    historico = models.ChamadoHistorico(
        chamado_id=novo_chamado.id,
        status_novo="AGENDADO",
        usuario_id=user.id,
        observacao=f"Agendado para {data_agendamento.strftime('%d/%m/%Y %H:%M')}"
    )
    db.add(historico)
    
    # Criar notificação
    notificacao = models.Notificacao(
        usuario_id=user.id,
        titulo="Agendamento Confirmado",
        mensagem=f"Seu agendamento para {data_agendamento.strftime('%d/%m/%Y às %H:%M')} foi confirmado!",
        tipo="chamado"
    )
    db.add(notificacao)
    
    db.commit()
    db.refresh(novo_chamado)
    
    return novo_chamado


# ==================== HISTÓRICO DE CHAMADOS ====================

@router.get("/chamados/{chamado_id}/historico")
def obter_historico_chamado(chamado_id: int, db: Session = Depends(get_db)):
    """Obter timeline completa de um chamado"""
    historico = db.query(models.ChamadoHistorico).filter(
        models.ChamadoHistorico.chamado_id == chamado_id
    ).order_by(models.ChamadoHistorico.criado_em).all()
    
    return historico


# ==================== NOTIFICAÇÕES ====================

@router.get(
    "/notificacoes/",
    response_model=List[schemas.NotificacaoResponse],
    operation_id="listar_notificacoes_extras"
)
def listar_notificacoes(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    """Listar notificações do usuário"""
    user = get_current_user(token=token, db=db)
    
    notificacoes = db.query(models.Notificacao).filter(
        models.Notificacao.usuario_id == user.id
    ).order_by(models.Notificacao.criado_em.desc()).limit(50).all()
    
    return notificacoes


@router.put("/notificacoes/{notificacao_id}/ler")
def marcar_notificacao_lida(notificacao_id: int, token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    """Marcar notificação como lida"""
    user = get_current_user(token=token, db=db)
    
    notificacao = db.query(models.Notificacao).filter(
        and_(models.Notificacao.id == notificacao_id,
             models.Notificacao.usuario_id == user.id)
    ).first()
    
    if not notificacao:
        raise HTTPException(status_code=404, detail="Notificação não encontrada")
    
    notificacao.lida = True
    db.commit()
    
    return {"detail": "Notificação marcada como lida"}


# ==================== CHAT ====================

@router.post("/chat/mensagem", response_model=schemas.MensagemChatResponse)
def enviar_mensagem(mensagem: schemas.MensagemChatCreate, token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    """Enviar mensagem no chat do chamado"""
    user = get_current_user(token=token, db=db)
    
    # Verificar se chamado existe e usuário faz parte dele
    chamado = db.query(models.Chamado).filter(models.Chamado.id == mensagem.chamado_id).first()
    if not chamado:
        raise HTTPException(status_code=404, detail="Chamado não encontrado")
    
    if user.id not in (chamado.cliente_id, chamado.barbeiro_id):
        raise HTTPException(status_code=403, detail="Você não faz parte deste chamado")
    
    nova_mensagem = models.MensagemChat(
        chamado_id=mensagem.chamado_id,
        remetente_id=user.id,
        mensagem=mensagem.mensagem
    )
    
    db.add(nova_mensagem)
    db.commit()
    db.refresh(nova_mensagem)
    
    return nova_mensagem


@router.get("/chat/{chamado_id}/mensagens", response_model=List[schemas.MensagemChatResponse])
def listar_mensagens_chat(chamado_id: int, token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    """Listar mensagens do chat de um chamado"""
    user = get_current_user(token=token, db=db)
    
    chamado = db.query(models.Chamado).filter(models.Chamado.id == chamado_id).first()
    if not chamado:
        raise HTTPException(status_code=404, detail="Chamado não encontrado")
    
    if user.id not in (chamado.cliente_id, chamado.barbeiro_id):
        raise HTTPException(status_code=403, detail="Você não faz parte deste chamado")
    
    mensagens = db.query(models.MensagemChat).filter(
        models.MensagemChat.chamado_id == chamado_id
    ).order_by(models.MensagemChat.criado_em).all()
    
    return mensagens


# ==================== INICIAR CHAT RÁPIDO ====================
@router.post("/chat/iniciar", response_model=schemas.ChamadoResponse)
def iniciar_chat(destinatario_id: int = None, token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    """Iniciar um chamado rápido para permitir chat entre cliente e barbeiro.

    Regras:
    - Se usuário for `cliente` e destinatario for `barbeiro`, cria um chamado entre eles.
    - Usa o primeiro `Servico` encontrado da barbearia do barbeiro.
    - Retorna o `Chamado` criado.
    """
    user = get_current_user(token=token, db=db)

    if destinatario_id is None:
        raise HTTPException(status_code=400, detail="destinatario_id obrigatório")

    destinatario = db.query(models.Usuario).filter(models.Usuario.id == destinatario_id).first()
    if not destinatario:
        raise HTTPException(status_code=404, detail="Usuário destinatário não encontrado")

    # Apenas cliente <-> barbeiro por enquanto
    if user.tipo == 'cliente' and destinatario.tipo == 'barbeiro':
        cliente = user
        barbeiro = destinatario
    elif user.tipo == 'barbeiro' and destinatario.tipo == 'cliente':
        cliente = destinatario
        barbeiro = user
    else:
        raise HTTPException(status_code=400, detail="Somente conversas entre clientes e barbeiros são permitidas")

    chamado_existente = db.query(models.Chamado).filter(
        models.Chamado.cliente_id == cliente.id,
        models.Chamado.barbeiro_id == barbeiro.id,
        models.Chamado.status.in_([
            models.StatusAgendamento.CONFIRMADO.value,
            models.StatusAgendamento.EM_ATENDIMENTO.value,
        ])
    ).order_by(models.Chamado.criado_em.desc()).first()

    if chamado_existente:
        return chamado_existente

    raise HTTPException(status_code=400, detail="Conversa disponível somente após o serviço ser aceito")

    notificacao = models.Notificacao(
        usuario_id=barbeiro.id,
        titulo='Nova conversa',
        mensagem=f'{cliente.nome or "Cliente"} iniciou uma conversa com você.',
        tipo='chat'
    )
    db.add(notificacao)

    db.commit()
    db.refresh(novo_chamado)

    return novo_chamado


# ==================== VERIFICAÇÃO DE EMAIL ====================

@router.get("/email/verificar", response_class=HTMLResponse)
async def verificar_email(token: str, db: Session = Depends(get_db)):
    """
    Confirmar email a partir do token JWT enviado ao usuário
    
    O usuário recebe um link como:
    http://localhost:8000/api/v1/email/verificar?token=<JWT_TOKEN>
    
    Query params:
        token: JWT token de verificação de email
        
    Returns:
        Página HTML de sucesso ou erro
    """
    # Validar e decodificar o token JWT
    email = verify_email_token(token)
    
    if not email:
        return HTMLResponse(
            content="""
            <!DOCTYPE html>
            <html lang="pt-BR">
            <head>
                <meta charset="UTF-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <title>Erro - BarberMove</title>
                <style>
                    * { margin: 0; padding: 0; box-sizing: border-box; }
                    body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; background: #000; 
                           display: flex; align-items: center; justify-content: center; min-height: 100vh; color: white; padding: 20px; }
                    .container { background: rgba(24, 24, 27, 0.9); border: 1px solid rgba(255, 255, 255, 0.1); 
                                border-radius: 24px; padding: 48px 32px; max-width: 480px; text-align: center; }
                    h1 { color: #ef4444; margin-bottom: 16px; font-size: 24px; }
                    p { color: #a1a1aa; margin-bottom: 24px; line-height: 1.6; }
                    .btn { background: white; color: black; padding: 16px 32px; border-radius: 12px; 
                          text-decoration: none; display: inline-block; font-weight: 700; }
                </style>
            </head>
            <body>
                <div class="container">
                    <h1>⚠️ Token Inválido</h1>
                    <p>O link de verificação é inválido ou expirou. Por favor, solicite um novo link de verificação.</p>
                    <a href="/" class="btn">Voltar ao App</a>
                </div>
            </body>
            </html>
            """,
            status_code=400
        )
    
    # Procurar pelo usuário com esse email
    user = db.query(models.Usuario).filter(models.Usuario.email == email).first()
    
    if not user:
        return HTMLResponse(
            content="""
            <!DOCTYPE html>
            <html lang="pt-BR">
            <head>
                <meta charset="UTF-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <title>Usuário não encontrado - BarberMove</title>
                <style>
                    * { margin: 0; padding: 0; box-sizing: border-box; }
                    body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; background: #000; 
                           display: flex; align-items: center; justify-content: center; min-height: 100vh; color: white; padding: 20px; }
                    .container { background: rgba(24, 24, 27, 0.9); border: 1px solid rgba(255, 255, 255, 0.1); 
                                border-radius: 24px; padding: 48px 32px; max-width: 480px; text-align: center; }
                    h1 { color: #ef4444; margin-bottom: 16px; font-size: 24px; }
                    p { color: #a1a1aa; margin-bottom: 24px; line-height: 1.6; }
                    .btn { background: white; color: black; padding: 16px 32px; border-radius: 12px; 
                          text-decoration: none; display: inline-block; font-weight: 700; }
                </style>
            </head>
            <body>
                <div class="container">
                    <h1>❌ Usuário não encontrado</h1>
                    <p>Não foi possível encontrar o usuário associado a este link.</p>
                    <a href="/" class="btn">Voltar ao App</a>
                </div>
            </body>
            </html>
            """,
            status_code=404
        )
    
    # Se já foi verificado, apenas retornar sucesso
    if user.email_verificado:
        # Ler o template HTML
        with open("app/templates/email_verificado.html", "r", encoding="utf-8") as f:
            html_content = f.read()
        
        # Substituir a variável de email
        html_content = html_content.replace("{{ email }}", email)
        
        return HTMLResponse(content=html_content)
    
    # Marcar como verificado
    user.email_verificado = True
    user.token_verificacao = None  # Limpar token
    db.commit()
    
    # Ler o template HTML
    with open("app/templates/email_verificado.html", "r", encoding="utf-8") as f:
        html_content = f.read()
    
    # Substituir a variável de email
    html_content = html_content.replace("{{ email }}", email)
    
    return HTMLResponse(content=html_content)


@router.get("/email/debug-token/{email}")
def debug_token_email(email: str, db: Session = Depends(get_db)):
    """
    [DEBUG] Retorna o token JWT de verificação de um email (apenas para desenvolvimento)
    
    Útil para testar o fluxo de verificação sem Configurar SMTP real.
    """
    user = db.query(models.Usuario).filter(models.Usuario.email == email).first()

    if not user:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")

    if user.email_verificado:
        raise HTTPException(status_code=400, detail="Email já verificado")

    # Gerar novo token JWT se não tiver um válido
    if not user.token_verificacao:
        user.token_verificacao = create_email_verification_token(email)
        db.commit()

    verification_url = f"http://localhost:8000/api/v1/email/verificar?token={user.token_verificacao}"
    
    return {
        "email": email,
        "token": user.token_verificacao,
        "verification_link": verification_url,
        "message": "Clique no link acima para verificar seu email",
        "debug_note": "Este endpoint é apenas para desenvolvimento!",
        "expires_in_hours": 24
    }


@router.post("/email/reenvio")
async def reenviar_email_verificacao(
    token: str = Depends(oauth2_scheme), 
    db: Session = Depends(get_db)
):
    """
    Reenviar link de verificação para o usuário autenticado
    
    O novo link será enviado para o email cadastrado.
    Útil se o usuário não recebeu o link original.
    """
    user = get_current_user(token=token, db=db)

    if user.email_verificado:
        return {
            "detail": "Email já está verificado",
            "status": "already_verified"
        }

    # Gerar novo token JWT
    novo_token = create_email_verification_token(user.email)
    user.token_verificacao = novo_token
    db.commit()
    db.refresh(user)

    # Enviar e-mail com fastapi-mail (assíncrono)
    await send_verification_email(user.email, novo_token, user.nome)

    response = {
        "detail": "Link de verificação reenviado com sucesso! Verifique seu email.",
        "status": "resent"
    }
    
    # Debug: retornar o token se configurado
    if DEBUG_EMAIL_TOKENS:
        response["token_debug"] = novo_token
        response["debug_message"] = "Token incluído para desenvolvimento"
        
    return response


# ==================== RECUPERAÇÃO DE SENHA ====================

@router.post("/recuperar-senha")
def solicitar_recuperacao_senha(request: schemas.RecuperarSenhaRequest, db: Session = Depends(get_db)):
    """Solicitar recuperação de senha (envia email com token)"""
    usuario = db.query(models.Usuario).filter(models.Usuario.email == request.email).first()
    
    if not usuario:
        # Não revelar se email existe ou não (segurança)
        return {"detail": "Se o email existir, você receberá instruções"}
    
    # Gerar token
    token = secrets.token_urlsafe(32)
    expira_em = datetime.now() + timedelta(hours=24)
    
    token_recuperacao = models.TokenRecuperacao(
        usuario_id=usuario.id,
        token=token,
        expira_em=expira_em
    )
    
    db.add(token_recuperacao)
    db.commit()

    reset_link = f"{RESET_PASSWORD_LINK_BASE}{token}"
    html_body = (
        f"<p>Olá, {usuario.nome}!</p>"
        "<p>Recebemos um pedido para redefinir sua senha. Se não foi você, ignore este email.</p>"
        f"<p><a href='{reset_link}'>Resetar senha</a></p>"
        f"<p>Ou copie e cole no navegador: {reset_link}</p>"
        "<p>O link expira em 24h.</p>"
    )
    text_body = (
        f"Olá, {usuario.nome}!\n"
        "Recebemos um pedido para redefinir sua senha. Se não foi você, ignore este email.\n"
        f"Link: {reset_link}\n"
        "O link expira em 24h.\n"
    )
    send_email(
        subject="Recuperação de senha - BarberMove",
        to_email=usuario.email,
        html_body=html_body,
        text_body=text_body,
    )

    response = {"detail": "Se o email existir, você receberá instruções"}
    if DEBUG_EMAIL_TOKENS:
        response["token_debug"] = token
    return response


@router.post("/resetar-senha")
def resetar_senha(request: schemas.ResetarSenhaRequest, db: Session = Depends(get_db)):
    """Resetar senha usando token"""
    token_db = db.query(models.TokenRecuperacao).filter(
        and_(models.TokenRecuperacao.token == request.token,
             models.TokenRecuperacao.usado == False,
             models.TokenRecuperacao.expira_em > datetime.now())
    ).first()
    
    if not token_db:
        raise HTTPException(status_code=400, detail="Token inválido ou expirado")
    
    # Atualizar senha
    usuario = db.query(models.Usuario).filter(models.Usuario.id == token_db.usuario_id).first()
    usuario.senha_hash = get_password_hash(request.nova_senha)
    
    # Marcar token como usado
    token_db.usado = True
    
    db.commit()
    
    return {"detail": "Senha resetada com sucesso"}


# ==================== ESTATÍSTICAS ====================

@router.get("/estatisticas/", response_model=schemas.EstatisticasResponse)
def obter_estatisticas(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    """Obter estatísticas do barbeiro/barbearia"""
    user = get_current_user(token=token, db=db)
    
    if user.tipo == "barbearia":
        # Estatísticas da barbearia
        barbearia = db.query(models.Barbearia).filter(models.Barbearia.usuario_id == user.id).first()
        chamados = db.query(models.Chamado).filter(models.Chamado.barbearia_id == barbearia.id)
    elif user.tipo == "barbeiro":
        # Estatísticas do barbeiro
        chamados = db.query(models.Chamado).filter(models.Chamado.barbeiro_id == user.id)
    else:
        raise HTTPException(status_code=403, detail="Apenas barbeiros/barbearias têm estatísticas")
    
    total_chamados = chamados.count()
    receita_total = db.query(func.sum(models.Chamado.valor_final)).filter(
        and_(models.Chamado.barbeiro_id == user.id if user.tipo == "barbeiro" else models.Chamado.barbearia_id == barbearia.id,
             models.Chamado.status == "CONCLUÍDO")
    ).scalar() or 0
    
    # Serviço mais pedido
    servico_mais_pedido = db.query(
        models.Servico.nome,
        func.count(models.Chamado.id).label('total')
    ).join(models.Chamado).filter(
        models.Chamado.barbeiro_id == user.id if user.tipo == "barbeiro" else models.Chamado.barbearia_id == barbearia.id
    ).group_by(models.Servico.nome).order_by(func.count(models.Chamado.id).desc()).first()
    
    # Média de avaliação
    media_aval = db.query(func.avg(models.Avaliacao.nota)).filter(
        models.Avaliacao.avaliado_id == user.id
    ).scalar()
    
    return {
        "total_chamados": total_chamados,
        "total_receita": float(receita_total),
        "servico_mais_pedido": servico_mais_pedido[0] if servico_mais_pedido else None,
        "media_avaliacao": round(float(media_aval), 2) if media_aval else None
    }


# ==================== 2FA ====================

@router.post("/2fa/ativar", response_model=schemas.Enable2FAResponse)
def ativar_2fa(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    """Ativar autenticação de dois fatores"""
    import pyotp
    import qrcode
    from io import BytesIO
    import base64
    
    user = get_current_user(token=token, db=db)
    
    # Gerar secret
    secret = pyotp.random_base32()
    
    # Gerar QR Code
    totp = pyotp.TOTP(secret)
    provisioning_uri = totp.provisioning_uri(name=user.email, issuer_name="BarberUber")
    
    # Criar QR Code
    qr = qrcode.QRCode(version=1, box_size=10, border=5)
    qr.add_data(provisioning_uri)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    
    # Converter para base64
    buffered = BytesIO()
    img.save(buffered, format="PNG")
    img_str = base64.b64encode(buffered.getvalue()).decode()
    
    # Salvar secret (mas não ativar ainda)
    user.twofa_secret = secret
    db.commit()
    
    return {
        "secret": secret,
        "qr_code_url": f"data:image/png;base64,{img_str}"
    }


@router.post("/2fa/verificar")
def verificar_2fa(request: schemas.Verify2FARequest, token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    """Verificar código 2FA e ativar"""
    import pyotp
    
    user = get_current_user(token=token, db=db)
    
    if not user.twofa_secret:
        raise HTTPException(status_code=400, detail="2FA não configurado")
    
    totp = pyotp.TOTP(user.twofa_secret)
    
    if not totp.verify(request.token):
        raise HTTPException(status_code=400, detail="Código inválido")
    
    # Ativar 2FA
    user.twofa_ativo = True
    db.commit()
    
    return {"detail": "2FA ativado com sucesso"}


@router.post("/2fa/desativar")
def desativar_2fa(request: schemas.Verify2FARequest, token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    """Desativar 2FA"""
    import pyotp
    
    user = get_current_user(token=token, db=db)
    
    if not user.twofa_ativo:
        raise HTTPException(status_code=400, detail="2FA não está ativo")
    
    totp = pyotp.TOTP(user.twofa_secret)
    
    if not totp.verify(request.token):
        raise HTTPException(status_code=400, detail="Código inválido")
    
    user.twofa_ativo = False
    user.twofa_secret = None
    db.commit()
    
    return {"detail": "2FA desativado"}
