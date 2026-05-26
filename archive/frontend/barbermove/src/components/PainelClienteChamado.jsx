import React from 'react';
import MapaRastreamento from './MapaRastreamento';

const STATUS_PENDENTE = 'pendente';
const STATUS_LIBERADO = new Set(['aceito', 'confirmado', 'em_atendimento']);

/**
 * PainelClienteChamado: Visão do cliente
 * - Mostra "Aguardando aceite..." enquanto PENDENTE
 * - Mostra mapa e coordenadas quando CONFIRMADO+
 */
export default function PainelClienteChamado({ 
  chamadoId, 
  status, 
  mostrarMapa, 
  coordenadas 
}) {
  const statusNormalizado = String(status || '').toLowerCase();
  const aguardandoAceite = statusNormalizado === STATUS_PENDENTE || !STATUS_LIBERADO.has(statusNormalizado);

  if (aguardandoAceite || !mostrarMapa) {
    return (
      <div className="mx-auto w-full max-w-[430px] rounded-[1.5rem] border border-zinc-800/80 bg-zinc-950/90 p-5 text-center shadow-2xl shadow-black/30">
        <div className="mb-4">
          <span className="inline-flex items-center rounded-full border border-orange-500/20 bg-orange-500/10 px-3 py-1 text-[10px] font-bold uppercase tracking-[0.2em] text-orange-300">
            Rastreamento pendente
          </span>
          <h3 className="mt-3 text-lg font-black text-white">Aguardando o barbeiro</h3>
          <p className="mt-2 text-sm leading-relaxed text-zinc-300">
            Seu pedido foi enviado. O mapa aparecerá assim que ele aceitar o atendimento.
          </p>
        </div>

        <div className="mx-auto h-10 w-10 animate-spin rounded-full border-2 border-orange-500 border-t-transparent" />
      </div>
    );
  }

  // Mapa habilitado: barbeiro aceitou o chamado
  return (
    <div className="mx-auto w-full max-w-[430px] space-y-4">
      <div className="rounded-[1.5rem] border border-emerald-500/20 bg-emerald-500/10 px-4 py-3 text-sm leading-relaxed text-emerald-100 shadow-lg shadow-black/20">
        ✓ Barbeiro aceitou seu chamado! Veja a localização em tempo real:
      </div>

      {coordenadas && (
        <div className="overflow-hidden rounded-[1.5rem] border border-zinc-800/80 bg-zinc-950/90 shadow-2xl shadow-black/30">
          <MapaRastreamento
            clienteLat={coordenadas.cliente_lat}
            clienteLon={coordenadas.cliente_lon}
            barbeirLat={coordenadas.barbeiro_lat}
            barbeirLon={coordenadas.barbeiro_lon}
            chamadoId={chamadoId}
          />
        </div>
      )}
    </div>
  );
}
