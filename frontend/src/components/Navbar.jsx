import React from 'react'
import { FiHome, FiFileText, FiScissors, FiCreditCard, FiUser } from 'react-icons/fi'
import { FiLogOut } from 'react-icons/fi'
import { useAuth } from '../context/AuthProvider'
import { useNavigate } from 'react-router-dom'

export default function Navbar({ activeTab, setActiveTab }) {
  const auth = useAuth()
  const navigate = useNavigate()
  const menuItems = [
    { id: 'inicio', label: 'Início', icon: <FiHome size={22} /> },
    { id: 'chamados', label: 'Chamados', icon: <FiFileText size={22} /> },
    { id: 'atendimentos', label: 'Atendimentos', icon: <FiScissors size={22} /> },
    { id: 'carteira', label: 'Carteira', icon: <FiCreditCard size={22} /> },
    { id: 'perfil', label: 'Perfil', icon: <FiUser size={22} /> },
  ]

  return (
    <div className="fixed bottom-0 left-0 right-0 bg-barberBg border-t border-gray-900 px-4 py-2 flex justify-between items-center z-50">
      {menuItems.map((item) => (
        <button
          key={item.id}
          onClick={() => setActiveTab(item.id)}
          className={`flex flex-col items-center justify-center flex-1 py-1 transition-colors ${
            activeTab === item.id ? 'text-[#8A56FF]' : 'text-barberTextGray'
          }`}
        >
          {item.icon}
          <span className="text-[10px] font-medium mt-1">{item.label}</span>
        </button>
      ))}
      <div className="absolute right-4 top-0 transform -translate-y-1/2">
        <button
          onClick={() => {
            auth && auth.logout && auth.logout()
            localStorage.removeItem('barbermove_token')
            localStorage.removeItem('user_profile')
            navigate('/')
          }}
          className="p-2 rounded-full bg-transparent text-barberTextGray hover:text-white"
          title="Sair"
        >
          <FiLogOut size={20} />
        </button>
      </div>
    </div>
  )
}
