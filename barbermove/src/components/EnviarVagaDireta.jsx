import React, { useEffect, useState } from 'react';
import FormularioVaga from './FormularioVaga';
import { buscarResumoVagas, enviarVagaDireta } from '../utils/vagas';

// Envio direto de vaga a um freelancer, a partir do perfil dele no painel do dono. Usa o mesmo
// formulário e o mesmo limite de cadeiras pagas do anúncio geral (o backend recalcula tudo).
export default function EnviarVagaDireta({ API_URL, token, notify, freelancer, onFechar, onEnviada, onAbrirAssinatura }) {
  const [resumo, setResumo] = useState(null);
  const [erro, setErro] = useState(false);
  const [enviando, setEnviando] = useState(false);

  useEffect(() => {
    let ativo = true;
    buscarResumoVagas(API_URL, token)
      .then((dados) => { if (ativo) setResumo(dados); })
      .catch(() => { if (ativo) setErro(true); });
    return () => { ativo = false; };
  }, [API_URL, token]);

  const confirmar = async (cadeirasEscolhidas, percentualFreelancer) => {
    if (percentualFreelancer === null) {
      notify('Informe a porcentagem do freelancer, de 0% a 100%.', 'error');
      return;
    }
    setEnviando(true);
    try {
      await enviarVagaDireta(API_URL, token, freelancer.id, cadeirasEscolhidas[0], percentualFreelancer);
      notify(`Vaga enviada para ${freelancer.nome}! Acompanhe a resposta em Ver e administrar vagas.`, 'success');
      onEnviada?.();
      onFechar();
    } catch (error) {
      notify(error?.message || 'Não foi possível enviar a vaga', 'error');
      buscarResumoVagas(API_URL, token).then(setResumo).catch(() => {});
    } finally {
      setEnviando(false);
    }
  };

  const cadeirasPagas = resumo?.cadeiras_pagas ?? 0;
  const disponiveis = resumo?.vagas_disponiveis_para_anunciar ?? 0;

  return (
    <div className="fixed inset-0 bg-black/80 z-[2300] flex items-center justify-center p-4" data-testid="enviar-vaga-direta">
      <div className="bg-zinc-950 border border-zinc-800 rounded-2xl w-full max-w-[420px] max-h-[90vh] overflow-y-auto p-4 space-y-3">
        <div className="flex justify-between items-start gap-2">
          <div className="min-w-0">
            <h3 className="text-sm font-black text-white uppercase tracking-wide">Enviar vaga</h3>
            <p className="text-xs text-zinc-400 truncate">Somente para {freelancer.nome}. A vaga não é divulgada aos outros freelancers.</p>
          </div>
          <button onClick={onFechar} disabled={enviando} className="text-zinc-400 px-2" aria-label="Fechar">✕</button>
        </div>

        {erro ? (
          <p className="text-xs text-red-300">Não foi possível carregar suas cadeiras. Tente de novo.</p>
        ) : !resumo ? (
          <div className="w-6 h-6 border-2 border-orange-500 border-t-transparent rounded-full animate-spin mx-auto my-4" />
        ) : cadeirasPagas === 0 || disponiveis <= 0 ? (
          <>
            <p className="text-xs text-zinc-400">
              {cadeirasPagas === 0
                ? 'Você precisa de ao menos uma cadeira com pagamento em dia para enviar vagas.'
                : 'Nenhuma cadeira paga livre para uma nova vaga agora.'}
            </p>
            {cadeirasPagas === 0 && onAbrirAssinatura && (
              <button
                type="button"
                onClick={() => { onFechar(); onAbrirAssinatura(); }}
                className="w-full rounded-xl border border-orange-500/50 px-3 py-2.5 text-xs font-black uppercase tracking-wide text-orange-300 hover:bg-orange-500/10"
              >
                Ver assinatura
              </button>
            )}
          </>
        ) : (
          <FormularioVaga
            cadeirasLivres={resumo.cadeiras_livres}
            maximo={1}
            enviando={enviando}
            textoEnviando="Enviando..."
            textoConfirmar={() => `Enviar vaga para ${freelancer.nome}`}
            onConfirmar={confirmar}
            onCancelar={onFechar}
          />
        )}
      </div>
    </div>
  );
}
