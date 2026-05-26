import React, { useEffect, useState, useCallback } from 'react';
import { AlertTriangle, X, CreditCard } from 'lucide-react';
import { getApiBaseUrl } from '../utils/api';

/**
 * Banner de alerta que aparece no topo do dashboard da barbearia
 * para avisar sobre vencimento próximo ou bloqueio
 */
export default function BannerVencimentoAssinatura({ token, onNavigateToPagamento }) {
  const defaultHost = typeof window !== 'undefined' ? window.location.hostname : 'localhost';
  const defaultProtocol = typeof window !== 'undefined' && window.location.protocol === 'https:' ? 'https' : 'http';
  const API_URL = import.meta.env.VITE_API_URL?.trim() || getApiBaseUrl();
  
  const [status, setStatus] = useState(null);
  const [dismissed, setDismissed] = useState(false);
  const [loading, setLoading] = useState(true);

  const verificarStatus = useCallback(async () => {
    try {
      const res = await fetch(`${API_URL}/api/v1/assinaturas/status`, {
        headers: { Authorization: `Bearer ${token}` }
      });

      if (res.ok) {
        const data = await res.json();
        setStatus(data);
      }
    } catch (err) {
      console.error('Erro ao verificar status:', err);
    } finally {
      setLoading(false);
    }
  }, [API_URL, token]);

  useEffect(() => {
    verificarStatus();
    // Verifica a cada 5 minutos
    const interval = setInterval(verificarStatus, 5 * 60 * 1000);
    return () => clearInterval(interval);
  }, [verificarStatus]);

  if (loading || dismissed || !status) return null;

  // Não mostrar se está tudo OK
  if (!status.bloqueada && !status.vencida && status.dias_vencimento > 7) {
    return null;
  }

  const getBannerStyle = () => {
    if (status.bloqueada || status.vencida) {
      return 'bg-red-600 border-red-700';
    }
    if (status.dias_vencimento <= 3) {
      return 'bg-yellow-600 border-yellow-700';
    }
    return 'bg-blue-600 border-blue-700';
  };

  const getIcon = () => {
    if (status.bloqueada || status.vencida) {
      return <AlertTriangle size={24} className="animate-pulse" />;
    }
    return <AlertTriangle size={24} />;
  };

  const getMessage = () => {
    if (status.bloqueada) {
      return `⛔ BARBEARIA BLOQUEADA! ${status.motivo_bloqueio}`;
    }
    if (status.vencida) {
      return `⚠️ Sua assinatura venceu! Pague R$ ${status.valor_mensalidade?.toFixed(2)} para desbloquear.`;
    }
    if (status.dias_vencimento <= 3) {
      return `⏰ Sua assinatura vence em ${status.dias_vencimento} dia(s)! Pague antes para evitar bloqueio.`;
    }
    return `📅 Sua assinatura vence em ${status.dias_vencimento} dias.`;
  };

  return (
    <div className={`${getBannerStyle()} border-b text-white shadow-lg`}>
      <div className="container mx-auto px-4 py-3">
        <div className="flex items-center justify-between gap-4">
          <div className="flex items-center gap-3 flex-1">
            {getIcon()}
            <div className="flex-1">
              <p className="font-bold text-sm md:text-base">{getMessage()}</p>
              {status.bloqueada || status.vencida ? (
                <p className="text-xs mt-1 opacity-90">
                  Clique em "Pagar agora" para desbloquear imediatamente.
                </p>
              ) : null}
            </div>
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={onNavigateToPagamento}
              className="bg-gradient-to-r from-orange-600 to-red-600 text-white font-extrabold px-4 py-2 rounded-2xl hover:from-orange-700 hover:to-red-700 transition flex items-center gap-2 text-sm"
            >
              <CreditCard size={16} />
              Pagar agora
            </button>
            
            {!status.bloqueada && !status.vencida && (
              <button
                onClick={() => setDismissed(true)}
                className="p-2 hover:bg-zinc-800/20 rounded transition text-zinc-200"
                title="Dispensar"
              >
                <X size={20} />
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
