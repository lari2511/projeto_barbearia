import React, { useState, useEffect } from 'react'
import Login from './components/Login'
import DashboardCliente from './components/DashboardCliente'

export default function App() {
  const [authenticated, setAuthenticated] = useState(false)

  useEffect(() => {
    const token = localStorage.getItem('access_token')
    if (token) setAuthenticated(true)
  }, [])

  return (
    <div className="min-h-screen bg-barberBg text-white">
      {!authenticated ? (
        <Login onAuth={() => setAuthenticated(true)} />
      ) : (
        <DashboardCliente />
      )}
    </div>
  )
}
