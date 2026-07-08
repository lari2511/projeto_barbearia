import React, { useState, useEffect, useCallback, useContext } from 'react';
import { Star, MapPin, Phone, Mail, Award, TrendingUp, MessageCircle } from 'lucide-react';
import ChatRoom from './ChatRoom';
import { AppContext } from '../contexts/AppContext';
import { getApiBaseUrl } from '../utils/api';

const DEFAULT_HOST = typeof window !== 'undefined' ? window.location.hostname : 'localhost';
const DEFAULT_PROTOCOL = typeof window !== 'undefined' && window.location.protocol === 'https:' ? 'https' : 'http';
const API_URL = import.meta.env.VITE_API_URL?.trim() || getApiBaseUrl();

/**
 * Componente de Perfil Aprimorado com Design Melhorado
 * Exibe avaliações, estatísticas e informações principais
 */
export default function ProfileCard({ usuarioId, userType, token, isOwnProfile: _isOwnProfile = false, onNotify }) {
  const [profile, setProfile] = useState(null);
  const [barbeariaProfile, setBarbeariaProfile] = useState(null);
  const [cadeirasBarbearia, setCadeirasBarbearia] = useState([]);
  const [carregandoBarbearia, setCarregandoBarbearia] = useState(false);
  const [chatOpen, setChatOpen] = useState(false);
  const [chatChamadoId, setChatChamadoId] = useState(null);
  const [avaliacoes, setAvaliacoes] = useState(null);
  const [loading, setLoading] = useState(true);
  const [erro, setErro] = useState('');
  const [portfolioFotos, setPortfolioFotos] = useState([]);
  const [zoomFoto, setZoomFoto] = useState(null);
  const [chatLoading, setChatLoading] = useState(false);

  const appContext = useContext(AppContext);
  const { notify } = appContext || {};
  const safeNotify = onNotify || notify || (() => {});

  const logErro = (mensagem, detalhe) => {
    if (import.meta.env.DEV) {
      console.error(mensagem, detalhe);
    }
  };

  const carregarPerfil = useCallback(async () => {
    try {
      setLoading(true);
      setErro('');
      
      // Buscar dados do perfil
      const res = await fetch(`${API_URL}/api/v1/usuario/${usuarioId}`, {
        headers: token ? { 'Authorization': `Bearer ${token}` } : {}
      });

      if (!res.ok) {
        throw new Error(`Erro ${res.status}: Usuário não encontrado`);
      }

      const data = await res.json();
      setProfile(data);

      // Buscar média de avaliações
      const mediaRes = await fetch(`${API_URL}/api/v1/usuario/${usuarioId}/media_avaliacao`, {
        headers: token ? { 'Authorization': `Bearer ${token}` } : {}
      });

      if (mediaRes.ok) {
        const mediaData = await mediaRes.json();
        setAvaliacoes(mediaData);
      }

      // Buscar fotos do portfólio (já vem em portfolio_fotos no profile)
      if (data.portfolio_fotos && Array.isArray(data.portfolio_fotos)) {
        setPortfolioFotos(data.portfolio_fotos);
      }

      if (userType === 'barbearia') {
        setCarregandoBarbearia(true);
        try {
          const barbeariaRes = await fetch(`${API_URL}/api/v1/barbearia/minha`, {
            headers: token ? { 'Authorization': `Bearer ${token}` } : {}
          });

          if (barbeariaRes.ok) {
            const encontrada = await barbeariaRes.json();

            if (encontrada?.id) {
              const cadeirasRes = await fetch(`${API_URL}/api/v1/cadeiras/barbearia/${encontrada.id}`, {
                headers: token ? { 'Authorization': `Bearer ${token}` } : {}
              });

              let cadeiras = [];
              if (cadeirasRes.ok) {
                const cadeirasData = await cadeirasRes.json();
                cadeiras = Array.isArray(cadeirasData) ? cadeirasData : [];
              }

              const possuiCadeiraDisponivel = cadeiras.some((cadeira) => {
                const status = String(cadeira?.status || cadeira?.status_atendimento || '').toLowerCase();
                return status.includes('dispon') || status === 'livre' || status === 'ativo';
              });

              setBarbeariaProfile({
                ...encontrada,
                cadeira_disponivel: possuiCadeiraDisponivel,
              });
              setCadeirasBarbearia(cadeiras);
            }
          }
        } catch (_err) {
          setBarbeariaProfile(null);
          setCadeirasBarbearia([]);
        } finally {
          setCarregandoBarbearia(false);
        }
      }
    } catch (err) {
      setErro('Perfil não encontrado. Tente novamente.');
      logErro('Erro ao carregar perfil:', err);
    } finally {
      setLoading(false);
    }
  }, [token, usuarioId]);

  useEffect(() => {
    carregarPerfil();
    // verificar se há chamado ativo entre usuário atual e este perfil
    const verificarChatExistente = async () => {
      try {
        const currentUserId = Number(localStorage.getItem('userId') || 0);
        const currentUserType = localStorage.getItem('userType');
        if (!token || !currentUserId || !currentUserType) return;

        if (currentUserType === 'cliente') {
          const res = await fetch(`${API_URL}/api/v1/cliente/meus_pedidos`, {
            headers: { 'Authorization': `Bearer ${token}` }
          });
          if (!res.ok) return;
          const pedidos = await res.json();
          const encontrado = (Array.isArray(pedidos) ? pedidos : []).find(p => Number(p.barbeiro_id) === Number(usuarioId) && ['confirmado','em_atendimento'].includes((p.status||'').toLowerCase()));
          if (encontrado) setChatChamadoId(encontrado.id);
        } else if (currentUserType === 'barbeiro') {
          const res = await fetch(`${API_URL}/api/v1/barbeiro/agendamentos/meus`, {
            headers: { 'Authorization': `Bearer ${token}` }
          });
          if (!res.ok) return;
          const ags = await res.json();
          const encontrado = (Array.isArray(ags) ? ags : []).find(a => Number(a.cliente_id) === Number(usuarioId) && ['confirmado','em_atendimento'].includes((a.status||'').toLowerCase()));
          if (encontrado) setChatChamadoId(encontrado.id);
        }
      } catch (_err) {
        // ignore
      }
    };

    verificarChatExistente();
  }, [carregarPerfil]);

  if (loading) {
    return (
      <div className="flex items-center justify-center py-8">
        <div className="text-center">
          <div className="inline-block animate-spin rounded-full h-8 w-8 border-t-2 border-b-2 border-orange-500 mb-3"></div>
          <div className="text-zinc-400 text-sm">Carregando perfil...</div>
        </div>
      </div>
    );
  }

  if (!profile) {
    return (
      <div className="flex items-center justify-center py-8">
        <div className="text-center">
          <div className="text-red-500 text-sm font-bold mb-2">⚠️ Perfil não encontrado</div>
          <div className="text-zinc-400 text-xs">{erro || 'Não conseguimos carregar este perfil'}</div>
        </div>
      </div>
    );
  }

  // Calcular média de avaliações
  const mediaAvaliacoes = avaliacoes?.media || 0;
  const totalAvaliacoes = avaliacoes?.total || 0;
  const statusDisponibilidade =
    profile?.presente_em_local && profile?.barbearia_atual_nome
      ? `Disponível em ${profile.barbearia_atual_nome}`
      : 'Disponível';
  const cadeirasDisponiveis = cadeirasBarbearia.filter((cadeira) => {
    const status = String(cadeira?.status || cadeira?.status_atendimento || '').toLowerCase();
    return status.includes('dispon') || status === 'livre' || status === 'ativo';
  });

  return (
    <div className="space-y-6">
      {/* Foto de Capa */}
      {profile.foto_capa && (
        <div className="relative h-48 rounded-2xl overflow-hidden">
          <img 
            src={profile.foto_capa} 
            alt="Capa do perfil" 
            className="w-full h-full object-cover"
          />
          <div className="absolute inset-0 bg-gradient-to-t from-black via-transparent to-transparent"></div>
        </div>
      )}

      {/* Card Principal */}
      <div className={`rounded-2xl border border-zinc-800 overflow-hidden ${
        profile.foto_capa ? '-mt-16' : ''
      }`}>
        <div className="bg-gradient-to-br from-zinc-900 to-black p-6 relative">
          {/* Foto de Perfil */}
          {profile.foto_perfil && (
            <div 
              className="mb-4 cursor-pointer group"
              onClick={() => setZoomFoto(profile.foto_perfil)}
            >
              <img 
                src={profile.foto_perfil} 
                alt={profile.nome} 
                className="w-24 h-24 rounded-full border-4 border-zinc-800 object-cover group-hover:opacity-80 transition-opacity"
              />
              <p className="text-xs text-zinc-500 mt-1">Toque para ampliar</p>
            </div>
          )}

          {/* Informações Principais */}
          <div className="flex justify-between items-start mb-4">
            <div className="flex-1">
              <h1 className="text-3xl font-bold text-white mb-1">{profile.nome}</h1>
              <p className="text-zinc-400 text-sm capitalize">{userType}</p>
            </div>

            {/* Badge de Status */}
            {profile.disponivel && (
              <div className="px-4 py-2 bg-green-500/20 border border-green-500/50 rounded-full">
                <p className="text-xs text-green-400 font-bold flex items-center gap-1">
                  ● {statusDisponibilidade}
                </p>
              </div>
            )}
          </div>

          {/* Rating Stars */}
          <div className="flex items-center gap-3 mb-6 pb-6 border-b border-zinc-800">
            <div className="flex items-center gap-1">
              {[...Array(5)].map((_, i) => (
                <Star
                  key={i}
                  size={20}
                  className={i < Math.round(mediaAvaliacoes) ? 'text-yellow-400 fill-yellow-400' : 'text-zinc-700'}
                />
              ))}
            </div>
            <div>
              <p className="text-sm font-bold text-white">
                {mediaAvaliacoes.toFixed(1)} de 5 estrelas
              </p>
              <p className="text-xs text-zinc-400">
                ({totalAvaliacoes} {totalAvaliacoes === 1 ? 'avaliação' : 'avaliações'})
              </p>
            </div>
          </div>

          {/* Contato e Localização */}
          <div className="space-y-3">
            {profile.endereco && (
              <div className="flex items-start gap-3">
                <MapPin size={18} className="text-orange-400 shrink-0 mt-1" />
                <div>
                  <p className="text-xs text-zinc-400">Localização</p>
                  <p className="text-sm text-white">{profile.endereco}</p>
                </div>
              </div>
            )}

            {profile.telefone && (
              <div className="flex items-start gap-3">
                <Phone size={18} className="text-green-400 shrink-0 mt-1" />
                <div>
                  <p className="text-xs text-zinc-400">Telefone</p>
                  <p className="text-sm text-white">{profile.telefone}</p>
                </div>
              </div>
            )}

            {profile.email && (
              <div className="flex items-start gap-3">
                <Mail size={18} className="text-blue-400 shrink-0 mt-1" />
                <div>
                  <p className="text-xs text-zinc-400">Email</p>
                  <p className="text-sm text-white break-all">{profile.email}</p>
                </div>
              </div>
            )}
          </div>

          {/* Bot\u00e3o WhatsApp */}

          {userType === 'barbearia' && (
            <div className="mt-6 pt-6 border-t border-zinc-800 space-y-3">
              <div className="flex items-center justify-between gap-3">
                <div>
                  <p className="text-xs text-zinc-400 uppercase">Cadeiras da barbearia</p>
                  <p className="text-sm font-bold text-white">
                    {carregandoBarbearia ? 'Carregando...' : `${cadeirasBarbearia.length} cadeira(s) cadastrada(s)`}
                  </p>
                </div>
                {barbeariaProfile?.cadeira_disponivel && (
                  <span className="px-3 py-1 rounded-full text-[11px] font-bold bg-green-500/20 text-green-400 border border-green-500/30">
                    Tem cadeira disponível
                  </span>
                )}
              </div>

              {!carregandoBarbearia && (
                <div className="grid grid-cols-2 gap-3">
                  <div className="bg-black/40 border border-zinc-800 rounded-lg p-3">
                    <p className="text-[11px] text-zinc-400">Disponíveis agora</p>
                    <p className="text-xl font-bold text-green-400">{cadeirasDisponiveis.length}</p>
                  </div>
                  <div className="bg-black/40 border border-zinc-800 rounded-lg p-3">
                    <p className="text-[11px] text-zinc-400">Total de cadeiras</p>
                    <p className="text-xl font-bold text-white">{cadeirasBarbearia.length}</p>
                  </div>
                </div>
              )}

              {cadeirasBarbearia.length > 0 ? (
                <div className="space-y-2 max-h-56 overflow-auto pr-1">
                  {cadeirasBarbearia.map((cadeira) => {
                    const status = String(cadeira?.status || cadeira?.status_atendimento || '').toLowerCase();
                    const disponivel = status.includes('dispon') || status === 'livre' || status === 'ativo';
                    return (
                      <div key={cadeira.id} className="flex items-center justify-between gap-3 rounded-lg border border-zinc-800 bg-black/30 px-3 py-2">
                        <div>
                          <p className="text-sm font-bold text-white">Cadeira {cadeira.numero}</p>
                          <p className="text-[11px] text-zinc-500">{cadeira.barbearia_nome || profile.nome}</p>
                        </div>
                        <span className={`px-2 py-1 rounded text-[10px] font-bold border ${disponivel ? 'bg-green-500/15 text-green-400 border-green-500/30' : 'bg-zinc-700/30 text-zinc-300 border-zinc-700'}`}>
                          {disponivel ? 'DISPONÍVEL' : String(cadeira.status || 'OCUPADA').toUpperCase()}
                        </span>
                      </div>
                    );
                  })}
                </div>
              ) : (
                !carregandoBarbearia && (
                  <p className="text-xs text-zinc-500">Nenhuma cadeira cadastrada ou disponível para essa barbearia.</p>
                )
              )}
            </div>
          )}
          {profile.telefone && userType === 'barbeiro' && (
            <div className="mt-6 pt-6 border-t border-zinc-800">
              <a
                href={`https://wa.me/55${profile.telefone.replace(/\D/g, '')}`}
                target="_blank"
                rel="noopener noreferrer"
                className="w-full bg-green-600 text-white px-4 py-3 rounded-lg font-bold flex items-center justify-center gap-2 hover:bg-green-700 active:scale-95 transition-all"
              >
                <MessageCircle size={20} />
                Entrar em Contato via WhatsApp
              </a>
            </div>
          )}

          {/* Botão Conversar (abre chat do chamado se existir) */}
          {token && (
            <div className="mt-3">
              <button
                onClick={async () => {
                  if (chatLoading || !chatChamadoId) return;
                  setChatLoading(true);
                  try {
                    setChatOpen(true);
                  } catch (err) {
                    console.error(err);
                    safeNotify('Erro ao iniciar conversa', 'error');
                  } finally {
                    setChatLoading(false);
                  }
                }}
                disabled={chatLoading || !chatChamadoId}
                className={`w-full px-4 py-3 rounded-lg font-bold flex items-center justify-center gap-2 ${chatLoading ? 'bg-zinc-700 text-zinc-300' : chatChamadoId ? 'bg-orange-600 hover:bg-orange-700 text-white' : 'bg-zinc-800 text-zinc-500 cursor-not-allowed'}`}
                title={chatChamadoId ? 'Abrir conversa do chamado confirmado' : 'Conversa liberada após o chamado ser confirmado'}
              >
                <MessageCircle size={18} />
                {chatLoading ? 'Abrindo...' : chatChamadoId ? 'Conversar' : 'Aguardando confirmação'}
              </button>
            </div>
          )}
        </div>
      </div>

      {/* Estatísticas */}
      {(profile.total_agendamentos || profile.tempo_experiencia) && (
        <div className="grid grid-cols-2 gap-4">
          {profile.total_agendamentos !== undefined && (
            <div className="bg-zinc-900 border border-zinc-800 rounded-lg p-4">
              <div className="flex items-center gap-2 mb-2">
                <TrendingUp size={18} className="text-blue-500" />
                <p className="text-xs text-zinc-400 font-bold">Total Atendimentos</p>
              </div>
              <p className="text-2xl font-bold text-white">{profile.total_agendamentos || 0}</p>
            </div>
          )}

          {profile.tempo_experiencia && (
            <div className="bg-zinc-900 border border-zinc-800 rounded-lg p-4">
              <div className="flex items-center gap-2 mb-2">
                <Award size={18} className="text-purple-500" />
                <p className="text-xs text-zinc-400 font-bold">Experiência</p>
              </div>
              <p className="text-2xl font-bold text-white">{profile.tempo_experiencia}</p>
            </div>
          )}
        </div>
      )}

      {/* Portfólio (se houver fotos) */}
      {(profile.portfolio_fotos && profile.portfolio_fotos.length > 0) || portfolioFotos.length > 0 ? (
        <div className="bg-zinc-900 border border-zinc-800 rounded-2xl p-6">
          <h3 className="text-lg font-bold text-white mb-4">Portfólio</h3>
          <div className="grid grid-cols-3 gap-3">
            {(profile.portfolio_fotos && profile.portfolio_fotos.length > 0 ? profile.portfolio_fotos : portfolioFotos).map((foto, idx) => (
              <div 
                key={idx} 
                className="aspect-square rounded-lg overflow-hidden border border-zinc-800 cursor-pointer group"
                onClick={() => setZoomFoto(foto)}
              >
                <img 
                  src={foto} 
                  alt={`Portfólio ${idx + 1}`} 
                  className="w-full h-full object-cover group-hover:scale-105 transition-transform"
                />
              </div>
            ))}
          </div>
        </div>
      ) : null}

      {/* Últimas Avaliações */}
      {avaliacoes?.ultimas && avaliacoes.ultimas.length > 0 && (
        <div className="bg-zinc-900 border border-zinc-800 rounded-2xl p-6">
          <h3 className="text-lg font-bold text-white mb-4">Últimas Avaliações</h3>
          <div className="space-y-3">
            {avaliacoes.ultimas.map((aval, idx) => (
              <div key={idx} className="bg-black/50 p-4 rounded-lg border border-zinc-800/50">
                <div className="flex justify-between items-start mb-2">
                  <div>
                    <p className="font-bold text-white">{aval.avaliador_nome || 'Usuário'}</p>
                    <p className="text-xs text-zinc-400">
                      {new Date(aval.data).toLocaleDateString('pt-BR')}
                    </p>
                  </div>
                  <div className="flex gap-1">
                    {[...Array(5)].map((_, i) => (
                      <Star
                        key={i}
                        size={16}
                        className={i < aval.nota ? 'text-yellow-400 fill-yellow-400' : 'text-zinc-700'}
                      />
                    ))}
                  </div>
                </div>
                {aval.comentario && (
                  <p className="text-sm text-zinc-300">{aval.comentario}</p>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Modal de Zoom Seguro */}
      {zoomFoto && (
        <div 
          className="fixed inset-0 bg-black z-50 flex items-center justify-center p-2"
          onClick={() => setZoomFoto(null)}
        >
          <div onClick={(e) => e.stopPropagation()} className="relative">
            <button
              onClick={() => setZoomFoto(null)}
              className="absolute -top-10 right-0 bg-red-600 text-white px-3 py-1 rounded text-xs font-bold hover:bg-red-700"
            >
              ✕ Fechar
            </button>
            <img 
              src={zoomFoto}
              alt="Zoom"
              className="max-w-[90vw] max-h-[85vh] object-contain rounded-lg"
            />
          </div>
        </div>
      )}

      {/* Modal de Chat (quando houver chamado entre usuários) */}
      {chatOpen && (
        <div className="fixed inset-0 bg-black/80 z-50 flex items-center justify-center p-2 sm:p-4">
          <div className="w-full max-w-[96vw] sm:max-w-5xl lg:max-w-6xl h-[92vh] bg-zinc-950 border border-zinc-800 rounded-2xl p-3 sm:p-5 flex flex-col shadow-2xl">
            <div className="flex items-center justify-between gap-3 mb-4 pb-3 border-b border-zinc-800">
              <div>
                <h3 className="text-base sm:text-lg font-bold text-white">Chat com {profile.nome}</h3>
                <p className="text-[11px] sm:text-xs text-zinc-400 mt-1">Conversa em tempo real com espaço maior para acompanhar a troca de mensagens</p>
              </div>
              <div className="flex items-center gap-2">
                <button onClick={() => setChatOpen(false)} className="text-zinc-400 hover:text-white transition-colors text-lg leading-none">✕</button>
              </div>
            </div>
            <div className="flex-1 min-h-0 overflow-hidden">
              {/* Reutiliza ChatRoom em modo expandido */}
              <ChatRoom chamadoId={chatChamadoId} token={token} API_URL={API_URL} compact={false} />
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
