# 🔐 CREDENCIAIS DE TESTE - BARBERMOVIE

## 👨‍💼 ADMIN

```
Email: allansiqueira@example.com
Senha: Senha@123
Tipo: admin
```

**Acesso:**
- Dashboard Admin: http://192.168.15.5:5175
- API Docs: http://192.168.15.5:8000/docs

---

## 👨‍💼 BARBEIRO (Exemplo)

```
Email: barbeiro@example.com
Senha: Senha@123
Tipo: barbeiro
```

**Pode fazer:**
- Aceitar chamados de clientes
- Controlar status (OFFLINE/ONLINE/PRESENTE)
- Receber avaliações

---

## 👥 CLIENTE (Exemplo)

```
Email: cliente@example.com
Senha: Senha@123
Tipo: cliente
```

**Pode fazer:**
- Criar chamados/agendamentos
- Avaliar barbeiro

---

## 🏪 BARBEARIA

```
Email: barbearia@example.com
Senha: Senha@123
Tipo: barbearia
```

**Pode fazer:**
- Gerenciar barbeiros
- Ver avaliações

---

## ⚡ FLUXO DE TESTE

### 1️⃣ Entrar como Cliente
```
1. Acesse http://192.168.15.5:5173
2. Login: cliente@example.com
3. Crie um chamado para um barbeiro
```

### 2️⃣ Entrar como Barbeiro
```
1. Acesse http://192.168.15.5:5173
2. Login: barbeiro@example.com
3. Aceite o chamado do cliente
4. Receba avaliação
```

### 3️⃣ Entrar como Admin
```
1. Acesse http://192.168.15.5:5175
2. Login: allansiqueira@example.com
3. Veja dashboard
4. Teste bloqueio/desbloqueio
```

---

## 🧪 TESTE DO AUTO-FLAGGING

**Objetivo:** Verificar se usuário é marcado como "problema" com 3+ avaliações ruins

### Passo a Passo:

1. **Login como Cliente #1**
   - Email: cliente@example.com

2. **Deixar 3 avaliações com ⭐ ou ⭐⭐**
   - Avaliação 1: 1 estrela
   - Avaliação 2: 2 estrelas
   - Avaliação 3: 1 estrela

3. **Esperar sistema flagar** (automático)

4. **Verificar como Admin**
   - Acesse: http://192.168.15.5:5175
   - Vá em "Usuários Problemáticos"
   - Deve aparecer o usuário
   - Pode bloquear com 1 clique

---

## 📲 COMPARTILHAR COM CELULAR

**Na mesma rede WiFi:**

```
Cliente:  http://192.168.15.5:5173
Admin:    http://192.168.15.5:5175
API:      http://192.168.15.5:8000
```

**Para teste remoto:**
- Compartilhe a URL acima
- Celular deve estar na mesma rede que o PC

---

## ❌ SE NÃO CONECTAR

```powershell
# Verificar IP do PC
ipconfig | findstr "IPv4"

# Deve mostrar 192.168.x.x (sua rede local)

# Verificar conectividade
ping 192.168.15.5

# Verificar porta
netstat -ano | findstr 5173
```

