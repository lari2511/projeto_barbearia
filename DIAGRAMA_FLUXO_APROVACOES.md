# 🔄 DIAGRAMA VISUAL DO FLUXO DE APROVAÇÕES BIDIRECIONAL

## Fase 1: Cliente Cria Agendamento

```
┌─────────────────────────────────────────────────────────────┐
│                   CLIENTE                                   │
│  "Quero cortar cabelo com João na BarberShop"               │
└─────────────────────────────────────────────────────────────┘
                          │
                          │ POST /cliente/agendar
                          ▼
┌─────────────────────────────────────────────────────────────┐
│              BANCO DE DADOS - Chamado                        │
│  ┌──────────────────────────────────────────────────────┐   │
│  │ id: 123                                              │   │
│  │ cliente_id: 1                                        │   │
│  │ barbeiro_id: 5                                       │   │
│  │ barbearia_id: 2                                      │   │
│  │ data: 2025-01-20                                     │   │
│  │ horario: 10:00                                       │   │
│  │ status: PENDENTE                                     │   │
│  │ aprovado_barbeiro: ❌ FALSE                          │   │
│  │ aprovado_barbearia: ❌ FALSE                         │   │
│  └──────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

---

## Fase 2: Barbeiro Aprova

```
┌─────────────────────────────────────────────────────────────┐
│                     BARBEIRO (João)                         │
│        "Posso fazer o corte para este cliente"              │
└─────────────────────────────────────────────────────────────┘
                          │
                          │ POST /chamados/123/aprovacao-barbeiro
                          │ + Authorization: Bearer {barbeiro_token}
                          ▼
┌─────────────────────────────────────────────────────────────┐
│              VALIDAÇÃO & LÓGICA BACKEND                     │
│  1. Verificar token do barbeiro ✓                           │
│  2. Verificar se chamado existe ✓                           │
│  3. aprovado_barbeiro = TRUE                                │
│  4. aprovado_barbeiro_em = 2025-01-20 09:50:00             │
│  5. Verificar status aprovação:                             │
│     - aprovado_barbeiro: ✅ TRUE                            │
│     - aprovado_barbearia: ❌ FALSE                          │
│     → Status segue PENDENTE (aguardando barbearia)          │
└─────────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│              BANCO DE DADOS - Chamado ATUALIZADO            │
│  ┌──────────────────────────────────────────────────────┐   │
│  │ status: PENDENTE (ainda não confirmado)              │   │
│  │ aprovado_barbeiro: ✅ TRUE                           │   │
│  │ aprovado_barbeiro_em: 2025-01-20 09:50:00            │   │
│  │ aprovado_barbearia: ❌ FALSE (aguardando)             │   │
│  └──────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

---

## Fase 3: Barbearia Aprova (CONFIRMAÇÃO!)

```
┌─────────────────────────────────────────────────────────────┐
│                 BARBEARIA (Dono/Manager)                    │
│    "Tudo certo, libero a cadeira para o corte"             │
└─────────────────────────────────────────────────────────────┘
                          │
                          │ POST /chamados/123/aprovacao-barbearia
                          │ + Authorization: Bearer {barbearia_token}
                          ▼
┌─────────────────────────────────────────────────────────────┐
│              VALIDAÇÃO & LÓGICA BACKEND                     │
│  1. Verificar token da barbearia ✓                          │
│  2. Verificar se chamado existe ✓                           │
│  3. aprovado_barbearia = TRUE                               │
│  4. aprovado_barbearia_em = 2025-01-20 09:51:00            │
│  5. Verificar status aprovação:                             │
│     - aprovado_barbeiro: ✅ TRUE                            │
│     - aprovado_barbearia: ✅ TRUE                           │
│     → ⚠️  AMBAS APROVARAM! Confirmar agendamento            │
│  6. status = CONFIRMADO                                     │
│  7. Bloquear primeira cadeira disponível:                   │
│     - Cadeira #2 → status = BLOQUEADA                       │
│     - Cadeira #2.chamado_id = 123                           │
└─────────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│        BANCO DE DADOS - AGENDAMENTO CONFIRMADO!             │
│  ┌──────────────────────────────────────────────────────┐   │
│  │ status: CONFIRMADO ✅✅                              │   │
│  │ aprovado_barbeiro: ✅ TRUE                           │   │
│  │ aprovado_barbearia: ✅ TRUE                          │   │
│  │ aprovado_barbeiro_em: 2025-01-20 09:50:00            │   │
│  │ aprovado_barbearia_em: 2025-01-20 09:51:00           │   │
│  └──────────────────────────────────────────────────────┘   │
│  ┌──────────────────────────────────────────────────────┐   │
│  │ CADEIRA #2 BLOQUEADA                                 │   │
│  │ id: 5                                                │   │
│  │ numero: "2"                                          │   │
│  │ status: BLOQUEADA 🔒                                 │   │
│  │ chamado_id: 123 (vinculada a este agendamento)       │   │
│  └──────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

---

## Fase 4: Durante o Serviço (Cadeira Bloqueada)

```
┌─────────────────────────────────────────────────────────────┐
│            OUTRO CLIENTE TENTANDO AGENDAR                   │
│         GET /barbearia/2/cadeiras-status                    │
└─────────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│              RESPOSTA - STATUS DE CADEIRAS                  │
│  ┌──────────────────────────────────────────────────────┐   │
│  │ Cadeira #1: DISPONÍVEL   ✅ (pode agendar)           │   │
│  │ Cadeira #2: BLOQUEADA 🔒 ❌ (NÃO pode agendar)       │   │
│  │ Cadeira #3: DISPONÍVEL   ✅ (pode agendar)           │   │
│  │                                                      │   │
│  │ A Cadeira #2 está BLOQUEADA para:                    │   │
│  │ - Cliente: João Silva (ID: 1)                        │   │
│  │ - Barbeiro: João Barbeiro (ID: 5)                    │   │
│  │ - Serviço: Corte de cabelo                           │   │
│  │ - Horário: 2025-01-20 10:00 até 10:30                │   │
│  └──────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

---

## Fase 5: Serviço Concluído (Liberar Cadeira)

```
┌─────────────────────────────────────────────────────────────┐
│                    BARBEIRO (João)                          │
│           "Corte concluído! Próximo cliente"                │
└─────────────────────────────────────────────────────────────┘
                          │
                          │ POST /cadeiras/5/liberar
                          │ Body: {"chamado_id": 123}
                          ▼
┌─────────────────────────────────────────────────────────────┐
│              VALIDAÇÃO & LÓGICA BACKEND                     │
│  1. Verificar cadeira #5 existe ✓                           │
│  2. Verificar se está bloqueada ✓                           │
│  3. cadeira.chamado_id = NULL                               │
│  4. cadeira.status = DISPONÍVEL                             │
│  5. chamado.status = CONCLUIDO                              │
└─────────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│          BANCO DE DADOS - CADEIRA LIBERADA                  │
│  ┌──────────────────────────────────────────────────────┐   │
│  │ CADEIRA #2                                           │   │
│  │ id: 5                                                │   │
│  │ status: DISPONÍVEL ✅ (outras pessoas podem usar)    │   │
│  │ chamado_id: NULL (sem vínculo)                       │   │
│  └──────────────────────────────────────────────────────┘   │
│  ┌──────────────────────────────────────────────────────┐   │
│  │ AGENDAMENTO FINALIZADO                               │   │
│  │ id: 123                                              │   │
│  │ status: CONCLUIDO ✅                                 │   │
│  └──────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

---

## Fase 6: Cliente Avalia (Novo!)

```
┌─────────────────────────────────────────────────────────────┐
│                     CLIENTE (no app)                        │
│              Aba "Avaliar" com pendentes                    │
│  ┌──────────────────────────────────────────────────────┐   │
│  │ "Você tem 1 avaliação pendente"                      │   │
│  │                                                      │   │
│  │ 📅 20/01/2025 10:00                                  │   │
│  │ ✂️  Corte de cabelo                                  │   │
│  │ 👨 João Barbeiro @ BarberShop                        │   │
│  │                                                      │   │
│  │ [Avaliar] ← Clica aqui                              │   │
│  └──────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
                          │
                          │ Modal AvaliacaoModal abre
                          ▼
┌─────────────────────────────────────────────────────────────┐
│                   MODAL DE AVALIAÇÃO                        │
│  ┌──────────────────────────────────────────────────────┐   │
│  │ "Como foi o serviço?"                               │   │
│  │                                                      │   │
│  │ ⭐ ⭐ ⭐ ⭐ ⭐  (5 estrelas selecionadas)              │   │
│  │ "Excelente!"                                         │   │
│  │                                                      │   │
│  │ Comentário (opcional):                               │   │
│  │ ┌──────────────────────────────────────────────────┐ │   │
│  │ │ João fez um corte perfeito! Vou voltar com      │ │   │
│  │ │ certeza! (85/500 caracteres)                     │ │   │
│  │ └──────────────────────────────────────────────────┘ │   │
│  │                                                      │   │
│  │ [Cancelar]  [Enviar Avaliação] ← Clica              │   │
│  └──────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
                          │
                          │ POST /api/v1/avaliacoes
                          │ Body: {
                          │   "chamado_id": 123,
                          │   "avaliado_id": 5,
                          │   "nota": 5,
                          │   "comentario": "João fez..."
                          │ }
                          ▼
┌─────────────────────────────────────────────────────────────┐
│        BANCO DE DADOS - AVALIAÇÃO SALVA                     │
│  ┌──────────────────────────────────────────────────────┐   │
│  │ AVALIACAO                                            │   │
│  │ id: 456                                              │   │
│  │ chamado_id: 123 ← Referência ao agendamento          │   │
│  │ avaliador_id: 1 ← Cliente que avaliou                │   │
│  │ avaliado_id: 5 ← Barbeiro avaliado                   │   │
│  │ nota: 5 ⭐⭐⭐⭐⭐                                      │   │
│  │ comentario: "João fez um corte perfeito..."          │   │
│  │ criado_em: 2025-01-20 11:00:00                       │   │
│  └──────────────────────────────────────────────────────┘   │
│  ┌──────────────────────────────────────────────────────┐   │
│  │ USUARIO (Barbeiro atualizado)                        │   │
│  │ id: 5                                                │   │
│  │ nome: João Barbeiro                                  │   │
│  │ media_avaliacao: 4.8 ⭐ (atualizada!)                │   │
│  └──────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

---

## Fase 7: Barbeiro Rejeita (Alternativa)

```
┌─────────────────────────────────────────────────────────────┐
│                     BARBEIRO (João)                         │
│          "Não posso fazer o corte neste dia"               │
└─────────────────────────────────────────────────────────────┘
                          │
                          │ POST /chamados/123/rejeitar-barbeiro
                          │ Body: {
                          │   "motivo": "Doente",
                          │   "horario_sugerido": "2025-01-21 14:00"
                          │ }
                          ▼
┌─────────────────────────────────────────────────────────────┐
│              VALIDAÇÃO & LÓGICA BACKEND                     │
│  1. Verificar token do barbeiro ✓                           │
│  2. status = CANCELADO                                      │
│  3. motivo salvo em observacao                              │
│  4. horario_sugerido = 2025-01-21 14:00                    │
│  5. ❌ Cadeira NÃO é bloqueada (foi rejeitado)             │
└─────────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│        BANCO DE DADOS - AGENDAMENTO CANCELADO               │
│  ┌──────────────────────────────────────────────────────┐   │
│  │ status: CANCELADO ❌                                 │   │
│  │ observacao: "Rejeitado pelo barbeiro: Doente"        │   │
│  │ horario_sugerido: "2025-01-21 14:00"                 │   │
│  │ aprovado_barbeiro: FALSE (rejeitou)                  │   │
│  └──────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│              CLIENTE RECEBE NOTIFICAÇÃO                     │
│  ┌──────────────────────────────────────────────────────┐   │
│  │ ❌ Agendamento Cancelado                             │   │
│  │                                                      │   │
│  │ Motivo: Barbeiro está doente                         │   │
│  │                                                      │   │
│  │ ⏰ Sugestão: 21/01/2025 às 14:00                      │   │
│  │                                                      │   │
│  │ [Reagendar] [Escolher Outro Barbeiro]               │   │
│  └──────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

---

## 📱 Interface do Cliente - Antes e Depois

### Antes (4 abas):
```
╔════════════════════════════════════════════════════════════╗
║         ClientDashboard - Antes                           ║
╠════════════════════════════════════════════════════════════╣
║                                                             ║
║  Conteúdo da aba ativa aqui...                            ║
║                                                             ║
║                                                             ║
║                                                             ║
╠════════════════════════════════════════════════════════════╣
║                                                             ║
║  [🔍 Buscar] [📅 Agenda] [👤 Perfil] [💳 Pagar]           ║
║                                                             ║
╚════════════════════════════════════════════════════════════╝
```

### Depois (5 abas):
```
╔════════════════════════════════════════════════════════════╗
║         ClientDashboard - Depois                          ║
╠════════════════════════════════════════════════════════════╣
║                                                             ║
║  Conteúdo da aba ativa aqui...                            ║
║                                                             ║
║  AbaPadronizadaAvaliacoes quando "Avaliar" está ativo     ║
║                                                             ║
╠════════════════════════════════════════════════════════════╣
║                                                             ║
║  [🔍] [📅] [⭐] [👤] [💳]  ← Nova aba "Avaliar"!          ║
║                                                             ║
╚════════════════════════════════════════════════════════════╝
```

---

## 🔄 Resumo do Fluxo (Timeline)

```
T0: 09:00 - Cliente cria agendamento
    ✓ Status: PENDENTE
    ✓ Ninguém aprovou ainda

T1: 09:50 - Barbeiro aprova
    ✓ Status: PENDENTE (aguardando barbearia)
    ✓ Cadeira: SEM BLOQUEAR ainda

T2: 09:51 - Barbearia aprova
    ✓ Status: CONFIRMADO 🎉
    ✓ Cadeira: BLOQUEADA 🔒

T3: 10:00 - Serviço começa
    ✓ Barbeiro corta cabelo
    ✓ Cadeira continua BLOQUEADA
    ✓ Outros clientes NÃO podem usar esta cadeira

T4: 10:30 - Serviço termina
    ✓ Barbeiro libera cadeira
    ✓ Status: CONCLUIDO
    ✓ Cadeira: DISPONÍVEL novamente

T5: 11:00 - Cliente avalia
    ✓ Modal de avaliação aparece
    ✓ Cliente seleciona ⭐⭐⭐⭐⭐
    ✓ Média do barbeiro é atualizada

RESULTADO:
✅ Agendamento confirmado apenas após AMBAS aprovações
✅ Cadeira bloqueada apenas quando confirmado
✅ Avaliação salva com sucesso
```

---

## 💡 Por que este fluxo é importante?

### ✅ Para o Cliente:
- Sabe que agendamento foi realmente confirmado
- Pode avaliar o barbeiro após o serviço
- Recebe sugestão de horário se rejeitado

### ✅ Para o Barbeiro:
- Controla sua agenda
- Pode rejeitar se indisponível
- Recebe avaliações dos clientes

### ✅ Para a Barbearia:
- Controla qual cadeira é usada
- Pode rejeitar agendamento
- Vê estatísticas de avaliações

### ✅ Para o Negócio:
- Menos no-shows (dupla aprovação = confirmação séria)
- Feedback importante via avaliações
- Otimização de cadeiras

---

**Visualização criada para:** Documentação e treinamento  
**Última atualização:** 2025  
**Status:** 🟢 Pronto para referência
