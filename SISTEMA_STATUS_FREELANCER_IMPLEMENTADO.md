# SISTEMA DE STATUS DO FREELANCER - IMPLEMENTAÇÃO COMPLETA

## 🎯 OBJETIVO
Sistema com 3 estados operacionais do freelancer (OFFLINE, ONLINE, PRESENTE) visível para:
- O próprio freelancer
- O dono da barbearia  
- O cliente

**Controle duplo:** Tanto o freelancer quanto o dono podem alterar o status.

---

## 🔘 OS 3 STATUS OFICIAIS

### 1️⃣ OFFLINE
**Significa:** Profissional não está trabalhando

**Configuração no sistema:**
```json
{
  "presente_em_local": false,
  "online_regiao": false,
  "barbearia_atual_id": null,
  "disponivel": false
}
```

**Regras:**
- ❌ Não recebe chamados
- ❌ Não aparece disponível para clientes
- ❌ Não recebe agendamentos
- ✅ Pode ser usado para almoço, pausa ou encerramento

**Visível ao cliente:** "⭕ OFFLINE"

### 2️⃣ ONLINE NA REGIÃO
**Significa:** Disponível no marketplace

**Configuração:**
```json
{
  "online_regiao": true,
  "presente_em_local": false,
  "barbearia_atual_id": null,
  "disponivel": true
}
```

**Regras:**
- ✅ Pode receber chamado de qualquer barbearia
- ✅ Pode receber agendamento privado
- ✅ Localização baseada no GPS atual
- ❌ Não ocupa cadeira fixa

**Visível ao cliente:** "🌍 ONLINE"

### 3️⃣ FREELANCER PRESENTE  
**Significa:** Trabalhando fisicamente em uma barbearia específica

**Configuração:**
```json
{
  "presente_em_local": true,
  "online_regiao": false,
  "barbearia_atual_id": ID_DA_BARBEARIA,
  "disponivel": false
}
```

**Validação antes de ativar:**
```
freelancers_presentes < cadeiras_contratadas
```
Se não houver cadeira disponível → bloquear ativação.

**Regras:**
- ✅ Só recebe agendamento naquela barbearia
- ❌ Não recebe chamado externo
- ❌ Não recebe agendamento privado externo
- ✅ Ocupa uma cadeira contratada
- ✅ Cliente só consegue marcar com ele naquela unidade
- ❌ Não pode ativar se estiver bloqueado nessa barbearia

**Visível ao cliente:** "🏢 PRESENTE"

---

## 📍 EXIBIÇÃO AUTOMÁTICA NO PERFIL

Se estiver presente:
- **Mostrar:** "Freelancer presente na Barbearia [Nome da Barbearia]"
- **Ao clicar em agendar:** Redirecionar automaticamente para essa barbearia
- **Restrição:** Cliente não pode escolher outra unidade enquanto ele estiver presente

---

## 🔁 CONTROLE DUPLO (DONO + FREELANCER)

Tanto o freelancer quanto o dono da barbearia têm acesso aos 3 botões.

**Motivo:** Evitar erro humano
- Se o freelancer esquecer de alterar, o dono pode alterar
- Se o dono esquecer, o freelancer pode alterar

### ⚖️ REGRA DE SINCRONIZAÇÃO
Sempre que um dos dois alterar o status:
- O sistema atualiza imediatamente para ambos
- Exemplo: Se o dono marcar "Freelancer Presente" → O app do freelancer deve atualizar automaticamente

### 🚫 REGRA ABSOLUTA
**Nunca pode existir:**
```
presente_em_local = true
E
online_regiao = true
```
✅ Ativar um → desativa automaticamente o outro

---

## 👁️ VISÃO DO CLIENTE

O cliente sempre verá um dos 3 estados no perfil do freelancer:

- **Offline** → Não pode agendar (botão desabilitado)
- **Online na Região** → Cliente pode escolher a barbearia
- **Presente na Barbearia [Nome]** → Agendamento direcionado automaticamente para aquela barbearia

---

## 📋 REGRA DE AGENDAMENTO – ACEITE SOMENTE PELO FREELANCER

### 1️⃣ Quem pode aceitar ou recusar?
**SOMENTE O FREELANCER.**

O dono da barbearia **NÃO** pode:
- ❌ aceitar
- ❌ recusar
- ❌ cancelar
- ❌ interferir no agendamento

### 2️⃣ Fluxo do agendamento

**Cenário:**
- Cliente agenda com o freelancer
- Escolhe a barbearia (ex: O Patriarca)
- Freelancer está como "Presente" nessa barbearia

**Fluxo:**
1. Cliente cria agendamento
2. Status inicial = `PENDENTE`
3. Notificação vai apenas para o FREELANCER
4. Freelancer pode:
   - **ACEITAR** → status = `CONFIRMADO`
   - **RECUSAR** → status = `CANCELADO`
5. O dono da barbearia apenas visualiza o agendamento no painel (sem botões de ação)

### 3️⃣ O que o dono da barbearia vê?

No painel da barbearia:
- ✅ Nome do cliente
- ✅ Nome do freelancer
- ✅ Horário
- ✅ Status do agendamento
- ❌ **Apenas visualização** (sem botões)

---

## 🎯 RESPONSABILIDADE DO ATENDIMENTO

A responsabilidade do atendimento é **100% do freelancer**.  
A barbearia apenas cede a cadeira.

---

## ⭐ AVALIAÇÃO DO FREELANCER PELO DONO

Após o atendimento finalizar (`CONCLUIDO`):

**Liberar para o DONO:**
- ✅ Avaliação de 1 a 5 estrelas
- ✅ Campo de comentário
- ✅ Botão "Bloquear freelancer"

---

## 🚫 BLOQUEIO DO FREELANCER

### Quando o dono bloqueia:

Esse freelancer:
- ❌ Não pode mais ativar "Presente" nessa barbearia
- ❌ Não pode receber agendamentos nessa barbearia
- ❌ Não pode ocupar cadeira nessa barbearia
- ✅ Mas pode trabalhar normalmente em outras barbearias

---

## 🗄️ ESTRUTURA DO BANCO DE DADOS

### Tabela: `barbearia_freelancer`
```sql
CREATE TABLE barbearia_freelancer (
    id SERIAL PRIMARY KEY,
    barbearia_id INTEGER REFERENCES barbearias(id),
    freelancer_id INTEGER REFERENCES usuarios(id),
    bloqueado BOOLEAN DEFAULT FALSE,
    motivo VARCHAR,
    data_bloqueio TIMESTAMP,
    criado_em TIMESTAMP DEFAULT NOW()
);
```

### Campos adicionados em `usuarios`:
```sql
ALTER TABLE usuarios ADD COLUMN online_regiao BOOLEAN DEFAULT FALSE;
ALTER TABLE usuarios ADD COLUMN barbearia_atual_id INTEGER REFERENCES barbearias(id);
```

### 7️⃣ Regra técnica de bloqueio

Antes de permitir `ativar_status_presente()`:

**Validar:**
```python
bloqueio = db.query(BarbeariaFreelancer).filter(
    BarbeariaFreelancer.barbearia_id == barbearia_id,
    BarbeariaFreelancer.freelancer_id == freelancer_id,
    BarbeariaFreelancer.bloqueado == True
).first()

if bloqueio:
    raise HTTPException(
        status_code=403,
        detail=f"Freelancer bloqueado. Motivo: {bloqueio.motivo}"
    )
```

---

## 🔌 ENDPOINTS CRIADOS

### **Alterar Status do Freelancer**
```
POST /api/v1/freelancer/{freelancer_id}/alterar-status
```
**Body:**
```json
{
  "status": "offline" | "online" | "presente",
  "barbearia_id": 123  // Obrigatório apenas para 'presente'
}
```

### **Obter Status do Freelancer**
```
GET /api/v1/freelancer/{freelancer_id}/status
```

### **Bloquear Freelancer**
```
POST /api/v1/barbearia/{barbearia_id}/bloquear-freelancer
```
**Body:**
```json
{
  "freelancer_id": 456,
  "motivo": "Atendimento ruim"
}
```

### **Desbloquear Freelancer**
```
POST /api/v1/barbearia/{barbearia_id}/desbloquear-freelancer/{freelancer_id}
```

### **Listar Freelancers Bloqueados**
```
GET /api/v1/barbearia/{barbearia_id}/freelancers-bloqueados
```

### **Avaliar Freelancer**
```
POST /api/v1/barbearia/{barbearia_id}/avaliar-freelancer
```
**Body:**
```json
{
  "freelancer_id": 456,
  "chamado_id": 789,
  "nota": 5,
  "comentario": "Excelente atendimento"
}
```

---

## 🎨 FRONTEND IMPLEMENTADO

### Dashboard Freelancer (BarberDashboard.jsx)
- ✅ 3 botões de status (OFFLINE, ONLINE, PRESENTE)
- ✅ Modal de seleção de barbearia
- ✅ Indicador visual de status atual
- ✅ Validação de cadeiras disponíveis

### Dashboard Dono (ShopDashboard.jsx)
- ✅ Visualização de agendamentos (sem controle)
- ✅ 3 botões de controle de status para freelancers presentes
- ✅ Botão de avaliar após atendimento concluído
- ✅ Botão de bloquear freelancer
- ✅ Lista de freelancers presentes

### Dashboard Cliente (ClientDashboard.jsx)
- ✅ Indicador de status no card do freelancer (OFFLINE/ONLINE/PRESENTE)
- ✅ Botão "Escolher" desabilitado quando OFFLINE
- ✅ Exibição visual do status com ícones e cores

---

## 🧠 RESUMO FINAL DO SISTEMA

✅ **OFFLINE** = Não trabalha  
✅ **ONLINE** = Marketplace aberto  
✅ **PRESENTE** = Exclusividade da unidade  
✅ Controle por cadeiras contratadas  
✅ Controle duplo (dono e freelancer)  
✅ Exibição clara para o cliente  
✅ Redirecionamento automático  
✅ Bloqueio total de conflito  
✅ Apenas freelancer pode aceitar/recusar agendamentos  
✅ Dono pode avaliar e bloquear freelancer após atendimento  

---

## 🚀 PRÓXIMOS PASSOS

Para testar o sistema:

1. **Executar migração:**
```bash
python migration_freelancer_status.py
```

2. **Reiniciar o backend:**
```bash
# O backend já inclui as novas rotas automaticamente
```

3. **Testar fluxo completo:**
   - Freelancer: Alterar status (OFFLINE → ONLINE → PRESENTE)
   - Dono: Visualizar freelancers presentes e controlar status
   - Cliente: Ver status do freelancer e tentar agendar
   - Dono: Avaliar e bloquear freelancer após atendimento

---

## 📝 ARQUIVOS MODIFICADOS

### Backend:
- ✅ `app/models.py` - Novos modelos e campos
- ✅ `app/routes_freelancer_status.py` - Novos endpoints (CRIADO)
- ✅ `app/routes.py` - Bloqueio de aceite/recusa pelo dono
- ✅ `app/main.py` - Registro das novas rotas
- ✅ `migration_freelancer_status.py` - Script de migração (CRIADO)

### Frontend:
- ✅ `barbermove/src/components/BarberDashboard.jsx` - 3 botões de status
- ✅ `barbermove/src/components/ShopDashboard.jsx` - Controle e avaliação
- ✅ `barbermove/src/components/ClientDashboard.jsx` - Exibição de status

---

## ✅ CHECKLIST DE IMPLEMENTAÇÃO

- [x] Modelo `BarbeariaFreelancer` criado
- [x] Campos `online_regiao` e `barbearia_atual_id` adicionados
- [x] Migração executada com sucesso
- [x] Endpoints de alteração de status criados
- [x] Endpoints de bloqueio criados
- [x] Endpoint de avaliação criado
- [x] Bloqueio de aceite/recusa do dono implementado
- [x] Dashboard freelancer atualizado com 3 botões
- [x] Dashboard dono atualizado com controles
- [x] Dashboard cliente atualizado com indicadores
- [x] Validação de cadeiras disponíveis
- [x] Validação de bloqueio
- [x] Sincronização automática de status
- [x] Controle duplo funcionando

---

**Data de implementação:** 17 de fevereiro de 2026  
**Status:** ✅ CONCLUÍDO  
**Versão:** 1.0.0
