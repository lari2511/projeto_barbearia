// Pilha simples de handlers do botao fisico/gesto de voltar do Android.
// Cada tela ativa registra um handler que sabe desfazer "um passo" da
// navegacao interna dela; se devolver false, significa "nao tenho mais
// nada pra desfazer aqui", e quem chamou decide o que fazer (ex.: minimizar
// o app quando estiver na tela raiz).
let stack = [];

export function pushBackHandler(handler) {
  stack.push(handler);
  return () => {
    stack = stack.filter((h) => h !== handler);
  };
}

export function handleBackButton() {
  for (let i = stack.length - 1; i >= 0; i -= 1) {
    if (stack[i]() !== false) return true;
  }
  return false;
}
