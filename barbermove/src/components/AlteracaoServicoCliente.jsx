import React, { useCallback, useEffect, useState } from 'react';

// Confirmação do cliente para a alteração de serviço pedida pelo freelancer.
// Só ao CONFIRMAR ALTERAÇÃO o serviço oficial do atendimento muda.
export default function AlteracaoServicoCliente({ token, API_URL, notify, onRespondido }) {
  const [pendente, setPendente] = useState(null);
  const [enviando, setEnviando] = useState(false);

  const carregar = useCallback(async () => {
    if (!token) return;
    try {
      const res = await fetch(`${API_URL}/api/v1/cliente/alteracoes-servico/pendentes`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!res.ok) return;
      const lista = await res.json();
      setPendente(Array.isArray(lista) && lista.length ? lista[0] : null);
    } catch (_) {
      // silencioso
    }
  }, [token, API_URL]);

  useEffect(() => {
    carregar();
    const t = setInterval(carregar, 8000);
    return () => clearInterval(t);
  }, [carregar]);

  if (!pendente) return null;

  const responder = async (confirmar) => {
    try {
      setEnviando(true);
      const res = await fetch(`${API_URL}/api/v1/alteracoes-servico/${pendente.id}/responder`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' },
        body: JSON.stringify({ confirmar }),
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) throw new Error(data?.detail || 'Não foi possível responder');
      notify?.(data?.message || (confirmar ? 'Alteração confirmada' : 'Alteração recusada'), confirmar ? 'success' : 'info');
      setPendente(null);
      onRespondido?.();
      carregar();
    } catch (err) {
      notify?.(err?.message || 'Erro ao responder', 'error');
      carregar();
    } finally {
      setEnviando(false);
    }
  };

  return (
    <div className="fixed inset-0 z-[2400] bg-black/80 flex items-center justify-center p-4">
      <div className="w-full max-w-sm rounded-2xl border border-orange-500/40 bg-zinc-950 p-5 space-y-4 text-center">
        <p className="text-base font-black text-white">Alteração no atendimento</p>
        <p className="text-sm text-zinc-300">{pendente.mensagem}</p>
        <div className="flex flex-col gap-2">
          <button
            type="button"
            onClick={() => responder(true)}
            disabled={enviando}
            className="w-full rounded-xl bg-emerald-600 hover:bg-emerald-500 disabled:opacity-60 py-3 text-sm font-black text-white"
          >
            CONFIRMAR ALTERAÇÃO
          </button>
          <button
            type="button"
            onClick={() => responder(false)}
            disabled={enviando}
            className="w-full rounded-xl border border-red-500/60 py-3 text-sm font-black text-red-400 hover:bg-red-500/10 disabled:opacity-60"
          >
            RECUSAR
          </button>
        </div>
      </div>
    </div>
  );
}
