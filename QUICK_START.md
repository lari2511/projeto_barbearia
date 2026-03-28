# ⚡ QUICK START - 5 MINUTOS

## 🚀 INICIAR TUDO

### Terminal 1 - Backend
```bash
cd c:\projeto_barbearia
python run.py
```
Esperado:
```
--- Banco de dados inicializado com sucesso ---
INFO:     Application startup complete
```

### Terminal 2 - Frontend
```bash
cd c:\projeto_barbearia\barbermove
npm run dev
```
Esperado:
```
VITE v7.2.6  ready in 679 ms
➜  Local:   http://localhost:5173/
```

---

## 🌐 ACESSAR

```
Frontend:   http://localhost:5173
Backend:    http://localhost:8000
Swagger:    http://localhost:8000/docs
Dados API:  http://localhost:8000/api/v1
```

---

## ✅ VALIDAÇÃO RÁPIDA

### 1. Backend está OK?
```bash
curl http://localhost:8000/docs
# Deve abrir página Swagger
```

### 2. Frontend está OK?
```
Abra http://localhost:5173
# Deve mostrar login page
```

### 3. Filtro de disponibilidade funciona?
- Login como cliente
- Vá para "Barbeiros"
- Veja botão "🟢 Mostrar apenas disponíveis"

### 4. Email teste?
- Cadastre novo barbeiro
- Verifique email recebido "⏳ Perfil em Análise"

---

## 📚 PRÓXIMO PASSO

Leia um destes:

1. **[00_COMECE_AQUI.md](00_COMECE_AQUI.md)** - Visão geral (5 min)
2. **[CHECKLIST_VALIDACAO.md](CHECKLIST_VALIDACAO.md)** - Testar tudo (15 min)
3. **[VERIFICACAO_VISUAL.md](VERIFICACAO_VISUAL.md)** - Status de tudo (5 min)

---

## 🎯 7 FEATURES ENTREGUES

1. ✅ Email - Perfil em Avaliação
2. ✅ Email - Perfil Aprovado
3. ✅ Dashboard Admin (visualizar docs)
4. ✅ Filtro de Disponibilidade
5. ✅ Notificações Push
6. ✅ Preços Customizados
7. ✅ Analytics de Avaliações

---

**Tudo pronto! 🎉**
