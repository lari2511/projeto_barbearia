"""
Dependencies customizadas para validações de negócio
"""
from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import datetime

from app.database import get_db
from app import models
from app.routes import get_current_user
from app.plan_policy import is_test_barbershop_profile


async def verificar_barbearia_ativa(
    db: Session = Depends(get_db),
    usuario_atual = Depends(get_current_user)
):
    """
    Verifica se a barbearia do usuário está ativa e não bloqueada.
    Bloqueia acesso se:
    - A barbearia está bloqueada por inadimplência
    - A assinatura está vencida
    
    Uso: Add como dependency em rotas críticas de barbearia
    """
    # Só aplica para usuários do tipo barbearia
    if usuario_atual.tipo != "barbearia":
        return usuario_atual
    
    # Buscar barbearia do usuário
    barbearia = db.query(models.Barbearia).filter(
        models.Barbearia.usuario_id == usuario_atual.id
    ).first()
    
    if not barbearia:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Barbearia não encontrada"
        )

    perfil_teste = is_test_barbershop_profile(usuario=usuario_atual, barbearia=barbearia)
    
    # Verificar se está bloqueada
    if barbearia.bloqueada and not perfil_teste:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "erro": "assinatura_bloqueada",
                "mensagem": barbearia.motivo_bloqueio or "Barbearia bloqueada. Complete o pagamento da mensalidade para continuar usando o app.",
                "bloqueada_em": barbearia.bloqueada_em.isoformat() if barbearia.bloqueada_em else None
            }
        )
    
    # Buscar assinatura
    assinatura = db.query(models.AssinaturaBarbearia).filter(
        models.AssinaturaBarbearia.barbearia_id == barbearia.id
    ).first()
    
    # Se não tem assinatura, bloqueia (precisa contratar)
    if not assinatura and not perfil_teste:
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail={
                "erro": "sem_assinatura",
                "mensagem": "Você precisa contratar uma assinatura para usar o app. Escolha quantas cadeiras deseja ativar."
            }
        )

    if not assinatura and perfil_teste:
        return usuario_atual
    
    # Verificar se assinatura está vencida
    if (assinatura.status == "inadimplente" or assinatura.proximo_vencimento < datetime.utcnow()) and not perfil_teste:
        # Bloquear automaticamente a barbearia
        if not barbearia.bloqueada:
            barbearia.bloqueada = True
            barbearia.motivo_bloqueio = f"Assinatura vencida desde {assinatura.proximo_vencimento.strftime('%d/%m/%Y')}. Regularize para continuar."
            barbearia.bloqueada_em = datetime.utcnow()
            assinatura.status = "inadimplente"
            db.commit()
        
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail={
                "erro": "assinatura_vencida",
                "mensagem": f"Sua assinatura venceu em {assinatura.proximo_vencimento.strftime('%d/%m/%Y')}. Complete o pagamento para continuar.",
                "valor_devido": assinatura.valor_mensalidade,
                "vencimento": assinatura.proximo_vencimento.isoformat()
            }
        )
    
    return usuario_atual


async def obter_barbearia_usuario(
    db: Session = Depends(get_db),
    usuario_atual = Depends(get_current_user)
):
    """
    Retorna a barbearia do usuário atual.
    Levanta exceção se não for do tipo barbearia ou não tiver barbearia cadastrada.
    """
    if usuario_atual.tipo != "barbearia":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Apenas donos de barbearia podem acessar este recurso"
        )
    
    barbearia = db.query(models.Barbearia).filter(
        models.Barbearia.usuario_id == usuario_atual.id
    ).first()
    
    if not barbearia:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Barbearia não encontrada"
        )
    
    return barbearia
