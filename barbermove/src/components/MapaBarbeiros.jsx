import { useEffect, useRef } from 'react';
import 'leaflet/dist/leaflet.css';
import L from 'leaflet';

// Corrige bug dos ícones no Webpack/Vite
delete L.Icon.Default.prototype._getIconUrl;
L.Icon.Default.mergeOptions({
  iconUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon.png',
  iconRetinaUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon-2x.png',
  shadowUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png',
});

const iconCliente = L.divIcon({
  className: '',
  html: `<div style="background:#f97316;border:2px solid white;border-radius:50%;width:18px;height:18px;box-shadow:0 2px 6px rgba(0,0,0,0.5)"></div>`,
  iconSize: [18, 18],
  iconAnchor: [9, 9],
});

const iconBarbeiro = L.divIcon({
  className: '',
  html: `<div style="background:#22c55e;border:2px solid white;border-radius:50%;width:14px;height:14px;box-shadow:0 2px 6px rgba(0,0,0,0.5)"></div>`,
  iconSize: [14, 14],
  iconAnchor: [7, 7],
});

const iconVagaRelampago = L.divIcon({
  className: '',
  html: `<div style="background:#ef4444;border:2px solid white;border-radius:50%;width:16px;height:16px;box-shadow:0 2px 8px rgba(239,68,68,0.6)"></div>`,
  iconSize: [16, 16],
  iconAnchor: [8, 8],
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

      L.marker([bLat, bLon], { icon: iconBarbeiro })
        .addTo(map)
        .bindPopup(`<b>${b.nome}</b><br/>${b.distancia_km != null ? `${b.distancia_km} km` : ''}`)
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
      <div className="flex items-center gap-2 px-3 py-2 bg-zinc-900 text-xs text-zinc-400">
        <span className="w-3 h-3 rounded-full bg-orange-500 inline-block" /> Você
        <span className="w-3 h-3 rounded-full bg-green-500 inline-block ml-2" /> Barbeiros
        <span className="w-3 h-3 rounded-full bg-red-500 inline-block ml-2" /> Vagas relâmpago
        <span className="ml-auto text-zinc-500">Toque no marcador para selecionar</span>
      </div>
      <div ref={containerRef} style={{ height: '260px', width: '100%' }} />
    </div>
  );
}
