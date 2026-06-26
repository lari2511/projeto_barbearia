import React, { useState, useEffect, useCallback } from 'react';
import ScreenWrapper from './ScreenWrapper';
import { getWsBaseUrl } from '../utils/api';
import { Store, LogOut, CheckCircle, AlertCircle, User, CreditCard, Calendar, Search, Star, TrendingUp, Users, Bell } from 'lucide-react';
import PaymentSection from './PaymentSection';
import AbaPadronizadaAvaliacoes from './AbaPadronizadaAvaliacoes';
import TelaPerfilUsuario from './TelaPerfilUsuario';
import TelaMensalidadeAssinatura from './TelaMensalidadeAssinatura';
import ChatRoom from './ChatRoom';

export default function ShopDashboard({ token, logout, notify, API_URL }) {
    const TABS_VALIDAS = ['inicio', 'barbeiros', 'freelancers', 'agenda', 'avaliar', 'assinatura', 'perfil', 'pagamento'];
    const [services, setServices] = useState([{id: 1, nome: "Corte Simples", valor: 30}]);
    const [newService, setNewService] = useState({nome: '', valor: ''});
    const [user, setUser] = useState(null);
    const [userData, setUserData] = useState(null);
    const [tab, setTab] = useState(() => {
        if (typeof window === 'undefined') return 'barbeiros';
        const tabSalva = localStorage.getItem('barbearia_dashboard_tab') || 'inicio';
        return TABS_VALIDAS.includes(tabSalva) ? tabSalva : 'inicio';
    });
    const [agendamentos, setAgendamentos] = useState([]);
    const [freelancersPresentes, setFreelancersPresentes] = useState([]);
    const [freelancersDisponiveis, setFreelancersDisponiveis] = useState([]);
    const [freelancersPendentesAprovacao, setFreelancersPendentesAprovacao] = useState([]);
    const [cadeirasBarbearia, setCadeirasBarbearia] = useState([]);
    const [loadingCadeirasBarbearia, setLoadingCadeirasBarbearia] = useState(false);
    const [ultimaAtualizacaoFreelancers, setUltimaAtualizacaoFreelancers] = useState(null);
        const freelancersPresentesNaBarbearia = freelancersPresentes.filter((freelancer) =>
            freelancer?.presente_em_local &&
            (!freelancer?.barbearia_atual_id || freelancer.barbearia_atual_id === barbeariaId)
        );
    const [wsConectado, setWsConectado] = useState(false);
    const [_loading, _setLoading] = useState(false);
    const [barbeariaId, setBarbeariaId] = useState(null);
    const [chatTarget, setChatTarget] = useState(null);
    const [vagasRelampago, setVagasRelampago] = useState([]);
    const [acionandoCadeiraId, setAcionandoCadeiraId] = useState(null);
    const [cancelandoVagaId, setCancelandoVagaId] = useState(null);

    useEffect(() => {
        fetch(`${API_URL}/api/v1/documentos/status`, {
            headers: {'Authorization': `Bearer ${token}`}
        })
        .then(r => r.json())
        .then(data => {
            setUser(data);
            setUserData(data);
        })
        .catch(() => {});

        // Carregar barbearia do usuário autenticado
        fetch(`${API_URL}/api/v1/barbearia/minha`, {
            headers: {'Authorization': `Bearer ${token}`}
        })
        .then(r => r.ok ? r.json() : null)
        .then(data => {
            if (data && data.id) {
                setBarbeariaId(data.id);
                setUserData(prev => ({ ...(prev || {}), id: data.usuario_id || prev?.id }));
            }
        })
        .catch(() => {});
    }, [API_URL, token]);

    useEffect(() => {
        if (typeof window !== 'undefined') {
            localStorage.setItem('barbearia_dashboard_tab', tab);
        }
    }, [tab]);

    // Carregar agendamentos da barbearia
    useEffect(() => {
        if (!barbeariaId) return;

        const carregarAgendamentos = async () => {
            try {
                const res = await fetch(`${API_URL}/api/v1/barbearia/${barbeariaId}/agendamentos`, {
                    headers: {
                        'Authorization': `Bearer ${token}`
                    }
                });

                if (res.ok) {
                    const data = await res.json();
                    setAgendamentos(Array.isArray(data) ? data : data.agendamentos || []);
                }
            } catch (_err) {
                // mantém a última lista carregada
            }
        };

        carregarAgendamentos();
        const interval = setInterval(carregarAgendamentos, 10000);
        return () => clearInterval(interval);
    }, [barbeariaId, API_URL, token]);

    // Alterar status do freelancer (controle duplo)
    const alterarStatusFreelancer = async (freelancerId, novoStatus, barbeariaIdAlvo = null) => {
        try {
            const res = await fetch(`${API_URL}/api/v1/freelancer/${freelancerId}/alterar-status`, {
                method: 'POST',
                headers: {
                    'Authorization': `Bearer ${token}`,
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    status: novoStatus,
                    barbearia_id: barbeariaIdAlvo || barbeariaId
                })
            });

            if (res.ok) {
                await res.json();
                notify(`Status do freelancer alterado para ${novoStatus.toUpperCase()}`, 'success');
                // Recarregar dados
                if (barbeariaId) {
                    carregarFreelancersPresentes();
                }
            } else {
                const error = await res.json().catch(() => ({}));
                notify(error.detail || 'Erro ao alterar status', 'error');
            }
        } catch (_err) {
            notify('Erro ao conectar com servidor', 'error');
        }
    };

    // Bloquear freelancer
    const bloquearFreelancer = async (freelancerId, motivo) => {
        if (!barbeariaId) {
            notify('Barbearia não identificada', 'error');
            return;
        }
        
        try {
            const res = await fetch(`${API_URL}/api/v1/barbearia/${barbeariaId}/bloquear-freelancer`, {
                method: 'POST',
                headers: {
                    'Authorization': `Bearer ${token}`,
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    freelancer_id: freelancerId,
                    motivo: motivo
                })
            });

            if (res.ok) {
                notify('Freelancer bloqueado com sucesso', 'success');
                carregarFreelancersPresentes();
            } else {
                const error = await res.json().catch(() => ({}));
                notify(error.detail || 'Erro ao bloquear freelancer', 'error');
            }
        } catch (_err) {
            notify('Erro ao conectar com servidor', 'error');
        }
    };

    // Avaliar freelancer
    const avaliarFreelancer = async (freelancerId, chamadoId, nota, comentario) => {
        if (!barbeariaId) {
            notify('Barbearia não identificada', 'error');
            return;
        }

        try {
            const res = await fetch(`${API_URL}/api/v1/barbearia/${barbeariaId}/avaliar-freelancer`, {
                method: 'POST',
                headers: {
                    'Authorization': `Bearer ${token}`,
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    freelancer_id: freelancerId,
                    chamado_id: chamadoId,
                    nota: nota,
                    comentario: comentario
                })
            });

            if (res.ok) {
                notify('Avaliação enviada com sucesso!', 'success');
            } else {
                const error = await res.json().catch(() => ({}));
                notify(error.detail || 'Erro ao enviar avaliação', 'error');
            }
        } catch (_err) {
            notify('Erro ao conectar com servidor', 'error');
        }
    };

    // Carregar freelancers presentes
    const carregarFreelancersPresentes = useCallback(async () => {
        if (!barbeariaId) return;
        
        try {
            const res = await fetch(`${API_URL}/api/v1/barbearia/${barbeariaId}/barbeiros-presentes`, {
                headers: {'Authorization': `Bearer ${token}`}
            });
            if (res.ok) {
                const data = await res.json();
                setFreelancersPresentes(Array.isArray(data) ? data : []);
                setUltimaAtualizacaoFreelancers(new Date());
            }
        } catch (_err) {
            // Erro ao carregar freelancers
        }
    }, [API_URL, barbeariaId, token]);

    const carregarFreelancersDisponiveis = useCallback(async () => {
        try {
            const res = await fetch(`${API_URL}/api/v1/barbeiros/todos`, {
                headers: {'Authorization': `Bearer ${token}`}
            });
            if (!res.ok) {
                setFreelancersDisponiveis([]);
                return;
            }

            const data = await res.json();
            const lista = Array.isArray(data) ? data : [];

            const pendentes = lista.filter((f) => !f?.perfil_aprovado);
            setFreelancersPendentesAprovacao(pendentes);

            const disponiveis = lista.filter((f) => {
                if (!f?.perfil_aprovado) return false;
                if (!f?.disponivel || f?.offline) return false;
                if (f?.presente_em_local && f?.barbearia_atual_id && f.barbearia_atual_id !== barbeariaId) return false;
                return true;
            });

            setFreelancersDisponiveis(disponiveis);
            setUltimaAtualizacaoFreelancers(new Date());
        } catch (_err) {
            setFreelancersDisponiveis([]);
            setFreelancersPendentesAprovacao([]);
        }
    }, [API_URL, barbeariaId, token]);

    const carregarCadeirasBarbearia = useCallback(async () => {
        if (!barbeariaId) return;

        try {
            setLoadingCadeirasBarbearia(true);
            const res = await fetch(`${API_URL}/api/v1/cadeiras/barbearia/${barbeariaId}`, {
                headers: {'Authorization': `Bearer ${token}`}
            });

            if (!res.ok) {
                setCadeirasBarbearia([]);
                return;
            }

            const data = await res.json();
            setCadeirasBarbearia(Array.isArray(data) ? data : []);
        } catch (_err) {
            setCadeirasBarbearia([]);
        } finally {
            setLoadingCadeirasBarbearia(false);
        }
    }, [API_URL, barbeariaId, token]);

    const carregarVagasRelampago = useCallback(async () => {
        if (!token) return;
        try {
            const res = await fetch(`${API_URL}/api/v1/on-demand/cadeiras-acionadas/minhas?limite=30`, {
                headers: {'Authorization': `Bearer ${token}`}
            });
            if (!res.ok) {
                setVagasRelampago([]);
                return;
            }

            const data = await res.json();
            setVagasRelampago(Array.isArray(data) ? data : []);
        } catch (_err) {
            setVagasRelampago([]);
        }
    }, [API_URL, token]);

    const acionarCadeira = async (cadeiraId) => {
        if (!barbeariaId || !cadeiraId) {
            notify('Barbearia não identificada', 'error');
            return;
        }

        try {
            setAcionandoCadeiraId(cadeiraId);
            const res = await fetch(`${API_URL}/api/v1/on-demand/cadeiras-acionadas/acionar`, {
                method: 'POST',
                headers: {
                    'Authorization': `Bearer ${token}`,
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    cadeira_id: cadeiraId,
                    raio_km: 5,
                    expira_em_minutos: 10
                })
            });

            if (res.ok) {
                const data = await res.json();
                notify(data.message || 'Cadeira acionada com sucesso', 'success');
                carregarCadeirasBarbearia();
                carregarFreelancersDisponiveis();
                carregarVagasRelampago();
            } else {
                const error = await res.json().catch(() => ({}));
                notify(error.detail || 'Erro ao acionar cadeira', 'error');
            }
        } catch (_err) {
            notify('Erro ao conectar com servidor', 'error');
        } finally {
            setAcionandoCadeiraId(null);
        }
    };

    const cancelarVagaRelampago = async (vagaId) => {
        if (!vagaId) return;
        try {
            setCancelandoVagaId(vagaId);
            const res = await fetch(`${API_URL}/api/v1/on-demand/cadeiras-acionadas/${vagaId}/cancelar`, {
                method: 'POST',
                headers: {'Authorization': `Bearer ${token}`}
            });

            const data = await res.json().catch(() => ({}));
            if (!res.ok) {
                throw new Error(data?.detail || 'Não foi possível cancelar a vaga relâmpago');
            }

            notify('Vaga relâmpago cancelada', 'success');
            carregarVagasRelampago();
        } catch (err) {
            notify(err?.message || 'Erro ao cancelar vaga relâmpago', 'error');
        } finally {
            setCancelandoVagaId(null);
        }
    };

    const acionarPrimeiraCadeiraDisponivel = async () => {
        const primeiraDisponivel = cadeirasBarbearia.find((cadeira) => String(cadeira.status || '').toLowerCase() === 'disponivel');
        if (!primeiraDisponivel) {
            notify('Nenhuma cadeira disponível para acionar', 'info');
            return;
        }
        await acionarCadeira(primeiraDisponivel.id);
    };

    const bloquearCadeira = async (cadeiraId) => {
        if (!barbeariaId) {
            notify('Barbearia não identificada', 'error');
            return;
        }

        try {
            const res = await fetch(`${API_URL}/api/v1/cadeiras/${cadeiraId}/bloquear`, {
                method: 'PUT',
                headers: {'Authorization': `Bearer ${token}`}
            });

            if (res.ok) {
                const data = await res.json();
                notify(data.message || 'Cadeira bloqueada com sucesso', 'success');
                carregarCadeirasBarbearia();
            } else {
                const error = await res.json().catch(() => ({}));
                notify(error.detail || 'Erro ao bloquear cadeira', 'error');
            }
        } catch (_err) {
            notify('Erro ao conectar com servidor', 'error');
        }
    };

    const desbloquearCadeira = async (cadeiraId) => {
        if (!barbeariaId) {
            notify('Barbearia não identificada', 'error');
            return;
        }

        try {
            const res = await fetch(`${API_URL}/api/v1/cadeiras/${cadeiraId}/desbloquear`, {
                method: 'PUT',
                headers: {'Authorization': `Bearer ${token}`}
            });

            if (res.ok) {
                const data = await res.json();
                notify(data.message || 'Cadeira desbloqueada com sucesso', 'success');
                carregarCadeirasBarbearia();
            } else {
                const error = await res.json().catch(() => ({}));
                notify(error.detail || 'Erro ao desbloquear cadeira', 'error');
            }
        } catch (_err) {
            notify('Erro ao conectar com servidor', 'error');
        }
    };

    useEffect(() => {
        if (!barbeariaId || tab !== 'barbeiros') return;

        // Sincronização inicial sempre ocorre.
        carregarFreelancersPresentes();
        carregarFreelancersDisponiveis();
        carregarCadeirasBarbearia();
        carregarVagasRelampago();

        // Se o WebSocket estiver conectado, não precisamos de polling.
        if (wsConectado) return;

        const interval = setInterval(() => {
            carregarFreelancersPresentes();
            carregarFreelancersDisponiveis();
            carregarCadeirasBarbearia();
            carregarVagasRelampago();
        }, 5000);
        return () => clearInterval(interval);
    }, [barbeariaId, tab, wsConectado, carregarFreelancersDisponiveis, carregarFreelancersPresentes, carregarCadeirasBarbearia, carregarVagasRelampago]);

    useEffect(() => {
        if (!barbeariaId || tab !== 'barbeiros') return;

        const WS_URL = import.meta.env.VITE_WS_URL?.trim() || getWsBaseUrl();
        const ws = new WebSocket(WS_URL);

        ws.onopen = () => {
            setWsConectado(true);
        };

        ws.onmessage = (event) => {
            try {
                const data = JSON.parse(event.data);
                const eventoBarbeariaId = data?.barbearia_id;
                if (eventoBarbeariaId && Number(eventoBarbeariaId) !== Number(barbeariaId)) {
                    return;
                }

                if (['freelancer_status_changed', 'cadeira_status_changed', 'cadeira_acionada', 'cadeira_liberada', 'cadeira_acionada_aberta', 'cadeira_acionada_fechada'].includes(data?.type)) {
                    carregarFreelancersPresentes();
                    carregarFreelancersDisponiveis();
                    carregarCadeirasBarbearia();
                    carregarVagasRelampago();
                }
            } catch {
                // Ignora mensagens não JSON como ping/pong
            }
        };

        ws.onclose = () => {
            setWsConectado(false);
        };

        ws.onerror = () => {
            setWsConectado(false);
        };

        return () => {
            setWsConectado(false);
            ws.close();
        };
    }, [API_URL, barbeariaId, tab, carregarFreelancersDisponiveis, carregarFreelancersPresentes, carregarCadeirasBarbearia, carregarVagasRelampago]);

    const addService = (e) => {
        e.preventDefault();
        if (!newService.nome || !newService.valor) {
            notify("Preencha nome e valor", "error");
            return;
        }
        setServices([...services, {id: Date.now(), nome: newService.nome, valor: parseFloat(newService.valor)}]);
        setNewService({nome: '', valor: ''});
        notify("Serviço adicionado!", "success");
    };

    return (
        <ScreenWrapper>
        <div className="min-h-[100dvh] w-full bg-[#050505] text-white font-sans flex justify-center overflow-x-hidden">
            <div className="app-container w-full min-h-[100dvh] max-w-[430px] flex flex-col overflow-x-hidden bg-[#050505] shadow-[0_0_0_1px_rgba(255,255,255,0.04)]">
            <div className="sticky top-0 z-20 px-3 pt-3 pb-2 bg-[#050505]/95 backdrop-blur-xl flex-shrink-0">
                <div className="flex justify-between items-center rounded-[1.5rem] border border-zinc-800/80 bg-zinc-950/90 px-4 py-3 shadow-xl shadow-black/25">
                    <div className="flex items-center gap-2 min-w-0">
                        <h1 className="text-lg font-black tracking-tight flex items-center gap-2 truncate">
                            <Store size={18} className="text-orange-500"/> Loja
                        </h1>
                        {user?.documento_verificado && (
                            <CheckCircle size={14} className="text-blue-500 fill-blue-500" />
                        )}
                    </div>
                    <div className="flex items-center gap-2 shrink-0">
                        <button onClick={logout} className="h-10 w-10 rounded-full bg-zinc-900 border border-zinc-800 flex items-center justify-center text-zinc-400 hover:text-white hover:bg-zinc-800 transition-colors"><LogOut size={18}/></button>
                    </div>
                </div>
            </div>

            <div className="flex-1 overflow-visible pb-[calc(6rem+env(safe-area-inset-bottom))]">

                {/* ABA: INÍCIO */}
                {tab === 'inicio' && (
                    <div className="p-4 space-y-4 max-w-3xl mx-auto w-full">
                        <div className="bm-card bg-zinc-900 rounded-2xl p-5 border border-zinc-800/60 space-y-3">
                            <div className="flex items-center gap-3">
                                <div className="w-12 h-12 rounded-2xl bg-orange-500/15 border border-orange-500/30 flex items-center justify-center text-2xl">💈</div>
                                <div>
                                    <p className="text-xs text-zinc-500 uppercase tracking-widest">Painel da</p>
                                    <h2 className="text-lg font-black text-white">Barbearia</h2>
                                </div>
                            </div>
                            <p className="text-sm text-zinc-400">Gerencie seus freelancers, agendamentos, avaliações e financeiro.</p>
                        </div>
                        <div className="grid grid-cols-2 gap-3">
                            <button onClick={() => setTab('barbeiros')} className="bm-card bg-zinc-900 rounded-2xl p-4 border border-zinc-800/60 flex flex-col items-center gap-2 hover:border-orange-500 transition-colors">
                                <Store size={22} className="text-orange-400" />
                                <span className="text-sm font-bold">Minha Loja</span>
                                <span className="text-xs text-zinc-500">Serviços e cadeiras</span>
                            </button>
                            <button onClick={() => setTab('freelancers')} className="bm-card bg-zinc-900 rounded-2xl p-4 border border-zinc-800/60 flex flex-col items-center gap-2 hover:border-orange-500 transition-colors">
                                <Users size={22} className="text-blue-400" />
                                <span className="text-sm font-bold">Freelancers</span>
                                <span className="text-xs text-zinc-500">Controle de presentes</span>
                            </button>
                            <button onClick={() => setTab('agenda')} className="bm-card bg-zinc-900 rounded-2xl p-4 border border-zinc-800/60 flex flex-col items-center gap-2 hover:border-orange-500 transition-colors">
                                <Calendar size={22} className="text-green-400" />
                                <span className="text-sm font-bold">Chamadas</span>
                                <span className="text-xs text-zinc-500">Agendamentos</span>
                            </button>
                            <button onClick={() => setTab('avaliar')} className="bm-card bg-zinc-900 rounded-2xl p-4 border border-zinc-800/60 flex flex-col items-center gap-2 hover:border-orange-500 transition-colors">
                                <Star size={22} className="text-yellow-400" />
                                <span className="text-sm font-bold">Avaliar</span>
                                <span className="text-xs text-zinc-500">Avaliações recebidas</span>
                            </button>
                            <button onClick={() => setTab('perfil')} className="bm-card bg-zinc-900 rounded-2xl p-4 border border-zinc-800/60 flex flex-col items-center gap-2 hover:border-orange-500 transition-colors">
                                <User size={22} className="text-purple-400" />
                                <span className="text-sm font-bold">Perfil</span>
                                <span className="text-xs text-zinc-500">Seus dados</span>
                            </button>
                            <button onClick={() => setTab('pagamento')} className="bm-card bg-zinc-900 rounded-2xl p-4 border border-zinc-800/60 flex flex-col items-center gap-2 hover:border-orange-500 transition-colors">
                                <CreditCard size={22} className="text-emerald-400" />
                                <span className="text-sm font-bold">Carteira</span>
                                <span className="text-xs text-zinc-500">Financeiro</span>
                            </button>
                        </div>
                    </div>
                )}
                
                {tab === 'barbeiros' && (
                    <div className="p-2 sm:p-4 space-y-3 pb-20 max-w-3xl mx-auto w-full">
                        {user && !user.documento_verificado && (
                            <div className="bg-yellow-600/10 border border-yellow-600/30 p-2 rounded-lg flex items-center gap-2">
                                <AlertCircle size={14} className="text-yellow-500"/>
                                <span className="text-yellow-400 text-xs">Verificação pendente</span>
                            </div>
                        )}
                        
                        <h2 className="text-sm font-bold text-zinc-300 uppercase tracking-wide">Bem-vindo à Barbearia</h2>
                        <div className="bm-card p-3 text-xs text-zinc-400">
                            <p>Selecione uma aba abaixo para gerenciar sua barbearia.</p>
                        </div>

                        <div className="bg-purple-600/10 border border-purple-600/30 p-5 rounded-2xl mb-6">
                          <div className="flex items-center justify-between mb-4">
                            <h3 className="text-purple-400 font-bold text-sm flex items-center gap-2">💺 Suas Cadeiras ({cadeirasBarbearia.length})</h3>
                            <button className="bg-gradient-to-r from-orange-600 to-red-600 text-white px-3 py-1.5 rounded-2xl text-xs font-extrabold flex items-center gap-1 transition-all"><span className="text-lg leading-none">+</span> Nova</button>
                          </div>

                          {loadingCadeirasBarbearia ? (
                            <div className="flex items-center justify-center gap-2 py-6">
                              <div className="w-4 h-4 border-2 border-orange-500 border-t-transparent rounded-full animate-spin"></div>
                              <span className="text-xs text-zinc-400">Carregando cadeiras...</span>
                            </div>
                          ) : cadeirasBarbearia.length === 0 ? (
                            <div className="bg-zinc-900/80 p-4 rounded-xl border border-zinc-800 text-sm text-zinc-300">
                              <p className="mb-3">Nenhuma cadeira cadastrada ainda.</p>
                            </div>
                          ) : (
                            <div className="space-y-2">
                              {cadeirasBarbearia.map(cadeira => {
                                const status = String(cadeira.status || '').toLowerCase();
                                const statusConfig = {
                                  disponivel: { bg: 'bg-black/40', border: 'border-green-600/30', label: '🟢 Disponível', labelColor: 'text-green-400', labelBg: 'bg-green-600/20' },
                                  ocupada: { bg: 'bg-black/40', border: 'border-blue-600/30', label: '🔵 Ocupada', labelColor: 'text-blue-400', labelBg: 'bg-blue-600/20' },
                                  bloqueada: { bg: 'bg-black/40', border: 'border-red-600/30', label: '🔒 Bloqueada', labelColor: 'text-red-400', labelBg: 'bg-red-600/20' }
                                };
                                const config = statusConfig[status] || statusConfig.disponivel;
                                
                                return (
                                  <div key={cadeira.id} className={`${config.bg} border ${config.border} p-3 rounded-lg transition-all hover:border-purple-600/50`}>
                                    <div className="flex items-center justify-between">
                                      <div className="flex-1">
                                        <p className="font-bold text-sm text-white">Cadeira {cadeira.numero}</p>
                                        <p className={`text-xs mt-1 font-bold ${config.labelColor}`}>{config.label}</p>
                                      </div>
                                      <div className="flex gap-2">
                                        {status === 'disponivel' && (
                                          <>
                                                                                        <button 
                                                                                            onClick={() => acionarCadeira(cadeira.id)}
                                                                                            disabled={acionandoCadeiraId === cadeira.id}
                                                                                            className="bg-orange-600 hover:bg-orange-700 disabled:bg-orange-800/50 text-white px-3 py-2 rounded-lg text-xs font-bold transition-all"
                                                                                        >
                                                                                            {acionandoCadeiraId === cadeira.id ? 'Acionando...' : 'Acionar'}
                                            </button>
                                            <button 
                                              onClick={() => bloquearCadeira(cadeira.id)}
                                              className="bg-zinc-700 hover:bg-red-700 text-white px-2 py-2 rounded-lg text-sm transition-all"
                                              title="Bloquear cadeira"
                                            >
                                              🔒
                                            </button>
                                          </>
                                        )}
                                        {status === 'ocupada' && (
                                          <button 
                                            onClick={() => desbloquearCadeira(cadeira.id)}
                                            className="bg-orange-600 hover:bg-orange-700 text-white px-3 py-2 rounded-lg text-xs font-bold transition-all"
                                          >
                                            Finalizar
                                          </button>
                                        )}
                                        {status === 'bloqueada' && (
                                          <button 
                                            onClick={() => desbloquearCadeira(cadeira.id)}
                                            className="bg-purple-600 hover:bg-purple-700 text-white px-2 py-2 rounded-lg text-sm transition-all"
                                            title="Desbloquear cadeira"
                                          >
                                            🔓
                                          </button>
                                        )}
                                      </div>
                                    </div>
                                  </div>
                                );
                              })}
                              <button
                                                                onClick={acionarPrimeiraCadeiraDisponivel}
                                className="w-full bg-purple-600 hover:bg-purple-700 text-white px-4 py-3 rounded-lg font-bold text-sm mt-3 transition-all"
                              >
                                ⚡ Liberar Próxima Vaga Disponível
                              </button>
                            </div>
                          )}

                                                    <div className="mt-4 space-y-2">
                                                        <p className="text-xs font-bold uppercase tracking-[0.14em] text-red-300">Vagas relâmpago recentes</p>
                                                        {vagasRelampago.length === 0 ? (
                                                            <div className="bg-zinc-900/80 p-3 rounded-xl border border-zinc-800 text-xs text-zinc-500">
                                                                Nenhuma vaga relâmpago registrada ainda.
                                                            </div>
                                                        ) : (
                                                            vagasRelampago.slice(0, 5).map((vaga) => {
                                                                const status = String(vaga.status || '').toLowerCase();
                                                                const aberta = status === 'disponivel';
                                                                return (
                                                                    <div key={vaga.id} className="bg-zinc-900/90 p-3 rounded-xl border border-zinc-800 flex items-center justify-between gap-3">
                                                                        <div>
                                                                            <p className="text-sm font-bold text-white">Vaga #{vaga.id} {vaga.cadeira_id ? `• Cadeira ${vaga.cadeira_id}` : ''}</p>
                                                                            <p className="text-xs text-zinc-400">Status: {status || 'desconhecido'}</p>
                                                                        </div>
                                                                        {aberta && (
                                                                            <button
                                                                                type="button"
                                                                                onClick={() => cancelarVagaRelampago(vaga.id)}
                                                                                disabled={cancelandoVagaId === vaga.id}
                                                                                className="rounded-lg bg-red-600 hover:bg-red-500 disabled:bg-red-800/50 text-white px-3 py-2 text-xs font-bold"
                                                                            >
                                                                                {cancelandoVagaId === vaga.id ? 'Cancelando...' : 'Cancelar'}
                                                                            </button>
                                                                        )}
                                                                    </div>
                                                                );
                                                            })
                                                        )}
                                                    </div>
                          <div className="bg-zinc-900/50 p-3 rounded-lg mt-4 border border-zinc-800">
                            <p className="text-zinc-400 text-xs mb-2">💡 <strong>Dicas:</strong></p>
                            <ul className="text-zinc-500 text-[10px] space-y-1 ml-4">
                              <li>• Use <strong>"Acionar"</strong> para notificar barbeiros próximos</li>
                              <li>• <strong>Bloqueie</strong> cadeiras em manutenção ou reservadas</li>
                              <li>• O sistema libera automaticamente clientes quando faltam 15 min</li>
                            </ul>
                          </div>
                        </div>

                        <div className="bg-zinc-900/60 p-5 rounded-2xl border border-purple-600/30 mb-6">
                            <h3 className="font-bold mb-4 text-sm flex items-center gap-2 text-purple-400">⚙️ Cadastrar Serviço</h3>
                            <form onSubmit={addService} className="space-y-3 mb-4">
                              <input 
                                className="w-full bg-black rounded-lg p-3 border border-zinc-800 text-sm outline-none focus:border-purple-500 text-white" 
                                placeholder="Nome do serviço (ex: Corte Degradê)" 
                                value={newService.nome} 
                                onChange={e => setNewService({...newService, nome: e.target.value})} 
                                required
                              />
                              <div className="grid grid-cols-2 gap-3">
                                <input 
                                  className="bg-black rounded-lg p-3 border border-zinc-800 text-sm outline-none focus:border-purple-500 text-white" 
                                  type="number" 
                                  placeholder="Valor R$" 
                                  value={newService.valor} 
                                  onChange={e => setNewService({...newService, valor: e.target.value})} 
                                  required
                                />
                                <input 
                                  className="bg-black rounded-lg p-3 border border-zinc-800 text-sm outline-none focus:border-purple-500 text-white" 
                                  type="number" 
                                  placeholder="Duração (min)" 
                                  value={newService.duracao_minutos} 
                                  onChange={e => setNewService({...newService, duracao_minutos: e.target.value})} 
                                  required
                                />
                              </div>
                              <button type="submit" className="w-full bg-orange-600 hover:bg-orange-700 text-white px-4 py-3 rounded-lg font-bold text-sm transition-all">+ Adicionar Serviço</button>
                            </form>
                            <div className="space-y-2">
                                {services.length > 0 ? (
                                  services.map(s => (
                                    <div key={s.id} className="flex justify-between items-center bg-black/60 p-3 rounded-lg border border-purple-600/20 hover:border-purple-600/40 transition-colors">
                                      <span className="text-sm font-medium text-white">{s.nome}</span>
                                      <div className="text-right flex gap-3">
                                        <span className="text-green-400 font-bold text-sm">R$ {parseFloat(s.valor).toFixed(2)}</span>
                                        <span className="text-purple-400 font-bold text-sm">{s.duracao_minutos || 30} min</span>
                                      </div>
                                    </div>
                                  ))
                                ) : (
                                  <div className="text-center text-zinc-500 text-xs py-4">Nenhum serviço cadastrado ainda</div>
                                )}
                            </div>
                        </div>

                    </div>
                )}

                {/* ABA: FREELANCERS */}
                {tab === 'freelancers' && (
                    <div className="p-2 sm:p-4 space-y-3 pb-20 max-w-3xl mx-auto w-full">
                        <div className="flex items-center justify-between gap-2">
                            <h2 className="text-sm font-bold text-zinc-300 uppercase tracking-wide">Controle de Freelancers</h2>
                            <button
                                onClick={() => setTab('barbeiros')}
                                className="bg-zinc-800 hover:bg-zinc-700 text-white px-3 py-1.5 rounded text-xs font-bold"
                            >
                                Voltar
                            </button>
                        </div>

                        <div className="bg-green-900/20 border border-green-700 rounded-lg p-2.5 flex items-center justify-between">
                            <div className="flex items-center gap-2">
                                <span className="h-2.5 w-2.5 rounded-full bg-green-400 animate-pulse"></span>
                                <span className="text-xs font-bold text-green-300">EM TEMPO REAL</span>
                            </div>
                            <span className="text-[11px] text-zinc-300">
                                {ultimaAtualizacaoFreelancers
                                    ? `Atualizado às ${ultimaAtualizacaoFreelancers.toLocaleTimeString('pt-BR')}`
                                    : 'Sincronizando...'}
                            </span>
                        </div>

                        <button
                            onClick={() => {
                                carregarFreelancersPresentes();
                                carregarFreelancersDisponiveis();
                            }}
                            className="w-full py-2 bg-zinc-800 hover:bg-zinc-700 rounded text-xs font-bold"
                        >
                            🔄 Atualizar Lista
                        </button>

                        {/* PRESENTES */}
                        <div className="bm-card p-3 space-y-2">
                            <h3 className="text-xs font-bold text-zinc-400 uppercase tracking-wide">Freelancers Presentes</h3>
                            {freelancersPresentesNaBarbearia.length === 0 ? (
                                <p className="text-zinc-600 text-xs">Nenhum freelancer presente no momento</p>
                            ) : (
                                <div className="space-y-2">
                                    {freelancersPresentesNaBarbearia.map(freelancer => (
                                        <div key={freelancer.id} className="bg-black/40 border border-zinc-700 rounded p-3 overflow-hidden">
                                            <div className="flex justify-between items-start mb-2">
                                                <div className="min-w-0 pr-2">
                                                    <p className="font-bold text-sm truncate">{freelancer.nome}</p>
                                                    <p className="text-xs text-zinc-400 truncate">{freelancer.email}</p>
                                                </div>
                                                <div className="h-2 w-2 bg-green-500 rounded-full animate-pulse"></div>
                                            </div>
                                            <div className="grid grid-cols-3 gap-2">
                                                <button
                                                    onClick={() => alterarStatusFreelancer(freelancer.id, 'offline')}
                                                    className="py-2 px-2 bg-red-600/20 hover:bg-red-600/30 border border-red-600/50 text-red-400 rounded text-xs font-bold"
                                                >
                                                    OFFLINE
                                                </button>
                                                <button
                                                    onClick={() => alterarStatusFreelancer(freelancer.id, 'online')}
                                                    className="py-2 px-2 bg-green-600/20 hover:bg-green-600/30 border border-green-600/50 text-green-400 rounded text-xs font-bold"
                                                >
                                                    ONLINE
                                                </button>
                                                <button
                                                    onClick={() => alterarStatusFreelancer(freelancer.id, 'presente', barbeariaId)}
                                                    className="py-2 px-2 bg-blue-600/20 hover:bg-blue-600/30 border border-blue-600/50 text-blue-400 rounded text-xs font-bold"
                                                >
                                                    PRESENTE
                                                </button>
                                            </div>
                                        </div>
                                    ))}
                                </div>
                            )}
                        </div>

                        {/* DISPONÍVEIS */}
                        <div className="bm-card p-3 space-y-2">
                            <div className="flex items-center justify-between">
                                <h3 className="text-xs font-bold text-zinc-400 uppercase tracking-wide">Disponíveis para sua Barbearia</h3>
                                <span className="text-[11px] text-green-400 font-bold">{freelancersDisponiveis.length}</span>
                            </div>
                            {freelancersDisponiveis.length === 0 ? (
                                <p className="text-zinc-600 text-xs">Nenhum barbeiro disponível agora.</p>
                            ) : (
                                <div className="space-y-2">
                                    {freelancersDisponiveis.map((f) => (
                                        <div key={f.usuario_id} className="bg-black/40 border border-zinc-700 rounded p-2">
                                            <p className="text-sm font-bold text-white">{f.nome}</p>
                                            <p className="text-[11px] text-zinc-400">{f.presente_em_local ? 'Disponível no local' : 'Disponível na região'}</p>
                                        </div>
                                    ))}
                                </div>
                            )}
                        </div>

                        {/* AGUARDANDO APROVAÇÃO */}
                        <div className="bm-card p-3 space-y-2">
                            <div className="flex items-center justify-between">
                                <h3 className="text-xs font-bold text-zinc-400 uppercase tracking-wide">Aguardando Aprovação</h3>
                                <span className="text-[11px] text-yellow-400 font-bold">{freelancersPendentesAprovacao.length}</span>
                            </div>
                            {freelancersPendentesAprovacao.length === 0 ? (
                                <p className="text-zinc-600 text-xs">Nenhum barbeiro pendente no momento.</p>
                            ) : (
                                <div className="space-y-2">
                                    {freelancersPendentesAprovacao.map((f) => (
                                        <div key={f.usuario_id} className="bg-black/40 border border-zinc-700 rounded p-2">
                                            <p className="text-sm font-bold text-white">{f.nome}</p>
                                            <p className="text-[11px] text-zinc-400">Perfil em análise pelo admin</p>
                                        </div>
                                    ))}
                                </div>
                            )}
                        </div>
                    </div>
                )}

                {tab === 'agenda' && (
                    <div className="p-2 sm:p-4 space-y-3 pb-20 max-w-3xl mx-auto w-full">
                        <h2 className="text-sm font-bold text-zinc-300 uppercase tracking-wide">Agendamentos</h2>
                        
                        {agendamentos.length === 0 ? (
                            <p className="text-zinc-600 text-center py-12 text-xs">Nenhum agendamento</p>
                        ) : (
                            <div className="space-y-2 max-w-2xl mx-auto w-full">
                                {agendamentos.map(ag => (
                                    <div key={ag.id} className="bm-card p-3.5 space-y-2.5 overflow-hidden">
                                        <div className="flex justify-between items-start">
                                            <div className="min-w-0 pr-2">
                                                <p className="font-bold text-sm truncate">{ag.servico_nome || 'Serviço'}</p>
                                                <p className="text-xs text-zinc-400 truncate">Cliente: {ag.cliente_nome}</p>
                                                <p className="text-xs text-zinc-400 truncate">Freelancer: {ag.barbeiro_nome}</p>
                                                <p className="text-xs text-zinc-300">
                                                    {ag.data_hora_inicio ? new Date(ag.data_hora_inicio).toLocaleString('pt-BR') : 'Horário não definido'}
                                                </p>
                                            </div>
                                            <div className={`text-xs px-2 py-1 rounded font-bold ${
                                                ag.status === 'concluido' ? 'bg-green-600/20 text-green-400' :
                                                ag.status === 'em_atendimento' ? 'bg-purple-600/20 text-purple-300' :
                                                ag.status === 'confirmado' ? 'bg-blue-600/20 text-blue-400' :
                                                ag.status === 'pendente' ? 'bg-yellow-600/20 text-yellow-400' :
                                                'bg-red-600/20 text-red-400'
                                            }`}>
                                                {ag.status.toUpperCase()}
                                            </div>
                                        </div>

                                        {ag.status === 'confirmado' && (
                                            <button
                                                onClick={() => setChatTarget(ag.id)}
                                                className="w-full bg-zinc-800 hover:bg-zinc-700 text-white rounded text-xs font-bold py-2"
                                            >
                                                Chat
                                            </button>
                                        )}

                                        {ag.status === 'em_atendimento' && (
                                            <div className="flex gap-2">
                                                <button
                                                    onClick={async () => {
                                                        const res = await fetch(`${API_URL}/api/v1/chamados/${ag.id}/finalizar`, {
                                                            method: 'PUT',
                                                            headers: { 'Authorization': `Bearer ${token}` }
                                                        });
                                                        if (res.ok) {
                                                            notify('Corte finalizado', 'success');
                                                            if (typeof window !== 'undefined') window.location.reload();
                                                        } else {
                                                            notify('Não foi possível finalizar', 'error');
                                                        }
                                                    }}
                                                    className="flex-1 bg-green-600 hover:bg-green-700 text-white rounded text-xs font-bold py-2"
                                                >
                                                    FINALIZAR_CORTE
                                                </button>
                                                <button
                                                    onClick={() => setChatTarget(ag.id)}
                                                    className="flex-1 bg-zinc-800 hover:bg-zinc-700 text-white rounded text-xs font-bold py-2"
                                                >
                                                    Chat
                                                </button>
                                            </div>
                                        )}

                                        {/* ✅ APENAS VISUALIZAÇÃO - Dono não pode aceitar/recusar */}
                                        {ag.status === 'pendente' && (
                                            <div className="bg-yellow-900/20 border border-yellow-600/30 p-2 rounded text-xs text-yellow-400">
                                                ⏳ Aguardando aceitação do freelancer
                                            </div>
                                        )}

                                        {/* 🎯 AVALIAR FREELANCER - Após concluído */}
                                        {ag.status === 'concluido' && !ag.avaliado_por_barbearia && (
                                            <div className="space-y-2 pt-2 border-t border-zinc-700">
                                                <p className="text-xs text-zinc-400 font-bold">Avaliar Freelancer:</p>
                                                <div className="flex gap-2">
                                                    {[1,2,3,4,5].map(nota => (
                                                        <button
                                                            key={nota}
                                                            onClick={() => {
                                                                const comentario = prompt('Comentário (opcional):');
                                                                avaliarFreelancer(ag.barbeiro_id, ag.id, nota, comentario);
                                                            }}
                                                            className="text-2xl hover:scale-110 transition"
                                                        >
                                                            ⭐
                                                        </button>
                                                    ))}
                                                </div>
                                                <button
                                                    onClick={() => {
                                                        if (confirm(`Bloquear ${ag.barbeiro_nome} de trabalhar na sua barbearia?`)) {
                                                            const motivo = prompt('Motivo do bloqueio:');
                                                            if (motivo) {
                                                                bloquearFreelancer(ag.barbeiro_id, motivo);
                                                            }
                                                        }
                                                    }}
                                                    className="w-full py-2 bg-red-600/20 hover:bg-red-600/30 border border-red-600/50 text-red-400 rounded text-xs font-bold"
                                                >
                                                    🚫 Bloquear Freelancer
                                                </button>
                                            </div>
                                        )}
                                    </div>
                                ))}
                            </div>
                        )}
                    </div>
                )}

                {tab === 'avaliar' && (
                    <div className="p-2 sm:p-4 pb-20 max-w-3xl mx-auto w-full">
                        {userData ? (
                            <AbaPadronizadaAvaliacoes
                                usuarioId={userData.id}
                                tipoUsuario="barbearia"
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

                {tab === 'perfil' && (
                    <TelaPerfilUsuario
                        userType="barbearia"
                        token={token}
                        onLogout={logout}
                        onNotify={notify}
                        mostrarFinanceiroBarbearia={false}
                    />
                )}

                {tab === 'assinatura' && barbeariaId && (
                    <div className="p-2 sm:p-4 pb-24 max-w-3xl mx-auto w-full">
                        <TelaMensalidadeAssinatura
                            token={token}
                            barbeariaId={barbeariaId}
                            API_URL={API_URL}
                            onNotify={notify}
                        />
                    </div>
                )}

                {tab === 'pagamento' && (
                    <div className="p-2 sm:p-4 pb-20 max-w-3xl mx-auto w-full">
                        <PaymentSection userType="barbearia" token={token} onNotify={notify} />
                    </div>
                )}

                {chatTarget && (
                    <div className="fixed left-3 right-3 bottom-20 z-50 mx-auto max-w-[430px]">
                        <div className="bg-zinc-950 border border-zinc-800 rounded-[1.5rem] p-3 shadow-2xl shadow-black/40">
                            <div className="flex items-center justify-between mb-2">
                                <div>
                                    <p className="font-bold text-sm">Chat do chamado #{chatTarget}</p>
                                </div>
                                <button onClick={() => setChatTarget(null)} className="text-xs text-zinc-400">Fechar</button>
                            </div>
                            <ChatRoom chamadoId={chatTarget} token={token} API_URL={API_URL} />
                        </div>
                    </div>
                )}
            </div>

            <div className="bm-bottom-nav sticky bottom-0 left-0 w-full h-[calc(4rem+env(safe-area-inset-bottom))] pb-[env(safe-area-inset-bottom)] flex justify-between items-center z-40 overflow-x-auto">
                <button data-active={tab === 'inicio'} onClick={() => setTab('inicio')} className={`bm-bottom-nav-btn flex flex-col items-center justify-center gap-0.5 h-full flex-1 text-center min-w-max ${tab === 'inicio' ? 'text-orange-500 bg-orange-500/5' : 'text-zinc-400 hover:text-zinc-200'}`}><span className="text-sm">🏠</span><span>Início</span></button>
                <button data-active={tab === 'barbeiros'} onClick={() => setTab('barbeiros')} className={`bm-bottom-nav-btn flex flex-col items-center justify-center gap-0.5 h-full flex-1 text-center min-w-max ${tab === 'barbeiros' ? 'text-orange-500 bg-orange-500/5' : 'text-zinc-400 hover:text-zinc-200'}`}><Store size={14} /><span>Loja</span></button>
                <button data-active={tab === 'freelancers'} onClick={() => setTab('freelancers')} className={`bm-bottom-nav-btn flex flex-col items-center justify-center gap-0.5 h-full flex-1 text-center min-w-max ${tab === 'freelancers' ? 'text-orange-500 bg-orange-500/5' : 'text-zinc-400 hover:text-zinc-200'}`}><Users size={14} /><span>Freelancers</span></button>
                <button data-active={tab === 'agenda'} onClick={() => setTab('agenda')} className={`bm-bottom-nav-btn flex flex-col items-center justify-center gap-0.5 h-full flex-1 text-center min-w-max ${tab === 'agenda' ? 'text-orange-500 bg-orange-500/5' : 'text-zinc-400 hover:text-zinc-200'}`}><Calendar size={14} /><span>Chamadas</span></button>
                <button data-active={tab === 'avaliar'} onClick={() => setTab('avaliar')} className={`bm-bottom-nav-btn flex flex-col items-center justify-center gap-0.5 h-full flex-1 text-center min-w-max ${tab === 'avaliar' ? 'text-orange-500 bg-orange-500/5' : 'text-zinc-400 hover:text-zinc-200'}`}><Star size={14} /><span>Avaliar</span></button>
                <button data-active={tab === 'perfil'} onClick={() => setTab('perfil')} className={`bm-bottom-nav-btn flex flex-col items-center justify-center gap-0.5 h-full flex-1 text-center min-w-max ${tab === 'perfil' ? 'text-orange-500 bg-orange-500/5' : 'text-zinc-400 hover:text-zinc-200'}`}><User size={14} /><span>Perfil</span></button>
                <button data-active={tab === 'pagamento'} onClick={() => setTab('pagamento')} className={`bm-bottom-nav-btn flex flex-col items-center justify-center gap-0.5 h-full flex-1 text-center min-w-max ${tab === 'pagamento' ? 'text-orange-500 bg-orange-500/5' : 'text-zinc-400 hover:text-zinc-200'}`}><CreditCard size={14} /><span>Carteira</span></button>
            </div>
            </div>
        </div>
        </ScreenWrapper>
    );
}