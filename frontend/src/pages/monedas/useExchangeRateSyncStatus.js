import { useCallback, useEffect, useRef, useState } from 'react'

import { apiClient } from '../../api/client'
import { exchangeRateActionError } from './exchangeRateUtils'
import { SYNC_BASE } from './exchangeRateSyncUtils'

export function useExchangeRateSyncStatus() {
  const [data, setData] = useState(null)
  const [error, setError] = useState(null)
  const [loading, setLoading] = useState(true)
  const mounted = useRef(false)
  const pending = useRef(null)

  const reload = useCallback(async ({ force = false } = {}) => {
    if (!mounted.current || (pending.current && !force)) return
    if (force) pending.current?.abort()
    const controller = new AbortController()
    pending.current = controller
    setLoading(true)
    try {
      const response = await apiClient.get(`${SYNC_BASE}/estado`, { signal: controller.signal })
      if (!controller.signal.aborted && mounted.current) {
        if (typeof response.data?.status !== 'string') throw new Error('Invalid status response')
        setData(response.data)
        setError(null)
      }
    } catch (requestError) {
      if (!controller.signal.aborted && mounted.current) setError(exchangeRateActionError(requestError, 'No fue posible consultar el estado de sincronización. El valor mostrado puede estar desactualizado.'))
    } finally {
      if (pending.current === controller) {
        pending.current = null
        if (mounted.current) setLoading(false)
      }
    }
  }, [])

  useEffect(() => {
    mounted.current = true
    const refreshVisible = () => { if (document.visibilityState !== 'hidden') reload() }
    refreshVisible()
    const interval = window.setInterval(refreshVisible, 60000)
    document.addEventListener('visibilitychange', refreshVisible)
    window.addEventListener('focus', refreshVisible)
    return () => {
      mounted.current = false
      window.clearInterval(interval)
      document.removeEventListener('visibilitychange', refreshVisible)
      window.removeEventListener('focus', refreshVisible)
      pending.current?.abort()
      pending.current = null
    }
  }, [reload])

  return { data, error, loading, reload }
}
