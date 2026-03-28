import React, { useState } from 'react';
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
  const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';
  
  const [metodoPagamento, setMetodoPagamento] = useState('pix');
  const [processando, setProcessando] = useState(false);
  const [pixData, setPixData] = useState(null);
  const [cartao, setCartao] = useState({ numero_cartao: '', titular: '', validade: '', cvv: '' });

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
      setPixData(await res.json());
    } catch (err) {
      alert(`Erro: ${err.message}`);
    } finally {
      setProcessando(false);
    }
  };

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
              <button
                onClick={gerarPix}
                disabled={processando}
                className="w-full bg-zinc-800 hover:bg-zinc-700 text-white font-bold py-2 rounded"
              >
                Gerar QR PIX
              </button>

              {pixData && (
                <div className="bg-zinc-800 rounded p-3">
                  <div className="flex justify-center mb-2">
                    <img src={`data:image/png;base64,${pixData.qrcode_base64}`} alt="PIX" className="w-40 h-40 bg-white p-1 rounded" />
                  </div>
                  <input
                    readOnly
                    value={pixData.pix_copia_cola || ''}
                    className="w-full bg-zinc-900 border border-zinc-700 rounded p-2 text-xs text-white"
                  />
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
