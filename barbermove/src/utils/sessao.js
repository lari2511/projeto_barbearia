// Sessão do app: token de acesso curto (60 min) + refresh token com rotação.
//
// - O refresh token (o segredo que mantém a pessoa logada por semanas) fica no
//   armazenamento seguro do aparelho (Keystore no Android / Keychain no iOS) quando o APK
//   tem o plugin @aparajita/capacitor-secure-storage. No navegador, ou num APK antigo sem
//   o plugin, cai para o localStorage.
// - O token de acesso continua em localStorage('token'), onde as telas já leem. Como agora
//   vale só 60 min, um vazamento dele tem efeito curto.
// - Um interceptador de fetch faz o resto sem mexer nas telas:
//     * logins/cadastros: envia `X-Suporta-Refresh: 1` e guarda o refresh_token da resposta;
//     * resposta 401 numa chamada autenticada: renova o token uma vez e repete a chamada;
//     * a cada minuto: renova se faltar menos de 5 min para o token vencer.
import { Capacitor } from '@capacitor/core';
import { getApiBaseUrl } from './api';

const CHAVE_REFRESH = 'bm_rt';
const EVENTO_TOKEN = 'bm:token-atualizado';
const ROTAS_QUE_ABREM_SESSAO = [
  /\/api\/v1\/login\/[a-z]+\/?$/,
  /\/api\/v1\/cadastro-rapido\/?$/,
  /\/api\/v1\/(clientes|barbeiros|barbearias)\/$/,
];
const ROTAS_DE_SESSAO = /\/api\/v1\/auth\//;

let fetchOriginal = null;
let renovacaoEmAndamento = null;
let pluginSeguro; // undefined = ainda não verificado; null = indisponível

// --- armazenamento ---------------------------------------------------------------------

async function obterPluginSeguro() {
  if (pluginSeguro !== undefined) return pluginSeguro;
  pluginSeguro = null;
  try {
    if (Capacitor.isNativePlatform() && Capacitor.isPluginAvailable('SecureStorage')) {
      const modulo = await import('@aparajita/capacitor-secure-storage');
      pluginSeguro = modulo.SecureStorage;
    }
  } catch (_e) {
    pluginSeguro = null;
  }
  return pluginSeguro;
}

function lerLocal(chave) {
  try { return localStorage.getItem(chave); } catch (_e) { return null; }
}

function gravarLocal(chave, valor) {
  try {
    if (valor) localStorage.setItem(chave, valor);
    else localStorage.removeItem(chave);
  } catch (_e) { /* sem storage */ }
}

export async function lerRefreshToken() {
  const seguro = await obterPluginSeguro();
  if (seguro) {
    try {
      const valor = await seguro.getItem(CHAVE_REFRESH);
      if (valor) return valor;
      // APK novo instalado por cima: leva o token do localStorage para o Keystore.
      const antigo = lerLocal(CHAVE_REFRESH);
      if (antigo) {
        await seguro.setItem(CHAVE_REFRESH, antigo);
        gravarLocal(CHAVE_REFRESH, null);
      }
      return antigo;
    } catch (_e) {
      return lerLocal(CHAVE_REFRESH);
    }
  }
  return lerLocal(CHAVE_REFRESH);
}

export async function gravarRefreshToken(valor) {
  const seguro = await obterPluginSeguro();
  if (seguro) {
    try {
      if (valor) await seguro.setItem(CHAVE_REFRESH, valor);
      else await seguro.removeItem(CHAVE_REFRESH);
      gravarLocal(CHAVE_REFRESH, null);
      return;
    } catch (_e) {
      // cai para o localStorage
    }
  }
  gravarLocal(CHAVE_REFRESH, valor);
}

function gravarAccessToken(token) {
  gravarLocal('token', token);
  if (lerLocal('access_token')) gravarLocal('access_token', token);
  try {
    window.dispatchEvent(new CustomEvent(EVENTO_TOKEN, { detail: { token } }));
  } catch (_e) { /* ignore */ }
}

export function aoAtualizarToken(callback) {
  const handler = (ev) => callback(ev?.detail?.token || null);
  window.addEventListener(EVENTO_TOKEN, handler);
  return () => window.removeEventListener(EVENTO_TOKEN, handler);
}

// --- JWT -------------------------------------------------------------------------------

function payloadDoJwt(token) {
  try {
    const parte = String(token).split('.')[1];
    const base64 = parte.replace(/-/g, '+').replace(/_/g, '/');
    return JSON.parse(atob(base64 + '='.repeat((4 - (base64.length % 4)) % 4)));
  } catch (_e) {
    return null;
  }
}

// --- chamadas ao backend ---------------------------------------------------------------

function urlDaApi(caminho) {
  return `${getApiBaseUrl()}${caminho}`;
}

function ehChamadaDaApi(url) {
  const base = getApiBaseUrl();
  return url.startsWith(base) || url.startsWith('/api/') || url.includes('/api/v1/');
}

async function postarJson(caminho, corpo, headers = {}) {
  const f = fetchOriginal || window.fetch.bind(window);
  return f(urlDaApi(caminho), {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ...headers },
    body: corpo === undefined ? undefined : JSON.stringify(corpo),
  });
}

/** Troca o refresh token por um par novo. Devolve o access token novo ou null. */
export function renovarSessao() {
  if (renovacaoEmAndamento) return renovacaoEmAndamento;
  renovacaoEmAndamento = (async () => {
    try {
      const refresh = await lerRefreshToken();
      if (!refresh) return null;
      const resp = await postarJson('/api/v1/auth/refresh', { refresh_token: refresh });
      if (resp.status === 401) {
        await gravarRefreshToken(null); // revogado/expirado: não adianta tentar de novo
        return null;
      }
      if (!resp.ok) return null;
      const dados = await resp.json();
      await gravarRefreshToken(dados.refresh_token);
      gravarAccessToken(dados.access_token);
      return dados.access_token;
    } catch (_e) {
      return null; // sem rede: tenta de novo na próxima
    } finally {
      setTimeout(() => { renovacaoEmAndamento = null; }, 0);
    }
  })();
  return renovacaoEmAndamento;
}

/** Logout: revoga o refresh token no servidor e apaga do aparelho. */
export async function encerrarSessao() {
  // Lido antes de qualquer await: o logout limpa o localStorage logo em seguida.
  const local = lerLocal(CHAVE_REFRESH);
  const refresh = (await lerRefreshToken()) || local;
  await gravarRefreshToken(null);
  if (!refresh) return;
  try {
    await postarJson('/api/v1/auth/logout', { refresh_token: refresh });
  } catch (_e) { /* offline: o token vence sozinho */ }
}

/** Quem já estava logado antes desta versão (token de 7 dias) ganha refresh sem relogar. */
async function migrarSessaoAntiga() {
  const token = lerLocal('token');
  if (!token || (await lerRefreshToken())) return;
  const payload = payloadDoJwt(token);
  if (!payload || payload.iat) return; // token novo sem refresh: login feito por front antigo
  try {
    const resp = await postarJson('/api/v1/auth/sessao', undefined, { Authorization: `Bearer ${token}` });
    if (!resp.ok) return;
    const dados = await resp.json();
    await gravarRefreshToken(dados.refresh_token);
    gravarAccessToken(dados.access_token);
  } catch (_e) { /* tenta no próximo início */ }
}

async function renovarSeEstiverVencendo() {
  const token = lerLocal('token');
  if (!token) return;
  const payload = payloadDoJwt(token);
  if (!payload?.exp || !payload.iat) return;
  const faltaMs = payload.exp * 1000 - Date.now();
  if (faltaMs < 5 * 60 * 1000) await renovarSessao();
}

// --- interceptador ---------------------------------------------------------------------

function cabecalhoAuthorization(headers) {
  if (!headers) return null;
  if (typeof Headers !== 'undefined' && headers instanceof Headers) return headers.get('Authorization');
  return headers.Authorization || headers.authorization || null;
}

function comCabecalho(init, nome, valor) {
  const headers = new Headers(init?.headers || {});
  headers.set(nome, valor);
  return { ...(init || {}), headers };
}

export function instalarSessao() {
  if (typeof window === 'undefined' || fetchOriginal) return;
  fetchOriginal = window.fetch.bind(window);

  window.fetch = async (input, init) => {
    // Request objects passam direto (o corpo não pode ser reenviado).
    const url = typeof input === 'string' ? input : (input instanceof URL ? input.href : null);
    if (!url || !ehChamadaDaApi(url)) return fetchOriginal(input, init);

    let caminho = url;
    try { caminho = new URL(url, window.location.href).pathname; } catch (_e) { /* mantém */ }
    const metodo = String(init?.method || 'GET').toUpperCase();

    // Login/cadastro: pede sessão com refresh e guarda o refresh_token.
    if (metodo === 'POST' && ROTAS_QUE_ABREM_SESSAO.some((re) => re.test(caminho))) {
      const resp = await fetchOriginal(url, comCabecalho(init, 'X-Suporta-Refresh', '1'));
      if (resp.ok) {
        try {
          const dados = await resp.clone().json();
          if (dados?.refresh_token) await gravarRefreshToken(dados.refresh_token);
        } catch (_e) { /* resposta sem JSON */ }
      }
      return resp;
    }

    const resp = await fetchOriginal(url, init);
    const auth = cabecalhoAuthorization(init?.headers);
    if (resp.status !== 401 || !auth || ROTAS_DE_SESSAO.test(caminho)) return resp;

    // 401 numa chamada autenticada: outra aba/tela já renovou? senão, renova agora.
    const enviado = String(auth).replace(/^Bearer\s+/i, '');
    let atual = lerLocal('token');
    if (!atual || atual === enviado) atual = await renovarSessao();
    if (!atual || atual === enviado) return resp;
    return fetchOriginal(url, comCabecalho(init, 'Authorization', `Bearer ${atual}`));
  };

  migrarSessaoAntiga();
  setInterval(renovarSeEstiverVencendo, 60 * 1000);
  document.addEventListener('visibilitychange', () => {
    if (document.visibilityState === 'visible') renovarSeEstiverVencendo();
  });
}
