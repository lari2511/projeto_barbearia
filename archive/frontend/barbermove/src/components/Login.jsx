// Tela de Login do BarberMovie
import React, { useState } from 'react';
import { User, Store, Scissors, ArrowRight } from 'lucide-react';
import { useApp } from '../contexts/AppContext';
import { Button, Input } from './Common';

export default function Login({ onLoginSuccess }) {
  const { login, loading } = useApp();
  const [step, setStep] = useState('escolha'); // 'escolha', 'login'
  const [selectedType, setSelectedType] = useState(null);
  const [email, setEmail] = useState('');
  const [senha, setSenha] = useState('');

  const handleTypeSelect = (type) => {
    setSelectedType(type);
    setStep('login');
  };

  const handleLogin = async (e) => {
    e.preventDefault();
    try {
      const success = await login(email, senha, selectedType);
      if (success && onLoginSuccess) {
        onLoginSuccess();
      }
    } catch (erro) {
      console.error('ERRO REAL DETECTADO NO LOGIN:', erro);
      alert('Falha na conexão: ' + (erro && erro.message ? erro.message : String(erro)));
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
      description: 'Assinatura R$ 49,90/mês',
      icon: Store,
      color: 'purple',
    },
  ];

  if (step === 'escolha') {
    return (
      <div className="min-h-screen bg-black text-white flex items-center justify-center p-4">
        <div className="w-full max-w-[430px]">
          <div className="text-center mb-8">
            <div className="mx-auto mb-4 w-24 h-24 rounded-3xl border border-zinc-800 bg-[#1e1e24] flex items-center justify-center shadow-[0_12px_30px_rgba(0,0,0,0.35)]">
              <span className="text-4xl font-black text-orange-500">B</span>
            </div>
            <h1 className="text-3xl font-black text-white mb-2">BarberMovie</h1>
            <p className="text-zinc-500 text-sm">Conectando barbearias, freelancers e clientes</p>
          </div>

          <div className="grid gap-3">
            {userTypes.map(({ type, title, description, icon, color }) => {
              const IconComponent = icon;
              const colors = {
                blue: 'from-sky-600 to-sky-700',
                green: 'from-emerald-600 to-emerald-700',
                purple: 'from-orange-600 to-orange-700',
              };

              return (
                <div
                  key={type}
                  onClick={() => handleTypeSelect(type)}
                  className={`bg-gradient-to-br ${colors[color]} text-white rounded-2xl p-5 cursor-pointer transform transition-all hover:scale-[1.01] hover:shadow-xl border border-white/5`}
                >
                  <IconComponent size={36} className="mb-4" />
                  <h2 className="text-xl font-black mb-2">{title}</h2>
                  <p className="text-white/90 text-sm">{description}</p>
                  <div className="mt-4 flex items-center text-sm font-semibold">
                    <span>Entrar</span>
                    <ArrowRight size={16} className="ml-1" />
                  </div>
                </div>
              );
            })}
          </div>

          <div className="text-center mt-8">
            <p className="text-zinc-500 text-sm">
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
      <div className="min-h-screen bg-black text-white flex items-center justify-center p-4">
        <div className="bg-[#1e1e24] rounded-2xl shadow-xl p-5 max-w-[430px] w-full border border-zinc-800/50">
          <button
            onClick={() => setStep('escolha')}
            className="text-zinc-400 hover:text-white mb-4 flex items-center"
          >
            ← Voltar
          </button>

          <div className="text-center mb-6">
            <selectedUserType.icon size={36} className="mx-auto mb-2 text-orange-400" />
            <h2 className="text-2xl font-black text-white">{selectedUserType.title}</h2>
            <p className="text-zinc-500 mt-1 text-sm">{selectedUserType.description}</p>
          </div>

          <form onSubmit={handleLogin}>
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

          <div className="mt-6 text-center">
            <button className="text-sm text-zinc-400 hover:text-white hover:underline">
              Esqueci minha senha
            </button>
          </div>

          <div className="mt-4 text-center">
            <p className="text-zinc-500 text-sm">
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

  return null;
}
