// Validação e máscara de CPF/CNPJ para o cadastro de proprietário de barbearia.
// O algoritmo de dígito verificador do CPF espelha exatamente o usado em
// app/schemas.py (BarbeariaCreate.validate_cpf) para não haver divergência
// entre o que o frontend aceita e o que o backend aceita.

const somenteDigitos = (valor) => String(valor || '').replace(/\D/g, '');

export function maskCPF(valor) {
  const digitos = somenteDigitos(valor).slice(0, 11);
  if (digitos.length > 9) return `${digitos.slice(0, 3)}.${digitos.slice(3, 6)}.${digitos.slice(6, 9)}-${digitos.slice(9)}`;
  if (digitos.length > 6) return `${digitos.slice(0, 3)}.${digitos.slice(3, 6)}.${digitos.slice(6)}`;
  if (digitos.length > 3) return `${digitos.slice(0, 3)}.${digitos.slice(3)}`;
  return digitos;
}

export function maskCNPJ(valor) {
  const digitos = somenteDigitos(valor).slice(0, 14);
  if (digitos.length > 12) return `${digitos.slice(0, 2)}.${digitos.slice(2, 5)}.${digitos.slice(5, 8)}/${digitos.slice(8, 12)}-${digitos.slice(12)}`;
  if (digitos.length > 8) return `${digitos.slice(0, 2)}.${digitos.slice(2, 5)}.${digitos.slice(5, 8)}/${digitos.slice(8)}`;
  if (digitos.length > 5) return `${digitos.slice(0, 2)}.${digitos.slice(2, 5)}.${digitos.slice(5)}`;
  if (digitos.length > 2) return `${digitos.slice(0, 2)}.${digitos.slice(2)}`;
  return digitos;
}

export function isValidCPF(valor) {
  const cpf = somenteDigitos(valor);
  if (cpf.length !== 11 || cpf === cpf[0].repeat(11)) return false;

  let soma = 0;
  for (let i = 0; i < 9; i++) soma += Number(cpf[i]) * (10 - i);
  const digito1 = ((soma * 10) % 11) % 10;
  if (digito1 !== Number(cpf[9])) return false;

  soma = 0;
  for (let i = 0; i < 10; i++) soma += Number(cpf[i]) * (11 - i);
  const digito2 = ((soma * 10) % 11) % 10;
  return digito2 === Number(cpf[10]);
}

export function isValidCNPJ(valor) {
  const cnpj = somenteDigitos(valor);
  if (cnpj.length !== 14 || cnpj === cnpj[0].repeat(14)) return false;

  const calcularDigito = (base) => {
    const pesos = base.length === 12
      ? [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
      : [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2];
    const soma = base.split('').reduce((acc, digito, idx) => acc + Number(digito) * pesos[idx], 0);
    const resto = soma % 11;
    return resto < 2 ? 0 : 11 - resto;
  };

  const base = cnpj.slice(0, 12);
  const digito1 = calcularDigito(base);
  const digito2 = calcularDigito(base + String(digito1));
  return cnpj.slice(12) === `${digito1}${digito2}`;
}
