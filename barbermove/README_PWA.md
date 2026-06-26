# 📱 BarberMove - Aplicativo Mobile PWA

## ✅ O que foi implementado

### 🎯 PWA (Progressive Web App)
- ✅ **Manifest.json configurado** - App instalável
- ✅ **Service Worker** - Funciona offline
- ✅ **Ícones PWA** (192x192, 512x512, Apple Touch Icon)
- ✅ **Meta tags mobile** - Otimizado para dispositivos móveis
- ✅ **Botão de instalação** - Prompt automático para instalar
- ✅ **Cache de API** - Requisições em cache para funcionamento offline

### 📦 Build de Produção
O build foi gerado com sucesso em `barbermove/dist/`:
- **Bundle otimizado**: 217KB (68KB gzipped)
- **Service Worker**: sw.js + workbox
- **Manifest**: manifest.webmanifest

## 🚀 Como usar

### 1️⃣ **Testar localmente (Development)**
```bash
cd barbermove
npm run dev
```
Acesse: http://localhost:5173

### 2️⃣ **Testar o PWA (Production)**
```bash
cd barbermove
npm run build
npm run preview
```
Acesse: http://localhost:4173

### 3️⃣ **Instalar no celular**

#### Opção A: Via navegador (mais fácil)
1. Acesse o site no Chrome/Safari do celular
2. Clique no botão **"Instalar BarberMove"** que aparecerá na tela
3. Confirme a instalação
4. O app aparecerá na tela inicial como app nativo!

#### Opção B: Menu do navegador
**Android (Chrome):**
1. Abra o site
2. Menu (⋮) → "Instalar aplicativo" ou "Adicionar à tela inicial"

**iOS (Safari):**
1. Abra o site
2. Botão Compartilhar → "Adicionar à Tela de Início"

### 4️⃣ **Deploy em produção**

Para disponibilizar publicamente, faça deploy em:
- **Vercel** (recomendado para React)
- **Netlify**
- **GitHub Pages**

Exemplo com Vercel:
```bash
npm install -g vercel
cd barbermove
vercel --prod
```

## 🎨 Funcionalidades PWA

### ✨ Instalação
- Prompt automático de instalação
- Botão personalizado "Instalar BarberMove"
- Ícone na tela inicial do celular

### 🔌 Offline
- Service Worker com estratégia NetworkFirst
- Cache de assets (JS, CSS, imagens)
- Cache de API por 5 minutos

### 📱 Mobile-First
- Design responsivo
- Viewport otimizado
- Tema escuro por padrão
- Status bar personalizada (iOS)

## 📂 Estrutura de arquivos PWA

```
barbermove/
├── public/
│   ├── pwa-192x192.png       # Ícone pequeno
│   ├── pwa-512x512.png       # Ícone grande
│   ├── apple-touch-icon.png  # Ícone iOS
│   └── pwa-icon.svg          # Ícone vetorial
├── src/
│   ├── components/
│   │   └── InstallPWA.jsx    # Botão de instalação
│   ├── App.jsx               # App principal
│   └── main.jsx              # Registro do SW
├── vite.config.js            # Configuração PWA
└── dist/                     # Build de produção
    ├── sw.js                 # Service Worker
    └── manifest.webmanifest  # Manifest PWA
```

## 🔧 Configurações PWA

### Manifest (vite.config.js)
- **Nome**: BarberMove - Seu Barbeiro a um Toque
- **Nome curto**: BarberMove
- **Tema**: #1f2937 (cinza escuro)
- **Display**: standalone (fullscreen sem barra de navegador)
- **Orientação**: portrait (vertical)

### Service Worker
- **Estratégia**: NetworkFirst (tenta rede, depois cache)
- **Cache de API**: 5 minutos
- **Assets em cache**: JS, CSS, HTML, imagens

## 🎯 Próximos passos

### Para transformar em app nativo (opcional):
1. **Capacitor** (recomendado)
   ```bash
   npm install @capacitor/core @capacitor/cli
   npx cap init
   npx cap add android
   npx cap add ios
   ```

2. **React Native** (mais complexo, requer reescrita)

### Melhorias sugeridas:
- [ ] Push notifications
- [ ] Background sync
- [ ] Geolocalização offline
- [ ] Share API (compartilhar agendamentos)
- [ ] Payment API (pagamentos in-app)

## ❓ FAQ

**P: O app funciona offline?**
R: Sim! O Service Worker cacheia a interface e requisições recentes da API.

**P: Preciso publicar na Google Play/App Store?**
R: Não! PWA instala direto do navegador. Mas você pode publicar nas lojas usando Capacitor se quiser.

**P: Funciona em iPhone?**
R: Sim! iOS suporta PWA desde a versão 11.3.

**P: Como atualizo o app após instalado?**
R: O Service Worker atualiza automaticamente. Usuários verão prompt de "Nova versão disponível".

## 📊 Status do Projeto

✅ Frontend PWA completo
✅ Backend FastAPI com JWT
✅ Banco de dados SQLite
✅ Autenticação de 3 tipos de usuários
✅ Sistema de agendamentos
✅ Build de produção otimizado
⏳ Backend em produção (necessário deploy)

---

**Desenvolvido com:** React 19 + Vite 7 + TailwindCSS + Vite-Plugin-PWA
