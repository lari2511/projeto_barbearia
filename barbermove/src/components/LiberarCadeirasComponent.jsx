import React, { useState, useEffect, useCallback } from 'react';
import { Loader, AlertCircle, CheckCircle, Armchair, Lock, LockOpen, Plus } from 'lucide-react';

export default function LiberarCadeirasComponent({ token, API_URL, notify, barbeariaId }) {
  const [cadeiras, setCadeiras] = useState([]);
  const [loading, setLoading] = useState(true);
  const [libertando, setLibertando] = useState(null);
  const [tempoRestante, setTempoRestante] = useState({});

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

  // Atualizar tempo restante a cada segundo
  useEffect(() => {
    const interval = setInterval(() => {
      setTempoRestante(prev => {
        const updated = { ...prev };
        cadeiras.forEach(c => {
          if (c.ocupada_em) {
            const ocupadaEm = new Date(c.ocupada_em).getTime();
            const agora = Date.now();
            const tempoDecorrido = (agora - ocupadaEm) / 1000; // segundos
            updated[c.id] = Math.max(0, tempoDecorrido);
          }
        });
        return updated;
      });
    }, 1000);
    return () => clearInterval(interval);
  }, [cadeiras]);

  const liberarCadeira = async (cadeiraId) => {
    try {
      setLibertando(cadeiraId);
      const res = await fetch(`${API_URL}/api/v1/cadeiras/${cadeiraId}/liberar`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        }
      });

      if (res.ok) {
        const data = await res.json();
        notify(`✅ Cadeira '${data.cadeira_id || cadeiraId}' liberada!`, 'success');
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
      <div className="bm-card text-sm text-purple-200">
        ⚠️ <strong>Barbearia não identificada</strong> — Configure seu perfil nas configurações.
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-bold text-white flex items-center gap-2">
          🪑 Gerenciar Cadeiras
        </h3>
        <button
          onClick={carregarCadeiras}
          disabled={loading}
          className="bg-purple-600 hover:bg-purple-700 text-white px-3 py-1.5 rounded-lg text-xs font-bold active:scale-95 disabled:opacity-50 transition flex items-center gap-1"
        >
          {loading ? <Loader size={14} className="animate-spin" /> : '🔄 Atualizar'}
        </button>
      </div>

      {/* Nova Cadeira */}
      <button className="w-full bg-transparent border border-zinc-800 text-zinc-300 py-3 rounded-lg font-bold text-sm flex items-center justify-center gap-2 transition active:scale-95">
        <Plus size={18} />
        Nova Cadeira
      </button>

      {/* Dicas */}
      <div className="bg-purple-600/10 border border-purple-600/30 rounded-lg p-3">
        <p className="text-xs text-purple-300">
          💡 <strong>Dica:</strong> Quando a barra fica <span className="text-purple-400">roxa e piscante</span>, significa que faltam 15 minutos — o próximo cliente já está sendo buscado pelo sistema!
        </p>
      </div>

      {loading ? (
        <div className="flex items-center justify-center py-8">
          <Loader className="animate-spin text-purple-500" size={24} />
        </div>
      ) : cadeiras.length === 0 ? (
        <div className="space-y-3">
          <div className="bm-banner">
            <div className="text-xl">📍</div>
            <div>
              <div className="text-sm text-purple-300">Nenhuma cadeira acionada próxima</div>
              <div className="text-xs text-zinc-400">Barbearias não acionaram cadeiras nas últimas 24h (raio 10km)</div>
            </div>
          </div>

          <div className="bm-ghost-card flex items-center justify-between">
            <div>
              <div className="text-sm font-bold text-orange-400">Verificação pendente</div>
              <div className="text-xs text-zinc-400">Complete sua verificação para liberar chamados</div>
            </div>
            <div className="text-orange-400">›</div>
          </div>

          <div className="bm-ghost-card">
            <div className="text-sm font-bold text-zinc-300">NOVOS CHAMADOS</div>
            <div className="mt-3 text-zinc-400 text-xs">Nenhum chamado disponível<br/>Novos chamados aparecerão aqui quando disponíveis.</div>
          </div>

          <div className="bm-card text-center">
            <AlertCircle className="text-zinc-600 mx-auto mb-3" size={32} />
            <p className="text-zinc-400 text-sm">Nenhuma cadeira cadastrada</p>
            <p className="text-zinc-500 text-xs mt-1">Clique em "Nova Cadeira" para começar!</p>
          </div>
        </div>
      ) : (
        <div className="space-y-3">
          {cadeiras.map(cadeira => {
            const status = (cadeira.status || '').toString().toLowerCase();
            const piscando = status === 'ocupada' && tempoRestante[cadeira.id] && tempoRestante[cadeira.id] >= (tempoRestante[cadeira.id] * 60 - 900); // últimos 15 min
            
            return (
              <div 
                key={cadeira.id} 
                className={`bm-card overflow-hidden transition ${
                  piscando 
                    ? 'border-purple-500 bg-purple-900/8 animate-pulse' 
                    : ''
                }`}>
              >
                {/* Barra de Progresso no topo */}
                {status === 'ocupada' && (
                  <div className={`bm-progress ${
                    piscando 
                      ? 'bg-purple-500 animate-pulse' 
                      : 'bg-orange-500'
                  }`} style={{
                    width: `${Math.min(100, (tempoRestante[cadeira.id] || 0) / 18)}%`
                  }} />
                )}

                {/* Conteúdo do Card */}
                <div className="p-4 flex items-center justify-between gap-4">
                  {/* Info da Cadeira */}
                  <div className="flex-1 flex items-center gap-3">
                    <div className="bg-purple-600/10 p-3 rounded-xl">
                      <Armchair size={18} className="text-purple-400" />
                    </div>
                    <div className="flex-1 min-w-0">
                      <p className="font-extrabold text-white text-base">Cadeira {cadeira.numero}</p>
                      <div className="flex items-center gap-2 mt-1">
                        <span className={`text-xs px-2 py-0.5 rounded-full font-bold ${
                          status === 'disponivel' ? 'bm-pill green' :
                          status === 'ocupada' ? 'bm-pill orange' :
                          'bm-pill purple'
                        }`}>
                          {status ? status.charAt(0).toUpperCase() + status.slice(1) : 'DESCONHECIDO'}
                        </span>
                        {status === 'ocupada' && cadeira.freelancer_nome && (
                          <span className="text-xs text-zinc-400 truncate">por {cadeira.freelancer_nome}</span>
                        )}
                      </div>
                    </div>
                  </div>

                  {/* Botões de Ação */}
                    <div className="flex items-center gap-2">
                    {status === 'ocupada' ? (
                      <button
                        onClick={() => liberarCadeira(cadeira.id)}
                        disabled={libertando === cadeira.id}
                        className="bg-gradient-to-r from-orange-500 to-orange-400 disabled:opacity-50 text-white font-bold py-2 px-3 rounded-xl text-sm transition-colors active:scale-95 flex items-center gap-2 whitespace-nowrap"
                      >
                        {libertando === cadeira.id ? (
                          <>
                            <Loader size={14} className="animate-spin" />
                            Liberando...
                          </>
                        ) : (
                          <>
                            ⚡ Liberar
                          </>
                        )}
                      </button>
                    ) : status === 'disponivel' ? (
                      <button
                        onClick={() => bloquearCadeira(cadeira.id)}
                        disabled={libertando === cadeira.id}
                        className="bg-zinc-800/60 border border-zinc-700 text-zinc-200 font-semibold py-2 px-3 rounded-full text-sm transition-colors active:scale-95 flex items-center gap-2"
                      >
                        {libertando === cadeira.id ? (
                          <Loader size={14} className="animate-spin" />
                        ) : (
                          <>
                            <Lock size={14} />
                            Bloquear
                          </>
                        )}
                      </button>
                    ) : (
                      <button
                        onClick={() => desbloquearCadeira(cadeira.id)}
                        disabled={libertando === cadeira.id}
                        className="bg-zinc-800/60 border border-zinc-700 text-zinc-200 font-semibold py-2 px-3 rounded-full text-sm transition-colors active:scale-95 flex items-center gap-2"
                      >
                        {libertando === cadeira.id ? (
                          <Loader size={14} className="animate-spin" />
                        ) : (
                          <>
                            <LockOpen size={14} />
                            Desbloquear
                          </>
                        )}
                      </button>
                    )}
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
