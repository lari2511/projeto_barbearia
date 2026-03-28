"""
Rotas para Cadeiras - BarberMovie
Endpoints para gestão de cadeiras das barbearias
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime, timedelta
import os

from app.database import get_db
from app.models import Barbearia, Cadeira, StatusCadeira, Assinatura, AssinaturaBarbearia, Usuario
from app.schemas import (
    CadeiraCreate,
    CadeiraUpdate,
    CadeiraResponse,
    AssinaturaResponse,
    CadeiraPresencaRequest,
    CadeiraPresencaEncerrarRequest,
)
from app.routes import get_current_user

router = APIRouter(prefix="/api/v1/cadeiras", tags=["Cadeiras"])

# ✅ CONTROLE: Assinatura obrigatória (0=dev, 1=produção)
# Durante desenvolvimento, manter em 0 para permitir testes
ASSINATURA_OBRIGATORIA = os.getenv("REQUIRE_ASSINATURA_ATIVA", "0") == "1"


def _buscar_assinatura_barbearia(barbearia_id: int, db: Session):
    """Busca assinatura priorizando o modelo novo e caindo no legado quando necessario."""
    assinatura_nova = db.query(AssinaturaBarbearia).filter(
        AssinaturaBarbearia.barbearia_id == barbearia_id
    ).first()
    if assinatura_nova:
        return assinatura_nova

    return db.query(Assinatura).filter(
        Assinatura.barbearia_id == barbearia_id
    ).first()


def _assinatura_ativa_e_limite(assinatura) -> tuple[bool, int]:
    """Normaliza status ativo e quantidade de cadeiras para modelos de assinatura diferentes."""
    if not assinatura:
        return False, 0

    status_assinatura = str(getattr(assinatura, "status", "")).lower()
    ativa_flag = getattr(assinatura, "ativa", None)
    assinatura_ativa = status_assinatura == "ativa" or ativa_flag is True

    proximo_vencimento = getattr(assinatura, "proximo_vencimento", None)
    if proximo_vencimento and proximo_vencimento < datetime.now():
        assinatura_ativa = False

    limite_cadeiras = int(getattr(assinatura, "quantidade_cadeiras", 0) or 0)
    return assinatura_ativa, limite_cadeiras


def _validar_limite_cadeiras_ativas(db: Session, barbearia_id: int, cadeira_id_atual: int | None = None):
    """Impede ativacao/uso acima da quantidade de cadeiras contratadas no plano."""
    assinatura = _buscar_assinatura_barbearia(barbearia_id, db)
    assinatura_ativa, limite_cadeiras = _assinatura_ativa_e_limite(assinatura)

    if not assinatura_ativa or limite_cadeiras <= 0:
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail="Assinatura inativa ou inexistente. Regularize seu plano para acionar cadeiras."
        )

    query_ativas = db.query(Cadeira).filter(
        Cadeira.barbearia_id == barbearia_id,
        Cadeira.acionada_em.isnot(None),
        Cadeira.status.in_([StatusCadeira.DISPONIVEL, StatusCadeira.OCUPADA])
    )
    if cadeira_id_atual is not None:
        query_ativas = query_ativas.filter(Cadeira.id != cadeira_id_atual)

    cadeiras_ativas = query_ativas.count()
    return limite_cadeiras, cadeiras_ativas


def verificar_assinatura_ativa(barbearia_id: int, db: Session):
    """Verifica se a barbearia tem assinatura ativa"""
    if not ASSINATURA_OBRIGATORIA:
        return True

    assinatura = db.query(Assinatura).filter(
        Assinatura.barbearia_id == barbearia_id
    ).first()
    
    if not assinatura:
        return False
    
    if assinatura.status != "ativa":
        return False
    
    if assinatura.proximo_vencimento < datetime.now():
        assinatura.status = "vencida"
        db.commit()
        return False
    
    return True


@router.post("/", response_model=CadeiraResponse)
def criar_cadeira(
    dados: CadeiraCreate,
    db: Session = Depends(get_db),
    usuario_atual = Depends(get_current_user)
):
    """Adiciona uma cadeira à barbearia"""
    # Buscar barbearia do usuário
    barbearia = db.query(Barbearia).filter(
        Barbearia.usuario_id == usuario_atual.id
    ).first()
    
    if not barbearia:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Barbearia não encontrada"
        )
    
    # Verificar se já existe cadeira com esse número
    cadeira_existente = db.query(Cadeira).filter(
        Cadeira.barbearia_id == barbearia.id,
        Cadeira.numero == dados.numero
    ).first()
    
    if cadeira_existente:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cadeira número {dados.numero} já existe"
        )
    
    # Criar cadeira
    cadeira = Cadeira(
        barbearia_id=barbearia.id,
        numero=dados.numero,
        status=StatusCadeira.DISPONIVEL
    )
    db.add(cadeira)
    db.commit()
    db.refresh(cadeira)
    
    return cadeira


@router.get("/", response_model=List[CadeiraResponse])
def listar_cadeiras(
    db: Session = Depends(get_db),
    usuario_atual = Depends(get_current_user)
):
    """Lista todas as cadeiras da barbearia"""
    barbearia = db.query(Barbearia).filter(
        Barbearia.usuario_id == usuario_atual.id
    ).first()
    
    if not barbearia:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Barbearia não encontrada"
        )
    
    cadeiras = db.query(Cadeira).filter(
        Cadeira.barbearia_id == barbearia.id
    ).order_by(Cadeira.numero).all()

    resultado = []
    for cadeira in cadeiras:
        resultado.append({
            "id": cadeira.id,
            "numero": cadeira.numero,
            "status": cadeira.status,
            "criado_em": cadeira.criado_em,
            "freelancer_id": cadeira.freelancer_id,
            "freelancer_nome": cadeira.freelancer.nome if cadeira.freelancer else None,
            "ocupada_em": cadeira.ocupada_em,
        })
    
    return resultado


@router.post("/presenca", response_model=dict)
def marcar_presenca_freelancer(
    payload: CadeiraPresencaRequest,
    db: Session = Depends(get_db),
    usuario_atual = Depends(get_current_user)
):
    """Marca freelancer como presente e ocupa a BRB"""
    barbearia = db.query(Barbearia).filter(
        Barbearia.usuario_id == usuario_atual.id
    ).first()
    
    if not barbearia:
        raise HTTPException(status_code=404, detail="Barbearia não encontrada")

    cadeira = db.query(Cadeira).filter(
        Cadeira.id == payload.cadeira_id,
        Cadeira.barbearia_id == barbearia.id
    ).first()
    
    if not cadeira:
        raise HTTPException(status_code=404, detail="Cadeira não encontrada")

    freelancer = db.query(Usuario).filter(Usuario.id == payload.freelancer_id).first()
    if not freelancer or freelancer.tipo != "barbeiro":
        raise HTTPException(status_code=404, detail="Freelancer não encontrado")

    if cadeira.status == StatusCadeira.OCUPADA and cadeira.freelancer_id != payload.freelancer_id:
        nome = cadeira.freelancer.nome if cadeira.freelancer else "Freelancer"
        raise HTTPException(status_code=400, detail=f"BRB ocupada por {nome}")

    ocupada_por_esse = db.query(Cadeira).filter(
        Cadeira.barbearia_id == barbearia.id,
        Cadeira.status == StatusCadeira.OCUPADA,
        Cadeira.freelancer_id == payload.freelancer_id,
        Cadeira.id != cadeira.id
    ).first()

    if ocupada_por_esse:
        raise HTTPException(status_code=400, detail="Freelancer já está presente em outra BRB")

    cadeira.status = StatusCadeira.OCUPADA
    cadeira.freelancer_id = payload.freelancer_id
    cadeira.ocupada_em = datetime.now()
    cadeira.chamado_id = None

    freelancer.disponivel = True
    db.commit()
    db.refresh(cadeira)

    return {
        "message": "Presença registrada",
        "cadeira_id": cadeira.id,
        "numero": cadeira.numero,
        "freelancer_id": cadeira.freelancer_id,
        "freelancer_nome": freelancer.nome,
        "status": cadeira.status,
        "ocupada_em": cadeira.ocupada_em,
    }


@router.post("/presenca/encerrar", response_model=dict)
def encerrar_presenca_freelancer(
    payload: CadeiraPresencaEncerrarRequest,
    db: Session = Depends(get_db),
    usuario_atual = Depends(get_current_user)
):
    """Encerra presenca e libera a BRB"""
    barbearia = db.query(Barbearia).filter(
        Barbearia.usuario_id == usuario_atual.id
    ).first()
    
    if not barbearia:
        raise HTTPException(status_code=404, detail="Barbearia não encontrada")

    cadeira = db.query(Cadeira).filter(
        Cadeira.id == payload.cadeira_id,
        Cadeira.barbearia_id == barbearia.id
    ).first()
    
    if not cadeira:
        raise HTTPException(status_code=404, detail="Cadeira não encontrada")

    freelancer_id = cadeira.freelancer_id

    cadeira.status = StatusCadeira.DISPONIVEL
    cadeira.freelancer_id = None
    cadeira.liberada_em = datetime.now()
    cadeira.ocupada_em = None
    cadeira.chamado_id = None
    db.commit()

    if freelancer_id:
        ainda_presente = db.query(Cadeira).filter(
            Cadeira.barbearia_id == barbearia.id,
            Cadeira.status == StatusCadeira.OCUPADA,
            Cadeira.freelancer_id == freelancer_id
        ).first()
        if not ainda_presente:
            freelancer = db.query(Usuario).filter(Usuario.id == freelancer_id).first()
            if freelancer:
                freelancer.disponivel = False
                db.commit()

    return {
        "message": "Presença encerrada",
        "cadeira_id": cadeira.id,
        "status": cadeira.status,
    }


@router.get("/acionadas/proximas")
def listar_cadeiras_acionadas_proximas(
    db: Session = Depends(get_db),
    usuario_atual = Depends(get_current_user)
):
    """Lista cadeiras acionadas (livres) das barbearias próximas para barbeiros"""
    from math import radians, sin, cos, sqrt, atan2
    
    # Verificar se usuário é barbeiro
    if usuario_atual.tipo != "barbeiro":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Apenas barbeiros podem ver cadeiras acionadas"
        )
    
    # Buscar cadeiras acionadas recentemente (últimas 24h)
    limite_tempo = datetime.now() - timedelta(hours=24)
    
    cadeiras_acionadas = db.query(Cadeira).filter(
        Cadeira.acionada_em.isnot(None),
        Cadeira.acionada_em >= limite_tempo,
        (
            (Cadeira.status == StatusCadeira.DISPONIVEL)
            |
            ((Cadeira.status == StatusCadeira.OCUPADA) & (Cadeira.freelancer_id.is_(None)))
        )
    ).all()
    
    # Filtrar por proximidade se barbeiro tem localização.
    # Se a barbearia nao tiver coordenadas, ainda assim retorna a cadeira
    # para nao bloquear o fluxo operacional.
    if usuario_atual.latitude and usuario_atual.longitude:
        raio_km = 10.0  # Raio de busca padrão: 10km
        
        cadeiras_proximas = []
        for cadeira in cadeiras_acionadas:
            barbearia = cadeira.barbearia
            if barbearia.latitude and barbearia.longitude:
                # Calcular distância usando fórmula de Haversine
                lat1, lon1 = radians(usuario_atual.latitude), radians(usuario_atual.longitude)
                lat2, lon2 = radians(barbearia.latitude), radians(barbearia.longitude)
                
                dlat = lat2 - lat1
                dlon = lon2 - lon1
                
                a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
                c = 2 * atan2(sqrt(a), sqrt(1-a))
                distancia_km = 6371 * c  # Raio da Terra em km
                
                if distancia_km <= raio_km:
                    cadeiras_proximas.append({
                        "id": cadeira.id,
                        "numero": cadeira.numero,
                        "barbearia_id": barbearia.id,
                        "barbearia_nome": barbearia.nome,
                        "barbearia_endereco": barbearia.endereco,
                        "distancia_km": round(distancia_km, 2),
                        "acionada_em": cadeira.acionada_em,
                        "status": cadeira.status
                    })
            else:
                cadeiras_proximas.append({
                    "id": cadeira.id,
                    "numero": cadeira.numero,
                    "barbearia_id": barbearia.id,
                    "barbearia_nome": barbearia.nome,
                    "barbearia_endereco": barbearia.endereco,
                    "distancia_km": None,
                    "acionada_em": cadeira.acionada_em,
                    "status": cadeira.status
                })
        
        # Ordenar por distância quando existir. Itens sem coordenada ficam no fim.
        cadeiras_proximas.sort(key=lambda x: (x["distancia_km"] is None, x["distancia_km"] or 9999))
        return cadeiras_proximas
    else:
        # Se barbeiro não tem localização, retornar todas as cadeiras acionadas
        return [{
            "id": c.id,
            "numero": c.numero,
            "barbearia_id": c.barbearia.id,
            "barbearia_nome": c.barbearia.nome,
            "barbearia_endereco": c.barbearia.endereco,
            "distancia_km": None,
            "acionada_em": c.acionada_em,
            "status": c.status
        } for c in cadeiras_acionadas]


@router.get("/barbearia/{barbearia_id}", response_model=List[CadeiraResponse])
def listar_cadeiras_barbearia(
    barbearia_id: int,
    apenas_disponiveis: bool = False,
    db: Session = Depends(get_db)
):
    """Lista cadeiras de uma barbearia específica (para freelancers/clientes)"""
    query = db.query(Cadeira).filter(
        Cadeira.barbearia_id == barbearia_id
    )
    
    if apenas_disponiveis:
        query = query.filter(Cadeira.status == StatusCadeira.DISPONIVEL)
    
    cadeiras = query.order_by(Cadeira.numero).all()
    return cadeiras


@router.post("/{cadeira_id}/acionar")
def acionar_cadeira(
    cadeira_id: int,
    db: Session = Depends(get_db),
    usuario_atual = Depends(get_current_user)
):
    """Aciona uma cadeira para torná-la visível para barbeiros próximos"""
    # Buscar barbearia do usuário
    barbearia = db.query(Barbearia).filter(
        Barbearia.usuario_id == usuario_atual.id
    ).first()
    
    if not barbearia:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Barbearia não encontrada"
        )
    
    # Buscar cadeira
    cadeira = db.query(Cadeira).filter(
        Cadeira.id == cadeira_id,
        Cadeira.barbearia_id == barbearia.id
    ).first()
    
    if not cadeira:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cadeira não encontrada"
        )

    # Regra de negocio do plano: SEMPRE respeitar limite de cadeiras contratadas.
    cadeiras_contratadas, cadeiras_ativas_outros = _validar_limite_cadeiras_ativas(
        db=db,
        barbearia_id=barbearia.id,
        cadeira_id_atual=cadeira.id
    )

    # Se a cadeira atual ja estava acionada, nao consome nova vaga
    esta_ja_acionada = bool(cadeira.acionada_em) and cadeira.status in [StatusCadeira.DISPONIVEL, StatusCadeira.OCUPADA]
    total_ativas_apos_acao = cadeiras_ativas_outros + (0 if esta_ja_acionada else 1)

    if total_ativas_apos_acao > cadeiras_contratadas:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Limite do plano atingido: {cadeiras_contratadas} cadeira(s). "
                f"Para acionar mais, aumente sua assinatura."
            )
        )
    
    # Acionar cadeira
    cadeira.acionada_em = datetime.now()
    cadeira.status = StatusCadeira.DISPONIVEL
    db.commit()
    db.refresh(cadeira)
    
    return {
        "message": "Cadeira acionada com sucesso! Barbeiros próximos foram notificados.",
        "cadeira_id": cadeira.id,
        "numero": cadeira.numero,
        "acionada_em": cadeira.acionada_em
    }


@router.patch("/{cadeira_id}", response_model=CadeiraResponse)
def atualizar_status_cadeira(
    cadeira_id: int,
    dados: CadeiraUpdate,
    db: Session = Depends(get_db),
    usuario_atual = Depends(get_current_user)
):
    """Atualiza o status da cadeira (disponível/bloqueada/ocupada)"""
    # Buscar barbearia do usuário
    barbearia = db.query(Barbearia).filter(
        Barbearia.usuario_id == usuario_atual.id
    ).first()
    
    if not barbearia:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Barbearia não encontrada"
        )
    
    # Verificar assinatura ativa
    if not verificar_assinatura_ativa(barbearia.id, db):
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail="Assinatura vencida. Renove para continuar usando o serviço."
        )
    
    # Buscar cadeira
    cadeira = db.query(Cadeira).filter(
        Cadeira.id == cadeira_id,
        Cadeira.barbearia_id == barbearia.id
    ).first()
    
    if not cadeira:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cadeira não encontrada"
        )
    
    # Validar status
    if dados.status not in [StatusCadeira.DISPONIVEL, StatusCadeira.BLOQUEADA, StatusCadeira.OCUPADA]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Status inválido. Use: disponivel, bloqueada ou ocupada"
        )
    
    cadeira.status = dados.status
    db.commit()
    db.refresh(cadeira)

    return cadeira


# ENDPOINTS TEMPORARIAMENTE DESABILITADOS (coluna acionada_em não existe no banco)
# @router.post("/{cadeira_id}/acionar", response_model=dict)
# def acionar_cadeira_livre(...

# @router.post("/{cadeira_id}/desacionar", response_model=dict)
# def desacionar_cadeira(...


@router.delete("/{cadeira_id}", response_model=dict)
def excluir_cadeira(
    cadeira_id: int,
    db: Session = Depends(get_db),
    usuario_atual = Depends(get_current_user)
):
    """Exclui uma cadeira da barbearia"""
    # Buscar barbearia do usuário
    barbearia = db.query(Barbearia).filter(
        Barbearia.usuario_id == usuario_atual.id
    ).first()
    
    if not barbearia:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Barbearia não encontrada"
        )
    
    # Buscar cadeira
    cadeira = db.query(Cadeira).filter(
        Cadeira.id == cadeira_id,
        Cadeira.barbearia_id == barbearia.id
    ).first()
    
    if not cadeira:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cadeira não encontrada"
        )
    
    # Verificar se cadeira está ocupada
    if cadeira.status == StatusCadeira.OCUPADA:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Não é possível excluir cadeira ocupada"
        )
    
    db.delete(cadeira)
    db.commit()
    
    return {"message": f"Cadeira {cadeira.numero} excluída com sucesso"}


@router.patch("/barbearia/status", response_model=dict)
def alterar_status_barbearia(
    online: bool,
    db: Session = Depends(get_db),
    usuario_atual = Depends(get_current_user)
):
    """Altera status online/offline da barbearia"""
    barbearia = db.query(Barbearia).filter(
        Barbearia.usuario_id == usuario_atual.id
    ).first()
    
    if not barbearia:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Barbearia não encontrada"
        )
    
    # Verificar assinatura ativa
    if online and not verificar_assinatura_ativa(barbearia.id, db):
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail="Assinatura vencida. Renove para continuar usando o serviço."
        )
    
    barbearia.status_online = online
    db.commit()
    
    return {
        "message": "Barbearia está online" if online else "Barbearia está offline",
        "status_online": online
    }


@router.get("/assinatura/status", response_model=AssinaturaResponse)
def verificar_status_assinatura(
    db: Session = Depends(get_db),
    usuario_atual = Depends(get_current_user)
):
    """Verifica status da assinatura da barbearia"""
    barbearia = db.query(Barbearia).filter(
        Barbearia.usuario_id == usuario_atual.id
    ).first()
    
    if not barbearia:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Barbearia não encontrada"
        )
    
    assinatura = db.query(Assinatura).filter(
        Assinatura.barbearia_id == barbearia.id
    ).first()
    
    if not assinatura:
        # Criar assinatura inicial (trial de 7 dias)
        assinatura = Assinatura(
            barbearia_id=barbearia.id,
            plano="basico",
            valor=49.90,
            status="ativa",
            proximo_vencimento=datetime.now() + timedelta(days=7)
        )
        db.add(assinatura)
        db.commit()
        db.refresh(assinatura)
    
    # Atualizar status se vencida
    if assinatura.proximo_vencimento < datetime.now() and assinatura.status == "ativa":
        assinatura.status = "vencida"
        db.commit()
    
    return assinatura


@router.post("/{cadeira_id}/ocupar")
def ocupar_cadeira(
    cadeira_id: int,
    db: Session = Depends(get_db),
    usuario_atual = Depends(get_current_user)
):
    """
    Barbeiro freelancer ocupa uma cadeira acionada
    
    Permite que barbeiro marque-se como presente/disponível em uma cadeira
    que foi acionada pelo dono da barbearia.
    """
    # ✅ GUARDIÃO: Apenas barbeiros podem ocupar cadeiras
    if usuario_atual.tipo != "barbeiro":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Apenas barbeiros podem ocupar cadeiras"
        )
    
    # Buscar cadeira
    cadeira = db.query(Cadeira).filter(Cadeira.id == cadeira_id).first()
    if not cadeira:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cadeira não encontrada"
        )
    
    # ✅ GUARDIÃO: Cadeira deve estar DISPONÍVEL (acionada mas livre)
    if cadeira.status != StatusCadeira.DISPONIVEL:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cadeira já está {cadeira.status.value.lower()}"
        )
    
    # ✅ GUARDIÃO: Cadeira deve ter sido acionada recentemente (últimas 24h)
    if not cadeira.acionada_em or cadeira.acionada_em < datetime.now() - timedelta(hours=24):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cadeira não foi acionada ou acionamento expirou (24h)"
        )
    
    # ✅ GUARDIÃO: Barbeiro não pode já estar em outra cadeira OCUPADA
    cadeira_ocupada_barbeiro = db.query(Cadeira).filter(
        Cadeira.freelancer_id == usuario_atual.id,
        Cadeira.status == StatusCadeira.OCUPADA
    ).first()
    
    if cadeira_ocupada_barbeiro:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Você já está ocupando a cadeira {cadeira_ocupada_barbeiro.numero} na barbearia {cadeira_ocupada_barbeiro.barbearia.nome}"
        )
    
    # ✅ Ocupar cadeira
    cadeira.status = StatusCadeira.OCUPADA
    cadeira.freelancer_id = usuario_atual.id
    cadeira.ocupada_em = datetime.now()
    
    # ✅ Atualizar status do barbeiro
    usuario_atual.presente_em_local = True
    usuario_atual.barbearia_atual_id = cadeira.barbearia_id
    
    db.commit()
    db.refresh(cadeira)
    
    return {
        "success": True,
        "message": f"Cadeira {cadeira.numero} ocupada com sucesso!",
        "cadeira": {
            "id": cadeira.id,
            "numero": cadeira.numero,
            "status": cadeira.status.value,
            "barbearia_nome": cadeira.barbearia.nome,
            "barbearia_endereco": cadeira.barbearia.endereco,
            "ocupada_em": cadeira.ocupada_em
        }
    }


@router.post("/{cadeira_id}/desocupar")
def desocupar_cadeira(
    cadeira_id: int,
    db: Session = Depends(get_db),
    usuario_atual = Depends(get_current_user)
):
    """
    Barbeiro desocupa cadeira quando sai da barbearia
    """
    # ✅ GUARDIÃO: Apenas barbeiros podem desocupar cadeiras
    if usuario_atual.tipo != "barbeiro":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Apenas barbeiros podem desocupar cadeiras"
        )
    
    # Buscar cadeira
    cadeira = db.query(Cadeira).filter(Cadeira.id == cadeira_id).first()
    if not cadeira:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cadeira não encontrada"
        )
    
    # ✅ GUARDIÃO: Apenas o barbeiro que está ocupando pode liberar
    if cadeira.freelancer_id != usuario_atual.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Você não está ocupando esta cadeira"
        )
    
    # ✅ Liberar cadeira
    cadeira.status = StatusCadeira.DISPONIVEL
    cadeira.freelancer_id = None
    cadeira.ocupada_em = None
    
    # ✅ Atualizar status do barbeiro
    usuario_atual.presente_em_local = False
    usuario_atual.barbearia_atual_id = None
    
    db.commit()
    db.refresh(cadeira)
    
    return {
        "success": True,
        "message": "Cadeira liberada com sucesso!",
        "cadeira": {
            "id": cadeira.id,
            "numero": cadeira.numero,
            "status": cadeira.status.value,
            "barbearia_nome": cadeira.barbearia.nome
        }
    }

# ============================================
# ✨ NOVOS ENDPOINTS: ACEITAR CADEIRA
# ============================================

@router.put("/{cadeira_id}/liberar-para-barbeiros")
def liberar_cadeira_para_barbeiros(
    cadeira_id: int,
    db: Session = Depends(get_db),
    usuario_atual = Depends(get_current_user)
):
    """
    Barbearia libera uma cadeira para que barbeiros possam aceitar
    Muda de DISPONIVEL para ACIONADA
    """
    # ✅ GUARDIÃO: Apenas dono de barbearia pode liberar
    if usuario_atual.tipo != "barbearia":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Apenas donos de barbearia podem liberar cadeiras"
        )
    
    # Buscar barbearia do usuário
    barbearia = db.query(Barbearia).filter(
        Barbearia.usuario_id == usuario_atual.id
    ).first()
    
    if not barbearia:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Barbearia não encontrada"
        )
    
    # Buscar cadeira
    cadeira = db.query(Cadeira).filter(
        Cadeira.id == cadeira_id,
        Cadeira.barbearia_id == barbearia.id
    ).first()
    
    if not cadeira:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cadeira não encontrada"
        )
    
    # ✅ Validar se está disponível
    if cadeira.status != StatusCadeira.DISPONIVEL:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cadeira não está disponível (Status: {cadeira.status})"
        )
    
    # ✅ Marcar como ACIONADA para barbeiros
    cadeira.status = StatusCadeira.OCUPADA  # Marca como ocupada mas sem freelancer ainda
    cadeira.freelancer_id = None  # Nenhum barbeiro ainda
    cadeira.acionada_em = datetime.now()
    
    db.commit()
    db.refresh(cadeira)
    
    return {
        "success": True,
        "message": f"Cadeira '{cadeira.numero}' liberada para barbeiros!",
        "cadeira": {
            "id": cadeira.id,
            "numero": cadeira.numero,
            "status": "acionada para barbeiros",
            "acionada_em": cadeira.acionada_em,
            "barbearia_id": barbearia.id,
            "barbearia_nome": barbearia.nome,
            "barbearia_endereco": barbearia.endereco
        }
    }


@router.put("/{cadeira_id}/bloquear")
def bloquear_cadeira(
    cadeira_id: int,
    db: Session = Depends(get_db),
    usuario_atual = Depends(get_current_user)
):
    """
    Barbearia bloqueia uma cadeira (trava/desativa)
    Muda status para BLOQUEADA
    """
    # ✅ GUARDIÃO: Apenas dono de barbearia pode bloquear
    if usuario_atual.tipo != "barbearia":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Apenas donos de barbearia podem bloquear cadeiras"
        )
    
    # Buscar barbearia do usuário
    barbearia = db.query(Barbearia).filter(
        Barbearia.usuario_id == usuario_atual.id
    ).first()
    
    if not barbearia:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Barbearia não encontrada"
        )
    
    # Buscar cadeira
    cadeira = db.query(Cadeira).filter(
        Cadeira.id == cadeira_id,
        Cadeira.barbearia_id == barbearia.id
    ).first()
    
    if not cadeira:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cadeira não encontrada"
        )
    
    # Bloquear cadeira
    cadeira.status = StatusCadeira.BLOQUEADA
    cadeira.bloqueada_em = datetime.now()
    
    db.commit()
    db.refresh(cadeira)
    
    return {
        "success": True,
        "message": f"Cadeira '{cadeira.numero}' bloqueada!",
        "cadeira": {
            "id": cadeira.id,
            "numero": cadeira.numero,
            "status": "bloqueada",
            "bloqueada_em": cadeira.bloqueada_em
        }
    }


@router.put("/{cadeira_id}/desbloquear")
def desbloquear_cadeira(
    cadeira_id: int,
    db: Session = Depends(get_db),
    usuario_atual = Depends(get_current_user)
):
    """
    Barbearia desbloqueia uma cadeira
    Volta a status DISPONÍVEL
    """
    # ✅ GUARDIÃO: Apenas dono de barbearia pode desbloquear
    if usuario_atual.tipo != "barbearia":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Apenas donos de barbearia podem desbloquear cadeiras"
        )
    
    # Buscar barbearia do usuário
    barbearia = db.query(Barbearia).filter(
        Barbearia.usuario_id == usuario_atual.id
    ).first()
    
    if not barbearia:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Barbearia não encontrada"
        )
    
    # Buscar cadeira
    cadeira = db.query(Cadeira).filter(
        Cadeira.id == cadeira_id,
        Cadeira.barbearia_id == barbearia.id
    ).first()
    
    if not cadeira:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cadeira não encontrada"
        )
    
    # Desbloquear cadeira
    cadeira.status = StatusCadeira.DISPONIVEL
    cadeira.bloqueada_em = None
    
    db.commit()
    db.refresh(cadeira)
    
    return {
        "success": True,
        "message": f"Cadeira '{cadeira.numero}' desbloqueada!",
        "cadeira": {
            "id": cadeira.id,
            "numero": cadeira.numero,
            "status": "disponível",
            "bloqueada_em": None
        }
    }


@router.post("/{cadeira_id}/aceitar")
def barbeiro_aceitar_cadeira(
    cadeira_id: int,
    db: Session = Depends(get_db),
    usuario_atual = Depends(get_current_user)
):
    """
    Barbeiro aceita uma cadeira que foi liberada pela barbearia
    Vincula barbeiro à cadeira
    """
    # ✅ GUARDIÃO: Apenas barbeiros podem aceitar
    if usuario_atual.tipo != "barbeiro":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Apenas barbeiros podem aceitar cadeiras"
        )
    
    # Buscar cadeira
    cadeira = db.query(Cadeira).filter(Cadeira.id == cadeira_id).first()
    
    if not cadeira:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cadeira não encontrada"
        )
    
    # ✅ A cadeira precisa estar no estado "aguardando barbeiro":
    # - acionada recentemente
    # - sem freelancer vinculado
    # - status pode vir como OCUPADA (fluxo novo) ou DISPONIVEL (fluxo legado)
    status_aceitavel = cadeira.status in [StatusCadeira.OCUPADA, StatusCadeira.DISPONIVEL]
    if (not status_aceitavel) or cadeira.freelancer_id is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cadeira nao esta aguardando barbeiro para aceite"
        )

    if not cadeira.acionada_em or cadeira.acionada_em < datetime.now() - timedelta(hours=24):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Acionamento da cadeira expirado. Peca para a barbearia liberar novamente"
        )

    # ✅ Validação de assinatura e limite sempre ativa
    assinatura = _buscar_assinatura_barbearia(cadeira.barbearia_id, db)
    assinatura_ativa, limite_cadeiras = _assinatura_ativa_e_limite(assinatura)
    if not assinatura_ativa or limite_cadeiras <= 0:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Barbearia com assinatura inativa ou vencida. Nao e possivel assumir atendimento"
        )

    cadeiras_ocupadas = db.query(Cadeira).filter(
        Cadeira.barbearia_id == cadeira.barbearia_id,
        Cadeira.status == StatusCadeira.OCUPADA,
        Cadeira.freelancer_id.isnot(None)
    ).count()

    # Se esta cadeira ainda nao tem freelancer, ao aceitar consumira +1.
    if cadeira.freelancer_id is None and (cadeiras_ocupadas + 1) > limite_cadeiras:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Limite de cadeiras contratadas atingido para esta barbearia"
        )
    
    # ✅ Verificar se barbeiro já está em outra cadeira
    cadeira_atual = db.query(Cadeira).filter(
        Cadeira.freelancer_id == usuario_atual.id,
        Cadeira.status == StatusCadeira.OCUPADA,
        Cadeira.id != cadeira_id
    ).first()
    
    if cadeira_atual:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Você já está ocupando a cadeira '{cadeira_atual.numero}' nesta barbearia"
        )
    
    # ✅ Aceitar cadeira - vincular barbeiro
    cadeira.status = StatusCadeira.OCUPADA
    cadeira.freelancer_id = usuario_atual.id
    cadeira.ocupada_em = datetime.now()
    
    # ✅ Atualizar status do barbeiro
    usuario_atual.presente_em_local = True
    usuario_atual.barbearia_atual_id = cadeira.barbearia_id
    usuario_atual.disponivel = True
    
    db.commit()
    db.refresh(cadeira)
    
    barbearia = cadeira.barbearia
    
    return {
        "success": True,
        "message": f"Cadeira '{cadeira.numero}' aceita com sucesso!",
        "cadeira": {
            "id": cadeira.id,
            "numero": cadeira.numero,
            "status": "ocupada",
            "freelancer_id": cadeira.freelancer_id,
            "freelancer_nome": usuario_atual.nome,
            "ocupada_em": cadeira.ocupada_em,
            "barbearia_id": barbearia.id,
            "barbearia_nome": barbearia.nome,
            "barbearia_endereco": barbearia.endereco,
            "barbearia_telefone": barbearia.telefone
        }
    }


@router.get("/disponiveis")
def listar_cadeiras_disponiveis_barbeiro(
    db: Session = Depends(get_db),
    usuario_atual = Depends(get_current_user)
):
    """
    Barbeiro lista todas as cadeiras disponíveis que ele pode aceitar
    Filtra por localização próxima e liberadas nos últimas 24h
    """
    # ✅ GUARDIÃO: Apenas barbeiros podem ver
    if usuario_atual.tipo != "barbeiro":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Apenas barbeiros podem ver cadeiras disponíveis"
        )
    
    # Ter localização
    if not usuario_atual.latitude or not usuario_atual.longitude:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Configure sua localização no perfil para ver cadeiras próximas"
        )
    
    # Buscar todas as cadeirasliberadas (status OCUPADA mas sem freelancer)
    from math import radians, cos, sin, asin, sqrt
    
    def haversine(lon1, lat1, lon2, lat2):
        """Calcula distância em km"""
        lon1, lat1, lon2, lat2 = map(radians, [lon1, lat1, lon2, lat2])
        dlon = lon2 - lon1
        dlat = lat2 - lat1
        a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
        c = 2 * asin(sqrt(a))
        return 6371 * c
    
    # Filtrar caderias liberadas (status OCUPADA, freelancer_id NULL, acionada nos últimas 24h)
    limite_tempo = datetime.now() - timedelta(hours=24)
    
    caderias_liberadas = db.query(Cadeira).filter(
        Cadeira.status == StatusCadeira.OCUPADA,
        Cadeira.freelancer_id.is_(None),
        Cadeira.acionada_em >= limite_tempo
    ).all()
    
    # Filtrar por distância e criar resposta
    resultado = []
    for cadeira in caderias_liberadas:
        if not cadeira.barbearia.latitude or not cadeira.barbearia.longitude:
            continue
        
        distancia = haversine(
            usuario_atual.longitude,
            usuario_atual.latitude,
            cadeira.barbearia.longitude,
            cadeira.barbearia.latitude
        )
        
        # Raio padrão 15km
        if distancia <= 15:
            resultado.append({
                "id": cadeira.id,
                "numero": cadeira.numero,
                "status": "disponível_para_aceitar",
                "status_atendimento": "AGUARDANDO",
                "acionada_em": cadeira.acionada_em,
                "distancia_km": round(distancia, 2),
                "barbearia": {
                    "id": cadeira.barbearia_id,
                    "nome": cadeira.barbearia.nome,
                    "endereco": cadeira.barbearia.endereco,
                    "telefone": cadeira.barbearia.telefone,
                    "latitude": cadeira.barbearia.latitude,
                    "longitude": cadeira.barbearia.longitude
                }
            })
    
    # Ordenar por distância
    resultado.sort(key=lambda x: x["distancia_km"])
    
    return {
        "total": len(resultado),
        "caderias": resultado
    }