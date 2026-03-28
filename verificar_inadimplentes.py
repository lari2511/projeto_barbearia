"""
Script de verificação automática de assinaturas vencidas
Bloqueia barbearias inadimplentes automaticamente

Execute periodicamente (cron/task scheduler):
- A cada hora durante horário comercial
- Uma vez por dia em produção
"""
from sqlalchemy.orm import Session
from datetime import datetime
from app.database import SessionLocal, engine
from app import models
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def verificar_e_bloquear_inadimplentes():
    """
    Verifica todas as assinaturas vencidas e bloqueia as barbearias
    """
    db = SessionLocal()
    try:
        # Buscar todas assinaturas ativas ou inadimplentes
        assinaturas = db.query(models.AssinaturaBarbearia).filter(
            models.AssinaturaBarbearia.status.in_(["ativa", "inadimplente"])
        ).all()
        
        bloqueadas = 0
        alertadas = 0
        
        for assinatura in assinaturas:
            # Verificar se está vencida
            if assinatura.proximo_vencimento < datetime.utcnow():
                # Buscar barbearia
                barbearia = db.query(models.Barbearia).filter(
                    models.Barbearia.id == assinatura.barbearia_id
                ).first()
                
                if not barbearia:
                    continue
                
                # Atualizar status da assinatura
                if assinatura.status != "inadimplente":
                    assinatura.status = "inadimplente"
                    assinatura.motivo_suspensao = f"Vencida em {assinatura.proximo_vencimento.strftime('%d/%m/%Y')}"
                    logger.info(f"Assinatura {assinatura.id} marcada como inadimplente")
                
                # Bloquear barbearia se ainda não estiver bloqueada
                if not barbearia.bloqueada:
                    barbearia.bloqueada = True
                    barbearia.motivo_bloqueio = (
                        f"Assinatura vencida desde {assinatura.proximo_vencimento.strftime('%d/%m/%Y')}. "
                        f"Valor devido: R$ {assinatura.valor_mensalidade:.2f}. "
                        f"Regularize o pagamento para continuar usando o app."
                    )
                    barbearia.bloqueada_em = datetime.utcnow()
                    bloqueadas += 1
                    logger.warning(f"Barbearia {barbearia.id} ({barbearia.nome}) bloqueada por inadimplência")
                    
                    # TODO: Enviar notificação/email para o dono
                    # notificar_bloqueio(barbearia, assinatura)
                
        db.commit()
        
        logger.info(f"Verificação concluída: {bloqueadas} barbearias bloqueadas")
        return {
            "bloqueadas": bloqueadas,
            "total_verificadas": len(assinaturas)
        }
        
    except Exception as e:
        logger.error(f"Erro ao verificar inadimplentes: {str(e)}")
        db.rollback()
        raise
    finally:
        db.close()


def alertar_vencimentos_proximos(dias_antes=3):
    """
    Alerta barbearias que vão vencer nos próximos X dias
    """
    db = SessionLocal()
    try:
        from datetime import timedelta
        data_limite = datetime.utcnow() + timedelta(days=dias_antes)
        
        assinaturas = db.query(models.AssinaturaBarbearia).filter(
            models.AssinaturaBarbearia.status == "ativa",
            models.AssinaturaBarbearia.proximo_vencimento <= data_limite,
            models.AssinaturaBarbearia.proximo_vencimento > datetime.utcnow()
        ).all()
        
        for assinatura in assinaturas:
            barbearia = db.query(models.Barbearia).filter(
                models.Barbearia.id == assinatura.barbearia_id
            ).first()
            
            if barbearia:
                dias_restantes = (assinatura.proximo_vencimento - datetime.utcnow()).days
                logger.info(
                    f"ALERTA: Barbearia {barbearia.nome} - "
                    f"Assinatura vence em {dias_restantes} dias "
                    f"({assinatura.proximo_vencimento.strftime('%d/%m/%Y')})"
                )
                # TODO: Enviar notificação/email
                # notificar_vencimento_proximo(barbearia, assinatura, dias_restantes)
        
        return len(assinaturas)
        
    except Exception as e:
        logger.error(f"Erro ao alertar vencimentos: {str(e)}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    logger.info("Iniciando verificação automática de inadimplências...")
    resultado = verificar_e_bloquear_inadimplentes()
    logger.info(f"Barbearias bloqueadas: {resultado['bloqueadas']}")
    logger.info(f"Total verificadas: {resultado['total_verificadas']}")
    
    logger.info("\nVerificando vencimentos próximos...")
    alertas = alertar_vencimentos_proximos(dias_antes=3)
    logger.info(f"Alertas enviados: {alertas}")
