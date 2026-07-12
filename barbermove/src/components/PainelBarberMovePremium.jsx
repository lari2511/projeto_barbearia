import { useState, useEffect, useCallback, useRef } from 'react';
import { Home, ClipboardList, Star, User, CreditCard, LogOut, CheckCircle, XCircle, DollarSign, Pause, Play, Copy } from 'lucide-react';
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
  const [pixQuitacao, setPixQuitacao] = useState(null);
  const [processandoQuitacao, setProcessandoQuitacao] = useState(false);
  const [processandoSaque, setProcessandoSaque] = useState(false);
  const [perfil, setPerfil] = useState(user || null);
  const [vagasRelampago, setVagasRelampago] = useState([]);
  const [aceitandoVagaId, setAceitandoVagaId] = useState(null);
  const [agoraMs, setAgoraMs] = useState(Date.now());
  const [timerPausado, setTimerPausado] = useState(false);
  const [pausadoEmMs, setPausadoEmMs] = useState(null);
  const [pausaAcumuladaMs, setPausaAcumuladaMs] = useState(0);
  const [alternandoPausa, setAlternandoPausa] = useState(false);
  const scrollRef = useRef(null);
  const ultimaSyncGpsRef = useRef(0);

  const atualizarStatusRadar = useCallback(async (isOnline) => {
    if (!token) return;
    try {
      await fetch(`${API_URL}/api/v1/on-demand/ligar-radar`, {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ is_online: isOnline }),
      });
    } catch (_) {
      // polling continua funcionando mesmo sem sincronizar status
    }
  }, [token, API_URL]);

  const handleLogout = useCallback(async () => {
    await atualizarStatusRadar(false);
    logout();
  }, [atualizarStatusRadar, logout]);

  const obterChavePausa = useCallback((id) => `barbermove.timer.pause.${id}`, []);

  const formatarDuracao = useCallback((totalSegundos) => {
    const seg = Math.max(0, Number(totalSegundos) || 0);
    const horas = Math.floor(seg / 3600);
    const minutos = Math.floor((seg % 3600) / 60);
    const segundos = seg % 60;
    if (horas > 0) {
      return `${String(horas).padStart(2, '0')}:${String(minutos).padStart(2, '0')}:${String(segundos).padStart(2, '0')}`;
    }
    return `${String(minutos).padStart(2, '0')}:${String(segundos).padStart(2, '0')}`;
  }, []);

  const calcularTempoRestanteMs = useCallback((chamado) => {
    if (!chamado) return null;
    const fim = chamado.data_hora_fim ? new Date(chamado.data_hora_fim).getTime() : NaN;
    if (!Number.isFinite(fim)) return null;

    const pausaAtualMs = timerPausado && pausadoEmMs ? (agoraMs - pausadoEmMs) : 0;
    return fim - agoraMs + pausaAcumuladaMs + pausaAtualMs;
  }, [agoraMs, timerPausado, pausadoEmMs, pausaAcumuladaMs]);

  const renderCronometro = useCallback((chamado, compacto = false) => {
    if (!chamado) return null;

    const status = String(chamado.status || '').toLowerCase();
    if (status !== 'em_atendimento') return null;

    const fim = chamado.data_hora_fim ? new Date(chamado.data_hora_fim).getTime() : NaN;
    if (!Number.isFinite(fim)) return null;

    const isChamadoAtivo = Number(chamadoAtivo?.id) === Number(chamado.id);
    const pausaAtualMs = isChamadoAtivo && timerPausado && pausadoEmMs ? (agoraMs - pausadoEmMs) : 0;
    const acumuladoMs = isChamadoAtivo ? pausaAcumuladaMs : 0;
    const restanteMs = fim - agoraMs + acumuladoMs + pausaAtualMs;
    const restanteSegundos = Math.ceil(Math.max(0, restanteMs) / 1000);
    const dentroJanelaProximo = restanteSegundos <= (10 * 60);

    return (
      <div className={`rounded-xl border border-zinc-700 bg-zinc-950/70 ${compacto ? 'p-2' : 'p-3'} space-y-2`}>
        <div className="flex items-center justify-between">
          <p className={`font-bold uppercase tracking-wide text-zinc-400 ${compacto ? 'text-[10px]' : 'text-[11px]'}`}>Cronometro</p>
          <span className={`text-[10px] font-bold px-2 py-1 rounded-full ${dentroJanelaProximo ? 'bg-emerald-500/20 text-emerald-300' : 'bg-amber-500/20 text-amber-300'}`}>
            {dentroJanelaProximo ? 'Liberado em 10 min' : 'Aguardando 10 min'}
          </span>
        </div>
        <p className={`${compacto ? 'text-lg' : 'text-2xl'} font-black text-white`}>{formatarDuracao(restanteSegundos)}</p>
      </div>
    );
  }, [agoraMs, chamadoAtivo?.id, formatarDuracao, pausaAcumuladaMs, pausadoEmMs, timerPausado]);

  const carregarPerfil = useCallback(async () => {
    if (!token) return;
    try {
      const res = await fetch(`${API_URL}/api/v1/usuarios/perfil-completo`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!res.ok) return;
      const data = await res.json().catch(() => null);
      if (data) setPerfil(data);
    } catch (_) {
      // sem bloqueio de UX por falha pontual
    }
  }, [token, API_URL]);
  
  // Buscar perfil completo
  useEffect(() => {
    carregarPerfil();
  }, [carregarPerfil]);

  useEffect(() => { localStorage.setItem('barbeiro_dashboard_tab', tab); }, [tab]);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTo({ top: 0, behavior: 'auto' });
    }
  }, [tab]);

  useEffect(() => {
    const t = setInterval(() => setAgoraMs(Date.now()), 1000);
    return () => clearInterval(t);
  }, []);

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

  useEffect(() => {
    if (!token) return;
    atualizarStatusRadar(true);
  }, [token, atualizarStatusRadar]);

  useEffect(() => {
    if (!token || !minhaPosicao?.latitude || !minhaPosicao?.longitude) return;

    const agora = Date.now();
    if (agora - ultimaSyncGpsRef.current < 8000) return;
    ultimaSyncGpsRef.current = agora;

    fetch(`${API_URL}/api/v1/on-demand/atualizar-localizacao`, {
      method: 'POST',
      headers: {
        Authorization: `Bearer ${token}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        latitude: minhaPosicao.latitude,
        longitude: minhaPosicao.longitude,
      }),
    }).catch(() => {
      // mantem silencioso para nao poluir UX com erro intermitente de GPS/rede
    });
  }, [token, API_URL, minhaPosicao]);

  const carregarChamados = useCallback(async () => {
    if (!token) return;
    try {
      let res = await fetch(`${API_URL}/api/v1/barbeiro/agendamentos/meus`, {
        headers: { Authorization: `Bearer ${token}` },
      });

      // Compatibilidade com ambientes legados: se falhar, tenta chamados abertos.
      if (!res.ok) {
        res = await fetch(`${API_URL}/api/v1/chamados/abertos`, {
          headers: { Authorization: `Bearer ${token}` },
        });
      }

      if (!res.ok) {
        setChamados([]);
        setChamadoAtivo(null);
        return;
      }

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

  const copiarTexto = useCallback(async (texto) => {
    try {
      await navigator.clipboard.writeText(texto || '');
      notify('Código PIX copiado', 'success');
    } catch (_err) {
      notify('Não foi possível copiar', 'error');
    }
  }, [notify]);

  const gerarPixQuitacao = async () => {
    try {
      setProcessandoQuitacao(true);
      const res = await fetch(`${API_URL}/api/v1/freelancer/carteira/quitacao/pix-gerar`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}` },
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) throw new Error(data?.detail || 'Erro ao gerar PIX de quitação');
      setPixQuitacao(data);
      notify('PIX de quitação gerado', 'success');
    } catch (err) {
      notify(err?.message || 'Falha ao gerar PIX', 'error');
    } finally {
      setProcessandoQuitacao(false);
    }
  };

  const confirmarQuitacao = async () => {
    try {
      if (!pixQuitacao?.valor_devedor) {
        notify('Gere o PIX de quitação primeiro', 'warning');
        return;
      }
      setProcessandoQuitacao(true);
      const res = await fetch(`${API_URL}/api/v1/freelancer/carteira/quitacao/confirmar`, {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ valor: Number(pixQuitacao.valor_devedor) }),
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) throw new Error(data?.detail || 'Erro ao confirmar quitação');
      notify('Saldo devedor quitado e app liberado', 'success');
      setPixQuitacao(null);
      carregarGanhos();
    } catch (err) {
      notify(err?.message || 'Falha ao confirmar quitação', 'error');
    } finally {
      setProcessandoQuitacao(false);
    }
  };

  const solicitarSaquePix = async () => {
    try {
      const saldo = Number(ganhos?.saldo_carteira || 0);
      if (saldo <= 0) {
        notify('Sem saldo positivo para saque', 'warning');
        return;
      }
      const chave = window.prompt('Informe sua chave PIX para saque:');
      if (!chave || !chave.trim()) return;

      setProcessandoSaque(true);
      const res = await fetch(`${API_URL}/api/v1/freelancer/carteira/saque/pix`, {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ chave_pix: chave.trim(), valor: saldo }),
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) throw new Error(data?.detail || 'Erro ao solicitar saque');
      notify('Saque solicitado via PIX', 'success');
      carregarGanhos();
    } catch (err) {
      notify(err?.message || 'Falha ao solicitar saque', 'error');
    } finally {
      setProcessandoSaque(false);
    }
  };

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
    if (!vagaId || bloqueadoFinanceiro) return;
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
      carregarPerfil();
    } catch (err) {
      notify(err?.message || 'Erro ao assumir vaga relâmpago', 'error');
    } finally {
      setAceitandoVagaId(null);
    }
  };

  useEffect(() => { carregarChamados(); }, [carregarChamados]);
  useEffect(() => { carregarGanhos(); }, [carregarGanhos]);
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

  useEffect(() => {
    if (!chamadoAtivo?.id) {
      setTimerPausado(false);
      setPausadoEmMs(null);
      setPausaAcumuladaMs(0);
      return;
    }

    try {
      const raw = localStorage.getItem(obterChavePausa(chamadoAtivo.id));
      if (!raw) {
        setTimerPausado(false);
        setPausadoEmMs(null);
        setPausaAcumuladaMs(0);
        return;
      }

      const parsed = JSON.parse(raw);
      const pausado = parsed?.timerPausado === true;
      const pausadoEm = Number(parsed?.pausadoEmMs);
      const acumulado = Number(parsed?.pausaAcumuladaMs);

      setTimerPausado(pausado);
      setPausadoEmMs(Number.isFinite(pausadoEm) ? pausadoEm : null);
      setPausaAcumuladaMs(Number.isFinite(acumulado) ? acumulado : 0);
    } catch (_err) {
      setTimerPausado(false);
      setPausadoEmMs(null);
      setPausaAcumuladaMs(0);
    }
  }, [chamadoAtivo?.id, obterChavePausa]);

  useEffect(() => {
    if (!chamadoAtivo?.id) return;
    try {
      localStorage.setItem(obterChavePausa(chamadoAtivo.id), JSON.stringify({
        timerPausado,
        pausadoEmMs,
        pausaAcumuladaMs,
      }));
    } catch (_err) {
      // Sem persistencia, segue fluxo normal.
    }
  }, [chamadoAtivo?.id, timerPausado, pausadoEmMs, pausaAcumuladaMs, obterChavePausa]);

  const togglePausaTemporizador = async () => {
    if (!token || !chamadoAtivo?.id || alternandoPausa) return;
    try {
      setAlternandoPausa(true);
      const pausarAgora = !timerPausado;
      const res = await fetch(`${API_URL}/api/v1/freelancer/pausar?pausar=${pausarAgora ? 'true' : 'false'}`, {
        method: 'PATCH',
        headers: { Authorization: `Bearer ${token}` },
      });

      if (!res.ok) {
        const errData = await res.json().catch(() => ({}));
        throw new Error(errData?.detail || 'Não foi possível alterar o status de pausa');
      }

      const agoraLocal = Date.now();
      if (pausarAgora) {
        setTimerPausado(true);
        setPausadoEmMs(agoraLocal);
        notify('Temporizador pausado. Novos chamados ficarão bloqueados até retomar.', 'warning');
      } else {
        const delta = pausadoEmMs ? Math.max(0, agoraLocal - pausadoEmMs) : 0;
        setPausaAcumuladaMs((prev) => prev + delta);
        setPausadoEmMs(null);
        setTimerPausado(false);
        notify('Temporizador retomado.', 'success');
      }
    } catch (err) {
      notify(err?.message || 'Falha ao pausar/retomar temporizador', 'error');
    } finally {
      setAlternandoPausa(false);
    }
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

  const bloqueadoFinanceiro = Boolean(ganhos?.bloqueado_financeiro);
  const saldoCarteiraAtual = Number(ganhos?.saldo_carteira || 0);

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
            <button onClick={handleLogout} className="h-10 w-10 rounded-full bg-zinc-900 border border-zinc-800 flex items-center justify-center text-zinc-400 hover:text-white transition-colors">
              <LogOut size={16} />
            </button>
          </div>
        </div>

        {/* CONTEÚDO */}
        <div ref={scrollRef} className="flex-1 overflow-y-auto pb-[calc(5rem+env(safe-area-inset-bottom))]">

          {/* INÍCIO */}
          {tab === 'inicio' && (
            <div className="p-4 space-y-4">
              <div className="rounded-2xl border border-zinc-800 bg-zinc-900 p-5 space-y-3">
                <div className="flex items-center gap-3">
                  <div className="w-12 h-12 rounded-2xl bg-green-500/15 border border-green-500/30 flex items-center justify-center text-2xl">✂️</div>
                  <div>
                    <p className="text-xs text-zinc-500 uppercase tracking-widest">Bem-vindo</p>
                    <h2 className="text-lg font-black">Olá, {perfil?.nome?.split(' ')[0] || 'Freelancer'}!</h2>
                    <p className="text-[11px] text-zinc-400 mt-0.5">
                      {perfil?.presente_em_local && perfil?.barbearia_atual_nome
                        ? `Presente em ${perfil.barbearia_atual_nome}`
                        : 'Disponível na região'}
                    </p>
                  </div>
                </div>
                {chamadoAtivo && (
                  <div className="rounded-xl border border-amber-500/30 bg-amber-500/10 p-3 text-sm">
                    <p className="font-bold text-amber-300">🔔 Chamado ativo: #{chamadoAtivo.id}</p>
                    <p className="text-xs text-zinc-400 mt-0.5">{chamadoAtivo.servico_nome || chamadoAtivo.descricao}</p>
                    <div className="mt-2">{renderCronometro(chamadoAtivo, true)}</div>
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

              <div className="rounded-2xl border border-orange-500/30 bg-orange-500/10 p-4 space-y-3">
                <div className="flex items-center justify-between gap-3">
                  <div>
                    <p className="text-xs font-black uppercase tracking-widest text-orange-300">Vagas anunciadas</p>
                    <p className="text-sm text-zinc-300">As vagas da barbearia aparecem aqui na abertura do painel.</p>
                  </div>
                  <span className="rounded-full border border-orange-500/40 bg-orange-500/15 px-3 py-1 text-xs font-bold text-orange-200">
                    {vagasRelampago.length}
                  </span>
                </div>

                {vagasRelampago.length > 0 ? (
                  <div className="space-y-2">
                    {vagasRelampago.slice(0, 3).map((vaga) => {
                      const status = String(vaga.status || '').toLowerCase();
                      const podeAssumir = status === 'disponivel' && !bloqueadoFinanceiro;
                      return (
                        <div key={vaga.id} className="rounded-xl border border-zinc-800 bg-zinc-950/70 p-3">
                          <div className="flex items-start justify-between gap-3">
                            <div className="min-w-0">
                              <p className="text-sm font-bold text-white truncate">{vaga.barbearia_nome || 'Barbearia'} {vaga.cadeira_id ? `• Cadeira ${vaga.cadeira_id}` : ''}</p>
                              <p className="text-xs text-zinc-400 truncate">Status: {status || 'desconhecido'}</p>
                            </div>
                            <div className="flex flex-col items-end gap-2">
                              <span className={`rounded-full px-2.5 py-1 text-[10px] font-black uppercase tracking-wide ${status === 'disponivel' ? 'bg-emerald-500/15 text-emerald-300 border border-emerald-500/30' : 'bg-zinc-800 text-zinc-300 border border-zinc-700'}`}>
                                {status === 'disponivel' ? 'Disponível' : status || 'Aberta'}
                              </span>
                              <button
                                type="button"
                                onClick={() => aceitarVagaRelampago(vaga.id)}
                                disabled={!podeAssumir || aceitandoVagaId === vaga.id}
                                className="rounded-md bg-orange-600 hover:bg-orange-500 disabled:bg-zinc-700 disabled:text-zinc-400 text-white px-2.5 py-1.5 text-[11px] font-bold"
                              >
                                {bloqueadoFinanceiro ? 'Bloqueado' : (aceitandoVagaId === vaga.id ? 'Assumindo...' : 'Assumir')}
                              </button>
                            </div>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                ) : (
                  <p className="text-xs text-zinc-400">Nenhuma vaga anunciada no momento.</p>
                )}
              </div>
            </div>
          )}

          {/* CHAMADOS */}
          {tab === 'chamados' && (
            <div className="p-4 space-y-3">
              <h2 className="text-xs font-black text-zinc-500 uppercase tracking-widest">Chamados</h2>

              <div className="rounded-2xl border border-zinc-800 bg-zinc-900 p-3">
                <p className="text-[11px] text-zinc-400 uppercase tracking-wide">Status atual</p>
                <p className="text-sm font-bold text-white mt-1">
                  {perfil?.presente_em_local && perfil?.barbearia_atual_nome
                    ? `Presente em ${perfil.barbearia_atual_nome}`
                    : 'Disponível na região'}
                </p>
              </div>

              {bloqueadoFinanceiro && (
                <div className="rounded-2xl border border-red-500/40 bg-red-500/10 p-4">
                  <p className="text-xs font-bold text-red-300 uppercase tracking-wide">Bloqueado por saldo devedor</p>
                  <p className="text-sm text-red-100 mt-1">Seu saldo atual é R$ {saldoCarteiraAtual.toFixed(2)}. Quite a fatura na aba Carteira para voltar a aceitar chamados.</p>
                </div>
              )}

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
                            onClick={() => !bloqueadoFinanceiro && aceitarVagaRelampago(vaga.id)}
                            disabled={aceitandoVagaId === vaga.id || bloqueadoFinanceiro}
                            className="rounded-lg bg-red-600 hover:bg-red-500 disabled:bg-red-800/50 disabled:text-red-200/80 text-white px-3 py-2 text-xs font-bold"
                          >
                            {bloqueadoFinanceiro ? '⛔ Bloqueado' : (aceitandoVagaId === vaga.id ? 'Assumindo...' : 'Assumir')}
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
                  <div className="space-y-2">
                    {renderCronometro(chamadoAtivo)}
                    {(String(chamadoAtivo.status || '').toLowerCase() === 'em_atendimento') && (
                      <div className="flex justify-end">
                        <button
                          onClick={togglePausaTemporizador}
                          disabled={alternandoPausa}
                          className={`inline-flex items-center gap-2 rounded-lg px-3 py-2 text-xs font-bold text-white ${timerPausado ? 'bg-emerald-600 hover:bg-emerald-500' : 'bg-amber-600 hover:bg-amber-500'} disabled:opacity-60`}
                        >
                          {timerPausado ? <Play size={12} /> : <Pause size={12} />}
                          {alternandoPausa ? 'Atualizando...' : (timerPausado ? 'Retomar' : 'Pausar')}
                        </button>
                      </div>
                    )}
                  </div>
                  <TrackingPanel
                    chamado={chamadoAtivo}
                    token={token}
                    API_URL={API_URL}
                    notify={notify}
                    modo="barbeiro"
                    minhaPosicao={minhaPosicao}
                  />
                  {['pendente'].includes((chamadoAtivo.status||'').toLowerCase()) && (
                    <button
                      onClick={() => !bloqueadoFinanceiro && aceitarChamado(chamadoAtivo.id)}
                      disabled={bloqueadoFinanceiro}
                      className="w-full bg-green-600 hover:bg-green-700 disabled:bg-zinc-700 disabled:text-zinc-400 text-white font-black rounded-xl py-3 text-sm"
                    >
                      {bloqueadoFinanceiro ? '⛔ Bloqueado por saldo devedor' : '✅ Aceitar Chamado'}
                    </button>
                  )}
                  {['em_atendimento'].includes((chamadoAtivo.status||'').toLowerCase()) && (
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
                      {renderCronometro(c, true)}
                      {(c.status||'').toLowerCase() === 'pendente' && (
                        <button
                          onClick={() => !bloqueadoFinanceiro && aceitarChamado(c.id)}
                          disabled={bloqueadoFinanceiro}
                          className="w-full bg-green-600 hover:bg-green-700 disabled:bg-zinc-700 disabled:text-zinc-400 text-white font-black rounded-xl py-2 text-xs"
                        >
                          {bloqueadoFinanceiro ? '⛔ Bloqueado' : '✅ Aceitar'}
                        </button>
                      )}
                      {['em_atendimento'].includes((c.status||'').toLowerCase()) && (
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
              <div className="space-y-4">
                <div className="rounded-2xl border border-zinc-800 bg-zinc-900 p-3">
                  <p className="text-[11px] text-zinc-400 uppercase tracking-wide">Status atual</p>
                  <p className="text-sm font-bold text-white mt-1">
                    {perfil?.presente_em_local && perfil?.barbearia_atual_nome
                      ? `Presente em ${perfil.barbearia_atual_nome}`
                      : 'Disponível na região'}
                  </p>
                </div>
                <TelaPerfilUsuario userType="barbeiro" token={token} API_URL={API_URL} onLogout={handleLogout} onNotify={notify} />
              </div>
            </div>
          )}

          {/* CARTEIRA */}
          {tab === 'carteira' && (
            <div className="p-4 space-y-4">
              <h2 className="text-xs font-black text-zinc-500 uppercase tracking-widest">Carteira</h2>
              {(() => {
                const saldoCarteira = Number(ganhos?.saldo_carteira || 0);
                const limiteNegativo = Number(ganhos?.limite_negativo ?? -50);
                const bloqueado = Boolean(ganhos?.bloqueado_financeiro) || saldoCarteira <= limiteNegativo;
                const alerta = saldoCarteira < 0 && !bloqueado;
                const positivo = saldoCarteira > 0;

                return (
                  <div className={`rounded-2xl border p-5 text-center ${bloqueado ? 'border-red-500/40 bg-red-500/10' : alerta ? 'border-amber-500/40 bg-amber-500/10' : positivo ? 'border-emerald-500/40 bg-emerald-500/10' : 'border-zinc-800 bg-zinc-900'}`}>
                    <p className="text-xs uppercase tracking-wide text-zinc-400 mb-1">Saldo da carteira</p>
                    <p className={`text-3xl font-black ${bloqueado ? 'text-red-400' : alerta ? 'text-amber-300' : positivo ? 'text-emerald-400' : 'text-white'}`}>
                      R$ {saldoCarteira.toFixed(2)}
                    </p>
                    {positivo && <p className="text-xs text-emerald-200 mt-2">Você pode solicitar saque via PIX.</p>}
                    {alerta && <p className="text-xs text-amber-200 mt-2">Sua comissão pendente será descontada nos próximos atendimentos via Pix/Cartão.</p>}
                    {bloqueado && <p className="text-xs text-red-200 mt-2">Saldo devedor no limite. Novos chamados estão bloqueados até a quitação.</p>}
                  </div>
                );
              })()}

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
                    <div className="flex justify-between"><span className="text-zinc-400">Taxa app</span><span className="font-bold text-orange-400">10%</span></div>
              </div>

              {Number(ganhos?.saldo_carteira || 0) > 0 && (
                <button
                  onClick={solicitarSaquePix}
                  disabled={processandoSaque}
                  className="w-full rounded-xl bg-emerald-600 hover:bg-emerald-500 disabled:bg-emerald-800/60 py-3 text-sm font-black"
                >
                  {processandoSaque ? 'Solicitando saque...' : 'Solicitar Saque via Pix'}
                </button>
              )}

              {Boolean(ganhos?.bloqueado_financeiro) && (
                <div className="rounded-2xl border border-red-500/40 bg-red-500/10 p-4 space-y-3">
                  <button
                    onClick={gerarPixQuitacao}
                    disabled={processandoQuitacao}
                    className="w-full rounded-xl bg-red-600 hover:bg-red-500 disabled:bg-red-800/60 py-3 text-sm font-black"
                  >
                    {processandoQuitacao ? 'Gerando PIX...' : 'Pagar Saldo Devedor para Liberar App'}
                  </button>

                  {pixQuitacao && (
                    <div className="space-y-3">
                      <p className="text-xs text-red-100">Valor devedor: <span className="font-bold">R$ {Number(pixQuitacao.valor_devedor || 0).toFixed(2)}</span></p>
                      {pixQuitacao.qrcode_base64 && (
                        <div className="bg-white p-2 rounded-lg inline-block">
                          <img src={`data:image/png;base64,${pixQuitacao.qrcode_base64}`} alt="QR PIX quitação" className="w-44 h-44" />
                        </div>
                      )}
                      <div className="flex gap-2">
                        <input
                          value={pixQuitacao.pix_copia_cola || ''}
                          readOnly
                          className="flex-1 bg-zinc-950 border border-zinc-700 rounded-lg px-3 py-2 text-[11px] text-zinc-200"
                        />
                        <button
                          onClick={() => copiarTexto(pixQuitacao.pix_copia_cola)}
                          className="px-3 py-2 rounded-lg bg-zinc-800 hover:bg-zinc-700"
                          type="button"
                        >
                          <Copy size={14} />
                        </button>
                      </div>
                      <button
                        onClick={confirmarQuitacao}
                        disabled={processandoQuitacao}
                        className="w-full rounded-xl bg-emerald-600 hover:bg-emerald-500 disabled:bg-emerald-800/60 py-2 text-sm font-black"
                      >
                        {processandoQuitacao ? 'Confirmando...' : 'Já paguei, confirmar quitação'}
                      </button>
                    </div>
                  )}
                </div>
              )}

              {Array.isArray(ganhos?.historico_movimentacoes) && ganhos.historico_movimentacoes.length > 0 && (
                <div className="rounded-2xl border border-zinc-800 bg-zinc-900 p-4 space-y-2">
                  <p className="text-xs font-black text-zinc-500 uppercase tracking-widest">Histórico de movimentações</p>
                  <div className="space-y-2 max-h-72 overflow-y-auto">
                    {ganhos.historico_movimentacoes.map((mov) => (
                      <div key={mov.id} className="rounded-xl border border-zinc-800 bg-zinc-950 p-3">
                        <p className="text-xs text-zinc-300 font-bold">{mov.descricao}</p>
                        <div className="flex justify-between text-[11px] mt-1">
                          <span className="text-zinc-500">{mov.criado_em ? new Date(mov.criado_em).toLocaleString('pt-BR') : '-'}</span>
                          <span className={Number(mov.valor) >= 0 ? 'text-emerald-400 font-bold' : 'text-red-400 font-bold'}>
                            {Number(mov.valor) >= 0 ? '+' : '-'}R$ {Math.abs(Number(mov.valor || 0)).toFixed(2)}
                          </span>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              <button onClick={carregarGanhos} className="w-full rounded-xl border border-zinc-800 bg-zinc-900 py-3 text-sm font-bold hover:bg-zinc-800 transition-colors">
                🔄 Atualizar
              </button>
            </div>
          )}
        </div>

        {/* NAVBAR */}
        <div className="fixed bottom-0 left-0 right-0 mx-auto w-full max-w-[430px] h-[calc(4.8rem+env(safe-area-inset-bottom))] pb-[env(safe-area-inset-bottom)] bg-[#121214] border-t border-zinc-900 grid grid-cols-5 gap-1 px-2 items-stretch z-50">
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
              className={`flex flex-col items-center justify-center gap-1 h-full text-center rounded-xl transition-colors ${tab === item.id ? 'text-orange-500 bg-orange-500/5' : 'text-zinc-500 hover:text-zinc-200'}`}
            >
              {item.icon}
              <span className="text-[10px] font-bold leading-none">{item.label}</span>
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}
