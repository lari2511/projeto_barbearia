import React, { useState } from 'react';

// "ALTERAR SERVIÇO" do cliente durante o atendimento em andamento.
// Remove/adiciona serviços do atendimento atual; aplica na hora (cronômetro e valor
// do freelancer/proprietário passam a refletir a nova seleção).
export default function AlterarServicoCliente({ chamadoId, token, API_URL, notify, onAlterado }) {
  const [info, setInfo] = useState(null);
  const [aberto, setAberto] = useState(false);
  const [carregando, setCarregando] = useState(false);
  const [selecionados, setSelecionados] = useState([]);
  const [enviando, setEnviando] = useState(false);

  const abrir = async () => {
    if (!chamadoId || !token) return;
    try {
      setCarregando(true);
      const res = await fetch(`${API_URL}/api/v1/cliente/chamados/${chamadoId}/alterar-servico`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) throw new Error(data?.detail || 'Não foi possível carregar os serviços');
      setInfo(data);
      setSelecionados([...new Set(data.servicos_atuais_ids || [])]);
      setAberto(true);
    } catch (err) {
      notify?.(err?.message || 'Erro ao carregar os serviços', 'error');
    } finally {
      setCarregando(false);
    }
  };

  const concluidos = info?.servicos_concluidos_ids || [];
  const opcoes = info?.opcoes || [];

  const alternar = (id) => {
    if (concluidos.includes(id)) return;
    setSelecionados((atual) => (atual.includes(id) ? atual.filter((x) => x !== id) : [...atual, id]));
  };

  const escolhidos = opcoes.filter((s) => selecionados.includes(s.id));
  const total = escolhidos.reduce((acc, s) => acc + (Number(s.valor) || 0), 0);
  const duracao = escolhidos.reduce((acc, s) => acc + (Number(s.duracao_minutos) || 0), 0);

  const confirmar = async () => {
    if (selecionados.length === 0) {
      notify?.('Selecione ao menos um serviço', 'warning');
      return;
    }
    try {
      setEnviando(true);
      const res = await fetch(`${API_URL}/api/v1/cliente/chamados/${chamadoId}/alterar-servico`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' },
        body: JSON.stringify({ servico_ids: selecionados }),
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) throw new Error(data?.detail || 'Não foi possível alterar o serviço');
      notify?.('Serviços atualizados', 'success');
      setAberto(false);
      onAlterado?.();
    } catch (err) {
      notify?.(err?.message || 'Erro ao alterar o serviço', 'error');
    } finally {
      setEnviando(false);
    }
  };

  return (
    <>
      <button
        type="button"
        onClick={abrir}
        disabled={carregando}
        className="w-full rounded-xl border border-zinc-700 bg-zinc-900 hover:border-orange-500 disabled:opacity-60 py-2.5 text-xs font-black tracking-wide text-zinc-200"
      >
        {carregando ? 'Carregando...' : 'ALTERAR SERVIÇO'}
      </button>

      {aberto && (
        <div className="fixed inset-0 z-[2400] bg-black/80 flex items-end sm:items-center justify-center p-4" onClick={() => setAberto(false)}>
          <div className="w-full max-w-sm rounded-2xl border border-zinc-800 bg-zinc-950 p-4 space-y-3" onClick={(e) => e.stopPropagation()}>
            <div>
              <p className="text-sm font-black text-white">Alterar serviço</p>
              <p className="text-[11px] text-zinc-400">Marque os serviços que você quer neste atendimento.</p>
            </div>
            <div className="space-y-1.5 max-h-72 overflow-y-auto">
              {opcoes.map((s) => {
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
                    <span className="min-w-0">
                      <span className="block truncate">{marcado ? '☑' : '☐'} {s.nome}{travado ? ' (concluído)' : ''}</span>
                      <span className="block text-[11px] text-zinc-500">{s.duracao_minutos} min</span>
                    </span>
                    <span className="shrink-0 text-xs text-zinc-400">R$ {Number(s.valor || 0).toFixed(2)}</span>
                  </button>
                );
              })}
            </div>
            <div className="flex items-center justify-between rounded-xl border border-zinc-800 bg-zinc-900 px-3 py-2 text-sm">
              <span className="text-zinc-400">Total · {duracao} min</span>
              <span className="font-black text-white">R$ {total.toFixed(2)}</span>
            </div>
            <div className="flex gap-2">
              <button type="button" onClick={() => setAberto(false)} className="flex-1 rounded-xl bg-zinc-800 py-2.5 text-xs font-bold text-white">
                Cancelar
              </button>
              <button
                type="button"
                onClick={confirmar}
                disabled={enviando}
                className="flex-1 rounded-xl bg-orange-600 hover:bg-orange-500 disabled:opacity-60 py-2.5 text-xs font-black text-white"
              >
                {enviando ? 'Salvando...' : 'Confirmar alteração'}
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
