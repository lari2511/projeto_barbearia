import React, { useCallback, useEffect, useState } from 'react';
import { ChevronDown, ChevronUp, MessageCircle, Minus, Plus } from 'lucide-react';
import ChatVaga from './ChatVaga';
import {
  anunciarVagas,
  aoReceberMensagemVaga,
  buscarCandidatosVaga,
  buscarResumoVagas,
  cancelarVaga,
  desbloquearCadeiraDaVaga,
  escolherCandidatoVaga,
  limitarQuantidadeVagas,
} from '../utils/vagas';

const INTERVALO_ATUALIZACAO_MS = 10000;

const textoVagas = (total) => `${total} ${total === 1 ? 'vaga' : 'vagas'}`;

const descreverVaga = (vaga) => {
  switch (vaga.status) {
    case 'disponivel':
      return `Aberta · ${vaga.total_candidatos} ${vaga.total_candidatos === 1 ? 'candidato' : 'candidatos'}`;
    case 'aguardando_desbloqueio':
      return `${vaga.barbeiro_nome || 'Freelancer'} escolhido · aguardando chegada`;
    case 'ocupada_por_barbeiro':
      return `${vaga.barbeiro_nome || 'Freelancer'} na cadeira`;
    case 'reservada_por_cliente':
      return 'Reservada por um cliente';
    default:
      return vaga.status;
  }
};

// Anúncio de vagas na tela inicial do dono. O limite vem sempre do backend, que recalcula
// as cadeiras pagas e as vagas ativas e recusa o que passar disso.
export default function AnunciarVagas({ API_URL, token, notify, onVerPerfil, onAbrirAssinatura }) {
  const [resumo, setResumo] = useState(null);
  const [seletorAberto, setSeletorAberto] = useState(false);
  const [quantidade, setQuantidade] = useState(1);
  const [publicando, setPublicando] = useState(false);
  const [listaAberta, setListaAberta] = useState(false);
  const [vagaExpandidaId, setVagaExpandidaId] = useState(null);
  const [candidatos, setCandidatos] = useState([]);
  const [acaoEmAndamento, setAcaoEmAndamento] = useState(null);
  const [cancelamentoPendenteId, setCancelamentoPendenteId] = useState(null);
  const [chatVaga, setChatVaga] = useState(null);

  const carregar = useCallback(async () => {
    try {
      setResumo(await buscarResumoVagas(API_URL, token));
    } catch (_error) {
      // Mantem o ultimo resumo carregado; tenta de novo no proximo ciclo.
    }
  }, [API_URL, token]);

  useEffect(() => {
    if (!token) return undefined;
    carregar();
    const intervalo = window.setInterval(carregar, INTERVALO_ATUALIZACAO_MS);
    const pararDeOuvir = aoReceberMensagemVaga(carregar);
    return () => {
      window.clearInterval(intervalo);
      pararDeOuvir();
    };
  }, [carregar, token]);

  const maximo = resumo?.vagas_disponiveis_para_anunciar ?? 0;
  const cadeirasPagas = resumo?.cadeiras_pagas ?? 0;
  const cadeirasVencidas = resumo?.cadeiras_vencidas ?? 0;
  const vagasAnunciadas = resumo?.vagas_anunciadas ?? 0;
  const vagas = resumo?.vagas || [];

  useEffect(() => {
    if (maximo <= 0) {
      setSeletorAberto(false);
      setQuantidade(1);
    } else {
      setQuantidade((atual) => limitarQuantidadeVagas(atual, maximo));
    }
  }, [maximo]);

  const carregarCandidatos = useCallback(async (vagaId) => {
    try {
      const lista = await buscarCandidatosVaga(API_URL, token, vagaId);
      setCandidatos(Array.isArray(lista) ? lista : []);
    } catch (_error) {
      setCandidatos([]);
    }
  }, [API_URL, token]);

  // Mantem os candidatos da vaga aberta em dia a cada atualizacao do resumo.
  useEffect(() => {
    if (vagaExpandidaId) carregarCandidatos(vagaExpandidaId);
  }, [vagaExpandidaId, resumo, carregarCandidatos]);

  const executar = async (chave, acao, mensagemSucesso) => {
    setAcaoEmAndamento(chave);
    try {
      const dados = await acao();
      notify(dados?.message || mensagemSucesso, 'success');
      await carregar();
      return true;
    } catch (error) {
      notify(error?.message || 'Não foi possível concluir a ação', 'error');
      await carregar();
      return false;
    } finally {
      setAcaoEmAndamento(null);
    }
  };

  const confirmarAnuncio = async () => {
    setPublicando(true);
    try {
      const dados = await anunciarVagas(API_URL, token, quantidade);
      setResumo(dados);
      setSeletorAberto(false);
      setQuantidade(1);
      notify(`${textoVagas(dados.publicadas.length)} ${dados.publicadas.length === 1 ? 'anunciada' : 'anunciadas'}!`, 'success');
    } catch (error) {
      notify(error?.message || 'Não foi possível anunciar as vagas', 'error');
      await carregar();
    } finally {
      setPublicando(false);
    }
  };

  const escolher = async (vagaId, candidato) => {
    const sucesso = await executar(
      `escolher-${candidato.freelancer_id}`,
      () => escolherCandidatoVaga(API_URL, token, vagaId, candidato.freelancer_id),
      'Freelancer escolhido! O chat privado da vaga foi liberado.'
    );
    if (sucesso) setVagaExpandidaId(null);
  };

  const cancelar = async (vaga) => {
    if (cancelamentoPendenteId !== vaga.id) {
      setCancelamentoPendenteId(vaga.id);
      return;
    }
    setCancelamentoPendenteId(null);
    await executar(`cancelar-${vaga.id}`, () => cancelarVaga(API_URL, token, vaga.id), 'Vaga cancelada.');
  };

  if (!resumo) return null;

  return (
    <div className="bm-card bg-zinc-900 rounded-2xl p-3 border border-zinc-800/60 space-y-3" data-testid="anunciar-vagas">
      <div className="flex items-start justify-between gap-2">
        <h3 className="text-sm font-black text-white leading-tight uppercase tracking-wide">
          Anuncie vagas <span className="text-orange-500">na sua barbearia</span>
        </h3>
        {vagasAnunciadas > 0 && (
          <span data-testid="vagas-anunciadas" className="shrink-0 rounded-full border border-orange-500/40 bg-orange-500/10 px-2 py-0.5 text-[10px] font-black uppercase text-orange-300">
            {vagasAnunciadas} {vagasAnunciadas === 1 ? 'vaga anunciada' : 'vagas anunciadas'}
          </span>
        )}
      </div>

      {cadeirasVencidas > 0 && cadeirasPagas > 0 && (
        <button
          type="button"
          onClick={onAbrirAssinatura}
          data-testid="cadeiras-vencidas"
          className="w-full rounded-xl border border-amber-500/40 bg-amber-500/10 px-3 py-2 text-left text-[11px] text-amber-200"
        >
          {cadeirasVencidas === 1
            ? '1 cadeira com mensalidade vencida não conta para anunciar vagas.'
            : `${cadeirasVencidas} cadeiras com mensalidade vencida não contam para anunciar vagas.`}{' '}
          <span className="font-black underline">Ver assinatura</span>
        </button>
      )}

      {cadeirasPagas === 0 ? (
        <>
          <p className="text-xs text-zinc-400">Você precisa de ao menos uma cadeira com pagamento em dia para anunciar vagas.</p>
          <button
            type="button"
            onClick={onAbrirAssinatura}
            className="w-full rounded-xl border border-orange-500/50 px-3 py-2.5 text-xs font-black uppercase tracking-wide text-orange-300 hover:bg-orange-500/10"
          >
            Ver assinatura
          </button>
        </>
      ) : !seletorAberto ? (
        <>
          <p className="text-xs text-zinc-400">
            {cadeirasPagas} {cadeirasPagas === 1 ? 'cadeira paga' : 'cadeiras pagas'} ·{' '}
            {maximo > 0 ? `você pode anunciar até ${textoVagas(maximo)}` : 'nenhuma cadeira livre para nova vaga'}
          </p>
          <button
            type="button"
            onClick={() => setSeletorAberto(true)}
            disabled={maximo <= 0}
            className="w-full inline-flex items-center justify-center gap-1.5 rounded-xl bg-orange-500 px-3 py-3 text-sm font-black uppercase tracking-wide text-white hover:bg-orange-600 disabled:bg-zinc-800 disabled:text-zinc-500"
          >
            <Plus size={16} /> Anunciar vaga
          </button>
        </>
      ) : (
        <div className="rounded-xl border border-zinc-800 bg-black/30 p-3 space-y-3">
          <div className="flex items-center justify-center gap-5">
            <button
              type="button"
              aria-label="Diminuir quantidade de vagas"
              onClick={() => setQuantidade((atual) => limitarQuantidadeVagas(atual - 1, maximo))}
              disabled={quantidade <= 1 || publicando}
              className="h-11 w-11 rounded-full border border-zinc-700 bg-zinc-800 text-white flex items-center justify-center disabled:opacity-30"
            >
              <Minus size={18} />
            </button>
            <span data-testid="quantidade-vagas" aria-live="polite" className="min-w-[2ch] text-center text-3xl font-black text-white">{quantidade}</span>
            <button
              type="button"
              aria-label="Aumentar quantidade de vagas"
              onClick={() => setQuantidade((atual) => limitarQuantidadeVagas(atual + 1, maximo))}
              disabled={quantidade >= maximo || publicando}
              className="h-11 w-11 rounded-full border border-orange-500/60 bg-orange-500/15 text-orange-300 flex items-center justify-center disabled:opacity-30"
            >
              <Plus size={18} />
            </button>
          </div>
          <p className="text-center text-[11px] text-zinc-400">Você pode anunciar até {textoVagas(maximo)}</p>
          <button
            type="button"
            onClick={confirmarAnuncio}
            disabled={publicando}
            className="w-full rounded-xl bg-orange-500 px-3 py-2.5 text-sm font-black uppercase tracking-wide text-white hover:bg-orange-600 disabled:opacity-50"
          >
            {publicando ? 'Anunciando...' : 'Confirmar anúncio'}
          </button>
          <button
            type="button"
            onClick={() => { setSeletorAberto(false); setQuantidade(1); }}
            disabled={publicando}
            className="w-full text-xs font-semibold text-zinc-400 hover:text-white"
          >
            Cancelar
          </button>
        </div>
      )}

      {vagas.length > 0 && (
        <button
          type="button"
          onClick={() => setListaAberta((aberta) => !aberta)}
          aria-expanded={listaAberta}
          className="w-full flex items-center justify-between rounded-lg px-1 text-xs font-bold text-zinc-300 hover:text-white"
        >
          Ver e administrar vagas
          {listaAberta ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
        </button>
      )}

      {listaAberta && vagas.length > 0 && (
        <div className="space-y-2" data-testid="lista-vagas">
          {vagas.map((vaga, indice) => {
            const aberta = vaga.status === 'disponivel';
            const aguardando = vaga.status === 'aguardando_desbloqueio';
            const temChat = aguardando || vaga.status === 'ocupada_por_barbeiro';
            const expandida = vagaExpandidaId === vaga.id;
            const titulo = `Cadeira ${vaga.cadeira_numero ?? indice + 1}`;
            return (
              <div key={vaga.id} className="rounded-xl border border-zinc-800 bg-black/30 p-2.5 space-y-2">
                <div className="flex items-center justify-between gap-2">
                  <div className="min-w-0">
                    <p className="text-xs font-bold text-white">
                      {titulo}{vaga.cadeira_bloqueada ? ' · 🔒 Bloqueada' : ''}
                    </p>
                    <p className="text-[11px] text-zinc-400 truncate">{descreverVaga(vaga)}</p>
                  </div>
                  {temChat && (
                    <button
                      type="button"
                      onClick={() => setChatVaga({ id: vaga.id, titulo: `${vaga.barbeiro_nome || 'Freelancer'} · ${titulo}` })}
                      className="relative shrink-0 inline-flex items-center gap-1 rounded-lg bg-zinc-800 px-2.5 py-1.5 text-[11px] font-bold text-white hover:bg-zinc-700"
                    >
                      <MessageCircle size={13} /> Chat
                      {vaga.nao_lidas > 0 && (
                        <span className="absolute -top-1.5 -right-1.5 min-w-[16px] h-4 px-1 rounded-full bg-orange-500 text-[9px] font-black flex items-center justify-center">
                          {vaga.nao_lidas}
                        </span>
                      )}
                    </button>
                  )}
                </div>

                <div className="flex flex-wrap gap-2">
                  {aberta && (
                    <button
                      type="button"
                      onClick={() => setVagaExpandidaId(expandida ? null : vaga.id)}
                      aria-expanded={expandida}
                      className="rounded-lg bg-zinc-800 px-2.5 py-1.5 text-[11px] font-bold text-white hover:bg-zinc-700"
                    >
                      {expandida ? 'Ocultar candidatos' : 'Ver candidatos'}
                    </button>
                  )}
                  {vaga.cadeira_bloqueada && vaga.cadeira_id && aguardando && (
                    <button
                      type="button"
                      onClick={() => executar(`desbloquear-${vaga.id}`, () => desbloquearCadeiraDaVaga(API_URL, token, vaga.cadeira_id), 'Cadeira desbloqueada.')}
                      disabled={acaoEmAndamento === `desbloquear-${vaga.id}`}
                      className="rounded-lg bg-emerald-600 px-2.5 py-1.5 text-[11px] font-bold text-white hover:bg-emerald-500 disabled:opacity-50"
                    >
                      🔓 Desbloquear cadeira
                    </button>
                  )}
                  {(aberta || aguardando) && (
                    <button
                      type="button"
                      onClick={() => cancelar(vaga)}
                      disabled={acaoEmAndamento === `cancelar-${vaga.id}`}
                      className="rounded-lg border border-red-600/40 px-2.5 py-1.5 text-[11px] font-bold text-red-300 hover:bg-red-600/10 disabled:opacity-50"
                    >
                      {cancelamentoPendenteId === vaga.id ? 'Toque de novo para cancelar' : 'Cancelar vaga'}
                    </button>
                  )}
                </div>

                {aberta && expandida && (
                  candidatos.length === 0 ? (
                    <p className="text-[11px] text-zinc-500">Nenhum freelancer se candidatou ainda.</p>
                  ) : (
                    <div className="space-y-1.5">
                      {candidatos.map((candidato) => (
                        <div key={candidato.id} className="flex items-center justify-between gap-2 rounded-md border border-zinc-800 bg-zinc-950/60 p-2">
                          <button
                            type="button"
                            onClick={() => onVerPerfil(candidato.freelancer_id, candidato.nome)}
                            className="min-w-0 flex-1 text-left text-xs font-bold text-white truncate underline decoration-dotted underline-offset-2"
                          >
                            {candidato.nome}
                          </button>
                          <button
                            type="button"
                            onClick={() => escolher(vaga.id, candidato)}
                            disabled={acaoEmAndamento === `escolher-${candidato.freelancer_id}`}
                            className="shrink-0 rounded-md bg-emerald-600 hover:bg-emerald-500 disabled:opacity-50 text-white px-2.5 py-1.5 text-[11px] font-bold"
                          >
                            Escolher
                          </button>
                        </div>
                      ))}
                    </div>
                  )
                )}
              </div>
            );
          })}
        </div>
      )}

      {chatVaga && (
        <ChatVaga
          token={token}
          apiBase={API_URL}
          vagaId={chatVaga.id}
          titulo={chatVaga.titulo}
          onFechar={() => { setChatVaga(null); carregar(); }}
        />
      )}
    </div>
  );
}
