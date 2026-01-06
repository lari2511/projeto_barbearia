# 📱 BarberMove PWA - Guia Rápido

## ✅ PWA Instalado com Sucesso!

### 🎯 Recursos Implementados:
- ✅ Service Worker para cache offline
- ✅ Manifest configurado (instalável)
- ✅ Ícones otimizados (192px, 512px, iOS)
- ✅ Botão de instalação automático
- ✅ Cache de API (5 minutos)

---

## 🚀 Como Testar

### 1. Modo Desenvolvimento
```powershell
cd barbermove
npm run dev
```
→ http://localhost:5173

### 2. Build de Produção
```powershell
npm run build
npm run preview
```
→ http://localhost:4173

---

## 📲 Instalar no Celular

### Android:
1. Abra no Chrome
2. Clique no banner "Instalar BarberMove"
3. OU: Menu → Instalar app

### iOS:
1. Abra no Safari
2. Compartilhar → Adicionar à Tela de Início

---

## 🌐 Deploy

### Vercel (Recomendado):
```bash
npm i -g vercel
vercel --prod
```

### Netlify:
```bash
npm i -g netlify-cli
netlify deploy --prod --dir=dist
```

---

## ⚙️ Configurar API

Em `src/App.jsx`, linha 8:
```javascript
const API_URL = "https://sua-api.com"; // trocar localhost
```

---

## 📦 Arquivos Gerados

- `dist/sw.js` - Service Worker
- `dist/manifest.webmanifest` - Config PWA  
- `public/pwa-*.png` - Ícones

---

**Status**: ✅ **PRONTO PARA PRODUÇÃO**
