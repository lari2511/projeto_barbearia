# 🚀 GUIA DE INSTALAÇÃO RÁPIDA - BarberMove Completo

## ⚡ Setup Rápido (5 minutos)

### 1️⃣ Preparar Ambiente

```powershell
# Ir para o diretório do projeto
cd C:\projeto_barbearia

# Ativar ambiente virtual
.\venv\Scripts\Activate.ps1

# Instalar TODAS as dependências
pip install -r requirements.txt
```

### 2️⃣ Recriar Banco de Dados

**IMPORTANTE:** O banco antigo não tem todas as tabelas novas!

```powershell
# Deletar banco antigo
Remove-Item barbearia.db -ErrorAction SilentlyContinue

# Servidor vai criar automaticamente com todas as tabelas
```

### 3️⃣ Rodar Servidor

```powershell
uvicorn app.main:app --reload
```

✅ Servidor rodando em: `http://localhost:8000`  
✅ Documentação: `http://localhost:8000/docs`

### 4️⃣ Testar Funcionalidades

```powershell
# Em outro terminal
python test_todas_funcionalidades.py
```

---

## 📋 Checklist de Instalação

- [ ] Ambiente virtual ativado
- [ ] Dependências instaladas (`pip install -r requirements.txt`)
- [ ] Banco de dados antigo deletado
- [ ] Servidor rodando (`uvicorn app.main:app --reload`)
- [ ] Documentação acessível (`http://localhost:8000/docs`)
- [ ] Teste executado com sucesso

---

## 🆕 O Que Mudou?

### Backend Python

**Novos Arquivos:**
- `app/routes_extras.py` - 600+ linhas de novas rotas
- `app/models.py` - 9 novos models
- `app/schemas.py` - 15+ novos schemas
- `FUNCIONALIDADES.md` - Documentação completa
- `test_todas_funcionalidades.py` - Script de teste

**Arquivos Modificados:**
- `app/main.py` - Incluiu routes_extras
- `app/routes.py` - Adicionou histórico e notificações
- `requirements.txt` - pyotp, qrcode, pillow

### Banco de Dados

**Novas Tabelas:**
```
✅ avaliacoes           - Sistema de avaliações
✅ favoritos            - Barbeiros/barbearias favoritas
✅ fotos                - Portfolio de fotos
✅ cupons               - Cupons de desconto
✅ pontos_fidelidade    - Sistema de pontos
✅ chamados_historico   - Timeline de chamados
✅ tokens_recuperacao   - Reset de senha
✅ notificacoes         - Notificações
✅ mensagens_chat       - Chat em tempo real
```

**Tabelas Atualizadas:**
```
✅ usuarios   - +email_verificado, +2fa, +geolocalização
✅ barbearias - +latitude, +longitude
✅ chamados   - +timestamps, +cupom, +valores
```

---

## 🎯 Endpoints Disponíveis

### Avaliações ⭐
- `POST /api/v1/avaliacoes/` - Criar avaliação
- `GET /api/v1/usuario/{id}/avaliacoes` - Listar avaliações
- `GET /api/v1/usuario/{id}/media_avaliacao` - Média

### Favoritos ❤️
- `POST /api/v1/favoritos/` - Adicionar
- `GET /api/v1/favoritos/` - Listar
- `DELETE /api/v1/favoritos/{id}` - Remover

### Cupons 🎟️
- `POST /api/v1/cupons/` - Criar
- `GET /api/v1/cupons/` - Listar ativos
- `POST /api/v1/cupons/validar` - Validar

### Fidelidade 🏆
- `GET /api/v1/fidelidade/` - Consultar pontos

### Fotos 📸
- `POST /api/v1/fotos/` - Adicionar
- `GET /api/v1/usuario/{id}/fotos` - Listar

### Geolocalização 📍
- `POST /api/v1/barbearias/proximas` - Buscar próximas

### Agendamento 📅
- `POST /api/v1/chamados/agendar` - Agendar futuro

### Histórico 📜
- `GET /api/v1/chamados/{id}/historico` - Timeline

### Notificações 🔔
- `GET /api/v1/notificacoes/` - Listar
- `PUT /api/v1/notificacoes/{id}/ler` - Marcar lida

### Chat 💬
- `POST /api/v1/chat/mensagem` - Enviar
- `GET /api/v1/chat/{id}/mensagens` - Listar

### Senha 🔑
- `POST /api/v1/recuperar-senha` - Solicitar token
- `POST /api/v1/resetar-senha` - Resetar

### Estatísticas 📊
- `GET /api/v1/estatisticas/` - Dashboard

### 2FA 🔐
- `POST /api/v1/2fa/ativar` - Ativar
- `POST /api/v1/2fa/verificar` - Verificar
- `POST /api/v1/2fa/desativar` - Desativar

---

## 🧪 Teste Rápido via Docs

1. Acesse `http://localhost:8000/docs`
2. Cadastre um cliente: `POST /api/v1/clientes/`
3. Faça login: `POST /api/v1/login/cliente/`
4. Copie o `access_token`
5. Clique em **Authorize** (cadeado verde)
6. Cole o token e clique **Authorize**
7. Agora pode testar endpoints protegidos! 🎉

---

## 🐛 Solução de Problemas

### Erro: "Table doesn't exist"
```powershell
# Deletar banco e reiniciar servidor
Remove-Item barbearia.db
uvicorn app.main:app --reload
```

### Erro: "Module not found"
```powershell
# Reinstalar dependências
pip install -r requirements.txt
```

### Erro: "Port already in use"
```powershell
# Usar outra porta
uvicorn app.main:app --reload --port 8001
```

### Erro 401 (Unauthorized)
- Verifique se fez login
- Copie o token correto
- Use **Authorize** na documentação

---

## 📱 Frontend (Opcional)

Para rodar o frontend React:

```powershell
cd C:\projeto_barbearia\barbermove
npm install
npm run dev
```

**Nota:** Frontend precisa ser atualizado para usar novas funcionalidades!

---

## 🔥 Comandos Úteis

```powershell
# Rodar servidor (desenvolvimento)
uvicorn app.main:app --reload

# Rodar servidor (produção)
uvicorn app.main:app --host 0.0.0.0 --port 8000

# Testar todas funcionalidades
python test_todas_funcionalidades.py

# Ver logs do servidor
# (Ctrl+C para parar)

# Criar seed de dados
python seed_database.py
```

---

## 📖 Documentação Completa

- `README.md` - Documentação original
- `FUNCIONALIDADES.md` - **Todas as novas features**
- `GUIA_PWA.md` - PWA e instalação
- `http://localhost:8000/docs` - API interativa

---

## ✅ Tudo Pronto!

Agora você tem:
- ✅ 16 funcionalidades completas
- ✅ API REST completa
- ✅ Documentação interativa
- ✅ Testes automatizados
- ✅ Segurança (JWT, 2FA, hashing)
- ✅ Sistema de pontos e cupons
- ✅ Chat e notificações
- ✅ Geolocalização
- ✅ Histórico completo

**Próximo passo:** Atualizar o frontend React! 🎨

---

## 🆘 Precisa de Ajuda?

1. Verifique `FUNCIONALIDADES.md` para detalhes
2. Teste via `http://localhost:8000/docs`
3. Execute `python test_todas_funcionalidades.py`
4. Verifique logs do servidor

**Bom desenvolvimento! 🚀**
