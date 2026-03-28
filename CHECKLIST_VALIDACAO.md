# ✅ CHECKLIST DE VALIDAÇÃO - FEATURES IMPLEMENTADAS

## 1️⃣ EMAILS DE CONFIRMAÇÃO E APROVAÇÃO

### ☐ Teste: Cadastro de Barbeiro
- [ ] Acesse a página de Login
- [ ] Clique em "Criar Conta" → Barbeiro
- [ ] Preencha todos os dados
- [ ] Upload de portfólio (3 imagens)
- [ ] Upload de documentos (frente, verso, selfie)
- [ ] Clique em "Criar Conta"
- **✅ Esperado**: Email recebido com "⏳ Perfil em Análise"

### ☐ Teste: Aprovação por Admin
- [ ] Vá para `http://localhost:5173/admin`
- [ ] Faça login como admin
- [ ] Veja usuários pendentes
- [ ] Clique em um usuário
- [ ] Visualize documentos e portfólio
- [ ] Clique "Aprovar"
- **✅ Esperado**: Email recebido com "✅ Perfil Aprovado"

---

## 2️⃣ DASHBOARD ADMIN

### ☐ Teste: Visualizar Documentos
- [ ] Admin dashboard aberto
- [ ] Clique em usuário pendente
- [ ] Veja foto de frente do documento
- [ ] Veja foto de verso do documento
- [ ] Veja selfie com documento
- [ ] Veja portfólio (se houver)

### ☐ Teste: Listar Usuários
- [ ] Verifique aba "Pendentes"
- [ ] Verifique aba "Aprovados"
- [ ] Use busca por email
- [ ] Veja estatísticas gerais (total, aprovados, barbeiros)

**Endpoints**:
```bash
curl http://localhost:8000/api/v1/notificacoes/pendentes
curl http://localhost:8000/api/v1/notificacoes/aprovados
curl http://localhost:8000/api/v1/notificacoes/usuario/1
```

---

## 3️⃣ FILTRO DE BARBEIROS DISPONÍVEIS

### ☐ Teste: Visualizar Filtro
- [ ] Faça login como cliente
- [ ] Vá para "Barbeiros"
- [ ] Veja botão "🟢 Mostrar apenas disponíveis"
- [ ] Botão mostra contagem de disponíveis

### ☐ Teste: Filtrar Disponibilidade
- [ ] Clique no botão para ativar filtro
- [ ] Botão fica verde
- [ ] Veja apenas barbeiros com 🟢 Disponível
- [ ] Clique novamente para desativar
- [ ] Veja todos os barbeiros de novo

### ☐ Teste: Status do Barbeiro
- [ ] Faça login como barbeiro
- [ ] No header veja botão "🟢 Disponível"
- [ ] Clique para mudar status
- [ ] Mude de 🟢 Disponível para ⚫ Ocupado
- [ ] Verifique em outro navegador (cliente) que mudou

---

## 4️⃣ SISTEMA DE NOTIFICAÇÕES

### ☐ Teste: Criar Notificação
```bash
# Backend: Ao criar chamado, notificação é criada automaticamente
curl -X GET http://localhost:8000/api/v1/notificacoes/ \
  -H "Authorization: Bearer {token}"
```

### ☐ Teste: Listar Notificações
- [ ] Endpoint: `GET /api/v1/notificacoes/`
- [ ] Deve retornar lista de notificações
- [ ] Cada uma com titulo, mensagem, tipo

### ☐ Teste: Marcar Como Lida
```bash
curl -X POST http://localhost:8000/api/v1/notificacoes/1/marcar-lida \
  -H "Authorization: Bearer {token}"
```
- [ ] Notificação marcada como `lida: true`

### ☐ Teste: Contar Não Lidas
```bash
curl -X GET http://localhost:8000/api/v1/notificacoes/nao-lidas/count \
  -H "Authorization: Bearer {token}"
```
- [ ] Retorna número de notificações não lidas

---

## 5️⃣ GERENCIADOR DE PREÇOS

### ☐ Teste: Listar Serviços
```bash
curl -X POST http://localhost:8000/api/v1/precos/listar-todos-servicos \
  -H "Authorization: Bearer {token_barbeiro}"
```
- [ ] Retorna lista de serviços
- [ ] Mostra preço original
- [ ] Mostra se tem customização

### ☐ Teste: Customizar Preço
```bash
curl -X POST http://localhost:8000/api/v1/precos/customizar/1 \
  -H "Authorization: Bearer {token_barbeiro}" \
  -H "Content-Type: application/json" \
  -d '{"valor_novo": 50}'
```
- [ ] Preço atualizado com sucesso
- [ ] Desconto % calculado automaticamente

### ☐ Teste: Remover Customização
```bash
curl -X DELETE http://localhost:8000/api/v1/precos/1 \
  -H "Authorization: Bearer {token_barbeiro}"
```
- [ ] Customização removida
- [ ] Volta ao preço original

### ☐ Teste: Obter Preço
```bash
curl -X GET http://localhost:8000/api/v1/precos/servico/1?barbeiro_id=5 \
  -H "Authorization: Bearer {token}"
```
- [ ] Retorna preço customizado ou original
- [ ] Campo `customizado: true/false`

---

## 6️⃣ ANALYTICS DE AVALIAÇÕES

### ☐ Teste: Estadísticas do Barbeiro
```bash
curl -X GET http://localhost:8000/api/v1/analytics/barbeiro/estatisticas \
  -H "Authorization: Bearer {token_barbeiro}"
```
- [ ] Retorna média de notas
- [ ] Total de avaliações
- [ ] Distribuição por nota (5⭐, 4⭐, 3⭐, 2⭐, 1⭐)
- [ ] Avaliações do último mês
- [ ] Tendência (subindo/estavel/caindo)

### ☐ Teste: Resumo da Reputação
```bash
curl -X GET http://localhost:8000/api/v1/analytics/barbeiro/resumo \
  -H "Authorization: Bearer {token_barbeiro}"
```
- [ ] Media: número com uma casa decimal (ex: 4.5)
- [ ] Total: quantidade total de reviews
- [ ] Cinco estrelas: contagem de 5⭐
- [ ] Percentual de 5 estrelas: ex 62.5%

### ☐ Teste: Últimas Avaliações
```bash
curl -X GET http://localhost:8000/api/v1/analytics/barbeiro/minhas-avaliacoes \
  -H "Authorization: Bearer {token_barbeiro}"
```
- [ ] Retorna últimas 50 avaliações
- [ ] Com nome do avaliador
- [ ] Nota (1-5)
- [ ] Comentário
- [ ] Data criação

### ☐ Teste: Analytics da Barbearia
- [ ] Endpoints `/barbearia/` funcionar igual ao `/barbeiro/`
- [ ] Retornar dados corretos de barbearia

---

## 🌐 ENDPOINTS DE API - REFERÊNCIA RÁPIDA

### Notificações
```
GET    /api/v1/notificacoes/
GET    /api/v1/notificacoes/?nao_lidas_apenas=true
POST   /api/v1/notificacoes/{id}/marcar-lida
POST   /api/v1/notificacoes/marcar-todas-lidas
DELETE /api/v1/notificacoes/{id}
GET    /api/v1/notificacoes/nao-lidas/count
```

### Preços
```
GET  /api/v1/precos/meus-precos
POST /api/v1/precos/customizar/{servico_id}
DELETE /api/v1/precos/{preco_id}
GET  /api/v1/precos/servico/{servico_id}
POST /api/v1/precos/listar-todos-servicos
```

### Analytics
```
GET /api/v1/analytics/barbeiro/minhas-avaliacoes
GET /api/v1/analytics/barbeiro/estatisticas
GET /api/v1/analytics/barbeiro/resumo
GET /api/v1/analytics/barbearia/minhas-avaliacoes
GET /api/v1/analytics/barbearia/estatisticas
GET /api/v1/analytics/barbearia/resumo
```

### Admin
```
GET  /admin/api/pendentes
GET  /admin/api/aprovados
GET  /admin/api/usuario/{id}
GET  /admin/api/estatisticas
GET  /admin/api/buscar?q=termo
POST /admin/api/aprovar/{id}
POST /admin/api/rejeitar/{id}
```

---

## 🧪 TESTE COM CURL

### 1. Adicionar Notificação
```bash
curl -X POST http://localhost:8000/api/v1/notificacoes/ \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer {token}" \
  -d '{
    "usuario_id": 1,
    "titulo": "Teste",
    "mensagem": "Notificação de teste",
    "tipo": "novo_chamado"
  }'
```

### 2. Listar Notificações
```bash
curl http://localhost:8000/api/v1/notificacoes/ \
  -H "Authorization: Bearer {token}"
```

### 3. Ver Documentação Swagger
```
http://localhost:8000/docs
```

---

## ⚠️ TROUBLESHOOTING

### Email não está sendo enviado?
- [ ] Verificar variáveis `.env` (SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASS)
- [ ] Verificar se email está na lista de permitidos
- [ ] Checar logs do backend

### Notificações não aparecem?
- [ ] Verificar se `BackgroundTasks` foi importado nas rotas
- [ ] Verificar se banco de dados tem tabela `notificacoes`

### Preços customizados não salvam?
- [ ] Verificar se usuário é barbeiro (`usuario.tipo == 'barbeiro'`)
- [ ] Verificar se serviço existe no banco

### Analytics retorna vazio?
- [ ] Criar algumas avaliações primeiro
- [ ] Verificar se avaliações foram criadas para o usuário correto

---

## 📝 OBSERVAÇÕES

- Todos os endpoints requerem autenticação com JWT
- Passar token no header: `Authorization: Bearer {seu_token_aqui}`
- Para obter token: faça login em `/api/v1/login/`
- Todos os timestamps estão em UTC
- Respostas no formato JSON

---

## ✅ CHECKLIST FINAL

- [ ] Email de confirmação funciona
- [ ] Email de aprovação funciona  
- [ ] Admin visualiza documentos
- [ ] Admin aprova usuários
- [ ] Filtro de disponibilidade aparece
- [ ] Barbeiro pode mudar status
- [ ] Notificações aparecem
- [ ] Preços podem ser customizados
- [ ] Analytics mostra dados corretos
- [ ] Sem erros no console (frontend/backend)
- [ ] Aplicação pronta para testes de usuário

---

**Última atualização**: 2025  
**Status**: ✅ PRONTO PARA TESTES
