export const NOTIFICATIONS_CHANGED = 'bab:notifications-changed'

export function notifyNotificationsChanged(target = window) {
  target.dispatchEvent(new Event(NOTIFICATIONS_CHANGED))
}

// One request at a time. Events received during a request coalesce into one refresh.
export function createNotificationPoller({ load, onData, onError, target = window, documentRef = document, intervalMs = 60000 }) {
  let active = true
  let current = null
  let queued = false
  let controller = null

  const refresh = () => {
    if (!active || documentRef.visibilityState === 'hidden') return Promise.resolve()
    if (current) {
      queued = true
      return current
    }
    controller = new AbortController()
    current = Promise.resolve()
      .then(() => load(controller.signal))
      .then((value) => { if (active) onData(value) })
      .catch((error) => {
        if (active && error?.name !== 'AbortError' && error?.code !== 'ERR_CANCELED') onError(error)
      })
      .finally(() => {
        current = null
        if (active && queued) {
          queued = false
          refresh()
        }
      })
    return current
  }
  const handleVisibility = () => {
    if (documentRef.visibilityState !== 'hidden') refresh()
  }
  const interval = target.setInterval(refresh, intervalMs)
  target.addEventListener('focus', refresh)
  target.addEventListener(NOTIFICATIONS_CHANGED, refresh)
  documentRef.addEventListener('visibilitychange', handleVisibility)
  refresh()
  return {
    refresh,
    stop() {
      active = false
      queued = false
      controller?.abort()
      target.clearInterval(interval)
      target.removeEventListener('focus', refresh)
      target.removeEventListener(NOTIFICATIONS_CHANGED, refresh)
      documentRef.removeEventListener('visibilitychange', handleVisibility)
    },
  }
}

export function presentDesktopNotifications(items, NotificationApi, onOpen) {
  if (!NotificationApi || NotificationApi.permission !== 'granted') return
  for (const item of items.slice(0, 3)) {
    try {
      const notice = new NotificationApi(item.titulo, {
        body: item.mensaje,
        tag: `bab-${item.id}-${item.revision}`,
      })
      notice.onclick = () => { notice.close(); onOpen(item) }
    } catch {
      // A claimed attempt is not released: the incident is still in the bell.
    }
  }
}
