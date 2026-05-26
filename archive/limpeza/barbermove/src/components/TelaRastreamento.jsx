import React from 'react';
import { MapaRastreamento } from './MapaRastreamento';
import ScreenWrapper from './ScreenWrapper';

export function TelaRastreamento({ chamadoId, dadosAgendamento, localizacao }) {
  return (
    <ScreenWrapper className="select-none">
      <div className="flex justify-between items-center mb-4 border-b border-zinc-900 pb-3">
        <h1 className="text-lg font-black tracking-tight text-white">Buscar Barbeiros</h1>
        <button className="text-zinc-500 hover:text-white transition-all">
          <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1" /></svg>
        </button>
      </div>

      <button className="flex items-center gap-2 text-zinc-400 text-xs mb-4 hover:text-white transition-all bg-transparent border-none cursor-pointer">
        <span>←</span> Voltar para barbearias
      </button>

      <div className="bg-[#1e1e24] rounded-2xl p-4 mb-4 flex justify-between items-center border border-zinc-800/40 shadow-lg">
        <div>
          <span className="text-xs text-zinc-500 block font-semibold">Barbeiro</span>
          <span className="text-base font-bold text-white mt-0.5 block">Lari</span>
        </div>
        <button className="bg-zinc-800 text-white text-xs font-bold px-4 py-2.5 rounded-xl border border-zinc-700/30 hover:bg-zinc-700 transition-all cursor-pointer">
          Ver perfil
        </button>
      </div>

      <div className="bg-[#0c1f14] border border-[#22c55e]/40 rounded-2xl p-4 mb-4 text-center">
        <h3 className="text-[#22c55e] text-xs font-black tracking-wider uppercase flex items-center justify-center gap-1.5">
          🚀 AGENDAMENTO EM TEMPO REAL
        </h3>
        <p className="text-zinc-200 text-xs font-bold mt-1.5">Lari aceitou o chamado!</p>
        <p className="text-[#22c55e] text-[11px] font-medium mt-0.5">Acompanhe o deslocamento no mapa abaixo</p>
      </div>

      <div className="bg-[#1e1e24] rounded-2xl overflow-hidden border border-zinc-800/50 shadow-xl mb-4 relative">
        <div className="w-full h-64 bg-zinc-900 relative">
          <MapaRastreamento agendamentoId={chamadoId} />
        </div>
      </div>

      <div className="bg-[#1e1e24] rounded-2xl p-4 border border-zinc-800/50 shadow-lg space-y-4">
        <div className="flex justify-between items-center pb-3 border-b border-zinc-800/60">
          <div>
            <span className="text-[11px] text-zinc-500 block font-semibold uppercase tracking-wider">Distância</span>
            <span className="text-base font-black text-white mt-0.5 block">{localizacao?.distancia || '0.01 km'}</span>
          </div>
          <div className="text-right">
            <span className="text-[11px] text-zinc-500 block font-semibold uppercase tracking-wider">Tempo Estimado</span>
            <span className="text-base font-black text-[#22c55e] mt-0.5 block">~1 min</span>
          </div>
        </div>

        <div className="space-y-3.5 pt-1 relative">
          <div className="absolute left-[5px] top-3 bottom-3 w-0.5 border-l border-dashed border-zinc-700"></div>

          <div className="flex items-start gap-3 relative z-10">
            <div className="w-2.5 h-2.5 rounded-full bg-zinc-500 mt-1 flex-shrink-0"></div>
            <div>
              <p className="text-[10px] text-zinc-500 uppercase font-bold tracking-wider">Sua Localização</p>
              <p className="text-xs font-semibold text-zinc-200">Rua Saturnino de Sousa, 790</p>
            </div>
          </div>

          <div className="flex items-start gap-3 relative z-10">
            <div className="w-2.5 h-2.5 rounded-full bg-[#f97316] mt-1 flex-shrink-0"></div>
            <div>
              <p className="text-[10px] text-[#f97316] uppercase font-bold tracking-wider">Destino (Barbearia)</p>
              <p className="text-xs font-semibold text-zinc-200">Rua Saturnino de Sousa, 796</p>
            </div>
          </div>
        </div>

        <div className="grid grid-cols-2 gap-3 pt-2">
          <button className="bg-[#f97316] hover:bg-orange-600 active:scale-[0.98] text-white font-bold text-xs py-3 rounded-xl transition-all shadow-md shadow-orange-600/10 text-center border-none cursor-pointer">
            Ver Rastreamento
          </button>
          <button className="bg-[#22c55e] hover:bg-emerald-600 active:scale-[0.98] text-white font-bold text-xs py-3 rounded-xl transition-all shadow-md shadow-emerald-600/10 text-center border-none cursor-pointer flex items-center justify-center gap-1">
            🚀 Chamar AGORA
          </button>
        </div>

        <button className="w-full bg-zinc-800/60 hover:bg-zinc-800 text-zinc-400 font-medium text-xs py-2.5 rounded-xl transition-all border border-zinc-700/20 cursor-pointer mt-1">
          Cancelar Chamado (Taxa: R$ 8,00)
        </button>
      </div>
    </ScreenWrapper>
  );
}

export default TelaRastreamento;
