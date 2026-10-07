import React, { useEffect, useState } from 'react'
import CompletarCadastro from './CompletarCadastro'

// Depois do cadastro rápido (e-mail + senha) o perfil fica com `cadastro_pendente`.
// - Freelancer e proprietário completam os dados antes de abrir a Home.
// - Cliente usa a Home normalmente; só vê um convite para completar nome e telefone.
// Se a consulta falhar, abre a Home (não trava quem já usa o app).

const TIPOS_QUE_EXIGEM = ['barbeiro', 'barbearia']

export default function GateCadastroPendente({ token, userType, API_URL, notify, logout, children }) {
  const [situacao, setSituacao] = useState('carregando') // carregando | pendente | ok
  const [formClienteAberto, setFormClienteAberto] = useState(false)
  const [conviteDispensado, setConviteDispensado] = useState(false)

  useEffect(() => {
    let ativo = true
    const carregar = async () => {
      try {
        const res = await fetch(`${API_URL}/api/v1/usuarios/perfil-completo`, {
          headers: { Authorization: `Bearer ${token}` },
        })
        const data = res.ok ? await res.json().catch(() => null) : null
        if (ativo) setSituacao(data?.cadastro_pendente ? 'pendente' : 'ok')
      } catch (_err) {
        if (ativo) setSituacao('ok')
      }
    }
    carregar()
    return () => {
      ativo = false
    }
  }, [API_URL, token])

  const concluir = () => {
    setSituacao('ok')
    setFormClienteAberto(false)
  }

  if (TIPOS_QUE_EXIGEM.includes(userType)) {
    if (situacao === 'carregando') {
      return <div className="min-h-screen flex items-center justify-center text-sm text-zinc-400">Carregando...</div>
    }
    if (situacao === 'pendente') {
      return (
        <CompletarCadastro
          tipo={userType}
          token={token}
          API_URL={API_URL}
          notify={notify}
          onConcluido={concluir}
          onSair={logout}
        />
      )
    }
    return children
  }

  if (situacao === 'pendente' && formClienteAberto) {
    return (
      <CompletarCadastro
        tipo="cliente"
        token={token}
        API_URL={API_URL}
        notify={notify}
        onConcluido={concluir}
        onPular={() => setFormClienteAberto(false)}
      />
    )
  }

  return (
    <>
      {situacao === 'pendente' && !conviteDispensado && (
        <div className="mx-3 mt-3 flex items-center gap-2 rounded-xl border border-sky-500/40 bg-sky-500/10 px-3 py-2 text-xs text-sky-100">
          <span className="flex-1">Complete seu perfil com nome e telefone.</span>
          <button
            type="button"
            onClick={() => setFormClienteAberto(true)}
            className="rounded-lg bg-sky-600 px-3 py-1 font-bold text-white hover:bg-sky-500"
          >
            Completar
          </button>
          <button
            type="button"
            onClick={() => setConviteDispensado(true)}
            className="px-1 text-zinc-400 hover:text-white"
            aria-label="Fechar"
          >
            ✕
          </button>
        </div>
      )}
      {children}
    </>
  )
}
