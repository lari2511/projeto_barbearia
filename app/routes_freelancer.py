"""
Rotas para Freelancers - BarberMovie
Endpoints para cadastro, portfólio, busca e gestão de freelancers
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime, timedelta
from sqlalchemy import func
from pydantic import BaseModel
import qrcode
import io
import base64
import os

from app.database import get_db
from app.models import (
    Usuario, Freelancer, EspecialidadeFreelancer, PortfolioFreelancer,
    AvaliacaoFreelancer, Comissao, Chamado, OrigemCliente,
    CarteiraBarbeiro, HistoricoMovimentacaoFinanceira, Saque
)
from app.schemas import (
    FreelancerCreate, FreelancerResponse, FreelancerDetalhes,
    PortfolioUpload, PortfolioResponse, RelatorioComissoes,
    AvaliacaoFreelancerResponse, AceitarRecusarAtendimento,
    SolicitarFreelancerRequest
)
from app.routes import get_current_user  # Import da função de autenticação

router = APIRouter(prefix="/api/v1/freelancer", tags=["Freelancer"])

LIMITE_NEGATIVO_PADRAO = -50.0


class CarteiraQuitacaoConfirmarRequest(BaseModel):
    valor: float


class CarteiraSaquePixRequest(BaseModel):
    chave_pix: str
    valor: float | None = None


def _obter_ou_criar_carteira(db: Session, barbeiro_id: int) -> CarteiraBarbeiro:
    carteira = db.query(CarteiraBarbeiro).filter(CarteiraBarbeiro.barbeiro_id == barbeiro_id).first()
    if carteira:
        if carteira.limite_negativo is None:
            carteira.limite_negativo = LIMITE_NEGATIVO_PADRAO
        return carteira

    carteira = CarteiraBarbeiro(
        barbeiro_id=barbeiro_id,
        saldo=0.0,
        limite_negativo=LIMITE_NEGATIVO_PADRAO,
    )
    db.add(carteira)
    db.flush()
    return carteira


def _registrar_movimentacao(
    db: Session,
    *,
    carteira: CarteiraBarbeiro,
    tipo: str,
    descricao: str,
    valor: float,
    chamado_id: int | None = None,
):
    saldo_antes = float(carteira.saldo or 0.0)
    saldo_depois = saldo_antes + float(valor)
    carteira.saldo = saldo_depois

    mov = HistoricoMovimentacaoFinanceira(
        carteira_id=carteira.id,
        barbeiro_id=carteira.barbeiro_id,
        chamado_id=chamado_id,
        tipo=tipo,
        descricao=descricao,
        valor=float(valor),
        saldo_antes=saldo_antes,
        saldo_depois=saldo_depois,
    )
    db.add(mov)
    return mov


@router.post("/cadastro", response_model=dict)
def cadastrar_freelancer(
    dados: FreelancerCreate,
    db: Session = Depends(get_db),
    usuario_atual = Depends(get_current_user)
):
    """
    Cadastro de freelancer (após criar usuário tipo 'barbeiro')
    Valida nível mínimo e cria especialidades
    """
    # Verificar se já existe freelancer para este usuário
    freelancer_existente = db.query(Freelancer).filter(
        Freelancer.usuario_id == usuario_atual.id
    ).first()
    
    if freelancer_existente:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Freelancer já cadastrado"
        )
    
    # Validar nível técnico mínimo
    if dados.nivel_tecnico not in ["intermediario", "avancado", "expert"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Nível técnico deve ser no mínimo intermediário"
        )
    
    # Criar freelancer
    freelancer = Freelancer(
        usuario_id=usuario_atual.id,
        tempo_experiencia_anos=dados.tempo_experiencia_anos,
        nivel_tecnico=dados.nivel_tecnico,
        comissao_ativa=False,  # 1º mês grátis
        latitude=usuario_atual.latitude,
        longitude=usuario_atual.longitude
    )
    db.add(freelancer)
    db.commit()
    db.refresh(freelancer)
    
    # Criar especialidades
    for esp in dados.especialidades:
        especialidade = EspecialidadeFreelancer(
            freelancer_id=freelancer.id,
            tipo=esp
        )
        db.add(especialidade)
    
    db.commit()
    
    return {
        "message": "Freelancer cadastrado com sucesso! 1 mês grátis, depois 10% de comissão.",
        "freelancer_id": freelancer.id,
        "trial_ate": (datetime.now() + timedelta(days=30)).isoformat()
    }


@router.post("/portfolio", response_model=PortfolioResponse)
def adicionar_portfolio(
    dados: PortfolioUpload,
    db: Session = Depends(get_db),
    usuario_atual = Depends(get_current_user)
):
    """Adiciona foto ao portfólio do freelancer"""
    freelancer = db.query(Freelancer).filter(
        Freelancer.usuario_id == usuario_atual.id
    ).first()
    
    if not freelancer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Freelancer não encontrado"
        )
    
    # Obter maior ordem atual
    max_ordem = db.query(func.max(PortfolioFreelancer.ordem)).filter(
        PortfolioFreelancer.freelancer_id == freelancer.id,
        PortfolioFreelancer.tipo_servico == dados.tipo_servico
    ).scalar() or 0
    
    portfolio = PortfolioFreelancer(
        freelancer_id=freelancer.id,
        tipo_servico=dados.tipo_servico,
        url_imagem=dados.url_imagem,
        descricao=dados.descricao,
        ordem=max_ordem + 1
    )
    db.add(portfolio)
    db.commit()
    db.refresh(portfolio)
    
    return portfolio


@router.get("/meu-portfolio", response_model=List[PortfolioResponse])
def obter_meu_portfolio(
    db: Session = Depends(get_db),
    usuario_atual = Depends(get_current_user)
):
    """Retorna portfólio do freelancer logado"""
    freelancer = db.query(Freelancer).filter(
        Freelancer.usuario_id == usuario_atual.id
    ).first()
    
    if not freelancer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Freelancer não encontrado"
        )
    
    portfolio = db.query(PortfolioFreelancer).filter(
        PortfolioFreelancer.freelancer_id == freelancer.id
    ).order_by(PortfolioFreelancer.tipo_servico, PortfolioFreelancer.ordem).all()
    
    return portfolio


@router.get("/proximos", response_model=List[FreelancerResponse])
def buscar_freelancers_proximos(
    latitude: float,
    longitude: float,
    raio_km: float = 5.0,
    especialidade: str = None,
    db: Session = Depends(get_db)
):
    """
    Busca freelancers próximos (para clientes e barbearias)
    Calcula distância usando fórmula de Haversine
    """
    # Buscar freelancers não pausados
    query = db.query(
        Freelancer,
        Usuario.nome,
        Usuario.foto_perfil,
        Usuario.latitude,
        Usuario.longitude
    ).join(Usuario, Freelancer.usuario_id == Usuario.id).filter(
        Freelancer.status_pausado == False,
        Usuario.latitude.isnot(None),
        Usuario.longitude.isnot(None)
    )
    
    # Filtrar por especialidade se fornecida
    if especialidade:
        query = query.join(EspecialidadeFreelancer).filter(
            EspecialidadeFreelancer.tipo == especialidade
        )
    
    freelancers = query.all()
    
    # Calcular distância e filtrar por raio
    from math import radians, cos, sin, asin, sqrt
    
    def haversine(lat1, lon1, lat2, lon2):
        """Calcula distância em km entre duas coordenadas"""
        R = 6371  # Raio da Terra em km
        
        dLat = radians(lat2 - lat1)
        dLon = radians(lon2 - lon1)
        lat1 = radians(lat1)
        lat2 = radians(lat2)
        
        a = sin(dLat/2)**2 + cos(lat1) * cos(lat2) * sin(dLon/2)**2
        c = 2 * asin(sqrt(a))
        
        return R * c
    
    resultado = []
    for freelancer, nome, foto, lat, lon in freelancers:
        distancia = haversine(latitude, longitude, lat, lon)
        
        if distancia <= raio_km:
            # Calcular média de avaliações
            media = db.query(func.avg(AvaliacaoFreelancer.nota)).filter(
                AvaliacaoFreelancer.freelancer_id == freelancer.id
            ).scalar() or 0
            
            total = db.query(func.count(AvaliacaoFreelancer.id)).filter(
                AvaliacaoFreelancer.freelancer_id == freelancer.id
            ).scalar() or 0
            
            resultado.append({
                "id": freelancer.id,
                "usuario_id": freelancer.usuario_id,
                "tempo_experiencia_anos": freelancer.tempo_experiencia_anos,
                "nivel_tecnico": freelancer.nivel_tecnico,
                "status_pausado": freelancer.status_pausado,
                "latitude": lat,
                "longitude": lon,
                "distancia_km": round(distancia, 2),
                "nome": nome,
                "foto_perfil": foto,
                "media_avaliacoes": round(media, 1) if media else None,
                "total_avaliacoes": total
            })
    
    # Ordenar por distância
    resultado.sort(key=lambda x: x["distancia_km"])
    
    return resultado


@router.get("/todos", response_model=List[dict])
def listar_freelancers_para_barbearia(
    db: Session = Depends(get_db),
    usuario_atual = Depends(get_current_user)
):
    """Lista freelancers para selecao no painel da barbearia"""
    if usuario_atual.tipo != "barbearia":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Apenas barbearias")

    # Lista todos os barbeiros, mesmo sem registro em Freelancer (cadastro recém-criado).
    freelancers = db.query(Usuario, Freelancer).outerjoin(
        Freelancer,
        Freelancer.usuario_id == Usuario.id
    ).filter(
        Usuario.tipo == "barbeiro"
    ).all()

    resultado = []
    for usuario, freelancer in freelancers:
        resultado.append({
            "freelancer_id": freelancer.id if freelancer else None,
            "usuario_id": usuario.id,
            "nome": usuario.nome,
            "email": usuario.email,
            "foto_perfil": usuario.foto_perfil,
            "nivel_tecnico": freelancer.nivel_tecnico if freelancer else None,
            "status_pausado": freelancer.status_pausado if freelancer else False,
            "perfil_aprovado": bool(usuario.perfil_aprovado),
            "disponivel": bool(usuario.disponivel),
            "offline": bool(usuario.offline),
            "online_regiao": bool(usuario.online_regiao),
            "presente_em_local": bool(usuario.presente_em_local),
            "barbearia_atual_id": usuario.barbearia_atual_id,
        })
    return resultado


@router.get("/{freelancer_id}", response_model=FreelancerDetalhes)
def obter_freelancer_detalhes(
    freelancer_id: int,
    db: Session = Depends(get_db)
):
    """Retorna detalhes completos do freelancer (portfólio + avaliações)"""
    freelancer = db.query(Freelancer).filter(Freelancer.id == freelancer_id).first()
    
    if not freelancer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Freelancer não encontrado"
        )
    
    usuario = db.query(Usuario).filter(Usuario.id == freelancer.usuario_id).first()
    
    # Especialidades
    especialidades = db.query(EspecialidadeFreelancer.tipo).filter(
        EspecialidadeFreelancer.freelancer_id == freelancer_id
    ).all()
    especialidades_list = [esp[0] for esp in especialidades]
    
    # Portfólio
    portfolio = db.query(PortfolioFreelancer).filter(
        PortfolioFreelancer.freelancer_id == freelancer_id
    ).order_by(PortfolioFreelancer.tipo_servico, PortfolioFreelancer.ordem).all()
    
    # Avaliações recentes (últimas 5)
    avaliacoes = db.query(
        AvaliacaoFreelancer,
        Usuario.nome.label("avaliador_nome"),
        Usuario.foto_perfil.label("avaliador_foto")
    ).join(Usuario, AvaliacaoFreelancer.avaliador_id == Usuario.id).filter(
        AvaliacaoFreelancer.freelancer_id == freelancer_id
    ).order_by(AvaliacaoFreelancer.criado_em.desc()).limit(5).all()
    
    avaliacoes_list = []
    for av, nome, foto in avaliacoes:
        avaliacoes_list.append({
            "id": av.id,
            "nota": av.nota,
            "comentario": av.comentario,
            "tipo_avaliador": av.tipo_avaliador,
            "criado_em": av.criado_em,
            "avaliador_nome": nome,
            "avaliador_foto": foto
        })
    
    # Média de avaliações
    media = db.query(func.avg(AvaliacaoFreelancer.nota)).filter(
        AvaliacaoFreelancer.freelancer_id == freelancer_id
    ).scalar() or 0
    
    total = db.query(func.count(AvaliacaoFreelancer.id)).filter(
        AvaliacaoFreelancer.freelancer_id == freelancer_id
    ).scalar() or 0
    
    return {
        "id": freelancer.id,
        "usuario_id": freelancer.usuario_id,
        "tempo_experiencia_anos": freelancer.tempo_experiencia_anos,
        "nivel_tecnico": freelancer.nivel_tecnico,
        "status_pausado": freelancer.status_pausado,
        "latitude": usuario.latitude,
        "longitude": usuario.longitude,
        "nome": usuario.nome,
        "foto_perfil": usuario.foto_perfil,
        "media_avaliacoes": round(media, 1) if media else None,
        "total_avaliacoes": total,
        "especialidades": especialidades_list,
        "portfolio": portfolio,
        "avaliacoes_recentes": avaliacoes_list
    }


@router.patch("/pausar", response_model=dict)
def pausar_atendimentos(
    pausar: bool,
    db: Session = Depends(get_db),
    usuario_atual = Depends(get_current_user)
):
    """Pausa ou retoma atendimentos (ex: almoço)"""
    freelancer = db.query(Freelancer).filter(
        Freelancer.usuario_id == usuario_atual.id
    ).first()
    
    if not freelancer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Freelancer não encontrado"
        )
    
    freelancer.status_pausado = pausar
    db.commit()
    
    return {
        "message": "Atendimentos pausados" if pausar else "Atendimentos retomados",
        "status_pausado": pausar
    }


@router.post("/solicitar", response_model=dict)
def solicitar_freelancer(
    dados: SolicitarFreelancerRequest,
    db: Session = Depends(get_db),
    usuario_atual = Depends(get_current_user)
):
    """Barbeiro ou barbearia solicita um freelancer para atender na cadeira livre"""
    from app.models import Barbearia, Cadeira, StatusCadeira
    
    # Validar tipo de usuário
    if usuario_atual.tipo not in ["barbeiro", "barbearia"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Apenas barbeiros e barbearias podem solicitar freelancers"
        )

    # Buscar freelancer
    freelancer = db.query(Freelancer).filter(Freelancer.id == dados.freelancer_id).first()
    if not freelancer:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Freelancer não encontrado")

    # Determinar barbearia
    barbearia = None
    if usuario_atual.tipo == "barbearia":
        barbearia = db.query(Barbearia).filter(Barbearia.usuario_id == usuario_atual.id).first()
    else:  # barbeiro
        # Barbeiro procura a barbearia onde os agendamentos dele recentes estão
        # Para simplificar, pegamos a primeira barbearia que tem agendamentos do barbeiro
        chamado_recente = db.query(Chamado).filter(
            Chamado.barbeiro_id == usuario_atual.id
        ).order_by(Chamado.criado_em.desc()).first()
        
        if chamado_recente:
            barbearia = db.query(Barbearia).filter(Barbearia.id == chamado_recente.barbearia_id).first()
    
    if not barbearia:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Não foi possível determinar a barbearia. Faça um agendamento primeiro."
        )

    # Validar cadeiras disponíveis (apenas para barbeiro)
    if usuario_atual.tipo == "barbeiro":
        cadeiras_disponiveis = db.query(Cadeira).filter(
            Cadeira.barbearia_id == barbearia.id,
            Cadeira.status == StatusCadeira.DISPONIVEL
        ).all()
        
        if not cadeiras_disponiveis:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Nenhuma cadeira disponível nesta barbearia"
            )

    # Validar serviço: se não fornecido, tentar pegar primeiro serviço ativo da barbearia
    servico_id = dados.servico_id
    if not servico_id:
        from app.models import Servico
        servico = db.query(Servico).filter(Servico.barbearia_id == barbearia.id, Servico.ativo == True).order_by(Servico.valor.asc()).first()
        if not servico:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cadastre um serviço na barbearia para solicitar freelancer")
        servico_id = servico.id

    # Validar cadeira (se informada) e status disponível
    if dados.cadeira_id:
        cadeira = db.query(Cadeira).filter(Cadeira.id == dados.cadeira_id, Cadeira.barbearia_id == barbearia.id).first()
        if not cadeira:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cadeira não encontrada")
        if cadeira.status == StatusCadeira.OCUPADA and cadeira.freelancer_id and cadeira.freelancer_id != freelancer.usuario_id:
            nome = cadeira.freelancer.nome if cadeira.freelancer else "Freelancer"
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"BRB ocupada por {nome}")
        if cadeira.status == StatusCadeira.BLOQUEADA:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cadeira bloqueada")

    # Criar chamado direcionado ao freelancer
    from app.models import Chamado, StatusAgendamento
    from app.routes import calcular_split_pagamento
    from app.models import Servico
    servico = db.query(Servico).filter(Servico.id == servico_id).first()
    if not servico:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Serviço não encontrado")

    inicio = dados.data_hora_inicio or datetime.now()
    duracao = servico.duracao_minutos if getattr(servico, 'duracao_minutos', None) else 30
    fim = inicio + timedelta(minutes=duracao)

    split = calcular_split_pagamento(servico.valor)

    novo = Chamado(
        cliente_id=usuario_atual.id,  # Quem solicita (barbeiro ou dono da barbearia)
        barbeiro_id=freelancer.usuario_id,  # Direcionado ao freelancer
        servico_id=servico_id,
        barbearia_id=barbearia.id,
        data_hora_inicio=inicio,
        data_hora_fim=fim,
        status=StatusAgendamento.PENDENTE,
        origem_cliente=OrigemCliente.PROPRIO,
        valor_total=split['valor_total'],
        comissao_plataforma=split['comissao_plataforma'],
        valor_freelancer=split['valor_freelancer'],
        valor_dono=split['valor_dono'],
        valor_original=servico.valor,
        valor_final=servico.valor,
        observacao=f"Solicitação de freelancer para cadeira livre ({usuario_atual.tipo})"
    )
    db.add(novo)
    db.commit()
    db.refresh(novo)

    return {"message": "Solicitação enviada ao freelancer", "chamado_id": novo.id}


@router.post("/aceitar-atendimento", response_model=dict)
def aceitar_recusar_atendimento(
    dados: AceitarRecusarAtendimento,
    db: Session = Depends(get_db),
    usuario_atual = Depends(get_current_user)
):
    """Freelancer aceita ou recusa solicitação de atendimento"""
    chamado = db.query(Chamado).filter(Chamado.id == dados.chamado_id).first()
    
    if not chamado:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chamado não encontrado"
        )
    
    # Verificar se o freelancer é o destinatário
    freelancer = db.query(Freelancer).filter(
        Freelancer.usuario_id == usuario_atual.id
    ).first()
    
    if not freelancer or chamado.barbeiro_id != usuario_atual.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Você não tem permissão para este chamado"
        )
    
    if dados.aceitar:
        from app.models import StatusAgendamento
        chamado.status = StatusAgendamento.CONFIRMADO
        mensagem = "Atendimento aceito com sucesso!"
    else:
        from app.models import StatusAgendamento
        chamado.status = StatusAgendamento.CANCELADO
        if dados.motivo:
            chamado.observacao = f"Recusado: {dados.motivo}"
        mensagem = "Atendimento recusado"
    
    db.commit()
    
    return {"message": mensagem, "status": chamado.status}


@router.get("/comissoes/relatorio", response_model=RelatorioComissoes)
def obter_relatorio_comissoes(
    db: Session = Depends(get_db),
    usuario_atual = Depends(get_current_user)
):
    """Relatório de ganhos e comissões do freelancer"""
    freelancer = db.query(Freelancer).filter(
        Freelancer.usuario_id == usuario_atual.id
    ).first()
    
    if not freelancer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Freelancer não encontrado"
        )
    
    # Buscar todos os atendimentos concluídos
    from app.models import StatusAgendamento
    
    atendimentos = db.query(Chamado).filter(
        Chamado.barbeiro_id == usuario_atual.id,
        Chamado.status == StatusAgendamento.CONCLUIDO
    ).all()
    
    total_atendimentos = len(atendimentos)
    atendimentos_app = [a for a in atendimentos if a.origem_cliente == OrigemCliente.APP]
    atendimentos_proprios = [a for a in atendimentos if a.origem_cliente == OrigemCliente.PROPRIO]
    
    ganhos_brutos = sum([a.valor_total or 0 for a in atendimentos])
    
    # Comissões (apenas de atendimentos via app)
    comissoes = db.query(Comissao).filter(
        Comissao.freelancer_id == freelancer.id
    ).all()
    
    total_comissoes = sum([c.valor_comissao for c in comissoes])
    comissoes_pendentes = sum([c.valor_comissao for c in comissoes if c.status == "pendente"])
    comissoes_pagas = sum([c.valor_comissao for c in comissoes if c.status == "pago"])
    
    ganhos_liquidos = ganhos_brutos - total_comissoes

    carteira = _obter_ou_criar_carteira(db, usuario_atual.id)
    limite_negativo = float(carteira.limite_negativo if carteira.limite_negativo is not None else LIMITE_NEGATIVO_PADRAO)
    saldo_carteira = float(carteira.saldo or 0.0)
    bloqueado_financeiro = saldo_carteira <= limite_negativo

    historico = db.query(HistoricoMovimentacaoFinanceira).filter(
        HistoricoMovimentacaoFinanceira.barbeiro_id == usuario_atual.id
    ).order_by(HistoricoMovimentacaoFinanceira.criado_em.desc()).limit(20).all()

    historico_payload = [
        {
            "id": h.id,
            "tipo": h.tipo,
            "descricao": h.descricao,
            "valor": float(h.valor or 0.0),
            "saldo_antes": float(h.saldo_antes or 0.0),
            "saldo_depois": float(h.saldo_depois or 0.0),
            "chamado_id": h.chamado_id,
            "criado_em": h.criado_em.isoformat() if h.criado_em else None,
        }
        for h in historico
    ]
    
    return {
        "total_atendimentos": total_atendimentos,
        "total_atendimentos_app": len(atendimentos_app),
        "total_atendimentos_proprios": len(atendimentos_proprios),
        "ganhos_brutos": ganhos_brutos,
        "total_comissoes": total_comissoes,
        "ganhos_liquidos": ganhos_liquidos,
        "comissoes_pendentes": comissoes_pendentes,
        "comissoes_pagas": comissoes_pagas,
        "comissoes": comissoes,
        "saldo_carteira": saldo_carteira,
        "limite_negativo": limite_negativo,
        "bloqueado_financeiro": bloqueado_financeiro,
        "historico_movimentacoes": historico_payload,
    }


@router.get("/carteira/resumo", response_model=dict)
def obter_resumo_carteira(
    db: Session = Depends(get_db),
    usuario_atual = Depends(get_current_user)
):
    carteira = _obter_ou_criar_carteira(db, usuario_atual.id)
    limite_negativo = float(carteira.limite_negativo if carteira.limite_negativo is not None else LIMITE_NEGATIVO_PADRAO)
    saldo = float(carteira.saldo or 0.0)

    return {
        "saldo": saldo,
        "limite_negativo": limite_negativo,
        "bloqueado_financeiro": saldo <= limite_negativo,
    }


@router.post("/carteira/quitacao/pix-gerar", response_model=dict)
def gerar_pix_quitacao_carteira(
    db: Session = Depends(get_db),
    usuario_atual = Depends(get_current_user)
):
    carteira = _obter_ou_criar_carteira(db, usuario_atual.id)
    saldo = float(carteira.saldo or 0.0)
    if saldo >= 0:
        raise HTTPException(status_code=400, detail="Não há saldo devedor para quitar")

    valor = round(abs(saldo), 2)
    pix_chave = os.getenv("PIX_CHAVE", "+5511999999999")
    nome_recebedor = (os.getenv("PIX_NOME", "BarberMove") + " " * 13)[:13]
    cidade_recebedor = (os.getenv("PIX_CIDADE", "SAO PAULO") + " " * 9)[:9]
    valor_str = f"{valor:.2f}"
    pix_payload = (
        f"00020126360014BR.GOV.BCB.PIX0114{pix_chave}"
        f"0204000053039865406{valor_str}5802BR"
        f"5913{nome_recebedor}6009{cidade_recebedor}"
        f"62140510DEBITO{usuario_atual.id:04d}6304"
    )

    qr = qrcode.QRCode(version=1, box_size=10, border=5)
    qr.add_data(pix_payload)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    qrcode_base64 = base64.b64encode(buffer.getvalue()).decode()

    return {
        "valor_devedor": valor,
        "pix_copia_cola": pix_payload,
        "qrcode_base64": qrcode_base64,
    }


@router.post("/carteira/quitacao/confirmar", response_model=dict)
def confirmar_quitacao_carteira(
    dados: CarteiraQuitacaoConfirmarRequest,
    db: Session = Depends(get_db),
    usuario_atual = Depends(get_current_user)
):
    carteira = _obter_ou_criar_carteira(db, usuario_atual.id)
    valor = round(float(dados.valor or 0.0), 2)
    if valor <= 0:
        raise HTTPException(status_code=400, detail="Valor inválido para quitação")

    _registrar_movimentacao(
        db,
        carteira=carteira,
        tipo="quitacao_debito_pix",
        descricao="Pagamento de saldo devedor para liberar o app",
        valor=valor,
        chamado_id=None,
    )
    db.commit()

    saldo = float(carteira.saldo or 0.0)
    limite_negativo = float(carteira.limite_negativo if carteira.limite_negativo is not None else LIMITE_NEGATIVO_PADRAO)
    return {
        "message": "Saldo devedor quitado com sucesso",
        "saldo_atual": saldo,
        "bloqueado_financeiro": saldo <= limite_negativo,
    }


@router.post("/carteira/saque/pix", response_model=dict)
def solicitar_saque_pix(
    dados: CarteiraSaquePixRequest,
    db: Session = Depends(get_db),
    usuario_atual = Depends(get_current_user)
):
    carteira = _obter_ou_criar_carteira(db, usuario_atual.id)
    saldo = float(carteira.saldo or 0.0)
    if saldo <= 0:
        raise HTTPException(status_code=400, detail="Sem saldo positivo para saque")

    valor_saque = round(float(dados.valor if dados.valor is not None else saldo), 2)
    if valor_saque <= 0:
        raise HTTPException(status_code=400, detail="Valor de saque inválido")
    if valor_saque > saldo:
        raise HTTPException(status_code=400, detail="Valor de saque maior que saldo disponível")

    taxa = 0.0
    valor_liquido = valor_saque - taxa

    saque = Saque(
        usuario_id=usuario_atual.id,
        valor=valor_saque,
        valor_liquido=valor_liquido,
        taxa=taxa,
        status="pendente",
        banco="PIX",
        agencia="PIX",
        conta=dados.chave_pix.strip(),
        tipo_conta="pix",
    )
    db.add(saque)

    _registrar_movimentacao(
        db,
        carteira=carteira,
        tipo="solicitacao_saque_pix",
        descricao=f"Solicitação de saque via PIX ({dados.chave_pix.strip()})",
        valor=-valor_saque,
        chamado_id=None,
    )

    db.commit()
    return {
        "message": "Solicitação de saque enviada",
        "saque_id": saque.id,
        "valor": valor_saque,
        "saldo_atual": float(carteira.saldo or 0.0),
    }
