import React, { useState, useEffect, useCallback, useMemo, useRef } from 'react';
import { getWsBaseUrl } from '../utils/api';
import { Store, LogOut, CheckCircle, AlertCircle, User, CreditCard, Calendar, Search, Star, TrendingUp, Users, Bell, Pencil, Trash2, X, Check } from 'lucide-react';
import PaymentSection from './PaymentSection';
import AbaPadronizadaAvaliacoes from './AbaPadronizadaAvaliacoes';
import TelaPerfilUsuario from './TelaPerfilUsuario';
import TelaMensalidadeAssinatura from './TelaMensalidadeAssinatura';
import { useBackHandler } from '../utils/useBackHandler';
import CronometroAtendimento, { parseDataServidorUTC } from './CronometroAtendimento';

const confirmarAcao = (mensagem) => {
    if (typeof window === 'undefined') return true;

    try {
        const userAgent = String(window.navigator?.userAgent || '').toLowerCase();
        const ambienteMobile = /android|iphone|ipad|ipod|wv|webview|capacitor/.test(userAgent);

        // Em webviews mobile, dialogos nativos (window.confirm) podem falhar
        // silenciosamente (retornar false sem mostrar nada); segue direto.
        if (ambienteMobile) return true;

        if (typeof window.confirm === 'function') {
            return window.confirm(mensagem);
        }

        return true;
    } catch (_err) {
        return true;
    }
};

export default function ShopDashboard({ token, logout, notify, API_URL }) {
    const TABS_VALIDAS = ['inicio', 'barbeiros', 'servicos', 'freelancers', 'agenda', 'avaliar', 'assinatura', 'perfil', 'pagamento'];
    const [services, setServices] = useState([]);
    const [newService, setNewService] = useState({ nome: '', valor: '', duracao_minutos: '30', categoria: 'outros', descricao: '' });
    const [editingServiceId, setEditingServiceId] = useState(null);
    const [editServiceForm, setEditServiceForm] = useState({ nome: '', valor: '', duracao_minutos: '' });
    const [savingServiceEdit, setSavingServiceEdit] = useState(false);
    const [user, setUser] = useState(null);
    const [userData, setUserData] = useState(null);
    const [tab, setTab] = useState(() => {
        if (typeof window === 'undefined') return 'barbeiros';
        const tabSalva = localStorage.getItem('barbearia_dashboard_tab') || 'inicio';
        return TABS_VALIDAS.includes(tabSalva) ? tabSalva : 'inicio';
    });
    useBackHandler(() => {
        if (tab === 'freelancers' || tab === 'servicos') { setTab('barbeiros'); return true; }
        if (tab === 'avaliar') { setTab('agenda'); return true; }
        if (tab === 'pagamento') { setTab('perfil'); return true; }
        if (tab === 'assinatura') { setTab('barbeiros'); return true; }
        if (tab !== 'inicio') { setTab('inicio'); return true; }
        return false;
    }, [tab]);

    const [agendamentos, setAgendamentos] = useState([]);
    const [freelancersPresentes, setFreelancersPresentes] = useState([]);
    const [freelancersDisponiveis, setFreelancersDisponiveis] = useState([]);
    const [freelancersPendentesAprovacao, setFreelancersPendentesAprovacao] = useState([]);
    const [cadeirasBarbearia, setCadeirasBarbearia] = useState([]);
    const [loadingCadeirasBarbearia, setLoadingCadeirasBarbearia] = useState(false);
    const [ultimaAtualizacaoFreelancers, setUltimaAtualizacaoFreelancers] = useState(null);
    const [wsConectado, setWsConectado] = useState(false);
    const [_loading, _setLoading] = useState(false);
    const [barbeariaId, setBarbeariaId] = useState(null);
    const [vagasRelampago, setVagasRelampago] = useState([]);
    const [acionandoCadeiraId, setAcionandoCadeiraId] = useState(null);
    const [cadeiraAnunciadaSucessoId, setCadeiraAnunciadaSucessoId] = useState(null);
    const [anunciandoProximaCadeira, setAnunciandoProximaCadeira] = useState(false);
    const [proximaCadeiraAnunciada, setProximaCadeiraAnunciada] = useState(false);
    const anuncioSucessoTimeoutRef = useRef(null);
    const anuncioProximaTimeoutRef = useRef(null);
    const freelancersPresentesNaBarbearia = useMemo(
        () => freelancersPresentes.filter((freelancer) =>
            freelancer?.presente_em_local &&
            (!freelancer?.barbearia_atual_id || Number(freelancer.barbearia_atual_id) === Number(barbeariaId))
        ),
        [freelancersPresentes, barbeariaId]
    );

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

    useEffect(() => () => {
        if (anuncioSucessoTimeoutRef.current) {
            clearTimeout(anuncioSucessoTimeoutRef.current);
        }
        if (anuncioProximaTimeoutRef.current) {
            clearTimeout(anuncioProximaTimeoutRef.current);
        }
    }, []);

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

    // Tique do cronômetro exibido nos atendimentos em andamento (mesma lógica do cliente/freelancer)
    const [agoraMsCronometro, setAgoraMsCronometro] = useState(Date.now());
    useEffect(() => {
        const t = setInterval(() => setAgoraMsCronometro(Date.now()), 1000);
        return () => clearInterval(t);
    }, []);

    // Cruza cadeiras com o chamado em_atendimento ativo (por freelancer), usado no destaque
    // "Atendimentos em andamento" da aba Chamadas/Agendamentos.
    const cadeirasComAtendimento = useMemo(() => {
        return cadeirasBarbearia.map((cadeira, index) => {
            const status = String(cadeira.status || cadeira.status_atendimento || '').trim().toLowerCase();
            const chamado = status === 'ocupada' && cadeira.freelancer_id
                ? agendamentos.find((ag) => (
                    String(ag.status || '').toLowerCase() === 'em_atendimento' &&
                    Number(ag.barbeiro_id) === Number(cadeira.freelancer_id)
                ))
                : null;
            return { cadeira, numeroExibido: index + 1, status, chamado };
        });
    }, [cadeirasBarbearia, agendamentos]);

    const carregarServicosBarbearia = useCallback(async () => {
        if (!barbeariaId) return;

        try {
            const res = await fetch(`${API_URL}/api/v1/barbearias/${barbeariaId}/servicos`, {
                headers: { 'Authorization': `Bearer ${token}` }
            });

            if (!res.ok) {
                setServices([]);
                return;
            }

            const data = await res.json();
            const lista = Array.isArray(data?.servicos) ? data.servicos : [];
            setServices(lista);
        } catch (_err) {
            setServices([]);
        }
    }, [API_URL, barbeariaId, token]);

    useEffect(() => {
        if (!barbeariaId) return;
        carregarServicosBarbearia();
    }, [barbeariaId, carregarServicosBarbearia]);

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
            return false;
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
                setCadeiraAnunciadaSucessoId(cadeiraId);
                if (anuncioSucessoTimeoutRef.current) {
                    clearTimeout(anuncioSucessoTimeoutRef.current);
                }
                anuncioSucessoTimeoutRef.current = setTimeout(() => {
                    setCadeiraAnunciadaSucessoId((atual) => (atual === cadeiraId ? null : atual));
                }, 1800);
                carregarCadeirasBarbearia();
                carregarFreelancersDisponiveis();
                carregarVagasRelampago();
                if (data?.cadeira_id) {
                    setVagasRelampago((prev) => {
                        const novaVaga = {
                            id: data.id || Date.now(),
                            cadeira_id: data.cadeira_id,
                            numero: data.numero,
                            barbearia_nome: userData?.nome || 'Barbearia',
                            barbearia_endereco: userData?.endereco || '',
                            status: 'disponivel',
                        };
                        const semDuplicata = prev.filter((vaga) => Number(vaga.cadeira_id) !== Number(novaVaga.cadeira_id));
                        return [novaVaga, ...semDuplicata];
                    });
                }
                return true;
            } else {
                const error = await res.json().catch(() => ({}));
                notify(error.detail || 'Erro ao acionar cadeira', 'error');
                return false;
            }
        } catch (_err) {
            notify('Erro ao conectar com servidor', 'error');
            return false;
        } finally {
            setAcionandoCadeiraId(null);
        }
    };

    const acionarPrimeiraCadeiraDisponivel = async () => {
        const primeiraDisponivel = cadeirasBarbearia.find((cadeira) => isCadeiraDisponivel(cadeira));
        if (!primeiraDisponivel) {
            notify('Nenhuma cadeira disponível para acionar', 'info');
            return;
        }
        setAnunciandoProximaCadeira(true);
        setProximaCadeiraAnunciada(false);
        const sucesso = await acionarCadeira(primeiraDisponivel.id);
        if (sucesso) {
            setProximaCadeiraAnunciada(true);
            if (anuncioProximaTimeoutRef.current) {
                clearTimeout(anuncioProximaTimeoutRef.current);
            }
            anuncioProximaTimeoutRef.current = setTimeout(() => {
                setProximaCadeiraAnunciada(false);
            }, 1800);
        }
        setAnunciandoProximaCadeira(false);
    };

    const isCadeiraDisponivel = (cadeira) => {
        const status = String(cadeira?.status || cadeira?.status_atendimento || '').trim().toLowerCase();
        return status === 'disponivel' || status === 'livre' || status === 'ativo';
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

    // Carrega o estado das cadeiras também na aba Chamadas/Agendamentos, para alimentar o
    // destaque "Atendimentos em andamento" sem exigir atualização manual da tela.
    useEffect(() => {
        if (!barbeariaId || tab !== 'agenda') return;

        carregarCadeirasBarbearia();
        const interval = setInterval(carregarCadeirasBarbearia, 10000);
        return () => clearInterval(interval);
    }, [barbeariaId, tab, carregarCadeirasBarbearia]);

    const addService = async (e) => {
        e.preventDefault();
        if (!newService.nome || !newService.valor) {
            notify("Preencha nome e valor", "error");
            return;
        }

        if (!barbeariaId) {
            notify("Barbearia não identificada", "error");
            return;
        }

        try {
            const res = await fetch(`${API_URL}/api/v1/barbearias/${barbeariaId}/servicos`, {
                method: 'POST',
                headers: {
                    'Authorization': `Bearer ${token}`,
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    nome: newService.nome.trim(),
                    categoria: newService.categoria || 'outros',
                    descricao: newService.descricao?.trim() || newService.nome.trim(),
                    valor: Number(newService.valor),
                    duracao_minutos: Number(newService.duracao_minutos) || 30,
                })
            });

            const data = await res.json().catch(() => ({}));
            if (!res.ok) {
                throw new Error(data.detail || 'Não foi possível salvar o serviço');
            }

            setNewService({ nome: '', valor: '', duracao_minutos: '30', categoria: 'outros', descricao: '' });
            await carregarServicosBarbearia();
            notify(data.mensagem || 'Serviço adicionado!', 'success');
        } catch (err) {
            notify(err.message || 'Erro ao salvar serviço', 'error');
        }
    };

    const iniciarEdicaoServico = (servico) => {
        setEditingServiceId(servico.id);
        setEditServiceForm({
            nome: servico.nome || '',
            valor: String(servico.valor ?? ''),
            duracao_minutos: String(servico.duracao_minutos ?? '30'),
        });
    };

    const cancelarEdicaoServico = () => {
        setEditingServiceId(null);
        setEditServiceForm({ nome: '', valor: '', duracao_minutos: '' });
    };

    const salvarEdicaoServico = async (servicoId) => {
        if (!editServiceForm.nome.trim() || !editServiceForm.valor) {
            notify('Preencha nome e valor', 'error');
            return;
        }

        setSavingServiceEdit(true);
        try {
            const res = await fetch(`${API_URL}/api/v1/servicos/${servicoId}`, {
                method: 'PUT',
                headers: {
                    'Authorization': `Bearer ${token}`,
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    nome: editServiceForm.nome.trim(),
                    valor: Number(editServiceForm.valor),
                    duracao_minutos: Number(editServiceForm.duracao_minutos) || 30,
                })
            });

            const data = await res.json().catch(() => ({}));
            if (!res.ok) {
                throw new Error(data.detail || 'Não foi possível atualizar o serviço');
            }

            cancelarEdicaoServico();
            await carregarServicosBarbearia();
            notify(data.mensagem || 'Serviço atualizado!', 'success');
        } catch (err) {
            notify(err.message || 'Erro ao atualizar serviço', 'error');
        } finally {
            setSavingServiceEdit(false);
        }
    };

    const excluirServico = async (servico) => {
        if (!confirmarAcao(`Excluir o serviço "${servico.nome}"? Essa ação não pode ser desfeita.`)) {
            return;
        }

        try {
            const res = await fetch(`${API_URL}/api/v1/servicos/${servico.id}`, {
                method: 'DELETE',
                headers: { 'Authorization': `Bearer ${token}` }
            });

            if (!res.ok) {
                const data = await res.json().catch(() => ({}));
                throw new Error(data.detail || 'Não foi possível excluir o serviço');
            }

            await carregarServicosBarbearia();
            notify('Serviço excluído!', 'success');
        } catch (err) {
            notify(err.message || 'Erro ao excluir serviço', 'error');
        }
    };

    return (
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
                        <div className="grid grid-cols-3 gap-2">
                            <button type="button" onClick={() => setTab('barbeiros')} className="rounded-xl px-2 py-2 text-xs font-bold bg-orange-500 text-white">Cadeiras</button>
                            <button type="button" onClick={() => setTab('servicos')} className="rounded-xl px-2 py-2 text-xs font-bold bg-zinc-800 text-zinc-300 hover:bg-zinc-700">Serviços</button>
                            <button type="button" onClick={() => setTab('freelancers')} className="rounded-xl px-2 py-2 text-xs font-bold bg-zinc-800 text-zinc-300 hover:bg-zinc-700">Freelancers</button>
                        </div>
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
                                                        <div>
                                                            <h3 className="text-purple-400 font-bold text-sm flex items-center gap-2">💺 Cadeiras ativas do plano ({cadeirasBarbearia.length})</h3>
                                                            <p className="mt-1 text-[11px] text-zinc-400">A ordem aqui é a ordem paga no plano. Se você tem 1 cadeira, só deve ver a Cadeira 1.</p>
                                                        </div>
                                                        <button
                                                            onClick={() => setTab('assinatura')}
                                                            className="bg-gradient-to-r from-orange-600 to-red-600 text-white px-3 py-1.5 rounded-2xl text-xs font-extrabold flex items-center gap-1 transition-all"
                                                        >
                                                            <span className="text-lg leading-none">+</span> Assinatura
                                                        </button>
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
                                                            {cadeirasBarbearia.map((cadeira, index) => {
                                                                const status = String(cadeira.status || cadeira.status_atendimento || '').trim().toLowerCase();
                                                                const disponivel = isCadeiraDisponivel(cadeira);
                                                                const cadeiraComVagaAberta = vagasRelampago.some((vaga) => (
                                                                    Number(vaga?.cadeira_id) === Number(cadeira.id) &&
                                                                    String(vaga?.status || '').toLowerCase() === 'disponivel'
                                                                ));
                                const statusConfig = {
                                  disponivel: { bg: 'bg-black/40', border: 'border-green-600/30', label: '🟢 Disponível', labelColor: 'text-green-400', labelBg: 'bg-green-600/20' },
                                  ocupada: { bg: 'bg-black/40', border: 'border-orange-600/30', label: '🔴 Ocupada', labelColor: 'text-orange-300', labelBg: 'bg-orange-600/20' },
                                  bloqueada: { bg: 'bg-black/40', border: 'border-red-600/30', label: '🔒 Bloqueada', labelColor: 'text-red-400', labelBg: 'bg-red-600/20' }
                                };
                                const config = statusConfig[status] || (disponivel ? statusConfig.disponivel : statusConfig.ocupada);
                                const numeroExibido = index + 1;
                                const badgeText = disponivel
                                  ? '● Disponível agora'
                                  : status === 'ocupada' && cadeira.freelancer_nome
                                    ? `🔴 Ocupada por ${cadeira.freelancer_nome}`
                                    : config.label;
                                const chamadoDaCadeira = status === 'ocupada' && cadeira.freelancer_id
                                    ? agendamentos.find((ag) => (
                                        String(ag.status || '').toLowerCase() === 'em_atendimento' &&
                                        Number(ag.barbeiro_id) === Number(cadeira.freelancer_id)
                                    ))
                                    : null;

                                return (
                                  <div key={cadeira.id} className={`${config.bg} border ${config.border} p-3 rounded-lg transition-all hover:border-purple-600/50`}>
                                    <div className="flex items-center justify-between">
                                      <div className="flex-1">
                                                                                <p className="font-bold text-sm text-white">Cadeira {numeroExibido}</p>
                                                                                <div className="mt-1 flex flex-wrap items-center gap-2">
                                                                                    <span className={`inline-flex items-center gap-1 rounded-full px-2 py-1 text-[11px] font-extrabold border ${disponivel ? 'bg-green-500/15 text-green-300 border-green-500/30' : config.labelBg + ' ' + config.labelColor + ' border-transparent'}`}>
                                                                                        {badgeText}
                                                                                    </span>
                                                                                </div>
                                                                                <p className="text-[11px] text-zinc-500 mt-1">Essa é a cadeira paga do plano. O número interno do banco não muda a ordem exibida.</p>
                                      </div>
                                      <div className="flex gap-2">
                                                                                {disponivel && (
                                          <>
                                                                                        <button 
                                                                                            onClick={() => acionarCadeira(cadeira.id)}
                                                                                            disabled={acionandoCadeiraId === cadeira.id || cadeiraComVagaAberta}
                                                                                            className={`${cadeiraComVagaAberta ? 'bg-emerald-700 text-emerald-100 cursor-not-allowed' : 'bg-orange-600 hover:bg-orange-700 disabled:bg-orange-800/50 text-white'} px-3 py-2 rounded-lg text-xs font-bold transition-all`}
                                                                                            title={cadeiraComVagaAberta ? 'Esta cadeira já está anunciada como vaga relâmpago' : 'Usar quando quiser anunciar esta cadeira para barbeiros disponíveis'}
                                                                                        >
                                                                                            {acionandoCadeiraId === cadeira.id ? 'Anunciando...' : cadeiraComVagaAberta ? 'Vaga acionada' : cadeiraAnunciadaSucessoId === cadeira.id ? 'Anunciada' : 'Anunciar vaga'}
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
                                                                                {!disponivel && status === 'ocupada' && (
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
                                    {chamadoDaCadeira && (
                                        <div className="mt-2">
                                            <CronometroAtendimento
                                                chamado={chamadoDaCadeira}
                                                chamadosGrupo={agendamentos}
                                                chamadoAtivoId={chamadoDaCadeira.id}
                                                isPausado={Boolean(chamadoDaCadeira.pausado)}
                                                pausadoEmMs={chamadoDaCadeira.pausado_em ? parseDataServidorUTC(chamadoDaCadeira.pausado_em) : null}
                                                pausaAcumuladaMs={Math.round((Number(chamadoDaCadeira.pausa_acumulada_segundos) || 0) * 1000)}
                                                agoraMs={agoraMsCronometro}
                                                compacto
                                            />
                                        </div>
                                    )}
                                  </div>
                                );
                              })}
                                                            <button
                                                                onClick={acionarPrimeiraCadeiraDisponivel}
                                                                disabled={anunciandoProximaCadeira}
                                                                className={`w-full px-4 py-3 rounded-lg font-bold text-sm mt-3 transition-all duration-200 inline-flex items-center justify-center gap-2 transform ${proximaCadeiraAnunciada ? 'bg-emerald-600 hover:bg-emerald-600 ring-1 ring-emerald-300/40 shadow-lg shadow-emerald-500/20 scale-[1.02]' : 'bg-purple-600 hover:bg-purple-700 scale-100'} disabled:bg-purple-800/50 text-white`}
                              >
                                                                                                                                {anunciandoProximaCadeira ? (
                                                                                                                                    'Anunciando vaga...'
                                                                                                                                ) : proximaCadeiraAnunciada ? (
                                                                                                                                    <>
                                                                                                                                        <CheckCircle size={16} className="animate-pulse" />
                                                                                                                                        Vaga anunciada
                                                                                                                                    </>
                                                                                                                                ) : (
                                                                                                                                    '⚡ Anunciar próxima cadeira disponível'
                                                                                                                                )}
                              </button>
                            </div>
                          )}

                                                    <div className="mt-4 rounded-xl border border-zinc-800 bg-zinc-950/50 p-3 text-xs text-zinc-300">
                                                        <p className="font-bold text-orange-300 mb-1">Como funciona</p>
                                                        <p className="text-zinc-400 leading-relaxed">
                                                            Você paga pelas cadeiras ativas do plano. Quando uma cadeira está <strong>disponível</strong>, o botão <strong>Anunciar vaga</strong> avisa os barbeiros que aquele posto pode ser usado.
                                                            Se você tem apenas 1 cadeira contratada, a tela deve mostrar só a <strong>Cadeira 1</strong>.
                                                        </p>
                                                    </div>

                          <div className="bg-zinc-900/50 p-3 rounded-lg mt-4 border border-zinc-800">
                            <p className="text-zinc-400 text-xs mb-2">💡 <strong>Dicas:</strong></p>
                            <ul className="text-zinc-500 text-[10px] space-y-1 ml-4">
                              <li>• Use <strong>"Anunciar vaga"</strong> quando quiser que barbeiros encontrem sua cadeira disponível</li>
                              <li>• <strong>Bloqueie</strong> cadeiras em manutenção ou reservadas</li>
                              <li>• O sistema libera automaticamente clientes quando faltam 15 min</li>
                            </ul>
                          </div>
                        </div>

                    </div>
                )}

                {/* ABA: CADASTRAR SERVIÇO */}
                {tab === 'servicos' && (
                    <div className="p-2 sm:p-4 space-y-3 pb-20 max-w-3xl mx-auto w-full">
                        <div className="grid grid-cols-3 gap-2">
                            <button type="button" onClick={() => setTab('barbeiros')} className="rounded-xl px-2 py-2 text-xs font-bold bg-zinc-800 text-zinc-300 hover:bg-zinc-700">Cadeiras</button>
                            <button type="button" onClick={() => setTab('servicos')} className="rounded-xl px-2 py-2 text-xs font-bold bg-orange-500 text-white">Serviços</button>
                            <button type="button" onClick={() => setTab('freelancers')} className="rounded-xl px-2 py-2 text-xs font-bold bg-zinc-800 text-zinc-300 hover:bg-zinc-700">Freelancers</button>
                        </div>

                        <div className="bg-zinc-900/60 p-5 rounded-2xl border border-purple-600/30">
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
                                    editingServiceId === s.id ? (
                                      <div key={s.id} className="bg-black/60 p-3 rounded-lg border border-purple-500 space-y-2">
                                        <input
                                          className="w-full bg-black rounded-lg p-2 border border-zinc-800 text-sm outline-none focus:border-purple-500 text-white"
                                          placeholder="Nome do serviço"
                                          value={editServiceForm.nome}
                                          onChange={e => setEditServiceForm({ ...editServiceForm, nome: e.target.value })}
                                        />
                                        <div className="grid grid-cols-2 gap-2">
                                          <input
                                            className="bg-black rounded-lg p-2 border border-zinc-800 text-sm outline-none focus:border-purple-500 text-white"
                                            type="number"
                                            placeholder="Valor R$"
                                            value={editServiceForm.valor}
                                            onChange={e => setEditServiceForm({ ...editServiceForm, valor: e.target.value })}
                                          />
                                          <input
                                            className="bg-black rounded-lg p-2 border border-zinc-800 text-sm outline-none focus:border-purple-500 text-white"
                                            type="number"
                                            placeholder="Duração (min)"
                                            value={editServiceForm.duracao_minutos}
                                            onChange={e => setEditServiceForm({ ...editServiceForm, duracao_minutos: e.target.value })}
                                          />
                                        </div>
                                        <div className="flex gap-2">
                                          <button
                                            type="button"
                                            disabled={savingServiceEdit}
                                            onClick={() => salvarEdicaoServico(s.id)}
                                            className="flex-1 flex items-center justify-center gap-1 bg-green-600 hover:bg-green-700 disabled:opacity-60 text-white px-3 py-2 rounded-lg text-xs font-bold"
                                          >
                                            <Check size={14} /> Salvar
                                          </button>
                                          <button
                                            type="button"
                                            disabled={savingServiceEdit}
                                            onClick={cancelarEdicaoServico}
                                            className="flex-1 flex items-center justify-center gap-1 bg-zinc-800 hover:bg-zinc-700 disabled:opacity-60 text-white px-3 py-2 rounded-lg text-xs font-bold"
                                          >
                                            <X size={14} /> Cancelar
                                          </button>
                                        </div>
                                      </div>
                                    ) : (
                                      <div key={s.id} className="flex justify-between items-center bg-black/60 p-3 rounded-lg border border-purple-600/20 hover:border-purple-600/40 transition-colors">
                                        <span className="text-sm font-medium text-white truncate mr-2">{s.nome}</span>
                                        <div className="text-right flex items-center gap-3 shrink-0">
                                          <span className="text-green-400 font-bold text-sm">R$ {parseFloat(s.valor).toFixed(2)}</span>
                                          <span className="text-purple-400 font-bold text-sm">{Number(s.duracao_minutos) || 30} min</span>
                                          <button
                                            type="button"
                                            onClick={() => iniciarEdicaoServico(s)}
                                            aria-label="Editar serviço"
                                            className="h-8 w-8 flex items-center justify-center rounded-lg bg-zinc-800 hover:bg-zinc-700 text-zinc-300 hover:text-white"
                                          >
                                            <Pencil size={14} />
                                          </button>
                                          <button
                                            type="button"
                                            onClick={() => excluirServico(s)}
                                            aria-label="Excluir serviço"
                                            className="h-8 w-8 flex items-center justify-center rounded-lg bg-red-900/40 hover:bg-red-700 text-red-300 hover:text-white"
                                          >
                                            <Trash2 size={14} />
                                          </button>
                                        </div>
                                      </div>
                                    )
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
                        <div className="grid grid-cols-3 gap-2">
                            <button type="button" onClick={() => setTab('barbeiros')} className="rounded-xl px-2 py-2 text-xs font-bold bg-zinc-800 text-zinc-300 hover:bg-zinc-700">Cadeiras</button>
                            <button type="button" onClick={() => setTab('servicos')} className="rounded-xl px-2 py-2 text-xs font-bold bg-zinc-800 text-zinc-300 hover:bg-zinc-700">Serviços</button>
                            <button type="button" onClick={() => setTab('freelancers')} className="rounded-xl px-2 py-2 text-xs font-bold bg-orange-500 text-white">Freelancers</button>
                        </div>
                        <h2 className="text-sm font-bold text-zinc-300 uppercase tracking-wide">Controle de Freelancers</h2>

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
                                            <p className="text-[11px] text-zinc-400">Perfil em análise</p>
                                        </div>
                                    ))}
                                </div>
                            )}
                        </div>
                    </div>
                )}

                {tab === 'agenda' && (
                    <div className="p-2 sm:p-4 space-y-3 pb-20 max-w-3xl mx-auto w-full">
                        <div className="grid grid-cols-2 gap-2">
                            <button type="button" onClick={() => setTab('agenda')} className="rounded-xl px-3 py-2 text-xs font-bold bg-orange-500 text-white">Chamadas</button>
                            <button type="button" onClick={() => setTab('avaliar')} className="rounded-xl px-3 py-2 text-xs font-bold bg-zinc-800 text-zinc-300 hover:bg-zinc-700">Avaliar</button>
                        </div>
                        {cadeirasComAtendimento.length > 0 && (
                            <div className="space-y-2.5">
                                <h2 className="text-sm font-bold text-zinc-300 uppercase tracking-wide">Atendimentos em andamento</h2>

                                {cadeirasComAtendimento.some((c) => c.chamado) ? (
                                    <div className="space-y-2">
                                        {cadeirasComAtendimento.filter((c) => c.chamado).map(({ cadeira, numeroExibido, chamado }) => (
                                            <div key={cadeira.id} className="bm-card border border-emerald-600/40 bg-emerald-950/10 p-3.5 space-y-2">
                                                <div className="flex items-center justify-between gap-2">
                                                    <p className="font-bold text-sm text-white">Cadeira {numeroExibido} — Ocupada</p>
                                                    <span className="inline-flex items-center gap-1 text-[11px] font-extrabold text-emerald-300 bg-emerald-600/20 px-2 py-1 rounded-full whitespace-nowrap">
                                                        <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" /> Em atendimento
                                                    </span>
                                                </div>
                                                <p className="text-xs text-zinc-300 truncate">Freelancer: <span className="font-semibold text-white">{chamado.barbeiro_nome || chamado.nome_barbeiro}</span></p>
                                                <p className="text-xs text-zinc-300 truncate">Cliente: <span className="font-semibold text-white">{chamado.cliente_nome || chamado.nome_cliente}</span></p>
                                                <p className="text-xs text-zinc-300 truncate">Serviço: <span className="font-semibold text-white">{chamado.servico_nome || chamado.descricao || 'Serviço'}</span></p>
                                                <CronometroAtendimento
                                                    chamado={chamado}
                                                    chamadosGrupo={agendamentos}
                                                    chamadoAtivoId={chamado.id}
                                                    isPausado={Boolean(chamado.pausado)}
                                                    pausadoEmMs={chamado.pausado_em ? parseDataServidorUTC(chamado.pausado_em) : null}
                                                    pausaAcumuladaMs={Math.round((Number(chamado.pausa_acumulada_segundos) || 0) * 1000)}
                                                    agoraMs={agoraMsCronometro}
                                                    compacto
                                                />
                                            </div>
                                        ))}
                                    </div>
                                ) : (
                                    <p className="text-zinc-600 text-xs">Nenhum atendimento em andamento no momento.</p>
                                )}

                                <div className="flex flex-wrap gap-2">
                                    {cadeirasComAtendimento.map(({ cadeira, numeroExibido, status }) => (
                                        <span
                                            key={cadeira.id}
                                            className={`text-[11px] font-bold px-2 py-1 rounded-full border ${
                                                status === 'ocupada' ? 'bg-emerald-600/15 text-emerald-300 border-emerald-600/30' :
                                                status === 'bloqueada' ? 'bg-red-600/15 text-red-300 border-red-600/30' :
                                                'bg-zinc-800 text-zinc-400 border-zinc-700'
                                            }`}
                                        >
                                            Cadeira {numeroExibido} — {status === 'ocupada' ? '🟢 Ocupada' : status === 'bloqueada' ? '🔒 Bloqueada' : '⚪ Livre'}
                                        </span>
                                    ))}
                                </div>
                            </div>
                        )}

                        <h2 className="text-sm font-bold text-zinc-300 uppercase tracking-wide">Agendamentos</h2>

                        {agendamentos.length === 0 ? (
                            <p className="text-zinc-600 text-center py-12 text-xs">Nenhum agendamento</p>
                        ) : (
                            <div className="space-y-2 max-w-2xl mx-auto w-full">
                                {agendamentos.map(ag => (
                                    <div key={ag.id} className="bm-card p-3.5 space-y-2.5 overflow-hidden">
                                        <div className="flex justify-between items-start">
                                            <div className="min-w-0 pr-2">
                                                <p className="font-bold text-sm truncate">{ag.servico_nome || ag.descricao || 'Serviço'}</p>
                                                <p className="text-xs text-zinc-400 truncate">Cliente: {ag.cliente_nome || ag.nome_cliente}</p>
                                                <p className="text-xs text-zinc-400 truncate">Freelancer: {ag.barbeiro_nome || ag.nome_barbeiro}</p>
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

                                        {ag.status === 'em_atendimento' && (
                                            <CronometroAtendimento
                                                chamado={ag}
                                                chamadosGrupo={agendamentos}
                                                chamadoAtivoId={ag.id}
                                                isPausado={Boolean(ag.pausado)}
                                                pausadoEmMs={ag.pausado_em ? parseDataServidorUTC(ag.pausado_em) : null}
                                                pausaAcumuladaMs={Math.round((Number(ag.pausa_acumulada_segundos) || 0) * 1000)}
                                                agoraMs={agoraMsCronometro}
                                                compacto
                                            />
                                        )}

                                        {/* ✅ APENAS VISUALIZAÇÃO - Dono não pode aceitar/recusar */}
                                        {ag.status === 'pendente' && (
                                            <div className="bg-yellow-900/20 border border-yellow-600/30 p-2 rounded text-xs text-yellow-400">
                                                ⏳ Aguardando aceitação do freelancer
                                            </div>
                                        )}

                                        {/* 🎯 AVALIAR FREELANCER - Após concluído */}
                                        {ag.status === 'concluido' && !(ag.avaliado_por_barbearia ?? ag.avaliado) && (
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
                    <div className="p-2 sm:p-4 pb-20 max-w-3xl mx-auto w-full space-y-3">
                        <div className="grid grid-cols-2 gap-2">
                            <button type="button" onClick={() => setTab('agenda')} className="rounded-xl px-3 py-2 text-xs font-bold bg-zinc-800 text-zinc-300 hover:bg-zinc-700">Chamadas</button>
                            <button type="button" onClick={() => setTab('avaliar')} className="rounded-xl px-3 py-2 text-xs font-bold bg-orange-500 text-white">Avaliar</button>
                        </div>
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
                    <div className="p-2 sm:p-4 pb-24 max-w-3xl mx-auto w-full space-y-4">
                        <div className="grid grid-cols-2 gap-2">
                            <button type="button" onClick={() => setTab('perfil')} className="rounded-xl px-3 py-2 text-xs font-bold bg-orange-500 text-white">Dados</button>
                            <button type="button" onClick={() => setTab('pagamento')} className="rounded-xl px-3 py-2 text-xs font-bold bg-zinc-800 text-zinc-300 hover:bg-zinc-700">Carteira</button>
                        </div>
                        <TelaPerfilUsuario
                            userType="barbearia"
                            token={token}
                            API_URL={API_URL}
                            onLogout={logout}
                            onNotify={notify}
                            mostrarFinanceiroBarbearia={false}
                            mostrarCabecalho={false}
                        />
                    </div>
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
                    <div className="p-2 sm:p-4 pb-20 max-w-3xl mx-auto w-full space-y-3">
                        <div className="grid grid-cols-2 gap-2">
                            <button type="button" onClick={() => setTab('perfil')} className="rounded-xl px-3 py-2 text-xs font-bold bg-zinc-800 text-zinc-300 hover:bg-zinc-700">Dados</button>
                            <button type="button" onClick={() => setTab('pagamento')} className="rounded-xl px-3 py-2 text-xs font-bold bg-orange-500 text-white">Carteira</button>
                        </div>
                        <PaymentSection userType="barbearia" token={token} onNotify={notify} />
                    </div>
                )}
            </div>

            <div className="bm-bottom-nav sticky bottom-0 left-0 w-full h-[calc(5.1rem+env(safe-area-inset-bottom))] pb-[env(safe-area-inset-bottom)] grid grid-cols-4 gap-1 items-stretch z-40 px-2 sm:px-3">
                <button data-active={tab === 'inicio'} onClick={() => setTab('inicio')} className={`bm-bottom-nav-btn flex flex-col items-center justify-center gap-0.5 h-full text-center rounded-xl ${tab === 'inicio' ? 'text-orange-500 bg-orange-500/5' : 'text-zinc-400 hover:text-zinc-200'}`}><span className="text-sm">🏠</span><span className="text-[10px] leading-none">Início</span></button>
                <button data-active={tab === 'barbeiros' || tab === 'servicos' || tab === 'freelancers'} onClick={() => setTab('barbeiros')} className={`bm-bottom-nav-btn flex flex-col items-center justify-center gap-0.5 h-full text-center rounded-xl ${tab === 'barbeiros' || tab === 'servicos' || tab === 'freelancers' ? 'text-orange-500 bg-orange-500/5' : 'text-zinc-400 hover:text-zinc-200'}`}><Store size={14} /><span className="text-[10px] leading-none">Loja</span></button>
                <button data-active={tab === 'agenda' || tab === 'avaliar'} onClick={() => setTab('agenda')} className={`bm-bottom-nav-btn flex flex-col items-center justify-center gap-0.5 h-full text-center rounded-xl ${tab === 'agenda' || tab === 'avaliar' ? 'text-orange-500 bg-orange-500/5' : 'text-zinc-400 hover:text-zinc-200'}`}><Calendar size={14} /><span className="text-[10px] leading-none">Chamadas</span></button>
                <button data-active={tab === 'perfil' || tab === 'pagamento'} onClick={() => setTab('perfil')} className={`bm-bottom-nav-btn flex flex-col items-center justify-center gap-0.5 h-full text-center rounded-xl ${tab === 'perfil' || tab === 'pagamento' ? 'text-orange-500 bg-orange-500/5' : 'text-zinc-400 hover:text-zinc-200'}`}><User size={14} /><span className="text-[10px] leading-none">Perfil</span></button>
            </div>
            </div>
        </div>
    );
}