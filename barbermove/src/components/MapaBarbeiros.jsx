import { useEffect, useRef } from 'react';
import 'leaflet/dist/leaflet.css';
import L from 'leaflet';
import { renderToString } from 'react-dom/server';
import { UserRound, Scissors, Store } from 'lucide-react';

// Corrige bug dos ícones no Webpack/Vite
delete L.Icon.Default.prototype._getIconUrl;
L.Icon.Default.mergeOptions({
  iconUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon.png',
  iconRetinaUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon-2x.png',
  shadowUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png',
});

const iconCliente = L.divIcon({
  className: 'custom-marker-zone',
  html: renderToString(
    <div style={{ position: 'relative', width: 34, height: 34 }}>
      <div style={{ position: 'absolute', inset: 0, background: 'rgba(59,130,246,.22)', borderRadius: '999px', animation: 'bmPing 1.6s ease-in-out infinite' }} />
      <div style={{ position: 'absolute', inset: 4, background: 'linear-gradient(135deg,#3b82f6,#2563eb)', border: '2px solid #fff', borderRadius: '999px', display: 'flex', alignItems: 'center', justifyContent: 'center', boxShadow: '0 4px 12px rgba(59,130,246,.55)', color: '#fff' }}>
        <UserRound size={14} strokeWidth={2.4} />
      </div>
    </div>
  ),
  iconSize: [34, 34],
  iconAnchor: [17, 17],
});

const iconBarbeiro = L.divIcon({
  className: 'custom-marker-zone',
  html: renderToString(
    <div style={{ background: 'linear-gradient(135deg,#f59e0b,#ea580c)', border: '2px solid #fff', borderRadius: '999px', width: 28, height: 28, display: 'flex', alignItems: 'center', justifyContent: 'center', boxShadow: '0 4px 10px rgba(245,158,11,.55)', color: '#111827' }}>
      <Scissors size={13} strokeWidth={2.4} />
    </div>
  ),
  iconSize: [28, 28],
  iconAnchor: [14, 14],
});

const criarIconeBarbeiroPorStatus = (barbeiro) => {
  const status = barbeiro?.presente_em_local
    ? {
        bg: 'linear-gradient(135deg,#22c55e,#15803d)',
        color: '#ecfeff',
        shadow: '0 4px 10px rgba(34,197,94,.55)',
      }
    : (barbeiro?.disponivel || barbeiro?.online_regiao)
      ? {
          bg: 'linear-gradient(135deg,#f59e0b,#ea580c)',
          color: '#111827',
          shadow: '0 4px 10px rgba(245,158,11,.55)',
        }
      : {
          bg: 'linear-gradient(135deg,#6b7280,#374151)',
          color: '#e5e7eb',
          shadow: '0 4px 10px rgba(55,65,81,.55)',
        };

  return L.divIcon({
    className: 'custom-marker-zone',
    html: renderToString(
      <div style={{ background: status.bg, border: '2px solid #fff', borderRadius: '999px', width: 28, height: 28, display: 'flex', alignItems: 'center', justifyContent: 'center', boxShadow: status.shadow, color: status.color }}>
        <Scissors size={13} strokeWidth={2.4} />
      </div>
    ),
    iconSize: [28, 28],
    iconAnchor: [14, 14],
  });
};

const iconVagaRelampago = L.divIcon({
  className: 'custom-marker-zone',
  html: renderToString(
    <div style={{ background: 'linear-gradient(135deg,#18181b,#0f172a)', border: '2px solid #f59e0b', borderRadius: 11, width: 30, height: 30, display: 'flex', alignItems: 'center', justifyContent: 'center', boxShadow: '0 4px 12px rgba(0,0,0,.45)', color: '#f59e0b' }}>
      <Store size={14} strokeWidth={2.3} />
    </div>
  ),
  iconSize: [30, 30],
  iconAnchor: [15, 30],
});

export default function MapaBarbeiros({ userLocation, barbeiros = [], vagasRelampago = [], onSelectBarbeiro, onSelectVagaRelampago }) {
  const containerRef = useRef(null);
  const mapRef = useRef(null);

  useEffect(() => {
    if (!containerRef.current) return;

    const lat = userLocation?.latitude ?? -23.55;
    const lon = userLocation?.longitude ?? -46.63;

    if (!mapRef.current) {
      mapRef.current = L.map(containerRef.current, { zoomControl: true }).setView([lat, lon], 14);
      L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '© OpenStreetMap',
        maxZoom: 19,
      }).addTo(mapRef.current);
    } else {
      mapRef.current.setView([lat, lon], 14);
    }

    const map = mapRef.current;

    // Limpar marcadores antigos
    map.eachLayer(layer => {
      if (layer instanceof L.Marker) map.removeLayer(layer);
    });

    // Marcador do cliente
    if (userLocation) {
      L.marker([lat, lon], { icon: iconCliente })
        .addTo(map)
        .bindPopup('<b>Você está aqui</b>');
    }

    // Marcadores dos barbeiros
    barbeiros.forEach(b => {
      const bLat = Number(b.latitude);
      const bLon = Number(b.longitude);
      if (!bLat || !bLon) return;

      const statusLabel = b?.presente_em_local
        ? (b?.barbearia_atual_nome ? `PRESENTE em ${b.barbearia_atual_nome}` : 'PRESENTE')
        : ((b?.disponivel || b?.online_regiao) ? 'ONLINE' : 'OFFLINE');

      L.marker([bLat, bLon], { icon: criarIconeBarbeiroPorStatus(b) })
        .addTo(map)
        .bindPopup(`<b>${b.nome}</b><br/>Status: ${statusLabel}<br/>${b.distancia_km != null ? `${b.distancia_km} km` : ''}`)
        .on('click', () => onSelectBarbeiro && onSelectBarbeiro(b));
    });

    // Marcadores das vagas relampago
    vagasRelampago.forEach((vaga) => {
      const vLat = Number(vaga?.barbearia_latitude);
      const vLon = Number(vaga?.barbearia_longitude);
      if (!Number.isFinite(vLat) || !Number.isFinite(vLon)) return;

      L.marker([vLat, vLon], { icon: iconVagaRelampago })
        .addTo(map)
        .bindPopup(`<b>Vaga relampago</b><br/>${vaga?.barbearia_nome || 'Barbearia'}<br/>ETA: ${vaga?.eta_min_usuario_atual ?? '-'} min`)
        .on('click', () => onSelectVagaRelampago && onSelectVagaRelampago(vaga));
    });
  }, [userLocation, barbeiros, vagasRelampago, onSelectBarbeiro, onSelectVagaRelampago]);

  useEffect(() => {
    return () => {
      if (mapRef.current) {
        mapRef.current.remove();
        mapRef.current = null;
      }
    };
  }, []);

  return (
    <div className="rounded-2xl overflow-hidden border border-zinc-800 mb-3">
      <style>{'@keyframes bmPing{0%,100%{transform:scale(1);opacity:.7}50%{transform:scale(1.5);opacity:0}}'}</style>
      <div className="flex items-center gap-2 px-3 py-2 bg-zinc-900 text-xs text-zinc-400">
        <span className="inline-flex items-center justify-center w-5 h-5 rounded-full bg-blue-500 text-white"><UserRound size={12} /></span> Você
        <span className="inline-flex items-center justify-center w-5 h-5 rounded-full bg-amber-500 text-zinc-900 ml-2"><Scissors size={12} /></span> Online
        <span className="inline-flex items-center justify-center w-5 h-5 rounded-full bg-green-600 text-white ml-2"><Scissors size={12} /></span> Presente
        <span className="inline-flex items-center justify-center w-5 h-5 rounded-full bg-zinc-600 text-zinc-100 ml-2"><Scissors size={12} /></span> Offline
        <span className="inline-flex items-center justify-center w-5 h-5 rounded-md bg-zinc-800 border border-amber-500 text-amber-500 ml-2"><Store size={11} /></span> Barbearia
        <span className="ml-auto text-zinc-500">Toque no marcador para selecionar</span>
      </div>
      <div ref={containerRef} style={{ height: '260px', width: '100%' }} />
    </div>
  );
}
