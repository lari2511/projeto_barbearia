import React, { useState, useEffect, useCallback } from 'react';
import { LogOut, Search, MapPin, Star, Calendar, ArrowRight, CheckCircle, User, CreditCard, MessageSquare, DollarSign, QrCode, X } from 'lucide-react';
import TelaPagamento from './TelaPagamento';
import TelaPerfilUsuario from './TelaPerfilUsuario';
import MapEmbed from './MapEmbed';
import AbaPadronizadaAvaliacoes from './AbaPadronizadaAvaliacoes';
import ProfileCard from './ProfileCard';

const getShopImage = (id) => `https://images.unsplash.com/photo-${id % 2 === 0 ? '1521590832874-552721032d00' : '1503951914290-d20607416905'}?auto=format&fit=crop&w=800&q=80`;

export default function ClientDashboard({ token, logout, API_URL, notify }) {
    const [shops, setShops] = useState([]); // Agora são BARBEIROS
    const [tab, setTab] = useState('buscar'); // 'buscar' | 'agenda' | 'avaliar' | 'perfil' | 'pagamento' 
    const [selectedBarber, setSelectedBarber] = useState(null); // Barbeiro selecionado
    const [barbearias, setBarbearias] = useState([]); // Barbearias disponíveis
    const [selectedBarbearia, setSelectedBarbearia] = useState(null); // Barbearia escolhida
    const [services, setServices] = useState([]);
    const [selectedServices, setSelectedServices] = useState([]);
    const [myOrders, setMyOrders] = useState([]);
        const [chamadoParaPagar, setChamadoParaPagar] = useState(null); // { id, valor, descricao }
    const [barbeiroInfo, setBarbeiroInfo] = useState(null);
    const [userLocation, setUserLocation] = useState(null);
    const [loadingLocation, setLoadingLocation] = useState(false);
    const [step, setStep] = useState('barbeiros'); // 'barbeiros' -> 'barbearias' -> 'servicos'
    const [userData, setUserData] = useState(null); // Dados do usuário logado
    const [dataHoraInicio, setDataHoraInicio] = useState('');
    const [perfilModal, setPerfilModal] = useState(null);

    const loadDefaultShops = useCallback(() => {
        // Carrega todos os barbeiros sem filtro de localização
        fetch(`${API_URL}/api/v1/barbeiros/todos`)
            .then(r => r.json())
            .then(data => {
                setShops(data);
            })
            .catch(() => {
                notify("Erro ao carregar barbeiros", "error");
            });
    }, [API_URL, notify]);

    const carregarMeusPedidos = useCallback(() => {
        fetch(`${API_URL}/api/v1/cliente/meus_pedidos`, { headers: {'Authorization': `Bearer ${token}`} })
            .then(r => r.json())
            .then(data => setMyOrders(Array.isArray(data) ? data : []))
            .catch(() => setMyOrders([]));
    }, [API_URL, token]);

    useEffect(() => {
        // NÃO solicitar localização automaticamente no início
        // Usuário pode buscar barbeiros manualmente quando quiser
        loadDefaultShops();
        
        // Carregar dados do usuário
        fetch(`${API_URL}/api/v1/usuarios/perfil-completo`, {
            headers: {'Authorization': `Bearer ${token}`}
        })
            .then(r => r.json())
            .then(setUserData)
            .catch(() => {});
    }, [API_URL, loadDefaultShops, token]);

    const requestUserLocation = () => {
        if (!navigator.geolocation) {
            notify("Seu navegador não suporta geolocalização", "error");
            loadDefaultShops();
            return;
        }

        setLoadingLocation(true);
        navigator.geolocation.getCurrentPosition(
            (position) => {
                const location = {
                    latitude: position.coords.latitude,
                    longitude: position.coords.longitude
                };
                setUserLocation(location);
                fetchNearbyShops(location);
                setLoadingLocation(false);
            },
            (error) => {
                const msg = error && error.code === 1
                    ? 'Permissão de localização negada. Ative nas configurações do navegador.'
                    : 'Não foi possível obter sua localização. Mostrando todas as barbearias.';
                notify(msg, "warning");
                loadDefaultShops();
                setLoadingLocation(false);
            }
        );
    };

    const fetchNearbyShops = async (location) => {
        try {
            // BUSCAR APENAS BARBEIROS PRÓXIMOS (não barbearias)
            const url = new URL(`${API_URL}/api/v1/barbeiros/proximos`);
            url.searchParams.append('latitude', location.latitude);
            url.searchParams.append('longitude', location.longitude);
            url.searchParams.append('raio_km', '10.0');
            
            const res = await fetch(url.toString(), {
                method: 'GET',
                headers: { 
                    'Authorization': `Bearer ${token}`
                }
            });
            
            if (res.ok) {
                const data = await res.json();
                console.log('🗺️ Barbeiros próximos:', data);
                setShops(data);
                if (data.length === 0) {
                    notify("Nenhum barbeiro encontrado próximo a você (raio 10km)", "info");
                } else {
                    notify(`${data.length} barbeiro(s) encontrado(s) próximo a você!`, "success");
                }
            } else {
                console.error('Erro ao buscar barbeiros:', res.status);
                loadDefaultShops();
            }
        } catch (err) {
            console.error('Erro na fetch:', err);
            loadDefaultShops();
        }
    };

    useEffect(() => {
        carregarMeusPedidos();
    }, [carregarMeusPedidos]);

    const handleSelectShop = async (barber) => {
        setSelectedBarber(barber);
        setStep('barbearias');
        
        try {
            // Buscar barbearias onde este barbeiro pode atender
            const res = await fetch(`${API_URL}/api/v1/barbeiro/${barber.id}/barbearias`, {
                headers: {'Authorization': `Bearer ${token}`}
            });
            let data = await res.json();
            const barbeariasDoBarbeiro = Array.isArray(data) ? data : [];
            
            // 📍 Se temos localização, FILTRAR barbearias dentro de 10km
            if (userLocation) {
                const barbeariaUrl = new URL(`${API_URL}/api/v1/barbearias/proximas`);
                barbeariaUrl.searchParams.append('latitude', userLocation.latitude);
                barbeariaUrl.searchParams.append('longitude', userLocation.longitude);
                barbeariaUrl.searchParams.append('raio_km', '10.0');
                
                try {
                    const proxRes = await fetch(barbeariaUrl.toString());
                    const proxBarbearias = await proxRes.json();
                    
                    // Manter apenas barbearias que o barbeiro trabalha E que estão próximas.
                    // Se nada cair no raio, mantém as barbearias válidas do barbeiro para não bloquear o agendamento.
                    const barbeariaIds = new Set(barbeariasDoBarbeiro.map(b => b.id));
                    const filtradasPorRaio = proxBarbearias.filter(b => barbeariaIds.has(b.id));

                    if (filtradasPorRaio.length > 0) {
                        data = filtradasPorRaio;
                        notify(`${filtradasPorRaio.length} barbearia(s) próxima(s) encontrada(s)!`, "success");
                    } else {
                        data = barbeariasDoBarbeiro;
                    }
                } catch (_err) {
                    console.error('Erro ao buscar barbearias próximas');
                    // Continuar com barbearias do barbeiro mesmo que a busca de proximas falhe
                    data = barbeariasDoBarbeiro;
                }
            }
            
            setBarbearias(data);
            
            // Buscar informações do barbeiro
            const infoRes = await fetch(`${API_URL}/api/v1/usuario/${barber.id}`, {
                headers: {'Authorization': `Bearer ${token}`}
            });
            if (infoRes.ok) {
                const info = await infoRes.json();
                setBarbeiroInfo(info);
            }
        } catch (_err) {
            setBarbearias([]);
        }
    };

    const handleSelectBarbearia = async (barbearia) => {
        setSelectedBarbearia(barbearia);
        setStep('servicos');
        
        try {
            // Buscar serviços da barbearia
            const res = await fetch(`${API_URL}/api/v1/barbearia/${barbearia.id}/servicos`, {
                headers: {'Authorization': `Bearer ${token}`}
            });
            const data = await res.json();
            setServices(Array.isArray(data) ? data : []);
        } catch (_err) {
            setServices([
                {id: 1, nome: "Corte Masculino", valor: 35, duracao_minutos: 30},
                {id: 2, nome: "Barba Completa", valor: 25, duracao_minutos: 20},
                {id: 3, nome: "Corte + Barba", valor: 50, duracao_minutos: 45}
            ]);
        }
    };

    const voltarParaBarbeiros = () => {
        setStep('barbeiros');
        setSelectedBarber(null);
        setBarbearias([]);
        setSelectedBarbearia(null);
        setServices([]);
        setSelectedServices([]);
        setDataHoraInicio('');
    };

    const voltarParaBarbearias = () => {
        setStep('barbearias');
        setSelectedBarbearia(null);
        setServices([]);
        setSelectedServices([]);
        setDataHoraInicio('');
    };

    const toggleServiceSelection = (service) => {
        setSelectedServices((prev) => {
            const exists = prev.find((s) => s.id === service.id);
            if (exists) {
                return prev.filter((s) => s.id !== service.id);
            }
            return [...prev, service];
        });
    };

    const totalSelecionado = selectedServices.reduce((acc, s) => acc + (Number(s.valor) || 0), 0);
    const duracaoSelecionada = selectedServices.reduce((acc, s) => acc + (Number(s.duracao_minutos) || 0), 0);

    // 🚀 MODELO UBER: Detectar se barbeiro está PRESENTE
    // Usa dados do perfil (mais confiáveis) com fallback para os dados da lista.
    const barbeiroPresenteEmLocal =
        (barbeiroInfo?.presente_em_local ?? selectedBarber?.presente_em_local) === true;
    const barbeariaAtualIdBarbeiro =
        barbeiroInfo?.barbearia_atual_id ?? selectedBarber?.barbearia_atual_id;
    const barbeariaSelecionadaId = selectedBarbearia?.id;
    const mesmaBarbearia =
        barbeariaAtualIdBarbeiro != null &&
        barbeariaSelecionadaId != null &&
        Number(barbeariaAtualIdBarbeiro) === Number(barbeariaSelecionadaId);

    // Se está presente no local e a barbearia bate, o chamado é imediato.
    // Fallback: se veio presente mas sem id consistente, mantém imediato para não bloquear o fluxo.
    const imediatoPorPresenca = barbeiroPresenteEmLocal && (mesmaBarbearia || barbeariaAtualIdBarbeiro == null);

    // Fluxo operacional atual: ao escolher barbeiro + barbearia e ele estar disponível,
    // tratamos como chamado em tempo real para não exigir data/hora.
    const imediatoPorDisponibilidade = selectedBarber?.disponivel === true && barbeariaSelecionadaId != null;

    const ehAgendamentoAgora = imediatoPorPresenca || imediatoPorDisponibilidade;
    const mensagemAgendamento = ehAgendamentoAgora ? "Agendar AGORA" : "Agendar";
    const horarioAgendamento = ehAgendamentoAgora 
        ? new Date().toISOString() 
        : (dataHoraInicio ? new Date(dataHoraInicio).toISOString() : null);

    const handleBooking = async (service) => {
        // ✅ Se barbeiro está PRESENTE, não precisa validar data/hora (é AGORA)
        if (!ehAgendamentoAgora && !dataHoraInicio) {
            notify('Selecione data e horario para agendar', 'error');
            return;
        }

        if(!confirm(`${mensagemAgendamento} ${service.nome} com ${selectedBarber.nome}${ehAgendamentoAgora ? ' AGORA na barbearia!' : ''}? R$${service.valor}`)) return;
        
        try {
            const res = await fetch(`${API_URL}/api/v1/chamados`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
                body: JSON.stringify({ 
                    barbeiro_id: selectedBarber.id,
                    barbeiro_selecionado_id: selectedBarber.id,
                    servico_id: service.id,
                    barbearia_id: selectedBarbearia.id,
                    data_hora_inicio: horarioAgendamento,
                    imediato: ehAgendamentoAgora
                })
            });

            if (!res.ok) {
                const errData = await res.json().catch(() => ({}));
                throw new Error(errData.detail || 'Não foi possível criar o chamado');
            }

            notify(ehAgendamentoAgora ? `🚀 Chamado enviado! ${selectedBarber.nome} vai receber em tempo real!` : `Agendado com ${selectedBarber.nome}!`, "success");
            voltarParaBarbeiros();
            setTab('agenda');
            carregarMeusPedidos();
        } catch (err) {
            notify(err.message || "Erro ao agendar. Tente novamente.", "error");
        }
    };

    const handleBookingMultiple = async () => {
        // ✅ Se barbeiro está PRESENTE, não precisa validar data/hora (é AGORA)
        if (!ehAgendamentoAgora && !dataHoraInicio) {
            notify('Selecione data e horario para agendar', 'error');
            return;
        }

        if (selectedServices.length === 0) {
            notify('Selecione pelo menos um serviço', 'error');
            return;
        }

        const nomes = selectedServices.map((s) => s.nome).join(', ');
        if (!confirm(`${mensagemAgendamento} ${nomes} com ${selectedBarber.nome}${ehAgendamentoAgora ? ' AGORA!' : ''}? R$${totalSelecionado}`)) {
            return;
        }

        try {
            const baseTime = ehAgendamentoAgora 
                ? new Date() 
                : new Date(dataHoraInicio);
                
            if (Number.isNaN(baseTime.getTime())) {
                notify('Data e horario invalidos', 'error');
                return;
            }

            let offsetMin = 0;
            for (const service of selectedServices) {
                const startTime = new Date(baseTime.getTime() + offsetMin * 60000);
                const duracao = Number(service.duracao_minutos) || 0;
                offsetMin += duracao;
                const res = await fetch(`${API_URL}/api/v1/chamados`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
                    body: JSON.stringify({
                        barbeiro_id: selectedBarber.id,
                        barbeiro_selecionado_id: selectedBarber.id,
                        servico_id: service.id,
                        barbearia_id: selectedBarbearia.id,
                        data_hora_inicio: startTime.toISOString(),
                        imediato: ehAgendamentoAgora
                    })
                });

                if (!res.ok) {
                    const errData = await res.json().catch(() => ({}));
                    throw new Error(errData.detail || `Falha ao criar chamado para ${service.nome}`);
                }
            }
            notify(ehAgendamentoAgora ? `🚀 Chamados enviados! ${selectedBarber.nome} vai receber em tempo real!` : `Agendado com ${selectedBarber.nome}!`, "success");
            voltarParaBarbeiros();
            setTab('agenda');
            carregarMeusPedidos();
        } catch (err) {
            notify(err.message || "Erro ao agendar. Tente novamente.", "error");
        }
    };

    return (
    <div className="bg-black h-full w-full max-w-full overflow-hidden flex flex-col text-white font-sans">
        {/* HEADER */}
        <div className="p-2 sm:p-4 flex justify-between items-center border-b border-zinc-800 bg-black/80 backdrop-blur-md z-20 flex-shrink-0">
            <h1 className="text-base sm:text-xl font-bold">Buscar Barbeiros</h1>
            <button onClick={logout} className="text-zinc-500 hover:text-white"><LogOut size={18}/></button>
        </div>

        {/* CONTEÚDO - SÓ UMA ABA */}
        <div className="flex-1 overflow-y-auto pb-16">
            {/* ABA: BUSCAR */}
            {tab === 'buscar' && (
                <div className="p-2 sm:p-4 space-y-3">
                    {step === 'barbeiros' && (
                        <>
                            <div className="sticky top-0 bg-black/90 z-10 pb-3">
                                <div className="relative mb-3">
                                    <Search className="absolute left-3 top-3 text-zinc-500" size={16} />
                                    <input placeholder="Buscar barbeiro..." className="w-full bg-zinc-900 pl-10 pr-4 py-2 rounded-lg border border-zinc-800 outline-none focus:border-orange-500 text-xs" />
                                </div>
                                <button 
                                    onClick={requestUserLocation}
                                    className="w-full bg-orange-600 text-white py-2 rounded-lg font-bold text-xs hover:bg-orange-700 transition-all"
                                >
                                    {loadingLocation ? 'Buscando...' : userLocation ? 'Atualizar Localização' : 'Buscar Próximos'}
                                </button>
                            </div>
                            <div className="space-y-2">
                                {shops && shops.length > 0 ? shops.map(barber => {
                                    // Determinar status do freelancer
                                    const statusInfo = barber.presente_em_local && barber.barbearia_atual_id ? {
                                        texto: barber.barbearia_atual_nome ? `DISPONÍVEL em ${barber.barbearia_atual_nome}` : 'PRESENTE',
                                        cor: 'bg-green-600',
                                        icone: '🏢'
                                    } : (barber.disponivel || barber.online_regiao) ? {
                                        texto: 'DISPONÍVEL',
                                        cor: 'bg-green-600',
                                        icone: '🌍'
                                    } : !barber.disponivel ? {
                                        texto: 'INDISPONÍVEL',
                                        cor: 'bg-red-600',
                                        icone: '⭕'
                                    } : {
                                        texto: 'OFFLINE',
                                        cor: 'bg-gray-600',
                                        icone: '⚫'
                                    };

                                    return (
                                    <div key={barber.id} className="bg-zinc-900 rounded-xl overflow-hidden border border-zinc-800 hover:border-orange-500 transition-colors">
                                        <div className="h-24 w-full relative bg-gradient-to-r from-zinc-800 to-zinc-900">
                                            <img src={getShopImage(barber.id)} className="w-full h-full object-cover opacity-50" alt={barber.nome} />
                                            <div className="absolute inset-0 flex items-end p-2">
                                                <div>
                                                    <p className="font-bold text-sm">{barber.nome}</p>
                                                    <p className="text-xs text-zinc-400">{barber.endereco}</p>
                                                </div>
                                            </div>
                                            {/* Indicador de Status */}
                                            <div className={`absolute top-2 left-2 ${statusInfo.cor} px-2 py-1 rounded text-xs font-bold flex items-center gap-1`}>
                                                <span>{statusInfo.icone}</span>
                                                <span>{statusInfo.texto}</span>
                                            </div>
                                            <div className="absolute top-2 right-2 bg-orange-600 px-2 py-1 rounded text-xs font-bold flex gap-1">
                                                <Star size={10} className="fill-white"/> {barber.avaliacao || 5.0}
                                            </div>
                                        </div>
                                        <div className="p-2 flex gap-2">
                                            <button
                                                onClick={() => handleSelectShop(barber)}
                                                disabled={statusInfo.texto === 'INDISPONÍVEL' || statusInfo.texto === 'OFFLINE'}
                                                className={`flex-1 ${(statusInfo.texto === 'INDISPONÍVEL' || statusInfo.texto === 'OFFLINE') ? 'bg-zinc-700 cursor-not-allowed' : 'bg-orange-600 hover:bg-orange-700'} text-white py-2 rounded-lg text-xs font-bold`}
                                            >
                                                {(statusInfo.texto === 'INDISPONÍVEL' || statusInfo.texto === 'OFFLINE') ? 'Indisponível' : 'Escolher'}
                                            </button>
                                            <button
                                                onClick={() => setPerfilModal({ id: barber.id, tipo: 'barbeiro' })}
                                                className="flex-1 bg-zinc-800 hover:bg-zinc-700 text-white py-2 rounded-lg text-xs font-bold"
                                            >
                                                Ver perfil
                                            </button>
                                        </div>
                                        {/* 📍 DISTÂNCIA E TEMPO like Uber */}
                                        {barber.distancia_km !== undefined && (
                                            <div className="px-2 pb-2 flex items-center justify-between text-xs text-zinc-400 border-t border-zinc-800 pt-2">
                                                <div className="flex items-center gap-1">
                                                    <MapPin size={12} />
                                                    <span>{barber.distancia_km} km</span>
                                                </div>
                                                {barber.tempo_estimado_minutos !== undefined && (
                                                    <div className="text-orange-400 font-bold">
                                                        ⏱ {barber.tempo_estimado_minutos} min
                                                    </div>
                                                )}
                                            </div>
                                        )}
                                    </div>
                                );
                                }) : (
                                    <p className="text-zinc-600 text-center py-10 text-xs">Nenhum barbeiro encontrado</p>
                                )}
                            </div>
                        </>
                    )}

                    {step === 'barbearias' && (
                        <>
                            <button onClick={voltarParaBarbeiros} className="text-xs text-zinc-400 hover:text-white flex items-center gap-1">
                                <ArrowRight size={12} className="rotate-180" /> Voltar para barbeiros
                            </button>
                            <h2 className="text-sm font-bold text-zinc-300">Escolha uma barbearia para {selectedBarber?.nome}</h2>
                            <div className="space-y-2">
                                {barbearias && barbearias.length > 0 ? barbearias.map(barbearia => (
                                    <div key={barbearia.id} className="bg-zinc-900 rounded-xl p-3 border border-zinc-800 hover:border-orange-500 transition-colors">
                                        <p className="font-bold text-sm">{barbearia.nome}</p>
                                        <p className="text-xs text-zinc-400">{barbearia.endereco || 'Endereco nao informado'}</p>
                                        {/* 📍 DISTÂNCIA E TEMPO like Uber */}
                                        {barbearia.distancia_km !== undefined && (
                                            <div className="mt-2 mb-2 flex items-center justify-between text-xs text-zinc-400">
                                                <div className="flex items-center gap-1">
                                                    <MapPin size={12} />
                                                    <span>{barbearia.distancia_km} km</span>
                                                </div>
                                                {barbearia.tempo_estimado_minutos !== undefined && (
                                                    <div className="text-orange-400 font-bold">
                                                        ⏱ {barbearia.tempo_estimado_minutos} min
                                                    </div>
                                                )}
                                            </div>
                                        )}
                                        <div className="mt-2 flex gap-2">
                                            <button
                                                onClick={() => handleSelectBarbearia(barbearia)}
                                                className="flex-1 bg-orange-600 hover:bg-orange-700 text-white py-2 rounded-lg text-xs font-bold"
                                            >
                                                Escolher
                                            </button>
                                            <button
                                                onClick={() => setPerfilModal({ id: barbearia.usuario_id || barbearia.id, tipo: 'barbearia' })}
                                                className="flex-1 bg-zinc-800 hover:bg-zinc-700 text-white py-2 rounded-lg text-xs font-bold"
                                            >
                                                Ver perfil
                                            </button>
                                        </div>
                                    </div>
                                )) : (
                                    <p className="text-zinc-600 text-center py-10 text-xs">Nenhuma barbearia encontrada</p>
                                )}
                            </div>
                        </>
                    )}

                    {step === 'servicos' && (
                        <>
                            <button onClick={voltarParaBarbearias} className="text-xs text-zinc-400 hover:text-white flex items-center gap-1">
                                <ArrowRight size={12} className="rotate-180" /> Voltar para barbearias
                            </button>
                            <h2 className="text-sm font-bold text-zinc-300">Escolha um ou mais servicos em {selectedBarbearia?.nome}</h2>
                            <div className="bg-zinc-900 border border-zinc-800 rounded-lg p-3 flex items-center justify-between">
                                <div>
                                    <p className="text-xs text-zinc-400">Barbeiro</p>
                                    <p className="text-sm font-bold text-white">{selectedBarber?.nome || 'Barbeiro'}</p>
                                </div>
                                <button
                                    onClick={() => setPerfilModal({ id: selectedBarber?.id, tipo: 'barbeiro' })}
                                    className="bg-zinc-800 hover:bg-zinc-700 text-white px-3 py-2 rounded-lg text-xs font-bold"
                                >
                                    Ver perfil
                                </button>
                            </div>

                            {/* 🚀 MODO UBER: Mostrar quando barbeiro está PRESENTE */}
                            {ehAgendamentoAgora && (
                                <div className="bg-green-900/30 border-2 border-green-500 rounded-lg p-3 text-center">
                                    <p className="text-green-400 font-bold text-sm">🚀 AGENDAMENTO EM TEMPO REAL</p>
                                    <p className="text-xs text-green-300 mt-1">{selectedBarber?.nome} está PRESENTE na barbearia!</p>
                                    <p className="text-xs text-green-300">Vai receber seu chamado AGORA</p>
                                </div>
                            )}

                            {/* 📅 MODO TRADICIONAL: Mostrar apenas para agendamentos futuros */}
                            {!ehAgendamentoAgora && (
                                <div className="bg-zinc-900 border border-zinc-800 rounded-lg p-3">
                                    <label className="text-xs text-zinc-400 block mb-2">Data e horario (Futuro)</label>
                                    <input
                                        type="datetime-local"
                                        value={dataHoraInicio}
                                        onChange={(e) => setDataHoraInicio(e.target.value)}
                                        className="w-full bg-black/40 text-white text-xs p-2 rounded border border-zinc-700 focus:border-orange-500 outline-none"
                                    />
                                </div>
                            )}
                            
                            <div className="space-y-2">
                                {services && services.length > 0 ? services.map(service => (
                                    <div key={service.id} className={`bg-zinc-900 rounded-xl p-3 border ${selectedServices.find(s => s.id === service.id) ? 'border-orange-500' : 'border-zinc-800'}`}>
                                        <div className="flex justify-between items-start">
                                            <div>
                                                <p className="font-bold text-sm">{service.nome}</p>
                                                <p className="text-xs text-zinc-400">{service.duracao_minutos || 30} min</p>
                                            </div>
                                            <p className="text-sm font-bold text-green-400">R$ {service.valor}</p>
                                        </div>
                                        <div className="flex gap-2 mt-3">
                                            <button
                                                onClick={() => toggleServiceSelection(service)}
                                                className={`flex-1 ${selectedServices.find(s => s.id === service.id) ? 'bg-zinc-700' : 'bg-orange-600 hover:bg-orange-700'} text-white py-2 rounded-lg font-bold text-xs`}
                                            >
                                                {selectedServices.find(s => s.id === service.id) ? 'Selecionado' : 'Selecionar'}
                                            </button>
                                            <button
                                                onClick={() => handleBooking(service)}
                                                className={`flex-1 ${ehAgendamentoAgora ? 'bg-green-600 hover:bg-green-700' : 'bg-blue-600 hover:bg-blue-700'} text-white py-2 rounded-lg font-bold text-xs`}
                                            >
                                                {ehAgendamentoAgora ? '🚀 Chamar AGORA' : 'Agendar'}
                                            </button>
                                        </div>
                                    </div>
                                )) : (
                                    <p className="text-zinc-600 text-center py-10 text-xs">Nenhum servico encontrado</p>
                                )}
                            </div>
                            {selectedServices.length > 0 && (
                                <div className="bg-zinc-900 border border-zinc-800 rounded-lg p-3 mt-2">
                                    <div className="flex justify-between text-xs text-zinc-400">
                                        <span>{selectedServices.length} servico(s)</span>
                                        <span>{duracaoSelecionada || 0} min</span>
                                    </div>
                                    <div className="flex justify-between items-center mt-2">
                                        <span className="text-sm font-bold text-white">Total</span>
                                        <span className="text-sm font-bold text-green-400">R$ {totalSelecionado}</span>
                                    </div>
                                    <button
                                        onClick={handleBookingMultiple}
                                        className={`mt-3 w-full ${ehAgendamentoAgora ? 'bg-green-600 hover:bg-green-700' : 'bg-orange-600 hover:bg-orange-700'} text-white py-2 rounded-lg font-bold text-xs`}
                                    >
                                        {ehAgendamentoAgora ? '🚀 Agendar AGORA' : 'Agendar selecionados'}
                                    </button>
                                </div>
                            )}
                        </>
                    )}
                </div>
            )}

            {/* ABA: AGENDA */}
            {tab === 'agenda' && (
                <div className="p-2 sm:p-4">
                    <h2 className="text-sm font-bold text-zinc-400 uppercase mb-4">Meus Agendamentos</h2>
                    {!Array.isArray(myOrders) || myOrders.length === 0 ? (
                        <p className="text-zinc-600 text-center py-12 text-xs">Nenhum agendamento</p>
                    ) : (
                        <div className="space-y-2">
                            {myOrders.map(order => (
                                <div key={order.id} className="bg-zinc-900 p-2 rounded-lg border border-zinc-800 text-xs">
                                    <p className="font-bold">{order.barbeiro_nome || 'Barbeiro'}</p>
                                    <p className="text-zinc-400">{order.servico_nome || order.descricao || 'Servico'}</p>
                                    <p className="text-zinc-500">{order.nome_barbearia || 'Barbearia'}</p>
                                    {order.data_hora_inicio && (
                                        <p className="text-zinc-500">{new Date(order.data_hora_inicio).toLocaleString('pt-BR')}</p>
                                    )}
                                    <p className="text-zinc-500">Status: {order.status}</p>
                                </div>
                            ))}
                        </div>
                    )}
                </div>
            )}

            {/* ABA: AVALIAR */}
            {tab === 'avaliar' && (
                <div className="p-2 sm:p-4 pb-20">
                    {userData ? (
                        <AbaPadronizadaAvaliacoes
                            usuarioId={userData?.id}
                            tipoUsuario="cliente"
                            nomeUsuario={userData?.nome}
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

            {/* ABA: PERFIL */}
            {tab === 'perfil' && (
                <TelaPerfilUsuario userType="cliente" token={token} onLogout={logout} onNotify={notify} />
            )}

            {/* ABA: PAGAMENTO */}
            {/* ABA: PAGAMENTO */}
            {tab === 'pagamento' && !chamadoParaPagar && (
                <div className="p-2 sm:p-4 pb-20">
                    <h2 className="text-base font-bold text-white mb-3">Pagamentos pendentes</h2>
                    {(() => {
                        const pendentes = (myOrders || []).filter(o =>
                            o.status === 'pendente' || o.status === 'confirmado'
                        );
                        if (pendentes.length === 0) {
                            return (
                                <div className="text-center py-14 space-y-2">
                                    <CheckCircle size={40} className="mx-auto text-zinc-700" />
                                    <p className="text-zinc-500 text-sm">Sem pagamentos pendentes</p>
                                    <p className="text-zinc-600 text-xs">Agende um serviço para pagar aqui</p>
                                </div>
                            );
                        }
                        return (
                            <div className="space-y-3">
                                {pendentes.map(order => (
                                    <div key={order.id} className="bg-zinc-900 rounded-xl border border-zinc-800 p-3 space-y-2">
                                        <div className="flex justify-between items-start">
                                            <div>
                                                <p className="font-bold text-white text-sm">{order.servico_nome || order.descricao || 'Serviço'}</p>
                                                <p className="text-zinc-400 text-xs">{order.barbeiro_nome || 'Barbeiro'} · {order.nome_barbearia || 'Barbearia'}</p>
                                            </div>
                                            <span className="text-green-400 font-bold text-sm">R$ {Number(order.valor || 0).toFixed(2)}</span>
                                        </div>
                                        <div className="flex gap-2 pt-1">
                                            <button
                                                onClick={() => setChamadoParaPagar({ id: order.id, valor: Number(order.valor || 0), descricao: order.servico_nome || order.descricao || 'Serviço' })}
                                                className="flex-1 bg-gradient-to-r from-orange-600 to-orange-500 hover:from-orange-700 hover:to-orange-600 text-white py-2 rounded-lg text-xs font-bold flex items-center justify-center gap-1 active:scale-95 transition-all"
                                            >
                                                <DollarSign size={13} /> Pagar agora
                                            </button>
                                        </div>
                                    </div>
                                ))}
                            </div>
                        );
                    })()}
                </div>
            )}

            {/* TELA DE PAGAMENTO (modal overlay) */}
            {tab === 'pagamento' && chamadoParaPagar && (
                <div className="p-2 sm:p-4 pb-20">
                    <button
                        onClick={() => setChamadoParaPagar(null)}
                        className="flex items-center gap-1 text-zinc-400 hover:text-white text-xs mb-3"
                    >
                        <X size={14} /> Voltar
                    </button>
                    <TelaPagamento
                        chamadoId={chamadoParaPagar.id}
                        valor={chamadoParaPagar.valor}
                        onPago={() => {
                            notify('Pagamento confirmado!', 'success');
                            setChamadoParaPagar(null);
                            carregarMeusPedidos();
                        }}
                    />
                </div>
            )}
        </div>

        {/* NAVBAR */}
        <div className="fixed bottom-0 left-1/2 -translate-x-1/2 w-full max-w-[400px] h-16 bg-zinc-950/98 backdrop-blur-lg border-t border-zinc-800 flex justify-around items-center z-50">
            <button onClick={() => setTab('buscar')} className={`flex flex-col items-center justify-center gap-0.5 h-full flex-1 text-center transition-colors ${tab === 'buscar' ? 'text-orange-500 bg-orange-500/5' : 'text-zinc-500 hover:text-zinc-400'}`}><Search size={14} /><span className="text-[7px] font-bold">Buscar</span></button>
            <button onClick={() => setTab('agenda')} className={`flex flex-col items-center justify-center gap-0.5 h-full flex-1 text-center transition-colors ${tab === 'agenda' ? 'text-orange-500 bg-orange-500/5' : 'text-zinc-500 hover:text-zinc-400'}`}><Calendar size={14} /><span className="text-[7px] font-bold">Agenda</span></button>
            <button onClick={() => setTab('avaliar')} className={`flex flex-col items-center justify-center gap-0.5 h-full flex-1 text-center transition-colors ${tab === 'avaliar' ? 'text-orange-500 bg-orange-500/5' : 'text-zinc-500 hover:text-zinc-400'}`}><Star size={14} /><span className="text-[7px] font-bold">Avaliar</span></button>
            <button onClick={() => setTab('perfil')} className={`flex flex-col items-center justify-center gap-0.5 h-full flex-1 text-center transition-colors ${tab === 'perfil' ? 'text-orange-500 bg-orange-500/5' : 'text-zinc-500 hover:text-zinc-400'}`}><User size={14} /><span className="text-[7px] font-bold">Perfil</span></button>
            <button onClick={() => setTab('pagamento')} className={`flex flex-col items-center justify-center gap-0.5 h-full flex-1 text-center transition-colors ${tab === 'pagamento' ? 'text-orange-500 bg-orange-500/5' : 'text-zinc-500 hover:text-zinc-400'}`}><CreditCard size={14} /><span className="text-[7px] font-bold">Pagar</span></button>
        </div>

        {perfilModal && (
            <div className="fixed inset-0 bg-black/70 z-[90] flex items-center justify-center p-4">
                <div className="bg-zinc-950 border border-zinc-800 rounded-2xl w-full max-w-[420px] max-h-[90vh] overflow-y-auto p-4">
                    <div className="flex justify-between items-center mb-3">
                        <h3 className="text-sm font-bold text-white">Perfil</h3>
                        <button onClick={() => setPerfilModal(null)} className="text-zinc-400">✕</button>
                    </div>
                    <ProfileCard
                        usuarioId={perfilModal.id}
                        userType={perfilModal.tipo}
                        token={token}
                    />
                </div>
            </div>
        )}
      </div>
    );
}