# Migração: Modelo de Agendamento com Snapshot Financeiro

## 📋 Resumo das Mudanças

Refatoração do modelo `Chamado` para implementar:
1. **Enum para Status** - Estados bem definidos em vez de strings soltas
2. **Snapshot Financeiro** - Valores salvos no momento do agendamento, nunca mudam
3. **Campos de Data/Hora** - Para rastrear início e fim do serviço

## 🔧 Mudanças no Banco de Dados

### Campos Adicionados

```sql
-- Novos campos de snapshot financeiro
ALTER TABLE chamados ADD COLUMN valor_total FLOAT;
ALTER TABLE chamados ADD COLUMN comissao_plataforma FLOAT;
ALTER TABLE chamados ADD COLUMN valor_freelancer FLOAT;
ALTER TABLE chamados ADD COLUMN valor_dono FLOAT;

-- Novos campos de tempo
ALTER TABLE chamados ADD COLUMN data_hora_inicio DATETIME;
ALTER TABLE chamados ADD COLUMN data_hora_fim DATETIME;
```

### Campo Modificado

```sql
-- Mudança do tipo para Enum (compatível com SQLAlchemy)
-- OBS: SQLAlchemy salva como String, mas o tipo no banco depende do driver
-- PostgreSQL: use ENUM, SQLite: fica String
ALTER TABLE chamados MODIFY COLUMN status VARCHAR(20) DEFAULT 'pendente';
```

## 📊 Mapeamento de Status Antigo → Novo

| Status Antigo | Status Novo  | Descrição |
|---|---|---|
| ABERTO | PENDENTE | Cliente pediu, aguardando aceite |
| ACEITO | CONFIRMADO | Barbeiro aceitou |
| CONCLUÍDO | CONCLUIDO | Serviço realizado |
| (novo) | CANCELADO | Cancelado por cliente ou barbeiro |

## 🔄 Script de Migração de Dados (SQL)

```sql
-- 1. Adicionar colunas novas (se usando SQLite, pode pular a criação de Enum)
ALTER TABLE chamados ADD COLUMN valor_total FLOAT;
ALTER TABLE chamados ADD COLUMN comissao_plataforma FLOAT;
ALTER TABLE chamados ADD COLUMN valor_freelancer FLOAT;
ALTER TABLE chamados ADD COLUMN valor_dono FLOAT;
ALTER TABLE chamados ADD COLUMN data_hora_inicio DATETIME;
ALTER TABLE chamados ADD COLUMN data_hora_fim DATETIME;

-- 2. Backfill: Calcular valores para registros antigos
UPDATE chamados
SET 
    valor_total = COALESCE(valor_final, valor_original, 0),
    comissao_plataforma = ROUND(COALESCE(valor_final, valor_original, 0) * 0.15, 2),
    valor_freelancer = ROUND(COALESCE(valor_final, valor_original, 0) * 0.45, 2),
    valor_dono = ROUND(COALESCE(valor_final, valor_original, 0) * 0.40, 2)
WHERE valor_total IS NULL;

-- 3. Mapear status antigos para novos (IMPORTANTE: fazer antes de deletar coluna)
UPDATE chamados SET status = 'pendente' WHERE status = 'ABERTO';
UPDATE chamados SET status = 'confirmado' WHERE status = 'ACEITO';
UPDATE chamados SET status = 'concluido' WHERE status = 'CONCLUÍDO';

-- 4. Verificar que tudo funcionou
SELECT 
    id, 
    status, 
    valor_total, 
    comissao_plataforma, 
    valor_freelancer, 
    valor_dono
FROM chamados
LIMIT 10;
```

## 🐍 Migração em Python (com SQLAlchemy)

Se estiver usando Alembic:

```bash
# Gerar migração automática
alembic revision --autogenerate -m "Add financial snapshot and datetime fields to Chamado"

# Rodar migração
alembic upgrade head
```

Se NÃO estiver usando Alembic (não recomendado):

```python
# arquivo: migrate_agendamento.py
from sqlalchemy import text
from app.database import engine

with engine.connect() as conn:
    # Adicionar colunas
    conn.execute(text("""
        ALTER TABLE chamados ADD COLUMN valor_total FLOAT;
        ALTER TABLE chamados ADD COLUMN comissao_plataforma FLOAT;
        ALTER TABLE chamados ADD COLUMN valor_freelancer FLOAT;
        ALTER TABLE chamados ADD COLUMN valor_dono FLOAT;
        ALTER TABLE chamados ADD COLUMN data_hora_inicio DATETIME;
        ALTER TABLE chamados ADD COLUMN data_hora_fim DATETIME;
    """))
    
    # Backfill dados
    conn.execute(text("""
        UPDATE chamados
        SET 
            valor_total = COALESCE(valor_final, valor_original, 0),
            comissao_plataforma = ROUND(COALESCE(valor_final, valor_original, 0) * 0.15, 2),
            valor_freelancer = ROUND(COALESCE(valor_final, valor_original, 0) * 0.45, 2),
            valor_dono = ROUND(COALESCE(valor_final, valor_original, 0) * 0.40, 2)
        WHERE valor_total IS NULL
    """))
    
    # Mapear status
    conn.execute(text("UPDATE chamados SET status = 'pendente' WHERE status = 'ABERTO'"))
    conn.execute(text("UPDATE chamados SET status = 'confirmado' WHERE status = 'ACEITO'"))
    conn.execute(text("UPDATE chamados SET status = 'concluido' WHERE status = 'CONCLUÍDO'"))
    
    conn.commit()
    print("✅ Migração concluída!")
```

## ✅ Checklist após Migração

- [ ] Campos novos adicionados ao banco
- [ ] Dados antigos importados com split de pagamento calculado
- [ ] Status migrados para novo esquema
- [ ] Testes com agendamentos antigos funcionando
- [ ] API retornando valores de snapshot corretamente
- [ ] Relatórios usando campos novos (não recalculando)

## 📝 Mudanças no Código

### app/models.py
```python
from enum import Enum

class StatusAgendamento(str, enum.Enum):
    PENDENTE = "pendente"
    CONFIRMADO = "confirmado"
    CONCLUIDO = "concluido"
    CANCELADO = "cancelado"

class Chamado(Base):
    # ... outros campos ...
    status = Column(String, default=StatusAgendamento.PENDENTE)
    valor_total = Column(Float, nullable=True)
    comissao_plataforma = Column(Float, nullable=True)
    valor_freelancer = Column(Float, nullable=True)
    valor_dono = Column(Float, nullable=True)
    data_hora_inicio = Column(DateTime, nullable=True)
    data_hora_fim = Column(DateTime, nullable=True)
```

### app/routes.py
```python
# Nova função helper
def calcular_split_pagamento(valor_total: float) -> dict:
    return {
        'valor_total': valor_total,
        'comissao_plataforma': round(valor_total * 0.15, 2),
        'valor_freelancer': round(valor_total * 0.45, 2),
        'valor_dono': round(valor_total - ... - ..., 2)  # Garante 100%
    }

# Usar ao criar agendamento
split = calcular_split_pagamento(servico.valor)
chamado = Chamado(
    valor_total=split['valor_total'],
    comissao_plataforma=split['comissao_plataforma'],
    valor_freelancer=split['valor_freelancer'],
    valor_dono=split['valor_dono'],
    status=StatusAgendamento.PENDENTE.value
)
```

### app/routes_relatorio.py
```python
# ANTES: recalcular percentuais
taxa = valor_servico * 0.15  # ❌ ERRADO

# DEPOIS: usar valores salvos
taxa = chamado.comissao_plataforma  # ✅ CORRETO
```

## 🚀 Deployment

1. **Backup do banco de dados** (SEMPRE!)
2. Rodar migração SQL
3. Deploy do código com novos modelos
4. Testar endpoints de agendamento
5. Verificar relatórios

## ⚠️ Comportamento Esperado Após Migração

✅ Novo agendamento com valor = 100:
```json
{
  "valor_total": 100.00,
  "comissao_plataforma": 15.00,
  "valor_freelancer": 45.00,
  "valor_dono": 40.00
}
```

✅ Agendamento antigo backfill:
```json
{
  "valor_total": 50.00,
  "comissao_plataforma": 7.50,
  "valor_freelancer": 22.50,
  "valor_dono": 20.00
}
```

✅ Status mapeados:
- "ABERTO" → "pendente"
- "ACEITO" → "confirmado"
- "CONCLUÍDO" → "concluido"

## 🐛 Troubleshooting

**Erro: "Coluna já existe"**
→ Coluna foi adicionada antes, apenas pule esse step

**Erro: "Status inválido"**
→ Verificar se o mapeamento de status foi completo

**Relatório mostrando valores errados**
→ Garantir que não está usando a função antiga de cálculo
