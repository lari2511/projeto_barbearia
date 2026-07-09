/**
 * TELA DE LOGIN - BARBEIRO (FREELANCER)
 * Integrada com Firebase Cloud Messaging para notificações push
 * 
 * Fluxo:
 * 1. Barbeiro digita email e senha
 * 2. Backend faz login e retorna token JWT
 * 3. React Native pede permissão para notificações
 * 4. Gera device token (FCM) único do celular
 * 5. Envia device token para backend via POST /api/v1/firebase/registrar-token
 * 6. Backend salva no campo device_token do Usuario
 * 7. Barbeiro recebe notificações: pagamentos, chamados, saques, etc
 */

import React, { useState } from 'react';
import { getApiBaseUrl } from '../utils/api';
// Versão web: usa classes Tailwind e layout do app

const TelaLoginFreelancer = ({ navigation, onLoginSuccess }) => {
  const [email, setEmail] = useState('barbeiro@teste.com');
  const [senha, setSenha] = useState('123456');
  const [loading, setLoading] = useState(false);
  const [mostraSenha, setMostraSenha] = useState(false);

  const API_URL = getApiBaseUrl();

  /**
   * Registra o device token no backend
   * Esse token permite que o servidor envie notificações push para esse aparelho específico
   */
  // Em web não configuramos FCM aqui; apenas salvamos o token retornado pelo backend.

  /**
   * Fazer login:
   * 1. Valida email/senha contra backend
   * 2. Recebe JWT token
   * 3. Configura notificações push
   * 4. Navega para dashboard
   */
  const fazerLogin = async () => {
    if (!email || !senha) {
      console.log('[alert]','Digite seu e-mail e senha');
      return;
    }

    setLoading(true);
    try {
      const form = new URLSearchParams({ username: email, password: senha });
      const res = await fetch(`${API_URL}/api/v1/login/barbeiro/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
        body: form.toString(),
      });
      if (!res.ok) {
        const err = await res.json().catch(()=>({ detail: 'Erro' }));
        console.log('[alert]', err.detail || 'E-mail ou senha incorretos');
        setLoading(false);
        return;
      }
      const data = await res.json();
      const jwtToken = data.access_token;
      const userId = data.user_id;
      // salva token para app web
      localStorage.setItem('token', jwtToken);
      localStorage.setItem('userType', 'barbeiro');
      if (onLoginSuccess) onLoginSuccess({ token: jwtToken, userId, email, tipo: data.tipo });
      console.log('[alert]','Login realizado');
      window.location.reload();
    } catch (e) {
      console.error(e);
      console.log('[alert]','Erro ao conectar com o servidor');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-black text-white p-4 font-sans antialiased flex flex-col items-center justify-center select-none">
      <div className="w-full max-w-[400px] bg-[#1e1e24] rounded-2xl p-6 border border-zinc-800/50 shadow-2xl space-y-6">
        <div className="text-center space-y-1">
          <h1 className="text-2xl font-black tracking-tight text-white uppercase">
            Barber<span className="text-[#f97316]">Move</span>
          </h1>
          <p className="text-xs text-zinc-400 font-bold">Login Barbeiro</p>
        </div>

        <div className="space-y-4">
          <div className="space-y-1.5">
            <label className="text-[11px] uppercase font-black tracking-wider text-zinc-400 block">E-mail</label>
            <input 
              type="email" 
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="w-full bg-black border border-zinc-800 focus:border-[#f97316] rounded-xl px-4 py-3.5 text-sm text-white placeholder-zinc-600 focus:outline-none transition-all"
            />
          </div>

          <div className="space-y-1.5 relative">
            <label className="text-[11px] uppercase font-black tracking-wider text-zinc-400 block">Senha</label>
            <div className="relative flex items-center">
              <input 
                type={mostraSenha ? "text" : "password"} 
                value={senha}
                onChange={(e) => setSenha(e.target.value)}
                className="w-full bg-black border border-zinc-800 focus:border-[#f97316] rounded-xl px-4 py-3.5 text-sm text-white focus:outline-none transition-all pr-16"
              />
              <button 
                type="button"
                onClick={() => setMostraSenha(!mostraSenha)}
                className="absolute right-3 text-[10px] font-black uppercase tracking-wider px-2.5 py-1.5 rounded-lg border border-zinc-800 transition-all cursor-pointer"
                style={{ background: '#0b0b0d', color: '#cbd5e1', borderColor: 'rgba(148,163,184,0.12)' }}
              >
                {mostraSenha ? 'Ocultar' : 'Mostrar'}
              </button>
            </div>
          </div>

          <div className="pt-2">
            <button onClick={fazerLogin} className="w-full bg-[#f97316] hover:bg-orange-600 active:scale-[0.98] text-white font-bold text-sm py-4 rounded-xl transition-all shadow-lg shadow-orange-600/10 text-center border-none cursor-pointer" style={{ background: '#f97316', color: '#ffffff' }}>
              {loading ? 'Entrando...' : 'Entrar na Conta'}
            </button>
          </div>
        </div>

        <div className="space-y-3 pt-2 border-t border-zinc-800/50 text-center">
          <p className="text-xs text-zinc-400 leading-relaxed">💡 Você receberá notificações push quando um cliente pagar pelo corte.</p>
          <p className="text-xs text-zinc-500">Não tem conta? <span className="text-[#f97316] font-bold cursor-pointer hover:underline">Cadastre-se</span></p>
          <div className="text-[11px] text-zinc-600 flex items-center justify-center gap-1.5 justify-center">
            <span>🔔</span> Firebase Cloud Messaging (opcional)
          </div>
        </div>
      </div>
    </div>
  );
};

export default TelaLoginFreelancer;
