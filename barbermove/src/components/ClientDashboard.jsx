import React, { useState, useEffect, useCallback, useRef } from 'react';
import { LogOut, Search, MapPin, Star, Calendar, ArrowRight, CheckCircle, User, CreditCard, MessageSquare, DollarSign, QrCode, X } from 'lucide-react';
import TelaPagamento from './TelaPagamento';
import TelaPerfilUsuario from './TelaPerfilUsuario';
import MapEmbed from './MapEmbed';
import AbaPadronizadaAvaliacoes from './AbaPadronizadaAvaliacoes';
import ProfileCard from './ProfileCard';
import ChatRoom from './ChatRoom';
import TrackingPanel from './TrackingPanel';
import TelaRotasAtivos from './TelaRotasAtivos';
import { obterLocalizacaoAtual, obterPosicaoAltaPrecisa } from '../utils/location';
import { getApiBaseUrl } from '../utils/api';

const API_URL = getApiBaseUrl();
const getShopImage = (id) => `https://images.unsplash.com/photo-${id % 2 === 0 ? '1521590832874-552721032d00' : '1503951914290-d20607416905'}?auto=format&fit=crop&w=800&q=80`;
const BARBEIROS_CACHE_KEY = 'barbermove.client.barbeiros_cache';
const GPS_PREFERENCE_KEY = 'barbermove.client.gps_preference';
const DEV_GPS_OVERRIDE = String(import.meta.env.VITE_DEV_MODE || '').toLowerCase() === 'true';

const normalizarListaBarbeiros = (data) => {
    if (Array.isArray(data)) return data;
    if (Array.isArray(data?.barbeiros)) return data.barbeiros;
    if (Array.isArray(data?.freelancers)) return data.freelancers;
    return [];
};

const ordenarBarbeirosParaExibicao = (lista) => {
    if (!Array.isArray(lista)) return [];

    return [...lista].sort((a, b) => {
        const aTeste = /teste/i.test(a?.nome || '') ? 1 : 0;
        const bTeste = /teste/i.test(b?.nome || '') ? 1 : 0;

        if (aTeste !== bTeste) {
            return bTeste - aTeste;
        }

        return String(a?.nome || '').localeCompare(String(b?.nome || ''), 'pt-BR', { sensitivity: 'base' });
    });
};

const lerBarbeirosCache = () => {
    if (typeof window === 'undefined') return [];
    try {
        const raw = window.localStorage.getItem(BARBEIROS_CACHE_KEY);
        if (!raw) return [];
        const parsed = JSON.parse(raw);
        return normalizarListaBarbeiros(parsed);
    } catch (_err) {
        return [];
    }
};

const salvarBarbeirosCache = (data) => {
    if (typeof window === 'undefined') return;
    try {
        const lista = ordenarBarbeirosParaExibicao(normalizarListaBarbeiros(data));
        window.localStorage.setItem(BARBEIROS_CACHE_KEY, JSON.stringify(lista));
    } catch (_err) {
        // Cache é apenas um fallback de UX.
    }
};

const lerPreferenciaGps = () => {
    if (typeof window === 'undefined') return 'ask';
    try {
        return window.localStorage.getItem(GPS_PREFERENCE_KEY)
            || window.sessionStorage.getItem(GPS_PREFERENCE_KEY)
            || 'ask';
    } catch (_err) {
        return 'ask';
    }
};

const salvarPreferenciaGps = (preferencia) => {
    if (typeof window === 'undefined') return;
    try {
        window.localStorage.removeItem(GPS_PREFERENCE_KEY);
        window.sessionStorage.removeItem(GPS_PREFERENCE_KEY);

        if (preferencia === 'always') {
            window.localStorage.setItem(GPS_PREFERENCE_KEY, 'always');
        } else if (preferencia === 'session') {
            window.sessionStorage.setItem(GPS_PREFERENCE_KEY, 'session');
        }
    } catch (_err) {
        // Preferência é apenas UX.
    }
};

const normalizarNumero = (valor) => {
    const numero = Number(valor);
    return Number.isFinite(numero) ? numero : null;
};

const calcularDistanciaKm = (lat1, lon1, lat2, lon2) => {
    const latitude1 = normalizarNumero(lat1);
    const longitude1 = normalizarNumero(lon1);
    const latitude2 = normalizarNumero(lat2);
    const longitude2 = normalizarNumero(lon2);

    if (latitude1 == null || longitude1 == null || latitude2 == null || longitude2 == null) {
        return null;
    }

    const toRad = (valor) => (valor * Math.PI) / 180;
    const R = 6371;
    const dLat = toRad(latitude2 - latitude1);
    const dLon = toRad(longitude2 - longitude1);
    const a =
        Math.sin(dLat / 2) ** 2 +
        Math.cos(toRad(latitude1)) * Math.cos(toRad(latitude2)) *
        Math.sin(dLon / 2) ** 2;
    return 2 * R * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
};

const estimarTempoMinutos = (distanciaKm) => {
    const distancia = normalizarNumero(distanciaKm);
    if (distancia == null) return null;
    return Math.max(1, Math.round((distancia / 40) * 60));
};

export default function ClientDashboard({ token, logout, API_URL, notify, onChamadoAceito }) {
    const NGROK_TEST_OVERRIDE = typeof window !== 'undefined' && String(window.location.hostname || '').includes('ngrok-free.dev');
    const TEST_GPS_OVERRIDE_ATIVO = DEV_GPS_OVERRIDE || NGROK_TEST_OVERRIDE;
    const TABS_VALIDAS = ['buscar', 'agenda', 'avaliar', 'perfil', 'pagamento'];
    const [shops, setShops] = useState([]); // Agora são BARBEIROS
    const [tab, setTab] = useState(() => {
        if (typeof window === 'undefined') return 'buscar';
        const tabSalva = localStorage.getItem('cliente_dashboard_tab') || 'buscar';
        return TABS_VALIDAS.includes(tabSalva) ? tabSalva : 'buscar';
    }); // 'buscar' | 'agenda' | 'avaliar' | 'perfil' | 'pagamento' 
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
    const [step, setStep] = useState('inicio'); // 'inicio' -> 'barbearias' -> 'barbeiros' -> 'servicos'
    const [activeChamado, setActiveChamado] = useState(null); // chamado retornado após booking
    const [userData, setUserData] = useState(null); // Dados do usuário logado
    const [dataHoraInicio, setDataHoraInicio] = useState('');
    const [perfilModal, setPerfilModal] = useState(null);
    const [cancelModalOpen, setCancelModalOpen] = useState(false);
    const [cancelandoChamado, setCancelandoChamado] = useState(false);
    const [tempoDecorrido, setTempoDecorrido] = useState(0); // Tempo em segundos desde horario_match
    const [gpsConsentOpen, setGpsConsentOpen] = useState(false);
    const [gpsPreference, setGpsPreference] = useState('always');

    const isConcluido = (status = '') => (status || '').toString().toLowerCase().includes('conclu');

    const getCancelamentoInfo = (chamado) => {
        if (!chamado) return { taxa: 0, motivo: '', minutos: 0, segundos: 0, tempoRestante: '5:00', texto: '' };

        const janelaGratuitaMinutos = 5;
        const taxaPadrao = 8;
        const status = (chamado.status || '').toLowerCase();

        // Se está em estado PENDENTE, cancelamento é grátis
        if (status === 'pendente') {
            return {
                taxa: 0,
                motivo: 'Cancelamento antes da confirmação do barbeiro',
                minutos: 0,
                segundos: 0,
                tempoRestante: '∞',
                texto: 'Você pode cancelar gratuitamente enquanto o barbeiro ainda não confirmou.'
            };
        }

        // Se freelancer está presente na barbearia, taxa é sempre 8.00
        const barbeiroPresente = Boolean(chamado.barbeiro_presente_em_local && chamado.barbeiro_barbearia_atual_id && Number(chamado.barbeiro_barbearia_atual_id) === Number(chamado.barbearia_id));
        if (barbeiroPresente) {
            return {
                taxa: taxaPadrao,
                motivo: 'Freelancer presente na barbearia',
                minutos: 0,
                segundos: 0,
                tempoRestante: 'Taxa aplicada',
                texto: 'Como o freelancer já está presente na barbearia, o cancelamento tem taxa de R$ 8,00.'
            };
        }

        // ✅ Usar horario_match para calcular tempo (quando o freelancer aceitou)
        const baseIso = chamado.horario_match || chamado.aprovado_barbeiro_em || chamado.data_agendamento || chamado.criado_em;
        const baseDate = baseIso ? new Date(baseIso) : null;
        const agora = new Date();
        const segundosDecorridos = baseDate && !Number.isNaN(baseDate.getTime())
            ? Math.max(0, Math.floor((agora.getTime() - baseDate.getTime()) / 1000))
            : 0;
        
        const minutosDecorridos = Math.floor(segundosDecorridos / 60);
        const segundosResto = segundosDecorridos % 60;
        const jaPassouDaJanela = minutosDecorridos > janelaGratuitaMinutos;
        const taxa = jaPassouDaJanela ? taxaPadrao : 0;

        // Calcular tempo restante para entrar na taxa
        const tempoRestanteSegundos = Math.max(0, (janelaGratuitaMinutos * 60) - segundosDecorridos);
        const minRestante = Math.floor(tempoRestanteSegundos / 60);
        const segRestante = tempoRestanteSegundos % 60;
        const tempoRestante = jaPassouDaJanela ? '0:00' : `${minRestante}:${String(segRestante).padStart(2, '0')}`;

        return {
            taxa,
            motivo: taxa > 0
                ? 'Cancelamento fora da janela gratuita de 5 minutos'
                : 'Cancelamento dentro da janela gratuita de 5 minutos',
            minutos: minutosDecorridos,
            segundos: segundosResto,
            tempoRestante,
            texto: taxa > 0
                ? `Você já passou da janela gratuita de ${janelaGratuitaMinutos} minutos. O cancelamento terá taxa de R$ ${taxaPadrao},00.`
                : `Você ainda está dentro da janela gratuita de ${janelaGratuitaMinutos} minutos para cancelar. Tempo restante: ${tempoRestante}`
        };
    };

    const getCancelamentoBotaoTexto = (chamado) => {
        const info = getCancelamentoInfo(chamado);
        return info.taxa > 0 ? `Cancelar com taxa de R$ ${info.taxa.toFixed(2)}` : 'Cancelar grátis';
    };

    const isChamadoVisivel = (chamado) => {
        if (!chamado) return false;
        const status = (chamado.status || '').toLowerCase();
        return !['cancelado', 'concluido', 'concluído'].includes(status);
    };

    const abrirConfirmacaoCancelamento = () => {
        if (!activeChamado) return;
        setCancelModalOpen(true);
    };

    const confirmarCancelamento = async () => {
        if (!activeChamado || cancelandoChamado) return;

        setCancelandoChamado(true);
        try {
            const res = await fetch(`${API_URL}/api/v1/chamados/${activeChamado.id}/cancelar`, {
                method: 'PUT',
                headers: {
                    'Content-Type': 'application/json',
                    Authorization: `Bearer ${token}`
                }
            });

            const data = await res.json().catch(() => ({}));
            if (!res.ok) {
                throw new Error(data.detail || 'Não foi possível cancelar o chamado');
            }

            notify(
                data.valor_taxa_cancelamento > 0
                    ? `Chamado cancelado. Taxa de R$ ${Number(data.valor_taxa_cancelamento).toFixed(2)} aplicada.`
                    : 'Chamado cancelado sem taxa.',
                data.valor_taxa_cancelamento > 0 ? 'warning' : 'success'
            );
            setCancelModalOpen(false);
            setActiveChamado(null);
            carregarMeusPedidos();
        } catch (err) {
            notify(err.message || 'Falha ao cancelar o chamado', 'error');
        } finally {
            setCancelandoChamado(false);
        }
    };

    const loadDefaultShops = useCallback(async ({ mostrarErro = false } = {}) => {
        // Carrega todos os barbeiros sem filtro de localização.
        try {
            const res = await fetch(`${API_URL}/api/v1/barbeiros/todos`);
            const rawText = await res.text();

            if (!res.ok) {
                throw new Error(`HTTP ${res.status}: ${rawText.slice(0, 120)}`);
            }

            const data = rawText ? JSON.parse(rawText) : [];
            const lista = ordenarBarbeirosParaExibicao(normalizarListaBarbeiros(data));
            setShops(lista);
            salvarBarbeirosCache(lista);

            if (lista.length === 0 && mostrarErro) {
                notify('Nenhum barbeiro encontrado no servidor', 'info');
            }
        } catch (err) {
            const cache = lerBarbeirosCache();
            if (cache.length > 0) {
                setShops(cache);
                notify('Mostrando barbeiros salvos em cache', 'warning');
                return;
            }

            setShops([]);
            if (mostrarErro) {
                notify(`Erro ao carregar barbeiros: ${err?.message || 'falha de conexão'}`, 'error');
            }
        }
    }, [API_URL, notify]);
        // Versão com filtro de localização
        const loadShopsByLocation = useCallback(async (latitude, longitude, { mostrarErro = false } = {}) => {
            try {
                const raio_km = 15; // Raio padrão de busca
                const res = await fetch(`${API_URL}/api/v1/freelancer/proximos?latitude=${latitude}&longitude=${longitude}&raio_km=${raio_km}`);
            
                if (!res.ok) {
                    throw new Error(`HTTP ${res.status}`);
                }

                const freelancers = await res.json();
            
                // Converter freelancers para formato compatível com o resto do app
                const lista = Array.isArray(freelancers) ? freelancers.map(f => ({
                    id: f.usuario_id,
                    nome: f.nome,
                    foto_perfil: f.foto_perfil,
                    distancia_km: f.distancia_km,
                    media_avaliacoes: f.media_avaliacoes,
                    total_avaliacoes: f.total_avaliacoes,
                    latitude: f.latitude,
                    longitude: f.longitude
                })) : [];
            
                setShops(lista);
                salvarBarbeirosCache(lista);

                if (lista.length === 0 && mostrarErro) {
                    notify(`Nenhum barbeiro encontrado até ${raio_km}km`, 'info');
                    await loadDefaultShops({ mostrarErro: false });
                }
            } catch (err) {
                const cache = lerBarbeirosCache();
                if (cache.length > 0) {
                    setShops(cache);
                    notify('Mostrando barbeiros salvos em cache', 'warning');
                    return;
                }

                setShops([]);
                if (mostrarErro) {
                    notify(`Erro ao carregar barbeiros por localização: ${err?.message || 'falha de conexão'}`, 'error');
                }
            }
        }, [API_URL, notify]);

    const loadDefaultBarbearias = useCallback(async ({ mostrarErro = false } = {}) => {
        try {
            const res = await fetch(`${API_URL}/api/v1/barbearias/todas-aprovadas`, {
                headers: token ? { 'Authorization': `Bearer ${token}` } : {}
            });
            if (!res.ok) {
                throw new Error(`HTTP ${res.status}`);
            }
            const data = await res.json();
            const listaBarbearias = Array.isArray(data)
                ? data
                : Array.isArray(data?.barbearias)
                    ? data.barbearias
                    : [];
            setBarbearias(listaBarbearias);
            if (listaBarbearias.length === 0 && mostrarErro) {
                notify('Nenhuma barbearia encontrada no servidor', 'info');
            }
        } catch (err) {
            setBarbearias([]);
            if (mostrarErro) notify(`Erro ao carregar barbearias: ${err?.message || 'falha de conexão'}`, 'error');
        }
    }, [API_URL, notify, token]);

    const carregarMeusPedidos = useCallback(() => {
        fetch(`${API_URL}/api/v1/cliente/meus_pedidos`, { headers: {'Authorization': `Bearer ${token}`} })
            .then(r => r.json())
            .then(data => {
                const pedidos = Array.isArray(data) ? data : [];
                setMyOrders(pedidos);
                const pedidoAtivo = pedidos.find((pedido) => !['concluido', 'concluído', 'cancelado'].includes((pedido.status || '').toLowerCase()));
                setActiveChamado(pedidoAtivo || null);
            })
            .catch(() => setMyOrders([]));
    }, [API_URL, token]);

    useEffect(() => {
        // Carregar barbearias primeiro (novo fluxo):
        loadDefaultBarbearias();
        
        // Carregar dados do usuário
        fetch(`${API_URL}/api/v1/usuarios/perfil-completo`, {
            headers: {'Authorization': `Bearer ${token}`}
        })
            .then(r => r.json())
            .then(setUserData)
            .catch(() => {});
            }, [API_URL, loadDefaultBarbearias, token]);

    useEffect(() => {
        if (typeof window !== 'undefined') {
            localStorage.setItem('cliente_dashboard_tab', tab);
        }
    }, [tab]);

    // Carregamento e atualização periódica dos pedidos são tratados
    // em outro useEffect mais abaixo para evitar múltiplos timers.

    // Fechar modal de cancelamento automaticamente se o chamado deixar de ser visível
    useEffect(() => {
        if (cancelModalOpen && !isChamadoVisivel(activeChamado)) {
            setCancelModalOpen(false);
        }
    }, [activeChamado, cancelModalOpen]);

    // Notificar o usuário se o chamado for cancelado ou finalizado externamente
    const prevChamadoRef = useRef(null);
    useEffect(() => {
        const prev = prevChamadoRef.current;

        if (prev && !activeChamado) {
            // Chamado desapareceu da lista (pode ter sido cancelado ou concluído)
            notify('Seu chamado foi cancelado ou finalizado por outra parte.', 'info');
        } else if (prev && activeChamado && prev.status !== (activeChamado.status || '')) {
            const novoStatus = (activeChamado.status || '').toLowerCase();
            if (novoStatus === 'cancelado') {
                notify('Seu chamado foi cancelado.', 'warning');
            } else if (novoStatus === 'concluido' || novoStatus === 'concluído') {
                notify('Seu chamado foi concluído.', 'success');
            }
        }

        prevChamadoRef.current = activeChamado;
    }, [activeChamado, notify]);

    // ✅ Timer: atualizar a cada segundo para mostrar tempo restante de cancelamento grátis
    useEffect(() => {
        if (!isChamadoVisivel(activeChamado) || !activeChamado?.horario_match) {
            return;
        }

        const intervalo = setInterval(() => {
            setTempoDecorrido(prev => prev + 1);
        }, 1000);

        return () => clearInterval(intervalo);
    }, [activeChamado?.id, activeChamado?.horario_match, isChamadoVisivel(activeChamado)]);

    const requestUserLocation = () => {
        setLoadingLocation(true);
        obterLocalizacaoAtual()
            .then((location) => {
                setUserLocation(location);
                return fetchNearbyShops(location);
            })
            .catch((error) => {
                const msg = error && error.message === 'Permissão de localização negada'
                    ? 'Permissão de localização negada. Ative nas configurações do celular.'
                    : 'Nao foi possivel obter sua localizacao. Ative o GPS para continuar.';
                notify(msg, 'error');
                loadDefaultShops({ mostrarErro: false });
            })
            .finally(() => {
                setLoadingLocation(false);
            });
    };

    const solicitarPermissaoGps = () => {
        setGpsPreference('always');
        salvarPreferenciaGps('always');
        requestUserLocation();
    };

    const fetchNearbyShops = async (location) => {
        try {
            // BUSCAR APENAS FREELANCERS PRÓXIMOS
            const url = new URL(`${API_URL}/api/v1/freelancer/proximos`);
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
                const lista = ordenarBarbeirosParaExibicao(Array.isArray(data)
                    ? data.map((freelancer) => ({
                        id: freelancer.usuario_id,
                        nome: freelancer.nome,
                        foto_perfil: freelancer.foto_perfil,
                        distancia_km: freelancer.distancia_km,
                        media_avaliacoes: freelancer.media_avaliacoes,
                        total_avaliacoes: freelancer.total_avaliacoes,
                        latitude: freelancer.latitude,
                        longitude: freelancer.longitude,
                    }))
                    : []);
                setShops(lista);
                salvarBarbeirosCache(lista);
                if (lista.length === 0) {
                    notify("Nenhum barbeiro encontrado próximo a você (raio 10km)", "info");
                    await loadDefaultShops({ mostrarErro: false });
                } else {
                    notify(`${lista.length} barbeiro(s) encontrado(s) próximo a você!`, "success");
                }
            } else {
                console.error('Erro ao buscar barbeiros:', res.status);
                await loadDefaultShops({ mostrarErro: false });
            }
        } catch (err) {
            console.error('Erro na fetch:', err);
            await loadDefaultShops({ mostrarErro: false });
        }
    };

    useEffect(() => {
        if (tab !== 'buscar') return;

        requestUserLocation();
    }, [tab, gpsPreference, loadDefaultShops]);

    useEffect(() => {
        requestUserLocation();
        const interval = window.setInterval(() => {
            requestUserLocation();
        }, 15000);
        return () => window.clearInterval(interval);
    }, [gpsPreference]);

    // Escuta eventos de mudança de status de barbeiro (ex.: sair da barbearia)
    useEffect(() => {
        const handler = () => {
            // Recarrega a lista atual de barbeiros para refletir mudanças de presença
            if (gpsPreference === 'always' || gpsPreference === 'session') {
                if (userLocation) {
                    requestUserLocation();
                } else {
                    loadDefaultShops();
                }
            } else {
                loadDefaultShops();
            }
        };

        try {
            window.addEventListener('barberStatusChanged', handler);
        } catch (_e) {}

        return () => {
            try { window.removeEventListener('barberStatusChanged', handler); } catch (_e) {}
        };
    }, [gpsPreference, userLocation, requestUserLocation, loadDefaultShops]);

    const aplicarPreferenciaGps = (preferencia) => {
        setGpsPreference(preferencia);
        salvarPreferenciaGps(preferencia);
        setGpsConsentOpen(false);

        if (preferencia === 'never') {
            setUserLocation(null);
            loadDefaultShops();
            return;
        }

        requestUserLocation();
    };

    useEffect(() => {
        carregarMeusPedidos();
    }, [carregarMeusPedidos]);

    useEffect(() => {
        const intervalo = window.setInterval(() => {
            carregarMeusPedidos();
        }, 10000);

        return () => window.clearInterval(intervalo);
    }, [carregarMeusPedidos]);

    const handleSelectShop = async (barber) => {
        setSelectedBarber(barber);
        const barbeariaJaSelecionada = selectedBarbearia?.id != null;

        if (barbeariaJaSelecionada) {
            try {
                const infoRes = await fetch(`${API_URL}/api/v1/usuario/${barber.id}`, {
                    headers: {'Authorization': `Bearer ${token}`}
                });
                if (infoRes.ok) {
                    const info = await infoRes.json();
                    setBarbeiroInfo(info);
                }

                await handleSelectBarbearia(selectedBarbearia);
                return;
            } catch (_err) {
                setStep('servicos');
            }
        }

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

            // Se só existir uma opção, já avança para os serviços para não travar o fluxo
            if (Array.isArray(data) && data.length === 1) {
                await handleSelectBarbearia(data[0]);
                return;
            }
            
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

    // Fluxo inverso: quando usuário selecionar uma barbearia primeiro (inicial),
    // carregar barbeiros presentes naquela barbearia e mostrar a lista de barbeiros.
    const handleSelectBarbeariaInicial = async (barbearia) => {
        try {
            setSelectedBarbearia(barbearia);
            // buscar barbeiros presentes na barbearia
            const res = await fetch(`${API_URL}/api/v1/barbearia/${barbearia.id}/barbeiros-presentes`, {
                headers: token ? {'Authorization': `Bearer ${token}`} : {}
            });
            if (!res.ok) {
                throw new Error(`HTTP ${res.status}`);
            }
            const data = await res.json();
            const lista = normalizarListaBarbeiros(data);
            if (lista.length > 0) {
                setShops(lista);
            } else {
                await loadDefaultShops({ mostrarErro: false });
            }
            // ir para a tela de barbeiros (onde o usuário pode escolher um barbeiro)
            setStep('barbeiros');
        } catch (_err) {
            await loadDefaultShops({ mostrarErro: false });
            setStep('barbeiros');
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

    const localizacaoCliente = userLocation || (
        normalizarNumero(userData?.latitude) != null && normalizarNumero(userData?.longitude) != null
            ? { latitude: normalizarNumero(userData.latitude), longitude: normalizarNumero(userData.longitude) }
            : null
    );

    const distanciaBarbeariaSelecionadaKm = (() => {
        if (!selectedBarbearia) return null;

        if (selectedBarbearia.distancia_km !== undefined && selectedBarbearia.distancia_km !== null) {
            const distanciaApi = normalizarNumero(selectedBarbearia.distancia_km);
            if (distanciaApi != null) return distanciaApi;
        }

        if (localizacaoCliente && selectedBarbearia.latitude != null && selectedBarbearia.longitude != null) {
            return calcularDistanciaKm(
                localizacaoCliente.latitude,
                localizacaoCliente.longitude,
                selectedBarbearia.latitude,
                selectedBarbearia.longitude
            );
        }

        return null;
    })();

    const tempoEstimadoBarbeariaMinutos = estimarTempoMinutos(distanciaBarbeariaSelecionadaKm);
    const clienteDentroDoLimite = tempoEstimadoBarbeariaMinutos !== null && tempoEstimadoBarbeariaMinutos <= 10;
    const distanciaBarbeiroParaBarbeariaKm = (() => {
        if (!selectedBarbearia) return null;
        const lat = normalizarNumero(barbeiroInfo?.latitude) ?? normalizarNumero(selectedBarber?.latitude);
        const lon = normalizarNumero(barbeiroInfo?.longitude) ?? normalizarNumero(selectedBarber?.longitude);
        if (lat == null || lon == null) return null;
        return calcularDistanciaKm(lat, lon, selectedBarbearia.latitude, selectedBarbearia.longitude);
    })();

    const tempoEstimadoBarbeiroMinutos = estimarTempoMinutos(distanciaBarbeiroParaBarbeariaKm);
    const barbeiroDentroDoLimite = tempoEstimadoBarbeiroMinutos !== null && tempoEstimadoBarbeiroMinutos <= 10;
    const gpsStatusTexto = (() => {
        if (!localizacaoCliente) return 'GPS indisponível';
        if (tempoEstimadoBarbeariaMinutos == null) return 'GPS detectado';
        return clienteDentroDoLimite ? 'GPS detectado com boa precisão' : 'GPS detectado, mas a distância está alta';
    })();
    const gpsStatusClasse = localizacaoCliente
        ? (clienteDentroDoLimite ? 'text-green-400' : 'text-amber-300')
        : 'text-red-400';
    const [barbeiroDisponibilidade, setBarbeiroDisponibilidade] = useState(null);

    // Consultar disponibilidade antecipada do barbeiro (regra dos 15 minutos)
    useEffect(() => {
        let mounted = true;
        const fetchDisponibilidade = async () => {
            if (!selectedBarber || !selectedBarber.id) {
                setBarbeiroDisponibilidade(null);
                return;
            }
            try {
                const res = await fetch(`${API_URL}/api/v1/barbeiro/${selectedBarber.id}/pode-receber-chamado`, {
                    headers: { 'Authorization': `Bearer ${token}` }
                });
                if (!mounted) return;
                if (res.ok) {
                    const data = await res.json();
                    setBarbeiroDisponibilidade(data);
                } else {
                    setBarbeiroDisponibilidade(null);
                }
            } catch (_e) {
                if (mounted) setBarbeiroDisponibilidade(null);
            }
        };

        fetchDisponibilidade();
        const interval = setInterval(fetchDisponibilidade, 10000);
        return () => { mounted = false; clearInterval(interval); };
    }, [selectedBarber, API_URL, token]);

    // 🚀 MODELO UBER: Detectar se barbeiro está PRESENTE
    // Usa dados do perfil (mais confiáveis) com fallback para os dados da lista.
    const barbeiroPodeReceberAgora =
        (barbeiroInfo?.pode_receber_chamado_agora ?? selectedBarber?.pode_receber_chamado_agora) === true;
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
    const imediatoPorPresenca = barbeiroPodeReceberAgora && barbeiroPresenteEmLocal && (mesmaBarbearia || barbeariaAtualIdBarbeiro == null);

    // Fluxo atual: só existe chamado em tempo real.
    // Permite chamar somente se tanto o cliente quanto o barbeiro estiverem a até 10 minutos da barbearia.
    const podeChamarAgora = (clienteDentroDoLimite && barbeiroDentroDoLimite) || imediatoPorPresenca || TEST_GPS_OVERRIDE_ATIVO;
    const ehAgendamentoAgora = podeChamarAgora;
    const mensagemAgendamento = "Chamar AGORA";
    const horarioAgendamento = new Date().toISOString();

    const handleBooking = async (service) => {
        // Obter posição precisa antes de validar o limite de 10 minutos
        let localizacao;
        try {
            setLoadingLocation(true);
            localizacao = await obterPosicaoAltaPrecisa();
            // atualizar estado para refletir na UI (evita usar coords de perfil antigo)
            setUserLocation(localizacao);
        } catch (_err) {
            notify('Não foi possível obter localização precisa. Ative o GPS e tente novamente.', 'error');
            return;
        } finally {
            setLoadingLocation(false);
        }

        // Recalcular distância/tempo usando a localização atual
        const distanciaKmAtual = (selectedBarbearia && localizacao)
            ? calcularDistanciaKm(localizacao.latitude, localizacao.longitude, selectedBarbearia.latitude, selectedBarbearia.longitude)
            : null;
        const tempoEstimadoAtual = estimarTempoMinutos(distanciaKmAtual);
        const clienteDentroDoLimiteAtual = tempoEstimadoAtual !== null && tempoEstimadoAtual <= 10;

        // Verificar também o tempo estimado do barbeiro até a barbearia
        const latBarbeiro = normalizarNumero(barbeiroInfo?.latitude) ?? normalizarNumero(selectedBarber?.latitude);
        const lonBarbeiro = normalizarNumero(barbeiroInfo?.longitude) ?? normalizarNumero(selectedBarber?.longitude);
        const distanciaBarbeiroAtualKm = (selectedBarbearia && latBarbeiro != null && lonBarbeiro != null)
            ? calcularDistanciaKm(latBarbeiro, lonBarbeiro, selectedBarbearia.latitude, selectedBarbearia.longitude)
            : null;
        const tempoEstimadoBarbeiroAtual = estimarTempoMinutos(distanciaBarbeiroAtualKm);
        const barbeiroDentroDoLimiteAtual = tempoEstimadoBarbeiroAtual !== null && tempoEstimadoBarbeiroAtual <= 10;

        // Exigir que ambos (cliente e barbeiro) estejam a ≤ 10 minutos, salvo override de dev ou presença imediata
        const podeChamarAgoraAtual = (clienteDentroDoLimiteAtual && barbeiroDentroDoLimiteAtual) || imediatoPorPresenca || TEST_GPS_OVERRIDE_ATIVO;
        if (!podeChamarAgoraAtual) {
            notify('Tanto o cliente quanto o barbeiro devem estar a no máximo 10 minutos da barbearia para chamar agora.', 'error');
            return;
        }

        const localizacaoParaEnvio = TEST_GPS_OVERRIDE_ATIVO && selectedBarbearia?.latitude != null && selectedBarbearia?.longitude != null
            ? { latitude: Number(selectedBarbearia.latitude), longitude: Number(selectedBarbearia.longitude) }
            : localizacao;

        if(!confirm(`${mensagemAgendamento} ${service.nome} com ${selectedBarber.nome}? R$${service.valor}`)) return;

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
                        imediato: true,
                        cliente_latitude: localizacaoParaEnvio.latitude,
                        cliente_longitude: localizacaoParaEnvio.longitude
                    })
            });

            if (!res.ok) {
                const errData = await res.json().catch(() => ({}));
                throw new Error(errData.detail || 'Não foi possível criar o chamado');
            }

            const created = await res.json().catch(() => null);
            if (created && created.id) {
                setActiveChamado(created);
            }
            notify(`🚀 Chamado enviado! ${selectedBarber.nome} vai receber agora!`, "success");
            voltarParaBarbeiros();
            setTab('agenda');
            carregarMeusPedidos();
        } catch (err) {
            notify(err.message || "Erro ao chamar. Tente novamente.", "error");
        }
    };

    const handleBookingMultiple = async () => {
        // Obter posição precisa antes de validar o limite de 10 minutos
        let localizacao;
        try {
            setLoadingLocation(true);
            localizacao = await obterPosicaoAltaPrecisa();
            setUserLocation(localizacao);
        } catch (_err) {
            notify('Não foi possível obter localização precisa. Ative o GPS e tente novamente.', 'error');
            return;
        } finally {
            setLoadingLocation(false);
        }

        const distanciaKmAtual = (selectedBarbearia && localizacao)
            ? calcularDistanciaKm(localizacao.latitude, localizacao.longitude, selectedBarbearia.latitude, selectedBarbearia.longitude)
            : null;
        const tempoEstimadoAtual = estimarTempoMinutos(distanciaKmAtual);

        const latBarbeiroMulti = normalizarNumero(barbeiroInfo?.latitude) ?? normalizarNumero(selectedBarber?.latitude);
        const lonBarbeiroMulti = normalizarNumero(barbeiroInfo?.longitude) ?? normalizarNumero(selectedBarber?.longitude);
        const distanciaBarbeiroMultiKm = (selectedBarbearia && latBarbeiroMulti != null && lonBarbeiroMulti != null)
            ? calcularDistanciaKm(latBarbeiroMulti, lonBarbeiroMulti, selectedBarbearia.latitude, selectedBarbearia.longitude)
            : null;
        const tempoEstimadoBarbeiroMulti = estimarTempoMinutos(distanciaBarbeiroMultiKm);
        const barbeiroDentroDoLimiteMulti = tempoEstimadoBarbeiroMulti !== null && tempoEstimadoBarbeiroMulti <= 10;

        const podeChamarAgoraMulti = ((tempoEstimadoAtual !== null && tempoEstimadoAtual <= 10) && barbeiroDentroDoLimiteMulti) || imediatoPorPresenca || TEST_GPS_OVERRIDE_ATIVO;
        const localizacaoParaEnvio = TEST_GPS_OVERRIDE_ATIVO && selectedBarbearia?.latitude != null && selectedBarbearia?.longitude != null
            ? { latitude: Number(selectedBarbearia.latitude), longitude: Number(selectedBarbearia.longitude) }
            : localizacao;


        if (!podeChamarAgoraMulti) {
                notify('Você precisa estar a no máximo 10 minutos da barbearia para chamar agora.', 'error');
                return;
            }
        if (selectedServices.length === 0) {
            notify('Selecione pelo menos um serviço', 'error');
            return;
        }

        const nomes = selectedServices.map((s) => s.nome).join(', ');
        if (!confirm(`${mensagemAgendamento} ${nomes} com ${selectedBarber.nome}? R$${totalSelecionado}`)) {
            return;
        }

        try {
            const baseTime = new Date();
                
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
                        imediato: true,
                        cliente_latitude: localizacaoParaEnvio.latitude,
                        cliente_longitude: localizacaoParaEnvio.longitude
                    })
                });

                if (!res.ok) {
                    const errData = await res.json().catch(() => ({}));
                    throw new Error(errData.detail || `Falha ao criar chamado para ${service.nome}`);
                }
            }
            notify(`🚀 Chamados enviados! ${selectedBarber.nome} vai receber agora!`, "success");
            // se backend retornou um objeto com id do primeiro chamado, sincroniza
            try {
                const recent = await fetch(`${API_URL}/api/v1/cliente/meus_pedidos`, { headers: {'Authorization': `Bearer ${token}`} });
                if (recent.ok) {
                    const pedidos = await recent.json();
                    if (Array.isArray(pedidos) && pedidos.length > 0) {
                        const pedidoAtivo = pedidos.find((pedido) => !['concluido', 'concluído', 'cancelado'].includes((pedido.status || '').toLowerCase()));
                        setActiveChamado(pedidoAtivo || pedidos[0]);
                    }
                }
            } catch (_) {}
            voltarParaBarbeiros();
            setTab('agenda');
            carregarMeusPedidos();
        } catch (err) {
            notify(err.message || "Erro ao chamar. Tente novamente.", "error");
        }
    };

    return (
    <div className="bg-black min-h-[100dvh] w-full max-w-full overflow-x-hidden flex flex-col text-white font-sans">
        {/* HEADER */}
        <div className="p-2 sm:p-4 flex justify-between items-center border-b border-zinc-800 bg-black/80 backdrop-blur-md z-20 flex-shrink-0">
            <h1 className="text-base sm:text-xl font-bold tracking-tight">Buscar Barbeiros</h1>
            <button onClick={logout} className="text-zinc-500 hover:text-white"><LogOut size={18}/></button>
        </div>

        {/* Painel de rastreamento/chat ativo (quando há um chamado imediato) */}
        {isChamadoVisivel(activeChamado) && (
            <div className="p-2 sm:p-4 max-w-3xl mx-auto w-full">
                <div className="bg-zinc-900/80 backdrop-blur rounded-lg p-3 space-y-3 border border-zinc-800">
                    <div className="flex items-center justify-between">
                        <div>
                            <p className="font-bold">Chamado ativo</p>
                            <p className="text-xs text-zinc-400">ID: {activeChamado.id} — {activeChamado.servico_nome || activeChamado.descricao || ''}</p>
                        </div>
                        <div className="text-right space-y-1">
                            <div className="text-xs text-zinc-400">Status: {activeChamado.status || 'ativo'}</div>
                            <div className="text-xs font-bold text-orange-400">
                                ⏱️ {getCancelamentoInfo(activeChamado).tempoRestante}
                            </div>
                            <div className="space-y-1">
                                {onChamadoAceito && (
                                    <button
                                        onClick={() => onChamadoAceito(activeChamado.id)}
                                        className="text-[11px] font-bold px-3 py-1 rounded-full text-white bg-blue-600 hover:bg-blue-500 transition-all w-full"
                                    >
                                        📍 Ver Rastreamento
                                    </button>
                                )}
                                <button
                                    onClick={abrirConfirmacaoCancelamento}
                                    className={`text-[11px] font-bold px-3 py-1 rounded-full text-white transition-all w-full ${
                                        getCancelamentoInfo(activeChamado).taxa > 0
                                            ? 'bg-red-600 hover:bg-red-500'
                                            : 'bg-green-600 hover:bg-green-500'
                                    }`}
                                >
                                    {getCancelamentoBotaoTexto(activeChamado)}
                                </button>
                            </div>
                        </div>
                    </div>
                    <div className={`rounded-lg border p-3 text-xs ${
                        getCancelamentoInfo(activeChamado).taxa > 0
                            ? 'border-red-500/50 bg-red-500/10 text-red-100'
                            : getCancelamentoInfo(activeChamado).tempoRestante === '0:00'
                                ? 'border-yellow-500/50 bg-yellow-500/10 text-yellow-100'
                                : 'border-green-500/50 bg-green-500/10 text-green-100'
                    }`}>
                        {getCancelamentoInfo(activeChamado).taxa === 0 ? (
                            <>
                                <div className="flex items-center gap-2 mb-1">
                                    <span>✅ Cancelamento grátis disponível</span>
                                </div>
                                <div className="text-xs opacity-90">
                                    Tempo restante para cancelar sem taxa: {getCancelamentoInfo(activeChamado).tempoRestante}
                                </div>
                            </>
                        ) : (
                            <>
                                <div className="flex items-center gap-2 mb-1">
                                    <span>⚠️ Janela de cancelamento grátis expirou</span>
                                </div>
                                <div className="text-xs opacity-90">
                                    Taxa de cancelamento: R$ {getCancelamentoInfo(activeChamado).taxa.toFixed(2)}
                                </div>
                            </>
                        )}
                    </div>

                    {/* Painel de rastreamento e informações adicionais */}
                    <div className="rounded-lg border border-amber-500/30 bg-amber-500/10 p-3 text-xs text-amber-100">
                        {getCancelamentoInfo(activeChamado).texto}
                        {getCancelamentoInfo(activeChamado).taxa > 0 && (
                            <div className="mt-1 font-bold">
                                Taxa de cancelamento: R$ {getCancelamentoInfo(activeChamado).taxa.toFixed(2)}
                            </div>
                        )}
                    </div>
                    <div className="grid grid-cols-1 lg:grid-cols-[minmax(0,1.3fr)_minmax(0,1fr)] gap-3 items-start">
                        <TrackingPanel chamado={activeChamado} token={token} API_URL={API_URL} notify={notify} />
                        <div className="min-h-[70vh]">
                            <ChatRoom chamadoId={activeChamado.id} token={token} API_URL={API_URL} compact={false} />
                        </div>
                    </div>
                </div>
            </div>
        )}

        {cancelModalOpen && activeChamado && (
            <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 px-4">
                <div className="w-full max-w-md rounded-2xl border border-zinc-800 bg-zinc-950 p-4 shadow-2xl">
                    <h3 className="text-lg font-bold">Cancelar chamado?</h3>
                    <p className="mt-2 text-sm text-zinc-300">{getCancelamentoInfo(activeChamado).texto}</p>
                    <p className="mt-2 text-xs text-zinc-500">Motivo: {getCancelamentoInfo(activeChamado).motivo}</p>
                    {getCancelamentoInfo(activeChamado).taxa > 0 && (
                        <p className="mt-2 text-xs font-bold text-amber-300">Taxa aplicada: R$ {getCancelamentoInfo(activeChamado).taxa.toFixed(2)}</p>
                    )}
                    <div className="mt-4 flex gap-2">
                        <button
                            onClick={() => setCancelModalOpen(false)}
                            className="flex-1 rounded-lg border border-zinc-700 px-4 py-2 text-sm font-bold text-zinc-200 hover:bg-zinc-800"
                            disabled={cancelandoChamado}
                        >
                            Voltar
                        </button>
                        <button
                            onClick={confirmarCancelamento}
                            className="flex-1 rounded-lg bg-red-600 px-4 py-2 text-sm font-bold text-white hover:bg-red-500 disabled:opacity-60"
                            disabled={cancelandoChamado}
                        >
                            {cancelandoChamado ? 'Cancelando...' : 'Confirmar cancelamento'}
                        </button>
                    </div>
                </div>
            </div>
        )}

            {/* CONTEÚDO - SÓ UMA ABA (inicial focada na barbearia) */}
        <div className="flex-1 overflow-visible pb-[calc(6rem+env(safe-area-inset-bottom))]">
            {/* ABA: BUSCAR */}
            {tab === 'buscar' && (
                <div className="p-2 sm:p-4 space-y-3 max-w-3xl mx-auto w-full">
                    {/* Tela inicial: itens da barbearia e lembretes */}
                    {step === 'inicio' && (
                        <div className="space-y-3">
                            <h2 className="text-sm font-bold text-zinc-300">Sua Barbearia</h2>
                            <div className="bg-zinc-900/60 border border-zinc-800 rounded-xl p-3 text-xs text-zinc-400">
                                O controle de cadeiras e o início do atendimento são feitos pela barbearia.
                            </div>

                            <div>
                                <button onClick={() => setStep('barbearias')} className="w-full py-2 bg-orange-600 hover:bg-orange-700 rounded text-xs font-bold">Selecionar Barbearia</button>
                            </div>
                        </div>
                    )}
                    {step === 'barbeiros' && (
                        <>
                            <div className="sticky top-0 bg-black/90 z-10 pb-3">
                                <div className="relative mb-3">
                                    <Search className="absolute left-3 top-3 text-zinc-500" size={16} />
                                    <input placeholder="Buscar barbeiro..." className="w-full bg-zinc-900 pl-10 pr-4 py-2 rounded-lg border border-zinc-800 outline-none focus:border-orange-500 text-xs" />
                                </div>
                                <button 
                                    onClick={solicitarPermissaoGps}
                                    className="w-full bg-orange-600 text-white py-2 rounded-lg font-bold text-xs hover:bg-orange-700 transition-all"
                                >
                                    {loadingLocation ? 'Atualizando GPS...' : userLocation ? 'GPS obrigatorio ativo' : 'Ativar GPS obrigatorio'}
                                </button>
                                <p className="mt-2 text-[11px] text-zinc-500">
                                    Localizacao obrigatoria para chamar e acompanhar em tempo real.
                                </p>
                            </div>
                            <div className="space-y-2">
                                {shops && shops.length > 0 ? shops.map(barber => {
                                    const barbeiroDeTeste = /teste/i.test(barber.nome || '');
                                    // Determinar status do freelancer
                                    const statusInfo = barbeiroDeTeste ? {
                                        texto: 'BARBEIRO DE TESTE',
                                        cor: 'bg-indigo-600',
                                        icone: '🧪'
                                    } : barber.presente_em_local && barber.barbearia_atual_id ? {
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
                                                disabled={!barbeiroDeTeste && (statusInfo.texto === 'INDISPONÍVEL' || statusInfo.texto === 'OFFLINE')}
                                                className={`flex-1 ${(!barbeiroDeTeste && (statusInfo.texto === 'INDISPONÍVEL' || statusInfo.texto === 'OFFLINE')) ? 'bg-zinc-700 cursor-not-allowed' : 'bg-orange-600 hover:bg-orange-700'} text-white py-2 rounded-lg text-xs font-bold`}
                                            >
                                                {(!barbeiroDeTeste && (statusInfo.texto === 'INDISPONÍVEL' || statusInfo.texto === 'OFFLINE')) ? 'Indisponível' : 'Escolher'}
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

                    {gpsConsentOpen && null}

                    {step === 'barbearias' && (
                        <>
                            <button onClick={voltarParaBarbeiros} className="text-xs text-zinc-400 hover:text-white flex items-center gap-1">
                                <ArrowRight size={12} className="rotate-180" /> Voltar para barbeiros
                            </button>
                            <h2 className="text-sm font-bold text-zinc-300">Escolha uma barbearia para {selectedBarber?.nome}</h2>
                            <div className="space-y-2">
                                {selectedBarber && barbearias.length > 1 && (
                                    <div className="rounded-xl border border-orange-500/30 bg-orange-500/10 p-3 text-xs text-orange-100">
                                        <p className="font-bold text-orange-300">Agora escolha a barbearia</p>
                                        <p className="mt-1 text-orange-100/80">
                                            O barbeiro {selectedBarber.nome} atende em mais de uma unidade. Toque em uma barbearia abaixo para seguir para os serviços.
                                        </p>
                                    </div>
                                )}
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
                                                onClick={() => handleSelectBarbeariaInicial(barbearia)}
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
                            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                                <div className={`rounded-lg p-3 border shadow-sm ${localizacaoCliente ? (clienteDentroDoLimite ? 'bg-green-950/40 border-green-500/40' : 'bg-amber-950/30 border-amber-500/40') : 'bg-red-950/30 border-red-500/40'}`}>
                                    <p className="text-[10px] uppercase tracking-wide text-zinc-500 mb-1">Sua localização detectada</p>
                                    <p className="text-sm font-bold text-white">
                                        {localizacaoCliente
                                            ? `${localizacaoCliente.latitude.toFixed(4)}, ${localizacaoCliente.longitude.toFixed(4)}`
                                            : 'GPS indisponível'}
                                    </p>
                                    <div className="mt-2 flex items-center gap-2 flex-wrap">
                                        <span className={`text-[10px] font-bold px-2 py-1 rounded-full border ${localizacaoCliente ? (clienteDentroDoLimite ? 'bg-green-500/15 text-green-300 border-green-500/30' : 'bg-amber-500/15 text-amber-300 border-amber-500/30') : 'bg-red-500/15 text-red-300 border-red-500/30'}`}>
                                            {localizacaoCliente ? (clienteDentroDoLimite ? 'GPS OK' : 'GPS DISTANTE') : 'SEM GPS'}
                                        </span>
                                        <p className={`text-[11px] font-semibold ${gpsStatusClasse}`}>{gpsStatusTexto}</p>
                                    </div>
                                </div>
                                <div className="bg-zinc-900 border border-zinc-800 rounded-lg p-3">
                                    <p className="text-[10px] uppercase tracking-wide text-zinc-500 mb-1">Barbearia selecionada</p>
                                    <p className="text-sm font-bold text-white">{selectedBarbearia?.nome || 'Barbearia'}</p>
                                    <p className="text-[11px] text-zinc-400 truncate">{selectedBarbearia?.endereco || 'Endereço não informado'}</p>
                                </div>
                            </div>
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

                            {/* 🚀 Modo chamada imediata: mostrar quando o backend confirmar presença real */}
                            {barbeiroPodeReceberAgora && (
                                <div className="bg-green-900/30 border-2 border-green-500 rounded-lg p-3 text-center">
                                    <p className="text-green-400 font-bold text-sm">🚀 CHAMADA EM TEMPO REAL</p>
                                    <p className="text-xs text-green-300 mt-1">{selectedBarber?.nome} está PRESENTE na barbearia!</p>
                                    <p className="text-xs text-green-300">Vai receber seu chamado AGORA</p>
                                </div>
                            )}

                            {!podeChamarAgora ? (
                                <div className="bg-red-900/30 border-2 border-red-500 rounded-lg p-3 text-center">
                                    <p className="text-red-300 font-bold text-sm">Você precisa estar a no máximo 10 minutos da barbearia</p>
                                    <p className="text-xs text-red-200 mt-1">
                                        {tempoEstimadoBarbeariaMinutos !== null
                                            ? `Distância estimada: ${tempoEstimadoBarbeariaMinutos} min. Vá até a barbearia e tente de novo.`
                                            : 'Não foi possível medir sua distância. Ative a localização para chamar agora.'}
                                    </p>
                                </div>
                            ) : (
                                <div className="bg-green-900/30 border-2 border-green-500 rounded-lg p-3 text-center">
                                    <p className="text-green-400 font-bold text-sm">🚀 CHAMADA EM TEMPO REAL</p>
                                    <p className="text-xs text-green-300 mt-1">
                                        Distância estimada: {tempoEstimadoBarbeariaMinutos} min até a barbearia.
                                    </p>
                                    <p className="text-xs text-green-300">Você pode chamar agora</p>
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
                                                    disabled={!podeChamarAgora}
                                                    className={`flex-1 ${podeChamarAgora ? 'bg-green-600 hover:bg-green-700' : 'bg-zinc-700 cursor-not-allowed'} text-white py-2 rounded-lg font-bold text-xs`}
                                            >
                                                Chamar AGORA
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
                                        disabled={!podeChamarAgora}
                                        className={`mt-3 w-full ${podeChamarAgora ? 'bg-green-600 hover:bg-green-700' : 'bg-zinc-700 cursor-not-allowed'} text-white py-2 rounded-lg font-bold text-xs`}
                                    >
                                        Chamar AGORA
                                    </button>
                                </div>
                            )}
                        </>
                    )}
                </div>
            )}

            {/* ABA: AGENDA */}
            {tab === 'agenda' && (
                <div className="p-2 sm:p-4 max-w-3xl mx-auto w-full">
                    <h2 className="text-sm font-bold text-zinc-300 uppercase tracking-wide mb-4">Minhas Chamadas</h2>
                    {!Array.isArray(myOrders) || myOrders.length === 0 ? (
                        <p className="text-zinc-600 text-center py-12 text-xs">Nenhuma chamada</p>
                    ) : (
                        <div className="space-y-2 max-w-2xl mx-auto w-full">
                            {myOrders.map(order => (
                                <div key={order.id} className="bg-zinc-900/60 p-3.5 rounded-xl border border-zinc-800/80 text-xs overflow-hidden space-y-1">
                                    <p className="font-bold truncate">{order.barbeiro_nome || 'Barbeiro'}</p>
                                    <p className="text-zinc-400 truncate">{order.servico_nome || order.descricao || 'Servico'}</p>
                                    <p className="text-zinc-500 truncate">{order.nome_barbearia || 'Barbearia'}</p>
                                    {order.data_hora_inicio && (
                                        <p className="text-zinc-300">{new Date(order.data_hora_inicio).toLocaleString('pt-BR')}</p>
                                    )}
                                    <p className="text-zinc-500">Status: {order.status}</p>

                                    {order.imediato && (
                                        <div className="mt-2 rounded-lg border border-zinc-700 bg-zinc-950/60 p-2.5 space-y-1.5">
                                            <p className="text-[11px] font-bold text-green-400">🚀 Chamar AGORA - Rastreamento</p>

                                            {order.cliente_distancia_ate_barbearia_km != null && (
                                                <p className="text-zinc-300 text-[11px]">
                                                    Cliente → Barbearia: {order.cliente_distancia_ate_barbearia_km} km
                                                    {order.cliente_eta_ate_barbearia_min != null ? ` (~${order.cliente_eta_ate_barbearia_min} min)` : ''}
                                                </p>
                                            )}

                                            {order.freelancer_distancia_ate_barbearia_km != null && (
                                                <p className="text-zinc-300 text-[11px]">
                                                    Freelancer → Barbearia: {order.freelancer_distancia_ate_barbearia_km} km
                                                    {order.freelancer_eta_ate_barbearia_min != null ? ` (~${order.freelancer_eta_ate_barbearia_min} min)` : ''}
                                                </p>
                                            )}

                                            {order.tempo_restante_limite_min != null && (
                                                <p className={`text-[11px] font-semibold ${order.tempo_restante_limite_min < 0 ? 'text-red-400' : 'text-amber-300'}`}>
                                                    Limite de chegada: {order.tempo_restante_limite_min < 0
                                                        ? `atrasado ${Math.abs(order.tempo_restante_limite_min)} min`
                                                        : `${order.tempo_restante_limite_min} min restantes`}
                                                </p>
                                            )}

                                            {order.freelancer_atrasado === true && (
                                                <p className="text-red-400 text-[11px] font-semibold">
                                                    ⚠️ Freelancer fora do prazo para chegar na barbearia.
                                                </p>
                                            )}
                                        </div>
                                    )}

                                    {isConcluido(order.status) ? (
                                        <div className="mt-2 rounded-lg border border-green-500/30 bg-green-500/10 p-2.5">
                                            <p className="text-[11px] font-bold text-green-300">Pagamento liberado</p>
                                            <p className="text-[11px] text-zinc-300">O serviço já foi concluído. A cobrança aparece na aba Pagamentos.</p>
                                        </div>
                                    ) : (
                                        <div className="mt-2 rounded-lg border border-zinc-700 bg-zinc-950/60 p-2.5">
                                            <p className="text-[11px] text-zinc-400">O pagamento só fica disponível depois da conclusão do serviço.</p>
                                        </div>
                                    )}
                                </div>
                            ))}
                        </div>
                    )}
                </div>
            )}

            {/* ABA: AVALIAR */}
            {tab === 'avaliar' && (
                <div className="p-2 sm:p-4 pb-20 max-w-3xl mx-auto w-full">
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
                <div className="p-2 sm:p-4 pb-20 max-w-3xl mx-auto w-full">
                    <h2 className="text-sm font-bold text-zinc-300 uppercase tracking-wide mb-4">Pagamentos do serviço concluído</h2>
                    {(() => {
                        const pendentes = (myOrders || []).filter(o =>
                            isConcluido(o.status)
                        );
                        if (pendentes.length === 0) {
                            return (
                                <div className="text-center py-14 space-y-2">
                                    <CheckCircle size={40} className="mx-auto text-zinc-700" />
                                    <p className="text-zinc-500 text-sm">Sem pagamentos liberados</p>
                                    <p className="text-zinc-600 text-xs">O pagamento aparece quando o serviço é concluído</p>
                                </div>
                            );
                        }
                        return (
                            <div className="space-y-3 max-w-2xl mx-auto w-full">
                                {pendentes.map(order => (
                                    <div key={order.id} className="bg-zinc-900/60 rounded-xl border border-zinc-800/80 p-3.5 space-y-2.5 overflow-hidden">
                                        <div className="flex justify-between items-start">
                                            <div className="min-w-0 pr-2">
                                                <p className="font-bold text-white text-sm truncate">{order.servico_nome || order.descricao || 'Serviço'}</p>
                                                <p className="text-zinc-400 text-xs truncate">{order.barbeiro_nome || 'Barbeiro'} · {order.nome_barbearia || 'Barbearia'}</p>
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
                <div className="p-2 sm:p-4 pb-20 max-w-3xl mx-auto w-full">
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
        <div className="sticky bottom-0 left-0 w-full h-[calc(4rem+env(safe-area-inset-bottom))] pb-[env(safe-area-inset-bottom)] bg-zinc-950/98 backdrop-blur-lg border-t border-zinc-800 flex justify-around items-center z-40">
            <button onClick={() => setTab('buscar')} className={`flex flex-col items-center justify-center gap-0.5 h-full flex-1 text-center transition-colors ${tab === 'buscar' ? 'text-orange-500 bg-orange-500/5' : 'text-zinc-400 hover:text-zinc-200'}`}><Search size={14} /><span className="text-[7px] font-bold">Buscar</span></button>
            <button onClick={() => setTab('agenda')} className={`flex flex-col items-center justify-center gap-0.5 h-full flex-1 text-center transition-colors ${tab === 'agenda' ? 'text-orange-500 bg-orange-500/5' : 'text-zinc-400 hover:text-zinc-200'}`}><Calendar size={14} /><span className="text-[7px] font-bold">Chamadas</span></button>
            <button onClick={() => setTab('avaliar')} className={`flex flex-col items-center justify-center gap-0.5 h-full flex-1 text-center transition-colors ${tab === 'avaliar' ? 'text-orange-500 bg-orange-500/5' : 'text-zinc-400 hover:text-zinc-200'}`}><Star size={14} /><span className="text-[7px] font-bold">Avaliar</span></button>
            <button onClick={() => setTab('perfil')} className={`flex flex-col items-center justify-center gap-0.5 h-full flex-1 text-center transition-colors ${tab === 'perfil' ? 'text-orange-500 bg-orange-500/5' : 'text-zinc-400 hover:text-zinc-200'}`}><User size={14} /><span className="text-[7px] font-bold">Perfil</span></button>
            <button onClick={() => setTab('pagamento')} className={`flex flex-col items-center justify-center gap-0.5 h-full flex-1 text-center transition-colors ${tab === 'pagamento' ? 'text-orange-500 bg-orange-500/5' : 'text-zinc-400 hover:text-zinc-200'}`}><CreditCard size={14} /><span className="text-[7px] font-bold">Pagamentos</span></button>
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
                        onNotify={notify}
                    />
                </div>
            </div>
        )}

        {/* Mostrar rotas quando chamado está confirmado */}
        {activeChamado && ['confirmado', 'em_atendimento'].includes((activeChamado.status || '').toLowerCase()) && (
          <TelaRotasAtivos
            chamado={activeChamado}
            userType="cliente"
            userLocation={localizacaoCliente}
            barbeiroLocation={selectedBarber}
            barbearia={selectedBarbearia}
            barbeiro={selectedBarber}
            onNotify={notify}
          />
        )}
        </div>
    );
}