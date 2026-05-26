import React, { useState, useEffect } from 'react';
import { LogOut, CheckCircle, AlertCircle, X, ArrowRight, Briefcase, Package, Home } from 'lucide-react';
import './index.css';

const API_URL = 'http://127.0.0.1:8000';

function LoginForm({ onLoginSuccess }) {
  const [email, setEmail] = useState('');
  const [senha, setSenha] = useState('');
  const [loading, setLoading] = useState(false);
  const [toast, setToast] = useState(null);

  const notify = (msg, type = 'success') => {
    setToast({ msg, type });
    setTimeout(() => setToast(null), 3000);
  };

  const handleLogin = async (e) => {
    e.preventDefault();
    setLoading(true);
    try {
      const params = new URLSearchParams();
      params.append('username', email);
      params.append('password', senha);
      console.log('🔐 Tentando login em:', `${API_URL}/api/v1/login/admin/`);
      console.log('📋 Email:', email);
      
      let res;
      try {
        res = await fetch(`${API_URL}/api/v1/login/admin/`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
          body: params
        });
      } catch (fetchErr) {
        console.error('🌐 Erro de fetch:', fetchErr);
        throw new Error(`Erro de conexão: ${fetchErr.message}`);
      }
      
      console.log('📡 Status da resposta:', res.status);
      console.log('📡 Headers:', res.headers);
      
      if (!res.ok) {
        let errorData = {};
        try {
          errorData = await res.json();
        } catch (e) {
          console.warn('Não conseguiu parsear JSON:', e);
        }
        console.error('❌ Erro:', errorData);
        throw new Error(errorData.detail || 'Email ou senha incorretos');
      }
      
      let data;
      try {
        data = await res.json();
      } catch (jsonErr) {
        console.error('❌ Erro ao parsear JSON:', jsonErr);
        throw new Error('Resposta inválida do servidor');
      }
      
      console.log('✅ Login bem-sucedido!', data);
      notify('✅ Bem-vindo ao Painel Admin!', 'success');
      
      // Aguardar um pouco para garantir que o toast seja mostrado
      setTimeout(() => {
        try {
          onLoginSuccess(data.access_token);
        } catch (error) {
          console.error('❌ Erro ao chamar onLoginSuccess:', error);
        }
      }, 800);
    } catch (err) {
      console.error('🔴 Erro completo:', err);
      setLoading(false);
      notify(err.message || 'Erro ao conectar com o servidor', 'error');
    }
  };

  const Toast = () => {
    if (!toast) return null;
    const colors = { success: 'bg-green-600', error: 'bg-red-600', info: 'bg-blue-600' };
    return (
      <div className={`fixed top-4 right-4 ${colors[toast.type]} text-white px-6 py-3 rounded-lg shadow-lg flex items-center gap-3 z-50`}>
        {toast.type === 'success' ? <CheckCircle size={20} /> : <AlertCircle size={20} />}
        <span>{toast.msg}</span>
      </div>
    );
  };

  return (
    <>
      <Toast />
      <div className="min-h-screen bg-gradient-to-br from-black via-zinc-900 to-black flex items-center justify-center p-4">
        <div className="bg-zinc-900 rounded-2xl border border-zinc-800 p-8 w-full max-w-md shadow-2xl">
          <div className="text-center mb-8">
            <h1 className="text-4xl font-bold text-orange-600 mb-2">BarberMove</h1>
            <p className="text-zinc-400">🔐 Painel Administrativo</p>
          </div>

          <form onSubmit={handleLogin} className="space-y-4">
            <div>
              <label className="text-zinc-300 text-sm font-bold">Email</label>
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="admin@example.com"
                className="w-full bg-zinc-800 border border-zinc-700 rounded-lg px-4 py-3 text-white mt-2 focus:border-orange-600 focus:outline-none"
                required
                autoComplete="email"
              />
            </div>

            <div>
              <label className="text-zinc-300 text-sm font-bold">Senha</label>
              <input
                type="password"
                value={senha}
                onChange={(e) => setSenha(e.target.value)}
                placeholder="••••••••"
                className="w-full bg-zinc-800 border border-zinc-700 rounded-lg px-4 py-3 text-white mt-2 focus:border-orange-600 focus:outline-none"
                required
                autoComplete="current-password"
              />
            </div>

            <button
              type="submit"
              disabled={loading}
              className="w-full bg-orange-600 hover:bg-orange-700 disabled:opacity-50 text-white font-bold py-3 rounded-lg transition mt-6"
            >
              {loading ? 'Conectando...' : 'Acessar Painel'}
            </button>
          </form>
        </div>
      </div>
    </>
  );
}

function App() {
  const [token, setToken] = useState(localStorage.getItem('token'));
  const [view, setView] = useState(token ? 'dashboard' : 'login');

  const handleLogout = () => {
    localStorage.removeItem('token');
    setToken(null);
    setView('login');
  };

  const handleLoginSuccess = (newToken) => {
    console.log('📌 Salvando token e mudando para dashboard...');
    console.log('🔑 Novo token:', newToken.substring(0, 80) + '...');
    console.log('🧹 Limpando localStorage antigo...');
    localStorage.clear();
    localStorage.setItem('token', newToken);
    console.log('✅ Token salvo em localStorage');
    setToken(newToken);
    setView('dashboard');
  };

  return (
    <div className="min-h-screen bg-black">
      {view === 'login' && <LoginForm onLoginSuccess={handleLoginSuccess} />}
      {view === 'dashboard' && <AdminPanel token={token} onLogout={handleLogout} />}
    </div>
  );
}

function AdminPanel({ token, onLogout }) {
  const [pendentes, setPendentes] = useState([]);
  const [aprovados, setAprovados] = useState([]);
  const [rejeitados, setRejeitados] = useState([]);
  const [perfisPendentes, setPerfisPendentes] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selectedUser, setSelectedUser] = useState(null);
  const [rejectReason, setRejectReason] = useState('');
  const [toast, setToast] = useState(null);
  const [expandedImage, setExpandedImage] = useState(null);
  const [activeTab, setActiveTab] = useState('pendentes');

  const notify = (msg, type = 'success') => {
    setToast({ msg, type });
    setTimeout(() => setToast(null), 3000);
  };

  useEffect(() => {
    const load = async () => {
      try {
        console.log('🔑 Token atual:', token ? token.substring(0, 50) + '...' : 'NENHUM');
        
        const res = await fetch(`${API_URL}/api/v1/documentos/admin/pendentes`, {
          headers: { 'Authorization': `Bearer ${token}` }
        });
        if (res.ok) {
          const data = await res.json();
          setPendentes(data.usuarios || []);
        }
        
        // Carregar aprovados e rejeitados
        const resAprovados = await fetch(`${API_URL}/api/v1/documentos/admin/todos`, {
          headers: { 'Authorization': `Bearer ${token}` }
        });
        if (resAprovados.ok) {
          const dataAprovados = await resAprovados.json();
          const approved = dataAprovados.usuarios?.filter(u => u.documento_verificado && !u.documento_rejeitado_motivo) || [];
          const rejected = dataAprovados.usuarios?.filter(u => u.documento_rejeitado_motivo) || [];
          setAprovados(approved);
          setRejeitados(rejected);
        }
        
        // Carregar perfis pendentes de aprovação (documentos já verificados, mas perfil não aprovado)
        console.log('🔍 Buscando perfis pendentes em:', `${API_URL}/admin/api/pendentes`);
        console.log('🔑 Com token:', token ? 'SIM' : 'NÃO');
        const resPerfis = await fetch(`${API_URL}/admin/api/pendentes`, {
          headers: { 'Authorization': `Bearer ${token}` }
        });
        console.log('📡 Status resposta perfis:', resPerfis.status);
        if (resPerfis.ok) {
          const dataPerfis = await resPerfis.json();
          console.log('✅ Perfis pendentes recebidos:', dataPerfis);
          console.log('📊 Total de perfis:', dataPerfis?.length || 0);
          setPerfisPendentes(dataPerfis || []);
        } else {
          const errorText = await resPerfis.text();
          console.error('❌ Erro ao buscar perfis:', resPerfis.status, resPerfis.statusText, errorText);
        }
      } catch (err) {
        console.error('🔴 Erro ao carregar dados:', err);
        notify('Erro ao carregar documentos', 'error');
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
      }
    } catch (err) {
      notify('Erro ao aprovar', 'error');
    }
  };

  const rejeitar = async (userId) => {
    try {
      const res = await fetch(`${API_URL}/api/v1/documentos/verificar`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
        body: JSON.stringify({ usuario_id: userId, aprovado: false, motivo_rejeicao: rejectReason || 'Rejeitado' })
      });
      if (res.ok) {
        notify('❌ Documento rejeitado', 'success');
        setPendentes(pendentes.filter(u => u.id !== userId));
        setSelectedUser(null);
        setRejectReason('');
      }
    } catch (err) {
      notify('Erro ao rejeitar', 'error');
    }
  };

  const aprovarPerfil = async (userId) => {
    try {
      const res = await fetch(`${API_URL}/admin/api/aprovar/${userId}`, {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${token}` }
      });
      if (res.ok) {
        notify('✅ Perfil aprovado!', 'success');
        setPerfisPendentes(perfisPendentes.filter(u => u.id !== userId));
        setSelectedUser(null);
      }
    } catch (err) {
      notify('Erro ao aprovar perfil', 'error');
    }
  };

  const rejeitarPerfil = async (userId) => {
    try {
      const res = await fetch(`${API_URL}/admin/api/rejeitar/${userId}`, {
        method: 'POST',
        headers: { 
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}` 
        },
        body: JSON.stringify({ motivo: rejectReason || 'Perfil não aprovado' })
      });
      if (res.ok) {
        notify('❌ Perfil rejeitado', 'success');
        setPerfisPendentes(perfisPendentes.filter(u => u.id !== userId));
        setSelectedUser(null);
        setRejectReason('');
      }
    } catch (err) {
      notify('Erro ao rejeitar perfil', 'error');
    }
  };

  const Toast = () => {
    if (!toast) return null;
    const colors = { success: 'bg-green-600', error: 'bg-red-600', info: 'bg-blue-600' };
    return (
      <div className={`fixed top-4 right-4 ${colors[toast.type]} text-white px-6 py-3 rounded-lg shadow-lg flex items-center gap-3 z-50`}>
        {toast.type === 'success' ? <CheckCircle size={20} /> : <AlertCircle size={20} />}
        <span>{toast.msg}</span>
      </div>
    );
  };

  if (expandedImage) {
    return (
      <div className="fixed inset-0 bg-black/95 z-[9999] flex items-center justify-center p-4" onClick={() => setExpandedImage(null)}>
        <div className="relative max-w-4xl max-h-[90vh] w-full h-full flex items-center justify-center">
          <button onClick={() => setExpandedImage(null)} className="absolute top-4 right-4 text-white bg-zinc-900 p-2 rounded-lg hover:bg-zinc-800 z-10">
            <X size={24} />
          </button>
          <img src={expandedImage} alt="Expandido" className="max-w-full max-h-full object-contain rounded-lg" />
        </div>
      </div>
    );
  }

  if (selectedUser) {
    const getImageUrl = (url) => {
      if (!url) return '';
      if (url.startsWith('http')) return url;
      return `${API_URL}${url.startsWith('/') ? '' : '/'}${url}`;
    };
    
    const ImageThumb = ({ src, alt, label }) => {
      const fullUrl = getImageUrl(src);
      return (
        <div>
          <p className="text-zinc-400 text-sm mb-2">{label}</p>
          <img 
            src={fullUrl} 
            alt={alt} 
            onClick={() => setExpandedImage(fullUrl)}
            className="w-full rounded-lg border border-zinc-700 max-h-64 object-cover cursor-pointer hover:opacity-80 transition-opacity" 
          />
        </div>
      );
    };
    return (
      <div className="fixed inset-0 bg-black/90 backdrop-blur-sm z-[9999] flex items-center justify-center p-4">
        <Toast />
        <div className="bg-zinc-900 rounded-2xl max-w-2xl w-full max-h-[85vh] border border-zinc-800 p-8 overflow-y-auto">
          <div className="flex justify-between items-center mb-6">
            <h2 className="text-2xl font-bold text-white">{selectedUser.nome}</h2>
            <button onClick={() => setSelectedUser(null)} className="text-zinc-500 hover:text-white">
              <X size={24} />
            </button>
          </div>

          <div className="grid grid-cols-3 gap-4 mb-6 text-xs">
            <div className="min-w-0">
              <p className="text-zinc-400">Email</p>
              <p className="text-white font-mono truncate" title={selectedUser.email}>{selectedUser.email}</p>
            </div>
            <div>
              <p className="text-zinc-400">Tipo</p>
              <p className="text-white capitalize">{selectedUser.tipo}</p>
            </div>
            <div className="min-w-0">
              <p className="text-zinc-400">CPF</p>
              <p className="text-white font-mono truncate">{selectedUser.cpf || '-'}</p>
            </div>
          </div>

          <div className="space-y-4 mb-6">
            {selectedUser.documento_frente_url && (
              <ImageThumb src={selectedUser.documento_frente_url} alt="Frente" label="📄 Documento - Frente" />
            )}
            {selectedUser.documento_verso_url && (
              <ImageThumb src={selectedUser.documento_verso_url} alt="Verso" label="📄 Documento - Verso" />
            )}
            {selectedUser.selfie_documento_url && (
              <ImageThumb src={selectedUser.selfie_documento_url} alt="Selfie" label="🤳 Selfie com Documento" />
            )}
          </div>

          <div className="mb-4">
            <label className="text-zinc-400 text-sm">Motivo da rejeição (se aplicável)</label>
            <textarea
              value={rejectReason}
              onChange={(e) => setRejectReason(e.target.value)}
              placeholder="Documentos ilegíveis, fora de validade, etc..."
              className="w-full bg-zinc-800 border border-zinc-700 rounded-lg px-4 py-2 text-white mt-2 text-sm"
              rows="3"
            />
          </div>

          <div className="flex gap-3">
            {selectedUser.from === 'perfis' ? (
              <>
                <button
                  onClick={() => rejeitarPerfil(selectedUser.id)}
                  className="flex-1 bg-red-600 hover:bg-red-700 text-white font-bold py-3 rounded-lg transition"
                >
                  ❌ Rejeitar Perfil
                </button>
                <button
                  onClick={() => aprovarPerfil(selectedUser.id)}
                  className="flex-1 bg-green-600 hover:bg-green-700 text-white font-bold py-3 rounded-lg transition"
                >
                  ✅ Aprovar Perfil
                </button>
              </>
            ) : (
              <>
                <button
                  onClick={() => rejeitar(selectedUser.id)}
                  className="flex-1 bg-red-600 hover:bg-red-700 text-white font-bold py-3 rounded-lg transition"
                >
                  ❌ Rejeitar Documento
                </button>
                <button
                  onClick={() => aprovar(selectedUser.id)}
                  className="flex-1 bg-green-600 hover:bg-green-700 text-white font-bold py-3 rounded-lg transition"
                >
                  ✅ Aprovar Documento
                </button>
              </>
            )}
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="bg-black min-h-screen text-white">
      <Toast />
      <div className="border-b border-zinc-800 sticky top-0 z-20 bg-black/80 backdrop-blur-sm">
        <div className="max-w-6xl mx-auto px-6 py-4 flex justify-between items-center">
          <div>
            <h1 className="text-2xl font-bold">🔐 BarberMove Admin</h1>
            <p className="text-zinc-400 text-sm">Painel de Documentos Pendentes</p>
          </div>
          <button
            onClick={onLogout}
            className="bg-red-600 hover:bg-red-700 text-white px-4 py-2 rounded-lg flex items-center gap-2 transition"
          >
            <LogOut size={18} /> Sair
          </button>
        </div>
      </div>

      <div className="max-w-6xl mx-auto p-6 pt-12">
        {/* Abas */}
        <div className="flex gap-4 mb-8 border-b border-zinc-800">
          <button
            onClick={() => setActiveTab('pendentes')}
            className={`pb-4 px-4 font-bold transition-colors ${activeTab === 'pendentes' ? 'text-orange-600 border-b-2 border-orange-600' : 'text-zinc-400 hover:text-white'}`}
          >
            📋 Pendentes ({pendentes.length})
          </button>
          <button
            onClick={() => setActiveTab('aprovados')}
            className={`pb-4 px-4 font-bold transition-colors ${activeTab === 'aprovados' ? 'text-green-600 border-b-2 border-green-600' : 'text-zinc-400 hover:text-white'}`}
          >
            ✅ Aprovados ({aprovados.length})
          </button>
          <button
            onClick={() => setActiveTab('rejeitados')}
            className={`pb-4 px-4 font-bold transition-colors ${activeTab === 'rejeitados' ? 'text-red-600 border-b-2 border-red-600' : 'text-zinc-400 hover:text-white'}`}
          >
            ❌ Rejeitados ({rejeitados.length})
          </button>
          <button
            onClick={() => setActiveTab('perfis')}
            className={`pb-4 px-4 font-bold transition-colors ${activeTab === 'perfis' ? 'text-blue-600 border-b-2 border-blue-600' : 'text-zinc-400 hover:text-white'}`}
          >
            👤 Perfis Pendentes ({perfisPendentes.length})
          </button>
        </div>

        {/* Conteúdo das Abas */}
        {loading ? (
          <div className="text-center py-12">
            <div className="inline-block animate-spin rounded-full h-8 w-8 border-t-2 border-orange-600"></div>
            <p className="text-zinc-400 mt-4">Carregando...</p>
          </div>
        ) : activeTab === 'pendentes' ? (
          pendentes.length === 0 ? (
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
                  <div className="flex justify-between items-center">
                    <div>
                      <h3 className="font-bold text-lg text-white">{user.nome}</h3>
                      <p className="text-sm text-zinc-400">{user.email}</p>
                      <p className="text-xs text-zinc-500 capitalize mt-1">Tipo: {user.tipo}</p>
                    </div>
                    <ArrowRight size={20} className="text-zinc-500" />
                  </div>
                </button>
              ))}
            </div>
          )
        ) : activeTab === 'aprovados' ? (
          aprovados.length === 0 ? (
            <div className="bg-zinc-900 border border-zinc-800 rounded-xl p-8 text-center">
              <p className="text-zinc-400">Nenhum perfil aprovado ainda.</p>
            </div>
          ) : (
            <div className="grid gap-4">
              {aprovados.map(user => (
                <button
                  key={user.id}
                  onClick={() => setSelectedUser(user)}
                  className="bg-green-900/20 border border-green-800 hover:border-green-600 p-4 rounded-xl text-left transition"
                >
                  <div className="flex justify-between items-center">
                    <div>
                      <h3 className="font-bold text-lg text-white">{user.nome}</h3>
                      <p className="text-sm text-zinc-400">{user.email}</p>
                      <p className="text-xs text-green-400 capitalize mt-1">✅ Tipo: {user.tipo}</p>
                    </div>
                    <ArrowRight size={20} className="text-green-500" />
                  </div>
                </button>
              ))}
            </div>
          )
        ) : activeTab === 'rejeitados' ? (
          rejeitados.length === 0 ? (
            <div className="bg-zinc-900 border border-zinc-800 rounded-xl p-8 text-center">
              <p className="text-zinc-400">Nenhum perfil rejeitado.</p>
            </div>
          ) : (
            <div className="grid gap-4">
              {rejeitados.map(user => (
                <button
                  key={user.id}
                  onClick={() => setSelectedUser(user)}
                  className="bg-red-900/20 border border-red-800 hover:border-red-600 p-4 rounded-xl text-left transition"
                >
                  <div className="flex justify-between items-center">
                    <div>
                      <h3 className="font-bold text-lg text-white">{user.nome}</h3>
                      <p className="text-sm text-zinc-400">{user.email}</p>
                      <p className="text-xs text-red-400 capitalize mt-1">❌ Motivo: {user.documento_rejeitado_motivo}</p>
                    </div>
                    <ArrowRight size={20} className="text-red-500" />
                  </div>
                </button>
              ))}
            </div>
          )
        ) : (
          perfisPendentes.length === 0 ? (
            <div className="bg-zinc-900 border border-zinc-800 rounded-xl p-8 text-center">
              <p className="text-zinc-400">✅ Não há perfis pendentes de aprovação!</p>
            </div>
          ) : (
            <div className="grid gap-4">
              {perfisPendentes.map(user => (
                <button
                  key={user.id}
                  onClick={() => setSelectedUser({ ...user, from: 'perfis' })}
                  className="bg-blue-900/20 border border-blue-800 hover:border-blue-600 p-4 rounded-xl text-left transition"
                >
                  <div className="flex justify-between items-center">
                    <div>
                      <h3 className="font-bold text-lg text-white">{user.nome}</h3>
                      <p className="text-sm text-zinc-400">{user.email}</p>
                      <p className="text-xs text-blue-400 capitalize mt-1">👤 Tipo: {user.tipo}</p>
                      {user.email_verificado && <p className="text-xs text-green-400 mt-1">✅ Email verificado</p>}
                    </div>
                    <ArrowRight size={20} className="text-blue-500" />
                  </div>
                </button>
              ))}
            </div>
          )
        )}
      </div>
    </div>
  );
}

export default App;
