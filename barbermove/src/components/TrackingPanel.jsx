import React, { useEffect, useMemo, useRef, useState } from 'react';
import MapEmbed from './MapEmbed';
import TrackingMapEmbed from './TrackingMapEmbed';

const toRad = (value) => (value * Math.PI) / 180;
const haversineKm = (lat1, lon1, lat2, lon2) => {
    if ([lat1, lon1, lat2, lon2].some((value) => value == null || Number.isNaN(Number(value)))) return null;
    const R = 6371;
    const dLat = toRad(lat2 - lat1);
    const dLon = toRad(lon2 - lon1);
    const a = Math.sin(dLat / 2) ** 2 + Math.cos(toRad(lat1)) * Math.cos(toRad(lat2)) * Math.sin(dLon / 2) ** 2;
    return R * (2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a)));
};

export default function TrackingPanel({ chamado, token, API_URL, notify, modo = 'cliente', barbeariaId = null }) {
    const [posicaoAtual, setPosicaoAtual] = useState(null);
    const [destinoInfo, setDestinoInfo] = useState(null);
    const [distanciaBackend, setDistanciaBackend] = useState(null);
    const [etaBackend, setEtaBackend] = useState(null);
    const [coordsCliente, setCoordsCliente] = useState(null);
    const [coordsBarbeiro, setCoordsBarbeiro] = useState(null);
    const [resumo, setResumo] = useState(null);
    const [agendamentos, setAgendamentos] = useState([]);
    const watchIdRef = useRef(null);
    const wsRef = useRef(null);

    const isBarbeiroMode = modo === 'barbeiro';
    const isBarbeariaMode = modo === 'barbearia';
    const isClienteMode = modo === 'cliente';

    useEffect(() => {
        const carregarResumo = async () => {
            try {
                const endpoint = isBarbeariaMode && barbeariaId
                    ? `${API_URL}/api/v1/barbearia/${barbeariaId}/agendamentos`
                    : isBarbeiroMode
                        ? `${API_URL}/api/v1/barbeiro/agendamentos/meus`
                        : `${API_URL}/api/v1/cliente/meus_pedidos`;

                const res = await fetch(endpoint, {
                    headers: { 'Authorization': `Bearer ${token}` }
                });
                if (!res.ok) return;

                const pedidos = await res.json();
                const lista = Array.isArray(pedidos) ? pedidos : Array.isArray(pedidos?.agendamentos) ? pedidos.agendamentos : [];
                setAgendamentos(lista);
                const atual = lista.length > 0
                    ? (chamado?.id ? lista.find((p) => Number(p.id) === Number(chamado.id)) : lista.find((p) => !['concluido', 'concluído', 'cancelado'].includes((p.status || '').toLowerCase())))
                    : null;

                if (!atual) return;
                setResumo(atual);
                setDistanciaBackend(isBarbeiroMode ? atual.freelancer_distancia_ate_barbearia_km : atual.cliente_distancia_ate_barbearia_km);
                setEtaBackend(isBarbeiroMode ? atual.freelancer_eta_ate_barbearia_min : atual.cliente_eta_ate_barbearia_min);

                if (atual?.id) {
                    try {
                        const trackingRes = await fetch(`${API_URL}/api/v1/tracking/chamados/${atual.id}/eta`, {
                            headers: { 'Authorization': `Bearer ${token}` }
                        });
                        if (trackingRes.ok) {
                            const tracking = await trackingRes.json();
                            const distanciaAtual = isBarbeiroMode
                                ? tracking?.freelancer_distancia_ate_barbearia_km
                                : tracking?.cliente_distancia_ate_barbearia_km;
                            const etaAtual = isBarbeiroMode
                                ? tracking?.freelancer_eta_ate_barbearia_min
                                : tracking?.cliente_eta_ate_barbearia_min;
                            if (distanciaAtual != null) setDistanciaBackend(distanciaAtual);
                            if (etaAtual != null) setEtaBackend(etaAtual);

                            const cCliente = tracking?.coordenadas_cliente;
                            const cBarbeiro = tracking?.coordenadas_barbeiro;
                            if (cCliente?.lat != null && cCliente?.lon != null) {
                                setCoordsCliente({ lat: Number(cCliente.lat), lon: Number(cCliente.lon) });
                            }
                            if (cBarbeiro?.lat != null && cBarbeiro?.lon != null) {
                                setCoordsBarbeiro({ lat: Number(cBarbeiro.lat), lon: Number(cBarbeiro.lon) });
                            }
                        }
                    } catch (_err) {
                        // fallback permanece no resumo já carregado
                    }
                }

                const barbeariaId = atual.barbearia_id;
                if (!barbeariaId) return;

                const barbeariaIdAtual = atual?.barbearia_id || barbeariaId || resumo?.barbearia_id;
                if (barbeariaIdAtual) {
                    const barbeariaRes = await fetch(`${API_URL}/api/v1/barbearias/${barbeariaIdAtual}`, {
                        headers: { 'Authorization': `Bearer ${token}` }
                    });
                    if (!barbeariaRes.ok) return;
                    const barbearia = await barbeariaRes.json();
                    setDestinoInfo(barbearia);
                }
            } catch (_err) {
                // silencioso: o painel já funciona com fallback de rota/mapa
            }
        };

        carregarResumo();
        const interval = window.setInterval(carregarResumo, 5000);
        return () => window.clearInterval(interval);
    }, [API_URL, barbeariaId, chamado?.id, token, isBarbeiroMode, isBarbeariaMode]);

    useEffect(() => {
        const chamadoIdAtual = chamado?.id || resumo?.id;
        if (!chamadoIdAtual) return;

        const wsUrl = API_URL
            ? `${API_URL.replace(/^http/, 'ws')}/ws/notificacoes`
            : null;
        if (!wsUrl) return;

        try {
            const ws = new WebSocket(wsUrl);
            wsRef.current = ws;

            ws.onmessage = (event) => {
                try {
                    const payload = JSON.parse(event.data);
                    if (payload?.type !== 'tracking_update') return;
                    if (Number(payload?.chamado_id) !== Number(chamadoIdAtual)) return;

                    const tracking = payload?.tracking || {};
                    const distanciaAtual = isBarbeiroMode
                        ? tracking?.freelancer_distancia_ate_barbearia_km
                        : tracking?.cliente_distancia_ate_barbearia_km;
                    const etaAtual = isBarbeiroMode
                        ? tracking?.freelancer_eta_ate_barbearia_min
                        : tracking?.cliente_eta_ate_barbearia_min;

                    if (distanciaAtual != null) setDistanciaBackend(distanciaAtual);
                    if (etaAtual != null) setEtaBackend(etaAtual);

                    const cCliente = tracking?.coordenadas_cliente;
                    const cBarbeiro = tracking?.coordenadas_barbeiro;
                    if (cCliente?.lat != null && cCliente?.lon != null) {
                        setCoordsCliente({ lat: Number(cCliente.lat), lon: Number(cCliente.lon) });
                    }
                    if (cBarbeiro?.lat != null && cBarbeiro?.lon != null) {
                        setCoordsBarbeiro({ lat: Number(cBarbeiro.lat), lon: Number(cBarbeiro.lon) });
                    }

                    const barbeariaTracking = tracking?.barbearia;
                    if (barbeariaTracking?.id) {
                        setDestinoInfo((prev) => ({ ...prev, ...barbeariaTracking }));
                    }
                } catch (_err) {
                    // Ignora payload inválido
                }
            };
        } catch (_err) {
            // Sem websocket disponível, mantém polling
        }

        return () => {
            if (wsRef.current) {
                try {
                    wsRef.current.close();
                } catch (_err) {
                    // noop
                }
                wsRef.current = null;
            }
        };
    }, [API_URL, chamado?.id, resumo?.id, isBarbeiroMode]);

    useEffect(() => {
        startSharing(true);

        return () => {
            stopSharing(true);
        };
    }, [API_URL, chamado?.id, resumo?.id, token, isBarbeariaMode, isBarbeiroMode]);

    const startSharing = (silencioso = false) => {
        if (!navigator.geolocation) {
            if (!silencioso) notify('Geolocalização não suportada', 'error');
            return;
        }
        if (watchIdRef.current != null) {
            navigator.geolocation.clearWatch(watchIdRef.current);
        }
        const inaccurateNotifiedRef = { current: false };
        watchIdRef.current = navigator.geolocation.watchPosition(async (pos) => {
            const payload = {
                latitude: pos.coords.latitude,
                longitude: pos.coords.longitude,
                accuracy: pos.coords.accuracy,
                ts: new Date().toISOString()
            };
            setPosicaoAtual(payload);
            // Se a precisão for muito baixa (ex.: > 5000m), não enviar — provavelmente vindo do provedor de rede
            const accuracyMeters = Number(pos.coords.accuracy || 1e9);
            if (accuracyMeters > 5000) {
                if (!inaccurateNotifiedRef.current && !silencioso) {
                    notify('Sinal de localização impreciso (usando localização por rede). Ative HTTPS/flags de confiança para usar GPS.', 'warning');
                    inaccurateNotifiedRef.current = true;
                }
                return; // pular envio enquanto precisão for ruim
            }
            // se recuperação de precisão ocorreu, resetar flag
            inaccurateNotifiedRef.current = false;
            try {
                const chamadoIdAtual = chamado?.id || resumo?.id;
                const usaTrackingPorChamado = Boolean(chamadoIdAtual) && !isBarbeariaMode;
                const endpoint = usaTrackingPorChamado
                    ? isBarbeiroMode
                        ? `${API_URL}/api/v1/tracking/chamados/${chamadoIdAtual}/posicao-barbeiro`
                        : `${API_URL}/api/v1/tracking/chamados/${chamadoIdAtual}/posicao-cliente`
                    : `${API_URL}/api/v1/atualizar-localizacao`;

                const method = usaTrackingPorChamado ? 'PATCH' : 'POST';
                const body = usaTrackingPorChamado
                    ? { latitude: payload.latitude, longitude: payload.longitude }
                    : { latitude: payload.latitude, longitude: payload.longitude, chamado_id: chamadoIdAtual || null };

                await fetch(endpoint, {
                    method,
                    headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
                    body: JSON.stringify(body)
                });
            } catch (_err) {
                // ignore
            }
        }, (err) => {
            if (!silencioso) notify('Erro ao obter localização: ' + (err.message || ''), 'error');
        }, { enableHighAccuracy: true, maximumAge: 0, timeout: 12000 });
        if (!silencioso) notify('Compartilhamento de localização ativo', 'success');
    };

    const stopSharing = (silencioso = false) => {
        if (watchIdRef.current != null) {
            navigator.geolocation.clearWatch(watchIdRef.current);
            watchIdRef.current = null;
        }
        if (!silencioso) notify('Compartilhamento de localização parado', 'info');
    };

    const distanciaAtualParaDestino = useMemo(() => {
        if (!posicaoAtual || !destinoInfo?.latitude || !destinoInfo?.longitude) return null;
        return haversineKm(posicaoAtual.latitude, posicaoAtual.longitude, destinoInfo.latitude, destinoInfo.longitude);
    }, [destinoInfo?.latitude, destinoInfo?.longitude, posicaoAtual]);

    const tempoEstimadoAtual = useMemo(() => {
        if (distanciaAtualParaDestino == null) return null;
        return Math.max(1, Math.round(distanciaAtualParaDestino * 4));
    }, [distanciaAtualParaDestino]);

    const coordsBarbearia = useMemo(() => {
        if (destinoInfo?.latitude == null || destinoInfo?.longitude == null) return null;
        return { lat: Number(destinoInfo.latitude), lon: Number(destinoInfo.longitude) };
    }, [destinoInfo?.latitude, destinoInfo?.longitude]);

    const distanciaClienteBarbeiroKm = useMemo(() => {
        if (!coordsCliente || !coordsBarbeiro) return null;
        return haversineKm(coordsCliente.lat, coordsCliente.lon, coordsBarbeiro.lat, coordsBarbeiro.lon);
    }, [coordsCliente, coordsBarbeiro]);

    const tituloPrincipal = isBarbeariaMode
        ? 'Painel da barbearia'
        : isBarbeiroMode
            ? 'Painel do barbeiro'
            : 'Painel do cliente';

    const resumoLabel = isBarbeariaMode
        ? 'Rastreamento obrigatório da unidade'
        : 'Rastreamento automático obrigatório';

    return (
        <div className="rounded-2xl border border-orange-500/20 bg-gradient-to-br from-zinc-950 via-zinc-900 to-zinc-950 p-4 sm:p-5 shadow-lg shadow-black/40 space-y-4">
            <div className="flex items-center justify-between gap-4">
                <div>
                    <p className="text-[10px] sm:text-[11px] uppercase tracking-[0.15em] text-orange-400/70 font-semibold">Rastreamento ao vivo</p>
                    <h3 className="text-base sm:text-lg font-bold text-white mt-1">{tituloPrincipal}</h3>
                </div>
                <div className="rounded-full border border-orange-500/30 bg-orange-500/15 px-3 py-1.5 text-[10px] sm:text-[11px] font-bold text-orange-300">
                    Barber Move
                </div>
            </div>

            <div className="rounded-xl border border-orange-500/20 bg-orange-500/5 px-3 sm:px-4 py-2.5 text-xs sm:text-sm text-zinc-300">
                <span className="text-zinc-400">{resumoLabel}</span>
            </div>

            {destinoInfo?.endereco && (
                <div className="overflow-hidden rounded-2xl border border-orange-500/20 bg-zinc-950/50">
                    <MapEmbed endereco={destinoInfo.endereco} nome={destinoInfo.nome || 'Barbearia'} height="240px" />
                    <div className="border-t border-orange-500/20 bg-zinc-900/40 p-3 sm:p-4 text-xs sm:text-sm text-zinc-300 space-y-2">
                        <div className="flex items-start justify-between gap-3 flex-col sm:flex-row">
                            <div className="min-w-0">
                                <p className="font-bold text-white text-sm truncate">{destinoInfo.nome || 'Barbearia'}</p>
                                <p className="text-zinc-400 text-xs truncate mt-1">{destinoInfo.endereco}</p>
                            </div>
                            {distanciaBackend != null && (
                                <div className="rounded-lg border border-orange-500/30 bg-orange-500/10 px-3 py-2 text-center shrink-0 w-full sm:w-auto">
                                    <p className="text-[10px] text-orange-300/80">Distância</p>
                                    <p className="font-bold text-orange-300 text-base mt-0.5">{Number(distanciaBackend).toFixed(2)} km</p>
                                </div>
                            )}
                        </div>
                        {tempoEstimadoAtual != null && (
                            <div className="flex items-center justify-between text-[11px] text-zinc-400">
                                <span>ETA local</span>
                                <span className="font-semibold text-orange-300">~ {tempoEstimadoAtual} min</span>
                            </div>
                        )}
                    </div>
                </div>
            )}

            <div className="grid gap-2">
                {isClienteMode && coordsBarbeiro && coordsBarbearia && (
                    <TrackingMapEmbed
                        origem={coordsBarbeiro}
                        destino={coordsBarbearia}
                        titulo="Barbeiro para barbearia"
                        subtitulo={
                            distanciaBackend != null
                                ? `Distancia: ${Number(distanciaBackend).toFixed(2)} km`
                                : 'Aguardando distancia da API'
                        }
                        height="200px"
                    />
                )}

                {isBarbeiroMode && coordsCliente && coordsBarbearia && (
                    <TrackingMapEmbed
                        origem={coordsCliente}
                        destino={coordsBarbearia}
                        titulo="Cliente para barbearia"
                        subtitulo={
                            distanciaBackend != null
                                ? `Distancia: ${Number(distanciaBackend).toFixed(2)} km`
                                : 'Aguardando distancia da API'
                        }
                        height="200px"
                    />
                )}

                {isBarbeariaMode && coordsCliente && coordsBarbearia && (
                    <TrackingMapEmbed
                        origem={coordsCliente}
                        destino={coordsBarbearia}
                        titulo="Cliente para barbearia"
                        subtitulo={
                            distanciaBackend != null
                                ? `Distancia: ${Number(distanciaBackend).toFixed(2)} km`
                                : 'Aguardando distancia da API'
                        }
                        height="200px"
                    />
                )}
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs sm:text-sm">
                <div className="rounded-lg border border-orange-500/20 bg-orange-500/5 p-3 sm:p-4">
                    <p className="text-zinc-400 text-xs uppercase tracking-wide font-semibold">{isBarbeariaMode ? 'Barbearia' : 'Sua localização'}</p>
                    <p className="mt-2 text-base sm:text-lg font-bold text-white">
                        {posicaoAtual?.latitude != null ? `${posicaoAtual.latitude.toFixed(5)}, ${posicaoAtual.longitude.toFixed(5)}` : 'GPS parado'}
                    </p>
                    <p className="text-zinc-400 text-xs mt-1">
                        {posicaoAtual ? '✓ Localizacao obrigatoria ativa' : 'Aguardando permissao de localizacao'}
                    </p>
                </div>
                <div className="rounded-lg border border-blue-500/20 bg-blue-500/5 p-3 sm:p-4">
                    <p className="text-zinc-400 text-xs uppercase tracking-wide font-semibold">Destino</p>
                    <p className="mt-2 text-base sm:text-lg font-bold text-white">
                        {distanciaBackend != null ? `${Number(distanciaBackend).toFixed(2)} km` : '—'}
                    </p>
                    <p className="text-zinc-400 text-xs mt-1">
                        {etaBackend != null ? `ETA ~${etaBackend} min` : 'ETA —'}
                    </p>
                </div>
            </div>

            {isBarbeariaMode && agendamentos.length > 0 && (
                <div className="space-y-2">
                    {agendamentos.slice(0, 3).map((agendamento) => (
                        <div key={agendamento.id} className="rounded-xl border border-zinc-800 bg-zinc-900/70 p-3 text-xs text-zinc-300 space-y-1">
                            <div className="flex items-center justify-between gap-2">
                                <div className="min-w-0">
                                    <p className="font-bold text-white truncate">{agendamento.nome_cliente || agendamento.cliente_nome || 'Cliente'}</p>
                                    <p className="text-zinc-500 truncate">{agendamento.nome_barbeiro || agendamento.barbeiro_nome || 'Freelancer'}</p>
                                </div>
                                <div className="text-right shrink-0">
                                    <p className="text-orange-300 font-bold uppercase">{(agendamento.status || '').toString()}</p>
                                </div>
                            </div>
                            <div className="grid grid-cols-2 gap-2 text-[11px]">
                                <div className="rounded-lg bg-zinc-950/60 p-2 border border-zinc-800">
                                    <p className="text-zinc-500">Cliente → Barbearia</p>
                                    <p className="font-semibold text-white">
                                        {agendamento.cliente_distancia_ate_barbearia_km != null ? `${Number(agendamento.cliente_distancia_ate_barbearia_km).toFixed(2)} km` : '—'}
                                    </p>
                                    <p className="text-zinc-400">
                                        {agendamento.cliente_eta_ate_barbearia_min != null ? `~ ${agendamento.cliente_eta_ate_barbearia_min} min` : '—'}
                                    </p>
                                </div>
                                <div className="rounded-lg bg-zinc-950/60 p-2 border border-zinc-800">
                                    <p className="text-zinc-500">Freelancer → Barbearia</p>
                                    <p className="font-semibold text-white">
                                        {agendamento.freelancer_distancia_ate_barbearia_km != null ? `${Number(agendamento.freelancer_distancia_ate_barbearia_km).toFixed(2)} km` : '—'}
                                    </p>
                                    <p className="text-zinc-400">
                                        {agendamento.freelancer_eta_ate_barbearia_min != null ? `~ ${agendamento.freelancer_eta_ate_barbearia_min} min` : '—'}
                                    </p>
                                </div>
                            </div>
                        </div>
                    ))}
                </div>
            )}

            {resumo?.cliente_nome && !isBarbeariaMode && (
                <div className="rounded-xl border border-zinc-800 bg-zinc-900/60 px-3 py-2 text-xs text-zinc-300">
                    <span className="text-zinc-500">Atendimento atual: </span>
                    <span className="font-semibold text-white">{resumo.cliente_nome}</span>
                </div>
            )}

            <div className="rounded-xl border border-emerald-500/20 bg-emerald-500/10 px-3 py-2 text-[11px] font-semibold text-emerald-200">
                {isClienteMode
                    ? 'Localizacao obrigatoria ativa para o cliente.'
                    : isBarbeiroMode
                        ? 'Localizacao obrigatoria ativa para o barbeiro.'
                        : 'Localizacao obrigatoria ativa para a barbearia.'}
            </div>
        </div>
    );
}
