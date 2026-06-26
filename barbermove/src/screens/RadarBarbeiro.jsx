/**
 * TELA DE RADAR DO BARBEIRO (WEB)
 * Versão adaptada para web usando geolocation e layout do painel.
 */

import React, { useEffect, useState, useRef } from 'react';

const RadarBarbeiro = ({ navigation }) => {
  const [radarOnline, setRadarOnline] = useState(false);
  const [carregando, setCarregando] = useState(false);
  const [mensagemStatus, setMensagemStatus] = useState('Radar inativo');
  const [localizacaoAtual, setLocalizacaoAtual] = useState(null);
  const [numSolicitacoes] = useState(0);
  const [tempoUltimaAtualizacao, setTempoUltimaAtualizacao] = useState(null);
  const watchIdRef = useRef(null);

  const defaultHost = typeof window !== 'undefined' ? window.location.hostname : 'localhost';
  const defaultProtocol = typeof window !== 'undefined' && window.location.protocol === 'https:' ? 'https' : 'http';
  const API_URL = import.meta.env.VITE_API_URL || `${defaultProtocol}://${defaultHost}:8000`;

  useEffect(() => {
    return () => {
      if (watchIdRef.current && navigator.geolocation) navigator.geolocation.clearWatch(watchIdRef.current);
    };
  }, []);

  const iniciarRadar = async () => {
    if (!navigator.geolocation) { console.log('[alert]','Geolocalização não disponível'); return; }
    setCarregando(true);
    try {
      setMensagemStatus('🟢 Radar ativo - Procurando clientes');
      setTempoUltimaAtualizacao(new Date());
      const id = navigator.geolocation.watchPosition(async (pos) => {
        const c = pos.coords;
        setLocalizacaoAtual(c);
        setTempoUltimaAtualizacao(new Date());
        try {
          const token = localStorage.getItem('token');
          await fetch(`${API_URL}/api/v1/on-demand/atualizar-localizacao`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', Authorization: token ? `Bearer ${token}` : '' },
            body: JSON.stringify({ latitude: c.latitude, longitude: c.longitude }),
          });
        } catch (e) { console.error(e); }
      }, (err) => { console.error(err); }, { enableHighAccuracy: true, maximumAge: 5000 });
      watchIdRef.current = id;
      setRadarOnline(true);
      console.log('[alert]','Radar iniciado');
    } catch (e) {
      console.error(e);
      console.log('[alert]','Erro ao iniciar radar');
    }
    setCarregando(false);
  };

  const pararRadar = async () => {
    setCarregando(true);
    try {
      if (watchIdRef.current && navigator.geolocation) navigator.geolocation.clearWatch(watchIdRef.current);
      watchIdRef.current = null;
      setRadarOnline(false);
      setMensagemStatus('🔴 Radar inativo - Offline');
    } catch (e) { console.error(e); }
    setCarregando(false);
  };

  const alternarRadar = async () => {
    if (!radarOnline) await iniciarRadar(); else await pararRadar();
  };

  return (
    <div className="min-h-screen bg-black text-white flex justify-center bm-app-frame">
      <div className="w-full max-w-[430px] min-h-screen p-4 bm-shell-content app-container client-dashboard-shell">
        <div className="bm-header-gradient flex items-center justify-between">
          <button onClick={() => navigation?.goBack()} className="text-white">←</button>
          <h2 className="font-bold">Radar Online</h2>
          <div style={{ width: 28 }} />
        </div>

        <div className="mt-6 space-y-4">
          <div className="p-4 bg-zinc-900 border border-zinc-800 rounded">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className={`w-3 h-3 rounded-full ${radarOnline ? 'bg-green-500' : 'bg-zinc-500'}`} />
                <div className="font-semibold">{radarOnline ? '🟢 ONLINE' : '🔴 OFFLINE'}</div>
              </div>
              <button onClick={alternarRadar} className="px-4 py-2 bg-orange-500 rounded">{carregando ? '...' : (radarOnline ? 'Desligar' : 'Ligar')}</button>
            </div>
            <p className="mt-3 text-zinc-400">{mensagemStatus}</p>
          </div>

          {localizacaoAtual && (
            <div className="p-4 bg-zinc-900 border border-zinc-800 rounded">
              <div className="font-semibold">📍 Sua Localização</div>
              <div className="text-sm text-zinc-400">Latitude: {localizacaoAtual.latitude.toFixed(4)}</div>
              <div className="text-sm text-zinc-400">Longitude: {localizacaoAtual.longitude.toFixed(4)}</div>
              <div className="text-sm text-zinc-400">Atualizado há {Math.round((new Date() - tempoUltimaAtualizacao) / 1000)}s</div>
            </div>
          )}

          <div className="p-4 bg-zinc-900 border border-zinc-800 rounded">
            <div className="font-semibold">📱 Solicitações</div>
            <div className="flex items-center gap-4 mt-2">
              <div className="text-4xl">🔔</div>
              <div>
                <div className="text-2xl font-bold">{numSolicitacoes}</div>
                <div className="text-sm text-zinc-400">{numSolicitacoes === 0 ? 'Nenhuma solicitação' : `${numSolicitacoes} solicitações`}</div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default RadarBarbeiro;
