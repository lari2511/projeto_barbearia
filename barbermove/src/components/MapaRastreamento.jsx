import React, { useEffect, useRef } from 'react';

/**
 * MapaRastreamento: Exibe mapa em tempo real do cliente e barbeiro
 * Usa coordenadas GPS do agendamento ativo
 */
export default function MapaRastreamento({
  clienteLat,
  clienteLon,
  barbeirLat,
  barbeirLon,
  chamadoId
}) {
  const mapContainer = useRef(null);
  const map = useRef(null);

  useEffect(() => {
    if (!mapContainer.current || !clienteLat || !clienteLon) {
      return;
    }

    // Tentar carregar Leaflet se disponível, senão mostrar versão simples
    const loadMap = async () => {
      try {
        // Se leaflet estiver disponível globalmente
        if (window.L) {
          const L = window.L;
          
          if (map.current) {
            map.current.remove();
          }

          // Inicializar mapa centrado no cliente
          map.current = L.map(mapContainer.current).setView(
            [clienteLat, clienteLon],
            15
          );

          // Tile layer
          L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
            attribution: '© OpenStreetMap contributors',
            maxZoom: 19,
          }).addTo(map.current);

          // Marcador do cliente
          L.marker([clienteLat, clienteLon], {
            icon: L.divIcon({
              className: 'custom-marker-client',
              html: '📍 Cliente',
              iconSize: [80, 30],
              iconAnchor: [40, 30],
            }),
          }).addTo(map.current);

          // Marcador do barbeiro (se disponível)
          if (barbeirLat && barbeirLon) {
            L.marker([barbeirLat, barbeirLon], {
              icon: L.divIcon({
                className: 'custom-marker-barber',
                html: '💇 Barbeiro',
                iconSize: [80, 30],
                iconAnchor: [40, 30],
              }),
            }).addTo(map.current);

            // Desenhar linha entre cliente e barbeiro
            L.polyline(
              [[clienteLat, clienteLon], [barbeirLat, barbeirLon]],
              { color: 'blue', weight: 2, opacity: 0.7 }
            ).addTo(map.current);
          }
        } else {
          // Fallback: mostrar tabela simples se Leaflet não disponível
          mapContainer.current.innerHTML = `
            <div style="padding: 20px; background: #f5f5f5; border-radius: 8px;">
              <h4>Coordenadas do Serviço</h4>
              <table style="width: 100%; border-collapse: collapse;">
                <tr style="border-bottom: 1px solid #ddd;">
                  <td style="padding: 8px; font-weight: bold;">Cliente</td>
                  <td style="padding: 8px;">${clienteLat.toFixed(4)}, ${clienteLon.toFixed(4)}</td>
                </tr>
                ${barbeirLat && barbeirLon ? `
                <tr>
                  <td style="padding: 8px; font-weight: bold;">Barbeiro</td>
                  <td style="padding: 8px;">${barbeirLat.toFixed(4)}, ${barbeirLon.toFixed(4)}</td>
                </tr>
                ` : ''}
              </table>
              <p style="font-size: 12px; color: #666; margin-top: 10px;">
                Mapa será exibido quando Leaflet estiver disponível
              </p>
            </div>
          `;
        }
      } catch (err) {
        console.error('Erro ao carregar mapa:', err);
      }
    };

    loadMap();

    return () => {
      if (map.current) {
        map.current.remove();
        map.current = null;
      }
    };
  }, [clienteLat, clienteLon, barbeirLat, barbeirLon]);

  return (
    <div
      ref={mapContainer}
      className="bm-map-surface w-full h-[400px] rounded-lg border border-zinc-800 mb-5 bg-zinc-900/40"
    />
  );
}
