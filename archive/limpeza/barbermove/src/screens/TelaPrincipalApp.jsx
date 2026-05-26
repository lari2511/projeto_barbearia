import React, { useState } from 'react';
import PainelLayout from '../components/PainelLayout';
import AppCard from '../components/AppCard';

export default function TelaPrincipalApp() {
  const [currentTab, setCurrentTab] = useState('inicio');

  return (
    <PainelLayout activeTab={currentTab} setActiveTab={setCurrentTab}>

      {/* Alerta de Nova Atualização no Topo */}
      <AppCard className="app-card flex-row justify-between items-center p-4">
        <div className="flex items-center gap-2">
          <span className="text-lg">🔔</span>
          <span className="text-sm font-bold">Nova atualização disponível!</span>
        </div>
        <button className="bg-transparent border-none text-white text-xl leading-none">×</button>
      </AppCard>

      {/* Card Principal: Chamado Ativo */}
      <AppCard className="app-card p-5 rounded-2xl">
        <div className="flex justify-between items-start">
          <div>
            <h2 className="card-title">Chamado ativo</h2>
            <p className="card-subtitle">ID: 36 — barba</p>
          </div>
          <div className="text-right">
            <p className="text-xs text-zinc-400">Status: em atendimento</p>
            <p className="text-sm font-bold text-orange-500">🔥 Taxa aplicada</p>
          </div>
        </div>
        
        <button className="bg-gradient-to-r from-orange-600 to-red-600 text-white font-extrabold text-base flex items-center justify-center rounded-2xl py-3.5 px-6 mt-4">
          Cancelar com taxa de R$ 8,00
        </button>
      </AppCard>

      {/* Card de Aviso de Cancelamento Expirado */}
      <AppCard className="app-card alert-danger p-4">
        <p className="card-title text-orange-500 text-sm">⚠️ Janela de cancelamento grátis expirou</p>
        <p className="text-sm text-zinc-200">Taxa de cancelamento: <span className="text-red-500">R$ 8,00</span></p>
      </AppCard>

      {/* Card Informativo com Texto Longo */}
      <AppCard className="app-card alert-warning p-5">
        <p className="text-sm text-zinc-200 leading-6">
          Como o freelancer já está presente na barbearia, o cancelamento tem taxa de R$ 8,00.
        </p>
        <p className="text-sm font-bold mt-2">Taxa de cancelamento: R$ 8,00</p>
      </AppCard>

      {/* Card do Rastreamento / Mapa */}
      <AppCard className="app-card p-0 overflow-hidden rounded-2xl">
        <div className="p-4">
          <p className="text-[11px] font-black uppercase tracking-wider text-zinc-400">RASTREAMENTO AO VIVO</p>
          <div className="flex justify-between items-center mt-2">
            <h3 className="card-title">Painel do cliente</h3>
            <span className="text-xs bg-zinc-800 px-2 py-1 rounded-lg">Barber Move</span>
          </div>
        </div>
        
        <div className="map-wrapper bg-zinc-900 h-48 flex items-center justify-center relative">
          <span className="text-sm text-zinc-400">📍 [Visualização do Mapa Integrado]</span>
          <div className="absolute bottom-2 left-2 bg-black/80 px-3 py-1 rounded-md text-xs text-zinc-200">
            🚶 Barbeiro para barbearia (Caminhada)
          </div>
        </div>
      </AppCard>

    </PainelLayout>
  );
}
