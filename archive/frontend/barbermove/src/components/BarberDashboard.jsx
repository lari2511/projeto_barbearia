import React, { useState, useEffect, useCallback, useRef } from 'react';
import ScreenWrapper from './ScreenWrapper';
import { Scissors, LogOut, CheckCircle, AlertCircle, Briefcase, User, Calendar, Star, MapPin, ArrowRight } from 'lucide-react';
import AbaPadronizadaAvaliacoes from './AbaPadronizadaAvaliacoes';
import ChatRoom from './ChatRoom';
import TrackingPanel from './TrackingPanel';
import TelaPerfilUsuario from './TelaPerfilUsuario';
import TelaRotasAtivos from './TelaRotasAtivos';

export default function BarberDashboard({ token, logout, notify, API_URL, onChamadoAceito }) {
    const TABS_VALIDAS = ['trabalhos', 'agenda', 'avaliar', 'perfil'];
    const [jobs, setJobs] = useState([]); // Novos chamados - vazio até carregar
    const [ongoingJobs, setOngoingJobs] = useState([]); // Atendimentos em andamento
    const [user, setUser] = useState(null);
    const [userData, setUserData] = useState(null);
    const [tab, setTab] = useState(() => {
        if (typeof window === 'undefined') return 'trabalhos';
        const tabSalva = localStorage.getItem('barbeiro_dashboard_tab') || 'trabalhos';
        return TABS_VALIDAS.includes(tabSalva) ? tabSalva : 'trabalhos';
    }); // 'trabalhos' | 'agenda' | 'avaliar' | 'perfil'
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
    const [chatTarget, setChatTarget] = useState(null);
    const [promptFinalizacaoJob, setPromptFinalizacaoJob] = useState(null);

    // Timers por atendimento (cronômetro)
    const [timers, setTimers] = useState({}); // { [jobId]: { running, startTs, elapsed } }
    const timerIntervalsRef = useRef({});
    const promptTimeoutsRef = useRef({});
    const promptedRef = useRef({});

    const formatElapsed = (ms) => {
        if (!ms || ms <= 0) return '00:00';
        const total = Math.floor(ms / 1000);
        const mm = String(Math.floor(total / 60)).padStart(2, '0');
        const ss = String(total % 60).padStart(2, '0');
        return `${mm}:${ss}`;
    };

    const startTimer = (jobId) => {
        setTimers(prev => {
            const existing = prev[jobId] || { running: false, startTs: null, elapsed: 0 };
            const startTs = Date.now() - (existing.elapsed || 0);
            return { ...prev, [jobId]: { ...existing, running: true, startTs } };
        });

        if (timerIntervalsRef.current[jobId]) return;
        timerIntervalsRef.current[jobId] = setInterval(() => {
            setTimers(prev => {
                const t = prev[jobId];
                if (!t) return prev;
                const elapsed = Date.now() - t.startTs;
                return { ...prev, [jobId]: { ...t, elapsed } };
            });
        }, 1000);
    };

    const stopTimer = (jobId) => {
        const interval = timerIntervalsRef.current[jobId];
        if (interval) {
            clearInterval(interval);
            delete timerIntervalsRef.current[jobId];
        }
        setTimers(prev => ({ ...prev, [jobId]: { ...(prev[jobId] || {}), running: false } }));
    };

    useEffect(() => {
        return () => {
            // cleanup intervals
            Object.values(timerIntervalsRef.current).forEach((ival) => clearInterval(ival));
            timerIntervalsRef.current = {};
            Object.values(promptTimeoutsRef.current).forEach((timeoutId) => clearTimeout(timeoutId));
            promptTimeoutsRef.current = {};
        };
    }, []);

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
                    ? agendados.filter(ag => ['confirmado', 'em_atendimento'].includes((ag.status || '').toString().toLowerCase()))
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

    // Quando houver agendamentos em andamento, garantir que timers sejam inicializados
    useEffect(() => {
        // inicializar timers para atendimentos em andamento a partir do servidor
        ongoingJobs.forEach(job => {
            try {
                if (!job || !job.id) return;
                // somente para agendamentos em atendimento/confirmado
                const status = (job.status || '').toString().toLowerCase();
                if (!['em_atendimento', 'confirmado'].includes(status)) return;

                // se servidor informou data_hora_inicio, usar como referência
                const serverStartIso = job.data_hora_inicio || job.data_hora_inicio_iso || job.data_hora_inicio && job.data_hora_inicio;
                const servDur = job.duracao_minutos || (job.servico && job.servico.duracao_minutos) || 30;

                if (serverStartIso) {
                    const serverStart = new Date(serverStartIso).getTime();
                    const elapsed = Math.max(0, Date.now() - serverStart);
                    setTimers(prev => ({ ...prev, [job.id]: { running: true, startTs: Date.now() - elapsed, elapsed } }));
                    // já cria o intervalo se não existir
                    if (!timerIntervalsRef.current[job.id]) startTimer(job.id);

                    // agendar prompt se ainda não agendado
                    const finishAt = serverStart + (servDur * 60000);
                    const timeLeft = finishAt - Date.now();
                    if (timeLeft <= 0) {
                        // tempo já estourou — perguntar imediatamente
                        askFinish(job);
                    } else {
                        try { if (promptTimeoutsRef.current[job.id]) clearTimeout(promptTimeoutsRef.current[job.id]); } catch(_){}
                        promptTimeoutsRef.current[job.id] = setTimeout(() => askFinish(job), timeLeft);
                    }
                } else {
                    // sem timestamp do servidor, garantir que o timer local exista
                    if (!timerIntervalsRef.current[job.id]) startTimer(job.id);
                }
            } catch (e) {
                console.error('Erro ao inicializar timer para job', job && job.id, e);
            }
        });

        // limpar timers/intervals para jobs que não estão mais em andamento
        const ongoingIds = new Set(ongoingJobs.map(j => j.id));
        Object.keys(timerIntervalsRef.current).forEach(k => {
            if (!ongoingIds.has(Number(k))) {
                try { clearInterval(timerIntervalsRef.current[k]); } catch(_){}
                delete timerIntervalsRef.current[k];
                setTimers(prev => {
                    const copy = { ...prev };
                    delete copy[k];
                    return copy;
                });
            }
        });

        // limpar prompts para jobs que terminaram
        Object.keys(promptTimeoutsRef.current).forEach(k => {
            if (!ongoingIds.has(Number(k))) {
                try { clearTimeout(promptTimeoutsRef.current[k]); } catch(_){}
                delete promptTimeoutsRef.current[k];
                delete promptedRef.current[k];
            }
        });
    }, [ongoingJobs]);

    useEffect(() => {
        if (typeof window !== 'undefined') {
            localStorage.setItem('barbeiro_dashboard_tab', tab);
        }
    }, [tab]);

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
                if (data.pode_receber_chamado_agora === true) {
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
        console.log('acceptJob called with id:', id);
        try {
            const response = await fetch(`${API_URL}/api/v1/chamados/${id}/aceitar`, {
                method: 'PUT',
                headers: { 'Authorization': `Bearer ${token}` }
            });

            if (response.ok) {
                const data = await response.json().catch(() => ({}));
                console.log('acceptJob response data:', data);
                const numeroCadeira = data?.cadeira?.numero;
                const mensagem = numeroCadeira
                    ? `Trabalho aceito! Cadeira ${numeroCadeira} reservada. ✓`
                    : "Trabalho aceito! ✓";
                notify(mensagem, "success");
                // Move o job de jobs para ongoingJobs, incluindo dados da cadeira retornada
                const acceptedJob = jobs.find(j => j.id === id);
                if (acceptedJob) {
                    const cadeiraData = data?.cadeira || {};
                    setOngoingJobs(prev => [...prev, { 
                        ...acceptedJob, 
                        status: 'confirmado',
                        cadeira_id: cadeiraData.id ?? acceptedJob.cadeira_id,
                        cadeira_numero: cadeiraData.numero ?? acceptedJob.cadeira_numero
                    }]);
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
        console.log('rejectJob called with id:', id);
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
                setPromptFinalizacaoJob(prev => (prev && prev.id === id ? null : prev));
                // Parar cronômetro local para este atendimento
                try { stopTimer(id); } catch (_) {}
                // limpar prompts/timeout relacionados
                try { if (promptTimeoutsRef.current[id]) clearTimeout(promptTimeoutsRef.current[id]); } catch(_){}
                try { delete promptTimeoutsRef.current[id]; } catch(_){}
                try { delete promptedRef.current[id]; } catch(_){}
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

    const askFinish = (job) => {
        if (!job || !job.id) return;
        if (promptFinalizacaoJob && promptFinalizacaoJob.id === job.id) return;
        promptedRef.current[job.id] = true;
        setPromptFinalizacaoJob(job);
    };

    const confirmarFinalizacaoPrompt = async () => {
        if (!promptFinalizacaoJob?.id) return;
        const id = promptFinalizacaoJob.id;
        setPromptFinalizacaoJob(null);
        await finalizeJob(id);
    };

    const adiarFinalizacaoPrompt = () => {
        if (!promptFinalizacaoJob?.id) return;
        const job = promptFinalizacaoJob;
        const id = job.id;
        setPromptFinalizacaoJob(null);
        notify('Continuando o atendimento. Vou perguntar novamente em 1 minuto.', 'info');
        try {
            if (promptTimeoutsRef.current[id]) clearTimeout(promptTimeoutsRef.current[id]);
        } catch (_) {}
        promptTimeoutsRef.current[id] = setTimeout(() => {
            promptedRef.current[id] = false;
            askFinish(job);
        }, 60 * 1000);
    };

    const iniciarCorte = async (id) => {
        try {
            const response = await fetch(`${API_URL}/api/v1/chamados/${id}/iniciar-corte`, {
                method: 'PUT',
                headers: { 'Authorization': `Bearer ${token}` }
            });

            if (response.ok) {
                notify('Corte iniciado!', 'success');
                sincronizarAgendamentos();
                // Iniciar cronômetro local para este atendimento
                try {
                    // solicitar payload do servidor para iniciar a partir de data_hora_inicio
                    const payload = await response.json().catch(() => null);
                    const serverStart = payload?.data_hora_inicio ? new Date(payload.data_hora_inicio).getTime() : Date.now();
                    const elapsed = Date.now() - serverStart;
                    setTimers(prev => ({ ...prev, [id]: { running: true, startTs: Date.now() - elapsed, elapsed } }));
                    startTimer(id);
                    // agendar prompt quando tempo do serviço terminar
                    const durMin = payload?.duracao_minutos || 30;
                    const timeLeft = Math.max(0, (serverStart + durMin * 60000) - Date.now());
                    try { if (promptTimeoutsRef.current[id]) clearTimeout(promptTimeoutsRef.current[id]); } catch(_){}
                    promptTimeoutsRef.current[id] = setTimeout(() => {
                        const job = ongoingJobs.find(j => j.id === id) || { id };
                        askFinish(job);
                    }, timeLeft);
                } catch (_) {}
            } else {
                const errorData = await response.json().catch(() => ({}));
                notify(errorData.detail || 'Não foi possível iniciar o corte', 'error');
            }
        } catch (_err) {
            notify('Erro ao conectar com servidor', 'error');
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
        <ScreenWrapper>
        <div className="min-h-[100dvh] w-full bg-[#050505] text-white font-sans flex justify-center overflow-x-hidden">
            <div className="app-container w-full min-h-[100dvh] flex flex-col overflow-x-hidden bg-[#050505] shadow-[0_0_0_1px_rgba(255,255,255,0.04)]">
            {/* HEADER FIXO */}
            <div className="sticky top-0 z-20 px-3 pt-3 pb-2 bg-[#050505]/95 backdrop-blur-xl flex-shrink-0">
                <div className="flex justify-between items-center rounded-[1.5rem] border border-zinc-800/80 bg-zinc-950/90 px-4 py-3 shadow-xl shadow-black/25">
                    <div className="flex items-center gap-2 min-w-0">
                        <h1 className="text-lg font-black tracking-tight flex items-center gap-2 truncate">
                            <Scissors size={18} className="text-orange-500"/> Barbeiro
                        </h1>
                        {user?.documento_verificado && (
                            <CheckCircle size={14} className="text-blue-500 fill-blue-500" />
                        )}
                    </div>
                    <div className="flex items-center gap-2 shrink-0">
                        <button
                            onClick={logout}
                            className="flex items-center gap-1 rounded-full border border-zinc-700 bg-zinc-900 px-3 py-1 text-[10px] font-bold text-zinc-300 hover:border-orange-500 hover:text-white"
                        >
                            <ArrowRight size={12} className="rotate-180" />
                            Início
                        </button>
                        <button onClick={logout} className="h-10 w-10 rounded-full bg-zinc-900 border border-zinc-800 flex items-center justify-center text-zinc-400 hover:text-white hover:bg-zinc-800 transition-colors"><LogOut size={18}/></button>
                    </div>
                </div>
            </div>

            {/* CONTEÚDO PRINCIPAL - SÓ UMA ABA DE CADA VEZ */}
            <div className="flex-1 overflow-visible pb-[calc(6rem+env(safe-area-inset-bottom))]">
                
                {/* === ABA 1: TRABALHOS === */}
                {tab === 'trabalhos' && (
                    <div className="p-2 sm:p-4 space-y-3 max-w-3xl mx-auto w-full">
                        {/* 🔘 3 BOTÕES DE STATUS */}
                        <div className="bm-card p-3 space-y-2">
                            <h3 className="text-xs font-bold text-zinc-400 uppercase tracking-wide mb-2">Status Operacional</h3>
                            
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
                                        <div className={`h-2 w-2 rounded-full ${statusFreelancer === 'offline' ? 'bg-zinc-100' : 'bg-zinc-600'}`}></div>
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
                                    <div className={`h-2 w-2 rounded-full ${statusFreelancer === 'online' || statusFreelancer === 'presente' ? 'bg-zinc-100 animate-pulse' : 'bg-zinc-600'}`}></div>
                                    {statusFreelancer === 'presente' ? 'DISPONÍVEL AQUI' : 'DISPONÍVEL'}
                                </button>

                                {/* PRESENTE ou SAIR */}
                                {statusFreelancer === 'presente' ? (
                                    <button
                                        onClick={() => alterarStatus('online')}
                                        disabled={toggleandoPresenca}
                                        className={`py-2 px-3 rounded-lg font-bold text-xs transition flex flex-col items-center justify-center gap-1 bg-yellow-600 hover:bg-yellow-700 text-white border-2 border-yellow-400 ${toggleandoPresenca ? 'opacity-50 cursor-not-allowed' : ''}`}
                                    >
                                        <div className="h-2 w-2 rounded-full bg-zinc-100"></div>
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
                                        <div className={`h-2 w-2 rounded-full ${statusFreelancer === 'presente' ? 'bg-zinc-100 animate-pulse' : 'bg-zinc-600'}`}></div>
                                        NO LOCAL
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

                        <TrackingPanel
                            chamado={ongoingJobs[0] || jobs[0] || null}
                            token={token}
                            API_URL={API_URL}
                            notify={notify}
                            modo="barbeiro"
                        />

                        {/* 📍 CADEIRAS ACIONADAS PRÓXIMAS */}
                        <div className="bm-card p-3">
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
                                                        <span className="text-[10px] text-zinc-400">
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
                                    <h3 className="text-lg font-bold mb-3">Selecione uma Barbearia</h3>
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

                        <h2 className="text-sm font-bold text-zinc-300 uppercase tracking-wide">Novos Chamados</h2>
                        <div className="space-y-2 pb-20 max-w-2xl mx-auto w-full">
                            {loading ? (
                                <div className="text-center py-8">
                                    <div className="w-6 h-6 border-3 border-orange-500 border-t-transparent rounded-full animate-spin mx-auto mb-2"></div>
                                    <p className="text-zinc-500 text-xs">Buscando chamados...</p>
                                </div>
                            ) : jobs && jobs.length > 0 ? jobs.map(job => (
                                <div key={job.id} className="bg-gradient-to-br from-orange-900/20 to-orange-800/10 border border-orange-500/30 p-3.5 rounded-xl overflow-hidden">
                                    <div className="flex justify-between items-start gap-2 mb-2.5">
                                        <div className="flex-1 min-w-0">
                                            <p className="font-bold text-sm truncate">{job.nome_cliente || job.cliente || 'Cliente'}</p>
                                            <p className="text-xs text-zinc-400 truncate">{job.descricao || job.servico || 'Serviço'} • R$ {job.valor || 0}</p>
                                            {job.data_hora_inicio && <p className="text-xs text-orange-400 mt-1">{new Date(job.data_hora_inicio).toLocaleString('pt-BR')}</p>}
                                        </div>
                                    </div>
                                    <div className="grid grid-cols-2 gap-2 w-full">
                                        <button onClick={() => acceptJob(job.id)} className="w-full bg-orange-600 hover:bg-orange-700 text-white text-xs px-2 py-2 rounded font-bold transition">
                                            ✓ Aceitar
                                        </button>
                                        <button onClick={() => rejectJob(job.id)} className="w-full bg-red-600 hover:bg-red-700 text-white text-xs px-2 py-2 rounded font-bold transition">
                                            ✕ Recusar
                                        </button>
                                    </div>
                                </div>
                            )) : (
                                <p className="text-zinc-600 text-center py-8 text-xs">Nenhum chamado</p>
                            )}
                        </div>

                        {/* Atendimentos em andamento */}
                        <h2 className="text-sm font-bold text-zinc-300 uppercase tracking-wide mt-6">Atendimentos em Andamento</h2>
                        <div className="space-y-2 pb-20 max-w-2xl mx-auto w-full">
                            {ongoingJobs && ongoingJobs.length > 0 ? ongoingJobs.map(job => (
                                <div key={job.id} className="bg-gradient-to-br from-green-900/20 to-green-800/10 border border-green-500/30 p-3.5 rounded-xl overflow-hidden">
                                    <div className="flex justify-between items-start gap-2 mb-2.5">
                                        <div className="flex-1 min-w-0">
                                            <p className="text-xs text-green-400 font-bold">✓ EM ANDAMENTO</p>
                                            <p className="font-bold text-sm truncate mt-1">{job.cliente_nome || job.cliente || 'Cliente'}</p>
                                            <p className="text-xs text-zinc-400 truncate">{job.servico_nome || job.servico || 'Serviço'} • R$ {job.valor || 0}</p>
                                            {(job.cadeira_numero || job.cadeira_id) && (
                                                <p className="text-xs text-orange-300 mt-1">
                                                    Cadeira {job.cadeira_numero || job.cadeira_id} reservada
                                                </p>
                                            )}
                                            {job.data_hora_inicio && <p className="text-xs text-green-300 mt-1">{new Date(job.data_hora_inicio).toLocaleString('pt-BR')}</p>}
                                        </div>
                                    </div>
                                    <div className="flex gap-2">
                                        {['aceito', 'confirmado'].includes(String(job.status || '').toLowerCase()) && (
                                            <button onClick={() => iniciarCorte(job.id)} className="flex-1 bg-blue-600 hover:bg-blue-700 text-white text-xs px-2 py-2 rounded font-bold transition">
                                                Iniciar Corte
                                            </button>
                                        )}
                                        {String(job.status || '').toLowerCase() === 'em_atendimento' && (
                                            <button onClick={() => finalizeJob(job.id)} className="flex-1 bg-green-600 hover:bg-green-700 text-white text-xs px-2 py-2 rounded font-bold transition">
                                                ✓ Finalizar Corte
                                            </button>
                                        )}
                                        <button onClick={() => setChatTarget(job.id)} className="flex-1 bg-zinc-800 hover:bg-zinc-700 text-white text-xs px-2 py-2 rounded font-bold transition">
                                            Chat
                                        </button>
                                        {typeof onChamadoAceito === 'function' && (
                                            <button onClick={() => onChamadoAceito(job.id)} className="flex-1 bg-blue-600 hover:bg-blue-700 text-white text-xs px-2 py-2 rounded font-bold transition">
                                                📍 Rastreamento
                                            </button>
                                        )}
                                    </div>
                                    <div className="mt-2 flex items-center gap-2">
                                        <div className="text-xs text-zinc-300">Tempo: <span className="font-mono text-sm">{formatElapsed(timers[job.id]?.elapsed)}</span></div>
                                        <button
                                            onClick={() => timers[job.id]?.running ? stopTimer(job.id) : startTimer(job.id)}
                                            className="px-2 py-1 bg-zinc-800 hover:bg-zinc-700 rounded text-xs text-white"
                                        >
                                            {timers[job.id]?.running ? 'Pausar' : 'Iniciar cronômetro'}
                                        </button>
                                    </div>
                                </div>
                            )) : (
                                <p className="text-zinc-600 text-center py-4 text-xs">Nenhum atendimento em andamento</p>
                            )}
                        </div>
                    </div>
                )}

                {/* === ABA 2: AGENDA === */}
                {tab === 'agenda' && (
                    <div className="p-2 sm:p-4 pb-20 max-w-3xl mx-auto w-full">
                        <h2 className="text-sm font-bold text-zinc-300 uppercase tracking-wide mb-4">Atendimentos em Andamento</h2>
                        {ongoingJobs && ongoingJobs.length > 0 ? (
                            <div className="space-y-2">
                                {ongoingJobs.map(job => (
                                    <div key={job.id} className="bg-gradient-to-br from-green-900/20 to-green-800/10 border border-green-500/30 p-3.5 rounded-xl">
                                        <div className="flex justify-between items-start gap-2 mb-2.5">
                                            <div className="flex-1 min-w-0">
                                                <p className="text-xs text-green-400 font-bold">✓ EM ANDAMENTO</p>
                                                <p className="font-bold text-sm truncate mt-1">{job.cliente_nome || job.cliente || 'Cliente'}</p>
                                                <p className="text-xs text-zinc-400">{job.servico_nome || job.servico || 'Serviço'} • R$ {job.valor || 0}</p>
                                                {(job.cadeira_numero || job.cadeira_id) && (
                                                    <p className="text-xs text-orange-300 mt-1">
                                                        Cadeira {job.cadeira_numero || job.cadeira_id} reservada
                                                    </p>
                                                )}
                                                {job.data_hora_inicio && <p className="text-xs text-green-300 mt-1">{new Date(job.data_hora_inicio).toLocaleString('pt-BR')}</p>}
                                            </div>
                                        </div>
                                        <div className="flex gap-2">
                                            {String(job.status || '').toLowerCase() === 'confirmado' && (
                                                <button onClick={() => iniciarCorte(job.id)} className="flex-1 bg-blue-600 hover:bg-blue-700 text-white text-xs px-2 py-2 rounded font-bold transition">
                                                    Iniciar Corte
                                                </button>
                                            )}
                                            {String(job.status || '').toLowerCase() === 'em_atendimento' && (
                                                <button onClick={() => finalizeJob(job.id)} className="flex-1 bg-green-600 hover:bg-green-700 text-white text-xs px-2 py-2 rounded font-bold transition">
                                                    ✓ Finalizar Corte
                                                </button>
                                            )}
                                            <button onClick={() => setChatTarget(job.id)} className="flex-1 bg-zinc-800 hover:bg-zinc-700 text-white text-xs px-2 py-2 rounded font-bold transition">
                                                Chat
                                            </button>
                                        </div>
                                        <div className="mt-2 flex items-center gap-2">
                                            <div className="text-xs text-zinc-300">Tempo: <span className="font-mono text-sm">{formatElapsed(timers[job.id]?.elapsed)}</span></div>
                                            <button
                                                onClick={() => timers[job.id]?.running ? stopTimer(job.id) : startTimer(job.id)}
                                                className="px-2 py-1 bg-zinc-800 hover:bg-zinc-700 rounded text-xs text-white"
                                            >
                                                {timers[job.id]?.running ? 'Pausar' : 'Iniciar cronômetro'}
                                            </button>
                                        </div>
                                    </div>
                                ))}
                            </div>
                        ) : (
                            <p className="text-zinc-600 text-center py-12 text-xs">Nenhum atendimento em andamento</p>
                        )}
                    </div>
                )}

                {/* === ABA 3: AVALIAR === */}
                {tab === 'avaliar' && (
                    <div className="p-2 sm:p-4 pb-20 max-w-3xl mx-auto w-full">
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

                {/* === ABA 4: PERFIL === */}
                {tab === 'perfil' && (
                    <TelaPerfilUsuario userType="barbeiro" token={token} onLogout={logout} onNotify={notify} />
                )}

                {chatTarget && (
                    <div className="fixed inset-0 z-50 bg-black/80 backdrop-blur-sm flex items-center justify-center p-2 sm:p-4">
                        <div className="w-full max-w-[96vw] sm:max-w-5xl lg:max-w-6xl h-[92vh] bg-zinc-900 border border-zinc-800 rounded-2xl p-3 sm:p-5 shadow-2xl flex flex-col">
                            <div className="flex items-center justify-between gap-3 mb-4 pb-3 border-b border-zinc-800">
                                <div>
                                    <p className="text-base sm:text-lg font-bold text-white">Chat do chamado #{chatTarget}</p>
                                    <p className="text-[11px] sm:text-xs text-zinc-400 mt-1">Área ampliada para acompanhar a conversa do cliente sem ficar presa em um quadrado pequeno</p>
                                </div>
                                <button onClick={() => setChatTarget(null)} className="text-xs text-zinc-400 hover:text-white">Fechar</button>
                            </div>
                            <div className="flex-1 min-h-0 overflow-hidden">
                                <ChatRoom chamadoId={chatTarget} token={token} API_URL={API_URL} compact={false} />
                            </div>
                        </div>
                    </div>
                )}

                {promptFinalizacaoJob && (
                    <div className="fixed inset-0 z-[60] bg-black/85 backdrop-blur-md flex items-center justify-center p-4">
                        <div className="w-full max-w-md bg-zinc-950 border border-orange-500/40 rounded-2xl shadow-2xl p-5 text-center">
                            <div className="mx-auto h-14 w-14 rounded-full bg-orange-500/15 border border-orange-500/30 flex items-center justify-center mb-4">
                                <Scissors size={24} className="text-orange-400" />
                            </div>
                            <p className="text-xs uppercase tracking-[0.3em] text-orange-300/80 mb-2">Tempo previsto encerrado</p>
                            <h3 className="text-lg font-bold text-white mb-2">Você finalizou o corte?</h3>
                            <p className="text-sm text-zinc-300 mb-4">
                                O atendimento de <span className="font-semibold text-white">{promptFinalizacaoJob.cliente_nome || promptFinalizacaoJob.cliente || 'cliente'}</span> já atingiu a duração prevista.
                            </p>
                            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                                <button
                                    onClick={adiarFinalizacaoPrompt}
                                    className="w-full rounded-xl border border-zinc-700 bg-zinc-900 px-4 py-3 text-sm font-bold text-zinc-200 hover:bg-zinc-800 transition"
                                >
                                    Ainda não
                                </button>
                                <button
                                    onClick={confirmarFinalizacaoPrompt}
                                    className="w-full rounded-xl bg-green-600 px-4 py-3 text-sm font-bold text-white hover:bg-green-700 transition"
                                >
                                    Sim, finalizar
                                </button>
                            </div>
                        </div>
                    </div>
                )}
            </div>

            {/* NAVBAR FIXA INFERIOR - 5 BOTÕES */}
            <div className="bm-bottom-nav sticky bottom-0 left-0 w-full h-[calc(4rem+env(safe-area-inset-bottom))] pb-[env(safe-area-inset-bottom)] flex justify-around items-center z-40">
                <button
                    onClick={() => setTab('trabalhos')}
                    data-active={tab === 'trabalhos'}
                    className={`bm-bottom-nav-btn flex flex-col items-center justify-center gap-0.5 h-full flex-1 text-center ${
                        tab === 'trabalhos' ? 'text-orange-500 bg-orange-500/5' : 'text-zinc-400 hover:text-zinc-200'
                    }`}
                >
                    <Briefcase size={14} />
                    <span>Trabalhos</span>
                </button>
                
                <button
                    onClick={() => setTab('agenda')}
                    data-active={tab === 'agenda'}
                    className={`bm-bottom-nav-btn flex flex-col items-center justify-center gap-0.5 h-full flex-1 text-center ${
                        tab === 'agenda' ? 'text-orange-500 bg-orange-500/5' : 'text-zinc-400 hover:text-zinc-200'
                    }`}
                >
                    <Calendar size={14} />
                    <span>Agenda</span>
                </button>
                
                <button
                    onClick={() => setTab('avaliar')}
                    data-active={tab === 'avaliar'}
                    className={`bm-bottom-nav-btn flex flex-col items-center justify-center gap-0.5 h-full flex-1 text-center ${
                        tab === 'avaliar' ? 'text-orange-500 bg-orange-500/5' : 'text-zinc-400 hover:text-zinc-200'
                    }`}
                >
                    <Star size={14} />
                    <span>Avaliar</span>
                </button>
                
                <button
                    onClick={() => setTab('perfil')}
                    data-active={tab === 'perfil'}
                    className={`bm-bottom-nav-btn flex flex-col items-center justify-center gap-0.5 h-full flex-1 text-center ${
                        tab === 'perfil' ? 'text-orange-500 bg-orange-500/5' : 'text-zinc-400 hover:text-zinc-200'
                    }`}
                >
                    <User size={14} />
                    <span>Perfil</span>
                </button>

            </div>


            {/* Mostrar rotas quando há atendimento em andamento */}
                        {ongoingJobs && ongoingJobs.length > 0 && ['aceito', 'confirmado', 'em_atendimento'].includes((ongoingJobs[0].status || '').toLowerCase()) && (
              <TelaRotasAtivos
                chamado={ongoingJobs[0]}
                userType="barbeiro"
                userLocation={user}
                clienteLocation={{
                  latitude: ongoingJobs[0]?.cliente_latitude,
                  longitude: ongoingJobs[0]?.cliente_longitude,
                }}
                barbearia={{
                  id: ongoingJobs[0]?.barbearia_id,
                  nome: ongoingJobs[0]?.barbearia_nome,
                  latitude: ongoingJobs[0]?.barbearia_latitude,
                  longitude: ongoingJobs[0]?.barbearia_longitude,
                  endereco: ongoingJobs[0]?.barbearia_endereco,
                  telefone: ongoingJobs[0]?.barbearia_telefone,
                }}
                barbeiro={user}
                onNotify={notify}
              />
            )}
                </div>
        </div>
        </ScreenWrapper>
    );
}
