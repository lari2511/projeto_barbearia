# 🚀 BarberMove - Sistema Completo de Agendamento para Barbearias

[![Status](https://img.shields.io/badge/status-100%25%20Funcional-success)](.)
[![Backend](https://img.shields.io/badge/backend-FastAPI-009688)](.)
[![Frontend](https://img.shields.io/badge/frontend-React-61DAFB)](.)
[![Mobile](https://img.shields.io/badge/mobile-PWA%20%2B%20Android-green)](.)

## 📋 Visão Geral

Plataforma completa de agendamento tipo "Uber para Barbearias" com três tipos de usuários:
- **👤 Clientes**: Buscam e agendam serviços, avaliam, ganham pontos
- **✂️ Barbeiros**: Aceitam trabalhos, gerenciam agenda, recebem avaliações
- **🏪 Barbearias**: Gerenciam serviços, equipe e disponibilidade

## ✨ Funcionalidades Principais

### 🔐 Autenticação & Segurança
- ✅ Login/Cadastro JWT
- ✅ Autenticação 2FA (Google Authenticator)
- ✅ Verificação de documentos (RG/CNH)
- ✅ Senhas criptografadas (Argon2)
- ✅ Recuperação de senha

### 💼 Funcionalidades Tipo "Uber"
- ✅ Geolocalização (buscar barbearias próximas)
- ✅ Agendamento em tempo real
- ✅ Chat entre cliente e barbeiro
- ✅ Avaliações e comentários ⭐
- ✅ Sistema de favoritos ❤️
- ✅ Notificações push 🔔
- ✅ Histórico completo de serviços
- ✅ Badge de perfil verificado ✓

### 💰 Financeiro
- ✅ **Pagamento PIX com QR Code**
- ✅ Cupons de desconto 🎟️
- ✅ Programa de fidelidade (pontos)
- ✅ Relatórios de ganhos
- ✅ Comissão da plataforma (15%)

### 📱 Mobile
- ✅ PWA (instalar no celular)
- ✅ APK Android nativo
- ✅ Modo offline (básico)

## 🚀 INÍCIO RÁPIDO (3 minutos)

### Opção 1: Script Automático (Recomendado)
```powershell
# Na raiz do projeto:
.\iniciar_app.ps1
```
Isso vai:
- ✅ Configurar ambiente Python
- ✅ Instalar dependências
- ✅ Iniciar backend (http://localhost:8000)
- ✅ Iniciar frontend (http://localhost:5173)

### Opção 2: Manual

#### 1. Backend
```powershell
# Ativar ambiente virtual
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt

# Iniciar servidor
python run.py
```
✅ Backend: `http://localhost:8000`  
📚 API Docs: `http://localhost:8000/docs`

#### 2. Frontend
```powershell
cd barbermove
npm install
npm run dev
```
✅ Frontend: `http://localhost:5173`

---

## 📱 GERAR APK/PWA

```powershell
# Na raiz do projeto:
.\build_producao.ps1
```

Isso vai:
- ✅ Gerar PWA otimizado (barbermove/dist/)
- ✅ Gerar APK Android (opcional)
- ✅ Criar cópia do APK na raiz

---

## 🎯 CONTAS DE TESTE

Após iniciar o app, você pode criar suas próprias contas ou usar o seed:

```powershell
python seed_database.py
```

Contas criadas:
- **Cliente:** cliente@test.com / senha123
- **Barbeiro:** barbeiro@test.com / senha123
- **Barbearia:** barbearia@test.com / senha123

---

## 📚 DOCUMENTAÇÃO COMPLETA

### 📖 Guias Técnicos
- 📖 [FINALIZACAO.md](FINALIZACAO.md) - **GUIA COMPLETO DE FINALIZAÇÃO**
- 🚀 [DEPLOY.md](DEPLOY.md) - Como publicar nas lojas e nuvem
- ✨ [FUNCIONALIDADES.md](FUNCIONALIDADES.md) - Todas as 16+ funcionalidades
- 📱 [GUIA_PWA.md](GUIA_PWA.md) - Progressive Web App
- 🏪 [GUIA_SERVICOS_BARBEARIA.md](GUIA_SERVICOS_BARBEARIA.md) - Sistema de serviços
- ⏰ [GUIA_VALIDACAO_HORARIOS.md](GUIA_VALIDACAO_HORARIOS.md) - Validação de horários

### ⚖️ Documentos Legais
- 📄 [TERMOS_DE_USO.md](TERMOS_DE_USO.md) - Termos de uso e condições gerais
- 🔒 [POLITICA_PRIVACIDADE.md](POLITICA_PRIVACIDADE.md) - Política de privacidade LGPD

**Acesso via API:**
- `http://localhost:8000/api/v1/termos-de-uso` - Termos em HTML
- `http://localhost:8000/api/v1/politica-privacidade` - Privacidade em HTML
- Também acessível diretamente no app (links na tela de login)

---

## 🏗️ ARQUITETURA

```
projeto_barbearia/
├── app/                          # Backend FastAPI
│   ├── main.py                   # App principal
│   ├── routes.py                 # Rotas principais (auth, users, chamados)
│   ├── routes_pagamentos.py      # Sistema de pagamentos PIX
│   ├── routes_documentos.py      # Verificação de documentos
│   ├── routes_extras.py          # Avaliações, favoritos, cupons
│   ├── routes_servicos.py        # CRUD de serviços
│   ├── routes_relatorio.py       # Relatórios financeiros
│   ├── models.py                 # Modelos do banco de dados
│   ├── schemas.py                # Validação Pydantic
│   └── database.py               # Configuração SQLAlchemy
├── barbermove/                   # Frontend React
│   ├── src/
│   │   ├── App.jsx              # App principal
│   │   └── components/
│   │       ├── ClientDashboard.jsx
│   │       ├── BarberDashboard.jsx
│   │       ├── ShopDashboard.jsx
│   │       ├── TelaPagamento.jsx
│   │       └── VerificacaoDocumentos.jsx
│   ├── android/                 # Projeto Android (Capacitor)
│   └── public/                  # Assets públicos
├── .env                         # Configurações (SECRET_KEY, CORS)
├── requirements.txt             # Dependências Python
├── iniciar_app.ps1              # Script para rodar tudo
├── build_producao.ps1           # Script para gerar builds
└── barbearia.db                 # Banco SQLite (gerado automaticamente)
```

---

## Funcionalidades Principais

### Autenticação
- **Cadastro** de cliente, barbeiro ou barbearia
- **Login** com JWT (access_token Bearer)
- **Hashing de senhas** com bcrypt (passlib)
- Endpoints protegidos com dependência `get_current_user`

### Fluxo Cliente
1. Cadastro/Login
2. Buscar barbearias disponíveis
3. Ver serviços de uma barbearia
4. Agendar serviço (cria Chamado)
5. Ver histórico de pedidos (com autorização Bearer token)

### Fluxo Barbearia
1. Cadastro/Login
2. Gerenciar status da cadeira (LIVRE/OCUPADA)
3. Adicionar/listar serviços
4. Visualizar serviços (via endpoint `/api/v1/barbearia/{id}/servicos`)

### Fluxo Barbeiro
1. Cadastro/Login
2. Buscar chamados abertos (`/api/v1/chamados/abertos`)
3. Aceitar trabalho (`PUT /api/v1/chamados/{id}/aceitar`)
4. Finalizar serviço (`PUT /api/v1/chamados/{id}/finalizar`)
5. Ver histórico de trabalhos (`/api/v1/barbeiro/trabalhos`)

---

## Endpoints Principais

### Autenticação
| Método | Rota | Descrição |
|--------|------|-----------|
| POST | `/api/v1/clientes/` | Cadastrar cliente |
| POST | `/api/v1/barbeiros/` | Cadastrar barbeiro |
| POST | `/api/v1/barbearias/` | Cadastrar barbearia |
| POST | `/api/v1/login/cliente/` | Login cliente (retorna `access_token`) |
| POST | `/api/v1/login/barbeiro/` | Login barbeiro |
| POST | `/api/v1/login/barbearia/` | Login barbearia |

### Dados (GET)
| Método | Rota | Autenticação |
|--------|------|---------|
| GET | `/api/v1/barbearias/todas` | Não |
| GET | `/api/v1/barbearia/{id}/servicos` | Não |
| GET | `/api/v1/cliente/meus_pedidos` | Bearer Token |
| GET | `/api/v1/barbeiro/trabalhos` | Bearer Token |
| GET | `/api/v1/chamados/abertos` | Não |

### Operações (POST/PUT)
| Método | Rota | Autenticação |
|--------|------|---------|
| POST | `/api/v1/chamados` | Bearer Token (cliente) |
| POST | `/api/v1/servicos/` | Não (dono_id manual) |
| POST | `/api/v1/barbearia/servicos` | Bearer Token (barbearia) |
| PUT | `/api/v1/chamados/{id}/aceitar` | Bearer Token (barbeiro) |
| PUT | `/api/v1/chamados/{id}/finalizar` | Bearer Token (barbeiro) |
| PUT | `/api/v1/barbearia/cadeira?livre=true` | Bearer Token (barbearia) |

---

## Segurança (Melhorias Implementadas)

✅ **Hashing de Senhas**: bcrypt via `passlib`
✅ **JWT Token**: OAuth2 Bearer token com expiração de 7 dias
✅ **Autenticação**: `get_current_user` dependency injection
✅ **CORS**: Habilitado para frontend (origem `*` em desenvolvimento)

⚠️ **Para Produção:**
- Trocar `SECRET_KEY` em `app/routes.py` (use variável de ambiente)
- Desabilitar CORS wildcard; especificar origem do frontend
- Usar HTTPS obrigatório
- Adicionar validações adicionais e rate limiting

---

## Estrutura de Dados

### Usuario
```python
id: int (PK)
nome: str
email: str (unique)
senha_hash: str (bcrypt)
tipo: str ('cliente', 'barbeiro', 'barbearia')
telefone: str (nullable)
endereco: str (nullable)
cep: str (nullable)
cadeira_livre: bool (default True)
```

### Servico
```python
id: int (PK)
nome: str
valor: float
dono_id: int (FK -> Usuario)
```

### Chamado
```python
id: int (PK)
data_criacao: datetime
cliente_id: int (FK -> Usuario)
prestador_id: int (FK -> Usuario)
servico_id: int (FK -> Servico)
nome_cliente: str
nome_prestador: str
descricao: str
valor: float
endereco: str
status: str ('ABERTO', 'EM_ANDAMENTO', 'CONCLUIDO')
```

---

## Testes Rápidos (PowerShell)

### Cadastrar cliente
```powershell
$body = @{ nome='Teste'; email='teste@ex.com'; senha='123'; telefone='000' } | ConvertTo-Json
Invoke-RestMethod -Uri 'http://localhost:8000/api/v1/clientes/' -Method Post -Body $body -ContentType 'application/json'
```

### Fazer login
```powershell
$body = @{ email='teste@ex.com'; senha='123' } | ConvertTo-Json
Invoke-RestMethod -Uri 'http://localhost:8000/api/v1/login/cliente/' -Method Post -Body $body -ContentType 'application/json'
```

### Chamar endpoint protegido
```powershell
$token = "eyJ0eXAiOiJKV1QiLCJhbGc..." # do login
$headers = @{ 'Authorization' = "Bearer $token" }
Invoke-RestMethod -Uri 'http://localhost:8000/api/v1/cliente/meus_pedidos' -Headers $headers
```

---

## Problemas Comuns e Soluções

| Erro | Causa | Solução |
|------|-------|---------|
| 404 Not Found | Rota não existe ou typo no endpoint | Verificar URL exata (prefixo `/api/v1`) |
| 401 Unauthorized | Token inválido/expirado ou faltando header | Enviar `Authorization: Bearer <token>` |
| 400 Bad Request | Dados inválidos ou duplicação (email) | Verificar payload JSON e emails únicos |
| ModuleNotFoundError | Dependência não instalada | `pip install -r requirements.txt` |
| CORS error (frontend) | Requisição bloqueada pelo CORS | Servidor rodando? CORS ativo em main.py? |

---

## Roadmap & Melhorias Futuras

- [ ] Validações mais rigorosas (email, telefone)
- [ ] Paginação em listagens
- [ ] Busca e filtro de barbearias
- [ ] Sistema de avaliações/ratings
- [ ] Notificações em tempo real (WebSocket)
- [ ] Pagamento integrado (Stripe/MercadoPago)
- [ ] Autenticação OAuth2 (Google, GitHub)
- [ ] Dashboard de analytics (barbearias)
- [ ] Mobile app nativo (React Native)

---

## Contato & Suporte

Projeto em desenvolvimento. Para dúvidas, abra uma issue no repositório.

---

**Status**: ✅ Versão 1.0 - Funcional (Desenvolvimento)
**Data**: Dezembro 2025
