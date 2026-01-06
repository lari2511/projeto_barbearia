/**
 * Color Coding para Status de Agendamentos (StatusAgendamento)
 * Localização: barbermove/src/utils/statusColors.js
 * 
 * Define as cores CSS e labels para cada status no frontend
 */

export const STATUS_COLORS = {
  'pendente': {
    bg: '#FEF3C7',      // Amber 100 (light yellow)
    border: '#F59E0B',  // Amber 500 (darker yellow)
    text: '#92400E',    // Amber 900 (dark text)
    badge: 'bg-yellow-100 text-yellow-800 border-yellow-300',
    label: 'Pendente',
    icon: '⏳',
    description: 'Aguardando aceite do barbeiro'
  },
  
  'confirmado': {
    bg: '#DCFCE7',      // Green 100
    border: '#22C55E',  // Green 500
    text: '#166534',    // Green 900
    badge: 'bg-green-100 text-green-800 border-green-300',
    label: 'Confirmado',
    icon: '✅',
    description: 'Barbeiro aceitou'
  },
  
  'concluido': {
    bg: '#E0E7FF',      // Indigo 100
    border: '#6366F1',  // Indigo 500
    text: '#312E81',    // Indigo 900
    badge: 'bg-indigo-100 text-indigo-800 border-indigo-300',
    label: 'Concluído',
    icon: '✨',
    description: 'Serviço realizado'
  },
  
  'cancelado': {
    bg: '#FEE2E2',      // Red 100
    border: '#EF4444',  // Red 500
    text: '#7F1D1D',    // Red 900
    badge: 'bg-red-100 text-red-800 border-red-300',
    label: 'Cancelado',
    icon: '❌',
    description: 'Agendamento cancelado'
  }
};

/**
 * Componente React para exibir badge de status
 */
export const StatusBadge = ({ status }) => {
  const color = STATUS_COLORS[status] || STATUS_COLORS['pendente'];
  
  return (
    <span
      className={`inline-flex items-center gap-1 px-3 py-1 rounded-full text-sm font-medium ${color.badge}`}
      title={color.description}
    >
      <span>{color.icon}</span>
      <span>{color.label}</span>
    </span>
  );
};

/**
 * Componente React para linha de status com barra de progresso
 */
export const StatusProgress = ({ status }) => {
  const statusOrder = ['pendente', 'confirmado', 'concluido'];
  const currentIndex = statusOrder.indexOf(status);
  const progress = ((currentIndex + 1) / statusOrder.length) * 100;
  
  return (
    <div className="w-full">
      {/* Barra de progresso */}
      <div className="w-full bg-gray-200 rounded-full h-2 mb-2 overflow-hidden">
        <div
          className="bg-gradient-to-r from-yellow-400 via-green-400 to-blue-500 h-full transition-all duration-300"
          style={{ width: `${progress}%` }}
        />
      </div>
      
      {/* Passos */}
      <div className="flex justify-between text-xs text-gray-600 mb-2">
        <span className={currentIndex >= 0 ? 'text-yellow-600 font-bold' : ''}>Pendente</span>
        <span className={currentIndex >= 1 ? 'text-green-600 font-bold' : ''}>Confirmado</span>
        <span className={currentIndex >= 2 ? 'text-blue-600 font-bold' : ''}>Concluído</span>
      </div>
    </div>
  );
};

/**
 * Hook para formatar status
 */
export const useStatusDisplay = (status) => {
  const color = STATUS_COLORS[status] || STATUS_COLORS['pendente'];
  
  return {
    ...color,
    className: `px-3 py-1 rounded-full font-medium`,
    style: {
      backgroundColor: color.bg,
      borderColor: color.border,
      color: color.text,
      border: `2px solid ${color.border}`
    }
  };
};

/**
 * Exemplo de uso no componente:
 * 
 * import { StatusBadge, StatusProgress, useStatusDisplay } from '@/utils/statusColors';
 * 
 * export function AgendamentoCard({ agendamento }) {
 *   return (
 *     <div className="border rounded-lg p-4">
 *       <StatusBadge status={agendamento.status} />
 *       <StatusProgress status={agendamento.status} />
 *       
 *       <div style={useStatusDisplay(agendamento.status).style}>
 *         Status customizado
 *       </div>
 *     </div>
 *   );
 * }
 */

/**
 * Maquina de estados: transições válidas
 */
export const VALID_TRANSITIONS = {
  'pendente': ['confirmado', 'cancelado'],      // Pode ser confirmado ou cancelado
  'confirmado': ['concluido', 'cancelado'],     // Pode ser concluído ou cancelado
  'concluido': [],                               // Terminal
  'cancelado': []                                // Terminal
};

export const canTransition = (fromStatus, toStatus) => {
  return VALID_TRANSITIONS[fromStatus]?.includes(toStatus) || false;
};

/**
 * Tradução de status
 */
export const translateStatus = (status) => {
  const translations = {
    'pendente': 'Pendente',
    'confirmado': 'Confirmado',
    'concluido': 'Concluído',
    'cancelado': 'Cancelado'
  };
  return translations[status] || status;
};
