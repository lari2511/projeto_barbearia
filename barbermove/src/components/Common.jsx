// Componentes reutilizáveis do BarberMove
import React from 'react'
import { Star, MapPin, Clock, Award, User, XCircle, AlertTriangle, CheckCircle, Info, Eye, EyeOff } from 'lucide-react'

export const Button = ({ children, variant = 'primary', fullWidth, onClick, disabled, icon: Icon, className = '' }) => {
  const variants = {
    primary: 'bg-orange-600 hover:bg-orange-700 text-white',
    secondary: 'bg-zinc-800 hover:bg-zinc-700 text-white',
    outline: 'border border-zinc-700 text-zinc-200 hover:bg-zinc-800',
    danger: 'bg-red-600 hover:bg-red-700 text-white',
    success: 'bg-emerald-600 hover:bg-emerald-700 text-white',
  }

  return (
    <button
      onClick={onClick}
      disabled={disabled}
      className={`px-4 py-3 rounded-xl font-medium transition-all flex items-center justify-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed ${variants[variant]} ${fullWidth ? 'w-full' : ''} ${className}`}
    >
      {Icon && <Icon size={20} />}
      {children}
    </button>
  )
}

export const Input = ({ label, error, icon: Icon, ...props }) => {
  const isPasswordInput = props.type === 'password'
  const [showPassword, setShowPassword] = React.useState(false)
  const inputType = isPasswordInput ? (showPassword ? 'text' : 'password') : props.type

  return (
    <div className="mb-4">
      {label && <label className="mb-1 block text-sm font-medium text-zinc-300">{label}</label>}
      <div className="relative">
        {Icon && (
          <div className="absolute left-3 top-1/2 -translate-y-1/2 text-zinc-500">
            <Icon size={20} />
          </div>
        )}
        <input
          {...props}
          type={inputType}
          className={`w-full rounded-xl border bg-black px-4 py-3 text-white outline-none focus:ring-2 focus:ring-orange-500 ${Icon ? 'pl-10' : ''} ${isPasswordInput ? 'pr-12' : ''} ${error ? 'border-red-500' : 'border-zinc-700'}`}
        />

        {isPasswordInput && (
          <button
            type="button"
            onClick={() => setShowPassword((prev) => !prev)}
            className="absolute right-3 top-1/2 -translate-y-1/2 text-zinc-400 hover:text-white"
            aria-label={showPassword ? 'Ocultar senha' : 'Mostrar senha'}
          >
            {showPassword ? <EyeOff size={18} /> : <Eye size={18} />}
          </button>
        )}
      </div>
      {error && <p className="mt-1 text-sm text-red-400">{error}</p>}
    </div>
  )
}

export const FreelancerCard = ({ freelancer, onClick, showDistance = false }) => {
  const { nome, foto_perfil, nivel_tecnico, media_avaliacoes, total_avaliacoes, distancia_km } = freelancer

  return (
    <div
      onClick={onClick}
      className="cursor-pointer rounded-2xl border border-zinc-800/50 bg-[#1e1e24] p-4 shadow-md transition-all hover:shadow-lg"
    >
      <div className="flex items-start gap-3">
        <img
          src={foto_perfil || `https://ui-avatars.com/api/?name=${encodeURIComponent(nome)}&background=random`}
          alt={nome}
          className="h-16 w-16 rounded-full object-cover"
        />
        <div className="flex-1">
          <h3 className="text-lg font-semibold text-white">{nome}</h3>
          <div className="mt-1 flex items-center gap-2 text-sm text-zinc-400">
            <Award size={14} className="text-orange-500" />
            <span className="capitalize">{nivel_tecnico}</span>
          </div>
          {media_avaliacoes != null && (
            <div className="mt-2 flex items-center gap-1">
              <Star size={14} className="fill-yellow-400 text-yellow-400" />
              <span className="text-sm font-medium text-zinc-200">{media_avaliacoes}</span>
              <span className="text-sm text-zinc-500">({total_avaliacoes})</span>
            </div>
          )}
          {showDistance && distancia_km !== undefined && (
            <div className="mt-1 flex items-center gap-1 text-sm text-zinc-400">
              <MapPin size={14} />
              <span>{distancia_km} km</span>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

export const BarbeariaCard = ({ barbearia, onClick, showCadeiras = false }) => {
  const { nome, endereco, distancia_km, media_avaliacoes, total_avaliacoes, cadeiras } = barbearia

  return (
    <div
      onClick={onClick}
      className="cursor-pointer rounded-2xl border border-zinc-800/50 bg-[#1e1e24] p-4 shadow-md transition-all hover:shadow-lg"
    >
      <h3 className="text-lg font-semibold text-white">{nome}</h3>
      <div className="mt-2 flex items-center gap-2 text-sm text-zinc-400">
        <MapPin size={14} />
        <span>{endereco}</span>
      </div>

      {distancia_km !== undefined && distancia_km !== null && (
        <p className="mt-1 text-sm text-zinc-500">{distancia_km} km de distância</p>
      )}

      {media_avaliacoes != null && (
        <div className="mt-2 flex items-center gap-1">
          <Star size={14} className="fill-yellow-400 text-yellow-400" />
          <span className="text-sm font-medium text-zinc-200">{media_avaliacoes}</span>
          <span className="text-sm text-zinc-500">({total_avaliacoes})</span>
        </div>
      )}

      {showCadeiras && Array.isArray(cadeiras) && (
        <p className="mt-2 text-sm font-medium text-emerald-400">{cadeiras.length} cadeira(s) disponível(is)</p>
      )}
    </div>
  )
}

export const RatingStars = ({ rating, onRate, size = 24, readonly = false }) => {
  const [hover, setHover] = React.useState(0)

  return (
    <div className="flex gap-1">
      {[1, 2, 3, 4, 5].map((star) => (
        <Star
          key={star}
          size={size}
          className={`cursor-pointer transition-colors ${(hover || rating) >= star ? 'fill-yellow-400 text-yellow-400' : 'text-zinc-500'}`}
          onClick={() => !readonly && onRate && onRate(star)}
          onMouseEnter={() => !readonly && setHover(star)}
          onMouseLeave={() => !readonly && setHover(0)}
        />
      ))}
    </div>
  )
}

export const Badge = ({ children, variant = 'default' }) => {
  const variants = {
    default: 'bg-zinc-800 text-zinc-200',
    blue: 'bg-blue-500/20 text-blue-300',
    green: 'bg-emerald-500/20 text-emerald-300',
    yellow: 'bg-amber-500/20 text-amber-300',
  }

  return <span className={`rounded-full px-3 py-1 text-sm font-medium ${variants[variant]}`}>{children}</span>
}

export const Toast = ({ message, type = 'info' }) => {
  const config = {
    success: { tone: 'bg-emerald-600', icon: CheckCircle },
    error: { tone: 'bg-red-600', icon: XCircle },
    warning: { tone: 'bg-amber-500', icon: AlertTriangle },
    info: { tone: 'bg-blue-600', icon: Info },
  }

  const current = config[type] || config.info
  const Icon = current.icon
  const text = typeof message === 'string' ? message : 'Mensagem'

  return (
    <div className={`fixed top-4 right-4 z-50 flex max-w-sm items-center gap-3 rounded-xl px-4 py-3 text-white shadow-lg ${current.tone}`}>
      <Icon size={18} className="shrink-0" />
      <span className="text-sm break-words">{text}</span>
    </div>
  )
}

export const Loading = ({ fullScreen = false }) => {
  const spinner = (
    <div className="flex items-center justify-center">
      <div className="h-12 w-12 animate-spin rounded-full border-b-2 border-orange-500" />
    </div>
  )

  if (fullScreen) {
    return (
      <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm">
        {spinner}
      </div>
    )
  }

  return spinner
}

export const AgendamentoCard = ({ agendamento, onClick }) => {
  const { cliente_nome, freelancer_nome, barbearia_nome, servico_nome, data_hora_inicio, status, valor_total } = agendamento

  const statusColors = {
    pendente: 'bg-yellow-100 text-yellow-700',
    confirmado: 'bg-blue-100 text-blue-700',
    concluido: 'bg-green-100 text-green-700',
    cancelado: 'bg-red-100 text-red-700',
  }

  return (
    <div onClick={onClick} className="cursor-pointer rounded-xl border border-zinc-800 bg-zinc-900 p-4 shadow-md transition-all hover:shadow-lg">
      <div className="mb-2 flex items-start justify-between">
        <div>
          <h3 className="font-semibold text-white">{servico_nome}</h3>
          <p className="text-sm text-zinc-400">{barbearia_nome}</p>
        </div>
        <span className={`rounded-full px-3 py-1 text-sm font-medium ${statusColors[status] || statusColors.pendente}`}>
          {status}
        </span>
      </div>

      <div className="mt-2 flex items-center gap-2 text-sm text-zinc-400">
        <Clock size={14} />
        <span>{new Date(data_hora_inicio).toLocaleString('pt-BR')}</span>
      </div>

      <div className="mt-1 flex items-center gap-2 text-sm text-zinc-400">
        <User size={14} />
        <span>{freelancer_nome || cliente_nome}</span>
      </div>

      {valor_total != null && (
        <p className="mt-2 text-lg font-semibold text-green-400">R$ {Number(valor_total).toFixed(2)}</p>
      )}
    </div>
  )
}

export const Modal = ({ isOpen, onClose, title, children }) => {
  if (!isOpen) return null

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4" onClick={onClose}>
      <div
        className="max-h-[90vh] w-full max-w-lg overflow-y-auto rounded-2xl border border-zinc-800 bg-zinc-950"
        onClick={(event) => event.stopPropagation()}
      >
        <div className="sticky top-0 flex items-center justify-between border-b border-zinc-800 bg-zinc-950 p-4">
          <h2 className="text-xl font-bold text-white">{title}</h2>
          <button onClick={onClose} className="text-zinc-400 hover:text-white" aria-label="Fechar modal">
            <XCircle size={24} />
          </button>
        </div>
        <div className="p-4 text-zinc-300">{children}</div>
      </div>
    </div>
  )
}
