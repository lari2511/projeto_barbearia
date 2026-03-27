import React, { useEffect, useState, useCallback } from 'react';
import { CreditCard, Calendar, AlertTriangle, CheckCircle, Loader, TrendingUp } from 'lucide-react';

export default function TelaAssinaturaBarbearia({ token, onNotify }) {
  const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';
  const DEBUG_PIX = Boolean(import.meta.env.DEV);

  const normalizarPixPayload = (data) => {
    const payload = data?.pix || data?.dados_pix || data || {};
    return {
      ...payload,
      qrcode_base64:
        payload.qrcode_base64 ||
        payload.qr_code_base64 ||
        payload.qrcode ||
        payload.qr_code ||
        payload.qrCodeBase64 ||
        null,
      pix_copia_cola:
        payload.pix_copia_cola ||
        payload.codigo_pix ||
        payload.copia_cola ||
        payload.emv ||
        '',
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
  const [copiado, setCopiado] = useState(false);
  const [cartao, setCartao] = useState({
    numero_cartao: '',
    titular: '',
    validade: '',
    cvv: ''
  });

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

      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || 'Erro ao processar assinatura');
      }

      onNotify?.(`Assinatura ${assinatura ? 'atualizada' : 'contratada'} com sucesso!`, 'success');
      await carregarDados();
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
      if (DEBUG_PIX) {
        console.debug('[PIX][assinatura-barbearia] resposta bruta:', data);
      }
      const pixNormalizado = normalizarPixPayload(data);
      if (DEBUG_PIX) {
        console.debug('[PIX][assinatura-barbearia] resposta normalizada:', pixNormalizado);
      }
      if (!pixNormalizado.qrcode_base64 && !pixNormalizado.pix_copia_cola) {
        throw new Error('PIX gerado sem QR Code e sem codigo copia e cola');
      }
      setPixData(pixNormalizado);
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

  return (
    <div className="space-y-6 p-4 md:p-6 max-w-4xl mx-auto">
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
              className="w-full bg-white text-orange-600 font-bold py-3 rounded-lg hover:bg-gray-100 transition disabled:opacity-50"
            >
              {processandoPagamento ? 'Processando...' : 'Gerar PIX da mensalidade'}
            </button>

            {pixData && (
              <div className="bg-white text-zinc-900 rounded-lg p-4 space-y-3">
                {pixData.qrcode_base64 && (
                  <div className="flex justify-center">
                    <img
                      src={`data:image/png;base64,${pixData.qrcode_base64}`}
                      alt="QR Code PIX mensalidade"
                      className="w-44 h-44"
                    />
                  </div>
                )}
                {!pixData.qrcode_base64 && (
                  <p className="text-xs text-amber-700 font-semibold">QR Code indisponivel. Use o codigo copia e cola.</p>
                )}
                <input
                  type="text"
                  readOnly
                  value={pixData.pix_copia_cola || ''}
                  className="w-full border border-zinc-300 rounded p-2 text-xs"
                />
                <button
                  onClick={copiarPix}
                  className="w-full bg-zinc-900 text-white py-2 rounded font-bold"
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

            <div className="bg-white/10 rounded-lg p-4 space-y-3">
              <p className="font-bold">Pagamento com cartao</p>
              <div className="grid grid-cols-2 gap-2">
                <button
                  onClick={() => setMetodoPagamento('cartao_credito')}
                  className={`py-2 rounded font-bold ${metodoPagamento === 'cartao_credito' ? 'bg-blue-600 text-white' : 'bg-white text-zinc-900'}`}
                >
                  Credito
                </button>
                <button
                  onClick={() => setMetodoPagamento('cartao_debito')}
                  className={`py-2 rounded font-bold ${metodoPagamento === 'cartao_debito' ? 'bg-indigo-600 text-white' : 'bg-white text-zinc-900'}`}
                >
                  Debito
                </button>
              </div>

              <input
                type="text"
                placeholder="Numero do cartao"
                value={cartao.numero_cartao}
                onChange={(e) => setCartao({ ...cartao, numero_cartao: e.target.value })}
                className="w-full rounded p-2 text-zinc-900"
              />
              <input
                type="text"
                placeholder="Nome do titular"
                value={cartao.titular}
                onChange={(e) => setCartao({ ...cartao, titular: e.target.value.toUpperCase() })}
                className="w-full rounded p-2 text-zinc-900"
              />
              <div className="grid grid-cols-2 gap-2">
                <input
                  type="text"
                  placeholder="MM/AA"
                  value={cartao.validade}
                  onChange={(e) => setCartao({ ...cartao, validade: e.target.value })}
                  className="rounded p-2 text-zinc-900"
                />
                <input
                  type="text"
                  placeholder="CVV"
                  value={cartao.cvv}
                  onChange={(e) => setCartao({ ...cartao, cvv: e.target.value })}
                  className="rounded p-2 text-zinc-900"
                />
              </div>

              <button
                onClick={() => pagarMensalidade(cartao)}
                disabled={processandoPagamento || !cartao.numero_cartao || !cartao.titular || !cartao.validade || !cartao.cvv || (metodoPagamento !== 'cartao_credito' && metodoPagamento !== 'cartao_debito')}
                className="w-full bg-white text-orange-600 font-bold py-3 rounded-lg hover:bg-gray-100 transition disabled:opacity-50"
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
                className="w-20 bg-zinc-800 border border-zinc-700 rounded p-2 text-white text-center"
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
