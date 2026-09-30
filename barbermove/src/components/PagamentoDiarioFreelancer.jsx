import React, { useCallback, useEffect, useState } from 'react';

// Pagamento diário do freelancer: fechamento 21:00, prazo 22:00 (horário de São Paulo).
// Depois das 22:00 sem confirmação do ADM o status fica travado em OFFLINE (regra no backend).

const TZ_SP = 'America/Sao_Paulo';

const formatarDataSP = (iso) => {
  if (!iso) return '';
  // data_referencia vem como "AAAA-MM-DD" (dia do calendário de SP)
  const [a, m, d] = String(iso).slice(0, 10).split('-');
  return `${d}/${m}/${a}`;
};

const formatarHoraSP = (iso) => {
  try {
    return new Date(iso).toLocaleTimeString('pt-BR', { timeZone: TZ_SP, hour: '2-digit', minute: '2-digit' });
  } catch (_) {
    return '';
  }
};

const brl = (v) => `R$ ${Number(v || 0).toFixed(2).replace('.', ',')}`;

export default function PagamentoDiarioFreelancer({ token, API_URL, notify, onResumo }) {
  const [resumo, setResumo] = useState(null);
  const [pix, setPix] = useState(null);
  const [processando, setProcessando] = useState(false);

  const carregar = useCallback(async () => {
    if (!token) return;
    try {
      const res = await fetch(`${API_URL}/api/v1/freelancer/carteira/resumo`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!res.ok) return;
      const data = await res.json().catch(() => null);
      const pd = data?.pagamento_diario || null;
      setResumo(pd);
      onResumo?.(pd);
    } catch (_) {
      // silencioso: o bloqueio é garantido pelo backend
    }
  }, [token, API_URL, onResumo]);

  useEffect(() => {
    carregar();
    const t = setInterval(carregar, 30000);
    return () => clearInterval(t);
  }, [carregar]);

  const gerarPix = async () => {
    try {
      setProcessando(true);
      const res = await fetch(`${API_URL}/api/v1/freelancer/carteira/quitacao/pix-gerar`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}` },
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) throw new Error(data?.detail || 'Erro ao gerar PIX');
      setPix(data);
    } catch (err) {
      notify?.(err?.message || 'Falha ao gerar PIX', 'error');
    } finally {
      setProcessando(false);
    }
  };

  const informarPagamento = async () => {
    try {
      setProcessando(true);
      const res = await fetch(`${API_URL}/api/v1/freelancer/carteira/quitacao/confirmar`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' },
        body: JSON.stringify({ valor: Number(pix?.valor_devedor || resumo?.valor_em_aberto || 0) }),
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) throw new Error(data?.detail || 'Erro ao informar pagamento');
      notify?.(data?.message || 'Pagamento enviado para confirmação do ADM', 'success');
      setPix(null);
      carregar();
    } catch (err) {
      notify?.(err?.message || 'Falha ao informar pagamento', 'error');
    } finally {
      setProcessando(false);
    }
  };

  const copiar = async () => {
    try {
      await navigator.clipboard.writeText(pix?.pix_copia_cola || '');
      notify?.('Código PIX copiado', 'success');
    } catch (_) {
      notify?.('Não foi possível copiar', 'error');
    }
  };

  const abertos = resumo?.fechamentos_abertos || [];
  if (!resumo || abertos.length === 0) return null;

  const bloqueado = Boolean(resumo.bloqueado);
  const aguardando = Boolean(resumo.aguardando_confirmacao);
  const recusado = abertos.some((f) => f.status === 'recusado');
  const dias = abertos.map((f) => formatarDataSP(f.data_referencia)).join(', ');
  const prazo = abertos[abertos.length - 1]?.prazo_pagamento;

  const cor = bloqueado
    ? 'border-red-500/40 bg-red-500/10'
    : 'border-amber-500/40 bg-amber-500/10';

  return (
    <div className={`rounded-xl border p-3 text-sm space-y-2 ${cor}`}>
      {bloqueado ? (
        <>
          <p className="font-bold text-red-300">🔒 Status bloqueado (OFFLINE)</p>
          <p className="text-xs text-red-100">{resumo.mensagem_bloqueio}</p>
          <p className="text-xs text-zinc-400">
            Você não pode ficar online, presente ou assumir novas atividades até o ADM confirmar o pagamento.
            Atendimentos já em andamento continuam normalmente.
          </p>
        </>
      ) : (
        <>
          <p className="font-bold text-amber-300">💰 Fechamento do dia ({dias})</p>
          <p className="text-xs text-amber-100">
            Valor devido: <span className="font-bold">{brl(resumo.valor_em_aberto)}</span>.
            Pague via Pix até as <span className="font-bold">{prazo ? formatarHoraSP(prazo) : resumo.hora_limite_pagamento}</span> (horário de Brasília).
          </p>
          <p className="text-[11px] text-zinc-400">
            Sem confirmação até as {resumo.hora_limite_pagamento}, seu status fica travado em OFFLINE.
          </p>
        </>
      )}

      {aguardando && !resumo.pode_pagar && (
        <p className="text-xs text-sky-300">⏳ Pagamento enviado — aguardando confirmação do ADM.</p>
      )}
      {recusado && (
        <p className="text-xs text-red-300">❌ O ADM não confirmou o pagamento. Verifique e envie novamente.</p>
      )}

      {resumo.pode_pagar && (
        <div className="space-y-2">
          <p className="text-xs text-zinc-300">Total a pagar: <span className="font-bold">{brl(resumo.valor_em_aberto)}</span></p>
          {!pix ? (
            <button
              type="button"
              onClick={gerarPix}
              disabled={processando}
              className="w-full rounded-lg bg-emerald-600 hover:bg-emerald-500 disabled:opacity-60 px-3 py-2 text-xs font-bold text-white"
            >
              {processando ? 'Gerando...' : 'Pagar via Pix'}
            </button>
          ) : (
            <div className="rounded-lg border border-zinc-700 bg-black/30 p-2 space-y-2">
              {pix.qrcode_base64 && (
                <div className="flex justify-center bg-white rounded-lg p-2">
                  <img src={`data:image/png;base64,${pix.qrcode_base64}`} alt="QR PIX" className="w-40 h-40" />
                </div>
              )}
              <input
                readOnly
                value={pix.pix_copia_cola || ''}
                className="w-full rounded bg-zinc-900 border border-zinc-700 px-2 py-1 text-[11px] text-zinc-300"
              />
              <div className="flex gap-2">
                <button type="button" onClick={copiar} className="flex-1 rounded-lg bg-zinc-800 px-3 py-2 text-xs font-bold text-white">
                  Copiar código
                </button>
                <button
                  type="button"
                  onClick={informarPagamento}
                  disabled={processando}
                  className="flex-1 rounded-lg bg-emerald-600 hover:bg-emerald-500 disabled:opacity-60 px-3 py-2 text-xs font-bold text-white"
                >
                  {processando ? 'Enviando...' : 'Já paguei'}
                </button>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
