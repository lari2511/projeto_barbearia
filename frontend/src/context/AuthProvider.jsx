import React, { createContext, useContext, useState, useEffect } from 'react'
import axios from '../api/axios'

const AuthContext = createContext(null)

export function useAuth() {
  return useContext(AuthContext)
}

export default function AuthProvider({ children }) {
  const [accessToken, setAccessToken] = useState(() => localStorage.getItem('access_token'))
  const [refreshToken, setRefreshToken] = useState(() => localStorage.getItem('refresh_token'))
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    if (accessToken) localStorage.setItem('access_token', accessToken)
    else localStorage.removeItem('access_token')
  }, [accessToken])

  useEffect(() => {
    if (refreshToken) localStorage.setItem('refresh_token', refreshToken)
    else localStorage.removeItem('refresh_token')
  }, [refreshToken])

  const login = async (credentials) => {
    setLoading(true)
    try {
      const res = await axios.post('/auth/login', credentials)
      const token = res?.data?.access_token || res?.data?.token
      const rtoken = res?.data?.refresh_token || res?.data?.refreshToken
      if (token) {
        setAccessToken(token)
        if (rtoken) setRefreshToken(rtoken)
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
    setRefreshToken(null)
  }

  const value = {
    accessToken,
    refreshToken,
    login,
    logout,
    loading,
  }

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}
