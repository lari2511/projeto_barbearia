// --- ARQUIVO: barbermove/src/components/TelaPagamento.jsx ---
// Componente para processar pagamentos (PIX/Cartão/Dinheiro)

import React, { useEffect, useRef, useState, useCallback } from 'react';
import { AlertCircle, CheckCircle, Copy, Loader, CreditCard, QrCode, DollarSign, Gift, X, ArrowLeft, Wallet } from 'lucide-react';
import {
  salvarMetodoPreferidoCliente,
  lerMetodoPreferidoCliente,
  normalizarPixMercadoPago,
  gerarQrDataUrl,
  validarCartaoBasico
} from './checkout/core';

export default function TelaPagamento({ chamadoId, valor, onPago }) {
  const preferenciaInicialAplicadaRef = useRef(false);
  const [metodoPreferidoCliente, setMetodoPreferidoCliente] = useState(() => lerMetodoPreferidoCliente());
  const [etapa, setEtapa] = useState('metodo'); // 'metodo', 'pix', 'cartao', 'processando', 'confirmacao'
  const [metodo, setMetodo] = useState(null);
  const [pagamentoId, setPagamentoId] = useState(null);
  const [qrcode, setQrcode] = useState(null);
  const [copiaCola, setCopiaCola] = useState(null);
  const [loading, setLoading] = useState(false);
  const [mensagem, setMensagem] = useState('');
  const [tipoMensagem, setTipoMensagem] = useState('info'); // 'success', 'error', 'info', 'warning'
  const [cupom, setCupom] = useState('');
  const [cupomAplicado, setCupomAplicado] = useState(false);
  const [valorComDesconto, setValorComDesconto] = useState(valor);
  const [parcelas, setParcelas] = useState(1);
  const [validandoCupom, setValidandoCupom] = useState(false);
  const [statusProcessamento, setStatusProcessamento] = useState('Preparando transacao...');

  // Dados cartão
  const [cartao, setCartao] = useState({
    numero: '',
    titular: '',
    validade: '',
    cvv: ''
  });

  // Erros de validação
  const [erros, setErros] = useState({});

  // Funções de formatação
  const formatarNumeroCartao = (valor) => {
    const apenasNumeros = valor.replace(/\D/g, '');
    const grupos = apenasNumeros.match(/.{1,4}/g);
    return grupos ? grupos.join(' ') : apenasNumeros;
  };

  const formatarValidade = (valor) => {
    const apenasNumeros = valor.replace(/\D/g, '');
    if (apenasNumeros.length >= 2) {
      return apenasNumeros.slice(0, 2) + '/' + apenasNumeros.slice(2, 4);
    }
    return apenasNumeros;
  };

  // Validações
  

  const mostrarMensagem = useCallback((texto, tipo = 'info') => {
    setMensagem(texto);
    setTipoMensagem(tipo);
    setTimeout(() => setMensagem(''), 4000);
  }, []);

  

  const gerarPix = useCallback(async (pagId) => {
    try {
      // Usar endpoint MercadoPago para gerar PIX real
      const response = await fetch(`${import.meta.env.VITE_API_URL}/api/v1/pagamentos/mercadopago/pix`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${localStorage.getItem('token')}`
        },
        body: JSON.stringify({ pagamento_id: pagId })
      });

      if (response.ok) {
        const data = await response.json();
        const pix = normalizarPixMercadoPago(data);

        let qrRender = pix.qrImage;
        if (!qrRender && pix.copia) {
          qrRender = await gerarQrDataUrl(pix.copia).catch(() => '');
        }

        setQrcode(qrRender || null);
        setCopiaCola(pix.copia || 'Código PIX disponível no banco');
        setEtapa('pix');
        mostrarMensagem('QR Code MercadoPago gerado! Escaneie para pagar.', 'success');
      } else {
        const error = await response.json();
        mostrarMensagem(error.detail || 'Erro ao gerar PIX', 'error');
      }
    } catch (err) {
      console.error('Erro:', err);
      mostrarMensagem('Erro ao gerar PIX. Tente novamente.', 'error');
    }
  }, [mostrarMensagem]);

  const copiarPix = () => {
    navigator.clipboard.writeText(copiaCola);
    mostrarMensagem('Código PIX copiado! Cole no seu app de pagamento.', 'success');
  };

  const aplicarCupom = async () => {
    if (!cupom || cupom.trim().length === 0) {
      mostrarMensagem('Digite um código de cupom', 'warning');
      return;
    }
    
    setValidandoCupom(true);
    try {
      // Simular validação de cupom (substituir com API real)
      await new Promise(resolve => setTimeout(resolve, 800));
      
      // Cupons de exemplo
      const cuponsValidos = {
        'PRIMEIRACOMPRA': 0.10, // 10%
        'FIDELIDADE20': 0.20,   // 20%
        'AMIGO15': 0.15,        // 15%
        'BEMVINDO': 0.05        // 5%
      };
      
      const desconto = cuponsValidos[cupom.toUpperCase()];
      
      if (desconto) {
        const novoValor = valor * (1 - desconto);
        setValorComDesconto(novoValor);
        setCupomAplicado(true);
        mostrarMensagem(`Cupom aplicado! ${(desconto * 100)}% de desconto`, 'success');
      } else {
        mostrarMensagem('Cupom inválido ou expirado', 'error');
      }
    } catch (_err) {
      mostrarMensagem('Erro ao validar cupom', 'error');
    }
    setValidandoCupom(false);
  };

  const removerCupom = () => {
    setCupom('');
    setCupomAplicado(false);
    setValorComDesconto(valor);
    mostrarMensagem('Cupom removido', 'info');
  };

  const confirmarPagamento = useCallback(async (metodoOverride = null, pagamentoIdOverride = null) => {
    const metodoAtual = metodoOverride || metodo;
    const pagamentoAtual = pagamentoIdOverride || pagamentoId;

    if (metodoAtual === 'cartao') {
      const novosErros = validarCartaoBasico({ numero: cartao.numero, titular: cartao.titular, validade: cartao.validade, cvv: cartao.cvv });
      setErros(novosErros);
      if (Object.keys(novosErros).length !== 0) {
        mostrarMensagem('Preencha todos os dados do cartão corretamente', 'error');
        return;
      }
    }

    setLoading(true);
    setEtapa('processando');
    setStatusProcessamento('Comunicando com o processador de pagamento...');

    // Delay curto para transicao visual e evitar multiplos cliques em sequencia.
    await new Promise((resolve) => setTimeout(resolve, 1200));
    try {
      // Se for cartão, usar endpoint MercadoPago
      if (metodoAtual === 'cartao') {
        const response = await fetch(`${import.meta.env.VITE_API_URL}/api/v1/pagamentos/mercadopago/cartao`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${localStorage.getItem('token')}`
          },
          body: JSON.stringify({
            pagamento_id: pagamentoAtual,
            numero_cartao: cartao.numero,
            titular: cartao.titular,
            data_validade: cartao.validade,
            cvv: cartao.cvv,
            parcelas: parcelas
          })
        });

        if (response.ok) {
          const data = await response.json();
          if (data.status === 'approved') {
            setStatusProcessamento('Pagamento aprovado! Atualizando agendamento...');
            setEtapa('confirmacao');
            mostrarMensagem('✅ Pagamento aprovado com sucesso!', 'success');
            setTimeout(() => onPago && onPago(), 2500);
          } else {
            setEtapa('cartao');
            mostrarMensagem(`Pagamento ${data.status}. Tente novamente.`, 'error');
          }
        } else {
          const error = await response.json();
          setEtapa('cartao');
          mostrarMensagem(error.detail || 'Erro ao processar cartão', 'error');
        }
      } else if (metodoAtual === 'pix') {
        // Para PIX, confirmar que o pagamento foi feito
        const response = await fetch(`${import.meta.env.VITE_API_URL}/api/v1/pagamentos/confirmar`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${localStorage.getItem('token')}`
          },
          body: JSON.stringify({
            pagamento_id: pagamentoAtual,
            metodo: 'pix'
          })
        });

        if (response.ok) {
          setStatusProcessamento('Pagamento confirmado! Finalizando...');
          setEtapa('confirmacao');
          mostrarMensagem('Pagamento confirmado com sucesso!', 'success');
          setTimeout(() => onPago && onPago(), 2500);
        } else {
          const error = await response.json();
          setEtapa('pix');
          mostrarMensagem(error.detail || 'Erro ao confirmar pagamento', 'error');
        }
      } else if (metodoAtual === 'dinheiro') {
        const response = await fetch(`${import.meta.env.VITE_API_URL}/api/v1/pagamentos/confirmar`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${localStorage.getItem('token')}`
          },
          body: JSON.stringify({
            pagamento_id: pagamentoAtual,
            metodo: 'dinheiro'
          })
        });

        if (response.ok) {
          setStatusProcessamento('Pagamento em dinheiro registrado! Finalizando...');
          setEtapa('confirmacao');
          mostrarMensagem('Pagamento em dinheiro confirmado!', 'success');
          setTimeout(() => onPago && onPago(), 2500);
        } else {
          const error = await response.json();
          setEtapa('metodo');
          mostrarMensagem(error.detail || 'Erro ao confirmar pagamento em dinheiro', 'error');
        }
      }
    } catch (err) {
      console.error('Erro:', err);
      setEtapa(metodoAtual === 'cartao' ? 'cartao' : metodoAtual === 'pix' ? 'pix' : 'metodo');
      mostrarMensagem('Erro ao processar pagamento. Tente novamente.', 'error');
    }
    setLoading(false);
  }, [metodo, pagamentoId, cartao, parcelas, mostrarMensagem, onPago]);

  const criarPagamento = useCallback(async (metodoSelecionado) => {
    setLoading(true);
    setMensagem('');
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
          cupom_codigo: cupom || null,
          parcelas: metodoSelecionado === 'cartao' ? parcelas : 1
        })
      });

      if (response.ok) {
        const data = await response.json();
        setPagamentoId(data.id);
        setValorComDesconto(data.valor_final ?? valorComDesconto);
        setMetodo(metodoSelecionado);

        if (metodoSelecionado === 'pix') {
          await gerarPix(data.id);
        } else if (metodoSelecionado === 'cartao') {
          setEtapa('cartao');
        } else if (metodoSelecionado === 'dinheiro') {
          await confirmarPagamento('dinheiro', data.id);
        }
        mostrarMensagem('Pagamento criado com sucesso!', 'success');
      } else {
        const error = await response.json();
        mostrarMensagem(error.detail || 'Erro ao criar pagamento', 'error');
      }
    } catch (err) {
      console.error('Erro:', err);
      mostrarMensagem('Erro ao criar pagamento. Tente novamente.', 'error');
    }
    setLoading(false);
  }, [chamadoId, cupom, parcelas, valorComDesconto, gerarPix, confirmarPagamento, mostrarMensagem]);

  useEffect(() => {
    if (preferenciaInicialAplicadaRef.current) return;
    preferenciaInicialAplicadaRef.current = true;

    const metodoPreferido = lerMetodoPreferidoCliente();
    if (!metodoPreferido) return;

    // Agendar em next tick para evitar setState síncrono dentro do efeito
    const timer = setTimeout(() => {
      if (metodoPreferido === 'pix') {
        criarPagamento('pix');
        return;
      }

      if (metodoPreferido === 'cartao_credito' || metodoPreferido === 'cartao_debito') {
        criarPagamento('cartao');
      }
    }, 0);

    return () => clearTimeout(timer);
  }, [criarPagamento]);

  return (
    <div className="bg-gradient-to-br from-zinc-900 via-zinc-900 to-zinc-800 rounded-3xl p-6 sm:p-8 border border-zinc-700 max-w-xl mx-auto shadow-2xl">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        {etapa !== 'metodo' && etapa !== 'confirmacao' && (
          <button
            onClick={() => {
              if (etapa === 'pix' || etapa === 'cartao') {
                setEtapa('metodo');
                setMetodo(null);
              }
            }}
            className="flex items-center gap-2 text-zinc-400 hover:text-white transition"
          >
            <ArrowLeft size={20} />
            <span>Voltar</span>
          </button>
        )}
        <h2 className="text-2xl font-bold text-white flex items-center gap-2">
          <Wallet className="text-blue-500" size={28} />
          Pagamento
        </h2>
        <div className="w-20"></div>
      </div>

      {/* Resumo do serviço */}
      <div className="bg-gradient-to-br from-zinc-800 to-zinc-800/50 rounded-2xl p-5 mb-6 border border-zinc-700 shadow-lg">
        <div className="flex justify-between items-center mb-3">
          <span className="text-zinc-400 text-sm">Valor do serviço:</span>
          <span className="text-white font-bold text-lg">R$ {valor.toFixed(2)}</span>
        </div>
        
        {cupomAplicado && (
          <div className="flex justify-between items-center mb-3 animate-pulse">
            <span className="text-zinc-400 text-sm flex items-center gap-1">
              <Gift size={16} className="text-green-500" />
              Desconto aplicado:
            </span>
            <span className="text-green-400 font-bold">- R$ {(valor - valorComDesconto).toFixed(2)}</span>
          </div>
        )}
        
        <div className="border-t border-zinc-700 pt-3 flex justify-between items-center">
          <span className="text-white font-bold text-lg">Total a pagar:</span>
          <span className="text-blue-400 font-bold text-2xl">R$ {valorComDesconto.toFixed(2)}</span>
        </div>

        {metodo === 'cartao' && parcelas > 1 && (
          <div className="mt-3 pt-3 border-t border-zinc-700">
            <p className="text-zinc-400 text-xs">
              {parcelas}x de R$ {(valorComDesconto / parcelas).toFixed(2)} sem juros
            </p>
          </div>
        )}
      </div>

      {/* Seleção de Método */}
      {etapa === 'metodo' && (
        <div className="space-y-5">
          {metodoPreferidoCliente && (
            <div className="bg-zinc-800/50 rounded-xl p-3 border border-zinc-700">
              <p className="text-xs text-zinc-300">
                Metodo preferido: <span className="font-bold text-orange-400">{metodoPreferidoCliente.replace('_', ' ')}</span>
              </p>
            </div>
          )}

          {/* Cupom de Desconto */}
          <div className="bg-zinc-800/50 rounded-xl p-4 border border-zinc-700">
            <p className="text-zinc-300 text-sm mb-3 flex items-center gap-2">
              <Gift size={16} className="text-yellow-500" />
              Tem um cupom de desconto?
            </p>
            <div className="flex gap-2">
              <input
                type="text"
                placeholder="Digite o código"
                className="flex-1 bg-zinc-900 text-white px-4 py-2.5 rounded-lg border border-zinc-600 focus:border-blue-500 focus:ring-2 focus:ring-blue-500/20 outline-none transition uppercase"
                value={cupom}
                onChange={(e) => setCupom(e.target.value.toUpperCase())}
                disabled={cupomAplicado}
              />
              {cupomAplicado ? (
                <button
                  onClick={removerCupom}
                  className="bg-red-600 hover:bg-red-700 text-white px-4 py-2.5 rounded-lg transition flex items-center gap-2"
                >
                  <X size={18} />
                </button>
              ) : (
                <button
                  onClick={aplicarCupom}
                  disabled={validandoCupom || !cupom}
                  className="bg-gradient-to-r from-yellow-600 to-orange-600 hover:from-yellow-700 hover:to-orange-700 text-white px-6 py-2.5 rounded-lg transition font-bold disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
                >
                  {validandoCupom ? (
                    <>
                      <Loader size={18} className="animate-spin" />
                      <span>Validando...</span>
                    </>
                  ) : (
                    'Aplicar'
                  )}
                </button>
              )}
            </div>
            <p className="text-xs text-zinc-500 mt-2">
              Cupons de exemplo: PRIMEIRACOMPRA, FIDELIDADE20, AMIGO15
            </p>
          </div>

          <p className="text-zinc-400 text-sm font-medium">Escolha como deseja pagar:</p>

          {/* PIX */}
          <button
            onClick={() => {
              salvarMetodoPreferidoCliente('pix');
              setMetodoPreferidoCliente('pix');
              criarPagamento('pix');
            }}
            disabled={loading}
            className="w-full bg-gradient-to-r from-purple-600 via-purple-500 to-blue-600 hover:from-purple-700 hover:via-purple-600 hover:to-blue-700 text-white font-bold py-5 rounded-2xl transition-all transform hover:scale-[1.02] active:scale-[0.98] flex items-center justify-between px-6 disabled:opacity-50 disabled:cursor-not-allowed shadow-lg hover:shadow-purple-500/50"
          >
            <div className="flex items-center gap-3">
              <QrCode size={28} />
              <div className="text-left">
                <p className="font-bold text-lg">Pagar com PIX</p>
                <p className="text-xs text-purple-100">Aprovação instantânea</p>
              </div>
            </div>
            <span className="text-2xl">→</span>
          </button>

          {/* Cartão */}
          <button
            onClick={() => {
              salvarMetodoPreferidoCliente('cartao_credito');
              setMetodoPreferidoCliente('cartao_credito');
              criarPagamento('cartao');
            }}
            disabled={loading}
            className="w-full bg-gradient-to-r from-green-600 via-emerald-500 to-teal-600 hover:from-green-700 hover:via-emerald-600 hover:to-teal-700 text-white font-bold py-5 rounded-2xl transition-all transform hover:scale-[1.02] active:scale-[0.98] flex items-center justify-between px-6 disabled:opacity-50 disabled:cursor-not-allowed shadow-lg hover:shadow-green-500/50"
          >
            <div className="flex items-center gap-3">
              <CreditCard size={28} />
              <div className="text-left">
                <p className="font-bold text-lg">Cartão de Crédito</p>
                <p className="text-xs text-green-100">Parcele em até 12x sem juros</p>
              </div>
            </div>
            <span className="text-2xl">→</span>
          </button>

          {/* Dinheiro */}
          <button
            onClick={() => criarPagamento('dinheiro')}
            disabled={loading}
            className="w-full bg-gradient-to-r from-orange-600 via-red-500 to-pink-600 hover:from-orange-700 hover:via-red-600 hover:to-pink-700 text-white font-bold py-5 rounded-2xl transition-all transform hover:scale-[1.02] active:scale-[0.98] flex items-center justify-between px-6 shadow-lg hover:shadow-orange-500/50"
          >
            <div className="flex items-center gap-3">
              <DollarSign size={28} />
              <div className="text-left">
                <p className="font-bold text-lg">Dinheiro na Hora</p>
                <p className="text-xs text-orange-100">Pague diretamente ao barbeiro</p>
              </div>
            </div>
            <span className="text-2xl">→</span>
          </button>

          {loading && (
            <div className="flex items-center justify-center gap-2 text-blue-400 py-3">
              <Loader size={20} className="animate-spin" />
              <span>Processando...</span>
            </div>
          )}
        </div>
      )}

      {/* Tela de Processamento */}
      {etapa === 'processando' && (
        <div className="text-center space-y-5 py-10 animate-in fade-in duration-300">
          <div className="mx-auto w-16 h-16 rounded-full border-4 border-blue-500/30 border-t-blue-500 animate-spin"></div>
          <h3 className="text-2xl font-bold text-white">Processando pagamento...</h3>
          <p className="text-zinc-300">{statusProcessamento}</p>
          <p className="text-zinc-500 text-sm">Nao feche esta tela. Isso pode levar alguns segundos.</p>
        </div>
      )}

      {/* Tela PIX */}
      {etapa === 'pix' && (
        <div className="space-y-6 text-center animate-in fade-in duration-500">
          {/* Badge MercadoPago */}
          <div className="flex justify-center">
            <div className="bg-gradient-to-r from-yellow-600 to-yellow-500 px-4 py-2 rounded-full text-white text-xs font-bold">
              💳 Pagamento via MercadoPago
            </div>
          </div>

          <div className="relative">
            {qrcode ? (
              <div className="bg-zinc-900 rounded-2xl p-6 inline-block shadow-2xl border-4 border-purple-500">
                <div className="bg-zinc-800 inline-block p-2 rounded">
                  <img src={qrcode} alt="QR Code PIX MercadoPago" className="w-64 h-64" />
                </div>
              </div>
            ) : (
              <div className="bg-zinc-900 border border-zinc-700 rounded-xl p-6 inline-block">
                <p className="text-yellow-300 text-sm">QR Code indisponível. Use o código de cópia abaixo.</p>
              </div>
            )}
            <div className="absolute -top-3 -right-3 bg-purple-600 text-white rounded-full p-3 shadow-lg">
              <QrCode size={24} />
            </div>
          </div>

          <div className="bg-gradient-to-r from-purple-600/20 to-blue-600/20 rounded-xl p-4 border border-purple-500/50">
            <p className="text-purple-300 text-sm mb-2 font-medium">
              📱 Escaneie com qualquer app de pagamento
            </p>
            <p className="text-xs text-zinc-300">
              ✅ Banco do Brasil • Nubank • Inter • NuConta • PicPay • e outros
            </p>
          </div>

          <div className="bg-gradient-to-r from-zinc-800 to-zinc-800/50 rounded-xl p-4 border border-zinc-700">
            <p className="text-xs text-zinc-400 mb-2 uppercase tracking-wide font-bold">
              Dados para cópia:
            </p>
            <div className="flex gap-2 items-center">
              <input
                type="text"
                value={copiaCola || 'Processando...'}
                readOnly
                className="flex-1 bg-zinc-900 text-white text-xs p-3 rounded-lg font-mono overflow-hidden border border-zinc-600 select-all"
                onClick={(e) => e.target.select()}
              />
              <button
                onClick={copiarPix}
                disabled={!copiaCola}
                className="bg-gradient-to-r from-blue-600 to-purple-600 hover:from-blue-700 hover:to-purple-700 text-white p-3 rounded-lg transition transform hover:scale-105 active:scale-95 shadow-lg disabled:opacity-50 disabled:cursor-not-allowed"
              >
                <Copy size={20} />
              </button>
            </div>
          </div>

          <div className="bg-blue-500/10 border border-blue-500/30 rounded-xl p-4">
            <p className="text-blue-300 flex items-center justify-center gap-2 text-sm">
              <AlertCircle size={20} />
              <span>✅ Após pagar, clique em "Confirmar Pagamento"</span>
            </p>
          </div>

          <button
            onClick={confirmarPagamento}
            disabled={loading}
            className="w-full bg-gradient-to-r from-green-600 to-emerald-600 hover:from-green-700 hover:to-emerald-700 text-white font-bold py-4 rounded-xl transition transform hover:scale-105 active:scale-95 disabled:opacity-50 disabled:cursor-not-allowed shadow-lg flex items-center justify-center gap-2"
          >
            {loading ? (
              <>
                <Loader size={20} className="animate-spin" />
                <span>Processando...</span>
              </>
            ) : (
              <>
                <CheckCircle size={20} />
                <span>✅ Já Paguei - Confirmar</span>
              </>
            )}
          </button>

          <p className="text-zinc-500 text-xs">
            ⏱️ O QR Code é válido por 30 minutos • 🔒 Seguro e criptografado
          </p>
        </div>
      )}

      {/* Tela Cartão */}
      {etapa === 'cartao' && (
        <div className="space-y-5 animate-in fade-in duration-500">
          {/* Badge MercadoPago */}
          <div className="flex justify-center">
            <div className="bg-gradient-to-r from-yellow-600 to-yellow-500 px-4 py-2 rounded-full text-white text-xs font-bold">
              💳 Pagamento via MercadoPago
            </div>
          </div>

          <div className="bg-gradient-to-br from-green-600/20 to-emerald-600/10 rounded-xl p-4 border border-green-500/30">
            <p className="text-green-300 text-sm flex items-center gap-2">
              <CreditCard size={18} />
              <span className="font-bold">Seus dados estão seguros</span>
            </p>
            <p className="text-xs text-zinc-400 mt-1">🔒 Processado por MercadoPago • Conexão SSL criptografada</p>
          </div>

          {/* Parcelas */}
          <div className="space-y-2">
            <label className="text-zinc-300 text-sm font-medium flex items-center gap-2">
              Parcelas
            </label>
            <select
              value={parcelas}
              onChange={(e) => setParcelas(parseInt(e.target.value))}
              className="w-full bg-zinc-800 text-white px-4 py-3 rounded-xl border border-zinc-600 focus:border-green-500 focus:ring-2 focus:ring-green-500/20 outline-none transition"
            >
              <option value={1}>À vista - R$ {valorComDesconto.toFixed(2)}</option>
              {[2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12].map(p => (
                <option key={p} value={p}>
                  {p}x de R$ {(valorComDesconto / p).toFixed(2)} sem juros
                </option>
              ))}
            </select>
          </div>

          {/* Número do Cartão */}
          <div className="space-y-2">
            <label className="text-zinc-300 text-sm font-medium">Número do Cartão</label>
            <input
              type="text"
              placeholder="0000 0000 0000 0000"
              maxLength="19"
              className={`w-full bg-zinc-800 text-white px-4 py-3 rounded-xl border ${
                erros.numero ? 'border-red-500' : 'border-zinc-600'
              } focus:border-green-500 focus:ring-2 focus:ring-green-500/20 outline-none transition font-mono text-lg tracking-wider`}
              value={formatarNumeroCartao(cartao.numero)}
              onChange={(e) => {
                const valor = e.target.value.replace(/\s/g, '');
                if (/^\d*$/.test(valor) && valor.length <= 16) {
                  setCartao(prev => ({ ...prev, numero: valor }));
                  if (erros.numero) setErros(prev => ({ ...prev, numero: null }));
                }
              }}
            />
            {erros.numero && (
              <p className="text-red-400 text-xs flex items-center gap-1">
                <AlertCircle size={12} /> {erros.numero}
              </p>
            )}
          </div>

          {/* Nome do Titular */}
          <div className="space-y-2">
            <label className="text-zinc-300 text-sm font-medium">Nome do Titular</label>
            <input
              type="text"
              placeholder="Nome como está no cartão"
              className={`w-full bg-zinc-800 text-white px-4 py-3 rounded-xl border ${
                erros.titular ? 'border-red-500' : 'border-zinc-600'
              } focus:border-green-500 focus:ring-2 focus:ring-green-500/20 outline-none transition uppercase`}
              value={cartao.titular}
              onChange={(e) => {
                const valor = e.target.value.toUpperCase();
                if (/^[A-Z\s]*$/.test(valor)) {
                  setCartao(prev => ({ ...prev, titular: valor }));
                  if (erros.titular) setErros(prev => ({ ...prev, titular: null }));
                }
              }}
            />
            {erros.titular && (
              <p className="text-red-400 text-xs flex items-center gap-1">
                <AlertCircle size={12} /> {erros.titular}
              </p>
            )}
          </div>

          {/* Validade e CVV */}
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <label className="text-zinc-300 text-sm font-medium">Validade</label>
              <input
                type="text"
                placeholder="MM/AA"
                maxLength="5"
                className={`w-full bg-zinc-800 text-white px-4 py-3 rounded-xl border ${
                  erros.validade ? 'border-red-500' : 'border-zinc-600'
                } focus:border-green-500 focus:ring-2 focus:ring-green-500/20 outline-none transition font-mono text-lg`}
                value={formatarValidade(cartao.validade)}
                onChange={(e) => {
                  const valor = e.target.value.replace(/\D/g, '');
                  if (valor.length <= 4) {
                    setCartao(prev => ({ ...prev, validade: valor }));
                    if (erros.validade) setErros(prev => ({ ...prev, validade: null }));
                  }
                }}
              />
              {erros.validade && (
                <p className="text-red-400 text-xs flex items-center gap-1">
                  <AlertCircle size={12} /> {erros.validade}
                </p>
              )}
            </div>

            <div className="space-y-2">
              <label className="text-zinc-300 text-sm font-medium">CVV</label>
              <input
                type="password"
                placeholder="123"
                maxLength="4"
                className={`w-full bg-zinc-800 text-white px-4 py-3 rounded-xl border ${
                  erros.cvv ? 'border-red-500' : 'border-zinc-600'
                } focus:border-green-500 focus:ring-2 focus:ring-green-500/20 outline-none transition font-mono text-lg text-center`}
                value={cartao.cvv}
                onChange={(e) => {
                  const valor = e.target.value;
                  if (/^\d*$/.test(valor)) {
                    setCartao(prev => ({ ...prev, cvv: valor }));
                    if (erros.cvv) setErros(prev => ({ ...prev, cvv: null }));
                  }
                }}
              />
              {erros.cvv && (
                <p className="text-red-400 text-xs flex items-center gap-1">
                  <AlertCircle size={12} /> {erros.cvv}
                </p>
              )}
            </div>
          </div>

          {/* Bandeiras aceitas */}
          <div className="bg-zinc-800/50 rounded-xl p-3 border border-zinc-700">
            <p className="text-xs text-zinc-400 mb-2">Bandeiras aceitas:</p>
            <div className="flex gap-2 flex-wrap">
              {['💳 Visa', '💳 Mastercard', '💳 Elo', '💳 American Express', '💳 Hipercard'].map(b => (
                <span key={b} className="text-xs bg-zinc-700 px-2 py-1 rounded-full text-zinc-300">
                  {b}
                </span>
              ))}
            </div>
          </div>

          <button
            onClick={confirmarPagamento}
            disabled={loading}
            className="w-full bg-gradient-to-r from-green-600 to-emerald-600 hover:from-green-700 hover:to-emerald-700 text-white font-bold py-4 rounded-xl transition transform hover:scale-105 active:scale-95 disabled:opacity-50 disabled:cursor-not-allowed shadow-lg flex items-center justify-center gap-2"
          >
            {loading ? (
              <>
                <Loader size={20} className="animate-spin" />
                <span>Processando pagamento...</span>
              </>
            ) : (
              <>
                <CreditCard size={20} />
                <span>Pagar R$ {valorComDesconto.toFixed(2)}</span>
              </>
            )}
          </button>
        </div>
      )}

      {/* Tela de Confirmação */}
      {etapa === 'confirmacao' && (
        <div className="text-center space-y-6 py-8 animate-in fade-in zoom-in duration-700">
          <div className="relative">
            <div className="bg-gradient-to-br from-green-500 to-emerald-500 rounded-full w-32 h-32 mx-auto flex items-center justify-center shadow-2xl shadow-green-500/50 animate-bounce">
              <CheckCircle size={80} className="text-white" />
            </div>
            <div className="absolute inset-0 bg-green-500 rounded-full w-32 h-32 mx-auto animate-ping opacity-20"></div>
          </div>

          <div className="space-y-2">
            <h3 className="text-3xl font-bold text-white">Pagamento Confirmado!</h3>
            <p className="text-green-400 text-lg font-medium">✓ Transação aprovada com sucesso</p>
          </div>

          <div className="bg-gradient-to-br from-green-500/20 to-emerald-500/10 rounded-2xl p-6 border border-green-500/30 space-y-3">
            <div className="flex justify-between items-center">
              <span className="text-zinc-300">Método:</span>
              <span className="text-white font-bold capitalize">{metodo}</span>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-zinc-300">Valor pago:</span>
              <span className="text-green-400 font-bold text-xl">R$ {valorComDesconto.toFixed(2)}</span>
            </div>
            {metodo === 'cartao' && parcelas > 1 && (
              <div className="flex justify-between items-center">
                <span className="text-zinc-300">Parcelado em:</span>
                <span className="text-white font-medium">{parcelas}x sem juros</span>
              </div>
            )}
          </div>

          <div className="space-y-2">
            <p className="text-zinc-400 text-sm">
              🎉 Seu serviço foi agendado com sucesso!
            </p>
            <p className="text-zinc-500 text-xs">
              Você receberá um comprovante por e-mail
            </p>
          </div>

          <div className="pt-4">
            <div className="flex items-center justify-center gap-2 text-blue-400">
              <Loader size={18} className="animate-spin" />
              <span className="text-sm">Redirecionando...</span>
            </div>
          </div>
        </div>
      )}

      {/* Mensagens de Feedback */}
      {mensagem && (
        <div className={`mt-6 rounded-xl p-4 border animate-in slide-in-from-bottom duration-300 ${
          tipoMensagem === 'success' ? 'bg-green-500/10 border-green-500/30 text-green-300' :
          tipoMensagem === 'error' ? 'bg-red-500/10 border-red-500/30 text-red-300' :
          tipoMensagem === 'warning' ? 'bg-yellow-500/10 border-yellow-500/30 text-yellow-300' :
          'bg-blue-500/10 border-blue-500/30 text-blue-300'
        }`}>
          <div className="flex items-center gap-2">
            {tipoMensagem === 'success' ? <CheckCircle size={18} /> :
             tipoMensagem === 'error' ? <AlertCircle size={18} /> :
             tipoMensagem === 'warning' ? <AlertCircle size={18} /> :
             <AlertCircle size={18} />}
            <p className="text-sm font-medium">{mensagem}</p>
          </div>
        </div>
      )}
    </div>
  );
}
