import React from 'react'
import './index.css'
import ClientDashboard from './components/ClientDashboard'
import BarberDashboard from './components/BarberDashboard'
import ShopDashboard from './components/ShopDashboard'
import Login from './components/Login'
import AppUpdateModal from './components/AppUpdateModal'
import AdminDashboard from './components/AdminDashboard'
import { useApp } from './contexts/AppContext.jsx'
import { getWsBaseUrl } from './utils/api'

let localNotificationsModulePromise = null

const getLocalNotifications = async () => {
  if (!localNotificationsModulePromise) {
    localNotificationsModulePromise = import('@capacitor/local-notifications')
  }

  return localNotificationsModulePromise
}

const isNativeApp = typeof window !== 'undefined' && (
  window.location.protocol === 'capacitor:' ||
  window.location.protocol === 'ionic:' ||
  window.Capacitor?.isNativePlatform?.() === true
)

export default function App() {
  const { token, userType, logout, notify, API_URL } = useApp()
  const apiRootForApk = React.useMemo(() => {
    const rawBase = String(API_URL || '').replace(/\/$/, '')
    if (rawBase.endsWith('/api/v1')) {
      return rawBase.slice(0, -7)
    }
    return rawBase
  }, [API_URL])
  const [updateInfo, setUpdateInfo] = React.useState(null)
  const [updateDismissed, setUpdateDismissed] = React.useState(false)
  const updateInfoRef = React.useRef(null)
  const wsRef = React.useRef(null)
  const reconnectRef = React.useRef(null)
  const notifiedEventsRef = React.useRef(new Set())
  const startUpdateDownload = React.useCallback((payload) => {
    if (!payload?.downloadUrl || !payload?.signature) return

    localStorage.setItem('apk_update_baseline_signature', payload.signature)
    localStorage.removeItem('apk_update_skip_signature')
    localStorage.setItem('apk_update_last_notified_signature', payload.signature)
    window.location.href = payload.downloadUrl
    setUpdateInfo(null)
  }, [])

  const notifyNativeUpdate = React.useCallback(async (updatePayload) => {
    if (!isNativeApp || !updatePayload?.signature) return

    const notificationKey = 'apk_update_last_notified_signature'
    if (localStorage.getItem(notificationKey) === updatePayload.signature) return

    try {
      const { LocalNotifications } = await getLocalNotifications()
      const permission = await LocalNotifications.checkPermissions()
      if (permission.display !== 'granted') {
        const request = await LocalNotifications.requestPermissions()
        if (request.display !== 'granted') return
      }

      await LocalNotifications.schedule({
        notifications: [
          {
            id: Math.abs(updatePayload.signature.split('').reduce((acc, char) => acc + char.charCodeAt(0), 0)) % 2147483647,
            title: 'BarberMove atualizado',
            body: 'Existe uma nova versão pronta. Toque para abrir e atualizar.',
            schedule: { at: new Date(Date.now() + 2000) },
            extra: {
              type: 'apk_update_available',
              downloadUrl: updatePayload.downloadUrl,
              signature: updatePayload.signature,
            },
          },
        ],
      })

      localStorage.setItem(notificationKey, updatePayload.signature)
    } catch (_error) {
      // Se a permissão ou o plugin falhar, o modal continua funcionando.
    }
  }, [])

  const buildRealtimeAlert = React.useCallback((message) => {
    const type = message?.type || message?.tipo

    switch (type) {
      case 'novo_chamado':
        return {
          title: 'Novo serviço disponível',
          body: `${message?.nome_cliente || 'Um cliente'} pediu ${message?.nome_servico || 'um serviço'}${message?.nome_barbearia ? ` em ${message.nome_barbearia}` : ''}.`,
        }
      case 'chamado_aceito':
        return {
          title: 'Serviço aceito',
          body: 'Seu serviço foi aceito e o atendimento já pode seguir.',
        }
      case 'chamado_recusado':
        return {
          title: 'Serviço recusado',
          body: 'O pedido recebeu uma recusa. Verifique outros profissionais.',
        }
      case 'chamado_em_atendimento':
        return {
          title: 'Atendimento iniciado',
          body: 'O atendimento entrou em andamento.',
        }
      case 'chamado':
      case 'agendamento':
      case 'agendamento_confirmado':
        return {
          title: 'Agendamento atualizado',
          body: message?.mensagem || 'Seu agendamento teve uma atualizacao.',
        }
      case 'agendamento_cancelado':
        return {
          title: 'Agendamento cancelado',
          body: message?.mensagem || 'Um agendamento foi cancelado.',
        }
      case 'pagamento_confirmado':
        return {
          title: 'Pagamento confirmado',
          body: message?.mensagem || 'Pagamento confirmado com sucesso.',
        }
      case 'saque_processado':
        return {
          title: 'Saque processado',
          body: message?.mensagem || 'Seu saque foi processado.',
        }
      case 'perfil_aprovado':
        return {
          title: 'Perfil aprovado',
          body: message?.mensagem || 'Seu perfil foi aprovado.',
        }
      case 'chamado_chegada_atualizada':
        return {
          title: 'Chegada atualizada',
          body: 'A confirmação de chegada foi atualizada no servidor.',
        }
      case 'tracking_update':
        return {
          title: 'Rastreamento atualizado',
          body: 'A posição do atendimento foi atualizada.',
        }
      case 'cadeira_acionada_aberta':
        return {
          title: 'Vaga relâmpago aberta',
          body: 'Uma nova vaga apareceu perto de você.',
        }
      case 'cadeira_acionada_fechada':
        return {
          title: 'Vaga relâmpago encerrada',
          body: `A vaga foi aceita por ${message?.accepted_by === 'barbeiro' ? 'um barbeiro' : 'um cliente'}.`,
        }
      default:
        return null
    }
  }, [])

  const emitRealtimeAlert = React.useCallback(async (message) => {
    const alert = buildRealtimeAlert(message)
    if (!alert) return

    const eventKey = JSON.stringify({
      type: message?.type || message?.tipo || 'evento',
      chamado_id: message?.chamado_id,
      vaga_id: message?.vaga?.id || message?.vaga_id,
      status: message?.status,
      accepted_by: message?.accepted_by,
    })

    if (notifiedEventsRef.current.has(eventKey)) return
    notifiedEventsRef.current.add(eventKey)
    if (notifiedEventsRef.current.size > 40) {
      notifiedEventsRef.current = new Set(Array.from(notifiedEventsRef.current).slice(-20))
    }

    notify(alert.body, 'info')

    if (!isNativeApp) return

    try {
      const { LocalNotifications } = await getLocalNotifications()
      const permission = await LocalNotifications.checkPermissions()
      if (permission.display !== 'granted') {
        const request = await LocalNotifications.requestPermissions()
        if (request.display !== 'granted') return
      }

      const notificationId = Math.abs(eventKey.split('').reduce((acc, char) => acc + char.charCodeAt(0), 0)) % 2147483647

      await LocalNotifications.schedule({
        notifications: [
          {
            id: notificationId,
            title: alert.title,
            body: alert.body,
            schedule: { at: new Date(Date.now() + 800) },
            extra: {
              eventKey,
              type: message?.type || message?.tipo,
            },
          },
        ],
      })
    } catch (_error) {
      // Se a notificação nativa falhar, o toast no app continua funcionando.
    }
  }, [buildRealtimeAlert, notify])

  const fetchUpdateInfo = React.useCallback(async () => {
    try {
      if (!apiRootForApk) return

      const res = await fetch(`${apiRootForApk}/apk/info`, { cache: 'no-store' })
      if (!res.ok) return

      const data = await res.json()
      if (data?.status !== 'ok') return

      const signature = data.latest_signature || `${data.latest_filename}:${data.latest_mtime_epoch}:${data.latest_size_bytes}`
      const baselineKey = 'apk_update_baseline_signature'
      const skipKey = 'apk_update_skip_signature'

      const baseline = localStorage.getItem(baselineKey)
      if (!baseline) {
        localStorage.setItem(baselineKey, signature)
        return
      }

      if (signature === baseline || signature === localStorage.getItem(skipKey)) {
        return
      }

      const nextUpdateInfo = {
        signature,
        filename: data.latest_filename,
        downloadUrl: data.download_url || data.latest_url || `${apiRootForApk}/downloads/${data.latest_filename}`,
        isNative: isNativeApp,
      }

      setUpdateInfo(nextUpdateInfo)
      setUpdateDismissed(false)

      if (isNativeApp) {
        await notifyNativeUpdate(nextUpdateInfo)
      }
    } catch (_err) {
      // Silencioso para nao quebrar a UX caso a API esteja indisponivel.
    }
  }, [apiRootForApk, notifyNativeUpdate])

  React.useEffect(() => {
    updateInfoRef.current = updateInfo
  }, [updateInfo])

  React.useEffect(() => {
    if (!isNativeApp) return undefined

    let cleanup = null

    const attachNotificationClickHandler = async () => {
      try {
        const { LocalNotifications } = await getLocalNotifications()
        const listener = await LocalNotifications.addListener('localNotificationActionPerformed', (event) => {
          const extra = event?.notification?.extra || {}
          const activeUpdate = updateInfoRef.current

          if ((extra?.type || extra?.kind) === 'apk_update_available') {
            startUpdateDownload({
              signature: extra?.signature || activeUpdate?.signature,
              downloadUrl: extra?.downloadUrl || activeUpdate?.downloadUrl,
            })
          }
        })

        cleanup = () => {
          try {
            listener?.remove?.()
          } catch (_error) {
            // Ignora falhas de cleanup de listener.
          }
        }
      } catch (_error) {
        // Sem plugin/permissao: seguimos sem interacao via toque na notificacao.
      }
    }

    attachNotificationClickHandler()

    return () => {
      if (cleanup) cleanup()
    }
  }, [startUpdateDownload])

  React.useEffect(() => {
    fetchUpdateInfo()
    const intervalId = window.setInterval(fetchUpdateInfo, isNativeApp ? 6 * 60 * 1000 : 10 * 60 * 1000)

    return () => window.clearInterval(intervalId)
  }, [fetchUpdateInfo])

  React.useEffect(() => {
    if (!isNativeApp) return

    const handleFocus = () => fetchUpdateInfo()
    window.addEventListener('focus', handleFocus)

    return () => window.removeEventListener('focus', handleFocus)
  }, [fetchUpdateInfo])

  React.useEffect(() => {
    if (!token) return undefined

    const connect = () => {
      try {
        const ws = new WebSocket(getWsBaseUrl())

        ws.onopen = () => {
          ws.send(JSON.stringify({ tipo: 'auth', token }))
        }

        ws.onmessage = async (event) => {
          try {
            const payload = JSON.parse(event.data)
            await emitRealtimeAlert(payload)
          } catch (_error) {
            // Mensagem não JSON ou inválida.
          }
        }

        ws.onerror = () => {
          // Reconnect acontece no onclose.
        }

        ws.onclose = () => {
          if (reconnectRef.current) window.clearTimeout(reconnectRef.current)
          reconnectRef.current = window.setTimeout(connect, 5000)
        }

        wsRef.current = ws
      } catch (_error) {
        if (reconnectRef.current) window.clearTimeout(reconnectRef.current)
        reconnectRef.current = window.setTimeout(connect, 5000)
      }
    }

    connect()

    return () => {
      if (reconnectRef.current) {
        window.clearTimeout(reconnectRef.current)
        reconnectRef.current = null
      }
      if (wsRef.current) {
        wsRef.current.close()
        wsRef.current = null
      }
    }
  }, [token, emitRealtimeAlert])

  const handleDownloadUpdate = () => {
    startUpdateDownload(updateInfo)
  }

  const handleSkipUpdate = () => {
    if (!updateInfo?.signature) return
    localStorage.setItem('apk_update_skip_signature', updateInfo.signature)
    localStorage.setItem('apk_update_last_notified_signature', updateInfo.signature)
    setUpdateInfo(null)
  }

  const handleDismissUpdate = () => {
    setUpdateDismissed(true)
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

    if (userType === 'admin') {
      return <AdminDashboard token={token} logout={logout} notify={notify} API_URL={API_URL} />
    }

    return <Login />
  }

  return (
    <div className="min-h-screen w-full bg-[#050507] flex justify-center items-start overflow-x-hidden">
      <div className="relative w-full max-w-[430px] min-h-screen bg-[#0a0a0c] shadow-[0_0_60px_rgba(0,0,0,0.8)] overflow-hidden">
        {updateInfo && !isNativeApp && (
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
          {updateInfo && !updateDismissed && isNativeApp && (
            <AppUpdateModal
              updateInfo={updateInfo}
              onUpdateNow={handleDownloadUpdate}
              onLater={handleSkipUpdate}
              onClose={handleDismissUpdate}
            />
          )}

          <div className="w-full">
            {token ? renderDashboard() : <Login />}
          </div>
        </div>

      </div>
    </div>
  )
}
