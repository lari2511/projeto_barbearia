import React, { useState } from 'react'
import { FiBell, FiAlertTriangle, FiCheck } from 'react-icons/fi'
import Navbar from './Navbar'
import axios from '../api/axios'

export default function DashboardCliente() {
  const [activeMenu, setActiveMenu] = useState('inicio')

  const handleFinish = async () => {
    try {
      await axios.post('/appointments/finish', { id: 36 })
      alert('Atendimento finalizado (simulação)')
    } catch (err) {
      console.error(err)
    }
  }

  const handlePause = async () => {
    try {
      await axios.post('/appointments/pause', { id: 36 })
      alert('Atendimento pausado (simulação)')
    } catch (err) {
      console.error(err)
    }
  }

  return (
    <div className="min-h-screen bg-barberBg text-white pb-24">
      <header className="flex justify-between items-center p-4 border-b border-gray-900/50 bg-barberBg/80 backdrop-blur sticky top-0 z-40">
        <div className="text-sm font-semibold text-barberTextGray">09:42</div>
        <button className="relative p-2 text-barberOrange hover:text-white transition-colors">
          <FiBell size={24} />
          <span className="absolute top-1 right-1 w-2.5 h-2.5 bg-red-500 rounded-full"></span>
        </button>
      </header>

      <main className="p-4 space-y-4 max-w-md mx-auto">
        {/* notification */}
        <div className="bg-[#1A2238] border border-blue-900/40 p-4 rounded-xl flex justify-between items-center shadow-lg">
          <div className="flex items-center space-x-3">
            <div className="w-2 h-2 bg-blue-400 rounded-full animate-pulse"></div>
            <p className="text-sm font-bold text-blue-200">Nova atualização disponível!</p>
          </div>
          <button className="text-blue-400 hover:text-white text-xs font-bold px-2 py-1">✕</button>
        </div>

        {/* rest of dashboard cards (omitted for brevity) */}
        <div className="bg-barberCard border border-gray-800/40 p-4 rounded-xl space-y-4 shadow-xl">
          <div className="flex justify-between items-start">
            <div>
              <span className="text-[10px] uppercase tracking-wider font-bold text-barberTextGray bg-barberBg px-2 py-1 rounded">Status: em atendimento</span>
              <h3 className="text-lg font-black mt-2">Chamado ativo</h3>
              <p className="text-xs text-barberTextGray">ID: 36 – barba</p>
            </div>
            <button className="bg-[#CC2929] hover:bg-red-700 text-white font-bold text-xs px-3 py-2 rounded-lg transition-colors shadow-md">
              Cancelar com taxa de R$ 8,00
            </button>
          </div>

          <div className="space-y-2 pt-2 border-t border-gray-900">
            <div className="bg-[#241414] border border-red-900/30 p-3 rounded-lg flex items-start space-x-2">
              <FiAlertTriangle className="text-red-500 mt-0.5 shrink-0" size={16} />
              <p className="text-xs text-red-300 font-medium">
                Janela de cancelamento grátis expirou. Taxa de cancelamento: <span className="font-bold">R$ 8,00</span>
              </p>
            </div>
          </div>

          <div className="flex space-x-3">
            <button onClick={handleFinish} className="flex-1 bg-emerald-600 hover:bg-emerald-500 text-white font-black py-3 rounded-xl flex items-center justify-center space-x-2 transition-colors shadow-md text-sm">
              <FiCheck size={18} />
              <span>Finalizar Corte</span>
            </button>
            <button onClick={handlePause} className="bg-barberActive hover:bg-gray-800 text-white font-bold px-5 py-3 rounded-xl flex items-center justify-center space-x-2 transition-colors border border-gray-700/30 text-sm">
              <span>⏸ Pausar</span>
            </button>
          </div>
        </div>

      </main>

      <Navbar activeTab={activeMenu} setActiveTab={setActiveMenu} />
    </div>
  )
}
