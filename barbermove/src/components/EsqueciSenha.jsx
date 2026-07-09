import { useState } from 'react';
import { ArrowLeft, Mail, Lock, CheckCircle, Eye, EyeOff } from 'lucide-react';
import { getApiBaseUrl } from '../utils/api';

const API_URL = getApiBaseUrl();

export default function EsqueciSenha({ onBack }) {
  const params = new URLSearchParams(window.location.search);
  const tokenDaUrl = params.get('reset_token') || '';

  const [step, setStep] = useState(tokenDaUrl ? 'token' : 'email');
  const [email, setEmail] = useState('');
  const [token, setToken] = useState(tokenDaUrl);
  const [novaSenha, setNovaSenha] = useState('');
  const [confirmar, setConfirmar] = useState('');
  const [loading, setLoading] = useState(false);
  const [erro, setErro] = useState('');
  const [msg, setMsg] = useState('');
  const [mostrarNovaSenha, setMostrarNovaSenha] = useState(false);
  const [mostrarConfirmarSenha, setMostrarConfirmarSenha] = useState(false);

  const enviarEmail = async (e) => {
    e.preventDefault();
    setErro('');
    setLoading(true);
    try {
      const normalizedEmail = String(email || '').trim().toLowerCase();
      const res = await fetch(`${API_URL}/api/v1/senha/solicitar-reset`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email: normalizedEmail }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || 'Não foi possível enviar as instruções.');
      setMsg(data.mensagem);
      setStep('token');
    } catch (err) {
      setErro(err?.message || 'Erro de conexão. Tente novamente.');
    } finally {
      setLoading(false);
    }
  };

  const redefinirSenha = async (e) => {
    e.preventDefault();
    setErro('');
    if (novaSenha !== confirmar) {
      setErro('As senhas não coincidem.');
      return;
    }
    if (novaSenha.length < 6) {
      setErro('A senha deve ter pelo menos 6 caracteres.');
      return;
    }
    setLoading(true);
    try {
      const res = await fetch(`${API_URL}/api/v1/senha/confirmar-reset`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ token, nova_senha: novaSenha }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || 'Erro ao redefinir senha.');
      setStep('sucesso');
    } catch (err) {
      setErro(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="bg-[#0b0b0d] text-white flex flex-col px-1 pt-2 pb-6 min-h-screen">
      <div className="w-full rounded-2xl border border-zinc-800/50 bg-[#1e1e24] p-4 space-y-4">

        <button onClick={onBack} className="flex items-center gap-2 text-sm text-zinc-400 hover:text-white">
          <ArrowLeft size={16} /> Voltar ao login
        </button>

        <div className="text-center space-y-1">
          <div className="mx-auto w-14 h-14 rounded-2xl bg-orange-500/15 border border-orange-500/30 flex items-center justify-center text-2xl">🔑</div>
          <h1 className="text-lg font-black text-white">Esqueci minha senha</h1>
          <p className="text-xs text-zinc-400">
            {step === 'email' && 'Informe seu email para receber as instruções'}
            {step === 'token' && 'Insira o token recebido e sua nova senha'}
            {step === 'sucesso' && 'Senha redefinida com sucesso!'}
          </p>
        </div>

        {erro && (
          <div className="rounded-xl border border-red-500/30 bg-red-500/10 px-3 py-2 text-sm text-red-300">
            {erro}
          </div>
        )}

        {/* STEP 1: Email */}
        {step === 'email' && (
          <form onSubmit={enviarEmail} className="space-y-3">
            <div>
              <label className="text-xs text-zinc-400 mb-1 block">Email</label>
              <div className="flex items-center gap-2 bg-zinc-900 border border-zinc-700 rounded-xl px-3 py-2">
                <Mail size={16} className="text-zinc-500" />
                <input
                  type="email"
                  value={email}
                  onChange={e => setEmail(e.target.value)}
                  placeholder="seu@email.com"
                  required
                  className="bg-transparent text-white text-sm outline-none flex-1"
                />
              </div>
            </div>
            <button
              type="submit"
              disabled={loading}
              className="w-full bg-orange-500 hover:bg-orange-600 disabled:opacity-50 text-white font-black rounded-xl py-3 text-sm transition-all"
            >
              {loading ? 'Enviando...' : 'Enviar instruções'}
            </button>
          </form>
        )}

        {/* STEP 2: Token + nova senha */}
        {step === 'token' && (
          <form onSubmit={redefinirSenha} className="space-y-3">
            {msg && (
              <div className="rounded-xl border border-green-500/30 bg-green-500/10 px-3 py-2 text-sm text-green-300">
                {msg} Verifique também o terminal do servidor para o link de teste.
              </div>
            )}
            <div>
              <label className="text-xs text-zinc-400 mb-1 block">Token recebido por email</label>
              <input
                type="text"
                value={token}
                onChange={e => setToken(e.target.value)}
                placeholder="Cole o token aqui"
                required
                className="w-full bg-zinc-900 border border-zinc-700 rounded-xl px-3 py-2 text-sm text-white outline-none focus:border-orange-500"
              />
            </div>
            <div>
              <label className="text-xs text-zinc-400 mb-1 block">Nova senha</label>
              <div className="flex items-center gap-2 bg-zinc-900 border border-zinc-700 rounded-xl px-3 py-2">
                <Lock size={16} className="text-zinc-500" />
                <input
                  type={mostrarNovaSenha ? 'text' : 'password'}
                  value={novaSenha}
                  onChange={e => setNovaSenha(e.target.value)}
                  placeholder="Mínimo 6 caracteres"
                  required
                  className="bg-transparent text-white text-sm outline-none flex-1"
                />
                <button
                  type="button"
                  onClick={() => setMostrarNovaSenha((prev) => !prev)}
                  className="text-zinc-400 hover:text-white"
                  aria-label={mostrarNovaSenha ? 'Ocultar senha' : 'Mostrar senha'}
                >
                  {mostrarNovaSenha ? <EyeOff size={16} /> : <Eye size={16} />}
                </button>
              </div>
            </div>
            <div>
              <label className="text-xs text-zinc-400 mb-1 block">Confirmar senha</label>
              <div className="flex items-center gap-2 bg-zinc-900 border border-zinc-700 rounded-xl px-3 py-2">
                <Lock size={16} className="text-zinc-500" />
                <input
                  type={mostrarConfirmarSenha ? 'text' : 'password'}
                  value={confirmar}
                  onChange={e => setConfirmar(e.target.value)}
                  placeholder="Repita a nova senha"
                  required
                  className="bg-transparent text-white text-sm outline-none flex-1"
                />
                <button
                  type="button"
                  onClick={() => setMostrarConfirmarSenha((prev) => !prev)}
                  className="text-zinc-400 hover:text-white"
                  aria-label={mostrarConfirmarSenha ? 'Ocultar senha' : 'Mostrar senha'}
                >
                  {mostrarConfirmarSenha ? <EyeOff size={16} /> : <Eye size={16} />}
                </button>
              </div>
            </div>
            <button
              type="submit"
              disabled={loading}
              className="w-full bg-orange-500 hover:bg-orange-600 disabled:opacity-50 text-white font-black rounded-xl py-3 text-sm transition-all"
            >
              {loading ? 'Redefinindo...' : 'Redefinir senha'}
            </button>
            <button type="button" onClick={() => setStep('email')} className="w-full text-xs text-zinc-500 hover:text-white">
              ← Tentar outro email
            </button>
          </form>
        )}

        {/* STEP 3: Sucesso */}
        {step === 'sucesso' && (
          <div className="text-center space-y-4">
            <CheckCircle size={48} className="mx-auto text-green-400" />
            <p className="text-sm text-zinc-300">Sua senha foi redefinida! Agora você já pode fazer login com a nova senha.</p>
            <button
              onClick={onBack}
              className="w-full bg-orange-500 hover:bg-orange-600 text-white font-black rounded-xl py-3 text-sm"
            >
              Ir para o login
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
