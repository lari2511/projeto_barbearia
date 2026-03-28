# ✅ SISTEMA DE STATUS DO FREELANCER - IMPLEMENTAÇÃO COMPLETA

## 📋 Especificação Técnica

Sistema de controle de status do freelancer (barbeiro) para evitar conflito de chamados quando ele estiver em diferentes situações.

---

## 🧩 MODELAGEM DE STATUS

### ENUM: `StatusFreelancer`
```python
class StatusFreelancer(str, enum.Enum):
    OFFLINE = "offline"                    # Não pode receber chamados
    ONLINE_REGION = "online_region"        # Disponível para qualquer barbearia da região
    PRESENT_LOCAL = "present_local"        # Presente em uma barbearia específica
```

### Campos no Banco de Dados (Usuario)
```python
offline: Boolean = False                   # Status OFFLINE
online_regiao: Boolean = False            # Status ONLINE_REGION
presente_em_local: Boolean = False        # Status PRESENT_LOCAL
barbearia_atual_id: Integer FK            # Barbearia onde está presente (PRESENT_LOCAL)
horario_chegada: DateTime                 # Horário que chegou na barbearia
disponivel: Boolean = False               # Flag de disponibilidade
```

---

## 🔘 REGRAS DE NEGÓCIO

### 1️⃣ STATUS: OFFLINE
- ❌ Não pode receber chamados
- ❌ Não aparece em buscas
- ❌ `barbearia_atual_id` = null
- ❌ `disponivel` = false

**Validação:**
```
if freelancer.offline == True:
    ➜ Bloquear criação de chamado
    ➜ Bloquear aceitação de chamado
    ➜ Retornar erro 400
```

---

### 2️⃣ STATUS: ONLINE_REGION
- ✅ Pode receber chamados de qualquer barbearia da região
- ✅ Aparece como disponível globalmente em buscas
- ✅ `barbearia_atual_id` = null
- ✅ `disponivel` = true

**Validação:**
```
if freelancer.online_regiao == True:
    ➜ Permitir criação de chamado em qualquer barbearia
    ➜ Permitir aceitação de chamado em qualquer barbearia
    ➜ Incluir em GET /barbeiros/proximos
    ➜ Incluir em GET /barbeiros/todos
```

---

### 3️⃣ STATUS: PRESENT_LOCAL
- ✅ **Obrigatório** ter `barbearia_atual_id` preenchido
- ✅ Só pode receber chamados dessa barbearia
- ❌ Não aparece em buscas regionais (GET /barbeiros/proximos, GET /barbeiros/todos)
- ❌ Não pode receber chamado de outra barbearia
- ✅ `disponivel` = true

**Validações:**
```
if freelancer.presente_em_local == True:
    1. Se barbearia_id do chamado != barbearia_atual_id:
       ➜ Bloquear criação de chamado → erro 400
       ➜ Bloquear aceitação de chamado → erro 400
    
    2. Ao listar barbeiros:
       ➜ Excluir de GET /barbeiros/proximos
       ➜ Excluir de GET /barbeiros/todos
       ➜ Aparecer APENAS para sua barbearia específica
```

---

## 🔒 LÓGICA DE FILTRAGEM DE CHAMADO

### Ao Criar Chamado (POST /chamados)

```python
# Validação 1: Verificar se barbeiro está offline
if chamado.barbeiro_id:
    barbeiro = get_usuario(chamado.barbeiro_id)
    
    if barbeiro.offline:
        ➜ HTTPException(400, "Barbeiro está OFFLINE. Não pode receber chamados.")
    
    # Validação 2: Se PRESENT_LOCAL, verificar barbearia
    if barbeiro.presente_em_local and barbeiro.barbearia_atual_id:
        if barbeiro.barbearia_atual_id != chamado.barbearia_id:
            nome_barb = get_barbearia(barbeiro.barbearia_atual_id).nome
            ➜ HTTPException(400, f"Barbeiro está PRESENTE em {nome_barb}. 
                                   Não pode receber chamados de outro local.")
```

### Ao Aceitar Chamado (PUT /chamados/{id}/aceitar)

```python
# Validação 1: Verificar se barbeiro está offline
barbeiro = get_current_user()

if barbeiro.offline:
    ➜ HTTPException(400, "Você está OFFLINE. Mude seu status para ONLINE ou PRESENTE 
                         antes de aceitar chamados.")

# Validação 2: Se PRESENT_LOCAL, verificar barbearia
if barbeiro.presente_em_local and barbeiro.barbearia_atual_id:
    if barbeiro.barbearia_atual_id != chamado.barbearia_id:
        nome_barb = get_barbearia(barbeiro.barbearia_atual_id).nome
        ➜ HTTPException(400, f"Você está PRESENTE em {nome_barb}. 
                               Não pode aceitar chamados de outro local.")
```

### Ao Listar Barbeiros (GET /barbeiros/proximos)

```python
# Query filtra:
barbeiros = db.query(Usuario).filter(
    Usuario.tipo == "barbeiro",
    Usuario.perfil_aprovado == True,
    Usuario.disponivel == True,
    Usuario.latitude.isnot(None),
    Usuario.longitude.isnot(None),
    or_(
        Usuario.presente_em_local == False,  # ❌ Excluir PRESENT_LOCAL
        Usuario.presente_em_local.is_(None)
    )
).all()
```

### Ao Listar Todos Barbeiros (GET /barbeiros/todos)

```python
# Query filtra:
barbeiros = db.query(Usuario).filter(
    Usuario.tipo == "barbeiro",
    or_(
        Usuario.presente_em_local == False,  # ❌ Excluir PRESENT_LOCAL
        Usuario.presente_em_local.is_(None)
    )
).all()
```

---

## 🔁 TROCA DE STATUS

### Endpoint: `PUT /barbeiro/status`

**Request:**
```json
{
    "status": "online_region",
    "barbearia_id": null
}
```

**Tipos de Status Permitidos:**
- `"offline"`
- `"online_region"`
- `"present_local"` (requer `barbearia_id`)

### Ao Clicar OFFLINE

```
POST /barbeiro/status
{
    "status": "offline"
}

Resultado:
- offline = true
- online_regiao = false
- presente_em_local = false
- barbearia_atual_id = null
- disponivel = false
```

### Ao Clicar ONLINE

```
POST /barbeiro/status
{
    "status": "online_region"
}

Resultado:
- offline = false
- online_regiao = true
- presente_em_local = false
- barbearia_atual_id = null
- disponivel = true
```

### Ao Clicar PRESENTE NO LOCAL

```
POST /barbeiro/status
{
    "status": "present_local",
    "barbearia_id": 1
}

Validação:
- barbearia_id é obrigatório
- barbearia_id deve existir no banco

Resultado:
- offline = false
- online_regiao = false
- presente_em_local = true
- barbearia_atual_id = 1
- horario_chegada = NOW()
- disponivel = true
```

---

## ✂️ FLUXO DE ATENDIMENTO

### Cenário 1: Barbeiro Recebe Chamado da Barbearia A

```
1. Cliente faz chamado na Barbearia A
2. Barbeiro vê chamado (se está ONLINE ou se é da Barbearia A)
3. Barbeiro aceita chamado
4. Barbeiro vai até o local Barbearia A
5. Barbeiro clica "PRESENTE NO LOCAL" (Barbearia A)
   - Status muda para PRESENT_LOCAL
   - barbearia_atual_id = 1 (Barbearia A)
   
6. Agora barbeiro:
   - ✅ Pode receber chamados APENAS da Barbearia A
   - ❌ Não aparece em busca regional
   - ❌ Não pode aceitar chamados de Barbearia B
   
7. Barbeiro finaliza corte
```

### Cenário 2: Barbeiro Termina Serviço - Opções

```
Opção A: Permanecer PRESENTE
- Continua recebendo apenas de Barbearia A
- Pronto para próximo cliente

Opção B: Voltar ONLINE
- Clica "ONLINE" para liberar de Barbearia A
- Status muda para ONLINE_REGION
- Pode rodar entre qualquer barbearia
- Aparece novamente em busca regional
```

---

## 🚨 REGRA CRÍTICA

### Enquanto `status = PRESENT_LOCAL`:

```
❌ Não pode aparecer na listagem regional
   - GET /barbeiros/proximos ➜ EXCLUÍDO
   - GET /barbeiros/todos ➜ EXCLUÍDO
   - Filtro: or_(presente_em_local == False, presente_em_local.is_(None))

❌ Não pode receber push de outra barbearia
   - POST /chamados with different barbearia_id ➜ erro 400

❌ Não pode aceitar chamado externo
   - PUT /chamados/{id}/aceitar with different barbearia_id ➜ erro 400

✅ Só pode fazer serviços na sua barbearia atual
```

---

## 📊 TABELA DE RESUMO

| Status | OFFLINE | ONLINE_REGION | PRESENT_LOCAL |
|--------|---------|---------------|---------------|
| Recebe chamado regional | ❌ | ✅ | ❌ |
| Recebe chamado da barbearia | ❌ | ✅ | ✅ (apenas sua) |
| Aparece em busca regional | ❌ | ✅ | ❌ |
| `offline` flag | `true` | `false` | `false` |
| `online_regiao` flag | `false` | `true` | `false` |
| `presente_em_local` flag | `false` | `false` | `true` |
| `barbearia_atual_id` | null | null | barberia_id |
| `disponivel` flag | `false` | `true` | `true` |
| `horario_chegada` | null | null | timestamp |

---

## 🧠 RESULTADO ESPERADO

✅ **Zero conflito de agenda**
- Barbeiro PRESENT_LOCAL não recebe de múltiplas barbearias
- Não pode estar em 2 lugares ao mesmo tempo

✅ **Zero duplicidade de local**
- Busca regional não mostra PRESENT_LOCAL
- Cliente não vê barbeiro em sua barbearia se estiver em outra

✅ **Controle total de operação**
- Barbeiro controla seu próprio status
- 3 estados bem definidos e exclusivos
- Validações em criação e aceitação de chamado

✅ **Experiência organizada**
- Interface simples: 3 botões (OFFLINE, ONLINE, PRESENTE)
- Fluxo intuitivo
- Sem confusão operacional

---

## 🔧 ENDPOINTS IMPLEMENTADOS

### 1. Mudar Status do Freelancer
```
PUT /barbeiro/status

Request:
{
    "status": "offline|online_region|present_local",
    "barbearia_id": 1  // Obrigatório se status = present_local
}

Response:
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

### 2. Listar Barbeiros Próximos (Regional)
```
GET /barbeiros/proximos?latitude=X&longitude=Y&raio_km=10

Filtro implementado:
- Exclui barbeiros em PRESENT_LOCAL
- Retorna apenas ONLINE_REGION + OFFLINE (se disponivel)
- Mostra distância e status
```

### 3. Listar Todos Barbeiros
```
GET /barbeiros/todos

Filtro implementado:
- Exclui barbeiros em PRESENT_LOCAL
- Retorna apenas ONLINE_REGION + OFFLINE
```

### 4. Criar Chamado
```
POST /chamados

Validações implementadas:
- Se barbeiro OFFLINE → erro 400
- Se barbeiro PRESENT_LOCAL em barbearia diferente → erro 400
```

### 5. Aceitar Chamado
```
PUT /chamados/{id}/aceitar

Validações implementadas:
- Se barbeiro OFFLINE → erro 400
- Se barbeiro PRESENT_LOCAL em barbearia diferente → erro 400
```

---

## 📝 SCHEMA ATUALIZADO

### Schema: `AtualizarStatusFreelancer`
```python
class AtualizarStatusFreelancer(BaseModel):
    """Atualizar status do freelancer"""
    status: str  # "offline", "online_region", "present_local"
    barbearia_id: Optional[int] = None  # Obrigatório se status = "present_local"
    
    class Config:
        json_schema_extra = {
            "example": {
                "status": "present_local",
                "barbearia_id": 1
            }
        }
```

---

## ✨ STATUS DE IMPLEMENTAÇÃO

- ✅ ENUM `StatusFreelancer` criado
- ✅ Campos no banco: `offline`, `online_regiao`, `presente_em_local`, `barbearia_atual_id`, `horario_chegada`
- ✅ Endpoint `PUT /barbeiro/status` implementado
- ✅ Validação na criação de chamado
- ✅ Validação ao aceitar chamado
- ✅ Filtro em `GET /barbeiros/proximos`
- ✅ Filtro em `GET /barbeiros/todos`
- ✅ Schema `AtualizarStatusFreelancer` criado
- ✅ Módulos importam sem erros

---

## 🎯 PRÓXIMOS PASSOS

1. Testar endpoints via Swagger
2. Integrar com UI (BarberDashboard - 3 botões de status)
3. Adicionar logs de auditoria para mudanças de status
4. Notificação quando barbeiro muda status
5. Dashboard mostrando status atual do barbeiro

---

**Data de Implementação:** 20 de Fevereiro de 2026
**Versão:** 1.0 - MVP Completo
