import React, { useEffect, useRef, useState } from 'react';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';

// Custom icons
const createBarbershopIcon = () => {
  return L.divIcon({
    className: 'custom-barbershop-icon',
    html: `
      <div style="
        background: linear-gradient(135deg, #f97316, #ea580c);
        border: 3px solid #fff;
        border-radius: 50%;
        width: 40px;
        height: 40px;
        display: flex;
        align-items: center;
        justify-content: center;
        box-shadow: 0 4px 12px rgba(249, 115, 22, 0.5);
        animation: pulse-barbershop 2s ease-in-out infinite;
      ">
        <span style="font-size: 20px;">💈</span>
      </div>
      <style>
        @keyframes pulse-barbershop {
          0%, 100% { transform: scale(1); box-shadow: 0 4px 12px rgba(249, 115, 22, 0.5); }
          50% { transform: scale(1.1); box-shadow: 0 6px 20px rgba(249, 115, 22, 0.8); }
        }
      </style>
    `,
    iconSize: [40, 40],
    iconAnchor: [20, 20],
  });
};

const createWalkingIcon = (isMoving = false) => {
  const animation = isMoving ? 'walk-animation 0.5s steps(2) infinite' : 'none';
  return L.divIcon({
    className: 'custom-walking-icon',
    html: `
      <div style="
        background: linear-gradient(135deg, #3b82f6, #2563eb);
        border: 3px solid #fff;
        border-radius: 50%;
        width: 36px;
        height: 36px;
        display: flex;
        align-items: center;
        justify-content: center;
        box-shadow: 0 4px 12px rgba(59, 130, 246, 0.5);
        animation: ${animation};
      ">
        <span style="font-size: 18px;">🚶</span>
      </div>
      <style>
        @keyframes walk-animation {
          0% { transform: translateX(-2px) rotate(-5deg); }
          50% { transform: translateX(2px) rotate(5deg); }
          100% { transform: translateX(-2px) rotate(-5deg); }
        }
      </style>
    `,
    iconSize: [36, 36],
    iconAnchor: [18, 18],
  });
};

const createRouteLine = (color = '#3b82f6') => {
  return {
    color: color,
    weight: 4,
    opacity: 0.7,
    dashArray: '10, 10',
    lineCap: 'round',
  };
};

export default function TrackingMapRealtime({
  origem,
  destino,
  titulo = 'Rota em tempo real',
  subtitulo,
  height = '300px',
  isMoving = false,
}) {
  const mapRef = useRef(null);
  const mapInstanceRef = useRef(null);
  const markerRef = useRef(null);
  const destinationMarkerRef = useRef(null);
  const routeLineRef = useRef(null);
  const [isLoaded, setIsLoaded] = useState(false);

  const latOrigem = Number(origem?.lat);
  const lonOrigem = Number(origem?.lon);
  const latDestino = Number(destino?.lat);
  const lonDestino = Number(destino?.lon);

  const possuiCoords = [latOrigem, lonOrigem, latDestino, lonDestino].every((value) => 
    Number.isFinite(value)
  );

  useEffect(() => {
    if (!possuiCoords || !mapRef.current) return;

    // Initialize map
    if (!mapInstanceRef.current) {
      mapInstanceRef.current = L.map(mapRef.current).setView([latOrigem, lonOrigem], 16);

      // Add OpenStreetMap tiles
      L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '© OpenStreetMap contributors',
        maxZoom: 19,
      }).addTo(mapInstanceRef.current);

      setIsLoaded(true);
    }

    // Remove existing markers and route
    if (markerRef.current) {
      mapInstanceRef.current.removeLayer(markerRef.current);
    }
    if (destinationMarkerRef.current) {
      mapInstanceRef.current.removeLayer(destinationMarkerRef.current);
    }
    if (routeLineRef.current) {
      mapInstanceRef.current.removeLayer(routeLineRef.current);
    }

    // Add destination marker (barbershop)
    destinationMarkerRef.current = L.marker([latDestino, lonDestino], {
      icon: createBarbershopIcon(),
    }).addTo(mapInstanceRef.current);

    // Add origin marker (walking person)
    markerRef.current = L.marker([latOrigem, lonOrigem], {
      icon: createWalkingIcon(isMoving),
    }).addTo(mapInstanceRef.current);

    // Draw route line
    routeLineRef.current = L.polyline(
      [[latOrigem, lonOrigem], [latDestino, lonDestino]],
      createRouteLine('#3b82f6')
    ).addTo(mapInstanceRef.current);

    // Fit bounds to show both markers
    const bounds = L.latLngBounds([
      [latOrigem, lonOrigem],
      [latDestino, lonDestino],
    ]);
    mapInstanceRef.current.fitBounds(bounds, { padding: [50, 50] });

    return () => {
      if (mapInstanceRef.current) {
        mapInstanceRef.current.remove();
        mapInstanceRef.current = null;
      }
    };
  }, [latOrigem, lonOrigem, latDestino, lonDestino, possuiCoords, isMoving]);

  // Update marker position when origem changes
  useEffect(() => {
    if (!mapInstanceRef.current || !markerRef.current || !possuiCoords) return;

    markerRef.current.setLatLng([latOrigem, lonOrigem]);
    
    // Update route line
    if (routeLineRef.current) {
      routeLineRef.current.setLatLngs([
        [latOrigem, lonOrigem],
        [latDestino, lonDestino],
      ]);
    }

    // Update walking icon animation based on movement
    if (isMoving) {
      markerRef.current.setIcon(createWalkingIcon(true));
    } else {
      markerRef.current.setIcon(createWalkingIcon(false));
    }
  }, [latOrigem, lonOrigem, latDestino, lonDestino, isMoving, possuiCoords]);

  if (!possuiCoords) {
    return (
      <div className="w-full rounded-xl overflow-hidden border border-zinc-800 bg-zinc-950/70">
        <div className="flex items-center justify-between gap-2 p-3 border-b border-zinc-800 bg-zinc-900/60">
          <div className="flex items-center gap-2">
            <span className="text-orange-400">📍</span>
            <p className="text-xs font-bold text-zinc-200">{titulo}</p>
          </div>
        </div>
        <div className="p-4 text-center text-zinc-400 text-sm">
          Aguardando coordenadas GPS...
        </div>
      </div>
    );
  }

  return (
    <div className="w-full rounded-xl overflow-hidden border border-zinc-800 bg-zinc-950/70">
      <div className="flex items-center justify-between gap-2 p-3 border-b border-zinc-800 bg-zinc-900/60">
        <div className="flex items-center gap-2 min-w-0">
          <span className="text-orange-400">📍</span>
          <p className="text-xs font-bold text-zinc-200 truncate">{titulo}</p>
        </div>
        <span className="text-[10px] px-2 py-1 rounded-full border border-blue-500/30 bg-blue-500/10 text-blue-300 shrink-0">
          {isMoving ? '🚶 Em movimento' : '⏸️ Parado'}
        </span>
      </div>

      <div 
        ref={mapRef} 
        style={{ height: height || '300px', width: '100%' }}
        className="bg-zinc-900"
      />

      {subtitulo && (
        <div className="p-2 text-[11px] text-zinc-400 border-t border-zinc-800 truncate">
          {subtitulo}
        </div>
      )}
    </div>
  );
}
