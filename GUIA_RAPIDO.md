# 🚀 GUIA RÁPIDO - BarberMove em 5 Minutos

## ⚡ INÍCIO ULTRA-RÁPIDO

### 1. Iniciar o App (1 clique)
```powershell
.\iniciar_app.ps1
```
✅ Backend: http://localhost:8000  
✅ Frontend: http://localhost:5173

### 2. Abrir no Browser
```
http://localhost:5173
```

### 3. Criar sua primeira conta
- Escolha tipo: Cliente, Barbeiro ou Barbearia
- Preencha os dados
- Faça login!

---

## 📱 TESTAR NO CELULAR (APK)

```powershell
.\build_producao.ps1
```

APK gerado: `barbermove-debug.apk`

**Instalar no celular:**
1. Copie o APK para o celular (WhatsApp, USB, etc)
2. Abra o arquivo no celular
3. Permita "Fontes desconhecidas" se necessário
4. Instale!

---

## 🎯 FLUXO COMPLETO DE TESTE

### Como Cliente:
1. ✅ Cadastrar-se
2. ✅ Buscar barbearias
3. ✅ Ver serviços
4. ✅ Fazer agendamento
5. ✅ Pagar com PIX
6. ✅ Enviar documentos (verificação)
7. ✅ Avaliar serviço

### Como Barbeiro:
1. ✅ Cadastrar-se
2. ✅ Ver chamados disponíveis
3. ✅ Aceitar chamado
4. ✅ Finalizar serviço
5. ✅ Ver ganhos

### Como Barbearia:
1. ✅ Cadastrar-se
2. ✅ Criar serviços
3. ✅ Gerenciar disponibilidade
4. ✅ Ver relatórios
5. ✅ Criar cupons de desconto

---

## 🐛 PROBLEMAS COMUNS

### Backend não inicia?
```powershell
# Instalar dependências:
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### Frontend não inicia?
```powershell
cd barbermove
npm install
```

### Porta ocupada?
- Backend: Mude porta em `run.py` (linha `port=8000`)
- Frontend: Mude em `barbermove/vite.config.js`

### APK não gera?
1. Certifique-se que Android SDK está instalado
2. Execute: `cd barbermove; npm run android:build:debug`

---

## 📚 ONDE ENCONTRAR MAIS INFO

| Arquivo | O que tem |
|---------|-----------|
| [STATUS_FINAL.md](STATUS_FINAL.md) | ✅ Resumo completo do que foi feito |
| [FINALIZACAO.md](FINALIZACAO.md) | 🚀 Como publicar nas lojas |
| [README.md](README.md) | 📖 Documentação técnica |
| [FUNCIONALIDADES.md](FUNCIONALIDADES.md) | ✨ Todas as 16+ features |
| [DEPLOY.md](DEPLOY.md) | ☁️ Hospedagem na nuvem |

---

## 💰 QUANTO CUSTA PUBLICAR?

| Item | Custo |
|------|-------|
| **Google Play Store** | $25 (uma vez) |
| **Apple App Store** | $99/ano |
| **Hospedagem (Vercel + Railway)** | $10-20/mês |
| **Domínio** | $10-15/ano |

**Total inicial:** ~$50 USD

---

## ⏱️ TEMPO ESTIMADO

| Tarefa | Tempo |
|--------|-------|
| Testar localmente | 5 min |
| Deploy frontend (Vercel) | 15 min |
| Deploy backend (Railway) | 15 min |
| Gerar APK assinado | 30 min |
| Publicar Play Store | 2-3 dias (revisão) |
| Publicar App Store | 3-7 dias (revisão) |

---

## 🎊 TUDO PRONTO!

O app está **100% completo** e pronto para:
- ✅ Usar localmente
- ✅ Testar com usuários
- ✅ Fazer deploy
- ✅ Publicar nas lojas

**Próximo passo:** Execute `.\iniciar_app.ps1` e comece a testar!

**Boa sorte! 🚀**
