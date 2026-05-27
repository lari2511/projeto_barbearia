import React, { createContext, useContext, useState, useEffect } from 'react'
import { barberService } from '../services/barberService'

const AuthContext = createContext(null)

export function useAuth() {
  return useContext(AuthContext)
}

export default function AuthProvider({ children }) {
  const [accessToken, setAccessToken] = useState(() => localStorage.getItem('access_token'))
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    if (accessToken) localStorage.setItem('access_token', accessToken)
    else localStorage.removeItem('access_token')
  }, [accessToken])

  const login = async (credentials) => {
    setLoading(true)
    try {
      const res = await barberService.login(credentials.email, credentials.password, credentials.type)
      if (res?.token) {
        setAccessToken(res.token)
        localStorage.setItem('barbermove_token', res.token)
        if (res.user) localStorage.setItem('user_profile', JSON.stringify(res.user))
        return { ok: true }
      }
      return { ok: false, error: 'Resposta inválida do servidor' }
    } catch (err) {
      return { ok: false, error: err?.response?.data?.detail || err?.message }
    } finally {
      setLoading(false)
    }
  }

  const logout = () => {
    setAccessToken(null)
    localStorage.removeItem('user_profile')
    localStorage.removeItem('barbermove_token')
    localStorage.removeItem('access_token')
  }

  const value = {
    accessToken,
    login,
    logout,
    loading,
  }

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}
