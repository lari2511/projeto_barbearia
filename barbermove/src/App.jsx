import React from 'react'
import './index.css'
import ClientDashboard from './components/ClientDashboard'
import BarberDashboard from './components/BarberDashboard'
import ShopDashboard from './components/ShopDashboard'
import Login from './components/Login'
import { useApp } from './contexts/AppContext.jsx'

export default function App() {
  const { token, userType, logout, notify, API_URL } = useApp()

  const renderDashboard = () => {
    if (userType === 'cliente') {
      return <ClientDashboard token={token} logout={logout} API_URL={API_URL} notify={notify} />
    }

    if (userType === 'barbeiro') {
      return <BarberDashboard token={token} logout={logout} API_URL={API_URL} notify={notify} />
    }

    if (userType === 'barbearia') {
      return <ShopDashboard token={token} logout={logout} notify={notify} API_URL={API_URL} />
    }

    return <Login />
  }

  return (
    <div className="min-h-screen w-full bg-[#050507] flex justify-center items-start overflow-x-hidden">
      <div className="relative w-full max-w-[430px] min-h-screen bg-[#0a0a0c] shadow-[0_0_60px_rgba(0,0,0,0.8)] overflow-hidden">
        <div className="relative flex flex-col w-full">
          <div className="w-full">
            {token ? renderDashboard() : <Login />}
          </div>
        </div>

      </div>
    </div>
  )
}
