// --- ARQUIVO: barbermove/src/components/TelaMensalidadeAssinatura.jsx ---
// Tela "Adicionar cadeiras" - Apenas para DONO DA BARBEARIA
// Preços e posições vêm sempre do servidor (/api/v1/cobrancas/cadeiras/orcamento).

import React, { useState, useEffect } from 'react';
import { Plus, Minus, Check, Loader, ChevronDown } from 'lucide-react';
import { gerarQrDataUrl, validarCartaoBasico, salvarMetodoPreferidoCliente } from './checkout/core';
import { getApiBaseUrl } from '../utils/api';
import PagamentoPix, { usePixDisponivel } from './PagamentoPix';
import { criarPixAssinaturaCadeiras, criarPixMensalidade, orcarCadeiras } from '../utils/cobrancasPix';

const MAX_CADEIRAS = 20;

export default function TelaMensalidadeAssinatura({ token, barbeariaId, API_URL, onNotify }) {
  const defaultHost = typeof window !== 'undefined' ? window.location.hostname : 'localhost';
  const defaultProtocol = typeof window !== 'undefined' && window.location.protocol === 'https:' ? 'https' : 'http';
  const apiBase = API_URL || import.meta.env.VITE_API_URL?.trim() || getApiBaseUrl();
  const chaveQtdLocal = `assinatura_qtd_cadeiras_${barbeariaId || 'default'}`;
  const mixedContentRisk =
    typeof window !== 'undefined' &&
    window.location.protocol === 'https:' &&
    apiBase.startsWith('http://');

  // Quantas cadeiras o dono quer ADICIONAR (o total é cadeirasAtuais + adicionar).
  const [adicionar, setAdicionar] = useState(1);
  const [loading, setLoading] = useState(false);
  const [processandoPagamento, setProcessandoPagamento] = useState(false);
  const [metodoPagamento, setMetodoPagamento] = useState('pix');
  const [tipoCartao, setTipoCartao] = useState('cartao_credito');
  const [cartao, setCartao] = useState({
    numero_cartao: '',
    titular: '',
    validade: '',
    cvv: '',
  });
  const [pixData, setPixData] = useState(null);
  const [pixQrFallbackSrc, setPixQrFallbackSrc] = useState('');
  const [pixQrImagemInvalida, setPixQrImagemInvalida] = useState(false);
  const [copiado, setCopiado] = useState(false);
  // Pix real (Mercado Pago): cadeiras/mensalidade só liberam após a aprovação no backend.
  const pixReal = usePixDisponivel(apiBase, token);
  // null = ainda carregando. O orçamento do servidor corrige este valor se divergir.
  const [cadeirasAtuais, setCadeirasAtuais] = useState(null);
  const [cobranca, setCobranca] = useState(null);
  const [acaoCobranca, setAcaoCobranca] = useState(null);
  const [outrasOpcoes, setOutrasOpcoes] = useState(false);
  const [qtdReduzir, setQtdReduzir] = useState(1);

  const pareceQrEmImagem = (valor) => {
    if (!valor || typeof valor !== 'string') return false;
    const conteudo = valor.trim();
    if (!conteudo) return false;
    if (conteudo.startsWith('data:image')) return true;
    if (conteudo.startsWith('http://') || conteudo.startsWith('https://')) return true;
    if (conteudo.startsWith('iVBORw0KGgo')) return true;
    if (conteudo.startsWith('/9j/')) return true;
    if (conteudo.startsWith('R0lGOD')) return true;
    if (conteudo.startsWith('PHN2Zy')) return true;
    if (conteudo.startsWith('000201')) return false;
    if (conteudo.includes('BR.GOV.BCB.PIX')) return false;
    return conteudo.length > 80 && /^[A-Za-z0-9+/=\s]+$/.test(conteudo);
  };

  const pareceCodigoPix = (valor) => {
    if (!valor || typeof valor !== 'string') return false;
    const conteudo = valor.trim();
    if (!conteudo) return false;
    if (conteudo.startsWith('000201')) return true;
    return conteudo.includes('BR.GOV.BCB.PIX');
  };

  const normalizarPixPayload = (data) => {
    const payload = data?.pix || data?.dados_pix || data?.data || data || {};
    const transactionData = payload?.point_of_interaction?.transaction_data || {};
    const nested = payload?.data || {};
    const cobr = payload?.cob || data?.cob || {};
    const loc = payload?.loc || data?.loc || {};

    const candidatosImagem = [
      payload.qrcode_base64,
      payload.qr_code_base64,
      payload.qrCodeBase64,
      payload.qrcode,
      payload.qr_code,
      payload.imagem_qr,
      payload.imagem_qrcode,
      payload.base64,
      payload.encodedImage,
      transactionData.qr_code_base64,
      transactionData.qr_code,
      transactionData.qrcode_base64,
      transactionData.encodedImage,
      nested.qrcode_base64,
      nested.qr_code_base64,
      nested.qrcode,
      nested.qr_code,
      nested.imagem_qr,
      nested.imagem_qrcode,
      nested.base64,
      nested.encodedImage,
      cobr.qrcode_base64,
      cobr.qr_code_base64,
      cobr.qrcode,
      cobr.qr_code,
      loc.qrcode_base64,
      loc.qr_code_base64,
      loc.qrcode,
      loc.qr_code,
    ];

    const candidatosTexto = [
      payload.pix_copia_cola,
      payload.codigo_pix,
      payload.copia_cola,
      payload.emv,
      payload.qrcode,
      payload.qr_code,
      payload.payload,
      payload.payload_pix,
      payload.qr,
      transactionData.qr_code,
      transactionData.qrcode,
      transactionData.payload,
      nested.pix_copia_cola,
      nested.codigo_pix,
      nested.copia_cola,
      nested.emv,
      nested.qrcode,
      nested.qr_code,
      nested.payload,
      nested.payload_pix,
      nested.qr,
      cobr.pix_copia_cola,
      cobr.codigo_pix,
      cobr.emv,
      cobr.qrcode,
      cobr.qr_code,
      loc.qrcode,
      loc.qr_code,
      data?.pix_copia_cola,
      data?.codigo_pix,
      data?.copia_cola,
      data?.emv,
      data?.qrcode,
      data?.qr_code,
      data?.payload,
      data?.payload_pix,
    ];

    let qrcodeBase64 = null;
    for (const item of candidatosImagem) {
      if (pareceQrEmImagem(item)) {
        qrcodeBase64 = item;
        break;
      }
    }

    let pixCopiaCola = '';
    for (const item of candidatosTexto) {
      if (pareceCodigoPix(item)) {
        pixCopiaCola = item;
        break;
      }
    }

    if (!pixCopiaCola) {
      pixCopiaCola = candidatosTexto.find((item) => typeof item === 'string' && item.trim()) || '';
    }

    return {
      ...payload,
      qrcode_base64: qrcodeBase64,
      pix_copia_cola: pixCopiaCola,
      valor: payload.valor ?? payload.amount ?? nested.valor ?? nested.amount ?? 0,
    };
  };

  const montarPixFinal = (pixRaw) => {
    const pixNormalizado = normalizarPixPayload(pixRaw);
    const payloadBruto = pixRaw?.pix || pixRaw?.dados_pix || pixRaw?.data || pixRaw || {};
    const payloadData = payloadBruto?.data || {};
    const payloadCobr = payloadBruto?.cob || {};

    return {
      ...payloadBruto,
      ...pixNormalizado,
      qrcode_base64:
        pixNormalizado.qrcode_base64 ||
        payloadBruto.qrcode_base64 ||
        payloadBruto.qr_code_base64 ||
        payloadBruto.qrCodeBase64 ||
        payloadData.qrcode_base64 ||
        payloadData.qr_code_base64 ||
        payloadCobr.qrcode_base64 ||
        payloadCobr.qr_code_base64 ||
        null,
      pix_copia_cola:
        pixNormalizado.pix_copia_cola ||
        payloadBruto.pix_copia_cola ||
        payloadBruto.codigo_pix ||
        payloadBruto.copia_cola ||
        payloadBruto.emv ||
        payloadBruto.qrcode ||
        payloadBruto.qr_code ||
        payloadBruto.payload ||
        payloadData.pix_copia_cola ||
        payloadData.codigo_pix ||
        payloadData.copia_cola ||
        payloadData.emv ||
        payloadData.payload ||
        payloadCobr.pix_copia_cola ||
        payloadCobr.codigo_pix ||
        payloadCobr.emv ||
        '',
      valor:
        pixNormalizado.valor ??
        payloadBruto.valor ??
        payloadBruto.amount ??
        payloadData.valor ??
        payloadData.amount ??
        payloadCobr.valor_original ??
        payloadBruto.valor_mensalidade ??
        0,
    };
  };

  const getPixQrSrc = (qrcodeBase64) => {
    if (!qrcodeBase64) return '';
    const conteudo = String(qrcodeBase64).trim();
    if (!conteudo) return '';
    if (conteudo.startsWith('data:image')) return conteudo;
    if (conteudo.startsWith('http://') || conteudo.startsWith('https://')) {
      if (mixedContentRisk && conteudo.startsWith('http://')) {
        if (import.meta.env.DEV) {
          console.warn('URL HTTP de QR bloqueada por mixed content. Usando fallback por copia e cola.');
        }
        return '';
      }
      return conteudo;
    }

    const conteudoLimpo = conteudo.replace(/\s/g, '');
    if (!conteudoLimpo) return '';

    let mime = 'image/png';
    if (conteudoLimpo.startsWith('/9j/')) mime = 'image/jpeg';
    if (conteudoLimpo.startsWith('R0lGOD')) mime = 'image/gif';
    if (conteudoLimpo.startsWith('PHN2Zy')) mime = 'image/svg+xml';
    return `data:${mime};base64,${conteudoLimpo}`;
  };

  // Formatador de moeda brasileira
  const formatarMoeda = (valor) => {
    return new Intl.NumberFormat('pt-BR', {
      style: 'currency',
      currency: 'BRL'
    }).format(valor);
  };

  const salvarQtdLocal = (qtd) => {
    try {
      if (typeof window !== 'undefined') window.localStorage.setItem(chaveQtdLocal, String(qtd));
    } catch (_) {
      // sem armazenamento local
    }
  };

  // Quantidade atual e preço de cada próxima posição, direto do servidor (mesmo cálculo do Pix).
  // Orçar o máximo devolve os preços de todas as posições livres numa chamada só.
  const [itensServidor, setItensServidor] = useState(null);
  const [erroCarga, setErroCarga] = useState(false);
  const [recarga, setRecarga] = useState(0);
  useEffect(() => {
    if (!barbeariaId || !token) return undefined;
    let ativo = true;
    setErroCarga(false);
    orcarCadeiras(apiBase, token, MAX_CADEIRAS)
      .then((orc) => {
        if (!ativo) return;
        const atuais = Number(orc?.cadeiras_atuais);
        if (Number.isNaN(atuais)) {
          setErroCarga(true);
          return;
        }
        setCadeirasAtuais(atuais);
        setItensServidor(Array.isArray(orc?.itens) ? orc.itens : []);
      })
      .catch(() => { if (ativo) setErroCarga(true); });
    return () => { ativo = false; };
  }, [barbeariaId, token, apiBase, recarga]);

  useEffect(() => {
    let ativo = true;

    const gerarQrFallback = async () => {
      if (!pixData?.pix_copia_cola) {
        setPixQrFallbackSrc('');
        setPixQrImagemInvalida(false);
        return;
      }

      setPixQrImagemInvalida(false);

      try {
        const dataUrl = await gerarQrDataUrl(pixData.pix_copia_cola);
        if (ativo) setPixQrFallbackSrc(dataUrl);
      } catch (err) {
        if (ativo) {
          setPixQrFallbackSrc('');
        }
      }
    };

    gerarQrFallback();

    return () => {
      ativo = false;
    };
  }, [pixData]);

  const carregado = cadeirasAtuais != null && itensServidor != null;
  const maxAdicionar = carregado ? Math.min(MAX_CADEIRAS - cadeirasAtuais, itensServidor.length) : 0;
  const qtdAdicionar = Math.min(Math.max(adicionar, 1), Math.max(maxAdicionar, 1));
  const itensSelecionados = carregado ? itensServidor.slice(0, qtdAdicionar) : [];
  // Soma dos valores que o servidor já calculou por posição (igual ao valor_cobranca do orçamento).
  const totalAdicional = Number(itensSelecionados.reduce((soma, item) => soma + Number(item.valor || 0), 0).toFixed(2));
  // Posições seguidas com o mesmo valor viram uma linha só (ex.: "6ª a 20ª · 15 × R$ 17,90").
  const faixasSelecionadas = itensSelecionados.reduce((faixas, item) => {
    const ultima = faixas[faixas.length - 1];
    if (ultima && ultima.valor === item.valor && ultima.ate === item.posicao - 1) {
      ultima.ate = item.posicao;
      ultima.qtd += 1;
    } else {
      faixas.push({ de: item.posicao, ate: item.posicao, qtd: 1, valor: item.valor });
    }
    return faixas;
  }, []);
  const totalDesejado = (cadeirasAtuais ?? 0) + qtdAdicionar;
  const qtdReduzirValida = Math.min(Math.max(qtdReduzir, 1), Math.max((cadeirasAtuais ?? 1) - 1, 1));

  const handleMais = () => setAdicionar(Math.min(qtdAdicionar + 1, maxAdicionar));
  const handleMenos = () => setAdicionar(Math.max(qtdAdicionar - 1, 1));

  // Pix real: o backend calcula o valor (o app nunca envia preço) e reaproveita a cobrança pendente.
  const gerarPixReal = async (acao) => {
    setLoading(true);
    try {
      const nova = acao.tipo === 'cadeiras'
        ? await criarPixAssinaturaCadeiras(apiBase, token, acao.total)
        : await criarPixMensalidade(apiBase, token);
      setAcaoCobranca(acao);
      setCobranca(nova);
    } catch (err) {
      onNotify('Erro: ' + err.message, 'error');
    } finally {
      setLoading(false);
    }
  };

  const aoConfirmarPix = async () => {
    onNotify('Pagamento confirmado! Plano liberado.', 'success');
    if (acaoCobranca?.total) salvarQtdLocal(acaoCobranca.total);
    setAdicionar(1);
    setRecarga((r) => r + 1);
  };

  const handleConfirmar = async (qtd) => {
    setLoading(true);
    try {
      const metodoPlano = metodoPagamento === 'cartao' ? tipoCartao : 'pix';

      const criarRes = await fetch(`${apiBase}/api/v1/assinaturas/criar`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({
          cadeiras_ativas: qtd,
          metodo_pagamento: metodoPlano
        })
      });

      const criarData = await criarRes.json().catch(() => ({}));
      if (!criarRes.ok) {
        throw new Error(criarData.detail || 'Erro ao confirmar plano');
      }

      if (metodoPagamento === 'cartao') {
        const errosCartao = validarCartaoBasico({ numero: cartao.numero_cartao, titular: cartao.titular, validade: cartao.validade, cvv: cartao.cvv });
        if (Object.keys(errosCartao).length > 0) {
          onNotify('Preencha todos os dados do cartão corretamente', 'error');
          return;
        }

        const cardRes = await fetch(`${apiBase}/api/v1/assinaturas/pagar-mensalidade`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${token}`
          },
          body: JSON.stringify({
            metodo_pagamento: tipoCartao,
            numero_cartao: cartao.numero_cartao,
            titular: cartao.titular,
            validade: cartao.validade,
            cvv: cartao.cvv
          })
        });

        const cardData = await cardRes.json().catch(() => ({}));
        if (!cardRes.ok) {
          throw new Error(cardData.detail || 'Erro ao processar pagamento com cartao');
        }

        setPixData(null);
        setCartao({ numero_cartao: '', titular: '', validade: '', cvv: '' });
        salvarQtdLocal(qtd);
        onNotify(cardData.message || 'Pagamento com cartao confirmado com sucesso!', 'success');
        setRecarga((r) => r + 1);
        return;
      }

      const pixRes = await fetch(`${apiBase}/api/v1/assinaturas/pagar-mensalidade/pix`, {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${token}` }
      });

      const pixRaw = await pixRes.json().catch(() => ({}));
      if (!pixRes.ok) {
        throw new Error(pixRaw.detail || 'Erro ao gerar PIX do plano');
      }

      const pixFinal = montarPixFinal(pixRaw);
      if (!pixFinal.qrcode_base64 && !pixFinal.pix_copia_cola) {
        throw new Error('PIX gerado sem QR Code e sem codigo copia e cola');
      }

      setPixData(pixFinal);
      salvarQtdLocal(qtd);
      onNotify('PIX do plano gerado com sucesso!', 'success');
    } catch (err) {
      onNotify('Erro ao conectar: ' + err.message, 'error');
    } finally {
      setLoading(false);
    }
  };

  const continuarParaPagamento = () => {
    if (!carregado || maxAdicionar <= 0 || pixReal === null) return;
    if (pixReal) {
      gerarPixReal({ tipo: 'cadeiras', total: totalDesejado });
      return;
    }
    handleConfirmar(totalDesejado);
  };

  const pagarMensalidade = () => {
    if (pixReal) {
      gerarPixReal({ tipo: 'mensalidade' });
      return;
    }
    handleConfirmar(cadeirasAtuais);
  };

  // Reduzir não gera cobrança no Pix real; no fluxo antigo segue o mesmo caminho de antes.
  const reduzirCadeiras = async () => {
    const qtd = qtdReduzirValida;
    if (!pixReal) {
      await handleConfirmar(qtd);
      return;
    }
    setLoading(true);
    try {
      const res = await fetch(`${apiBase}/api/v1/assinaturas/criar`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
        body: JSON.stringify({ cadeiras_ativas: qtd, metodo_pagamento: 'pix' })
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) throw new Error(data.detail || 'Erro ao reduzir cadeiras');
      salvarQtdLocal(qtd);
      onNotify('Plano atualizado.', 'success');
      setOutrasOpcoes(false);
      setRecarga((r) => r + 1);
    } catch (err) {
      onNotify('Erro: ' + err.message, 'error');
    } finally {
      setLoading(false);
    }
  };

  const confirmarPagamentoPix = async () => {
    setProcessandoPagamento(true);
    try {
      const res = await fetch(`${apiBase}/api/v1/assinaturas/pagar-mensalidade`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({
          metodo_pagamento: 'pix',
          confirmar_pix: true
        })
      });

      const data = await res.json().catch(() => ({}));
      if (!res.ok) {
        throw new Error(data.detail || 'Erro ao confirmar pagamento PIX');
      }

      setPixData(null);
      onNotify(data.message || 'Pagamento PIX confirmado com sucesso!', 'success');
      setRecarga((r) => r + 1);
    } catch (err) {
      onNotify('Erro: ' + err.message, 'error');
    } finally {
      setProcessandoPagamento(false);
    }
  };

  const voltarParaSelecao = () => {
    setPixData(null);
    setCobranca(null);
    setAcaoCobranca(null);
    setProcessandoPagamento(false);
    setLoading(false);
    setCopiado(false);
    setPixQrFallbackSrc('');
    setPixQrImagemInvalida(false);
  };

  const copiarPix = async () => {
    if (!pixData?.pix_copia_cola) return;
    await navigator.clipboard.writeText(pixData.pix_copia_cola);
    setCopiado(true);
    setTimeout(() => setCopiado(false), 1500);
    onNotify('Codigo PIX copiado', 'success');
  };

  const pixQrSrc = getPixQrSrc(pixData?.qrcode_base64);
  const emPagamento = Boolean((pixReal && cobranca) || (!pixReal && pixData));
  const rotuloCadeiras = (n) => `${n} ${n === 1 ? 'cadeira' : 'cadeiras'}`;

  return (
    <div className="w-full min-h-[100dvh] overflow-x-hidden bg-gradient-to-br from-black via-zinc-950 to-zinc-900">
      <div className="w-full max-w-md mx-auto px-4 pt-4 pb-24">
        <h2 className="text-2xl font-bold text-white mb-1">Adicionar cadeiras</h2>

        {carregado ? (
          <p className="text-sm text-zinc-300 mb-5">
            Você já possui <span className="font-bold text-white">{rotuloCadeiras(cadeirasAtuais)}</span>.
          </p>
        ) : erroCarga ? (
          <div className="rounded-2xl border border-red-800/60 bg-red-900/20 p-4 mt-4 text-sm text-red-200">
            <p className="mb-3">Não foi possível carregar suas cadeiras.</p>
            <button
              type="button"
              onClick={() => setRecarga((r) => r + 1)}
              className="rounded-xl border border-red-700 px-4 py-2 font-bold text-red-100 active:scale-95"
            >
              Tentar novamente
            </button>
          </div>
        ) : (
          <p className="text-sm text-zinc-400 mb-5 flex items-center gap-2">
            <Loader size={14} className="animate-spin" /> Carregando…
          </p>
        )}

        {mixedContentRisk && (
          <div className="bg-amber-900/30 border border-amber-600 text-amber-200 rounded-lg p-2 text-xs mb-3 leading-tight">
            Possivel bloqueio: app em HTTPS e API em HTTP. Use HTTPS no VITE_API_URL.
          </div>
        )}

        {carregado && !emPagamento && (maxAdicionar <= 0 ? (
          <div className="rounded-2xl border border-zinc-800 bg-zinc-900/60 p-4 text-sm text-zinc-300">
            Você já está no limite de {MAX_CADEIRAS} cadeiras.
          </div>
        ) : (
          <>
            {/* SELETOR */}
            <section className="rounded-2xl border border-zinc-800 bg-zinc-900/60 p-4 mb-3">
              <p className="text-base font-semibold text-white text-center mb-4">Quantas cadeiras deseja adicionar?</p>
              <div className="flex items-center justify-center gap-6">
                <button
                  type="button"
                  onClick={handleMenos}
                  aria-label="Diminuir quantidade de cadeiras"
                  disabled={qtdAdicionar <= 1 || loading}
                  className="w-14 h-14 flex items-center justify-center rounded-full bg-zinc-800 border border-zinc-700 text-white disabled:opacity-40 active:scale-95 transition"
                >
                  <Minus size={24} />
                </button>
                <span className="w-16 text-center text-5xl font-bold text-orange-500 tabular-nums" aria-live="polite">
                  {qtdAdicionar}
                </span>
                <button
                  type="button"
                  onClick={handleMais}
                  aria-label="Aumentar quantidade de cadeiras"
                  disabled={qtdAdicionar >= maxAdicionar || loading}
                  className="w-14 h-14 flex items-center justify-center rounded-full bg-orange-600 hover:bg-orange-700 text-white disabled:opacity-40 active:scale-95 transition"
                >
                  <Plus size={24} />
                </button>
              </div>

              {/* PREÇO DE CADA CADEIRA NOVA (posição e valor vindos do servidor) */}
              <div className="mt-4 pt-3 border-t border-zinc-800 text-sm">
                {qtdAdicionar === 1 ? (
                  <p className="text-zinc-300 text-center leading-relaxed">
                    A próxima cadeira será a <span className="font-bold text-white">{itensSelecionados[0]?.posicao}ª</span>
                    {' '}e custará <span className="font-bold text-white">{formatarMoeda(itensSelecionados[0]?.valor ?? 0)}/mês</span>.
                  </p>
                ) : (
                  <ul className="space-y-1.5">
                    {faixasSelecionadas.map((faixa) => (
                      <li key={faixa.de} className="flex items-center justify-between gap-3">
                        <span className="text-zinc-400">
                          {faixa.qtd === 1 ? `${faixa.de}ª cadeira` : `${faixa.de}ª a ${faixa.ate}ª cadeira`}
                        </span>
                        <span className="font-semibold text-white tabular-nums text-right">
                          {faixa.qtd > 1 && <span className="text-zinc-400 font-normal">{faixa.qtd} × </span>}
                          {formatarMoeda(faixa.valor)}/mês
                        </span>
                      </li>
                    ))}
                  </ul>
                )}
              </div>
            </section>

            {/* TOTAL ADICIONAL */}
            <div className="rounded-2xl border border-orange-600/40 bg-orange-600/10 px-4 py-3 mb-4 flex items-center justify-between gap-3">
              <span className="text-sm font-semibold text-orange-200">Total mensal adicional</span>
              <span className="text-2xl font-bold text-white tabular-nums">{formatarMoeda(totalAdicional)}</span>
            </div>

            {/* FLUXO ANTIGO (sem Pix do Mercado Pago): escolha do método */}
            {pixReal === false && (
              <div className="mb-4 space-y-2">
                <div className="grid grid-cols-2 gap-2">
                  <button
                    type="button"
                    onClick={() => {
                      salvarMetodoPreferidoCliente && salvarMetodoPreferidoCliente('pix');
                      setMetodoPagamento('pix');
                    }}
                    className={`rounded-xl px-3 py-2 text-sm font-bold border transition ${metodoPagamento === 'pix' ? 'bg-orange-600/20 border-orange-500 text-orange-300' : 'bg-zinc-800 border-zinc-700 text-zinc-300 hover:bg-zinc-700'}`}
                  >
                    PIX
                  </button>
                  <button
                    type="button"
                    onClick={() => {
                      salvarMetodoPreferidoCliente && salvarMetodoPreferidoCliente('cartao_credito');
                      setMetodoPagamento('cartao');
                    }}
                    className={`rounded-xl px-3 py-2 text-sm font-bold border transition ${metodoPagamento === 'cartao' ? 'bg-blue-600/20 border-blue-500 text-blue-300' : 'bg-zinc-800 border-zinc-700 text-zinc-300 hover:bg-zinc-700'}`}
                  >
                    Cartao
                  </button>
                </div>

                {metodoPagamento === 'cartao' && (
                  <div className="space-y-2 bg-zinc-800/40 border border-zinc-700 rounded-xl p-3">
                    <div className="grid grid-cols-2 gap-2">
                      <button
                        type="button"
                        onClick={() => setTipoCartao('cartao_credito')}
                        className={`rounded py-2 text-sm font-bold border transition ${tipoCartao === 'cartao_credito' ? 'bg-blue-600/20 border-blue-500 text-blue-300' : 'bg-zinc-800 border-zinc-700 text-zinc-300 hover:bg-zinc-700'}`}
                      >
                        Credito
                      </button>
                      <button
                        type="button"
                        onClick={() => setTipoCartao('cartao_debito')}
                        className={`rounded py-2 text-sm font-bold border transition ${tipoCartao === 'cartao_debito' ? 'bg-indigo-600/20 border-indigo-500 text-indigo-300' : 'bg-zinc-800 border-zinc-700 text-zinc-300 hover:bg-zinc-700'}`}
                      >
                        Debito
                      </button>
                    </div>

                    <input
                      type="text"
                      placeholder="Numero do cartao"
                      value={cartao.numero_cartao}
                      onChange={(e) => setCartao({ ...cartao, numero_cartao: e.target.value.replace(/\D/g, '').slice(0, 19) })}
                      className="w-full bg-zinc-900 border border-zinc-700 rounded px-3 py-2 text-sm text-white outline-none focus:border-orange-500"
                    />
                    <input
                      type="text"
                      placeholder="Nome no cartao"
                      value={cartao.titular}
                      onChange={(e) => setCartao({ ...cartao, titular: e.target.value.toUpperCase() })}
                      className="w-full bg-zinc-900 border border-zinc-700 rounded px-3 py-2 text-sm text-white outline-none focus:border-orange-500"
                    />
                    <div className="grid grid-cols-2 gap-2">
                      <input
                        type="text"
                        placeholder="MM/AA"
                        value={cartao.validade}
                        onChange={(e) => setCartao({ ...cartao, validade: e.target.value.slice(0, 5) })}
                        className="w-full bg-zinc-900 border border-zinc-700 rounded px-3 py-2 text-sm text-white outline-none focus:border-orange-500"
                      />
                      <input
                        type="text"
                        placeholder="CVV"
                        value={cartao.cvv}
                        onChange={(e) => setCartao({ ...cartao, cvv: e.target.value.replace(/\D/g, '').slice(0, 4) })}
                        className="w-full bg-zinc-900 border border-zinc-700 rounded px-3 py-2 text-sm text-white outline-none focus:border-orange-500"
                      />
                    </div>
                  </div>
                )}
              </div>
            )}

            <button
              type="button"
              onClick={continuarParaPagamento}
              disabled={loading || processandoPagamento || pixReal === null}
              className="w-full bg-gradient-to-r from-orange-600 to-orange-700 hover:from-orange-700 hover:to-orange-800 disabled:from-zinc-700 disabled:to-zinc-700 text-white font-bold py-4 px-4 rounded-2xl transition active:scale-95 flex items-center justify-center gap-2 text-base"
            >
              {loading ? (
                <>
                  <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                  <span>Gerando pagamento...</span>
                </>
              ) : (
                <>
                  <Check className="w-5 h-5" />
                  <span>Continuar para pagamento</span>
                </>
              )}
            </button>
          </>
        ))}

        {pixReal && cobranca && (
          <div className="mb-3">
            <PagamentoPix
              key={cobranca.identificador}
              token={token}
              API_URL={apiBase}
              cobranca={cobranca}
              titulo={acaoCobranca?.tipo === 'mensalidade' ? 'Pagamento da mensalidade' : 'Pagamento das cadeiras'}
              notify={onNotify}
              onConfirmado={aoConfirmarPix}
              onGerarNovo={acaoCobranca ? () => gerarPixReal(acaoCobranca) : undefined}
              onFechar={() => { setCobranca(null); setAcaoCobranca(null); }}
            />
          </div>
        )}

        {!pixReal && pixData && (
          <div className="bg-zinc-800 border border-zinc-700 rounded p-2 sm:p-3 space-y-2 sm:space-y-3 ring-1 ring-orange-500/60 mb-2 sm:mb-3 overflow-hidden">
            <p className="text-xs sm:text-sm font-bold text-white">PIX Gerado</p>

            {pixQrSrc && !pixQrImagemInvalida && (
              <div className="flex justify-center">
                <div className="bg-zinc-800 p-1 sm:p-2 rounded">
                  <img
                    src={pixQrSrc}
                    alt="QR Code PIX"
                    className="w-32 sm:w-40 h-32 sm:h-40 object-contain"
                    onError={() => setPixQrImagemInvalida(true)}
                  />
                </div>
              </div>
            )}
            {(pixQrImagemInvalida || !pixQrSrc) && pixQrFallbackSrc && (
              <div className="flex justify-center">
                <div className="bg-zinc-800 p-1 sm:p-2 rounded">
                  <img
                    src={pixQrFallbackSrc}
                    alt="QR Code PIX"
                    className="w-32 sm:w-40 h-32 sm:h-40 object-contain"
                  />
                </div>
              </div>
            )}
            {(pixQrImagemInvalida || !pixQrSrc) && !pixQrFallbackSrc && (
              <p className="text-xs text-amber-300 font-semibold">Use o código abaixo</p>
            )}

            <input
              type="text"
              readOnly
              value={pixData.pix_copia_cola || ''}
              className="w-full border border-zinc-600 bg-zinc-900 rounded p-1 sm:p-2 text-xs text-zinc-200 font-mono overflow-hidden truncate"
            />

            <button
              onClick={copiarPix}
              className="w-full bg-zinc-100 text-zinc-900 py-1.5 sm:py-2 rounded font-bold text-xs sm:text-sm"
            >
              {copiado ? '✓ Copiado!' : 'Copiar Código PIX'}
            </button>

            <button
              onClick={confirmarPagamentoPix}
              disabled={processandoPagamento}
              className="w-full bg-green-600 hover:bg-green-700 text-white py-1.5 sm:py-2 rounded font-bold disabled:opacity-60 flex items-center justify-center gap-1 sm:gap-2 text-xs sm:text-sm"
            >
              {processandoPagamento ? (
                <>
                  <Loader size={14} className="animate-spin" />
                  Confirmando...
                </>
              ) : (
                'Confirmar Pagamento'
              )}
            </button>

            <button
              onClick={voltarParaSelecao}
              className="w-full bg-transparent border border-zinc-600 text-zinc-200 py-1.5 sm:py-2 rounded font-bold text-xs sm:text-sm hover:bg-zinc-700"
            >
              Voltar para seleção de cadeiras
            </button>
          </div>
        )}

        {/* OUTRAS OPÇÕES (mensalidade sem cadeira nova / reduzir) — recolhidas */}
        {carregado && !emPagamento && cadeirasAtuais > 0 && pixReal !== null && (
          <div className="mt-6">
            <button
              type="button"
              onClick={() => setOutrasOpcoes((v) => !v)}
              aria-expanded={outrasOpcoes}
              className="w-full flex items-center justify-center gap-1 py-2 text-sm text-zinc-400 hover:text-zinc-200"
            >
              Outras opções
              <ChevronDown size={16} className={`transition-transform ${outrasOpcoes ? 'rotate-180' : ''}`} />
            </button>
            {outrasOpcoes && (
              <div className="mt-2 space-y-3 rounded-2xl border border-zinc-800 bg-zinc-900/40 p-3">
                <button
                  type="button"
                  onClick={pagarMensalidade}
                  disabled={loading}
                  className="w-full rounded-xl border border-zinc-700 bg-zinc-900 py-3 text-sm font-bold text-zinc-200 hover:bg-zinc-800 disabled:opacity-50 active:scale-95"
                >
                  Pagar mensalidade atual
                </button>
                {cadeirasAtuais > 1 && (
                  <div className="flex items-center gap-2">
                    <label htmlFor="qtd-reduzir" className="text-sm text-zinc-400 shrink-0">Reduzir para</label>
                    <select
                      id="qtd-reduzir"
                      value={qtdReduzirValida}
                      onChange={(e) => setQtdReduzir(Number(e.target.value))}
                      className="flex-1 min-w-0 rounded-xl border border-zinc-700 bg-zinc-900 px-3 py-2.5 text-sm text-white"
                    >
                      {Array.from({ length: cadeirasAtuais - 1 }, (_, i) => i + 1).map((n) => (
                        <option key={n} value={n}>{rotuloCadeiras(n)}</option>
                      ))}
                    </select>
                    <button
                      type="button"
                      onClick={reduzirCadeiras}
                      disabled={loading}
                      className="shrink-0 rounded-xl border border-zinc-700 px-4 py-2.5 text-sm font-bold text-zinc-200 hover:bg-zinc-800 disabled:opacity-50 active:scale-95"
                    >
                      Reduzir
                    </button>
                  </div>
                )}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
