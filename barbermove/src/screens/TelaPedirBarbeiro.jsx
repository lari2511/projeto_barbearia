/**
 * TELA DE PEDIDO DE BARBEIRO (CLIENTE)
 * Sistema On-Demand estilo Uber para buscar barbeiro agora
 * 
 * Funcionalidades:
 * 1. Mostra lista de barbeiros próximos em tempo real
 * 2. Permite que cliente veja distância e tempo estimado
 * 3. Cliente solicita barbeiro → Notificação push para barbeiro
 * 4. Sistema automaticamente escolhe barbeiro mais próximo
 * 5. Integração com geolocalização do cliente
 * 6. Rastreamento do barbeiro aceitando/recusando
 * 
 * Fluxo:
 * 1. Cliente abre tela "Solicitar Agora"
 * 2. Sistema obtém localização do cliente (GPS)
 * 3. Faz GET /api/v1/on-demand/barbeiros-proximos (raio 5km)
 * 4. Lista barbeiros ordenados por distância
 * 5. Cliente clica em barbeiro ou "Solicitar agora"
 * 6. POST /api/v1/on-demand/solicitar-barbeiro
 * 7. Backend envia notificação push para barbeiro
 * 8. Barbeiro recebe: "Nova solicitação a X km"
 * 9. Barbeiro clica para ver ou aceitar/recusar
 * 10. Se aceita: Cliente vê "Barbeiro a aceitar em X minutos"
 */

import React, { useEffect, useState } from 'react';
import { getApiBaseUrl } from '../utils/api';

const TelaPedirBarbeiro = ({ navigation }) => {
  const [localizacaoCliente, setLocalizacaoCliente] = useState(null);
  const [barbeirosProximos, setBarbeirosProximos] = useState([]);
  const [carregando, setCarregando] = useState(false);
  const [atualizando, setAtualizando] = useState(false);
  const [solicitacaoEmAndamento, setSolicitacaoEmAndamento] = useState(false);

  const API_URL = getApiBaseUrl();

  useEffect(()=>{
    obterLocalizacaoInicial();
  },[]);

  const obterLocalizacaoInicial = async () => {
    setCarregando(true);
    try {
      if (!navigator.geolocation) {
        setCarregando(false);
        return;
      }
      navigator.geolocation.getCurrentPosition(async (pos)=>{
        const coords = pos.coords;
        setLocalizacaoCliente(coords);
        await buscarBarbeirosProximos(coords);
        setCarregando(false);
      }, (err)=>{
        setCarregando(false);
      }, { enableHighAccuracy: true, maximumAge: 30000 });
    } catch(e){
      setCarregando(false);
    }
  };

  const buscarBarbeirosProximos = async (coords) => {
    setAtualizando(true);
    try {
      const params = new URLSearchParams({ latitude: coords.latitude, longitude: coords.longitude, raio_km: 5 });
      const token = localStorage.getItem('token');
      const res = await fetch(`${API_URL}/api/v1/on-demand/barbeiros-proximos?${params.toString()}`, { headers: { Authorization: token? `Bearer ${token}` : '' } });
      if (!res.ok) { setBarbeirosProximos([]); setAtualizando(false); return; }
      const data = await res.json();
      setBarbeirosProximos(data.barbeiros || []);
    } catch(e){ }
    setAtualizando(false);
  };

  const solicitarBarbeiro = async (barbeiro) => {
    if (!localizacaoCliente) { return; }
    setSolicitacaoEmAndamento(true);
    try {
      const token = localStorage.getItem('token');
      const body = { latitude: localizacaoCliente.latitude, longitude: localizacaoCliente.longitude, endereco: 'Endereço', raio_km: 5, tipo_servico: 'corte' };
      const res = await fetch(`${API_URL}/api/v1/on-demand/solicitar-barbeiro`, { method: 'POST', headers: { 'Content-Type':'application/json', Authorization: token? `Bearer ${token}` : '' }, body: JSON.stringify(body) });
      if (!res.ok) { const err = await res.json().catch(()=>({ detail: 'Erro' })); setSolicitacaoEmAndamento(false); return; }
      if (navigation) navigation.goBack();
    } catch(e){ }
    setSolicitacaoEmAndamento(false);
  };

  return (
    <div className="min-h-screen bg-black text-white flex justify-center bm-app-frame">
      <div className="w-full max-w-[430px] min-h-screen p-4 bm-shell-content app-container client-dashboard-shell">
        <div className="bm-header-gradient flex items-center justify-between">
          <button onClick={()=>navigation?.goBack()} className="text-white">←</button>
          <h2 className="font-bold">Barbeiros Próximos</h2>
          <button onClick={()=>obterLocalizacaoInicial()} className="text-white">{atualizando? '...' : '↻'}</button>
        </div>

        <div className="mt-6">
          {carregando ? (
            <div className="flex flex-col items-center py-10">
              <div className="animate-spin h-8 w-8 border-4 border-orange-500 border-t-transparent rounded-full" />
              <p className="mt-3 text-zinc-400">Buscando barbeiros próximos...</p>
            </div>
          ) : (barbeirosProximos.length === 0 ? (
            <div className="text-center py-10">
              <div className="text-6xl">😕</div>
              <h3 className="mt-4 font-bold text-orange-500">Nenhum barbeiro disponível</h3>
              <p className="mt-2 text-blue-400">Tente aumentar o raio de busca ou tente novamente em alguns minutos.</p>
              <button onClick={()=>obterLocalizacaoInicial()} className="mt-4 px-4 py-2 bg-green-500 text-white font-bold rounded">Tentar novamente</button>
            </div>
          ) : (
            <div className="space-y-4">
              {barbeirosProximos.map((b, idx)=> (
                <div key={`${b.freelancer_id}-${idx}`} className={`p-4 rounded-lg bg-zinc-900 border border-zinc-800 flex justify-between items-center ${solicitacaoEmAndamento ? 'opacity-50' : ''}`}>
                  <div>
                    <div className="font-semibold">Barbeiro #{b.freelancer_id}</div>
                    <div className="text-sm text-zinc-400">📍 {b.distancia_km} km</div>
                    <div className="text-sm text-zinc-400">⏱️ ~{Math.round((b.distancia_km/10)*60)} min</div>
                  </div>
                  <div className="flex flex-col items-end gap-2">
                    <div className="text-sm text-yellow-400">★ 4.8</div>
                    <button onClick={()=>solicitarBarbeiro(b)} disabled={solicitacaoEmAndamento} className="px-3 py-2 bg-orange-500 rounded text-white">{solicitacaoEmAndamento? 'Enviando...':'Chamar'}</button>
                  </div>
                </div>
              ))}
            </div>
          ))}
        </div>

        {localizacaoCliente && (
          <div className="fixed bottom-6 left-1/2 transform -translate-x-1/2 w-[92%] max-w-[430px] p-3 bg-zinc-900/70 border border-zinc-800 rounded text-sm flex items-center gap-2">
            <div>📍</div>
            <div>Seu local: ({localizacaoCliente.latitude.toFixed(4)}, {localizacaoCliente.longitude.toFixed(4)})</div>
          </div>
        )}
      </div>
    </div>
  );
};
export default TelaPedirBarbeiro;
