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

export const anunciarVagas = (apiBase, token, cadeiraIds, percentualFreelancer) =>
  requisitar(
    apiBase,
    token,
    '/on-demand/cadeiras-acionadas/anunciar',
    enviarJson({ cadeira_ids: cadeiraIds, percentual_freelancer: percentualFreelancer })
  );

// Mesma vaga de diária, enviada só para um freelancer escolhido pelo dono (uma cadeira).
export const enviarVagaDireta = (apiBase, token, freelancerId, cadeiraId, percentualFreelancer) =>
  requisitar(
    apiBase,
    token,
    '/on-demand/cadeiras-acionadas/enviar-direto',
    enviarJson({ freelancer_id: freelancerId, cadeira_id: cadeiraId, percentual_freelancer: percentualFreelancer })
  );

// Freelancer convidado recusa a vaga enviada direto para ele.
export const recusarVagaDireta = (apiBase, token, vagaId) =>
  requisitar(apiBase, token, `/on-demand/cadeiras-acionadas/${vagaId}/recusar`, { method: 'POST' });

// Percentual digitado pelo dono ("50", "50%", "37,5") -> número de 0 a 100; inválido ou vazio: null.
export const lerPercentualFreelancer = (texto) => {
  const limpo = String(texto ?? '').replace('%', '').trim().replace(',', '.');
  if (!/^\d{1,3}(\.\d{1,2})?$/.test(limpo)) return null;
  const valor = Number(limpo);
  return valor >= 0 && valor <= 100 ? valor : null;
};

// 50 -> "50%", 37.5 -> "37,5%". Sem percentual: null.
export const textoPercentual = (percentual) => {
  if (percentual === null || percentual === undefined || !Number.isFinite(Number(percentual))) return null;
  return `${Number(percentual).toLocaleString('pt-BR', { maximumFractionDigits: 2 })}%`;
};

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
