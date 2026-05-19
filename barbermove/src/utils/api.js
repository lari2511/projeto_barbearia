const getWindowLocation = () => {
  if (typeof window === 'undefined') return null;
  return window.location;
};

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

  if (envUrl) {
    return normalizeUrlHost(envUrl, protocol, hostname);
  }

  // Quando servido de um host público (por exemplo via ngrok), evitar usar
  // a porta 8000 direta (que não estará exposta). Em vez disso, apontamos
  // para um caminho proxy relativo que o Vite dev server já encaminha para
  // o backend local (`/proxy -> http://127.0.0.1:8000`). Isso permite testar
  // o frontend público sem alterar variáveis de ambiente.
  if (!isPrivateHost(hostname)) {
    return `${protocol}://${hostname}/proxy`;
  }

  return `${protocol}://${hostname}:8000`;
};

export const getWsBaseUrl = () => {
  const envUrl = import.meta.env.VITE_WS_URL?.trim();
  const location = getWindowLocation();
  const hostname = location?.hostname || 'localhost';
  const protocol = location?.protocol === 'https:' ? 'wss' : 'ws';

  if (envUrl) {
    return normalizeUrlHost(envUrl, protocol, hostname, '/ws/notificacoes');
  }

  return `${protocol}://${hostname}:8000/ws/notificacoes`;
};