import React from 'react'
import { Routes, Route, Navigate } from 'react-router-dom'
import Login from './components/Login'
import Registro from './components/Registro'
import DashboardCliente from './components/DashboardCliente'
import Carteira from './components/Carteira'

function requireAuth(element) {
  const token = localStorage.getItem('access_token')
  return token ? element : <Navigate to="/" replace />
}

export default function App() {
  return (
    <div className="min-h-screen bg-barberBg text-white">
      <Routes>
        <Route path="/" element={<Login />} />
        <Route path="/registro" element={<Registro />} />
        <Route path="/dashboard" element={requireAuth(<DashboardCliente />)} />
        <Route path="/carteira" element={requireAuth(<Carteira />)} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </div>
  )
}
