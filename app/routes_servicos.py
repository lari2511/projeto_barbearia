"""
Rotas para gerenciar SERVIÇOS de uma barbearia.

O princípio-chave:
- Cada barbearia tem SEUS OWN serviços
- Barbearia A: "Corte R$ 30"
- Barbearia B: "Corte R$ 50"
- São registros diferentes no banco!
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import datetime

from . import models, schemas
from .database import get_db
from .routes import get_current_user, oauth2_scheme

router = APIRouter()

# ============================================================================
# TEMPLATES/SUGESTÕES DE SERVIÇOS (Valores padrão)
# ============================================================================

# Lista de templates que o dono pode usar como referência
TEMPLATES_SERVICOS = [
    {
        "nome": "Corte Masculino",
        "descricao": "Corte clássico com máquina e tesoura",
        "valor_padrao": 35.00,
        "duracao_minutos_padrao": 30,
        "categoria": "corte"
    },
    {
        "nome": "Barba Completa",
        "descricao": "Barba com navalha e acabamento",
        "valor_padrao": 25.00,
        "duracao_minutos_padrao": 20,
        "categoria": "barba"
    },
    {
        "nome": "Combo Corte + Barba",
        "descricao": "Corte + barba completa",
        "valor_padrao": 55.00,
        "duracao_minutos_padrao": 50,
        "categoria": "combo"
    },
    {
        "nome": "Design de Sobrancelha",
        "descricao": "Cuidado e design das sobrancelhas",
        "valor_padrao": 15.00,
        "duracao_minutos_padrao": 15,
        "categoria": "sobrancelha"
    },
    {
        "nome": "Corte Infantil",
        "descricao": "Corte especial para crianças",
        "valor_padrao": 25.00,
        "duracao_minutos_padrao": 20,
        "categoria": "infantil"
    },
    {
        "nome": "Hidratação Capilar",
        "descricao": "Tratamento hidratante para os cabelos",
        "valor_padrao": 45.00,
        "duracao_minutos_padrao": 40,
        "categoria": "tratamento"
    }
]


@router.get("/templates/servicos", tags=["Templates"])
def listar_templates_servicos():
    """
    Retorna lista de SUGESTÕES de serviços que o dono pode usar como referência.
    
    O dono pode:
    1. Ver um template (ex: "Corte Masculino - R$ 35")
    2. Clicar em "Adicionar"
    3. O app já preenche nome, descrição, valor padrão, duração
    4. Dono edita o valor se quiser (ex: "Eu quero R$ 40")
    5. Salva na barbearia dele
    
    Returns:
        Lista de templates com nome, descrição, valor padrão, duração, categoria
    """
    return {
        "templates": TEMPLATES_SERVICOS,
        "total": len(TEMPLATES_SERVICOS),
        "mensagem": "Use esses templates como inspiração! Você pode editar todos os valores antes de salvar."
    }


# ============================================================================
# CRIAR SERVIÇO (O dono da barbearia)
# ============================================================================

@router.post("/barbearias/{barbearia_id}/servicos", tags=["Serviços"])
def criar_servico(
    barbearia_id: int,
    servico: schemas.ServicoCreate,
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
):
    """
    Criar um novo serviço para uma barbearia.
    
    ✅ O dono pode criar quantos serviços quiser
    ✅ Cada serviço é único para essa barbearia
    ✅ Se outra barbearia tiver um "Corte" com preço diferente, é um serviço diferente
    
    Args:
        barbearia_id: ID da barbearia
        servico: Dados do serviço (nome, valor, duração)
        
    Returns:
        Serviço criado com ID
    """
    # Validar que usuário é dono dessa barbearia
    user = get_current_user(token=token, db=db)
    
    barbearia = db.query(models.Barbearia).filter(
        models.Barbearia.id == barbearia_id
    ).first()
    
    if not barbearia:
        raise HTTPException(status_code=404, detail="Barbearia não encontrada")
    
    if barbearia.usuario_id != user.id:
        raise HTTPException(
            status_code=403,
            detail="Você só pode criar serviços na sua própria barbearia"
        )
    
    # ✅ IMPORTANTE: barbearia_id é definido automaticamente
    novo_servico = models.Servico(
        barbearia_id=barbearia_id,  # O SEGREDO: Sempre a barbearia do dono
        nome=servico.nome,
        categoria=servico.categoria,  # ✅ HÍBRIDO: Nome criativo + Categoria padrão
        descricao=servico.descricao,
        valor=servico.valor,
        duracao_minutos=servico.duracao_minutos or 30,
        ativo=True
    )
    
    db.add(novo_servico)
    db.commit()
    db.refresh(novo_servico)
    
    return {
        "id": novo_servico.id,
        "barbearia_id": novo_servico.barbearia_id,
        "nome": novo_servico.nome,
        "categoria": novo_servico.categoria,
        "valor": novo_servico.valor,
        "duracao_minutos": novo_servico.duracao_minutos,
        "mensagem": "✅ Serviço criado com sucesso!"
    }


# ============================================================================
# LISTAR SERVIÇOS (Cliente vendo os serviços de uma barbearia)
# ============================================================================

@router.get("/barbearias/{barbearia_id}/servicos", tags=["Serviços"])
def listar_servicos_barbearia(barbearia_id: int, db: Session = Depends(get_db)):
    """
    Listar TODOS os serviços de uma barbearia específica.
    
    Isso é o que o CLIENT vê quando:
    1. Clica em "Barbearia João"
    2. A app busca SELECT * FROM servicos WHERE barbearia_id = ID_JOAO
    3. Mostra só os serviços do João
    
    Args:
        barbearia_id: ID da barbearia
        
    Returns:
        Lista de serviços ativos daquela barbearia
    """
    barbearia = db.query(models.Barbearia).filter(
        models.Barbearia.id == barbearia_id
    ).first()
    
    if not barbearia:
        raise HTTPException(status_code=404, detail="Barbearia não encontrada")
    
    # Buscar APENAS serviços dessa barbearia que estão ativos
    servicos = db.query(models.Servico).filter(
        models.Servico.barbearia_id == barbearia_id,
        models.Servico.ativo == True
    ).all()
    
    return {
        "barbearia_id": barbearia_id,
        "barbearia_nome": barbearia.nome,
        "total": len(servicos),
        "servicos": [
            {
                "id": s.id,
                "nome": s.nome,
                "categoria": s.categoria,
                "descricao": s.descricao,
                "valor": s.valor,
                "duracao_minutos": s.duracao_minutos,
                "criado_em": s.criado_em
            }
            for s in servicos
        ]
    }


# ============================================================================
# ATUALIZAR SERVIÇO (O dono)
# ============================================================================

@router.put("/servicos/{servico_id}", tags=["Serviços"])
def atualizar_servico(
    servico_id: int,
    servico_update: schemas.ServicoUpdate,
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
):
    """
    Atualizar um serviço existente.
    
    O dono pode mudar:
    - Nome
    - Descrição
    - Valor (recomendado: novos agendamentos usam novo valor)
    - Duração
    - Ativo/Inativo (desativar sem deletar)
    
    Args:
        servico_id: ID do serviço
        servico_update: Campos a atualizar (todos opcionais)
        
    Returns:
        Serviço atualizado
    """
    user = get_current_user(token=token, db=db)
    
    servico = db.query(models.Servico).filter(
        models.Servico.id == servico_id
    ).first()
    
    if not servico:
        raise HTTPException(status_code=404, detail="Serviço não encontrado")
    
    # Validar que é dono dessa barbearia
    barbearia = db.query(models.Barbearia).filter(
        models.Barbearia.id == servico.barbearia_id
    ).first()
    
    if barbearia.usuario_id != user.id:
        raise HTTPException(
            status_code=403,
            detail="Você só pode editar serviços da sua própria barbearia"
        )
    
    # Atualizar apenas os campos fornecidos
    if servico_update.nome is not None:
        servico.nome = servico_update.nome
    if servico_update.descricao is not None:
        servico.descricao = servico_update.descricao
    if servico_update.valor is not None:
        servico.valor = servico_update.valor
    if servico_update.duracao_minutos is not None:
        servico.duracao_minutos = servico_update.duracao_minutos
    if servico_update.ativo is not None:
        servico.ativo = servico_update.ativo
    
    db.commit()
    db.refresh(servico)
    
    return {
        "id": servico.id,
        "nome": servico.nome,
        "valor": servico.valor,
        "duracao_minutos": servico.duracao_minutos,
        "ativo": servico.ativo,
        "mensagem": "✅ Serviço atualizado!"
    }


# ============================================================================
# DELETAR/DESATIVAR SERVIÇO (O dono)
# ============================================================================

@router.delete("/servicos/{servico_id}", tags=["Serviços"])
def deletar_servico(
    servico_id: int,
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
):
    """
    Desativar um serviço (soft delete).
    
    ⚠️ IMPORTANTE: Não deletamos de verdade, apenas desativamos.
    Por quê? Os agendamentos antigos ainda referem esse serviço.
    
    Args:
        servico_id: ID do serviço
        
    Returns:
        Mensagem de sucesso
    """
    user = get_current_user(token=token, db=db)
    
    servico = db.query(models.Servico).filter(
        models.Servico.id == servico_id
    ).first()
    
    if not servico:
        raise HTTPException(status_code=404, detail="Serviço não encontrado")
    
    # Validar que é dono
    barbearia = db.query(models.Barbearia).filter(
        models.Barbearia.id == servico.barbearia_id
    ).first()
    
    if barbearia.usuario_id != user.id:
        raise HTTPException(
            status_code=403,
            detail="Você só pode deletar serviços da sua própria barbearia"
        )
    
    # Desativar (não deletar de verdade)
    servico.ativo = False
    db.commit()
    
    return {
        "id": servico.id,
        "mensagem": "✅ Serviço desativado! (Agendamentos antigos não são afetados)"
    }


# ============================================================================
# BONUS: Listar TODOS os serviços do dono (dashboard)
# ============================================================================

@router.get("/meus-servicos", tags=["Serviços"])
def listar_meus_servicos(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
):
    """
    Listar TODOS os serviços de TODAS as barbearias do dono.
    
    Útil para o dashboard do dono ver um sumário.
    
    Returns:
        Lista de serviços agrupados por barbearia
    """
    user = get_current_user(token=token, db=db)
    
    if user.tipo != "barbearia":
        raise HTTPException(
            status_code=403,
            detail="Apenas donos de barbearias podem acessar"
        )
    
    # Buscar todas as barbearias do usuário
    barbearias = db.query(models.Barbearia).filter(
        models.Barbearia.usuario_id == user.id
    ).all()
    
    resultado = []
    for barbearia in barbearias:
        servicos = db.query(models.Servico).filter(
            models.Servico.barbearia_id == barbearia.id
        ).all()
        
        resultado.append({
            "barbearia_id": barbearia.id,
            "barbearia_nome": barbearia.nome,
            "total_servicos": len(servicos),
            "servicos": [
                {
                    "id": s.id,
                    "nome": s.nome,
                    "valor": s.valor,
                    "duracao_minutos": s.duracao_minutos,
                    "ativo": s.ativo
                }
                for s in servicos
            ]
        })
    
    return {
        "total_barbearias": len(barbearias),
        "barbearias": resultado
    }
