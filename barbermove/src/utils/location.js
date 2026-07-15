import { Geolocation } from '@capacitor/geolocation';

const DIAGNOSTIC_ENDPOINT = `${import.meta.env.VITE_API_URL?.trim() || ''}/api/v1/notificacoes/frontend-diagnostic`;
let lastDiagnosticKey = '';
let lastDiagnosticAt = 0;
const isNativeApp = typeof window !== 'undefined' && (
  window.location.protocol === 'capacitor:' ||
  window.location.protocol === 'ionic:' ||
  window.Capacitor?.isNativePlatform?.() === true
);

const enviarDiagnostico = async ({ contexto, etapa, mensagem = '', extra = null }) => {
  const key = `${contexto}|${etapa}|${mensagem}`;
  const now = Date.now();
  if (lastDiagnosticKey === key && (now - lastDiagnosticAt) < 2500) {
    return;
  }

  lastDiagnosticKey = key;
  lastDiagnosticAt = now;

  try {
    const apiBase = import.meta.env.VITE_API_URL?.trim() || '';
    if (!apiBase) return;

    await fetch(DIAGNOSTIC_ENDPOINT, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        origem: 'frontend',
        contexto,
        etapa,
        mensagem,
        url: typeof window !== 'undefined' ? window.location.href : null,
        user_agent: typeof navigator !== 'undefined' ? navigator.userAgent : null,
        user_type: typeof window !== 'undefined' ? window.localStorage?.getItem?.('userType') || null : null,
        extra,
      }),
    });
  } catch (_err) {
    // Silencioso: diagnóstico não pode interferir no fluxo principal.
  }
};

const obterLocalizacaoPeloNavegador = () => new Promise((resolve, reject) => {
  if (!navigator?.geolocation) {
    void enviarDiagnostico({ contexto: 'location.browser', etapa: 'geolocation-unavailable', mensagem: 'navigator.geolocation ausente' });
    reject(new Error('Geolocalização indisponível'));
    return;
  }

  navigator.geolocation.getCurrentPosition(
    (position) => {
      void enviarDiagnostico({
        contexto: 'location.browser',
        etapa: 'success',
        mensagem: 'Localização obtida via navegador',
        extra: { accuracy: position.coords.accuracy },
      });
      resolve({
        latitude: position.coords.latitude,
        longitude: position.coords.longitude,
        accuracy: position.coords.accuracy
      });
    },
    (error) => {
      void enviarDiagnostico({
        contexto: 'location.browser',
        etapa: 'error',
        mensagem: error?.message || 'Falha getCurrentPosition',
        extra: { code: error?.code ?? null },
      });
      reject(error);
    },
    {
      enableHighAccuracy: true,
      timeout: 10000,
      maximumAge: 0,
    }
  );
});

export const obterLocalizacaoAtual = async () => {
  if (isNativeApp) {
    void enviarDiagnostico({
      contexto: 'location.strategy',
      etapa: 'native-browser-first',
      mensagem: 'App nativo usando navigator.geolocation antes do plugin Capacitor',
    });

    try {
      return await obterLocalizacaoPeloNavegador();
    } catch (browserErr) {
      void enviarDiagnostico({
        contexto: 'location.strategy',
        etapa: 'native-browser-fallback-capacitor',
        mensagem: browserErr?.message || 'Falha no geolocation do navegador; tentando Capacitor',
      });
    }
  }

  try {
    void enviarDiagnostico({ contexto: 'location.capacitor', etapa: 'request-permission:start', mensagem: 'Solicitando permissão' });
    const permissao = await Geolocation.requestPermissions();
    void enviarDiagnostico({
      contexto: 'location.capacitor',
      etapa: 'request-permission:result',
      mensagem: `Permissão retornou ${permissao?.location || 'desconhecido'}`,
      extra: permissao || null,
    });
    if (permissao?.location === 'denied') {
      throw new Error('Permissão de localização negada');
    }

    void enviarDiagnostico({ contexto: 'location.capacitor', etapa: 'get-current-position:start', mensagem: 'Buscando posição via Capacitor' });
    const position = await Geolocation.getCurrentPosition({
      enableHighAccuracy: true,
      timeout: 10000,
      maximumAge: 0,
    });

    void enviarDiagnostico({
      contexto: 'location.capacitor',
      etapa: 'get-current-position:success',
      mensagem: 'Posição obtida via Capacitor',
      extra: { accuracy: position.coords.accuracy },
    });

    return {
    latitude: position.coords.latitude,
    longitude: position.coords.longitude,
    accuracy: position.coords.accuracy
  };
  } catch (err) {
    void enviarDiagnostico({
      contexto: 'location.capacitor',
      etapa: 'fallback-browser',
      mensagem: err?.message || 'Falha no Capacitor, usando navegador',
    });
    return obterLocalizacaoPeloNavegador();
  }
};

// Tenta obter posição via watchPosition para "acordar" GPS em dispositivos móveis
export const obterPosicaoAltaPrecisa = async () => {
  if (typeof navigator === 'undefined' || !navigator.geolocation) {
    void enviarDiagnostico({ contexto: 'location.watch', etapa: 'navigator-unavailable', mensagem: 'watchPosition indisponível, usando fallback' });
    return obterLocalizacaoAtual();
  }
  // Coleta múltiplas amostras via watchPosition e retorna a mais precisa
  return new Promise((resolve, reject) => {
    let watchId = null;
    const samples = [];
    const options = { enableHighAccuracy: true, timeout: 15000, maximumAge: 0 };

    const pickBest = () => {
      if (samples.length === 0) return null;
      // escolher a amostra com menor accuracy (melhor)
      samples.sort((a, b) => (a.accuracy || 1e9) - (b.accuracy || 1e9));
      const best = samples[0];
      return { latitude: best.latitude, longitude: best.longitude, accuracy: best.accuracy };
    };

    const cleanup = () => {
      if (watchId != null) {
        try { navigator.geolocation.clearWatch(watchId); } catch (_) {}
        watchId = null;
      }
    };

    const success = (position) => {
      const { latitude, longitude, accuracy } = position.coords;
      samples.push({ latitude, longitude, accuracy, ts: Date.now() });
      void enviarDiagnostico({
        contexto: 'location.watch',
        etapa: 'sample',
        mensagem: 'Amostra de watchPosition recebida',
        extra: { accuracy },
      });

      // Se a precisão for boa, retorna imediatamente
      if (typeof accuracy === 'number' && accuracy <= 30) {
        cleanup();
        resolve({ latitude, longitude, accuracy });
      }
    };

    const fail = async (err) => {
      cleanup();
      void enviarDiagnostico({
        contexto: 'location.watch',
        etapa: 'error',
        mensagem: err?.message || 'Falha no watchPosition',
        extra: { code: err?.code ?? null },
      });
      try {
        const fallback = await obterLocalizacaoAtual();
        resolve(fallback);
      } catch (_e) {
        reject(err);
      }
    };

    try {
      watchId = navigator.geolocation.watchPosition(success, fail, options);
    } catch (err) {
      fail(err);
      return;
    }

    // Tempo máximo para aguardar amostras
    const maxWait = 12000;
    const timer = setTimeout(async () => {
      cleanup();
      const best = pickBest();
      if (best) {
        void enviarDiagnostico({ contexto: 'location.watch', etapa: 'timeout-best-sample', mensagem: 'Usando melhor amostra disponível', extra: { accuracy: best.accuracy } });
        resolve(best);
        return;
      }
      try {
        const fallback = await obterLocalizacaoAtual();
        resolve(fallback);
      } catch (e) {
        reject(e);
      }
    }, maxWait);

    // Se resolver/rejeitar antes, limpar timer
    // não é necessário aqui pois resolve/reject encerram o flow
  });
};