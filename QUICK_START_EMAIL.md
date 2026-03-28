# ⚡ QUICK START: Verificação de Email

## 🎯 O que você tem

Sistema de verificação de email **completo e funcional**:

✅ FastAPI-Mail instalado
✅ SMTP Resend configurado no `.env`
✅ Rotas de cadastro com envio automático
✅ Rota de verificação `/email/verificar?token=...`
✅ Debug mode com `/email/debug-token/{email}`

---

## 🚀 Para Começar (3 passos)

### 1️⃣ Testar SMTP

```bash
python test_smtp.py
```

Isso vai:
- ✅ Validar configuração do `.env`
- ✅ Gerar um token de teste
- ✅ Tentar enviar um email de teste

---

### 2️⃣ Registrar um Cliente

```bash
POST http://localhost:8000/api/v1/clientes/
Content-Type: application/json

{
  "nome": "João Silva",
  "email": "seu.email@gmail.com",
  "cpf": "12345678901",
  "senha": "senha123",
  "telefone": "11999999999"
}
```

**O que acontece:**
- ✅ Usuário criado com `email_verificado = False`
- ✅ Token JWT gerado (válido 24h)
- ✅ Email enviado automaticamente

---

### 3️⃣ Verificar Email

**Opção A: Email Real**
1. Abra sua caixa de entrada
2. Procure por email de "Equipe BarberMove"
3. Clique no botão "Confirmar E-mail"

**Opção B: Debug (Desenvolvimento)**
```bash
GET http://localhost:8000/api/v1/email/debug-token/seu.email@gmail.com
```

Copie o `verification_link` e abra no navegador.

---

## 🔧 Configurar com Gmail (opcional)

Se quiser usar Gmail ao invés de Resend:

1. **Gere Senha de App:**
   - Acesse https://myaccount.google.com/security
   - App passwords → Mail → Device → Copie

2. **Atualize `.env`:**
```env
MAIL_USERNAME=seu.email@gmail.com
MAIL_PASSWORD=xxxx xxxx xxxx xxxx
MAIL_FROM=seu.email@gmail.com
MAIL_SERVER=smtp.gmail.com
MAIL_PORT=587
```

3. **Teste:**
```bash
python test_smtp.py
```

---

## 📧 Estrutura de Email

**O email que seu cliente recebe:**

```
De: onboarding@resend.dev (Equipe BarberMove)
Assunto: BarberMove - Confirme seu cadastro

---

Bem-vindo ao BarberMove!

[Botão: Confirmar E-mail]

O link expira em 24 horas.
```

---

## 🧪 Testes Manuais

### Listar um usuário já registrado

```bash
GET http://localhost:8000/api/v1/usuarios/{user_id}
Authorization: Bearer {seu_token}
```

Você verá:
```json
{
  "id": 1,
  "email": "seu.email@gmail.com",
  "email_verificado": true,  // ← Muda após clicar link
  "nome": "João Silva"
}
```

### Fazer login com email verificado

```bash
POST http://localhost:8000/api/v1/login/cliente/
Content-Type: application/json

{
  "email": "seu.email@gmail.com",
  "senha": "senha123"
}
```

Se `email_verificado = False`, a rota pode rejeitar (dependendo de `REQUIRE_EMAIL_VERIFIED`).

---

## 📋 Checklist Final

- [ ] `.env` configurado com SMTP
- [ ] `python test_smtp.py` passando
- [ ] Email recebido com sucesso
- [ ] Link de verificação funcionando
- [ ] Login funcionando após verificação

---

## 📖 Docs Completo

Para mais detalhes sobre configuração, troubleshooting e advanced:

👉 Veja: **GUIA_SMTP_VERIFICACAO_EMAIL.md**

---

## 🆘 Problema Comum

**"Email não chega"**

1. ✅ Verifique pasta Spam/Lixo
2. ✅ Aguarde 1-2 minutos
3. ✅ Veja logs no terminal (procure por `[DEBUG E-MAIL]`)
4. ✅ Se usar Resend: Você está em trial? Pode estar bloqueado
5. ✅ Se usar Gmail: Você gerou a Senha de App?

---

✅ **Tá tudo pronto! Vamo testar?**
