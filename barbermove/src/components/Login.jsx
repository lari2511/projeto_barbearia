// Tela de Login do BarberMove
import React, { useState } from 'react';
import { User, Store, Scissors, ArrowRight } from 'lucide-react';
import { useApp } from '../contexts/AppContext';
import { Button, Input } from './Common';
import Cadastro from './Cadastro';
import EsqueciSenha from './EsqueciSenha';

export default function Login({ onLoginSuccess }) {
  const { login, loading } = useApp();
  const [step, setStep] = useState(() => {
    // Verifica se veio com token de reset na URL
    const params = new URLSearchParams(window.location.search);
    return params.get('reset_token') ? 'esqueci' : 'escolha';
  });
  const [selectedType, setSelectedType] = useState(null);
  const [email, setEmail] = useState('');
  const [senha, setSenha] = useState('');
  const [erroLogin, setErroLogin] = useState('');

  const handleTypeSelect = (type) => {
    setSelectedType(type);
    setErroLogin('');
    setStep('login');
  };

  const handleLogin = async (e) => {
    e.preventDefault();
    try {
      setErroLogin('');
      const success = await login(email, senha, selectedType);
      if (success && onLoginSuccess) {
        onLoginSuccess();
        return;
      }

      setErroLogin('Não foi possível entrar. Verifique os dados e tente novamente.');
    } catch (erro) {
      const mensagem = erro instanceof Error ? erro.message : 'Não foi possível entrar. Tente novamente.';
      setErroLogin(mensagem);
    }
  };

  const userTypes = [
    {
      type: 'cliente',
      title: 'Sou Cliente',
      description: 'Encontre freelancers e barbearias',
      icon: User,
      color: 'blue',
    },
    {
      type: 'barbeiro',
      title: 'Sou Freelancer',
      description: 'Taxa de 10% por serviço',
      icon: Scissors,
      color: 'green',
    },
    {
      type: 'barbearia',
      title: 'Tenho uma Barbearia',
      description: 'Assinatura R$ 47,90/mês',
      icon: Store,
      color: 'purple',
    },
  ];

  if (step === 'escolha') {
    return (
      <div className="bg-[#0b0b0d] text-white flex flex-col justify-start px-1 pt-2 pb-4">
        <div className="w-full min-w-0">
          <div className="text-center mb-4">
            <div className="mx-auto mb-3 w-28 h-28 rounded-3xl border border-orange-500/30 bg-zinc-950 flex items-center justify-center shadow-[0_0_40px_rgba(249,115,22,0.25),0_12px_30px_rgba(0,0,0,0.5)] overflow-hidden">
              <img src="/logo.jpeg" alt="BarberMove" className="h-full w-full object-cover" />
            </div>
            <h1 className="mt-2 text-xl font-black tracking-[0.22em] uppercase">
              <span className="text-white">Barber</span>
              <span className="text-orange-400">Move</span>
            </h1>
            <p className="text-zinc-500 text-xs mt-1 tracking-widest uppercase">Seu barbeiro a um toque</p>
          </div>

          <div className="grid gap-1">
            {userTypes.map(({ type, title, description, icon, color }) => {
              const IconComponent = icon;
              const styles = {
                blue: { borderColor: '#7dd3fc', backgroundColor: '#0ea5e9', color: '#fff' },
                green: { borderColor: '#86efac', backgroundColor: '#22c55e', color: '#fff' },
                purple: { borderColor: '#fb923c', backgroundColor: '#f97316', color: '#fff' },
                orange: { borderColor: '#fdba74', backgroundColor: '#ea580c', color: '#fff' },
              };

              return (
                <div
                  key={type}
                  onClick={() => handleTypeSelect(type)}
                  className="rounded-2xl p-2 cursor-pointer transform transition-all hover:scale-[1.01] hover:shadow-xl border text-white"
                  style={styles[color]}
                >
                  <IconComponent size={22} className="mb-1.5" />
                  <h2 className="text-sm font-black mb-0.5">{title}</h2>
                  <p className="text-white/75 text-xs sm:text-sm">{description}</p>
                  <div className="mt-1 flex items-center text-xs font-semibold">
                    <span>Entrar</span>
                    <ArrowRight size={16} className="ml-1" />
                  </div>
                </div>
              );
            })}
          </div>

          <div className="text-center mt-1.5">
            <p className="text-white/70 text-xs sm:text-sm">
              Não tem conta?{' '}
              <button onClick={() => setStep('cadastro')} className="text-orange-400 font-semibold hover:underline">
                Cadastre-se
              </button>
            </p>
          </div>
        </div>
      </div>
    );
  }

  if (step === 'login') {
    const selectedUserType = userTypes.find(t => t.type === selectedType);

    return (
      <div className="bg-[#0b0b0d] text-white flex flex-col justify-start px-1 pt-2 pb-6">
        <div className="bg-zinc-950 rounded-2xl shadow-sm p-3 w-full border border-white/10">
          <button
            onClick={() => setStep('escolha')}
            className="text-zinc-400 hover:text-white mb-2.5 flex items-center"
          >
            ← Voltar
          </button>

          <div className="text-center mb-2.5">
            <selectedUserType.icon size={28} className="mx-auto mb-2 text-orange-400" />
            <h2 className="text-base font-black text-white">{selectedUserType.title}</h2>
            <p className="text-zinc-500 mt-1 text-xs sm:text-sm">{selectedUserType.description}</p>
          </div>

          <form onSubmit={handleLogin}>
            {erroLogin && (
              <div className="mb-3 rounded-xl border border-red-500/40 bg-red-500/10 px-3 py-2 text-xs text-red-200 font-semibold">
                {erroLogin}
              </div>
            )}

            <Input
              label="Email"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="seu@email.com"
              required
            />

            <Input
              label="Senha"
              type="password"
              value={senha}
              onChange={(e) => setSenha(e.target.value)}
              placeholder="••••••"
              required
            />

            <Button type="submit" fullWidth disabled={loading}>
              {loading ? 'Entrando...' : 'Entrar'}
            </Button>
          </form>

          <div className="mt-3 text-center">
            <button onClick={() => setStep('esqueci')} className="text-sm text-zinc-400 hover:text-white hover:underline">
              Esqueci minha senha
            </button>
          </div>

          <div className="mt-2 text-center">
            <p className="text-white/70 text-xs sm:text-sm">
              Não tem conta?{' '}
              <button onClick={() => setStep('cadastro')} className="text-orange-400 font-semibold hover:underline">
                Cadastre-se
              </button>
            </p>
          </div>
        </div>
      </div>
    );
  }

  if (step === 'esqueci') {
    return <EsqueciSenha onBack={() => setStep('login')} />;
  }

  if (step === 'cadastro') {
    return (
      <Cadastro
        initialType={selectedType || 'cliente'}
        onBack={() => setStep('escolha')}
        onSuccess={() => {
          if (onLoginSuccess) {
            onLoginSuccess();
          }
        }}
      />
    );
  }

  return null;
}
