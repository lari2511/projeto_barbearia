import { useEffect, useState, useRef, useCallback } from 'react';
import { getWsBaseUrl } from '../utils/api';

/**
 * Hook customizado para sincronização em tempo real via WebSocket
 * Conecta ao backend e notifica mudanças em agendamentos
 */
export function useRealTimeUpdates(token, onUpdate) {
  const wsRef = useRef(null);
  const [isConnected, setIsConnected] = useState(false);
  const reconnectTimeoutRef = useRef(null);

  useEffect(() => {
    if (!token) return;

    const connectWebSocket = () => {
      try {
        const WS_URL = import.meta.env.VITE_WS_URL?.trim() || getWsBaseUrl();
        const ws = new WebSocket(WS_URL);

        ws.onopen = () => {
          setIsConnected(true);
          
          // Enviar token para autenticação
          ws.send(JSON.stringify({ tipo: 'auth', token }));
        };

        ws.onmessage = (event) => {
          try {
            const msg = JSON.parse(event.data);

            // Notificar componentes quando há mudança
            if (msg.tipo === 'chamado_aceito' || msg.tipo === 'agendamento_atualizado') {
              if (onUpdate) {
                onUpdate(msg);
              }
            }
          } catch (_e) {
            // Erro ao processar mensagem
          }
        };

        ws.onerror = (_error) => {
          setIsConnected(false);
        };

        ws.onclose = () => {
          setIsConnected(false);
          
          // Reconectar em 5 segundos
          reconnectTimeoutRef.current = setTimeout(connectWebSocket, 5000);
        };

        wsRef.current = ws;
      } catch (_error) {
        setIsConnected(false);
      }
    };

    connectWebSocket();

    return () => {
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
      }
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, [token, onUpdate]);

  return isConnected;
}

/**
 * Hook para gerenciar lista de chamados com sincronização em tempo real
 * Atualiza lista sem fazer fetch completo
 */
export function useLiveJobs(token, apiUrl) {
  const [jobs, setJobs] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  // Buscar jobs inicialmente
  useEffect(() => {
    if (!token) return;

    const fetchJobs = async () => {
      setLoading(true);
      try {
        const res = await fetch(`${apiUrl}/api/v1/chamados/abertos`, {
          headers: { 'Authorization': `Bearer ${token}` }
        });
        if (!res.ok) throw new Error('Erro ao carregar chamados');
        const data = await res.json();
        setJobs(Array.isArray(data) ? data : []);
      } catch (err) {
        setError(err.message);
        setJobs([]);
      } finally {
        setLoading(false);
      }
    };

    fetchJobs();
    
    // Recarregar a cada 10 segundos como fallback
    const interval = setInterval(fetchJobs, 10000);
    return () => clearInterval(interval);
  }, [token, apiUrl]);

  // Sincronizar com WebSocket
  const isConnected = useRealTimeUpdates(token, (msg) => {
    if (msg.tipo === 'chamado_aceito') {
      // Remover chamado aceito da lista
      setJobs(prev => prev.filter(j => j.id !== msg.chamado_id));
    } else if (msg.tipo === 'novo_chamado') {
      // Adicionar novo chamado à lista
      setJobs(prev => [msg.chamado, ...prev]);
    }
  });

  return { jobs, loading, error, isConnected };
}

/**
 * Hook para monitorar um chamado específico em tempo real
 */
export function useWatchChamado(chamadoId, token, apiUrl) {
  const [chamado, setChamado] = useState(null);
  const [loading, setLoading] = useState(false);

  // Buscar estado inicial
  useEffect(() => {
    if (!chamadoId || !token) return;

    const fetchChamado = async () => {
      setLoading(true);
      try {
        const res = await fetch(`${apiUrl}/chamados/${chamadoId}`, {
          headers: { 'Authorization': `Bearer ${token}` }
        });
        if (!res.ok) throw new Error('Chamado não encontrado');
        const data = await res.json();
        setChamado(data);
      } catch (_err) {
        // Erro ao carregar chamado
      } finally {
        setLoading(false);
      }
    };

    fetchChamado();
  }, [chamadoId, token, apiUrl]);

  // Monitorar mudanças via WebSocket
  useRealTimeUpdates(token, (msg) => {
    if (msg.chamado_id === chamadoId) {
      if (msg.tipo === 'agendamento_atualizado') {
        setChamado(prev => ({ ...prev, status: msg.novo_status }));
      }
    }
  });

  return { chamado, loading };
}

/**
 * Hook para auto-refresh de lista com fallback em caso de desconexão
 */
export function useAutoRefreshList(token, apiUrl, endpoint, interval = 15000) {
  const [data, setData] = useState([]);
  const [loading, setLoading] = useState(false);
  const lastFetchRef = useRef(Date.now());

  const fetchData = useCallback(async () => {
    if (!token || Date.now() - lastFetchRef.current < 5000) return; // Evitar fetch rápido demais
    
    setLoading(true);
    try {
      const res = await fetch(`${apiUrl}${endpoint}`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      if (!res.ok) throw new Error('Erro ao carregar');
      const result = await res.json();
      setData(Array.isArray(result) ? result : []);
      lastFetchRef.current = Date.now();
    } catch (_err) {
      // Erro em fetch automático
    } finally {
      setLoading(false);
    }
  }, [apiUrl, endpoint, token]);

  useEffect(() => {
    fetchData();
    const timer = setInterval(fetchData, interval);
    return () => clearInterval(timer);
  }, [fetchData, interval]);

  return { data, loading, refetch: fetchData };
}
