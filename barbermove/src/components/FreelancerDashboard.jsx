// Dashboard do Freelancer - BarberMovie
import React, { useState, useEffect, useCallback } from 'react';
import ScreenWrapper from './ScreenWrapper';
import { 
  MapPin, Upload, Image as ImageIcon, Star, 
  DollarSign, Pause, Play, Check, X, Calendar,
  TrendingUp, Award, Users
} from 'lucide-react';
import { useApp } from '../contexts/AppContext';
import { Button, Input, Badge, RatingStars, Modal, Loading, AgendamentoCard, BarbeariaCard } from './Common';

export default function FreelancerDashboard() {
  const { apiRequest, notify, user } = useApp();
  const [view, setView] = useState('home'); // home, portfolio, solicitacoes, agendamentos, ganhos
  const [_freelancer, _setFreelancer] = useState(null);
  const [portfolio, setPortfolio] = useState([]);
  const [solicitacoes, _setSolicitacoes] = useState([]);
  const [barbearias, setBarbearias] = useState([]);
  const [loading, setLoading] = useState(true);
  const [statusPausado, setStatusPausado] = useState(false);

  const loadFreelancerData = useCallback(async () => {
    try {
      setLoading(true);
      // Aqui você precisaria ter um endpoint que retorna dados do freelancer
      // Por enquanto, vamos simular
      
      const portfolioData = await apiRequest('/api/v1/freelancer/meu-portfolio');
      setPortfolio(portfolioData);
      
      setLoading(false);
    } catch (error) {
      notify(error.message, 'error');
      setLoading(false);
    }
  }, [apiRequest, notify]);

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    loadFreelancerData();
  }, [loadFreelancerData]);

  const togglePausar = async () => {
    try {
      await apiRequest('/api/v1/freelancer/pausar', {
        method: 'PATCH',
        body: JSON.stringify({ pausar: !statusPausado })
      });
      
      setStatusPausado(!statusPausado);
      notify(statusPausado ? 'Atendimentos retomados' : 'Atendimentos pausados', 'success');
    } catch (error) {
      notify(error.message, 'error');
    }
  };

  const buscarBarbeariasProximas = async () => {
    try {
      const data = await apiRequest('/api/v1/barbearias/proximas?raio_km=10');
      const lista = Array.isArray(data?.barbearias) ? data.barbearias : Array.isArray(data) ? data : [];
      if (lista.length > 0) {
        setBarbearias(lista);
        return;
      }

      const fallback = await apiRequest('/api/v1/barbearias/todas-aprovadas');
      const fallbackLista = Array.isArray(fallback?.barbearias) ? fallback.barbearias : Array.isArray(fallback) ? fallback : [];
      setBarbearias(fallbackLista);
    } catch (error) {
      notify(error.message, 'error');
    }
  };

  if (loading) return <Loading fullScreen />;

  // HOME
  if (view === 'home') {
    return (
      <ScreenWrapper>
      <div className="min-h-screen bg-black text-white pb-20">
        <div className="bg-gradient-to-r from-zinc-900 to-zinc-950 text-white p-4 border-b border-zinc-800">
          <div className="flex justify-between items-center">
            <div>
              <h1 className="text-2xl font-black">Olá, {user?.nome || 'Freelancer'}!</h1>
              <p className="text-zinc-400">Pronto para atender?</p>
            </div>
            <Button 
              variant={statusPausado ? 'success' : 'secondary'}
              onClick={togglePausar}
              icon={statusPausado ? Play : Pause}
            >
              {statusPausado ? 'Retomar' : 'Pausar'}
            </Button>
          </div>
        </div>

        <div className="p-4 space-y-4">
          {/* Cards de resumo */}
          <div className="grid grid-cols-2 gap-4">
            <div className="bg-[#1e1e24] rounded-2xl p-4 shadow-md border border-zinc-800/50">
              <div className="flex items-center gap-2 text-orange-400 mb-2">
                <Calendar size={20} />
                <span className="text-sm font-medium">Hoje</span>
              </div>
              <p className="text-2xl font-bold">0</p>
              <p className="text-sm text-zinc-400">atendimentos</p>
            </div>

            <div className="bg-[#1e1e24] rounded-2xl p-4 shadow-md border border-zinc-800/50">
              <div className="flex items-center gap-2 text-emerald-400 mb-2">
                <DollarSign size={20} />
                <span className="text-sm font-medium">Ganhos</span>
              </div>
              <p className="text-2xl font-bold">R$ 0</p>
              <p className="text-sm text-zinc-400">no mês</p>
            </div>
          </div>

          {/* Solicitações pendentes */}
          <div className="bg-[#1e1e24] rounded-2xl p-4 shadow-md border border-zinc-800/50">
            <h2 className="font-bold text-lg mb-3 text-white">Solicitações Pendentes</h2>
            {solicitacoes.length === 0 ? (
              <p className="text-zinc-500 text-center py-8">Nenhuma solicitação no momento</p>
            ) : (
              <div className="space-y-3">
                {solicitacoes.map(sol => (
                  <SolicitacaoCard key={sol.id} solicitacao={sol} />
                ))}
              </div>
            )}
          </div>

          {/* Barbearias próximas */}
          <div className="bg-[#1e1e24] rounded-2xl p-4 shadow-md border border-zinc-800/50">
            <div className="flex justify-between items-center mb-3">
              <h2 className="font-bold text-lg text-white">Barbearias Próximas</h2>
              <Button variant="outline" onClick={buscarBarbeariasProximas}>
                <MapPin size={16} />
                Buscar
              </Button>
            </div>
            
            {barbearias.length === 0 ? (
              <p className="text-zinc-500 text-center py-8">
                Clique em "Buscar" para ver barbearias próximas
              </p>
            ) : (
              <div className="space-y-3">
                {barbearias.map(barb => (
                  <BarbeariaCard key={barb.id} barbearia={barb} showCadeiras />
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Bottom Navigation */}
        <BottomNav active="home" onChange={setView} type="freelancer" />
      </div>
    );
  }

  // PORTFÓLIO
  if (view === 'portfolio') {
    return (
      <PortfolioView 
        portfolio={portfolio} 
        onBack={() => setView('home')}
        onUpload={(foto) => {
          setPortfolio([...portfolio, foto]);
          notify('Foto adicionada ao portfólio!', 'success');
        }}
      />
    );
  }

  // GANHOS
  if (view === 'ganhos') {
    return <GanhosView onBack={() => setView('home')} />;
  }

  return null;
}

// Componente de solicitação de atendimento
function SolicitacaoCard({ solicitacao }) {
  const { apiRequest, notify } = useApp();
  const [respondendo, setRespondendo] = useState(false);

  const responder = async (aceitar) => {
    setRespondendo(true);
    try {
      await apiRequest('/api/v1/freelancer/aceitar-atendimento', {
        method: 'POST',
        body: JSON.stringify({
          chamado_id: solicitacao.id,
          aceitar
        })
      });
      
      notify(aceitar ? 'Atendimento aceito!' : 'Atendimento recusado', 'success');
    } catch (error) {
      notify(error.message, 'error');
    } finally {
      setRespondendo(false);
    }
  };

  return (
    <div className="border border-gray-200 rounded-lg p-4">
      <div className="flex justify-between items-start mb-2">
        <div>
          <h3 className="font-semibold">{solicitacao.cliente_nome}</h3>
          <p className="text-sm text-gray-600">{solicitacao.servico_nome}</p>
        </div>
        <span className="text-lg font-bold text-green-600">
          R$ {solicitacao.valor?.toFixed(2)}
        </span>
      </div>
      
      <p className="text-sm text-gray-600 mb-2">
        📍 {solicitacao.barbearia_nome} - {solicitacao.distancia} km
      </p>
      
      <p className="text-sm text-gray-600 mb-3">
        🕐 {new Date(solicitacao.data_hora).toLocaleString('pt-BR')}
      </p>
      
      <div className="flex gap-2">
        <Button 
          variant="success" 
          fullWidth 
          icon={Check}
          onClick={() => responder(true)}
          disabled={respondendo}
        >
          Aceitar
        </Button>
        <Button 
          variant="danger" 
          fullWidth 
          icon={X}
          onClick={() => responder(false)}
          disabled={respondendo}
        >
          Recusar
        </Button>
        </div>
      </div>
      </ScreenWrapper>
    );
}

// View de Portfólio
function PortfolioView({ portfolio, onBack, onUpload }) {
  const { apiRequest, notify } = useApp();
  const [uploading, setUploading] = useState(false);
  const [selectedType, setSelectedType] = useState('corte');
  const [imageUrl, setImageUrl] = useState('');
  const [descricao, setDescricao] = useState('');

  const tipos = ['corte', 'barba', 'sobrancelha', 'facial'];

  const handleUpload = async (e) => {
    e.preventDefault();
    setUploading(true);
    
    try {
      const data = await apiRequest('/api/v1/freelancer/portfolio', {
        method: 'POST',
        body: JSON.stringify({
          tipo_servico: selectedType,
          url_imagem: imageUrl,
          descricao
        })
      });
      
      onUpload(data);
      setImageUrl('');
      setDescricao('');
    } catch (error) {
      notify(error.message, 'error');
    } finally {
      setUploading(false);
    }
  };

  const portfolioPorTipo = tipos.reduce((acc, tipo) => {
    acc[tipo] = portfolio.filter(p => p.tipo_servico === tipo);
    return acc;
  }, {});

  return (
    <div className="min-h-screen bg-black">
      <div className="bg-zinc-950/80 border-b border-zinc-800 sticky top-0 z-10">
        <div className="p-4 flex items-center gap-3">
          <button onClick={onBack} className="text-zinc-300">←</button>
          <h1 className="text-xl font-bold text-white">Meu Portfólio</h1>
        </div>
      </div>

      <div className="p-4 space-y-6">
        {/* Upload de nova foto */}
        <div className="bg-zinc-900 rounded-xl p-4 shadow-md border border-zinc-800">
          <h2 className="font-bold mb-3 text-white">Adicionar Foto</h2>
          <form onSubmit={handleUpload} className="space-y-3">
            <div>
              <label className="block text-sm font-medium mb-1">Tipo de Serviço</label>
              <select 
                value={selectedType}
                onChange={(e) => setSelectedType(e.target.value)}
                className="w-full px-4 py-2 border rounded-lg"
              >
                {tipos.map(tipo => (
                  <option key={tipo} value={tipo}>{tipo.charAt(0).toUpperCase() + tipo.slice(1)}</option>
                ))}
              </select>
            </div>

            <Input 
              label="URL da Imagem"
              value={imageUrl}
              onChange={(e) => setImageUrl(e.target.value)}
              placeholder="https://..."
              required
            />

            <Input 
              label="Descrição (opcional)"
              value={descricao}
              onChange={(e) => setDescricao(e.target.value)}
              placeholder="Ex: Corte degradê..."
            />

            <Button type="submit" fullWidth icon={Upload} disabled={uploading}>
              {uploading ? 'Enviando...' : 'Adicionar Foto'}
            </Button>
          </form>
        </div>

        {/* Galeria por tipo */}
        {tipos.map(tipo => (
          <div key={tipo} className="bg-zinc-900 rounded-xl p-4 shadow-md border border-zinc-800">
            <h3 className="font-bold mb-3 capitalize text-white">{tipo}</h3>
            <div className="grid grid-cols-2 gap-3">
              {portfolioPorTipo[tipo]?.length > 0 ? (
                portfolioPorTipo[tipo].map(foto => (
                  <div key={foto.id} className="relative aspect-square rounded-lg overflow-hidden">
                    <img 
                      src={foto.url_imagem} 
                      alt={foto.descricao}
                      className="w-full h-full object-cover"
                    />
                    {foto.descricao && (
                      <div className="absolute bottom-0 left-0 right-0 bg-black/50 text-white p-2 text-xs">
                        {foto.descricao}
                      </div>
                    )}
                  </div>
                ))
              ) : (
                <div className="col-span-2 text-center py-8 text-zinc-500">
                  Nenhuma foto ainda
                </div>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

// View de Ganhos
function GanhosView({ onBack }) {
  const { apiRequest } = useApp();
  const [relatorio, setRelatorio] = useState(null);
  const [loading, setLoading] = useState(true);

  const loadRelatorio = useCallback(async () => {
    try {
      const data = await apiRequest('/api/v1/freelancer/comissoes/relatorio');
      setRelatorio(data);
    } catch (_error) {
      // Erro ao carregar relatório
    } finally {
      setLoading(false);
    }
  }, [apiRequest]);

  useEffect(() => {
    loadRelatorio();
  }, [loadRelatorio]);

  if (loading) return <Loading fullScreen />;

  return (
    <div className="min-h-screen bg-black">
      <div className="bg-zinc-950/80 border-b sticky top-0 z-10">
        <div className="p-4 flex items-center gap-3">
          <button onClick={onBack} className="text-zinc-300">←</button>
          <h1 className="text-xl font-bold text-white">Ganhos e Comissões</h1>
        </div>
      </div>

      <div className="p-4 space-y-4">
        {/* Cards de resumo */}
        <div className="grid grid-cols-2 gap-4">
          <div className="bg-zinc-900 rounded-xl p-4 shadow-md border border-zinc-800">
            <div className="flex items-center gap-2 text-blue-600 mb-2">
              <TrendingUp size={20} />
              <span className="text-sm font-medium">Ganhos Brutos</span>
            </div>
            <p className="text-2xl font-bold">R$ {relatorio?.ganhos_brutos?.toFixed(2) || '0.00'}</p>
          </div>

          <div className="bg-zinc-900 rounded-xl p-4 shadow-md border border-zinc-800">
            <div className="flex items-center gap-2 text-red-600 mb-2">
              <DollarSign size={20} />
              <span className="text-sm font-medium">Comissões</span>
            </div>
            <p className="text-2xl font-bold">R$ {relatorio?.total_comissoes?.toFixed(2) || '0.00'}</p>
          </div>
        </div>

        <div className="bg-gradient-to-r from-green-500 to-green-600 text-white rounded-xl p-6 shadow-md">
          <p className="text-sm opacity-90 mb-1">Ganhos Líquidos</p>
          <p className="text-3xl font-bold">R$ {relatorio?.ganhos_liquidos?.toFixed(2) || '0.00'}</p>
        </div>

        {/* Detalhes */}
        <div className="bg-zinc-900 rounded-xl p-4 shadow-md border border-zinc-800">
          <h2 className="font-bold mb-3 text-white">Detalhes</h2>
          <div className="space-y-2 text-sm">
            <div className="flex justify-between">
              <span className="text-zinc-400">Total de atendimentos:</span>
              <span className="font-semibold text-white">{relatorio?.total_atendimentos || 0}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-zinc-400">Via BarberMovie:</span>
              <span className="font-semibold">{relatorio?.total_atendimentos_app || 0}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-600">Clientes próprios:</span>
              <span className="font-semibold">{relatorio?.total_atendimentos_proprios || 0}</span>
            </div>
          </div>
        </div>

        <p className="text-xs text-gray-500 text-center">
          💡 Comissão de 4% apenas sobre atendimentos via app
        </p>
      </div>
    </div>
  );
}

// Bottom Navigation
function BottomNav({ active, onChange, type }) {
  const items = {
    freelancer: [
      { id: 'home', label: 'Início', icon: '🏠' },
      { id: 'portfolio', label: 'Portfólio', icon: '📸' },
      { id: 'agendamentos', label: 'Agenda', icon: '📅' },
      { id: 'ganhos', label: 'Ganhos', icon: '💰' },
    ],
  };

  return (
    <div className="bm-bottom-nav fixed bottom-0 left-0 right-0 shadow-lg">
      <div className="flex justify-around py-2">
        {items[type].map(item => (
          <button
            key={item.id}
            onClick={() => onChange(item.id)}
            data-active={active === item.id}
            className={`bm-bottom-nav-btn flex flex-col items-center gap-1 px-4 py-2 ${
              active === item.id ? 'text-orange-500' : 'text-zinc-500'
            }`}
          >
            <span className="text-xl">{item.icon}</span>
            <span>{item.label}</span>
          </button>
        ))}
      </div>
    </div>
  );
}
