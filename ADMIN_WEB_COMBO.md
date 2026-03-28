# 🔧 ADMIN DASHBOARD WEB + CLI COMBO

## ✨ O que foi implementado

### **1️⃣ Admin CLI (Terminal)**
```bash
python admin_cli.py
```
- Menu interativo em texto
- Listar pendentes/aprovados
- Aprovar/rejeitar perfis
- Válido para usar em qualquer lugar

### **2️⃣ Admin Dashboard Web (Visual)** ✨ NOVO
```bash
python admin_web.py
```
- Interface gráfica bonita
- Acesso em: `http://localhost:8001/admin`
- Estatísticas em tempo real
- Busca por email/nome
- Botões para aprovar/rejeitar

---

## 🚀 COMO USAR

### **Passo 1: Criar Admin no Banco**
Primeira vez, execute:
```bash
python criar_admin.py
```

**Output:**
```
✅ ADMIN CRIADO COM SUCESSO!
📧 Email: admin@barbermovie.local
🔐 Senha: admin123456
🆔 ID: 1
```

### **Passo 2: Escolher o Tipo de Acesso**

#### **OPÇÃO A: Usar CLI (Recomendado para Terminal)**
```bash
python admin_cli.py
```

Menu aparecerá:
```
1. 📋 Listar perfis pendentes
2. ✅ Listar perfis aprovados
3. ✨ Aprovar um perfil
4. ❌ Rejeitar um perfil
5. 🚪 Sair
```

#### **OPÇÃO B: Usar Dashboard Web (Recomendado para Navegador)**
```bash
python admin_web.py
```

Abra no navegador:
```
http://localhost:8001/admin
```

**Faça login com:**
- Email: `admin@barbermovie.local`
- Senha: `admin123456`

---

## 📊 DASHBOARD WEB - FEATURES

### **Seção de Estatísticas**
```
┌─────────────────────────────────┐
│ 📊 Total de Usuários: 15        │
│ ⏳ Pendentes: 3                 │
│ ✅ Aprovados: 12               │
│ 👨‍💼 Barbeiros: 8               │
│ 👤 Clientes: 5                 │
│ 🏪 Barbearias: 2               │
└─────────────────────────────────┘
```

### **Abas**
- **⏳ Pendentes** - Usuários aguardando aprovação
- **✅ Aprovados** - Usuários já aprovados

### **Cada Usuário Mostra**
```
┌─────────────────────────────────────────────┐
│ BARBEIRO                                    │
│ João Silva                                  │
│ 📧 joao@email.com                           │
│ 📞 (11) 99999-8888                          │
│                                             │
│ 📄 Documentos:                              │
│    ✅ Frente, ✅ Verso, ✅ Selfie          │
│                                             │
│ [✅ Aprovar] [❌ Rejeitar]                 │
└─────────────────────────────────────────────┘
```

### **Busca**
- Procure por email ou nome
- Resultados em tempo real
- Mostra status (Aprovado/Pendente)

### **Auto-Refresh**
- Dashboard atualiza a cada 30 segundos
- Sem necessidade de F5

---

## 🔐 SEGURANÇA

✅ **Protegido por JWT** - Só admin consegue acessar
✅ **Verificação de tipo** - `usuario.tipo == 'admin'`
✅ **Endpoints protegidos** - GET `/admin/api/*` requer token
✅ **Token do localStorage** - Login via JWT no app

---

## 📱 COMPARAÇÃO: CLI vs Web

| Feature | CLI | Web |
|---------|-----|-----|
| Interface | Terminal | Visual bonita |
| Pode usar em qualquer lugar | ✅ | ❌ (precisa navegador) |
| Atualização automática | ❌ | ✅ (30s) |
| Busca | ❌ | ✅ |
| Estatísticas | ✅ (básicas) | ✅ (completas) |
| Multi-usuário | ❌ | ✅ (mesma sessão) |
| Documentos visíveis | ✅ (URLs) | ✅ (badges) |

---

## 🔗 ENDPOINTS DA API

Todos protegidos por JWT (admin only):

```
GET  /admin/api/pendentes          → Lista usuários pendentes
GET  /admin/api/aprovados          → Lista usuários aprovados
GET  /admin/api/estatisticas       → Estatísticas gerais
GET  /admin/api/buscar?q=texto     → Busca por email/nome
POST /admin/api/aprovar/{id}       → Aprova um usuário
POST /admin/api/rejeitar/{id}      → Rejeita um usuário
GET  /admin/                       → Página HTML do dashboard
```

---

## ⚠️ TROUBLESHOOTING

### **Erro: "Acesso negado - apenas admins"**
- Certifique-se que fez login como `admin@barbermovie.local`
- Verifique se o token está sendo enviado corretamente

### **Dashboard não carrega em localhost:8001**
- Verifique se a porta 8001 está disponível
- Se não estiver, edite `admin_web.py` e mude para outra porta (ex: 8002)

### **"Usuário não encontrado" ao aprovar**
- O usuário pode ter sido deletado
- Recarregue a página

### **Busca retorna resultado vazio**
- Digite no mínimo 2 caracteres
- Procure por email ou nome

---

## 📝 WORKFLOW RECOMENDADO

```
1. Abra Dashboard Web
   → http://localhost:8001/admin

2. Veja estatísticas
   → Total de usuários, pendentes, etc

3. Clique em "⏳ Pendentes"
   → Veja quem está aguardando

4. Para cada usuário:
   a. Verifique documentos
   b. Se OK: clique "✅ Aprovar"
   c. Se não OK: clique "❌ Rejeitar"

5. O usuário:
   - Se aprovado → acesso liberado no app
   - Se rejeitado → deletado do sistema

6. Atualização automática
   → Dashboard atualiza a cada 30s
```

---

## 🚀 PRÓXIMAS FASES

- [ ] Enviar email ao aprovar/rejeitar
- [ ] Histórico de ações do admin
- [ ] Motivo de rejeição customizado
- [ ] Editar dados do usuário antes de aprovar
- [ ] Exportar relatórios em CSV/PDF
- [ ] Dashboard de métricas (aprovação/dia, taxa de aprovação, etc)

---

**Versão: 3.0 - Admin CLI + Web Combo**
**Data: 17 de Janeiro de 2026**
**Status: ✅ PRONTO PARA TESTES**

---

## 📞 SUPORTE

Se tiver dúvidas:
1. Verifique o console do navegador (F12)
2. Verifique os logs do backend
3. Certifique-se de que o banco PostgreSQL está rodando
4. Use CLI como fallback se web não funcionar
