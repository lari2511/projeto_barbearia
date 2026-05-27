import axios from '../api/axios'

const loginEndpoints = {
  Cliente: '/login/cliente/',
  Barbeiro: '/login/barbeiro/',
  Barbearia: '/login/barbearia/',
}

const toFormUrlEncoded = (payload) => {
  const params = new URLSearchParams()
  Object.entries(payload).forEach(([key, value]) => {
    if (value !== undefined && value !== null) {
      params.append(key, String(value))
    }
  })
  return params
}

export const barberService = {
  login: async (email, password, userType = 'Cliente') => {
    const endpoint = loginEndpoints[userType] || loginEndpoints.Cliente
    const res = await axios.post(
      endpoint,
      toFormUrlEncoded({
        grant_type: 'password',
        username: email,
        password,
        scope: '',
        client_id: '',
        client_secret: '',
      }),
      {
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      }
    )

    const token = res?.data?.access_token || res?.data?.token
    const user = res?.data?.usuario || res?.data?.user || res?.data?.profile || null
    return { token, user, raw: res.data }
  },

  register: async (payload) => {
    const role = (payload.role || 'Cliente').toLowerCase()
    if (role === 'cliente') {
      const res = await axios.post('/clientes/', {
        nome: payload.nome,
        email: payload.email,
        senha: payload.senha,
        telefone: payload.telefone || null,
        cpf: payload.cpf,
      })
      return res.data
    }

    if (role === 'barbearia') {
      const res = await axios.post('/barbearias/', {
        nome: payload.nome,
        email: payload.email,
        senha: payload.senha,
        telefone: payload.telefone || null,
        endereco: payload.endereco,
        cep: payload.cep || null,
        cpf: payload.cpf,
        cnpj: payload.cnpj || null,
        latitude: payload.latitude ?? null,
        longitude: payload.longitude ?? null,
      })
      return res.data
    }

    throw new Error('Cadastro de barbeiro requer autenticação e não está disponível no formulário público.')
  },

  getCarteira: async () => {
    const res = await axios.get('/usuarios/saldo')
    return res.data
  },

  finishAppointment: async (id) => {
    const res = await axios.put(`/chamados/${id}/finalizar`)
    return res.data
  },

  pauseAppointment: async (id) => {
    const res = await axios.put(`/chamados/${id}/iniciar-corte`)
    return res.data
  },

  cancelAppointment: async (id) => {
    const res = await axios.put(`/chamados/${id}/cancelar`)
    return res.data
  },

  getProfile: async () => {
    const res = await axios.get('/usuarios/perfil-completo')
    return res.data
  },

  getAppointmentsHistory: async (chamadoId) => {
    const res = await axios.get(`/chamados/${chamadoId}/historico`)
    return res.data
  },

  getChatMessages: async (chamadoId) => {
    const res = await axios.get(`/chat/${chamadoId}/mensagens`)
    return res.data
  },

  startChat: async (destinatarioId) => {
    const res = await axios.post('/chat/iniciar', null, {
      params: destinatarioId ? { destinatario_id: destinatarioId } : {},
    })
    return res.data
  },

  sendChatMessage: async ({ chamado_id, mensagem }) => {
    const res = await axios.post('/chat/mensagem', { chamado_id, mensagem })
    return res.data
  },

  // Other API helpers can be added here
}
