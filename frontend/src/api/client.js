import axios from 'axios'

import { API_URL } from '../config/env'
import { normalizeApiError } from '../components/forms/formErrorUtils'
import { clearAccessToken, getAccessToken, runRefreshHandler } from './tokenStore'
import { completeEconomicIntent, economicIntent, isEconomicWrite } from './economicIntent'

export const apiClient = axios.create({
  baseURL: API_URL,
  withCredentials: true,
})

apiClient.interceptors.request.use((config) => {
  const token = getAccessToken()
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  if (isEconomicWrite(config) && !config.headers['Idempotency-Key']) {
    // A session refresh may change the token, but not the account's identity.
    let actor = 'session'
    try {
      actor = JSON.parse(atob(token.split('.')[1].replace(/-/g, '+').replace(/_/g, '/'))).sub || actor
    } catch { /* Server validates auth. */ }
    const intent = economicIntent(config, actor)
    config.headers['Idempotency-Key'] = intent.key
    config._economicIntent = intent.signature
  }
  return config
})

apiClient.interceptors.response.use(
  (response) => {
    if (response.config._economicIntent) completeEconomicIntent(response.config._economicIntent)
    return response
  },
  async (error) => {
    const originalRequest = error.config
    const requestPath = originalRequest?.url || ''

    if (
      error.response?.status === 401 &&
      !originalRequest?._retry &&
      !requestPath.includes('/auth/login') &&
      !requestPath.includes('/auth/refresh')
    ) {
      originalRequest._retry = true

      // Fetch streams on rejected HTTP responses must be closed before refresh.
      // Do not abort the request signal: the authenticated retry reuses it.
      originalRequest._abortLenyFetch?.()
      if (typeof error.response?.data?.cancel === 'function') {
        try { error.response.data.cancel().catch(() => {}) } catch { /* Already closed. */ }
      }

      try {
        const session = await runRefreshHandler()
        originalRequest.headers.Authorization = `Bearer ${session.access_token}`
        return apiClient(originalRequest)
      } catch (refreshError) {
        clearAccessToken()
        return Promise.reject(refreshError)
      }
    }

    error.normalizedError = normalizeApiError(error)

    return Promise.reject(error)
  },
)
