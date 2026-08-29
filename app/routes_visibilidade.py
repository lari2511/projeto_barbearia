"""
Camada de VISIBILIDADE do ecossistema local - BarberMove.

SOMENTE LEITURA. Nao altera chamados, matching, cadeiras, cronometro,
pagamento, avaliacoes, regra de chegada nem o status do freelancer.

Responde a duas perguntas:
- Freelancer:    "Quais barbearias do BarberMove existem perto de mim?"
- Proprietario:  "Quais freelancers do BarberMove estao disponiveis perto da minha barbearia?"

Reutiliza os sistemas que ja existem:
- localizacao:   Usuario.latitude/longitude (GPS pessoal, sincronizado via
                 /api/v1/on-demand/atualizar-localizacao), RadarFreelancer.latitude/longitude
                 e Barbearia.latitude/longitude (endereco fixo geocodificado por CEP)
- status:        Usuario.online_regiao / presente_em_local / barbearia_atual_id
- disponibilidade de cadeira: Cadeira.status
- bloqueios:     BarbeariaFreelancer.bloqueado
"""

from math import radians, sin, cos, sqrt, atan2
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import and_, or_
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import (
    Barbearia,
    BarbeariaFreelancer,
    Cadeira,
    RadarFreelancer,
    StatusCadeira,
    Usuario,
)
from app.routes import get_current_user

router = APIRouter(prefix="/api/v1/visibilidade", tags=["Visibilidade"])


def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Distancia em km entre dois pontos (mesma formula usada no resto do app)."""
    lat1r, lon1r, lat2r, lon2r = map(radians, [lat1, lon1, lat2, lon2])
    dlat = lat2r - lat1r
    dlon = lon2r - lon1r
    a = sin(dlat / 2) ** 2 + cos(lat1r) * cos(lat2r) * sin(dlon / 2) ** 2
    return 6371.0 * 2 * atan2(sqrt(a), sqrt(1 - a))


def _faixa_aproximada(distancia_km: float) -> str:
    """
    Rotulo de distancia APROXIMADA para pessoas (nunca a posicao exata).
    Regra 4 da especificacao: para freelancers, so distancia aproximada.
    """
    metros = distancia_km * 1000
    if metros < 150:
        return "Proximo de voce"
    if metros < 1000:
        centenas = int(round(metros / 100.0) * 100)
        return f"~{centenas} m"
    km = round(distancia_km * 2) / 2  # arredonda para 0,5 km
    return f"~{km:g} km"


@router.get("/barbearias-proximas")
def barbearias_proximas_do_freelancer(
    latitude: Optional[float] = Query(None, description="Opcional; se ausente usa a localizacao salva do freelancer"),
    longitude: Optional[float] = Query(None),
    raio_km: float = Query(10.0, gt=0, le=50),
    db: Session = Depends(get_db),
    usuario_atual: Usuario = Depends(get_current_user),
):
    """
    Lista as barbearias BarberMove proximas do freelancer.

    Aparece TODA barbearia cadastrada e aprovada dentro do raio, mesmo sem
    nenhuma cadeira disponivel (regra 8). O campo `cadeira_disponivel` diz se
    o local deve receber o destaque "cadeira disponivel".
    """
    if usuario_atual.tipo != "barbeiro":
        raise HTTPException(status_code=403, detail="Apenas freelancers podem ver barbearias proximas")

    lat = latitude if latitude is not None else usuario_atual.latitude
    lon = longitude if longitude is not None else usuario_atual.longitude
    if lat is None or lon is None:
        return {"total": 0, "com_cadeira_disponivel": 0, "barbearias": []}

    barbearias = (
        db.query(Barbearia, Usuario)
        .join(Usuario, Barbearia.usuario_id == Usuario.id)
        .filter(
            Usuario.tipo == "barbearia",
            Usuario.perfil_aprovado == True,  # noqa: E712
            Barbearia.latitude.isnot(None),
            Barbearia.longitude.isnot(None),
        )
        .all()
    )

    itens = []
    for barbearia, dono in barbearias:
        dist = _haversine_km(lat, lon, barbearia.latitude, barbearia.longitude)
        if dist > raio_km:
            continue

        cadeira_disponivel = (
            db.query(Cadeira)
            .filter(
                Cadeira.barbearia_id == barbearia.id,
                or_(
                    Cadeira.status == StatusCadeira.DISPONIVEL,
                    and_(
                        Cadeira.status == StatusCadeira.OCUPADA,
                        Cadeira.freelancer_id.is_(None),
                    ),
                ),
            )
            .first()
            is not None
        )

        itens.append(
            {
                "id": barbearia.id,
                "nome": barbearia.nome or dono.nome,
                "endereco": barbearia.endereco,
                # Estabelecimento comercial: pode expor a localizacao exata (regra 4).
                "latitude": barbearia.latitude,
                "longitude": barbearia.longitude,
                "distancia_km": round(dist, 2),
                "cadastrada": True,
                "cadeira_disponivel": cadeira_disponivel,
            }
        )

    itens.sort(key=lambda x: x["distancia_km"])
    return {
        "total": len(itens),
        "com_cadeira_disponivel": sum(1 for i in itens if i["cadeira_disponivel"]),
        "barbearias": itens,
    }


@router.get("/freelancers-proximos")
def freelancers_proximos_da_barbearia(
    raio_km: float = Query(10.0, gt=0, le=50),
    db: Session = Depends(get_db),
    usuario_atual: Usuario = Depends(get_current_user),
):
    """
    Lista os freelancers do BarberMove proximos da barbearia do proprietario.

    Centro = endereco fixo da barbearia. Inclui:
      - freelancers com status "disponivel na regiao" (online_regiao)
      - freelancers PRESENTES nesta mesma barbearia
    Exclui (regra 6): offline e quem esta PRESENTE em outra barbearia.

    Privacidade (regra 4): NAO retorna a localizacao exata do freelancer, apenas
    uma distancia aproximada em faixa.
    """
    if usuario_atual.tipo != "barbearia":
        raise HTTPException(status_code=403, detail="Apenas proprietarios de barbearia")

    barbearia = db.query(Barbearia).filter(Barbearia.usuario_id == usuario_atual.id).first()
    if not barbearia or barbearia.latitude is None or barbearia.longitude is None:
        return {"total": 0, "freelancers": [], "erro": "Barbearia sem localizacao definida"}

    centro_lat, centro_lon = barbearia.latitude, barbearia.longitude

    freelancers = (
        db.query(Usuario)
        .filter(
            Usuario.tipo == "barbeiro",
            Usuario.perfil_aprovado == True,  # noqa: E712
            Usuario.bloqueado_por_admin.isnot(True),
            or_(
                Usuario.online_regiao == True,  # noqa: E712
                and_(
                    Usuario.presente_em_local == True,  # noqa: E712
                    Usuario.barbearia_atual_id == barbearia.id,
                ),
            ),
        )
        .all()
    )

    bloqueados_aqui = {
        row[0]
        for row in db.query(BarbeariaFreelancer.freelancer_id)
        .filter(
            BarbeariaFreelancer.barbearia_id == barbearia.id,
            BarbeariaFreelancer.bloqueado == True,  # noqa: E712
        )
        .all()
    }

    itens = []
    for f in freelancers:
        if f.id in bloqueados_aqui:
            continue

        radar = db.query(RadarFreelancer).filter(RadarFreelancer.freelancer_id == f.id).first()
        flat = radar.latitude if radar and radar.latitude is not None else f.latitude
        flon = radar.longitude if radar and radar.longitude is not None else f.longitude
        if flat is None or flon is None:
            continue

        dist = _haversine_km(centro_lat, centro_lon, flat, flon)
        if dist > raio_km:
            continue

        presente_aqui = bool(f.presente_em_local and f.barbearia_atual_id == barbearia.id)
        itens.append(
            {
                "usuario_id": f.id,
                "nome": f.nome,
                "foto_perfil": f.foto_perfil,
                "status": "presente" if presente_aqui else "online_regiao",
                "status_label": "Presente na barbearia" if presente_aqui else "Disponivel na regiao",
                "distancia_aproximada": _faixa_aproximada(dist),
                # bucket grosseiro (100 m) apenas para ordenar - nao e a posicao exata
                "_ordem": round(dist * 10) / 10,
            }
        )

    itens.sort(key=lambda x: x["_ordem"])
    for i in itens:
        i.pop("_ordem", None)

    return {"total": len(itens), "freelancers": itens}
