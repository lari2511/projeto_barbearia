import React, { useState, useEffect } from 'react';
import { 
  User, Scissors, Store, MapPin, 
  LogOut, CheckCircle, AlertCircle, ArrowRight, 
  History, Search, X, Star, Navigation, Bell, CreditCard, Lock, Calendar
} from 'lucide-react';
import { useLiveJobs, useRealTimeUpdates } from './hooks/useRealTimeUpdates';

const API_URL = import.meta.env.VITE_API_URL || "https://unpuritan-gastrocnemial-charlyn.ngrok-free.dev";
const WS_URL = import.meta.env.VITE_WS_URL || "wss://unpuritan-gastrocnemial-charlyn.ngrok-free.dev/ws/notificacoes";
const BRAND_LOGO = "/brand-logo.png"; // coloque a logo em public/brand-logo.png

// Utilitário para imagens
const getShopImage = (id) => `https://images.unsplash.com/photo-${id % 2 === 0 ? '1521590832874-552721032d00' : '1503951914290-d20607416905'}?auto=format&fit=crop&w=800&q=80`;

export default function App() {
  const [userType, setUserType] = useState(localStorage.getItem('userType'));
  const [token, setToken] = useState(localStorage.getItem('token'));
  const [view, setView] = useState(token ? 'dashboard' : 'login');
  const [toast, setToast] = useState(null);

  // WebSocket Global para notificações
  useEffect(() => {
    if (token) {
      const ws = new WebSocket(WS_URL);
      ws.onopen = () => setNotifications(prev => [...prev, { id: Date.now(), message: "Sistema de notificações conectado", type: "info" }]);
      ws.onmessage = (event) => {
        const msg = JSON.parse(event.data);
        notify(msg.texto || "Nova atualização!", 'info');
      };
      return () => ws.close();
    }
  }, [token]);

  const notify = (message, type = 'success') => {
    setToast({ message, type });
    setTimeout(() => setToast(null), 4000);
  };

  const saveLogin = (type, access_token, userId) => {
    localStorage.setItem('userType', type);
    localStorage.setItem('token', access_token);
    localStorage.setItem('userId', userId);
    setUserType(type);
    setToken(access_token);
    setView('dashboard');
  };

  const logout = () => {
    localStorage.clear();
    setUserType(null);
    setToken(null);
    setView('login');
  };

  // --- COMPONENTES UI COMPARTILHADOS ---
  const Toast = () => {
    if (!toast) return null;
    const colors = { success: 'bg-green-600', error: 'bg-red-600', info: 'bg-blue-600' };
    return (
      <div className={`absolute top-6 left-1/2 transform -translate-x-1/2 z-[60] flex items-center gap-3 px-6 py-4 rounded-2xl shadow-2xl animate-in slide-in-from-top-5 border border-white/10 w-[90%] max-w-[350px] ${colors[toast.type] || 'bg-zinc-800'} text-white`}>
        {toast.type === 'success' ? <CheckCircle size={24} /> : toast.type === 'error' ? <AlertCircle size={24} /> : <Bell size={24} />}
        <div className="flex-1"><p className="text-xs opacity-90 font-bold">{toast.message}</p></div>
        <button onClick={() => setToast(null)}><X size={18}/></button>
      </div>
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

  // ----------------------------------------------------------------------
  // ARQUIVO: src/components/LoginScreen.jsx
  // ----------------------------------------------------------------------
  const LoginScreen = () => {
    const [isLogin, setIsLogin] = useState(true);
    const [activeTab, setActiveTab] = useState('cliente');
    const [loading, setLoading] = useState(false);
    const [formData, setFormData] = useState({ email: '', senha: '', nome: '', endereco: '', telefone: '', cpf: '', cnpj: '' });

    const validateForm = () => {
      if (!formData.email.includes('@')) throw new Error('Email inválido');
      if ((formData.senha || '').length < 6) throw new Error('Senha precisa ter 6 caracteres ou mais');
      if (!isLogin && (formData.nome || '').trim().length < 3) throw new Error('Informe o nome completo');
      if (!isLogin && activeTab !== 'cliente' && (formData.endereco || '').trim().length < 5) throw new Error('Endereço obrigatório para barbearia');
      if (!isLogin && formData.telefone && formData.telefone.replace(/\D/g, '').length < 10) throw new Error('Telefone com DDD obrigatório');
    };

    const handleSubmit = async (e) => {
      e.preventDefault();
      setLoading(true);

      try {
        validateForm();
        const endpoint = isLogin ? `login/${activeTab}/` : `${activeTab === 'cliente' ? 'clientes' : activeTab === 'barbeiro' ? 'barbeiros' : 'barbearias'}/`;
        const payload = isLogin ? 
          { email: formData.email, senha: formData.senha } : 
          { 
            nome: formData.nome, 
            email: formData.email, 
            senha: formData.senha, 
            endereco: formData.endereco, 
            telefone: formData.telefone,
            cpf: formData.cpf || undefined,
            cnpj: formData.cnpj || undefined
          };

        const res = await fetch(`${API_URL}/api/v1/${endpoint}`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload)
        });
        
        const data = await res.json();
        
        if (!res.ok) throw new Error(data.detail || data.message || "Erro na requisição");

        if (isLogin) {
          saveLogin(activeTab, data.access_token, data.user_id);
          notify(`Bem-vindo!`, 'success');
        } else {
          notify("Conta criada! Faça login.", 'success');
          setIsLogin(true);
        }
      } catch (err) {
        notify(err.message === "Failed to fetch" ? `Erro de conexão com API - Verifique se o celular está na mesma rede Wi-Fi (${API_URL})` : err.message, 'error');
      } finally {
        setLoading(false);
      }
    };

    return (
      <div className="flex flex-col items-center justify-center h-full p-6 text-white bg-black animate-in fade-in">
        <div className="text-center mb-8">
            <div className="flex justify-center mb-4">
              <img src={BRAND_LOGO} alt="BarberMove" className="h-16 w-16 object-contain" onError={(e) => e.currentTarget.style.display='none'} />
            </div>
            <h1 className="text-3xl font-extrabold mb-2 tracking-tighter">Barber<span className="text-orange-500">Move</span></h1>
            <p className="text-zinc-500 text-xs uppercase tracking-widest font-bold">Agenda e gestão profissional</p>
        </div>
        
        <div className="bg-zinc-900/50 p-1 rounded-xl mb-6 flex border border-zinc-800 w-full relative">
            {['cliente', 'barbeiro', 'barbearia'].map(t => (
                <button key={t} onClick={() => setActiveTab(t)} className={`flex-1 py-2.5 capitalize text-[11px] font-bold rounded-lg transition-all z-10 ${activeTab === t ? 'bg-zinc-800 text-white shadow-lg' : 'text-zinc-500 hover:text-zinc-300'}`}>{t}</button>
            ))}
        </div>

        <form onSubmit={handleSubmit} className="space-y-3 w-full">
            {!isLogin && <input name="nome" placeholder="Nome Completo" className="input-modern" onChange={e => setFormData({...formData, nome: e.target.value})} required />}
            {!isLogin && <input name="telefone" placeholder="Telefone com DDD" className="input-modern" onChange={e => setFormData({...formData, telefone: e.target.value})} />}
            {!isLogin && (activeTab === 'cliente' || activeTab === 'barbeiro') && (
              <input 
                name="cpf" 
                placeholder="CPF (opcional)" 
                className="input-modern" 
                maxLength="14"
                onChange={e => {
                  let value = e.target.value.replace(/\D/g, '');
                  if (value.length <= 11) {
                    value = value.replace(/(\d{3})(\d{3})(\d{3})(\d{2})/, '$1.$2.$3-$4');
                  }
                  setFormData({...formData, cpf: value});
                  e.target.value = value;
                }} 
              />
            )}
            {!isLogin && activeTab === 'barbearia' && (
              <>
                <input 
                  name="cpf" 
                  placeholder="CPF do Dono (opcional)" 
                  className="input-modern" 
                  maxLength="14"
                  onChange={e => {
                    let value = e.target.value.replace(/\D/g, '');
                    if (value.length <= 11) {
                      value = value.replace(/(\d{3})(\d{3})(\d{3})(\d{2})/, '$1.$2.$3-$4');
                    }
                    setFormData({...formData, cpf: value});
                    e.target.value = value;
                  }} 
                />
                <input 
                  name="cnpj" 
                  placeholder="CNPJ da Empresa (opcional)" 
                  className="input-modern" 
                  maxLength="18"
                  onChange={e => {
                    let value = e.target.value.replace(/\D/g, '');
                    if (value.length <= 14) {
                      value = value.replace(/(\d{2})(\d{3})(\d{3})(\d{4})(\d{2})/, '$1.$2.$3/$4-$5');
                    }
                    setFormData({...formData, cnpj: value});
                    e.target.value = value;
                  }} 
                />
              </>
            )}
            {!isLogin && activeTab !== 'cliente' && <input name="endereco" placeholder="Endereço da Loja/Base" className="input-modern" onChange={e => setFormData({...formData, endereco: e.target.value})} required />}
            <input name="email" type="email" placeholder="Email" className="input-modern" onChange={e => setFormData({...formData, email: e.target.value})} required />
            <input name="senha" type="password" placeholder="Senha" className="input-modern" onChange={e => setFormData({...formData, senha: e.target.value})} required />
            
            <button disabled={loading} className="w-full bg-white text-black py-4 rounded-xl font-bold mt-4 active:scale-95 transition-all hover:bg-zinc-200 disabled:opacity-50">
                {loading ? 'Processando...' : (isLogin ? 'Entrar na Conta' : 'Criar Nova Conta')}
            </button>
        </form>
        
        <button onClick={() => setIsLogin(!isLogin)} className="mt-8 text-zinc-500 text-xs font-medium hover:text-white transition-colors">
            {isLogin ? 'Não tem uma conta? Cadastre-se' : 'Já possui conta? Faça login'}
        </button>
        <p className="mt-4 text-[10px] text-zinc-700">Sua conta será validada com email e senha fortes.</p>
        
        <style>{`.input-modern { width: 100%; padding: 1rem; border-radius: 0.75rem; background-color: #18181b; color: white; border: 1px solid #27272a; outline: none; transition: all 0.2s; font-size: 0.9rem; } .input-modern:focus { border-color: #f97316; background-color: #000; }`}</style>
      </div>
    );
  };

  // ----------------------------------------------------------------------
  // ARQUIVO: src/components/ClientDashboard.jsx
  // ----------------------------------------------------------------------
  const ClientDashboard = () => {
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

    const formatDistanceEta = (shop) => {
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

    useEffect(() => {
        // Buscar barbeiros próximos se tiver geolocalização
        if (userCoords) {
          fetch(`${API_URL}/api/v1/barbeiros/proximos?latitude=${userCoords.lat}&longitude=${userCoords.lon}&raio_km=5`)
            .then(async r => {
              if (!r.ok) throw new Error('Erro ao listar barbeiros');
              return r.json();
            })
            .then(setBarbeiros)
            .catch(() => {
              // Fallback: buscar todos se geolocalização falhar
              fetch(`${API_URL}/api/v1/barbeiros/todos`)
                .then(r => r.json())
                .then(setBarbeiros)
                .catch(() => setBarbeiros([]));
            });
        } else {
          // Sem geolocalização: buscar todos
          fetch(`${API_URL}/api/v1/barbeiros/todos`)
            .then(r => r.json())
            .then(setBarbeiros)
            .catch(() => setBarbeiros([]));
        }

        if (token) {
          fetch(`${API_URL}/api/v1/cliente/meus_pedidos`, { headers: {'Authorization': `Bearer ${token}`} })
            .then(async r => {
              if (!r.ok) throw new Error();
              return r.json();
            }).then(setMyOrders).catch(() => setMyOrders([]));
        }
    }, [token, userCoords]);

    useEffect(() => {
      if (!navigator.geolocation) return;
      navigator.geolocation.getCurrentPosition(
        (pos) => setUserCoords({ lat: pos.coords.latitude, lon: pos.coords.longitude }),
        () => {},
        { enableHighAccuracy: false, timeout: 8000 }
      );
    }, [token]);

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
      
      try {
        const dataHora = new Date(`${selectedDate}T${selectedTime}:00`);
        
        const res = await fetch(`${API_URL}/api/v1/chamados`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
          body: JSON.stringify({ 
            servico_id: selectedService.id, 
            barbearia_id: selectedShop.id,
            barbeiro_id: selectedBarbeiro.id,
            data_hora_inicio: dataHora.toISOString()
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
                        className="px-3 py-1 rounded-full bg-white/90 text-black font-bold text-[10px] active:scale-95"
                      >Abrir no Maps</button>
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
                            <button onClick={() => handleBooking(s)} className="bg-white text-black px-4 py-2 rounded-lg font-bold text-xs flex items-center gap-2 active:scale-95">Agendar</button>
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
                            className="w-full bg-black border border-zinc-800 rounded-lg p-3 text-white outline-none focus:border-orange-500"
                          />
                        </div>
                        
                        <div>
                          <label className="block text-xs font-bold text-zinc-400 mb-2">Horário</label>
                          <input
                            type="time"
                            value={selectedTime}
                            onChange={(e) => setSelectedTime(e.target.value)}
                            className="w-full bg-black border border-zinc-800 rounded-lg p-3 text-white outline-none focus:border-orange-500"
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
          <>
            <div className="p-5 pt-8 sticky top-0 bg-black/80 backdrop-blur-md z-20 border-b border-zinc-800">
                <div className="flex justify-between items-center mb-4">
                    <h1 className="text-xl font-bold">Olá, Cliente</h1>
                    <button onClick={logout} className="p-2 bg-zinc-900 rounded-full text-zinc-400 hover:text-white"><LogOut size={16}/></button>
                </div>
                {tab === 'barbeiros' && (
                    <div className="relative">
                        <Search className="absolute left-3 top-3 text-zinc-500" size={18} />
                        <input placeholder="Buscar barbeiro..." className="w-full bg-zinc-900 pl-10 pr-4 py-3 rounded-xl border border-zinc-800 outline-none focus:border-orange-500 text-sm" />
                    </div>
                )}
            </div>

            <div className="flex-1 overflow-y-auto p-4 space-y-4 pb-24">
                {tab === 'barbeiros' ? barbeiros.map(barbeiro => (
                    <div key={barbeiro.id} onClick={() => handleSelectBarbeiro(barbeiro)} className="bg-zinc-900 rounded-2xl p-4 border border-zinc-800 active:scale-95 transition-transform cursor-pointer group flex items-center gap-4">
                        <div className="h-16 w-16 rounded-full bg-gradient-to-br from-orange-500 to-orange-700 flex items-center justify-center text-white font-bold text-2xl">
                          {barbeiro.nome.charAt(0).toUpperCase()}
                        </div>
                        <div className="flex-1">
                          <h3 className="font-bold text-lg">{barbeiro.nome}</h3>
                          <p className="text-xs text-zinc-500">{barbeiro.telefone || 'Sem telefone'}</p>
                          <div className="flex items-center gap-2 mt-1">
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
                )) : (
                    <div className="space-y-3">
                        <h2 className="font-bold text-sm text-zinc-400 uppercase tracking-widest mb-4">Meus Agendamentos</h2>
                        {myOrders.length === 0 && <p className="text-zinc-600 text-center py-10">Nenhum agendamento.</p>}
                        {myOrders.map((p) => (
                          <div key={p.id} className="bg-zinc-900 p-4 rounded-xl border border-zinc-800 flex gap-4 items-center">
                            <div className="h-10 w-10 rounded-full bg-orange-600/20 flex items-center justify-center text-orange-500"><Calendar size={18}/></div>
                            <div className="flex-1">
                              <h3 className="font-bold text-sm">{p.descricao || "Serviço"}</h3>
                              <p className="text-xs text-zinc-500">{p.nome_barbearia || "Barbearia"}</p>
                            </div>
                            <div className="text-right">
                              <span className="block text-green-400 font-bold text-sm">R$ {p.valor || 0}</span>
                              <span className="text-[10px] text-zinc-500">{p.status || "AGENDADO"}</span>
                            </div>
                          </div>
                        ))}
                    </div>
                )}
            </div>

            <div className="absolute bottom-0 left-0 w-full bg-zinc-950/90 backdrop-blur-lg border-t border-zinc-800 p-2 pb-6 flex justify-around items-center z-50">
              <button onClick={() => setTab('barbeiros')} className={`flex flex-col items-center gap-1 p-2 w-20 ${tab === 'barbeiros' ? 'text-orange-500' : 'text-zinc-600'}`}><Search size={20} /><span className="text-[10px] font-bold">Barbeiros</span></button>
              <button onClick={() => setTab('pedidos')} className={`flex flex-col items-center gap-1 p-2 w-20 ${tab === 'pedidos' ? 'text-orange-500' : 'text-zinc-600'}`}><History size={20} /><span className="text-[10px] font-bold">Agenda</span></button>
            </div>
          </>
        )}
      </div>
    );
  };

  // ----------------------------------------------------------------------
  // ARQUIVO: src/components/BarberDashboard.jsx
  // ----------------------------------------------------------------------
  const BarberDashboard = () => {
    const [user, setUser] = useState(null);
    
    // Usar hook de sincronização em tempo real para jobs
    const { jobs, loading, isConnected } = useLiveJobs(token, API_URL);

    useEffect(() => {
      // Buscar status de verificação
      fetch(`${API_URL}/api/v1/documentos/status`, {
        headers: {'Authorization': `Bearer ${token}`}
      })
      .then(r => r.json())
      .then(data => setUser(data))
      .catch(() => {});
    }, [token]);

    const acceptJob = async (id) => {
      try {
        const res = await fetch(`${API_URL}/api/v1/chamados/${id}/aceitar`, {
          method: 'PUT',
          headers: { 'Authorization': `Bearer ${token}` }
        });
        if (!res.ok) throw new Error();
            notify("Trabalho aceito!", "success");
            // Hook cuida de remover da lista automaticamente
      } catch {
        notify("Não foi possível aceitar o chamado.", "error");
      }
    };

    return (
        <div className="bg-black h-full p-4 text-white">
            <div className="flex justify-between items-center mb-6 pt-4">
                <div className="flex items-center gap-2">
                    <h1 className="text-xl font-bold flex items-center gap-2"><Scissors className="text-orange-500"/> Área do Barbeiro</h1>
                    {user?.documento_verificado && (
                        <CheckCircle size={20} className="text-blue-500 fill-blue-500" title="Verificado ✓" />
                    )}
                </div>
                <button onClick={logout} className="text-zinc-500"><LogOut size={20}/></button>
            </div>
            {user && !user.documento_verificado && (
                <div className="bg-yellow-600/10 border border-yellow-600/30 p-4 rounded-xl mb-4 flex items-center gap-3">
                    <AlertCircle size={20} className="text-yellow-500"/>
                    <div className="flex-1">
                        <span className="text-yellow-500 font-bold text-sm block">Verificação Pendente</span>
                        <span className="text-yellow-400 text-xs">Complete sua verificação para receber chamados</span>
                    </div>
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
            <h3 className="text-zinc-500 text-xs font-bold uppercase mb-4">Novos Chamados {loading && '(atualizando...)'}</h3>
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
                        <button onClick={() => acceptJob(job.id)} className="w-full bg-white text-black py-3 rounded-xl font-bold text-sm hover:bg-zinc-200">ACEITAR AGENDAMENTO</button>
                    </div>
                ))}
                {jobs.length === 0 && <p className="text-zinc-600 text-center text-sm py-10">Procurando agendamentos próximos...</p>}
            </div>
        </div>
    );
  };

  // ----------------------------------------------------------------------
  // ARQUIVO: src/components/ShopDashboard.jsx
  // ----------------------------------------------------------------------
  const ShopDashboard = () => {
    const [services, setServices] = useState([]);
    const [agendamentos, setAgendamentos] = useState([]);
    const [newService, setNewService] = useState({nome: '', valor: ''});
    const [barbeariaId, setBarbeariaId] = useState(null);
    const [user, setUser] = useState(null);

    useEffect(() => {
      // Buscar status de verificação
      fetch(`${API_URL}/api/v1/documentos/status`, {
        headers: {'Authorization': `Bearer ${token}`}
      })
      .then(r => r.json())
      .then(data => setUser(data))
      .catch(() => {});
    }, [token]);

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
        } catch (err) {
          notify('Erro ao carregar dados', 'error');
        }
      };
      load();
    }, [token]);

    const addService = async (e) => {
      e.preventDefault();
      if (!newService.nome.trim() || Number(newService.valor) <= 0) {
        notify('Preencha nome e valor válidos.', 'error');
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
            duracao_minutos: 30
          })
        });
        if (!res.ok) throw new Error();
        const created = await res.json();
        setServices([...services, created]);
        setNewService({nome: '', valor: ''});
        notify("Serviço adicionado!", "success");
      } catch (err) {
        notify('Não foi possível adicionar o serviço.', 'error');
        console.error(err);
      }
    };

    return (
        <div className="bg-black h-full p-4 text-white">
            <div className="flex justify-between items-center mb-6 pt-4">
                <div className="flex items-center gap-2">
                    <h1 className="text-xl font-bold flex items-center gap-2"><Store className="text-orange-500"/> Gestão da Loja</h1>
                    {user?.documento_verificado && (
                        <CheckCircle size={20} className="text-blue-500 fill-blue-500" title="Verificado ✓" />
                    )}
                </div>
                <button onClick={logout} className="text-zinc-500"><LogOut size={20}/></button>
            </div>
            {user && !user.documento_verificado && (
                <div className="bg-yellow-600/10 border border-yellow-600/30 p-4 rounded-xl mb-4 flex items-center gap-3">
                    <AlertCircle size={20} className="text-yellow-500"/>
                    <div className="flex-1">
                        <span className="text-yellow-500 font-bold text-sm block">Verificação Pendente</span>
                        <span className="text-yellow-400 text-xs">Complete sua verificação para ativar a loja</span>
                    </div>
                </div>
            )}

            <div className="bg-zinc-900 p-5 rounded-2xl border border-zinc-800 mb-6">
                <h3 className="font-bold mb-4 text-sm">Adicionar Serviço</h3>
                <form onSubmit={addService} className="flex gap-2 mb-4">
                    <input className="flex-1 bg-black rounded-lg p-3 border border-zinc-800 text-sm outline-none focus:border-orange-500" placeholder="Nome (ex: Barba)" value={newService.nome} onChange={e => setNewService({...newService, nome: e.target.value})} required/>
                    <input className="w-20 bg-black rounded-lg p-3 border border-zinc-800 text-sm outline-none focus:border-orange-500 text-center" type="number" placeholder="R$" value={newService.valor} onChange={e => setNewService({...newService, valor: e.target.value})} required/>
                    <button className="bg-white text-black w-10 rounded-lg font-bold text-xl flex items-center justify-center hover:bg-zinc-200">+</button>
                </form>
                <div className="space-y-2">
                    {services.map(s => (
                        <div key={s.id} className="flex justify-between items-center bg-black/40 p-3 rounded-lg border border-zinc-800/50">
                            <span className="text-sm">{s.nome}</span>
                            <span className="font-bold text-green-400">R$ {s.valor}</span>
                        </div>
                    ))}
                </div>
            </div>

            {/* Notificações de Agendamentos */}
            {agendamentos.length > 0 && (
              <div className="bg-blue-600/10 border border-blue-600/30 p-4 rounded-xl mb-4">
                <h3 className="font-bold text-sm text-blue-400 mb-3 flex items-center gap-2">
                  <Calendar size={16}/> Próximos Agendamentos
                </h3>
                <div className="space-y-2">
                  {agendamentos.slice(0, 5).map(ag => (
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
                        <div className="mt-2 flex gap-2">
                          <button 
                            onClick={async () => {
                              try {
                                const res = await fetch(`${API_URL}/api/v1/chamados/${ag.id}/barbearia/aceitar`, {
                                  method: 'PUT',
                                  headers: { 'Authorization': `Bearer ${token}` }
                                });
                                if (res.ok) {
                                  notify('Agendamento confirmado!', 'success');
                                  // Recarregar agendamentos
                                  const agRes = await fetch(`${API_URL}/api/v1/barbearia/${data.id}/agendamentos`, { 
                                    headers: { 'Authorization': `Bearer ${token}` } 
                                  });
                                  if (agRes.ok) {
                                    const agData = await agRes.json();
                                    setAgendamentos(Array.isArray(agData) ? agData : []);
                                  }
                                } else {
                                  notify('Erro ao confirmar', 'error');
                                }
                              } catch {
                                notify('Erro ao confirmar', 'error');
                              }
                            }}
                            className="flex-1 bg-green-600 text-white py-2 rounded-lg font-bold text-[10px] hover:bg-green-500"
                          >
                            ✓ CONFIRMAR CADEIRA
                          </button>
                          <button 
                            onClick={async () => {
                              try {
                                const res = await fetch(`${API_URL}/api/v1/chamados/${ag.id}/barbearia/recusar`, {
                                  method: 'PUT',
                                  headers: { 'Authorization': `Bearer ${token}` }
                                });
                                if (res.ok) {
                                  notify('Agendamento recusado', 'success');
                                  // Recarregar agendamentos
                                  const agRes = await fetch(`${API_URL}/api/v1/barbearia/${data.id}/agendamentos`, { 
                                    headers: { 'Authorization': `Bearer ${token}` } 
                                  });
                                  if (agRes.ok) {
                                    const agData = await agRes.json();
                                    setAgendamentos(Array.isArray(agData) ? agData : []);
                                  }
                                } else {
                                  notify('Erro ao recusar', 'error');
                                }
                              } catch {
                                notify('Erro ao recusar', 'error');
                              }
                            }}
                            className="flex-1 bg-red-600 text-white py-2 rounded-lg font-bold text-[10px] hover:bg-red-500"
                          >
                            ✗ RECUSAR
                          </button>
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            )}

            <div className="grid grid-cols-2 gap-4">
                <div className="bg-zinc-900 p-4 rounded-xl border border-zinc-800 text-center">
                    <h4 className="text-zinc-500 text-[10px] uppercase font-bold mb-2">Faturamento Hoje</h4>
                    <p className="text-2xl font-bold text-green-500">R$ 450</p>
                </div>
                <div className="bg-zinc-900 p-4 rounded-xl border border-zinc-800 text-center">
                    <h4 className="text-zinc-500 text-[10px] uppercase font-bold mb-2">Agendamentos</h4>
                    <p className="text-2xl font-bold text-white">{agendamentos.length}</p>
                </div>
            </div>
        </div>
    );
  };

  // --- RENDERIZADOR PRINCIPAL ---
  return (
    <div className="min-h-screen bg-zinc-950 flex justify-center sm:items-center sm:py-8 font-sans">
      <div className="w-full sm:max-w-[400px] bg-black h-screen sm:h-[800px] sm:max-h-[90vh] sm:rounded-[2.5rem] sm:border-[8px] sm:border-zinc-800 sm:shadow-2xl relative overflow-hidden flex flex-col pt-12">
        {/* Dynamic Notch */}
        <div className="hidden sm:block absolute top-0 left-1/2 -translate-x-1/2 w-1/3 h-7 bg-zinc-800 rounded-b-xl z-50 pointer-events-none"></div>
        
        <Toast />
        
        {view === 'login' && <LoginScreen />}
        {view === 'dashboard' && userType === 'cliente' && <ClientDashboard />}
        {view === 'dashboard' && userType === 'barbeiro' && <BarberDashboard />}
        {view === 'dashboard' && userType === 'barbearia' && <ShopDashboard />}
      </div>
    </div>
  );
}

