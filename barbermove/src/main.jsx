import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import App from './App.jsx'
import ErrorBoundary from './components/ErrorBoundary.jsx'
import { AppProvider } from './contexts/AppContext.jsx'

// Em app nativo e em desenvolvimento, evita cache antigo de service worker
// que pode manter bundle velho mesmo após instalar um APK novo.
const isDev = import.meta.env.DEV
const isNativeApp = typeof window !== 'undefined' && (
  window.location.protocol === 'capacitor:' ||
  window.location.protocol === 'ionic:' ||
  window.Capacitor?.isNativePlatform?.() === true
)

if ('serviceWorker' in navigator) {
  // Para evitar servir bundles antigos durante desenvolvimento e testes via ngrok,
  // sempre removemos quaisquer service workers e caches existentes ao carregar.
  window.addEventListener('load', async () => {
    try {
      const regs = await navigator.serviceWorker.getRegistrations()
      await Promise.all(regs.map((reg) => reg.unregister()))
    } catch (_err) {
      // ignore
    }

    try {
      if ('caches' in window) {
        const cacheKeys = await caches.keys()
        await Promise.all(cacheKeys.map((key) => caches.delete(key)))
      }
    } catch (_err) {
      // ignore
    }
    // Não registrar service worker automaticamente para testes locais.
  })
}

// Desenvolvimento: suprimir popups bloqueantes (alert/confirm) para edição visual
try {
  window.alert = (msg) => { console.log('[alert]', msg); };
  window.confirm = (msg) => { console.log('[confirm]', msg); return true; };
} catch (e) {}

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <ErrorBoundary>
      <AppProvider>
        <App />
      </AppProvider>
    </ErrorBoundary>
  </StrictMode>,
)
