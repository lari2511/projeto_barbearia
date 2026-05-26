import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import './theme/painel.css'
import App from './App.jsx'
import ErrorBoundary from './components/ErrorBoundary.jsx'

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

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <ErrorBoundary>
      <div className="min-h-screen bg-black text-white flex justify-center bm-app-frame">
        <div className="w-full max-w-[430px] min-h-screen p-4 bm-shell-content">
          <App />
        </div>
      </div>
    </ErrorBoundary>
  </StrictMode>,
)
