import { useEffect } from 'react';
import { pushBackHandler } from './backButtonStack';

// Registra `handler` como o responsavel por tratar o botao fisico/gesto de
// voltar do Android enquanto o componente estiver montado. `handler` deve
// retornar false quando nao ha mais nada a desfazer nesta tela.
export function useBackHandler(handler, deps) {
  useEffect(() => {
    return pushBackHandler(handler);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps);
}
