import React, { useState } from 'react';
import { Star } from 'lucide-react';

/**
 * Componente de Avaliação Reutilizável
 * Não fecha ao clicar nas estrelas - apenas seleciona
 */
export default function RatingComponent({ 
  onRate, 
  defaultRating = 0, 
  targetName = '', 
  color = 'yellow',
  showComment = true 
}) {
  const [rating, setRating] = useState(defaultRating);
  const [comment, setComment] = useState('');
  const [hoveredRating, setHoveredRating] = useState(0);

  const colorClasses = {
    yellow: {
      text: 'text-yellow-400',
      hover: 'hover:text-yellow-300',
      bg: 'bg-yellow-500/20',
      border: 'border-yellow-500/30'
    },
    cyan: {
      text: 'text-cyan-400',
      hover: 'hover:text-cyan-300',
      bg: 'bg-cyan-500/20',
      border: 'border-cyan-500/30'
    },
    purple: {
      text: 'text-purple-400',
      hover: 'hover:text-purple-300',
      bg: 'bg-purple-500/20',
      border: 'border-purple-500/30'
    },
    orange: {
      text: 'text-orange-400',
      hover: 'hover:text-orange-300',
      bg: 'bg-orange-500/20',
      border: 'border-orange-500/30'
    }
  };

  const currentColor = colorClasses[color] || colorClasses.yellow;

  const handleRate = (value) => {
    setRating(value);
    // NÃO fecha, apenas registra
  };

  const handleSubmit = () => {
    if (onRate && rating > 0) {
      onRate({
        nota: rating,
        comentario: comment
      });
      // Resetar após envio
      setRating(0);
      setComment('');
    }
  };

  return (
    <div className={`p-4 rounded-lg border ${currentColor.bg} ${currentColor.border}`}>
      {/* Título com nome alvo */}
      <div className="mb-3">
        <p className="text-xs text-zinc-400">Avaliando:</p>
        <p className="font-bold text-sm text-white">{targetName || 'Serviço'}</p>
      </div>

      {/* Estrelas */}
      <div className="flex items-center gap-2 mb-3">
        {[1, 2, 3, 4, 5].map(n => (
          <button
            key={n}
            onClick={() => handleRate(n)}
            onMouseEnter={() => setHoveredRating(n)}
            onMouseLeave={() => setHoveredRating(0)}
            className={`text-3xl transition-all transform ${
              hoveredRating >= n || rating >= n
                ? `${currentColor.text} scale-125`
                : 'text-zinc-700'
            } ${currentColor.hover} cursor-pointer`}
            type="button"
          >
            {hoveredRating >= n || rating >= n ? '★' : '☆'}
          </button>
        ))}
      </div>

      {/* Rating display */}
      {rating > 0 && (
        <p className="text-xs text-zinc-400 mb-3">
          {rating} de 5 estrelas selecionadas
        </p>
      )}

      {/* Comentário */}
      {showComment && (
        <textarea
          className="w-full bg-black/40 rounded-lg p-2 border border-zinc-700 text-xs placeholder-zinc-600 focus:border-zinc-500 outline-none mb-3 resize-none"
          placeholder="Deixe um comentário (opcional)"
          value={comment}
          onChange={(e) => setComment(e.target.value)}
          rows="2"
        />
      )}

      {/* Botão enviar */}
      <button
        onClick={handleSubmit}
        disabled={rating === 0}
        className={`w-full py-2 rounded-lg text-xs font-bold transition-all ${
          rating > 0
            ? `bg-gradient-to-r ${
                color === 'yellow' ? 'from-yellow-500 to-orange-500' :
                color === 'cyan' ? 'from-cyan-500 to-blue-500' :
                color === 'purple' ? 'from-purple-500 to-pink-500' :
                'from-orange-500 to-red-500'
              } text-black hover:shadow-lg cursor-pointer`
            : 'bg-zinc-700 text-zinc-400 cursor-not-allowed opacity-50'
        }`}
      >
        ✅ Enviar Avaliação
      </button>
    </div>
  );
}
