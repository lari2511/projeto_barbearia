import React from 'react'
import { ArrowDownToLine, Clock3, ShieldAlert, Sparkles, X } from 'lucide-react'

export default function AppUpdateModal({ updateInfo, onUpdateNow, onLater, onClose }) {
  if (!updateInfo) return null

  const title = updateInfo.isNative ? 'Nova atualização do APK' : 'Nova atualização disponível'
  const subtitle = updateInfo.isNative
    ? 'Uma nova versão do aplicativo está pronta para instalar no seu Android.'
    : 'Uma nova versão do app está pronta para ser baixada.'

  return (
    <div className="fixed inset-0 z-[80] flex items-center justify-center bg-black/75 px-4 py-6 backdrop-blur-md">
      <div className="relative w-full max-w-md overflow-hidden rounded-[28px] border border-orange-400/25 bg-[#0b0b0f] shadow-[0_30px_120px_rgba(0,0,0,0.75)]">
        <div className="absolute inset-0 bg-[radial-gradient(circle_at_top,rgba(249,115,22,0.24),transparent_40%),radial-gradient(circle_at_bottom_right,rgba(14,165,233,0.12),transparent_35%)]" />

        <button
          type="button"
          onClick={onClose || onLater}
          className="absolute right-3 top-3 z-10 inline-flex h-9 w-9 items-center justify-center rounded-full border border-zinc-700/80 bg-black/50 text-zinc-300 hover:text-white"
          aria-label="Fechar aviso de atualização"
        >
          <X size={18} />
        </button>

        <div className="relative z-10 p-5 sm:p-6">
          <div className="flex items-center gap-4">
            <div className="relative h-18 w-18 shrink-0 overflow-hidden rounded-3xl border border-orange-400/30 bg-zinc-950 shadow-[0_0_40px_rgba(249,115,22,0.25)]">
              <img src="/brand-logo.png" alt="BarberMove" className="h-full w-full object-cover" />
            </div>
            <div className="min-w-0 flex-1">
              <div className="inline-flex items-center gap-1.5 rounded-full border border-orange-400/30 bg-orange-500/10 px-3 py-1 text-[10px] font-black uppercase tracking-[0.26em] text-orange-200">
                <Sparkles size={12} />
                Atualização
              </div>
              <h2 className="mt-3 text-2xl font-black tracking-tight text-white">{title}</h2>
              <p className="mt-2 text-sm leading-relaxed text-zinc-300">{subtitle}</p>
            </div>
          </div>

          <div className="mt-5 grid gap-3 rounded-3xl border border-zinc-800/80 bg-black/35 p-4">
            <div className="flex items-start gap-3">
              <ShieldAlert size={18} className="mt-0.5 text-orange-300" />
              <div>
                <p className="text-sm font-bold text-white">Correções e melhorias</p>
                <p className="mt-1 text-xs leading-relaxed text-zinc-400">
                  A nova versão traz correções automáticas, melhorias de estabilidade e ajustes de tela.
                </p>
              </div>
            </div>

            <div className="flex items-start gap-3">
              <Clock3 size={18} className="mt-0.5 text-sky-300" />
              <div>
                <p className="text-sm font-bold text-white">Leve e rápida</p>
                <p className="mt-1 text-xs leading-relaxed text-zinc-400">
                  O download é o novo APK publicado no servidor. Basta tocar em atualizar.
                </p>
              </div>
            </div>
          </div>

          <div className="mt-5 flex gap-2">
            <button
              type="button"
              onClick={onUpdateNow}
              className="flex-1 inline-flex items-center justify-center gap-2 rounded-2xl bg-orange-500 px-4 py-3 text-sm font-black text-white shadow-[0_16px_30px_rgba(249,115,22,0.22)] hover:bg-orange-600"
            >
              <ArrowDownToLine size={18} />
              Atualizar agora
            </button>
            <button
              type="button"
              onClick={onLater}
              className="rounded-2xl border border-zinc-700 bg-zinc-950/70 px-4 py-3 text-sm font-bold text-zinc-200 hover:bg-zinc-800"
            >
              Depois
            </button>
          </div>

          <p className="mt-4 text-center text-[11px] text-zinc-500">
            {updateInfo.filename ? `Versão: ${updateInfo.filename}` : 'Verificando nova versão pelo servidor'}
          </p>
        </div>
      </div>
    </div>
  )
}