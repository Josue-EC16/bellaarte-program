import { useCallback, useEffect, useMemo, useState } from 'react'

import { apiClient } from '../../api/client'

function normalizeParams(params) {
  return Object.fromEntries(
    Object.entries(params || {}).filter(([, value]) => value !== undefined && value !== null && value !== ''),
  )
}

export function useListingSummary(endpoint, params) {
  const normalizedParams = useMemo(() => normalizeParams(params), [params])
  const [summary, setSummary] = useState(null)
  const [loading, setLoading] = useState(true)

  const loadSummary = useCallback(async () => {
    setLoading(true)
    try {
      const response = await apiClient.get(endpoint, { params: normalizedParams })
      setSummary(response.data)
    } catch {
      setSummary(null)
    } finally {
      setLoading(false)
    }
  }, [endpoint, normalizedParams])

  useEffect(() => {
    loadSummary()
  }, [loadSummary])

  return { summary, loading, reload: loadSummary }
}
