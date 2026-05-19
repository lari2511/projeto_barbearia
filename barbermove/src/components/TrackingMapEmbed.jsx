import React from 'react';
import { MapPin } from 'lucide-react';

export default function TrackingMapEmbed({
  origem,
  destino,
  titulo = 'Rota em caminhada',
  subtitulo,
  height = '220px',
}) {
  const latOrigem = Number(origem?.lat);
  const lonOrigem = Number(origem?.lon);
  const latDestino = Number(destino?.lat);
  const lonDestino = Number(destino?.lon);

  const possuiCoords = [latOrigem, lonOrigem, latDestino, lonDestino].every((value) => Number.isFinite(value));
  if (!possuiCoords) return null;

  // f=d + dirflg=w forcando direcao em modo caminhada no embed do Google Maps.
  // Adiciona marcadores explícitos para origem (U) e destino (D) para garantir o "bonequinho" visível
  const markers = `&markers=size:mid%7Ccolor:blue%7Clabel:U%7C${latOrigem},${lonOrigem}&markers=size:mid%7Ccolor:red%7Clabel:D%7C${latDestino},${lonDestino}`;
  const rotaUrl = `https://maps.google.com/maps?output=embed&f=d&saddr=${latOrigem},${lonOrigem}&daddr=${latDestino},${lonDestino}&dirflg=w${markers}`;

  return (
    <div className="w-full rounded-xl overflow-hidden border border-zinc-800 bg-zinc-950/70">
      <div className="flex items-center justify-between gap-2 p-3 border-b border-zinc-800 bg-zinc-900/60">
        <div className="flex items-center gap-2 min-w-0">
          <MapPin size={14} className="text-orange-400 shrink-0" />
          <p className="text-xs font-bold text-zinc-200 truncate">{titulo}</p>
        </div>
        <span className="text-[10px] px-2 py-1 rounded-full border border-orange-500/30 bg-orange-500/10 text-orange-300 shrink-0">
          caminhada
        </span>
      </div>

      <iframe
        title={titulo}
        src={rotaUrl}
        width="100%"
        height={height}
        frameBorder="0"
        scrolling="no"
        marginHeight="0"
        marginWidth="0"
        style={{ border: 'none', display: 'block' }}
      />

      {subtitulo && (
        <div className="p-2 text-[11px] text-zinc-400 border-t border-zinc-800 truncate">{subtitulo}</div>
      )}
    </div>
  );
}
