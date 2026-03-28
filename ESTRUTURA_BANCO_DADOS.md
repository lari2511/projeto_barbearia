# 🗄️ MUDANÇAS NO BANCO DE DADOS

## ✅ TABELAS A ADICIONAR

### 1. Tabela: `transacoes`

```sql
CREATE TABLE transacoes (
    id SERIAL PRIMARY KEY,
    usuario_id INTEGER NOT NULL REFERENCES usuario(id) ON DELETE CASCADE,
    tipo VARCHAR(20) NOT NULL,  -- 'credito' ou 'debito'
    valor FLOAT NOT NULL,
    descricao VARCHAR(255),
    status VARCHAR(20) DEFAULT 'disponivel',  -- 'disponivel' ou 'retencao'
    data_criacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    data_atualizacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Index para buscas rápidas
CREATE INDEX idx_transacoes_usuario_id ON transacoes(usuario_id);
CREATE INDEX idx_transacoes_data ON transacoes(data_criacao);
```

### 2. Tabela: `saques`

```sql
CREATE TABLE saques (
    id SERIAL PRIMARY KEY,
    usuario_id INTEGER NOT NULL REFERENCES usuario(id) ON DELETE CASCADE,
    valor FLOAT NOT NULL,
    status VARCHAR(20) DEFAULT 'pendente',  -- 'pendente', 'processando', 'concluido', 'rejeitado'
    banco VARCHAR(100),
    conta VARCHAR(20),
    agencia VARCHAR(10),
    motivo_rejeicao TEXT,
    data_solicitacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    data_processamento TIMESTAMP,
    data_conclusao TIMESTAMP
);

CREATE INDEX idx_saques_usuario_id ON saques(usuario_id);
CREATE INDEX idx_saques_status ON saques(status);
```

---

## 🔄 ALTERAÇÕES EM TABELAS EXISTENTES

### Tabela: `usuario`

Adicione as colunas:

```sql
-- Se ainda não existem
ALTER TABLE usuario ADD COLUMN IF NOT EXISTS saldo_disponivel FLOAT DEFAULT 0;
ALTER TABLE usuario ADD COLUMN IF NOT EXISTS saldo_em_retencao FLOAT DEFAULT 0;
ALTER TABLE usuario ADD COLUMN IF NOT EXISTS total_ganhos FLOAT DEFAULT 0;
ALTER TABLE usuario ADD COLUMN IF NOT EXISTS numero_avaliacoes INTEGER DEFAULT 0;
ALTER TABLE usuario ADD COLUMN IF NOT EXISTS soma_avaliacoes INTEGER DEFAULT 0;
ALTER TABLE usuario ADD COLUMN IF NOT EXISTS agencia VARCHAR(10);
ALTER TABLE usuario ADD COLUMN IF NOT EXISTS conta VARCHAR(20);
ALTER TABLE usuario ADD COLUMN IF NOT EXISTS banco VARCHAR(100);
ALTER TABLE usuario ADD COLUMN IF NOT EXISTS chave_pix VARCHAR(255);
```

### Tabela: `avaliacao`

Certifique-se que tem estas colunas:

```sql
ALTER TABLE avaliacao ADD COLUMN IF NOT EXISTS avaliador_nome VARCHAR(255);
ALTER TABLE avaliacao ADD COLUMN IF NOT EXISTS data_criacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP;
```

---

## 🔧 SCRIPT PYTHON PARA CRIAR ESTRUTURA

**Arquivo**: `criar_estrutura_pagamentos.py`

```python
#!/usr/bin/env python3
"""Script para criar tabelas de pagamentos"""

from app.database import engine, Base
from app.models import *  # Importa todos os modelos
from sqlalchemy import Column, Integer, Float, String, DateTime, ForeignKey, Index, func
from sqlalchemy.orm import relationship
from datetime import datetime

# Criar as tabelas
Base.metadata.create_all(bind=engine)

print("✅ Tabelas criadas com sucesso!")

# Adicionar colunas se não existirem
from sqlalchemy import inspect, text

def adicionar_coluna_se_nao_existir(engine, tabela, coluna, tipo):
    """Adiciona coluna se não existir"""
    inspector = inspect(engine)
    colunas_existentes = [c['name'] for c in inspector.get_columns(tabela)]
    
    if coluna not in colunas_existentes:
        with engine.connect() as conn:
            conn.execute(text(f"ALTER TABLE {tabela} ADD COLUMN {coluna} {tipo}"))
            conn.commit()
        print(f"✅ Coluna {tabela}.{coluna} criada")
    else:
        print(f"⚠️  Coluna {tabela}.{coluna} já existe")

# Adicionar colunas em usuario
print("\n📝 Adicionando colunas em usuario...")
adicionar_coluna_se_nao_existir(engine, 'usuario', 'saldo_disponivel', 'FLOAT DEFAULT 0')
adicionar_coluna_se_nao_existir(engine, 'usuario', 'saldo_em_retencao', 'FLOAT DEFAULT 0')
adicionar_coluna_se_nao_existir(engine, 'usuario', 'agencia', 'VARCHAR(10)')
adicionar_coluna_se_nao_existir(engine, 'usuario', 'conta', 'VARCHAR(20)')
adicionar_coluna_se_nao_existir(engine, 'usuario', 'banco', 'VARCHAR(100)')
adicionar_coluna_se_nao_existir(engine, 'usuario', 'chave_pix', 'VARCHAR(255)')

print("\n✅ Estrutura de pagamentos pronta!")
```

**Execute com**:
```bash
python criar_estrutura_pagamentos.py
```

---

## 📊 RELACIONAMENTOS

```
Usuario (1) ──< Transacao (N)
Usuario (1) ──< Saque (N)
Usuario (1) ──< Avaliacao (N)
```

---

## 🔐 INDICES DE PERFORMANCE

```sql
-- Índices principais
CREATE INDEX idx_transacoes_usuario_id ON transacoes(usuario_id);
CREATE INDEX idx_transacoes_data ON transacoes(data_criacao DESC);
CREATE INDEX idx_transacoes_status ON transacoes(status);

CREATE INDEX idx_saques_usuario_id ON saques(usuario_id);
CREATE INDEX idx_saques_status ON saques(status);
CREATE INDEX idx_saques_data ON saques(data_solicitacao DESC);

-- Para avaliações
CREATE INDEX idx_avaliacao_avaliado_id ON avaliacao(avaliado_id);
CREATE INDEX idx_avaliacao_data ON avaliacao(criado_em DESC);
```

---

## 🧪 TESTES BÁSICOS

```python
from app.database import SessionLocal
from app import models
from datetime import datetime

db = SessionLocal()

# Criar transação de teste
trans = models.Transacao(
    usuario_id=1,
    tipo="credito",
    valor=50.0,
    descricao="Corte de cabelo",
    status="disponivel"
)
db.add(trans)
db.commit()

# Buscar transações
transacoes = db.query(models.Transacao).filter(
    models.Transacao.usuario_id == 1
).all()

print(f"✅ {len(transacoes)} transações encontradas")
```

---

## 📋 MIGRATIONS (se usar Alembic)

```bash
# Gerar migration
alembic revision --autogenerate -m "Adicionar tabelas de pagamento"

# Aplicar migration
alembic upgrade head
```

---

## ✅ CHECKLIST

- [ ] Tabela `transacoes` criada
- [ ] Tabela `saques` criada
- [ ] Colunas adicionadas em `usuario`
- [ ] Índices criados
- [ ] Script Python testado
- [ ] Dados de teste inseridos
- [ ] Backups realizados

---

## 💾 BACKUP ANTES DE FAZER MUDANÇAS!

```bash
# PostgreSQL
pg_dump -U usuario -h localhost barbearia_db > backup_antes_mudancas.sql

# SQLite
cp barbearia.db barbearia_backup.db
```

Restaurar se necessário:
```bash
# PostgreSQL
psql -U usuario -h localhost barbearia_db < backup.sql

# SQLite
cp barbearia_backup.db barbearia.db
```

---

Pronto! O banco está configurado para suportar pagamentos e avaliações! 🎉
