import { useEffect, useState } from 'react';
import PainelClienteChamado from './PainelClienteChamado';
import PainelBarbeiroChamado from './PainelBarbeiroChamado';
import { useRealTimeUpdates } from '../hooks/useRealTimeUpdates';
import { getApiBaseUrl } from '../utils/api';

/**
 * TelaDoChamado: Gerencia o fluxo de aceite de chamado
 * - Cliente vê "Aguardando aceite..." até barbeiro aceitar
 * - Barbeiro vê botão "Aceitar Chamado"
 * - Ambos recebem notificação via WebSocket quando aceite ocorre
 * - Mapa só aparece após status = CONFIRMADO
 */
export default function TelaDoChamado({ chamadoId, userType, token: tokenProp, API_URL: apiUrlProp, barbearia, minhaPosicao }) {
  const [status, setStatus] = useState(null);
  const [mostrarMapa, setMostrarMapa] = useState(false);
  const [coordenadas, setCoordenadas] = useState({});
  const [loading, setLoading] = useState(true);
  
  const token = tokenProp || localStorage.getItem('access_token');
  const API_BASE = apiUrlProp || import.meta.env.VITE_API_URL?.trim() || getApiBaseUrl();

  // 1. Carregar status inicial
  useEffect(() => {
    const carregarStatus = async () => {
      try {
        const resp = await fetch(
          `${API_BASE}/api/v1/agendamento/${chamadoId}/status-rastreamento`
        );
        if (!resp.ok) throw new Error('Falha ao carregar status');
        
        const data = await resp.json();
        setStatus(data.status);
        setMostrarMapa(data.mostrar_mapa);
        
        if (data.cliente_lat && data.cliente_lon) {
          setCoordenadas({
            cliente_lat: data.cliente_lat,
            cliente_lon: data.cliente_lon,
            barbeiro_lat: data.barbeiro_lat,
            barbeiro_lon: data.barbeiro_lon,
          });
        }
      } catch (err) {
        console.error('❌ Erro ao carregar status:', err);
      } finally {
        setLoading(false);
      }
    };

    carregarStatus();
  }, [chamadoId, API_BASE]);

  // 2. Conectar WebSocket via hook e escutar 'chamado_aceito'
  useRealTimeUpdates(token, (msg) => {
    // Se receber evento 'chamado_aceito' com este chamado_id
    if (msg.type === 'chamado_aceito' && msg.chamado_id === chamadoId) {
      console.log('✓ Chamado aceito via WebSocket!', msg);
      
      // Recarregar status do servidor
      setTimeout(async () => {
        try {
          const resp = await fetch(
            `${API_BASE}/api/v1/agendamento/${chamadoId}/status-rastreamento`
          );
          if (resp.ok) {
            const data = await resp.json();
            setStatus(data.status);
            setMostrarMapa(data.mostrar_mapa);
            
            if (data.cliente_lat && data.cliente_lon) {
              setCoordenadas({
                cliente_lat: data.cliente_lat,
                cliente_lon: data.cliente_lon,
                barbeiro_lat: data.barbeiro_lat,
                barbeiro_lon: data.barbeiro_lon,
              });
            }
          }
        } catch (err) {
          console.error('Erro ao recarregar status:', err);
        }
      }, 500);
    }
  });

  // 3. Callback para quando barbeiro aceita
  const handleChamadoAceito = async () => {
    try {
      const resp = await fetch(
        `${API_BASE}/api/v1/agendamento/${chamadoId}/status-rastreamento`
      );
      if (resp.ok) {
        const data = await resp.json();
        setStatus(data.status);
        setMostrarMapa(data.mostrar_mapa);
        
        if (data.cliente_lat && data.cliente_lon) {
          setCoordenadas({
            cliente_lat: data.cliente_lat,
            cliente_lon: data.cliente_lon,
            barbeiro_lat: data.barbeiro_lat,
            barbeiro_lon: data.barbeiro_lon,
          });
        }
      }
    } catch (err) {
      console.error('Erro ao recarregar status:', err);
    }
  };

  if (loading) {
    return (
      <div className="p-5 text-center">
        <p>Carregando...</p>
      </div>
    );
  }

  // Renderizar painel apropriado conforme userType
  if (userType === 'cliente') {
    return (
      <PainelClienteChamado
        chamadoId={chamadoId}
        status={status}
        mostrarMapa={mostrarMapa}
        coordenadas={coordenadas}
      />
    );
  } else if (userType === 'barbeiro') {
    return (
      <PainelBarbeiroChamado
        chamadoId={chamadoId}
        status={status}
        mostrarMapa={mostrarMapa}
        coordenadas={coordenadas}
        onAceito={handleChamadoAceito}
        token={token}
        API_URL={API_BASE}
        barbearia={barbearia}
        minhaPosicao={minhaPosicao}
      />
    );
  }

  return <div>Tipo de usuário inválido</div>;
}
