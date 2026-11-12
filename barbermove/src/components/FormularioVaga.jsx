import React, { useEffect, useState } from 'react';
import { Check } from 'lucide-react';
import { lerPercentualFreelancer } from '../utils/vagas';

const textoVagas = (total) => `${total} ${total === 1 ? 'vaga' : 'vagas'}`;

// Formulário da vaga de diária: escolha da cadeira + percentual do freelancer. Usado pelo
// anúncio geral (várias cadeiras, até `maximo`) e pelo envio direto a um freelancer (uma cadeira).
export default function FormularioVaga({
  cadeirasLivres,
  maximo,
  enviando,
  textoEnviando,
  textoConfirmar,
  onConfirmar,
  onCancelar,
}) {
  const [cadeirasEscolhidas, setCadeirasEscolhidas] = useState(() =>
    // Com uma cadeira só não há o que escolher: já vem marcada.
    cadeirasLivres?.length === 1 ? [cadeirasLivres[0].id] : []
  );
  // Texto livre: o dono digita o percentual que quiser oferecer (sem valor padrão).
  const [percentualTexto, setPercentualTexto] = useState('');

  // O resumo atualiza sozinho: tira da escolha a cadeira que deixou de estar livre.
  useEffect(() => {
    const idsLivres = (cadeirasLivres || []).map((cadeira) => cadeira.id);
    setCadeirasEscolhidas((atual) => {
      const validas = atual.filter((id) => idsLivres.includes(id)).slice(0, maximo);
      return validas.length === atual.length ? atual : validas;
    });
  }, [maximo, cadeirasLivres]);

  const alternarCadeira = (cadeiraId) => {
    setCadeirasEscolhidas((atual) => {
      if (atual.includes(cadeiraId)) return atual.filter((id) => id !== cadeiraId);
      if (maximo === 1) return [cadeiraId];
      return atual.length < maximo ? [...atual, cadeiraId] : atual;
    });
  };

  const percentualFreelancer = lerPercentualFreelancer(percentualTexto);
  const percentualInvalido = percentualTexto.trim() !== '' && percentualFreelancer === null;

  return (
    <div className="rounded-xl border border-zinc-800 bg-black/30 p-3 space-y-3">
      <p className="text-xs font-bold text-white">Escolha a cadeira da vaga</p>
      <div className="grid grid-cols-2 gap-2" data-testid="seletor-cadeiras">
        {(cadeirasLivres || []).map((cadeira) => {
          const marcada = cadeirasEscolhidas.includes(cadeira.id);
          return (
            <button
              key={cadeira.id}
              type="button"
              aria-pressed={marcada}
              onClick={() => alternarCadeira(cadeira.id)}
              disabled={enviando || (!marcada && maximo !== 1 && cadeirasEscolhidas.length >= maximo)}
              className={`min-h-[44px] rounded-xl border px-3 py-2 text-left disabled:opacity-40 ${marcada ? 'border-orange-500 bg-orange-500/15' : 'border-zinc-700 bg-zinc-800'}`}
            >
              <span className="flex items-center justify-between gap-1 text-xs font-black text-white">
                Cadeira {cadeira.numero}
                {marcada && <Check size={14} className="shrink-0 text-orange-300" />}
              </span>
              <span className="block text-[11px] text-zinc-400">{cadeira.bloqueada ? '🔒 Bloqueada' : 'Liberada'}</span>
            </button>
          );
        })}
      </div>
      {maximo > 1 && <p className="text-center text-[11px] text-zinc-400">Você pode anunciar até {textoVagas(maximo)}</p>}
      <div className="space-y-1">
        <label htmlFor="percentual-freelancer" className="block text-xs font-bold text-white">
          Valor da porcentagem ao freelancer
        </label>
        <div className="relative">
          <input
            id="percentual-freelancer"
            data-testid="percentual-freelancer"
            type="text"
            inputMode="decimal"
            autoComplete="off"
            placeholder="Ex.: 50"
            value={percentualTexto}
            onChange={(e) => setPercentualTexto(e.target.value)}
            disabled={enviando}
            aria-invalid={percentualInvalido}
            className={`w-full rounded-xl border bg-zinc-800 px-3 py-2.5 pr-8 text-sm text-white placeholder-zinc-500 outline-none focus:border-orange-500 ${percentualInvalido ? 'border-red-500' : 'border-zinc-700'}`}
          />
          <span className="pointer-events-none absolute right-3 top-1/2 -translate-y-1/2 text-sm font-bold text-zinc-400">%</span>
        </div>
        <p className={`text-[11px] ${percentualInvalido ? 'text-red-400' : 'text-zinc-500'}`}>
          {percentualInvalido
            ? 'Digite um percentual de 0 a 100.'
            : 'Percentual de cada serviço realizado (corte, barba, sobrancelha e demais) que vai para o freelancer.'}
        </p>
      </div>
      <button
        type="button"
        onClick={() => onConfirmar(cadeirasEscolhidas, percentualFreelancer)}
        disabled={enviando || cadeirasEscolhidas.length === 0 || percentualFreelancer === null}
        className="w-full rounded-xl bg-orange-500 px-3 py-2.5 text-sm font-black uppercase tracking-wide text-white hover:bg-orange-600 disabled:opacity-50"
      >
        {enviando ? textoEnviando : textoConfirmar(cadeirasEscolhidas.length)}
      </button>
      <button
        type="button"
        onClick={onCancelar}
        disabled={enviando}
        className="w-full text-xs font-semibold text-zinc-400 hover:text-white"
      >
        Cancelar
      </button>
    </div>
  );
}
