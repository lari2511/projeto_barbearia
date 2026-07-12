# 📧 GUIA COMPLETO: VERIFICAÇÃO DE EMAIL COM SMTP

## ✅ Status Atual

Sistema **já implementado e funcional** no projeto! Estrutura:

- ✅ `app/email.py` - Configuração FastAPI-Mail (SMTP)
- ✅ `app/routes.py` - Funções de token JWT (create_email_verification_token, verify_email_token)
- ✅ `app/routes_extras.py` - Rota `/email/verificar` para confirmar email
- ✅ `app/email_utils.py` - Envio de emails
- ✅ `.env` - Configurado com Resend SMTP

---

## 🔧 Configuração do .env

Seu `.env` está **quase pronto**. Você pode usar três cenários:

### Opção 1: RESEND (Atual - Recomendado para Produção)

```env
# Já configurado no projeto!
MAIL_USERNAME=resend
MAIL_PASSWORD=re_UtnbQ8JA_AUJyBsiyNvWsJxavcUzXMxGu
MAIL_FROM=onboarding@resend.dev
MAIL_FROM_NAME="Equipe BarberMove"
MAIL_PORT=587
MAIL_SERVER=smtp.resend.com
MAIL_STARTTLS=True
MAIL_SSL_TLS=False
USE_CREDENTIALS=True
VALIDATE_CERTS=True
```

⚠️ **Aviso**: `onboarding@resend.dev` é apenas para testes. Para produção:
1. Compre domínio próprio (exemplo: `noreply@barbermovie.com`)
2. Configure DNS records no Resend dashboard
3. Troque `MAIL_FROM` para seu domínio

---

### Opção 2: GMAIL (Para Testes Pessoais)

Se quiser usar sua conta Gmail pessoal:

1. **Gere uma "Senha de App"** no Google:
   - Acesse https://myaccount.google.com/security
   - Ative "2-Step Verification" (se não ativado)
   - Volte em Security → App passwords → Select app (Mail) → Select device (Windows/Linux)
   - Copie a senha gerada (16 caracteres)

2. **Configure seu `.env`**:
```env
MAIL_USERNAME=seu.email@gmail.com
MAIL_PASSWORD=xxxx xxxx xxxx xxxx  # A senha de app gerada (16 chars)
MAIL_FROM=seu.email@gmail.com
MAIL_FROM_NAME="BarberMove"
MAIL_PORT=587
MAIL_SERVER=smtp.gmail.com
MAIL_STARTTLS=True
MAIL_SSL_TLS=False
USE_CREDENTIALS=True
VALIDATE_CERTS=True
```

---

### Opção 3: OUTLOOK / Microsoft 365

```env
MAIL_USERNAME=seu.email@outlook.com
MAIL_PASSWORD=sua_senha_normal_ou_app_password
MAIL_FROM=seu.email@outlook.com
MAIL_FROM_NAME="BarberMove"
MAIL_PORT=587
MAIL_SERVER=smtp-mail.outlook.com
MAIL_STARTTLS=True
MAIL_SSL_TLS=False
USE_CREDENTIALS=True
VALIDATE_CERTS=True
```

---

## 🚀 Fluxo de Verificação de Email

### 1. Cliente Registra uma Conta

```bash
POST /api/v1/clientes/
```

**Request:**
```json
{
  "nome": "João Silva",
  "email": "joao@example.com",
  "cpf": "123.456.789-00",
  "senha": "senha123",
  "telefone": "11999999999"
}
```

**Response (201):**
```json
{
  "message": "Cadastro realizado. Verifique seu e-mail.",
  "email": "joao@example.com"
}
```

**O que acontece nos bastidores:**
1. Usuário criado com `email_verificado = False`
2. Token JWT gerado (válido 24h)
3. Email enviado automaticamente via SMTP com link de verificação
4. Token armazenado em `token_verificacao`

---

### 2. Cliente Recebe Email

Você receberá um email de `onboarding@resend.dev` (ou seu email configurado) com:

**Assunto:** "BarberMove - Confirme seu cadastro"

**Corpo HTML:**
```
Bem-vindo ao BarberMove!

[Botão: Confirmar E-mail]

O link expira em 24 horas.
```

**Link no botão:**
```
https://sua-api.up.railway.app/api/v1/email/verificar?token=eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...
```

---

### 3. Cliente Clica no Link (ou Frontend faz a chamada)

```bash
GET https://sua-api.up.railway.app/api/v1/email/verificar?token=eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...
```

**Response (200):**
```json
{
  "detail": "Email verificado com sucesso! Você já pode fazer login.",
  "status": "success",
  "email": "joao@example.com"
}
```

**O que acontece:**
1. Token é validado (JWT)
2. Email é extraído do token
3. Usuário é marcado como `email_verificado = True`
4. Token de verificação é limpo
5. Agora pode fazer login normalmente

---

## 🧪 Testando

### Teste 1: Ver Token sem Enviar Email (Debug)

```bash
GET https://sua-api.up.railway.app/api/v1/email/debug-token/seu.email@example.com
```

**Response:**
```json
{
  "email": "seu.email@example.com",
  "token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
  "verification_link": "https://sua-api.up.railway.app/api/v1/email/verificar?token=eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
  "message": "Clique no link acima para verificar seu email",
  "debug_note": "Este endpoint é apenas para desenvolvimento!",
  "expires_in_hours": 24
}
```

Copie o `verification_link` e abra no navegador para simular clique do cliente.

---

### Teste 2: Fluxo Completo (Com Email Real)

**1. Registrar cliente:**
```bash
curl -X POST https://sua-api.up.railway.app/api/v1/clientes/ \
  -H "Content-Type: application/json" \
  -d '{
    "nome": "João Silva",
    "email": "seu.email@gmail.com",
    "cpf": "12345678901",
    "senha": "senha123",
    "telefone": "11999999999"
  }'
```

**2. Checar email:**
- Acesse sua caixa de entrada
- Procure por email de "Equipe BarberMove" ou de `onboarding@resend.dev`
- Se não encontrou, verifique spam!

**3. Clicar no link:**
- Clique no botão "Confirmar E-mail" no email
- Ou use a rota debug acima para pegar o token manualmente

**4. Fazer login:**
```bash
POST https://sua-api.up.railway.app/api/v1/login/cliente/
```

```json
{
  "email": "seu.email@gmail.com",
  "senha": "senha123"
}
```

---

## 🔐 Implementação no Frontend

### React Component: Verificação de Email

```jsx
import React, { useEffect, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import axios from 'axios';

export default function VerificacaoEmail() {
  const [searchParams] = useSearchParams();
  const [loading, setLoading] = useState(true);
  const [success, setSuccess] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    const verificarEmail = async () => {
      const token = searchParams.get('token');
      
      if (!token) {
        setError('Token não encontrado na URL');
        setLoading(false);
        return;
      }

      try {
        const response = await axios.get(
          `${process.env.REACT_APP_API_URL}/api/v1/email/verificar`,
          { params: { token } }
        );
        
        setSuccess(true);
      } catch (err) {
        setError(err.response?.data?.detail || 'Erro ao verificar email');
      } finally {
        setLoading(false);
      }
    };

    verificarEmail();
  }, [searchParams]);

  if (loading) {
    return <h2>Verificando seu email...</h2>;
  }

  if (success) {
    return (
      <div style={{ textAlign: 'center' }}>
        <h2>✅ Email Verificado!</h2>
        <p>Sua conta foi ativada com sucesso.</p>
        <a href="/login">Fazer Login</a>
      </div>
    );
  }

  return (
    <div style={{ textAlign: 'center', color: 'red' }}>
      <h2>❌ Erro na Verificação</h2>
      <p>{error}</p>
      <p>O link pode ter expirado. Solicite um novo link.</p>
    </div>
  );
}
```

### Route em AppRouter.jsx

```jsx
import VerificacaoEmail from './components/VerificacaoEmail';

export const routes = [
  // ... outras rotas
  {
    path: '/verificar-email',
    element: <VerificacaoEmail />
  }
];
```

---

## 🛠️ Troubleshooting

### Erro: "SMTPAuthenticationError"

```
AuthenticationError: (535, b'5.7.8 Username and password not accepted')
```

**Solução:** 
- Se usar Gmail: Você gerou a **Senha de App** corretamente?
- Se usar Outlook: Tente a "Senha de App" em vez da senha normal
- Se usar Resend: Verifique se a chave API começa com `re_`

---

### Erro: "SMTPNotSupportedError"

```
SMTPNotSupportedError: SMTP STARTTLS extension not supported
```

**Solução:**
- Mudou `MAIL_SSL_TLS=True` acidentalmente? Coloque `False`
- Verifique se `MAIL_STARTTLS=True` está correto

---

### Email não chega na caixa de entrada

**Verificar:**
1. ✅ Pasta de Spam/Lixo
2. ✅ Às vezes leva 1-2 minutos
3. ✅ Se usar Resend: Você está usando `onboarding@resend.dev`? Funciona mas é de teste
4. ✅ Logs no terminal - há mensagens `[DEBUG E-MAIL]`?

---

### Como Ver os Logs

Abra seu terminal onde o servidor está rodando:

```
--- [DEBUG E-MAIL] Iniciando envio para: joao@example.com ---
--- [DEBUG E-MAIL] Link de verificação: https://sua-api.up.railway.app/api/v1/email/verificar?token=... ---
--- [DEBUG E-MAIL] Sucesso! E-mail enviado para joao@example.com ---
```

Se vir **ERRO CRÍTICO**, o SMTP não conectou. Revise o `.env`.

---

## 📋 Checklist de Implementação

- ✅ `fastapi-mail` instalado
- ✅ `.env` configurado com SMTP
- ✅ Rotas implementadas (`app/routes.py` e `app/routes_extras.py`)
- ✅ Modelos têm campo `email_verificado` e `token_verificacao`
- ✅ Frontend rota `/verificar-email?token=...` implementada
- ✅ Testes manuais funcionando

---

## 🚀 Próximas Funcionalidades

1. **Reenviar Email**: Rota para reenviar token se cliente não recebeu
   ```bash
   POST /api/v1/email/reenviar-verificacao
   Body: { "email": "..." }
   ```

2. **Notificações**: Webhooks para rastrear entrega/abertura
   - Resend oferece isso nativamente

3. **Boas-vindas**: Email de boas-vindas após verificação
   - Já existe `send_welcome_email()` em `email.py`!

---

## 📞 Suporte

- **Resend Docs**: https://resend.com/docs
- **FastAPI-Mail**: https://sabuhish.github.io/fastapi-mail/
- **JWT Tokens**: https://python-jose.readthedocs.io/

✅ **Sistema pronto para usar!**
