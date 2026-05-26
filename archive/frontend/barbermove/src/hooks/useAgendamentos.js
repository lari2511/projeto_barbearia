import { useState, useEffect } from 'react';

/**
 * Hook para buscar agendamentos de um barbeiro
 * Usa fetch API para fazer requisições ao backend
 */
export function useAgendamentosBarbeiro(barbeiro_id, apiUrl) {
  const [agendamentos, setAgendamentos] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (!barbeiro_id || !apiUrl) return;

    const fetchAgendamentos = async () => {
      setLoading(true);
      setError(null);
      
      try {
        const response = await fetch(
          `${apiUrl}/api/v1/barbeiro/${barbeiro_id}/agendamentos`
        );
        
        if (!response.ok) {
          throw new Error(`Erro ${response.status}: ${response.statusText}`);
        }
        
        const data = await response.json();
        setAgendamentos(Array.isArray(data) ? data : []);
      } catch (err) {
        setError(err.message);
        setAgendamentos([]);
      } finally {
        setLoading(false);
      }
    };

    fetchAgendamentos();
    
    // Recarregar a cada 30 segundos
    const interval = setInterval(fetchAgendamentos, 30000);
    return () => clearInterval(interval);
  }, [barbeiro_id, apiUrl]);

  return { agendamentos, loading, error };
}

/**
 * Hook para buscar agendamentos do barbeiro autenticado (com token)
 * Útil quando você quer dados do usuário logado
 */
export function useMeusAgendamentos(token, apiUrl) {
  const [agendamentos, setAgendamentos] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (!token || !apiUrl) return;

    const fetchMeusAgendamentos = async () => {
      setLoading(true);
      setError(null);
      
      try {
        const response = await fetch(
          `${apiUrl}/api/v1/barbeiro/agendamentos/meus`,
          {
            headers: {
              'Authorization': `Bearer ${token}`,
              'Content-Type': 'application/json'
            }
          }
        );
        
        if (!response.ok) {
          throw new Error(`Erro ${response.status}: ${response.statusText}`);
        }
        
        const data = await response.json();
        setAgendamentos(Array.isArray(data) ? data : []);
      } catch (err) {
        setError(err.message);
        setAgendamentos([]);
      } finally {
        setLoading(false);
      }
    };

    fetchMeusAgendamentos();
    
    // Recarregar a cada 30 segundos
    const interval = setInterval(fetchMeusAgendamentos, 30000);
    return () => clearInterval(interval);
  }, [token, apiUrl]);

  const refetch = async () => {
    setLoading(true);
    try {
      const response = await fetch(
        `${apiUrl}/api/v1/barbeiro/agendamentos/meus`,
        {
          headers: {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json'
          }
        }
      );
      if (!response.ok) throw new Error('Erro ao recarregar');
      const data = await response.json();
      setAgendamentos(Array.isArray(data) ? data : []);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return { agendamentos, loading, error, refetch };
}

/**
 * Hook para filtrar agendamentos por status, data, etc.
 */
export function useFiltrarAgendamentos(barbeiro_id, apiUrl) {
  const [agendamentos, setAgendamentos] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const filtrar = async (opcoesFiltro) => {
    if (!barbeiro_id || !apiUrl) {
      setError('barbeiro_id ou apiUrl não fornecido');
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const response = await fetch(
        `${apiUrl}/api/v1/barbeiro/${barbeiro_id}/agendamentos/filtrar`,
        {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json'
          },
          body: JSON.stringify(opcoesFiltro)
        }
      );

      if (!response.ok) {
        throw new Error(`Erro ${response.status}: ${response.statusText}`);
      }

      const data = await response.json();
      setAgendamentos(Array.isArray(data) ? data : []);
    } catch (err) {
      setError(err.message);
      setAgendamentos([]);
    } finally {
      setLoading(false);
    }
  };

  return { agendamentos, loading, error, filtrar };
}
