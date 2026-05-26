import React from 'react';
import { MapPin } from 'lucide-react';

/**
 * Componente para exibir Google Maps embarcado
 * Exibe um mapa com o endereço fornecido
 */
export default function MapEmbed({ endereco, nome = "Local", height = "250px" }) {
  if (!endereco) return null;

  // Construir URL do Google Maps
  const query = `${nome} ${endereco}`;
  const mapaUrl = `https://maps.google.com/maps?q=${encodeURIComponent(query)}&t=&z=15&ie=UTF8&iwloc=&output=embed`;

  return (
    <div className="map-wrapper mt-3">
      <div className="flex items-center gap-2 p-3 bg-zinc-900/50 border-b border-zinc-700">
        <MapPin size={16} className="text-orange-500" />
        <p className="text-xs font-bold text-zinc-400">Localização</p>
      </div>
      <iframe
        width="100%"
        height={height}
        src={mapaUrl}
        frameBorder="0"
        scrolling="no"
        marginHeight="0"
        marginWidth="0"
        title="Mapa do Local"
        className="block w-full h-full border-0"
      />
      <div className="p-3 bg-zinc-900/30 text-xs text-zinc-400">
        <p className="truncate">{endereco}</p>
      </div>
    </div>
  );
}
