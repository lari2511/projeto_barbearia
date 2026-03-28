# 💰 ESTRUTURA DE RASTREAMENTO FINANCEIRO - BarberMovie

## 📋 Visão Geral

O sistema BarberMovie agora possui uma **estrutura completa de rastreamento financeiro** que registra cada etapa do fluxo de dinheiro:

```
Cliente paga R$ 100 pelo serviço
         ↓
    CORTE criado (tabela: cortes)
         ↓
    Automaticamente gera 3 TRANSAÇÕES:
    ├─ 70% (R$ 70) → Freelancer (tabela: transacoes_financeiras)
    ├─ 20% (R$ 20) → Dono da Barbearia (tabela: transacoes_financeiras)
    └─ 10% (R$ 10) → BarberMovie/Plataforma (tabela: transacoes_financeiras)
         ↓
    AUDITORIA COMPLETA: Você pode rastrear cada centavo
```

---

## 📊 Três Tabelas Fundamentais

### 1️⃣ **Tabela: `cortes`**
**O que é?** Registro de cada serviço realizado na plataforma.

**Propósito:** Tabela central que conecta cliente → barbeiro → barbearia → pagamento.

**Quando cria?** Quando um cliente finaliza o pagamento no checkout (TelaCheckoutCliente).

**Campos principais:**
```python
id: int (PK)
cliente_id: int (FK - Usuario)
freelancer_id: int (FK - Usuario, o barbeiro)
barbearia_id: int (FK - Barbearia)
servico_id: int (FK - Servico)
chamado_id: int (FK - Chamado)

valor_total: float          # R$ 100.00 (valor total cobrado)
metodo_pagamento: str       # PIX, CARTAO, DINHEIRO
status_pagamento: str       # aprovado, pendente, falhou

data_criacao: datetime
data_conclusao: datetime
```

**Exemplo:**
```json
{
  "id": 1,
  "cliente_id": 101,
  "freelancer_id": 25,
  "barbearia_id": 5,
  "valor_total": 100.00,
  "metodo_pagamento": "PIX",
  "status_pagamento": "aprovado",
  "data_criacao": "2026-03-04T14:30:00Z"
}
```

### 2️⃣ **Tabela: `transacoes_financeiras`**
**O que é?** Registro de CADA movimentação de dinheiro no sistema.

**Propósito:** Auditoria completa. Para cada "Corte", gera automaticamente **3 transações**.

**Quando cria?** Automaticamente quando um CORTE é criado.

**Campos principais:**
```python
id: int (PK)
corte_id: int (FK - Corte)       # Qual corte gerou esta transação

recebedor_id: int (FK - Usuario) # Quem recebe o dinheiro (freelancer, barbearia, ou admin)
tipo: str                         # comissao_freelancer, comissao_barbearia, taxa_plataforma
valor: float                      # R$ 70.00, R$ 20.00, R$ 10.00
percentual: float                 # 70%, 20%, 10%

status_repasse: str               # concluido, pendente, falhou, revertido
data_repasse: datetime            # Quando foi repassado efetivamente
motivo_falha: str                 # Se falhou, por quê?

data_transacao: datetime
```

**Exemplo (Corte de R$ 100 gera 3 transações):**

```json
[
  {
    "id": 1001,
    "corte_id": 1,
    "recebedor_id": 25,           # Freelancer/Barbeiro
    "tipo": "comissao_freelancer",
    "valor": 70.00,
    "percentual": 70,
    "status_repasse": "concluido",
    "data_transacao": "2026-03-04T14:31:00Z"
  },
  {
    "id": 1002,
    "corte_id": 1,
    "recebedor_id": 5,            # Dono da Barbearia
    "tipo": "comissao_barbearia",
    "valor": 20.00,
    "percentual": 20,
    "status_repasse": "concluido",
    "data_transacao": "2026-03-04T14:31:00Z"
  },
  {
    "id": 1003,
    "corte_id": 1,
    "recebedor_id": 1,            # Admin/BarberMovie
    "tipo": "taxa_plataforma",
    "valor": 10.00,
    "percentual": 10,
    "status_repasse": "concluido",
    "data_transacao": "2026-03-04T14:31:00Z"
  }
]
```

### 3️⃣ **Tabela: `assinaturas_barbearia`**
**O que é?** Registro mensal das cadeiras ativas da barbearia.

**Propósito:** Armazenar o número de cadeiras ativas (1-20) e calcular a mensalidade com desconto progressivo.

**Quando cria?** Quando uma barbearia se inscreve no BarberMovie.

**Tabela de Preços (FIXA):**
```
1ª cadeira: R$ 47,90
2ª cadeira: R$ 27,90
3ª cadeira: R$ 24,90
4ª cadeira: R$ 22,90
5ª cadeira: R$ 19,90
6+ cadeiras: R$ 17,90 (piso mínimo)
```

**Exemplos de cálculo:**
- 1 cadeira: R$ 47,90/mês (sem desconto)
- 2 cadeiras: R$ 75,80/mês (R$ 47,90 + R$ 27,90)
- 3 cadeiras: R$ 100,70/mês (R$ 47,90 + R$ 27,90 + R$ 24,90)
- 5 cadeiras: R$ 143,50/mês
- 10 cadeiras: R$ 233,00/mês

**Campos principais:**
```python
id: int (PK)
barbearia_id: int (FK - Barbearia, unique=True)

quantidade_cadeiras: int          # 1-20 (número ativo)
valor_mensalidade: float          # Quanto custa por mês
valor_por_cadeira: str            # JSON com breakdown: [47.90, 27.90, 24.90, ...]
economia_mensal: float            # Quanto economiza vs 1ª cadeira

dia_vencimento: int               # Dia do mês para cobrar (ex: 10)
proximo_vencimento: datetime      # Data exata do próximo vencimento

status: str                        # ativa, inadimplente, cancelada, suspensa
motivo_suspensao: str              # Se suspenso, por quê?

ultima_atualizacao: datetime      # Quando quantidade_cadeiras foi alterado
criado_em: datetime
cancelado_em: datetime            # Se foi cancelado
```

**Exemplo:**
```json
{
  "id": 1,
  "barbearia_id": 5,
  "quantidade_cadeiras": 3,
  "valor_mensalidade": 100.70,
  "valor_por_cadeira": "[47.90, 27.90, 24.90]",
  "economia_mensal": 43.00,
  "dia_vencimento": 10,
  "proximo_vencimento": "2026-04-10T00:00:00Z",
  "status": "ativa",
  "ultima_atualizacao": "2026-03-04T14:00:00Z"
}
```

### 4️⃣ **Tabela: `faturas_assinatura` (Extra)**
**O que é?** Histórico mensal de faturas geradas.

**Propósito:** Registrar cada fatura gerada para uma barbearia (para relatórios, auditorias, etc).

**Campos principais:**
```python
id: int (PK)
assinatura_id: int (FK - AssinaturaBarbearia)

mes_referencia: str               # YYYY-MM (ex: 2026-03)
data_inicio_periodo: datetime
data_fim_periodo: datetime

valor_fatura: float               # Valor cobrado
quantidade_cadeiras: int          # Snapshot de cadeiras no mês
data_vencimento: datetime
data_pagamento: datetime          # Quando foi pago
status: str                        # pendente, pago, vencido, cancelado
```

---

## 🔌 APIs Criadas

### **POST /api/v1/transacoes/cortes**
Criar um novo corte e gerar transações automaticamente.

```bash
curl -X POST "http://localhost:8000/api/v1/transacoes/cortes" \
  -H "Authorization: Bearer {token}" \
  -H "Content-Type: application/json" \
  -d '{
    "cliente_id": 101,
    "freelancer_id": 25,
    "barbearia_id": 5,
    "servico_id": 10,
    "chamado_id": 150,
    "valor_total": 100.00,
    "metodo_pagamento": "PIX"
  }'
```

**Resposta:**
```json
{
  "id": 1,
  "cliente_id": 101,
  "freelancer_id": 25,
  "barbearia_id": 5,
  "valor_total": 100.00,
  "metodo_pagamento": "PIX",
  "status_pagamento": "aprovado",
  "data_criacao": "2026-03-04T14:30:00Z"
}
```

### **GET /api/v1/transacoes/historico**
Listar histórico de transações do usuário logado.

```bash
curl -X GET "http://localhost:8000/api/v1/transacoes/historico?tipo=comissao_freelancer&limite=20" \
  -H "Authorization: Bearer {token}"
```

**Resposta:**
```json
[
  {
    "id": 1001,
    "corte_id": 1,
    "recebedor_id": 25,
    "tipo": "comissao_freelancer",
    "valor": 70.00,
    "percentual": 70,
    "status_repasse": "concluido",
    "data_transacao": "2026-03-04T14:31:00Z"
  },
  ...
]
```

### **GET /api/v1/transacoes/saldo**
Obter saldo disponível para saque (apenas para barbeiros).

```bash
curl -X GET "http://localhost:8000/api/v1/transacoes/saldo" \
  -H "Authorization: Bearer {token}"
```

**Resposta:**
```json
{
  "saldo_total": 1050.00,
  "saldo_bloqueado": 200.00,
  "saldo_disponivel": 850.00
}
```

### **GET /api/v1/transacoes/cortes**
Listar cortes com filtros (admin, barbeiro, barbearia ou cliente).

```bash
curl -X GET "http://localhost:8000/api/v1/transacoes/cortes?cliente_id=101&limite=50" \
  -H "Authorization: Bearer {token}"
```

### **GET /api/v1/transacoes/assinaturas/{barbearia_id}**
Obter detalhes da assinatura de uma barbearia.

```bash
curl -X GET "http://localhost:8000/api/v1/transacoes/assinaturas/5" \
  -H "Authorization: Bearer {token}"
```

**Resposta:**
```json
{
  "id": 1,
  "barbearia_id": 5,
  "quantidade_cadeiras": 3,
  "valor_mensalidade": 100.70,
  "economia_mensal": 43.00,
  "status": "ativa",
  "proximo_vencimento": "2026-04-10T00:00:00Z"
}
```

### **GET /api/v1/transacoes/faturas/{barbearia_id}**
Listar faturas de assinatura de uma barbearia.

```bash
curl -X GET "http://localhost:8000/api/v1/transacoes/faturas/5?limite=12" \
  -H "Authorization: Bearer {token}"
```

**Resposta:**
```json
[
  {
    "id": 1,
    "mes_referencia": "2026-03",
    "valor_fatura": 100.70,
    "quantidade_cadeiras": 3,
    "data_vencimento": "2026-03-10T00:00:00Z",
    "data_pagamento": "2026-03-08T15:30:00Z",
    "status": "pago"
  },
  ...
]
```

---

## 🔐 AUDITORIA COMPLETA

Se um barbeiro reclamar: **"Não recebi R$ 70 do corte de ontem"**

Você consegue: 
1. **Produzir prova** → Consultar `transacoes_financeiras` e mostrar que foi gerada
2. **Rastrear status** → Ver se foi "concluido", "pendente" ou "falhou"
3. **Encontrar problemas** → Se falhou, o motivo está em `motivo_falha`

**Exemplo de query SQL:**
```sql
-- Rastrear todas as comissões de um barbeiro em março
SELECT 
  tf.id as transacao_id,
  c.data_criacao,
  tf.tipo,
  tf.valor,
  tf.status_repasse,
  tf.motivo_falha
FROM transacoes_financeiras tf
JOIN cortes c ON tf.corte_id = c.id
WHERE tf.recebedor_id = 25  -- ID do barbeiro
  AND tf.tipo = 'comissao_freelancer'
  AND DATE_TRUNC('month', c.data_criacao) = '2026-03'
ORDER BY c.data_criacao DESC;
```

---

## 🚀 PRÓXIMOS PASSOS

1. **Rodar migrations** para criar as tabelas:
   ```bash
   python -c "from app.database import init_db; init_db()"
   ```

2. **Integrar com TelaCheckoutCliente** → Quando cliente confirma pagamento:
   ```javascript
   // Chamar API para criar corte
   const response = await fetch(`${API_URL}/api/v1/transacoes/cortes`, {
     method: 'POST',
     headers: {
       'Content-Type': 'application/json',
       'Authorization': `Bearer ${token}`
     },
     body: JSON.stringify({
       cliente_id: clienteId,
       freelancer_id: barbeiroDId,
       barbearia_id: barbeariaId,
       servico_id: servicoId,
       chamado_id: chamadoId,
       valor_total: valorServico,
       metodo_pagamento: metodoPagamento
     })
   });
   ```

3. **Criar job de faturas** (cron job mensal):
   - Ler `assinaturas_barbearia`
   - Gerar `faturas_assinatura`
   - Tentar cobrar via gateway (MercadoPago)

4. **Dashboard de auditoria** (admin):
   - Ver todos os cortes do período
   - Filtrar por status
   - Exportar relatórios

---

## 📝 EXEMPLO COMPLETO DE FLUXO

```
1. Cliente abre TelaCheckoutCliente (R$ 100)
   ↓
2. Seleciona PIX e clica "Confirmar Pagamento"
   ↓
3. Sistema chama POST /api/v1/transacoes/cortes
   ├─ Cria CORTE (id=1, valor_total=100, metodo=PIX)
   ├─ Cria TRANSACAO 1: freelancer recebe R$ 70
   ├─ Cria TRANSACAO 2: barbearia recebe R$ 20
   ├─ Cria TRANSACAO 3: plataforma recebe R$ 10
   ↓
4. Cliente entrega seu número de conta bancária
   ↓
5. Sistema processa saques via cron job:
   - Consulta GET /api/v1/transacoes/saldo → R$ 70 disponível
   - Solicita saque (saques.py) → POST /api/v1/saques/solicitar
   - Cria registro em saques (modelo Saque)
   - Transação com recebedor_id muda para status "processando"
   ↓
6. Barbeiro é creditado na conta bancária em 2 dias úteis
   - Admin processa via POST /api/v1/transacoes/processar-saque/{saque_id}
   - Status muda para "concluido"
   ↓
7. Admin faz auditoria completa:
   - Query em transacoes_financeiras filtra por barbeiro_id=25
   - Vê COMISSAO_FREELANCER status="concluido"
   - Vê SAQUE_PROCESSADO
   - Tudo bate ✅
```

---

**Seu sistema agora tem rastreamento financeiro de nível enterprise!** 🎉
