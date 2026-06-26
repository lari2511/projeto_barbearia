import { useEffect, useRef, useState, useCallback } from 'react';
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
const etaMin = (km) => Math.max(1, Math.round(km * 60 / 25)); // ~25 km/h caminhando/moto

const iconCliente = () => L.divIcon({
  className: '',
  html: `
    <div style="position:relative;width:44px;height:44px">
      <div style="
        position:absolute;inset:0;background:rgba(59,130,246,0.25);
        border-radius:50%;animation:ping 1.4s ease-in-out infinite;
      "></div>
      <div style="
        position:absolute;inset:4px;background:linear-gradient(135deg,#3b82f6,#2563eb);
        border:3px solid white;border-radius:50%;
        display:flex;align-items:center;justify-content:center;
        box-shadow:0 4px 14px rgba(59,130,246,0.6);
        font-size:18px;
      ">🚶</div>
    </div>
    <style>
      @keyframes ping{0%,100%{transform:scale(1);opacity:.7}50%{transform:scale(1.6);opacity:0}}
    </style>
  `,
  iconSize: [44, 44],
  iconAnchor: [22, 22],
});

const iconBarbearia = () => L.divIcon({
  className: '',
  html: `
    <div style="
      background:linear-gradient(135deg,#f97316,#ea580c);
      border:3px solid white;border-radius:12px;
      width:44px;height:44px;
      display:flex;align-items:center;justify-content:center;
      box-shadow:0 4px 14px rgba(249,115,22,0.6);
      font-size:22px;
    ">💈</div>
  `,
  iconSize: [44, 44],
  iconAnchor: [22, 44],
});

const iconBarbeiro = () => L.divIcon({
  className: '',
  html: `
    <div style="
      background:linear-gradient(135deg,#22c55e,#16a34a);
      border:3px solid white;border-radius:50%;
      width:38px;height:38px;
      display:flex;align-items:center;justify-content:center;
      box-shadow:0 4px 14px rgba(34,197,94,0.6);
      font-size:18px;
    ">✂️</div>
  `,
  iconSize: [38, 38],
  iconAnchor: [19, 19],
});

export default function MapaUberBarbeiro({ chamadoId, token, API_URL, minhaPosicao, barbearia }) {
  const containerRef = useRef(null);
  const mapRef = useRef(null);
  const marcadorClienteRef = useRef(null);
  const marcadorBarbeariaRef = useRef(null);
  const marcadorBarbeiroRef = useRef(null);
  const rotaRef = useRef(null);
  const prevClientePos = useRef(null);

  const [coordsCliente, setCoordsCliente] = useState(null);
  const [distKm, setDistKm] = useState(null);
  const [eta, setEta] = useState(null);
  const [statusCliente, setStatusCliente] = useState('Aguardando...');

  // Polling: busca posição do cliente no backend a cada 3s
  const fetchTracking = useCallback(async () => {
    if (!chamadoId || !token) return;
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
        if (data.cliente_distancia_ate_barbearia_km != null) {
          setDistKm(Number(data.cliente_distancia_ate_barbearia_km));
          setEta(data.cliente_eta_ate_barbearia_min ?? etaMin(Number(data.cliente_distancia_ate_barbearia_km)));
        }
        setStatusCliente('Online');
      }
    } catch (_) {}
  }, [chamadoId, token, API_URL]);

  useEffect(() => {
    fetchTracking();
    const t = setInterval(fetchTracking, 3000);
    return () => clearInterval(t);
  }, [fetchTracking]);

  // Init mapa
  useEffect(() => {
    if (!containerRef.current || mapRef.current) return;
    const lat = barbearia?.latitude ?? minhaPosicao?.latitude ?? -23.55;
    const lon = barbearia?.longitude ?? minhaPosicao?.longitude ?? -46.63;
    mapRef.current = L.map(containerRef.current, { zoomControl: false }).setView([lat, lon], 15);
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
      attribution: '© OpenStreetMap',
      maxZoom: 19,
    }).addTo(mapRef.current);
    L.control.zoom({ position: 'bottomright' }).addTo(mapRef.current);
    return () => {
      if (mapRef.current) { mapRef.current.remove(); mapRef.current = null; }
    };
  }, []);

  // Marcador da barbearia (fixo)
  useEffect(() => {
    if (!mapRef.current || !barbearia?.latitude) return;
    if (marcadorBarbeariaRef.current) marcadorBarbeariaRef.current.remove();
    marcadorBarbeariaRef.current = L.marker(
      [Number(barbearia.latitude), Number(barbearia.longitude)],
      { icon: iconBarbearia() }
    ).addTo(mapRef.current).bindPopup(`<b>💈 ${barbearia.nome || 'Barbearia'}</b><br/>${barbearia.endereco || ''}`);
  }, [barbearia?.latitude, barbearia?.longitude]);

  // Marcador do barbeiro (você)
  useEffect(() => {
    if (!mapRef.current || !minhaPosicao?.latitude) return;
    const pos = [Number(minhaPosicao.latitude), Number(minhaPosicao.longitude)];
    if (marcadorBarbeiroRef.current) {
      marcadorBarbeiroRef.current.setLatLng(pos);
    } else {
      marcadorBarbeiroRef.current = L.marker(pos, { icon: iconBarbeiro() })
        .addTo(mapRef.current)
        .bindPopup('<b>✂️ Você (Barbeiro)</b>');
    }
  }, [minhaPosicao?.latitude, minhaPosicao?.longitude]);

  // Marcador do cliente + rota animada
  useEffect(() => {
    if (!mapRef.current || !coordsCliente) return;
    const pos = [coordsCliente.lat, coordsCliente.lon];

    if (marcadorClienteRef.current) {
      marcadorClienteRef.current.setLatLng(pos);
      marcadorClienteRef.current.setIcon(iconCliente());
    } else {
      marcadorClienteRef.current = L.marker(pos, { icon: iconCliente() })
        .addTo(mapRef.current)
        .bindPopup('<b>🚶 Cliente</b><br/>Em movimento');
    }

    // Rota cliente → barbearia
    if (barbearia?.latitude) {
      const bPos = [Number(barbearia.latitude), Number(barbearia.longitude)];
      if (rotaRef.current) rotaRef.current.setLatLngs([pos, bPos]);
      else {
        rotaRef.current = L.polyline([pos, bPos], {
          color: '#3b82f6', weight: 4, opacity: 0.75,
          dashArray: '12 8', lineCap: 'round',
        }).addTo(mapRef.current);
      }
    }

    // Ajusta bounds para mostrar cliente + barbearia
    if (barbearia?.latitude) {
      const bPos = [Number(barbearia.latitude), Number(barbearia.longitude)];
      mapRef.current.fitBounds(L.latLngBounds([pos, bPos]), { padding: [60, 60], maxZoom: 16 });
    }

    prevClientePos.current = coordsCliente;
  }, [coordsCliente?.lat, coordsCliente?.lon, barbearia?.latitude]);

  const distLabel = distKm != null ? `${distKm.toFixed(2)} km` : '—';
  const etaLabel = eta != null ? `${eta} min` : '—';

  return (
    <div className="rounded-2xl overflow-hidden border border-zinc-800 bg-zinc-950 shadow-xl">
      {/* Header estilo Uber */}
      <div className="flex items-center justify-between px-4 py-3 bg-zinc-900 border-b border-zinc-800">
        <div>
          <p className="text-[10px] uppercase tracking-widest text-zinc-500 font-bold">Rastreamento ao vivo</p>
          <p className="text-sm font-black text-white mt-0.5">Cliente a caminho</p>
        </div>
        <span className={`text-[10px] font-bold px-2 py-1 rounded-full border ${
          statusCliente === 'Online'
            ? 'bg-green-500/15 text-green-300 border-green-500/30'
            : 'bg-zinc-800 text-zinc-400 border-zinc-700'
        }`}>
          {statusCliente === 'Online' ? '🟢 Online' : '⏳ Aguardando'}
        </span>
      </div>

      {/* Mapa */}
      <div ref={containerRef} style={{ height: '320px', width: '100%' }} />

      {/* Footer estilo Uber com km e minutos */}
      <div className="grid grid-cols-3 divide-x divide-zinc-800 bg-zinc-900 border-t border-zinc-800">
        <div className="flex flex-col items-center py-3 px-2">
          <span className="text-[10px] text-zinc-500 uppercase tracking-wide">Distância</span>
          <span className="text-lg font-black text-white mt-0.5">{distLabel}</span>
        </div>
        <div className="flex flex-col items-center py-3 px-2">
          <span className="text-[10px] text-zinc-500 uppercase tracking-wide">Chegada</span>
          <span className="text-lg font-black text-orange-400 mt-0.5">{etaLabel}</span>
        </div>
        <div className="flex flex-col items-center py-3 px-2 gap-1">
          <span className="text-[10px] text-zinc-500 uppercase tracking-wide">Legenda</span>
          <div className="flex items-center gap-1 text-[10px] text-zinc-400"><span className="text-base">🚶</span> Cliente</div>
          <div className="flex items-center gap-1 text-[10px] text-zinc-400"><span className="text-base">💈</span> Barbearia</div>
        </div>
      </div>
    </div>
  );
}
