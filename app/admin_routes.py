"""
Rotas para Admin Dashboard Web
Endpoints para gerenciar aprovações via interface web
Protegido por autenticação de admin
"""

from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.responses import HTMLResponse
from sqlalchemy import func, or_
from sqlalchemy.orm import Session
from datetime import datetime

from app.database import get_db
from app.models import (
    Usuario, Foto, Freelancer, PortfolioFreelancer, FechamentoDiarioFreelancer,
    Barbearia, Cadeira, AssinaturaBarbearia, CadeiraContratada, FaturaAssinatura,
    AvaliacaoFreelancer, AvaliacaoBarbearia,
)
from app.routes import get_current_user

router = APIRouter(prefix="/admin", tags=["Admin"])


def _portfolio_de_usuario(db: Session, usuario: Usuario):
    """Fotos de portfólio de um usuário.

    Barbeiro salva portfólio na tabela `fotos` (usuario_id); freelancer
    cadastrado salva em `portfolio_freelancer` (freelancer_id). Reúne as duas.
    """
    itens = []

    for f in (
        db.query(Foto)
        .filter(Foto.usuario_id == usuario.id)
        .order_by(Foto.criado_em.desc())
        .all()
    ):
        itens.append({"url": f.url, "descricao": f.descricao})

    freelancer = db.query(Freelancer).filter(Freelancer.usuario_id == usuario.id).first()
    if freelancer:
        for p in (
            db.query(PortfolioFreelancer)
            .filter(PortfolioFreelancer.freelancer_id == freelancer.id)
            .order_by(PortfolioFreelancer.tipo_servico, PortfolioFreelancer.ordem)
            .all()
        ):
            desc = p.descricao or p.tipo_servico
            itens.append({"url": p.url_imagem, "descricao": desc})

    return itens

# Verificar se é admin ou barbearia (permitir ambos)
def verificar_admin(usuario = Depends(get_current_user)):
    print(f"🔍 verificar_admin - Usuário: {usuario.email}, Tipo: {usuario.tipo}")
    if usuario.tipo not in ["admin", "barbearia"]:
        print(f"❌ Acesso negado para tipo: {usuario.tipo}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acesso negado - apenas admins e barbearias"
        )
    print(f"✅ Acesso permitido para {usuario.email}")
    return usuario


def verificar_somente_admin(usuario = Depends(get_current_user)):
    if usuario.tipo != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acesso negado - apenas admins"
        )
    return usuario

# ============================================================================
# TESTE DE AUTENTICAÇÃO
# ============================================================================

@router.get("/api/test-auth")
def testar_autenticacao(admin = Depends(verificar_admin)):
    """Endpoint de teste para verificar autenticação"""
    return {
        "status": "autenticado",
        "usuario_id": admin.id,
        "email": admin.email,
        "tipo": admin.tipo
    }

# ============================================================================
# ENDPOINTS DA API
# ============================================================================

@router.get("/api/pendentes")
def listar_pendentes(
    db: Session = Depends(get_db),
    admin = Depends(verificar_admin)
):
    """Lista usuários pendentes de aprovação"""
    pendentes = db.query(Usuario).filter(
        Usuario.perfil_aprovado == False,
        Usuario.tipo.in_(['barbeiro', 'cliente', 'barbearia']),
        # cadastro rápido ainda sem fotos/documentos: não está pronto para análise
        or_(Usuario.cadastro_pendente == False, Usuario.cadastro_pendente.is_(None)),  # noqa: E712
    ).order_by(Usuario.criado_em).all()
    
    return [{
        "id": u.id,
        "nome": u.nome,
        "email": u.email,
        "tipo": u.tipo,
        "telefone": u.telefone,
        "rg": u.rg,
        "criado_em": u.criado_em,
        "documento_frente": bool(u.documento_frente_url),
        "documento_verso": bool(u.documento_verso_url),
        "selfie": bool(u.selfie_documento_url),
        "email_verificado": u.email_verificado,
        "documento_frente_url": u.documento_frente_url,
        "documento_verso_url": u.documento_verso_url,
        "selfie_documento_url": u.selfie_documento_url,
        "tempo_experiencia": u.tempo_experiencia,
        "portfolio": _portfolio_de_usuario(db, u),
    } for u in pendentes]

@router.get("/api/aprovados")
def listar_aprovados(
    db: Session = Depends(get_db),
    admin = Depends(verificar_admin)
):
    """Lista usuários já aprovados"""
    aprovados = db.query(Usuario).filter(
        Usuario.perfil_aprovado == True,
        Usuario.tipo.in_(['barbeiro', 'cliente', 'barbearia'])
    ).order_by(Usuario.perfil_aprovado_em.desc()).all()
    
    return [{
        "id": u.id,
        "nome": u.nome,
        "email": u.email,
        "tipo": u.tipo,
        "telefone": u.telefone,
        "aprovado_em": u.perfil_aprovado_em,
        "documento_frente_url": u.documento_frente_url,
        "documento_verso_url": u.documento_verso_url,
        "selfie_documento_url": u.selfie_documento_url,
        "tempo_experiencia": u.tempo_experiencia,
        "portfolio": _portfolio_de_usuario(db, u),
    } for u in aprovados]

@router.get("/api/estatisticas")
def obter_estatisticas(
    db: Session = Depends(get_db),
    admin = Depends(verificar_admin)
):
    """Estatísticas gerais"""
    total_usuarios = db.query(Usuario).filter(
        Usuario.tipo.in_(['barbeiro', 'cliente', 'barbearia'])
    ).count()
    
    aprovados = db.query(Usuario).filter(
        Usuario.perfil_aprovado == True,
        Usuario.tipo.in_(['barbeiro', 'cliente', 'barbearia'])
    ).count()
    
    pendentes = total_usuarios - aprovados
    
    barbeiros = db.query(Usuario).filter(
        Usuario.tipo == 'barbeiro'
    ).count()
    
    clientes = db.query(Usuario).filter(
        Usuario.tipo == 'cliente'
    ).count()
    
    barbearias = db.query(Usuario).filter(
        Usuario.tipo == 'barbearia'
    ).count()
    
    # Mesma lista que a área "Pagamentos pendentes" mostra (só o ADM vê pagamentos).
    pagamentos_pendentes = None
    if admin.tipo == "admin":
        from app import pagamento_diario
        pagamentos_pendentes = db.query(FechamentoDiarioFreelancer).filter(
            FechamentoDiarioFreelancer.status.in_(pagamento_diario.STATUS_ABERTOS)
        ).count()

    return {
        "total": total_usuarios,
        "aprovados": aprovados,
        "pendentes": pendentes,
        "barbeiros": barbeiros,
        "clientes": clientes,
        "barbearias": barbearias,
        "pagamentos_pendentes": pagamentos_pendentes,
    }

@router.get("/api/usuario/{usuario_id}")
def obter_usuario_detalhes(
    usuario_id: int,
    db: Session = Depends(get_db),
    admin = Depends(verificar_admin)
):
    """Retorna detalhes completos do usuário (documentos, portfólio, etc)"""
    usuario = db.query(Usuario).filter(Usuario.id == usuario_id).first()
    
    if not usuario:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")
    
    portfolio = _portfolio_de_usuario(db, usuario)

    barbearia = None
    if usuario.tipo == "barbearia":
        barbearia = _dados_barbearia(db, usuario, com_historico=True)

    return {
        "barbearia": barbearia,
        "id": usuario.id,
        "nome": usuario.nome,
        "email": usuario.email,
        "tipo": usuario.tipo,
        "telefone": usuario.telefone,
        "rg": usuario.rg,
        "criado_em": usuario.criado_em,
        "documento_frente": usuario.documento_frente_url,
        "documento_verso": usuario.documento_verso_url,
        "selfie": usuario.selfie_documento_url,
        "tempo_experiencia": usuario.tempo_experiencia,
        "portfolio": portfolio,
        "aprovado": usuario.perfil_aprovado,
        "aprovado_em": usuario.perfil_aprovado_em,
    }

@router.post("/api/aprovar/{usuario_id}")
def aprovar_usuario(
    usuario_id: int,
    db: Session = Depends(get_db),
    admin = Depends(verificar_admin),
    background_tasks = None
):
    """Aprova um usuário e envia email de confirmação"""
    usuario = db.query(Usuario).filter(Usuario.id == usuario_id).first()
    
    if not usuario:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")
    
    if usuario.perfil_aprovado:
        raise HTTPException(status_code=400, detail="Usuário já aprovado")
    
    usuario.perfil_aprovado = True
    usuario.perfil_aprovado_em = datetime.now()
    db.commit()
    
    # Enviar email de aprovação em background
    if background_tasks:
        from app.email_send import send_perfil_approved_email
        background_tasks.add_task(
            send_perfil_approved_email,
            usuario.email,
            usuario.nome,
            usuario.tipo
        )
    
    return {"status": "aprovado", "usuario_id": usuario.id}

@router.post("/api/rejeitar/{usuario_id}")
def rejeitar_usuario(
    usuario_id: int,
    request: Request,
    db: Session = Depends(get_db),
    admin = Depends(verificar_admin)
):
    """Rejeita um usuário"""
    usuario = db.query(Usuario).filter(Usuario.id == usuario_id).first()
    
    if not usuario:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")

    bloqueios = _historico_que_impede_exclusao(db, usuario)
    if bloqueios:
        raise HTTPException(
            status_code=409,
            detail="Não dá para recusar: este cadastro já tem histórico no app (" + ", ".join(bloqueios) + ")."
        )

    # Remove primeiro o que pertence só ao cadastro (fotos, portfólio, notificações...);
    # sem isso o Postgres recusa apagar o usuário por causa das chaves estrangeiras.
    _apagar_dados_do_cadastro(db, usuario)
    db.delete(usuario)
    db.commit()

    return {"status": "rejeitado", "usuario_id": usuario_id}


# Linhas que pertencem só ao cadastro e podem sair junto com ele: (tabela, coluna -> usuarios.id).
_DADOS_DO_CADASTRO = {
    ("fotos", "usuario_id"),
    ("notificacoes", "usuario_id"),
    ("notificacoes_barbeiro", "barbeiro_id"),
    ("tokens_recuperacao", "usuario_id"),
    ("disponibilidades", "usuario_id"),
    ("radar_freelancer", "freelancer_id"),
    ("request_views", "freelancer_id"),
    ("favoritos", "usuario_id"),
    ("favoritos", "favorito_id"),
    ("precos_customizados", "barbeiro_id"),
    ("configuracoes_repasse_usuarios", "usuario_id"),
    ("contas_pagamento_usuarios", "usuario_id"),
    ("carteiras", "barbeiro_id"),  # só sai se não tiver movimentação (historico_movimentacoes bloqueia)
    ("freelancers", "usuario_id"),  # portfólio/especialidades saem junto; avaliações/comissões bloqueiam
}
_FILHOS_DO_FREELANCER = {"portfolio_freelancer", "especialidades_freelancer"}
# Campos preenchidos pelo próprio ADM ao decidir algo; não são histórico do usuário recusado.
_CAMPOS_DO_ADM = {"revisada_por_admin_id", "decidido_por_id", "atualizado_por_id"}

_NOMES_HISTORICO = {
    "chamados": "atendimentos", "agendamentos_ativos": "atendimentos", "cortes": "atendimentos",
    "avaliacoes": "avaliações", "avaliacoes_freelancer": "avaliações", "avaliacoes_barbearia": "avaliações",
    "fechamentos_diarios_freelancer": "pagamentos diários", "historico_movimentacoes": "movimentações financeiras",
    "transacoes_financeiras": "transações", "saques": "saques", "comissoes": "comissões",
    "barbearias": "barbearia cadastrada", "mensagens_chat": "mensagens",
}


def _fks_para(tabela_alvo: str):
    from app.database import Base
    for tabela in Base.metadata.sorted_tables:
        for coluna in tabela.columns:
            for fk in coluna.foreign_keys:
                if fk.column.table.name == tabela_alvo and fk.column.name == "id":
                    yield tabela, coluna


def _historico_que_impede_exclusao(db: Session, usuario: Usuario):
    """Tabelas com registros reais do usuário (atendimentos, pagamentos, avaliações...)."""
    from sqlalchemy import select
    achados = set()
    for tabela, coluna in _fks_para("usuarios"):
        if (tabela.name, coluna.name) in _DADOS_DO_CADASTRO or coluna.name in _CAMPOS_DO_ADM:
            continue
        if db.execute(select(func.count()).select_from(tabela).where(coluna == usuario.id)).scalar():
            achados.add(_NOMES_HISTORICO.get(tabela.name, tabela.name))

    ids_freelancer = [f.id for f in db.query(Freelancer).filter(Freelancer.usuario_id == usuario.id).all()]
    if ids_freelancer:
        for tabela, coluna in _fks_para("freelancers"):
            if tabela.name in _FILHOS_DO_FREELANCER:
                continue
            if db.execute(select(func.count()).select_from(tabela).where(coluna.in_(ids_freelancer))).scalar():
                achados.add(_NOMES_HISTORICO.get(tabela.name, tabela.name))
    return sorted(achados)


def _apagar_dados_do_cadastro(db: Session, usuario: Usuario):
    ids_freelancer = [f.id for f in db.query(Freelancer).filter(Freelancer.usuario_id == usuario.id).all()]
    if ids_freelancer:
        for tabela, coluna in _fks_para("freelancers"):
            if tabela.name in _FILHOS_DO_FREELANCER:
                db.execute(tabela.delete().where(coluna.in_(ids_freelancer)))
    # freelancers por último, depois dos filhos
    for tabela, coluna in sorted(_fks_para("usuarios"), key=lambda tc: tc[0].name == "freelancers"):
        if (tabela.name, coluna.name) in _DADOS_DO_CADASTRO:
            db.execute(tabela.delete().where(coluna == usuario.id))
    db.flush()

@router.get("/api/buscar")
def buscar_usuario(
    q: str = "",
    db: Session = Depends(get_db),
    admin = Depends(verificar_admin)
):
    """Buscar usuário por email ou nome"""
    if not q or len(q) < 2:
        return []
    
    usuarios = db.query(Usuario).filter(
        (Usuario.email.ilike(f"%{q}%")) | (Usuario.nome.ilike(f"%{q}%")),
        Usuario.tipo.in_(['barbeiro', 'cliente', 'barbearia'])
    ).limit(10).all()
    
    return [{
        "id": u.id,
        "nome": u.nome,
        "email": u.email,
        "tipo": u.tipo,
        "aprovado": u.perfil_aprovado,
    } for u in usuarios]

# ============================================================================
# PAINEL ORGANIZADO (Freelancers / Proprietários / Clientes) - só leitura
# ============================================================================

def _iso(dt):
    return dt.isoformat() if dt else None


def _qtd_fotos(db: Session, usuario: Usuario) -> int:
    """Quantidade de fotos de portfólio (mesmas fontes de _portfolio_de_usuario)."""
    total = db.query(Foto).filter(Foto.usuario_id == usuario.id).count()
    freelancer = db.query(Freelancer).filter(Freelancer.usuario_id == usuario.id).first()
    if freelancer:
        total += db.query(PortfolioFreelancer).filter(PortfolioFreelancer.freelancer_id == freelancer.id).count()
    return total


def _dados_barbearia(db: Session, usuario: Usuario, com_historico: bool = False):
    """Barbearia do proprietário + cadeiras/assinatura já registradas no sistema."""
    b = db.query(Barbearia).filter(Barbearia.usuario_id == usuario.id).first()
    if not b:
        return None

    cadeiras = db.query(Cadeira).filter(
        Cadeira.barbearia_id == b.id,
        Cadeira.status != "inativa",
    ).count()
    assinatura = db.query(AssinaturaBarbearia).filter(AssinaturaBarbearia.barbearia_id == b.id).first()
    primeira_contratacao = db.query(func.min(CadeiraContratada.data_contratacao)).filter(
        CadeiraContratada.barbearia_id == b.id
    ).scalar()
    data_contratacao = primeira_contratacao or (assinatura.criado_em if assinatura else None)

    dados = {
        "id": b.id,
        "nome": b.nome,
        "endereco": b.endereco,
        "cadeiras": cadeiras,
        "data_contratacao": _iso(data_contratacao),
        "assinatura": {
            "quantidade_cadeiras": assinatura.quantidade_cadeiras,
            "valor_mensalidade": assinatura.valor_mensalidade,
            "status": assinatura.status,
            "proximo_vencimento": _iso(assinatura.proximo_vencimento),
        } if assinatura else None,
        "faturas": [],
    }
    if com_historico and assinatura:
        faturas = db.query(FaturaAssinatura).filter(
            FaturaAssinatura.assinatura_id == assinatura.id
        ).order_by(FaturaAssinatura.data_vencimento.desc()).limit(24).all()
        dados["faturas"] = [{
            "mes_referencia": f.mes_referencia,
            "valor": f.valor_fatura,
            "quantidade_cadeiras": f.quantidade_cadeiras,
            "status": f.status,
            "data_vencimento": _iso(f.data_vencimento),
            "data_pagamento": _iso(f.data_pagamento),
        } for f in faturas]
    return dados


@router.get("/api/lista")
def listar_por_tipo(
    tipo: str,
    situacao: str = "todos",
    q: str = "",
    db: Session = Depends(get_db),
    admin = Depends(verificar_admin)
):
    """Lista enxuta por tipo (barbeiro/barbearia/cliente), filtrando pendente/aprovado e busca."""
    if tipo not in ("barbeiro", "barbearia", "cliente"):
        raise HTTPException(status_code=400, detail="Tipo inválido")

    query = db.query(Usuario).filter(Usuario.tipo == tipo)
    if situacao == "pendente":
        query = query.filter(or_(Usuario.perfil_aprovado == False, Usuario.perfil_aprovado.is_(None)))  # noqa: E712
        # cadastro rápido ainda sem fotos/documentos: não está pronto para análise
        query = query.filter(or_(Usuario.cadastro_pendente == False, Usuario.cadastro_pendente.is_(None)))  # noqa: E712
    elif situacao == "aprovado":
        query = query.filter(Usuario.perfil_aprovado == True)  # noqa: E712

    termo = (q or "").strip()
    if termo:
        filtro = or_(Usuario.nome.ilike(f"%{termo}%"), Usuario.email.ilike(f"%{termo}%"))
        if tipo == "barbearia":
            donos = db.query(Barbearia.usuario_id).filter(Barbearia.nome.ilike(f"%{termo}%"))
            filtro = or_(filtro, Usuario.id.in_(donos))
        query = query.filter(filtro)

    if situacao == "pendente":
        query = query.order_by(Usuario.criado_em)
    else:
        query = query.order_by(Usuario.nome)

    resultado = []
    for u in query.limit(200).all():
        item = {
            "id": u.id,
            "nome": u.nome,
            "email": u.email,
            "telefone": u.telefone,
            "tipo": u.tipo,
            "aprovado": bool(u.perfil_aprovado),
            "cadastro_incompleto": bool(u.cadastro_pendente),
            "criado_em": _iso(u.criado_em),
        }
        if tipo == "barbeiro":
            item["tempo_experiencia"] = u.tempo_experiencia
            item["qtd_fotos"] = _qtd_fotos(db, u)
        elif tipo == "barbearia":
            item["barbearia"] = _dados_barbearia(db, u)
        resultado.append(item)
    return resultado


# Reclamação = avaliação de 1 ou 2 estrelas (mesmo corte de /api/v1/admin/avaliacoes/negativas).
# Pendente/resolvida = ainda não / já revisada pelo ADM (revisada_por_admin_id).
NOTA_RECLAMACAO = 2
_AVALIADORES_VALIDOS = {
    "freelancer": ["cliente", "barbearia"],   # quem avalia o freelancer
    "barbearia": ["cliente", "freelancer"],   # quem avalia a barbearia
}


def _serializar_avaliacao(av, alvo: str, sobre_nome: str) -> dict:
    return {
        "id": av.id,
        "alvo": alvo,
        "sobre_nome": sobre_nome,
        "nota": av.nota,
        "comentario": av.comentario,
        "tipo_avaliador": av.tipo_avaliador,
        "avaliador_nome": av.avaliador.nome if av.avaliador else None,
        "criado_em": _iso(av.criado_em),
        "reclamacao": (av.nota or 0) <= NOTA_RECLAMACAO,
        "status": "resolvida" if av.revisada_por_admin_id else "pendente",
        "bloqueada": bool(av.bloqueada_por_admin),
    }


@router.get("/api/avaliacoes")
def listar_avaliacoes_admin(
    alvo: str = "todos",            # freelancer | barbearia | todos
    avaliador: str = "todos",       # cliente | barbearia | freelancer | todos
    reclamacoes: bool = False,      # só notas 1-2
    status_reclamacao: str = "",    # pendente | resolvida
    db: Session = Depends(get_db),
    admin = Depends(verificar_somente_admin)
):
    """Comentários e reclamações (avaliações) para as áreas do painel ADM."""
    itens = []
    fontes = [
        ("freelancer", AvaliacaoFreelancer),
        ("barbearia", AvaliacaoBarbearia),
    ]
    for nome_alvo, Modelo in fontes:
        if alvo not in (nome_alvo, "todos"):
            continue
        validos = _AVALIADORES_VALIDOS[nome_alvo]
        if avaliador != "todos" and avaliador not in validos:
            continue
        query = db.query(Modelo).filter(
            Modelo.tipo_avaliador.in_([avaliador] if avaliador != "todos" else validos)
        )
        if reclamacoes:
            query = query.filter(Modelo.nota <= NOTA_RECLAMACAO)
            if status_reclamacao == "pendente":
                query = query.filter(Modelo.revisada_por_admin_id.is_(None))
            elif status_reclamacao == "resolvida":
                query = query.filter(Modelo.revisada_por_admin_id.isnot(None))

        for av in query.order_by(Modelo.criado_em.desc()).limit(200).all():
            if nome_alvo == "freelancer":
                fr = av.freelancer
                sobre = fr.usuario.nome if fr and fr.usuario else "Freelancer"
            else:
                sobre = av.barbearia.nome if av.barbearia else "Barbearia"
            itens.append(_serializar_avaliacao(av, nome_alvo, sobre))

    itens.sort(key=lambda i: i["criado_em"] or "", reverse=True)
    return itens


@router.post("/api/avaliacoes/{alvo}/{avaliacao_id}/resolver")
def resolver_reclamacao(
    alvo: str,
    avaliacao_id: int,
    db: Session = Depends(get_db),
    admin = Depends(verificar_somente_admin)
):
    """Marca a reclamação como resolvida (revisada pelo ADM). Não bloqueia nem altera a nota."""
    Modelo = {"freelancer": AvaliacaoFreelancer, "barbearia": AvaliacaoBarbearia}.get(alvo)
    if not Modelo:
        raise HTTPException(status_code=400, detail="Alvo inválido")
    av = db.query(Modelo).filter(Modelo.id == avaliacao_id).first()
    if not av:
        raise HTTPException(status_code=404, detail="Avaliação não encontrada")
    av.revisada_por_admin_id = admin.id
    db.commit()
    return {"status": "resolvida", "id": av.id}

# ============================================================================
# PAGAMENTO DIÁRIO DO FREELANCER (fechamento 21:00 / prazo 22:00 - São Paulo)
# ============================================================================

@router.get("/api/pagamentos-diarios")
def listar_pagamentos_diarios(
    db: Session = Depends(get_db),
    admin = Depends(verificar_somente_admin)
):
    """Fechamentos diários em aberto (aguardando confirmação primeiro)."""
    from app import pagamento_diario

    agora = pagamento_diario.agora_sp()
    fechamentos = db.query(FechamentoDiarioFreelancer).filter(
        FechamentoDiarioFreelancer.status.in_(pagamento_diario.STATUS_ABERTOS)
    ).order_by(FechamentoDiarioFreelancer.data_referencia.desc()).all()

    ordem = {"aguardando_confirmacao": 0, "recusado": 1, "pendente": 2}
    fechamentos.sort(key=lambda f: ordem.get(f.status, 9))

    resultado = []
    for f in fechamentos:
        item = pagamento_diario.serializar_fechamento(f, agora)
        u = f.freelancer
        item["freelancer_nome"] = u.nome if u else None
        item["freelancer_email"] = u.email if u else None
        item["freelancer_telefone"] = u.telefone if u else None
        item["bloqueado"] = bool(pagamento_diario.fechamento_bloqueante(db, f.freelancer_id, agora))
        resultado.append(item)
    return resultado


@router.get("/api/pagamentos-diarios/confirmados")
def listar_pagamentos_diarios_confirmados(
    db: Session = Depends(get_db),
    admin = Depends(verificar_somente_admin)
):
    """Histórico dos fechamentos já confirmados pelo ADM (só leitura)."""
    from app import pagamento_diario

    fechamentos = db.query(FechamentoDiarioFreelancer).filter(
        FechamentoDiarioFreelancer.status == "confirmado"
    ).order_by(
        FechamentoDiarioFreelancer.decidido_em.desc(),
        FechamentoDiarioFreelancer.data_referencia.desc(),
    ).limit(100).all()

    resultado = []
    for f in fechamentos:
        item = pagamento_diario.serializar_fechamento(f)
        u = f.freelancer
        item["freelancer_nome"] = u.nome if u else None
        item["freelancer_email"] = u.email if u else None
        item["decidido_em"] = _iso(f.decidido_em)
        resultado.append(item)
    return resultado


@router.post("/api/pagamentos-diarios/{fechamento_id}/confirmar")
def confirmar_pagamento_diario(
    fechamento_id: int,
    db: Session = Depends(get_db),
    admin = Depends(verificar_somente_admin)
):
    """SIM - pagamento confirmado: quita na carteira e devolve o controle do status ao freelancer."""
    from app import pagamento_diario
    from app.routes_freelancer import _obter_ou_criar_carteira, _registrar_movimentacao

    f = db.query(FechamentoDiarioFreelancer).filter(FechamentoDiarioFreelancer.id == fechamento_id).first()
    if not f:
        raise HTTPException(status_code=404, detail="Fechamento não encontrado")
    if f.status == "confirmado":
        raise HTTPException(status_code=400, detail="Pagamento já confirmado")

    carteira = _obter_ou_criar_carteira(db, f.freelancer_id)
    _registrar_movimentacao(
        db,
        carteira=carteira,
        tipo="quitacao_debito_pix",
        descricao=f"Pagamento diário via Pix ({f.data_referencia.strftime('%d/%m/%Y')}) confirmado pelo ADM",
        valor=round(float(f.valor_devido or 0.0), 2),
        chamado_id=None,
    )
    f.status = "confirmado"
    f.decidido_em = datetime.utcnow()
    f.decidido_por_id = admin.id
    db.commit()

    # Não coloca o freelancer online: apenas remove a trava (derivada dos fechamentos em aberto).
    ainda_bloqueado = bool(pagamento_diario.fechamento_bloqueante(db, f.freelancer_id))
    return {
        "message": "Pagamento confirmado",
        "fechamento": pagamento_diario.serializar_fechamento(f),
        "freelancer_bloqueado": ainda_bloqueado,
    }


@router.post("/api/pagamentos-diarios/{fechamento_id}/recusar")
def recusar_pagamento_diario(
    fechamento_id: int,
    db: Session = Depends(get_db),
    admin = Depends(verificar_somente_admin)
):
    """NÃO - pagamento não confirmado: o freelancer continua bloqueado/OFFLINE."""
    from app import pagamento_diario

    f = db.query(FechamentoDiarioFreelancer).filter(FechamentoDiarioFreelancer.id == fechamento_id).first()
    if not f:
        raise HTTPException(status_code=404, detail="Fechamento não encontrado")
    if f.status == "confirmado":
        raise HTTPException(status_code=400, detail="Pagamento já confirmado")

    f.status = "recusado"
    f.decidido_em = datetime.utcnow()
    f.decidido_por_id = admin.id
    db.commit()
    return {
        "message": "Pagamento não confirmado",
        "fechamento": pagamento_diario.serializar_fechamento(f),
    }


# ============================================================================
# PÁGINA HTML DO DASHBOARD
# ============================================================================

@router.get("/", response_class=HTMLResponse)
def dashboard_page():
    """Página do dashboard admin - com login integrado"""
    # no-store: o painel é servido pelo backend (não passa pelo build do PWA);
    # sem isso o navegador guardava a versão antiga e o admin não via as atualizações.
    return HTMLResponse(content=_DASHBOARD_HTML, headers={"Cache-Control": "no-store, must-revalidate"})


_DASHBOARD_HTML = r"""
    <!DOCTYPE html>
    <html lang="pt-BR">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Painel Administrativo - BarberMove</title>
        <style>
            :root {
                --bg: #0a0d14;
                --bloco: #121a2e;
                --bloco-2: #17213a;
                --borda: #22304f;
                --laranja: #f97316;
                --texto: #ffffff;
                --cinza: #9ca3af;
                --verde: #10b981;
                --vermelho: #ef4444;
                --amarelo: #f59e0b;
            }
            * { margin: 0; padding: 0; box-sizing: border-box; }
            body {
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                background: var(--bg);
                color: var(--texto);
                min-height: 100vh;
                padding: 16px;
            }
            #app { max-width: 560px; margin: 0 auto; padding-bottom: 40px; }
            button { font-family: inherit; }

            /* Topo */
            .topo-home { display: flex; justify-content: space-between; align-items: flex-start; margin: 4px 0 18px; }
            .marca { font-size: 24px; font-weight: 800; }
            .marca span { color: var(--laranja); }
            .subtitulo { color: var(--cinza); font-size: 14px; margin-top: 2px; }
            .btn-sair {
                background: transparent; border: 1px solid var(--borda); color: var(--cinza);
                padding: 8px 14px; border-radius: 10px; font-weight: 700; cursor: pointer;
            }
            .topo { margin: 0 0 16px; }
            .btn-voltar {
                background: var(--bloco); border: 1px solid var(--borda); color: var(--texto);
                padding: 10px 16px; border-radius: 12px; font-weight: 800; font-size: 14px; cursor: pointer;
            }
            .titulo { font-size: 20px; font-weight: 800; margin-top: 14px; }
            .titulo-sub { color: var(--cinza); font-size: 13px; margin-top: 4px; }

            /* Resumo compacto */
            .resumo {
                background: var(--bloco); border: 1px solid var(--borda); border-radius: 14px;
                padding: 6px 14px; margin-bottom: 18px;
            }
            .resumo-linha {
                display: flex; justify-content: space-between; padding: 7px 0;
                font-size: 14px; color: var(--cinza); border-bottom: 1px solid var(--borda);
            }
            .resumo-linha:last-child { border-bottom: none; }
            .resumo-linha b { color: var(--texto); }
            .resumo-linha b.destaque { color: var(--laranja); }

            /* Barrinhas principais */
            .rows { display: flex; flex-direction: column; gap: 10px; }
            .row {
                display: flex; align-items: center; gap: 12px; width: 100%;
                min-height: 64px; padding: 14px 16px; text-align: left;
                background: var(--bloco); border: 1px solid var(--borda); border-radius: 14px;
                color: var(--texto); cursor: pointer;
            }
            .row:hover, .row:active { border-color: var(--laranja); }
            .row.grande { min-height: 76px; }
            .row .ic { font-size: 22px; width: 28px; text-align: center; flex-shrink: 0; }
            .row .txt { flex: 1; min-width: 0; }
            .row .txt b { display: block; font-size: 15px; font-weight: 800; letter-spacing: 0.3px; }
            .row .txt small { display: block; color: var(--cinza); font-size: 12px; margin-top: 3px; }
            .row .badge {
                background: var(--laranja); color: #fff; font-size: 12px; font-weight: 800;
                padding: 3px 9px; border-radius: 999px;
            }
            .row .chev { color: var(--cinza); font-size: 24px; line-height: 1; }

            /* Busca */
            .busca {
                width: 100%; padding: 13px 14px; margin-bottom: 14px;
                background: var(--bloco); border: 1px solid var(--borda); border-radius: 12px;
                color: var(--texto); font-size: 15px;
            }
            .busca:focus { outline: none; border-color: var(--laranja); }

            /* Itens de lista */
            .item {
                background: var(--bloco); border: 1px solid var(--borda); border-radius: 14px;
                padding: 14px 16px;
            }
            .item h3 { font-size: 16px; font-weight: 800; margin-bottom: 6px; }
            .item p { font-size: 13px; color: var(--cinza); margin-top: 3px; }
            .item p.texto { color: #e5e7eb; font-size: 14px; margin-top: 8px; white-space: pre-wrap; }
            .item .acoes { display: flex; gap: 8px; margin-top: 12px; flex-wrap: wrap; }
            .estrelas { color: var(--laranja); letter-spacing: 1px; }

            .btn {
                border: none; border-radius: 12px; padding: 12px 16px; min-height: 46px;
                font-size: 14px; font-weight: 800; cursor: pointer; color: #fff;
            }
            .btn-laranja { background: var(--laranja); }
            .btn-verde { background: var(--verde); }
            .btn-vermelho { background: var(--vermelho); }
            .btn-neutro { background: var(--bloco-2); border: 1px solid var(--borda); }
            .btn-largo { width: 100%; }

            .status-pendente, .item p.status-pendente { color: var(--laranja); font-weight: 800; }
            .status-ok, .item p.status-ok { color: var(--verde); font-weight: 800; }
            .status-ruim, .item p.status-ruim { color: var(--vermelho); font-weight: 800; }

            /* Perfil */
            .ficha { background: var(--bloco); border: 1px solid var(--borda); border-radius: 14px; padding: 4px 16px; }
            .campo { padding: 11px 0; border-bottom: 1px solid var(--borda); }
            .campo:last-child { border-bottom: none; }
            .campo .rotulo { color: var(--cinza); font-size: 11px; font-weight: 800; letter-spacing: 0.6px; }
            .campo .valor { font-size: 15px; margin-top: 3px; word-break: break-word; }
            .decisao { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin-top: 16px; }
            .decisao .btn { min-height: 54px; font-size: 15px; }
            .secao { margin-top: 16px; }
            .secao-titulo { color: var(--laranja); font-size: 13px; font-weight: 800; margin-bottom: 8px; }

            .segmento { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; margin-bottom: 14px; }
            .segmento button {
                min-height: 46px; border-radius: 12px; font-weight: 800; font-size: 14px; cursor: pointer;
                background: var(--bloco); border: 1px solid var(--borda); color: var(--cinza);
            }
            .segmento button.ativo { border-color: var(--laranja); color: var(--texto); background: rgba(249,115,22,0.12); }

            .vazio { text-align: center; color: var(--cinza); padding: 36px 10px; font-size: 14px; }
            .carregando { text-align: center; color: var(--cinza); padding: 36px 10px; }

            /* Fotos */
            .thumb-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 8px; }
            .thumb {
                position: relative; display: block; width: 100%; aspect-ratio: 1 / 1;
                border: 1px solid var(--borda); border-radius: 10px; overflow: hidden;
                cursor: pointer; background: #0f1524; padding: 0;
            }
            .thumb img { width: 100%; height: 100%; object-fit: cover; display: block; }
            .thumb .thumb-cap {
                position: absolute; left: 0; right: 0; bottom: 0;
                background: linear-gradient(transparent, rgba(0,0,0,0.75));
                color: #fff; font-size: 10px; padding: 10px 4px 3px; text-align: left;
                white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
            }
            .thumb.faltando {
                display: flex; align-items: center; justify-content: center;
                color: var(--cinza); font-size: 11px; cursor: default; text-align: center;
            }

            /* Lightbox */
            .lightbox {
                position: fixed; inset: 0; background: rgba(0,0,0,0.92);
                display: none; align-items: center; justify-content: center; z-index: 1000;
            }
            .lightbox.aberto { display: flex; }
            .lightbox img { max-width: 92vw; max-height: 80vh; object-fit: contain; border-radius: 8px; }
            .lightbox .lb-fechar {
                position: absolute; top: 14px; right: 18px; font-size: 34px; color: #fff;
                background: none; border: none; cursor: pointer; line-height: 1;
            }
            .lightbox .lb-nav {
                position: absolute; top: 50%; transform: translateY(-50%);
                font-size: 40px; line-height: 1; color: #fff; background: rgba(255,255,255,0.12);
                border: none; cursor: pointer; width: 48px; height: 60px; border-radius: 12px;
                display: flex; align-items: center; justify-content: center;
            }
            .lightbox .lb-prev { left: 8px; }
            .lightbox .lb-next { right: 8px; }
            .lightbox .lb-info { position: absolute; bottom: 18px; left: 0; right: 0; text-align: center; color: #d4d4d8; font-size: 13px; }

            /* Login */
            .login { background: var(--bloco); border: 1px solid var(--borda); border-radius: 16px; padding: 28px 20px; margin-top: 60px; }
            .login label { display: block; margin: 14px 0 6px; color: var(--cinza); font-size: 13px; }
            .login input {
                width: 100%; padding: 13px; background: var(--bg); border: 1px solid var(--borda);
                border-radius: 10px; color: #fff; font-size: 15px;
            }
            .login .erro { color: var(--vermelho); text-align: center; margin-top: 14px; font-size: 14px; }
        </style>
    </head>
    <body>
        <div id="app"><div class="carregando">Carregando...</div></div>

        <!-- LIGHTBOX (fotos dos trabalhos / documentos) -->
        <div class="lightbox" id="lightbox" onclick="if(event.target===this)fecharLightbox()">
            <button class="lb-fechar" onclick="fecharLightbox()" title="Fechar">&times;</button>
            <button class="lb-nav lb-prev" id="lbPrev" onclick="navLightbox(-1)" title="Anterior">&#8249;</button>
            <img id="lightboxImg" src="" alt="">
            <button class="lb-nav lb-next" id="lbNext" onclick="navLightbox(1)" title="Próxima">&#8250;</button>
            <div class="lb-info" id="lightboxInfo"></div>
        </div>

        <script>
            const API_URL = "/admin/api";
            let token = localStorage.getItem('token');
            let viewAtual = null;
            const app = document.getElementById('app');

            // ---------------------------------------------------------------
            // Utilidades
            // ---------------------------------------------------------------
            function esc(t) {
                return String(t == null ? '' : t).replace(/[&<>"']/g, c => ({
                    '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'
                }[c]));
            }

            function dataBR(iso) {
                if (!iso) return '—';
                const [a, m, d] = String(iso).slice(0, 10).split('-');
                return `${d}/${m}/${a}`;
            }

            function dinheiro(v) {
                return 'R$ ' + Number(v || 0).toFixed(2).replace('.', ',');
            }

            function estrelas(n) {
                const k = Math.max(0, Math.min(5, Number(n) || 0));
                return '★'.repeat(k) + '☆'.repeat(5 - k);
            }

            const QUEM_AVALIOU = { cliente: 'Cliente', barbearia: 'Proprietário', freelancer: 'Freelancer' };

            async function api(caminho, opcoes = {}) {
                const res = await fetch(API_URL + caminho, {
                    ...opcoes,
                    headers: { 'Authorization': `Bearer ${token}`, ...(opcoes.headers || {}) }
                });
                if (res.status === 401) {
                    sessaoExpirada();
                    throw new Error('sessao');
                }
                const data = await res.json().catch(() => ({}));
                if (!res.ok) {
                    const err = new Error(data.detail || `Erro ${res.status}`);
                    err.status = res.status;
                    throw err;
                }
                return data;
            }

            function linha(ic, titulo, sub, acao, badge, grande) {
                return `
                    <button class="row ${grande ? 'grande' : ''}" onclick="${acao}">
                        <span class="ic">${ic}</span>
                        <span class="txt"><b>${titulo}</b>${sub ? `<small>${sub}</small>` : ''}</span>
                        ${badge ? `<span class="badge">${badge}</span>` : ''}
                        <span class="chev">›</span>
                    </button>`;
            }

            function topo(titulo, sub) {
                return `
                    <div class="topo">
                        <button class="btn-voltar" onclick="voltar()">← VOLTAR</button>
                        <div class="titulo">${titulo}</div>
                        ${sub ? `<div class="titulo-sub" id="tituloSub">${sub}</div>` : '<div class="titulo-sub" id="tituloSub"></div>'}
                    </div>`;
            }

            function erroHtml(err) {
                if (err && err.status === 403) return '<div class="vazio">Apenas o ADM pode ver esta área.</div>';
                return '<div class="vazio">Erro ao carregar. Tente novamente.</div>';
            }

            // ---------------------------------------------------------------
            // Navegação (botão VOLTAR e o voltar do navegador/celular)
            // ---------------------------------------------------------------
            function ir(view, params) {
                history.pushState({ view, params: params || {} }, '');
                render(view, params || {});
                window.scrollTo(0, 0);
            }

            function voltar() {
                if (history.state && history.state.view !== 'home') history.back();
                else render('home', {});
            }

            window.addEventListener('popstate', e => {
                const s = e.state || { view: 'home', params: {} };
                render(s.view, s.params || {});
            });

            const VIEWS = {};

            function render(view, params) {
                viewAtual = view;
                (VIEWS[view] || VIEWS.home)(params || {});
            }

            // ---------------------------------------------------------------
            // Login
            // ---------------------------------------------------------------
            function mostrarLogin() {
                app.innerHTML = `
                    <div class="login">
                        <div class="marca" style="text-align:center">Barber<span>Move</span></div>
                        <div class="subtitulo" style="text-align:center">Painel Administrativo</div>
                        <form onsubmit="fazerLogin(event)">
                            <label>Email</label>
                            <input type="email" id="email" required placeholder="admin@barbermove.com">
                            <label>Senha</label>
                            <input type="password" id="senha" required placeholder="••••••••">
                            <button type="submit" class="btn btn-laranja btn-largo" style="margin-top:22px">Entrar</button>
                            <p id="erro" class="erro"></p>
                        </form>
                    </div>`;
            }

            async function fazerLogin(e) {
                e.preventDefault();
                const email = document.getElementById('email').value;
                const senha = document.getElementById('senha').value;
                const erro = document.getElementById('erro');
                try {
                    const formData = new URLSearchParams();
                    formData.append('username', email);
                    formData.append('password', senha);
                    // Tentar login em múltiplos endpoints (admin ou barbearia)
                    const endpoints = ['/api/v1/login/admin/', '/api/v1/login/barbearia/'];
                    for (const endpoint of endpoints) {
                        const res = await fetch(endpoint, {
                            method: 'POST',
                            headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
                            body: formData
                        });
                        if (res.ok) {
                            const data = await res.json();
                            localStorage.setItem('token', data.access_token);
                            location.reload();
                            return;
                        }
                    }
                    erro.textContent = 'Email ou senha incorretos, ou sem permissão de admin';
                } catch (err) {
                    erro.textContent = 'Erro ao conectar - verifique se o backend está rodando';
                }
            }

            function sessaoExpirada() {
                // Token invalido/expirado (ex.: sobrou login de barbearia nesse dominio).
                localStorage.removeItem('token');
                token = null;
                mostrarLogin();
            }

            function logout() {
                localStorage.clear();
                window.location.href = '/';
            }

            // ---------------------------------------------------------------
            // 1. Tela principal
            // ---------------------------------------------------------------
            VIEWS.home = async () => {
                app.innerHTML = `
                    <div class="topo-home">
                        <div>
                            <div class="marca">Barber<span>Move</span></div>
                            <div class="subtitulo">Painel Administrativo</div>
                        </div>
                        <button class="btn-sair" onclick="logout()">Sair</button>
                    </div>
                    <div class="resumo" id="resumo"><div class="resumo-linha">Carregando resumo...</div></div>
                    <div class="rows">
                        ${linha('👤', 'FREELANCERS', '', "ir('freelancers')", '', true)}
                        ${linha('🏪', 'PROPRIETÁRIOS', '', "ir('proprietarios')", '', true)}
                        ${linha('👥', 'CLIENTES', '', "ir('clientes')", '', true)}
                        ${linha('💰', 'PAGAMENTOS DE FREELANCERS', '', "ir('pagamentos')", '', true)}
                    </div>`;
                try {
                    const s = await api('/estatisticas');
                    if (viewAtual !== 'home') return;
                    const l = (rotulo, valor, destaque) =>
                        `<div class="resumo-linha"><span>${rotulo}</span><b class="${destaque && valor ? 'destaque' : ''}">${valor}</b></div>`;
                    document.getElementById('resumo').innerHTML =
                        l('Pendentes de aprovação', s.pendentes, true) +
                        l('Freelancers', s.barbeiros) +
                        l('Proprietários', s.barbearias) +
                        l('Clientes', s.clientes) +
                        (s.pagamentos_pendentes == null ? '' : l('Pagamentos pendentes', s.pagamentos_pendentes, true));
                } catch (err) {
                    if (err.message === 'sessao') return;
                    sessaoExpirada();
                }
            };

            // ---------------------------------------------------------------
            // Busca dentro de uma seção (nome / e-mail / barbearia)
            // ---------------------------------------------------------------
            let buscaTimer = null;
            function buscaSecao(tipo, input) {
                clearTimeout(buscaTimer);
                const q = input.value.trim();
                const menu = document.getElementById('menuSecao');
                const res = document.getElementById('resultadoBusca');
                if (q.length < 2) {
                    menu.style.display = '';
                    res.innerHTML = '';
                    return;
                }
                buscaTimer = setTimeout(async () => {
                    menu.style.display = 'none';
                    res.innerHTML = '<div class="carregando">Buscando...</div>';
                    try {
                        const lista = await api(`/lista?tipo=${tipo}&situacao=todos&q=${encodeURIComponent(q)}`);
                        res.innerHTML = lista.length
                            ? `<div class="rows">${lista.map(itemPessoa).join('')}</div>`
                            : '<div class="vazio">Nenhum resultado.</div>';
                    } catch (err) { res.innerHTML = erroHtml(err); }
                }, 300);
            }

            function campoBusca(tipo, placeholder) {
                return `<input class="busca" type="search" placeholder="🔎 ${placeholder}" oninput="buscaSecao('${tipo}', this)">
                        <div id="resultadoBusca"></div>`;
            }

            // ---------------------------------------------------------------
            // 2. Freelancers
            // ---------------------------------------------------------------
            VIEWS.freelancers = async () => {
                app.innerHTML = topo('👤 FREELANCERS') + campoBusca('barbeiro', 'Buscar por nome ou e-mail') + `
                    <div class="rows" id="menuSecao">
                        ${linha('🆕', 'NOVOS FREELANCERS', 'Pendentes de análise', "ir('lista', {tipo:'barbeiro', situacao:'pendente'})", '<span id="qtdNovos"></span>')}
                        ${linha('👤', 'FREELANCERS CADASTRADOS', 'Freelancers aprovados', "ir('lista', {tipo:'barbeiro', situacao:'aprovado'})")}
                        ${linha('💬', 'AVALIAÇÕES / RECLAMAÇÕES', '', "ir('avaliacoesMenu', {alvo:'freelancer'})")}
                        ${linha('💰', 'PAGAMENTOS', '', "ir('pagamentos')")}
                    </div>`;
                try {
                    const pend = await api('/lista?tipo=barbeiro&situacao=pendente');
                    const el = document.getElementById('qtdNovos');
                    if (el) {
                        if (pend.length) el.textContent = pend.length;
                        else el.parentElement.remove();
                    }
                } catch (_) {}
            };

            // ---------------------------------------------------------------
            // Listas (novos / cadastrados / proprietários / clientes)
            // ---------------------------------------------------------------
            function itemPessoa(u) {
                const verPerfil = `<div class="acoes"><button class="btn btn-laranja" onclick="ir('perfil', {id:${u.id}})">VER PERFIL</button></div>`;
                const status = u.aprovado
                    ? '<p class="status-ok">🟢 Aprovado</p>'
                    : '<p class="status-pendente">🟠 Pendente de análise</p>';

                if (u.tipo === 'barbeiro') {
                    const exp = u.tempo_experiencia ? `🕒 ${esc(u.tempo_experiencia)} de profissão` : '🕒 Tempo de profissão não informado';
                    const fotos = u.aprovado ? '' : `<p>📷 ${u.qtd_fotos} foto${u.qtd_fotos === 1 ? '' : 's'} dos trabalhos</p>`;
                    const cadastro = u.aprovado ? '' : `<p>📅 Cadastro: ${dataBR(u.criado_em)}</p>`;
                    const statusFreelancer = u.aprovado ? status : '<p class="status-pendente">🟠 EM ANÁLISE</p>';
                    return `<div class="item"><h3>${esc(u.nome)}</h3><p>📧 ${esc(u.email)}</p><p>${exp}</p>${fotos}${cadastro}${statusFreelancer}${verPerfil}</div>`;
                }
                if (u.tipo === 'barbearia') {
                    const b = u.barbearia;
                    const nome = b && b.nome ? b.nome : u.nome;
                    const cadeiras = b ? `<p>🪑 ${b.cadeiras} cadeira${b.cadeiras === 1 ? '' : 's'} cadastrada${b.cadeiras === 1 ? '' : 's'}</p>` : '';
                    return `<div class="item"><h3>${esc(nome)}</h3><p>Proprietário: ${esc(u.nome)}</p>${cadeiras}${u.aprovado ? '' : status}${verPerfil}</div>`;
                }
                return `<div class="item"><h3>${esc(u.nome)}</h3><p>📧 ${esc(u.email)}</p><p>📅 Cadastro: ${dataBR(u.criado_em)}</p>${u.aprovado ? '' : status}${verPerfil}</div>`;
            }

            const TITULOS_LISTA = {
                'barbeiro:pendente': ['🆕 NOVOS FREELANCERS', n => `${n} pendente${n === 1 ? '' : 's'} de análise`, 'Nenhum freelancer aguardando análise.'],
                'barbeiro:aprovado': ['👤 FREELANCERS CADASTRADOS', n => `${n} freelancer${n === 1 ? '' : 's'} aprovado${n === 1 ? '' : 's'}`, 'Nenhum freelancer aprovado.'],
                'barbearia:pendente': ['🆕 PROPRIETÁRIOS PENDENTES', n => `${n} pendente${n === 1 ? '' : 's'} de análise`, 'Nenhum proprietário pendente.'],
                'barbearia:aprovado': ['🏪 PROPRIETÁRIOS CADASTRADOS', n => `${n} proprietário${n === 1 ? '' : 's'}`, 'Nenhum proprietário cadastrado.'],
                'cliente:pendente': ['🆕 CLIENTES PENDENTES', n => `${n} pendente${n === 1 ? '' : 's'}`, 'Nenhum cliente pendente.'],
                'cliente:todos': ['👤 CLIENTES CADASTRADOS', n => `${n} cliente${n === 1 ? '' : 's'}`, 'Nenhum cliente cadastrado.'],
            };

            const BUSCA_LISTA = { barbeiro: 'Buscar por nome ou e-mail', barbearia: 'Buscar por nome, e-mail ou barbearia', cliente: 'Buscar por nome ou e-mail' };

            VIEWS.lista = async (p) => {
                const [titulo, contagem, vazio] = TITULOS_LISTA[`${p.tipo}:${p.situacao}`] || ['LISTA', n => `${n}`, 'Nada aqui.'];
                const comBusca = p.situacao !== 'pendente';
                app.innerHTML = topo(titulo, 'Carregando...') +
                    (comBusca ? `<input class="busca" type="search" placeholder="🔎 ${BUSCA_LISTA[p.tipo]}" oninput="filtrarLista(this.value)">` : '') +
                    '<div class="rows" id="lista"></div>';

                async function carregar(q) {
                    const box = document.getElementById('lista');
                    try {
                        const itens = await api(`/lista?tipo=${p.tipo}&situacao=${p.situacao}&q=${encodeURIComponent(q || '')}`);
                        if (!q) document.getElementById('tituloSub').textContent = contagem(itens.length);
                        box.innerHTML = itens.length ? itens.map(itemPessoa).join('') : `<div class="vazio">${q ? 'Nenhum resultado.' : vazio}</div>`;
                    } catch (err) { box.innerHTML = erroHtml(err); }
                }
                window.filtrarLista = (q) => {
                    clearTimeout(buscaTimer);
                    buscaTimer = setTimeout(() => carregar(q.trim()), 300);
                };
                carregar('');
            };

            // ---------------------------------------------------------------
            // Perfil (freelancer / proprietário / cliente)
            // ---------------------------------------------------------------
            const galerias = {};

            function campo(rotulo, valor) {
                return `<div class="campo"><div class="rotulo">${rotulo}</div><div class="valor">${valor}</div></div>`;
            }

            function blocoFotos(titulo, chave, itens, faltando) {
                if ((!itens || !itens.length) && (!faltando || !faltando.length)) return '';
                galerias[chave] = itens;
                const thumbs = itens.map((it, i) => {
                    const cap = it.descricao ? `<span class="thumb-cap">${esc(it.descricao)}</span>` : '';
                    return `<button class="thumb" onclick="abrirLightbox('${chave}', ${i})"><img src="${esc(it.url)}" alt="${esc(it.descricao || 'Foto')}" loading="lazy">${cap}</button>`;
                }).join('');
                const vazios = (faltando || []).map(l => `<div class="thumb faltando">❌ ${esc(l)}</div>`).join('');
                return `<div class="secao"><div class="secao-titulo">${titulo}</div><div class="thumb-grid">${thumbs}${vazios}</div></div>`;
            }

            function blocoDocumentos(u) {
                const mapa = [['Frente', u.documento_frente], ['Verso', u.documento_verso], ['Selfie', u.selfie]];
                const itens = [], faltando = [];
                mapa.forEach(([rotulo, url]) => { if (url) itens.push({ url, descricao: rotulo }); else faltando.push(rotulo); });
                if (!itens.length) return '';
                return blocoFotos('📄 DOCUMENTOS', 'doc-' + u.id, itens, faltando);
            }

            const STATUS_FATURA = { pago: ['🟢 Pago', 'status-ok'], pendente: ['🟠 Pendente', 'status-pendente'], vencido: ['🔴 Vencido', 'status-ruim'], cancelado: ['⚪ Cancelado', ''] };

            function blocoPagamentosBarbearia(b) {
                if (!b.assinatura && !b.faturas.length) {
                    return `<div class="secao"><div class="secao-titulo">💳 PAGAMENTOS</div><div class="item"><p>Nenhum pagamento registrado ainda.</p></div></div>`;
                }
                const a = b.assinatura;
                const resumo = a ? `
                    <p>Mensalidade: <b style="color:#fff">${dinheiro(a.valor_mensalidade)}</b> · ${a.quantidade_cadeiras} cadeira${a.quantidade_cadeiras === 1 ? '' : 's'}</p>
                    <p>Situação: ${esc(a.status)}${a.proximo_vencimento ? ` · Próximo vencimento: ${dataBR(a.proximo_vencimento)}` : ''}</p>` : '';
                const faturas = b.faturas.length ? b.faturas.map(f => {
                    const [rot, cls] = STATUS_FATURA[f.status] || [esc(f.status), ''];
                    return `<div class="campo"><div class="valor">${esc(f.mes_referencia)} — ${dinheiro(f.valor)}</div>
                        <div class="rotulo" style="font-weight:600;letter-spacing:0">Vence ${dataBR(f.data_vencimento)}${f.data_pagamento ? ` · Pago em ${dataBR(f.data_pagamento)}` : ''} · <span class="${cls}">${rot}</span></div></div>`;
                }).join('') : '<p style="padding:10px 0">Sem histórico de faturas.</p>';
                return `
                    <div class="secao"><div class="secao-titulo">💳 PAGAMENTOS</div>
                        <div class="item">${resumo}
                            <div class="acoes"><button class="btn btn-neutro" onclick="const d=document.getElementById('faturas'); d.hidden=!d.hidden">VER DETALHES</button></div>
                            <div id="faturas" hidden style="margin-top:8px">${faturas}</div>
                        </div>
                    </div>`;
            }

            VIEWS.perfil = async (p) => {
                app.innerHTML = topo('PERFIL') + '<div class="carregando">Carregando...</div>';
                let u;
                try { u = await api(`/usuario/${p.id}`); }
                catch (err) { app.innerHTML = topo('PERFIL') + erroHtml(err); return; }

                const pendente = !u.aprovado;
                const contato = campo('E-MAIL', esc(u.email)) + campo('TELEFONE', esc(u.telefone || 'Sem telefone'));
                const decisao = pendente ? `
                    <div class="decisao">
                        <button class="btn btn-verde" onclick="aprovar(${u.id})">APROVAR</button>
                        <button class="btn btn-vermelho" onclick="rejeitar(${u.id})">RECUSAR</button>
                    </div>` : '';
                let corpo = '';

                if (u.tipo === 'barbeiro') {
                    const status = pendente
                        ? '<span class="status-pendente">🟠 EM ANÁLISE</span>'
                        : '<span class="status-ok">🟢 FREELANCER CADASTRADO</span>';
                    const fotos = (u.portfolio || []).filter(f => f && f.url);
                    corpo = `
                        <div class="ficha">
                            ${campo('NOME', esc(u.nome))}
                            ${campo('TEMPO DE PROFISSÃO', u.tempo_experiencia ? '🕒 ' + esc(u.tempo_experiencia) : 'Não informado')}
                            ${campo('STATUS', status)}
                            ${contato}
                            ${campo('CADASTRO', dataBR(u.criado_em))}
                        </div>
                        ${fotos.length ? blocoFotos(`📷 FOTOS DOS TRABALHOS (${fotos.length})`, 'pf-' + u.id, fotos, []) : '<div class="secao"><div class="secao-titulo">📷 FOTOS DOS TRABALHOS</div><div class="item"><p>Nenhuma foto enviada.</p></div></div>'}
                        ${blocoDocumentos(u)}
                        ${decisao}`;
                } else if (u.tipo === 'barbearia') {
                    const b = u.barbearia;
                    corpo = `
                        <div class="ficha">
                            ${campo('BARBEARIA', esc(b && b.nome ? b.nome : '—'))}
                            ${campo('PROPRIETÁRIO', esc(u.nome))}
                            ${b ? campo('CADEIRAS', `🪑 ${b.cadeiras} cadeira${b.cadeiras === 1 ? '' : 's'} cadastrada${b.cadeiras === 1 ? '' : 's'}`) : ''}
                            ${campo('DATA DA CONTRATAÇÃO', b && b.data_contratacao ? dataBR(b.data_contratacao) : '—')}
                            ${pendente ? campo('STATUS', '<span class="status-pendente">🟠 PENDENTE DE ANÁLISE</span>') : ''}
                            ${b && b.endereco ? campo('ENDEREÇO', esc(b.endereco)) : ''}
                            ${contato}
                            ${campo('CADASTRO', dataBR(u.criado_em))}
                        </div>
                        ${b ? blocoPagamentosBarbearia(b) : ''}
                        ${blocoDocumentos(u)}
                        ${decisao}`;
                } else {
                    corpo = `
                        <div class="ficha">
                            ${campo('NOME', esc(u.nome))}
                            ${contato}
                            ${campo('CADASTRO', dataBR(u.criado_em))}
                            ${pendente ? campo('STATUS', '<span class="status-pendente">🟠 PENDENTE</span>') : ''}
                        </div>
                        ${decisao}`;
                }
                app.innerHTML = topo(u.tipo === 'barbearia' ? 'PROPRIETÁRIO' : u.tipo === 'barbeiro' ? 'FREELANCER' : 'CLIENTE') + corpo;
            };

            async function aprovar(usuarioId) {
                if (!confirm('Confirmar aprovação?')) return;
                try {
                    await api(`/aprovar/${usuarioId}`, { method: 'POST' });
                    alert('✅ Aprovado!');
                    voltar();
                } catch (err) {
                    if (err.message !== 'sessao') alert('❌ Erro ao aprovar: ' + err.message);
                }
            }

            async function rejeitar(usuarioId) {
                if (!confirm('Confirmar recusa?')) return;
                try {
                    await api(`/rejeitar/${usuarioId}`, { method: 'POST' });
                    alert('❌ Cadastro recusado.');
                    voltar();
                } catch (err) {
                    if (err.message !== 'sessao') alert('❌ Erro ao recusar: ' + err.message);
                }
            }

            // ---------------------------------------------------------------
            // Avaliações / Reclamações
            // ---------------------------------------------------------------
            VIEWS.avaliacoesMenu = (p) => {
                if (p.alvo === 'freelancer') {
                    app.innerHTML = topo('💬 AVALIAÇÕES / RECLAMAÇÕES', 'Freelancers') + `<div class="rows">
                        ${linha('⭐', 'Comentários dos clientes', 'Sobre freelancers', "ir('avaliacoes', {alvo:'freelancer', avaliador:'cliente'})")}
                        ${linha('⭐', 'Comentários dos proprietários', 'Sobre freelancers', "ir('avaliacoes', {alvo:'freelancer', avaliador:'barbearia'})")}
                        ${linha('⚠️', 'Reclamações', 'Relacionadas aos freelancers', "ir('reclamacoes', {alvo:'freelancer', avaliador:'todos', status:'pendente'})")}
                    </div>`;
                } else {
                    app.innerHTML = topo('💬 AVALIAÇÕES / RECLAMAÇÕES', 'Proprietários') + `<div class="rows">
                        ${linha('⭐', 'Comentários dos clientes', 'Sobre proprietários', "ir('avaliacoes', {alvo:'barbearia', avaliador:'cliente'})")}
                        ${linha('⭐', 'Comentários dos freelancers', 'Sobre proprietários', "ir('avaliacoes', {alvo:'barbearia', avaliador:'freelancer'})")}
                        ${linha('⚠️', 'Reclamações', 'Relacionadas aos proprietários', "ir('reclamacoes', {alvo:'barbearia', avaliador:'todos', status:'pendente'})")}
                    </div>`;
                }
            };

            function itemAvaliacao(a, comAcao) {
                const status = a.status === 'resolvida'
                    ? '<p class="status-ok">🟢 Resolvida</p>'
                    : '<p class="status-ruim">🔴 Pendente</p>';
                const acao = comAcao && a.status !== 'resolvida'
                    ? `<div class="acoes"><button class="btn btn-verde" onclick="resolverReclamacao('${a.alvo}', ${a.id})">MARCAR COMO RESOLVIDA</button></div>` : '';
                return `
                    <div class="item">
                        <h3>${esc(a.avaliador_nome || '—')} <span style="color:var(--cinza);font-weight:600;font-size:12px">(${QUEM_AVALIOU[a.tipo_avaliador] || esc(a.tipo_avaliador)})</span></h3>
                        <p>Sobre: <b style="color:#fff">${esc(a.sobre_nome)}</b></p>
                        <p>📅 ${dataBR(a.criado_em)} · <span class="estrelas">${estrelas(a.nota)}</span></p>
                        <p class="texto">${a.comentario ? esc(a.comentario) : '<i style="color:var(--cinza)">(sem comentário)</i>'}</p>
                        ${comAcao ? status : ''}
                        ${acao}
                    </div>`;
            }

            const TITULO_AVALIACOES = {
                'freelancer:cliente': ['⭐ CLIENTES SOBRE FREELANCERS'],
                'freelancer:barbearia': ['⭐ PROPRIETÁRIOS SOBRE FREELANCERS'],
                'barbearia:cliente': ['⭐ CLIENTES SOBRE PROPRIETÁRIOS'],
                'barbearia:freelancer': ['⭐ FREELANCERS SOBRE PROPRIETÁRIOS'],
                'todos:cliente': ['⭐ COMENTÁRIOS DOS CLIENTES'],
            };

            VIEWS.avaliacoes = async (p) => {
                const [titulo] = TITULO_AVALIACOES[`${p.alvo}:${p.avaliador}`] || ['⭐ COMENTÁRIOS'];
                app.innerHTML = topo(titulo) + '<div class="rows" id="lista"><div class="carregando">Carregando...</div></div>';
                const box = document.getElementById('lista');
                try {
                    const itens = await api(`/avaliacoes?alvo=${p.alvo}&avaliador=${p.avaliador}`);
                    document.getElementById('tituloSub').textContent = `${itens.length} comentário${itens.length === 1 ? '' : 's'}`;
                    box.innerHTML = itens.length ? itens.map(a => itemAvaliacao(a, false)).join('') : '<div class="vazio">Nenhum comentário ainda.</div>';
                } catch (err) { box.innerHTML = erroHtml(err); }
            };

            const TITULO_RECLAMACOES = {
                freelancer: '⚠️ RECLAMAÇÕES — FREELANCERS',
                barbearia: '⚠️ RECLAMAÇÕES — PROPRIETÁRIOS',
                todos: '💬 RECLAMAÇÕES DOS CLIENTES',
            };

            VIEWS.reclamacoes = async (p) => {
                const status = p.status || 'pendente';
                const trocar = (s) => `history.replaceState({view:'reclamacoes', params:{alvo:'${p.alvo}', avaliador:'${p.avaliador}', status:'${s}'}}, ''); render('reclamacoes', history.state.params)`;
                app.innerHTML = topo(TITULO_RECLAMACOES[p.alvo] || '⚠️ RECLAMAÇÕES', 'Avaliações de 1 ou 2 estrelas') + `
                    <div class="segmento">
                        <button class="${status === 'pendente' ? 'ativo' : ''}" onclick="${trocar('pendente')}">🔴 Pendentes</button>
                        <button class="${status === 'resolvida' ? 'ativo' : ''}" onclick="${trocar('resolvida')}">🟢 Resolvidas</button>
                    </div>
                    <div class="rows" id="lista"><div class="carregando">Carregando...</div></div>`;
                const box = document.getElementById('lista');
                try {
                    const itens = await api(`/avaliacoes?alvo=${p.alvo}&avaliador=${p.avaliador}&reclamacoes=true&status_reclamacao=${status}`);
                    box.innerHTML = itens.length
                        ? itens.map(a => itemAvaliacao(a, true)).join('')
                        : `<div class="vazio">${status === 'pendente' ? 'Nenhuma reclamação pendente.' : 'Nenhuma reclamação resolvida.'}</div>`;
                } catch (err) { box.innerHTML = erroHtml(err); }
            };

            async function resolverReclamacao(alvo, id) {
                if (!confirm('Marcar esta reclamação como resolvida?')) return;
                try {
                    await api(`/avaliacoes/${alvo}/${id}/resolver`, { method: 'POST' });
                    render('reclamacoes', history.state.params);
                } catch (err) {
                    if (err.message !== 'sessao') alert('❌ ' + err.message);
                }
            }

            // ---------------------------------------------------------------
            // Pagamentos de freelancers
            // ---------------------------------------------------------------
            VIEWS.pagamentos = async () => {
                app.innerHTML = topo('💰 PAGAMENTOS DE FREELANCERS') + `<div class="rows">
                    ${linha('🔴', 'PAGAMENTOS PENDENTES', '', "ir('pagamentosLista', {status:'pendentes'})", '<span id="qtdPag"></span>')}
                    ${linha('🟢', 'PAGAMENTOS CONFIRMADOS', '', "ir('pagamentosLista', {status:'confirmados'})")}
                </div>`;
                try {
                    const lista = await api('/pagamentos-diarios');
                    const el = document.getElementById('qtdPag');
                    if (el) {
                        if (lista.length) el.textContent = lista.length;
                        else el.parentElement.remove();
                    }
                } catch (_) {
                    const el = document.getElementById('qtdPag');
                    if (el) el.parentElement.remove();
                }
            };

            const STATUS_PAG = {
                aguardando_confirmacao: ['⏳ Aguardando confirmação', 'var(--amarelo)'],
                recusado: ['❌ Não confirmado', 'var(--vermelho)'],
                pendente: ['• Não pago', 'var(--cinza)'],
                confirmado: ['✅ Confirmado', 'var(--verde)'],
            };

            VIEWS.pagamentosLista = async (p) => {
                const confirmados = p.status === 'confirmados';
                app.innerHTML = topo(confirmados ? '🟢 PAGAMENTOS CONFIRMADOS' : '🔴 PAGAMENTOS PENDENTES') +
                    '<div class="rows" id="lista"><div class="carregando">Carregando...</div></div>';
                const box = document.getElementById('lista');
                try {
                    const lista = await api(confirmados ? '/pagamentos-diarios/confirmados' : '/pagamentos-diarios');
                    document.getElementById('tituloSub').textContent = `${lista.length} pagamento${lista.length === 1 ? '' : 's'}`;
                    if (!lista.length) {
                        box.innerHTML = `<div class="vazio">${confirmados ? 'Nenhum pagamento confirmado ainda.' : 'Nenhum pagamento pendente!'}</div>`;
                        return;
                    }
                    box.innerHTML = lista.map(f => {
                        const [rotulo, cor] = STATUS_PAG[f.status] || [f.status, 'var(--cinza)'];
                        const botoes = confirmados ? '' : `
                            <div class="acoes" style="flex-direction:column">
                                <button class="btn btn-verde btn-largo" onclick="decidirPagamento(${f.id}, true)">SIM — PAGAMENTO CONFIRMADO</button>
                                ${f.status !== 'recusado' ? `<button class="btn btn-vermelho btn-largo" onclick="decidirPagamento(${f.id}, false)">NÃO — PAGAMENTO NÃO CONFIRMADO</button>` : ''}
                            </div>`;
                        return `
                            <div class="item">
                                <h3>${esc(f.freelancer_nome || ('#' + f.freelancer_id))}</h3>
                                <p>💵 Valor: <b style="color:#fff">${dinheiro(f.valor_devido)}</b></p>
                                <p>📅 Data: ${dataBR(f.data_referencia)}</p>
                                <p style="color:${cor};font-weight:800">${rotulo}${f.bloqueado ? ' · 🔒 Bloqueado (OFFLINE)' : ''}</p>
                                ${confirmados && f.decidido_em ? `<p>Confirmado em ${dataBR(f.decidido_em)}</p>` : ''}
                                ${botoes}
                            </div>`;
                    }).join('');
                } catch (err) { box.innerHTML = erroHtml(err); }
            };

            async function decidirPagamento(id, confirmado) {
                const msg = confirmado
                    ? 'Confirmar o recebimento deste pagamento? O freelancer volta a poder escolher o status.'
                    : 'Marcar como NÃO confirmado? O freelancer continua bloqueado (OFFLINE).';
                if (!confirm(msg)) return;
                try {
                    const data = await api(`/pagamentos-diarios/${id}/${confirmado ? 'confirmar' : 'recusar'}`, { method: 'POST' });
                    if (confirmado) {
                        alert(data.freelancer_bloqueado
                            ? '✅ Pagamento confirmado. O freelancer ainda tem outro pagamento em aberto.'
                            : '✅ Pagamento confirmado. Freelancer liberado.');
                    } else {
                        alert('❌ Pagamento marcado como não confirmado.');
                    }
                } catch (err) {
                    if (err.message !== 'sessao') alert('❌ ' + (err.message || 'Erro ao registrar decisão'));
                }
                render('pagamentosLista', { status: 'pendentes' });
            }

            // ---------------------------------------------------------------
            // Proprietários
            // ---------------------------------------------------------------
            VIEWS.proprietarios = async () => {
                app.innerHTML = topo('🏪 PROPRIETÁRIOS') + campoBusca('barbearia', 'Buscar por nome, e-mail ou barbearia') + `
                    <div class="rows" id="menuSecao">
                        <span id="linhaPendentesProp"></span>
                        ${linha('🏪', 'PROPRIETÁRIOS CADASTRADOS', '', "ir('lista', {tipo:'barbearia', situacao:'aprovado'})")}
                        ${linha('💳', 'CADEIRAS / PAGAMENTOS', '', "ir('cadeiras')")}
                        ${linha('💬', 'AVALIAÇÕES / RECLAMAÇÕES', '', "ir('avaliacoesMenu', {alvo:'barbearia'})")}
                    </div>`;
                // Fluxo de pendentes só aparece se existir alguém aguardando análise.
                try {
                    const pend = await api('/lista?tipo=barbearia&situacao=pendente');
                    const el = document.getElementById('linhaPendentesProp');
                    if (el && pend.length) {
                        el.outerHTML = linha('🆕', 'NOVOS PROPRIETÁRIOS', 'Pendentes de análise', "ir('lista', {tipo:'barbearia', situacao:'pendente'})", pend.length);
                    }
                } catch (_) {}
            };

            VIEWS.cadeiras = async () => {
                app.innerHTML = topo('💳 CADEIRAS / PAGAMENTOS') + '<div class="rows" id="lista"><div class="carregando">Carregando...</div></div>';
                const box = document.getElementById('lista');
                try {
                    const itens = await api('/lista?tipo=barbearia&situacao=todos');
                    document.getElementById('tituloSub').textContent = `${itens.length} proprietário${itens.length === 1 ? '' : 's'}`;
                    box.innerHTML = itens.length ? itens.map(u => {
                        const b = u.barbearia || { cadeiras: 0 };
                        const a = b.assinatura;
                        return `
                            <div class="item">
                                <h3>${esc(b.nome || u.nome)}</h3>
                                <p>Proprietário: ${esc(u.nome)}</p>
                                <p>🪑 ${b.cadeiras} cadeira${b.cadeiras === 1 ? '' : 's'} cadastrada${b.cadeiras === 1 ? '' : 's'}</p>
                                <p>${a ? `💳 Mensalidade ${dinheiro(a.valor_mensalidade)} · ${esc(a.status)}` : '💳 Sem pagamentos registrados'}</p>
                                <div class="acoes"><button class="btn btn-laranja" onclick="ir('perfil', {id:${u.id}})">VER DETALHES</button></div>
                            </div>`;
                    }).join('') : '<div class="vazio">Nenhum proprietário cadastrado.</div>';
                } catch (err) { box.innerHTML = erroHtml(err); }
            };

            // ---------------------------------------------------------------
            // Clientes
            // ---------------------------------------------------------------
            VIEWS.clientes = async () => {
                app.innerHTML = topo('👥 CLIENTES') + campoBusca('cliente', 'Buscar por nome ou e-mail') + `
                    <div class="rows" id="menuSecao">
                        <span id="linhaPendentesCli"></span>
                        ${linha('👤', 'CLIENTES CADASTRADOS', '', "ir('lista', {tipo:'cliente', situacao:'todos'})")}
                        ${linha('💬', 'RECLAMAÇÕES / COMENTÁRIOS', '', "ir('clientesReclamacoes')")}
                    </div>`;
                try {
                    const pend = await api('/lista?tipo=cliente&situacao=pendente');
                    const el = document.getElementById('linhaPendentesCli');
                    if (el && pend.length) {
                        el.outerHTML = linha('🆕', 'CLIENTES PENDENTES', 'Aguardando aprovação', "ir('lista', {tipo:'cliente', situacao:'pendente'})", pend.length);
                    }
                } catch (_) {}
            };

            VIEWS.clientesReclamacoes = () => {
                app.innerHTML = topo('💬 RECLAMAÇÕES / COMENTÁRIOS', 'Enviados pelos clientes') + `<div class="rows">
                    ${linha('🔴', 'Pendentes', 'Reclamações ainda não resolvidas', "ir('reclamacoes', {alvo:'todos', avaliador:'cliente', status:'pendente'})")}
                    ${linha('🟢', 'Resolvidas', 'Reclamações já resolvidas', "ir('reclamacoes', {alvo:'todos', avaliador:'cliente', status:'resolvida'})")}
                    ${linha('⭐', 'Comentários', 'Todos os comentários dos clientes', "ir('avaliacoes', {alvo:'todos', avaliador:'cliente'})")}
                </div>`;
            };

            // ---------------------------------------------------------------
            // Lightbox
            // ---------------------------------------------------------------
            let lbChave = null, lbIdx = 0;

            function abrirLightbox(chave, idx) {
                const g = galerias[chave];
                if (!g || !g.length) return;
                lbChave = chave;
                lbIdx = idx;
                renderLightbox();
                document.getElementById('lightbox').classList.add('aberto');
            }

            function renderLightbox() {
                const g = galerias[lbChave];
                if (!g) return;
                const item = g[lbIdx];
                document.getElementById('lightboxImg').src = item.url;
                document.getElementById('lightboxInfo').textContent =
                    `${lbIdx + 1} / ${g.length}` + (item.descricao ? ` — ${item.descricao}` : '');
                const solo = g.length <= 1;
                document.getElementById('lbPrev').hidden = solo;
                document.getElementById('lbNext').hidden = solo;
            }

            function navLightbox(delta) {
                const g = galerias[lbChave];
                if (!g || g.length <= 1) return;
                lbIdx = (lbIdx + delta + g.length) % g.length;
                renderLightbox();
            }

            function fecharLightbox() {
                document.getElementById('lightbox').classList.remove('aberto');
                document.getElementById('lightboxImg').src = '';
                lbChave = null;
            }

            document.addEventListener('keydown', e => {
                if (!document.getElementById('lightbox').classList.contains('aberto')) return;
                if (e.key === 'Escape') fecharLightbox();
                else if (e.key === 'ArrowLeft') navLightbox(-1);
                else if (e.key === 'ArrowRight') navLightbox(1);
            });

            (function () {
                let x0 = null;
                const lb = document.getElementById('lightbox');
                lb.addEventListener('touchstart', e => { x0 = e.changedTouches[0].clientX; }, { passive: true });
                lb.addEventListener('touchend', e => {
                    if (x0 === null) return;
                    const dx = e.changedTouches[0].clientX - x0;
                    if (Math.abs(dx) > 45) navLightbox(dx < 0 ? 1 : -1);
                    x0 = null;
                }, { passive: true });
            })();

            // ---------------------------------------------------------------
            // Início
            // ---------------------------------------------------------------
            if (!token) {
                mostrarLogin();
            } else {
                history.replaceState({ view: 'home', params: {} }, '');
                render('home', {});
                // Só o resumo da tela principal se atualiza sozinho (as outras telas não perdem a rolagem).
                setInterval(() => { if (viewAtual === 'home' && token) render('home', {}); }, 30000);
            }
        </script>
    </body>
    </html>
"""
