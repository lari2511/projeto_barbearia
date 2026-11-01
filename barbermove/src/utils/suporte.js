import { useCallback, useEffect, useState } from 'react';

// Evento disparado pelo socket autenticado do App.jsx quando chega mensagem de suporte.
const EVENTO_SUPORTE = 'barbermove:suporte-mensagem';
const INTERVALO_NAO_LIDAS_MS = 30000;

let chatAberto = false;

export const definirChatSuporteAberto = (aberto) => {
  chatAberto = aberto;
};
export const chatSuporteEstaAberto = () => chatAberto;

export const avisarMensagemSuporte = () => window.dispatchEvent(new Event(EVENTO_SUPORTE));

export const aoReceberMensagemSuporte = (callback) => {
  window.addEventListener(EVENTO_SUPORTE, callback);
  return () => window.removeEventListener(EVENTO_SUPORTE, callback);
};

async function requisitar(apiBase, token, caminho, opcoes = {}) {
  const res = await fetch(`${apiBase}/api/v1/suporte${caminho}`, {
    ...opcoes,
    headers: { Authorization: `Bearer ${token}`, ...(opcoes.headers || {}) },
  });
  if (!res.ok) throw new Error(`Erro ${res.status}`);
  return res.json();
}

export const buscarConversaSuporte = (apiBase, token) => requisitar(apiBase, token, '/minha-conversa');

export const enviarMensagemSuporte = (apiBase, token, mensagem) =>
  requisitar(apiBase, token, '/mensagens', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ mensagem }),
  });

export const marcarSuporteLido = (apiBase, token) => requisitar(apiBase, token, '/marcar-lidas', { method: 'POST' });

export function useSuporteNaoLidas(apiBase, token) {
  const [naoLidas, setNaoLidas] = useState(0);

  const atualizar = useCallback(async () => {
    if (!token) return;
    try {
      const dados = await requisitar(apiBase, token, '/nao-lidas');
      setNaoLidas(dados.nao_lidas || 0);
    } catch (_error) {
      // Mantem o ultimo valor conhecido; tenta de novo no proximo ciclo.
    }
  }, [apiBase, token]);

  useEffect(() => {
    atualizar();
    const intervalo = window.setInterval(atualizar, INTERVALO_NAO_LIDAS_MS);
    const pararDeOuvir = aoReceberMensagemSuporte(atualizar);
    return () => {
      window.clearInterval(intervalo);
      pararDeOuvir();
    };
  }, [atualizar]);

  return [naoLidas, atualizar];
}
