// Termos de Uso / Política de Privacidade: leitura, situação, aceite e recusa.
// O servidor decide o que é exigido e grava data/hora; o app só mostra e envia as confirmações.

// Usuario.tipo -> perfil dos documentos
export const PERFIL_DOCUMENTOS = { cliente: 'cliente', barbeiro: 'freelancer', barbearia: 'proprietario' }

// Código que a API devolve (HTTP 428) quando falta aceite
export const CODIGO_TERMOS_PENDENTES = 'TERMOS_PENDENTES'

const lerJson = async (res) => {
  const data = await res.json().catch(() => ({}))
  if (!res.ok) throw new Error(typeof data?.detail === 'string' ? data.detail : 'Não foi possível concluir')
  return data
}

export const listarDocumentos = async (API_URL, tipoUsuario) => {
  const perfil = PERFIL_DOCUMENTOS[tipoUsuario] || tipoUsuario
  const res = await fetch(`${API_URL}/api/v1/termos/documentos?perfil=${encodeURIComponent(perfil)}`)
  return (await lerJson(res)).documentos || []
}

export const lerDocumento = async (API_URL, codigo, versao) => {
  const query = versao ? `?versao=${encodeURIComponent(versao)}` : ''
  const res = await fetch(`${API_URL}/api/v1/termos/documentos/${encodeURIComponent(codigo)}${query}`)
  return lerJson(res)
}

export const consultarSituacao = async (API_URL, token) => {
  const res = await fetch(`${API_URL}/api/v1/termos/situacao`, { headers: { Authorization: `Bearer ${token}` } })
  return lerJson(res)
}

// documentos: [{ codigo, versao }] todos confirmados pelo usuário nas caixas de seleção
export const aceitarDocumentos = async (API_URL, token, documentos, dataNascimento) => {
  const res = await fetch(`${API_URL}/api/v1/termos/aceitar`, {
    method: 'POST',
    headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' },
    body: JSON.stringify({
      aceites: documentos.map(({ codigo, versao }) => ({ codigo, versao, confirmado: true })),
      data_nascimento: dataNascimento || undefined,
    }),
  })
  return lerJson(res)
}

export const recusarDocumentos = async (API_URL, token) => {
  const res = await fetch(`${API_URL}/api/v1/termos/recusar`, {
    method: 'POST',
    headers: { Authorization: `Bearer ${token}` },
  })
  return lerJson(res)
}
