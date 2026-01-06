# 🔧 SOLUÇÃO RÁPIDA - Configurar API no App

## ✅ BACKEND JÁ ESTÁ RODANDO!

O backend está acessível em:
- **http://192.168.15.5:8000**
- http://localhost:8000 (apenas no PC)

---

## 📱 OPÇÃO 1: Testar no Navegador do Celular (Mais Rápido)

Enquanto recompila o APK, teste no navegador:

1. **Abra Chrome no celular**
2. **Digite:** `http://192.168.15.5:8000/docs`
3. **Teste a API** diretamente pela documentação interativa

**Criar Conta:**
- Vá em `/api/v1/clientes/` → POST
- Clique em "Try it out"
- Preencha os dados
- Execute

---

## 🔨 OPÇÃO 2: Recompilar APK (15 minutos)

### Passos:

```powershell
# 1. Build do React (com nova URL)
cd C:\projeto_barbearia\barbermove
npm run build

# 2. Sync com Capacitor
npx cap sync android

# 3. Compilar APK
cd android
.\gradlew assembleDebug

# 4. Copiar APK para raiz
Copy-Item "app\build\outputs\apk\debug\app-debug.apk" "..\BarberMove-NEW.apk"
```

### Depois:
1. Baixe o novo APK: `http://192.168.15.5:8888/BarberMove-NEW.apk`
2. Instale (substitui o anterior)

---

## 🌐 OPÇÃO 3: Testar PWA (Sem Instalar)

Acesse no Chrome do celular:
```
http://192.168.15.5:5173
```

(Precisa rodar `npm run dev` no PC)

---

## ⚡ SOLUÇÃO TEMPORÁRIA: Usar IP Fixo

Se quiser usar o app atual:

**⚠️ Limitação:** O APK atual está configurado para `localhost`, que não funciona do celular.

**Alternativas:**
1. Use o navegador: `http://192.168.15.5:8000/docs`
2. Recompile o APK (recomendado)
3. Use PWA (temporário)

---

## 🎯 RECOMENDAÇÃO

**Melhor opção agora:**
1. Teste no navegador do celular (`/docs`)
2. Enquanto isso, recompile o APK

**Para produção:**
- Deploy backend em servidor online (Heroku, Railway, etc)
- Use domínio fixo (ex: `https://barbermove-api.com`)
- Nunca mais precisa recompilar por causa de IP
