import React, { useState } from 'react'
import Login from './components/Login'
import Navbar from './components/Navbar'

export default function App() {
  const [activeTab, setActiveTab] = useState('inicio')

  return (
    <div className="min-h-screen bg-barberBg text-white">
      <Login />
      <Navbar activeTab={activeTab} setActiveTab={setActiveTab} />
    </div>
  )
}
