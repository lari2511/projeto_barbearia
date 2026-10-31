// O backend salva/serializa datas em UTC "ingenuo" (sem sufixo Z/offset).
// new Date(string) sem timezone e interpretado pelo JS como horario LOCAL
// do aparelho, nao UTC -- isso adiantava em 3h os horarios exibidos no Brasil.
// Forca a interpretacao como UTC quando a string nao ja traz timezone.
export function parseDataServidorUTC(valor) {
  if (!valor) return NaN;
  const temTimezone = /Z$|[+-]\d{2}:?\d{2}$/.test(valor);
  return new Date(temTimezone ? valor : `${valor}Z`).getTime();
}

const TZ_BRASILIA = 'America/Sao_Paulo';

function paraDate(valor) {
  if (valor instanceof Date) return valor;
  if (typeof valor !== 'string') return new Date(NaN);
  // Data pura (sem hora) nao e um instante: nao pode mudar de dia na conversao.
  if (/^\d{4}-\d{2}-\d{2}$/.test(valor)) return new Date(`${valor}T12:00:00Z`);
  return new Date(parseDataServidorUTC(valor));
}

function formatar(valor, metodo, opcoes) {
  const data = paraDate(valor);
  if (Number.isNaN(data.getTime())) return '-';
  return data[metodo]('pt-BR', { timeZone: TZ_BRASILIA, ...opcoes });
}

// Horario oficial do app (Brasilia), independente do fuso configurado no aparelho.
export const formatarDataSP = (valor) => formatar(valor, 'toLocaleDateString');
export const formatarHoraSP = (valor) => formatar(valor, 'toLocaleTimeString', { hour: '2-digit', minute: '2-digit' });
export const formatarDataHoraSP = (valor) => formatar(valor, 'toLocaleString');
