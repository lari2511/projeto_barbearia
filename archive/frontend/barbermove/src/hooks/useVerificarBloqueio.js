import { useState, useEffect, useCallback } from 'react';

/**
 * Hook customizado para verificar status de bloqueio da barbearia
 * e interceptar erros 402/403 da API
 */
import { getApiBaseUrl } from '../utils/api';

export function useVerificarBloqueio(token) {
  const defaultHost = typeof window !== 'undefined' ? window.location.hostname : 'localhost';
  const defaultProtocol = typeof window !== 'undefined' && window.location.protocol === 'https:' ? 'https' : 'http';
  const API_URL = import.meta.env.VITE_API_URL?.trim() || getApiBaseUrl();
  
  const [statusBloqueio, setStatusBloqueio] = useState(null);
  const [estaCarregando, setEstaCarregando] = useState(true);

  const verificarStatus = useCallback(async () => {
    if (!token) {
      setEstaCarregando(false);
      return;
    }

    try {
      const res = await fetch(`${API_URL}/api/v1/assinaturas/status`, {
        headers: { Authorization: `Bearer ${token}` }
      });

      if (res.ok) {
        const data = await res.json();
        setStatusBloqueio(data);
      }
    } catch (err) {
      console.error('Erro ao verificar bloqueio:', err);
    } finally {
      setEstaCarregando(false);
    }
  }, [token, API_URL]);

  useEffect(() => {
    verificarStatus();
    // Verifica a cada 5 minutos
    const interval = setInterval(verificarStatus, 5 * 60 * 1000);
    return () => clearInterval(interval);
  }, [verificarStatus]);

  /**
   * Intercepta erros de requisição e detecta bloqueio
   * Uso: const res = await interceptarBloqueio(fetch(...))
   */
  const interceptarBloqueio = useCallback(async (fetchPromise) => {
    const res = await fetchPromise;

    // Detectar bloqueio por HTTP 402 ou 403
    if (res.status === 402 || res.status === 403) {
      const errorData = await res.json().catch(() => ({}));

      // Se é erro de bloqueio, atualizar status
      if (errorData.detail?.erro === 'assinatura_bloqueada' || 
          errorData.detail?.erro === 'assinatura_vencida' ||
          errorData.detail?.erro === 'sem_assinatura') {

        setStatusBloqueio({
          bloqueada: true,
          motivo_bloqueio: errorData.detail.mensagem,
          valor_mensalidade: errorData.detail.valor_devido,
          proximo_vencimento: errorData.detail.vencimento
        });

        throw new Error('BARBEARIA_BLOQUEADA');
      }
    }

    return res;
  }, []);

  const estaBloqueada = statusBloqueio?.bloqueada || statusBloqueio?.vencida || false;
  const estaProximoVencimento = statusBloqueio?.dias_vencimento <= 7 && !estaBloqueada;

  return {
    statusBloqueio,
    estaBloqueada,
    estaProximoVencimento,
    estaCarregando,
    verificarStatus,
    interceptarBloqueio
  };
}

export default useVerificarBloqueio;
