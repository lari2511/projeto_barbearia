import React, { useState, useEffect, useCallback } from 'react';
import { CreditCard, Check, AlertCircle, TrendingDown, QrCode, Copy } from 'lucide-react';

const API_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

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
        valor: payload.valor ?? payload.amount ?? payload.valor_mensalidade ?? 0,
    };
};

export default function AssinaturaPage({ token, notify }) {
    const [qtdCadeiras, setQtdCadeiras] = useState(1);
    const [assinaturaAtual, setAssinaturaAtual] = useState(null);
    const [loading, setLoading] = useState(false);
    const [pagamentoProcessando, setPagamentoProcessando] = useState(false);
    const [metodoPagamento, setMetodoPagamento] = useState('pix');
    const [tipoCartao, setTipoCartao] = useState('cartao_credito');
    const [pixMensalidade, setPixMensalidade] = useState(null);
    const [cartao, setCartao] = useState({
        numero_cartao: '',
        titular: '',
        validade: '',
        cvv: ''
    });

    // Regra de negócio: valor acumulado progressivo por cadeira
    const obterPrecoCadeiraPorPosicao = (posicao) => {
        if (posicao === 1) return 47.90;
        if (posicao === 2) return 37.90;
        if (posicao === 3) return 27.90;
        if (posicao === 4) return 20.90;
        return 17.90;
    };

    const breakdown = Array.from({ length: qtdCadeiras }, (_, idx) => ({
        cadeira: idx + 1,
        valor: obterPrecoCadeiraPorPosicao(idx + 1),
    }));

    const totalMensal = breakdown.reduce((acc, item) => acc + item.valor, 0);
    const precoCadeiraAtual = obterPrecoCadeiraPorPosicao(qtdCadeiras);

    // Calcular economia vs plano individual
    const economiaVsIndividual = ((47.90 * qtdCadeiras) - totalMensal).toFixed(2);

    const carregarAssinatura = useCallback(async () => {
        setLoading(true);
        try {
            const res = await fetch(`${API_URL}/api/v1/assinaturas/minha-assinatura`, {
                headers: { 'Authorization': `Bearer ${token}` }
            });

            if (res.ok) {
                const data = await res.json();
                setAssinaturaAtual(data);
                if (data.cadeiras_ativas) {
                    setQtdCadeiras(data.cadeiras_ativas);
                }
            } else if (res.status !== 404) {
                notify('Erro ao carregar assinatura', 'error');
            }
        } catch (_err) {
            console.error('Erro ao carregar assinatura');
        } finally {
            setLoading(false);
        }
    }, [notify, token]);

    // Carregar assinatura atual
    useEffect(() => {
        carregarAssinatura();
    }, [carregarAssinatura]);

    const criarOuAtualizarPlano = async (metodo) => {
        const res = await fetch(`${API_URL}/api/v1/assinaturas/criar`, {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${token}`,
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                cadeiras_ativas: qtdCadeiras,
                metodo_pagamento: metodo
            })
        });

        const data = await res.json().catch(() => ({}));
        if (!res.ok) {
            throw new Error(data.detail || 'Erro ao salvar plano');
        }

        return data;
    };

    const confirmarPagamentoPix = async () => {
        setPagamentoProcessando(true);
        try {
            const res = await fetch(`${API_URL}/api/v1/assinaturas/pagar-mensalidade`, {
                method: 'POST',
                headers: {
                    'Authorization': `Bearer ${token}`,
                    'Content-Type': 'application/json'
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

            setPixMensalidade(null);
            notify('Pagamento PIX confirmado com sucesso!', 'success');
            await carregarAssinatura();
        } catch (err) {
            notify(err.message || 'Erro ao confirmar PIX', 'error');
        } finally {
            setPagamentoProcessando(false);
        }
    };

    const copiarCodigoPix = async () => {
        if (!pixMensalidade?.pix_copia_cola) return;
        try {
            await navigator.clipboard.writeText(pixMensalidade.pix_copia_cola);
            notify('Codigo PIX copiado!', 'success');
        } catch (_err) {
            notify('Nao foi possivel copiar automaticamente', 'error');
        }
    };

    const processarPagamento = async () => {
        setPagamentoProcessando(true);
        try {
            if (metodoPagamento === 'pix') {
                await criarOuAtualizarPlano('pix');

                const pixRes = await fetch(`${API_URL}/api/v1/assinaturas/pagar-mensalidade/pix`, {
                    method: 'POST',
                    headers: {
                        'Authorization': `Bearer ${token}`
                    }
                });

                const pixData = await pixRes.json().catch(() => ({}));
                if (!pixRes.ok) {
                    throw new Error(pixData.detail || 'Erro ao gerar PIX da mensalidade');
                }

                const pixNormalizado = normalizarPixPayload(pixData);
                if (!pixNormalizado.qrcode_base64 && !pixNormalizado.pix_copia_cola) {
                    throw new Error('PIX gerado sem QR Code e sem codigo copia e cola');
                }

                setPixMensalidade(pixNormalizado);
                notify('PIX gerado! Escaneie o QR Code ou use o copia e cola.', 'success');
                await carregarAssinatura();
                return;
            }

            if (!cartao.numero_cartao || !cartao.titular || !cartao.validade || !cartao.cvv) {
                throw new Error('Preencha todos os dados do cartao');
            }

            await criarOuAtualizarPlano(tipoCartao);

            const cardRes = await fetch(`${API_URL}/api/v1/assinaturas/pagar-mensalidade`, {
                method: 'POST',
                headers: {
                    'Authorization': `Bearer ${token}`,
                    'Content-Type': 'application/json'
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
                throw new Error(cardData.detail || 'Erro ao pagar com cartao');
            }

            setCartao({ numero_cartao: '', titular: '', validade: '', cvv: '' });
            notify(`Pagamento por ${tipoCartao === 'cartao_debito' ? 'Cartao de Debito' : 'Cartao de Credito'} confirmado!`, 'success');
            await carregarAssinatura();
        } catch (err) {
            notify(err.message || 'Erro ao processar pagamento', 'error');
        } finally {
            setPagamentoProcessando(false);
        }
    };

    const renovarAssinatura = async () => {
        setPagamentoProcessando(true);
        try {
            const res = await fetch(`${API_URL}/api/v1/assinaturas/renovar`, {
                method: 'POST',
                headers: {
                    'Authorization': `Bearer ${token}`,
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    metodo_pagamento: metodoPagamento
                })
            });

            const data = await res.json();

            if (res.ok) {
                notify('Assinatura renovada com sucesso!', 'success');
                await carregarAssinatura();
            } else {
                notify(data.detail || 'Erro ao renovar assinatura', 'error');
            }
        } catch (_err) {
            notify('Erro ao conectar com servidor', 'error');
        } finally {
            setPagamentoProcessando(false);
        }
    };

    if (loading) {
        return (
            <div className="flex items-center justify-center h-screen bg-black">
                <div className="text-white text-center">
                    <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-orange-500 mx-auto mb-4"></div>
                    <p>Carregando...</p>
                </div>
            </div>
        );
    }

    return (
        <div className="min-h-screen bg-black text-white p-4 pb-24">
            <div className="max-w-2xl mx-auto">
                {/* Header */}
                <div className="mb-6">
                    <h1 className="text-2xl font-bold mb-2">Assinatura BarberMove</h1>
                    <p className="text-zinc-400 text-sm">Gerenciamento de Cadeiras para sua Barbearia</p>
                </div>

                {/* Status da Assinatura Atual */}
                {assinaturaAtual && (
                    <div className="bg-gradient-to-br from-green-900/30 to-green-800/20 border border-green-700/50 rounded-xl p-4 mb-6">
                        <div className="flex items-start gap-3">
                            <Check className="text-green-400 mt-1" size={20} />
                            <div className="flex-1">
                                <h3 className="font-bold text-green-400 mb-1">Assinatura Ativa</h3>
                                <p className="text-sm text-zinc-300">
                                    <span className="font-bold">{assinaturaAtual.cadeiras_ativas}</span> cadeira(s) ativa(s)
                                </p>
                                <p className="text-xs text-zinc-400 mt-1">
                                    Vence em: {new Date(assinaturaAtual.proximo_vencimento).toLocaleDateString('pt-BR')}
                                </p>
                                <p className="text-xs text-zinc-400">
                                    Valor: R$ {assinaturaAtual.valor_mensal?.toFixed(2)}
                                </p>
                                <p className="text-xs text-zinc-400">
                                    Metodo: {(assinaturaAtual.metodo_pagamento || 'pix').replace('_', ' ')}
                                </p>
                            </div>
                        </div>
                        <button
                            onClick={renovarAssinatura}
                            disabled={pagamentoProcessando}
                            className="w-full mt-3 bg-green-600 hover:bg-green-700 text-white py-2 px-4 rounded-lg font-bold text-sm transition disabled:opacity-50"
                        >
                            {pagamentoProcessando ? 'Processando...' : 'Renovar Assinatura'}
                        </button>
                    </div>
                )}

                {/* Seletor de Cadeiras */}
                <div className="bg-zinc-900 border border-zinc-800 rounded-xl p-6 mb-6">
                    <label className="block text-sm font-bold mb-4 text-zinc-300">
                        Quantas cadeiras quer ativar?
                    </label>
                    
                    <div className="flex items-center justify-center gap-6 mb-6">
                        <button
                            onClick={() => setQtdCadeiras(Math.max(1, qtdCadeiras - 1))}
                            className="w-12 h-12 bg-zinc-800 hover:bg-zinc-700 rounded-full text-2xl font-bold transition active:scale-95"
                        >
                            -
                        </button>
                        
                        <div className="text-center">
                            <div className="text-5xl font-bold text-orange-500">{qtdCadeiras}</div>
                            <div className="text-xs text-zinc-500 mt-1">
                                {qtdCadeiras === 1 ? 'cadeira' : 'cadeiras'}
                            </div>
                        </div>
                        
                        <button
                            onClick={() => setQtdCadeiras(qtdCadeiras + 1)}
                            className="w-12 h-12 bg-zinc-800 hover:bg-zinc-700 rounded-full text-2xl font-bold transition active:scale-95"
                        >
                            +
                        </button>
                    </div>

                    {/* Indicador de Desconto */}
                    {qtdCadeiras >= 2 && (
                        <div className="bg-gradient-to-r from-orange-900/30 to-red-900/30 border border-orange-700/50 rounded-lg p-3 mb-4">
                            <div className="flex items-center gap-2">
                                <TrendingDown className="text-orange-400" size={18} />
                                <div className="flex-1">
                                    <p className="text-xs font-bold text-orange-400">
                                        {qtdCadeiras === 2 ? 'Preço progressivo aplicado!' : 'Desconto progressivo aplicado!'}
                                    </p>
                                    <p className="text-xs text-zinc-400">
                                        Você economiza R$ {economiaVsIndividual}/mês
                                    </p>
                                </div>
                            </div>
                        </div>
                    )}
                </div>

                {/* Resumo de Valores */}
                <div className="bg-zinc-900 border border-zinc-800 rounded-xl p-6 mb-6">
                    <label className="block text-sm font-bold mb-3 text-zinc-300">
                        Forma de pagamento
                    </label>
                    <div className="grid grid-cols-1 sm:grid-cols-3 gap-2 mb-6">
                        <button
                            type="button"
                            onClick={() => setMetodoPagamento('pix')}
                            className={`rounded-lg px-3 py-2 text-sm font-bold border transition ${metodoPagamento === 'pix' ? 'bg-orange-600/20 border-orange-500 text-orange-300' : 'bg-zinc-800 border-zinc-700 text-zinc-300 hover:bg-zinc-700'}`}
                        >
                            PIX
                        </button>
                        <button
                            type="button"
                            onClick={() => setMetodoPagamento('cartao')}
                            className={`rounded-lg px-3 py-2 text-sm font-bold border transition ${metodoPagamento === 'cartao' ? 'bg-orange-600/20 border-orange-500 text-orange-300' : 'bg-zinc-800 border-zinc-700 text-zinc-300 hover:bg-zinc-700'}`}
                        >
                            Cartao
                        </button>
                    </div>

                    {metodoPagamento === 'cartao' && (
                        <div className="mb-6 bg-zinc-800/40 border border-zinc-700 rounded-lg p-3">
                            <p className="text-xs text-zinc-400 mb-2">Tipo de cartao</p>
                            <div className="grid grid-cols-2 gap-2 mb-3">
                                <button
                                    type="button"
                                    onClick={() => setTipoCartao('cartao_credito')}
                                    className={`py-2 rounded text-sm font-bold border transition ${tipoCartao === 'cartao_credito' ? 'bg-blue-600/20 border-blue-500 text-blue-300' : 'bg-zinc-800 border-zinc-700 text-zinc-300 hover:bg-zinc-700'}`}
                                >
                                    Credito
                                </button>
                                <button
                                    type="button"
                                    onClick={() => setTipoCartao('cartao_debito')}
                                    className={`py-2 rounded text-sm font-bold border transition ${tipoCartao === 'cartao_debito' ? 'bg-indigo-600/20 border-indigo-500 text-indigo-300' : 'bg-zinc-800 border-zinc-700 text-zinc-300 hover:bg-zinc-700'}`}
                                >
                                    Debito
                                </button>
                            </div>

                            <div className="space-y-2">
                                <input
                                    type="text"
                                    placeholder="Numero do cartao"
                                    value={cartao.numero_cartao}
                                    onChange={(e) => setCartao({ ...cartao, numero_cartao: e.target.value.replace(/\D/g, '').slice(0, 19) })}
                                    className="w-full bg-zinc-900 border border-zinc-700 rounded-lg px-3 py-2 text-sm text-white outline-none focus:border-orange-500"
                                />
                                <input
                                    type="text"
                                    placeholder="Nome no cartao"
                                    value={cartao.titular}
                                    onChange={(e) => setCartao({ ...cartao, titular: e.target.value.toUpperCase() })}
                                    className="w-full bg-zinc-900 border border-zinc-700 rounded-lg px-3 py-2 text-sm text-white outline-none focus:border-orange-500"
                                />
                                <div className="grid grid-cols-2 gap-2">
                                    <input
                                        type="text"
                                        placeholder="MM/AA"
                                        value={cartao.validade}
                                        onChange={(e) => setCartao({ ...cartao, validade: e.target.value })}
                                        className="w-full bg-zinc-900 border border-zinc-700 rounded-lg px-3 py-2 text-sm text-white outline-none focus:border-orange-500"
                                    />
                                    <input
                                        type="text"
                                        placeholder="CVV"
                                        value={cartao.cvv}
                                        onChange={(e) => setCartao({ ...cartao, cvv: e.target.value.replace(/\D/g, '').slice(0, 4) })}
                                        className="w-full bg-zinc-900 border border-zinc-700 rounded-lg px-3 py-2 text-sm text-white outline-none focus:border-orange-500"
                                    />
                                </div>
                            </div>
                        </div>
                    )}

                    {metodoPagamento === 'pix' && pixMensalidade && (
                        <div className="mb-6 bg-zinc-800/40 border border-zinc-700 rounded-lg p-3 space-y-3">
                            <div className="flex items-center gap-2 text-green-300 font-bold text-sm">
                                <QrCode size={16} />
                                PIX gerado
                            </div>
                            <p className="text-xs text-zinc-400">Valor: R$ {Number(pixMensalidade.valor || 0).toFixed(2)}</p>

                            {pixMensalidade.qrcode_base64 && (
                                <img
                                    src={`data:image/png;base64,${pixMensalidade.qrcode_base64}`}
                                    alt="QR Code PIX"
                                    className="w-44 h-44 bg-white rounded p-2 mx-auto"
                                />
                            )}

                            {!pixMensalidade.qrcode_base64 && (
                                <p className="text-[11px] text-yellow-300">
                                    QR Code indisponivel. Use o codigo copia e cola abaixo.
                                </p>
                            )}

                            <div className="bg-zinc-900 border border-zinc-700 rounded p-2">
                                <p className="text-[11px] text-zinc-400 mb-1">PIX copia e cola</p>
                                <p className="text-[11px] text-zinc-200 break-all">{pixMensalidade.pix_copia_cola}</p>
                            </div>

                            <button
                                type="button"
                                onClick={copiarCodigoPix}
                                className="w-full bg-zinc-700 hover:bg-zinc-600 text-white py-2 rounded font-bold text-sm flex items-center justify-center gap-2"
                            >
                                <Copy size={16} />
                                Copiar codigo PIX
                            </button>

                            <button
                                type="button"
                                onClick={confirmarPagamentoPix}
                                disabled={pagamentoProcessando}
                                className="w-full bg-green-600 hover:bg-green-700 disabled:opacity-50 text-white py-2 rounded font-bold text-sm"
                            >
                                {pagamentoProcessando ? 'Confirmando...' : 'Ja paguei, confirmar PIX'}
                            </button>
                        </div>
                    )}

                    <div className="space-y-3">
                        <div className="flex justify-between items-center pb-3 border-b border-zinc-800">
                            <span className="text-zinc-400 text-sm">Valor da {qtdCadeiras}a cadeira:</span>
                            <span className="text-green-400 font-bold text-lg">
                                R$ {precoCadeiraAtual.toFixed(2)}
                            </span>
                        </div>
                        
                        <div className="space-y-1 pb-3 border-b border-zinc-800">
                            <span className="text-zinc-400 text-sm">Detalhamento:</span>
                            {breakdown.map((item) => (
                                <div key={item.cadeira} className="flex justify-between items-center text-xs">
                                    <span className="text-zinc-500">{item.cadeira}a cadeira</span>
                                    <span className="text-zinc-300">R$ {item.valor.toFixed(2)}</span>
                                </div>
                            ))}
                        </div>

                        <div className="flex justify-between items-center pt-2">
                            <span className="text-lg font-bold">Total Mensal:</span>
                            <span className="text-2xl font-bold text-orange-500">
                                R$ {totalMensal.toFixed(2)}
                            </span>
                        </div>
                    </div>

                    {/* Botão de Pagamento */}
                    <button
                        onClick={processarPagamento}
                        disabled={pagamentoProcessando}
                        className="w-full mt-6 bg-gradient-to-r from-orange-600 to-red-600 hover:from-orange-700 hover:to-red-700 text-white py-4 px-6 rounded-xl font-bold text-lg transition active:scale-95 disabled:opacity-50 flex items-center justify-center gap-2"
                    >
                        {pagamentoProcessando ? (
                            <>
                                <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-white"></div>
                                Processando...
                            </>
                        ) : (
                            <>
                                <CreditCard size={20} />
                                {metodoPagamento === 'pix'
                                    ? 'Gerar PIX (QR Code e copia e cola)'
                                    : (assinaturaAtual ? 'Cadastrar cartao e alterar plano' : 'Cadastrar cartao e ativar assinatura')}
                            </>
                        )}
                    </button>
                </div>

                {/* Informações Adicionais */}
                <div className="bg-blue-900/20 border border-blue-700/30 rounded-xl p-4">
                    <div className="flex items-start gap-3">
                        <AlertCircle className="text-blue-400 mt-0.5" size={18} />
                        <div className="text-xs text-blue-300">
                            <p className="font-bold mb-1">Como funciona:</p>
                            <ul className="space-y-1 text-blue-200/80">
                                <li>• Desconto automático conforme você adiciona cadeiras</li>
                                <li>• Cobrança mensal recorrente</li>
                                <li>• Barbeiros ganham acesso às cadeiras contratadas</li>
                                <li>• Cancele ou ajuste a quantidade a qualquer momento</li>
                            </ul>
                        </div>
                    </div>
                </div>

                {/* Tabela de Preços */}
                <div className="mt-6 bg-zinc-900 border border-zinc-800 rounded-xl p-4">
                    <h3 className="font-bold text-sm mb-3 text-zinc-300">Tabela de Preços</h3>
                    <div className="space-y-2 text-xs">
                        <div className="flex justify-between items-center py-2 border-b border-zinc-800">
                            <span className="text-zinc-400">1a cadeira</span>
                            <span className="font-bold">R$ 47,90</span>
                        </div>
                        <div className="flex justify-between items-center py-2 border-b border-zinc-800">
                            <span className="text-zinc-400">2a cadeira</span>
                            <span className="font-bold text-green-400">R$ 37,90</span>
                        </div>
                        <div className="flex justify-between items-center py-2 border-b border-zinc-800">
                            <span className="text-zinc-400">3a cadeira</span>
                            <span className="font-bold text-green-400">R$ 27,90</span>
                        </div>
                        <div className="flex justify-between items-center py-2 border-b border-zinc-800">
                            <span className="text-zinc-400">4a cadeira</span>
                            <span className="font-bold text-green-400">R$ 20,90</span>
                        </div>
                        <div className="flex justify-between items-center py-2">
                            <span className="text-zinc-400">6a em diante</span>
                            <span className="font-bold text-green-400">R$ 17,90</span>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
}
