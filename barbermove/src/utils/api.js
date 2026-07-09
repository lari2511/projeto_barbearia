const getWindowLocation = () => {
  if (typeof window === 'undefined') return null;
  return window.location;
};

const PROD_API_FALLBACK = 'https://projetobarbearia-production.up.railway.app';
const PROD_WS_FALLBACK = 'wss://projetobarbearia-production.up.railway.app/ws/notificacoes';

const isNativeScheme = (protocol) => protocol === 'capacitor:' || protocol === 'ionic:';

const isLocalhostHost = (hostname) =>
  hostname === 'localhost' || hostname === '127.0.0.1' || hostname === '::1';

const isPrivateHost = (hostname) =>
  isLocalhostHost(hostname) ||
  /^10\./.test(hostname) ||
  /^192\.168\./.test(hostname) ||
  /^172\.(1[6-9]|2\d|3[0-1])\./.test(hostname);

const normalizeUrlHost = (rawUrl, fallbackProtocol, fallbackHostname, fallbackPath) => {
  try {
    const parsedUrl = new URL(rawUrl);
    const location = getWindowLocation();

    if (location && fallbackHostname && isPrivateHost(parsedUrl.hostname) && parsedUrl.hostname !== fallbackHostname) {
      parsedUrl.hostname = fallbackHostname;
      if (fallbackProtocol) {
        parsedUrl.protocol = `${fallbackProtocol}:`;
      }
    }

    if (fallbackPath && !parsedUrl.pathname) {
      parsedUrl.pathname = fallbackPath;
    }

    return parsedUrl.toString().replace(/\/$/, '');
  } catch {
    return rawUrl;
  }
};

export const getApiBaseUrl = () => {
  const envUrl = import.meta.env.VITE_API_URL?.trim();
  const location = getWindowLocation();
  const hostname = location?.hostname || 'localhost';
  const protocol = location?.protocol === 'https:' ? 'https' : 'http';
  const isNativeApp = isNativeScheme(location?.protocol);

  if (envUrl) {
    return normalizeUrlHost(envUrl, protocol, hostname);
  }

  // Decisão de URL base para API:
  // - Em DEV, usamos sempre `/proxy` para atravessar o proxy do Vite até o
  //   backend local em :8000, inclusive quando o front está acessado via ngrok.
  // - Em produção, se o host for privado, apontamos direto para :8000.
  // - Em produção com host público, usamos a própria origem apenas quando
  //   o app já estiver servido pelo backend correto.
  const port = location?.port || '';
  const isViteDevPort = ['5173', '5174', '5175'].includes(port);

  if (import.meta.env.DEV) {
    return `${protocol}://${hostname}/proxy`;
  }

  // No app nativo, evitar fallback para localhost quando env não vier.
  if (isNativeApp) {
    return normalizeUrlHost(PROD_API_FALLBACK, 'https', hostname);
  }

  if (isPrivateHost(hostname)) {
    // If running on a private network host, point to backend port 8000 explicitly
    return `${protocol}://${hostname}:8000`;
  }

  // Public host (ngrok or real domain) — use relative paths so the frontend
  // always talks to the current origin. This avoids hardcoding an absolute
  // hostname which can break when tunnels or proxies change.
  return '';
};

export const getWsBaseUrl = () => {
  const envUrl = import.meta.env.VITE_WS_URL?.trim();
  const location = getWindowLocation();
  const hostname = location?.hostname || 'localhost';
  const protocol = location?.protocol === 'https:' ? 'wss' : 'ws';
  const isNativeApp = isNativeScheme(location?.protocol);

  if (envUrl) {
    return normalizeUrlHost(envUrl, protocol, hostname, '/ws/notificacoes');
  }

  const port = location?.port || '';
  const isViteDevPort = ['5173', '5174', '5175'].includes(port);

  if (import.meta.env.DEV) {
    return `${protocol}://${hostname}/proxy/ws/notificacoes`;
  }

  // No app nativo, evitar fallback para websocket local.
  if (isNativeApp) {
    return normalizeUrlHost(PROD_WS_FALLBACK, 'wss', hostname, '/ws/notificacoes');
  }

  if (isPrivateHost(hostname)) {
    return `${protocol}://${hostname}:8000/ws/notificacoes`;
  }

  // Public host — return a relative websocket path so the browser will open
  // the socket on the same origin (ws/wss) used to load the page.
  return `/ws/notificacoes`;
};