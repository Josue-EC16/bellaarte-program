import { clearEconomicIntents } from './economicIntent'

let accessToken = null
let refreshHandler = null
let sessionHandler = null
let refreshPromise = null
let sessionGeneration = 0
let requestsController = new AbortController()
let logoutRequested = false
export const LOGOUT_REQUESTED_KEY = 'bab-vdos-logout-requested'

export function isLogoutRequested() {
  try { return logoutRequested || globalThis.localStorage?.getItem(LOGOUT_REQUESTED_KEY) === 'true' }
  catch { return logoutRequested }
}

export function markLogoutRequested() {
  logoutRequested = true
  try { globalThis.localStorage?.setItem(LOGOUT_REQUESTED_KEY, 'true') } catch { /* Keep the in-memory intent. */ }
}

export function clearLogoutRequest() {
  logoutRequested = false
  try { globalThis.localStorage?.removeItem(LOGOUT_REQUESTED_KEY) } catch { /* Storage may be disabled. */ }
}

export function getAccessToken() {
  return accessToken
}

export function setAccessToken(token) {
  accessToken = token
}

export function clearAccessToken() {
  sessionGeneration += 1
  requestsController.abort()
  requestsController = new AbortController()
  clearEconomicIntents()
  accessToken = null
}

export function getSessionGeneration() {
  return sessionGeneration
}

export function getSessionSignal() {
  return requestsController.signal
}

export function registerSessionHandler(handler) {
  sessionHandler = handler
}

export function invalidateSession(code = 'SESSION_REVOKED') {
  clearAccessToken()
  sessionHandler?.({ type: 'revoked', code })
}

export function updateSessionUser(user) {
  sessionHandler?.({ type: 'session', user })
}

export function registerRefreshHandler(handler) {
  refreshHandler = handler
}

export async function runRefreshHandler() {
  if (isLogoutRequested()) throw new Error('El cierre de sesión requiere un nuevo ingreso explícito.')
  if (!refreshHandler) {
    throw new Error('No existe un handler de refresh registrado')
  }

  if (!refreshPromise) {
    const handler = refreshHandler
    const generation = sessionGeneration
    // Tabs share the HttpOnly refresh cookie, but never share or persist tokens.
    // Serialize cookie rotation across tabs as well as concurrent requests here.
    const run = () => {
      if (isLogoutRequested() || generation !== sessionGeneration || refreshHandler !== handler) throw new Error('La sesión terminó antes de renovarse.')
      return handler()
    }
    refreshPromise = (globalThis.navigator?.locks?.request
      ? navigator.locks.request('bab-vdos-session-refresh', run)
      : Promise.resolve().then(run)).finally(() => { refreshPromise = null })
  }
  return refreshPromise
}
