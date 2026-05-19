import React, { useEffect, useState } from 'react';
import { AlertTriangle, CreditCard, X, Loader } from 'lucide-react';

/**
 * Modal que aparece quando a barbearia tenta realizar uma ação
 * mas está bloqueada por inadimplência
 */
export default function ModalBloqueio({ 
  isOpen, 
  onClose, 
  statusBloqueio, 
  token,
  onPagamentoSucesso 
}) {
  const defaultHost = typeof window !== 'undefined' ? window.location.hostname : 'localhost';
  const defaultProtocol = typeof window !== 'undefined' && window.location.protocol === 'https:' ? 'https' : 'http';
  const API_URL = import.meta.env.VITE_API_URL || `${defaultProtocol}://${defaultHost}:8000`;
  const mixedContentRisk =
    typeof window !== 'undefined' &&
    window.location.protocol === 'https:' &&
    API_URL.startsWith('http://');

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

    return {
      ...payload,
      qrcode_base64: candidatosImagem.find((item) => pareceQrEmImagem(item)) || null,
      pix_copia_cola:
        candidatosTexto.find((item) => pareceCodigoPix(item)) ||
        candidatosTexto.find((item) => typeof item === 'string' && item.trim()) ||
        '',
      valor: payload.valor ?? payload.amount ?? nested.valor ?? nested.amount ?? 0,
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
  
  const [metodoPagamento, setMetodoPagamento] = useState('pix');
  const [processando, setProcessando] = useState(false);
  const [pixData, setPixData] = useState(null);
  const [pixQrFallbackSrc, setPixQrFallbackSrc] = useState('');
  const [pixQrImagemInvalida, setPixQrImagemInvalida] = useState(false);
  const [copiado, setCopiado] = useState(false);
  const [cartao, setCartao] = useState({ numero_cartao: '', titular: '', validade: '', cvv: '' });

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
        const QRCode = (await import('qrcode')).default;
        const dataUrl = await QRCode.toDataURL(pixData.pix_copia_cola, {
          width: 320,
          margin: 1,
          errorCorrectionLevel: 'M',
        });

        if (ativo) {
          setPixQrFallbackSrc(dataUrl);
        }
      } catch (err) {
        console.error('Erro ao gerar QR fallback no frontend:', err);
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

  const copiarPix = async () => {
    if (!pixData?.pix_copia_cola) return;
    await navigator.clipboard.writeText(pixData.pix_copia_cola);
    setCopiado(true);
    setTimeout(() => setCopiado(false), 1500);
  };

  if (!isOpen || !statusBloqueio) return null;

  const pagarMensalidade = async (payloadExtra = {}) => {
    setProcessando(true);
    try {
      const res = await fetch(`${API_URL}/api/v1/assinaturas/pagar-mensalidade`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`
        },
        body: JSON.stringify({ metodo_pagamento: metodoPagamento, ...payloadExtra })
      });

      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || 'Erro ao processar pagamento');
      }

      const data = await res.json();
      alert(data.message || 'Pagamento confirmado! Barbearia desbloqueada.');
      onPagamentoSucesso?.();
      onClose();
    } catch (err) {
      alert(`Erro: ${err.message}`);
    } finally {
      setProcessando(false);
    }
  };

  const gerarPix = async () => {
    setMetodoPagamento('pix');
    setProcessando(true);
    try {
      const res = await fetch(`${API_URL}/api/v1/assinaturas/pagar-mensalidade/pix`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}` }
      });
      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || 'Erro ao gerar PIX');
      }
      const data = await res.json();
      const pixFinal = montarPixFinal(data);
      if (!pixFinal.qrcode_base64 && !pixFinal.pix_copia_cola) {
        throw new Error('PIX gerado sem QR Code e sem codigo copia e cola');
      }
      setPixData(pixFinal);
    } catch (err) {
      alert(`Erro: ${err.message}`);
    } finally {
      setProcessando(false);
    }
  };

  const pixQrSrc = getPixQrSrc(pixData?.qrcode_base64);

  return (
    <div className="fixed inset-0 bg-black/80 flex items-center justify-center z-50 p-4">
      <div className="bg-zinc-900 border border-red-600 rounded-lg max-w-md w-full shadow-2xl">
        {/* Header */}
        <div className="bg-red-600 text-white p-6 rounded-t-lg">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <AlertTriangle size={32} className="animate-pulse" />
              <div>
                <h2 className="text-xl font-bold">Barbearia Bloqueada</h2>
                <p className="text-sm opacity-90">Ação não permitida</p>
              </div>
            </div>
            <button
              onClick={onClose}
              className="p-2 hover:bg-white/10 rounded transition"
            >
              <X size={24} />
            </button>
          </div>
        </div>

        {/* Content */}
        <div className="p-6 space-y-4">
          <div className="bg-red-900/20 border border-red-600 rounded-lg p-4">
            <p className="text-red-300 font-bold text-center">
              {statusBloqueio.motivo_bloqueio || 'Sua barbearia está bloqueada por inadimplência.'}
            </p>
          </div>

          {statusBloqueio.valor_mensalidade && (
            <div className="bg-zinc-800 rounded-lg p-4">
              <div className="flex justify-between items-center">
                <span className="text-zinc-400">Valor devido:</span>
                <span className="text-3xl font-bold text-white">
                  R$ {statusBloqueio.valor_mensalidade.toFixed(2)}
                </span>
              </div>
              {statusBloqueio.proximo_vencimento && (
                <p className="text-xs text-zinc-500 mt-2">
                  Vencimento: {new Date(statusBloqueio.proximo_vencimento).toLocaleDateString('pt-BR')}
                </p>
              )}
            </div>
          )}

          <div>
            <p className="text-white font-bold mb-3">Escolha a forma de pagamento:</p>
            <div className="grid grid-cols-3 gap-2">
              <button
                onClick={() => setMetodoPagamento('pix')}
                className={`p-3 rounded-lg font-bold transition ${
                  metodoPagamento === 'pix'
                    ? 'bg-orange-500 text-white'
                    : 'bg-zinc-800 text-zinc-400 hover:bg-zinc-700'
                }`}
              >
                PIX
              </button>
              <button
                onClick={() => setMetodoPagamento('cartao_credito')}
                className={`p-3 rounded-lg font-bold transition ${
                  metodoPagamento === 'cartao_credito'
                    ? 'bg-blue-500 text-white'
                    : 'bg-zinc-800 text-zinc-400 hover:bg-zinc-700'
                }`}
              >
                Crédito
              </button>
              <button
                onClick={() => setMetodoPagamento('cartao_debito')}
                className={`p-3 rounded-lg font-bold transition ${
                  metodoPagamento === 'cartao_debito'
                    ? 'bg-indigo-500 text-white'
                    : 'bg-zinc-800 text-zinc-400 hover:bg-zinc-700'
                }`}
              >
                Débito
              </button>
            </div>

            <div className="mt-3 space-y-3">
              {mixedContentRisk && (
                <div className="bg-amber-900/30 border border-amber-600 text-amber-200 rounded-lg p-3 text-xs">
                  Possivel bloqueio de conteudo misto: app em HTTPS e API em HTTP. Ajuste o VITE_API_URL para HTTPS para evitar bloqueio do QR Code no navegador.
                </div>
              )}

              <button
                onClick={gerarPix}
                disabled={processando}
                className="w-full bg-zinc-800 hover:bg-zinc-700 text-white font-bold py-2 rounded"
              >
                Gerar QR PIX
              </button>

              {pixData && (
                <div className="bg-zinc-800 rounded p-3">
                  {pixQrSrc && !pixQrImagemInvalida && (
                    <div className="flex justify-center mb-2">
                      <img src={pixQrSrc} alt="PIX" className="w-40 h-40 bg-white p-1 rounded" onError={() => setPixQrImagemInvalida(true)} />
                    </div>
                  )}
                  {(pixQrImagemInvalida || !pixQrSrc) && pixQrFallbackSrc && (
                    <div className="flex justify-center mb-2">
                      <img src={pixQrFallbackSrc} alt="PIX" className="w-40 h-40 bg-white p-1 rounded" />
                    </div>
                  )}
                  {(pixQrImagemInvalida || !pixQrSrc) && !pixQrFallbackSrc && (
                    <p className="text-xs text-yellow-300 mb-2">QR Code indisponivel. Use o codigo copia e cola.</p>
                  )}
                  <input
                    readOnly
                    value={pixData.pix_copia_cola || ''}
                    className="w-full bg-zinc-900 border border-zinc-700 rounded p-2 text-xs text-white"
                  />
                  <button
                    onClick={copiarPix}
                    className="w-full mt-2 bg-zinc-200 hover:bg-zinc-100 text-zinc-900 font-bold py-2 rounded"
                  >
                    {copiado ? 'Copiado!' : 'Copiar codigo PIX'}
                  </button>
                  <button
                    onClick={() => pagarMensalidade({ confirmar_pix: true })}
                    disabled={processando}
                    className="w-full mt-2 bg-green-600 hover:bg-green-700 disabled:opacity-50 text-white font-bold py-2 rounded"
                  >
                    Confirmar PIX
                  </button>
                </div>
              )}

              {(metodoPagamento === 'cartao_credito' || metodoPagamento === 'cartao_debito') && (
                <div className="bg-zinc-800 rounded p-3 space-y-2">
                  <input
                    type="text"
                    placeholder="Numero do cartao"
                    value={cartao.numero_cartao}
                    onChange={(e) => setCartao({ ...cartao, numero_cartao: e.target.value })}
                    className="w-full bg-zinc-900 border border-zinc-700 rounded p-2 text-white"
                  />
                  <input
                    type="text"
                    placeholder="Nome do titular"
                    value={cartao.titular}
                    onChange={(e) => setCartao({ ...cartao, titular: e.target.value.toUpperCase() })}
                    className="w-full bg-zinc-900 border border-zinc-700 rounded p-2 text-white"
                  />
                  <div className="grid grid-cols-2 gap-2">
                    <input
                      type="text"
                      placeholder="MM/AA"
                      value={cartao.validade}
                      onChange={(e) => setCartao({ ...cartao, validade: e.target.value })}
                      className="bg-zinc-900 border border-zinc-700 rounded p-2 text-white"
                    />
                    <input
                      type="text"
                      placeholder="CVV"
                      value={cartao.cvv}
                      onChange={(e) => setCartao({ ...cartao, cvv: e.target.value })}
                      className="bg-zinc-900 border border-zinc-700 rounded p-2 text-white"
                    />
                  </div>
                </div>
              )}
            </div>
          </div>

          <button
            onClick={() => pagarMensalidade(cartao)}
            disabled={processando || ((metodoPagamento === 'cartao_credito' || metodoPagamento === 'cartao_debito') && (!cartao.numero_cartao || !cartao.titular || !cartao.validade || !cartao.cvv)) || metodoPagamento === 'pix'}
            className="w-full bg-gradient-to-r from-orange-500 to-orange-600 hover:from-orange-600 hover:to-orange-700 disabled:opacity-50 text-white font-bold py-4 rounded-lg transition flex items-center justify-center gap-2"
          >
            {processando ? (
              <>
                <Loader size={20} className="animate-spin" />
                Processando pagamento...
              </>
            ) : (
              <>
                <CreditCard size={20} />
                Pagar e Desbloquear
              </>
            )}
          </button>

          <p className="text-center text-xs text-zinc-500">
            Após o pagamento, sua barbearia será desbloqueada instantaneamente.
          </p>
        </div>
      </div>
    </div>
  );
}
