import React, { useState } from 'react'

export default function Login() {
  const [userType, setUserType] = useState('Cliente')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')

  const handleLogin = (e) => {
    e.preventDefault()
    console.log(`Logando como ${userType}:`, { email, password })
  }

  return (
    <div className="min-h-screen bg-barberBg text-white flex flex-col items-center justify-center p-6">
      <div className="w-full max-w-md flex flex-col items-center space-y-8">
        <div className="flex flex-col items-center space-y-3">
          <div className="w-28 h-28 bg-white rounded-lg flex items-center justify-center p-2 shadow-lg">
            <img src="/path-to-your-logo.png" alt="BarberMove Logo" className="w-full h-full object-contain" />
          </div>

          <h1 className="text-4xl font-black tracking-tight mt-2">
            Barber<span className="text-barberOrange">Move</span>
          </h1>
          <p className="text-xs font-bold tracking-widest text-barberTextGray uppercase">Agenda e Gestão Profissional</p>
        </div>

        <div className="w-full bg-barberCard p-1 rounded-xl flex justify-between border border-gray-800/40">
          {['Cliente', 'Barbeiro', 'Barbearia'].map((type) => (
            <button
              key={type}
              type="button"
              onClick={() => setUserType(type)}
              className={`flex-1 py-3 text-sm font-bold rounded-lg transition-all duration-200 ${
                userType === type ? 'bg-barberActive text-white shadow-md' : 'text-barberTextGray hover:text-white'
              }`}
            >
              {type}
            </button>
          ))}
        </div>

        <form onSubmit={handleLogin} className="w-full space-y-4">
          <div>
            <input
              type="email"
              placeholder="E-mail ou usuário"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="w-full bg-[#EBF2FA] text-black placeholder-gray-500 font-medium px-5 py-4 rounded-xl focus:outline-none focus:ring-2 focus:ring-barberOrange/50 transition-all text-base"
              required
            />
          </div>

          <div>
            <input
              type="password"
              placeholder="Sua senha"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="w-full bg-[#EBF2FA] text-black placeholder-gray-500 font-medium px-5 py-4 rounded-xl focus:outline-none focus:ring-2 focus:ring-barberOrange/50 transition-all text-base"
              required
            />
          </div>

          <button type="submit" className="w-full bg-[#E5E5E5] text-black font-black py-4 rounded-xl hover:bg-white transition-colors duration-200 text-center text-base mt-2 shadow-md">
            Entrar na Conta
          </button>
        </form>

        <div className="text-center pt-2">
          <p className="text-sm text-barberTextGray">
            Não tem uma conta?{' '}
            <span className="text-barberOrange font-bold cursor-pointer hover:underline">Registre-se</span>
          </p>
        </div>
      </div>
    </div>
  )
}
