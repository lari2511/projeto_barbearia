import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import App from './App.jsx'
import ErrorBoundary from './components/ErrorBoundary.jsx'

// Em localhost, evita cache antigo de service worker durante debug.
const isLocalhost = typeof window !== 'undefined' && (
  window.location.hostname === 'localhost' ||
  window.location.hostname === '127.0.0.1'
)

if ('serviceWorker' in navigator) {
  window.addEventListener('load', async () => {
    if (isLocalhost) {
      const regs = await navigator.serviceWorker.getRegistrations()
      await Promise.all(regs.map((reg) => reg.unregister()))
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
