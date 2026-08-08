import { getApiBaseUrl } from './api';

const API_URL = getApiBaseUrl();

// Reporta erros direto pro backend, sem depender do React/AppContext (funciona
// mesmo antes do app montar ou se o proprio React quebrar).
export const reportCrashDirect = (contexto, errorOrMessage, extra) => {
  try {
    const mensagem = errorOrMessage?.message || String(errorOrMessage || 'Erro desconhecido');
    const stack = errorOrMessage?.stack || null;
    fetch(`${API_URL}/api/v1/notificacoes/frontend-crash`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        origem: 'frontend',
        contexto,
        mensagem: String(mensagem).slice(0, 2000),
        stack,
        url: typeof window !== 'undefined' ? window.location.href : null,
        user_agent: typeof navigator !== 'undefined' ? navigator.userAgent : null,
        extra: extra || null,
      }),
      keepalive: true,
    }).catch(() => {});
  } catch (_err) {
    // ignore
  }
};
