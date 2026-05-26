import React, { useEffect, useState, useCallback, useRef } from 'react';
import { CreditCard, Calendar, AlertTriangle, CheckCircle, Loader, TrendingUp } from 'lucide-react';
import { getApiBaseUrl } from '../utils/api';

export default function TelaAssinaturaBarbearia({ token, onNotify }) {
  const defaultHost = typeof window !== 'undefined' ? window.location.hostname : 'localhost';
  const defaultProtocol = typeof window !== 'undefined' && window.location.protocol === 'https:' ? 'https' : 'http';
  const API_URL = import.meta.env.VITE_API_URL?.trim() || getApiBaseUrl();
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
    const camposImagem = [
      payload.qrcode_base64,
      payload.qr_code_base64,
      payload.qrCodeBase64,
      payload.qrcode,
      payload.qr_code,
      payload.imagem_qr,
      payload.imagem_qrcode,
      payload.base64,
      payload.encodedImage,
      payload.image_base64,
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
      nested.image_base64,
      cobr.qrcode_base64,
      cobr.qr_code_base64,
      cobr.qrcode,
      cobr.qr_code,
      loc.qrcode_base64,
      loc.qr_code_base64,
      loc.qrcode,
      loc.qr_code,
    ];
    const camposTexto = [
      payload.pix_copia_cola,
      payload.codigo_pix,
      payload.copia_cola,
      payload.emv,
      payload.qrcode,
      payload.qr_code,
      payload.qr,
      payload.payload,
      payload.payload_pix,
      payload.qrCode,
      transactionData.qr_code,
      transactionData.qrcode,
      transactionData.payload,
      nested.pix_copia_cola,
      nested.codigo_pix,
      nested.copia_cola,
      nested.emv,
      nested.qrcode,
      nested.qr_code,
      nested.qr,
      nested.payload,
      nested.payload_pix,
      nested.qrCode,
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
    for (const campo of camposImagem) {
      if (pareceQrEmImagem(campo)) {
        qrcodeBase64 = campo;
        break;
      }
    }

    let pixCopiaCola = '';
    for (const campo of camposTexto) {
      if (pareceCodigoPix(campo)) {
        pixCopiaCola = campo;
        break;
      }
    }
    if (!pixCopiaCola) {
      pixCopiaCola =
        camposTexto.find((item) => typeof item === 'string' && item.trim()) ||
        payload.pix_copia_cola ||
        '';
    }

    return {
      ...payload,
      qrcode_base64: qrcodeBase64,
      pix_copia_cola: pixCopiaCola,
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

  const [loading, setLoading] = useState(true);
  const [assinatura, setAssinatura] = useState(null);
  const [status, setStatus] = useState(null);
  const [cadeirasDesejadas, setCadeirasDesejadas] = useState(1);
  const [calculoPreco, setCalculoPreco] = useState(null);
  const [metodoPagamento, setMetodoPagamento] = useState('pix');
  const [processandoPagamento, setProcessandoPagamento] = useState(false);
  const [pixData, setPixData] = useState(null);
  const [pixQrFallbackSrc, setPixQrFallbackSrc] = useState('');
  const [pixQrImagemInvalida, setPixQrImagemInvalida] = useState(false);
  const [copiado, setCopiado] = useState(false);
  const pixSectionRef = useRef(null);
  const [cartao, setCartao] = useState({
    numero_cartao: '',
    titular: '',
    validade: '',
    cvv: ''
  });

  useEffect(() => {
    if (pixData && pixSectionRef.current) {
      pixSectionRef.current.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }
  }, [pixData]);

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

  useEffect(() => {
    if (import.meta.env.DEV) {
      console.log('Estado atual do pixData:', pixData);
    }
  }, [pixData]);

  const carregarDados = useCallback(async () => {
    setLoading(true);
    try {
      const statusRes = await fetch(`${API_URL}/api/v1/assinaturas/status`, {
        headers: { Authorization: `Bearer ${token}` }
      });

      if (statusRes.ok) {
        const statusData = await statusRes.json();
        setStatus(statusData);

        if (statusData.tem_assinatura) {
          const assinaturaRes = await fetch(`${API_URL}/api/v1/assinaturas/minha`, {
            headers: { Authorization: `Bearer ${token}` }
          });

          if (assinaturaRes.ok) {
            const assinaturaData = await assinaturaRes.json();
            setAssinatura(assinaturaData);
            setCadeirasDesejadas(assinaturaData.cadeiras_ativas);
          }
        }
      }
    } catch (err) {
      console.error('Erro ao carregar assinatura:', err);
      onNotify?.('Erro ao carregar dados da assinatura', 'error');
    } finally {
      setLoading(false);
    }
  }, [API_URL, onNotify, token]);

  const calcularPreco = useCallback(async (numCadeiras) => {
    try {
      const res = await fetch(`${API_URL}/api/v1/assinaturas/calcular?cadeiras=${numCadeiras}`);
      if (res.ok) {
        const data = await res.json();
        setCalculoPreco(data);
      }
    } catch (err) {
      console.error('Erro ao calcular preço:', err);
    }
  }, [API_URL]);

  useEffect(() => {
    carregarDados();
  }, [carregarDados]);

  useEffect(() => {
    if (cadeirasDesejadas >= 1 && cadeirasDesejadas <= 20) {
      calcularPreco(cadeirasDesejadas);
    }
  }, [cadeirasDesejadas, calcularPreco]);

  const contratarOuAtualizar = async () => {
    setProcessandoPagamento(true);
    try {
      const res = await fetch(`${API_URL}/api/v1/assinaturas/criar`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`
        },
        body: JSON.stringify({
          cadeiras_ativas: cadeirasDesejadas,
          metodo_pagamento: metodoPagamento
        })
      });

      const assinaturaPayload = await res.json().catch(() => ({}));

      if (!res.ok) {
        throw new Error(assinaturaPayload.detail || 'Erro ao processar assinatura');
      }

      if (assinaturaPayload?.id) {
        setAssinatura(assinaturaPayload);
      }

      if (metodoPagamento === 'pix') {
        const pixRes = await fetch(`${API_URL}/api/v1/assinaturas/pagar-mensalidade/pix`, {
          method: 'POST',
          headers: {
            Authorization: `Bearer ${token}`
          }
        });

        if (!pixRes.ok) {
          const pixErr = await pixRes.json();
          throw new Error(pixErr.detail || 'Erro ao gerar PIX da assinatura');
        }

        const pixRaw = await pixRes.json();
        if (import.meta.env.DEV) {
          console.log('Dados brutos do PIX (assinatura):', pixRaw);
        }
        const pixFinal = montarPixFinal(pixRaw);
        if (import.meta.env.DEV) {
          console.log('Dados normalizados do PIX (assinatura):', pixFinal);
        }
        if (!pixFinal.qrcode_base64 && !pixFinal.pix_copia_cola) {
          throw new Error('PIX gerado sem QR Code e sem codigo copia e cola');
        }

        setPixData(pixFinal);
        onNotify?.('PIX da assinatura gerado com sucesso', 'success');

        // Mantem o PIX visivel sem refresh imediato que pode trocar o contexto da tela.
        setStatus((prev) => {
          if (!prev) return prev;
          return {
            ...prev,
            tem_assinatura: true,
            cadeiras_ativas: assinaturaPayload?.cadeiras_ativas ?? prev.cadeiras_ativas,
            valor_mensalidade: assinaturaPayload?.valor_mensal ?? prev.valor_mensalidade,
          };
        });
      } else {
        setPixData(null);
        onNotify?.(`Assinatura ${assinatura ? 'atualizada' : 'contratada'} com sucesso!`, 'success');
        await carregarDados();
      }
    } catch (err) {
      onNotify?.(`Erro: ${err.message}`, 'error');
    } finally {
      setProcessandoPagamento(false);
    }
  };

  const pagarMensalidade = async (payloadExtra = {}) => {
    setProcessandoPagamento(true);
    try {
      const res = await fetch(`${API_URL}/api/v1/assinaturas/pagar-mensalidade`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`
        },
        body: JSON.stringify({
          metodo_pagamento: metodoPagamento,
          ...payloadExtra
        })
      });

      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || 'Erro ao processar pagamento');
      }

      const data = await res.json();
      onNotify?.(data.message || 'Pagamento confirmado!', 'success');
      setPixData(null);
      await carregarDados();
    } catch (err) {
      onNotify?.(`Erro: ${err.message}`, 'error');
    } finally {
      setProcessandoPagamento(false);
    }
  };

  const gerarPixMensalidade = async () => {
    setMetodoPagamento('pix');
    setProcessandoPagamento(true);
    try {
      const res = await fetch(`${API_URL}/api/v1/assinaturas/pagar-mensalidade/pix`, {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${token}`
        }
      });

      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || 'Erro ao gerar PIX da mensalidade');
      }

      const data = await res.json();
      if (import.meta.env.DEV) {
        console.log('Dados brutos do PIX (mensalidade):', data);
      }
      const pixFinal = montarPixFinal(data);
      if (import.meta.env.DEV) {
        console.log('Dados normalizados do PIX (mensalidade):', pixFinal);
      }
      if (!pixFinal.qrcode_base64 && !pixFinal.pix_copia_cola) {
        throw new Error('PIX gerado sem QR Code e sem codigo copia e cola');
      }
      setPixData(pixFinal);
      onNotify?.('PIX da mensalidade gerado com sucesso', 'success');
    } catch (err) {
      onNotify?.(`Erro: ${err.message}`, 'error');
    } finally {
      setProcessandoPagamento(false);
    }
  };

  const copiarPix = async () => {
    if (!pixData?.pix_copia_cola) return;
    await navigator.clipboard.writeText(pixData.pix_copia_cola);
    setCopiado(true);
    setTimeout(() => setCopiado(false), 1500);
    onNotify?.('Codigo PIX copiado', 'success');
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center p-8">
        <Loader size={32} className="animate-spin text-orange-500" />
      </div>
    );
  }

  const getStatusColor = () => {
    if (status?.bloqueada) return 'bg-red-900/20 border-red-600 text-red-300';
    if (status?.vencida) return 'bg-red-900/20 border-red-600 text-red-300';
    if (status?.dias_vencimento <= 3) return 'bg-yellow-900/20 border-yellow-600 text-yellow-300';
    if (status?.dias_vencimento <= 7) return 'bg-blue-900/20 border-blue-600 text-blue-300';
    return 'bg-green-900/20 border-green-600 text-green-300';
  };

  const pixQrSrc = getPixQrSrc(pixData?.qrcode_base64);

  return (
    <div className="relative z-10 space-y-6 p-4 md:p-6 max-w-4xl mx-auto pb-40">
      {mixedContentRisk && (
        <div className="bg-amber-900/30 border border-amber-600 text-amber-200 rounded-lg p-3 text-sm">
          Possivel bloqueio de conteudo misto: app em HTTPS e API em HTTP. Use uma API segura para evitar bloqueio do QR Code no navegador.
        </div>
      )}

      {status && (
        <div className={`${getStatusColor()} border rounded-lg p-4`}>
          <div className="flex items-start gap-3">
            {status.bloqueada || status.vencida ? (
              <AlertTriangle size={24} className="flex-shrink-0 mt-0.5" />
            ) : (
              <CheckCircle size={24} className="flex-shrink-0 mt-0.5" />
            )}
            <div className="flex-1">
              <p className="font-bold text-lg">{status.mensagem}</p>
              {status.tem_assinatura && (
                <div className="mt-2 text-sm opacity-90">
                  <p>Cadeiras ativas: {status.cadeiras_ativas}</p>
                  <p>Valor mensal: R$ {status.valor_mensalidade?.toFixed(2)}</p>
                  <p>Vencimento: {new Date(status.proximo_vencimento).toLocaleDateString('pt-BR')}</p>
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {(status?.bloqueada || status?.vencida) && (
        <div className="bg-gradient-to-r from-orange-500 to-orange-600 rounded-lg p-6 text-white shadow-lg">
          <h2 className="text-2xl font-bold mb-4">⛔ Desbloqueie sua barbearia agora!</h2>
          <p className="mb-4">Pague R$ {status.valor_mensalidade?.toFixed(2)} para continuar usando o app.</p>
          
          <div className="space-y-3 mb-4">
            <button
              onClick={gerarPixMensalidade}
              disabled={processandoPagamento}
              className="bm-primary w-full py-3 rounded-lg font-bold disabled:opacity-50"
            >
              {processandoPagamento ? 'Processando...' : 'Gerar PIX da mensalidade'}
            </button>

            {pixData && (
              <div ref={pixSectionRef} className="bg-zinc-900 text-zinc-200 rounded-lg p-4 space-y-3 ring-2 ring-orange-300/40 border border-zinc-800">
                {pixQrSrc && !pixQrImagemInvalida && (
                  <div className="flex justify-center">
                    <img
                      src={pixQrSrc}
                      alt="QR Code PIX mensalidade"
                      className="w-44 h-44"
                      onError={() => setPixQrImagemInvalida(true)}
                    />
                  </div>
                )}
                {(pixQrImagemInvalida || !pixQrSrc) && pixQrFallbackSrc && (
                  <div className="flex justify-center">
                    <img
                      src={pixQrFallbackSrc}
                      alt="QR Code PIX mensalidade"
                      className="w-44 h-44"
                    />
                  </div>
                )}
                {(pixQrImagemInvalida || !pixQrSrc) && !pixQrFallbackSrc && (
                  <p className="text-xs text-amber-700 font-semibold">QR Code indisponivel. Use o codigo copia e cola.</p>
                )}
                <input
                  type="text"
                  readOnly
                  value={pixData.pix_copia_cola || ''}
                  className="bm-input w-full border border-zinc-700 rounded p-2 text-xs bg-zinc-800 text-white"
                />
                <button
                  onClick={copiarPix}
                  className="w-full bg-zinc-800 text-zinc-200 py-2 rounded-lg font-bold border border-zinc-700"
                >
                  {copiado ? 'Copiado!' : 'Copiar codigo PIX'}
                </button>
                <button
                  onClick={() => pagarMensalidade({ confirmar_pix: true })}
                  disabled={processandoPagamento}
                  className="w-full bg-gradient-to-r from-orange-600 to-red-600 text-white py-2 rounded-2xl font-extrabold disabled:opacity-60"
                >
                  Confirmar pagamento PIX
                </button>
              </div>
            )}

            <div className="bg-zinc-900/10 rounded-lg p-4 space-y-3 border border-zinc-800">
              <p className="font-bold">Pagamento com cartao</p>
              <div className="grid grid-cols-2 gap-2">
                <button
                  onClick={() => setMetodoPagamento('cartao_credito')}
                  className={`py-2 rounded font-bold ${metodoPagamento === 'cartao_credito' ? 'bg-blue-600 text-white' : 'bg-zinc-800 text-zinc-300'}`}
                >
                  Credito
                </button>
                <button
                  onClick={() => setMetodoPagamento('cartao_debito')}
                  className={`py-2 rounded font-bold ${metodoPagamento === 'cartao_debito' ? 'bg-indigo-600 text-white' : 'bg-zinc-800 text-zinc-300'}`}
                >
                  Debito
                </button>
              </div>

              <input
                type="text"
                placeholder="Numero do cartao"
                value={cartao.numero_cartao}
                onChange={(e) => setCartao({ ...cartao, numero_cartao: e.target.value })}
                className="bm-input w-full rounded p-2 text-zinc-900"
              />
              <input
                type="text"
                placeholder="Nome do titular"
                value={cartao.titular}
                onChange={(e) => setCartao({ ...cartao, titular: e.target.value.toUpperCase() })}
                className="bm-input w-full rounded p-2 text-zinc-900"
              />
              <div className="grid grid-cols-2 gap-2">
                <input
                  type="text"
                  placeholder="MM/AA"
                  value={cartao.validade}
                  onChange={(e) => setCartao({ ...cartao, validade: e.target.value })}
                  className="bm-input rounded p-2 text-zinc-900"
                />
                <input
                  type="text"
                  placeholder="CVV"
                  value={cartao.cvv}
                  onChange={(e) => setCartao({ ...cartao, cvv: e.target.value })}
                  className="bm-input rounded p-2 text-zinc-900"
                />
              </div>

              <button
                onClick={() => pagarMensalidade(cartao)}
                disabled={processandoPagamento || !cartao.numero_cartao || !cartao.titular || !cartao.validade || !cartao.cvv || (metodoPagamento !== 'cartao_credito' && metodoPagamento !== 'cartao_debito')}
                className="w-full bg-gradient-to-r from-orange-600 to-red-600 text-white font-extrabold py-3 rounded-2xl hover:from-orange-700 hover:to-red-700 transition disabled:opacity-50"
              >
                {processandoPagamento ? 'Processando...' : 'Pagar com cartao'}
              </button>
            </div>
          </div>
        </div>
      )}

      <div className="bg-zinc-900 border border-zinc-800 rounded-lg p-6">
        <h2 className="text-xl font-bold text-white mb-4 flex items-center gap-2">
          <TrendingUp size={24} className="text-orange-500" />
          {assinatura ? 'Gerenciar Assinatura' : 'Contratar Assinatura'}
        </h2>

        <div className="space-y-4">
          <div>
            <label className="text-white font-bold mb-2 block">
              Quantas cadeiras você precisa?
            </label>
            <div className="flex items-center gap-4">
              <input
                type="range"
                min="1"
                max="20"
                value={cadeirasDesejadas}
                onChange={(e) => setCadeirasDesejadas(parseInt(e.target.value))}
                className="flex-1"
              />
              <input
                type="number"
                min="1"
                max="20"
                value={cadeirasDesejadas}
                onChange={(e) => setCadeirasDesejadas(parseInt(e.target.value))}
                className="bm-input w-20 bg-zinc-800 border border-zinc-700 rounded p-2 text-white text-center"
              />
            </div>
          </div>

          {calculoPreco && (
            <div className="bg-zinc-800 rounded-lg p-4">
              <div className="flex justify-between items-center mb-3">
                <span className="text-zinc-400">Valor total mensal:</span>
                <span className="text-3xl font-bold text-white">
                  R$ {calculoPreco.valor_total.toFixed(2)}
                </span>
              </div>
              
              {calculoPreco.economia > 0 && (
                <div className="bg-green-900/20 border border-green-600 rounded p-2 text-green-300 text-sm">
                  💰 Você economiza R$ {calculoPreco.economia.toFixed(2)} vs. preço individual
                </div>
              )}

              <div className="mt-3 pt-3 border-t border-zinc-700">
                <p className="text-xs text-zinc-500 mb-2">Detalhamento por cadeira:</p>
                {calculoPreco.breakdown.map((preco, idx) => (
                  <div key={idx} className="flex justify-between text-sm text-zinc-400 mb-1">
                    <span>{idx + 1}ª cadeira:</span>
                    <span>R$ {preco.toFixed(2)}</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          <div>
            <label className="text-white font-bold mb-2 block">
              Método de Pagamento Preferido:
            </label>
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
          </div>

          <button
            onClick={contratarOuAtualizar}
            disabled={processandoPagamento || !calculoPreco}
            className="w-full bg-gradient-to-r from-orange-500 to-orange-600 hover:from-orange-600 hover:to-orange-700 disabled:opacity-50 text-white font-bold py-4 rounded-lg transition flex items-center justify-center gap-2"
          >
            {processandoPagamento ? (
              <>
                <Loader size={20} className="animate-spin" />
                Processando...
              </>
            ) : assinatura ? (
              <>
                <CreditCard size={20} />
                Atualizar Assinatura
              </>
            ) : (
              <>
                <CheckCircle size={20} />
                Contratar por R$ {calculoPreco?.valor_total.toFixed(2)}
              </>
            )}
          </button>

          {pixData && (
            <div ref={pixSectionRef} className="bg-zinc-800 border border-zinc-700 rounded-lg p-4 space-y-3 ring-2 ring-orange-500/60">
              <p className="text-sm font-bold text-white">PIX gerado</p>
              {pixQrSrc && !pixQrImagemInvalida && (
                <div className="flex justify-center">
                  <div className="bg-zinc-800 p-2 rounded">
                    <img
                      src={pixQrSrc}
                      alt="QR Code PIX assinatura"
                      className="w-40 h-40 object-contain"
                      onError={() => setPixQrImagemInvalida(true)}
                    />
                  </div>
                </div>
              )}
              {(pixQrImagemInvalida || !pixQrSrc) && pixQrFallbackSrc && (
                <div className="flex justify-center">
                  <div className="bg-zinc-800 p-2 rounded">
                    <img
                      src={pixQrFallbackSrc}
                      alt="QR Code PIX assinatura"
                      className="w-40 h-40 object-contain"
                    />
                  </div>
                </div>
              )}
              {(pixQrImagemInvalida || !pixQrSrc) && !pixQrFallbackSrc && (
                <p className="text-xs text-amber-300 font-semibold">QR Code indisponivel. Use o codigo copia e cola.</p>
              )}
              <input
                type="text"
                readOnly
                value={pixData.pix_copia_cola || ''}
                className="w-full border border-zinc-600 bg-zinc-900 rounded p-2 text-xs text-zinc-200"
              />
              <button
                onClick={copiarPix}
                className="w-full bg-zinc-800 text-zinc-200 py-2 rounded font-bold"
              >
                {copiado ? 'Copiado!' : 'Copiar codigo PIX'}
              </button>
              <button
                onClick={() => pagarMensalidade({ confirmar_pix: true })}
                disabled={processandoPagamento}
                className="w-full bg-green-600 text-white py-2 rounded font-bold disabled:opacity-60"
              >
                Confirmar pagamento PIX
              </button>
            </div>
          )}
        </div>
      </div>

      <div className="bg-zinc-900 border border-zinc-800 rounded-lg p-6">
        <h3 className="text-lg font-bold text-white mb-4">📊 Tabela de Preços</h3>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          {[1, 2, 3, 4, 5, 10, 15, 20].map((num) => {
            const valores = [47.90, 37.90, 27.90, 20.90, 17.90];
            const minimo = 17.90;
            let total = 0;
            for (let i = 0; i < num; i++) {
              total += i < valores.length ? valores[i] : minimo;
            }
            return (
              <div key={num} className="bg-zinc-800 rounded-lg p-3 text-center">
                <div className="text-2xl font-bold text-white">{num}</div>
                <div className="text-xs text-zinc-400 mb-1">
                  {num === 1 ? 'cadeira' : 'cadeiras'}
                </div>
                <div className="text-lg font-bold text-orange-500">
                  R$ {total.toFixed(2)}
                </div>
                <div className="text-xs text-zinc-500">/mês</div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
