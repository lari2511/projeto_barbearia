import React, { useState, useEffect, useCallback } from 'react';
import { MapPin, Clock, Building2, Loader, CheckCircle, AlertCircle } from 'lucide-react';

export default function CadeirasDisponíveisComponent({ token, API_URL, notify }) {
  const [cadeiras, setCadeiras] = useState([]);
  const [loading, setLoading] = useState(true);
  const [aceitando, setAceitando] = useState(null);
  const [cadeiraAceita, setCadeiraAceita] = useState(null);

  const carregarCadeirasDisponiveis = useCallback(async () => {
    try {
      setLoading(true);
      const res = await fetch(`${API_URL}/api/v1/cadeiras/disponiveis`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });

      if (res.ok) {
        const data = await res.json();
        setCadeiras(data.caderias || []);
        if ((!data.caderias || data.caderias.length === 0) && data.total === 0) {
          notify('Nenhuma cadeira disponível próxima a você', 'info');
        }
      } else {
        const error = await res.json();
        notify(error.detail || 'Erro ao carregar caderias', 'error');
      }
    } catch (err) {
      notify('Erro ao carregar caderias: ' + err.message, 'error');
    } finally {
      setLoading(false);
    }
  }, [API_URL, notify, token]);

  useEffect(() => {
    carregarCadeirasDisponiveis();
  }, [carregarCadeirasDisponiveis]);

  const aceitarCadeira = async (cadeiraId) => {
    try {
      setAceitando(cadeiraId);
      const res = await fetch(`${API_URL}/api/v1/cadeiras/${cadeiraId}/aceitar`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        }
      });

      if (res.ok) {
        const data = await res.json();
        notify(`✅ Cadeira '${data.cadeira.numero}' aceita!`, 'success');
        setCadeiraAceita(data.cadeira);
        
        // Remover da lista
        setCadeiras(cadeiras.filter(c => c.id !== cadeiraId));
        
        // Recarregar as cadeiras disponíveis após 2 segundos
        setTimeout(() => {
          carregarCadeirasDisponiveis();
        }, 2000);
      } else {
        const error = await res.json();
        notify(error.detail || 'Erro ao aceitar cadeira', 'error');
      }
    } catch (err) {
      notify('Erro: ' + err.message, 'error');
    } finally {
      setAceitando(null);
    }
  };

  return (
    <div className="space-y-4 p-4 pb-24">
      {/* Header */}
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-white flex items-center gap-2">
          ✨ Cadeiras Disponíveis
        </h1>
        <button
          onClick={carregarCadeirasDisponiveis}
          disabled={loading}
          className="bg-orange-500 text-white px-3 py-2 rounded-lg text-xs font-bold active:scale-95 disabled:opacity-50"
        >
          {loading ? '⏳' : '🔄'} Atualizar
        </button>
      </div>

      {loading ? (
        <div className="flex flex-col items-center justify-center py-12">
          <Loader className="animate-spin text-orange-500 mb-2" size={32} />
          <p className="text-zinc-400">Procurando cadeiras próximas...</p>
        </div>
      ) : cadeiraAceita ? (
        <div className="space-y-4">
          <div className="bg-green-600/10 border border-green-600 rounded-lg p-4">
            <div className="flex items-start gap-3">
              <CheckCircle className="text-green-500 flex-shrink-0 mt-1" size={20} />
              <div>
                <h2 className="font-bold text-green-400">Cadeira Aceita!</h2>
                <p className="text-sm text-zinc-300 mt-1">
                  Você aceitou a cadeira <span className="font-bold">{cadeiraAceita.numero}</span> em <span className="font-bold">{cadeiraAceita.barbearia_nome}</span>
                </p>
                <p className="text-xs text-zinc-400 mt-2">{cadeiraAceita.barbearia_endereco}</p>
              </div>
            </div>
          </div>
        </div>
      ) : cadeiras.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-12">
          <AlertCircle className="text-zinc-600 mb-2" size={32} />
          <p className="text-zinc-400">Nenhuma cadeira disponível próxima a você</p>
          <p className="text-xs text-zinc-500 mt-2">Configure sua localização no perfil</p>
        </div>
      ) : (
        <div className="space-y-3">
          {cadeiras.map(cadeira => (
            <div key={cadeira.id} className="bg-zinc-900 border border-zinc-800 rounded-lg p-4 hover:border-orange-500 transition-colors">
              {/* Número da cadeira */}
              <div className="flex items-center justify-between mb-3">
                <h3 className="text-lg font-bold text-white">
                  👍 Cadeira {cadeira.numero}
                </h3>
                <span className="bg-orange-600/20 text-orange-400 px-2 py-1 rounded text-xs font-bold">
                  {cadeira.distancia_km}km
                </span>
              </div>

              {/* Barbearia info */}
              <div className="space-y-2 mb-4">
                <div className="flex items-center gap-2 text-sm">
                  <Building2 size={16} className="text-zinc-500" />
                  <div>
                    <p className="text-zinc-300">{cadeira.barbearia.nome}</p>
                    <p className="text-xs text-zinc-500">{cadeira.barbearia.endereco}</p>
                  </div>
                </div>

                <div className="flex items-center gap-2 text-sm">
                  <Clock size={16} className="text-zinc-500" />
                  <span className="text-zinc-400">
                    Liberada há {Math.round((new Date() - new Date(cadeira.acionada_em)) / 1000 / 60)} minutos
                  </span>
                </div>

              </div>

              {(cadeira.statusAtendimento === 'AGUARDANDO' || cadeira.status_atendimento === 'AGUARDANDO' || cadeira.status === 'disponível_para_aceitar' || cadeira.status === 'aguardando_barbeiro') && (
                <div className="bg-blue-900/20 border border-blue-600/30 rounded-lg p-3 space-y-3">
                  <p className="text-xs text-blue-300 font-semibold">Novo cliente aguardando na cadeira!</p>
                  <button
                    onClick={() => aceitarCadeira(cadeira.id)}
                    disabled={aceitando === cadeira.id}
                    className="w-full bg-blue-600 hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed text-white font-bold py-3 rounded-lg transition-colors active:scale-95"
                  >
                    {aceitando === cadeira.id ? (
                      <span className="flex items-center justify-center gap-2">
                        <Loader size={16} className="animate-spin" />
                        Assumindo...
                      </span>
                    ) : (
                      'ASSUMIR ATENDIMENTO'
                    )}
                  </button>
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
