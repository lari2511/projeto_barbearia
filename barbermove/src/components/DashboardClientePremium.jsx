import React, { useState } from 'react'

export default function DashboardClientePremium({ onLogout }) {
  const [activeTab, setActiveTab] = useState('inicio')

  const handleLogout = () => {
    if (typeof onLogout === 'function') {
      onLogout()
      return
    }

    try {
      localStorage.clear()
      sessionStorage.clear()
    } catch (_error) {
      // ignore
    }
    window.location.reload()
  }

  const menuItems = [
    { title: 'Meu perfil', subtitle: 'Dados e preferências', icon: '👤' },
    { title: 'Meus agendamentos', subtitle: 'Histórico e próximas visitas', icon: '📅' },
    { title: 'Ajuda e suporte', subtitle: 'Falar com a equipe', icon: '💬' },
  ]

  const profileButtons = [
    { title: 'Editar dados', subtitle: 'Nome, telefone e senha', icon: '✏️' },
    { title: 'Histórico', subtitle: 'Últimos agendamentos', icon: '🧾' },
    { title: 'Ajuda rápida', subtitle: 'Suporte e dúvidas', icon: '💡' },
  ]

  return (
    <div className="relative flex flex-col w-full min-w-0 bg-black text-white font-sans select-none">
      <div className="flex flex-col px-2.5 py-2.5 gap-2.5 pb-28">
        {activeTab === 'perfil' ? (
          <>
            <div className="rounded-2xl border border-zinc-800 bg-[#0e0e10] p-3.5">
              <div className="flex items-center justify-between">
                <div>
                  <div className="text-xs uppercase tracking-[0.2em] text-zinc-500">Perfil</div>
                  <div className="text-xl font-black mt-1">Meu menu</div>
                </div>
                <div className="h-12 w-12 rounded-full bg-[#f97316] flex items-center justify-center text-xl font-black">L</div>
              </div>

              <div className="mt-3 grid gap-2">
                {menuItems.map((item) => (
                  <button
                    key={item.title}
                    type="button"
                    className="flex items-center gap-3 rounded-xl border border-zinc-800 bg-black/30 px-3 py-2.5 text-left"
                  >
                    <span className="text-xl">{item.icon}</span>
                    <span className="min-w-0 flex-1">
                      <span className="block text-sm font-bold">{item.title}</span>
                      <span className="block text-xs text-zinc-400">{item.subtitle}</span>
                    </span>
                    <span className="text-zinc-500">›</span>
                  </button>
                ))}
              </div>
            </div>

            <div className="rounded-2xl border border-zinc-800 bg-[#0e0e10] p-3.5">
              <div className="text-sm font-bold text-zinc-300">Atalhos do perfil</div>
              <div className="mt-3 grid gap-2">
                {profileButtons.map((item) => (
                  <button
                    key={item.title}
                    type="button"
                    className="flex items-center gap-3 rounded-xl border border-zinc-800 bg-black/30 px-3 py-2.5 text-left"
                  >
                    <span className="text-xl">{item.icon}</span>
                    <span className="min-w-0 flex-1">
                      <span className="block text-sm font-bold">{item.title}</span>
                      <span className="block text-xs text-zinc-400">{item.subtitle}</span>
                    </span>
                    <span className="text-zinc-500">›</span>
                  </button>
                ))}
              </div>
            </div>

            <div className="rounded-2xl border border-zinc-800 bg-[#0e0e10] p-3.5">
              <div className="text-sm font-bold text-zinc-300">Encerrar sessão</div>
              <p className="mt-1 text-xs text-zinc-500">Sai do perfil e limpa os dados locais do app.</p>
              <button
                type="button"
                onClick={handleLogout}
                className="mt-3 w-full rounded-xl border border-red-500/30 bg-red-500/10 px-4 py-3 text-sm font-black text-red-300"
              >
                Sair da conta
              </button>
            </div>
          </>
        ) : (
          <>
            <div className="flex items-center justify-between gap-3">
              <div className="text-base font-black">Seu barbeiro a um toque</div>
              <button
                type="button"
                onClick={() => setActiveTab('perfil')}
                className="rounded-full border border-zinc-800 bg-[#0e0e10] px-3 py-2 text-xs font-bold text-zinc-300"
              >
                ☰ Menu
              </button>
            </div>

            <div className="rounded-xl border border-zinc-800 bg-[#0e0e10] p-2.5 text-sm">
              <div className="font-bold">Tempo de Chegada</div>
              <div className="text-xl font-black">22min</div>
              <div className="text-xs text-zinc-400">Distância: 1.4 km</div>
            </div>

            <div className="rounded-xl border border-zinc-800 bg-[#0e0e10] p-2.5 flex items-center justify-between">
              <div>
                <div className="text-sm font-black">📍 Allan Siqueira</div>
                <div className="text-xs text-zinc-400">Localização em tempo real</div>
              </div>
              <div className="text-xs text-emerald-400 font-black">ONLINE</div>
            </div>

            <div className="rounded-xl border border-zinc-800 bg-[#050506] h-36 flex items-center justify-center text-zinc-500">
              [ Área do Mapa ]
            </div>

            <button className="w-full rounded-lg bg-[#f97316] py-2 text-sm font-black">🗺️ Ver Rota Completa no Mapa</button>

            <div className="rounded-xl border border-zinc-800 bg-[#0e0e10] p-2.5">
              <div className="text-xs uppercase tracking-[0.18em] text-zinc-500">Atalhos do perfil</div>
              <div className="mt-2.5 grid gap-2 sm:grid-cols-3">
                <button type="button" className="rounded-lg border border-zinc-800 bg-black/30 px-3 py-3 text-left text-sm font-bold">
                  <div>Editar dados</div>
                  <div className="mt-1 text-xs font-normal text-zinc-400">Nome e telefone</div>
                </button>
                <button type="button" className="rounded-lg border border-zinc-800 bg-black/30 px-3 py-3 text-left text-sm font-bold">
                  <div>Pedidos</div>
                  <div className="mt-1 text-xs font-normal text-zinc-400">Ver agendamentos</div>
                </button>
                <button type="button" onClick={handleLogout} className="rounded-lg border border-red-500/30 bg-red-500/10 px-3 py-3 text-left text-sm font-black text-red-300">
                  <div>Sair da conta</div>
                  <div className="mt-1 text-xs font-normal text-red-200/70">Volta para o login</div>
                </button>
              </div>
            </div>

            <div className="rounded-xl border border-zinc-800 bg-[#0e0e10] p-2.5 text-sm">
              <div className="font-bold">ℹ️ STATUS: CONFIRMADO</div>
              <div className="mt-2 grid grid-cols-2 gap-2 text-sm">
                <div>
                  <div className="text-xs text-zinc-400">Serviço</div>
                  <div className="font-black">barba</div>
                </div>
                <div className="text-right">
                  <div className="text-xs text-zinc-400">Valor</div>
                  <div className="font-black">R$ 30</div>
                </div>
              </div>
            </div>

            <div className="text-xs text-zinc-500">O tempo estimado pode variar. Acompanhe a localização em tempo real no mapa.</div>
          </>
        )}

        <div className="mt-auto px-1 pb-[calc(0.35rem+env(safe-area-inset-bottom))]">
          <div className="mx-auto grid w-full max-w-full grid-cols-5 gap-1 rounded-lg border border-white/5 bg-[#08080a]/90 p-1">
            {[
              { n: 'Início', i: '🏠', tab: 'inicio' },
              { n: 'Chamados', i: '📋', tab: 'inicio' },
              { n: 'Atendimentos', i: '💇‍♂️', tab: 'inicio' },
              { n: 'Carteira', i: '💳', tab: 'inicio' },
              { n: 'Perfil', i: '👤', tab: 'perfil' },
            ].map((item) => (
              <button
                key={item.n}
                type="button"
                onClick={() => setActiveTab(item.tab)}
                className="flex flex-col items-center text-xs py-2"
              >
                <span className="text-sm">{item.i}</span>
                <span className="mt-1">{item.n}</span>
              </button>
            ))}
          </div>
        </div>
      </div>
    </div>
  )
}
