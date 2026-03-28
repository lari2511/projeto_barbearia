import React, { useEffect, useState, useCallback } from 'react';
import { Copy, Check, CreditCard, Banknote, QrCode, ArrowDownCircle, AlertCircle, Loader } from 'lucide-react';

export default function TelaPagamentoNova({ chamadoId, valor, userType, token, onPago, onNotify }) {
  const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

  const [step, setStep] = useState('selecionar');
  const [loading, setLoading] = useState(false);
  const [copiado, setCopiado] = useState(false);
  const [pagamentoId, setPagamentoId] = useState(null);
  const [tipoCartao, setTipoCartao] = useState('credito');
  const [pixData, setPixData] = useState(null);

  const [cartao, setCartao] = useState({
    numero: '',
    titular: '',
    validade: '',
    cvv: ''
  });

  const [saque, setSaque] = useState({
    banco: '',
    agencia: '',
    conta: '',
    tipo_conta: 'corrente'
  });

  const [saldo, setSaldo] = useState(0);

  const carregarSaldo = useCallback(async () => {
    try {
      const res = await fetch(`${API_URL}/api/v1/usuarios/saldo`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      if (res.ok) {
        const data = await res.json();
        setSaldo(data.saldo || 0);
      }
    } catch (err) {
      console.error('Erro ao carregar saldo:', err);
    }
  }, [API_URL, token]);

  useEffect(() => {
    carregarSaldo();
  }, [carregarSaldo]);

  const copiarParaClipboard = (texto) => {
    navigator.clipboard.writeText(texto || '');
    setCopiado(true);
    setTimeout(() => setCopiado(false), 2000);
    onNotify?.('Copiado!', 'success');
  };

  const garantirPagamento = async () => {
    if (pagamentoId) return pagamentoId;

    const criarRes = await fetch(`${API_URL}/api/v1/pagamentos/criar`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${token}`
      },
      body: JSON.stringify({ chamado_id: chamadoId })
    });

    if (!criarRes.ok) {
      const err = await criarRes.json();
      throw new Error(err.detail || 'Erro ao criar pagamento');
    }

    const novoPagamento = await criarRes.json();
    setPagamentoId(novoPagamento.id);
    return novoPagamento.id;
  };

  const confirmarPagamento = async (metodo) => {
    const idPagamento = await garantirPagamento();
    const res = await fetch(`${API_URL}/api/v1/pagamentos/confirmar`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${token}`
      },
      body: JSON.stringify({ pagamento_id: idPagamento, metodo })
    });

    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || 'Erro ao confirmar pagamento');
    }

    return res.json();
  };

  const gerarPix = async () => {
    setLoading(true);
    try {
      const idPagamento = await garantirPagamento();
      const res = await fetch(`${API_URL}/api/v1/pagamentos/pix/${idPagamento}`, {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${token}`
        }
      });

      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || 'Erro ao gerar PIX');
      }

      const data = await res.json();
      setPixData(data);
      setStep('pix');
      onNotify?.('PIX gerado com sucesso', 'success');
    } catch (err) {
      onNotify?.(`Erro ao gerar PIX: ${err.message}`, 'error');
    } finally {
      setLoading(false);
    }
  };

  const processarCartao = async () => {
    setLoading(true);
    try {
      const metodo = tipoCartao === 'debito' ? 'cartao_debito' : 'cartao_credito';
      const data = await confirmarPagamento(metodo);
      setStep('confirmacao');
      onNotify?.(`Pagamento ${tipoCartao} confirmado`, 'success');
      onPago && onPago(data);
    } catch (err) {
      onNotify?.(`Erro: ${err.message}`, 'error');
    } finally {
      setLoading(false);
    }
  };

  const processarDinheiro = async () => {
    setLoading(true);
    try {
      const data = await confirmarPagamento('dinheiro');
      setStep('confirmacao');
      onNotify?.('Pagamento em dinheiro confirmado', 'success');
      onPago && onPago(data);
    } catch (err) {
      onNotify?.(`Erro: ${err.message}`, 'error');
    } finally {
      setLoading(false);
    }
  };

  const processarSaque = async () => {
    if (!saque.banco || !saque.agencia || !saque.conta) {
      onNotify?.('Preencha os dados bancarios', 'error');
      return;
    }

    const valorSaque = Math.max(50, saldo * 0.9);
    if (saldo < valorSaque) {
      onNotify?.('Saldo insuficiente', 'error');
      return;
    }

    setLoading(true);
    try {
      const res = await fetch(`${API_URL}/api/v1/saques/solicitar`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`
        },
        body: JSON.stringify({
          valor: valorSaque,
          banco: saque.banco,
          agencia: saque.agencia,
          conta: saque.conta,
          tipo_conta: saque.tipo_conta
        })
      });

      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || 'Erro ao solicitar saque');
      }

      setStep('confirmacao');
      onNotify?.('Saque solicitado com sucesso', 'success');
      setSaque({ banco: '', agencia: '', conta: '', tipo_conta: 'corrente' });
      carregarSaldo();
    } catch (err) {
      onNotify?.(`Erro: ${err.message}`, 'error');
    } finally {
      setLoading(false);
    }
  };

  const valores = {
    pix: valor,
    cartao: valor,
    dinheiro: valor,
    saque: Math.max(50, saldo * 0.9)
  };

  if (step === 'selecionar') {
    return (
      <div className="space-y-4 p-4">
        <h2 className="text-xl font-bold text-white mb-4">Escolha a forma de pagamento</h2>

        <button
          onClick={gerarPix}
          disabled={loading}
          className="w-full bg-gradient-to-r from-orange-500 to-orange-600 hover:from-orange-600 hover:to-orange-700 disabled:opacity-50 p-4 rounded-lg text-white font-bold flex items-center justify-between active:scale-95 transition"
        >
          <div className="flex items-center gap-3">
            <QrCode size={24} />
            <div className="text-left">
              <div className="font-bold">PIX</div>
              <div className="text-xs opacity-90">Transferencia instantanea</div>
            </div>
          </div>
          <div className="text-lg font-bold">R$ {valores.pix.toFixed(2)}</div>
        </button>

        <button
          onClick={() => {
            setTipoCartao('credito');
            setStep('cartao');
          }}
          disabled={loading}
          className="w-full bg-gradient-to-r from-blue-500 to-blue-600 hover:from-blue-600 hover:to-blue-700 disabled:opacity-50 p-4 rounded-lg text-white font-bold flex items-center justify-between active:scale-95 transition"
        >
          <div className="flex items-center gap-3">
            <CreditCard size={24} />
            <div className="text-left">
              <div className="font-bold">Cartao de Credito</div>
              <div className="text-xs opacity-90">Pagamento no credito</div>
            </div>
          </div>
          <div className="text-lg font-bold">R$ {valores.cartao.toFixed(2)}</div>
        </button>

        <button
          onClick={() => {
            setTipoCartao('debito');
            setStep('cartao');
          }}
          disabled={loading}
          className="w-full bg-gradient-to-r from-indigo-500 to-indigo-600 hover:from-indigo-600 hover:to-indigo-700 disabled:opacity-50 p-4 rounded-lg text-white font-bold flex items-center justify-between active:scale-95 transition"
        >
          <div className="flex items-center gap-3">
            <CreditCard size={24} />
            <div className="text-left">
              <div className="font-bold">Cartao de Debito</div>
              <div className="text-xs opacity-90">Debito a vista</div>
            </div>
          </div>
          <div className="text-lg font-bold">R$ {valores.cartao.toFixed(2)}</div>
        </button>

        {userType !== 'cliente' && (
          <button
            onClick={processarDinheiro}
            disabled={loading}
            className="w-full bg-gradient-to-r from-green-500 to-green-600 hover:from-green-600 hover:to-green-700 disabled:opacity-50 p-4 rounded-lg text-white font-bold flex items-center justify-between active:scale-95 transition"
          >
            <div className="flex items-center gap-3">
              <Banknote size={24} />
              <div className="text-left">
                <div className="font-bold">Dinheiro</div>
                <div className="text-xs opacity-90">Pagamento na entrega</div>
              </div>
            </div>
            <div className="text-lg font-bold">R$ {valores.dinheiro.toFixed(2)}</div>
          </button>
        )}

        {userType === 'barbeiro' && (
          <button
            onClick={() => setStep('saque')}
            className="w-full bg-gradient-to-r from-purple-500 to-purple-600 hover:from-purple-600 hover:to-purple-700 p-4 rounded-lg text-white font-bold flex items-center justify-between active:scale-95 transition"
          >
            <div className="flex items-center gap-3">
              <ArrowDownCircle size={24} />
              <div className="text-left">
                <div className="font-bold">Sacar para conta</div>
                <div className="text-xs opacity-90">Saldo disponivel: R$ {saldo.toFixed(2)}</div>
              </div>
            </div>
            {saldo > 0 && <div className="text-lg font-bold">R$ {Math.max(50, saldo * 0.9).toFixed(2)}</div>}
          </button>
        )}
      </div>
    );
  }

  if (step === 'pix' && pixData) {
    return (
      <div className="space-y-4 p-4">
        <button onClick={() => setStep('selecionar')} className="text-orange-400 font-bold mb-4">
          Voltar
        </button>

        <h2 className="text-xl font-bold text-white">PIX</h2>

        {pixData.qrcode_base64 && (
          <div className="bg-white p-4 rounded-lg flex justify-center">
            <img src={`data:image/png;base64,${pixData.qrcode_base64}`} alt="QR Code PIX" className="w-48 h-48" />
          </div>
        )}

        <div className="bg-zinc-900 border border-zinc-800 rounded-lg p-4">
          <p className="text-zinc-400 text-xs mb-2">Copie o codigo:</p>
          <div className="flex gap-2">
            <input type="text" value={pixData.pix_copia_cola || ''} readOnly className="flex-1 bg-black border border-zinc-800 rounded p-3 text-white text-xs font-mono" />
            <button onClick={() => copiarParaClipboard(pixData.pix_copia_cola)} className={`${copiado ? 'bg-green-600' : 'bg-orange-500'} text-white px-4 rounded font-bold transition`}>
              {copiado ? <Check size={18} /> : <Copy size={18} />}
            </button>
          </div>
        </div>

        <div className="bg-blue-900/20 border border-blue-600 rounded-lg p-3 flex gap-2">
          <AlertCircle size={18} className="text-blue-400 flex-shrink-0 mt-0.5" />
          <div className="text-sm text-blue-300">Depois de pagar no banco, confirme abaixo.</div>
        </div>

        <button
          onClick={async () => {
            setLoading(true);
            try {
              const data = await confirmarPagamento('pix');
              setStep('confirmacao');
              onNotify?.('Pagamento PIX confirmado', 'success');
              onPago && onPago(data);
            } catch (err) {
              onNotify?.(`Erro: ${err.message}`, 'error');
            } finally {
              setLoading(false);
            }
          }}
          disabled={loading}
          className="w-full bg-green-600 hover:bg-green-700 disabled:opacity-50 text-white font-bold py-3 rounded-lg active:scale-95"
        >
          Confirmar pagamento
        </button>
      </div>
    );
  }

  if (step === 'cartao') {
    return (
      <div className="space-y-4 p-4">
        <button onClick={() => setStep('selecionar')} className="text-orange-400 font-bold mb-4">
          Voltar
        </button>

        <h2 className="text-xl font-bold text-white">Dados do cartao ({tipoCartao})</h2>

        <input
          type="text"
          placeholder="Numero do cartao"
          value={cartao.numero}
          onChange={(e) => setCartao({ ...cartao, numero: e.target.value.replace(/\D/g, '').slice(0, 16) })}
          className="w-full bg-zinc-900 border border-zinc-800 rounded p-3 text-white"
        />

        <input
          type="text"
          placeholder="Nome do titular"
          value={cartao.titular}
          onChange={(e) => setCartao({ ...cartao, titular: e.target.value.toUpperCase() })}
          className="w-full bg-zinc-900 border border-zinc-800 rounded p-3 text-white"
        />

        <div className="flex gap-3">
          <input
            type="text"
            placeholder="MM/AA"
            value={cartao.validade}
            onChange={(e) => setCartao({ ...cartao, validade: e.target.value })}
            className="flex-1 bg-zinc-900 border border-zinc-800 rounded p-3 text-white"
          />
          <input
            type="text"
            placeholder="CVV"
            value={cartao.cvv}
            onChange={(e) => setCartao({ ...cartao, cvv: e.target.value })}
            className="flex-1 bg-zinc-900 border border-zinc-800 rounded p-3 text-white"
          />
        </div>

        <button
          onClick={processarCartao}
          disabled={loading || !cartao.numero || !cartao.titular || !cartao.validade || !cartao.cvv}
          className="w-full bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-white font-bold py-3 rounded-lg active:scale-95 flex items-center justify-center gap-2"
        >
          {loading ? (
            <>
              <Loader size={18} className="animate-spin" />
              Processando...
            </>
          ) : (
            `Pagar R$ ${valores.cartao.toFixed(2)}`
          )}
        </button>
      </div>
    );
  }

  if (step === 'saque') {
    return (
      <div className="space-y-4 p-4">
        <button onClick={() => setStep('selecionar')} className="text-orange-400 font-bold mb-4">
          Voltar
        </button>

        <h2 className="text-xl font-bold text-white">Solicitar saque</h2>

        <div className="bg-purple-900/20 border border-purple-600 rounded-lg p-4">
          <p className="text-purple-300 text-sm">
            Saldo disponivel: <span className="font-bold text-lg">R$ {saldo.toFixed(2)}</span>
          </p>
          <p className="text-purple-300 text-xs mt-1">Taxa de 10% no saque</p>
        </div>

        <select value={saque.banco} onChange={(e) => setSaque({ ...saque, banco: e.target.value })} className="w-full bg-zinc-900 border border-zinc-800 rounded p-3 text-white">
          <option value="">Selecione o banco</option>
          <option value="001">Banco do Brasil</option>
          <option value="033">Santander</option>
          <option value="104">Caixa</option>
          <option value="341">Itau</option>
          <option value="237">Bradesco</option>
          <option value="260">Nubank</option>
        </select>

        <input type="text" placeholder="Agencia" value={saque.agencia} onChange={(e) => setSaque({ ...saque, agencia: e.target.value })} className="w-full bg-zinc-900 border border-zinc-800 rounded p-3 text-white" />
        <input type="text" placeholder="Conta" value={saque.conta} onChange={(e) => setSaque({ ...saque, conta: e.target.value })} className="w-full bg-zinc-900 border border-zinc-800 rounded p-3 text-white" />

        <select value={saque.tipo_conta} onChange={(e) => setSaque({ ...saque, tipo_conta: e.target.value })} className="w-full bg-zinc-900 border border-zinc-800 rounded p-3 text-white">
          <option value="corrente">Conta corrente</option>
          <option value="poupanca">Conta poupanca</option>
        </select>

        <button onClick={processarSaque} disabled={loading || saldo < 50} className="w-full bg-purple-600 hover:bg-purple-700 disabled:opacity-50 text-white font-bold py-3 rounded-lg active:scale-95 flex items-center justify-center gap-2">
          {loading ? (
            <>
              <Loader size={18} className="animate-spin" />
              Solicitando...
            </>
          ) : (
            `Sacar R$ ${Math.max(50, saldo * 0.9).toFixed(2)}`
          )}
        </button>
      </div>
    );
  }

  if (step === 'confirmacao') {
    return (
      <div className="space-y-4 p-4 text-center">
        <div className="text-5xl mb-4">OK</div>
        <h2 className="text-2xl font-bold text-green-400">Pronto!</h2>
        <p className="text-zinc-300">Seu pagamento foi processado com sucesso.</p>
        <button
          onClick={() => {
            setStep('selecionar');
            onPago && onPago();
          }}
          className="w-full bg-orange-600 hover:bg-orange-700 text-white font-bold py-3 rounded-lg active:scale-95"
        >
          Fechar
        </button>
      </div>
    );
  }

  return null;
}
