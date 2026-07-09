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

// Guardas de runtime para reduzir fechamento inesperado no app nativo.
if (isNativeApp && typeof window !== 'undefined') {
  // Em WebView Android, reload pode derrubar a tela/app em alguns cenarios.
  try {
    window.location.reload = () => {
      console.warn('[native-guard] reload bloqueado para evitar fechamento do app');
    };
  } catch (_err) {
    // ignore
  }

  // Alguns aparelhos/WebViews lidam mal com prompt; evitamos chamada nativa.
  try {
    window.prompt = (msg, defaultValue = '') => {
      console.log('[prompt]', msg);
      return defaultValue;
    };
  } catch (_err) {
    // ignore
  }

  // Evita que excecoes assincronas derrubem a aplicacao sem feedback.
  window.addEventListener('unhandledrejection', (event) => {
    try {
      console.error('[unhandledrejection]', event?.reason);
      event.preventDefault();
    } catch (_err) {
      // ignore
    }
  });

  window.addEventListener('error', (event) => {
    try {
      console.error('[window.error]', event?.error || event?.message);
      if (event?.preventDefault) {
        event.preventDefault();
      }
    } catch (_err) {
      // ignore
    }
  });

  window.onerror = (_message, _source, _lineno, _colno, error) => {
    try {
      console.error('[onerror]', error || _message);
    } catch (_err) {
      // ignore
    }
    return true;
  };

  window.onunhandledrejection = (event) => {
    try {
      console.error('[onunhandledrejection]', event?.reason);
      if (event?.preventDefault) {
        event.preventDefault();
      }
    } catch (_err) {
      // ignore
    }
    return true;
  };
}

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
  if (!window.prompt) {
    window.prompt = (msg, defaultValue = '') => { console.log('[prompt]', msg); return defaultValue; };
  }
} catch (e) {}

createRoot(document.getElementById('root')).render(
  <ErrorBoundary>
    <AppProvider>
      <App />
    </AppProvider>
  </ErrorBoundary>,
)
