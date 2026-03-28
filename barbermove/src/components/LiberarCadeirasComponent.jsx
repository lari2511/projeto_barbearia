import React, { useState, useEffect, useCallback } from 'react';
import { Loader, AlertCircle, CheckCircle, Armchair, Lock, LockOpen } from 'lucide-react';

export default function LiberarCadeirasComponent({ token, API_URL, notify, barbeariaId }) {
  const [cadeiras, setCadeiras] = useState([]);
  const [loading, setLoading] = useState(true);
  const [libertando, setLibertando] = useState(null);

  const carregarCadeiras = useCallback(async () => {
    if (!barbeariaId) {
      setLoading(false);
      return;
    }

    try {
      setLoading(true);
      const res = await fetch(`${API_URL}/api/v1/cadeiras?barbearia_id=${barbeariaId}`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });

      if (res.ok) {
        const data = await res.json();
        setCadeiras(Array.isArray(data) ? data : []);
      } else {
        notify('Erro ao carregar cadeiras', 'error');
      }
    } catch (err) {
      notify('Erro ao carregar cadeiras: ' + err.message, 'error');
    } finally {
      setLoading(false);
    }
  }, [API_URL, barbeariaId, notify, token]);

  useEffect(() => {
    carregarCadeiras();
  }, [carregarCadeiras]);

  const liberarCadeira = async (cadeiraId) => {
    try {
      setLibertando(cadeiraId);
      const res = await fetch(`${API_URL}/api/v1/cadeiras/${cadeiraId}/liberar-para-barbeiros`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        }
      });

      if (res.ok) {
        const data = await res.json();
        notify(`✅ Cadeira '${data.cadeira.numero}' liberada para freelancers!`, 'success');
        carregarCadeiras();
      } else {
        const error = await res.json();
        notify(error.detail || 'Erro ao liberar cadeira', 'error');
      }
    } catch (err) {
      notify('Erro: ' + err.message, 'error');
    } finally {
      setLibertando(null);
    }
  };

  const bloquearCadeira = async (cadeiraId) => {
    try {
      setLibertando(cadeiraId);
      const res = await fetch(`${API_URL}/api/v1/cadeiras/${cadeiraId}/bloquear`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        }
      });

      if (res.ok) {
        const data = await res.json();
        notify(`🔒 Cadeira '${data.cadeira.numero}' bloqueada!`, 'success');
        carregarCadeiras();
      } else {
        const error = await res.json();
        notify(error.detail || 'Erro ao bloquear cadeira', 'error');
      }
    } catch (err) {
      notify('Erro: ' + err.message, 'error');
    } finally {
      setLibertando(null);
    }
  };

  const desbloquearCadeira = async (cadeiraId) => {
    try {
      setLibertando(cadeiraId);
      const res = await fetch(`${API_URL}/api/v1/cadeiras/${cadeiraId}/desbloquear`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        }
      });

      if (res.ok) {
        const data = await res.json();
        notify(`🔓 Cadeira '${data.cadeira.numero}' desbloqueada!`, 'success');
        carregarCadeiras();
      } else {
        const error = await res.json();
        notify(error.detail || 'Erro ao desbloquear cadeira', 'error');
      }
    } catch (err) {
      notify('Erro: ' + err.message, 'error');
    } finally {
      setLibertando(null);
    }
  };

  if (!barbeariaId) {
    return (
      <div className="bg-yellow-900/20 border border-yellow-600 rounded-lg p-3 text-yellow-400 text-xs">
        ⚠️ Barbearia não identificada. Configure seu perfil.
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-bold text-white flex items-center gap-2">
          👍 Liberar Cadeiras
        </h3>
        <button
          onClick={carregarCadeiras}
          disabled={loading}
          className="bg-orange-500 text-white px-2 py-1 rounded text-xs font-bold active:scale-95 disabled:opacity-50"
        >
          {loading ? '⏳' : '🔄'}
        </button>
      </div>

      {loading ? (
        <div className="flex items-center justify-center py-6">
          <Loader className="animate-spin text-orange-500" size={20} />
        </div>
      ) : cadeiras.length === 0 ? (
        <div className="bg-zinc-900/50 border border-zinc-800 rounded-lg p-4 text-center">
          <AlertCircle className="text-zinc-600 mx-auto mb-2" size={24} />
          <p className="text-zinc-400 text-xs">Nenhuma cadeira cadastrada</p>
        </div>
      ) : (
        <div className="space-y-2">
          {cadeiras.map(cadeira => {
            const status = (cadeira.status || '').toString().toLowerCase();
            return (
            <div key={cadeira.id} className="bg-zinc-900 border border-zinc-800 rounded-lg p-3">
              <div className="flex items-center justify-between mb-2">
                <div className="flex items-center gap-2">
                  <Armchair size={16} className="text-orange-500" />
                  <span className="font-bold text-sm">{cadeira.numero}</span>
                </div>
                <span className={`text-xs px-2 py-1 rounded font-bold ${
                  status === 'disponivel' ? 'bg-green-600/20 text-green-400' :
                  status === 'ocupada' ? 'bg-blue-600/20 text-blue-400' :
                  'bg-red-600/20 text-red-400'
                }`}>
                  {status ? status.toUpperCase() : 'DESCONHECIDO'}
                </span>
              </div>

              {status === 'disponivel' ? (
                <div className="flex gap-2">
                  <button
                    onClick={() => liberarCadeira(cadeira.id)}
                    disabled={libertando === cadeira.id}
                    className="flex-1 bg-green-600 hover:bg-green-700 disabled:opacity-50 disabled:cursor-not-allowed text-white font-bold py-2 rounded text-xs transition-colors active:scale-95"
                  >
                    {libertando === cadeira.id ? (
                      <span className="flex items-center justify-center gap-1">
                        <Loader size={12} className="animate-spin" />
                        Liberando...
                      </span>
                    ) : (
                      '✅ Liberar'
                    )}
                  </button>
                  <button
                    onClick={() => bloquearCadeira(cadeira.id)}
                    disabled={libertando === cadeira.id}
                    className="flex-1 bg-red-600 hover:bg-red-700 disabled:opacity-50 disabled:cursor-not-allowed text-white font-bold py-2 rounded text-xs transition-colors active:scale-95"
                  >
                    {libertando === cadeira.id ? (
                      <span className="flex items-center justify-center gap-1">
                        <Loader size={12} className="animate-spin" />
                      </span>
                    ) : (
                      '🔒 Bloquear'
                    )}
                  </button>
                </div>
              ) : status === 'ocupada' && cadeira.freelancer_id ? (
                <div className="bg-blue-900/20 border border-blue-600/30 rounded p-2 text-xs text-blue-400">
                  <div className="flex items-center gap-1">
                    <CheckCircle size={12} />
                    <span>Ocupada por {cadeira.freelancer_nome || 'Freelancer'}</span>
                  </div>
                </div>
              ) : status === 'ocupada' && !cadeira.freelancer_id ? (
                <div className="bg-orange-900/20 border border-orange-600/30 rounded p-2 text-xs text-orange-400">
                  Aguardando freelancer aceitar...
                </div>
              ) : (
                <button
                  onClick={() => desbloquearCadeira(cadeira.id)}
                  disabled={libertando === cadeira.id}
                  className="w-full bg-yellow-600 hover:bg-yellow-700 disabled:opacity-50 disabled:cursor-not-allowed text-white font-bold py-2 rounded text-xs transition-colors active:scale-95"
                >
                  {libertando === cadeira.id ? (
                    <span className="flex items-center justify-center gap-1">
                      <Loader size={12} className="animate-spin" />
                      Desbloqueando...
                    </span>
                  ) : (
                    <>
                      <LockOpen size={12} className="inline mr-1" />
                      Desbloquear
                    </>
                  )}
                </button>
              )}
            </div>
          )})}
        </div>
      )}
    </div>
  );
}
