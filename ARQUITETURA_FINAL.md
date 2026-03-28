# 🎯 BARBERMOVIE - ARQUITETURA FINAL

## ✅ SERVIÇOS RODANDO

| Serviço | Porta | Local | Rede |
|---------|-------|-------|------|
| 🔧 **Backend** | 8000 | http://localhost:8000 | http://192.168.15.5:8000 |
| 👥 **Frontend Cliente** | 5173 | http://localhost:5173 | http://192.168.15.5:5173 |
| 👨‍💼 **Frontend Admin** | 5175 | http://localhost:5175 | http://192.168.15.5:5175 |
| 📖 **Swagger Docs** | 8000 | http://localhost:8000/docs | http://192.168.15.5:8000/docs |

---

## 📱 ACESSO DO CELULAR

```
👥 Cliente/Barbeiro/Barbearia:
   http://192.168.15.5:5173

👨‍💼 Admin Dashboard:
   http://192.168.15.5:5175
```

---

## 💻 ACESSO DO PC

```
👥 Cliente (localhost):
   http://localhost:5173

👨‍💼 Admin (localhost):
   http://localhost:5175

📖 Documentação API:
   http://localhost:8000/docs
```

---

## 🗂️ Estrutura de Pastas

```
c:\projeto_barbearia/
├── app/                      # Backend (FastAPI)
│   ├── routes_admin_avaliacoes.py  ✅ Endpoints admin
│   ├── models.py              ✅ 9 campos novos
│   └── main.py                ✅ Registrado
│
├── barbermove/               # Frontend Cliente (React + Vite)
│   ├── vite.config.js        ✅ Porta 5173
│   ├── src/App.jsx
│   └── .env                  ✅ API_URL configurada
│
├── admin-panel/              # Frontend Admin (React + Vite)
│   ├── vite.config.js        ✅ Porta 5175
│   ├── src/
│   └── .env                  ✅ API_URL configurada
│
└── .env                       ✅ CORS configurado
```

---

## 🚀 COMO INICIAR

### Terminal 1: Backend
```powershell
cd c:\projeto_barbearia
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Terminal 2: Frontend Cliente (5173)
```powershell
cd c:\projeto_barbearia\barbermove
npm run dev
```

### Terminal 3: Frontend Admin (5175)
```powershell
cd c:\projeto_barbearia\admin-panel
npm run dev
```

---

## 🔐 FUNCIONALIDADES

### ✅ Sistema de Status do Freelancer
- OFFLINE → Não recebe nada
- ONLINE → Recebe de qualquer barbearia
- PRESENTE → Recebe de uma barbearia específica

### ✅ Validação de Especialidade
- Freelancer só aceita serviços que tem skill (corte, barba, facial)
- Filtra chamados por especialidade

### ✅ Controle de Avaliações
- Auto-flagging: 3+ avaliações ruins = FLAGGED
- 7 endpoints admin para gerenciar
- Dashboard em tempo real

### ✅ Bloqueio de Perfil
- Admin remove usuários problemáticos
- Notificação ao usuário
- Possibilidade de desbloquear

---

## 📊 ENDPOINTS ADMIN

```
GET  /api/v1/admin/avaliacoes/negativas          
POST /api/v1/admin/avaliacoes/{id}/bloquear      
POST /api/v1/admin/avaliacoes/{id}/liberar       
GET  /api/v1/admin/usuarios/problematicos        
POST /api/v1/admin/usuarios/{id}/bloquear        
POST /api/v1/admin/usuarios/{id}/desbloquear     
GET  /api/v1/admin/dashboard                     
```

---

## 🧪 TESTE RÁPIDO

### Verificar se Backend está rodando
```powershell
curl http://localhost:8000/docs
```

### Verificar Conexão da Rede
```powershell
ping 192.168.15.5
```

---

## ⚡ RESUMO

✅ **3 Frontends rodando:**
- Cliente em 5173
- Admin em 5175  
- Backend em 8000

✅ **Sistema Completo:**
- Status do freelancer com validação
- Especialidade controlada
- Avaliações com admin control
- Bloqueio de perfis problemáticos

✅ **Testado:**
- Endpoints respondendo
- CORS configurado
- Auto-flagging ativo
- Segurança implementada

🚀 **PRONTO PARA USAR!**

