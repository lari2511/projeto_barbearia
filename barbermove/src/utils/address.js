export const formatarEndereco = (endereco) => {
  if (!endereco || typeof endereco !== 'string') return '';

  const texto = endereco.replace(/\s+/g, ' ').trim();
  if (!texto) return '';

  const partes = texto.split(',').map((parte) => parte.trim()).filter(Boolean);
  const rua = partes[0] || '';
  if (!rua) return '';

  let numero = '';
  let bairro = '';

  if (partes.length > 1) {
    const segundaParte = partes[1];
    const partesHifen = segundaParte.split(/\s*[-–—]\s*/);

    if (partesHifen.length >= 2) {
      numero = partesHifen[0].trim();
      bairro = partesHifen.slice(1).join(' - ').split(',')[0].trim();
    } else if (/\d/.test(segundaParte)) {
      numero = segundaParte.trim();
      if (partes.length > 2) {
        const candidatoBairro = partes[2].split(/[-–—]/)[0].trim();
        if (candidatoBairro && !/^\d+$/.test(candidatoBairro)) {
          bairro = candidatoBairro;
        }
      }
    } else {
      bairro = segundaParte.trim();
    }
  }

  if (!numero && !bairro) {
    const partesHifenDireto = rua.split(/\s*[-–—]\s*/).map((parte) => parte.trim()).filter(Boolean);
    if (partesHifenDireto.length >= 2) {
      return `${partesHifenDireto[0]} - ${partesHifenDireto.slice(1).join(' - ')}`;
    }
    return rua;
  }

  let resultado = rua;
  if (numero) resultado += `, ${numero}`;
  if (bairro) resultado += ` - ${bairro}`;
  return resultado;
};
