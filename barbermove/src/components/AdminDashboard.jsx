import React from 'react'
import { ShieldCheck, LogOut, CheckCircle, XCircle, ExternalLink, ClipboardList, Users, BadgeInfo } from 'lucide-react'

const getAdminBaseUrl = (apiUrl) => (apiUrl || '').replace(/\/api\/v1$/, '')

export default function AdminDashboard({ token, logout, notify, API_URL }) {
  const adminBaseUrl = React.useMemo(() => getAdminBaseUrl(API_URL), [API_URL])
  const [stats, setStats] = React.useState(null)
  const [pendentes, setPendentes] = React.useState([])
  const [loading, setLoading] = React.useState(false)

  const carregarDados = React.useCallback(async () => {
    if (!token) return

    setLoading(true)
    try {
      const [statsRes, pendentesRes] = await Promise.all([
        fetch(`${adminBaseUrl}/admin/api/estatisticas`, {
          headers: { Authorization: `Bearer ${token}` },
        }),
        fetch(`${adminBaseUrl}/admin/api/pendentes`, {
          headers: { Authorization: `Bearer ${token}` },
        }),
      ])

      if (statsRes.ok) {
        setStats(await statsRes.json())
      }

      if (pendentesRes.ok) {
        const pendingData = await pendentesRes.json()
        setPendentes(Array.isArray(pendingData) ? pendingData : [])
      }
    } catch (_error) {
      notify('Não foi possível carregar o painel admin', 'error')
    } finally {
      setLoading(false)
    }
  }, [adminBaseUrl, notify, token])

  React.useEffect(() => {
    carregarDados()
  }, [carregarDados])

  const aprovarUsuario = async (usuarioId) => {
    try {
      const res = await fetch(`${adminBaseUrl}/admin/api/aprovar/${usuarioId}`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}` },
      })

      if (!res.ok) throw new Error('Falha ao aprovar')

      notify('Usuário aprovado no servidor', 'success')
      await carregarDados()
    } catch (_error) {
      notify('Não foi possível aprovar o usuário', 'error')
    }
  }

  const rejeitarUsuario = async (usuarioId) => {
    try {
      const res = await fetch(`${adminBaseUrl}/admin/api/rejeitar/${usuarioId}`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}` },
      })

      if (!res.ok) throw new Error('Falha ao rejeitar')

      notify('Usuário rejeitado no servidor', 'info')
      await carregarDados()
    } catch (_error) {
      notify('Não foi possível rejeitar o usuário', 'error')
    }
  }

  return (
    <div className="min-h-screen bg-[#050507] px-4 py-5 text-white">
      <div className="mx-auto flex w-full max-w-5xl flex-col gap-4">
        <div className="rounded-[28px] border border-orange-400/20 bg-[#0d0d10] p-5 shadow-[0_25px_80px_rgba(0,0,0,0.45)]">
          <div className="flex items-center justify-between gap-3">
            <div className="flex items-center gap-3">
              <div className="flex h-14 w-14 items-center justify-center rounded-2xl border border-orange-400/30 bg-orange-500/10 text-orange-300">
                <ShieldCheck size={28} />
              </div>
              <div>
                <p className="text-xs font-black uppercase tracking-[0.28em] text-orange-300">Painel Admin</p>
                <h1 className="text-2xl font-black">BarberMove Server</h1>
                <p className="text-sm text-zinc-400">Aprovações e monitoramento centralizados no servidor.</p>
              </div>
            </div>
            <button
              type="button"
              onClick={logout}
              className="inline-flex items-center gap-2 rounded-2xl border border-zinc-700 bg-zinc-950 px-4 py-2 text-sm font-bold text-zinc-200"
            >
              <LogOut size={16} />
              Sair
            </button>
          </div>

          <div className="mt-4 flex flex-wrap gap-2">
            <button
              type="button"
              onClick={() => window.open(`${adminBaseUrl}/admin`, '_blank', 'noopener,noreferrer')}
              className="inline-flex items-center gap-2 rounded-2xl bg-orange-500 px-4 py-2 text-sm font-black text-white"
            >
              Abrir painel web
              <ExternalLink size={16} />
            </button>
            <button
              type="button"
              onClick={carregarDados}
              className="rounded-2xl border border-zinc-700 bg-zinc-950 px-4 py-2 text-sm font-bold text-zinc-200"
            >
              Atualizar dados
            </button>
          </div>
        </div>

        <div className="grid gap-3 sm:grid-cols-3">
          <MetricCard icon={Users} label="Total usuários" value={stats?.total ?? '—'} tone="orange" />
          <MetricCard icon={CheckCircle} label="Aprovados" value={stats?.aprovados ?? '—'} tone="emerald" />
          <MetricCard icon={BadgeInfo} label="Pendentes" value={stats?.pendentes ?? '—'} tone="sky" />
        </div>

        <div className="rounded-[28px] border border-zinc-800 bg-[#0d0d10] p-5">
          <div className="flex items-center justify-between gap-3">
            <div>
              <h2 className="text-lg font-black">Pendências de aprovação</h2>
              <p className="text-sm text-zinc-400">Perfis aguardando liberação no servidor.</p>
            </div>
            <div className="inline-flex items-center gap-2 rounded-full border border-zinc-700 px-3 py-1 text-xs font-bold text-zinc-300">
              <ClipboardList size={14} />
              {loading ? 'Carregando...' : `${pendentes.length} item(ns)`}
            </div>
          </div>

          <div className="mt-4 space-y-3">
            {pendentes.length === 0 ? (
              <div className="rounded-2xl border border-dashed border-zinc-800 bg-black/30 p-6 text-center text-sm text-zinc-400">
                Nenhuma pendência no momento.
              </div>
            ) : (
              pendentes.map((usuario) => (
                <div key={usuario.id} className="rounded-2xl border border-zinc-800 bg-black/40 p-4">
                  <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
                    <div>
                      <p className="text-base font-bold text-white">{usuario.nome}</p>
                      <p className="text-sm text-zinc-400">{usuario.email} • {usuario.tipo}</p>
                    </div>
                    <div className="flex gap-2">
                      <button
                        type="button"
                        onClick={() => aprovarUsuario(usuario.id)}
                        className="inline-flex items-center gap-2 rounded-2xl bg-emerald-500 px-4 py-2 text-sm font-black text-white"
                      >
                        <CheckCircle size={16} />
                        Aprovar
                      </button>
                      <button
                        type="button"
                        onClick={() => rejeitarUsuario(usuario.id)}
                        className="inline-flex items-center gap-2 rounded-2xl border border-red-500/30 bg-red-500/10 px-4 py-2 text-sm font-bold text-red-200"
                      >
                        <XCircle size={16} />
                        Rejeitar
                      </button>
                    </div>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>
      </div>
    </div>
  )
}

function MetricCard({ icon: Icon, label, value, tone }) {
  const tones = {
    orange: 'border-orange-400/20 bg-orange-500/10 text-orange-200',
    emerald: 'border-emerald-400/20 bg-emerald-500/10 text-emerald-200',
    sky: 'border-sky-400/20 bg-sky-500/10 text-sky-200',
  }

  return (
    <div className={`rounded-[24px] border p-4 ${tones[tone] || tones.orange}`}>
      <div className="flex items-center justify-between gap-3">
        <div>
          <p className="text-xs font-bold uppercase tracking-[0.2em] opacity-70">{label}</p>
          <p className="mt-2 text-3xl font-black text-white">{value}</p>
        </div>
        <Icon size={26} className="opacity-80" />
      </div>
    </div>
  )
}