"""
Rotas para corrigir problemas identificados:
1. Verificação de email not being marked
2. Acionar cadeira (chair available button)
3. Profile photo issue
4. Cross-evaluation system
"""

from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Request
from sqlalchemy.orm import Session
from sqlalchemy import and_
from typing import List
from datetime import datetime

from . import models, schemas
from .database import get_db
from .routes import get_current_user, oauth2_scheme
import os
import uuid

router = APIRouter(tags=["Fixes"])


def _buscar_assinatura_barbearia(db: Session, barbearia_id: int):
    assinatura_nova = db.query(models.AssinaturaBarbearia).filter(
        models.AssinaturaBarbearia.barbearia_id == barbearia_id
    ).first()
    if assinatura_nova:
        return assinatura_nova

    return db.query(models.Assinatura).filter(
        models.Assinatura.barbearia_id == barbearia_id
    ).first()


def _assinatura_ativa_limite(assinatura):
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

# ==================== 1. EMAIL VERIFICATION FIX ====================

@router.post("/usuarios/verificar-email-confirmado")
def verificar_email_confirmado(db: Session = Depends(get_db), usuario = Depends(get_current_user)):
    """
    Verifica se o email foi confirmado via link e retorna status atualizado
    """
    usuario = db.query(models.Usuario).filter(models.Usuario.id == usuario.id).first()
    
    if not usuario:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")
    
    return {
        "email_verificado": usuario.email_verificado,
        "documento_verificado": usuario.documento_verificado,
        "id": usuario.id,
        "email": usuario.email,
        "nome": usuario.nome,
        "tipo": usuario.tipo
    }

@router.get("/usuarios/perfil-completo")
def get_perfil_completo(db: Session = Depends(get_db), usuario = Depends(get_current_user)):
    """
    Retorna o perfil completo do usuário com todos os dados atualizados
    """
    usuario = db.query(models.Usuario).filter(models.Usuario.id == usuario.id).first()
    
    if not usuario:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")
    
    barbearia_atual_nome = None
    if usuario.barbearia_atual_id:
        barbearia_atual = db.query(models.Barbearia).filter(
            models.Barbearia.id == usuario.barbearia_atual_id
        ).first()
        if barbearia_atual:
            barbearia_atual_nome = barbearia_atual.nome

    return {
        "id": usuario.id,
        "email": usuario.email,
        "nome": usuario.nome,
        "tipo": usuario.tipo,
        "telefone": usuario.telefone,
        "endereco": usuario.endereco,
        "latitude": usuario.latitude,
        "longitude": usuario.longitude,
        "foto_perfil": usuario.foto_perfil,
        "cpf": usuario.cpf,
        "cnpj": usuario.cnpj,
        "email_verificado": usuario.email_verificado,
        "documento_verificado": usuario.documento_verificado,
        "perfil_aprovado": usuario.perfil_aprovado,
        "disponivel": usuario.disponivel,
        "online_regiao": usuario.online_regiao,
        "presente_em_local": usuario.presente_em_local,
        "barbearia_atual_id": usuario.barbearia_atual_id,
        "barbearia_atual_nome": barbearia_atual_nome,
        "pode_receber_chamado_agora": bool(usuario.presente_em_local and usuario.barbearia_atual_id),
        "criado_em": usuario.criado_em
    }

@router.post("/upload/imagem")
def upload_imagem(
    request: Request,
    file: UploadFile = File(...),
    pasta: str = "geral",
    usuario = Depends(get_current_user)
):
    """Recebe uma imagem e salva em /uploads, retornando a URL pública."""
    conteudos_validos = {"image/jpeg", "image/png", "image/webp"}
    if file.content_type not in conteudos_validos:
        raise HTTPException(status_code=400, detail="Apenas imagens JPEG, PNG ou WEBP")

    ext = os.path.splitext(file.filename or "")[1].lower()
    if ext not in [".jpg", ".jpeg", ".png", ".webp"]:
        ext = ".jpg"

    pasta_segura = "perfil" if pasta == "perfil" else "portfolio"
    dest_dir = os.path.join("uploads", pasta_segura)
    os.makedirs(dest_dir, exist_ok=True)

    nome_arquivo = f"{uuid.uuid4().hex}{ext}"
    caminho = os.path.join(dest_dir, nome_arquivo)

    with open(caminho, "wb") as out:
        out.write(file.file.read())

    path_publica = f"/uploads/{pasta_segura}/{nome_arquivo}"
    base = str(request.base_url).rstrip("/")
    url_publica = f"{base}{path_publica}"
    return {"url": url_publica, "path": path_publica}

@router.post("/usuarios/foto-perfil")
def atualizar_foto_perfil(
    payload: dict,
    db: Session = Depends(get_db),
    usuario = Depends(get_current_user)
):
    """Atualiza a foto de perfil do usuário atual (URL)."""
    url = payload.get("url")
    if not url:
        raise HTTPException(status_code=400, detail="URL da foto é obrigatória")
    u = db.query(models.Usuario).filter(models.Usuario.id == usuario.id).first()
    if not u:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")
    u.foto_perfil = url
    db.commit()
    db.refresh(u)
    return {"message": "Foto atualizada", "foto_perfil": u.foto_perfil}


@router.patch("/usuarios/me")
def atualizar_perfil_usuario(
    payload: dict,
    db: Session = Depends(get_db),
    usuario = Depends(get_current_user)
):
    """Atualiza dados básicos do usuário autenticado."""
    u = db.query(models.Usuario).filter(models.Usuario.id == usuario.id).first()
    if not u:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")

    novo_email = payload.get("email")
    if novo_email and novo_email != u.email:
        existente = db.query(models.Usuario).filter(models.Usuario.email == novo_email).first()
        if existente:
            raise HTTPException(status_code=400, detail="Email já está em uso")
        u.email = novo_email

    for field in ["nome", "telefone", "endereco", "cpf", "cnpj", "foto_perfil", "disponivel"]:
        if field in payload:
            setattr(u, field, payload.get(field))

    db.commit()
    db.refresh(u)
    return {
        "message": "Perfil atualizado",
        "nome": u.nome,
        "email": u.email,
        "telefone": u.telefone,
        "endereco": u.endereco,
        "cpf": u.cpf,
        "cnpj": u.cnpj,
        "foto_perfil": u.foto_perfil,
        "disponivel": u.disponivel,
    }

# ==================== 1.5. PRESENÇA - MARCAR BARBEIRO NO LOCAL ====================

@router.patch("/usuarios/me/presenca")
def marcar_presenca_barbeiro(
    payload: dict,
    db: Session = Depends(get_db),
    usuario = Depends(get_current_user)
):
    """
    Marca barbeiro/barbearia como presente/ausente no local
    Usado quando barbeiro está atendendo em uma barbearia específica
    """
    u = db.query(models.Usuario).filter(models.Usuario.id == usuario.id).first()
    if not u:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")
    
    # Apenas barbeiro e barbearia podem usar
    if u.tipo not in ["barbeiro", "barbearia"]:
        raise HTTPException(status_code=403, detail="Apenas barbeiros e barbearias podem marcar presença")
    
    # Atualizar presença
    presente = payload.get("presente_em_local", False)
    u.presente_em_local = presente
    
    # Se está marcando como presente, registrar horário de chegada
    if presente:
        from datetime import datetime
        u.horario_chegada = datetime.utcnow()
    else:
        u.horario_chegada = None
    
    db.commit()
    db.refresh(u)
    
    return {
        "message": f"Barbeiro marcado como {'presente' if presente else 'ausente'}",
        "presente_em_local": u.presente_em_local,
        "horario_chegada": u.horario_chegada.isoformat() if u.horario_chegada else None,
    }

# ==================== 2. CADEIRA - ACIONAR (Chair Available System) ====================

@router.post("/cadeiras/{cadeira_id}/acionar-simples")
def acionar_cadeira_simples(
    cadeira_id: int,
    db: Session = Depends(get_db),
    usuario = Depends(get_current_user)
):
    """
    Barbearia aciona uma cadeira como disponível
    Versão simplificada sem banco de dados de colunas
    """
    # Buscar barbearia do usuário
    barbearia = db.query(models.Barbearia).filter(
        models.Barbearia.usuario_id == usuario.id
    ).first()
    
    if not barbearia:
        raise HTTPException(
            status_code=404,
            detail="Barbearia não encontrada"
        )
    
    # Buscar cadeira
    cadeira = db.query(models.Cadeira).filter(
        models.Cadeira.id == cadeira_id,
        models.Cadeira.barbearia_id == barbearia.id
    ).first()
    
    if not cadeira:
        raise HTTPException(
            status_code=404,
            detail="Cadeira não encontrada"
        )
    
    # Validar status
    if cadeira.status != "disponivel":
        raise HTTPException(
            status_code=400,
            detail="Cadeira deve estar disponível"
        )
    
    assinatura = _buscar_assinatura_barbearia(db, barbearia.id)
    assinatura_ativa, limite_cadeiras = _assinatura_ativa_limite(assinatura)
    if not assinatura_ativa or limite_cadeiras <= 0:
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail="Assinatura inativa ou inexistente. Regularize o plano para acionar cadeiras"
        )

    cadeiras_ativas_ou_ocupadas = db.query(models.Cadeira).filter(
        models.Cadeira.barbearia_id == barbearia.id,
        models.Cadeira.id != cadeira.id,
        models.Cadeira.status == "ocupada"
    ).count()
    total_apos_acao = cadeiras_ativas_ou_ocupadas + 1
    if total_apos_acao > limite_cadeiras:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Limite do plano atingido: {limite_cadeiras} cadeira(s)."
        )

    # Marcar como ocupada (proxy para "acionada")
    cadeira.status = "ocupada"
    cadeira.acionada_em = datetime.now()
    db.commit()
    db.refresh(cadeira)
    
    return {
        "success": True,
        "message": "Cadeira marcada como disponível para barbeiros",
        "cadeira": {
            "id": cadeira.id,
            "numero": cadeira.numero,
            "status": cadeira.status,
            "barbearia_id": cadeira.barbearia_id
        }
    }

@router.post("/cadeiras/{cadeira_id}/desacionar-simples")
def desacionar_cadeira_simples(
    cadeira_id: int,
    db: Session = Depends(get_db),
    usuario = Depends(get_current_user)
):
    """
    Barbearia desaciona uma cadeira
    """
    # Buscar barbearia do usuário
    barbearia = db.query(models.Barbearia).filter(
        models.Barbearia.usuario_id == usuario.id
    ).first()
    
    if not barbearia:
        raise HTTPException(status_code=404, detail="Barbearia não encontrada")
    
    # Buscar cadeira
    cadeira = db.query(models.Cadeira).filter(
        models.Cadeira.id == cadeira_id,
        models.Cadeira.barbearia_id == barbearia.id
    ).first()
    
    if not cadeira:
        raise HTTPException(status_code=404, detail="Cadeira não encontrada")
    
    # Voltar para disponível e limpar acionamento para não contar no limite do plano
    cadeira.status = "disponivel"
    cadeira.acionada_em = None
    cadeira.chamado_id = None
    cadeira.freelancer_id = None
    db.commit()
    db.refresh(cadeira)
    
    return {
        "success": True,
        "message": "Cadeira desacionada",
        "cadeira_id": cadeira.id
    }

# ==================== 3. AVALIAÇÕES CRUZADAS ====================

@router.post("/avaliacoes/criar")
def criar_avaliacao_cruzada(
    avaliacao: schemas.AvaliacaoCreate,
    db: Session = Depends(get_db),
    usuario = Depends(get_current_user)
):
    """
    Sistema de avaliações cruzadas:
    - Cliente avalia: Barbeiro e Barbearia
    - Barbeiro avalia: Cliente e Barbearia
    - Barbearia avalia: Cliente e Barbeiro
    
    Salva em tabelas específicas (AvaliacaoFreelancer, AvaliacaoBarbearia) 
    E também na tabela genérica (Avaliacao)
    """
    # Verificar se o chamado existe
    chamado = db.query(models.Chamado).filter(
        models.Chamado.id == avaliacao.chamado_id
    ).first()
    
    if not chamado:
        raise HTTPException(status_code=404, detail="Chamado não encontrado")
    
    # Verificar permissões de avaliação
    if usuario.tipo == "cliente":
        # Cliente pode avaliar barbeiro ou barbearia (proprietário)
        if avaliacao.avaliado_id not in [chamado.barbeiro_id, chamado.barbearia.usuario_id]:
            raise HTTPException(
                status_code=403,
                detail="Cliente só pode avaliar o barbeiro ou barbearia do chamado"
            )
    elif usuario.tipo == "barbeiro":
        # Barbeiro pode avaliar cliente ou barbearia
        if avaliacao.avaliado_id not in [chamado.cliente_id, chamado.barbearia.usuario_id]:
            raise HTTPException(
                status_code=403,
                detail="Barbeiro só pode avaliar o cliente ou barbearia do chamado"
            )
    elif usuario.tipo == "barbearia":
        # Barbearia pode avaliar cliente ou barbeiro
        if avaliacao.avaliado_id not in [chamado.cliente_id, chamado.barbeiro_id]:
            raise HTTPException(
                status_code=403,
                detail="Barbearia só pode avaliar o cliente ou barbeiro do chamado"
            )
    
    # Criar avaliação genérica
    nova_avaliacao = models.Avaliacao(
        chamado_id=avaliacao.chamado_id,
        avaliador_id=usuario.id,
        avaliado_id=avaliacao.avaliado_id,
        nota=avaliacao.nota,
        comentario=avaliacao.comentario,
        criado_em=datetime.now()
    )
    
    db.add(nova_avaliacao)
    
    # Também salvar em tabelas específicas para garantir que apareça nos endpoints de retorno
    avaliado_user = db.query(models.Usuario).filter(
        models.Usuario.id == avaliacao.avaliado_id
    ).first()
    
    if avaliado_user and avaliado_user.tipo == "barbeiro":
        # Se avaliou um barbeiro, salvar em AvaliacaoFreelancer também
        freelancer = db.query(models.Freelancer).filter(
            models.Freelancer.usuario_id == avaliacao.avaliado_id
        ).first()
        
        if freelancer:
            aval_freelancer = models.AvaliacaoFreelancer(
                freelancer_id=freelancer.id,
                avaliador_id=usuario.id,
                nota=avaliacao.nota,
                comentario=avaliacao.comentario,
                data=datetime.now()
            )
            db.add(aval_freelancer)
    
    elif avaliado_user and avaliado_user.tipo == "barbearia":
        # Se avaliou uma barbearia, salvar em AvaliacaoBarbearia também
        barbearia = db.query(models.Barbearia).filter(
            models.Barbearia.usuario_id == avaliacao.avaliado_id
        ).first()
        
        if barbearia:
            aval_barbearia = models.AvaliacaoBarbearia(
                barbearia_id=barbearia.id,
                avaliador_id=usuario.id,
                nota=avaliacao.nota,
                comentario=avaliacao.comentario,
                data=datetime.now()
            )
            db.add(aval_barbearia)
    
    db.commit()
    db.refresh(nova_avaliacao)
    
    return {
        "id": nova_avaliacao.id,
        "avaliador_id": nova_avaliacao.avaliador_id,
        "avaliado_id": nova_avaliacao.avaliado_id,
        "nota": nova_avaliacao.nota,
        "comentario": nova_avaliacao.comentario,
        "criado_em": nova_avaliacao.criado_em
    }

@router.get("/avaliacoes/usuario/{usuario_id}")
def get_avaliacoes_usuario(
    usuario_id: int,
    db: Session = Depends(get_db)
):
    """
    Retorna todas as avaliações recebidas por um usuário
    """
    avaliacoes = db.query(models.Avaliacao).filter(
        models.Avaliacao.avaliado_id == usuario_id
    ).all()
    
    if not avaliacoes:
        return {
            "usuario_id": usuario_id,
            "avaliacoes": [],
            "media": 0,
            "total": 0
        }
    
    # Calcular média
    notas = [a.nota for a in avaliacoes]
    media = sum(notas) / len(notas) if notas else 0
    
    return {
        "usuario_id": usuario_id,
        "avaliacoes": [
            {
                "id": a.id,
                "avaliador_id": a.avaliador_id,
                "avaliador_nome": a.avaliador.nome if a.avaliador else "Anônimo",
                "nota": a.nota,
                "comentario": a.comentario,
                "criado_em": a.criado_em
            }
            for a in avaliacoes
        ],
        "media": round(media, 2),
        "total": len(avaliacoes)
    }

@router.get("/avaliacoes/perfil/{usuario_id}")
def get_avaliacoes_perfil(usuario_id: int, db: Session = Depends(get_db)):
    """
    Retorna dados de avaliação para exibir no perfil do usuário
    """
    usuario = db.query(models.Usuario).filter(models.Usuario.id == usuario_id).first()
    
    if not usuario:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")
    
    avaliacoes = db.query(models.Avaliacao).filter(
        models.Avaliacao.avaliado_id == usuario_id
    ).all()
    
    notas = [a.nota for a in avaliacoes]
    media = sum(notas) / len(notas) if notas else 0
    
    # Contagem por nota
    contagem_notas = {}
    for nota in notas:
        contagem_notas[nota] = contagem_notas.get(nota, 0) + 1
    
    return {
        "usuario_id": usuario_id,
        "usuario_nome": usuario.nome,
        "usuario_tipo": usuario.tipo,
        "media": round(media, 2),
        "total_avaliacoes": len(avaliacoes),
        "contagem_por_nota": contagem_notas,
        "avaliacoes_recentes": [
            {
                "nota": a.nota,
                "comentario": a.comentario,
                "avaliador_nome": a.avaliador.nome if a.avaliador else "Anônimo",
                "criado_em": a.criado_em
            }
            for a in avaliacoes[-5:]  # Últimas 5
        ]
    }

# ==================== PORTFÓLIO DE BARBEIROS ====================

@router.post("/barbeiro/portfolio")
def salvar_portfolio_barbeiro(
    portfolio_data: dict,
    db: Session = Depends(get_db),
    usuario = Depends(get_current_user)
):
    """
    Salva foto de portfólio para barbeiro (tipo='barbeiro')
    Diferente de freelancer, usa tabela 'fotos'
    
    Body:
    {
        "url_imagem": "http://...",
        "tipo_servico": "corte|barba|facial",
        "descricao": "descrição opcional"
    }
    """
    # Validar que é barbeiro
    if usuario.tipo != "barbeiro":
        raise HTTPException(
            status_code=403, 
            detail="Apenas barbeiros podem adicionar portfólio"
        )
    
    url = portfolio_data.get("url_imagem")
    tipo = portfolio_data.get("tipo_servico", "corte")
    descricao = portfolio_data.get("descricao", "")
    
    if not url:
        raise HTTPException(status_code=400, detail="URL da imagem é obrigatória")
    
    # Criar foto no banco
    foto = models.Foto(
        usuario_id=usuario.id,
        url=url,
        descricao=f"{tipo}: {descricao}" if descricao else tipo
    )
    db.add(foto)
    db.commit()
    db.refresh(foto)
    
    return {
        "id": foto.id,
        "url": foto.url,
        "descricao": foto.descricao,
        "tipo_servico": tipo,
        "criado_em": foto.criado_em
    }

@router.get("/barbeiro/portfolio")
def listar_portfolio_barbeiro(
    db: Session = Depends(get_db),
    usuario = Depends(get_current_user)
):
    """
    Lista portfólio (fotos) do barbeiro logado
    """
    if usuario.tipo != "barbeiro":
        raise HTTPException(
            status_code=403, 
            detail="Apenas barbeiros podem acessar portfólio"
        )
    
    fotos = db.query(models.Foto).filter(
        models.Foto.usuario_id == usuario.id
    ).order_by(models.Foto.criado_em.desc()).all()
    
    return [
        {
            "id": f.id,
            "url": f.url,
            "descricao": f.descricao,
            "criado_em": f.criado_em
        }
        for f in fotos
    ]

@router.delete("/barbeiro/portfolio/{foto_id}")
def deletar_portfolio_barbeiro(
    foto_id: int,
    db: Session = Depends(get_db),
    usuario = Depends(get_current_user)
):
    """
    Deleta foto de portfólio do barbeiro
    """
    if usuario.tipo != "barbeiro":
        raise HTTPException(
            status_code=403, 
            detail="Apenas barbeiros podem deletar portfólio"
        )
    
    foto = db.query(models.Foto).filter(
        and_(
            models.Foto.id == foto_id,
            models.Foto.usuario_id == usuario.id
        )
    ).first()
    
    if not foto:
        raise HTTPException(status_code=404, detail="Foto não encontrada")
    
    db.delete(foto)
    db.commit()
    
    return {"message": "Foto deletada com sucesso"}


@router.patch("/barbearias/me/presenca")
def marcar_presenca_barbearia(
    payload: dict,
    db: Session = Depends(get_db),
    usuario = Depends(get_current_user)
):
    """
    Marca barbearia como aberta/fechada no local
    Apenas para usuários com tipo='barbearia'
    """
    from datetime import datetime
    
    if usuario.tipo != "barbearia":
        raise HTTPException(status_code=403, detail="Apenas barbearias podem usar este endpoint")
    
    # Encontrar a barbearia do usuário
    barbearia = db.query(models.Barbearia).filter(
        models.Barbearia.usuario_id == usuario.id
    ).first()
    
    if not barbearia:
        raise HTTPException(status_code=404, detail="Barbearia não encontrada")
    
    # Atualizar presença
    presente = payload.get("presente_em_local", False)
    barbearia.presente_em_local = presente
    
    # Se está marcando como aberta, registrar horário de chegada
    if presente:
        barbearia.horario_chegada = datetime.utcnow()
    else:
        barbearia.horario_chegada = None
    
    db.commit()
    db.refresh(barbearia)
    
    return {
        "message": f"Barbearia marcada como {'aberta' if presente else 'fechada'}",
        "presente_em_local": barbearia.presente_em_local,
        "horario_chegada": barbearia.horario_chegada
    }
