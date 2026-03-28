# 🧪 TESTE COMPLETO - SISTEMA DE STATUS DO FREELANCER

## 📋 Checklist de Testes

Use este guia para testar todos os fluxos do sistema de status do freelancer implementado.

---

## 1️⃣ TESTE: Endpoint de Mudar Status

### 1.1 - Mudar para OFFLINE

**Endpoint:** `PUT /barbeiro/status`

**Request:**
```json
{
    "status": "offline"
}
```

**Expected Response (200):**
```json
{
    "success": true,
    "message": "Status atualizado para OFFLINE",
    "status": "offline",
    "offline": true,
    "online_regiao": false,
    "presente_em_local": false,
    "barbearia_atual_id": null,
    "horario_chegada": null
}
```

**Validação:**
- [ ] Status muda para "offline"
- [ ] offline = true
- [ ] online_regiao = false
- [ ] presente_em_local = false

---

### 1.2 - Mudar para ONLINE_REGION

**Endpoint:** `PUT /barbeiro/status`

**Request:**
```json
{
    "status": "online_region"
}
```

**Expected Response (200):**
```json
{
    "success": true,
    "message": "Status atualizado para ONLINE_REGIÃO",
    "status": "online_region",
    "offline": false,
    "online_regiao": true,
    "presente_em_local": false,
    "barbearia_atual_id": null,
    "horario_chegada": null
}
```

**Validação:**
- [ ] Status muda para "online_region"
- [ ] offline = false
- [ ] online_regiao = true
- [ ] presente_em_local = false

---

### 1.3 - Mudar para PRESENT_LOCAL

**Endpoint:** `PUT /barbeiro/status`

**Request:**
```json
{
    "status": "present_local",
    "barbearia_id": 1
}
```

**Expected Response (200):**
```json
{
    "success": true,
    "message": "Status atualizado para PRESENTE EM Barbearia XYZ",
    "status": "present_local",
    "offline": false,
    "online_regiao": false,
    "presente_em_local": true,
    "barbearia_atual_id": 1,
    "horario_chegada": "2026-02-20T14:30:00"
}
```

**Validação:**
- [ ] Status muda para "present_local"
- [ ] offline = false
- [ ] presente_em_local = true
- [ ] barbearia_atual_id = 1
- [ ] horario_chegada é timestamp recente

---

### 1.4 - Erro: PRESENT_LOCAL sem barbearia_id

**Endpoint:** `PUT /barbeiro/status`

**Request:**
```json
{
    "status": "present_local"
}
```

**Expected Response (400):**
```json
{
    "detail": "barbearia_id é obrigatório quando status = 'present_local'"
}
```

**Validação:**
- [ ] Retorna 400
- [ ] Mensagem de erro clara

---

### 1.5 - Erro: Status inválido

**Endpoint:** `PUT /barbeiro/status`

**Request:**
```json
{
    "status": "invalid_status"
}
```

**Expected Response (400):**
```json
{
    "detail": "Status inválido. Use: 'offline', 'online_region' ou 'present_local'"
}
```

**Validação:**
- [ ] Retorna 400
- [ ] Lista status válidos

---

## 2️⃣ TESTE: Criar Chamado com Validação de Status

### 2.1 - Criar Chamado com Barbeiro OFFLINE (deve falhar)

**Setup:**
1. Barbeiro está com status OFFLINE

**Endpoint:** `POST /chamados`

**Request:**
```json
{
    "servico_id": 1,
    "barbearia_id": 1,
    "barbeiro_id": 2,
    "data_hora_inicio": "2026-02-20T15:00:00",
    "cadeira_id": null
}
```

**Expected Response (400):**
```json
{
    "detail": "Barbeiro está OFFLINE. Não pode receber chamados."
}
```

**Validação:**
- [ ] Chamado NÃO é criado
- [ ] Retorna 400
- [ ] Mensagem clara sobre status OFFLINE

---

### 2.2 - Criar Chamado com Barbeiro PRESENT_LOCAL em Barbearia Diferente (deve falhar)

**Setup:**
1. Barbeiro está com status PRESENT_LOCAL na Barbearia 1
2. Tentir criar chamado na Barbearia 2

**Endpoint:** `POST /chamados`

**Request:**
```json
{
    "servico_id": 1,
    "barbearia_id": 2,
    "barbeiro_id": 3,
    "data_hora_inicio": "2026-02-20T15:00:00"
}
```

**Expected Response (400):**
```json
{
    "detail": "Barbeiro está PRESENTE em Barbearia 1. Não pode receber chamados de outro local."
}
```

**Validação:**
- [ ] Chamado NÃO é criado
- [ ] Retorna 400
- [ ] Identifica a barbearia correta

---

### 2.3 - Criar Chamado com Barbeiro PRESENT_LOCAL na Mesma Barbearia (deve funcionar)

**Setup:**
1. Barbeiro está com status PRESENT_LOCAL na Barbearia 1
2. Criar chamado na mesma Barbearia 1

**Endpoint:** `POST /chamados`

**Request:**
```json
{
    "servico_id": 1,
    "barbearia_id": 1,
    "barbeiro_id": 3,
    "data_hora_inicio": "2026-02-20T15:00:00"
}
```

**Expected Response (200):**
```json
{
    "id": 100,
    "status": "pendente",
    "cliente_id": 1,
    "servico_id": 1,
    "descricao": "Corte de Cabelo",
    "valor": 50.00
}
```

**Validação:**
- [ ] Chamado É criado
- [ ] Retorna 200
- [ ] chamado.id está preenchido

---

### 2.4 - Criar Chamado com Barbeiro ONLINE_REGION em Qualquer Barbearia (deve funcionar)

**Setup:**
1. Barbeiro está com status ONLINE_REGION
2. Criar chamado em Barbearia 1

**Endpoint:** `POST /chamados`

**Request:**
```json
{
    "servico_id": 1,
    "barbearia_id": 1,
    "barbeiro_id": 4,
    "data_hora_inicio": "2026-02-20T16:00:00"
}
```

**Expected Response (200):**
```json
{
    "id": 101,
    "status": "pendente",
    "cliente_id": 1,
    "servico_id": 1,
    "descricao": "Corte de Cabelo",
    "valor": 50.00
}
```

**Validação:**
- [ ] Chamado É criado
- [ ] Retorna 200

---

## 3️⃣ TESTE: Aceitar Chamado com Validação de Status

### 3.1 - Aceitar Chamado com Barbeiro OFFLINE (deve falhar)

**Setup:**
1. Barbeiro está com status OFFLINE
2. Tem um chamado PENDENTE

**Endpoint:** `PUT /chamados/{id}/aceitar`

**Expected Response (400):**
```json
{
    "detail": "Você está OFFLINE. Mude seu status para ONLINE ou PRESENTE antes de aceitar chamados."
}
```

**Validação:**
- [ ] Chamado NÃO é aceito
- [ ] Retorna 400
- [ ] Status do chamado permanece PENDENTE

---

### 3.2 - Aceitar Chamado com Barbeiro PRESENT_LOCAL em Barbearia Diferente (deve falhar)

**Setup:**
1. Barbeiro está com status PRESENT_LOCAL na Barbearia 1
2. Tem um chamado PENDENTE da Barbearia 2

**Endpoint:** `PUT /chamados/{id}/aceitar`

**Expected Response (400):**
```json
{
    "detail": "Você está PRESENTE em Barbearia 1. Não pode aceitar chamados de outro local."
}
```

**Validação:**
- [ ] Chamado NÃO é aceito
- [ ] Retorna 400
- [ ] Status do chamado permanece PENDENTE

---

### 3.3 - Aceitar Chamado com Barbeiro PRESENT_LOCAL na Mesma Barbearia (deve funcionar)

**Setup:**
1. Barbeiro está com status PRESENT_LOCAL na Barbearia 1
2. Tem um chamado PENDENTE da Barbearia 1

**Endpoint:** `PUT /chamados/{id}/aceitar`

**Expected Response (200):**
```json
{
    "id": 100,
    "status": "confirmado"
}
```

**Validação:**
- [ ] Chamado É aceito
- [ ] Retorna 200
- [ ] Status muda para CONFIRMADO

---

### 3.4 - Aceitar Chamado com Barbeiro ONLINE_REGION em Qualquer Barbearia (deve funcionar)

**Setup:**
1. Barbeiro está com status ONLINE_REGION
2. Tem um chamado PENDENTE de qualquer barbearia

**Endpoint:** `PUT /chamados/{id}/aceitar`

**Expected Response (200):**
```json
{
    "id": 101,
    "status": "confirmado"
}
```

**Validação:**
- [ ] Chamado É aceito
- [ ] Retorna 200

---

## 4️⃣ TESTE: Filtros em Busca de Barbeiros

### 4.1 - GET /barbeiros/proximos - Excluir PRESENT_LOCAL

**Setup:**
1. Barbeiro A está ONLINE_REGION
2. Barbeiro B está PRESENT_LOCAL
3. Ambos dentro do raio de 10km

**Endpoint:** `GET /barbeiros/proximos?latitude=-23.5505&longitude=-46.6333&raio_km=10`

**Expected Response:**
```json
[
    {
        "id": 1,
        "nome": "Barbeiro A",
        "presente_em_local": false,
        "barbearia_atual_id": null,
        "online_regiao": true,
        "distancia_km": 2.5
    }
]
```

**Validação:**
- [ ] Barbeiro A aparece (ONLINE_REGION)
- [ ] Barbeiro B NÃO aparece (PRESENT_LOCAL)
- [ ] Lista tem apenas 1 resultado
- [ ] Campo `presente_em_local` = false

---

### 4.2 - GET /barbeiros/todos - Excluir PRESENT_LOCAL

**Setup:**
1. Barbeiro A está ONLINE_REGION
2. Barbeiro B está PRESENT_LOCAL
3. Ambos com `perfil_aprovado` = true

**Endpoint:** `GET /barbeiros/todos`

**Expected Response:**
```json
[
    {
        "id": 1,
        "nome": "Barbeiro A",
        "presente_em_local": false,
        "online_regiao": true,
        ...
    },
    {
        "id": 3,
        "nome": "Barbeiro C",
        "presente_em_local": false,
        "online_regiao": true,
        ...
    }
]
```

**Validação:**
- [ ] Barbeiro A aparece (ONLINE_REGION)
- [ ] Barbeiro B NÃO aparece (PRESENT_LOCAL)
- [ ] Barbeiro C aparece (ONLINE_REGION)
- [ ] Todos têm `presente_em_local` = false

---

## 5️⃣ TESTE: Fluxo Completo de Atendimento

### Cenário: Barbeiro Recebe e Atende Chamado em Barbearia

**Passo 1: Barbeiro muda para ONLINE**
```
PUT /barbeiro/status
{
    "status": "online_region"
}

✅ Barbeiro aparece em buscas regionais
✅ Pode receber chamados de qualquer barbearia
```

**Passo 2: Cliente cria chamado na Barbearia A**
```
POST /chamados
{
    "servico_id": 1,
    "barbearia_id": 1,
    "barbeiro_id": 2,
    "data_hora_inicio": "2026-02-20T15:00:00"
}

✅ Chamado criado
✅ Status = PENDENTE
```

**Passo 3: Barbeiro vai para local e muda para PRESENT_LOCAL**
```
PUT /barbeiro/status
{
    "status": "present_local",
    "barbearia_id": 1
}

✅ Status muda para PRESENT_LOCAL
❌ Barbeiro desaparece de busca regional
```

**Passo 4: Barbeiro aceita chamado da Barbearia A (mesmo local)**
```
PUT /chamados/{id}/aceitar

✅ Chamado aceito
✅ Status = CONFIRMADO
```

**Passo 5: Cliente tenta criar novo chamado em Barbearia B**
```
POST /chamados
{
    "servico_id": 1,
    "barbearia_id": 2,
    "barbeiro_id": 2,
    ...
}

❌ Erro 400: "Barbeiro está PRESENTE em Barbearia A..."
✅ Barbeiro está protegido de conflito
```

**Passo 6: Barbeiro finaliza e volta ONLINE**
```
PUT /barbeiro/status
{
    "status": "online_region"
}

✅ Status muda para ONLINE_REGION
✅ Barbeiro reaparece em buscas regionais
✅ Pode rodar novamente
```

---

## 🎯 Checklist Final

- [ ] ✅ ENUM `StatusFreelancer` criado em models.py
- [ ] ✅ Schema `AtualizarStatusFreelancer` criado em schemas.py
- [ ] ✅ Endpoint `PUT /barbeiro/status` implementado
- [ ] ✅ Validação na criação de chamado
- [ ] ✅ Validação ao aceitar chamado
- [ ] ✅ Filtro em `GET /barbeiros/proximos`
- [ ] ✅ Filtro em `GET /barbeiros/todos`
- [ ] ✅ Módulos importam sem erros
- [ ] ✅ Todos os 5 testes básicos passaram
- [ ] ✅ Fluxo completo de atendimento funciona

---

## 🚀 Como Testar via Swagger

1. Abrir: `http://localhost:8000/docs`
2. Naveir até "Barbeiro"
3. Procurar por `PUT /barbeiro/status`
4. Clicar em "Try it out"
5. Preencher body com JSON de teste
6. Clicar "Execute"
7. Ver resposta em "Response"

---

**Status:** Pronto para testes
**Data:** 20 de Fevereiro de 2026

