import { Pause, Play } from 'lucide-react';

// O backend salva/serializa datas em UTC "ingenuo" (sem sufixo Z/offset).
// new Date(string) sem timezone e interpretado pelo JS como horario LOCAL
// do aparelho, nao UTC -- isso inflava o cronometro em +3h (fuso do Brasil).
// Forca a interpretacao como UTC quando a string nao ja traz timezone.
export function parseDataServidorUTC(valor) {
  if (!valor) return NaN;
  const temTimezone = /Z$|[+-]\d{2}:?\d{2}$/.test(valor);
  return new Date(temTimezone ? valor : `${valor}Z`).getTime();
}

export function formatarDuracao(totalSegundos) {
  const seg = Math.max(0, Number(totalSegundos) || 0);
  const horas = Math.floor(seg / 3600);
  const minutos = Math.floor((seg % 3600) / 60);
  const segundos = seg % 60;
  if (horas > 0) {
    return `${String(horas).padStart(2, '0')}:${String(minutos).padStart(2, '0')}:${String(segundos).padStart(2, '0')}`;
  }
  return `${String(minutos).padStart(2, '0')}:${String(segundos).padStart(2, '0')}`;
}

// Cronometro de contagem regressiva de um atendimento. Compartilhado entre o
// painel do freelancer e o dashboard do cliente para que ambos mostrem
// exatamente o mesmo tempo restante, com a mesma logica de fuso e de pausa.
export default function CronometroAtendimento({
  chamado,
  chamadosGrupo = [],
  chamadoAtivoId = null,
  isPausado = false,
  pausadoEmMs = null,
  pausaAcumuladaMs = 0,
  agoraMs,
  compacto = false,
  variante = 'lista',
  onTogglePausa = null,
  alternandoPausa = false,
}) {
  if (!chamado) return null;

  const status = String(chamado.status || '').toLowerCase();
  if (status !== 'em_atendimento') return null;

  // Quando o cliente seleciona varios servicos juntos (grupo_id compartilhado),
  // o cronometro precisa contar ate o fim do ULTIMO servico do grupo, nao so do
  // que esta em_atendimento agora -- senao mostraria "livre" 10min antes do fim
  // do primeiro servico mesmo com outro ja esperando na fila.
  const statusAtivoNaFila = ['pendente', 'confirmado', 'em_atendimento'];
  const membrosGrupo = chamado.grupo_id
    ? chamadosGrupo.filter((c) => c.grupo_id === chamado.grupo_id && statusAtivoNaFila.includes(String(c.status || '').toLowerCase()))
    : [chamado];

  const fim = membrosGrupo.reduce((maior, membro) => {
    const fimMembro = membro.data_hora_fim ? parseDataServidorUTC(membro.data_hora_fim) : NaN;
    return Number.isFinite(fimMembro) && fimMembro > maior ? fimMembro : maior;
  }, NaN);
  if (!Number.isFinite(fim)) return null;

  const nomeCombinado = membrosGrupo.length > 1
    ? membrosGrupo.map((m) => m.servico_nome || m.descricao || m.servico).filter(Boolean).join(' + ')
    : null;

  const isChamadoAtivo = Number(chamadoAtivoId) === Number(chamado.id);
  const pausaAtualMs = isChamadoAtivo && isPausado && pausadoEmMs ? (agoraMs - pausadoEmMs) : 0;
  const acumuladoMs = isChamadoAtivo ? pausaAcumuladaMs : 0;
  const restanteMs = fim - agoraMs + acumuladoMs + pausaAtualMs;
  const restanteSegundos = Math.ceil(Math.max(0, restanteMs) / 1000);
  const dentroJanelaProximo = restanteSegundos <= (10 * 60);
  const pausadoAgora = isChamadoAtivo && isPausado;

  if (variante === 'circular') {
    const totalSegundos = Math.max(1, membrosGrupo.reduce((soma, m) => soma + ((Number(m.duracao_minutos) || 30) * 60), 0));
    const fracaoRestante = Math.min(1, Math.max(0, restanteSegundos / totalSegundos));
    const raio = 36;
    const circunferencia = 2 * Math.PI * raio;

    return (
      <div className="rounded-2xl border border-zinc-800 bg-zinc-900 p-4">
        {nomeCombinado && (
          <p className="text-[10px] text-zinc-500 truncate mb-1">{nomeCombinado}</p>
        )}
        <div className="flex items-center justify-between gap-4">
          <div className="min-w-0">
            <p className="text-[11px] font-bold uppercase tracking-wide text-zinc-400">
              {pausadoAgora ? '⏸ Atendimento pausado' : 'Tempo restante'}
            </p>
            <p className="text-4xl font-black text-white leading-tight mt-1">{formatarDuracao(restanteSegundos)}</p>
            <p className="text-xs text-zinc-500 mt-0.5">de {formatarDuracao(totalSegundos)}</p>
          </div>
          <div className="relative w-20 h-20 shrink-0">
            <svg viewBox="0 0 84 84" className="w-20 h-20 -rotate-90">
              <circle cx="42" cy="42" r={raio} fill="none" stroke="#27272a" strokeWidth="8" />
              <circle
                cx="42" cy="42" r={raio} fill="none"
                stroke={pausadoAgora ? '#f59e0b' : '#f97316'}
                strokeWidth="8"
                strokeLinecap="round"
                strokeDasharray={circunferencia}
                strokeDashoffset={circunferencia * (1 - fracaoRestante)}
              />
            </svg>
            {typeof onTogglePausa === 'function' && (
              <button
                type="button"
                onClick={onTogglePausa}
                disabled={alternandoPausa}
                aria-label={pausadoAgora ? 'Retomar' : 'Pausar'}
                className="absolute inset-0 m-auto w-10 h-10 rounded-full bg-white text-zinc-900 flex items-center justify-center shadow-lg disabled:opacity-60"
              >
                {pausadoAgora ? <Play size={16} /> : <Pause size={16} />}
              </button>
            )}
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className={`rounded-xl border border-zinc-700 bg-zinc-950/70 ${compacto ? 'p-2' : 'p-3'} space-y-2`}>
      <div className="flex items-center justify-between">
        <p className={`font-bold uppercase tracking-wide text-zinc-400 ${compacto ? 'text-[10px]' : 'text-[11px]'}`}>
          {pausadoAgora ? '⏸ Atendimento pausado' : 'Cronometro'}
        </p>
        <span className={`text-[10px] font-bold px-2 py-1 rounded-full ${dentroJanelaProximo ? 'bg-emerald-500/20 text-emerald-300' : 'bg-amber-500/20 text-amber-300'}`}>
          {dentroJanelaProximo ? 'Liberado em 10 min' : 'Aguardando 10 min'}
        </span>
      </div>
      {nomeCombinado && (
        <p className="text-[10px] text-zinc-400 truncate">{nomeCombinado}</p>
      )}
      <p className={`${compacto ? 'text-lg' : 'text-2xl'} font-black text-white`}>{formatarDuracao(restanteSegundos)}</p>
    </div>
  );
}
