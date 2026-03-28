# 🚀 COMO ACESSAR O BARBERMOVE

## ✅ Status Atual

```
IP Local: 192.168.15.5
Backend: Rodando em http://192.168.15.5:8000 ✅
Frontend: Rodando em http://192.168.15.5:5174 ✅
```

---

## 📱 ACESSO PELO CELULAR/TABLET

### Via Navegador (Recomendado para teste)
```
http://192.168.15.5:5174
```

### Via Aplicativo Native (APK)
```
Modifique o build com:
API_URL=http://192.168.15.5:8000
Recompile o APK
```

---

## 💻 ACESSO PELO PC (LOCALHOST)

### Frontend
```
http://localhost:5174
```

### Backend (Swagger Docs)
```
http://localhost:8000/docs
```

---

## 🔧 CONFIGURAÇÕES

### Backend .env
```
DATABASE_URL=sqlite:///./barbearia.db
API_URL=http://192.168.15.5:8000
ALLOWED_ORIGINS=http://192.168.15.5:5174,http://localhost:5174,...
```

### Frontend .env
```
VITE_API_URL=http://192.168.15.5:8000
VITE_WS_URL=ws://192.168.15.5:8000/ws/notificacoes
```

---

## 🧪 TESTE DE CONEXÃO

### Terminal
```powershell
curl http://192.168.15.5:8000/api/v1/ping
```

### Resultado esperado
```
HTTP 404 (porque /ping não existe, mas backend respondeu ✅)
```

---

## 🛠️ PORTAS ABERTAS

| Serviço | Porta | Status |
|---------|-------|--------|
| Backend (FastAPI) | 8000 | 🟢 ABERTA |
| Frontend (Vite) | 5173/5174 | 🟢 ABERTA |
| Banco (SQLite) | - | 🟢 LOCAL |

---

## ⚠️ PROBLEMAS COMUNS

### 1. "Connection refused"
- ✅ Certifique-se que está na MESMA rede Wi-Fi
- ✅ Verifique se é 192.168.15.x
- ✅ Reinicie o backend e frontend

### 2. "Network unreachable"
- ✅ Firewall pode estar bloqueando
- ✅ Digite `netstat -ano | findstr :8000` para verificar
- ✅ Adicione exceção no firewall do Windows

### 3. "Erro de API"
- ✅ Verifique se `VITE_API_URL` está correto
- ✅ Abra DevTools (F12) → Network
- ✅ Veja qual URL está sendo usada

---

## 🎯 PRÓXIMOS PASSOS

1. ✅ Abra http://192.168.15.5:5174 no celular
2. ✅ Faça login (ou crie uma conta)
3. ✅ Teste a funcionalidade de avaliações
4. ✅ Acesse http://192.168.15.5:8000/docs no PC

---

## 📊 ENDPOINTS ÚTEIS PARA TESTE

```
# Frontend
http://192.168.15.5:5174

# Backend Docs
http://192.168.15.5:8000/docs

# Admin Endpoints
GET /api/v1/admin/dashboard
GET /api/v1/admin/avaliacoes/negativas
GET /api/v1/admin/usuarios/problematicos
```

---

**Tudo pronto!** 🎉 Acesse pelo IP local no seu dispositivo!
