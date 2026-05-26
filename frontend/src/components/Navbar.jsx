import React from 'react'
import { FiHome, FiFileText, FiScissors, FiCreditCard, FiUser } from 'react-icons/fi'

export default function Navbar({ activeTab, setActiveTab }) {
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
    </div>
  )
}
