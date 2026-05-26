import React, { useState, useEffect, useCallback, useRef } from 'react';
import { 
  User, Scissors, Store, MapPin, 
  LogOut, CheckCircle, AlertCircle, ArrowRight, 
  History, Search, X, Star, Navigation, Bell, CreditCard, Lock, Calendar, Briefcase
} from 'lucide-react';
import './styles.css';
import './theme/painel.css';
import PoliticaPrivacidade from './components/PoliticaPrivacidade';
import TermosDeUso from './components/TermosDeUso';
import TelaPerfilUsuario from './components/TelaPerfilUsuario';
// clean preview components removed per user request
import RatingComponent from './components/RatingComponent';
import AbaPadronizadaAvaliacoes from './components/AbaPadronizadaAvaliacoes';
import PaymentSection from './components/PaymentSection';
import ProfileCard from './components/ProfileCard';
import AssinaturaPage from './components/AssinaturaPage';
import ClientDashboardView from './components/ClientDashboard';
import PainelChamadasCliente from './components/PainelChamadasCliente';
import BarberDashboardView from './components/BarberDashboard';
import ShopDashboardView from './components/ShopDashboard';
import TelaDoChamado from './components/TelaDoChamado';
import TelaLogin from './screens/TelaLogin';
import PainelLayout from './components/PainelLayout';
// LoginClean removed
import { useLiveJobs } from './hooks/useRealTimeUpdates';
import { obterLocalizacaoAtual } from './utils/location';
import { getApiBaseUrl, getWsBaseUrl } from './utils/api';

const API_URL = getApiBaseUrl();
const WS_URL = getWsBaseUrl();
const BRAND_LOGO = "/brand-logo.png"; // coloque a logo em public/brand-logo.png

// Utilitário para imagens
const getShopImage = (id) => `https://images.unsplash.com/photo-${id % 2 === 0 ? '1521590832874-552721032d00' : '1503951914290-d20607416905'}?auto=format&fit=crop&w=800&q=80`;

export default function App() {
  // Preview mode removed (clean components deleted)
  const [userType, setUserType] = useState(localStorage.getItem('userType'));
  const [token, setToken] = useState(localStorage.getItem('token'));
  const [view, setView] = useState(token ? 'dashboard' : 'login');
  const [chamadoId, setChamadoId] = useState(null); // Para rastreamento de chamado
  const [toast, setToast] = useState(null);
  const [swWaiting, setSwWaiting] = useState(false);
  const swRegRef = useRef(null);
  const [shopTab, setShopTab] = useState('gestao');
  const [showTerms, setShowTerms] = useState(false);
  const [showPrivacy, setShowPrivacy] = useState(false);
  const [currentUser, setCurrentUser] = useState(null);
  const [userApproved, setUserApproved] = useState(true);
  const [gpsObrigatorioAtivo, setGpsObrigatorioAtivo] = useState(false);
  const [gpsMensagemBloqueio, setGpsMensagemBloqueio] = useState('');
  const [gpsRetryCounter, setGpsRetryCounter] = useState(0);
  const watchIdRef = useRef(null);

  useEffect(() => {
    const handleAuthExpired = () => {
      localStorage.clear();
      setUserType(null);
      setToken(null);
      setView('login');
      setCurrentUser(null);
      setUserApproved(true);
      setToast({ message: 'Sessao expirada. Faca login novamente.', type: 'error' });
    };

    window.addEventListener('auth:expired', handleAuthExpired);
    return () => window.removeEventListener('auth:expired', handleAuthExpired);
  }, []);

  // Verificar aprovação do usuário quando entra no dashboard
  useEffect(() => {
    if (token && view === 'dashboard') {
      fetch(`${API_URL}/api/v1/documentos/status`, {
        headers: { 'Authorization': `Bearer ${token}` }
      })
      .then(r => {
        if (r.status === 401) {
          window.dispatchEvent(new CustomEvent('auth:expired'));
          return null;
        }
        return r.ok ? r.json() : Promise.reject();
      })
      .then(data => {
        if (!data) return;
        setCurrentUser(data);
        setUserApproved(Boolean(data?.perfil_aprovado));
      })
      .catch(() => setUserApproved(true));
    }
  }, [token, view]);

  const notify = useCallback((message, type = 'success') => {
    setToast({ message, type });
    setTimeout(() => setToast(null), 4000);
  }, []);

  // WebSocket Global para notificações
  useEffect(() => {
    if (token) {
      const ws = new WebSocket(WS_URL);
      ws.onopen = () => {
        ws.send(JSON.stringify({ tipo: 'auth', token }));
      };
      ws.onmessage = (event) => {
        const msg = JSON.parse(event.data);
        notify(msg.texto || "Nova atualização!", 'info');
      };
      return () => ws.close();
    }
  }, [token, notify]);

  // Service Worker: detectar updates e notificar usuário para atualizar
  useEffect(() => {
    if (!('serviceWorker' in navigator)) return undefined;

    const onReady = async () => {
      try {
        const registration = await navigator.serviceWorker.getRegistration();
        if (!registration) return;

        // Se já existe um SW em waiting, sinaliza atualização disponível
        if (registration.waiting) {
          swRegRef.current = registration;
          setSwWaiting(true);
        }

        registration.addEventListener('updatefound', () => {
          const newWorker = registration.installing;
          if (!newWorker) return;
          newWorker.addEventListener('statechange', () => {
            if (newWorker.state === 'installed' && navigator.serviceWorker.controller) {
              swRegRef.current = registration;
              setSwWaiting(true);
            }
          });
        });
      } catch (_err) {
        // ignore
      }
    };

    onReady();

    const onControllerChange = () => {
      // Quando o novo SW assume, recarrega para aplicar novo bundle
      window.location.reload();
    };

    navigator.serviceWorker.addEventListener('controllerchange', onControllerChange);

    return () => {
      try { navigator.serviceWorker.removeEventListener('controllerchange', onControllerChange); } catch (_e) {}
    };
  }, []);

  const applyServiceWorkerUpdate = async () => {
    try {
      const reg = swRegRef.current;
      const waiting = reg?.waiting || (reg?.installing && reg.installing.state === 'installed' ? reg.installing : null);
      if (waiting) {
        waiting.postMessage({ type: 'SKIP_WAITING' });
      }
    } catch (_err) {
      // fallback: reload
      window.location.reload();
    }
  };

  useEffect(() => {
    const gpsObrigatorioParaPerfil = view === 'dashboard' && (userType === 'cliente' || userType === 'barbearia');

    if (!token || typeof navigator === 'undefined' || !navigator.geolocation) {
      if (gpsObrigatorioParaPerfil) {
        setGpsObrigatorioAtivo(false);
        setGpsMensagemBloqueio('Ative a localização para continuar usando o app.');
      }
      return undefined;
    }

    if (gpsObrigatorioParaPerfil) {
      setGpsObrigatorioAtivo(false);
    }

    const sendLocation = async (coords) => {
      try {
        const response = await fetch(`${API_URL}/api/v1/atualizar-localizacao`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${token}`,
          },
          body: JSON.stringify({
            latitude: coords.latitude,
            longitude: coords.longitude,
          }),
        });

        if (!response.ok && gpsObrigatorioParaPerfil) {
          setGpsObrigatorioAtivo(false);
          setGpsMensagemBloqueio('Nao foi possivel enviar sua localizacao. Verifique conexao e permissao.');
          return;
        }

        if (gpsObrigatorioParaPerfil) {
          setGpsObrigatorioAtivo(true);
          setGpsMensagemBloqueio('');
        }
      } catch (_err) {
        if (gpsObrigatorioParaPerfil) {
          setGpsObrigatorioAtivo(false);
          setGpsMensagemBloqueio('Falha ao sincronizar localizacao. Tente novamente.');
        }
      }
    };

    watchIdRef.current = navigator.geolocation.watchPosition(
      (position) => {
        sendLocation(position.coords);
      },
      (err) => {
        if (gpsObrigatorioParaPerfil) {
          const msg = err?.code === 1
            ? 'Permissao de localizacao negada. Habilite a localizacao no navegador.'
            : 'Nao foi possivel obter localizacao. Ative o GPS e tente novamente.';
          setGpsObrigatorioAtivo(false);
          setGpsMensagemBloqueio(msg);
        }
      },
      {
        enableHighAccuracy: true,
        maximumAge: 3000,
        timeout: 10000,
      }
    );

    return () => {
      if (watchIdRef.current != null) {
        navigator.geolocation.clearWatch(watchIdRef.current);
        watchIdRef.current = null;
      }
    };
  }, [token, userType, view, gpsRetryCounter]);

  const gpsBloqueado = false;

  const GpsObrigatorioOverlay = () => (
    <div className="fixed bottom-4 left-4 right-4 z-[95] flex justify-center pointer-events-none">
      <div className="max-w-md w-full bg-zinc-900/95 rounded-3xl border border-zinc-800 p-4 text-center shadow-2xl pointer-events-auto">
        <h2 className="text-xl font-bold text-white">Localizacao obrigatoria</h2>
        <p className="text-zinc-300 mt-3 text-sm">
          {gpsMensagemBloqueio || 'Ative o GPS para continuar no perfil cliente/barbearia.'}
        </p>
        <button
          onClick={() => setGpsRetryCounter((v) => v + 1)}
          className="mt-4 w-full px-4 py-3 bg-orange-600 hover:bg-orange-700 text-white font-bold rounded-lg"
        >
          Tentar novamente
        </button>
      </div>
    </div>
  );

  const saveLogin = (type, access_token, userId) => {
    localStorage.setItem('userType', type);
    localStorage.setItem('token', access_token);
    localStorage.setItem('userId', userId);
    setUserType(type);
    setToken(access_token);
    setView('dashboard');
    setShopTab('gestao');
  };

  const logout = () => {
    localStorage.clear();
    setUserType(null);
    setToken(null);
    setView('login');
    setCurrentUser(null);
    setUserApproved(true);
    setShopTab('gestao');
  };

  const abrirTelaRastreamento = (chamadoId) => {
    setChamadoId(chamadoId);
    setView('rastreamento');
  };

  // --- COMPONENTES UI COMPARTILHADOS ---

  // ⏳ TELA DE ESPERA POR APROVAÇÃO
  const PendingApprovalScreen = () => (
    <div className="fixed inset-0 bg-gradient-to-br from-black via-zinc-900 to-black flex items-center justify-center p-4 z-50">
      <div className="max-w-md w-full bg-zinc-900 rounded-3xl border border-zinc-800 p-8 text-center shadow-2xl">
        <div className="mb-6 flex justify-center">
          <div className="relative">
            <div className="w-20 h-20 rounded-full bg-yellow-600/20 border-2 border-yellow-600 flex items-center justify-center animate-pulse">
              <AlertCircle size={40} className="text-yellow-500" />
            </div>
          </div>
        </div>
        
        <h1 className="text-2xl font-bold text-white mb-2">Perfil em Análise</h1>
        <p className="text-zinc-400 mb-6">
          Seu perfil foi enviado para aprovação. A equipe de administração está analisando seus dados.
        </p>
        
        <div className="bg-zinc-800/50 rounded-lg p-4 mb-6 border border-zinc-700">
          <p className="text-sm text-zinc-300 mb-2">⏱️ Tempo estimado:</p>
          <p className="text-lg font-bold text-yellow-500">Até 24 horas</p>
        </div>
        
        {currentUser && (
          <div className="bg-zinc-800/30 rounded-lg p-4 mb-6 border border-zinc-700/50">
            <p className="text-xs text-zinc-500 mb-2">Usuário:</p>
            <p className="text-sm font-semibold text-white">{currentUser.nome}</p>
            <p className="text-xs text-zinc-400">{currentUser.email}</p>
          </div>
        )}
        
        <p className="text-xs text-zinc-500 mb-6">
          Você receberá um email quando sua aprovação for concluída.
        </p>
        
        <button
          onClick={() => {
            setUserApproved(true); // Reload
            window.location.reload();
          }}
          className="w-full px-6 py-3 bg-blue-600 hover:bg-blue-700 text-white font-bold rounded-lg transition mb-3"
        >
          🔄 Verificar Novamente
        </button>
        
        <button
          onClick={logout}
          className="w-full px-6 py-3 bg-zinc-800 hover:bg-zinc-700 text-white font-bold rounded-lg transition"
        >
          ← Sair
        </button>
      </div>
    </div>
  );

  const Toast = () => {
    if (!toast) return null;
    const bgClass = toast.type === 'error'
      ? 'bg-red-600'
      : toast.type === 'success'
      ? 'bg-green-600'
      : 'bg-blue-600';

    return (
      <div className={`bm-toast absolute top-6 left-1/2 transform -translate-x-1/2 z-[60] animate-slide-in-top w-[92%] max-w-[380px]` }>
        {toast.type === 'success' ? <CheckCircle size={20} className="text-white" /> : toast.type === 'error' ? <AlertCircle size={20} className="text-white" /> : <Bell size={20} className="text-white" />}
        <div className="flex-1"><p className="text-sm opacity-95">{toast.message}</p></div>
        <button onClick={() => setToast(null)} className="bm-action bm-bottom-nav-btn" aria-label="Fechar aviso"><X size={16} className="text-white"/></button>
      </div>
    );
  };

  const UpdateBanner = () => {
    if (!swWaiting) return null;
    return (
      <div className="bm-update-banner absolute top-20 left-1/2 transform -translate-x-1/2 z-[61] flex items-center gap-3 w-[92%] max-w-[420px]">
        <div className="flex-1">Nova versão disponível</div>
        <button data-active="true" onClick={applyServiceWorkerUpdate} className="bm-update-action bm-bottom-nav-btn" aria-label="Atualizar">Atualizar</button>
      </div>
    );
  };

  const VerificationBadge = ({ user, onClick }) => {
    if (!user) return null;
    const emailOk = !!user.email_verificado;
    const docOk = !!user.documento_verificado;
    const statusColor = emailOk && docOk ? 'bg-green-600' : emailOk && !docOk ? 'bg-yellow-600' : 'bg-red-600';
    const title = emailOk && docOk ? 'Verificado' : emailOk ? 'Docs pendentes' : 'Email pendente';
    return (
      <button
        title={title}
        onClick={onClick}
        className={`ml-2 px-2 py-1 rounded-full text-[10px] font-bold text-white ${statusColor}`}
      >
        {title}
      </button>
    );
  };

  const MapFrame = ({ address }) => {
    const encodedAddress = encodeURIComponent(address || "São Paulo");
    return (
      <div className="w-full bg-zinc-800 rounded-2xl overflow-hidden border border-zinc-700 relative group shadow-lg h-32 shrink-0">
        <iframe width="100%" height="100%" src={`https://maps.google.com/maps?q=${encodedAddress}&t=&z=15&ie=UTF8&iwloc=&output=embed`} frameBorder="0" scrolling="no" className="opacity-80 group-hover:opacity-100 transition-opacity" title="Mapa"></iframe>
      </div>
    );
  };

  // ==================== ADMIN DASHBOARD (TIPO: ADMIN) ====================
  const AdminDashboard = () => {
    const [splitForm, setSplitForm] = useState({
      percentual_barbeiro: '40',
      percentual_barbearia: '50',
      percentual_barbermove: '10',
      deposito_nome: '',
      deposito_chave_pix: '',
      deposito_banco: '',
      deposito_agencia: '',
      deposito_conta: ''
    });
    const [loadingSplit, setLoadingSplit] = useState(true);
    const [savingSplit, setSavingSplit] = useState(false);

    const totalSplit =
      (parseFloat(splitForm.percentual_barbeiro || 0) || 0) +
      (parseFloat(splitForm.percentual_barbearia || 0) || 0) +
      (parseFloat(splitForm.percentual_barbermove || 0) || 0);

    useEffect(() => {
      const carregarSplit = async () => {
        try {
          const res = await fetch(`${API_URL}/api/v1/pagamentos-config/split`, {
            headers: { 'Authorization': `Bearer ${token}` }
          });

          if (!res.ok) {
            throw new Error('Nao foi possivel carregar configuracoes de split');
          }

          const data = await res.json();
          setSplitForm({
            percentual_barbeiro: String(data.percentual_barbeiro ?? 40),
            percentual_barbearia: String(data.percentual_barbearia ?? 50),
            percentual_barbermove: String(data.percentual_barbermove ?? 10),
            deposito_nome: data.deposito_nome || '',
            deposito_chave_pix: data.deposito_chave_pix || '',
            deposito_banco: data.deposito_banco || '',
            deposito_agencia: data.deposito_agencia || '',
            deposito_conta: data.deposito_conta || ''
          });
        } catch (err) {
          notify(err.message || 'Erro ao carregar split', 'error');
        } finally {
          setLoadingSplit(false);
        }
      };

      carregarSplit();
    }, []);

    const salvarSplit = async () => {
      if (Math.abs(totalSplit - 100) > 0.0001) {
        notify('A soma dos percentuais deve ser 100%', 'error');
        return;
      }

      setSavingSplit(true);
      try {
        const payload = {
          percentual_barbeiro: parseFloat(splitForm.percentual_barbeiro || 0) || 0,
          percentual_barbearia: parseFloat(splitForm.percentual_barbearia || 0) || 0,
          percentual_barbermove: parseFloat(splitForm.percentual_barbermove || 0) || 0,
          deposito_nome: splitForm.deposito_nome || null,
          deposito_chave_pix: splitForm.deposito_chave_pix || null,
          deposito_banco: splitForm.deposito_banco || null,
          deposito_agencia: splitForm.deposito_agencia || null,
          deposito_conta: splitForm.deposito_conta || null
        };

        const res = await fetch(`${API_URL}/api/v1/pagamentos-config/split`, {
          method: 'PUT',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${token}`
          },
          body: JSON.stringify(payload)
        });

        if (!res.ok) {
          const err = await res.json().catch(() => ({}));
          throw new Error(err.detail || 'Erro ao salvar configuracao');
        }

        notify('Split e deposito salvos com sucesso', 'success');
      } catch (err) {
        notify(err.message || 'Erro ao salvar split', 'error');
      } finally {
        setSavingSplit(false);
      }
    };

    return (
      <div className="bg-black h-full flex flex-col text-white">
        <div className="p-5 pt-8 sticky top-0 bg-black/80 backdrop-blur-md z-20 border-b border-zinc-800">
          <div className="flex justify-between items-center mb-4">
            <h1 className="text-xl font-bold">🔧 Painel Administrativo</h1>
            <button onClick={logout} className="text-zinc-500"><LogOut size={20}/></button>
          </div>
          <p className="text-zinc-400 text-sm">Acesso restrito a desenvolvedores e donos do negócio</p>
        </div>

        <div className="flex-1 overflow-y-auto p-6">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-6">
            <button 
              onClick={() => setView('admin')} 
              className="bg-gradient-to-r from-purple-600 to-purple-800 p-6 rounded-xl hover:scale-105 transition text-left"
            >
              <div className="text-3xl mb-2">📊</div>
              <h3 className="font-bold text-lg">Validar Documentos</h3>
              <p className="text-sm text-purple-200">Aprovar ou rejeitar documentos de barbeiros</p>
            </button>

            <div className="bg-gradient-to-r from-zinc-800 to-zinc-900 p-6 rounded-xl border border-zinc-700">
              <div className="text-3xl mb-2">📈</div>
              <h3 className="font-bold text-lg">Estatísticas</h3>
              <p className="text-sm text-zinc-400">Em breve - Dashboard de métricas</p>
            </div>

            <div className="bg-gradient-to-r from-zinc-800 to-zinc-900 p-6 rounded-xl border border-zinc-700">
              <div className="text-3xl mb-2">👥</div>
              <h3 className="font-bold text-lg">Usuários</h3>
              <p className="text-sm text-zinc-400">Em breve - Gerenciar usuários</p>
            </div>

            <div className="bg-gradient-to-r from-zinc-800 to-zinc-900 p-6 rounded-xl border border-zinc-700">
              <div className="text-3xl mb-2">⚙️</div>
              <h3 className="font-bold text-lg">Configurações</h3>
              <p className="text-sm text-zinc-400">Split de pagamento e deposito da plataforma</p>
            </div>
          </div>

          <div className="bg-zinc-900 border border-zinc-700 p-5 rounded-xl mb-6">
            <h3 className="text-lg font-bold mb-1">Repasse e Deposito Barber Move</h3>
            <p className="text-xs text-zinc-400 mb-4">Defina os percentuais de divisao e a conta de deposito da plataforma.</p>

            {loadingSplit ? (
              <p className="text-zinc-500 text-sm">Carregando configuracoes...</p>
            ) : (
              <>
                <div className="grid grid-cols-1 md:grid-cols-3 gap-3 mb-3">
                  <label className="text-xs text-zinc-300">
                    % Barbeiro
                      <input
                      type="number"
                      step="0.01"
                      value={splitForm.percentual_barbeiro}
                      onChange={(e) => setSplitForm((prev) => ({ ...prev, percentual_barbeiro: e.target.value }))}
                      className="bm-input mt-1 w-full bg-black border border-zinc-700 rounded-lg px-3 py-2 text-sm"
                    />
                  </label>
                  <label className="text-xs text-zinc-300">
                    % Barbearia
                    <input
                      type="number"
                      step="0.01"
                      value={splitForm.percentual_barbearia}
                      onChange={(e) => setSplitForm((prev) => ({ ...prev, percentual_barbearia: e.target.value }))}
                      className="bm-input mt-1 w-full bg-black border border-zinc-700 rounded-lg px-3 py-2 text-sm"
                    />
                  </label>
                  <label className="text-xs text-zinc-300">
                    % Barber Move
                    <input
                      type="number"
                      step="0.01"
                      value={splitForm.percentual_barbermove}
                      onChange={(e) => setSplitForm((prev) => ({ ...prev, percentual_barbermove: e.target.value }))}
                      className="bm-input mt-1 w-full bg-black border border-zinc-700 rounded-lg px-3 py-2 text-sm"
                    />
                  </label>
                </div>

                <div className={`text-xs font-bold mb-4 ${Math.abs(totalSplit - 100) < 0.0001 ? 'text-green-400' : 'text-red-400'}`}>
                  Soma atual: {totalSplit.toFixed(2)}%
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-3 mb-4">
                  <label className="text-xs text-zinc-300">
                    Nome do titular
                    <input
                      type="text"
                      value={splitForm.deposito_nome}
                      onChange={(e) => setSplitForm((prev) => ({ ...prev, deposito_nome: e.target.value }))}
                      className="bm-input mt-1 w-full bg-black border border-zinc-700 rounded-lg px-3 py-2 text-sm"
                      placeholder="Barber Move"
                    />
                  </label>
                  <label className="text-xs text-zinc-300">
                    Chave PIX
                    <input
                      type="text"
                      value={splitForm.deposito_chave_pix}
                      onChange={(e) => setSplitForm((prev) => ({ ...prev, deposito_chave_pix: e.target.value }))}
                      className="bm-input mt-1 w-full bg-black border border-zinc-700 rounded-lg px-3 py-2 text-sm"
                    />
                  </label>
                  <label className="text-xs text-zinc-300">
                    Banco
                      <input
                      type="text"
                      value={splitForm.deposito_banco}
                      onChange={(e) => setSplitForm((prev) => ({ ...prev, deposito_banco: e.target.value }))}
                      className="bm-input mt-1 w-full bg-black border border-zinc-700 rounded-lg px-3 py-2 text-sm"
                    />
                  </label>
                  <label className="text-xs text-zinc-300">
                    Agencia
                    <input
                      type="text"
                      value={splitForm.deposito_agencia}
                      onChange={(e) => setSplitForm((prev) => ({ ...prev, deposito_agencia: e.target.value }))}
                      className="bm-input mt-1 w-full bg-black border border-zinc-700 rounded-lg px-3 py-2 text-sm"
                    />
                  </label>
                  <label className="text-xs text-zinc-300 md:col-span-2">
                    Conta
                    <input
                      type="text"
                      value={splitForm.deposito_conta}
                      onChange={(e) => setSplitForm((prev) => ({ ...prev, deposito_conta: e.target.value }))}
                      className="bm-input mt-1 w-full bg-black border border-zinc-700 rounded-lg px-3 py-2 text-sm"
                    />
                  </label>
                </div>

                <button
                  type="button"
                  onClick={salvarSplit}
                  disabled={savingSplit}
                  className="bm-primary bg-orange-600 hover:bg-orange-700 disabled:opacity-60 text-white font-bold px-5 py-2 rounded-lg transition"
                >
                  {savingSplit ? 'Salvando...' : 'Salvar Configuracao'}
                </button>
              </>
            )}
          </div>

          <div className="bg-orange-600/10 border border-orange-600/30 p-4 rounded-xl">
            <h3 className="font-bold text-orange-500 mb-2">⚠️ Acesso Administrativo</h3>
            <p className="text-sm text-zinc-400">Este painel é exclusivo para administradores do sistema. Não é acessível por clientes, barbeiros ou barbearias.</p>
          </div>
        </div>
      </div>
    );
  };

  // ==================== ADMIN VALIDATION SCREEN ====================
  const AdminValidationScreen = () => {
    const [pendentes, setPendentes] = useState([]);
    const [loading, setLoading] = useState(true);
    const [selectedUser, setSelectedUser] = useState(null);

    useEffect(() => {
      const load = async () => {
        try {
          const res = await fetch(`${API_URL}/api/v1/documentos/admin/pendentes`, {
            headers: { 'Authorization': `Bearer ${token}` }
          });
          if (res.ok) {
            const data = await res.json();
            setPendentes(data.usuarios || []);
          }
        } catch (_err) {
          notify('Erro ao carregar documentos pendentes', 'error');
        } finally {
          setLoading(false);
        }
      };
      load();
    }, []);

    const aprovar = async (userId) => {
      try {
        const res = await fetch(`${API_URL}/api/v1/documentos/verificar`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
          body: JSON.stringify({ usuario_id: userId, aprovado: true })
        });
        if (res.ok) {
          notify('✅ Documento aprovado!', 'success');
          setPendentes(pendentes.filter(u => u.id !== userId));
          setSelectedUser(null);
        } else {
          notify('Erro ao aprovar', 'error');
        }
      } catch (_err) {
        notify('Erro na requisição', 'error');
      }
    };

    const rejeitar = async (userId, motivo) => {
      try {
        const res = await fetch(`${API_URL}/api/v1/documentos/verificar`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
          body: JSON.stringify({ usuario_id: userId, aprovado: false, motivo_rejeicao: motivo })
        });
        if (res.ok) {
          notify('❌ Documento rejeitado', 'success');
          setPendentes(pendentes.filter(u => u.id !== userId));
          setSelectedUser(null);
        } else {
          notify('Erro ao rejeitar', 'error');
        }
      } catch (_err) {
        notify('Erro na requisição', 'error');
      }
    };

    if (selectedUser) {
      return (
        <div className="fixed inset-0 bg-black/90 backdrop-blur-sm z-50 flex items-center justify-center p-4 overflow-y-auto">
          <div className="bg-zinc-900 rounded-2xl max-w-2xl w-full border border-zinc-800 p-8">
            <div className="flex justify-between items-center mb-6">
              <h2 className="text-2xl font-bold text-white">{selectedUser.nome}</h2>
              <button onClick={() => setSelectedUser(null)} className="text-zinc-500"><X size={24}/></button>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
              <div>
                <p className="text-zinc-400 text-sm">Email</p>
                <p className="text-white font-mono text-sm">{selectedUser.email}</p>
              </div>
              <div>
                <p className="text-zinc-400 text-sm">Tipo</p>
                <p className="text-white capitalize">{selectedUser.tipo}</p>
              </div>
              <div>
                <p className="text-zinc-400 text-sm">RG</p>
                <p className="text-white font-mono">{selectedUser.rg || '-'}</p>
              </div>
            </div>

            <div className="space-y-4 mb-6">
              {selectedUser.documento_frente_url && (
                <div>
                  <p className="text-zinc-400 text-sm mb-2">📄 Documento - Frente</p>
                  <img src={selectedUser.documento_frente_url} alt="Frente" className="w-full rounded-lg border border-zinc-700 max-h-64 object-cover"/>
                </div>
              )}
              {selectedUser.documento_verso_url && (
                <div>
                  <p className="text-zinc-400 text-sm mb-2">📄 Documento - Verso</p>
                  <img src={selectedUser.documento_verso_url} alt="Verso" className="w-full rounded-lg border border-zinc-700 max-h-64 object-cover"/>
                </div>
              )}
              {selectedUser.selfie_documento_url && (
                <div>
                  <p className="text-zinc-400 text-sm mb-2">🤳 Selfie com Documento</p>
                  <img src={selectedUser.selfie_documento_url} alt="Selfie" className="w-full rounded-lg border border-zinc-700 max-h-64 object-cover"/>
                </div>
              )}
            </div>

            <div className="flex gap-3">
              <button
                onClick={() => rejeitar(selectedUser.id, 'Documentos inválidos ou ilegíveis')}
                className="flex-1 bg-red-600 hover:bg-red-700 text-white font-bold py-3 rounded-xl transition"
              >
                ❌ Rejeitar
              </button>
              <button
                onClick={() => aprovar(selectedUser.id)}
                className="flex-1 bg-green-600 hover:bg-green-700 text-white font-bold py-3 rounded-xl transition"
              >
                ✅ Aprovar
              </button>
            </div>
          </div>
        </div>
      );
    }

    return (
      <div className="bg-black min-h-screen text-white p-6">
        <div className="max-w-4xl mx-auto">
          <button onClick={() => setView('dashboard')} className="mb-6 flex items-center gap-2 text-zinc-400 hover:text-white">
            <ArrowRight size={20} className="rotate-180"/> Voltar
          </button>

          <h1 className="text-3xl font-bold mb-2">📋 Validar Documentos</h1>
          <p className="text-zinc-400 mb-6">Pendentes de aprovação: {pendentes.length}</p>

          {loading ? (
            <div className="text-center py-12">
              <div className="inline-block animate-spin rounded-full h-8 w-8 border-t-2 border-orange-600"></div>
              <p className="text-zinc-400 mt-4">Carregando...</p>
            </div>
          ) : pendentes.length === 0 ? (
            <div className="bg-zinc-900 border border-zinc-800 rounded-xl p-8 text-center">
              <p className="text-zinc-400">✅ Não há documentos pendentes!</p>
            </div>
          ) : (
            <div className="grid gap-4">
              {pendentes.map(user => (
                <button
                  key={user.id}
                  onClick={() => setSelectedUser(user)}
                  className="bg-zinc-900 border border-zinc-800 hover:border-orange-600 p-4 rounded-xl text-left transition"
                >
                  <div className="flex justify-between items-start">
                    <div>
                      <h3 className="font-bold text-white">{user.nome}</h3>
                      <p className="text-sm text-zinc-400">{user.email}</p>
                      <p className="text-xs text-zinc-500 capitalize mt-1">Tipo: {user.tipo}</p>
                    </div>
                    <ArrowRight size={20} className="text-zinc-500"/>
                  </div>
                </button>
              ))}
            </div>
          )}
        </div>
      </div>
    );
  };

  // ----------------------------------------------------------------------
  // ClientDashboard foi movido para src/components/ClientDashboard.jsx
  // ----------------------------------------------------------------------
  const ClientDashboard_OLD_REMOVED = () => {
    const [barbeiros, setBarbeiros] = useState([]);
    const [shops, setShops] = useState([]);
    const [tab, setTab] = useState('barbeiros'); // Mudado: inicia em barbeiros
    const [selectedBarbeiro, setSelectedBarbeiro] = useState(null); // Novo estado
    const [selectedShop, setSelectedShop] = useState(null);
    const [selectedService, setSelectedService] = useState(null);
    const [showDatePicker, setShowDatePicker] = useState(false);
    const [selectedDate, setSelectedDate] = useState('');
    const [selectedTime, setSelectedTime] = useState('');
    const [services, setServices] = useState([]);
    const [myOrders, setMyOrders] = useState([]);
    const [userCoords, setUserCoords] = useState(null);
    const [clientUser, setClientUser] = useState(null);
    const [avaliacoesBarbeiro, setAvaliacoesBarbeiro] = useState([]);
    const [avaliacoesShop, setAvaliacoesShop] = useState([]);
    const [avaliarPedido, setAvaliarPedido] = useState({ id: null, alvo: null, nota: 5, comentario: '' });
    const [selectedOrder, setSelectedOrder] = useState(null); // Novo estado para agendamento selecionado
    const [_pagamentoSelecionado, setPagamentoSelecionado] = useState(null);
    const [showAvailableOnly, setShowAvailableOnly] = useState(false); // 🔴 Filtro de disponibilidade
    const ETA_SPEED_KMH = 30; // velocidade média urbana para estimar chegada

    const toRad = (deg) => deg * (Math.PI / 180);
    const distanceKm = (aLat, aLon, bLat, bLon) => {
      const R = 6371;
      const dLat = toRad(bLat - aLat);
      const dLon = toRad(bLon - aLon);
      const lat1 = toRad(aLat);
      const lat2 = toRad(bLat);
      const h = Math.sin(dLat/2)**2 + Math.cos(lat1) * Math.cos(lat2) * Math.sin(dLon/2)**2;
      return R * 2 * Math.atan2(Math.sqrt(h), Math.sqrt(1 - h));
    };

    const _formatDistanceEta = (shop) => {
      const hasShopCoords = shop.latitude !== null && shop.latitude !== undefined && shop.longitude !== null && shop.longitude !== undefined;
      if (!userCoords || !hasShopCoords) return null;
      const km = distanceKm(userCoords.lat, userCoords.lon, shop.latitude, shop.longitude);
      const etaMinutes = Math.round((km / ETA_SPEED_KMH) * 60);
      return { km: km.toFixed(1), eta: etaMinutes };
    };

    const openMaps = (shop) => {
      const hasCoords = shop.latitude !== null && shop.latitude !== undefined && shop.longitude !== null && shop.longitude !== undefined;
      const query = hasCoords ? `${shop.latitude},${shop.longitude}` : encodeURIComponent(shop.endereco || shop.nome || 'barbearia');
      const url = `https://www.google.com/maps/search/?api=1&query=${query}`;
      window.open(url, '_blank');
    };

    const normalizePhone = (phone) => (phone || '').replace(/\D/g, '');

    const handleCall = (phone) => {
      const normalized = normalizePhone(phone);
      if (!normalized) {
        notify('Telefone nao informado.', 'error');
        return;
      }
      window.open(`tel:${normalized}`);
    };

    const handleWhatsApp = (phone) => {
      const normalized = normalizePhone(phone);
      if (!normalized) {
        notify('Telefone nao informado.', 'error');
        return;
      }
      window.open(`https://wa.me/${normalized}`, '_blank');
    };

    useEffect(() => {
        // Buscar barbeiros próximos se tiver geolocalização
        if (userCoords) {
          console.log('🔄 Buscando barbeiros próximos com coords:', userCoords);
          fetch(`${API_URL}/api/v1/barbeiros/proximos?latitude=${userCoords.lat}&longitude=${userCoords.lon}&raio_km=5`)
            .then(async r => {
              if (!r.ok) {
                console.error('❌ Erro ao listar barbeiros:', r.status);
                throw new Error('Erro ao listar barbeiros');
              }
              return r.json();
            })
            .then(data => {
              console.log('✅ Barbeiros próximos recebidos:', data.length, data);
              setBarbeiros(data);
            })
            .catch(err => {
              console.warn('⚠️ Falha ao buscar barbeiros próximos, usando fallback:', err.message);
              // Fallback: buscar todos se geolocalização falhar
              fetch(`${API_URL}/api/v1/barbeiros/todos`)
                .then(r => r.json())
                .then(data => {
                  console.log('📍 Usando fallback - todos os barbeiros:', data.length);
                  setBarbeiros(data);
                })
                .catch(err => {
                  console.error('❌ Erro ao buscar barbeiros:', err);
                  setBarbeiros([]);
                });
            });

          // 🆕 Buscar barbearias próximas e aprovadas
          fetch(`${API_URL}/api/v1/barbearias/proximas?raio_km=10`, {
            headers: { 'Authorization': `Bearer ${token}` }
          })
            .then(async r => {
              if (!r.ok) throw new Error('Erro ao listar barbearias');
              return r.json();
            })
            .then(data => setShops(data.barbearias || []))
            .catch(() => {
              // Fallback: buscar todas aprovadas
              fetch(`${API_URL}/api/v1/barbearias/todas-aprovadas`, {
                headers: { 'Authorization': `Bearer ${token}` }
              })
                .then(r => r.json())
                .then(data => setShops(data.barbearias || []))
                .catch(() => setShops([]));
            });
        } else {
          console.log('📍 Sem geolocalização, buscando todos os barbeiros');
          fetch(`${API_URL}/api/v1/barbeiros/todos`)
            .then(r => r.json())
            .then(data => {
              console.log('📍 Todos os barbeiros:', data.length);
              setBarbeiros(data);
            })
            .catch(() => setBarbeiros([]));
          
          // 🆕 Buscar todas as barbearias aprovadas
          if (token) {
            fetch(`${API_URL}/api/v1/barbearias/todas-aprovadas`, {
              headers: { 'Authorization': `Bearer ${token}` }
            })
              .then(r => r.json())
              .then(data => setShops(data.barbearias || []))
              .catch(() => setShops([]));
          }
        }

        if (token) {
          fetch(`${API_URL}/api/v1/cliente/meus_pedidos`, { headers: {'Authorization': `Bearer ${token}`} })
            .then(async r => {
              if (!r.ok) throw new Error();
              return r.json();
            }).then(setMyOrders).catch(() => setMyOrders([]));
          
          // Status de verificação do usuário atual
          const fetchUserStatus = () => {
            fetch(`${API_URL}/api/v1/documentos/status`, { headers: {'Authorization': `Bearer ${token}`} })
              .then(r => r.json())
              .then(setClientUser)
              .catch(() => {});
          };
          
          fetchUserStatus();
          
          // Se email não está verificado, recarregar a cada 10 segundos
          const interval = setInterval(() => {
            if (!clientUser?.email_verificado) {
              fetchUserStatus();
            }
          }, 10000);
          
          return () => clearInterval(interval);
        }
    }, [userCoords, clientUser?.email_verificado]);

    useEffect(() => {
      console.log('🔍 Solicitando geolocalização...');
      obterLocalizacaoAtual()
        .then((coords) => {
          const localizacao = { lat: coords.latitude, lon: coords.longitude };
          console.log('✅ Geolocalização obtida:', localizacao);
          setUserCoords(localizacao);
        })
        .catch((error) => {
          console.error('❌ Erro de geolocalização:', error?.message || error);
          console.log('Caindo para fallback e buscando todos os barbeiros...');
        });
    }, []);

    const handleSelectBarbeiro = async (barbeiro) => {
        setSelectedBarbeiro(barbeiro);
        // Buscar barbearias onde esse barbeiro atende
        try {
          const res = await fetch(`${API_URL}/api/v1/barbeiro/${barbeiro.id}/barbearias`);
          const data = await res.json();
          setShops(Array.isArray(data) ? data : []);
        } catch {
          notify('Erro ao carregar barbearias', 'error');
          setShops([]);
        }

        // Avaliações do barbeiro
        try {
          const r = await fetch(`${API_URL}/api/v1/avaliacoes/freelancer/${barbeiro.id}/recebidas?limite=5`);
          if (r.ok) {
            const avs = await r.json();
            setAvaliacoesBarbeiro(Array.isArray(avs) ? avs : []);
          } else {
            setAvaliacoesBarbeiro([]);
          }
        } catch { setAvaliacoesBarbeiro([]); }
    };

    const handleSelectShop = async (shop) => {
        setSelectedShop(shop);
        // Fetch Services
        try {
          const res = await fetch(`${API_URL}/api/v1/barbearia/${shop.id}/servicos`);
          const data = await res.json();
          setServices(Array.isArray(data) ? data : []);
        } catch {
          notify('Erro ao carregar serviços', 'error');
          setServices([]);
        }

        // Avaliações da barbearia
        try {
          const r = await fetch(`${API_URL}/api/v1/avaliacoes/barbearia/${shop.id}/recebidas?limite=5`);
          if (r.ok) {
            const avs = await r.json();
            setAvaliacoesShop(Array.isArray(avs) ? avs : []);
          } else {
            setAvaliacoesShop([]);
          }
        } catch { setAvaliacoesShop([]); }
    };

    const handleBooking = async (service) => {
      setSelectedService(service);
      
      // Definir data mínima (hoje) e hora padrão
      const today = new Date();
      const tomorrow = new Date(today);
      tomorrow.setDate(tomorrow.getDate() + 1);
      
      setSelectedDate(tomorrow.toISOString().split('T')[0]);
      setSelectedTime('10:00');
      setShowDatePicker(true);
    };

    const confirmBooking = async () => {
      if (!selectedDate || !selectedTime) {
        notify('Selecione data e horário', 'error');
        return;
      }

      let localizacao;
      try {
        localizacao = await obterLocalizacaoAtual();
      } catch (_err) {
        notify('Ative a localização para agendar.', 'error');
        return;
      }
      
      try {
        const dataHora = new Date(`${selectedDate}T${selectedTime}:00`);
        
        const res = await fetch(`${API_URL}/api/v1/chamados`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
          body: JSON.stringify({ 
            servico_id: selectedService.id, 
            barbearia_id: selectedShop.id,
            barbeiro_id: selectedBarbeiro?.id || null,
            data_hora_inicio: dataHora.toISOString(),
            cliente_latitude: localizacao.latitude,
            cliente_longitude: localizacao.longitude
          })
        });
        if (!res.ok) {
          const error = await res.json();
          throw new Error(error.detail || 'Erro ao agendar');
        }
        notify("Agendamento enviado! Aguarde o barbeiro aceitar.", "success");
        setShowDatePicker(false);
        setSelectedService(null);
        setSelectedBarbeiro(null);
        setSelectedShop(null);
        setTab('pedidos');
      } catch (err) {
        notify(err.message || "Erro ao agendar. Verifique sua conexão.", "error");
      }
    };

    const abrirPagamento = (pedido) => {
      setPagamentoSelecionado(pedido);
      setTab('pagamentos');
    };

    const enviarAvaliacao = async (pedido, alvo, nota, comentario) => {
      try {
        if (!pedido?.id) throw new Error('Pedido inválido');
        const notaFinal = nota || avaliarPedido.nota || 5;
        const comentarioFinal = comentario !== undefined ? comentario : avaliarPedido.comentario || '';
        const campoAvaliado = alvo === 'freelancer'
          ? 'avaliacao_freelancer_enviada'
          : 'avaliacao_barbearia_enviada';

        if (pedido?.[campoAvaliado]) {
          notify('Essa avaliação já foi enviada.', 'info');
          return;
        }
        
        let url = '';
        if (alvo === 'freelancer' && pedido.barbeiro_id) {
          url = `${API_URL}/api/v1/avaliacoes/freelancer/${pedido.barbeiro_id}`;
        } else if (alvo === 'barbearia' && pedido.barbearia_id) {
          url = `${API_URL}/api/v1/avaliacoes/barbearia/${pedido.barbearia_id}`;
        } else {
          throw new Error('Dados do avaliando ausentes');
        }
        const r = await fetch(url, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
          body: JSON.stringify({ chamado_id: pedido.id, nota: notaFinal, comentario: comentarioFinal })
        });
        const data = await r.json();
        if (!r.ok) throw new Error(data.detail || 'Falha ao avaliar');
        notify('Avaliação enviada!', 'success');
        // Mantém o pedido visível e marca apenas o alvo avaliado para evitar
        // que a seção de avaliações "desapareça" após o envio.
        setMyOrders((prev) => prev.map((o) => {
          if (o.id !== pedido.id) return o;
          return { ...o, [campoAvaliado]: true };
        }));
        setSelectedOrder((prev) => {
          if (!prev || prev.id !== pedido.id) return prev;
          return { ...prev, [campoAvaliado]: true };
        });
        setAvaliarPedido({ id: null, alvo: null, nota: 5, comentario: '' });
      } catch (err) {
        notify(err.message || 'Erro ao enviar avaliação', 'error');
      }
    };

    return (
      <div className="bg-black h-full flex flex-col w-full text-white">
        {/* ETAPA 3: Visualizar Serviços e Agendar */}
        {selectedShop && selectedBarbeiro ? (
          <div className="h-full flex flex-col bg-zinc-900 w-full animate-in slide-in-from-right">
             <div className="relative h-64 shrink-0">
                <img src={getShopImage(selectedShop.id)} className="w-full h-full object-cover" alt="Shop" />
                <div className="absolute inset-0 bg-gradient-to-t from-black via-transparent to-transparent"></div>
                <button onClick={() => setSelectedShop(null)} className="absolute top-4 left-4 p-2 bg-black/50 rounded-full text-white backdrop-blur"><ArrowRight size={20} className="rotate-180"/></button>
                <div className="absolute bottom-4 left-4">
                    <h1 className="text-2xl font-bold">{selectedShop.nome}</h1>
                    <p className="text-sm text-zinc-300">Barbeiro: {selectedBarbeiro.nome}</p>
                      <div className="flex items-center gap-2 text-xs text-zinc-300 flex-wrap mt-1">
                      <span className="flex items-center gap-1"><MapPin size={12}/> {selectedShop.endereco}</span>
                      <button
                        onClick={() => openMaps(selectedShop)}
                        className="px-3 py-1 rounded-full bg-gradient-to-r from-orange-600 to-red-600 text-white font-extrabold text-[10px] active:scale-95"
                      >Abrir no Maps</button>
                    </div>
                    <div className="flex flex-wrap gap-2 mt-3">
                      <button
                        onClick={() => handleCall(selectedBarbeiro?.telefone)}
                        className="px-3 py-1 rounded-full bg-zinc-800 text-white text-[10px] font-bold"
                      >Ligar Barbeiro</button>
                      <button
                        onClick={() => handleWhatsApp(selectedBarbeiro?.telefone)}
                        className="px-3 py-1 rounded-full bg-green-600 text-white text-[10px] font-bold"
                      >WhatsApp</button>
                      <button
                        onClick={() => handleCall(selectedShop?.telefone)}
                        className="px-3 py-1 rounded-full bg-zinc-700 text-white text-[10px] font-bold"
                      >Ligar Barbearia</button>
                    </div>
                </div>
            </div>
            <div className="flex-1 bg-black -mt-6 rounded-t-3xl p-6 relative z-10 overflow-y-auto pb-20">
                <div className="w-10 h-1 bg-zinc-800 rounded-full mx-auto mb-6"></div>
                <h3 className="text-zinc-500 text-[10px] font-bold uppercase tracking-widest mb-3">Serviços</h3>
                <div className="space-y-3">
                    {services.map(s => (
                        <div key={s.id} className="flex justify-between items-center bg-zinc-900 p-4 rounded-xl border border-zinc-800">
                            <div><span className="block font-bold text-sm">{s.nome}</span><span className="text-green-400 text-xs font-bold">R$ {s.valor}</span></div>
                            <button onClick={() => handleBooking(s)} className="bg-gradient-to-r from-orange-600 to-red-600 text-white px-4 py-2 rounded-2xl font-extrabold text-sm flex items-center gap-2 active:scale-95">Agendar</button>
                        </div>
                    ))}
                </div>
                
                {/* Modal de seleção de data/hora */}
                {showDatePicker && selectedService && (
                  <div className="fixed inset-0 bg-black/80 backdrop-blur-sm z-50 flex items-end sm:items-center justify-center p-4">
                    <div className="bg-zinc-900 rounded-2xl w-full max-w-md p-6 border border-zinc-800 animate-in slide-in-from-bottom">
                      <h3 className="text-xl font-bold mb-2">{selectedService.nome}</h3>
                      <p className="text-sm text-zinc-400 mb-6">R$ {selectedService.valor} • {selectedBarbeiro.nome}</p>
                      
                      <div className="space-y-4">
                        <div>
                          <label className="block text-xs font-bold text-zinc-400 mb-2">Data</label>
                          <input
                            type="date"
                            value={selectedDate}
                            onChange={(e) => setSelectedDate(e.target.value)}
                            min={new Date().toISOString().split('T')[0]}
                            className="bm-input w-full bg-black border border-zinc-800 rounded-lg p-3 text-white outline-none focus:border-orange-500"
                          />
                        </div>
                        
                        <div>
                          <label className="block text-xs font-bold text-zinc-400 mb-2">Horário</label>
                          <input
                            type="time"
                            value={selectedTime}
                            onChange={(e) => setSelectedTime(e.target.value)}
                            className="bm-input w-full bg-black border border-zinc-800 rounded-lg p-3 text-white outline-none focus:border-orange-500"
                          />
                        </div>
                      </div>
                      
                      <div className="flex gap-3 mt-6">
                        <button
                          onClick={() => { setShowDatePicker(false); setSelectedService(null); }}
                          className="flex-1 bg-zinc-800 text-white px-4 py-3 rounded-lg font-bold active:scale-95"
                        >
                          Cancelar
                        </button>
                        <button
                          onClick={confirmBooking}
                          className="flex-1 bg-orange-500 text-white px-4 py-3 rounded-lg font-bold active:scale-95"
                        >
                          Confirmar
                        </button>
                      </div>
                    </div>
                  </div>
                )}
            </div>
          </div>
        ) : selectedBarbeiro ? (
          /* ETAPA 2: Selecionar Barbearia */
          <>
            <div className="p-5 pt-8 sticky top-0 bg-black/80 backdrop-blur-md z-20 border-b border-zinc-800">
                <div className="flex items-center gap-3 mb-4">
                    <button onClick={() => setSelectedBarbeiro(null)} className="p-2 bg-zinc-900 rounded-full text-zinc-400"><ArrowRight size={16} className="rotate-180"/></button>
                    <div>
                      <h1 className="text-xl font-bold">{selectedBarbeiro.nome}</h1>
                      <p className="text-xs text-zinc-500">Selecione o local de atendimento</p>
                    </div>
                </div>
            </div>
            <div className="flex-1 overflow-y-auto p-4 space-y-4 pb-24">
                {shops.map(shop => (
                    <div key={shop.id} onClick={() => handleSelectShop(shop)} className="bg-zinc-900 rounded-2xl overflow-hidden border border-zinc-800 active:scale-95 transition-transform cursor-pointer group">
                        <div className="h-32 w-full relative">
                            <img src={getShopImage(shop.id)} className="w-full h-full object-cover opacity-60 group-hover:opacity-80 transition-opacity" alt={shop.nome} />
                            <div className="absolute bottom-2 left-3 font-bold text-lg shadow-black drop-shadow-md">{shop.nome}</div>
                        </div>
                        <div className="p-3 flex justify-between items-center">
                    <div className="flex items-center gap-2 text-xs text-zinc-400">
                      <span className="flex items-center gap-1"><MapPin size={12}/> {shop.endereco}</span>
                      <button
                      className="px-3 py-1 rounded-lg bg-zinc-800 border border-zinc-700 text-[10px] font-bold hover:border-orange-500"
                      onClick={(e) => { e.stopPropagation(); openMaps(shop); }}
                      >Ver rota</button>
                    </div>
                    <span className="text-green-500 text-[10px] font-bold px-2 py-1 bg-green-900/20 rounded">ABERTO</span>
                        </div>
                    </div>
                ))}
            </div>
          </>
        ) : (
          /* ETAPA 1: Selecionar Barbeiro */
            <div className="flex flex-col h-full w-full bg-black">
              {/* Header fixo no topo */}
              <div className="p-5 pt-8 bg-black border-b border-zinc-800 shrink-0">
                  <div className="flex justify-between items-center mb-4">
                      <h1 className="text-xl font-bold">Olá, Cliente</h1>
                      <div className="flex items-center">
                        <button onClick={logout} className="p-2 bg-zinc-900 rounded-full text-zinc-400 hover:text-white ml-1"><LogOut size={16}/></button>
                      </div>
                  </div>
                  {tab === 'barbeiros' && (
                      <div className="space-y-3">
                          <div className="relative">
                              <Search className="absolute left-3 top-3 text-zinc-500" size={18} />
                              <input placeholder="Buscar barbeiro..." className="bm-input w-full bg-zinc-900 pl-10 pr-4 py-3 rounded-xl border border-zinc-800 outline-none focus:border-orange-500 text-sm" />
                          </div>
                          <button 
                            onClick={() => setShowAvailableOnly(!showAvailableOnly)}
                            className={`w-full px-4 py-2 rounded-xl font-bold text-sm transition-all ${
                              showAvailableOnly 
                                ? 'bg-green-600 text-white' 
                                : 'bg-zinc-900 text-zinc-300 border border-zinc-800'
                            }`}
                          >
                            🟢 Mostrar apenas disponíveis ({barbeiros.filter(b => b.disponivel).length})
                          </button>
                      </div>
                  )}
              </div>

              {/* Conteúdo scrollável */}
              <div className="flex-1 overflow-y-auto p-4 space-y-4 pb-24">
                {tab === 'barbeiros' ? barbeiros.filter(b => !showAvailableOnly || b.disponivel).map(barbeiro => {
                    const disponivelEmBarbearia = barbeiro.presente_em_local && barbeiro.barbearia_atual_nome;
                    const statusTexto = disponivelEmBarbearia
                      ? `🟢 Disponível em ${barbeiro.barbearia_atual_nome}`
                      : (barbeiro.disponivel || barbeiro.online_regiao)
                        ? '🟢 Disponível'
                        : '⚫ Ocupado';
                    const statusClass = (barbeiro.disponivel || barbeiro.online_regiao)
                      ? 'bg-green-900/40 text-green-400'
                      : 'bg-zinc-800/40 text-zinc-400';

                    return (
                    <div key={barbeiro.id} onClick={() => handleSelectBarbeiro(barbeiro)} className="bg-zinc-900 rounded-2xl p-4 border border-zinc-800 active:scale-95 transition-transform cursor-pointer group flex items-center gap-4">
                        <div className="relative h-16 w-16">
                          <div className="h-16 w-16 rounded-full bg-gradient-to-br from-orange-500 to-orange-700 flex items-center justify-center text-white font-bold text-2xl">
                            {barbeiro.nome.charAt(0).toUpperCase()}
                          </div>
                          <div className={`absolute bottom-0 right-0 w-5 h-5 rounded-full border-2 border-zinc-900 ${barbeiro.disponivel ? 'bg-green-500 animate-pulse' : 'bg-zinc-700'}`}></div>
                        </div>
                        <div className="flex-1">
                          <h3 className="font-bold text-lg">{barbeiro.nome}</h3>
                          <p className="text-xs text-zinc-500">{barbeiro.telefone || 'Sem telefone'}</p>
                          <div className="flex items-center gap-2 mt-1 flex-wrap">
                            <span className={`text-[10px] font-bold px-2 py-1 rounded-full ${statusClass}`}>
                              {statusTexto}
                            </span>
                            {barbeiro.documento_verificado && (
                              <span className="inline-flex items-center gap-1 text-[10px] text-blue-400"><CheckCircle size={12}/> Verificado</span>
                            )}
                            {barbeiro.distancia_km !== undefined && (
                              <span className="inline-flex items-center gap-1 text-[10px] text-zinc-500">
                                <MapPin size={10}/> {barbeiro.distancia_km} km
                              </span>
                            )}
                          </div>
                        </div>
                        <ArrowRight className="text-zinc-600 group-hover:text-orange-500" size={20}/>
                    </div>
                    );
                    }) : tab === 'barbearias' ? (
                    <div className="space-y-3">
                        <h2 className="font-bold text-sm text-zinc-400 uppercase tracking-widest mb-4">Barbearias Próximas ✅</h2>
                        {shops.length === 0 ? (
                            <p className="text-zinc-600 text-center py-10">Nenhuma barbearia disponível próxima.</p>
                        ) : (
                            shops.map(shop => (
                                <div key={shop.id} onClick={() => openMaps(shop)} className="bg-zinc-900 rounded-2xl p-4 border border-zinc-800 active:scale-95 transition-transform cursor-pointer group">
                                    <div className="flex items-start justify-between mb-2">
                                        <div>
                                            <h3 className="font-bold text-lg">{shop.nome}</h3>
                                            <p className="text-xs text-zinc-500">{shop.bairro}, {shop.cidade}</p>
                                        </div>
                                        <div className="text-right">
                                            {shop.distancia_km && (
                                                <div className="flex items-center gap-1 text-orange-500 text-sm font-bold">
                                                    <MapPin size={14}/> {shop.distancia_km} km
                                                </div>
                                            )}
                                        </div>
                                    </div>
                                    <p className="text-xs text-zinc-400 mb-3">{shop.endereco}</p>
                                    {shop.descricao && <p className="text-xs text-zinc-500 mb-2">{shop.descricao}</p>}
                                    <div className="flex gap-2 text-[10px]">
                                        {shop.telefone && <a href={`tel:${shop.telefone}`} className="flex-1 bg-blue-600/20 text-blue-400 px-3 py-2 rounded-lg">📞 {shop.telefone}</a>}
                                        <a href={`mailto:${shop.email}`} className="flex-1 bg-purple-600/20 text-purple-400 px-3 py-2 rounded-lg">📧 Email</a>
                                    </div>
                                </div>
                            ))
                        )}
                    </div>
                ) : tab === 'perfil' ? (
                    <div className="space-y-4 pb-24">
                      <TelaPerfilUsuario userType="cliente" token={token} onLogout={logout} onNotify={notify} />
                    </div>
                ) : tab === 'pedidos' ? (
                    <div className="space-y-3">
                        <h2 className="font-bold text-sm text-zinc-400 uppercase tracking-widest mb-4">Meus Agendamentos</h2>
                        {!Array.isArray(myOrders) || myOrders.length === 0 ? (
                          <p className="text-zinc-600 text-center py-10">Nenhum agendamento.</p>
                        ) : myOrders.map((p) => (
                          <div key={p.id} onClick={() => setSelectedOrder(selectedOrder?.id === p.id ? null : p)} className={`bg-zinc-900 p-4 rounded-xl border cursor-pointer transition-all ${selectedOrder?.id === p.id ? 'border-orange-500 bg-zinc-800 shadow-lg shadow-orange-500/20' : 'border-zinc-800 hover:border-orange-500/50'}`}>
                            <div className="flex gap-4 items-center">
                              <div className="h-10 w-10 rounded-full bg-orange-600/20 flex items-center justify-center text-orange-500"><Calendar size={18}/></div>
                              <div className="flex-1">
                                <h3 className="font-bold text-sm">{p.descricao || "Serviço"}</h3>
                                <p className="text-xs text-zinc-500">{p.nome_barbearia || "Barbearia"}</p>
                                {p.status === 'concluido' && (
                                  <p className="text-xs text-yellow-400 font-bold mt-1">👆 Clique para avaliar</p>
                                )}
                              </div>
                              <div className="text-right">
                                <span className="block text-green-400 font-bold text-sm">R$ {p.valor || 0}</span>
                                <span className={`text-[10px] font-bold ${p.status === 'concluido' ? 'text-yellow-400' : 'text-zinc-500'}`}>{p.status === 'concluido' ? '✅ CONCLUÍDO' : p.status || "AGENDADO"}</span>
                              </div>
                            </div>
                            <div className="mt-3">
                              <button
                                onClick={(e) => { e.stopPropagation(); abrirPagamento(p); }}
                                className="w-full bg-gradient-to-r from-orange-600 to-red-600 text-white py-2 rounded-2xl font-extrabold text-sm active:scale-95"
                              >Pagar</button>
                            </div>
                            
                            {/* Expandir ao clicar */}
                            {selectedOrder?.id === p.id && p.status === 'concluido' && (
                              <div className="mt-3 grid grid-cols-1 gap-3 animate-in fade-in">
                                <div className="bg-gradient-to-br from-yellow-500/10 to-orange-500/10 p-4 rounded-lg border border-yellow-500/30">
                                  <p className="text-xs text-yellow-400 mb-2 font-bold flex items-center gap-2">⭐ Avaliar Barbeiro/Freelancer</p>
                                  <div className="mb-3 bg-black/30 p-2 rounded-lg border border-yellow-500/20">
                                    <p className="text-xs text-zinc-400">Avaliando:</p>
                                    <p className="font-bold text-sm text-white">{p.nome_barbeiro || 'Barbeiro'}</p>
                                  </div>
                                  <div className="flex items-center gap-3 mb-3">
                                    {[1,2,3,4,5].map(n => (
                                      <button key={n} onClick={() => setAvaliarPedido({ ...avaliarPedido, id: p.id, alvo: 'freelancer', nota: n })} className={`text-2xl transition-all ${avaliarPedido.id===p.id && avaliarPedido.alvo==='freelancer' && avaliarPedido.nota>=n ? 'text-yellow-400 scale-125' : 'text-zinc-700 hover:text-yellow-400'}`}>★</button>
                                    ))}
                                  </div>
                                  <input className="bm-input bg-black/40 rounded-lg p-3 border border-zinc-700 text-xs w-full placeholder-zinc-600 focus:border-yellow-400 outline-none" placeholder="Deixe um comentário... (opcional)" value={avaliarPedido.id===p.id && avaliarPedido?.alvo==='freelancer' ? avaliarPedido?.comentario || '' : ''} onChange={e=> setAvaliarPedido({ ...avaliarPedido, id: p.id, alvo: 'freelancer', comentario: e.target.value }) } />
                                  <button
                                    onClick={() => enviarAvaliacao(p, 'freelancer')}
                                    disabled={p.avaliacao_freelancer_enviada || p.avaliado_freelancer}
                                    className="mt-3 w-full bg-gradient-to-r from-yellow-500 to-orange-500 text-black px-4 py-2 rounded-lg text-xs font-bold hover:shadow-lg hover:shadow-yellow-500/30 transition-all disabled:opacity-60 disabled:cursor-not-allowed"
                                  >
                                    {p.avaliacao_freelancer_enviada || p.avaliado_freelancer ? '✅ Avaliação Enviada' : '✅ Enviar Avaliação'}
                                  </button>
                                </div>
                                <div className="bg-gradient-to-br from-blue-500/10 to-cyan-500/10 p-4 rounded-lg border border-blue-500/30">
                                  <p className="text-xs text-blue-400 mb-2 font-bold flex items-center gap-2">🏪 Avaliar Barbearia</p>
                                  <div className="mb-3 bg-black/30 p-2 rounded-lg border border-blue-500/20">
                                    <p className="text-xs text-zinc-400">Avaliando:</p>
                                    <p className="font-bold text-sm text-white">{p.nome_barbearia || 'Barbearia'}</p>
                                  </div>
                                  <div className="flex items-center gap-3 mb-3">
                                    {[1,2,3,4,5].map(n => (
                                      <button key={n} onClick={() => setAvaliarPedido({ ...avaliarPedido, id: p.id, alvo: 'barbearia', nota: n })} className={`text-2xl transition-all ${avaliarPedido.id===p.id && avaliarPedido.alvo==='barbearia' && avaliarPedido.nota>=n ? 'text-blue-400 scale-125' : 'text-zinc-700 hover:text-blue-400'}`}>★</button>
                                    ))}
                                  </div>
                                  <input className="bm-input bg-black/40 rounded-lg p-3 border border-zinc-700 text-xs w-full placeholder-zinc-600 focus:border-blue-400 outline-none" placeholder="Deixe um comentário... (opcional)" value={avaliarPedido.id===p.id && avaliarPedido?.alvo==='barbearia' ? avaliarPedido?.comentario || '' : ''} onChange={e=> setAvaliarPedido({ ...avaliarPedido, id: p.id, alvo: 'barbearia', comentario: e.target.value }) } />
                                  <button
                                    onClick={() => enviarAvaliacao(p, 'barbearia')}
                                    disabled={p.avaliacao_barbearia_enviada || p.avaliado_barbearia}
                                    className="mt-3 w-full bg-gradient-to-r from-blue-500 to-cyan-500 text-black px-4 py-2 rounded-lg text-xs font-bold hover:shadow-lg hover:shadow-blue-500/30 transition-all disabled:opacity-60 disabled:cursor-not-allowed"
                                  >
                                    {p.avaliacao_barbearia_enviada || p.avaliado_barbearia ? '✅ Avaliação Enviada' : '✅ Enviar Avaliação'}
                                  </button>
                                </div>
                              </div>
                            )}
                            
                            {selectedOrder?.id === p.id && p.status !== 'concluido' && (
                              <div className="mt-3 p-3 bg-black/40 rounded-lg border border-zinc-800/50 text-xs text-zinc-400">
                                <p>Agendamento será concluído para avaliar após o atendimento</p>
                              </div>
                            )}
                          </div>
                        ))}
                    </div>
                ) : null}
              </div>

              {/* Avaliações do perfil selecionado */}
              {selectedBarbeiro && (
                <div className="p-4 pb-24">
                  <h3 className="text-zinc-500 text-xs font-bold uppercase mb-2">Avaliações do Barbeiro</h3>
                  <div className="space-y-2">
                    {avaliacoesBarbeiro.map(av => (
                      <div key={av.id} className="bg-zinc-900 p-3 rounded-lg border border-zinc-800/50 flex items-center justify-between">
                        <div>
                          <p className="text-sm font-bold">{av.avaliador_nome || 'Usuário'}</p>
                          <p className="text-xs text-zinc-400">{av.comentario || 'Sem comentário'}</p>
                        </div>
                        <div className="text-yellow-400 font-bold text-sm">{'★'.repeat(av.nota)}</div>
                      </div>
                    ))}
                    {avaliacoesBarbeiro.length === 0 && <p className="text-zinc-600 text-xs">Sem avaliações ainda.</p>}
                  </div>
                </div>
              )}

              {selectedShop && (
                <div className="p-4 pb-24">
                  <h3 className="text-zinc-500 text-xs font-bold uppercase mb-2">Avaliações da Barbearia</h3>
                  <div className="space-y-2">
                    {avaliacoesShop.map(av => (
                      <div key={av.id} className="bg-zinc-900 p-3 rounded-lg border border-zinc-800/50 flex items-center justify-between">
                        <div>
                          <p className="text-sm font-bold">{av.avaliador_nome || 'Usuário'}</p>
                          <p className="text-xs text-zinc-400">{av.comentario || 'Sem comentário'}</p>
                        </div>
                        <div className="text-yellow-400 font-bold text-sm">{'★'.repeat(av.nota)}</div>
                      </div>
                    ))}
                    {avaliacoesShop.length === 0 && <p className="text-zinc-600 text-xs">Sem avaliações ainda.</p>}
                  </div>
                </div>
              )}

            <div className="bm-bottom-nav fixed bottom-0 left-1/2 -translate-x-1/2 w-full max-w-[400px] h-[calc(4.4rem+env(safe-area-inset-bottom))] pb-[env(safe-area-inset-bottom)] flex justify-around items-center z-30 px-2">
              <button data-active={tab === 'barbeiros'} onClick={() => setTab('barbeiros')} className={`bm-bottom-nav-btn flex flex-col items-center gap-1 p-1 w-12 ${tab === 'barbeiros' ? 'text-orange-500 bg-orange-500/5' : 'text-zinc-600'}`}><Search size={16} /><span>Buscar</span></button>
              <button data-active={tab === 'barbearias'} onClick={() => setTab('barbearias')} className={`bm-bottom-nav-btn flex flex-col items-center gap-1 p-1 w-12 ${tab === 'barbearias' ? 'text-orange-500 bg-orange-500/5' : 'text-zinc-600'}`}><Store size={16} /><span>Lojas</span></button>
              <button data-active={tab === 'pedidos'} onClick={() => setTab('pedidos')} className={`bm-bottom-nav-btn flex flex-col items-center gap-1 p-1 w-12 ${tab === 'pedidos' ? 'text-orange-500 bg-orange-500/5' : 'text-zinc-600'}`}><History size={16} /><span>Agenda</span></button>
              <button data-active={tab === 'perfil'} onClick={() => setTab('perfil')} className={`bm-bottom-nav-btn flex flex-col items-center gap-1 p-1 w-12 ${tab === 'perfil' ? 'text-orange-500 bg-orange-500/5' : 'text-zinc-600'}`}><User size={16} /><span>Perfil</span></button>
            </div>
          </div>
        )}
      </div>
    );
  };

  // ----------------------------------------------------------------------
  // ARQUIVO: src/components/BarberDashboard.jsx
  // ----------------------------------------------------------------------
  const BarberDashboard = () => {
    const [user, setUser] = useState(null);
    const [, setMinhasAvaliacoes] = useState(null);
    const [meusAgendamentos, setMeusAgendamentos] = useState([]);
    const [_avaliarComoBarbeiro, _setAvaliarComoBarbeiro] = useState({ chamadoId: null, alvo: null, nota: 5, comentario: '' });
    const [cadeirasDisponiveis, setCadeirasDisponiveis] = useState([]);
    const [assumindoCadeiraId, setAssumindoCadeiraId] = useState(null);
    const [, setSelectedAgendamento] = useState(null); // Novo estado para agendamento selecionado
    const [tabBarbeiro, setTabBarbeiro] = useState('inicio'); // Tab: inicio | agenda | ganhos | avaliar | perfil
    const [disponivel, setDisponivel] = useState(false); // Estado para disponibilidade
    const [clientePerfil, setClientePerfil] = useState(null);
    const [clientePerfilLoading, setClientePerfilLoading] = useState(false);
    const [clienteFotoModal, setClienteFotoModal] = useState(null);
    const [, setClienteHistorico] = useState([]);
    const [, setClienteAvaliacoes] = useState([]);
    const [clienteAvaliacaoMedia, setClienteAvaliacaoMedia] = useState(null);
    const isConcluido = (status = '') => (status || '').toString().toLowerCase().includes('conclu');

    // Usar hook de sincronização em tempo real para jobs
    const { jobs, loading: _loading, isConnected } = useLiveJobs(token, API_URL);

    const carregarMeusAgendamentos = useCallback(async () => {
      try {
        const r = await fetch(`${API_URL}/api/v1/barbeiro/agendamentos/meus`, {
          headers: { 'Authorization': `Bearer ${token}` }
        });
        if (r.ok) {
          const data = await r.json();
          setMeusAgendamentos(Array.isArray(data) ? data : []);
        } else {
          setMeusAgendamentos([]);
        }
      } catch {
        setMeusAgendamentos([]);
      }
    }, []);

    useEffect(() => {
      // Buscar status de verificação
      const fetchUserStatus = () => {
        fetch(`${API_URL}/api/v1/documentos/status`, {
          headers: {'Authorization': `Bearer ${token}`}
        })
        .then(r => r.json())
        .then(data => {
          setUser(data);
          // Inicializar estado de disponibilidade com valor do backend
          if (data.disponivel !== undefined) {
            setDisponivel(data.disponivel);
          }
        })
        .catch(() => setUser(null));
      };
      
      fetchUserStatus();
      
      // Se email não está verificado, recarregar a cada 10 segundos
      const interval = setInterval(() => {
        if (!user?.email_verificado) {
          fetchUserStatus();
        }
      }, 10000);
      
      return () => clearInterval(interval);
    }, [user?.email_verificado]);

    useEffect(() => {
      if (!clientePerfil) return;
      const onKeyDown = (event) => {
        if (event.key === 'Escape') {
          setClientePerfil(null);
        }
      };
      window.addEventListener('keydown', onKeyDown);
      return () => window.removeEventListener('keydown', onKeyDown);
    }, [clientePerfil]);

    useEffect(() => {
      // Agendamentos do barbeiro (usado para avaliar cliente/barbearia após conclusão)
      carregarMeusAgendamentos();

      // Buscar cadeiras acionadas próximas
      (async () => {
        try {
          const r = await fetch(`${API_URL}/api/v1/cadeiras/acionadas/proximas`, {
            headers: { 'Authorization': `Bearer ${token}` }
          });
          if (r.ok) {
            const data = await r.json();
            setCadeirasDisponiveis(Array.isArray(data) ? data : []);
          } else {
            setCadeirasDisponiveis([]);
          }
        } catch {
          setCadeirasDisponiveis([]);
        }
      })();

      // Atualizar cadeiras a cada 30 segundos
      const interval = setInterval(async () => {
        try {
          const r = await fetch(`${API_URL}/api/v1/cadeiras/acionadas/proximas`, {
            headers: { 'Authorization': `Bearer ${token}` }
          });
          if (r.ok) {
            const data = await r.json();
            setCadeirasDisponiveis(Array.isArray(data) ? data : []);
          }
        } catch (_err) {
          setCadeirasDisponiveis([]);
        }
      }, 30000);

      // Atualizar agendamentos periodicamente
      const intervalAgendamentos = setInterval(carregarMeusAgendamentos, 10000);

      return () => {
        clearInterval(interval);
        clearInterval(intervalAgendamentos);
      };
    }, [carregarMeusAgendamentos]);

    useEffect(() => {
      // Minhas avaliações recebidas (como freelancer)
      (async () => {
        try {
          const r = await fetch(`${API_URL}/api/v1/avaliacoes/minhas-avaliacoes-recebidas`, {
            headers: { 'Authorization': `Bearer ${token}` }
          });
          if (r.ok) {
            const data = await r.json();
            setMinhasAvaliacoes(data);
          }
        } catch (_err) {
          setMinhasAvaliacoes(null);
        }
      })();
    }, []);

    const acceptJob = async (id) => {
      try {
        let res = await fetch(`${API_URL}/api/v1/chamados/${id}/aceitar`, {
          method: 'PUT',
          headers: { 'Authorization': `Bearer ${token}` }
        });

        if (!res.ok) {
          res = await fetch(`${API_URL}/api/v1/chamados/${id}/aprovacao-barbeiro`, {
            method: 'POST',
            headers: { 'Authorization': `Bearer ${token}` }
          });
        }

        if (!res.ok) {
          const data = await res.json().catch(() => ({}));
          throw new Error(data.detail || 'Erro ao aceitar');
        }

        const data = await res.json().catch(() => ({}));
        const numeroCadeira = data?.cadeira?.numero;
        const mensagem = numeroCadeira
          ? `Trabalho aceito! Cadeira ${numeroCadeira} reservada.`
          : "Trabalho aceito!";
        notify(mensagem, "success");
        await carregarMeusAgendamentos();
      } catch (err) {
        notify(err.message || "Não foi possível aceitar o chamado.", "error");
      }
    };

    const assumirAtendimento = async (cadeiraId) => {
      try {
        setAssumindoCadeiraId(cadeiraId);
        const res = await fetch(`${API_URL}/api/v1/cadeiras/${cadeiraId}/aceitar`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${token}`
          }
        });

        if (!res.ok) {
          const error = await res.json().catch(() => ({}));
          notify(error.detail || 'Nao foi possivel assumir atendimento', 'error');
          return;
        }

        const data = await res.json();
        notify(data.message || 'Atendimento assumido com sucesso!', 'success');
        setCadeirasDisponiveis((prev) => prev.filter((cadeira) => cadeira.id !== cadeiraId));
      } catch (err) {
        notify('Erro ao assumir atendimento: ' + err.message, 'error');
      } finally {
        setAssumindoCadeiraId(null);
      }
    };

    const rejectJob = async (id) => {
      try {
        const res = await fetch(`${API_URL}/api/v1/chamados/${id}/rejeitar`, {
          method: 'PUT',
          headers: { 'Authorization': `Bearer ${token}` }
        });

        if (!res.ok) {
          const data = await res.json().catch(() => ({}));
          throw new Error(data.detail || 'Erro ao recusar');
        }

        notify('Agendamento recusado', 'success');
        setMeusAgendamentos((prev) => prev.filter((a) => a.id !== id));
      } catch (err) {
        notify(err.message || 'Erro ao recusar', 'error');
      }
    };

    const abrirPerfilCliente = async (clienteId) => {
      if (!clienteId) {
        notify('Cliente nao identificado', 'error');
        return;
      }
      setClientePerfilLoading(true);
      try {
        const res = await fetch(`${API_URL}/api/v1/usuario/${clienteId}`);
        if (!res.ok) {
          const data = await res.json().catch(() => ({}));
          throw new Error(data.detail || 'Erro ao carregar perfil');
        }
        const data = await res.json();
        setClientePerfil(data);

        const historico = (meusAgendamentos || []).filter((ag) => ag.cliente_id === clienteId);
        setClienteHistorico(historico);

        try {
          const [avsRes, mediaRes] = await Promise.all([
            fetch(`${API_URL}/api/v1/usuario/${clienteId}/avaliacoes`),
            fetch(`${API_URL}/api/v1/usuario/${clienteId}/media_avaliacao`)
          ]);

          const avsData = avsRes.ok ? await avsRes.json() : [];
          const mediaData = mediaRes.ok ? await mediaRes.json() : null;

          setClienteAvaliacoes(Array.isArray(avsData) ? avsData : []);
          setClienteAvaliacaoMedia(mediaData);
        } catch {
          setClienteAvaliacoes([]);
          setClienteAvaliacaoMedia(null);
        }
      } catch (err) {
        notify(err.message || 'Erro ao carregar perfil', 'error');
      } finally {
        setClientePerfilLoading(false);
      }
    };

    const finalizarAtendimento = async (agendamento) => {
      try {
        // 1. Finalizar o chamado
        const res = await fetch(`${API_URL}/api/v1/chamados/${agendamento.id}/finalizar`, {
          method: 'PUT',
          headers: { 'Authorization': `Bearer ${token}` }
        });
        if (!res.ok) {
          const data = await res.json().catch(() => ({}));
          throw new Error(data.detail || 'Erro ao finalizar o corte');
        }

        // 2. Marcar como disponível
        try {
          await fetch(`${API_URL}/api/v1/barbeiro/disponibilidade`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
            body: JSON.stringify({ disponivel: true })
          });
          setDisponivel(true);
        } catch (err) {
          console.error('Erro ao atualizar disponibilidade:', err);
        }

        // 3. Recarregar agendamentos
        await carregarMeusAgendamentos();

        setSelectedAgendamento(agendamento);
        notify('✅ Corte finalizado! Avalie o cliente.', 'success');
      } catch (err) {
        notify(err.message || 'Erro ao finalizar o corte', 'error');
      }
    };

    return (
        <div className="bg-black h-full p-4 pb-32 text-white">
            <div className="flex justify-between items-center mb-6 pt-4">
                <div className="flex items-center gap-2">
                    <h1 className="text-xl font-bold flex items-center gap-2"><Scissors className="text-orange-500"/> Área do Barbeiro</h1>
                    {user?.documento_verificado && (
                        <CheckCircle size={20} className="text-blue-500 fill-blue-500" title="Verificado ✓" />
                    )}
                </div>
                <div className="flex items-center gap-2">
                  <button 
                    onClick={async () => {
                      try {
                        const novoEstado = !disponivel;
                        const res = await fetch(`${API_URL}/api/v1/barbeiro/disponibilidade`, {
                          method: 'PUT',
                          headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
                          body: JSON.stringify({ disponivel: novoEstado })
                        });
                        const data = await res.json();
                        if (res.ok) {
                          setDisponivel(novoEstado);
                          notify(novoEstado ? 'Você agora está disponível! 🟢' : 'Você saiu do ar ✓', 'success');
                        } else {
                          notify(data.detail || 'Erro ao atualizar disponibilidade', 'error');
                        }
                      } catch (_err) {
                        notify('Erro ao atualizar disponibilidade', 'error');
                      }
                    }}
                    className={`px-4 py-2 rounded-lg font-bold text-sm transition-all ${disponivel ? 'bg-green-600 hover:bg-green-700' : 'bg-zinc-800 hover:bg-zinc-700'}`}
                  >
                    {disponivel ? '🟢 Disponível' : '⚫ Offline'}
                  </button>
                  <VerificationBadge user={user} onClick={() => {
                    if (!user?.email_verificado) {
                      notify('Verifique seu email para receber chamados.', 'info');
                    }
                  }} />
                  <button onClick={logout} className="text-zinc-500"><LogOut size={20}/></button>
                </div>
            </div>
            {user && !user.email_verificado && (
                <div className="bg-yellow-600/10 border border-yellow-600/30 p-4 rounded-xl mb-4 flex items-center gap-3">
                    <AlertCircle size={20} className="text-yellow-500"/>
                    <div className="flex-1">
                  <span className="text-yellow-500 font-bold text-sm block">Verificação de email pendente</span>
                  <span className="text-yellow-400 text-xs">Confirme seu email para receber chamados</span>
                    </div>
                    <button 
                      onClick={async () => {
                        try {
                          const r = await fetch(`${API_URL}/api/v1/reenviar_email_verificacao`, {
                            method: 'POST',
                            headers: { 'Authorization': `Bearer ${token}` }
                          });
                          const data = await r.json();
                          if (r.ok) notify('Email reenviado! Verifique sua caixa de entrada 📧', 'success');
                          else notify(data.detail || 'Erro ao reenviar', 'error');
                        } catch (_e) {
                          notify('Erro ao reenviar email', 'error');
                        }
                      }}
                      className="px-4 py-2 bg-yellow-600 hover:bg-yellow-700 text-white text-sm rounded-lg font-bold whitespace-nowrap"
                    >📧 Reenviar</button>
                </div>
            )}
            {clientePerfil && (
              <div
                className="fixed inset-0 bg-black/70 backdrop-blur-sm z-50 flex items-center justify-center p-4"
                onClick={() => setClientePerfil(null)}
              >
                <div
                  className="bg-zinc-900 rounded-2xl w-full max-w-sm border border-zinc-800 p-6 relative"
                  onClick={(e) => e.stopPropagation()}
                >
                  <button
                    onClick={() => setClientePerfil(null)}
                    className="absolute top-3 right-3 text-zinc-400 hover:text-white"
                  >
                    <X size={18} />
                  </button>

                  {/* Foto Grande */}
                  <div className="flex justify-center mb-6">
                    <button
                      type="button"
                      onClick={() => clientePerfil.foto_perfil && setClienteFotoModal(clientePerfil.foto_perfil)}
                      className="h-20 w-20 rounded-full bg-orange-600 flex items-center justify-center font-bold overflow-hidden border-2 border-orange-500 hover:border-orange-400 transition-all cursor-pointer"
                      title={clientePerfil.foto_perfil ? 'Clique para expandir' : 'Sem foto'}
                    >
                      {clientePerfil.foto_perfil ? (
                        <img
                          src={clientePerfil.foto_perfil}
                          alt="Foto do cliente"
                          className="h-20 w-20 object-cover"
                        />
                      ) : (
                        <span className="text-3xl text-white">{(clientePerfil.nome || 'C')[0]}</span>
                      )}
                    </button>
                  </div>

                  {/* Informações */}
                  <div className="text-center mb-6">
                    <p className="text-xl font-bold">{clientePerfil.nome || 'Cliente'}</p>
                    <p className="text-sm text-zinc-400 mt-1">{clientePerfil.email || 'Email não informado'}</p>
                    {clienteAvaliacaoMedia && (
                      <div className="mt-3 flex items-center justify-center gap-2">
                        <span className="text-yellow-400 text-lg">{'★'.repeat(Math.round(clienteAvaliacaoMedia.media || 0))}</span>
                        <p className="text-sm font-bold text-zinc-300">{clienteAvaliacaoMedia.media || 0} <span className="text-zinc-500">({clienteAvaliacaoMedia.total_avaliacoes || 0})</span></p>
                      </div>
                    )}
                  </div>

                  {/* Dados de Contato */}
                  <div className="space-y-3 bg-black/40 rounded-lg p-4 border border-zinc-800/50">
                    {clientePerfil.telefone && (
                      <div className="flex items-center gap-2">
                        <span className="text-zinc-500">📱</span>
                        <div>
                          <p className="text-xs text-zinc-400">Telefone</p>
                          <p className="text-sm font-bold">{clientePerfil.telefone}</p>
                        </div>
                      </div>
                    )}
                    {clientePerfil.endereco && (
                      <div className="flex items-center gap-2">
                        <span className="text-zinc-500">📍</span>
                        <div>
                          <p className="text-xs text-zinc-400">Endereço</p>
                          <p className="text-sm font-bold">{clientePerfil.endereco}</p>
                        </div>
                      </div>
                    )}
                    {!clientePerfil.telefone && !clientePerfil.endereco && (
                      <p className="text-xs text-zinc-500 text-center">Sem informações de contato</p>
                    )}
                  </div>

                  <p className="text-xs text-zinc-600 text-center mt-4">Clique fora ou pressione ESC para fechar</p>
                </div>
              </div>
            )}

            {clienteFotoModal && (
              <div className="fixed inset-0 bg-black/80 backdrop-blur-sm z-50 flex items-center justify-center p-4" onClick={() => setClienteFotoModal(null)}>
                <img src={clienteFotoModal} alt="Foto do cliente" className="max-w-[90vw] max-h-[80vh] rounded-2xl border border-zinc-800" />
              </div>
            )}
            <div className="bg-orange-600/10 border border-orange-600/30 p-4 rounded-xl mb-6 flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <div className="h-2 w-2 bg-green-500 rounded-full animate-pulse"></div>
                  <span className="text-orange-500 font-bold text-sm">Disponível para chamados</span>
                </div>
                {isConnected && <span className="text-[10px] text-green-400 font-bold">🔴 Sincronizado</span>}
                {!isConnected && <span className="text-[10px] text-yellow-400 font-bold">⚠️ Atualizando...</span>}
            </div>

            {tabBarbeiro === 'inicio' && (
              <div className="pb-24">
                <h3 className="text-zinc-500 text-xs font-bold uppercase mb-4">Novos Chamados</h3>

                <div className="space-y-4">
                {jobs.map(job => (
                    <div key={job.id} className="bg-zinc-900 p-5 rounded-2xl border border-zinc-800 relative">
                        <div className="absolute top-0 right-0 bg-orange-500 text-white text-[10px] font-bold px-3 py-1 rounded-bl-xl">NOVO</div>
                        <h3 className="font-bold text-lg mb-1">{job.nome_cliente || 'Cliente'}</h3>
                        <p className="text-zinc-400 text-xs mb-1 flex items-center gap-1"><MapPin size={12}/> {job.nome_barbearia || 'Barbearia'}</p>
                        <p className="text-zinc-500 text-xs mb-3">{job.endereco_barbearia || 'Endereço não informado'}</p>
                        {job.data_hora_inicio && (
                          <p className="text-orange-400 text-xs mb-3 flex items-center gap-1">
                            <Calendar size={12}/> {new Date(job.data_hora_inicio).toLocaleString('pt-BR', { 
                              day: '2-digit', 
                              month: '2-digit', 
                              hour: '2-digit', 
                              minute: '2-digit' 
                            })}
                          </p>
                        )}
                        <div className="bg-black/40 p-3 rounded-xl mb-3 border border-zinc-800/50 flex justify-between items-center">
                          <span className="text-sm font-medium">{job.descricao || 'Serviço'}</span>
                          <span className="text-green-400 font-bold">R$ {job.valor || 0}</span>
                        </div>
                        <div className="grid grid-cols-2 gap-2">
                          <button onClick={() => acceptJob(job.id)} className="bg-gradient-to-r from-orange-600 to-red-600 text-white py-3 rounded-2xl font-extrabold text-sm hover:from-orange-700 hover:to-red-700">ACEITAR</button>
                          <button onClick={() => rejectJob(job.id)} className="bg-red-600 text-white py-3 rounded-xl font-bold text-sm hover:bg-red-700">RECUSAR</button>
                        </div>
                        <button
                          onClick={() => abrirPerfilCliente(job.cliente_id)}
                          disabled={clientePerfilLoading}
                          className="mt-2 w-full bg-zinc-800 text-white py-2 rounded-lg text-xs font-bold hover:bg-zinc-700 disabled:opacity-50"
                        >
                          {clientePerfilLoading ? 'Carregando...' : 'Ver perfil do cliente'}
                        </button>
                    </div>
                ))}
                {jobs.length === 0 && <p className="text-zinc-600 text-center text-sm py-10"></p>}
                </div>

                {meusAgendamentos.filter(a => !isConcluido(a.status)).length > 0 && (
                  <div className="bg-zinc-900/60 p-5 rounded-2xl border border-zinc-800 mt-6">
                    <h3 className="font-bold mb-4 text-sm">Atendimentos em andamento</h3>
                    <div className="space-y-3">
                      {meusAgendamentos.filter(a => !isConcluido(a.status)).map((ag) => (
                        <div key={ag.id} className="bg-black/40 p-4 rounded-lg border border-zinc-800/40">
                          <div className="flex items-center justify-between gap-3">
                            <div>
                              <p className="font-bold text-sm">{ag.cliente_nome || 'Cliente'}</p>
                              <p className="text-xs text-zinc-400">{ag.descricao || ag.servico || 'Serviço'}</p>
                              {ag.data_hora_inicio && (
                                <p className="text-xs text-orange-400 mt-1">
                                  {new Date(ag.data_hora_inicio).toLocaleString('pt-BR', {
                                    day: '2-digit',
                                    month: '2-digit',
                                    hour: '2-digit',
                                    minute: '2-digit'
                                  })}
                                </p>
                              )}
                            </div>
                            <span className="text-[10px] bg-yellow-600 text-white px-2 py-1 rounded font-bold">EM ANDAMENTO</span>
                          </div>
                          <button
                            onClick={() => finalizarAtendimento(ag)}
                            className="mt-3 w-full bg-green-600 hover:bg-green-700 text-white py-2 rounded-lg text-xs font-bold"
                          >✅ Finalizar Corte</button>
                          <button
                            onClick={() => abrirPerfilCliente(ag.cliente_id)}
                            disabled={clientePerfilLoading}
                            className="mt-2 w-full bg-zinc-800 text-white py-2 rounded-lg text-xs font-bold hover:bg-zinc-700 disabled:opacity-50"
                          >
                            {clientePerfilLoading ? 'Carregando...' : 'Ver perfil do cliente'}
                          </button>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* Cadeiras Disponíveis Próximas */}
                {cadeirasDisponiveis.length > 0 && (
                  <div className="mt-8">
                    <h3 className="text-zinc-500 text-xs font-bold uppercase mb-4 flex items-center gap-2">
                      <span className="h-2 w-2 bg-blue-500 rounded-full animate-pulse"></span>
                      Cadeiras Disponíveis Próximas ({cadeirasDisponiveis.length})
                    </h3>
                    <div className="space-y-3">
                      {cadeirasDisponiveis.map((cadeira) => (
                    <div key={cadeira.id} className="bg-zinc-900 p-4 rounded-xl border border-zinc-800/60">
                      <div className="flex justify-between items-center mb-1">
                        <h4 className="font-bold text-white text-base">{cadeira.barbearia_nome || 'Barbearia'}</h4>
                      </div>
                      <p className="text-xs text-zinc-400 flex items-center gap-1 mb-3">
                        <MapPin size={12}/> {cadeira.barbearia_endereco || 'Endereço não disponível'}
                      </p>
                      <div className="bg-blue-900/20 border border-blue-600/30 rounded-lg p-3">
                        <p className="text-xs text-blue-300 mb-2 font-semibold">Novo cliente aguardando na cadeira!</p>
                        <button 
                          onClick={() => assumirAtendimento(cadeira.id)}
                          disabled={assumindoCadeiraId === cadeira.id}
                          className="w-full bg-blue-600 hover:bg-blue-700 disabled:opacity-60 disabled:cursor-not-allowed text-white py-3 rounded-xl text-sm font-bold"
                        >
                          {assumindoCadeiraId === cadeira.id ? 'Assumindo...' : 'ASSUMIR ATENDIMENTO'}
                        </button>
                      </div>
                    </div>
                  ))}
                    </div>
                  </div>
                )}


                
              </div>
            )}

            {tabBarbeiro === 'agenda' && (
              <div className="pb-24">
                <h3 className="text-zinc-500 text-xs font-bold uppercase mb-4">Minha agenda</h3>
                {meusAgendamentos.length === 0 ? (
                  <p className="text-zinc-600 text-center text-sm py-10">Nenhum agendamento no momento.</p>
                ) : (
                  <div className="space-y-3">
                    {meusAgendamentos.map((ag) => (
                      <div key={ag.id} className="bg-zinc-900 p-4 rounded-xl border border-zinc-800">
                        <div className="flex items-center justify-between gap-3">
                          <div>
                            <p className="font-bold text-sm">{ag.cliente_nome || 'Cliente'}</p>
                            <p className="text-xs text-zinc-400">{ag.descricao || ag.servico || 'Serviço'}</p>
                            {ag.data_hora_inicio && (
                              <p className="text-xs text-orange-400 mt-1">
                                {new Date(ag.data_hora_inicio).toLocaleString('pt-BR', {
                                  day: '2-digit',
                                  month: '2-digit',
                                  hour: '2-digit',
                                  minute: '2-digit'
                                })}
                              </p>
                            )}
                          </div>
                          <span className="text-[10px] bg-zinc-800 text-zinc-300 px-2 py-1 rounded font-bold">
                            {String(ag.status || '').toUpperCase() || 'STATUS'}
                          </span>
                        </div>
                        {!isConcluido(ag.status) && (
                          <button
                            onClick={() => finalizarAtendimento(ag)}
                            className="mt-3 w-full bg-green-600 hover:bg-green-700 text-white py-2 rounded-lg text-xs font-bold"
                          >✅ Finalizar Corte</button>
                        )}
                        <button
                          onClick={() => abrirPerfilCliente(ag.cliente_id)}
                          disabled={clientePerfilLoading}
                          className="mt-2 w-full bg-zinc-800 text-white py-2 rounded-lg text-xs font-bold hover:bg-zinc-700 disabled:opacity-50"
                        >
                          {clientePerfilLoading ? 'Carregando...' : 'Ver perfil do cliente'}
                        </button>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}

            {tabBarbeiro === 'ganhos' && (
              <div className="pb-24">
                <PaymentSection userType="barbeiro" token={token} onNotify={notify} />
              </div>
            )}

            {tabBarbeiro === 'avaliar' && (
              <div className="pb-24">
                <AbaPadronizadaAvaliacoes
                  usuarioId={user?.id}
                  tipoUsuario="barbeiro"
                  nomeUsuario={user?.nome}
                  API_URL={API_URL}
                  token={token}
                  notify={notify}
                />
              </div>
            )}

            {tabBarbeiro === 'perfil' && (
              <div className="pb-24">
                <TelaPerfilUsuario userType="barbeiro" token={token} onLogout={logout} onNotify={notify} />
              </div>
            )}

            <div className="bm-bottom-nav fixed bottom-0 left-1/2 -translate-x-1/2 w-full max-w-[400px] h-[calc(4.4rem+env(safe-area-inset-bottom))] pb-[env(safe-area-inset-bottom)] flex justify-around items-center z-50 px-2">
              <button data-active={tabBarbeiro === 'inicio'} onClick={() => setTabBarbeiro('inicio')} className={`bm-bottom-nav-btn flex flex-col items-center gap-1 p-1 flex-1 ${tabBarbeiro === 'inicio' ? 'text-orange-500 bg-orange-500/5' : 'text-zinc-600'}`}>
                <Calendar size={16} />
                <span className="hidden sm:block">Início</span>
              </button>
              <button data-active={tabBarbeiro === 'agenda'} onClick={() => setTabBarbeiro('agenda')} className={`bm-bottom-nav-btn flex flex-col items-center gap-1 p-1 flex-1 ${tabBarbeiro === 'agenda' ? 'text-orange-500 bg-orange-500/5' : 'text-zinc-600'}`}>
                <History size={16} />
                <span className="hidden sm:block">Agenda</span>
              </button>
              <button data-active={tabBarbeiro === 'ganhos'} onClick={() => setTabBarbeiro('ganhos')} className={`bm-bottom-nav-btn flex flex-col items-center gap-1 p-1 flex-1 ${tabBarbeiro === 'ganhos' ? 'text-orange-500 bg-orange-500/5' : 'text-zinc-600'}`}>
                <CreditCard size={16} />
                <span className="hidden sm:block">Ganhos</span>
              </button>
              <button data-active={tabBarbeiro === 'avaliar'} onClick={() => setTabBarbeiro('avaliar')} className={`bm-bottom-nav-btn flex flex-col items-center gap-1 p-1 flex-1 ${tabBarbeiro === 'avaliar' ? 'text-orange-500 bg-orange-500/5' : 'text-zinc-600'}`}>
                <Star size={16} />
                <span className="hidden sm:block">Avaliar</span>
              </button>
              <button data-active={tabBarbeiro === 'perfil'} onClick={() => setTabBarbeiro('perfil')} className={`bm-bottom-nav-btn flex flex-col items-center gap-1 p-1 flex-1 ${tabBarbeiro === 'perfil' ? 'text-orange-500 bg-orange-500/5' : 'text-zinc-600'}`}>
                <User size={16} />
                <span className="hidden sm:block">Perfil</span>
              </button>
            </div>
        </div>
    );
  };

  // ----------------------------------------------------------------------
  // ARQUIVO: src/components/ShopDashboard.jsx
  // ----------------------------------------------------------------------
  const ShopDashboard = ({ token, logout, API_URL, notify, tabShop, setTabShop }) => {
    const [tabShopFallback, setTabShopFallback] = useState('gestao');
    const tabShopSafe = typeof tabShop === 'string' ? tabShop : tabShopFallback;
    const setTabShopSafe = useCallback((proximaAba) => {
      if (typeof setTabShop === 'function') {
        setTabShop(proximaAba);
        return;
      }
      setTabShopFallback(proximaAba);
    }, [setTabShop]);

    const [services, setServices] = useState([]);
    const [agendamentos, setAgendamentos] = useState([]);
    const [newService, setNewService] = useState({nome: '', valor: '', duracao_minutos: 30});
    const [barbeariaId, setBarbeariaId] = useState(null);
    const [user, setUser] = useState(null);
    const [hideVerification, setHideVerification] = useState(false);
    const [cadeiras, setCadeiras] = useState([]);
    const [cadeirasLoading, setCadeirasLoading] = useState(false);
    const [barbeirosPresentes, setBarbeirosPresentes] = useState([]);
    const [_barbeirosLoading, _setBarbeirosLoading] = useState(false);
    const [_freelancers, setFreelancers] = useState([]);
    const [_freelancersLoading, setFreelancersLoading] = useState(false);
    const [selectedFreelancerId, setSelectedFreelancerId] = useState('');
    const [selectedCadeiraId, setSelectedCadeiraId] = useState('');
    const [_presencaLoading, setPresencaLoading] = useState(false);
    const [solicitarFreelancerId, setSolicitarFreelancerId] = useState('');
    const [solicitarCadeiraId, setSolicitarCadeiraId] = useState('');
    const [_solicitarLoading, setSolicitarLoading] = useState(false);
    const [avaliacoesBarbearia, setAvaliacoesBarbearia] = useState([]);
    const [avaliarComoBarbearia, setAvaliarComoBarbearia] = useState({ chamadoId: null, alvo: null, nota: 5, comentario: '' });
    const [selectedAgendamentoShop, setSelectedAgendamentoShop] = useState(null); // Novo estado
    const isConcluidoShop = (status = '') => (status || '').toString().toLowerCase().includes('conclu');
    const isCanceladoShop = (status = '') => (status || '').toString().toLowerCase().includes('cancel');
    const agendamentosVisiveis = agendamentos.filter(a => !isCanceladoShop(a.status));
    useEffect(() => {
      // Buscar status de verificação
      const fetchUserStatus = () => {
        fetch(`${API_URL}/api/v1/documentos/status`, {
          headers: {'Authorization': `Bearer ${token}`}
        })
        .then(r => r.json())
        .then(data => setUser(data))
        .catch(() => {});
      };
      
      fetchUserStatus();
      
      // Se email não está verificado, recarregar a cada 10 segundos
      const interval = setInterval(() => {
        if (!user?.email_verificado) {
          fetchUserStatus();
        }
      }, 10000);
      
      return () => clearInterval(interval);
    }, [API_URL, token, user?.email_verificado]);

    useEffect(() => {
      const load = async () => {
        try {
          const b = await fetch(`${API_URL}/api/v1/barbearia/minha`, { headers: { 'Authorization': `Bearer ${token}` } });
          if (!b.ok) throw new Error();
          const data = await b.json();
          setBarbeariaId(data.id);
          const servicesRes = await fetch(`${API_URL}/api/v1/barbearia/${data.id}/servicos`);
          const servicesData = await servicesRes.json();
          setServices(Array.isArray(servicesData) ? servicesData : []);
          
          // Buscar agendamentos confirmados
          const agendamentosRes = await fetch(`${API_URL}/api/v1/barbearia/${data.id}/agendamentos`, { headers: { 'Authorization': `Bearer ${token}` } });
          if (agendamentosRes.ok) {
            const agendamentosData = await agendamentosRes.json();
            setAgendamentos(Array.isArray(agendamentosData) ? agendamentosData : []);
          }
        } catch (_err) {
          notify('Erro ao carregar dados', 'error');
        }
      };
      load();
    }, [API_URL, notify, token]);

    useEffect(() => {
      if (!barbeariaId) return;
      const loadCadeiras = async () => {
        try {
          const res = await fetch(`${API_URL}/api/v1/cadeiras/barbearia/${barbeariaId}`, {
            headers: { 'Authorization': `Bearer ${token}` }
          });
          if (res.ok) {
            const data = await res.json();
            setCadeiras(Array.isArray(data) ? data : []);
          }
        } catch (_err) {
          // Erro ao carregar cadeiras
        }
      };

      const loadBarbeirosPresentes = async () => {
        try {
          const res = await fetch(`${API_URL}/api/v1/barbearia/${barbeariaId}/barbeiros-presentes`, {
            headers: { 'Authorization': `Bearer ${token}` }
          });
          if (res.ok) {
            const data = await res.json();
            setBarbeirosPresentes(Array.isArray(data) ? data : []);
          }
        } catch (_err) {
          // Erro ao carregar barbeiros presentes
        }
      };

      loadCadeiras();
      loadBarbeirosPresentes();

      // Atualizar a cada 30 segundos
      const interval = setInterval(() => {
        loadCadeiras();
        loadBarbeirosPresentes();
      }, 30000);

      return () => clearInterval(interval);
    }, [API_URL, barbeariaId, token]);

    useEffect(() => {
      if (!barbeariaId || tabShopSafe !== 'gestao') return;
      const loadFreelancers = async () => {
        setFreelancersLoading(true);
        try {
          const res = await fetch(`${API_URL}/api/v1/barbeiros/todos`, {
            headers: { 'Authorization': `Bearer ${token}` }
          });
          if (res.ok) {
            const data = await res.json();
            setFreelancers(Array.isArray(data) ? data : []);
          } else {
            setFreelancers([]);
          }
        } catch {
          setFreelancers([]);
        } finally {
          setFreelancersLoading(false);
        }
      };
      loadFreelancers();
    }, [API_URL, barbeariaId, tabShopSafe, token]);

    useEffect(() => {
      if (!barbeariaId) return;
      const loadAvaliacoes = async () => {
        try {
          const r = await fetch(`${API_URL}/api/v1/avaliacoes/barbearia/${barbeariaId}/recebidas?limite=5`, {
            headers: { 'Authorization': `Bearer ${token}` }
          });
          if (r.ok) {
            const avs = await r.json();
            setAvaliacoesBarbearia(Array.isArray(avs) ? avs : []);
          } else {
            setAvaliacoesBarbearia([]);
          }
        } catch {
          setAvaliacoesBarbearia([]);
        }
      };
      loadAvaliacoes();
    }, [API_URL, barbeariaId, token]);

    const enviarAvaliacaoBarbearia = async (chamadoId, avaliadoId, alvo, naoFechar = false) => {
      try {
        if (!chamadoId || !avaliadoId) throw new Error('Dados incompletos para avaliação');
        const payload = {
          chamado_id: chamadoId,
          avaliado_id: avaliadoId,
          nota: avaliarComoBarbearia.nota || 5,
          comentario: avaliarComoBarbearia.comentario || ''
        };
        const res = await fetch(`${API_URL}/api/v1/avaliacoes/criar`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
          body: JSON.stringify(payload)
        });

        const raw = await res.text();
        let data = {};
        try {
          data = raw ? JSON.parse(raw) : {};
        } catch {
          data = { detail: raw };
        }

        console.log('📝 Avaliacao barbearia', {
          status: res.status,
          ok: res.ok,
          payload,
          response: data
        });

        if (!res.ok) throw new Error(data.detail || 'Erro ao enviar avaliação');
        notify('Avaliação enviada!', 'success');
        // Remover o agendamento avaliado da lista
        setAgendamentos(agendamentos.filter(a => a.id !== chamadoId));
        setAvaliarComoBarbearia({ chamadoId: null, alvo: null, nota: 5, comentario: '' });
        // Fechar o modal após sucesso
        if (!naoFechar) {
          setSelectedAgendamentoShop(null);
        }
      } catch (err) {
        notify(err.message || 'Falha ao avaliar', 'error');
      }
    };

    const acionarCadeira = async (cadeiraId) => {
      try {
        const res = await fetch(`${API_URL}/api/v1/cadeiras/${cadeiraId}/acionar`, {
          method: 'POST',
          headers: { 'Authorization': `Bearer ${token}` }
        });
        if (!res.ok) {
          const err = await res.json().catch(() => ({}));
          throw new Error(err.detail || 'Não foi possível acionar a cadeira');
        }
        notify('Cadeira acionada! Barbeiros próximos foram notificados 📢', 'success');
        // reload
        const cadRes = await fetch(`${API_URL}/api/v1/cadeiras/barbearia/${barbeariaId}`, {
          headers: { 'Authorization': `Bearer ${token}` }
        });
        if (cadRes.ok) {
          const data = await cadRes.json();
          setCadeiras(Array.isArray(data) ? data : []);
        }
      } catch (err) {
        notify(err.message || 'Erro ao acionar cadeira', 'error');
      }
    };

    const _desacionarCadeira = async (cadeiraId) => {
      try {
        const res = await fetch(`${API_URL}/api/v1/cadeiras/${cadeiraId}/desacionar-simples`, {
          method: 'POST',
          headers: { 'Authorization': `Bearer ${token}` }
        });
        if (!res.ok) throw new Error('Não foi possível desacionar a cadeira');
        notify('Cadeira desacionada', 'success');
        const cadRes = await fetch(`${API_URL}/api/v1/cadeiras/barbearia/${barbeariaId}`, {
          headers: { 'Authorization': `Bearer ${token}` }
        });
        if (cadRes.ok) {
          const data = await cadRes.json();
          setCadeiras(Array.isArray(data) ? data : []);
        }
      } catch (err) {
        notify(err.message || 'Erro ao desacionar cadeira', 'error');
      }
    };

    const acionarVagaRapida = async () => {
      if (!barbeariaId || cadeirasLoading) return;
      setCadeirasLoading(true);
      try {
        let lista = cadeiras;

        if (!lista.length) {
          // Garante pelo menos uma cadeira (número 1) para acionar
          const resCriar = await fetch(`${API_URL}/api/v1/cadeiras/`, {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
              'Authorization': `Bearer ${token}`
            },
            body: JSON.stringify({ numero: 1 })
          });

          if (!resCriar.ok && resCriar.status !== 400) {
            const body = await resCriar.json().catch(() => ({}));
            throw new Error(body?.detail || 'Erro ao preparar vaga');
          }

          const cadRes = await fetch(`${API_URL}/api/v1/cadeiras/barbearia/${barbeariaId}`, {
            headers: { 'Authorization': `Bearer ${token}` }
          });
          if (cadRes.ok) {
            const data = await cadRes.json();
            lista = Array.isArray(data) ? data : [];
            setCadeiras(lista);
          }
        }

        const alvo = lista.find(c => c.status === 'disponivel') || lista[0];
        if (!alvo) throw new Error('Nenhuma cadeira disponível');

        await acionarCadeira(alvo.id);
      } catch (err) {
        notify(err.message || 'Não foi possível acionar a vaga', 'error');
      } finally {
        setCadeirasLoading(false);
      }
    };

    const _marcarPresenca = async () => {
      if (!selectedFreelancerId || !selectedCadeiraId) {
        notify('Selecione freelancer e BRB', 'error');
        return;
      }
      setPresencaLoading(true);
      try {
        const res = await fetch(`${API_URL}/api/v1/cadeiras/presenca`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${token}`
          },
          body: JSON.stringify({
            freelancer_id: Number(selectedFreelancerId),
            cadeira_id: Number(selectedCadeiraId)
          })
        });
        const data = await res.json();
        if (!res.ok) throw new Error(data.detail || 'Erro ao marcar presença');
        notify('Freelancer presente! BRB ocupada.', 'success');
        setSelectedFreelancerId('');
        setSelectedCadeiraId('');
        const cadRes = await fetch(`${API_URL}/api/v1/cadeiras/barbearia/${barbeariaId}`, {
          headers: { 'Authorization': `Bearer ${token}` }
        });
        if (cadRes.ok) {
          const cadData = await cadRes.json();
          setCadeiras(Array.isArray(cadData) ? cadData : []);
        }
      } catch (err) {
        notify(err.message || 'Erro ao marcar presença', 'error');
      } finally {
        setPresencaLoading(false);
      }
    };

    const encerrarPresenca = async (cadeiraId) => {
      setPresencaLoading(true);
      try {
        const res = await fetch(`${API_URL}/api/v1/cadeiras/presenca/encerrar`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${token}`
          },
          body: JSON.stringify({ cadeira_id: Number(cadeiraId) })
        });
        const data = await res.json();
        if (!res.ok) throw new Error(data.detail || 'Erro ao encerrar presença');
        notify('Presença encerrada. BRB liberada.', 'success');
        const cadRes = await fetch(`${API_URL}/api/v1/cadeiras/barbearia/${barbeariaId}`, {
          headers: { 'Authorization': `Bearer ${token}` }
        });
        if (cadRes.ok) {
          const cadData = await cadRes.json();
          setCadeiras(Array.isArray(cadData) ? cadData : []);
        }
      } catch (err) {
        notify(err.message || 'Erro ao encerrar presença', 'error');
      } finally {
        setPresencaLoading(false);
      }
    };

    const criarNovaCadeira = async () => {
      console.log('🔍 criarNovaCadeira chamada', { barbeariaId, cadeiras });
      if (!barbeariaId) {
        console.error('❌ barbeariaId não encontrado!');
        notify('❌ Erro: Barbearia não encontrada', 'error');
        return;
      }
      setCadeirasLoading(true);
      try {
        // Encontrar próximo número disponível
        const proximoNumero = cadeiras.length ? Math.max(...cadeiras.map(c => c.numero)) + 1 : 1;
        
        const res = await fetch(`${API_URL}/api/v1/cadeiras/`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${token}`
          },
          body: JSON.stringify({ numero: proximoNumero })
        });
        
        console.log('📡 Resposta POST /cadeiras:', res.status, res.ok);
        
        if (!res.ok) {
          const data = await res.json();
          console.error('❌ Erro na resposta:', data);
          throw new Error(data.detail || 'Erro ao criar cadeira');
        }
        
        notify(`✅ Cadeira ${proximoNumero} criada com sucesso!`, 'success');
        
        // Recarregar lista
        const cadRes = await fetch(`${API_URL}/api/v1/cadeiras/barbearia/${barbeariaId}`, {
          headers: { 'Authorization': `Bearer ${token}` }
        });
        if (cadRes.ok) {
          const cadData = await cadRes.json();
          setCadeiras(Array.isArray(cadData) ? cadData : []);
        }
      } catch (err) {
        console.error('❌ Erro ao criar cadeira:', err);
        notify(err.message || 'Erro ao criar cadeira', 'error');
      } finally {
        setCadeirasLoading(false);
      }
    };

    const toggleBloquearCadeira = async (cadeiraId, statusAtual) => {
      console.log('🔍 toggleBloquearCadeira chamada', { cadeiraId, statusAtual });
      setCadeirasLoading(true);
      try {
        const novoStatus = statusAtual === 'bloqueada' ? 'disponivel' : 'bloqueada';
        
        const res = await fetch(`${API_URL}/api/v1/cadeiras/${cadeiraId}`, {
          method: 'PATCH',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${token}`
          },
          body: JSON.stringify({ status: novoStatus })
        });
        
        console.log('📡 Resposta PATCH /cadeiras:', res.status, res.ok, novoStatus);
        
        if (!res.ok) {
          const data = await res.json();
          console.error('❌ Erro na resposta:', data);
          throw new Error(data.detail || 'Erro ao atualizar status');
        }
        
        notify(
          novoStatus === 'bloqueada' 
            ? '🔒 Cadeira bloqueada' 
            : '✅ Cadeira desbloqueada',
          'success'
        );
        
        // Recarregar lista
        const cadRes = await fetch(`${API_URL}/api/v1/cadeiras/barbearia/${barbeariaId}`, {
          headers: { 'Authorization': `Bearer ${token}` }
        });
        if (cadRes.ok) {
          const cadData = await cadRes.json();
          setCadeiras(Array.isArray(cadData) ? cadData : []);
        }
      } catch (err) {
        console.error('❌ Erro ao bloquear/desbloquear:', err);
        notify(err.message || 'Erro ao atualizar status da cadeira', 'error');
      } finally {
        setCadeirasLoading(false);
      }
    };

    const _solicitarFreelancer = async () => {
      if (!solicitarFreelancerId) {
        notify('Selecione o barbeiro', 'error');
        return;
      }
      setSolicitarLoading(true);
      try {
        const payload = {
          freelancer_id: Number(solicitarFreelancerId)
        };
        if (solicitarCadeiraId) {
          payload.cadeira_id = Number(solicitarCadeiraId);
        }

        const res = await fetch(`${API_URL}/api/v1/freelancer/solicitar`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${token}`
          },
          body: JSON.stringify(payload)
        });
        const data = await res.json().catch(() => ({}));
        if (!res.ok) {
          throw new Error(data.detail || 'Erro ao solicitar barbeiro');
        }
        notify('Solicitacao enviada ao barbeiro!', 'success');
        setSolicitarFreelancerId('');
        setSolicitarCadeiraId('');
      } catch (err) {
        notify(err.message || 'Erro ao solicitar barbeiro', 'error');
      } finally {
        setSolicitarLoading(false);
      }
    };

    const addService = async (e) => {
      e.preventDefault();
      if (!newService.nome.trim() || Number(newService.valor) <= 0 || Number(newService.duracao_minutos) <= 0) {
        notify('Preencha nome, valor e duração válidos.', 'error');
        return;
      }
      try {
        // Buscar ID da barbearia
        const barbeariaRes = await fetch(`${API_URL}/api/v1/barbearia/minha`, {
          headers: { 'Authorization': `Bearer ${token}` }
        });
        if (!barbeariaRes.ok) throw new Error('Barbearia não encontrada');
        const barbearia = await barbeariaRes.json();
        
        const res = await fetch(`${API_URL}/api/v1/barbearias/${barbearia.id}/servicos`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
          body: JSON.stringify({ 
            nome: newService.nome, 
            valor: Number(newService.valor),
            categoria: 'outros',
            descricao: '',
            duracao_minutos: Number(newService.duracao_minutos) || 30
          })
        });
        if (!res.ok) throw new Error();
        const created = await res.json();
        setServices([...services, created]);
        setNewService({nome: '', valor: '', duracao_minutos: 30});
        notify("Serviço adicionado!", "success");
      } catch (_err) {
        notify('Não foi possível adicionar o serviço.', 'error');
      }
    };

    return (
      <div className="bg-black h-full p-4 pb-32 text-white overflow-y-auto">
            <div className="flex justify-between items-center mb-6 pt-4">
                <div className="flex items-center gap-2">
                    <h1 className="text-xl font-bold flex items-center gap-2"><Store className="text-orange-500"/> Gestão da Loja</h1>
                    {user?.documento_verificado && (
                        <CheckCircle size={20} className="text-blue-500 fill-blue-500" title="Verificado ✓" />
                    )}
                </div>
                <div className="flex items-center">
                  <VerificationBadge user={user} onClick={() => {
                    if (!user?.email_verificado) {
                      notify('Verifique seu email para liberar recursos.', 'info');
                    } else if (!user?.documento_verificado) {
                      notify('Envie seus documentos no perfil para concluir a verificacao.', 'info');
                    }
                  }} />
                  <button onClick={logout} className="text-zinc-500 ml-1"><LogOut size={20}/></button>
                </div>
            </div>
            {user && !user.email_verificado && !hideVerification && (
              <div className="bg-yellow-600/10 border border-yellow-600/30 p-4 rounded-xl mb-4">
                <div className="flex items-center gap-3 mb-3">
                  <AlertCircle size={20} className="text-yellow-500"/>
                  <div className="flex-1">
                    <span className="text-yellow-500 font-bold text-sm block">Verificação de email pendente</span>
                    <span className="text-yellow-400 text-xs">Confirme seu email para liberar todos os recursos</span>
                  </div>
                  <button 
                    onClick={async () => {
                      try {
                        const r = await fetch(`${API_URL}/api/v1/reenviar_email_verificacao`, {
                          method: 'POST',
                          headers: { 'Authorization': `Bearer ${token}` }
                        });
                        const data = await r.json();
                        if (r.ok) notify('Email reenviado! Verifique sua caixa de entrada 📧', 'success');
                        else notify(data.detail || 'Erro ao reenviar', 'error');
                      } catch (_e) {
                        notify('Erro ao reenviar email', 'error');
                      }
                    }}
                    className="px-3 py-1 bg-yellow-600 hover:bg-yellow-700 text-white text-xs rounded font-bold mr-2"
                  >📧 Reenviar</button>
                  <button onClick={() => setHideVerification(true)} className="text-yellow-400 text-xs font-bold">Fechar</button>
                </div>
                <div className="text-zinc-400 text-xs">Acesse seu email e confirme o link enviado.</div>
              </div>
            )}

            <div className="bg-zinc-900/60 p-5 rounded-2xl border border-purple-600/30 mb-6">
                <h3 className="font-bold mb-4 text-sm flex items-center gap-2 text-purple-400">⚙️ Cadastrar Serviço</h3>
                <form onSubmit={addService} className="space-y-3 mb-4">
                  <input 
                    className="bm-input w-full bg-black rounded-lg p-3 border border-zinc-800 text-sm outline-none focus:border-purple-500" 
                    placeholder="Nome do serviço (ex: Corte Degradê)" 
                    value={newService.nome} 
                    onChange={e => setNewService({...newService, nome: e.target.value})} 
                    required
                  />
                  <div className="grid grid-cols-2 gap-3">
                    <input 
                      className="bm-input bg-black rounded-lg p-3 border border-zinc-800 text-sm outline-none focus:border-purple-500" 
                      type="number" 
                      placeholder="Valor R$" 
                      value={newService.valor} 
                      onChange={e => setNewService({...newService, valor: e.target.value})} 
                      required
                    />
                    <input 
                      className="bm-input bg-black rounded-lg p-3 border border-zinc-800 text-sm outline-none focus:border-purple-500" 
                      type="number" 
                      placeholder="Duração (min)" 
                      value={newService.duracao_minutos} 
                      onChange={e => setNewService({...newService, duracao_minutos: e.target.value})} 
                      required
                    />
                  </div>
                  <button type="submit" className="w-full bg-orange-600 hover:bg-orange-700 text-white px-4 py-3 rounded-lg font-bold text-sm transition-all">+ Adicionar Serviço</button>
                </form>
                <div className="space-y-2">
                    {services.length > 0 ? (
                      services.map(s => (
                        <div key={s.id} className="flex justify-between items-center bg-black/60 p-3 rounded-lg border border-purple-600/20 hover:border-purple-600/40 transition-colors">
                          <span className="text-sm font-medium text-white">{s.nome}</span>
                          <div className="text-right flex gap-3">
                            <span className="text-green-400 font-bold text-sm">R$ {parseFloat(s.valor).toFixed(2)}</span>
                            <span className="text-purple-400 font-bold text-sm">{s.duracao_minutos || 30} min</span>
                          </div>
                        </div>
                      ))
                    ) : (
                      <div className="text-center text-zinc-500 text-xs py-4">Nenhum serviço cadastrado ainda</div>
                    )}
                </div>
            </div>

            {/* Notificações de Agendamentos - Preview */}
            {tabShopSafe === 'gestao' && agendamentos.length > 0 && (
              <div className="bg-blue-600/10 border border-blue-600/30 p-4 rounded-xl mb-4">
                <h3 className="font-bold text-sm text-blue-400 mb-3 flex items-center gap-2 justify-between">
                  <span><Calendar size={16}/> Próximos Agendamentos</span>
                  <button 
                    onClick={() => setTabShopSafe('agendamentos')}
                    className="text-xs bg-blue-600 px-2 py-1 rounded text-white"
                  >
                    Ver todos
                  </button>
                </h3>
                <div className="space-y-2">
                  {agendamentos.slice(0, 3).filter(a => !isConcluidoShop(a.status)).map(ag => (
                    <div key={ag.id} className="bg-black/40 p-3 rounded-lg border border-blue-800/30 text-xs">
                      <div className="flex justify-between items-start mb-1">
                        <span className="font-bold text-white">{ag.nome_cliente}</span>
                        <span className={`text-[10px] font-bold ${
                          ag.status === 'confirmado' ? 'text-green-400' : 'text-yellow-400'
                        }`}>{ag.status.toUpperCase()}</span>
                      </div>
                      <div className="text-zinc-400">
                        <p>Barbeiro: {ag.nome_barbeiro}</p>
                        {ag.data_hora_inicio && (
                          <p className="text-orange-400 mt-1">
                            {new Date(ag.data_hora_inicio).toLocaleString('pt-BR', { 
                              day: '2-digit', 
                              month: '2-digit', 
                              hour: '2-digit', 
                              minute: '2-digit' 
                            })}
                          </p>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {tabShopSafe === 'gestao' && (
              <>
                {/* Barbeiros Presentes no Local */}
                {barbeirosPresentes.length > 0 && (
                  <div className="bg-blue-600/10 border border-blue-600/30 p-4 rounded-2xl mb-6">
                    <h3 className="text-blue-400 font-bold text-sm mb-4 flex items-center gap-2">
                      👥 Barbeiros Presentes ({barbeirosPresentes.length})
                    </h3>
                    <div className="space-y-3">
                      {barbeirosPresentes.map(barbeiro => (
                        <div key={barbeiro.id} className="bg-zinc-900/80 p-3 rounded-xl border border-zinc-800">
                          <div className="flex items-center gap-3">
                            <div className="w-12 h-12 rounded-full bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center">
                              {barbeiro.foto_perfil ? (
                                <img src={barbeiro.foto_perfil} alt={barbeiro.nome} className="w-full h-full rounded-full object-cover" />
                              ) : (
                                <span className="text-white font-bold text-lg">{barbeiro.nome.charAt(0)}</span>
                              )}
                            </div>
                            <div className="flex-1">
                              <p className="font-bold text-white text-sm">{barbeiro.nome}</p>
                              {barbeiro.cadeira_numero && (
                                <p className="text-xs text-purple-400">📍 Cadeira {barbeiro.cadeira_numero}</p>
                              )}
                              {barbeiro.tempo_presente && (
                                <p className="text-xs text-zinc-400">⏱️ Há {barbeiro.tempo_presente}</p>
                              )}
                            </div>
                            <div className="text-right">
                              {barbeiro.atendendo_cliente ? (
                                <div className="bg-orange-600/20 border border-orange-600/50 px-2 py-1 rounded text-xs">
                                  <p className="text-orange-400 font-bold">🔵 Ocupado</p>
                                  <p className="text-zinc-400 text-[10px] mt-1">{barbeiro.atendendo_cliente}</p>
                                  {barbeiro.servico && (
                                    <p className="text-zinc-500 text-[10px]">{barbeiro.servico}</p>
                                  )}
                                </div>
                              ) : (
                                <div className="bg-green-600/20 border border-green-600/50 px-2 py-1 rounded text-xs">
                                  <p className="text-green-400 font-bold">🟢 Disponível</p>
                                </div>
                              )}
                            </div>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                <div className="bg-purple-600/10 border border-purple-600/30 p-5 rounded-2xl mb-6">
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-purple-400 font-bold text-sm flex items-center gap-2">
                  <Navigation size={16}/> Suas Cadeiras ({cadeiras.length})
                </h3>
                <button
                  onClick={criarNovaCadeira}
                  disabled={cadeirasLoading}
                  className="bg-purple-600 hover:bg-purple-700 disabled:opacity-50 text-white px-3 py-1.5 rounded-lg text-xs font-bold flex items-center gap-1 transition-all"
                  title="Adicionar nova cadeira"
                >
                  <span className="text-lg leading-none">+</span> Nova
                </button>
              </div>

              {cadeiras.length === 0 ? (
                <div className="bg-zinc-900/80 p-4 rounded-xl border border-zinc-800 text-sm text-zinc-300">
                  <p className="mb-3">Nenhuma cadeira cadastrada ainda.</p>
                  <button
                    onClick={criarNovaCadeira}
                    disabled={cadeirasLoading}
                    className="w-full bg-purple-600 hover:bg-purple-700 disabled:opacity-50 text-white px-4 py-2 rounded-lg font-bold text-xs transition-all"
                  >
                    {cadeirasLoading ? 'Criando...' : '➕ Criar Primeira Cadeira'}
                  </button>
                </div>
              ) : (
                <div className="space-y-2">
                  {cadeiras.map(cadeira => {
                    const statusConfig = {
                      disponivel: { bg: 'bg-black/40', border: 'border-green-600/30', label: '🟢 Disponível', labelColor: 'text-green-400', labelBg: 'bg-green-600/20' },
                      ocupada: { bg: 'bg-black/40', border: 'border-blue-600/30', label: '🔵 Ocupada', labelColor: 'text-blue-400', labelBg: 'bg-blue-600/20' },
                      bloqueada: { bg: 'bg-black/40', border: 'border-red-600/30', label: '🔒 Bloqueada', labelColor: 'text-red-400', labelBg: 'bg-red-600/20' }
                    };
                    const config = statusConfig[cadeira.status] || statusConfig.disponivel;
                    
                    return (
                      <div key={cadeira.id} className={`${config.bg} border ${config.border} p-3 rounded-lg transition-all hover:border-purple-600/50`}>
                        <div className="flex items-center justify-between">
                          <div className="flex-1">
                            <p className="font-bold text-sm text-white">Cadeira {cadeira.numero}</p>
                            <p className={`text-xs mt-1 font-bold ${config.labelColor}`}>
                              {config.label}
                              {cadeira.status === 'ocupada' && cadeira.freelancer_nome && (
                                <span className="text-zinc-400 font-normal"> • {cadeira.freelancer_nome}</span>
                              )}
                            </p>
                          </div>
                          <div className="flex gap-2">
                            {cadeira.status === 'disponivel' && (
                              <>
                                <button 
                                  onClick={() => acionarCadeira(cadeira.id)}
                                  disabled={cadeirasLoading}
                                  className="bg-orange-600 hover:bg-orange-700 disabled:opacity-50 text-white px-3 py-2 rounded-lg text-xs font-bold transition-all"
                                >
                                  Acionar
                                </button>
                                <button 
                                  onClick={() => toggleBloquearCadeira(cadeira.id, cadeira.status)}
                                  disabled={cadeirasLoading}
                                  className="bg-zinc-700 hover:bg-red-700 disabled:opacity-50 text-white px-2 py-2 rounded-lg text-sm transition-all"
                                  title="Bloquear cadeira"
                                >
                                  🔒
                                </button>
                              </>
                            )}
                            {cadeira.status === 'ocupada' && (
                              <button 
                                onClick={() => encerrarPresenca(cadeira.id)}
                                disabled={cadeirasLoading}
                                className="bg-orange-600 hover:bg-orange-700 disabled:opacity-50 text-white px-3 py-2 rounded-lg text-xs font-bold transition-all"
                              >
                                Finalizar
                              </button>
                            )}
                            {cadeira.status === 'bloqueada' && (
                              <button 
                                onClick={() => toggleBloquearCadeira(cadeira.id, cadeira.status)}
                                disabled={cadeirasLoading}
                                className="bg-purple-600 hover:bg-purple-700 disabled:opacity-50 text-white px-2 py-2 rounded-lg text-sm transition-all"
                                title="Desbloquear cadeira"
                              >
                                🔓
                              </button>
                            )}
                          </div>
                        </div>
                      </div>
                    );
                  })}
                  <button
                    onClick={acionarVagaRapida}
                    disabled={cadeirasLoading}
                    className="w-full bg-purple-600 hover:bg-purple-700 disabled:opacity-50 text-white px-4 py-3 rounded-lg font-bold text-sm mt-3 transition-all"
                  >
                    {cadeirasLoading ? 'Acionando...' : '⚡ Liberar Próxima Vaga Disponível'}
                  </button>
                </div>
              )}
              <div className="bg-zinc-900/50 p-3 rounded-lg mt-4 border border-zinc-800">
                <p className="text-zinc-400 text-xs mb-2">💡 <strong>Dicas:</strong></p>
                <ul className="text-zinc-500 text-[10px] space-y-1 ml-4">
                  <li>• Use <strong>"Acionar"</strong> para notificar barbeiros próximos</li>
                  <li>• <strong>Bloqueie</strong> cadeiras em manutenção ou reservadas</li>
                  <li>• O sistema libera automaticamente clientes quando faltam 15 min</li>
                </ul>
              </div>
            </div>
              </>
            )}

            <div className="grid grid-cols-1 gap-4 mb-6">
                <div className="bg-zinc-900 p-4 rounded-xl border border-zinc-800 text-center">
                    <h4 className="text-zinc-500 text-[10px] uppercase font-bold mb-2">Agendamentos</h4>
                <p className="text-2xl font-bold text-white">{agendamentosVisiveis.length}</p>
                </div>
            </div>

            {tabShopSafe === 'gestao' && avaliacoesBarbearia.length > 0 && (
              <div className="bg-zinc-900 p-5 rounded-2xl border border-zinc-800">
                <h3 className="font-bold mb-4 text-sm">Avaliações Recentes</h3>
                <div className="space-y-3">
                  {avaliacoesBarbearia.map((av) => (
                    <div key={av.id} className="bg-black/40 p-3 rounded-lg border border-zinc-800/40 flex items-center justify-between">
                      <div>
                        <p className="text-sm font-bold">{av.avaliador_nome || 'Usuário'}</p>
                        <p className="text-xs text-zinc-400">{av.comentario || 'Sem comentário'}</p>
                      </div>
                      <div className="text-yellow-400 font-bold text-sm">{'★'.repeat(av.nota)}</div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {tabShopSafe === 'agendamentos' && (
              <div className="pb-24">
                <h2 className="font-bold text-lg mb-4 flex items-center gap-2">
                  <Calendar size={20} className="text-red-500" />
                  Gerenciar Agendamentos
                </h2>

                {/* Notificações de Agendamentos */}
                {agendamentosVisiveis.length > 0 && (
                  <div className="bg-blue-600/10 border border-blue-600/30 p-4 rounded-xl mb-4">
                    <h3 className="font-bold text-sm text-blue-400 mb-3 flex items-center gap-2">
                      <Calendar size={16}/> Próximos Agendamentos ({agendamentosVisiveis.filter(a => !isConcluidoShop(a.status)).length})
                    </h3>
                    <div className="space-y-2">
                      {agendamentosVisiveis.filter(a => !isConcluidoShop(a.status)).map(ag => (
                        <div key={ag.id} className="bg-black/40 p-3 rounded-lg border border-blue-800/30 text-xs">
                          <div className="flex justify-between items-start mb-1">
                            <span className="font-bold text-white">{ag.nome_cliente}</span>
                            <span className={`text-[10px] font-bold ${
                              ag.status === 'confirmado' ? 'text-green-400' : 'text-yellow-400'
                            }`}>{ag.status.toUpperCase()}</span>
                          </div>
                          <div className="text-zinc-400">
                            <p>Barbeiro: {ag.nome_barbeiro}</p>
                            {ag.data_hora_inicio && (
                              <p className="text-orange-400 mt-1">
                                {new Date(ag.data_hora_inicio).toLocaleString('pt-BR', { 
                                  day: '2-digit', 
                                  month: '2-digit', 
                                  hour: '2-digit', 
                                  minute: '2-digit' 
                                })}
                              </p>
                            )}
                          </div>
                          {ag.status === 'confirmado' && (
                            <div className="mt-2 bg-green-600/10 border border-green-600/30 text-green-400 rounded-lg py-2 px-3 text-[10px] font-bold">
                              ✓ Agendamento confirmado
                            </div>
                          )}
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* Modal de Avaliação - renderizado em qualquer aba */}
                {selectedAgendamentoShop && (
                  <div className="fixed inset-0 bg-black/80 backdrop-blur-sm z-50 flex items-end sm:items-center justify-center p-4">
                    <div className="bg-zinc-900 rounded-2xl w-full max-w-lg p-6 border border-zinc-800 max-h-[90vh] overflow-y-auto animate-in slide-in-from-bottom">
                      <div className="flex justify-between items-center mb-6">
                        <h2 className="text-xl font-bold">Avaliar Agendamento</h2>
                        <button onClick={() => setSelectedAgendamentoShop(null)} className="text-zinc-400 hover:text-white text-2xl">×</button>
                      </div>

                      <div className="space-y-6">
                        {/* Avaliação do Cliente */}
                        <div className="bg-gradient-to-br from-orange-500/20 to-orange-600/20 p-5 rounded-xl border border-orange-500/40">
                          <p className="text-sm font-bold text-orange-400 mb-3">👤 Avaliar Cliente</p>
                          <div className="mb-4 bg-black/30 p-3 rounded-lg border border-orange-500/20">
                            <p className="text-xs text-zinc-400">Cliente:</p>
                            <p className="font-bold text-sm text-white">{selectedAgendamentoShop.nome_cliente || 'Cliente'}</p>
                          </div>
                          <div className="flex items-center gap-2 mb-4">
                            {[1,2,3,4,5].map(n => (
                              <button
                                key={n}
                                onClick={() => setAvaliarComoBarbearia({ ...avaliarComoBarbearia, chamadoId: selectedAgendamentoShop.id, alvo: 'cliente', nota: n })}
                                className={`text-3xl transition-all ${avaliarComoBarbearia.chamadoId===selectedAgendamentoShop.id && avaliarComoBarbearia.alvo==='cliente' && avaliarComoBarbearia.nota>=n ? 'text-orange-400 scale-125' : 'text-zinc-700 hover:text-orange-400'}`}
                              >★</button>
                            ))}
                          </div>
                          <input
                            className="bm-input bg-black/40 rounded-lg p-3 border border-orange-500/30 text-xs w-full placeholder-zinc-600 focus:border-orange-400 outline-none mb-3"
                            placeholder="Comentário (opcional)"
                            value={avaliarComoBarbearia.chamadoId===selectedAgendamentoShop.id && avaliarComoBarbearia.alvo==='cliente' ? (avaliarComoBarbearia.comentario || '') : ''}
                            onChange={e => setAvaliarComoBarbearia({ ...avaliarComoBarbearia, chamadoId: selectedAgendamentoShop.id, alvo: 'cliente', comentario: e.target.value })}
                          />
                          <button
                            onClick={() => enviarAvaliacaoBarbearia(selectedAgendamentoShop.id, selectedAgendamentoShop.cliente_id, 'cliente', false)}
                            className="w-full bg-gradient-to-r from-orange-500 to-orange-600 text-black px-3 py-2 rounded-lg text-xs font-bold hover:shadow-lg hover:shadow-orange-500/30"
                          >✅ Enviar Avaliação</button>
                        </div>

                        {/* Avaliação do Barbeiro */}
                        {selectedAgendamentoShop.barbeiro_id && (
                          <div className="bg-gradient-to-br from-orange-500/20 to-orange-600/20 p-5 rounded-xl border border-orange-500/40">
                            <p className="text-sm font-bold text-orange-400 mb-3">✂️ Avaliar Barbeiro</p>
                            <div className="mb-4 bg-black/30 p-3 rounded-lg border border-orange-500/20">
                              <p className="text-xs text-zinc-400">Barbeiro:</p>
                              <p className="font-bold text-sm text-white">{selectedAgendamentoShop.nome_barbeiro || 'Barbeiro'}</p>
                            </div>
                            <div className="flex items-center gap-2 mb-4">
                              {[1,2,3,4,5].map(n => (
                                <button
                                  key={n}
                                  onClick={() => setAvaliarComoBarbearia({ ...avaliarComoBarbearia, chamadoId: selectedAgendamentoShop.id, alvo: 'barbeiro', nota: n })}
                                  className={`text-3xl transition-all ${avaliarComoBarbearia.chamadoId===selectedAgendamentoShop.id && avaliarComoBarbearia.alvo==='barbeiro' && avaliarComoBarbearia.nota>=n ? 'text-orange-400 scale-125' : 'text-zinc-700 hover:text-orange-400'}`}
                                >★</button>
                              ))}
                            </div>
                            <input
                              className="bm-input bg-black/40 rounded-lg p-3 border border-orange-500/30 text-xs w-full placeholder-zinc-600 focus:border-orange-400 outline-none mb-3"
                              placeholder="Comentário (opcional)"
                              value={avaliarComoBarbearia.chamadoId===selectedAgendamentoShop.id && avaliarComoBarbearia.alvo==='barbeiro' ? (avaliarComoBarbearia.comentario || '') : ''}
                              onChange={e => setAvaliarComoBarbearia({ ...avaliarComoBarbearia, chamadoId: selectedAgendamentoShop.id, alvo: 'barbeiro', comentario: e.target.value })}
                            />
                            <button
                              onClick={() => enviarAvaliacaoBarbearia(selectedAgendamentoShop.id, selectedAgendamentoShop.barbeiro_id, 'barbeiro', false)}
                              className="w-full bg-gradient-to-r from-orange-500 to-orange-600 text-black px-3 py-2 rounded-lg text-xs font-bold hover:shadow-lg hover:shadow-orange-500/30"
                            >✅ Enviar Avaliação</button>
                          </div>
                        )}
                      </div>

                      <button
                        onClick={() => setSelectedAgendamentoShop(null)}
                        className="w-full mt-6 bg-zinc-800 text-white px-4 py-3 rounded-lg font-bold text-sm"
                      >Fechar</button>
                    </div>
                  </div>
                )}

                {agendamentos.length === 0 && (
                  <div className="text-center py-10 text-zinc-600">
                    <p>Nenhum agendamento no momento</p>
                  </div>
                )}
              </div>
            )}

            {tabShopSafe === 'assinatura' && (
              <AssinaturaPage 
                token={token} 
                notify={notify} 
              />
            )}

            {tabShopSafe === 'avaliar' && (
              <div className="p-4 pb-24">
                {agendamentos.filter(a => isConcluidoShop(a.status)).length > 0 ? (
                  <div className="space-y-4">
                    <h2 className="text-lg font-bold mb-4">⭐ Avaliar Agendamentos Concluídos</h2>
                    <div className="space-y-3">
                      {agendamentos.filter(a => isConcluidoShop(a.status)).map(ag => (
                        <div key={ag.id} onClick={() => setSelectedAgendamentoShop(ag)} className="p-4 rounded-lg border border-orange-500/30 bg-black/30 hover:border-orange-500/60 cursor-pointer">
                          <div className="flex justify-between items-start gap-3">
                            <div className="flex-1">
                              <p className="font-bold text-sm">{ag.nome_cliente || 'Cliente'}</p>
                              <p className="text-xs text-zinc-400">{ag.descricao || 'Serviço'}</p>
                              <p className="text-xs text-orange-400 font-bold mt-2">👆 Clique para avaliar</p>
                            </div>
                            <span className="text-[10px] bg-green-600 text-white px-2 py-1 rounded font-bold">✓ CONCLUÍDO</span>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                ) : (
                  <div className="text-center py-12 text-zinc-600">
                    <p>Nenhum agendamento concluído para avaliar</p>
                  </div>
                )}
              </div>
            )}

            {tabShopSafe === 'perfil' && (
              <div className="pb-24">
                <TelaPerfilUsuario userType="barbearia" token={token} onLogout={logout} onNotify={notify} />
              </div>
            )}

            <div className="bm-bottom-nav fixed bottom-0 left-1/2 -translate-x-1/2 w-full max-w-[400px] h-[calc(4.4rem+env(safe-area-inset-bottom))] pb-[env(safe-area-inset-bottom)] flex justify-around items-center z-[999] px-2 pointer-events-auto">
              <button data-active={tabShopSafe === 'gestao'} onClick={() => setTabShopSafe('gestao')} className={`bm-bottom-nav-btn flex flex-col items-center gap-1 p-1 flex-1 ${tabShopSafe === 'gestao' ? 'text-orange-500 bg-orange-500/5' : 'text-zinc-600'}`}>
                <Store size={16} />
                <span className="hidden sm:block">Gestão</span>
              </button>
              <button data-active={tabShopSafe === 'agendamentos'} onClick={() => setTabShopSafe('agendamentos')} className={`bm-bottom-nav-btn flex flex-col items-center gap-1 p-1 flex-1 ${tabShopSafe === 'agendamentos' ? 'text-orange-500 bg-orange-500/5' : 'text-zinc-600'}`}>
                <Calendar size={16} />
                <span className="hidden sm:block">Agend.</span>
              </button>
              <button data-active={tabShopSafe === 'assinatura'} onClick={() => setTabShopSafe('assinatura')} className={`bm-bottom-nav-btn flex flex-col items-center gap-1 p-1 flex-1 ${tabShopSafe === 'assinatura' ? 'text-orange-500 bg-orange-500/5' : 'text-zinc-600'}`}>
                <CreditCard size={16} />
                <span className="hidden sm:block">Assinar</span>
              </button>
              <button data-active={tabShopSafe === 'avaliar'} onClick={() => setTabShopSafe('avaliar')} className={`bm-bottom-nav-btn flex flex-col items-center gap-1 p-1 flex-1 ${tabShopSafe === 'avaliar' ? 'text-orange-500 bg-orange-500/5' : 'text-zinc-600'}`}>
                <Star size={16} />
                <span className="hidden sm:block">Avaliar</span>
              </button>
              <button data-active={tabShopSafe === 'perfil'} onClick={() => setTabShopSafe('perfil')} className={`bm-bottom-nav-btn flex flex-col items-center gap-1 p-1 flex-1 ${tabShopSafe === 'perfil' ? 'text-orange-500 bg-orange-500/5' : 'text-zinc-600'}`}>
                <User size={16} />
                <span className="hidden sm:block">Perfil</span>
              </button>
            </div>
        </div>
    );
  };

  // --- RENDERIZADOR PRINCIPAL ---
  return (
    <div className="min-h-screen bg-zinc-950 flex justify-center sm:items-center sm:py-8 font-sans">
      <div className="app-container w-full sm:max-w-[400px] bg-black min-h-screen sm:min-h-screen sm:h-auto sm:max-h-none sm:rounded-[2.5rem] sm:border-[8px] sm:border-zinc-800 sm:shadow-2xl relative overflow-y-visible overflow-x-hidden sm:overflow-y-auto sm:overflow-x-hidden flex flex-col pt-12 pb-[max(env(safe-area-inset-bottom),1rem)]">
        {/* Dynamic Notch */}
        <div className="hidden sm:block absolute top-0 left-1/2 -translate-x-1/2 w-1/3 h-7 bg-zinc-800 rounded-b-xl z-50 pointer-events-none"></div>
        
        <Toast />
        <UpdateBanner />
        
        {/* ⏳ MOSTRAR TELA DE APROVAÇÃO PENDENTE SE NÃO APROVADO */}
        {!userApproved && <PendingApprovalScreen />}
        {gpsBloqueado && <GpsObrigatorioOverlay />}
        
        {view === 'login' && (
          <TelaLogin
            API_URL={API_URL}
            BRAND_LOGO={BRAND_LOGO}
            notify={notify}
            saveLogin={saveLogin}
            setShowTerms={setShowTerms}
            setShowPrivacy={setShowPrivacy}
          />
        )}
        {view === 'dashboard' && userType === 'cliente' && userApproved && (
          <PainelLayout activeTab={undefined} setActiveTab={undefined}>
            <ClientDashboardView token={token} logout={logout} API_URL={API_URL} notify={notify} onChamadoAceito={abrirTelaRastreamento} />
          </PainelLayout>
        )}
        {view === 'dashboard' && userType === 'barbeiro' && userApproved && (
          <PainelLayout activeTab={undefined} setActiveTab={undefined}>
            <BarberDashboardView token={token} logout={logout} API_URL={API_URL} notify={notify} onChamadoAceito={abrirTelaRastreamento} />
          </PainelLayout>
        )}
        {view === 'dashboard' && userType === 'barbearia' && userApproved && (
          <PainelLayout activeTab={undefined} setActiveTab={undefined}>
            <ShopDashboardView token={token} logout={logout} API_URL={API_URL} notify={notify} tabShop={shopTab} setTabShop={setShopTab} />
          </PainelLayout>
        )}
        {view === 'dashboard' && userType === 'admin' && userApproved && (
          <PainelLayout activeTab={undefined} setActiveTab={undefined}>
            <AdminDashboard token={token} logout={logout} API_URL={API_URL} notify={notify} />
          </PainelLayout>
        )}
        {view === 'admin' && userType === 'admin' && userApproved && (
          <PainelLayout activeTab={undefined} setActiveTab={undefined}>
            <AdminValidationScreen token={token} logout={logout} API_URL={API_URL} notify={notify} />
          </PainelLayout>
        )}
        {view === 'rastreamento' && chamadoId && (
          <PainelLayout activeTab={undefined} setActiveTab={undefined}>
            <TelaDoChamado chamadoId={chamadoId} userType={userType} />
          </PainelLayout>
        )}

        {showTerms && (
          <div className="fixed inset-0 bg-black/70 backdrop-blur-sm z-[80] flex items-center justify-center p-4">
            <div className="bg-zinc-900 rounded-2xl max-h-[90vh] overflow-y-auto border border-zinc-800 w-full max-w-3xl relative">
              <button className="absolute top-3 right-3 text-zinc-500 hover:text-white" onClick={() => setShowTerms(false)}><X size={18} /></button>
              <TermosDeUso onVoltar={() => setShowTerms(false)} />
            </div>
          </div>
        )}

        {showPrivacy && (
          <div className="fixed inset-0 bg-black/70 backdrop-blur-sm z-[80] flex items-center justify-center p-4">
            <div className="bg-zinc-900 rounded-2xl max-h-[90vh] overflow-y-auto border border-zinc-800 w-full max-w-3xl relative">
              <button className="absolute top-3 right-3 text-zinc-500 hover:text-white" onClick={() => setShowPrivacy(false)}><X size={18} /></button>
              <PoliticaPrivacidade onVoltar={() => setShowPrivacy(false)} />
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

