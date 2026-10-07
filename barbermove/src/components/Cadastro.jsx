import React, { useMemo, useState } from 'react'
import { ArrowLeft, Mail, Scissors, Store, User, Lock } from 'lucide-react'
import { useApp } from '../contexts/AppContext'
import { Button, Input } from './Common'

// Envia breadcrumbs do fluxo de cadastro pro servidor (visivel via `railway logs`),
// já que console.log local nunca chega até quem está depurando remotamente.
const enviarDiagnosticoCadastro = async (apiUrl, etapa, mensagem, extra) => {
  try {
    if (!apiUrl) return
    await fetch(`${apiUrl}/api/v1/notificacoes/frontend-diagnostic`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        origem: 'frontend',
        contexto: 'cadastro',
        etapa,
        mensagem: mensagem || null,
        url: typeof window !== 'undefined' ? window.location.href : null,
        user_agent: typeof navigator !== 'undefined' ? navigator.userAgent : null,
        extra: extra || null,
      }),
    })
  } catch (_err) {
    // Diagnostico nao pode quebrar o fluxo principal.
  }
}

const userTypes = [
  {
    type: 'cliente',
    label: 'Cliente',
    description: 'Compra serviços e acompanha agendamentos',
    icon: User,
    accent: 'from-sky-600 to-sky-700',
  },
  {
    type: 'barbeiro',
    label: 'Freelancer',
    description: 'Profissional autônomo com CPF e endereço',
    icon: Scissors,
    accent: 'from-emerald-600 to-emerald-700',
  },
  {
    type: 'barbearia',
    label: 'Barbearia',
    description: 'Negócio físico com endereço obrigatório',
    icon: Store,
    accent: 'from-orange-600 to-orange-700',
  },
]

const EMAIL_REGEX = /^[^\s@]+@[^\s@]+\.[^\s@]+$/

// Cadastro rápido: só e-mail + senha. Nome, telefone, documentos, fotos e dados da
// barbearia são pedidos depois, já dentro do app (CompletarCadastro).
export default function Cadastro({ initialType = 'cliente', onBack, onSuccess }) {
  const { register, loading, API_URL } = useApp()
  const [selectedType, setSelectedType] = useState(initialType || 'cliente')
  const [form, setForm] = useState({ email: '', senha: '', confirmarSenha: '' })
  const [localError, setLocalError] = useState('')

  const senhasDiferentes = Boolean(form.confirmarSenha) && form.senha !== form.confirmarSenha

  const selectedConfig = useMemo(
    () => userTypes.find((item) => item.type === selectedType) || userTypes[0],
    [selectedType]
  )

  const handleChange = (field) => (event) => {
    const value = event.target.value
    setForm((current) => ({ ...current, [field]: value }))
  }

  const handleSubmit = async (event) => {
    event.preventDefault()
    void enviarDiagnosticoCadastro(API_URL, 'submit:start', 'handleSubmit disparado', { selectedType })

    const email = form.email.trim().toLowerCase()
    if (!email || !form.senha || !form.confirmarSenha) {
      setLocalError('Preencha e-mail, senha e confirmação de senha')
      return
    }
    if (!EMAIL_REGEX.test(email)) {
      setLocalError('Informe um e-mail válido.')
      return
    }
    if (form.senha.length < 6) {
      setLocalError('A senha precisa ter 6 caracteres ou mais')
      return
    }
    if (form.senha !== form.confirmarSenha) {
      setLocalError('As senhas não coincidem.')
      return
    }

    setLocalError('')
    try {
      const result = await register(selectedType, { email, senha: form.senha })
      void enviarDiagnosticoCadastro(API_URL, 'submit:resultado', result ? 'register() retornou sucesso' : 'register() retornou false/falha', { sucesso: Boolean(result) })
      if (!result) {
        setLocalError('O servidor recusou o cadastro. Veja o aviso no topo da tela para o motivo.')
        return
      }
      onSuccess?.(result)
    } catch (err) {
      void enviarDiagnosticoCadastro(API_URL, 'submit:excecao', err?.message || String(err), null)
      setLocalError(`Erro inesperado: ${err?.message || err}`)
    }
  }

  return (
    <div className="bg-black text-white flex flex-col justify-start px-1 pt-2 pb-6">
      <div className="w-full min-w-0 rounded-2xl border border-zinc-800/50 bg-[#1e1e24] shadow-xl p-3">
        <button
          type="button"
          onClick={onBack}
          className="mb-3 flex items-center gap-2 text-sm text-zinc-400 hover:text-white"
        >
          <ArrowLeft size={16} />
          Voltar
        </button>

        <div className="mb-4 text-center">
          <div className={`mx-auto mb-3 flex h-16 w-16 items-center justify-center rounded-3xl bg-gradient-to-br ${selectedConfig.accent} shadow-[0_14px_32px_rgba(0,0,0,0.35)]`}>
            <selectedConfig.icon size={28} className="text-white" />
          </div>
          <h1 className="text-xl font-black">Criar conta</h1>
          <p className="mt-1 text-xs text-zinc-400">Escolha o perfil e crie seu acesso.</p>
        </div>

        <div className="grid grid-cols-3 gap-2 mb-3">
          {userTypes.map((item) => {
            const Icon = item.icon
            const active = selectedType === item.type
            return (
              <button
                key={item.type}
                type="button"
                onClick={() => setSelectedType(item.type)}
                className={`rounded-2xl border p-2 text-left transition ${active ? 'border-orange-500 bg-orange-500/10' : 'border-zinc-800 bg-black/30'}`}
              >
                <Icon size={18} className={`mb-2 ${active ? 'text-orange-400' : 'text-zinc-400'}`} />
                <div className="text-xs font-black leading-tight">{item.label}</div>
              </button>
            )
          })}
        </div>

        <form onSubmit={handleSubmit} className="space-y-1">
          <Input
            label="E-mail"
            type="email"
            icon={Mail}
            value={form.email}
            onChange={handleChange('email')}
            placeholder="voce@email.com"
            required
          />

          <Input
            label="Senha"
            type="password"
            icon={Lock}
            value={form.senha}
            onChange={handleChange('senha')}
            placeholder="••••••"
            required
          />

          <Input
            label="Confirmar senha"
            type="password"
            icon={Lock}
            value={form.confirmarSenha}
            onChange={handleChange('confirmarSenha')}
            placeholder="••••••"
            required
          />
          {senhasDiferentes && (
            <p className="-mt-1 mb-1 text-xs font-semibold text-red-400">As senhas não coincidem.</p>
          )}

          {localError && (
            <div className="rounded-xl border border-red-500/30 bg-red-500/10 px-3 py-2 text-sm text-red-200">
              {localError}
            </div>
          )}

          <Button type="submit" fullWidth disabled={loading || senhasDiferentes} className="mt-2">
            {loading ? 'Criando conta...' : 'Criar conta'}
          </Button>
        </form>
      </div>
    </div>
  )
}
