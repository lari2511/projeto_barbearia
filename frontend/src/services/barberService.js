import axios from '../api/axios'

export const barberService = {
  login: async (email, password, userType = 'Cliente') => {
    const res = await axios.post('/auth/login', { email, password, type: userType })
    // Normalize response
    const token = res?.data?.access_token || res?.data?.token
    const user = res?.data?.user || res?.data?.profile || res?.data
    return { token, user, raw: res.data }
  },

  register: async (payload) => {
    const res = await axios.post('/auth/register', payload)
    return res.data
  },

  getCarteira: async () => {
    const res = await axios.get('/financeiro/carteira')
    return res.data
  },

  // Other API helpers can be added here
}
