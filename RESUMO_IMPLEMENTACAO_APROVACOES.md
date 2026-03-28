# 📱 SISTEMA DE APROVAÇÕES BIDIRECIONAL - RESUMO TÉCNICO

## 🎯 Objetivo Principal
Implementar um sistema onde **AMBOS** o barbeiro e a barbearia (dono) devem aprovar um agendamento antes dele ser confirmado. Além disso, bloquear cadeiras quando barbeiro está usando e padrão izar avaliações.

---

## ✅ O QUE FOI IMPLEMENTADO

### 1️⃣ Backend - Modelo de Dados (app/models.py)

#### Mudanças no Modelo `Chamado`:
```python
# Campos adicionados:
aprovado_barbeiro: bool = False
aprovado_barbearia: bool = False
aprovado_barbeiro_em: datetime = None
aprovado_barbearia_em: datetime = None
```

#### Mudanças no Modelo `Cadeira`:
```python
# Campos adicionados:
chamado_id: int (Foreign Key para Chamado)
chamado: Relationship
```

---

### 2️⃣ Backend - Novo Router (app/routes_aprovacoes.py)

#### Endpoint 1: Barbeiro Aprova
```
POST /api/v1/chamados/{chamado_id}/aprovacao-barbeiro
Headers: Authorization: Bearer {token}

Lógica:
- Verifica token JWT do barbeiro
- Define aprovado_barbeiro = True
- Define aprovado_barbeiro_em = now()
- Se aprovado_barbearia TAMBÉM estiver True:
  - Status muda para CONFIRMADO
  - Primeira cadeira disponível fica BLOQUEADA
  - Cadeira vinculada ao chamado (chamado_id)
```

#### Endpoint 2: Barbearia Aprova
```
POST /api/v1/chamados/{chamado_id}/aprovacao-barbearia
Headers: Authorization: Bearer {token}

Lógica:
- Verifica token JWT da barbearia
- Define aprovado_barbearia = True
- Define aprovado_barbearia_em = now()
- Se aprovado_barbeiro TAMBÉM estiver True:
  - Status muda para CONFIRMADO
  - Primeira cadeira disponível fica BLOQUEADA
```

#### Endpoint 3: Barbeiro Rejeita
```
POST /api/v1/chamados/{chamado_id}/rejeitar-barbeiro
Body:
{
  "motivo": "Não posso fazer nesse dia",
  "horario_sugerido": "2025-01-20 14:00"
}

Lógica:
- Status muda para CANCELADO
- Motivo é salvo em observacao
- Se horario_sugerido fornecido, fica disponível para cliente
```

#### Endpoint 4: Sugerir Horários Alternativos
```
GET /api/v1/chamados/{chamado_id}/horarios-alternativos

Resposta:
{
  "horarios_disponiveis": [
    {"data": "2025-01-20", "horario": "10:00"},
    {"data": "2025-01-20", "horario": "14:00"},
    ...
  ]
}
```

#### Endpoint 5: Liberar Cadeira Após Serviço
```
POST /api/v1/cadeiras/{cadeira_id}/liberar
Body: {"chamado_id": 123}

Lógica:
- Cadeira volta para DISPONÍVEL
- Vínculo com chamado removido
- Chamado status muda para CONCLUIDO (se serviço terminou)
```

#### Endpoint 6: Status de Cadeiras
```
GET /api/v1/barbearia/{barbearia_id}/cadeiras-status

Resposta:
{
  "cadeiras": [
    {
      "id": 1,
      "numero": "1",
      "status": "BLOQUEADA",
      "chamado_id": 123
    },
    {
      "id": 2,
      "numero": "2",
      "status": "DISPONÍVEL",
      "chamado_id": null
    }
  ]
}
```

---

### 3️⃣ Frontend - Componentes Novos

#### AvaliacaoModal.jsx
```jsx
<AvaliacaoModal
  onClose={() => setShowModal(false)}
  onSubmit={(nota, comentario) => submitAvaliacao(nota, comentario)}
  loading={loading}
  erro={erro}
/>
```

**Funcionalidades:**
- 5 estrelas interativas (hover feedback)
- Campo de comentário (max 500 chars)
- Botões Cancel/Send
- Carregamento e tratamento de erro

---

#### ListaAvaliacoes.jsx
```jsx
<ListaAvaliacoes
  avaliacoes={avaliacoes}
/>
```

**Funcionalidades:**
- Mostra nota média com visual
- Histograma de distribuição (5★, 4★, 3★, 2★, 1★)
- Lista últimas 5 avaliações
- Botão "Ver todas"

---

#### AprovacaoAgendamento.jsx
```jsx
<AprovacaoAgendamento
  chamado={agendamento}
  tipoUsuario="barbeiro"
  onAprovar={() => aprovarAgendamento()}
  onRejeitar={() => rejeitarAgendamento()}
  API_URL={API_URL}
  token={token}
/>
```

**Funcionalidades:**
- Exibe status de aprovação (checkboxes)
- Botões Aprovar/Rejeitar (condicionais)
- Modal de rejeição com:
  - Campo de motivo
  - Dropdown de horários alternativos
- Status final: Verde "Confirmado" / Vermelho "Cancelado"

---

#### AbaPadronizadaAvaliacoes.jsx
```jsx
<AbaPadronizadaAvaliacoes
  usuarioId={123}
  tipoUsuario="cliente"
  nomeUsuario="João"
  API_URL={API_URL}
  token={token}
  notify={notify}
/>
```

**Funcionalidades:**
- Seção "Avaliações Pendentes" com agendamentos completos
- Integra `AvaliacaoModal` para submeter nota
- Integra `ListaAvaliacoes` para histórico
- Suporta: cliente, barbeiro, barbearia
- Carregamento de endpoints:
  - GET `/api/v1/avaliacoes/cliente/{id}`
  - GET `/api/v1/avaliacoes/{tipo}/{id}`
  - POST `/api/v1/avaliacoes`

---

### 4️⃣ Frontend - Integração no ClientDashboard

**Navbar (5 abas):**
```
Buscar | Agenda | Avaliar | Perfil | Pagar
```

**Nova Aba "Avaliar":**
```jsx
{tab === 'avaliacoes' && (
  <AbaPadronizadaAvaliacoes
    usuarioId={userData?.id}
    tipoUsuario="cliente"
    nomeUsuario={userData?.nome}
    API_URL={API_URL}
    token={token}
    notify={notify}
  />
)}
```

---

## 🟡 O QUE AINDA FALTA

### Endpoints de Avaliações (⚠️ CRÍTICO)
```python
# routes_avaliacoes.py (NÃO CRIADO AINDA)

POST /api/v1/avaliacoes
Body: {
  "chamado_id": 123,
  "avaliado_id": 456,
  "nota": 5,
  "comentario": "Excelente trabalho!"
}

GET /api/v1/avaliacoes/cliente/{cliente_id}
GET /api/v1/avaliacoes/barbeiro/{barbeiro_id}
GET /api/v1/avaliacoes/barbearia/{barbearia_id}
```

### Integração no BarberDashboard
- Adicionar aba "Avaliar"
- Usar `AbaPadronizadaAvaliacoes` com `tipoUsuario="barbeiro"`
- Modificar navbar de 4 para 5 abas

### Integração no ShopDashboard
- Adicionar aba "Avaliar"
- Usar `AbaPadronizadaAvaliacoes` com `tipoUsuario="barbearia"`
- Modificar navbar de 4 para 5 abas

### Integração do AprovacaoAgendamento
- Adicionar em ClientDashboard (aba Agenda)
- Adicionar em BarberDashboard (Meus Agendamentos)
- Adicionar em ShopDashboard (Agendamentos)

### Testes End-to-End
- Criar fluxo completo de aprovação
- Testar bloqueio/liberação de cadeiras
- Testar rejeição com sugestão
- Testar submissão de avaliações

---

## 📊 FLUXO DE APROVAÇÃO COMPLETO

```
1. CLIENTE AGENDA
   Cria novo Chamado
   Status: PENDENTE
   aprovado_barbeiro: False
   aprovado_barbearia: False

2. BARBEIRO APROVA
   POST /aprovacao-barbeiro
   aprovado_barbeiro = True
   aprovado_barbeiro_em = now()
   Status: PENDENTE (aguardando barbearia)

3. BARBEARIA APROVA
   POST /aprovacao-barbearia
   aprovado_barbearia = True
   aprovado_barbearia_em = now()
   Status: CONFIRMADO ✅
   ⚠️ Primeira cadeira BLOQUEADA

4. DURANTE O SERVIÇO
   Cadeira permanece BLOQUEADA
   Outros clientes NÃO podem marcar essa cadeira

5. APÓS O SERVIÇO
   Barbeiro clica "Serviço Concluído"
   POST /cadeiras/{id}/liberar
   Cadeira volta para DISPONÍVEL
   Status: CONCLUIDO

6. AVALIAÇÃO
   Cliente vê "Avaliar" pendente
   Clica e submete nota (1-5 estrelas)
   Avaliação é salva
```

---

## 🐛 POSSÍVEIS BUGS/ISSUES

1. **WebSocket 403:** Logs mostram erros de autenticação WebSocket
   - Pode afetar notificações em tempo real
   - Não afeta aprovações (HTTP REST)

2. **Endpoints de Avaliações Faltando:**
   - AbaPadronizadaAvaliacoes.jsx chama endpoints que não existem
   - Precisa criar routes_avaliacoes.py

3. **Migrations do Banco:**
   - Modelos atualizados mas banco pode estar desatualizado
   - Pode ser necessário: `alembic revision --autogenerate`

4. **Props Faltando:**
   - AprovacaoAgendamento precisa ser integrado nas views
   - Cada dashboard precisa passar props corretas

---

## 📦 ARQUIVOS CRIADOS

```
✅ app/routes_aprovacoes.py         (278 linhas)
✅ barbermove/src/components/AvaliacaoModal.jsx              (140 linhas)
✅ barbermove/src/components/ListaAvaliacoes.jsx             (100 linhas)
✅ barbermove/src/components/AprovacaoAgendamento.jsx        (280 linhas)
✅ barbermove/src/components/AbaPadronizadaAvaliacoes.jsx    (150 linhas)
```

## 📝 ARQUIVOS MODIFICADOS

```
✅ app/models.py                    (+8 linhas para aprovações)
✅ app/main.py                      (+1 import, +1 include_router)
✅ barbermove/src/components/ClientDashboard.jsx   (+aba avaliacoes)
```

---

## 🚀 PRÓXIMO PASSO CRÍTICO

**Criar arquivo:** `app/routes_avaliacoes.py`

```python
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from . import models, schemas, database
from .database import get_db

router = APIRouter()

@router.post("/avaliacoes")
def criar_avaliacao(
    avaliacao: schemas.AvaliacaoCreate,
    db: Session = Depends(get_db),
    token: str = Depends(oauth2_scheme)
):
    # Implementar lógica de salvamento
    pass

@router.get("/avaliacoes/cliente/{cliente_id}")
def listar_avaliacoes_cliente(cliente_id: int, db: Session = Depends(get_db)):
    # Implementar lógica de listagem
    pass

# ... mais endpoints
```

Sem isso, o sistema funcionará visualmente mas não salvará avaliações!

---

**Status Geral:** 🟡 80% COMPLETO - Pronto para integração e testes
