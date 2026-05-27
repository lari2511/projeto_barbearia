import React from 'react'
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import Login from './components/Login'
import Registro from './components/Registro'
import DashboardCliente from './components/DashboardCliente'
import Carteira from './components/Carteira'

const RotaProtegida = ({ children }) => {
  const token = localStorage.getItem('barbermove_token') || localStorage.getItem('access_token')
  return token ? children : <Navigate to="/" replace />
}

export default function AppRoutes() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Login />} />
        <Route path="/registro" element={<Registro />} />
        <Route
          path="/dashboard"
          element={
            <RotaProtegida>
              <DashboardCliente />
            </RotaProtegida>
          }
        />
        <Route
          path="/carteira"
          element={
            <RotaProtegida>
              <Carteira />
            </RotaProtegida>
          }
        />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  )
}
