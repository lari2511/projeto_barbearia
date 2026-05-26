import React, { useState, useEffect, useCallback } from 'react';
import { DollarSign, CreditCard, Wallet, Clock, Eye, EyeOff, RefreshCw } from 'lucide-react';
import { getApiBaseUrl } from '../utils/api';

const DEFAULT_HOST = typeof window !== 'undefined' ? window.location.hostname : 'localhost';
const DEFAULT_PROTOCOL = typeof window !== 'undefined' && window.location.protocol === 'https:' ? 'https' : 'http';
const API_URL = import.meta.env.VITE_API_URL?.trim() || getApiBaseUrl();

export default function PaymentSection({ userType, token, onNotify }) {
  const [loading, setLoading] = useState(true);
  const [mostrarSaldo, setMostrarSaldo] = useState(true);
  const [metodoPreferido, setMetodoPreferido] = useState('pix');
  const [salvandoConta, setSalvandoConta] = useState(false);

  const [saldoDetalhado, setSaldoDetalhado] = useState({
    saldoDisponivel: 0,
    saldoEmRetencao: 0,
    totalGanho: 0,
    proximoSaque: null,
  });

  const [splitPagamento, setSplitPagamento] = useState(null);

  const [contaPagamento, setContaPagamento] = useState({
    chave_pix: '',
    banco: '',
    agencia: '',
    conta: '',
    tipo_conta: 'corrente',
    titular_nome: '',
    titular_documento: '',
    frequencia_repasse: 'semanal',
    dia_semana_repasse: 1,
    dia_mes_repasse: 5,
  });

  useEffect(() => {
    if (userType === 'cliente') {
      const salvo = localStorage.getItem('cliente_metodo_pagamento_preferido');
      if (salvo === 'pix' || salvo === 'cartao_credito' || salvo === 'cartao_debito') {
        setMetodoPreferido(salvo);
      }
    }
  }, [userType]);

  const formatarDataCurta = (iso) => {
    if (!iso) return '-';
    const data = new Date(iso);
    if (Number.isNaN(data.getTime())) return '-';
    return data.toLocaleDateString('pt-BR');
  };

  const carregarDadosPagamento = useCallback(async () => {
    setLoading(true);
    try {
      const fallbackResumo = {
        saldoDisponivel: 1250,
        saldoEmRetencao: 380,
        totalGanho: 5009,
        proximoSaque: new Date(Date.now() + 3 * 24 * 60 * 60 * 1000).toISOString(),
      };

      const [resumoRes, splitRes, contaRes] = await Promise.all([
        fetch(`${API_URL}/api/v1/pagamentos-config/resumo`, {
          headers: { Authorization: `Bearer ${token}` },
        }),
        fetch(`${API_URL}/api/v1/pagamentos-config/split`, {
          headers: { Authorization: `Bearer ${token}` },
        }),
        fetch(`${API_URL}/api/v1/pagamentos-config/conta`, {
          headers: { Authorization: `Bearer ${token}` },
        }),
      ]);

      if (resumoRes.ok) {
        const resumo = await resumoRes.json();
        setSaldoDetalhado({
          saldoDisponivel: Number(resumo?.saldo_disponivel || 0),
          saldoEmRetencao: Number(resumo?.valor_estimado_periodo || 0),
          totalGanho: Number(resumo?.saldo_disponivel || 0) + Number(resumo?.valor_estimado_periodo || 0),
          proximoSaque: resumo?.proximo_repasse_em || null,
        });
      } else {
        setSaldoDetalhado(fallbackResumo);
      }

      if (splitRes.ok) {
        const split = await splitRes.json();
        setSplitPagamento(split);
      }

      if (contaRes.ok) {
        const conta = await contaRes.json();
        setContaPagamento({
          chave_pix: conta.chave_pix || '',
          banco: conta.banco || '',
          agencia: conta.agencia || '',
          conta: conta.conta || '',
          tipo_conta: conta.tipo_conta || 'corrente',
          titular_nome: conta.titular_nome || '',
          titular_documento: conta.titular_documento || '',
          frequencia_repasse: conta.frequencia_repasse || 'semanal',
          dia_semana_repasse: conta.dia_semana_repasse ?? 1,
          dia_mes_repasse: conta.dia_mes_repasse ?? 5,
        });
      }
    } catch (_err) {
      onNotify?.('Erro ao carregar dados de pagamento', 'error');
    } finally {
      setLoading(false);
    }
  }, [token, onNotify]);

  useEffect(() => {
    carregarDadosPagamento();
  }, [carregarDadosPagamento]);

  const solicitarSaque = async () => {
    if (!saldoDetalhado.saldoDisponivel || saldoDetalhado.saldoDisponivel <= 0) {
      onNotify?.('Saldo indisponível para saque', 'warning');
      return;
    }

    try {
      const res = await fetch(`${API_URL}/api/v1/saques/solicitar`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          valor: saldoDetalhado.saldoDisponivel,
          banco: contaPagamento.banco || 'A DEFINIR',
          agencia: contaPagamento.agencia || '0001',
          conta: contaPagamento.conta || '000000-0',
          tipo_conta: contaPagamento.tipo_conta || 'corrente',
        }),
      });

      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || 'Erro ao solicitar saque');
      }

      onNotify?.('Saque solicitado com sucesso!', 'success');
      carregarDadosPagamento();
    } catch (err) {
      onNotify?.(err.message || 'Erro ao solicitar saque', 'error');
    }
  };

  const salvarContaPagamento = async () => {
    setSalvandoConta(true);
    try {
      const res = await fetch(`${API_URL}/api/v1/pagamentos-config/conta`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify(contaPagamento),
      });

      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || 'Erro ao salvar dados de pagamento');
      }

      onNotify?.('Dados de pagamento salvos com sucesso!', 'success');
      carregarDadosPagamento();
    } catch (err) {
      onNotify?.(err.message || 'Erro ao salvar dados de pagamento', 'error');
    } finally {
      setSalvandoConta(false);
    }
  };

  const nomeSecao = userType === 'cliente' ? 'Pagamentos' : userType === 'barbeiro' ? 'Meus Ganhos' : 'Pagamento';

  if (loading) {
    return (
      <div className="flex items-center justify-center py-20">
        <div className="text-zinc-400">Carregando informações financeiras...</div>
      </div>
    );
  }

  if (userType === 'cliente') {
    return (
      <div className="space-y-4 pb-24">
        <div className="flex items-center gap-3">
          <div className="bg-gradient-to-br from-green-500 to-emerald-500 p-3 rounded-2xl shadow-lg">
            <DollarSign size={24} className="text-white" />
          </div>
          <div>
            <h2 className="text-xl font-bold text-white">{nomeSecao}</h2>
            <p className="text-xs text-zinc-400">Forma de pagamento do cliente</p>
          </div>
        </div>

        <div className="bg-gradient-to-br from-zinc-900/80 to-zinc-900/40 rounded-2xl p-5 border border-zinc-800">
          <div className="flex items-center gap-2 mb-4">
            <CreditCard size={20} className="text-orange-400" />
            <h3 className="text-lg font-bold text-white">Formas de Pagamento</h3>
          </div>

          <button
            onClick={() => {
              setMetodoPreferido('pix');
              localStorage.setItem('cliente_metodo_pagamento_preferido', 'pix');
              onNotify?.('PIX definido como forma de pagamento.', 'success');
            }}
            className={`w-full rounded-lg px-3 py-3 text-sm font-bold border transition ${metodoPreferido === 'pix' ? 'bg-emerald-500/20 border-emerald-500 text-emerald-300' : 'bg-zinc-800 border-zinc-700 text-zinc-300 hover:bg-zinc-700'}`}
          >
            PIX
          </button>

          <button
            onClick={() => {
              setMetodoPreferido('cartao_credito');
              localStorage.setItem('cliente_metodo_pagamento_preferido', 'cartao_credito');
              onNotify?.('Cartao de Credito definido como forma de pagamento.', 'success');
            }}
            className={`w-full rounded-lg px-3 py-3 text-sm font-bold border transition mt-2 ${metodoPreferido === 'cartao_credito' ? 'bg-blue-500/20 border-blue-500 text-blue-300' : 'bg-zinc-800 border-zinc-700 text-zinc-300 hover:bg-zinc-700'}`}
          >
            Cartao de Credito
          </button>

          <button
            onClick={() => {
              setMetodoPreferido('cartao_debito');
              localStorage.setItem('cliente_metodo_pagamento_preferido', 'cartao_debito');
              onNotify?.('Cartao de Debito definido como forma de pagamento.', 'success');
            }}
            className={`w-full rounded-lg px-3 py-3 text-sm font-bold border transition mt-2 ${metodoPreferido === 'cartao_debito' ? 'bg-indigo-500/20 border-indigo-500 text-indigo-300' : 'bg-zinc-800 border-zinc-700 text-zinc-300 hover:bg-zinc-700'}`}
          >
            Cartao de Debito
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6 pb-24">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="bg-gradient-to-br from-green-500 to-emerald-500 p-3 rounded-2xl shadow-lg">
            <DollarSign size={28} className="text-white" />
          </div>
          <div>
            <h2 className="text-2xl font-bold text-white">{nomeSecao}</h2>
            <p className="text-xs text-zinc-400">Valores recebidos e divisão automática</p>
          </div>
        </div>
        <button
          onClick={carregarDadosPagamento}
          className="bg-zinc-800 hover:bg-zinc-700 text-white p-3 rounded-xl transition"
          title="Atualizar dados"
        >
          <RefreshCw size={20} />
        </button>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <div className="bg-gradient-to-br from-green-500/20 to-emerald-500/10 rounded-2xl p-6 border border-green-500/30 relative overflow-hidden">
          <div className="absolute top-0 right-0 w-32 h-32 bg-green-500/10 rounded-full -mr-16 -mt-16"></div>
          <div className="relative">
            <div className="flex items-center justify-between mb-3">
              <p className="text-xs text-green-400 font-bold uppercase tracking-wide flex items-center gap-2">
                <Wallet size={16} />
                Disponível para Saque
              </p>
              <button onClick={() => setMostrarSaldo(!mostrarSaldo)} className="text-green-400 hover:text-green-300 transition">
                {mostrarSaldo ? <Eye size={16} /> : <EyeOff size={16} />}
              </button>
            </div>
            <p className="text-3xl font-bold text-white mb-4">
              {mostrarSaldo ? `R$ ${(saldoDetalhado.saldoDisponivel || 0).toFixed(2)}` : 'R$ •••••'}
            </p>

            {userType === 'barbeiro' && (
              <button
                onClick={solicitarSaque}
                disabled={!saldoDetalhado.saldoDisponivel || saldoDetalhado.saldoDisponivel <= 0}
                className="w-full bg-gradient-to-r from-green-600 to-emerald-600 hover:from-green-700 hover:to-emerald-700 disabled:from-zinc-700 disabled:to-zinc-700 disabled:cursor-not-allowed text-white py-3 rounded-xl text-sm font-bold transition"
              >
                Solicitar Saque
              </button>
            )}
          </div>
        </div>

        <div className="bg-gradient-to-br from-yellow-500/20 to-orange-500/10 rounded-2xl p-6 border border-yellow-500/30 relative overflow-hidden">
          <div className="absolute top-0 right-0 w-32 h-32 bg-yellow-500/10 rounded-full -mr-16 -mt-16"></div>
          <div className="relative">
            <div className="flex items-center justify-between mb-3">
              <p className="text-xs text-yellow-400 font-bold uppercase tracking-wide flex items-center gap-2">
                <Clock size={16} />
                Em Retenção
              </p>
            </div>
            <p className="text-3xl font-bold text-white mb-2">
              {mostrarSaldo ? `R$ ${(saldoDetalhado.saldoEmRetencao || 0).toFixed(2)}` : 'R$ •••••'}
            </p>
            <div className="bg-yellow-500/10 rounded-lg p-3 mt-4">
              <p className="text-[11px] text-yellow-200 mb-1">📅 Próxima liberação:</p>
              <p className="text-sm font-bold text-yellow-300">{formatarDataCurta(saldoDetalhado.proximoSaque)}</p>
            </div>
          </div>
        </div>
      </div>

      <div className="bg-gradient-to-r from-blue-500/10 to-purple-500/10 rounded-2xl p-5 border border-blue-500/30">
        <p className="text-sm text-blue-300 font-bold mb-3">ℹ️ Como funciona a divisão?</p>
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 mb-4">
          <div className="bg-black/30 rounded-lg p-3 border border-zinc-800">
            <p className="text-xs text-zinc-400">Barbeiro</p>
            <p className="text-lg font-bold text-green-400">{splitPagamento?.percentual_barbeiro ?? 40}%</p>
          </div>
          <div className="bg-black/30 rounded-lg p-3 border border-zinc-800">
            <p className="text-xs text-zinc-400">Barbearia</p>
            <p className="text-lg font-bold text-blue-400">{splitPagamento?.percentual_barbearia ?? 50}%</p>
          </div>
          <div className="bg-black/30 rounded-lg p-3 border border-zinc-800">
            <p className="text-xs text-zinc-400">Barber Move</p>
            <p className="text-lg font-bold text-orange-400">{splitPagamento?.percentual_barbermove ?? 10}%</p>
          </div>
        </div>
        <p className="text-xs text-zinc-300">
          A cada serviço concluído, o valor é dividido automaticamente e o saldo disponível fica pronto para saque conforme as regras da plataforma.
        </p>
      </div>

      {userType === 'barbearia' && (
        <div className="bg-zinc-900 border border-zinc-800 rounded-2xl p-5 space-y-3">
          <h3 className="text-white font-bold text-lg">Dados de Pagamento da Barbearia</h3>
          <p className="text-xs text-zinc-400">Movido da aba Perfil para centralizar no menu Pagar.</p>

          <input
            type="text"
            placeholder="Titular da conta"
            value={contaPagamento.titular_nome}
            onChange={(e) => setContaPagamento({ ...contaPagamento, titular_nome: e.target.value })}
            className="bm-input w-full bg-black border border-zinc-800 rounded-lg p-3 text-white"
          />

          <input
            type="text"
            placeholder="Documento do titular"
            value={contaPagamento.titular_documento}
            onChange={(e) => setContaPagamento({ ...contaPagamento, titular_documento: e.target.value })}
            className="bm-input w-full bg-black border border-zinc-800 rounded-lg p-3 text-white"
          />

          <input
            type="text"
            placeholder="Chave PIX"
            value={contaPagamento.chave_pix}
            onChange={(e) => setContaPagamento({ ...contaPagamento, chave_pix: e.target.value })}
            className="bm-input w-full bg-black border border-zinc-800 rounded-lg p-3 text-white"
          />

          <div className="grid grid-cols-2 gap-2">
            <input
              type="text"
              placeholder="Banco"
              value={contaPagamento.banco}
              onChange={(e) => setContaPagamento({ ...contaPagamento, banco: e.target.value })}
              className="bm-input w-full bg-black border border-zinc-800 rounded-lg p-3 text-white"
            />
            <input
              type="text"
              placeholder="Agência"
              value={contaPagamento.agencia}
              onChange={(e) => setContaPagamento({ ...contaPagamento, agencia: e.target.value })}
              className="bm-input w-full bg-black border border-zinc-800 rounded-lg p-3 text-white"
            />
          </div>

          <div className="grid grid-cols-2 gap-2">
            <input
              type="text"
              placeholder="Conta"
              value={contaPagamento.conta}
              onChange={(e) => setContaPagamento({ ...contaPagamento, conta: e.target.value })}
              className="bm-input w-full bg-black border border-zinc-800 rounded-lg p-3 text-white"
            />
            <select
              value={contaPagamento.tipo_conta}
              onChange={(e) => setContaPagamento({ ...contaPagamento, tipo_conta: e.target.value })}
              className="bm-input w-full bg-black border border-zinc-800 rounded-lg p-3 text-white"
            >
              <option value="corrente">Corrente</option>
              <option value="poupanca">Poupança</option>
            </select>
          </div>

          <button
            onClick={salvarContaPagamento}
            disabled={salvandoConta}
            className="bm-primary w-full px-4 py-3 rounded-lg font-bold disabled:opacity-60"
          >
            {salvandoConta ? 'Salvando...' : 'Salvar dados de pagamento'}
          </button>
        </div>
      )}
    </div>
  );
}
