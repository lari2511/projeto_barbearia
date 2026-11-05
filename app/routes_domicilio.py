"""
Atendimento A DOMICÍLIO - BarberMove.

Modalidade em que o cliente escolhe direto um freelancer próximo, sem passar
por barbearia. O chamado é o mesmo `Chamado` de sempre (aceite, chat,
rastreamento, cronômetro, alteração de serviço, fechamento diário), marcado com
`modalidade = ATENDIMENTO_DOMICILIAR` e sem vínculo com barbearia/proprietário:
- barbearia_id = None, cadeira_id = None, valor_dono = 0
- endereço/coordenadas do atendimento ficam no próprio chamado
- não entra na fila de espera nem no controle de cadeira da barbearia

Serviços e preços a domicílio são do freelancer: linhas de `servicos` com
`freelancer_id` preenchido e `barbearia_id = None` (reusa duração/nome/valor
que o resto do sistema já lê por `chamado.servico_id`).

Reutiliza: localização (Usuario.latitude/longitude), status do freelancer
(online_regiao/disponivel/presente_em_local), bloqueio por taxa diária
(pagamento_diario) e resumo de avaliações (avaliacoes_service).
"""

from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app import firebase_config, models, schemas
from app.avaliacoes_service import resumo_freelancer
from app.database import get_db
from app.pagamento_diario import freelancer_bloqueado, freelancers_com_taxa_vencida
from app.routes_servicos import TEMPLATES_SERVICOS
from app.routes import (
    calcular_distancia_km,
    estimar_tempo_minutos,
    get_current_user,
    is_horario_disponivel,
)

router = APIRouter(prefix="/api/v1/domicilio", tags=["Atendimento a domicílio"])

RAIO_PADRAO_KM = 15.0
# Plataforma 10% / freelancer 90%: sem proprietário, não há parte do dono.
# A taxa diária do freelancer (fechamento 21h) já é 10% do valor do atendimento.
PERCENTUAL_PLATAFORMA = 0.10

STATUS_ATIVOS = [
    models.StatusAgendamento.PENDENTE.value,
    models.StatusAgendamento.CONFIRMADO.value,
    models.StatusAgendamento.EM_ATENDIMENTO.value,
]
CATEGORIAS_VALIDAS = {c.value for c in models.CategoriaServico}


# ============================================================
# HELPERS
# ============================================================

def calcular_split_domiciliar(valor_total: float) -> dict:
    valor_total = float(valor_total or 0)
    comissao = round(valor_total * PERCENTUAL_PLATAFORMA, 2)
    return {
        "valor_total": valor_total,
        "comissao_plataforma": comissao,
        "valor_freelancer": round(valor_total - comissao, 2),
        "valor_dono": 0.0,
    }


def servicos_domicilio_ativos(db: Session, freelancer_id: int):
    return db.query(models.Servico).filter(
        models.Servico.freelancer_id == freelancer_id,
        models.Servico.barbearia_id.is_(None),
        models.Servico.ativo == True,  # noqa: E712
    ).order_by(models.Servico.valor.asc(), models.Servico.nome.asc()).all()


def chamados_ativos_do_freelancer(db: Session, freelancer_id: int):
    return db.query(models.Chamado).filter(
        models.Chamado.barbeiro_id == freelancer_id,
        models.Chamado.status.in_(STATUS_ATIVOS),
    ).all()


def freelancer_em_domicilio_ativo(db: Session, freelancer_id: int) -> bool:
    """Tem atendimento a domicílio em aberto (usado para não misturar com a fila da barbearia)."""
    return db.query(models.Chamado.id).filter(
        models.Chamado.barbeiro_id == freelancer_id,
        models.Chamado.modalidade == models.MODALIDADE_DOMICILIAR,
        models.Chamado.status.in_(STATUS_ATIVOS),
    ).first() is not None


def _pausado(db: Session, freelancer_id: int) -> bool:
    perfil = db.query(models.Freelancer).filter(models.Freelancer.usuario_id == freelancer_id).first()
    return bool(perfil and getattr(perfil, "status_pausado", False))


def _disponibilidade_domicilio(db: Session, f: models.Usuario, com_taxa_pendente: set) -> tuple[bool, str]:
    """(pode_receber_agora, motivo). Mesmas regras que criar_chamado_domiciliar valida."""
    if f.id in com_taxa_pendente:
        return False, "Indisponível no momento"
    if _pausado(db, f.id):
        return False, "Atendimentos pausados"
    if chamados_ativos_do_freelancer(db, f.id):
        return False, "Em atendimento"
    return True, "Disponível"


def _serializar_servico(s: models.Servico) -> dict:
    return {
        "id": s.id,
        "nome": s.nome,
        "descricao": s.descricao,
        "categoria": s.categoria,
        "valor": s.valor,
        "duracao_minutos": s.duracao_minutos or 30,
        "ativo": bool(s.ativo),
    }


# ============================================================
# CLIENTE: freelancers perto de você (modalidade A DOMICÍLIO)
# ============================================================

@router.get("/freelancers-proximos")
def listar_freelancers_domicilio(
    latitude: Optional[float] = Query(None),
    longitude: Optional[float] = Query(None),
    raio_km: float = Query(RAIO_PADRAO_KM, gt=0, le=50),
    db: Session = Depends(get_db),
    usuario: models.Usuario = Depends(get_current_user),
):
    """
    Somente freelancers (nunca barbearias) que atendem a domicílio, perto do
    cliente, ordenados pela menor distância. Centro = lat/lon informados ou a
    última localização salva do cliente. Não expõe coordenadas do freelancer.
    """
    lat = latitude if latitude is not None else usuario.latitude
    lon = longitude if longitude is not None else usuario.longitude
    if lat is None or lon is None:
        return {"freelancers": [], "erro": "localizacao_indisponivel"}

    candidatos = db.query(models.Usuario).filter(
        models.Usuario.tipo == "barbeiro",
        models.Usuario.perfil_aprovado == True,  # noqa: E712
        models.Usuario.atende_domicilio == True,  # noqa: E712
        models.Usuario.latitude.isnot(None),
        models.Usuario.longitude.isnot(None),
        models.Usuario.id != usuario.id,
    ).all()

    com_taxa_pendente = freelancers_com_taxa_vencida(db)
    resultado = []
    for f in candidatos:
        # PRESENTE numa barbearia = atendendo lá; offline = fora do app.
        if f.presente_em_local:
            continue
        if not (f.online_regiao or f.disponivel or f.em_atendimento):
            continue
        servicos = servicos_domicilio_ativos(db, f.id)
        if not servicos:
            continue
        distancia = calcular_distancia_km(lat, lon, f.latitude, f.longitude)
        if distancia > raio_km:
            continue

        pode_receber, motivo = _disponibilidade_domicilio(db, f, com_taxa_pendente)
        perfil = db.query(models.Freelancer).filter(models.Freelancer.usuario_id == f.id).first()
        avaliacao = resumo_freelancer(db, perfil.id) if perfil else {"media": 0, "total": 0}

        resultado.append({
            "id": f.id,
            "nome": f.nome,
            "foto_perfil": f.foto_perfil,
            "distancia_km": round(distancia, 1),
            "tempo_estimado_minutos": estimar_tempo_minutos(distancia, velocidade_media_kmh=40.0),
            "media_avaliacoes": avaliacao["media"],
            "total_avaliacoes": avaliacao["total"],
            "disponivel": pode_receber,
            "status_texto": motivo,
            "tempo_experiencia": f.tempo_experiencia,
            "a_partir_de": min(float(s.valor or 0) for s in servicos),
            "total_servicos": len(servicos),
        })

    resultado.sort(key=lambda item: item["distancia_km"])
    return {"freelancers": resultado}


@router.get("/freelancer/{freelancer_id}/servicos")
def listar_servicos_domicilio_do_freelancer(
    freelancer_id: int,
    db: Session = Depends(get_db),
    usuario: models.Usuario = Depends(get_current_user),
):
    # Preços a domicílio são para o cliente (modalidade A DOMICÍLIO) e o próprio freelancer.
    if usuario.tipo not in ("cliente", "admin") and usuario.id != freelancer_id:
        raise HTTPException(status_code=403, detail="Preços a domicílio são exibidos só para clientes")
    f = db.query(models.Usuario).filter(
        models.Usuario.id == freelancer_id,
        models.Usuario.tipo == "barbeiro",
    ).first()
    if not f:
        raise HTTPException(status_code=404, detail="Freelancer não encontrado")
    if not f.atende_domicilio:
        return {"atende_domicilio": False, "servicos": []}
    return {
        "atende_domicilio": True,
        "servicos": [_serializar_servico(s) for s in servicos_domicilio_ativos(db, f.id)],
    }


# ============================================================
# FREELANCER: ligar/desligar e catálogo de serviços a domicílio
# ============================================================

class AtendeDomicilioIn(BaseModel):
    atende_domicilio: bool


class ServicoDomicilioIn(BaseModel):
    nome: str = Field(..., min_length=2, max_length=80)
    categoria: str = "corte"
    valor: float = Field(..., gt=0, le=5000)
    duracao_minutos: int = Field(30, ge=5, le=480)
    descricao: Optional[str] = Field(None, max_length=300)
    ativo: bool = True


def _exigir_freelancer(usuario: models.Usuario) -> None:
    if usuario.tipo != "barbeiro":
        raise HTTPException(status_code=403, detail="Apenas freelancers")


def _validar_categoria(categoria: str) -> str:
    cat = str(categoria or "").strip().lower()
    if cat not in CATEGORIAS_VALIDAS:
        raise HTTPException(status_code=400, detail="Categoria de serviço inválida")
    return cat


@router.get("/meus-servicos")
def meus_servicos_domicilio(db: Session = Depends(get_db), usuario: models.Usuario = Depends(get_current_user)):
    _exigir_freelancer(usuario)
    servicos = db.query(models.Servico).filter(
        models.Servico.freelancer_id == usuario.id,
        models.Servico.barbearia_id.is_(None),
    ).order_by(models.Servico.nome.asc()).all()
    return {
        "atende_domicilio": bool(usuario.atende_domicilio),
        "servicos": [_serializar_servico(s) for s in servicos],
    }


@router.put("/atendimento")
def alterar_atende_domicilio(
    dados: AtendeDomicilioIn,
    db: Session = Depends(get_db),
    usuario: models.Usuario = Depends(get_current_user),
):
    _exigir_freelancer(usuario)
    if dados.atende_domicilio and not servicos_domicilio_ativos(db, usuario.id):
        raise HTTPException(status_code=400, detail="Cadastre ao menos um serviço a domicílio antes de ativar.")
    usuario.atende_domicilio = dados.atende_domicilio
    db.commit()
    return {"atende_domicilio": bool(usuario.atende_domicilio)}


@router.post("/meus-servicos")
def criar_servico_domicilio(
    dados: ServicoDomicilioIn,
    db: Session = Depends(get_db),
    usuario: models.Usuario = Depends(get_current_user),
):
    _exigir_freelancer(usuario)
    servico = models.Servico(
        barbearia_id=None,
        freelancer_id=usuario.id,
        nome=dados.nome.strip(),
        descricao=(dados.descricao or "").strip() or None,
        categoria=_validar_categoria(dados.categoria),
        valor=round(float(dados.valor), 2),
        duracao_minutos=dados.duracao_minutos,
        ativo=dados.ativo,
    )
    db.add(servico)
    db.commit()
    db.refresh(servico)
    return _serializar_servico(servico)


def _servico_do_freelancer(db: Session, servico_id: int, usuario: models.Usuario) -> models.Servico:
    servico = db.query(models.Servico).filter(
        models.Servico.id == servico_id,
        models.Servico.freelancer_id == usuario.id,
        models.Servico.barbearia_id.is_(None),
    ).first()
    if not servico:
        raise HTTPException(status_code=404, detail="Serviço não encontrado")
    return servico


@router.put("/meus-servicos/{servico_id}")
def editar_servico_domicilio(
    servico_id: int,
    dados: ServicoDomicilioIn,
    db: Session = Depends(get_db),
    usuario: models.Usuario = Depends(get_current_user),
):
    _exigir_freelancer(usuario)
    servico = _servico_do_freelancer(db, servico_id, usuario)
    servico = _versionar_servico(
        db, servico,
        nome=dados.nome.strip(),
        descricao=(dados.descricao or "").strip() or None,
        categoria=_validar_categoria(dados.categoria),
        valor=round(float(dados.valor), 2),
        duracao_minutos=dados.duracao_minutos,
    )
    if not dados.ativo:
        servico.ativo = False
    _desligar_se_sem_servicos(db, usuario)
    db.commit()
    db.refresh(servico)
    return _serializar_servico(servico)


@router.delete("/meus-servicos/{servico_id}")
def remover_servico_domicilio(
    servico_id: int,
    db: Session = Depends(get_db),
    usuario: models.Usuario = Depends(get_current_user),
):
    """Desativa (não apaga): chamados antigos continuam lendo nome/valor/duração."""
    _exigir_freelancer(usuario)
    servico = _servico_do_freelancer(db, servico_id, usuario)
    servico.ativo = False
    _desligar_se_sem_servicos(db, usuario)
    db.commit()
    return {"ok": True, "atende_domicilio": bool(usuario.atende_domicilio)}


def _versionar_servico(db: Session, servico: models.Servico, **novos) -> models.Servico:
    """
    Aplica nome/preço/duração novos. Se o serviço já foi usado em algum chamado,
    não mexe nele: desativa e cria uma versão nova. Assim cada chamado continua
    apontando para o preço/duração de quando foi feito (telas, taxa e alteração
    de serviço leem `chamado.servico_id`).
    """
    mudou = any(getattr(servico, campo) != valor for campo, valor in novos.items())
    if not mudou:
        return servico
    usado = db.query(models.Chamado.id).filter(models.Chamado.servico_id == servico.id).first() is not None
    if not usado:
        for campo, valor in novos.items():
            setattr(servico, campo, valor)
        return servico
    servico.ativo = False
    dados = {
        "nome": servico.nome, "descricao": servico.descricao, "categoria": servico.categoria,
        "valor": servico.valor, "duracao_minutos": servico.duracao_minutos,
    }
    dados.update(novos)
    nova = models.Servico(barbearia_id=None, freelancer_id=servico.freelancer_id, ativo=True, **dados)
    db.add(nova)
    db.flush()
    return nova


# ============================================================
# FREELANCER: "Valores a cobrar a domicílio" (mesmos serviços-modelo do proprietário)
# ============================================================

def _chave(nome: str) -> str:
    return " ".join(str(nome or "").lower().split())


class ValorDomicilioIn(BaseModel):
    nome: str = Field(..., min_length=2, max_length=80)
    categoria: str = "outros"
    valor: Optional[float] = Field(None, ge=0, le=5000)   # vazio/0 = não ofereço
    duracao_minutos: int = Field(30, ge=5, le=480)


class ValoresDomicilioIn(BaseModel):
    itens: list[ValorDomicilioIn]


def _valores_do_freelancer(db: Session, usuario: models.Usuario) -> dict:
    ativos = servicos_domicilio_ativos(db, usuario.id)
    por_nome = {_chave(s.nome): s for s in ativos}
    nomes_modelo = set()
    itens = []
    for modelo in TEMPLATES_SERVICOS:
        chave = _chave(modelo["nome"])
        nomes_modelo.add(chave)
        atual = por_nome.get(chave)
        itens.append({
            "nome": modelo["nome"],
            "categoria": modelo["categoria"],
            "descricao": modelo.get("descricao"),
            "servico_id": atual.id if atual else None,
            "valor": atual.valor if atual else None,
            "duracao_minutos": (atual.duracao_minutos if atual else None) or modelo["duracao_minutos_padrao"],
        })
    outros = [_serializar_servico(s) for s in ativos if _chave(s.nome) not in nomes_modelo]
    return {"atende_domicilio": bool(usuario.atende_domicilio), "itens": itens, "outros": outros}


@router.get("/valores")
def meus_valores_domicilio(db: Session = Depends(get_db), usuario: models.Usuario = Depends(get_current_user)):
    _exigir_freelancer(usuario)
    return _valores_do_freelancer(db, usuario)


@router.put("/valores")
def salvar_valores_domicilio(
    dados: ValoresDomicilioIn,
    db: Session = Depends(get_db),
    usuario: models.Usuario = Depends(get_current_user),
):
    """Cadastra/atualiza/remove (valor vazio) os preços a domicílio, um por serviço."""
    _exigir_freelancer(usuario)
    if len(dados.itens) > 40:
        raise HTTPException(status_code=400, detail="Itens demais")
    ativos = {_chave(s.nome): s for s in servicos_domicilio_ativos(db, usuario.id)}
    for item in dados.itens:
        chave = _chave(item.nome)
        atual = ativos.get(chave)
        valor = round(float(item.valor), 2) if item.valor else None
        if valor is None:
            if atual:
                atual.ativo = False
            continue
        if atual:
            ativos[chave] = _versionar_servico(db, atual, valor=valor, duracao_minutos=item.duracao_minutos)
        else:
            novo = models.Servico(
                barbearia_id=None, freelancer_id=usuario.id, nome=" ".join(item.nome.split()),
                categoria=_validar_categoria(item.categoria), valor=valor,
                duracao_minutos=item.duracao_minutos, ativo=True,
            )
            db.add(novo)
            db.flush()
            ativos[chave] = novo
    _desligar_se_sem_servicos(db, usuario)
    db.commit()
    return _valores_do_freelancer(db, usuario)


def _desligar_se_sem_servicos(db: Session, usuario: models.Usuario) -> None:
    db.flush()
    if usuario.atende_domicilio and not servicos_domicilio_ativos(db, usuario.id):
        usuario.atende_domicilio = False


# ============================================================
# CRIAÇÃO DO CHAMADO DOMICILIAR (chamado por POST /api/v1/chamados)
# ============================================================

def criar_chamado_domiciliar(chamado: schemas.ChamadoCreate, user: models.Usuario, db: Session) -> dict:
    if user.tipo != "cliente":
        raise HTTPException(status_code=403, detail="Apenas clientes podem solicitar atendimento a domicílio")
    if chamado.barbearia_id:
        raise HTTPException(status_code=400, detail="Atendimento a domicílio não tem barbearia")
    if not chamado.barbeiro_id:
        raise HTTPException(status_code=400, detail="Escolha o freelancer")
    if chamado.barbeiro_selecionado_id and chamado.barbeiro_selecionado_id != chamado.barbeiro_id:
        raise HTTPException(status_code=400, detail="Conflito no freelancer selecionado. Atualize a tela e tente novamente.")
    if chamado.cliente_latitude is None or chamado.cliente_longitude is None:
        raise HTTPException(status_code=400, detail="A localização é obrigatória para realizar um chamado em tempo real.")

    endereco = str(chamado.endereco_atendimento or "").strip()
    if len(endereco) < 5:
        raise HTTPException(status_code=400, detail="Informe o endereço onde você quer ser atendido.")
    endereco = endereco[:255]
    lat_atendimento = chamado.latitude_atendimento if chamado.latitude_atendimento is not None else chamado.cliente_latitude
    lon_atendimento = chamado.longitude_atendimento if chamado.longitude_atendimento is not None else chamado.cliente_longitude

    servico = db.query(models.Servico).filter(models.Servico.id == chamado.servico_id).first()
    if (
        not servico
        or servico.barbearia_id is not None
        or servico.freelancer_id != chamado.barbeiro_id
        or not servico.ativo
    ):
        raise HTTPException(status_code=400, detail="Este serviço ou preço a domicílio foi atualizado pelo freelancer. Volte e escolha de novo.")

    barbeiro = db.query(models.Usuario).filter(models.Usuario.id == chamado.barbeiro_id).first()
    if not barbeiro or barbeiro.tipo != "barbeiro" or not barbeiro.perfil_aprovado:
        raise HTTPException(status_code=404, detail="Freelancer não encontrado")
    if not barbeiro.atende_domicilio:
        raise HTTPException(status_code=400, detail="Este profissional não atende a domicílio no momento.")
    if barbeiro.presente_em_local:
        raise HTTPException(status_code=400, detail="Este profissional está atendendo numa barbearia agora. Tente outro profissional.")
    if not (barbeiro.online_regiao or barbeiro.disponivel):
        raise HTTPException(status_code=400, detail="Este profissional não está disponível para novos agendamentos.")
    if freelancer_bloqueado(db, barbeiro.id):
        raise HTTPException(status_code=400, detail="Este profissional não está disponível para novos chamados agora. Escolha outro profissional.")
    if _pausado(db, barbeiro.id):
        raise HTTPException(status_code=400, detail="Barbeiro está com atendimentos pausados no momento.")

    if barbeiro.latitude is not None and barbeiro.longitude is not None:
        distancia = calcular_distancia_km(lat_atendimento, lon_atendimento, barbeiro.latitude, barbeiro.longitude)
        if distancia > RAIO_PADRAO_KM:
            raise HTTPException(status_code=400, detail="Este profissional está longe demais do endereço informado.")

    # Domicílio não tem fila de espera: o freelancer só pode ter este atendimento
    # (os outros serviços do MESMO pedido entram pelo grupo_id).
    grupo_base = None
    if chamado.grupo_id:
        grupo_base = db.query(models.Chamado).filter(models.Chamado.id == chamado.grupo_id).first()
        if (
            not grupo_base
            or grupo_base.cliente_id != user.id
            or grupo_base.barbeiro_id != barbeiro.id
            or not models.chamado_domiciliar(grupo_base)
        ):
            raise HTTPException(status_code=400, detail="Pedido inválido")
    grupo_ids = {chamado.grupo_id} if chamado.grupo_id else set()
    for ativo in chamados_ativos_do_freelancer(db, barbeiro.id):
        if ativo.id in grupo_ids or (ativo.grupo_id and ativo.grupo_id in grupo_ids):
            continue
        raise HTTPException(status_code=400, detail="Este profissional já está com um atendimento em andamento. Tente novamente depois.")

    if not chamado.data_hora_inicio:
        raise HTTPException(status_code=400, detail="Data e hora de início obrigatórias")
    duracao = servico.duracao_minutos or 30
    hora_fim = chamado.data_hora_inicio + timedelta(minutes=duracao)
    if not grupo_base and not is_horario_disponivel(db, barbeiro.id, chamado.data_hora_inicio, hora_fim):
        raise HTTPException(status_code=400, detail="Barbeiro ja tem um corte aceito nesse horario. Tente outro horario.")

    user.latitude = chamado.cliente_latitude
    user.longitude = chamado.cliente_longitude

    split = calcular_split_domiciliar(servico.valor)
    novo = models.Chamado(
        cliente_id=user.id,
        barbeiro_id=barbeiro.id,
        servico_id=servico.id,
        barbearia_id=None,
        cadeira_id=None,
        modalidade=models.MODALIDADE_DOMICILIAR,
        endereco_atendimento=endereco,
        latitude_atendimento=lat_atendimento,
        longitude_atendimento=lon_atendimento,
        data_hora_inicio=chamado.data_hora_inicio,
        data_hora_fim=hora_fim,
        grupo_id=chamado.grupo_id,
        status=models.StatusAgendamento.PENDENTE.value,
        # O cliente já está no local do atendimento: só falta o freelancer chegar.
        cliente_chegou=True,
        valor_total=split["valor_total"],
        comissao_plataforma=split["comissao_plataforma"],
        valor_freelancer=split["valor_freelancer"],
        valor_dono=split["valor_dono"],
        valor_original=servico.valor,
        valor_final=servico.valor,
    )
    db.add(novo)
    db.commit()
    db.refresh(novo)

    if grupo_base and not grupo_base.grupo_id:
        grupo_base.grupo_id = grupo_base.id
        db.commit()

    db.add(models.ChamadoHistorico(
        chamado_id=novo.id,
        status_novo="ABERTO",
        usuario_id=user.id,
        observacao="Chamado a domicílio criado",
    ))
    db.add(models.Notificacao(
        usuario_id=barbeiro.id,
        titulo="Novo Chamado a domicílio!",
        mensagem=f"{user.nome} solicitou {servico.nome} a domicílio",
        tipo="novo_chamado",
        referencia_id=novo.id,
    ))
    db.commit()

    try:
        token = getattr(barbeiro, "device_token", None)
        if token:
            firebase_config.enviar_notificacao_novo_chamado(token, user.nome, servico.nome, "A domicílio")
    except Exception:
        pass

    return {
        "id": novo.id,
        "status": novo.status,
        "cliente_id": novo.cliente_id,
        "servico_id": novo.servico_id,
        "descricao": servico.nome,
        "valor": novo.valor_total,
        "valor_total": novo.valor_total,
        "modalidade": novo.modalidade,
        "endereco_atendimento": novo.endereco_atendimento,
        "data_hora_inicio": novo.data_hora_inicio.isoformat() if novo.data_hora_inicio else None,
        "data_hora_fim": novo.data_hora_fim.isoformat() if novo.data_hora_fim else None,
        "cliente_latitude": chamado.cliente_latitude,
        "cliente_longitude": chamado.cliente_longitude,
        "rastreamento_ativo": True,
    }
