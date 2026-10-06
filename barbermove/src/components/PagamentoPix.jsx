import React, { useCallback, useEffect, useRef, useState } from 'react';
import { consultarCobranca } from '../utils/cobrancasPix';

// Pagamento Pix reutilizável (plano/cadeiras do proprietário, mensalidade, taxa do freelancer).
// O app só exibe e acompanha a cobrança: quem decide se está PAGO é o backend,
// depois da confirmação do Mercado Pago. Copiar o código ou abrir esta tela não paga nada.
// Nenhuma credencial do Mercado Pago passa pelo app.

const INTERVALO_CONSULTA_MS = 5000;

const brl = (v) => `R$ ${Number(v || 0).toFixed(2).replace('.', ',')}`;

const formatarHora = (iso) => {
  if (!iso) return '';
  try {
    return new Date(iso).toLocaleTimeString('pt-BR', { timeZone: 'America/Sao_Paulo', hour: '2-digit', minute: '2-digit' });
  } catch (_) {
    return '';
  }
};

async function copiarTexto(texto) {
  try {
    await navigator.clipboard.writeText(texto);
    return true;
  } catch (_) {
    // WebView sem permissão de clipboard: fallback com seleção
    try {
      const el = document.createElement('textarea');
      el.value = texto;
      el.setAttribute('readonly', '');
      el.style.position = 'fixed';
      el.style.opacity = '0';
      document.body.appendChild(el);
      el.select();
      const ok = document.execCommand('copy');
      document.body.removeChild(el);
      return ok;
    } catch (__) {
      return false;
    }
  }
}

const VISUAL_STATUS = {
  AGUARDANDO_PAGAMENTO: { rotulo: 'Aguardando pagamento', cor: 'text-amber-300', borda: 'border-amber-500/40 bg-amber-500/10' },
  PAGO: { rotulo: 'Pagamento confirmado', cor: 'text-emerald-300', borda: 'border-emerald-500/40 bg-emerald-500/10' },
  EXPIRADO: { rotulo: 'Pix expirado', cor: 'text-zinc-300', borda: 'border-zinc-600 bg-zinc-800/40' },
  CANCELADO: { rotulo: 'Cobrança cancelada', cor: 'text-zinc-300', borda: 'border-zinc-600 bg-zinc-800/40' },
  REJEITADO: { rotulo: 'Pagamento recusado', cor: 'text-red-300', borda: 'border-red-500/40 bg-red-500/10' },
  ESTORNADO: { rotulo: 'Pagamento estornado', cor: 'text-red-300', borda: 'border-red-500/40 bg-red-500/10' },
};

/**
 * Props:
 * - token, API_URL
 * - cobranca: objeto retornado por criarPix... (utils/cobrancasPix.js). Para trocar de cobrança,
 *   renderize com key={cobranca.identificador}.
 * - titulo (opcional)
 * - notify(msg, tipo) (opcional)
 * - onConfirmado(cobranca): chamado uma vez quando o backend confirmar PAGO + liberado
 * - onGerarNovo(): opcional; mostra "Gerar novo Pix" quando expirar/cancelar/recusar
 * - onFechar(): opcional
 */
export default function PagamentoPix({ token, API_URL, cobranca: inicial, titulo, notify, onConfirmado, onGerarNovo, onFechar }) {
  const [cobranca, setCobranca] = useState(inicial);
  const [copiado, setCopiado] = useState(false);
  const avisouConfirmacao = useRef(false);

  const status = cobranca?.status || 'AGUARDANDO_PAGAMENTO';
  const aguardando = status === 'AGUARDANDO_PAGAMENTO';

  const identificador = cobranca?.identificador;

  const atualizar = useCallback(async () => {
    if (!identificador || !token) return;
    try {
      const data = await consultarCobranca(API_URL, token, identificador);
      setCobranca(data);
    } catch (_) {
      // silencioso: tenta de novo no próximo ciclo
    }
  }, [API_URL, token, identificador]);

  useEffect(() => {
    if (!aguardando) return undefined;
    const t = setInterval(atualizar, INTERVALO_CONSULTA_MS);
    return () => clearInterval(t);
  }, [aguardando, atualizar]);

  useEffect(() => {
    if (status === 'PAGO' && cobranca?.liberado && !avisouConfirmacao.current) {
      avisouConfirmacao.current = true;
      onConfirmado?.(cobranca);
    }
  }, [status, cobranca, onConfirmado]);

  const copiar = async () => {
    const ok = await copiarTexto(cobranca?.pix_copia_cola || '');
    setCopiado(ok);
    notify?.(ok ? 'Código Pix copiado' : 'Não foi possível copiar. Selecione o código manualmente.', ok ? 'success' : 'error');
  };

  if (!cobranca) return null;

  const visual = VISUAL_STATUS[status] || VISUAL_STATUS.AGUARDANDO_PAGAMENTO;
  const pagoEmAnalise = status === 'PAGO' && !cobranca.liberado;

  return (
    <div className={`rounded-xl border p-3 text-sm space-y-3 ${visual.borda}`}>
      <div className="flex items-start justify-between gap-2">
        <div>
          <p className="font-bold text-white">{titulo || 'Pagamento via Pix'}</p>
          {cobranca.descricao && <p className="text-[11px] text-zinc-400">{cobranca.descricao}</p>}
        </div>
        {onFechar && (
          <button type="button" onClick={onFechar} className="text-zinc-400 hover:text-white text-xs px-1" aria-label="Fechar">
            ✕
          </button>
        )}
      </div>

      <div className="flex items-center justify-between">
        <span className="text-xs text-zinc-400">Valor</span>
        <span className="text-lg font-bold text-white">{brl(cobranca.valor)}</span>
      </div>

      <div className="flex items-center gap-2">
        {aguardando && <span className="inline-block w-3 h-3 rounded-full border-2 border-amber-300 border-t-transparent animate-spin" />}
        <span className={`text-xs font-bold ${visual.cor}`}>
          {pagoEmAnalise ? 'Pagamento recebido — em análise' : visual.rotulo}
        </span>
      </div>

      {aguardando && (
        <>
          {cobranca.qr_code_base64 && (
            <div className="flex justify-center bg-white rounded-lg p-2">
              <img src={`data:image/png;base64,${cobranca.qr_code_base64}`} alt="QR Code Pix" className="w-44 h-44" />
            </div>
          )}

          <div className="space-y-1">
            <p className="text-[11px] text-zinc-400">Pix Copia e Cola</p>
            <textarea
              readOnly
              rows={3}
              value={cobranca.pix_copia_cola || ''}
              onFocus={(e) => e.target.select()}
              className="w-full resize-none rounded bg-zinc-900 border border-zinc-700 px-2 py-1 text-[11px] text-zinc-300 break-all"
            />
          </div>

          <button
            type="button"
            onClick={copiar}
            disabled={!cobranca.pix_copia_cola}
            className="w-full rounded-lg bg-emerald-600 hover:bg-emerald-500 disabled:opacity-60 px-3 py-2 text-xs font-bold text-white"
          >
            {copiado ? 'Copiado ✓ — copiar de novo' : 'Copiar Pix'}
          </button>

          <p className="text-[11px] text-zinc-400">
            Pague no app do seu banco. A confirmação aparece aqui automaticamente assim que o pagamento for aprovado
            {cobranca.expira_em ? ` (válido até ${formatarHora(cobranca.expira_em)})` : ''}.
          </p>
        </>
      )}

      {status === 'PAGO' && cobranca.liberado && (
        <p className="text-xs text-emerald-200">✅ Pagamento confirmado. Tudo liberado.</p>
      )}
      {pagoEmAnalise && (
        <p className="text-xs text-amber-200">Recebemos o pagamento, mas ele precisa de conferência. Fale com o suporte BarberMove.</p>
      )}

      {['EXPIRADO', 'CANCELADO', 'REJEITADO'].includes(status) && (
        <div className="space-y-2">
          <p className="text-xs text-zinc-300">Nada foi cobrado por esta cobrança. Gere um novo Pix para pagar.</p>
          {onGerarNovo && (
            <button
              type="button"
              onClick={onGerarNovo}
              className="w-full rounded-lg bg-zinc-800 hover:bg-zinc-700 px-3 py-2 text-xs font-bold text-white"
            >
              Gerar novo Pix
            </button>
          )}
        </div>
      )}

    </div>
  );
}
