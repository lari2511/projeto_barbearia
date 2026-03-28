# 🔐 FLUXO COMPLETO DE VERIFICAÇÃO DE EMAIL

## 📋 RESUMO DO PROCESSO

```
┌─────────────────────────────────────────────────────────────────────┐
│ 1️⃣  REGISTRO DO USUÁRIO                                             │
└─────────────────────────────────────────────────────────────────────┘
     ↓
   POST /api/v1/clientes (ou /api/v1/barbeiros)
     ↓
   Backend:
   - Cria novo usuário com email_verificado = FALSE
   - Gera token JWT de verificação (válido por 24h)
   - Armazena token na coluna: token_verificacao
     ↓
   ✉️  Envia email em BACKGROUND (não bloqueia resposta)
     ↓
┌─────────────────────────────────────────────────────────────────────┐
│ 2️⃣  EMAIL ENVIADO AO USUÁRIO                                        │
└─────────────────────────────────────────────────────────────────────┘
     ↓
   Conteúdo do email:
   - Link: http://localhost:8000/api/v1/email/verificar?token=JWT_TOKEN
   - Botão clicável: "Verificar email"
     ↓
┌─────────────────────────────────────────────────────────────────────┐
│ 3️⃣  USUÁRIO CLICA NO LINK                                           │
└─────────────────────────────────────────────────────────────────────┘
     ↓
   GET /api/v1/email/verificar?token=JWT_TOKEN
     ↓
   Backend:
   - Decodifica o token JWT
   - Valida a assinatura e expiração (24h)
   - Busca o usuário pelo email no token
   - Marca: email_verificado = TRUE
   - Limpa: token_verificacao = NULL
     ↓
   Retorna: Página HTML com mensagem de sucesso
     ↓
┌─────────────────────────────────────────────────────────────────────┐
│ 4️⃣  FRONTEND ATUALIZA AUTOMATICAMENTE                               │
└─────────────────────────────────────────────────────────────────────┘
     ↓
   Frontend POLLING (a cada 10 segundos):
   - GET /api/v1/documentos/status
   - Se email_verificado = TRUE:
     * Remove badge "Email pendente" ❌
     * Mostra "Verificado" ✅ (se docs também verificados)
     * Para polling (economiza requisições)
```

---

## 🔧 CÓDIGO TÉCNICO

### 1️⃣ Gerar Token de Verificação

```python
# app/routes.py - Linha 130

def create_email_verification_token(email: str) -> str:
    """Gera um token JWT específico para verificação de e-mail (válido por 24h)"""
    expire = datetime.utcnow() + timedelta(hours=EMAIL_TOKEN_EXPIRE_HOURS)
    to_encode = {
        "sub": email,           # Email do usuário
        "exp": expire,          # Expira em 24h
        "type": "email_verification"  # Tipo: diferencia de tokens de login
    }
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt
```

### 2️⃣ Enviar Email em Background

```python
# app/routes.py - Linha 243

novo_usuario = models.Usuario(
    email=cliente.email,
    nome=cliente.nome,
    token_verificacao=token_verificacao,
    email_verificado=False,  # Começa como não verificado ❌
)
db.add(novo_usuario)
db.commit()

# Envia email em background (não bloqueia)
background_tasks.add_task(
    send_verification_email, 
    novo_usuario.email, 
    token_verificacao,
    novo_usuario.nome
)
```

### 3️⃣ Verificar Email (Clique no Link)

```python
# app/routes_extras.py - Linha 627

@router.get("/email/verificar", response_class=HTMLResponse)
async def verificar_email(token: str, db: Session = Depends(get_db)):
    """
    Confirmar email a partir do token JWT
    
    Quando usuário clica no link:
    http://localhost:8000/api/v1/email/verificar?token=JWT_TOKEN
    """
    
    # 1. Validar e decodificar token
    email = verify_email_token(token)
    
    if not email:
        return HTMLResponse("Token inválido ou expirou", status_code=400)
    
    # 2. Buscar usuário
    user = db.query(models.Usuario).filter(
        models.Usuario.email == email
    ).first()
    
    if not user:
        return HTMLResponse("Usuário não encontrado", status_code=404)
    
    # 3. Marcar como verificado
    user.email_verificado = True  # ✅ AQUI MUDA PARA TRUE
    user.token_verificacao = None  # Limpar token
    db.commit()
    
    # 4. Retornar página HTML de sucesso
    return HTMLResponse("Email verificado com sucesso!")
```

### 4️⃣ Decodificar Token

```python
# app/routes.py - Linha 138

def verify_email_token(token: str) -> str | None:
    """
    Verifica e decodifica o token de e-mail.
    Retorna o email se válido, None caso contrário.
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        token_type: str = payload.get("type")
        
        # Validações:
        if email is None:
            return None
        if token_type != "email_verification":
            return None
        
        return email
    except JWTError:
        # Token expirou ou é inválido
        return None
```

### 5️⃣ Frontend Atualiza (Polling)

```javascript
// barbermove/src/App.jsx

useEffect(() => {
  const fetchUserStatus = () => {
    fetch(`${API_URL}/api/v1/documentos/status`, {
      headers: {'Authorization': `Bearer ${token}`}
    })
    .then(r => r.json())
    .then(data => setUser(data))
    .catch(() => {});
  };
  
  fetchUserStatus();
  
  // Se email não está verificado, recarregar a cada 10 segundos ⏱️
  const interval = setInterval(() => {
    if (!user?.email_verificado) {
      fetchUserStatus();
    }
  }, 10000);  // 10 segundos
  
  return () => clearInterval(interval);
}, [token, user?.email_verificado]);
```

---

## 🗂️ BANCO DE DADOS

### Tabela `usuarios` - Colunas Importantes

| Coluna | Tipo | Descrição |
|--------|------|-----------|
| `id` | INTEGER | ID do usuário |
| `email` | STRING | Email (único) |
| `email_verificado` | BOOLEAN | ✅ FALSE até clicar no link |
| `token_verificacao` | STRING | JWT de 24h para verificação |
| `criado_em` | DATETIME | Quando registrou |

**Estados do email:**
- 🟥 **Novo registro**: `email_verificado = FALSE`, `token_verificacao = JWT_TOKEN`
- 🟨 **Clicou no link**: `email_verificado = TRUE`, `token_verificacao = NULL`

---

## ⏱️ DURAÇÃO DOS TOKENS

| Tipo | Duração | Uso |
|------|---------|-----|
| **Email Verification** | 24 horas | Verificar email |
| **Access Token** | 30 dias | Login/Autenticação |
| **Refresh Token** | 90 dias | Renovar Access Token |

---

## 🐛 PROBLEMAS COMUNS

### ❌ "Email pendente" mesmo após verificar

**Causa**: Frontend carregou dados uma vez e não atualiza
**Solução**: ✅ Implementei polling a cada 10 segundos (RESOLVIDO)

### ❌ Email não chega

**Causa**: SMTP não configurado ou erro no envio
**Solução**: Verificar `.env` e logs do servidor

### ❌ Link expirado

**Causa**: Clicou depois de 24h
**Solução**: Reenviar link via endpoint `/email/reenviar`

---

## 🔍 COMO TESTAR

### Teste 1: Ver Token Gerado
```bash
GET /api/v1/email/debug-token/allansiqueira06@gmail.com
```
Retorna o token armazenado e informações de expiração.

### Teste 2: Verificar Manualmente
```bash
GET http://localhost:8000/api/v1/email/verificar?token=JWT_TOKEN_AQUI
```

### Teste 3: Simular Clique em Tempo Real
1. Registre novo usuário
2. Copie o token do banco de dados
3. Abra em nova aba: `http://localhost:8000/api/v1/email/verificar?token=TOKEN`
4. Volte ao app em 10 segundos
5. Badge mudará para "Verificado" ✅

---

## 📊 FLUXO VISUAL

```
┌────────────────┐
│   Novo Usuário │ email_verificado = FALSE
│   Registra     │ token_verificacao = "JWT"
└────────┬────────┘
         │
         ├─→ ✉️ Email enviado em background
         │
         └─→ 🔗 Link no email:
             http://localhost:8000/api/v1/email/verificar?token=JWT

             ↓ Usuário clica no link ↓

┌────────────────────────────────┐
│ Backend valida token JWT       │
│ Decodifica email do token      │
│ Busca usuário por email        │
│ Marca: email_verificado = TRUE │
│ Limpa: token_verificacao = NULL│
│ Retorna: Página HTML sucesso   │
└────────────────────────────────┘

             ↓ Usuário volta ao app ↓

┌────────────────────────────────┐
│ Frontend detecta (polling)      │
│ GET /documentos/status          │
│ Recebe: email_verificado = TRUE │
│ Remove badge "Email pendente"   │
│ Mostra: "Verificado" ✅         │
└────────────────────────────────┘
```

---

## ✨ MELHORIAS FUTURAS

- [ ] Usar WebSocket em vez de polling (atualização em tempo real)
- [ ] Notificar usuário quando email for verificado
- [ ] Sistema de reenvio automático se expirar
- [ ] Reduzir intervalo de polling para 5 segundos
- [ ] Rate limiting no endpoint de reenvio
