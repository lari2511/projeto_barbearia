import React, { useState, useEffect, useCallback } from 'react';
import { Store, LogOut, CheckCircle, AlertCircle, User, CreditCard, Calendar, Search, Star, ThumbsUp, TrendingUp } from 'lucide-react';
import PaymentSection from './PaymentSection';
import AbaPadronizadaAvaliacoes from './AbaPadronizadaAvaliacoes';
import TelaPerfilUsuario from './TelaPerfilUsuario';
import LiberarCadeirasComponent from './LiberarCadeirasComponent';
import TelaMensalidadeAssinatura from './TelaMensalidadeAssinatura';

export default function ShopDashboard({ token, logout, notify, API_URL }) {
    const [services, setServices] = useState([{id: 1, nome: "Corte Simples", valor: 30}]);
    const [newService, setNewService] = useState({nome: '', valor: ''});
    const [user, setUser] = useState(null);
    const [userData, setUserData] = useState(null);
    const [tab, setTab] = useState('barbeiros');
    const [agendamentos, setAgendamentos] = useState([]);
    const [freelancersPresentes, setFreelancersPresentes] = useState([]);
    const [freelancersDisponiveis, setFreelancersDisponiveis] = useState([]);
    const [freelancersPendentesAprovacao, setFreelancersPendentesAprovacao] = useState([]);
    const [ultimaAtualizacaoFreelancers, setUltimaAtualizacaoFreelancers] = useState(null);
    const [wsConectado, setWsConectado] = useState(false);
    const [_loading, _setLoading] = useState(false);
    const [barbeariaId, setBarbeariaId] = useState(null);

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

    // Carregar agendamentos da barbearia
    useEffect(() => {
        if (!barbeariaId) return;
        
        const carregarAgendamentos = async () => {
            try {
                const res = await fetch(`${API_URL}/api/v1/barbearias/${barbeariaId}/agendamentos`, {
                    headers: {'Authorization': `Bearer ${token}`}
                });
                if (res.ok) {
                    const data = await res.json();
                    setAgendamentos(Array.isArray(data) ? data : []);
                }
            } catch (err) {
                console.error('Erro ao carregar agendamentos:', err);
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
            console.error('Erro ao carregar freelancers');
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
            console.error('Erro ao carregar freelancers disponíveis');
            setFreelancersDisponiveis([]);
            setFreelancersPendentesAprovacao([]);
        }
    }, [API_URL, barbeariaId, token]);

    useEffect(() => {
        if (!barbeariaId || tab !== 'barbeiros') return;

        // Sincronização inicial sempre ocorre.
        carregarFreelancersPresentes();
        // eslint-disable-next-line react-hooks/set-state-in-effect
        carregarFreelancersDisponiveis();

        // Se o WebSocket estiver conectado, não precisamos de polling.
        if (wsConectado) return;

        const interval = setInterval(() => {
            carregarFreelancersPresentes();
            carregarFreelancersDisponiveis();
        }, 5000);
        return () => clearInterval(interval);
    }, [barbeariaId, tab, wsConectado, carregarFreelancersDisponiveis, carregarFreelancersPresentes]);

    useEffect(() => {
        if (!barbeariaId || tab !== 'barbeiros') return;

        const wsBase = API_URL.replace(/^http/, 'ws');
        const ws = new WebSocket(`${wsBase}/ws/notificacoes`);

        ws.onopen = () => {
            setWsConectado(true);
        };

        ws.onmessage = (event) => {
            try {
                const data = JSON.parse(event.data);
                if (data?.type !== 'freelancer_status_changed') return;

                const eventoBarbeariaId = data?.barbearia_id;
                if (eventoBarbeariaId && Number(eventoBarbeariaId) !== Number(barbeariaId)) {
                    return;
                }

                carregarFreelancersPresentes();
                carregarFreelancersDisponiveis();
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
    }, [API_URL, barbeariaId, tab, carregarFreelancersDisponiveis, carregarFreelancersPresentes]);

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
        <div className="bg-black h-full w-full max-w-full overflow-hidden flex flex-col text-white font-sans">
            <div className="p-2 sm:p-4 flex justify-between items-center border-b border-zinc-800 bg-black/80 backdrop-blur-md z-20 flex-shrink-0">
                <div className="flex items-center gap-2">
                    <h1 className="text-base sm:text-xl font-bold flex items-center gap-2">
                        <Store size={18} className="text-orange-500"/> Loja
                    </h1>
                    {user?.documento_verificado && (
                        <CheckCircle size={14} className="text-blue-500 fill-blue-500" />
                    )}
                </div>
                <button onClick={logout} className="text-zinc-500 hover:text-white"><LogOut size={18}/></button>
            </div>

            <div className="flex-1 overflow-y-auto pb-16">
                
                {tab === 'barbeiros' && (
                    <div className="p-2 sm:p-4 space-y-3 pb-20">
                        {user && !user.documento_verificado && (
                            <div className="bg-yellow-600/10 border border-yellow-600/30 p-2 rounded-lg flex items-center gap-2">
                                <AlertCircle size={14} className="text-yellow-500"/>
                                <span className="text-yellow-400 text-xs">Verificação pendente</span>
                            </div>
                        )}
                        
                        <h2 className="text-sm font-bold text-zinc-400 uppercase">Freelancers Presentes</h2>
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
                        <p className="text-[11px] text-zinc-500">
                            {wsConectado ? 'Canal ao vivo: WebSocket conectado' : 'Canal ao vivo: reconectando (fallback por polling ativo)'}
                        </p>
                        <div className="bg-zinc-900/50 border border-zinc-800 rounded-lg p-3 space-y-2">
                            <div className="flex items-center justify-between">
                                <h3 className="text-xs font-bold text-zinc-400 uppercase">Disponíveis para sua Barbearia</h3>
                                <span className="text-[11px] text-green-400 font-bold">{freelancersDisponiveis.length}</span>
                            </div>
                            {freelancersDisponiveis.length === 0 ? (
                                <p className="text-zinc-600 text-xs">Nenhum barbeiro disponível agora.</p>
                            ) : (
                                <div className="space-y-2">
                                    {freelancersDisponiveis.slice(0, 6).map((f) => (
                                        <div key={f.usuario_id} className="bg-black/40 border border-zinc-700 rounded p-2">
                                            <p className="text-sm font-bold text-white">{f.nome}</p>
                                            <p className="text-[11px] text-zinc-400">{f.presente_em_local ? 'Disponível no local' : 'Disponível na região'}</p>
                                        </div>
                                    ))}
                                </div>
                            )}
                        </div>

                        <div className="bg-zinc-900/50 border border-zinc-800 rounded-lg p-3 space-y-2">
                            <div className="flex items-center justify-between">
                                <h3 className="text-xs font-bold text-zinc-400 uppercase">Aguardando Aprovação</h3>
                                <span className="text-[11px] text-yellow-400 font-bold">{freelancersPendentesAprovacao.length}</span>
                            </div>
                            {freelancersPendentesAprovacao.length === 0 ? (
                                <p className="text-zinc-600 text-xs">Nenhum barbeiro pendente no momento.</p>
                            ) : (
                                <div className="space-y-2">
                                    {freelancersPendentesAprovacao.slice(0, 6).map((f) => (
                                        <div key={f.usuario_id} className="bg-black/40 border border-zinc-700 rounded p-2">
                                            <p className="text-sm font-bold text-white">{f.nome}</p>
                                            <p className="text-[11px] text-zinc-400">Perfil em análise pelo admin</p>
                                        </div>
                                    ))}
                                </div>
                            )}
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

                        {freelancersPresentes.length === 0 ? (
                            <p className="text-zinc-600 text-center py-8 text-xs">Nenhum freelancer presente no momento</p>
                        ) : (
                            <div className="space-y-2">
                                {freelancersPresentes.map(freelancer => (
                                    <div key={freelancer.id} className="bg-zinc-900/50 border border-zinc-800 p-3 rounded-lg space-y-2">
                                        <div className="flex justify-between items-start">
                                            <div>
                                                <p className="font-bold text-sm">{freelancer.nome}</p>
                                                <p className="text-xs text-zinc-400">{freelancer.email}</p>
                                            </div>
                                            <div className="h-2 w-2 bg-green-500 rounded-full animate-pulse"></div>
                                        </div>

                                        {/* 🎛️ CONTROLE DE STATUS (Controle Duplo) */}
                                        <div className="space-y-2 pt-2 border-t border-zinc-700">
                                            <p className="text-xs text-zinc-400 font-bold">Alterar Status:</p>
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
                                    </div>
                                ))}
                            </div>
                        )}

                        <h2 className="text-sm font-bold text-zinc-400 uppercase mt-6">Meus Serviços</h2>
                        <div className="bg-zinc-900/50 p-3 rounded-lg border border-zinc-800/50">
                            <form onSubmit={addService} className="space-y-2 mb-3">
                                <input
                                    className="w-full bg-black/50 text-white text-xs p-2 rounded border border-zinc-800 focus:border-orange-500 outline-none"
                                    placeholder="Nome do serviço"
                                    value={newService.nome}
                                    onChange={e => setNewService({...newService, nome: e.target.value})}
                                    required
                                />
                                <div className="flex gap-2">
                                    <input
                                        className="flex-1 bg-black/50 text-white text-xs p-2 rounded border border-zinc-800 focus:border-orange-500 outline-none"
                                        type="number"
                                        placeholder="Valor R$"
                                        value={newService.valor}
                                        onChange={e => setNewService({...newService, valor: e.target.value})}
                                        required
                                    />
                                    <button className="bg-orange-600 hover:bg-orange-700 text-white text-xs px-3 rounded font-bold transition">Adicionar</button>
                                </div>
                            </form>
                            
                            <div className="space-y-2">
                                {services.map(s => (
                                    <div key={s.id} className="flex justify-between items-center bg-black/40 p-2 rounded text-xs">
                                        <span>{s.nome}</span>
                                        <span className="text-green-400 font-bold">R$ {s.valor}</span>
                                    </div>
                                ))}
                            </div>
                        </div>

                        <div className="mt-8">
                            <LiberarCadeirasComponent 
                                token={token} 
                                API_URL={API_URL} 
                                notify={notify} 
                                barbeariaId={barbeariaId}
                            />
                        </div>
                    </div>
                )}

                {tab === 'agenda' && (
                    <div className="p-2 sm:p-4 space-y-3 pb-20">
                        <h2 className="text-sm font-bold text-zinc-400 uppercase">Agendamentos</h2>
                        
                        {agendamentos.length === 0 ? (
                            <p className="text-zinc-600 text-center py-12 text-xs">Nenhum agendamento</p>
                        ) : (
                            <div className="space-y-2">
                                {agendamentos.map(ag => (
                                    <div key={ag.id} className="bg-zinc-900/50 border border-zinc-800 p-3 rounded-lg space-y-2">
                                        <div className="flex justify-between items-start">
                                            <div>
                                                <p className="font-bold text-sm">{ag.servico_nome || 'Serviço'}</p>
                                                <p className="text-xs text-zinc-400">Cliente: {ag.cliente_nome}</p>
                                                <p className="text-xs text-zinc-400">Freelancer: {ag.barbeiro_nome}</p>
                                                <p className="text-xs text-zinc-400">
                                                    {ag.data_hora_inicio ? new Date(ag.data_hora_inicio).toLocaleString('pt-BR') : 'Horário não definido'}
                                                </p>
                                            </div>
                                            <div className={`text-xs px-2 py-1 rounded font-bold ${
                                                ag.status === 'concluido' ? 'bg-green-600/20 text-green-400' :
                                                ag.status === 'confirmado' ? 'bg-blue-600/20 text-blue-400' :
                                                ag.status === 'pendente' ? 'bg-yellow-600/20 text-yellow-400' :
                                                'bg-red-600/20 text-red-400'
                                            }`}>
                                                {ag.status.toUpperCase()}
                                            </div>
                                        </div>

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

                {tab === 'aprovar' && (
                    <div className="p-2 sm:p-4">
                        <h2 className="text-sm font-bold text-zinc-400 uppercase mb-4">Aprovações</h2>
                        <p className="text-zinc-600 text-center py-12 text-xs">Nenhuma aprovação</p>
                    </div>
                )}

                {tab === 'avaliar' && (
                    <div className="p-2 sm:p-4 pb-20">
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
                    <TelaPerfilUsuario userType="barbearia" token={token} onLogout={logout} onNotify={notify} />
                )}

                {tab === 'assinatura' && barbeariaId && (
                    <div className="p-2 sm:p-4 pb-24">
                        <TelaMensalidadeAssinatura
                            token={token}
                            barbeariaId={barbeariaId}
                            API_URL={API_URL}
                            onNotify={notify}
                        />
                    </div>
                )}

                {tab === 'pagamento' && (
                    <div className="p-2 sm:p-4 pb-20">
                        <PaymentSection userType="barbearia" token={token} onNotify={notify} />
                    </div>
                )}

            </div>

            <div className="fixed bottom-0 left-1/2 -translate-x-1/2 w-full max-w-[400px] h-16 bg-zinc-950/98 backdrop-blur-lg border-t border-zinc-800 flex justify-between items-center z-50 overflow-x-auto">
                <button onClick={() => setTab('barbeiros')} className={`flex flex-col items-center justify-center gap-0.5 h-full flex-1 text-center transition-colors min-w-max ${tab === 'barbeiros' ? 'text-orange-500 bg-orange-500/5' : 'text-zinc-500 hover:text-zinc-400'}`}><Search size={14} /><span className="text-[7px] font-bold">Serviços</span></button>
                <button onClick={() => setTab('agenda')} className={`flex flex-col items-center justify-center gap-0.5 h-full flex-1 text-center transition-colors min-w-max ${tab === 'agenda' ? 'text-orange-500 bg-orange-500/5' : 'text-zinc-500 hover:text-zinc-400'}`}><Calendar size={14} /><span className="text-[7px] font-bold">Agenda</span></button>
                <button onClick={() => setTab('aprovar')} className={`flex flex-col items-center justify-center gap-0.5 h-full flex-1 text-center transition-colors min-w-max ${tab === 'aprovar' ? 'text-orange-500 bg-orange-500/5' : 'text-zinc-500 hover:text-zinc-400'}`}><ThumbsUp size={14} /><span className="text-[7px] font-bold">Aprovar</span></button>
                <button onClick={() => setTab('avaliar')} className={`flex flex-col items-center justify-center gap-0.5 h-full flex-1 text-center transition-colors min-w-max ${tab === 'avaliar' ? 'text-orange-500 bg-orange-500/5' : 'text-zinc-500 hover:text-zinc-400'}`}><Star size={14} /><span className="text-[7px] font-bold">Avaliar</span></button>
                <button onClick={() => setTab('assinatura')} className={`flex flex-col items-center justify-center gap-0.5 h-full flex-1 text-center transition-colors min-w-max ${tab === 'assinatura' ? 'text-orange-500 bg-orange-500/5' : 'text-zinc-500 hover:text-zinc-400'}`}><TrendingUp size={14} /><span className="text-[7px] font-bold">Plano</span></button>
                <button onClick={() => setTab('perfil')} className={`flex flex-col items-center justify-center gap-0.5 h-full flex-1 text-center transition-colors min-w-max ${tab === 'perfil' ? 'text-orange-500 bg-orange-500/5' : 'text-zinc-500 hover:text-zinc-400'}`}><User size={14} /><span className="text-[7px] font-bold">Perfil</span></button>
                <button onClick={() => setTab('pagamento')} className={`flex flex-col items-center justify-center gap-0.5 h-full flex-1 text-center transition-colors min-w-max ${tab === 'pagamento' ? 'text-orange-500 bg-orange-500/5' : 'text-zinc-500 hover:text-zinc-400'}`}><CreditCard size={14} /><span className="text-[7px] font-bold">Pagar</span></button>
            </div>
        </div>
    );
}