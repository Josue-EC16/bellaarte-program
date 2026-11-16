import axios from 'axios'

import { API_URL } from '../config/env'
import { normalizeApiError } from '../components/forms/formErrorUtils'
import {
  getAccessToken, getSessionGeneration, getSessionSignal, invalidateSession,
  runRefreshHandler, updateSessionUser,
} from './tokenStore'
import { completeEconomicIntent, economicIntent, isEconomicWrite } from './economicIntent'

export const apiClient = axios.create({
  baseURL: API_URL,
  withCredentials: true,
})

const REVOKED_CODES = new Set(['SESSION_REVOKED', 'SESSION_EXPIRED', 'SESSION_INVALID',
  'ACCOUNT_DISABLED', 'ACCOUNT_INACTIVE', 'TOKEN_INVALID', 'REFRESH_TOKEN_REUSED', 'SESSION_TOKEN_REUSED'])

function sessionSignal(config) {
  config._callerSignal ??= config.signal
  const sources = [config._callerSignal, getSessionSignal()].filter(Boolean)
  if (typeof AbortSignal.any === 'function') return AbortSignal.any(sources)
  const controller = new AbortController()
  const abort = () => controller.abort()
  for (const source of sources) {
    if (source.aborted) abort()
    else source.addEventListener('abort', abort, { once: true })
  }
  config._releaseSessionSignal = () => sources.forEach((source) => source.removeEventListener('abort', abort))
  return controller.signal
}

async function decodeAuthenticationError(error) {
  const body = error.response?.data
  const contentType = error.response?.headers?.get?.('content-type') || error.response?.headers?.['content-type'] || ''
  if (!body?.getReader || !contentType.includes('application/json')) return
  const reader = body.getReader()
  let timeout
  try {
    const decoded = (async () => {
      const decoder = new TextDecoder()
      let text = ''
      let size = 0
      while (true) {
        const { value, done } = await reader.read()
        if (done) break
        size += value.byteLength
        if (size > 65536) return
        text += decoder.decode(value, { stream: true })
      }
      return JSON.parse(text + decoder.decode())
    })()
    const data = await Promise.race([decoded, new Promise((resolve) => { timeout = setTimeout(resolve, 500) })])
    if (data) error.response.data = data
  } catch { /* Keep the safe HTTP fallback for malformed responses. */ }
  finally {
    clearTimeout(timeout)
    reader.cancel().catch(() => {})
    try { reader.releaseLock() } catch { /* A timed-out read may still be cancelling. */ }
  }
}

apiClient.interceptors.request.use((config) => {
  config._sessionGeneration = getSessionGeneration()
  if (!config._sessionControl && !/^\/auth\/(login|refresh|logout|change-password)(?:$|\?)/.test(config.url || '')) {
    config.signal = sessionSignal(config)
  }
  const token = getAccessToken()
  if (token && !config._preserveAuthorization) {
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
    // Streaming responses keep their signal until the stream is cancelled or
    // the session ends; ordinary responses release listeners immediately.
    if (response.config.responseType !== 'stream') response.config._releaseSessionSignal?.()
    if (response.config._economicIntent) completeEconomicIntent(response.config._economicIntent)
    return response
  },
  async (error) => {
    const originalRequest = error.config
    const requestPath = originalRequest?.url || ''
    originalRequest?._releaseSessionSignal?.()
    if (axios.isCancel(error) || originalRequest?.signal?.aborted) return Promise.reject(error)
    if ([401, 403].includes(error.response?.status)) await decodeAuthenticationError(error)
    const detail = error.response?.data?.detail
    const code = detail?.code || error.response?.data?.code
    if (error.response?.status === 401 && REVOKED_CODES.has(code)) {
      if (originalRequest?._sessionGeneration === getSessionGeneration()) invalidateSession(code)
      error.normalizedError = normalizeApiError(error)
      return Promise.reject(error)
    }
    if (error.response?.status === 403 && code === 'PASSWORD_CHANGE_REQUIRED') {
      // Refresh user state so the existing route guard takes the user to the
      // mandatory password page; a normal permission denial never logs out.
      try {
        const response = await apiClient.get('/auth/me')
        updateSessionUser(response.data.user)
      } catch { /* A concurrent revocation is handled by its own response. */ }
    }

    if (
      error.response?.status === 401 &&
      originalRequest &&
      !originalRequest._skipAuthRefresh &&
      !originalRequest?._retry &&
      !requestPath.includes('/auth/login') &&
      !requestPath.includes('/auth/refresh')
    ) {
      originalRequest._retry = true

      // Fetch streams on rejected HTTP responses must be closed before refresh.
      // Do not abort the request signal: the authenticated retry reuses it.
      originalRequest._abortLenyFetch?.()
      originalRequest._abortAuthFetch?.()
      if (typeof error.response?.data?.cancel === 'function') {
        try { error.response.data.cancel().catch(() => {}) } catch { /* Already closed. */ }
      }

      try {
        const session = await runRefreshHandler()
        if (originalRequest._sessionGeneration !== getSessionGeneration() || originalRequest._callerSignal?.aborted) {
          return Promise.reject(new axios.CanceledError('La sesión terminó.'))
        }
        originalRequest.headers.Authorization = `Bearer ${session.access_token}`
        return apiClient(originalRequest)
      } catch (refreshError) {
        if (originalRequest._sessionGeneration === getSessionGeneration()) invalidateSession('SESSION_EXPIRED')
        return Promise.reject(refreshError)
      }
    }

    error.normalizedError = normalizeApiError(error)

    return Promise.reject(error)
  },
)
