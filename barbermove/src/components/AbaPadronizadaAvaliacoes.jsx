import React, { useState, useEffect, useCallback } from 'react';
import { Star, MessageCircle } from 'lucide-react';
import ListaAvaliacoes from './ListaAvaliacoes';
import FluxoAvaliacaoCliente from './FluxoAvaliacaoCliente';

/**
 * Aba "Avaliacoes" padronizada (cliente / barbeiro / barbearia).
 *
 * - Cliente: mostra as avaliacoes pendentes (freelancer + barbearia) dos atendimentos
 *   ja pagos e permite avaliar pelo mesmo fluxo de 2 passos do pos-pagamento.
 * - Barbeiro / Barbearia: mostra as avaliacoes recebidas (fonte unica:
 *   AvaliacaoFreelancer / AvaliacaoBarbearia).
 */
export default function AbaPadronizadaAvaliacoes({
    usuarioId,
    tipoUsuario, // 'cliente', 'barbeiro', 'barbearia'
    _nomeUsuario,
    API_URL,
    token,
    notify,
}) {
    const [avaliacoes, setAvaliacoes] = useState([]);
    const [carregando, setCarregando] = useState(true);
    const [pendencias, setPendencias] = useState([]);
    const [pendenciaAtiva, setPendenciaAtiva] = useState(null);

    const carregarRecebidas = useCallback(async () => {
        if (tipoUsuario === 'cliente') {
            setAvaliacoes([]);
            return;
        }
        try {
            const res = await fetch(`${API_URL}/api/v1/avaliacoes/minhas-avaliacoes-recebidas`, {
                headers: { Authorization: `Bearer ${token}` },
            });
            if (res.ok) {
                const data = await res.json();
                const lista = [
                    ...(Array.isArray(data?.como_freelancer) ? data.como_freelancer : []),
                    ...(Array.isArray(data?.como_barbearia) ? data.como_barbearia : []),
                ];
                setAvaliacoes(lista);
            }
        } catch (_err) {
            notify?.('Erro ao carregar avaliacoes', 'error');
        }
    }, [API_URL, token, tipoUsuario, notify]);

    const carregarPendencias = useCallback(async () => {
        if (tipoUsuario !== 'cliente') {
            setPendencias([]);
            return;
        }
        try {
            const res = await fetch(`${API_URL}/api/v1/avaliacoes/pendentes-cliente`, {
                headers: { Authorization: `Bearer ${token}` },
            });
            if (res.ok) {
                const data = await res.json();
                const lista = (Array.isArray(data) ? data : []).filter((p) => (
                    !p.avaliacao_freelancer_enviada || !p.avaliacao_barbearia_enviada
                ));
                setPendencias(lista);
            }
        } catch (_err) {
            notify?.('Erro ao carregar avaliacoes pendentes', 'error');
        }
    }, [API_URL, token, tipoUsuario, notify]);

    const recarregar = useCallback(async () => {
        setCarregando(true);
        await Promise.all([carregarRecebidas(), carregarPendencias()]);
        setCarregando(false);
    }, [carregarRecebidas, carregarPendencias]);

    useEffect(() => {
        recarregar();
    }, [recarregar]);

    return (
        <div className="space-y-4 pb-24 max-w-3xl mx-auto w-full">
            {/* Cabecalho */}
            <div className="flex items-center gap-3 bg-zinc-900/50 border border-zinc-800 rounded-xl p-3">
                <div className="bg-orange-600/20 p-2.5 rounded-full">
                    <Star size={20} className="text-orange-500" />
                </div>
                <div>
                    <h2 className="text-xl sm:text-2xl font-bold text-white">Avaliacoes</h2>
                    <p className="text-zinc-300 text-sm">
                        {tipoUsuario === 'cliente'
                            ? 'Avalie o freelancer e a barbearia dos seus atendimentos'
                            : 'Avaliacoes que voce recebeu'}
                    </p>
                </div>
            </div>

            {/* Pendencias (cliente) */}
            {tipoUsuario === 'cliente' && pendencias.length > 0 && (
                <div className="bg-blue-900/20 border border-blue-500/70 rounded-xl p-4 sm:p-5">
                    <h3 className="text-base sm:text-lg font-bold text-blue-300 mb-3 flex items-center gap-2">
                        <MessageCircle size={18} />
                        {pendencias.length} atendimento{pendencias.length > 1 ? 's' : ''} para avaliar
                    </h3>

                    <div className="space-y-2.5">
                        {pendencias.map((p) => (
                            <div
                                key={p.chamado_id}
                                className="bg-zinc-900/80 border border-zinc-700 rounded-lg p-3 flex justify-between items-center gap-3 overflow-hidden"
                            >
                                <div className="min-w-0">
                                    <p className="font-bold text-white text-sm truncate">
                                        {p.freelancer_nome} · {p.barbearia_nome}
                                    </p>
                                    <p className="text-zinc-500 text-xs">
                                        {p.avaliacao_freelancer_enviada
                                            ? 'Falta avaliar a barbearia'
                                            : p.avaliacao_barbearia_enviada
                                            ? 'Falta avaliar o freelancer'
                                            : 'Avaliar freelancer e barbearia'}
                                    </p>
                                </div>
                                <button
                                    onClick={() => setPendenciaAtiva(p)}
                                    className="shrink-0 bg-orange-600 hover:bg-orange-700 text-white px-3 py-2 rounded-lg font-bold text-sm flex items-center gap-1.5 transition-colors"
                                >
                                    <Star size={14} />
                                    Avaliar
                                </button>
                            </div>
                        ))}
                    </div>
                </div>
            )}

            {/* Lista de avaliacoes recebidas */}
            {carregando ? (
                <div className="text-center py-12">
                    <div className="inline-block">
                        <div className="w-8 h-8 border-4 border-orange-500 border-t-transparent rounded-full animate-spin" />
                    </div>
                    <p className="text-zinc-500 mt-3">Carregando avaliacoes...</p>
                </div>
            ) : tipoUsuario === 'cliente' ? (
                pendencias.length === 0 && (
                    <div className="text-center py-12 text-zinc-500">
                        <Star size={32} className="mx-auto mb-3 opacity-50" />
                        <p>Nenhuma avaliacao pendente</p>
                    </div>
                )
            ) : (
                <ListaAvaliacoes avaliacoes={avaliacoes} />
            )}

            {/* Fluxo de avaliacao do cliente (2 passos) */}
            {pendenciaAtiva && (
                <FluxoAvaliacaoCliente
                    pendencia={pendenciaAtiva}
                    API_URL={API_URL}
                    token={token}
                    notify={notify}
                    onDone={() => {
                        setPendenciaAtiva(null);
                        recarregar();
                    }}
                />
            )}
        </div>
    );
}
