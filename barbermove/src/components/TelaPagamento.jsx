// --- ARQUIVO: barbermove/src/components/TelaPagamento.jsx ---
// Componente para processar pagamentos (PIX/Cartão)

import React, { useState, useEffect } from 'react';
import { AlertCircle, CheckCircle, Copy, Loader, CreditCard, QrCode } from 'lucide-react';

export default function TelaPagamento({ chamadoId, valor, onPago }) {
  const [etapa, setEtapa] = useState('metodo'); // 'metodo', 'pix', 'cartao', 'confirmacao'
  const [metodo, setMetodo] = useState(null);
  const [pagamentoId, setPagamentoId] = useState(null);
  const [qrcode, setQrcode] = useState(null);
  const [copiaCola, setCopiaCola] = useState(null);
  const [loading, setLoading] = useState(false);
  const [mensagem, setMensagem] = useState('');
  const [cupom, setCupom] = useState('');
  const [cupomAplicado, setCupomAplicado] = useState(false);
  const [valorComDesconto, setValorComDesconto] = useState(valor);

  // Dados cartão
  const [cartao, setCartao] = useState({
    numero: '',
    titular: '',
    validade: '',
    cvv: ''
  });

  const criarPagamento = async (metodoSelecionado) => {
    setLoading(true);
    try {
      const response = await fetch(`${import.meta.env.VITE_API_URL}/api/v1/pagamentos/criar`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${localStorage.getItem('token')}`
        },
        body: JSON.stringify({
          chamado_id: chamadoId,
          metodo: metodoSelecionado,
          cupom_codigo: cupom || null
        })
      });

      if (response.ok) {
        const data = await response.json();
        setPagamentoId(data.id);
        setValorComDesconto(data.valor_final);
        setMetodo(metodoSelecionado);

        if (metodoSelecionado === 'pix') {
          await gerarPix(data.id);
        } else {
          setEtapa('cartao');
        }
      }
    } catch (err) {
      setMensagem('Erro ao criar pagamento');
    }
    setLoading(false);
  };

  const gerarPix = async (pagId) => {
    try {
      const response = await fetch(`${import.meta.env.VITE_API_URL}/api/v1/pagamentos/pix`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${localStorage.getItem('token')}`
        },
        body: JSON.stringify({ pagamento_id: pagId })
      });

      if (response.ok) {
        const data = await response.json();
        setQrcode(data.qrcode);
        setCopiaCola(data.copia_cola);
        setEtapa('pix');
      }
    } catch (err) {
      setMensagem('Erro ao gerar PIX');
    }
  };

  const copiarPix = () => {
    navigator.clipboard.writeText(copiaCola);
    setMensagem('PIX copiado!');
    setTimeout(() => setMensagem(''), 2000);
  };

  const aplicarCupom = async () => {
    if (!cupom) return;
    // Validar cupom
    setMensagem('Cupom aplicado com sucesso!');
    setCupomAplicado(true);
  };

  const confirmarPagamento = async () => {
    setLoading(true);
    try {
      const response = await fetch(`${import.meta.env.VITE_API_URL}/api/v1/pagamentos/confirmar`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${localStorage.getItem('token')}`
        },
        body: JSON.stringify({
          pagamento_id: pagamentoId
        })
      });

      if (response.ok) {
        setEtapa('confirmacao');
        setTimeout(() => onPago && onPago(), 2000);
      }
    } catch (err) {
      setMensagem('Erro ao confirmar pagamento');
    }
    setLoading(false);
  };

  return (
    <div className="bg-zinc-900 rounded-3xl p-8 border border-zinc-800 max-w-xl mx-auto">
      <h2 className="text-2xl font-bold text-white mb-8">Pagamento</h2>

      {/* Resumo do serviço */}
      <div className="bg-zinc-800 rounded-xl p-4 mb-6 border border-zinc-700">
        <div className="flex justify-between mb-2">
          <span className="text-zinc-400">Valor do serviço:</span>
          <span className="text-white font-bold">R$ {valor.toFixed(2)}</span>
        </div>
        {cupomAplicado && (
          <div className="flex justify-between mb-2">
            <span className="text-zinc-400">Desconto:</span>
            <span className="text-green-500 font-bold">- R$ {(valor - valorComDesconto).toFixed(2)}</span>
          </div>
        )}
        <div className="border-t border-zinc-700 pt-2 flex justify-between">
          <span className="text-white font-bold">Total:</span>
          <span className="text-white font-bold text-lg">R$ {valorComDesconto.toFixed(2)}</span>
        </div>
      </div>

      {etapa === 'metodo' && (
        <div className="space-y-4">
          {/* Cupom */}
          <div className="flex gap-2 mb-6">
            <input
              type="text"
              placeholder="Código do cupom"
              className="flex-1 bg-zinc-800 text-white px-4 py-2 rounded-lg border border-zinc-700 focus:border-blue-500 outline-none"
              value={cupom}
              onChange={(e) => setCupom(e.target.value)}
            />
            <button
              onClick={aplicarCupom}
              className="bg-blue-600 hover:bg-blue-700 text-white px-6 py-2 rounded-lg transition"
            >
              Aplicar
            </button>
          </div>

          <p className="text-zinc-400 mb-4">Escolha o método de pagamento:</p>

          {/* Opção PIX */}
          <button
            onClick={() => criarPagamento('pix')}
            disabled={loading}
            className="w-full bg-gradient-to-r from-purple-600 to-blue-600 hover:from-purple-700 hover:to-blue-700 text-white font-bold py-4 rounded-xl transition flex items-center justify-between px-6 disabled:opacity-50"
          >
            <div className="flex items-center gap-3">
              <QrCode size={24} />
              <span>Pagar com PIX</span>
            </div>
            <span className="text-lg">→</span>
          </button>

          {/* Opção Cartão */}
          <button
            onClick={() => criarPagamento('cartao')}
            disabled={loading}
            className="w-full bg-gradient-to-r from-green-600 to-emerald-600 hover:from-green-700 hover:to-emerald-700 text-white font-bold py-4 rounded-xl transition flex items-center justify-between px-6 disabled:opacity-50"
          >
            <div className="flex items-center gap-3">
              <CreditCard size={24} />
              <span>Cartão de Crédito</span>
            </div>
            <span className="text-lg">→</span>
          </button>

          {/* Opção Dinheiro */}
          <button
            onClick={() => {
              setMetodo('dinheiro');
              setEtapa('confirmacao');
            }}
            className="w-full bg-gradient-to-r from-orange-600 to-red-600 hover:from-orange-700 hover:to-red-700 text-white font-bold py-4 rounded-xl transition flex items-center justify-between px-6"
          >
            <div className="flex items-center gap-3">
              <span>💵</span>
              <span>Pagar em Dinheiro</span>
            </div>
            <span className="text-lg">→</span>
          </button>
        </div>
      )}

      {etapa === 'pix' && qrcode && (
        <div className="space-y-6 text-center">
          <div className="bg-white rounded-xl p-4 inline-block">
            <img src={qrcode} alt="QR Code PIX" className="w-64 h-64" />
          </div>

          <p className="text-zinc-400">Escaneie o QR code ou copie o código abaixo:</p>

          <div className="bg-zinc-800 rounded-xl p-4 border border-zinc-700">
            <p className="text-xs text-zinc-400 mb-2">Copiar para colar:</p>
            <div className="flex gap-2 items-center">
              <input
                type="text"
                value={copiaCola}
                readOnly
                className="flex-1 bg-zinc-700 text-white text-xs p-2 rounded font-mono overflow-hidden"
              />
              <button
                onClick={copiarPix}
                className="bg-blue-600 hover:bg-blue-700 text-white p-2 rounded transition"
              >
                <Copy size={20} />
              </button>
            </div>
          </div>

          <p className="text-yellow-500 flex items-center gap-2">
            <AlertCircle size={20} />
            Após pagar, clique em confirmar pagamento
          </p>

          <button
            onClick={confirmarPagamento}
            className="w-full bg-green-600 hover:bg-green-700 text-white font-bold py-3 rounded-xl transition"
          >
            Confirmar Pagamento Realizado
          </button>
        </div>
      )}

      {etapa === 'cartao' && (
        <div className="space-y-4">
          <input
            type="text"
            placeholder="Número do Cartão"
            maxLength="16"
            className="w-full bg-zinc-800 text-white px-4 py-3 rounded-xl border border-zinc-700 focus:border-blue-500 outline-none"
            value={cartao.numero}
            onChange={(e) => setCartao(prev => ({ ...prev, numero: e.target.value }))}
          />
          <input
            type="text"
            placeholder="Nome do Titular"
            className="w-full bg-zinc-800 text-white px-4 py-3 rounded-xl border border-zinc-700 focus:border-blue-500 outline-none"
            value={cartao.titular}
            onChange={(e) => setCartao(prev => ({ ...prev, titular: e.target.value }))}
          />
          <div className="grid grid-cols-2 gap-4">
            <input
              type="text"
              placeholder="MM/YY"
              maxLength="5"
              className="bg-zinc-800 text-white px-4 py-3 rounded-xl border border-zinc-700 focus:border-blue-500 outline-none"
              value={cartao.validade}
              onChange={(e) => setCartao(prev => ({ ...prev, validade: e.target.value }))}
            />
            <input
              type="text"
              placeholder="CVV"
              maxLength="4"
              className="bg-zinc-800 text-white px-4 py-3 rounded-xl border border-zinc-700 focus:border-blue-500 outline-none"
              value={cartao.cvv}
              onChange={(e) => setCartao(prev => ({ ...prev, cvv: e.target.value }))}
            />
          </div>

          <div className="flex gap-4">
            <button
              onClick={() => setEtapa('metodo')}
              className="flex-1 bg-zinc-800 hover:bg-zinc-700 text-white font-bold py-3 rounded-xl transition"
            >
              Voltar
            </button>
            <button
              onClick={confirmarPagamento}
              className="flex-1 bg-green-600 hover:bg-green-700 text-white font-bold py-3 rounded-xl transition"
            >
              Pagar R$ {valorComDesconto.toFixed(2)}
            </button>
          </div>
        </div>
      )}

      {etapa === 'confirmacao' && (
        <div className="text-center space-y-4">
          <CheckCircle size={64} className="mx-auto text-green-500 animate-bounce" />
          <h3 className="text-xl font-bold text-white">Pagamento Confirmado! ✓</h3>
          <p className="text-zinc-400">Seu serviço foi agendado com sucesso.</p>
        </div>
      )}

      {mensagem && (
        <div className="mt-4 bg-blue-600 border border-blue-500 rounded-xl p-3">
          <p className="text-white text-sm">{mensagem}</p>
        </div>
      )}
    </div>
  );
}
