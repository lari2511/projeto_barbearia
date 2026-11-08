// Evento disparado pelo socket autenticado do App.jsx quando chega mensagem no chat da vaga.
const EVENTO_CHAT_VAGA = 'barbermove:vaga-chat-mensagem';

let vagaComChatAberto = null;

export const definirChatVagaAberto = (vagaId) => {
  vagaComChatAberto = vagaId;
};
export const chatDaVagaEstaAberto = (vagaId) => vagaComChatAberto !== null && Number(vagaComChatAberto) === Number(vagaId);

export const avisarMensagemVaga = () => window.dispatchEvent(new Event(EVENTO_CHAT_VAGA));

export const aoReceberMensagemVaga = (callback) => {
  window.addEventListener(EVENTO_CHAT_VAGA, callback);
  return () => window.removeEventListener(EVENTO_CHAT_VAGA, callback);
};

async function requisitar(apiBase, token, caminho, opcoes = {}) {
  const res = await fetch(`${apiBase}/api/v1${caminho}`, {
    ...opcoes,
    headers: { Authorization: `Bearer ${token}`, ...(opcoes.headers || {}) },
  });
  const dados = await res.json().catch(() => ({}));
  if (!res.ok) {
    throw new Error(typeof dados?.detail === 'string' ? dados.detail : `Erro ${res.status}`);
  }
  return dados;
}

const enviarJson = (dados) => ({
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify(dados),
});

export const buscarResumoVagas = (apiBase, token) => requisitar(apiBase, token, '/on-demand/cadeiras-acionadas/resumo');

export const anunciarVagas = (apiBase, token, cadeiraIds) =>
  requisitar(apiBase, token, '/on-demand/cadeiras-acionadas/anunciar', enviarJson({ cadeira_ids: cadeiraIds }));

// "a 3,5 km de você" (abaixo de 10 km com uma casa decimal) / "a 18 km de você". Sem posição: null.
export const textoDistanciaCandidato = (distanciaKm) => {
  if (distanciaKm === null || distanciaKm === undefined || !Number.isFinite(Number(distanciaKm))) return null;
  const km = Number(distanciaKm);
  const valor = km < 10
    ? km.toLocaleString('pt-BR', { minimumFractionDigits: 0, maximumFractionDigits: 1 })
    : Math.round(km).toLocaleString('pt-BR');
  return `a ${valor} km de você`;
};

export const buscarCandidatosVaga =(apiBase, token, vagaId) =>
  requisitar(apiBase, token, `/on-demand/cadeiras-acionadas/${vagaId}/candidatos`);

export const escolherCandidatoVaga = (apiBase, token, vagaId, freelancerId) =>
  requisitar(apiBase, token, `/on-demand/cadeiras-acionadas/${vagaId}/escolher-freelancer`, enviarJson({ barbeiro_id: freelancerId }));

export const cancelarVaga = (apiBase, token, vagaId) =>
  requisitar(apiBase, token, `/on-demand/cadeiras-acionadas/${vagaId}/cancelar`, { method: 'POST' });

export const desbloquearCadeiraDaVaga = (apiBase, token, cadeiraId) =>
  requisitar(apiBase, token, `/cadeiras/${cadeiraId}/desbloquear`, { method: 'PUT' });

export const buscarMinhasSelecoes = (apiBase, token) => requisitar(apiBase, token, '/vagas/minhas-selecoes');

export const buscarConversaVaga = (apiBase, token, vagaId) => requisitar(apiBase, token, `/vagas/${vagaId}/chat`);

export const enviarMensagemVaga = (apiBase, token, vagaId, mensagem) =>
  requisitar(apiBase, token, `/vagas/${vagaId}/chat`, enviarJson({ mensagem }));

export const marcarVagaLida = (apiBase, token, vagaId) =>
  requisitar(apiBase, token, `/vagas/${vagaId}/chat/marcar-lidas`, { method: 'POST' });
