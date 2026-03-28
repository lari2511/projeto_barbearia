#!/usr/bin/env python3
"""
Rotas para relatório de ganhos da plataforma.
Mostra quanto a plataforma deve receber (15% de cada serviço concluído).
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime, timedelta

from . import models
from .database import get_db
from .routes import get_current_user

router = APIRouter()


@router.get("/relatorio/ganhos")
def relatorio_ganhos(
    token_user: models.Usuario = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Retorna relatório de ganhos da plataforma.
    Apenas o dono da plataforma pode acessar.
    
    Usa os valores de snapshot financeiro salvos no momento do agendamento.
    Isso garante que mesmo se as percentagens mudarem, o histórico não muda.
    """
    # Verificar se é um admin/dono (você pode usar um campo 'is_admin' se tiver)
    # Por enquanto, qualquer usuario pode ver (depois restrinja)
    
    # Serviços concluídos
    chamados_concluidos = db.query(models.Chamado).filter(
        models.Chamado.status == models.StatusAgendamento.CONCLUIDO.value
    ).all()
    
    total_geral = 0.0
    ganho_total = 0.0
    detalhes = []
    
    for chamado in chamados_concluidos:
        # Usar valores do snapshot, não recalcular
        valor_servico = chamado.valor_total or 0.0
        taxa_plataforma = chamado.comissao_plataforma or 0.0
        
        total_geral += valor_servico
        ganho_total += taxa_plataforma
        
        # Buscar nome da barbearia
        barbearia = db.query(models.Barbearia).filter(
            models.Barbearia.id == chamado.barbearia_id
        ).first()
        
        detalhes.append({
            "chamado_id": chamado.id,
            "barbearia": barbearia.nome if barbearia else "Desconhecida",
            "valor_servico": valor_servico,
            "taxa_plataforma": round(taxa_plataforma, 2),
            "data_conclusao": chamado.concluido_em,
            "cliente": chamado.cliente.nome if chamado.cliente else "Desconhecido"
        })
    
    return {
        "total_servicos": len(chamados_concluidos),
        "valor_total_movimentado": round(total_geral, 2),
        "ganho_plataforma_total": round(ganho_total, 2),
        "detalhes": detalhes
    }


@router.get("/relatorio/ganhos-pendentes")
def relatorio_ganhos_pendentes(
    token_user: models.Usuario = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Relatório apenas de ganhos que ainda não foram cobrados/recebidos.
    Serviços concluídos que a plataforma ainda não recebeu.
    """
    
    # Serviços concluídos SEM pagamento registrado
    chamados_nao_pagos = db.query(models.Chamado).filter(
        models.Chamado.status == models.StatusAgendamento.CONCLUIDO.value
    ).outerjoin(models.Pagamento).filter(
        models.Pagamento.id == None  # Não tem registro de pagamento
    ).all()
    
    total_pendente = 0.0
    ganho_pendente = 0.0
    detalhes = []
    
    for chamado in chamados_nao_pagos:
        # Usar valores do snapshot
        valor_servico = chamado.valor_total or 0.0
        taxa_plataforma = chamado.comissao_plataforma or 0.0
        
        total_pendente += valor_servico
        ganho_pendente += taxa_plataforma
        
        barbearia = db.query(models.Barbearia).filter(
            models.Barbearia.id == chamado.barbearia_id
        ).first()
        
        detalhes.append({
            "chamado_id": chamado.id,
            "barbearia": barbearia.nome if barbearia else "Desconhecida",
            "valor_servico": valor_servico,
            "taxa_plataforma": round(taxa_plataforma, 2),
            "data_conclusao": chamado.concluido_em or "Não concluído"
        })
    
    return {
        "servicos_pendentes": len(chamados_nao_pagos),
        "valor_total_pendente": round(total_pendente, 2),
        "ganho_pendente": round(ganho_pendente, 2),
        "detalhes": detalhes,
        "instrucoes": "Envie estes detalhes para os barbeiros/barbearias cobrarem os valores"
    }


@router.post("/pagamento/{chamado_id}/registrar-recebido")
def registrar_pagamento_recebido(
    chamado_id: int,
    token_user: models.Usuario = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Registra que você recebeu o pagamento dos 15% para um serviço.
    Cria/atualiza o registro de Pagamento usando valores do snapshot.
    """
    
    chamado = db.query(models.Chamado).filter(
        models.Chamado.id == chamado_id
    ).first()
    
    if not chamado:
        raise HTTPException(status_code=404, detail="Chamado não encontrado")
    
    # Usar valores do snapshot, não recalcular
    valor_total = chamado.valor_total or 0.0
    taxa_plataforma = chamado.comissao_plataforma or 0.0
    valor_para_barbeiro = chamado.valor_freelancer or 0.0
    
    # Verificar se já existe registro
    pagamento = db.query(models.Pagamento).filter(
        models.Pagamento.chamado_id == chamado_id
    ).first()
    
    if pagamento:
        pagamento.pago_em = datetime.now()
    else:
        pagamento = models.Pagamento(
            chamado_id=chamado_id,
            valor_total=valor_total,
            taxa_plataforma=taxa_plataforma,
            valor_barbeiro=valor_para_barbeiro,
            pago_em=datetime.now()
        )
        db.add(pagamento)
    
    db.commit()
    db.refresh(pagamento)
    
    return {
        "sucesso": True,
        "mensagem": f"Pagamento de R$ {taxa_plataforma:.2f} registrado",
        "taxa_plataforma": round(taxa_plataforma, 2),
        "data_recebimento": pagamento.pago_em
    }
