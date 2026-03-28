# 🧪 GUIA DE TESTE MANUAL - SISTEMA DE APROVAÇÕES

## 📋 Pré-Requisitos

✅ Backend rodando: `http://localhost:8000`  
✅ Frontend rodando: `http://localhost:5175`  
✅ 3 navegadores abertos (ou abas diferentes):
   - Cliente
   - Barbeiro
   - Barbearia/Dono

---

## 👥 Contas de Teste

```
CLIENTE:
  Email: clientes@test.com
  Senha: 123456

BARBEIRO:
  Email: barbeiros@test.com
  Senha: 123456

BARBEARIA:
  Email: barbearias@test.com
  Senha: 123456
```

---

## 🧪 TESTE 1: Criar Agendamento (Cliente)

### Passos:
1. Abrir http://localhost:5175 em **navegador 1**
2. Fazer login com CLIENTE (clientes@test.com / 123456)
3. Clicar em aba **"Buscar"**
4. Preencher:
   - **Barbeiro:** Selecionar qualquer barbeiro disponível
   - **Barbearia:** Selecionar a barbearia onde trabalha o barbeiro
   - **Data:** Amanhã ou próxima data disponível
   - **Horário:** 10:00 (ou próximo disponível)
   - **Serviço:** "Corte de cabelo"
   - **Observação:** "Teste de agendamento com aprovações"
5. Clicar **"Agendar"**

### Resultado Esperado:
```
✅ Mensagem de sucesso: "Agendamento criado com sucesso!"
✅ Agendamento aparece na aba "Agenda"
✅ Status mostra: "PENDENTE" (aguardando aprovações)
✅ Mostra dois checkboxes vazios:
   ☐ Barbeiro aprovado
   ☐ Barbearia aprovada
```

---

## 🧪 TESTE 2: Barbeiro Aprova (Barbeiro)

### Passos:
1. Abrir http://localhost:5175 em **navegador 2** (aba diferente/incógnita/outro navegador)
2. Fazer login com BARBEIRO (barbeiros@test.com / 123456)
3. Ir para aba **"Meus Agendamentos"** ou similar
4. Encontrar o agendamento que o cliente acabou de criar (status PENDENTE)
5. Clicar **"Aprovar"** (botão verde)

### Resultado Esperado:
```
✅ Notificação: "Agendamento aprovado!"
✅ Status continua: "PENDENTE" (aguardando barbearia)
✅ Checkbox do barbeiro fica marcado:
   ☑ Barbeiro aprovado
   ☐ Barbearia aprovada
✅ Botão "Aprovar" desaparece (já aprovado)
```

### Verificar no Cliente:
- Voltar ao **navegador 1** (cliente)
- Ir para aba **"Agenda"**
- Encontrar o agendamento
- **✅ Checkbox "Barbeiro aprovado" deve estar marcado**

---

## 🧪 TESTE 3: Barbearia Aprova (Dono/Manager)

### Passos:
1. Abrir http://localhost:5175 em **navegador 3** (ou terceira aba)
2. Fazer login com BARBEARIA (barbearias@test.com / 123456)
3. Ir para aba **"Agendamentos"** ou **"Gerenciar Agendamentos"**
4. Encontrar o agendamento PENDENTE que o cliente criou
5. Clicar **"Aprovar"** (botão verde)

### Resultado Esperado:
```
✅ Notificação: "Agendamento aprovado por todos!"
✅ Status MUDA PARA: "CONFIRMADO" 🎉
✅ Ambos checkboxes ficam marcados:
   ☑ Barbeiro aprovado
   ☑ Barbearia aprovada
✅ Card fica com fundo VERDE
✅ Mensagem: "Agendamento Confirmado! Barbeiro e barbearia aprovaram."
✅ Botões desaparecem
```

### Verificar em Todas as Abas:
- **Cliente:** Aba "Agenda" → Status CONFIRMADO (verde)
- **Barbeiro:** Aba "Meus Agendamentos" → Status CONFIRMADO
- **Barbearia:** Aba "Agendamentos" → Status CONFIRMADO

---

## 🧪 TESTE 4: Verificar Bloqueio de Cadeira

### Passos:
1. Na conta **BARBEARIA** (navegador 3)
2. Ir para aba **"Cadeiras"** ou **"Gerenciar Cadeiras"**
3. Procurar por cadeiras com status "BLOQUEADA" 🔒

### Resultado Esperado:
```
✅ Mostrar lista de cadeiras:
   Cadeira #1: DISPONÍVEL ✅
   Cadeira #2: BLOQUEADA 🔒 (vinculada ao agendamento confirmado)
   Cadeira #3: DISPONÍVEL ✅

✅ Ao clicar na cadeira BLOQUEADA, mostrar:
   - Status: BLOQUEADA
   - Ocupada por: João Silva (cliente)
   - Barbeiro: João Barbeiro
   - Horário: 2025-01-20 10:00
   - Duração: ~30 min
   - Botão "Liberar" aparece quando serviço terminar
```

---

## 🧪 TESTE 5: Tentar Agendar Cadeira Bloqueada (Outro Cliente)

### Passos:
1. Abrir **navegador 4** (ou nova aba incógnita) com outra conta de cliente
2. Fazer login com CLIENTE (ou criar nova conta)
3. Ir para **"Buscar"**
4. Selecionar:
   - Barbeiro: Mesmo barbeiro do agendamento confirmado
   - Barbearia: Mesma barbearia
   - Data/Horário: **MESMO dia e horário do primeiro agendamento**
   - Serviço: Qualquer serviço

### Resultado Esperado:
```
✅ Mostrar mensagem de ERRO:
   "Essa cadeira não está disponível neste horário.
    Sugestões de horários alternativos:
    • 2025-01-20 11:00 ✅
    • 2025-01-20 14:00 ✅
    • 2025-01-21 10:00 ✅"

✅ NÃO permitir agendar
✅ Sugerir horários alternativos
```

---

## 🧪 TESTE 6: Rejeição com Sugestão (Barbeiro)

### Passos:
1. Cliente cria NOVO agendamento (navegador 1)
2. Na conta BARBEIRO (navegador 2):
3. Encontrar o novo agendamento
4. Clicar **"Rejeitar"** (botão vermelho) ← Antes de aprovar!
5. Modal abre com:
   - **Campo "Motivo":** "Estou doente"
   - **Dropdown "Horário Sugerido":** Selecionar "2025-01-21 14:00"
6. Clicar **"Rejeitar Agendamento"**

### Resultado Esperado:
```
✅ Notificação: "Agendamento rejeitado com sugestão de horário"
✅ Status MUDA PARA: "CANCELADO" ❌
✅ Card fica com fundo VERMELHO
✅ Mensagem: "Cancelado pelo barbeiro: Estou doente"
✅ Mostra sugestão: "Barbeiro sugeriu: 21/01/2025 14:00"
```

### Verificar no Cliente:
- **Navegador 1** (Cliente)
- Aba "Agenda"
- Encontrar agendamento rejeitado
```
❌ CANCELADO
Motivo: Barbeiro está doente
⏰ Sugestão: 21/01/2025 às 14:00

[Reagendar] [Escolher Outro Barbeiro]
```

---

## 🧪 TESTE 7: Aba de Avaliação (Cliente)

### Pré-Requisito:
- Agendamento com status "CONCLUIDO"
- Se nenhum existir, criar um novo e marcar manualmente como CONCLUIDO

### Passos:
1. Na conta **CLIENTE** (navegador 1)
2. Clicar na nova aba **"Avaliar"** ⭐
3. Verificar seção **"Avaliações Pendentes"**

### Resultado Esperado:
```
✅ Mostra: "Você tem 1 avaliação pendente"
✅ Lista agendamentos completos não avaliados:

   📅 20/01/2025 10:00
   ✂️  Corte de cabelo
   👨 João Barbeiro @ BarberShop
   
   [Avaliar] ← Botão para abrir modal

✅ Clique em "Avaliar"
✅ Modal abre com:
   - 5 Estrelas interativas
   - Campo de comentário (max 500 chars)
   - Botões: Cancel / Enviar
```

### Submeter Avaliação:
1. **Selecionar nota:** Clicar em 5ª estrela
2. **Feedback visual:** Mostrar "Excelente!"
3. **Comentário:** "João fez um corte perfeito! Recomendo!"
4. Clicar **"Enviar"**

### Resultado Esperado:
```
✅ Modal fecha com mensagem: "Avaliação enviada com sucesso!"
✅ Avaliação removida de "Pendentes"
✅ Seção "Avaliações" mostra:
   - Nota média atualizada
   - Histograma de distribuição
   - Nova avaliação na lista de histórico
```

---

## 🧪 TESTE 8: Visualizar Avaliações do Barbeiro

### Passos:
1. Na conta **BARBEIRO** (navegador 2)
2. Ir para perfil ou aba de avaliações (quando implementado)
3. Procurar seção **"Minhas Avaliações"**

### Resultado Esperado:
```
✅ Mostra avaliação submetida pelo cliente:
   Nota: ⭐⭐⭐⭐⭐ (5 estrelas)
   Comentário: "João fez um corte perfeito! Recomendo!"
   Data: 20/01/2025 às 11:00
   Cliente: João Silva

✅ Média atualizada: 4.8 ⭐ (ou valor calculado)
✅ Histograma mostrando:
   5★: 1 avaliação
   4★: 0 avaliações
   3★: 0 avaliações
   2★: 0 avaliações
   1★: 0 avaliações
```

---

## 🧪 TESTE 9: Liberar Cadeira Após Serviço

### Passos:
1. Na conta **BARBEARIA** (navegador 3)
2. Ir para **"Cadeiras"**
3. Encontrar cadeira BLOQUEADA
4. Clicar nela
5. Botão **"Liberar Cadeira"** aparece
6. Clicar **"Liberar"**

### Resultado Esperado:
```
✅ Notificação: "Cadeira liberada com sucesso!"
✅ Status MUDA PARA: "DISPONÍVEL" ✅
✅ Cadeira removed from blocked list
✅ Agendamento status: CONCLUIDO
✅ Cadeira pode ser agendada novamente

Status antes:
Cadeira #2: BLOQUEADA 🔒 (Agendamento #123)

Status depois:
Cadeira #2: DISPONÍVEL ✅ (sem vínculo)
```

---

## 🧪 TESTE 10: Fluxo Completo (Simulação)

### Timeline de 1 Segundo para Outro:

```
T0: 09:00 - CLIENTE cria agendamento
    ✓ aba "Buscar" → cria novo → status PENDENTE

T1: 09:05 - BARBEIRO aprova
    ✓ aba "Meus Agendamentos" → clica Aprovar
    ✓ Status: PENDENTE (aguardando barbearia)

T2: 09:07 - BARBEARIA aprova  
    ✓ aba "Agendamentos" → clica Aprovar
    ✓ Status: CONFIRMADO 🎉
    ✓ Cadeira fica BLOQUEADA

T3: 09:10 - Outro CLIENTE tenta agendar mesma hora
    ✓ Erro: cadeira indisponível
    ✓ Sugestão de horários

T4: 10:00 - Serviço começa

T5: 10:30 - Serviço termina
    ✓ BARBEIRO clica "Serviço Concluído"
    ✓ Cadeira liberada
    ✓ Status: CONCLUIDO

T6: 11:00 - CLIENTE avalia
    ✓ aba "Avaliar" → clica Avaliar
    ✓ Seleciona 5 estrelas
    ✓ Comenta
    ✓ Clica Enviar

T7: 11:01 - BARBEIRO vê avaliação
    ✓ Perfil/Avaliações mostra nova avaliação
    ✓ Média atualizada
```

---

## 📊 Checklist de Verificação

```
AGENDAMENTO:
☐ Cliente consegue criar novo agendamento
☐ Status inicial é PENDENTE
☐ Aparecem dois checkboxes vazios

APROVAÇÃO BARBEIRO:
☐ Barbeiro consegue aprovar
☐ Status continua PENDENTE
☐ Checkbox barbeiro fica marcado
☐ Cliente vê checkbox marcado

APROVAÇÃO BARBEARIA:
☐ Barbearia consegue aprovar
☐ Status MUDA para CONFIRMADO
☐ Ambos checkboxes ficam marcados
☐ Card fica verde
☐ Aparece mensagem "Agendamento Confirmado!"

CADEIRA BLOQUEADA:
☐ Cadeira aparece com status BLOQUEADA
☐ Vinculação correta (chamado_id)
☐ Outro cliente NÃO consegue agendar

REJEIÇÃO:
☐ Barbeiro consegue rejeitar
☐ Status MUDA para CANCELADO
☐ Card fica vermelho
☐ Motivo é exibido
☐ Sugestão é exibida

AVALIAÇÃO:
☐ Aba "Avaliar" aparece (5ª aba)
☐ Mostra agendamentos pendentes
☐ Modal abre com 5 estrelas
☐ Campo comentário funciona
☐ Avaliação é salva
☐ Barbeiro vê avaliação
☐ Média é atualizada

CADEIRA LIBERADA:
☐ Botão "Liberar" aparece
☐ Cadeira status muda para DISPONÍVEL
☐ Agendamento status muda para CONCLUIDO
☐ Cadeira pode ser agendada novamente

GERAL:
☐ Nenhum erro no console (F12)
☐ Nenhum erro no backend (logs)
☐ Banco de dados atualizado corretamente
☐ Interface responsiva em mobile
☐ Performance aceitável (<500ms por requisição)
```

---

## 🐛 Possíveis Issues e Soluções

### Issue 1: Agendamento não aparece após criar
**Solução:**
- Fazer refresh na página (F5)
- Verificar no console (F12) se há erro 404 ou 500
- Verificar token JWT no localStorage

### Issue 2: Status não muda após aprovar
**Solução:**
- Verificar permissões de token
- Fazer refresh na página
- Verificar logs do backend

### Issue 3: Cadeira não aparece como BLOQUEADA
**Solução:**
- Verificar se ambas aprovações foram confirmadas
- Fazer GET /barbearia/{id}/cadeiras-status manualmente
- Verificar se modelo Cadeira foi atualizado no BD

### Issue 4: Avaliação não salva
**Solução:**
- Verificar se endpoints de avaliação existem
- Confirmar que chamado_id está correto
- Ver logs no console (F12) para erro exato

### Issue 5: Modal não aparece
**Solução:**
- Verificar se componente AvaliacaoModal.jsx foi criado
- Verificar imports em ClientDashboard.jsx
- Fazer npm run dev novamente

---

## 📞 Contato / Dúvidas

Se algum teste falhar:

1. **Verificar logs do backend:**
   ```bash
   # Ver erros do servidor
   # Terminal rodando python run.py
   ```

2. **Verificar console do frontend:**
   ```
   # Abrir Dev Tools (F12)
   # Aba "Console"
   # Procurar por erros vermelhos
   ```

3. **Verificar banco de dados:**
   ```bash
   # Exemplo no SQLite
   sqlite3 database.db
   SELECT * FROM chamados WHERE id = 123;
   SELECT * FROM cadeiraas WHERE chamado_id = 123;
   ```

---

## ✅ Conclusão

Se todos os 10 testes passarem, o sistema de aprovações bidirecional está **100% funcional** e pronto para produção!

**Status Esperado:** 🟢 VERDE - Sistema em funcionamento

---

**Guia criado em:** 2025  
**Última atualização:** 2025  
**Versão:** 1.0
