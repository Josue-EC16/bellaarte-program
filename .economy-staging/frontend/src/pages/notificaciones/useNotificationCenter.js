import { useCallback, useEffect, useRef, useState } from 'react'

import { apiClient } from '../../api/client'
import { buildNotificationOriginPath } from './notificationUtils'
import { createNotificationPoller, notifyNotificationsChanged, presentDesktopNotifications } from './notificationTransport'

const EMPTY_SUMMARY = { unread_count: 0, unresolved_count: 0, urgent_count: 0, latest: [] }

export function useNotificationCenter(user, navigate) {
  const [summary, setSummary] = useState(EMPTY_SUMMARY)
  const [error, setError] = useState(null)
  const [reading, setReading] = useState([])
  const pendingReads = useRef(new Set())
  const poller = useRef(null)
  const canUse = Boolean(user?.permissions?.includes('notifications:list'))
  const userId = user?.id ?? user?.user_id

  useEffect(() => {
    setSummary(EMPTY_SUMMARY)
    setError(null)
    if (!canUse) return undefined
    let active = true
    const instance = createNotificationPoller({
      async load(signal) {
        const [response, preferences] = await Promise.all([
          apiClient.get('/notificaciones/resumen', { signal }),
          apiClient.get('/notificaciones/preferencias', { signal }),
        ])
        if (active && preferences.data.desktop_enabled && window.Notification?.permission === 'granted') {
          const claimed = await apiClient.post('/notificaciones/escritorio/reclamar', {}, { signal })
          if (active) {
            presentDesktopNotifications(claimed.data.items, window.Notification, (item) => {
              if (!active) return
              window.focus()
              apiClient.patch(`/notificaciones/${item.id}/read`, { revision: item.revision })
                .then(() => notifyNotificationsChanged())
                .catch(() => setError('No fue posible reconocer el aviso. Puedes hacerlo desde la campana.'))
              navigate(buildNotificationOriginPath(item))
            })
          }
        }
        return response.data
      },
      onData(data) { setSummary(data); setError(null) },
      onError() { setError('No se pudieron actualizar las notificaciones. Reintenta para ver el estado actual.') },
    })
    poller.current = instance
    return () => {
      active = false
      instance.stop()
      poller.current = null
    }
  }, [canUse, userId, navigate])

  const refresh = useCallback(() => poller.current?.refresh(), [])
  const markRead = useCallback(async (notification) => {
    if (pendingReads.current.has(notification.id)) return
    pendingReads.current.add(notification.id)
    setReading([...pendingReads.current])
    try {
      await apiClient.patch(`/notificaciones/${notification.id}/read`, { revision: notification.revision })
      notifyNotificationsChanged()
    } catch (requestError) {
      setError(requestError.response?.data?.detail || 'No se pudo marcar la notificación como leída.')
    } finally {
      pendingReads.current.delete(notification.id)
      setReading([...pendingReads.current])
    }
  }, [])
  return { summary, error, refresh, markRead, reading, canUse }
}
