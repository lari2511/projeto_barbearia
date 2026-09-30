import React, { useCallback, useEffect, useState } from 'react';

// "ALTERAR SERVIÇO" no atendimento do freelancer (atendimento com mais de um serviço).
// O pedido só vale depois que o CLIENTE confirma; até lá o atendimento segue como agendado.
export default function AlterarServicoFreelancer({ chamadoId, token, API_URL, notify, onAtualizado }) {
  const [info, setInfo] = useState(null);
  const [aberto, setAberto] = useState(false);
  const [selecionados, setSelecionados] = useState([]);
  const [enviando, setEnviando] = useState(false);

  const carregar = useCallback(async () => {
    if (!chamadoId || !token) return;
    try {
      const res = await fetch(`${API_URL}/api/v1/chamados/${chamadoId}/alteracao-servico`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!res.ok) { setInfo(null); return; }
      const data = await res.json();
      setInfo((antes) => {
        // Pedido pendente acabou de ser respondido pelo cliente: recarrega o atendimento.
        if (antes?.pendente && !data?.pendente) onAtualizado?.();
        return data;
      });
    } catch (_) {
      // silencioso: opção extra, não trava o atendimento
    }
  }, [chamadoId, token, API_URL, onAtualizado]);

  useEffect(() => {
    carregar();
    const t = setInterval(carregar, 8000);
    return () => clearInterval(t);
  }, [carregar]);

  if (!info?.pode_alterar) return null;

  const concluidos = info.servicos_concluidos_ids || [];

  const abrir = () => {
    setSelecionados(info.servicos_atuais_ids || []);
    setAberto(true);
  };

  const alternar = (id) => {
    if (concluidos.includes(id)) return;
    setSelecionados((atual) => (atual.includes(id) ? atual.filter((x) => x !== id) : [...atual, id]));
  };

  const enviar = async () => {
    if (selecionados.length === 0) {
      notify?.('Selecione o serviço realizado', 'warning');
      return;
    }
    try {
      setEnviando(true);
      const res = await fetch(`${API_URL}/api/v1/chamados/${chamadoId}/alteracao-servico`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' },
        body: JSON.stringify({ servico_ids: selecionados }),
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) throw new Error(data?.detail || 'Não foi possível enviar a alteração');
      notify?.('Alteração enviada. Aguardando confirmação do cliente.', 'success');
      setAberto(false);
      carregar();
    } catch (err) {
      notify?.(err?.message || 'Erro ao enviar alteração', 'error');
    } finally {
      setEnviando(false);
    }
  };

  return (
    <>
      {info.pendente ? (
        <div className="rounded-xl border border-sky-500/30 bg-sky-500/10 px-3 py-2 text-xs text-sky-200">
          ⏳ Alteração enviada: {info.pendente.servicos_originais} → {info.pendente.servicos_novos}. Aguardando o cliente confirmar.
        </div>
      ) : (
        <button
          type="button"
          onClick={abrir}
          className="w-full rounded-xl border border-zinc-700 bg-zinc-900 hover:border-orange-500 py-2.5 text-xs font-black tracking-wide text-zinc-200"
        >
          ALTERAR SERVIÇO
        </button>
      )}

      {aberto && (
        <div className="fixed inset-0 z-[2400] bg-black/80 flex items-end sm:items-center justify-center p-4" onClick={() => setAberto(false)}>
          <div className="w-full max-w-sm rounded-2xl border border-zinc-800 bg-zinc-950 p-4 space-y-3" onClick={(e) => e.stopPropagation()}>
            <div>
              <p className="text-sm font-black text-white">Alterar serviço</p>
              <p className="text-[11px] text-zinc-400">Agendado: {info.servicos_atuais}. Marque o que será realizado.</p>
            </div>
            <div className="space-y-1.5 max-h-72 overflow-y-auto">
              {(info.opcoes || []).map((s) => {
                const marcado = selecionados.includes(s.id);
                const travado = concluidos.includes(s.id);
                return (
                  <button
                    key={s.id}
                    type="button"
                    onClick={() => alternar(s.id)}
                    disabled={travado}
                    className={`w-full flex items-center justify-between gap-2 rounded-xl border px-3 py-2 text-left text-sm ${marcado ? 'border-orange-500 bg-orange-500/10 text-white' : 'border-zinc-800 bg-zinc-900 text-zinc-300'} ${travado ? 'opacity-70' : ''}`}
                  >
                    <span className="truncate">{marcado ? '☑' : '☐'} {s.nome}{travado ? ' (concluído)' : ''}</span>
                    <span className="shrink-0 text-xs text-zinc-400">R$ {Number(s.valor || 0).toFixed(2)}</span>
                  </button>
                );
              })}
            </div>
            <p className="text-[11px] text-zinc-500">A alteração só vale depois que o cliente confirmar.</p>
            <div className="flex gap-2">
              <button type="button" onClick={() => setAberto(false)} className="flex-1 rounded-xl bg-zinc-800 py-2.5 text-xs font-bold text-white">
                Cancelar
              </button>
              <button
                type="button"
                onClick={enviar}
                disabled={enviando}
                className="flex-1 rounded-xl bg-orange-600 hover:bg-orange-500 disabled:opacity-60 py-2.5 text-xs font-black text-white"
              >
                {enviando ? 'Enviando...' : 'Confirmar alteração'}
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
