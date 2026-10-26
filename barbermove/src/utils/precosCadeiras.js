// Tabela progressiva das cadeiras — espelho de app/routes_assinaturas.py, só para exibição.
// O valor cobrado vem sempre do servidor (/api/v1/cobrancas/cadeiras/orcamento e a própria cobrança).
// O preço é o da posição da cadeira no total contratado (a 6ª em diante custa o mínimo).
export const PRECOS_CADEIRAS = [47.9, 37.9, 30.9, 23.9, 19.9];
export const PRECO_CADEIRA_MINIMO = 17.9;

export function precoCadeiraPorPosicao(posicao) {
  if (posicao <= 1) return PRECOS_CADEIRAS[0];
  return PRECOS_CADEIRAS[posicao - 1] ?? PRECO_CADEIRA_MINIMO;
}

export function mensalidadePorQuantidade(qtd) {
  let total = 0;
  for (let i = 1; i <= qtd; i += 1) total += precoCadeiraPorPosicao(i);
  return Number(total.toFixed(2));
}
