"""
🛡️ ROTAS ADMIN - GERENCIAMENTO DE AVALIAÇÕES
Endpoints para administradores gerenciarem avaliações problemáticas
e controlar usuários com comportamento inadequado
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import datetime
from app.database import get_db
from app import models, schemas
from app.routes import get_current_user, oauth2_scheme

router = APIRouter(prefix="/api/v1/admin", tags=["Admin - Avaliações"])


@router.get("/avaliacoes/negativas")
def listar_avaliacoes_negativas(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
    filtro_bloqueadas: bool = False,
    nota_maxima: int = 2,  # ⭐⭐ ou menos por padrão
    limite: int = 50
):
    """
    ✅ ADMIN: Listar avaliações NEGATIVAS (1-2 estrelas)
    Filtra automaticamente avaliações ruins para revisão
    """
    admin = get_current_user(token=token, db=db)
    
    # Validar que é admin
    if admin.tipo != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Apenas admins podem acessar este endpoint"
        )
    
    # Buscar avaliações de freelancers
    avaliacoes_freelancer = db.query(models.AvaliacaoFreelancer).filter(
        models.AvaliacaoFreelancer.nota <= nota_maxima
    )
    
    if filtro_bloqueadas:
        avaliacoes_freelancer = avaliacoes_freelancer.filter(
            models.AvaliacaoFreelancer.bloqueada_por_admin == False
        )
    
    resultado_freelancer = []
    for av in avaliacoes_freelancer.limit(limite).all():
        freelancer = db.query(models.Freelancer).filter(
            models.Freelancer.id == av.freelancer_id
        ).first()
        usuario = db.query(models.Usuario).filter(
            models.Usuario.id == freelancer.usuario_id if freelancer else None
        ).first() if freelancer else None
        
        resultado_freelancer.append({
            "id": av.id,
            "tipo": "freelancer",
            "freelancer_id": av.freelancer_id,
            "freelancer_nome": usuario.nome if usuario else "Desconhecido",
            "nota": av.nota,
            "comentario": av.comentario,
            "avaliador_id": av.avaliador_id,
            "tipo_avaliador": av.tipo_avaliador,
            "criado_em": av.criado_em.isoformat() if av.criado_em else None,
            "bloqueada_por_admin": av.bloqueada_por_admin,
            "motivo_bloqueio": av.motivo_bloqueio,
            "bloqueada_em": av.bloqueada_em.isoformat() if av.bloqueada_em else None
        })
    
    # Buscar avaliações de barbearias
    avaliacoes_barbearia = db.query(models.AvaliacaoBarbearia).filter(
        models.AvaliacaoBarbearia.nota <= nota_maxima
    )
    
    if filtro_bloqueadas:
        avaliacoes_barbearia = avaliacoes_barbearia.filter(
            models.AvaliacaoBarbearia.bloqueada_por_admin == False
        )
    
    resultado_barbearia = []
    for av in avaliacoes_barbearia.limit(limite - len(resultado_freelancer)).all():
        barbearia = db.query(models.Barbearia).filter(
            models.Barbearia.id == av.barbearia_id
        ).first()
        
        resultado_barbearia.append({
            "id": av.id,
            "tipo": "barbearia",
            "barbearia_id": av.barbearia_id,
            "barbearia_nome": barbearia.nome if barbearia else "Desconhecido",
            "nota": av.nota,
            "comentario": av.comentario,
            "avaliador_id": av.avaliador_id,
            "tipo_avaliador": av.tipo_avaliador,
            "criado_em": av.criado_em.isoformat() if av.criado_em else None,
            "bloqueada_por_admin": av.bloqueada_por_admin,
            "motivo_bloqueio": av.motivo_bloqueio,
            "bloqueada_em": av.bloqueada_em.isoformat() if av.bloqueada_em else None
        })
    
    return {
        "total": len(resultado_freelancer) + len(resultado_barbearia),
        "avaliacoes_freelancer": resultado_freelancer,
        "avaliacoes_barbearia": resultado_barbearia
    }


@router.post("/avaliacoes/{avaliacao_id}/bloquear")
def bloquear_avaliacao(
    avaliacao_id: int,
    tipo: str,  # 'freelancer' ou 'barbearia'
    motivo: str,
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
):
    """
    ✅ ADMIN: Bloquear uma avaliação problemática
    Remove exibição e marca para revisão
    """
    admin = get_current_user(token=token, db=db)
    
    if admin.tipo != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Apenas admins podem bloquear avaliações"
        )
    
    if tipo == "freelancer":
        avaliacao = db.query(models.AvaliacaoFreelancer).filter(
            models.AvaliacaoFreelancer.id == avaliacao_id
        ).first()
    elif tipo == "barbearia":
        avaliacao = db.query(models.AvaliacaoBarbearia).filter(
            models.AvaliacaoBarbearia.id == avaliacao_id
        ).first()
    else:
        raise HTTPException(status_code=400, detail="Tipo inválido")
    
    if not avaliacao:
        raise HTTPException(status_code=404, detail="Avaliação não encontrada")
    
    # Bloquear
    avaliacao.bloqueada_por_admin = True
    avaliacao.motivo_bloqueio = motivo
    avaliacao.bloqueada_em = datetime.utcnow()
    avaliacao.revisada_por_admin_id = admin.id
    
    db.commit()
    db.refresh(avaliacao)
    
    return {"success": True, "mensagem": f"Avaliação bloqueada. Motivo: {motivo}"}


@router.post("/avaliacoes/{avaliacao_id}/liberar")
def liberar_avaliacao(
    avaliacao_id: int,
    tipo: str,  # 'freelancer' ou 'barbearia'
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
):
    """
    ✅ ADMIN: Liberar uma avaliação bloqueada (se foi por engano)
    """
    admin = get_current_user(token=token, db=db)
    
    if admin.tipo != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Apenas admins podem liberar avaliações"
        )
    
    if tipo == "freelancer":
        avaliacao = db.query(models.AvaliacaoFreelancer).filter(
            models.AvaliacaoFreelancer.id == avaliacao_id
        ).first()
    elif tipo == "barbearia":
        avaliacao = db.query(models.AvaliacaoBarbearia).filter(
            models.AvaliacaoBarbearia.id == avaliacao_id
        ).first()
    else:
        raise HTTPException(status_code=400, detail="Tipo inválido")
    
    if not avaliacao:
        raise HTTPException(status_code=404, detail="Avaliação não encontrada")
    
    # Liberar
    avaliacao.bloqueada_por_admin = False
    avaliacao.motivo_bloqueio = None
    avaliacao.bloqueada_em = None
    
    db.commit()
    db.refresh(avaliacao)
    
    return {"success": True, "mensagem": "Avaliação liberada"}


@router.get("/usuarios/problematicos")
def listar_usuarios_problematicos(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
    tipo_filtro: str = "barbeiro",  # 'barbeiro', 'barbearia', 'cliente'
    limite: int = 50
):
    """
    ✅ ADMIN: Listar usuários com MUITAS avaliações negativas
    Identifica padrão de comportamento inadequado
    """
    admin = get_current_user(token=token, db=db)
    
    if admin.tipo != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Apenas admins podem acessar este endpoint"
        )
    
    # Buscar usuários do tipo especificado
    usuarios_problematicos = db.query(models.Usuario).filter(
        models.Usuario.tipo == tipo_filtro,
        models.Usuario.total_avaliacoes_negativas >= 3  # ⚠️ 3 ou mais avaliações ruins
    ).order_by(
        models.Usuario.total_avaliacoes_negativas.desc()
    ).limit(limite).all()
    
    resultado = []
    for usuario in usuarios_problematicos:
        # Contar avaliações negativas recentes
        if usuario.tipo == "barbeiro":
            freelancer = db.query(models.Freelancer).filter(
                models.Freelancer.usuario_id == usuario.id
            ).first()
            if freelancer:
                avaliacoes_ruins = db.query(models.AvaliacaoFreelancer).filter(
                    models.AvaliacaoFreelancer.freelancer_id == freelancer.id,
                    models.AvaliacaoFreelancer.nota <= 2,
                    models.AvaliacaoFreelancer.bloqueada_por_admin == False
                ).all()
            else:
                avaliacoes_ruins = []
        else:
            avaliacoes_ruins = []
        
        resultado.append({
            "id": usuario.id,
            "nome": usuario.nome,
            "email": usuario.email,
            "tipo": usuario.tipo,
            "total_avaliacoes_negativas": usuario.total_avaliacoes_negativas,
            "media_avaliacoes": usuario.media_avaliacoes_negativas,
            "bloqueado": usuario.bloqueado_por_admin,
            "motivo_bloqueio": usuario.motivo_bloqueio,
            "avaliacoes_ruins_ativas": len(avaliacoes_ruins),
            "criado_em": usuario.criado_em.isoformat() if usuario.criado_em else None
        })
    
    return {
        "total": len(resultado),
        "usuarios": resultado
    }


@router.post("/usuarios/{usuario_id}/bloquear")
def bloquear_usuario(
    usuario_id: int,
    motivo: str,
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
):
    """
    🛑 ADMIN: Bloquear um usuário (REMOVE DO APP)
    Depois de avaliações negativas ou comportamento inadequado
    """
    admin = get_current_user(token=token, db=db)
    
    if admin.tipo != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Apenas admins podem bloquear usuários"
        )
    
    usuario = db.query(models.Usuario).filter(
        models.Usuario.id == usuario_id
    ).first()
    
    if not usuario:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")
    
    if usuario.id == admin.id:
        raise HTTPException(
            status_code=400,
            detail="Você não pode bloquear a si mesmo"
        )
    
    # Bloquear
    usuario.bloqueado_por_admin = True
    usuario.motivo_bloqueio = motivo
    usuario.bloqueado_em = datetime.utcnow()
    usuario.perfil_aprovado = False  # Remover do app
    
    # Criar notificação para o usuário
    notificacao = models.Notificacao(
        usuario_id=usuario.id,
        titulo="⚠️ Perfil Bloqueado",
        mensagem=f"Seu perfil foi bloqueado por: {motivo}. Entre em contato com o suporte.",
        tipo="perfil_bloqueado"
    )
    db.add(notificacao)
    db.commit()
    
    return {
        "success": True,
        "mensagem": f"Usuário {usuario.nome} foi bloqueado",
        "motivo": motivo
    }


@router.post("/usuarios/{usuario_id}/desbloquear")
def desbloquear_usuario(
    usuario_id: int,
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
):
    """
    ✅ ADMIN: Desbloquear um usuário
    """
    admin = get_current_user(token=token, db=db)
    
    if admin.tipo != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Apenas admins podem desbloquear usuários"
        )
    
    usuario = db.query(models.Usuario).filter(
        models.Usuario.id == usuario_id
    ).first()
    
    if not usuario:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")
    
    # Desbloquear
    usuario.bloqueado_por_admin = False
    usuario.motivo_bloqueio = None
    usuario.bloqueado_em = None
    usuario.total_avaliacoes_negativas = 0  # Reset do contador
    
    db.commit()
    db.refresh(usuario)
    
    return {"success": True, "mensagem": f"Usuário {usuario.nome} foi desbloqueado"}


@router.get("/dashboard")
def dashboard_avaliacoes(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
):
    """
    📊 ADMIN: Dashboard com estatísticas de avaliações
    """
    admin = get_current_user(token=token, db=db)
    
    if admin.tipo != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Apenas admins podem acessar este dashboard"
        )
    
    # Total de avaliações
    total_avaliacoes_freelancer = db.query(models.AvaliacaoFreelancer).count()
    total_avaliacoes_barbearia = db.query(models.AvaliacaoBarbearia).count()
    
    # Avaliações bloqueadas
    bloqueadas_freelancer = db.query(models.AvaliacaoFreelancer).filter(
        models.AvaliacaoFreelancer.bloqueada_por_admin == True
    ).count()
    bloqueadas_barbearia = db.query(models.AvaliacaoBarbearia).filter(
        models.AvaliacaoBarbearia.bloqueada_por_admin == True
    ).count()
    
    # Avaliações negativas (não bloqueadas)
    negativas_freelancer = db.query(models.AvaliacaoFreelancer).filter(
        models.AvaliacaoFreelancer.nota <= 2,
        models.AvaliacaoFreelancer.bloqueada_por_admin == False
    ).count()
    negativas_barbearia = db.query(models.AvaliacaoBarbearia).filter(
        models.AvaliacaoBarbearia.nota <= 2,
        models.AvaliacaoBarbearia.bloqueada_por_admin == False
    ).count()
    
    # Usuários bloqueados
    usuarios_bloqueados = db.query(models.Usuario).filter(
        models.Usuario.bloqueado_por_admin == True
    ).count()
    
    # Usuários problemáticos (com muitas avaliações ruins)
    usuarios_problematicos = db.query(models.Usuario).filter(
        models.Usuario.total_avaliacoes_negativas >= 3
    ).count()
    
    return {
        "dashboard": {
            "avaliacoes_freelancer": {
                "total": total_avaliacoes_freelancer,
                "bloqueadas": bloqueadas_freelancer,
                "negativas_pendentes": negativas_freelancer
            },
            "avaliacoes_barbearia": {
                "total": total_avaliacoes_barbearia,
                "bloqueadas": bloqueadas_barbearia,
                "negativas_pendentes": negativas_barbearia
            },
            "usuarios": {
                "bloqueados": usuarios_bloqueados,
                "problematicos": usuarios_problematicos
            },
            "timestamp": datetime.utcnow().isoformat()
        }
    }
