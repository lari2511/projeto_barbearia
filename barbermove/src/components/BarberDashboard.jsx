import React, { useState, useEffect, useCallback } from 'react';
import { Scissors, LogOut, CheckCircle, AlertCircle, Briefcase, User, Calendar, Star, ThumbsUp, MapPin, ArrowRight, Armchair, Wallet } from 'lucide-react';
import AbaPadronizadaAvaliacoes from './AbaPadronizadaAvaliacoes';
import TelaPerfilUsuario from './TelaPerfilUsuario';
import CadeirasDisponíveisComponent from './CadeirasDisponíveisComponent';

export default function BarberDashboard({ token, logout, notify, API_URL }) {
    const [jobs, setJobs] = useState([]); // Novos chamados - vazio até carregar
    const [ongoingJobs, setOngoingJobs] = useState([]); // Atendimentos em andamento
    const [user, setUser] = useState(null);
    const [userData, setUserData] = useState(null);
    const [tab, setTab] = useState('trabalhos'); // 'trabalhos' | 'agenda' | 'aprovar' | 'avaliar' | 'perfil'
    const [loading, setLoading] = useState(true);
    const [presenteNoLocal, setPresenteNoLocal] = useState(false); // Barbeiro presente no local
    const [toggleandoPresenca, setTogandoPresenca] = useState(false); // Enquanto carrega toggle de presença
    const [statusFreelancer, setStatusFreelancer] = useState('offline'); // 'offline', 'online', 'presente'
    const [barbeariasDisponiveis, setBarbeariasDisponiveis] = useState([]); // Lista de barbearias para selecionar
    const [barbeariaSelecionada, setBarbeariaSelecionada] = useState(null); // Barbearia selecionada para modo presente
    const [mostrarSeletorBarbearia, setMostrarSeletorBarbearia] = useState(false);
    const [cadeirasAcionadas, setCadeirasAcionadas] = useState([]); // Cadeiras disponíveis próximas
    const [loadingCadeiras, setLoadingCadeiras] = useState(false);
    const [cadeiraOcupada, setCadeiraOcupada] = useState(null); // Cadeira que o barbeiro está ocupando

    const sincronizarAgendamentos = useCallback(async () => {
        try {
            setLoading(true);

            const resNovos = await fetch(`${API_URL}/api/v1/chamados/abertos`, {
                headers: { 'Authorization': `Bearer ${token}` }
            });
            const novos = resNovos.ok ? await resNovos.json() : [];
            setJobs(Array.isArray(novos) ? novos : []);

            const resAgendados = await fetch(`${API_URL}/api/v1/barbeiro/agendamentos/meus`, {
                headers: { 'Authorization': `Bearer ${token}` }
            });

            if (resAgendados.ok) {
                const agendados = await resAgendados.json();
                const emAndamento = Array.isArray(agendados)
                    ? agendados.filter(ag => ag.status === 'confirmado')
                    : [];
                setOngoingJobs(emAndamento);
            } else {
                setOngoingJobs([]);
            }
        } catch (err) {
            console.error('Erro ao carregar agendamentos:', err);
            setJobs([]);
            setOngoingJobs([]);
        } finally {
            setLoading(false);
        }
    }, [API_URL, token]);

    // Carregar agendamentos do backend
    useEffect(() => {
        if (token) {
            sincronizarAgendamentos();
            // Recarregar a cada 10 segundos para novos chamados
            const interval = setInterval(sincronizarAgendamentos, 10000);
            return () => clearInterval(interval);
        }
    }, [token, sincronizarAgendamentos]);

    useEffect(() => {
        fetch(`${API_URL}/api/v1/documentos/status`, {
            headers: {'Authorization': `Bearer ${token}`}
        })
        .then(r => r.json())
        .then(data => {
            setUser(data);
            // Carregar status de presença
            setPresenteNoLocal(data.presente_em_local || false);
            setUserData(data);
        })
        .catch(() => {});

        fetch(`${API_URL}/api/v1/usuarios/perfil-completo`, {
            headers: {'Authorization': `Bearer ${token}`}
        })
        .then(r => {
            if (!r.ok) throw new Error('Erro');
            return r.json();
        })
        .then(data => {
            if (data && data.id) {
                setUserData(data);
                setPresenteNoLocal(data.presente_em_local || false);
                if (data.presente_em_local && data.barbearia_atual_id) {
                    setStatusFreelancer('presente');
                    setBarbeariaSelecionada(data.barbearia_atual_id);
                } else if (data.online_regiao) {
                    setStatusFreelancer('online');
                } else {
                    setStatusFreelancer('offline');
                }
            }
        })
        .catch(() => {});
    }, [API_URL, token]);

    // Carregar cadeiras acionadas próximas
    const carregarCadeirasAcionadas = useCallback(async () => {
        try {
            setLoadingCadeiras(true);
            const res = await fetch(`${API_URL}/api/v1/cadeiras/acionadas/proximas`, {
                headers: { 'Authorization': `Bearer ${token}` }
            });
            if (res.ok) {
                const data = await res.json();
                setCadeirasAcionadas(Array.isArray(data) ? data : []);
            } else {
                setCadeirasAcionadas([]);
            }
        } catch (_err) {
            console.error('Erro ao carregar cadeiras');
            setCadeirasAcionadas([]);
        } finally {
            setLoadingCadeiras(false);
        }
    }, [API_URL, token]);

    useEffect(() => {
        if (token && tab === 'trabalhos') {
            carregarCadeirasAcionadas();
            // Atualizar a cada 30s
            const interval = setInterval(carregarCadeirasAcionadas, 30000);
            return () => clearInterval(interval);
        }
    }, [tab, token, carregarCadeirasAcionadas]);

    const ocuparCadeira = async (cadeiraId) => {
        try {
            const res = await fetch(`${API_URL}/api/v1/cadeiras/${cadeiraId}/aceitar`, {
                method: 'POST',
                headers: { 'Authorization': `Bearer ${token}` }
            });
            
            if (res.ok) {
                const data = await res.json();
                notify(data.message || '✅ Cadeira bloqueada automaticamente! Agora você está trabalhando nela.', 'success');
                setCadeiraOcupada(data.cadeira);
                carregarCadeirasAcionadas(); // Recarregar lista
                // Atualizar status para PRESENTE automaticamente
                setStatusFreelancer('presente');
                setPresenteNoLocal(true);
            } else {
                const error = await res.json();
                notify(error.detail || 'Erro ao aceitar cadeira', 'error');
            }
        } catch (err) {
            console.error('Erro:', err);
            notify('Erro ao conectar com servidor', 'error');
        }
    };

    const desocuparCadeira = async () => {
        if (!cadeiraOcupada) return;
        
        try {
            const res = await fetch(`${API_URL}/api/v1/cadeiras/${cadeiraOcupada.id}/desocupar`, {
                method: 'POST',
                headers: { 'Authorization': `Bearer ${token}` }
            });
            
            if (res.ok) {
                const data = await res.json();
                notify(data.message || 'Cadeira liberada com sucesso!', 'success');
                setCadeiraOcupada(null);
                carregarCadeirasAcionadas(); // Recarregar lista
                // Voltar para OFFLINE
                await alterarStatus('offline');
            } else {
                const error = await res.json();
                notify(error.detail || 'Erro ao liberar cadeira', 'error');
            }
        } catch (err) {
            console.error('Erro:', err);
            notify('Erro ao conectar com servidor', 'error');
        }
    };

    const acceptJob = async (id) => {
        try {
            const response = await fetch(`${API_URL}/api/v1/chamados/${id}/aceitar`, {
                method: 'PUT',
                headers: { 'Authorization': `Bearer ${token}` }
            });

            if (response.ok) {
                notify("Trabalho aceito! ✓", "success");
                // Move o job de jobs para ongoingJobs
                const acceptedJob = jobs.find(j => j.id === id);
                if (acceptedJob) {
                    setOngoingJobs(prev => [...prev, { ...acceptedJob, status: 'confirmado' }]);
                }
                setJobs(prevJobs => prevJobs.filter(j => j.id !== id));

                // Sincronizar com backend para evitar inconsistência visual
                sincronizarAgendamentos();
            } else {
                const errorData = await response.json().catch(() => ({}));
                notify(errorData.detail || "Erro ao aceitar trabalho", "error");
            }
        } catch (_err) {
            notify("Erro ao conectar com servidor", "error");
        }
    };

    const rejectJob = async (id) => {
        try {
            const response = await fetch(`${API_URL}/api/v1/chamados/${id}/rejeitar`, {
                method: 'PUT',
                headers: { 'Authorization': `Bearer ${token}` }
            });

            if (response.ok) {
                notify("Agendamento recusado", "success");
                setJobs(prevJobs => prevJobs.filter(j => j.id !== id));
                sincronizarAgendamentos();
            } else {
                notify("Erro ao recusar agendamento", "error");
            }
        } catch (_err) {
            notify("Erro ao conectar com servidor", "error");
        }
    };

    const finalizeJob = async (id) => {
        try {
            const response = await fetch(`${API_URL}/api/v1/chamados/${id}/finalizar`, {
                method: 'PUT',
                headers: { 'Authorization': `Bearer ${token}` }
            });

            if (response.ok) {
                notify("Corte finalizado! ✓", "success");
                setOngoingJobs(prevJobs => prevJobs.filter(j => j.id !== id));
                // Recarrega chamados abertos imediatamente para evitar sumiço visual
                // quando ainda existem solicitações pendentes para aceitar/recusar.
                sincronizarAgendamentos();
            } else {
                const errorData = await response.json().catch(() => ({}));
                notify(errorData.detail || "Erro ao finalizar corte", "error");
            }
        } catch (_err) {
            notify("Erro ao conectar com servidor", "error");
        }
    };

    // Carregar barbearias disponíveis
    useEffect(() => {
        const carregarBarbearias = async () => {
            try {
                const res = await fetch(`${API_URL}/api/v1/barbearias/proximas?raio_km=50`, {
                    headers: { 'Authorization': `Bearer ${token}` }
                });
                if (res.ok) {
                    const data = await res.json();
                    const lista = Array.isArray(data) ? data : (Array.isArray(data?.barbearias) ? data.barbearias : []);
                    if (lista.length > 0) {
                        setBarbeariasDisponiveis(lista);
                        return;
                    }
                }

                // Fallback para quando não há localização cadastrada no perfil
                const fallbackRes = await fetch(`${API_URL}/api/v1/barbearias/todas-aprovadas`, {
                    headers: { 'Authorization': `Bearer ${token}` }
                });
                if (fallbackRes.ok) {
                    const fallbackData = await fallbackRes.json();
                    const fallbackLista = Array.isArray(fallbackData)
                        ? fallbackData
                        : (Array.isArray(fallbackData?.barbearias) ? fallbackData.barbearias : []);
                    setBarbeariasDisponiveis(fallbackLista);
                } else {
                    setBarbeariasDisponiveis([]);
                }
            } catch (err) {
                console.error('Erro ao carregar barbearias:', err);
                setBarbeariasDisponiveis([]);
            }
        };
        if (token) carregarBarbearias();
    }, [API_URL, token]);

    // Função para alterar status do freelancer
    const alterarStatus = async (novoStatus, barbeariaId = null) => {
        try {
            setTogandoPresenca(true);
            
            // Mapear status do frontend para backend
            const statusMap = {
                'offline': 'offline',
                'online': 'online_region',
                'presente': 'present_local'
            };
            
            const statusBackend = statusMap[novoStatus] || novoStatus;
            
            const response = await fetch(`${API_URL}/api/v1/barbeiro/status`, {
                method: 'PUT',
                headers: { 
                    'Authorization': `Bearer ${token}`,
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    status: statusBackend,
                    barbearia_id: barbeariaId
                })
            });

            if (response.ok) {
                const data = await response.json();
                setStatusFreelancer(novoStatus);
                setPresenteNoLocal(data.presente_em_local);
                setBarbeariaSelecionada(data.barbearia_atual_id || barbeariaId || null);
                
                const mensagens = {
                    'offline': '😴 Você está OFFLINE (não recebe chamados)',
                    'online': '🌍 Você está ONLINE (recebe chamados da região)',
                    'presente': `🏢 Você está PRESENTE na barbearia`
                };
                
                notify(mensagens[novoStatus] || 'Status atualizado', 'success');
                setMostrarSeletorBarbearia(false);
                sincronizarAgendamentos();
            } else {
                const error = await response.json().catch(() => ({}));
                notify(error.detail || 'Erro ao alterar status', 'error');
            }
        } catch (err) {
            console.error('Erro:', err);
            notify('Erro ao conectar com servidor', 'error');
        } finally {
            setTogandoPresenca(false);
        }
    };

    const _togglePresenca = async () => {
        // Mantido para compatibilidade com código legado
        await alterarStatus(presenteNoLocal ? 'offline' : 'online');
    };

    return (
        <div className="bg-black h-full w-full max-w-full overflow-hidden flex flex-col text-white font-sans">
            {/* HEADER FIXO */}
            <div className="p-2 sm:p-4 flex justify-between items-center border-b border-zinc-800 bg-black/80 backdrop-blur-md z-20 flex-shrink-0">
                <div className="flex items-center gap-2">
                    <h1 className="text-base sm:text-xl font-bold flex items-center gap-2">
                        <Scissors size={18} className="text-orange-500"/> Barbeiro
                    </h1>
                    {user?.documento_verificado && (
                        <CheckCircle size={14} className="text-blue-500 fill-blue-500" />
                    )}
                </div>
                <button onClick={logout} className="text-zinc-500 hover:text-white"><LogOut size={18}/></button>
            </div>

            {/* CONTEÚDO PRINCIPAL - SÓ UMA ABA DE CADA VEZ */}
            <div className="flex-1 overflow-y-auto pb-16">
                
                {/* === ABA 1: TRABALHOS === */}
                {tab === 'trabalhos' && (
                    <div className="p-2 sm:p-4 space-y-3">
                        {/* 🔘 3 BOTÕES DE STATUS */}
                        <div className="bg-zinc-900/50 border border-zinc-800 p-3 rounded-lg space-y-2">
                            <h3 className="text-xs font-bold text-zinc-400 uppercase mb-2">Status Operacional</h3>
                            
                            <div className="grid grid-cols-3 gap-2">
                                {/* OFFLINE */}
                                <button
                                    onClick={() => alterarStatus('offline')}
                                    disabled={toggleandoPresenca}
                                    className={`py-2 px-3 rounded-lg font-bold text-xs transition flex flex-col items-center justify-center gap-1 ${
                                        statusFreelancer === 'offline'
                                            ? 'bg-red-600 text-white border-2 border-red-400'
                                            : 'bg-zinc-800 text-zinc-400 border border-zinc-700 hover:bg-zinc-700'
                                    } ${toggleandoPresenca ? 'opacity-50 cursor-not-allowed' : ''}`}
                                >
                                    <div className={`h-2 w-2 rounded-full ${statusFreelancer === 'offline' ? 'bg-white' : 'bg-zinc-600'}`}></div>
                                    OFFLINE
                                </button>

                                {/* DISPONÍVEL */}
                                <button
                                    onClick={() => statusFreelancer === 'presente' ? alterarStatus('presente', barbeariaSelecionada) : alterarStatus('online')}
                                    disabled={toggleandoPresenca}
                                    className={`py-2 px-3 rounded-lg font-bold text-xs transition flex flex-col items-center justify-center gap-1 ${
                                        statusFreelancer === 'online' || statusFreelancer === 'presente'
                                            ? 'bg-green-600 text-white border-2 border-green-400'
                                            : 'bg-zinc-800 text-zinc-400 border border-zinc-700 hover:bg-zinc-700'
                                    } ${toggleandoPresenca ? 'opacity-50 cursor-not-allowed' : ''}`}
                                >
                                    <div className={`h-2 w-2 rounded-full ${statusFreelancer === 'online' || statusFreelancer === 'presente' ? 'bg-white animate-pulse' : 'bg-zinc-600'}`}></div>
                                    {statusFreelancer === 'presente' ? 'DISPONÍVEL AQUI' : 'DISPONÍVEL'}
                                </button>

                                {/* PRESENTE ou SAIR */}
                                {statusFreelancer === 'presente' ? (
                                    <button
                                        onClick={() => alterarStatus('online')}
                                        disabled={toggleandoPresenca}
                                        className={`py-2 px-3 rounded-lg font-bold text-xs transition flex flex-col items-center justify-center gap-1 bg-yellow-600 hover:bg-yellow-700 text-white border-2 border-yellow-400 ${toggleandoPresenca ? 'opacity-50 cursor-not-allowed' : ''}`}
                                    >
                                        <div className="h-2 w-2 rounded-full bg-white"></div>
                                        SAIR
                                    </button>
                                ) : (
                                    <button
                                        onClick={() => setMostrarSeletorBarbearia(true)}
                                        disabled={toggleandoPresenca}
                                        className={`py-2 px-3 rounded-lg font-bold text-xs transition flex flex-col items-center justify-center gap-1 ${
                                            statusFreelancer === 'presente'
                                                ? 'bg-blue-600 text-white border-2 border-blue-400'
                                                : 'bg-zinc-800 text-zinc-400 border border-zinc-700 hover:bg-zinc-700'
                                        } ${toggleandoPresenca ? 'opacity-50 cursor-not-allowed' : ''}`}
                                    >
                                        <div className={`h-2 w-2 rounded-full ${statusFreelancer === 'presente' ? 'bg-white animate-pulse' : 'bg-zinc-600'}`}></div>
                                        PRESENTE
                                    </button>
                                )}
                            </div>

                            {/* Indicador de status atual */}
                            <div className="text-center mt-2 p-2 bg-zinc-800/50 rounded">
                                <p className="text-xs text-zinc-300">
                                    {statusFreelancer === 'offline' && '🔴 Não recebe chamados'}
                                    {statusFreelancer === 'online' && '🟢 Disponível para trabalhar em qualquer barbearia'}
                                    {statusFreelancer === 'presente' && '🔵 Trabalhando em uma barbearia específica'}
                                </p>
                            </div>

                            {toggleandoPresenca && (
                                <div className="flex items-center justify-center gap-2 py-2">
                                    <div className="w-4 h-4 border-2 border-orange-500 border-t-transparent rounded-full animate-spin"></div>
                                    <span className="text-xs text-zinc-400">Atualizando status...</span>
                                </div>
                            )}
                        </div>

                        {/* 📍 CADEIRAS ACIONADAS PRÓXIMAS */}
                        <div className="bg-zinc-900/50 border border-zinc-800 p-3 rounded-lg">
                            <h3 className="text-xs font-bold text-zinc-400 uppercase mb-2 flex items-center gap-2">
                                <MapPin size={14} className="text-green-500" />
                                Cadeiras Disponíveis Próximas
                            </h3>
                            
                            {/* Se já ocupou uma cadeira */}
                            {cadeiraOcupada && (
                                <div className="bg-green-900/20 border border-green-700 rounded-lg p-3 mb-3">
                                    <div className="flex items-start justify-between gap-2">
                                        <div className="flex-1">
                                            <p className="text-xs font-bold text-green-400 mb-1">✓ Você está na cadeira {cadeiraOcupada.numero}</p>
                                            <p className="text-xs text-zinc-300">{cadeiraOcupada.barbearia_nome}</p>
                                            <p className="text-[10px] text-zinc-500">{cadeiraOcupada.barbearia_endereco}</p>
                                        </div>
                                        <button
                                            onClick={desocuparCadeira}
                                            className="px-3 py-1.5 bg-red-600 hover:bg-red-700 rounded text-xs font-bold active:scale-95"
                                        >
                                            Sair
                                        </button>
                                    </div>
                                </div>
                            )}
                            
                            {loadingCadeiras ? (
                                <div className="flex items-center justify-center gap-2 py-4">
                                    <div className="w-4 h-4 border-2 border-orange-500 border-t-transparent rounded-full animate-spin"></div>
                                    <span className="text-xs text-zinc-400">Buscando cadeiras...</span>
                                </div>
                            ) : cadeirasAcionadas.length === 0 ? (
                                <div className="text-center py-4">
                                    <p className="text-xs text-zinc-500 mb-1">📍 Nenhuma cadeira acionada próxima</p>
                                    <p className="text-[10px] text-zinc-600">Barbearias não acionaram cadeiras nas últimas 24h (raio 10km)</p>
                                </div>
                            ) : (
                                <div className="space-y-2">
                                    {cadeirasAcionadas.slice(0, 5).map(cadeira => (
                                        <div key={cadeira.id} className="bg-zinc-800/50 border border-zinc-700 rounded-lg p-2.5">
                                            <div className="flex items-start justify-between gap-2">
                                                <div className="flex-1">
                                                    <p className="text-xs font-bold text-white mb-0.5">
                                                        Cadeira {cadeira.numero} - {cadeira.barbearia_nome}
                                                    </p>
                                                    <p className="text-[10px] text-zinc-400 mb-1">{cadeira.barbearia_endereco}</p>
                                                    <div className="flex items-center gap-2">
                                                        {cadeira.distancia_km && (
                                                            <span className="text-[10px] text-green-400 font-bold">
                                                                📍 {cadeira.distancia_km} km
                                                            </span>
                                                        )}
                                                        <span className="text-[10px] text-zinc-500">
                                                            Acionada há {Math.floor((new Date() - new Date(cadeira.acionada_em)) / 60000)} min
                                                        </span>
                                                    </div>
                                                </div>
                                                {!cadeiraOcupada && (
                                                    <button
                                                        onClick={() => ocuparCadeira(cadeira.id)}
                                                        className="px-3 py-1.5 bg-green-600 hover:bg-green-700 rounded text-xs font-bold active:scale-95 flex items-center gap-1"
                                                    >
                                                        <ArrowRight size={12} />
                                                        Aceitar
                                                    </button>
                                                )}
                                            </div>
                                        </div>
                                    ))}
                                </div>
                            )}
                        </div>

                        {/* Modal Seletor de Barbearia */}
                        {mostrarSeletorBarbearia && (
                            <div className="fixed inset-0 bg-black/80 z-50 flex items-center justify-center p-4">
                                <div className="bg-zinc-900 border border-zinc-700 rounded-lg p-4 max-w-md w-full max-h-[80vh] overflow-y-auto">
                                    <h3 className="text-lg font-bold mb-3">Selecione a Barbearia</h3>
                                    <p className="text-xs text-zinc-400 mb-4">Escolha em qual barbearia você está presente:</p>
                                    
                                    <div className="space-y-2 mb-4">
                                        {barbeariasDisponiveis.map(barb => (
                                            <button
                                                key={barb.id}
                                                onClick={() => {
                                                    setBarbeariaSelecionada(barb.id);
                                                    alterarStatus('presente', barb.id);
                                                }}
                                                className="w-full p-3 bg-zinc-800 hover:bg-zinc-700 border border-zinc-700 rounded-lg text-left"
                                            >
                                                <p className="font-bold text-sm">{barb.nome}</p>
                                                <p className="text-xs text-zinc-400">{barb.endereco}</p>
                                            </button>
                                        ))}
                                        {barbeariasDisponiveis.length === 0 && (
                                            <p className="text-xs text-zinc-500 text-center py-3">
                                                Nenhuma barbearia com cadeira disponivel encontrada.
                                            </p>
                                        )}
                                    </div>

                                    <button
                                        onClick={() => setMostrarSeletorBarbearia(false)}
                                        className="w-full py-2 bg-zinc-700 hover:bg-zinc-600 rounded-lg text-sm font-bold"
                                    >
                                        Cancelar
                                    </button>
                                </div>
                            </div>
                        )}

                        {user && !user.documento_verificado && (
                            <div className="bg-yellow-600/10 border border-yellow-600/30 p-2 rounded-lg flex items-center gap-2">
                                <AlertCircle size={14} className="text-yellow-500"/>
                                <span className="text-yellow-400 text-xs">Verificação pendente</span>
                            </div>
                        )}

                        <h2 className="text-sm font-bold text-zinc-400 uppercase">Novos Chamados</h2>
                        <div className="space-y-2 pb-20">
                            {loading ? (
                                <div className="text-center py-8">
                                    <div className="w-6 h-6 border-3 border-orange-500 border-t-transparent rounded-full animate-spin mx-auto mb-2"></div>
                                    <p className="text-zinc-500 text-xs">Buscando chamados...</p>
                                </div>
                            ) : jobs && jobs.length > 0 ? jobs.map(job => (
                                <div key={job.id} className="bg-gradient-to-br from-orange-900/20 to-orange-800/10 border border-orange-500/30 p-3 rounded-lg">
                                    <div className="flex justify-between items-start gap-2 mb-2">
                                        <div className="flex-1 min-w-0">
                                            <p className="font-bold text-sm truncate">{job.nome_cliente || job.cliente || 'Cliente'}</p>
                                            <p className="text-xs text-zinc-400">{job.descricao || job.servico || 'Serviço'} • R$ {job.valor || 0}</p>
                                            {job.data_hora_inicio && <p className="text-xs text-orange-400 mt-1">{new Date(job.data_hora_inicio).toLocaleString('pt-BR')}</p>}
                                        </div>
                                    </div>
                                    <div className="flex gap-2 w-full">
                                        <button onClick={() => acceptJob(job.id)} className="flex-1 bg-orange-600 hover:bg-orange-700 text-white text-xs px-2 py-2 rounded font-bold transition">
                                            ✓ Aceitar
                                        </button>
                                        <button onClick={() => rejectJob(job.id)} className="flex-1 bg-red-600 hover:bg-red-700 text-white text-xs px-2 py-2 rounded font-bold transition">
                                            ✕ Recusar
                                        </button>
                                    </div>
                                </div>
                            )) : (
                                <p className="text-zinc-600 text-center py-8 text-xs">Nenhum chamado</p>
                            )}
                        </div>

                        {/* Atendimentos em andamento */}
                        <h2 className="text-sm font-bold text-zinc-400 uppercase mt-6">Atendimentos em Andamento</h2>
                        <div className="space-y-2 pb-20">
                            {ongoingJobs && ongoingJobs.length > 0 ? ongoingJobs.map(job => (
                                <div key={job.id} className="bg-gradient-to-br from-green-900/20 to-green-800/10 border border-green-500/30 p-3 rounded-lg">
                                    <div className="flex justify-between items-start gap-2 mb-2">
                                        <div className="flex-1 min-w-0">
                                            <p className="text-xs text-green-400 font-bold">✓ EM ANDAMENTO</p>
                                            <p className="font-bold text-sm truncate mt-1">{job.cliente_nome || job.cliente || 'Cliente'}</p>
                                            <p className="text-xs text-zinc-400">{job.servico_nome || job.servico || 'Serviço'} • R$ {job.valor || 0}</p>
                                            {job.data_hora_inicio && <p className="text-xs text-green-300 mt-1">{new Date(job.data_hora_inicio).toLocaleString('pt-BR')}</p>}
                                        </div>
                                    </div>
                                    <button onClick={() => finalizeJob(job.id)} className="w-full bg-green-600 hover:bg-green-700 text-white text-xs px-2 py-2 rounded font-bold transition">
                                        ✓ Finalizar Corte
                                    </button>
                                </div>
                            )) : (
                                <p className="text-zinc-600 text-center py-4 text-xs">Nenhum atendimento em andamento</p>
                            )}
                        </div>
                    </div>
                )}

                {/* === ABA 2: AGENDA === */}
                {tab === 'agenda' && (
                    <div className="p-2 sm:p-4 pb-20">
                        <h2 className="text-sm font-bold text-zinc-400 uppercase mb-4">Atendimentos em Andamento</h2>
                        {ongoingJobs && ongoingJobs.length > 0 ? (
                            <div className="space-y-2">
                                {ongoingJobs.map(job => (
                                    <div key={job.id} className="bg-gradient-to-br from-green-900/20 to-green-800/10 border border-green-500/30 p-3 rounded-lg">
                                        <div className="flex justify-between items-start gap-2 mb-2">
                                            <div className="flex-1 min-w-0">
                                                <p className="text-xs text-green-400 font-bold">✓ EM ANDAMENTO</p>
                                                <p className="font-bold text-sm truncate mt-1">{job.cliente_nome || job.cliente || 'Cliente'}</p>
                                                <p className="text-xs text-zinc-400">{job.servico_nome || job.servico || 'Serviço'} • R$ {job.valor || 0}</p>
                                                {job.data_hora_inicio && <p className="text-xs text-green-300 mt-1">{new Date(job.data_hora_inicio).toLocaleString('pt-BR')}</p>}
                                            </div>
                                        </div>
                                        <button onClick={() => finalizeJob(job.id)} className="w-full bg-green-600 hover:bg-green-700 text-white text-xs px-2 py-2 rounded font-bold transition">
                                            ✓ Finalizar Corte
                                        </button>
                                    </div>
                                ))}
                            </div>
                        ) : (
                            <p className="text-zinc-600 text-center py-12 text-xs">Nenhum atendimento em andamento</p>
                        )}
                    </div>
                )}

                {/* === ABA 3: APROVAR === */}
                {tab === 'aprovar' && (
                    <div className="p-2 sm:p-4">
                        <h2 className="text-sm font-bold text-zinc-400 uppercase mb-4">Aprovações</h2>
                        <p className="text-zinc-600 text-center py-12 text-xs">Nenhuma aprovação pendente</p>
                    </div>
                )}

                {/* === ABA 4: AVALIAR === */}
                {tab === 'avaliar' && (
                    <div className="p-2 sm:p-4 pb-20">
                        {userData ? (
                            <AbaPadronizadaAvaliacoes
                                usuarioId={userData.id}
                                tipoUsuario="barbeiro"
                                nomeUsuario={userData.nome}
                                API_URL={API_URL}
                                token={token}
                                notify={notify}
                            />
                        ) : (
                            <div className="text-center py-10">
                                <div className="w-6 h-6 border-3 border-orange-500 border-t-transparent rounded-full animate-spin mx-auto mb-2"></div>
                                <p className="text-zinc-500 text-xs">Carregando...</p>
                            </div>
                        )}
                    </div>
                )}

                {/* === ABA 5: PERFIL === */}
                {tab === 'perfil' && (
                    <TelaPerfilUsuario userType="barbeiro" token={token} onLogout={logout} onNotify={notify} />
                )}

                {/* === ABA 6: CADEIRAS DISPONÍVEIS === */}
                {tab === 'cadeiras' && (
                    <CadeirasDisponíveisComponent token={token} API_URL={API_URL} notify={notify} />
                )}

                {/* === ABA 7: CARTEIRA === */}
                {tab === 'carteira' && (
                    <TelaCarteiraFreelancer 
                        barbeiroDashId={userData?.id}
                        token={token} 
                        API_URL={API_URL} 
                        onNotify={notify} 
                    />
                )}

            </div>

            {/* NAVBAR FIXA INFERIOR - 5 BOTÕES */}
            <div className="fixed bottom-0 left-1/2 -translate-x-1/2 w-full max-w-[400px] h-16 bg-zinc-950/98 backdrop-blur-lg border-t border-zinc-800 flex justify-around items-center z-50">
                <button
                    onClick={() => setTab('trabalhos')}
                    className={`flex flex-col items-center justify-center gap-0.5 h-full flex-1 text-center transition-colors ${
                        tab === 'trabalhos' ? 'text-orange-500 bg-orange-500/5' : 'text-zinc-500 hover:text-zinc-400'
                    }`}
                >
                    <Briefcase size={14} />
                    <span className="text-[7px] font-bold">Trabalhos</span>
                </button>
                
                <button
                    onClick={() => setTab('agenda')}
                    className={`flex flex-col items-center justify-center gap-0.5 h-full flex-1 text-center transition-colors ${
                        tab === 'agenda' ? 'text-orange-500 bg-orange-500/5' : 'text-zinc-500 hover:text-zinc-400'
                    }`}
                >
                    <Calendar size={14} />
                    <span className="text-[7px] font-bold">Agenda</span>
                </button>
                
                <button
                    onClick={() => setTab('aprovar')}
                    className={`flex flex-col items-center justify-center gap-0.5 h-full flex-1 text-center transition-colors ${
                        tab === 'aprovar' ? 'text-orange-500 bg-orange-500/5' : 'text-zinc-500 hover:text-zinc-400'
                    }`}
                >
                    <ThumbsUp size={14} />
                    <span className="text-[7px] font-bold">Aprovar</span>
                </button>
                
                <button
                    onClick={() => setTab('avaliar')}
                    className={`flex flex-col items-center justify-center gap-0.5 h-full flex-1 text-center transition-colors ${
                        tab === 'avaliar' ? 'text-orange-500 bg-orange-500/5' : 'text-zinc-500 hover:text-zinc-400'
                    }`}
                >
                    <Star size={14} />
                    <span className="text-[7px] font-bold">Avaliar</span>
                </button>
                
                <button
                    onClick={() => setTab('perfil')}
                    className={`flex flex-col items-center justify-center gap-0.5 h-full flex-1 text-center transition-colors ${
                        tab === 'perfil' ? 'text-orange-500 bg-orange-500/5' : 'text-zinc-500 hover:text-zinc-400'
                    }`}
                >
                    <User size={14} />
                    <span className="text-[7px] font-bold">Perfil</span>
                </button>

                <button
                    onClick={() => setTab('cadeiras')}
                    className={`flex flex-col items-center justify-center gap-0.5 h-full flex-1 text-center transition-colors ${
                        tab === 'cadeiras' ? 'text-orange-500 bg-orange-500/5' : 'text-zinc-500 hover:text-zinc-400'
                    }`}
                >
                    <Armchair size={14} />
                    <span className="text-[7px] font-bold">Cadeiras</span>
                </button>

                <button
                    onClick={() => setTab('carteira')}
                    className={`flex flex-col items-center justify-center gap-0.5 h-full flex-1 text-center transition-colors ${
                        tab === 'carteira' ? 'text-green-500 bg-green-500/5' : 'text-zinc-500 hover:text-zinc-400'
                    }`}
                >
                    <Wallet size={14} />
                    <span className="text-[7px] font-bold">Carteira</span>
                </button>
            </div>
        </div>
    );
}
