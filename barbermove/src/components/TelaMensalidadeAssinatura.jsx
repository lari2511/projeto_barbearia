// --- ARQUIVO: barbermove/src/components/TelaMensalidadeAssinatura.jsx ---
// Tela de Plano e Assinatura - Mensalidade Progressiva por Cadeira
// Apenas para DONO DA BARBEARIA

import React, { useState, useEffect } from 'react';
import { Plus, Minus, TrendingUp, AlertCircle, Check } from 'lucide-react';

export default function TelaMensalidadeAssinatura({ token, barbeariaId, API_URL, onNotify }) {
  const [quantidadeCadeiras, setQuantidadeCadeiras] = useState(1);
  const [loading, setLoading] = useState(false);

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
        const res = await fetch(`${API_URL}/api/v1/cadeiras?barbearia_id=${barbeariaId}`, {
          headers: { 'Authorization': `Bearer ${token}` }
        });
        if (res.ok) {
          const cadeiras = await res.json();
          const ativas = Array.isArray(cadeiras) ? cadeiras.filter(c => c.status !== 'inativa').length : 0;
          setQuantidadeCadeiras(Math.max(1, ativas));
        }
      } catch (err) {
        console.error('Erro ao carregar cadeiras:', err);
      }
    };

    if (barbeariaId && token) {
      carregarCadeiras();
    }
  }, [barbeariaId, token, API_URL]);

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
      // Aqui você pode chamar um endpoint para salvar a quantidade de cadeiras
      // ou para processar a assinatura
      const res = await fetch(`${API_URL}/api/v1/mensalidade/barbearia/${barbeariaId}`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });

      if (res.ok) {
        await res.json();
        onNotify('Plano de assinatura confirmado!', 'success');
      } else {
        onNotify('Erro ao confirmar plano', 'error');
      }
    } catch (err) {
      onNotify('Erro ao conectar: ' + err.message, 'error');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="p-4 sm:p-6 bg-gradient-to-br from-black via-zinc-950 to-zinc-900 rounded-2xl border border-zinc-800 max-w-2xl mx-auto">
      {/* HEADER */}
      <div className="mb-6">
        <h2 className="text-2xl sm:text-3xl font-bold text-white mb-2 flex items-center gap-2">
          <TrendingUp size={28} className="text-orange-500" />
          Seu Plano de Assinatura
        </h2>
        <p className="text-sm text-zinc-400">
          Modelo progressivo por cadeira - quanto mais cadeiras, maior o desconto por unidade
        </p>
      </div>

      {/* SEÇÃO PRINCIPAL - SIMULADOR */}
      <div className="bg-zinc-900/50 border border-zinc-800 rounded-xl p-4 sm:p-6 mb-6">
        <h3 className="text-lg font-bold text-white mb-4">Simulador de Cadeiras</h3>

        {/* CONTROLE DE QUANTIDADE */}
        <div className="flex flex-col sm:flex-row items-center justify-between gap-4 mb-6 bg-zinc-800/30 p-4 rounded-lg">
          <div className="text-center flex-1">
            <p className="text-zinc-400 text-sm mb-1">Quantidade de Cadeiras</p>
            <p className="text-4xl font-bold text-orange-500">{quantidadeCadeiras}</p>
          </div>

          <div className="flex gap-2">
            <button
              onClick={handleMenos}
              disabled={quantidadeCadeiras <= 1}
              className="p-3 bg-red-600 hover:bg-red-700 disabled:bg-zinc-700 disabled:text-zinc-500 text-white rounded-lg transition active:scale-95"
            >
              <Minus size={20} />
            </button>
            <button
              onClick={handleMais}
              disabled={quantidadeCadeiras >= 20}
              className="p-3 bg-green-600 hover:bg-green-700 disabled:bg-zinc-700 disabled:text-zinc-500 text-white rounded-lg transition active:scale-95"
            >
              <Plus size={20} />
            </button>
          </div>

          <div className="text-center flex-1">
            <p className="text-zinc-400 text-sm mb-1">Mensalidade</p>
            <p className="text-3xl font-bold text-green-500">
              {formatarMoeda(calculos.total)}
            </p>
          </div>
        </div>

        {/* ECONOMIA */}
        <div className="bg-green-900/20 border border-green-700 rounded-lg p-3 mb-4">
          <div className="flex items-start gap-2">
            <Check size={20} className="text-green-400 flex-shrink-0 mt-0.5" />
            <div>
              <p className="text-green-400 font-bold text-sm">Economia Total</p>
              <p className="text-green-300 text-sm">
                Você economiza <strong>{formatarMoeda(calculos.economia)}</strong> em relação ao preço uniforme
              </p>
            </div>
          </div>
        </div>

        {/* DETALHAMENTO DE PREÇOS */}
        <div className="mb-4">
          <p className="text-zinc-400 text-xs uppercase tracking-wider font-bold mb-2">Detalhamento por Cadeira</p>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 max-h-40 overflow-y-auto">
            {calculos.detalhamento.map((item) => (
              <div
                key={item.cadeira}
                className="bg-zinc-800/50 border border-zinc-700 rounded p-2 text-center hover:bg-zinc-800/80 transition"
              >
                <p className="text-zinc-400 text-xs">Cadeira {item.cadeira}</p>
                <p className="text-white font-bold text-sm">{formatarMoeda(item.preco)}</p>
              </div>
            ))}
          </div>
        </div>

        {/* INFORMAÇÕES IMPORTANTES */}
        <div className="bg-blue-900/20 border border-blue-700 rounded-lg p-3 mb-4">
          <div className="flex items-start gap-2">
            <AlertCircle size={20} className="text-blue-400 flex-shrink-0 mt-0.5" />
            <div>
              <p className="text-blue-400 font-bold text-sm">Como Funciona</p>
              <ul className="text-blue-300 text-xs mt-1 space-y-1 ml-4 list-disc">
                <li>1ª cadeira: R$ 47,90</li>
                <li>2ª cadeira: R$ 37,90</li>
                <li>3ª cadeira: R$ 27,90</li>
                <li>4ª cadeira: R$ 20,90</li>
                <li>5ª cadeira: R$ 17,90</li>
                <li>6ª+ cadeira: R$ 17,90 (valor mínimo fixo)</li>
              </ul>
            </div>
          </div>
        </div>
      </div>

      {/* PRÓXIMA CADEIRA */}
      {quantidadeCadeiras < 20 && (
        <div className="bg-orange-900/20 border border-orange-700 rounded-xl p-4 mb-6">
          <p className="text-orange-400 font-bold text-sm mb-2">Se você adicionar mais uma cadeira:</p>
          <div className="flex justify-between items-center">
            <div>
              <p className="text-zinc-300 text-sm">
                Nova mensalidade: <span className="font-bold text-orange-400">{formatarMoeda(proximoDetalhamento.total)}</span>
              </p>
              <p className="text-zinc-400 text-xs mt-1">
                Incremento: +{formatarMoeda(incrementoProxima)} / mês (+{formatarMoeda(incrementoProxima * 12)} / ano)
              </p>
            </div>
            <button
              onClick={() => handleMais()}
              className="px-4 py-2 bg-orange-600 hover:bg-orange-700 text-white rounded-lg font-bold text-sm active:scale-95 transition"
            >
              +1 Cadeira
            </button>
          </div>
        </div>
      )}

      {/* TABELA RÁPIDA DE REFERÊNCIA */}
      <div className="mb-6">
        <p className="text-zinc-400 text-xs uppercase tracking-wider font-bold mb-2">Tabela de Preços</p>
        <div className="grid grid-cols-3 sm:grid-cols-5 gap-2">
          {[1, 2, 3, 4, 5, 6, 8, 10, 12, 15].map((qtd) => {
            const calc = calcularMensalidadeTotal(qtd);
            const isAtual = qtd === quantidadeCadeiras;
            return (
              <div
                key={qtd}
                onClick={() => setQuantidadeCadeiras(qtd)}
                className={`p-2 rounded-lg border text-center cursor-pointer transition ${
                  isAtual
                    ? 'bg-orange-600 border-orange-400 text-white font-bold'
                    : 'bg-zinc-800/50 border-zinc-700 text-zinc-300 hover:bg-zinc-800 hover:border-zinc-600'
                }`}
              >
                <p className="text-xs">{qtd} cad.</p>
                <p className={`text-sm font-bold ${isAtual ? 'text-white' : 'text-orange-400'}`}>
                  {formatarMoeda(calc.total)}
                </p>
              </div>
            );
          })}
        </div>
      </div>

      {/* BOTÃO DE CONFIRMAÇÃO */}
      <button
        onClick={handleConfirmar}
        disabled={loading}
        className="w-full bg-gradient-to-r from-orange-600 to-orange-700 hover:from-orange-700 hover:to-orange-800 disabled:from-zinc-700 disabled:to-zinc-700 text-white font-bold py-3 px-4 rounded-xl transition active:scale-95 flex items-center justify-center gap-2"
      >
        {loading ? (
          <>
            <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
            Processando...
          </>
        ) : (
          <>
            <Check size={20} />
            Confirmar Plano de {quantidadeCadeiras} Cadeira{quantidadeCadeiras > 1 ? 's' : ''}
          </>
        )}
      </button>

      {/* RODAPÉ */}
      <p className="text-zinc-500 text-xs text-center mt-4">
        Cobrança mensal realizada no 1º dia útil do mês. Cancele a qualquer momento.
      </p>
    </div>
  );
}
