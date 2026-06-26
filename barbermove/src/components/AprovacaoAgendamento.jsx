import React, { useState } from 'react';
import { CheckCircle, XCircle, Clock, AlertCircle } from 'lucide-react';

export default function AprovacaoAgendamento({
    chamado,
    tipoUsuario, // 'barbeiro' ou 'barbearia'
    onAprovar,
    onRejeitar,
    _onSuggestHorario,
    isLoading = false,
    API_URL,
    token
}) {
    const [mostrarRejeitarModal, setMostrarRejeitarModal] = useState(false);
    const [motivo, setMotivo] = useState('');
    const [horarioSugerido, setHorarioSugerido] = useState('');
    const [horariosDisponiveis, setHorariosDisponiveis] = useState([]);
    const [carregandoHorarios, setCarregandoHorarios] = useState(false);

    const logErro = (mensagem, detalhe) => {
        if (import.meta.env.DEV) {
            console.error(mensagem, detalhe);
        }
    };

    // Determinar se já foi aprovado
    const jaAprovadoBarbeiro = chamado?.aprovado_barbeiro;
    const jaAprovadoBarbearia = chamado?.aprovado_barbearia;
    const statusAtual = chamado?.status;

    // Se já foi confirmado, mostrar status final
    if (statusAtual === 'confirmado') {
        return (
            <div className="bg-green-900/20 border border-green-500 rounded-xl p-6">
                <div className="flex items-center gap-3 mb-2">
                    <CheckCircle size={24} className="text-green-500" />
                    <h3 className="text-lg font-bold text-green-400">Agendamento Confirmado!</h3>
                </div>
                <p className="text-green-300 text-sm">
                    Barbeiro e barbearia aprovaram. A cadeira foi bloqueada para este horário.
                </p>
                <p className="text-green-300 text-sm mt-2">
                    Data: {new Date(chamado?.data_hora_inicio).toLocaleDateString('pt-BR')} às {new Date(chamado?.data_hora_inicio).toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' })}
                </p>
            </div>
        );
    }

    // Se foi cancelado
    if (statusAtual === 'cancelado') {
        return (
            <div className="bg-red-900/20 border border-red-500 rounded-xl p-6">
                <div className="flex items-center gap-3 mb-2">
                    <XCircle size={24} className="text-red-500" />
                    <h3 className="text-lg font-bold text-red-400">Agendamento Cancelado</h3>
                </div>
                <p className="text-red-300 text-sm">{chamado?.observacao}</p>
            </div>
        );
    }

    const handleAprovar = async () => {
        try {
            await onAprovar(chamado.id, tipoUsuario);
        } catch (err) {
            logErro('Erro ao aprovar:', err);
        }
    };

    const handleRejeitar = async () => {
        if (!motivo.trim()) {
            return;
        }

        try {
            await onRejeitar(chamado.id, motivo, horarioSugerido);
            setMostrarRejeitarModal(false);
            setMotivo('');
            setHorarioSugerido('');
        } catch (err) {
            logErro('Erro ao rejeitar:', err);
        }
    };

    const carregarHorarios = async () => {
        setCarregandoHorarios(true);
        try {
            const res = await fetch(`${API_URL}/api/v1/chamados/${chamado.id}/horarios-alternativos`, {
                headers: { 'Authorization': `Bearer ${token}` }
            });
            const data = await res.json();
            setHorariosDisponiveis(data.horarios_disponiveis || []);
        } catch (err) {
            logErro('Erro ao carregar horarios:', err);
        } finally {
            setCarregandoHorarios(false);
        }
    };

    return (
        <div className="space-y-4">
            {/* Status Atual */}
            <div className="bg-zinc-900 border border-zinc-800 rounded-xl p-4">
                <p className="text-zinc-400 text-sm mb-3">Status de Aprovação:</p>
                <div className="space-y-2">
                    {/* Aprovação Barbeiro */}
                    <div className="flex items-center justify-between">
                        <span className="text-zinc-300 text-sm">Barbeiro:</span>
                        <div className="flex items-center gap-2">
                            {jaAprovadoBarbeiro ? (
                                <>
                                    <CheckCircle size={18} className="text-green-500" />
                                    <span className="text-green-400 text-sm font-bold">Aprovado</span>
                                </>
                            ) : (
                                <>
                                    <Clock size={18} className="text-yellow-500" />
                                    <span className="text-yellow-400 text-sm">Aguardando</span>
                                </>
                            )}
                        </div>
                    </div>

                    {/* Aprovação Barbearia */}
                    <div className="flex items-center justify-between">
                        <span className="text-zinc-300 text-sm">Barbearia:</span>
                        <div className="flex items-center gap-2">
                            {jaAprovadoBarbearia ? (
                                <>
                                    <CheckCircle size={18} className="text-green-500" />
                                    <span className="text-green-400 text-sm font-bold">Aprovado</span>
                                </>
                            ) : (
                                <>
                                    <Clock size={18} className="text-yellow-500" />
                                    <span className="text-yellow-400 text-sm">Aguardando</span>
                                </>
                            )}
                        </div>
                    </div>
                </div>
            </div>

            {/* Aviso */}
            <div className="flex gap-2 bg-blue-900/20 border border-blue-500 rounded-lg p-3">
                <AlertCircle size={18} className="text-blue-400 flex-shrink-0 mt-0.5" />
                <p className="text-blue-300 text-sm">
                    {tipoUsuario === 'barbeiro'
                        ? 'Como barbeiro, você precisa aprovar este agendamento. A barbearia também deve aprovar.'
                        : 'Como dono da barbearia, você precisa aprovar este agendamento. O barbeiro também deve aprovar.'}
                </p>
            </div>

            {/* Botões de Ação */}
            {tipoUsuario === 'barbeiro' && !jaAprovadoBarbeiro && (
                <div className="flex gap-3">
                    <button
                        onClick={handleAprovar}
                        disabled={isLoading}
                        className="flex-1 bg-green-600 hover:bg-green-700 disabled:bg-zinc-700 text-white py-3 rounded-lg font-bold flex items-center justify-center gap-2 transition-colors"
                    >
                        <CheckCircle size={18} />
                        {isLoading ? 'Aprovando...' : 'Aprovar'}
                    </button>
                    <button
                        onClick={() => { carregarHorarios(); setMostrarRejeitarModal(true); }}
                        disabled={isLoading || carregandoHorarios}
                        className="flex-1 bg-red-600 hover:bg-red-700 disabled:bg-zinc-700 text-white py-3 rounded-lg font-bold flex items-center justify-center gap-2 transition-colors"
                    >
                        <XCircle size={18} />
                        {carregandoHorarios ? 'Carregando...' : 'Rejeitar'}
                    </button>
                </div>
            )}

            {tipoUsuario === 'barbearia' && !jaAprovadoBarbearia && (
                <div className="flex gap-3">
                    <button
                        onClick={handleAprovar}
                        disabled={isLoading}
                        className="flex-1 bg-green-600 hover:bg-green-700 disabled:bg-zinc-700 text-white py-3 rounded-lg font-bold flex items-center justify-center gap-2 transition-colors"
                    >
                        <CheckCircle size={18} />
                        {isLoading ? 'Aprovando...' : 'Aprovar'}
                    </button>
                    <button
                        onClick={() => setMostrarRejeitarModal(true)}
                        disabled={isLoading}
                        className="flex-1 bg-red-600 hover:bg-red-700 disabled:bg-zinc-700 text-white py-3 rounded-lg font-bold flex items-center justify-center gap-2 transition-colors"
                    >
                        <XCircle size={18} />
                        Rejeitar
                    </button>
                </div>
            )}

            {/* Modal de Rejeição */}
            {mostrarRejeitarModal && (
                <div className="fixed inset-0 bg-black/70 flex items-center justify-center z-[9999] p-4">
                    <div className="bg-zinc-900 rounded-2xl w-full max-w-md border border-zinc-800">
                        <div className="p-6">
                            <h3 className="text-xl font-bold text-white mb-4">Rejeitar Agendamento</h3>

                            <div className="space-y-4">
                                {/* Motivo */}
                                <div>
                                    <label className="text-zinc-400 text-sm font-bold mb-2 block">
                                        Motivo da Rejeição
                                    </label>
                                    <textarea
                                        value={motivo}
                                        onChange={(e) => setMotivo(e.target.value)}
                                        placeholder="Ex: Estou indisponível neste horário"
                                        className="w-full bg-zinc-800 border border-zinc-700 rounded-lg p-3 text-white placeholder-zinc-500 outline-none focus:border-orange-500 resize-none"
                                        rows={3}
                                    />
                                </div>

                                {/* Horários Disponíveis */}
                                {horariosDisponiveis.length > 0 && (
                                    <div>
                                        <label className="text-zinc-400 text-sm font-bold mb-2 block">
                                            Sugerir Horário Alternativo
                                        </label>
                                        <select
                                            value={horarioSugerido}
                                            onChange={(e) => setHorarioSugerido(e.target.value)}
                                            className="w-full bg-zinc-800 border border-zinc-700 rounded-lg p-3 text-white outline-none focus:border-orange-500"
                                        >
                                            <option value="">Selecionar horário...</option>
                                            {horariosDisponiveis.map((horario, idx) => (
                                                <option key={idx} value={horario.data_hora}>
                                                    {new Date(horario.data_hora).toLocaleDateString('pt-BR')} às {new Date(horario.data_hora).toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' })}
                                                </option>
                                            ))}
                                        </select>
                                    </div>
                                )}
                            </div>
                        </div>

                        <div className="flex gap-3 p-6 border-t border-zinc-800">
                            <button
                                onClick={() => setMostrarRejeitarModal(false)}
                                className="flex-1 bg-zinc-800 hover:bg-zinc-700 text-white py-2 rounded-lg font-bold transition-colors"
                            >
                                Cancelar
                            </button>
                            <button
                                onClick={handleRejeitar}
                                disabled={isLoading || !motivo.trim()}
                                className="flex-1 bg-red-600 hover:bg-red-700 disabled:bg-zinc-700 text-white py-2 rounded-lg font-bold transition-colors"
                            >
                                Rejeitar
                            </button>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
}
