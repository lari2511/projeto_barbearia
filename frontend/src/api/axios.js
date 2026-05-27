import axios from 'axios'

const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000/api'

const instance = axios.create({
  baseURL: API_BASE,
  headers: {
    'Content-Type': 'application/json',
  },
})

// Add auth token if present
instance.interceptors.request.use((config) => {
  const token = localStorage.getItem('access_token')
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

// Response interceptor to attempt refresh on 401
let isRefreshing = false
let failedQueue = []

const processQueue = (error, token = null) => {
  failedQueue.forEach((prom) => {
    if (error) prom.reject(error)
    else prom.resolve(token)
  })
  failedQueue = []
}

instance.interceptors.response.use(
  (res) => res,
  async (err) => {
    const originalRequest = err.config
    if (err.response && err.response.status === 401 && !originalRequest._retry) {
      const refreshToken = localStorage.getItem('refresh_token')
      if (!refreshToken) {
        return Promise.reject(err)
      }

      if (isRefreshing) {
        return new Promise(function (resolve, reject) {
          failedQueue.push({ resolve, reject })
        })
          .then((token) => {
            originalRequest.headers.Authorization = 'Bearer ' + token
            return instance(originalRequest)
          })
          .catch((e) => Promise.reject(e))
      }

      originalRequest._retry = true
      isRefreshing = true

      try {
        // try refresh
        const refreshRes = await axios.post(`${API_BASE}/auth/refresh`, { refresh_token: refreshToken })
        const newToken = refreshRes?.data?.access_token || refreshRes?.data?.token
        const newRefresh = refreshRes?.data?.refresh_token || refreshRes?.data?.refreshToken
        if (newToken) {
          localStorage.setItem('access_token', newToken)
          if (newRefresh) localStorage.setItem('refresh_token', newRefresh)
          instance.defaults.headers.common['Authorization'] = 'Bearer ' + newToken
          processQueue(null, newToken)
          return instance(originalRequest)
        }
        processQueue(new Error('Refresh failed'))
        return Promise.reject(err)
      } catch (e) {
        processQueue(e)
        return Promise.reject(e)
      } finally {
        isRefreshing = false
      }
    }

    return Promise.reject(err)
  }
)

export default instance
