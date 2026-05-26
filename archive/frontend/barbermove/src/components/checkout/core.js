// Helpers comuns para checkout: preferência, normalização de PIX, QR fallback e validação de cartão
export const CLIENTE_METODO_PREF_KEY = 'cliente_metodo_pagamento_preferido';

export const salvarMetodoPreferidoCliente = (metodo) => {
  if (!metodo) return;
  try {
    if (typeof window !== 'undefined') {
      window.localStorage.setItem(CLIENTE_METODO_PREF_KEY, metodo);
    }
  } catch (_err) {
    // ignore
  }
};

export const lerMetodoPreferidoCliente = () => {
  try {
    if (typeof window !== 'undefined') {
      return window.localStorage.getItem(CLIENTE_METODO_PREF_KEY) || null;
    }
  } catch (_err) {
    return null;
  }
  return null;
};

export const pareceCodigoPix = (valor) => {
  if (!valor || typeof valor !== 'string') return false;
  const conteudo = valor.trim();
  if (!conteudo) return false;
  if (conteudo.startsWith('000201')) return true;
  return conteudo.includes('BR.GOV.BCB.PIX');
};

export const normalizarPixMercadoPago = (data) => {
  const payload = data || {};
  const tx = payload?.point_of_interaction?.transaction_data || {};

  const candidatosImagem = [
    payload.qrcode_base64,
    payload.qr_code_base64,
    tx.qr_code_base64,
    payload.qrcode,
    payload.qr_code,
    tx.qr_code,
  ].filter((item) => typeof item === 'string' && item.trim());

  const candidatosTexto = [
    payload.pix_copia_cola,
    payload.codigo_pix,
    payload.copia_cola,
    payload.emv,
    tx.qr_code,
    payload.qrcode,
    payload.qr_code,
  ].filter((item) => typeof item === 'string' && item.trim());

  let qrImage = null;
  for (const item of candidatosImagem) {
    const conteudo = item.trim();
    if (conteudo.startsWith('data:image')) {
      qrImage = conteudo;
      break;
    }
    if (conteudo.startsWith('http://') || conteudo.startsWith('https://')) {
      qrImage = conteudo;
      break;
    }
    if (!pareceCodigoPix(conteudo)) {
      qrImage = `data:image/png;base64,${conteudo}`;
      break;
    }
  }

  const copia =
    candidatosTexto.find((item) => pareceCodigoPix(item)) ||
    candidatosTexto[0] ||
    '';

  return { qrImage, copia };
};

export const gerarQrDataUrl = async (texto) => {
  if (!texto) return '';
  try {
    const QRCode = (await import('qrcode')).default;
    return await QRCode.toDataURL(texto, { width: 320, margin: 1, errorCorrectionLevel: 'M' });
  } catch (err) {
    console.error('Erro gerarQrDataUrl:', err);
    return '';
  }
};

export const validarCartaoBasico = (cartao) => {
  const erros = {};
  const numLimpo = (cartao?.numero || '').replace(/\s/g, '');
  if (!numLimpo || numLimpo.length < 13) erros.numero = 'Número do cartão inválido';
  if (!cartao?.titular || cartao.titular.length < 3) erros.titular = 'Nome do titular é obrigatório';
  const validadeLimpa = (cartao?.validade || '').replace(/\D/g, '');
  if (!validadeLimpa || validadeLimpa.length !== 4) {
    erros.validade = 'Validade inválida (MM/AA)';
  } else {
    const mes = parseInt(validadeLimpa.slice(0, 2));
    const ano = parseInt('20' + validadeLimpa.slice(2, 4));
    const hoje = new Date();
    const anoAtual = hoje.getFullYear();
    const mesAtual = hoje.getMonth() + 1;
    if (mes < 1 || mes > 12) erros.validade = 'Mês inválido';
    else if (ano < anoAtual || (ano === anoAtual && mes < mesAtual)) erros.validade = 'Cartão vencido';
  }
  if (!cartao?.cvv || String(cartao.cvv).length < 3) erros.cvv = 'CVV inválido';
  return erros;
};

export default {
  salvarMetodoPreferidoCliente,
  lerMetodoPreferidoCliente,
  pareceCodigoPix,
  normalizarPixMercadoPago,
  gerarQrDataUrl,
  validarCartaoBasico,
};
