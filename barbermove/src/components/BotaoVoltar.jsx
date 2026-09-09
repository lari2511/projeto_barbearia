import React from 'react';
import { ArrowLeft } from 'lucide-react';
import { handleBackButton } from '../utils/backButtonStack';

// Botao de voltar global do BarberMove.
//
// So a flecha (<-), discreto, canto superior esquerdo. Sem texto "Voltar".
// Por padrao dispara o MESMO fluxo do botao fisico/gesto de voltar do Android
// (handleBackButton), respeitando a hierarquia de navegacao ja registrada por
// cada tela via useBackHandler. Passe `onClick` apenas quando a tela nao usa
// esse mecanismo (ex.: telas cheias fora do dashboard).
//
// Nao renderize este componente quando nao ha para onde voltar (tela raiz do
// perfil). Quem usa decide a visibilidade.
export default function BotaoVoltar({ onClick, className = '', label = 'Voltar' }) {
  const handleClick = (event) => {
    if (event && typeof event.preventDefault === 'function') {
      event.preventDefault();
    }

    if (typeof onClick === 'function') {
      onClick();
      return;
    }

    handleBackButton();
  };

  return (
    <button
      type="button"
      onClick={handleClick}
      aria-label={label}
      title={label}
      className={
        'flex-shrink-0 inline-flex items-center justify-center h-9 w-9 -ml-1 rounded-full ' +
        'text-zinc-300 hover:text-white hover:bg-white/10 active:bg-white/15 ' +
        'transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-orange-500/50 ' +
        className
      }
    >
      <ArrowLeft size={22} strokeWidth={2.5} />
    </button>
  );
}
