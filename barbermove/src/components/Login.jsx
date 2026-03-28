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
    const success = await login(email, senha, selectedType);
    if (success && onLoginSuccess) {
      onLoginSuccess();
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
      <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 flex items-center justify-center p-4">
        <div className="max-w-4xl w-full">
          <div className="text-center mb-8">
            <h1 className="text-4xl font-bold text-gray-900 mb-2">BarberMovie</h1>
            <p className="text-gray-600">Conectando barbearias, freelancers e clientes</p>
          </div>

          <div className="grid md:grid-cols-3 gap-6">
            {userTypes.map(({ type, title, description, icon, color }) => {
              const IconComponent = icon;
              const colors = {
                blue: 'from-blue-500 to-blue-600 hover:from-blue-600 hover:to-blue-700',
                green: 'from-green-500 to-green-600 hover:from-green-600 hover:to-green-700',
                purple: 'from-purple-500 to-purple-600 hover:from-purple-600 hover:to-purple-700',
              };

              return (
                <div
                  key={type}
                  onClick={() => handleTypeSelect(type)}
                  className={`bg-gradient-to-br ${colors[color]} text-white rounded-2xl p-6 cursor-pointer transform transition-all hover:scale-105 hover:shadow-xl`}
                >
                  <IconComponent size={48} className="mb-4" />
                  <h2 className="text-2xl font-bold mb-2">{title}</h2>
                  <p className="text-white/90">{description}</p>
                  <div className="mt-4 flex items-center text-sm font-semibold">
                    <span>Entrar</span>
                    <ArrowRight size={16} className="ml-1" />
                  </div>
                </div>
              );
            })}
          </div>

          <div className="text-center mt-8">
            <p className="text-gray-600">
              Não tem conta?{' '}
              <button onClick={() => setStep('cadastro')} className="text-blue-600 font-semibold hover:underline">
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
      <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 flex items-center justify-center p-4">
        <div className="bg-white rounded-2xl shadow-xl p-8 max-w-md w-full">
          <button
            onClick={() => setStep('escolha')}
            className="text-gray-600 hover:text-gray-900 mb-4 flex items-center"
          >
            ← Voltar
          </button>

          <div className="text-center mb-6">
            <selectedUserType.icon size={48} className="mx-auto mb-2 text-blue-600" />
            <h2 className="text-2xl font-bold">{selectedUserType.title}</h2>
            <p className="text-gray-600 mt-1">{selectedUserType.description}</p>
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
            <button className="text-sm text-blue-600 hover:underline">
              Esqueci minha senha
            </button>
          </div>

          <div className="mt-4 text-center">
            <p className="text-gray-600 text-sm">
              Não tem conta?{' '}
              <button onClick={() => setStep('cadastro')} className="text-blue-600 font-semibold hover:underline">
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
