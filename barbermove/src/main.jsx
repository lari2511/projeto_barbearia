import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
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
  window.addEventListener('load', async () => {
    if (isDev || isNativeApp) {
      const regs = await navigator.serviceWorker.getRegistrations()
      await Promise.all(regs.map((reg) => reg.unregister()))

      if ('caches' in window) {
        const cacheKeys = await caches.keys()
        await Promise.all(cacheKeys.map((key) => caches.delete(key)))
      }

      return
    }

    navigator.serviceWorker.register('/sw.js').catch(() => {
      // Falha no registro nao deve quebrar a inicializacao do app.
    })
  })
}

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <ErrorBoundary>
      <App />
    </ErrorBoundary>
  </StrictMode>,
)
