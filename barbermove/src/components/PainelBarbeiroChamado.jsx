import { useState, useEffect, useRef, useCallback } from 'react';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';

const toRad = (v) => (v * Math.PI) / 180;
const haversineKm = (lat1, lon1, lat2, lon2) => {
  const R = 6371;
  const dLat = toRad(lat2 - lat1);
  const dLon = toRad(lon2 - lon1);
  const a = Math.sin(dLat / 2) ** 2 + Math.cos(toRad(lat1)) * Math.cos(toRad(lat2)) * Math.sin(dLon / 2) ** 2;
  return R * 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
};
const etaMin = (km) => Math.max(1, Math.round((km / 25) * 60));

// ── Ícones ──────────────────────────────────────────────────────────────────
const mkIconCliente = () => L.divIcon({
  className: '',
  html: `<div style="position:relative;width:48px;height:48px">
    <div style="position:absolute;inset:0;background:rgba(59,130,246,.3);border-radius:50%;animation:uberpingc 1.4s ease-in-out infinite"></div>
    <div style="position:absolute;inset:5px;background:linear-gradient(135deg,#3b82f6,#1d4ed8);border:3px solid #fff;border-radius:50%;display:flex;align-items:center;justify-content:center;font-size:20px;box-shadow:0 4px 16px rgba(59,130,246,.7)">🚶</div>
  </div>
  <style>@keyframes uberpingc{0%,100%{transform:scale(1);opacity:.6}50%{transform:scale(1.8);opacity:0}}</style>`,
  iconSize: [48, 48], iconAnchor: [24, 24],
});

const mkIconBarbearia = () => L.divIcon({
  className: '',
  html: `<div style="background:linear-gradient(135deg,#f97316,#dc2626);border:3px solid #fff;border-radius:14px;width:48px;height:48px;display:flex;align-items:center;justify-content:center;font-size:24px;box-shadow:0 6px 20px rgba(249,115,22,.7)">💈</div>`,
  iconSize: [48, 48], iconAnchor: [24, 48],
});

const mkIconBarbeiro = () => L.divIcon({
  className: '',
  html: `<div style="background:linear-gradient(135deg,#22c55e,#15803d);border:3px solid #fff;border-radius:50%;width:42px;height:42px;display:flex;align-items:center;justify-content:center;font-size:20px;box-shadow:0 4px 14px rgba(34,197,94,.6)">✂️</div>`,
  iconSize: [42, 42], iconAnchor: [21, 21],
});

// ── Mapa ─────────────────────────────────────────────────────────────────────
function MapaUber({ coordsCliente, barbearia, minhaPosicao }) {
  const containerRef = useRef(null);
  const mapRef = useRef(null);
  const mClienteRef = useRef(null);
  const mBarbeariaRef = useRef(null);
  const mBarbeiroRef = useRef(null);
  const rotaRef = useRef(null);

  // Init
  useEffect(() => {
    if (!containerRef.current || mapRef.current) return;
    const lat = barbearia?.latitude ?? minhaPosicao?.latitude ?? -23.55;
    const lon = barbearia?.longitude ?? minhaPosicao?.longitude ?? -46.63;
    mapRef.current = L.map(containerRef.current, { zoomControl: false }).setView([lat, lon], 15);
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
      attribution: '© OpenStreetMap', maxZoom: 19,
    }).addTo(mapRef.current);
    L.control.zoom({ position: 'bottomright' }).addTo(mapRef.current);
    return () => { if (mapRef.current) { mapRef.current.remove(); mapRef.current = null; } };
  }, []);

  // Barbearia (fixo)
  useEffect(() => {
    if (!mapRef.current || !barbearia?.latitude) return;
    if (mBarbeariaRef.current) mBarbeariaRef.current.remove();
    mBarbeariaRef.current = L.marker(
      [Number(barbearia.latitude), Number(barbearia.longitude)],
      { icon: mkIconBarbearia() }
    ).addTo(mapRef.current)
      .bindPopup(`<b>💈 ${barbearia.nome || 'Barbearia'}</b><br/><span style="font-size:12px">${barbearia.endereco || ''}</span>`);
  }, [barbearia?.latitude, barbearia?.longitude]);

  // Barbeiro (você)
  useEffect(() => {
    if (!mapRef.current || !minhaPosicao?.latitude) return;
    const pos = [Number(minhaPosicao.latitude), Number(minhaPosicao.longitude)];
    if (mBarbeiroRef.current) mBarbeiroRef.current.setLatLng(pos);
    else {
      mBarbeiroRef.current = L.marker(pos, { icon: mkIconBarbeiro() })
        .addTo(mapRef.current).bindPopup('<b>✂️ Você</b>');
    }
  }, [minhaPosicao?.latitude, minhaPosicao?.longitude]);

  // Cliente + rota animada
  useEffect(() => {
    if (!mapRef.current || !coordsCliente) return;
    const pos = [coordsCliente.lat, coordsCliente.lon];

    if (mClienteRef.current) {
      mClienteRef.current.setLatLng(pos);
      mClienteRef.current.setIcon(mkIconCliente());
    } else {
      mClienteRef.current = L.marker(pos, { icon: mkIconCliente() })
        .addTo(mapRef.current).bindPopup('<b>🚶 Cliente</b>');
    }

    if (barbearia?.latitude) {
      const bPos = [Number(barbearia.latitude), Number(barbearia.longitude)];
      if (rotaRef.current) rotaRef.current.setLatLngs([pos, bPos]);
      else rotaRef.current = L.polyline([pos, bPos], {
        color: '#3b82f6', weight: 5, opacity: .8, dashArray: '12 8', lineCap: 'round',
      }).addTo(mapRef.current);

      mapRef.current.fitBounds(L.latLngBounds([pos, bPos]), { padding: [70, 70], maxZoom: 16 });
    }
  }, [coordsCliente?.lat, coordsCliente?.lon]);

  return <div ref={containerRef} className="bm-map-surface" style={{ height: '320px', width: '100%' }} />;
}

// ── Painel principal ──────────────────────────────────────────────────────────
const STATUS_PENDENTE = 'pendente';
const STATUS_LIBERADO = new Set(['aceito', 'confirmado', 'em_atendimento']);

export default function PainelBarbeiroChamado({
  chamadoId, status, mostrarMapa, coordenadas, onAceito,
  token, API_URL, barbearia, minhaPosicao,
}) {
  const [loading, setLoading] = useState(false);
  const [erro, setErro] = useState(null);
  const [coordsCliente, setCoordsCliente] = useState(null);
  const [distKm, setDistKm] = useState(null);
  const [eta, setEta] = useState(null);
  const [clienteOnline, setClienteOnline] = useState(false);
  const [elapsedSec, setElapsedSec] = useState(0);

  const statusNorm = String(status || '').toLowerCase();
  const aguardandoAceite = statusNorm === STATUS_PENDENTE;
  const mapaLiberado = STATUS_LIBERADO.has(statusNorm) && mostrarMapa;

  // Timer de chamado ativo
  useEffect(() => {
    if (!mapaLiberado) return;
    const t = setInterval(() => setElapsedSec(s => s + 1), 1000);
    return () => clearInterval(t);
  }, [mapaLiberado]);

  const tempoFormatado = `${String(Math.floor(elapsedSec / 60)).padStart(2, '0')}:${String(elapsedSec % 60).padStart(2, '0')}`;

  // Polling posição do cliente
  const fetchTracking = useCallback(async () => {
    if (!chamadoId || !token || !API_URL) return;
    try {
      const res = await fetch(`${API_URL}/api/v1/tracking/chamados/${chamadoId}/eta`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!res.ok) return;
      const data = await res.json();
      const c = data?.coordenadas_cliente;
      if (c?.lat != null && c?.lon != null) {
        const pos = { lat: Number(c.lat), lon: Number(c.lon) };
        setCoordsCliente(pos);
        setClienteOnline(true);

        // Calcular distância cliente → barbearia
        if (barbearia?.latitude) {
          const km = haversineKm(pos.lat, pos.lon, Number(barbearia.latitude), Number(barbearia.longitude));
          setDistKm(km);
          setEta(data.cliente_eta_ate_barbearia_min ?? etaMin(km));
        }
      }
    } catch (_) {}
  }, [chamadoId, token, API_URL, barbearia?.latitude]);

  useEffect(() => {
    if (!mapaLiberado) return;
    fetchTracking();
    const t = setInterval(fetchTracking, 3000);
    return () => clearInterval(t);
  }, [mapaLiberado, fetchTracking]);

  // Coordenadas fallback (props passadas direto)
  useEffect(() => {
    if (coordenadas?.cliente_lat && !coordsCliente) {
      setCoordsCliente({ lat: Number(coordenadas.cliente_lat), lon: Number(coordenadas.cliente_lon) });
    }
  }, [coordenadas]);

  // Aceitar chamado
  const handleAceitar = async () => {
    setLoading(true);
    setErro(null);
    try {
      const tk = token || localStorage.getItem('access_token');
      const base = API_URL || (await import('../utils/api')).getApiBaseUrl();
      const res = await fetch(`${base}/api/v1/chamados/${chamadoId}/aceitar`, {
        method: 'PUT',
        headers: { Authorization: `Bearer ${tk}`, 'Content-Type': 'application/json' },
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || 'Falha ao aceitar chamado');
      }
      if (onAceito) setTimeout(onAceito, 400);
    } catch (err) {
      setErro(err.message);
    } finally {
      setLoading(false);
    }
  };

  // ── Pendente ──
  if (aguardandoAceite) {
    return (
      <div className="rounded-2xl border border-amber-500/30 bg-amber-500/10 p-4 space-y-3">
        <div className="flex items-center gap-2">
          <span className="text-2xl">🔔</span>
          <div>
            <p className="text-sm font-black text-white">Novo chamado!</p>
            <p className="text-xs text-zinc-400">Cliente aguardando sua confirmação</p>
          </div>
        </div>
        {erro && <p className="text-xs text-red-400 bg-red-500/10 rounded-lg p-2">{erro}</p>}
        <button
          onClick={handleAceitar}
          disabled={loading}
          className="w-full bg-gradient-to-r from-orange-500 to-orange-600 hover:from-orange-600 hover:to-orange-700 disabled:opacity-50 text-white font-black rounded-xl py-3 text-sm transition-all"
        >
          {loading ? '⏳ Aceitando...' : '✅ Aceitar Serviço'}
        </button>
      </div>
    );
  }

  // ── Mapa liberado ──
  if (mapaLiberado) {
    return (
      <div className="rounded-2xl overflow-hidden border border-zinc-800 bg-zinc-950 shadow-2xl">
        {/* Header estilo Uber */}
        <div className="flex items-center justify-between px-4 py-3 bg-zinc-900 border-b border-zinc-800">
          <div>
            <p className="text-[10px] uppercase tracking-widest text-zinc-500 font-bold">Rastreamento ao vivo</p>
            <p className="text-sm font-black text-white mt-0.5">Cliente a caminho da barbearia</p>
          </div>
          <div className="flex flex-col items-end gap-1">
            <span className={`text-[10px] font-bold px-2 py-1 rounded-full border ${
              clienteOnline
                ? 'bg-green-500/15 text-green-300 border-green-500/30'
                : 'bg-zinc-800 text-zinc-400 border-zinc-700'
            }`}>
              {clienteOnline ? '🟢 Cliente online' : '⏳ Aguardando GPS'}
            </span>
            <span className="text-[10px] text-zinc-500 font-mono">⏱ {tempoFormatado}</span>
          </div>
        </div>

        {/* Legenda */}
        <div className="flex items-center gap-4 px-4 py-2 bg-zinc-950 border-b border-zinc-800/50 text-[11px] text-zinc-400">
          <span>🚶 Cliente</span>
          <span>💈 Barbearia</span>
          <span>✂️ Você</span>
          <span className="ml-auto text-zinc-600">Atualiza a cada 3s</span>
        </div>

        {/* Mapa */}
        <MapaUber
          coordsCliente={coordsCliente}
          barbearia={barbearia}
          minhaPosicao={minhaPosicao}
        />

        {/* Footer estilo Uber: distância + ETA */}
        <div className="grid grid-cols-2 divide-x divide-zinc-800 bg-zinc-900 border-t border-zinc-800">
          <div className="flex flex-col items-center py-4 px-3">
            <span className="text-[10px] text-zinc-500 uppercase tracking-wide mb-1">Distância do cliente</span>
            <span className="text-2xl font-black text-white">
              {distKm != null ? `${distKm.toFixed(2)} km` : '—'}
            </span>
            <span className="text-[10px] text-zinc-500 mt-0.5">até a barbearia</span>
          </div>
          <div className="flex flex-col items-center py-4 px-3">
            <span className="text-[10px] text-zinc-500 uppercase tracking-wide mb-1">Chegada estimada</span>
            <span className="text-2xl font-black text-orange-400">
              {eta != null ? `${eta} min` : '—'}
            </span>
            <span className="text-[10px] text-zinc-500 mt-0.5">tempo estimado</span>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="p-4 text-center text-zinc-500 text-sm">
      Carregando rastreamento...
    </div>
  );
}
