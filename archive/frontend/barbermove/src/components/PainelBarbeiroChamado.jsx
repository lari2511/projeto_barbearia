import React, { useState } from 'react';
import MapaRastreamento from './MapaRastreamento';

const STATUS_PENDENTE = 'pendente';
const STATUS_LIBERADO = new Set(['aceito', 'confirmado', 'em_atendimento']);

/**
 * PainelBarbeiroChamado: Visão do barbeiro
 * - Mostra botão "Aceitar Chamado" quando PENDENTE
 * - Mostra mapa após CONFIRMADO
 */
export default function PainelBarbeiroChamado({ 
  chamadoId, 
  status, 
  mostrarMapa, 
  coordenadas,
  onAceito 
}) {
  const [loading, setLoading] = useState(false);
  const [erro, setErro] = useState(null);
  const statusNormalizado = String(status || '').toLowerCase();
  const aguardandoAceite = statusNormalizado === STATUS_PENDENTE;
  const mapaLiberado = STATUS_LIBERADO.has(statusNormalizado) && mostrarMapa;

  const handleAceitar = async () => {
    setLoading(true);
    setErro(null);

    try {
      const token = localStorage.getItem('access_token');
      if (!token) {
        throw new Error('Token não encontrado. Faça login novamente.');
      }

      const { getApiBaseUrl } = await import('../utils/api');
      const API_BASE = import.meta.env.VITE_API_URL?.trim() || getApiBaseUrl();
      const resp = await fetch(
        `${API_BASE}/api/v1/agendamento/${chamadoId}/aceitar`,
        {
          method: 'PATCH',
          headers: {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json',
          },
        }
      );

      if (!resp.ok) {
        const errData = await resp.json();
        throw new Error(errData.detail || 'Falha ao aceitar chamado');
      }

      console.log('✓ Chamado aceito com sucesso!');
      
      // Aguardar WebSocket notificar e atualizar status
      // Ou chamar callback para recarregar status
      if (onAceito) {
        setTimeout(() => onAceito(), 500);
      }
    } catch (err) {
      console.error('❌ Erro ao aceitar:', err);
      setErro(err.message);
    } finally {
      setLoading(false);
    }
  };

  // Se ainda PENDENTE: mostrar botão de aceite
  if (aguardandoAceite) {
    return (
      <div className="p-5 bg-zinc-900 rounded-2xl m-5 border border-zinc-800">
        <h3 className="text-white">Novo Chamado: Cliente aguardando</h3>
        <p className="mb-5 text-zinc-400">Aceite para liberar o rastreamento.</p>

        {erro && (
          <div className="bg-rose-900 text-rose-200 p-3 rounded mb-4">❌ {erro}</div>
        )}

        <button
          onClick={handleAceitar}
          disabled={loading}
          className={`w-full px-4 py-3 rounded-md font-bold ${loading ? 'opacity-60 cursor-not-allowed' : ''}`}
          style={{ background: 'linear-gradient(135deg, var(--brand-orange), #ea580c)' }}
        >
          {loading ? '⏳ Aceitando...' : '✓ Aceitar Serviço'}
        </button>
      </div>
    );
  }

  // Se ACEITO/CONFIRMADO+: mostrar mapa e coordenadas
  if (mapaLiberado) {
    return (
      <div className="p-5">
        <div className="bg-zinc-800 text-white p-3 rounded mb-5 border border-zinc-700">✓ Chamado aceito! Veja a localização do cliente em tempo real:</div>

        {coordenadas && (
          <MapaRastreamento
            clienteLat={coordenadas.cliente_lat}
            clienteLon={coordenadas.cliente_lon}
            barbeirLat={coordenadas.barbeiro_lat}
            barbeirLon={coordenadas.barbeiro_lon}
            chamadoId={chamadoId}
          />
        )}
      </div>
    );
  }

  return <div className="p-5 text-white">Carregando rastreamento...</div>;
}
