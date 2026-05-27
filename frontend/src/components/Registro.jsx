import React, { useState } from 'react'
import axios from '../api/axios'
import LayoutMobile from './LayoutMobile'

export default function Registro() {
  const [userType, setUserType] = useState('Cliente')
  const [nome, setNome] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [documento, setDocumento] = useState('')
  const [error, setError] = useState('')
  const [success, setSuccess] = useState(false)

  const handleRegister = async (e) => {
    e.preventDefault()
    setError('')
    setSuccess(false)

    try {
      await axios.post('/auth/register', {
        nome,
        email,
        senha: password,
        documento,
        role: userType.toLowerCase(),
      })

      setSuccess(true)
      setTimeout(() => {
        window.location.href = '/'
      }, 1500)
    } catch (err) {
      setError(err.response?.data?.message || 'Erro ao realizar o cadastro. Tente novamente.')
    }
  }

  return (
    <LayoutMobile>
      <div className="flex-1 flex flex-col justify-center p-6 space-y-6">
        <div className="text-center">
          <h2 className="text-2xl font-black">Crie sua conta</h2>
          <p className="text-xs text-barberTextGray mt-1">Seja bem-vindo ao BarberMove</p>
        </div>

        <div className="w-full bg-barberCard p-1 rounded-xl flex justify-between border border-gray-800/40">
          {['Cliente', 'Barbeiro', 'Barbearia'].map((type) => (
            <button
              key={type}
              type="button"
              onClick={() => {
                setUserType(type)
                setDocumento('')
              }}
              className={`flex-1 py-2 text-xs font-bold rounded-lg transition-all ${
                userType === type ? 'bg-barberActive text-white shadow' : 'text-barberTextGray'
              }`}
            >
              {type}
            </button>
          ))}
        </div>

        <form onSubmit={handleRegister} className="space-y-3.5">
          {error && <p className="text-red-500 text-xs font-bold text-center bg-red-500/10 py-2 rounded-lg">{error}</p>}
          {success && <p className="text-emerald-500 text-xs font-bold text-center bg-emerald-500/10 py-2 rounded-lg">Cadastro realizado! Redirecionando...</p>}

          <input
            type="text"
            placeholder="Nome completo ou Razão Social"
            value={nome}
            onChange={(e) => setNome(e.target.value)}
            className="w-full bg-[#EBF2FA] text-black placeholder-gray-500 font-medium px-4 py-3.5 rounded-xl focus:outline-none text-sm"
            required
          />

          <input
            type="email"
            placeholder="Seu e-mail"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            className="w-full bg-[#EBF2FA] text-black placeholder-gray-500 font-medium px-4 py-3.5 rounded-xl focus:outline-none text-sm"
            required
          />

          <input
            type="text"
            placeholder={userType === 'Cliente' ? 'CPF' : 'CNPJ / Registro Profissional'}
            value={documento}
            onChange={(e) => setDocumento(e.target.value)}
            className="w-full bg-[#EBF2FA] text-black placeholder-gray-500 font-medium px-4 py-3.5 rounded-xl focus:outline-none text-sm"
            required
          />

          <input
            type="password"
            placeholder="Crie uma senha"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            className="w-full bg-[#EBF2FA] text-black placeholder-gray-500 font-medium px-4 py-3.5 rounded-xl focus:outline-none text-sm"
            required
          />

          <button type="submit" className="w-full bg-[#E5E5E5] text-black font-black py-3.5 rounded-xl text-sm shadow mt-4 transition-colors hover:bg-white">
            Finalizar Cadastro
          </button>
        </form>

        <div className="text-center">
          <p className="text-xs text-barberTextGray">
            Já possui uma conta?{' '}
            <span onClick={() => window.location.href = '/'} className="text-barberOrange font-bold cursor-pointer hover:underline">Fazer Login</span>
          </p>
        </div>

      </div>
    </LayoutMobile>
  )
}
