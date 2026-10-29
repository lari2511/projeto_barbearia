import React, { useCallback, useEffect, useState } from 'react'
import AceiteTermos from './AceiteTermos'
import { consultarSituacao } from '../utils/termos'

// Antes da Home: confere no servidor se o usuário tem aceite vigente dos documentos do
// seu perfil. Sem aceite, mostra só a tela de aceite (o servidor também bloqueia a API).
// Reconfere ao voltar para o app, para pegar uma versão publicada com o app aberto.
// Se a consulta falhar, abre a Home: o servidor continua barrando o que for protegido.

export default function GateTermos({ token, API_URL, logout, children }) {
  const [situacao, setSituacao] = useState(null)
  const [estado, setEstado] = useState('carregando') // carregando | pendente | ok

  const carregar = useCallback(async () => {
    try {
      const data = await consultarSituacao(API_URL, token)
      setSituacao(data)
      setEstado(data?.liberado === false ? 'pendente' : 'ok')
    } catch (_err) {
      setEstado((atual) => (atual === 'carregando' ? 'ok' : atual))
    }
  }, [API_URL, token])

  useEffect(() => {
    carregar()
  }, [carregar])

  useEffect(() => {
    const aoVoltar = () => {
      if (document.visibilityState === 'visible') carregar()
    }
    document.addEventListener('visibilitychange', aoVoltar)
    return () => document.removeEventListener('visibilitychange', aoVoltar)
  }, [carregar])

  if (estado === 'carregando') {
    return <div className="min-h-screen flex items-center justify-center text-sm text-zinc-400">Carregando...</div>
  }

  if (estado === 'pendente') {
    return (
      <AceiteTermos
        key={(situacao?.pendentes || []).map((doc) => `${doc.codigo}@${doc.versao}`).join('|')}
        API_URL={API_URL}
        token={token}
        situacao={situacao}
        onLiberado={(nova) => {
          setSituacao(nova)
          setEstado('ok')
        }}
        onAtualizar={(nova) => {
          if (!nova) {
            carregar()
            return
          }
          setSituacao(nova)
          setEstado(nova.liberado ? 'ok' : 'pendente')
        }}
        onSair={logout}
      />
    )
  }

  return children
}
