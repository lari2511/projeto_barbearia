// Componentes reutilizáveis do BarberMovie
import React from 'react';
import { Star, MapPin, Clock, Award, User } from 'lucide-react';

// Botão padrão
export const Button = ({ children, variant = 'primary', fullWidth, onClick, disabled, icon: Icon, className = '' }) => {
  const variants = {
    primary: 'bg-blue-600 hover:bg-blue-700 text-white',
    secondary: 'bg-gray-600 hover:bg-gray-700 text-white',
    outline: 'border-2 border-blue-600 text-blue-600 hover:bg-blue-50',
    danger: 'bg-red-600 hover:bg-red-700 text-white',
    success: 'bg-green-600 hover:bg-green-700 text-white',
  };

  return (
    <button
      onClick={onClick}
      disabled={disabled}
      className={`px-4 py-2 rounded-lg font-medium transition-all flex items-center justify-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed ${variants[variant]} ${fullWidth ? 'w-full' : ''} ${className}`}
    >
      {Icon && <Icon size={20} />}
      {children}
    </button>
  );
};

// Input com label
export const Input = ({ label, error, icon: Icon, ...props }) => {
  return (
    <div className="mb-4">
      {label && <label className="block text-sm font-medium mb-1 text-gray-700">{label}</label>}
      <div className="relative">
        {Icon && (
          <div className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400">
            <Icon size={20} />
          </div>
        )}
        <input
          {...props}
          className={`w-full px-4 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent ${Icon ? 'pl-10' : ''} ${error ? 'border-red-500' : 'border-gray-300'}`}
        />
      </div>
      {error && <p className="text-red-500 text-sm mt-1">{error}</p>}
    </div>
  );
};

// Card de freelancer
export const FreelancerCard = ({ freelancer, onClick, showDistance = false }) => {
  const { nome, foto_perfil, nivel_tecnico, media_avaliacoes, total_avaliacoes, distancia_km } = freelancer;

  return (
    <div 
      onClick={onClick}
      className="bg-white rounded-xl shadow-md p-4 cursor-pointer hover:shadow-lg transition-all border border-gray-200"
    >
      <div className="flex items-start gap-3">
        <img 
          src={foto_perfil || `https://ui-avatars.com/api/?name=${encodeURIComponent(nome)}&background=random`}
          alt={nome}
          className="w-16 h-16 rounded-full object-cover"
        />
        <div className="flex-1">
          <h3 className="font-semibold text-lg">{nome}</h3>
          <div className="flex items-center gap-2 text-sm text-gray-600 mt-1">
            <Award size={14} className="text-blue-600" />
            <span className="capitalize">{nivel_tecnico}</span>
          </div>
          
          {media_avaliacoes && (
            <div className="flex items-center gap-1 mt-2">
              <Star size={14} className="fill-yellow-400 text-yellow-400" />
              <span className="font-medium text-sm">{media_avaliacoes}</span>
              <span className="text-gray-500 text-sm">({total_avaliacoes})</span>
            </div>
          )}
          
          {showDistance && distancia_km !== undefined && (
            <div className="flex items-center gap-1 text-sm text-gray-600 mt-1">
              <MapPin size={14} />
              <span>{distancia_km} km</span>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

// Card de barbearia
export const BarbeariaCard = ({ barbearia, onClick, showCadeiras = false }) => {
  const { nome, endereco, distancia_km, media_avaliacoes, total_avaliacoes, cadeiras } = barbearia;

  return (
    <div 
      onClick={onClick}
      className="bg-white rounded-xl shadow-md p-4 cursor-pointer hover:shadow-lg transition-all border border-gray-200"
    >
      <h3 className="font-semibold text-lg">{nome}</h3>
      <div className="flex items-center gap-2 text-sm text-gray-600 mt-2">
        <MapPin size={14} />
        <span>{endereco}</span>
      </div>
      
      {distancia_km && (
        <p className="text-sm text-gray-500 mt-1">{distancia_km} km de distância</p>
      )}
      
      {media_avaliacoes && (
        <div className="flex items-center gap-1 mt-2">
          <Star size={14} className="fill-yellow-400 text-yellow-400" />
          <span className="font-medium text-sm">{media_avaliacoes}</span>
          <span className="text-gray-500 text-sm">({total_avaliacoes})</span>
        </div>
      )}
      
      {showCadeiras && cadeiras && (
        <p className="text-sm text-green-600 mt-2 font-medium">
          {cadeiras.length} cadeira(s) disponível(is)
        </p>
      )}
    </div>
  );
};

// Sistema de avaliação (estrelas)
export const RatingStars = ({ rating, onRate, size = 24, readonly = false }) => {
  const [hover, setHover] = React.useState(0);

  return (
    <div className="flex gap-1">
      {[1, 2, 3, 4, 5].map((star) => (
        <Star
          key={star}
          size={size}
          className={`cursor-pointer transition-colors ${
            (hover || rating) >= star
              ? 'fill-yellow-400 text-yellow-400'
              : 'text-gray-300'
          }`}
          onClick={() => !readonly && onRate && onRate(star)}
          onMouseEnter={() => !readonly && setHover(star)}
          onMouseLeave={() => !readonly && setHover(0)}
        />
      ))}
    </div>
  );
};

// Badge de especialidade
export const Badge = ({ children, variant = 'default' }) => {
  const variants = {
    default: 'bg-gray-100 text-gray-700',
    blue: 'bg-blue-100 text-blue-700',
    green: 'bg-green-100 text-green-700',
    yellow: 'bg-yellow-100 text-yellow-700',
  };

  return (
    <span className={`px-3 py-1 rounded-full text-sm font-medium ${variants[variant]}`}>
      {children}
    </span>
  );
};

// Toast de notificação
export const Toast = ({ message, type = 'info', onClose }) => {
  const types = {
    success: 'bg-green-500',
    error: 'bg-red-500',
    info: 'bg-blue-500',
    warning: 'bg-yellow-500',
  };

  // Converte QUALQUER coisa para string segura
  let msgText = '';
  try {
    if (message === null || message === undefined) {
      msgText = 'Erro desconhecido';
    } else if (typeof message === 'string') {
      msgText = message;
    } else if (typeof message === 'object') {
      msgText = JSON.stringify(message);
      if (msgText === '{}' || msgText.includes('[object Object]')) {
        msgText = 'Erro ao processar requisição';
      }
    } else {
      msgText = String(message);
    }
  } catch (_e) {
    msgText = 'Erro ao exibir mensagem';
  }

  // Remove [object Object] se aparecer
  msgText = msgText.replace(/\[object Object\]/g, 'erro no servidor');

  return (
    <div className={`fixed top-4 right-4 ${types[type]} text-white px-6 py-3 rounded-lg shadow-lg flex items-center gap-3 z-50 animate-slide-in max-w-sm`}>
      <span className="text-sm break-words">{msgText}</span>
      {onClose && (
        <button onClick={onClose} className="ml-2 hover:bg-white/20 rounded p-1 flex-shrink-0">
          ×
        </button>
      )}
    </div>
  );
};

// Loading spinner
export const Loading = ({ fullScreen = false }) => {
  const spinner = (
    <div className="flex items-center justify-center">
      <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
    </div>
  );

  if (fullScreen) {
    return (
      <div className="fixed inset-0 bg-white/80 backdrop-blur-sm flex items-center justify-center z-50">
        {spinner}
      </div>
    );
  }

  return spinner;
};

// Card de agendamento
export const AgendamentoCard = ({ agendamento, onClick }) => {
  const { cliente_nome, freelancer_nome, barbearia_nome, servico_nome, data_hora_inicio, status, valor_total } = agendamento;

  const statusColors = {
    pendente: 'bg-yellow-100 text-yellow-700',
    confirmado: 'bg-blue-100 text-blue-700',
    concluido: 'bg-green-100 text-green-700',
    cancelado: 'bg-red-100 text-red-700',
  };

  return (
    <div 
      onClick={onClick}
      className="bg-white rounded-xl shadow-md p-4 cursor-pointer hover:shadow-lg transition-all border border-gray-200"
    >
      <div className="flex justify-between items-start mb-2">
        <div>
          <h3 className="font-semibold">{servico_nome}</h3>
          <p className="text-sm text-gray-600">{barbearia_nome}</p>
        </div>
        <span className={`px-3 py-1 rounded-full text-sm font-medium ${statusColors[status]}`}>
          {status}
        </span>
      </div>
      
      <div className="flex items-center gap-2 text-sm text-gray-600 mt-2">
        <Clock size={14} />
        <span>{new Date(data_hora_inicio).toLocaleString('pt-BR')}</span>
      </div>
      
      <div className="flex items-center gap-2 text-sm text-gray-600 mt-1">
        <User size={14} />
        <span>{freelancer_nome || cliente_nome}</span>
      </div>
      
      {valor_total && (
        <p className="text-lg font-semibold text-blue-600 mt-2">
          R$ {valor_total.toFixed(2)}
        </p>
      )}
    </div>
  );
};

// Modal genérico
export const Modal = ({ isOpen, onClose, title, children }) => {
  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4" onClick={onClose}>
      <div className="bg-white rounded-2xl max-w-lg w-full max-h-[90vh] overflow-y-auto" onClick={(e) => e.stopPropagation()}>
        <div className="sticky top-0 bg-white border-b p-4 flex justify-between items-center">
          <h2 className="text-xl font-bold">{title}</h2>
          <button onClick={onClose} className="text-gray-500 hover:text-gray-700">
            <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>
        <div className="p-4">
          {children}
        </div>
      </div>
    </div>
  );
};
