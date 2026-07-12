// --- ARQUIVO: barbermove/src/components/TelaMensalidadeAssinatura.jsx ---
// Tela de Plano e Assinatura - Mensalidade Progressiva por Cadeira
// Apenas para DONO DA BARBEARIA

import React, { useState, useEffect } from 'react';
import { Plus, Minus, TrendingUp, AlertCircle, Check, Loader } from 'lucide-react';
import { gerarQrDataUrl, validarCartaoBasico, salvarMetodoPreferidoCliente } from './checkout/core';
import { getApiBaseUrl } from '../utils/api';

export default function TelaMensalidadeAssinatura({ token, barbeariaId, API_URL, onNotify, onBack }) {
  const defaultHost = typeof window !== 'undefined' ? window.location.hostname : 'localhost';
  const defaultProtocol = typeof window !== 'undefined' && window.location.protocol === 'https:' ? 'https' : 'http';
  const apiBase = API_URL || import.meta.env.VITE_API_URL?.trim() || getApiBaseUrl();
  const chaveQtdLocal = `assinatura_qtd_cadeiras_${barbeariaId || 'default'}`;
  const mixedContentRisk =
    typeof window !== 'undefined' &&
    window.location.protocol === 'https:' &&
    apiBase.startsWith('http://');

  const [quantidadeCadeiras, setQuantidadeCadeiras] = useState(1);
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

  // Constantes da lógica de mensalidade
  const PRECOS_FIXOS = {
    1: 47.90,
    2: 37.90,
    3: 27.90,
    4: 20.90,
    5: 17.90,
  };
  const VALOR_MINIMO = 17.90;

  // Função para calcular o preço de cada cadeira
  const calcularPrecoCadeira = (numeroCadeira) => {
    if (numeroCadeira in PRECOS_FIXOS) {
      return PRECOS_FIXOS[numeroCadeira];
    }
    return VALOR_MINIMO;
  };

  // Função para calcular a mensalidade total
  const calcularMensalidadeTotal = (qtd) => {
    let total = 0;
    let detalhamento = [];

    for (let i = 1; i <= qtd; i++) {
      const preco = calcularPrecoCadeira(i);
      total += preco;
      detalhamento.push({ cadeira: i, preco });
    }

    // Economia vs uniforme (todas a R$47,90)
    const valorUniforme = qtd * 47.90;
    const economia = valorUniforme - total;

    return {
      total: parseFloat(total.toFixed(2)),
      economia: parseFloat(economia.toFixed(2)),
      detalhamento
    };
  };

  // Carregar quantidade atual de cadeiras da barbearia
  useEffect(() => {
    const carregarCadeiras = async () => {
      try {
        // 1) Prioriza valor salvo localmente para não perder seleção da UI.
        const valorLocal = typeof window !== 'undefined' ? window.localStorage.getItem(chaveQtdLocal) : null;
        if (valorLocal) {
          const qtdLocal = Number(valorLocal);
          if (!Number.isNaN(qtdLocal) && qtdLocal >= 1 && qtdLocal <= 20) {
            setQuantidadeCadeiras(qtdLocal);
          }
        }

        // 2) Busca assinatura salva no backend e sincroniza UI.
        const resAssinatura = await fetch(`${apiBase}/api/v1/assinaturas/minha-assinatura`, {
          headers: { 'Authorization': `Bearer ${token}` }
        });

        if (resAssinatura.ok) {
          const assinatura = await resAssinatura.json();
          const qtdAssinatura = Number(assinatura?.cadeiras_ativas ?? assinatura?.quantidade_cadeiras);
          if (!Number.isNaN(qtdAssinatura) && qtdAssinatura >= 1 && qtdAssinatura <= 20) {
            setQuantidadeCadeiras(qtdAssinatura);
            if (typeof window !== 'undefined') {
              window.localStorage.setItem(chaveQtdLocal, String(qtdAssinatura));
            }
            return;
          }
        }

        // 3) Fallback: estimar por cadeiras ativas da barbearia.
        const resCadeiras = await fetch(`${apiBase}/api/v1/cadeiras?barbearia_id=${barbeariaId}`, {
          headers: { 'Authorization': `Bearer ${token}` }
        });
        if (resCadeiras.ok) {
          const cadeiras = await resCadeiras.json();
          const ativas = Array.isArray(cadeiras) ? cadeiras.filter(c => c.status !== 'inativa').length : 0;
          const qtdFallback = Math.max(1, ativas);
          setQuantidadeCadeiras(qtdFallback);
          if (typeof window !== 'undefined') {
            window.localStorage.setItem(chaveQtdLocal, String(qtdFallback));
          }
        }
      } catch (err) {
        // Erro ao carregar cadeiras
      }
    };

    if (barbeariaId && token) {
      carregarCadeiras();
    }
  }, [barbeariaId, token, apiBase, chaveQtdLocal]);

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

  const calculos = calcularMensalidadeTotal(quantidadeCadeiras);
  const proximaCadeira = quantidadeCadeiras + 1;
  const proximoDetalhamento = calcularMensalidadeTotal(proximaCadeira);
  const incrementoProxima = proximoDetalhamento.total - calculos.total;

  const handleMais = () => {
    if (quantidadeCadeiras < 20) {
      setQuantidadeCadeiras(quantidadeCadeiras + 1);
    }
  };

  const handleMenos = () => {
    if (quantidadeCadeiras > 1) {
      setQuantidadeCadeiras(quantidadeCadeiras - 1);
    }
  };

  const handleConfirmar = async () => {
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
          cadeiras_ativas: quantidadeCadeiras,
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
        if (typeof window !== 'undefined') {
          window.localStorage.setItem(chaveQtdLocal, String(quantidadeCadeiras));
        }
        onNotify(cardData.message || 'Pagamento com cartao confirmado com sucesso!', 'success');
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
      if (typeof window !== 'undefined') {
        window.localStorage.setItem(chaveQtdLocal, String(quantidadeCadeiras));
      }
      onNotify('PIX do plano gerado com sucesso!', 'success');
    } catch (err) {
      onNotify('Erro ao conectar: ' + err.message, 'error');
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
    } catch (err) {
      onNotify('Erro: ' + err.message, 'error');
    } finally {
      setProcessandoPagamento(false);
    }
  };

  const voltarParaSelecao = () => {
    setPixData(null);
    setProcessandoPagamento(false);
    setLoading(false);
    setCopiado(false);
    setPixQrFallbackSrc('');
    setPixQrImagemInvalida(false);
    onBack && onBack();
  };

  const copiarPix = async () => {
    if (!pixData?.pix_copia_cola) return;
    await navigator.clipboard.writeText(pixData.pix_copia_cola);
    setCopiado(true);
    setTimeout(() => setCopiado(false), 1500);
    onNotify('Codigo PIX copiado', 'success');
  };

  const pixQrSrc = getPixQrSrc(pixData?.qrcode_base64);

  return (
    <div className="w-full min-h-[100dvh] overflow-x-hidden bg-gradient-to-br from-black via-zinc-950 to-zinc-900">
      <div className="w-full max-w-xl mx-auto p-2 sm:p-4 md:p-6 pb-24 sm:pb-32">
        {/* HEADER */}
        <div className="mb-3 sm:mb-6 flex items-start justify-between gap-3">
          <button
            type="button"
            onClick={voltarParaSelecao}
            className="shrink-0 rounded-lg border border-zinc-700 bg-zinc-900 px-3 py-2 text-xs sm:text-sm font-bold text-zinc-200 hover:bg-zinc-800"
          >
            Voltar
          </button>
          <div className="flex-1 min-w-0">
          <h2 className="text-lg sm:text-2xl md:text-3xl font-bold text-white mb-1 sm:mb-2 flex items-center gap-2">
            <TrendingUp size={20} className="text-orange-500 flex-shrink-0" />
            Seu Plano
          </h2>
          <p className="text-xs sm:text-sm text-zinc-300 leading-tight">
            Progressivo por cadeira - maior desconto com mais unidades
          </p>
          </div>
        </div>

      {mixedContentRisk && (
        <div className="bg-amber-900/30 border border-amber-600 text-amber-200 rounded-lg p-2 text-xs mb-3 leading-tight">
          Possivel bloqueio: app em HTTPS e API em HTTP. Use HTTPS no VITE_API_URL.
        </div>
      )}

      {/* SEÇÃO PRINCIPAL - SIMULADOR */}
      <div className="bg-zinc-900/50 border border-zinc-800 rounded-lg p-2 sm:p-3 md:p-4 mb-3 sm:mb-4 overflow-hidden">
        <h3 className="text-sm sm:text-base font-bold text-white mb-2 sm:mb-3">Simulador</h3>

        {/* CONTROLE DE QUANTIDADE */}
        <div className="grid grid-cols-3 gap-2 sm:gap-3 mb-3 sm:mb-4 bg-zinc-800/30 p-2 sm:p-3 rounded-lg items-center">
          <div className="text-center">
            <p className="text-xs text-zinc-300 mb-1">Cadeiras</p>
            <p className="text-xl sm:text-2xl font-bold text-orange-500">{quantidadeCadeiras}</p>
          </div>

          <div className="flex gap-1 sm:gap-2 justify-center">
            <button
              onClick={handleMenos}
              aria-label="Diminuir quantidade de cadeiras"
              disabled={quantidadeCadeiras <= 1}
              className="w-8 h-8 sm:w-10 sm:h-10 flex items-center justify-center bg-red-600 hover:bg-red-700 disabled:bg-zinc-700 disabled:text-zinc-500 text-white rounded text-xs sm:text-sm transition active:scale-95"
            >
              −
            </button>
            <button
              onClick={handleMais}
              aria-label="Aumentar quantidade de cadeiras"
              disabled={quantidadeCadeiras >= 20}
              className="w-8 h-8 sm:w-10 sm:h-10 flex items-center justify-center bg-green-600 hover:bg-green-700 disabled:bg-zinc-700 disabled:text-zinc-500 text-white rounded text-xs sm:text-sm transition active:scale-95"
            >
              +
            </button>
          </div>

          <div className="text-center">
            <p className="text-xs text-zinc-300 mb-1">Total</p>
            <p className="text-lg sm:text-xl font-bold text-green-500">
              {formatarMoeda(calculos.total)}
            </p>
          </div>
        </div>

        <div className="rounded-xl border border-zinc-800 bg-zinc-950/70 p-3 mb-3 text-xs text-zinc-300 leading-relaxed">
          <p className="font-bold text-orange-300 mb-1">Como funciona a cadeira</p>
          <p className="text-zinc-400">
            A cadeira 1 é a primeira cadeira paga do plano. Quando você aumenta a quantidade, o sistema adiciona a cadeira 2, 3 e assim por diante com preço progressivo.
            Se a barbearia contratou só 1 cadeira, apenas a <strong>Cadeira 1</strong> deve ficar ativa no painel.
          </p>
        </div>

        <div className="bg-zinc-900/70 border border-zinc-800 rounded-lg p-2 mb-3 text-xs text-zinc-300 leading-relaxed">
          <p className="font-bold text-orange-300 mb-1">Lógica das cadeiras</p>
          <p className="text-zinc-400">
            A cadeira 1 é a primeira vaga paga do plano. Ao aumentar a quantidade, o sistema adiciona a cadeira 2, 3 e assim por diante com preço progressivo.
            Se a sua barbearia contratou só 1 cadeira, a tela e o painel devem mostrar apenas a <strong>Cadeira 1</strong>.
          </p>
        </div>

        {/* ECONOMIA */}
        {calculos.economia > 0 && (
          <div className="bg-green-900/20 border border-green-700 rounded p-2 mb-3 text-xs">
            <p className="text-green-400 font-bold text-xs mb-0.5">Você economiza {formatarMoeda(calculos.economia)}</p>
            <p className="text-green-300 text-xs">em relação ao preço uniforme</p>
          </div>
        )}

        {/* DETALHAMENTO DE PREÇOS - APENAS EM DESKTOP/TABLET */}
        <div className="hidden sm:block mb-3 px-1">
          <p className="text-xs uppercase tracking-wider font-bold text-zinc-300 mb-2">Preços por Cadeira</p>
          <div className="grid grid-cols-3 gap-2 md:grid-cols-4">
            {calculos.detalhamento.slice(0, 6).map((item) => (
              <div
                key={item.cadeira}
                className={`rounded px-2 py-2 text-center text-xs transition ${
                  item.cadeira === quantidadeCadeiras
                    ? 'bg-zinc-800/80 border border-orange-500/40'
                    : 'bg-zinc-800/40 border border-zinc-700 opacity-60'
                }`}
              >
                <p className="text-zinc-300 text-xs font-semibold">#{item.cadeira}</p>
                <p className="text-white font-bold text-xs">{formatarMoeda(item.preco)}</p>
              </div>
            ))}
          </div>
        </div>

        {/* INFORMAÇÕES IMPORTANTES - COMPRIMIDO */}
        <div className="hidden sm:block bg-blue-900/20 border border-blue-700 rounded p-2 mb-3 text-xs">
          <p className="text-blue-400 font-bold text-xs mb-1">Estrutura:</p>
          <div className="grid grid-cols-2 gap-1 text-blue-300 text-xs">
            <div>1ª: R$47.90 | 2ª: R$37.90</div>
            <div>3ª: R$27.90 | 4ª: R$20.90</div>
            <div>5ª+: R$17.90 (mín)</div>
          </div>
        </div>
      </div>

      {/* PRÓXIMA CADEIRA - COMPACTA NO MOBILE */}
      {quantidadeCadeiras < 20 && (
        <div className="bg-orange-900/20 border border-orange-700 rounded p-2 mb-2 sm:p-3 sm:mb-3">
          <p className="text-orange-400 font-bold text-xs sm:text-sm mb-1">Próxima cadeira:</p>
          <div className="flex gap-2 items-center justify-between">
            <div className="text-xs sm:text-sm">
              <p className="text-zinc-300">Mensalidade: <span className="font-bold text-orange-400">{formatarMoeda(proximoDetalhamento.total)}</span></p>
              <p className="text-zinc-400 text-xs">+{formatarMoeda(incrementoProxima)}/mês</p>
            </div>
            <button
              onClick={() => handleMais()}
              className="px-2 sm:px-3 py-1 sm:py-2 bg-orange-600 hover:bg-orange-700 text-white rounded font-bold text-xs sm:text-sm whitespace-nowrap active:scale-95 transition"
            >
              +1
            </button>
          </div>
        </div>
      )}

      {/* BOTÃO DE CONFIRMAÇÃO */}
      <div className="bg-zinc-900/50 border border-zinc-800 rounded-lg p-2 sm:p-3 md:p-4 mb-3 sm:mb-4">
        <p className="text-xs sm:text-sm font-bold text-white mb-2">Forma de pagamento</p>
        <div className="grid grid-cols-2 gap-2 mb-2">
          <button
            type="button"
            onClick={() => {
              salvarMetodoPreferidoCliente && salvarMetodoPreferidoCliente('pix');
              setMetodoPagamento('pix');
            }}
            className={`rounded px-3 py-2 text-xs sm:text-sm font-bold border transition ${metodoPagamento === 'pix' ? 'bg-orange-600/20 border-orange-500 text-orange-300' : 'bg-zinc-800 border-zinc-700 text-zinc-300 hover:bg-zinc-700'}`}
          >
            PIX
          </button>
          <button
            type="button"
            onClick={() => {
              salvarMetodoPreferidoCliente && salvarMetodoPreferidoCliente('cartao_credito');
              setMetodoPagamento('cartao');
            }}
            className={`rounded px-3 py-2 text-xs sm:text-sm font-bold border transition ${metodoPagamento === 'cartao' ? 'bg-blue-600/20 border-blue-500 text-blue-300' : 'bg-zinc-800 border-zinc-700 text-zinc-300 hover:bg-zinc-700'}`}
          >
            Cartao
          </button>
        </div>

        {metodoPagamento === 'cartao' && (
          <div className="space-y-2 bg-zinc-800/40 border border-zinc-700 rounded p-2 sm:p-3">
            <div className="grid grid-cols-2 gap-2">
              <button
                type="button"
                onClick={() => setTipoCartao('cartao_credito')}
                className={`rounded py-2 text-xs sm:text-sm font-bold border transition ${tipoCartao === 'cartao_credito' ? 'bg-blue-600/20 border-blue-500 text-blue-300' : 'bg-zinc-800 border-zinc-700 text-zinc-300 hover:bg-zinc-700'}`}
              >
                Credito
              </button>
              <button
                type="button"
                onClick={() => setTipoCartao('cartao_debito')}
                className={`rounded py-2 text-xs sm:text-sm font-bold border transition ${tipoCartao === 'cartao_debito' ? 'bg-indigo-600/20 border-indigo-500 text-indigo-300' : 'bg-zinc-800 border-zinc-700 text-zinc-300 hover:bg-zinc-700'}`}
              >
                Debito
              </button>
            </div>

            <input
              type="text"
              placeholder="Numero do cartao"
              value={cartao.numero_cartao}
              onChange={(e) => setCartao({ ...cartao, numero_cartao: e.target.value.replace(/\D/g, '').slice(0, 19) })}
              className="w-full bg-zinc-900 border border-zinc-700 rounded px-3 py-2 text-xs sm:text-sm text-white outline-none focus:border-orange-500"
            />
            <input
              type="text"
              placeholder="Nome no cartao"
              value={cartao.titular}
              onChange={(e) => setCartao({ ...cartao, titular: e.target.value.toUpperCase() })}
              className="w-full bg-zinc-900 border border-zinc-700 rounded px-3 py-2 text-xs sm:text-sm text-white outline-none focus:border-orange-500"
            />
            <div className="grid grid-cols-2 gap-2">
              <input
                type="text"
                placeholder="MM/AA"
                value={cartao.validade}
                onChange={(e) => setCartao({ ...cartao, validade: e.target.value.slice(0, 5) })}
                className="w-full bg-zinc-900 border border-zinc-700 rounded px-3 py-2 text-xs sm:text-sm text-white outline-none focus:border-orange-500"
              />
              <input
                type="text"
                placeholder="CVV"
                value={cartao.cvv}
                onChange={(e) => setCartao({ ...cartao, cvv: e.target.value.replace(/\D/g, '').slice(0, 4) })}
                className="w-full bg-zinc-900 border border-zinc-700 rounded px-3 py-2 text-xs sm:text-sm text-white outline-none focus:border-orange-500"
              />
            </div>
          </div>
        )}
      </div>

      <button
        onClick={handleConfirmar}
        disabled={loading || processandoPagamento}
        className="w-full bg-gradient-to-r from-orange-600 to-orange-700 hover:from-orange-700 hover:to-orange-800 disabled:from-zinc-700 disabled:to-zinc-700 text-white font-bold py-2 px-3 sm:py-3 sm:px-4 rounded transition active:scale-95 flex items-center justify-center gap-2 text-xs sm:text-base mb-2 sm:mb-3"
      >
        {loading ? (
          <>
            <div className="w-3 h-3 sm:w-4 sm:h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
            <span>{metodoPagamento === 'pix' ? 'Gerando PIX...' : 'Processando cartao...'}</span>
          </>
        ) : (
          <>
            <Check className="w-3 h-3 sm:w-4 sm:h-4" />
            <span>
              {metodoPagamento === 'pix'
                ? `Gerar PIX (${quantidadeCadeiras})`
                : `Pagar com ${tipoCartao === 'cartao_debito' ? 'Debito' : 'Credito'} (${quantidadeCadeiras})`}
            </span>
          </>
        )}
      </button>

      {pixData && (
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

      {/* RODAPÉ */}
      <p className="text-zinc-500 text-xs text-center mt-2 leading-tight pb-4">
        Cobrança mensal no 1º dia útil. Cancele a qualquer momento.
      </p>
      </div>
    </div>
  );
}
