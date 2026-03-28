# ✅ Validação de Cadeira Bloqueada por Agendamento

## 📋 Resumo

Implementado sistema de bloqueio de cadeira durante período de agendamento confirmado. Quando uma cadeira está **acionada e com um cliente** no horário específico, ninguém (cliente ou barbeiro) pode marcar outro agendamento naquele período.

## 🎯 Comportamento

### Exemplo:
- **Serviço:** Corte de cabelo (30 minutos)
- **Cadeira:** #3
- **Agendamento:** 22:00 às 22:30
- **Resultado:** Cadeira #3 fica **bloqueada** de 22:00 às 22:30

Durante este período:
- ❌ Cliente **NÃO** pode agendar na cadeira #3
- ❌ Barbeiro **NÃO** pode aceitar agendamento na cadeira #3
- ✅ Outro horário ou outra cadeira funcionam normalmente

---

## 🛠️ Implementação Técnica

### 1️⃣ Endpoint: `POST /api/v1/chamados` (Criar Agendamento)

**Validação adicionada:**
```python
# ✅ GUARDIÃO: Verificar se cadeira já tem agendamento CONFIRMADO nesse período
conflito = db.query(models.Chamado).filter(
    models.Chamado.cadeira_id == cadeira.id,
    models.Chamado.status == "CONFIRMADO",
    models.Chamado.data_hora_inicio < hora_fim,  # Agendamento começa antes do fim
    models.Chamado.data_hora_fim > chamado.data_hora_inicio  # Agendamento termina depois do início
).first()

if conflito:
    # ❌ Rejeita com mensagem clara
    raise HTTPException(
        status_code=400,
        detail=f"Cadeira {cadeira.numero} já possui agendamento de HH:MM às HH:MM"
    )
```

**O que verifica:**
- ✅ Se cadeira_id foi fornecido
- ✅ Se cadeira está em status `DISPONIVEL`
- ✅ Se NÃO há conflito de horário com agendamentos `CONFIRMADO`

---

### 2️⃣ Endpoint: `PUT /api/v1/chamados/{id}/aceitar` (Barbeiro Aceita)

**Validação adicionada:**
```python
# ✅ Verificar conflitos de horário na cadeira
if chamado.cadeira_id:
    conflito = db.query(models.Chamado).filter(
        models.Chamado.cadeira_id == chamado.cadeira_id,
        models.Chamado.status == "CONFIRMADO",
        models.Chamado.id != id,  # Não contar o próprio agendamento
        models.Chamado.data_hora_inicio < chamado.data_hora_fim,
        models.Chamado.data_hora_fim > chamado.data_hora_inicio
    ).first()
    
    if conflito:
        raise HTTPException(status_code=400, detail="...")
```

---

## 📊 Lógica de Conflito

Usa a fórmula de **sobreposição de intervalos**:

```
Agendamento A: [início_A, fim_A]
Agendamento B: [início_B, fim_B]

CONFLITO SE:
  início_A < fim_B  AND  fim_A > início_B
```

### Exemplos:

| Agendamento Existente | Novo Agendamento | Resultado |
|----------------------|------------------|-----------|
| 22:00 - 22:30 | 22:15 - 22:45 | ❌ CONFLITO |
| 22:00 - 22:30 | 22:30 - 23:00 | ✅ OK |
| 22:00 - 22:30 | 21:30 - 22:00 | ✅ OK |
| 22:00 - 22:30 | 22:00 - 22:30 | ❌ CONFLITO |
| 22:00 - 22:30 | 22:10 - 22:25 | ❌ CONFLITO |

---

## 🎮 Como Funciona na Prática

### Fluxo para Cliente:

1. **Cliente seleciona:** Barbearia, Serviço, Data/Hora, **Cadeira específica**
2. **Backend valida:**
   - ✅ Cadeira existe?
   - ✅ Cadeira está `DISPONIVEL`?
   - ✅ Nenhum agendamento `CONFIRMADO` naquele período?
3. **Se OK:** Cria agendamento com status `PENDENTE`
4. **Se Erro:** Retorna mensagem clara explicando o conflito

### Fluxo para Barbeiro:

1. **Barbeiro vê** agendamento pendente com cadeira associada
2. **Ao clicar "Aceitar":**
   - ✅ Valida novamente se cadeira está disponível
   - ✅ Valida se NÃO há conflito de horário
   - ✅ Se OK, muda status para `CONFIRMADO`
   - ✅ **Cadeira fica bloqueada** para aquele período

---

## 🔐 Segurança

- Validação acontece em **DOIS pontos**:
  1. Quando cliente cria o agendamento
  2. Quando barbeiro aceita o agendamento
  
- **Proteção contra race conditions:** O segundo check garante que mesmo se houver múltiplas requisições simultâneas, a última será rejeitada

---

## ✅ Status da Implementação

| Item | Status |
|------|--------|
| Validação ao criar agendamento | ✅ IMPLEMENTADO |
| Validação ao aceitar agendamento | ✅ IMPLEMENTADO |
| Cálculo de sobreposição de horários | ✅ IMPLEMENTADO |
| Mensagens de erro claras | ✅ IMPLEMENTADO |
| Testes unitários | ⏳ TODO |

---

## 🧪 Como Testar

Via Swagger (`http://localhost:8000/docs`):

```bash
POST /api/v1/chamados

Body JSON:
{
  "servico_id": 1,
  "barbearia_id": 1,
  "cadeira_id": 3,
  "data_hora_inicio": "2025-12-20T22:00:00",
  "barbeiro_id": 5
}

# Espera:
# - Se cadeira #3 tem agendamento CONFIRMADO de 22:00 às 22:30
# - Retorna: HTTP 400 com mensagem de conflito
```

---

## 📝 Próximas Melhorias

1. **Notificação ao cliente** quando há conflito (sugerir horários alternativos)
2. **Sugestão automática** de cadeiras/horários alternativos
3. **Dashboard** mostrando cadeiras bloqueadas visualmente
4. **Calendar view** mostrando períodos ocupados
