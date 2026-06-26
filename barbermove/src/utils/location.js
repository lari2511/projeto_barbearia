import { Geolocation } from '@capacitor/geolocation';

const obterLocalizacaoPeloNavegador = () => new Promise((resolve, reject) => {
  if (!navigator?.geolocation) {
    reject(new Error('Geolocalização indisponível'));
    return;
  }

  navigator.geolocation.getCurrentPosition(
    (position) => {
      resolve({
        latitude: position.coords.latitude,
        longitude: position.coords.longitude,
        accuracy: position.coords.accuracy
      });
    },
    reject,
    {
      enableHighAccuracy: true,
      timeout: 10000,
      maximumAge: 0,
    }
  );
});

export const obterLocalizacaoAtual = async () => {
  try {
    const permissao = await Geolocation.requestPermissions();
    if (permissao?.location === 'denied') {
      throw new Error('Permissão de localização negada');
    }

    const position = await Geolocation.getCurrentPosition({
      enableHighAccuracy: true,
      timeout: 10000,
      maximumAge: 0,
    });

    return {
    latitude: position.coords.latitude,
    longitude: position.coords.longitude,
    accuracy: position.coords.accuracy
  };
  } catch (_err) {
    return obterLocalizacaoPeloNavegador();
  }
};

// Tenta obter posição via watchPosition para "acordar" GPS em dispositivos móveis
export const obterPosicaoAltaPrecisa = async () => {
  if (typeof navigator === 'undefined' || !navigator.geolocation) {
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

      // Se a precisão for boa, retorna imediatamente
      if (typeof accuracy === 'number' && accuracy <= 30) {
        cleanup();
        resolve({ latitude, longitude, accuracy });
      }
    };

    const fail = async (err) => {
      cleanup();
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