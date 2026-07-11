import React from 'react'
import './index.css'
import ClientDashboard from './components/ClientDashboard'
import BarberDashboard from './components/BarberDashboard'
import ShopDashboard from './components/ShopDashboard'
import Login from './components/Login'
import { useApp } from './contexts/AppContext.jsx'

const isNativeApp = typeof window !== 'undefined' && (
  window.location.protocol === 'capacitor:' ||
  window.location.protocol === 'ionic:' ||
  window.Capacitor?.isNativePlatform?.() === true
)

export default function App() {
  const { token, userType, logout, notify, API_URL } = useApp()
  const [updateInfo, setUpdateInfo] = React.useState(null)

  React.useEffect(() => {
    // Em modo nativo, desabilita checagem de atualizacao em runtime para evitar
    // comportamentos de navegacao inesperados em WebView.
    if (isNativeApp) return

    const fetchUpdateInfo = async () => {
      try {
        const res = await fetch(`${API_URL}/apk/info`, { cache: 'no-store' })
        if (!res.ok) return

        const data = await res.json()
        if (data?.status !== 'ok') return

        const signature = data.latest_signature || `${data.latest_filename}:${data.latest_mtime_epoch}:${data.latest_size_bytes}`
        const baselineKey = 'apk_update_baseline_signature'
        const skipKey = 'apk_update_skip_signature'

        const baseline = localStorage.getItem(baselineKey)
        if (!baseline) {
          // Primeiro boot apos instalacao: cria baseline sem incomodar o usuario.
          localStorage.setItem(baselineKey, signature)
          return
        }

        if (signature === baseline || signature === localStorage.getItem(skipKey)) {
          return
        }

        setUpdateInfo({
          signature,
          filename: data.latest_filename,
          downloadUrl: data.download_url || data.latest_url || `${API_URL}/downloads/${data.latest_filename}`,
        })
      } catch (_err) {
        // Silencioso para nao quebrar a UX caso a API esteja indisponivel.
      }
    }

    fetchUpdateInfo()
  }, [API_URL])

  const handleDownloadUpdate = () => {
    if (!updateInfo?.downloadUrl) return

    localStorage.setItem('apk_update_baseline_signature', updateInfo.signature)
    localStorage.removeItem('apk_update_skip_signature')
    window.location.href = updateInfo.downloadUrl
    setUpdateInfo(null)
  }

  const handleSkipUpdate = () => {
    if (!updateInfo?.signature) return
    localStorage.setItem('apk_update_skip_signature', updateInfo.signature)
    setUpdateInfo(null)
  }

  const renderDashboard = () => {
    if (userType === 'cliente') {
      return <ClientDashboard token={token} logout={logout} API_URL={API_URL} notify={notify} />
    }

    if (userType === 'barbeiro') {
      return <BarberDashboard token={token} logout={logout} API_URL={API_URL} notify={notify} />
    }

    if (userType === 'barbearia') {
      return <ShopDashboard token={token} logout={logout} notify={notify} API_URL={API_URL} />
    }

    return <Login />
  }

  return (
    <div className="min-h-screen w-full bg-[#050507] flex justify-center items-start overflow-x-hidden">
      <div className="relative w-full max-w-[430px] min-h-screen bg-[#0a0a0c] shadow-[0_0_60px_rgba(0,0,0,0.8)] overflow-hidden">
        {updateInfo && (
          <div className="absolute inset-x-3 top-3 z-50 rounded-2xl border border-orange-400/50 bg-zinc-950/95 p-3 shadow-2xl">
            <p className="text-sm font-black text-orange-300">Atualizacao disponivel</p>
            <p className="mt-1 text-xs text-zinc-300">Existe uma nova versao do app pronta para baixar.</p>
            <div className="mt-3 flex gap-2">
              <button
                onClick={handleDownloadUpdate}
                className="flex-1 rounded-xl bg-orange-500 px-3 py-2 text-xs font-black text-white hover:bg-orange-600"
              >
                Baixar atualizacao
              </button>
              <button
                onClick={handleSkipUpdate}
                className="rounded-xl border border-zinc-700 px-3 py-2 text-xs font-semibold text-zinc-300 hover:bg-zinc-800"
              >
                Depois
              </button>
            </div>
          </div>
        )}

        <div className="relative flex flex-col w-full">
          <div className="w-full">
            {token ? renderDashboard() : <Login />}
          </div>
        </div>

      </div>
    </div>
  )
}
