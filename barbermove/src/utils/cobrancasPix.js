// Chamadas ao backend de cobranças Pix. Nenhuma credencial do Mercado Pago fica no app:
// o backend cria o Pix e confirma o pagamento direto com o Mercado Pago.

async function chamar(API_URL, token, caminho, opcoes = {}) {
  const res = await fetch(`${API_URL}/api/v1/cobrancas${caminho}`, {
    ...opcoes,
    headers: {
      Authorization: `Bearer ${token}`,
      ...(opcoes.body ? { 'Content-Type': 'application/json' } : {}),
    },
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    const erro = new Error(data?.detail || 'Não foi possível concluir a operação');
    erro.status = res.status;
    throw erro;
  }
  return data;
}

export const obterConfigPagamentos = (API_URL, token) => chamar(API_URL, token, '/config');
export const criarPixAssinaturaCadeiras = (API_URL, token, cadeirasAtivas) =>
  chamar(API_URL, token, '/pix/assinatura-cadeiras', {
    method: 'POST',
    body: JSON.stringify({ cadeiras_ativas: cadeirasAtivas }),
  });
export const criarPixMensalidade = (API_URL, token) => chamar(API_URL, token, '/pix/mensalidade', { method: 'POST' });
export const criarPixTaxaFreelancer = (API_URL, token) => chamar(API_URL, token, '/pix/taxa-freelancer', { method: 'POST' });
export const consultarCobranca = (API_URL, token, identificador) =>
  chamar(API_URL, token, `/${encodeURIComponent(identificador)}`);
