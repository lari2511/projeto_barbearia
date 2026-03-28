# COMO USAR: SISTEMA ON-DEMAND BARBER MOVE

Parabéns! O sistema foi validado com sucesso. Aqui está como usar:

---

## 1. INICIAR O SERVIDOR

```bash
# Terminal 1: Ativar ambiente Python
cd c:\projeto_barbearia
.\.venv\Scripts\Activate.ps1

# Iniciar servidor
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

**Você verá**:
```
INFO:     Uvicorn running on http://127.0.0.1:8000
INFO:     Application startup complete
```

---

## 2. ACESSAR DOCUMENTACAO

Abra no navegador: **http://localhost:8000/docs**

Você verá:
- Todos os 11 endpoints disponíveis
- Parâmetros de cada endpoint
- Exemplos de request/response
- Botão "Try it out" para testar


### Endpoints Disponíveis

**ON-DEMAND (7 endpoints)**:
- `GET /api/v1/on-demand/ligar-radar` - Barbeiro fica online
- `PUT /api/v1/on-demand/atualizar-localizacao` - Atualizar GPS
- `GET /api/v1/on-demand/barbeiros-proximos` - Buscar barbeiros próximos
- `POST /api/v1/on-demand/solicitar-barbeiro` - Cliente solicita barbeiro
- `GET /api/v1/on-demand/minhas-solicitacoes` - Ver solicitações do cliente
- `PUT /api/v1/on-demand/aceitar-solicitacao/{id}` - Barbeiro aceita
- `DELETE /api/v1/on-demand/cancelar-solicitacao/{id}` - Cancelar pedido

**FIREBASE (4 endpoints)**:
- `GET /api/v1/firebase/status` - Status do Firebase
- `POST /api/v1/firebase/register-token` - Registrar device token FCM
- `POST /api/v1/firebase/test-notification` - Enviar notificação teste
- `POST /api/v1/firebase/broadcast` - Enviar para múltiplos usuários

---

## 3. FAZER LOGIN

Usar Swagger para testar login primeiro:

1. Clique em "Authorize" (se houver)
2. Faça POST em `/api/v1/login` com:
   ```json
   {
     "email": "barbeiro@teste.com",
     "senha": "123456"
   }
   ```
3. Copiar o JWT token retornado

---

## 4. USAR O SISTEMA COMO BARBEIRO

### Passo 1: Ativar o Radar
```bash
curl -X GET http://localhost:8000/api/v1/on-demand/ligar-radar \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

**Resposta esperada**:
```json
{
  "status": "success",
  "mensagem": "Radar ativado com sucesso"
}
```

### Passo 2: Atualizar Localização
```bash
curl -X PUT http://localhost:8000/api/v1/on-demand/atualizar-localizacao \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "latitude": -23.5505,
    "longitude": -46.6333
  }'
```

### Passo 3: Aceitar Solicitações
Quando um cliente solicita um barbeiro, você recebe notificação e pode aceitar:
```bash
curl -X PUT http://localhost:8000/api/v1/on-demand/aceitar-solicitacao/1 \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

---

## 5. USAR O SISTEMA COMO CLIENTE

### Passo 1: Login
```bash
curl -X POST http://localhost:8000/api/v1/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "cliente@teste.com",
    "senha": "123456"
  }'
```

### Passo 2: Buscar Barbeiros Próximos
```bash
curl -X GET "http://localhost:8000/api/v1/on-demand/barbeiros-proximos?latitude=-23.5505&longitude=-46.6333&raio_km=5" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

**Resposta esperada**:
```json
{
  "barbeiros": [
    {
      "id": 1,
      "nome": "Joao Barbeiro",
      "distancia_km": 0.5,
      "latitude": -23.5520,
      "longitude": -46.6340
    }
  ],
  "total_encontrados": 1
}
```

### Passo 3: Solicitar Barbeiro
```bash
curl -X POST http://localhost:8000/api/v1/on-demand/solicitar-barbeiro \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "barbeiro_id": 1,
    "servico": "corte",
    "valor": 50.0
  }'
```

### Passo 4: Acompanhar Localização
Uma vez aceito, você recebe atualizações de GPS em tempo real do barbeiro até chegar.

---

## 6. TESTAR NOTIFICACOES FIREBASE

### Enviar notificação teste
```bash
curl -X POST http://localhost:8000/api/v1/firebase/test-notification \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "usuario_id": 2,
    "titulo": "Barbeiro próximo!",
    "mensagem": "João está a 500m de você"
  }'
```

(Precisa de `device_token` registrado no dispositivo)

---

## 7. ACOMPANHAR PERFORMANCE

Verificar logs do servidor:
```bash
# No terminal onde rodou uvicorn, você verá:
INFO:     127.0.0.1:57824 - "GET /api/v1/on-demand/barbeiros-proximos HTTP/1.1" 401
INFO:     Haversine: 2.18km em 0.0017ms
```

---

## 8. ESTRUTURA DE PASTA

```
c:\projeto_barbearia\
├── app/
│   ├── main.py                 # Servidor FastAPI
│   ├── models.py               # 33 modelos SQLAlchemy
│   ├── database.py             # Configuração banco
│   ├── routes_on_demand.py     # 7 endpoints On-Demand
│   ├── routes_firebase.py      # 4 endpoints Firebase
│   ├── firebase_config.py      # Configuração Firebase
│   └── ... (25 outros arquivos de routes)
├── barbearia.db                # Banco de dados SQLite
├── test_simples.py             # Testes validação (10/10 OK)
├── setup_usuarios_teste.py     # Script criar usuários
├── VALIDACAO_COMPLETA.md       # Este relatório
└── ... (11 docs adicionais)
```

---

## TROUBLESHOOTING

### Erro: "Conexão recusada na porta 8000"
```bash
# Verifique se servidor está rodando:
netstat -ano | findstr :8000
# Se nada aparecer, execute: uvicorn app.main:app --reload --port 8000
```

### Erro: "JWT inválido"
```bash
# Refaça login:
curl -X POST http://localhost:8000/api/v1/login \
  -H "Content-Type: application/json" \
  -d '{"email": "barbeiro@teste.com", "senha": "123456"}'
# Copie o novo token da resposta
```

### Erro: "Firebase não configurado"
```bash
# Isso é normal se não tiver credenciais Firebase
# Sistema funciona sem Firebase, mas sem notificações push
# Para ativar: Crie firebase-credentials.json na raiz
```

### Erro: "Banco de dados bloqueado"
```bash
# Feche todos os processos Python:
# Ctrl+C no terminal do servidor
# Depois execute: python rebuild_db.py
```

---

## PROXIMAS MELHORIAS

- [ ] Autenticação OAuth2 (Google, Facebook)
- [ ] Integração com pagamento (Stripe, PagSeguro)
- [ ] Sistema de avaliações e reviews
- [ ] Chat em tempo real (WebSocket)
- [ ] Agendamentos futuros (além de on-demand)
- [ ] Histórico de transações e relatórios
- [ ] Suporte a múltiplas barbearias
- [ ] Dark mode no app

---

**Enjoy! Sistema está pronto para usar** 🎉
