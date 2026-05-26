import React, { useState, useEffect, useCallback } from 'react';
import { Star, MessageCircle } from 'lucide-react';
import AvaliacaoModal from './AvaliacaoModal';
import ListaAvaliacoes from './ListaAvaliacoes';

export default function AbaPadronizadaAvaliacoes({
    usuarioId,
    tipoUsuario, // 'cliente', 'barbeiro', 'barbearia'
    _nomeUsuario,
    API_URL,
    token,
    notify
}) {
    const [avaliacoes, setAvaliacoes] = useState([]);
    const [carregando, setCarregando] = useState(true);
    const [modalAberta, setModalAberta] = useState(false);
    const [chamadoSelecionado, setChamadoSelecionado] = useState(null);
    const [chamadosPendentes, setChamadosPendentes] = useState([]);
    const [chamadosAvaliadosAgora, setChamadosAvaliadosAgora] = useState([]);

    const chamadoJaAvaliado = useCallback((ch) => {
        if (!ch) return false;
        return Boolean(
            ch.avaliado ||
            ch.avaliacao_enviada ||
            ch.avaliacao_freelancer_enviada ||
            ch.avaliacao_barbearia_enviada ||
            ch.avaliacao_cliente_enviada ||
            ch.avaliado_cliente ||
            ch.avaliado_freelancer ||
            ch.avaliado_barbearia ||
            ch.avaliado_por_cliente ||
            ch.avaliado_por_barbeiro ||
            ch.avaliado_por_barbearia
        );
    }, []);

    const carregarAvaliacoes = useCallback(async () => {
        setCarregando(true);
        try {
            const endpoint = `/api/v1/avaliacoes/usuario/${usuarioId}`;

            const res = await fetch(`${API_URL}${endpoint}`, {
                headers: { 'Authorization': `Bearer ${token}` }
            });

            if (res.ok) {
                const data = await res.json();
                const lista = Array.isArray(data) ? data : data.avaliacoes || [];
                setAvaliacoes(lista);
            }
        } catch (_err) {
            if (notify) {
                notify('Erro ao carregar avaliacoes', 'error');
            }
        } finally {
            setCarregando(false);
        }
    }, [API_URL, notify, token, usuarioId]);

    const handleEnviarAvaliacao = async (dados) => {
        try {
            const alvoId = tipoUsuario === 'cliente'
                ? (chamadoSelecionado?.barbeiro_id || chamadoSelecionado?.barbearia_usuario_id)
                : chamadoSelecionado?.cliente_id;

            if (!alvoId) {
                notify('Nao foi possivel identificar quem deve ser avaliado', 'error');
                return false;
            }

            const payload = {
                chamado_id: chamadoSelecionado.id,
                avaliado_id: alvoId,
                nota: dados.nota,
                comentario: dados.comentario
            };

            const res = await fetch(`${API_URL}/api/v1/avaliacoes/criar`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${token}`
                },
                body: JSON.stringify(payload)
            });

            if (res.ok) {
                notify('Avaliação enviada com sucesso! ✅', 'success');
                carregarAvaliacoes();

                if (chamadoSelecionado?.id != null) {
                    setChamadosAvaliadosAgora((prev) => {
                        if (prev.includes(chamadoSelecionado.id)) return prev;
                        return [...prev, chamadoSelecionado.id];
                    });
                }

                // Remove localmente o chamado já avaliado para não continuar aparecendo na lista.
                setChamadosPendentes((prev) => prev.filter((item) => item.id !== chamadoSelecionado?.id));
                await carregarChamadosPendentes();
                return true;
            } else {
                notify('Erro ao enviar avaliação', 'error');
                return false;
            }
        } catch (_err) {
            notify('Erro ao enviar avaliação', 'error');
            return false;
        }
    };

    const carregarChamadosPendentes = useCallback(async () => {
        try {
            // Buscar chamados concluídos que ainda não foram avaliados
            let endpoint = tipoUsuario === 'cliente'
                ? '/api/v1/cliente/meus_pedidos'
                : tipoUsuario === 'barbeiro'
                ? '/api/v1/barbeiro/agendamentos/meus'
                : null;

            if (tipoUsuario === 'barbearia') {
                const barbeariaRes = await fetch(`${API_URL}/api/v1/barbearia/minha`, {
                    headers: { 'Authorization': `Bearer ${token}` }
                });

                if (!barbeariaRes.ok) {
                    return null;
                }

                const barbearia = await barbeariaRes.json();
                endpoint = `/api/v1/barbearia/${barbearia.id}/agendamentos`;
            }

            if (!endpoint) {
                return null;
            }

            const res = await fetch(`${API_URL}${endpoint}`, {
                headers: { 'Authorization': `Bearer ${token}` }
            });

            if (res.ok) {
                const data = await res.json();
                const pendentes = (Array.isArray(data) ? data : data.chamados || [])
                    .filter(ch => {
                        const status = String(ch.status || '').toLowerCase();
                        const foiAvaliadoAgora = chamadosAvaliadosAgora.includes(ch.id);
                        return (status === 'concluido' || status === 'concluído') && !chamadoJaAvaliado(ch) && !foiAvaliadoAgora;
                    })
                    .slice(0, 3);
                setChamadosPendentes(pendentes);
                return pendentes;
            }
        } catch (_err) {
            if (notify) {
                notify('Erro ao carregar chamados', 'error');
            }
            return null;
        }
    }, [API_URL, notify, tipoUsuario, token, chamadoJaAvaliado, chamadosAvaliadosAgora]);

    // Carregar avaliações do usuário
    useEffect(() => {
        carregarAvaliacoes();
        carregarChamadosPendentes();
    }, [carregarAvaliacoes, carregarChamadosPendentes]);

    const handleAvaliarClick = (chamado) => {
        setChamadoSelecionado(chamado);
        setModalAberta(true);
    };

    return (
        <div className="space-y-4 pb-24 max-w-3xl mx-auto w-full">
            {/* Cabeçalho */}
            <div className="flex items-center gap-3 bg-zinc-900/50 border border-zinc-800 rounded-xl p-3">
                <div className="bg-orange-600/20 p-2.5 rounded-full">
                    <Star size={20} className="text-orange-500" />
                </div>
                <div>
                    <h2 className="text-xl sm:text-2xl font-bold text-white">Avaliações</h2>
                    <p className="text-zinc-300 text-sm">
                        {tipoUsuario === 'cliente'
                            ? 'Avaliações que você deu'
                            : 'Avaliações que você recebeu'}
                    </p>
                </div>
            </div>

            {/* Avaliações Pendentes */}
            {chamadosPendentes.length > 0 && (
                <div className="bg-blue-900/20 border border-blue-500/70 rounded-xl p-4 sm:p-5">
                    <h3 className="text-base sm:text-lg font-bold text-blue-300 mb-3 flex items-center gap-2">
                        <MessageCircle size={18} />
                        Você tem {chamadosPendentes.length} avaliação{chamadosPendentes.length > 1 ? 'ões' : ''} pendente{chamadosPendentes.length > 1 ? 's' : ''}
                    </h3>

                    <div className="space-y-2.5">
                        {chamadosPendentes.map((chamado) => (
                            <div
                                key={chamado.id}
                                className="bg-zinc-900/80 border border-zinc-700 rounded-lg p-3 flex justify-between items-center gap-3 overflow-hidden"
                            >
                                <div className="min-w-0">
                                    <p className="font-bold text-white text-sm truncate">
                                        {tipoUsuario === 'cliente'
                                            ? `${chamado.barbeiro_nome || 'Barbeiro'} - ${chamado.servico_nome || 'Serviço'}`
                                            : `${chamado.cliente_nome || 'Cliente'} - ${chamado.servico_nome || 'Serviço'}`}
                                    </p>
                                    <p className="text-zinc-500 text-xs">
                                        {chamado.concluido_em || chamado.data_hora_inicio
                                            ? new Date(chamado.concluido_em || chamado.data_hora_inicio).toLocaleDateString('pt-BR')
                                            : 'Data nao informada'}
                                    </p>
                                </div>
                                <button
                                    onClick={() => handleAvaliarClick(chamado)}
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

            {/* Lista de Avaliações */}
            {carregando ? (
                <div className="text-center py-12">
                    <div className="inline-block">
                        <div className="w-8 h-8 border-4 border-orange-500 border-t-transparent rounded-full animate-spin" />
                    </div>
                    <p className="text-zinc-500 mt-3">Carregando avaliações...</p>
                </div>
            ) : (
                <ListaAvaliacoes avaliacoes={avaliacoes} />
            )}

            {/* Modal */}
            <AvaliacaoModal
                isOpen={modalAberta}
                onClose={() => {
                    setModalAberta(false);
                    setChamadoSelecionado(null);
                }}
                onSubmit={handleEnviarAvaliacao}
                titulo={tipoUsuario === 'cliente'
                    ? `Avaliar ${chamadoSelecionado?.barbeiro_nome || 'Barbeiro'}`
                    : `Avaliar ${chamadoSelecionado?.cliente_nome || 'Cliente'}`}
            />
        </div>
    );
}
