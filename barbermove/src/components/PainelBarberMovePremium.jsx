import { useState, useEffect, useCallback } from 'react';
import { Home, ClipboardList, Star, User, CreditCard, LogOut, CheckCircle, XCircle, DollarSign } from 'lucide-react';
import { useApp } from '../contexts/AppContext';
import { getApiBaseUrl, getWsBaseUrl } from '../utils/api';
import AbaPadronizadaAvaliacoes from './AbaPadronizadaAvaliacoes';
import TelaPerfilUsuario from './TelaPerfilUsuario';
import TrackingPanel from './TrackingPanel';

export default function PainelBarberMovePremium({ token: tokenProp, logout: logoutProp, API_URL: apiUrlProp, notify: notifyProp }) {
  const { user, logout: ctxLogout, token: ctxToken, notify: ctxNotify } = useApp();
  const token = tokenProp || ctxToken;
  const logout = logoutProp || ctxLogout;
  const notify = notifyProp || ctxNotify || ((msg, type) => console.log(`[${type}]`, msg));
  const API_URL = apiUrlProp || getApiBaseUrl();

  const TABS = ['inicio', 'chamados', 'avaliar', 'perfil', 'carteira'];
  const [tab, setTab] = useState(() => {
    const s = localStorage.getItem('barbeiro_dashboard_tab') || 'inicio';
    return TABS.includes(s) ? s : 'inicio';
  });
  const [chamados, setChamados] = useState([]);
  const [chamadoAtivo, setChamadoAtivo] = useState(null);
  const [minhaPosicao, setMinhaPosicao] = useState(null);
  const [ganhos, setGanhos] = useState(null);
  const [perfil, setPerfil] = useState(user || null);
  const [vagasRelampago, setVagasRelampago] = useState([]);
  const [aceitandoVagaId, setAceitandoVagaId] = useState(null);

  // Buscar perfil completo
  useEffect(() => {
    if (!token) return;
    fetch(`${API_URL}/api/v1/usuarios/perfil-completo`, {
      headers: { Authorization: `Bearer ${token}` },
    }).then(r => r.ok ? r.json() : null).then(d => { if (d) setPerfil(d); }).catch(() => {});
  }, [token, API_URL]);

  useEffect(() => { localStorage.setItem('barbeiro_dashboard_tab', tab); }, [tab]);

  // GPS contínuo
  useEffect(() => {
    if (!navigator.geolocation) return;
    const id = navigator.geolocation.watchPosition(
      (pos) => setMinhaPosicao({ latitude: pos.coords.latitude, longitude: pos.coords.longitude }),
      () => {},
      { enableHighAccuracy: true, maximumAge: 5000 }
    );
    return () => navigator.geolocation.clearWatch(id);
  }, []);

  const carregarChamados = useCallback(async () => {
    if (!token) return;
    try {
      const res = await fetch(`${API_URL}/api/v1/barbeiro/trabalhos`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!res.ok) return;
      const data = await res.json();
      const lista = Array.isArray(data) ? data : [];
      setChamados(lista);
      const ativo = lista.find(c => !['concluido','concluído','cancelado'].includes((c.status||'').toLowerCase()));
      setChamadoAtivo(ativo || null);
    } catch (_) {}
  }, [token, API_URL]);

  const carregarGanhos = useCallback(async () => {
    if (!token) return;
    try {
      const res = await fetch(`${API_URL}/api/v1/freelancer/comissoes/relatorio`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (res.ok) setGanhos(await res.json());
    } catch (_) {}
  }, [token, API_URL]);

  const carregarVagasRelampago = useCallback(async () => {
    if (!token) return;
    try {
      const res = await fetch(`${API_URL}/api/v1/on-demand/cadeiras-acionadas/ativas`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!res.ok) {
        setVagasRelampago([]);
        return;
      }

      const data = await res.json();
      setVagasRelampago(Array.isArray(data) ? data : []);
    } catch (_) {
      setVagasRelampago([]);
    }
  }, [token, API_URL]);

  const aceitarVagaRelampago = async (vagaId) => {
    if (!vagaId) return;
    try {
      setAceitandoVagaId(vagaId);
      const res = await fetch(`${API_URL}/api/v1/on-demand/cadeiras-acionadas/${vagaId}/aceitar-barbeiro`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}` },
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) {
        throw new Error(data?.detail || 'Não foi possível aceitar a vaga relâmpago');
      }

      notify('Vaga relâmpago assumida! Você tem 10 minutos para chegar.', 'success');
      setVagasRelampago((prev) => prev.filter((vaga) => Number(vaga.id) !== Number(vagaId)));
    } catch (err) {
      notify(err?.message || 'Erro ao assumir vaga relâmpago', 'error');
    } finally {
      setAceitandoVagaId(null);
    }
  };

  useEffect(() => { carregarChamados(); }, [carregarChamados]);
  useEffect(() => { carregarVagasRelampago(); }, [carregarVagasRelampago]);
  useEffect(() => {
    const t = setInterval(carregarChamados, 8000);
    return () => clearInterval(t);
  }, [carregarChamados]);
  useEffect(() => {
    const t = setInterval(carregarVagasRelampago, 8000);
    return () => clearInterval(t);
  }, [carregarVagasRelampago]);

  useEffect(() => {
    if (!token) return;
    const wsUrl = import.meta.env.VITE_WS_URL?.trim() || getWsBaseUrl();
    let ws = null;

    try {
      ws = new WebSocket(wsUrl);
      ws.onmessage = (event) => {
        try {
          const payload = JSON.parse(event.data);
          if (payload?.type === 'cadeira_acionada_aberta') {
            const vaga = payload?.vaga;
            if (!vaga?.id) return;
            setVagasRelampago((prev) => {
              const semAtual = prev.filter((item) => Number(item.id) !== Number(vaga.id));
              return [vaga, ...semAtual];
            });
            return;
          }

          if (payload?.type === 'cadeira_acionada_fechada') {
            const vaga = payload?.vaga;
            if (!vaga?.id) return;
            setVagasRelampago((prev) => prev.filter((item) => Number(item.id) !== Number(vaga.id)));
          }
        } catch (_) {
          // ignora mensagens nao json
        }
      };
    } catch (_) {
      // sem websocket, polling continua
    }

    return () => {
      if (ws) {
        try { ws.close(); } catch (_) { /* noop */ }
      }
    };
  }, [token]);

  const aceitarChamado = async (id) => {
    try {
      const res = await fetch(`${API_URL}/api/v1/chamados/${id}/aceitar`, {
        method: 'PUT', headers: { Authorization: `Bearer ${token}` },
      });
      if (res.ok) { notify('Chamado aceito!', 'success'); carregarChamados(); }
      else notify('Erro ao aceitar', 'error');
    } catch (_) { notify('Erro de conexão', 'error'); }
  };

  const finalizarChamado = async (id) => {
    try {
      const res = await fetch(`${API_URL}/api/v1/chamados/${id}/finalizar`, {
        method: 'PUT', headers: { Authorization: `Bearer ${token}` },
      });
      if (res.ok) { notify('Serviço finalizado!', 'success'); carregarChamados(); }
      else notify('Erro ao finalizar', 'error');
    } catch (_) { notify('Erro de conexão', 'error'); }
  };

  const statusColor = (s) => {
    const st = (s||'').toLowerCase();
    if (st === 'pendente') return 'text-yellow-400 bg-yellow-500/10 border-yellow-500/30';
    if (['aceito','confirmado','em_atendimento'].includes(st)) return 'text-green-400 bg-green-500/10 border-green-500/30';
    if (st.includes('conclu')) return 'text-blue-400 bg-blue-500/10 border-blue-500/30';
    return 'text-zinc-400 bg-zinc-500/10 border-zinc-500/30';
  };

  return (
    <div className="min-h-[100dvh] w-full bg-[#050505] text-white flex justify-center">
      <div className="w-full max-w-[430px] flex flex-col min-h-[100dvh] bg-[#050505]">

        {/* HEADER */}
        <div className="sticky top-0 z-20 px-3 pt-3 pb-2 bg-[#050505]/95 backdrop-blur-xl">
          <div className="flex justify-between items-center rounded-2xl border border-zinc-800/80 bg-zinc-950/90 px-4 py-3">
            <div>
              <p className="text-[10px] uppercase tracking-widest text-zinc-500">Freelancer</p>
              <h1 className="text-base font-black text-white">✂️ {perfil?.nome || 'Barbeiro'}</h1>
            </div>
            <button onClick={logout} className="h-10 w-10 rounded-full bg-zinc-900 border border-zinc-800 flex items-center justify-center text-zinc-400 hover:text-white transition-colors">
              <LogOut size={16} />
            </button>
          </div>
        </div>

        {/* CONTEÚDO */}
        <div className="flex-1 overflow-y-auto pb-[calc(5rem+env(safe-area-inset-bottom))]">

          {/* INÍCIO */}
          {tab === 'inicio' && (
            <div className="p-4 space-y-4">
              <div className="rounded-2xl border border-zinc-800 bg-zinc-900 p-5 space-y-3">
                <div className="flex items-center gap-3">
                  <div className="w-12 h-12 rounded-2xl bg-green-500/15 border border-green-500/30 flex items-center justify-center text-2xl">✂️</div>
                  <div>
                    <p className="text-xs text-zinc-500 uppercase tracking-widest">Bem-vindo</p>
                    <h2 className="text-lg font-black">Olá, {perfil?.nome?.split(' ')[0] || 'Freelancer'}!</h2>
                  </div>
                </div>
                {chamadoAtivo && (
                  <div className="rounded-xl border border-amber-500/30 bg-amber-500/10 p-3 text-sm">
                    <p className="font-bold text-amber-300">🔔 Chamado ativo: #{chamadoAtivo.id}</p>
                    <p className="text-xs text-zinc-400 mt-0.5">{chamadoAtivo.servico_nome || chamadoAtivo.descricao}</p>
                  </div>
                )}
              </div>
              <div className="grid grid-cols-2 gap-3">
                <button onClick={() => setTab('chamados')} className="rounded-2xl border border-zinc-800 bg-zinc-900 p-4 flex flex-col items-center gap-2 hover:border-orange-500 transition-colors">
                  <ClipboardList size={22} className="text-orange-400" />
                  <span className="text-sm font-bold">Chamados</span>
                  <span className="text-xs text-zinc-500">{chamados.length} no histórico</span>
                </button>
                <button onClick={() => setTab('avaliar')} className="rounded-2xl border border-zinc-800 bg-zinc-900 p-4 flex flex-col items-center gap-2 hover:border-orange-500 transition-colors">
                  <Star size={22} className="text-yellow-400" />
                  <span className="text-sm font-bold">Avaliar</span>
                  <span className="text-xs text-zinc-500">Suas avaliações</span>
                </button>
                <button onClick={() => setTab('perfil')} className="rounded-2xl border border-zinc-800 bg-zinc-900 p-4 flex flex-col items-center gap-2 hover:border-orange-500 transition-colors">
                  <User size={22} className="text-purple-400" />
                  <span className="text-sm font-bold">Perfil</span>
                  <span className="text-xs text-zinc-500">Seus dados</span>
                </button>
                <button onClick={() => { setTab('carteira'); carregarGanhos(); }} className="rounded-2xl border border-zinc-800 bg-zinc-900 p-4 flex flex-col items-center gap-2 hover:border-orange-500 transition-colors">
                  <CreditCard size={22} className="text-emerald-400" />
                  <span className="text-sm font-bold">Carteira</span>
                  <span className="text-xs text-zinc-500">Ganhos e comissões</span>
                </button>
              </div>
            </div>
          )}

          {/* CHAMADOS */}
          {tab === 'chamados' && (
            <div className="p-4 space-y-3">
              <h2 className="text-xs font-black text-zinc-500 uppercase tracking-widest">Chamados</h2>

              {vagasRelampago.length > 0 && (
                <div className="rounded-2xl border border-red-500/30 bg-red-500/10 p-4 space-y-3">
                  <p className="text-xs font-bold text-red-300 uppercase tracking-wide">⚡ Vagas relâmpago próximas</p>
                  <div className="space-y-2">
                    {vagasRelampago.slice(0, 5).map((vaga) => (
                      <div key={vaga.id} className="rounded-xl border border-zinc-700 bg-zinc-900/80 p-3">
                        <div className="flex items-center justify-between gap-3">
                          <div>
                            <p className="text-sm font-bold text-white">{vaga.barbearia_nome || 'Barbearia'} {vaga.cadeira_id ? `• Cadeira ${vaga.cadeira_id}` : ''}</p>
                            <p className="text-xs text-zinc-400">ETA atual: {vaga.eta_min_usuario_atual ?? '-'} min</p>
                          </div>
                          <button
                            type="button"
                            onClick={() => aceitarVagaRelampago(vaga.id)}
                            disabled={aceitandoVagaId === vaga.id}
                            className="rounded-lg bg-red-600 hover:bg-red-500 disabled:bg-red-800/50 text-white px-3 py-2 text-xs font-bold"
                          >
                            {aceitandoVagaId === vaga.id ? 'Assumindo...' : 'Assumir'}
                          </button>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {chamadoAtivo && (
                <div className="rounded-2xl border border-green-500/30 bg-green-500/10 p-4 space-y-3">
                  <p className="text-xs font-bold text-green-300 uppercase tracking-wide">🚀 Chamado Ativo #{chamadoAtivo.id}</p>
                  <p className="text-sm font-bold text-white">{chamadoAtivo.servico_nome || chamadoAtivo.descricao}</p>
                  <p className="text-xs text-zinc-400">Cliente: {chamadoAtivo.cliente_nome || chamadoAtivo.nome_cliente}</p>
                  <p className="text-xs text-zinc-400">Barbearia: {chamadoAtivo.nome_barbearia}</p>
                  <TrackingPanel
                    chamado={chamadoAtivo}
                    token={token}
                    API_URL={API_URL}
                    notify={notify}
                    modo="barbeiro"
                    minhaPosicao={minhaPosicao}
                  />
                  {['pendente'].includes((chamadoAtivo.status||'').toLowerCase()) && (
                    <button onClick={() => aceitarChamado(chamadoAtivo.id)} className="w-full bg-green-600 hover:bg-green-700 text-white font-black rounded-xl py-3 text-sm">
                      ✅ Aceitar Chamado
                    </button>
                  )}
                  {['aceito','confirmado','em_atendimento'].includes((chamadoAtivo.status||'').toLowerCase()) && (
                    <button onClick={() => finalizarChamado(chamadoAtivo.id)} className="w-full bg-blue-600 hover:bg-blue-700 text-white font-black rounded-xl py-3 text-sm">
                      🏁 Finalizar Serviço
                    </button>
                  )}
                </div>
              )}

              {chamados.length === 0 ? (
                <div className="text-center py-12">
                  <p className="text-zinc-600 text-sm">Nenhum chamado ainda</p>
                </div>
              ) : (
                <div className="space-y-2">
                  {chamados.map(c => (
                    <div key={c.id} className="rounded-xl border border-zinc-800 bg-zinc-900 p-3.5 space-y-2">
                      <div className="flex justify-between items-start">
                        <div className="min-w-0 pr-2">
                          <p className="font-bold text-sm truncate">{c.servico_nome || c.descricao || 'Serviço'}</p>
                          <p className="text-xs text-zinc-400 truncate">Cliente: {c.cliente_nome || c.nome_cliente}</p>
                          <p className="text-xs text-zinc-400 truncate">{c.nome_barbearia || 'Barbearia'}</p>
                        </div>
                        <span className={`text-[10px] font-bold px-2 py-1 rounded-full border ${statusColor(c.status)}`}>
                          {(c.status||'').toUpperCase()}
                        </span>
                      </div>
                      <div className="flex justify-between items-center text-xs text-zinc-500">
                        <span>#{c.id}</span>
                        <span className="text-green-400 font-bold">R$ {Number(c.valor||0).toFixed(2)}</span>
                      </div>
                      {(c.status||'').toLowerCase() === 'pendente' && (
                        <button onClick={() => aceitarChamado(c.id)} className="w-full bg-green-600 hover:bg-green-700 text-white font-black rounded-xl py-2 text-xs">
                          ✅ Aceitar
                        </button>
                      )}
                      {['aceito','confirmado','em_atendimento'].includes((c.status||'').toLowerCase()) && (
                        <button onClick={() => finalizarChamado(c.id)} className="w-full bg-blue-600 hover:bg-blue-700 text-white font-black rounded-xl py-2 text-xs">
                          🏁 Finalizar
                        </button>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          {/* AVALIAR */}
          {tab === 'avaliar' && (
            <div className="p-4">
              {perfil ? (
                <AbaPadronizadaAvaliacoes
                  usuarioId={perfil.id}
                  tipoUsuario="barbeiro"
                  nomeUsuario={perfil.nome}
                  API_URL={API_URL}
                  token={token}
                  notify={notify}
                />
              ) : (
                <p className="text-center text-zinc-500 text-sm py-12">Carregando...</p>
              )}
            </div>
          )}

          {/* PERFIL */}
          {tab === 'perfil' && (
            <div className="p-4">
              <TelaPerfilUsuario userType="barbeiro" token={token} onLogout={logout} onNotify={notify} />
            </div>
          )}

          {/* CARTEIRA */}
          {tab === 'carteira' && (
            <div className="p-4 space-y-4">
              <h2 className="text-xs font-black text-zinc-500 uppercase tracking-widest">Carteira</h2>
              <div className="grid grid-cols-2 gap-3">
                <div className="rounded-2xl border border-zinc-800 bg-zinc-900 p-4">
                  <p className="text-xs text-zinc-500 uppercase tracking-wide mb-1">Ganhos brutos</p>
                  <p className="text-xl font-black text-white">R$ {Number(ganhos?.ganhos_brutos||0).toFixed(2)}</p>
                </div>
                <div className="rounded-2xl border border-zinc-800 bg-zinc-900 p-4">
                  <p className="text-xs text-zinc-500 uppercase tracking-wide mb-1">Comissões</p>
                  <p className="text-xl font-black text-red-400">R$ {Number(ganhos?.total_comissoes||0).toFixed(2)}</p>
                </div>
              </div>
              <div className="rounded-2xl border border-green-500/30 bg-green-500/10 p-5 text-center">
                <p className="text-xs text-zinc-400 uppercase tracking-wide mb-1">Ganhos líquidos</p>
                <p className="text-3xl font-black text-green-400">R$ {Number(ganhos?.ganhos_liquidos||0).toFixed(2)}</p>
              </div>
              <div className="rounded-2xl border border-zinc-800 bg-zinc-900 p-4 space-y-2 text-sm">
                <div className="flex justify-between"><span className="text-zinc-400">Atendimentos</span><span className="font-bold">{ganhos?.total_atendimentos||0}</span></div>
                <div className="flex justify-between"><span className="text-zinc-400">Via app</span><span className="font-bold">{ganhos?.total_atendimentos_app||0}</span></div>
                <div className="flex justify-between"><span className="text-zinc-400">Taxa app</span><span className="font-bold text-orange-400">4%</span></div>
              </div>
              <button onClick={carregarGanhos} className="w-full rounded-xl border border-zinc-800 bg-zinc-900 py-3 text-sm font-bold hover:bg-zinc-800 transition-colors">
                🔄 Atualizar
              </button>
            </div>
          )}
        </div>

        {/* NAVBAR */}
        <div className="fixed bottom-0 left-0 right-0 mx-auto w-full max-w-[430px] h-[calc(4.4rem+env(safe-area-inset-bottom))] pb-[env(safe-area-inset-bottom)] bg-[#121214] border-t border-zinc-900 flex justify-around items-center z-50">
          {[
            { id: 'inicio', icon: <Home size={16}/>, label: 'Início' },
            { id: 'chamados', icon: <ClipboardList size={16}/>, label: 'Chamados' },
            { id: 'avaliar', icon: <Star size={16}/>, label: 'Avaliar' },
            { id: 'perfil', icon: <User size={16}/>, label: 'Perfil' },
            { id: 'carteira', icon: <CreditCard size={16}/>, label: 'Carteira' },
          ].map(item => (
            <button
              key={item.id}
              onClick={() => { setTab(item.id); if (item.id === 'carteira') carregarGanhos(); }}
              className={`flex flex-col items-center justify-center gap-1 flex-1 h-full text-center transition-colors ${tab === item.id ? 'text-orange-500' : 'text-zinc-500 hover:text-zinc-200'}`}
            >
              {item.icon}
              <span className="text-[10px] font-bold">{item.label}</span>
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}
