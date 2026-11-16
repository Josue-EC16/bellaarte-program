import { apiClient } from './client'

const MAX_EVENT_BYTES = 65536

function validSessionEvent(event) {
  if (event?.type === 'heartbeat') return true
  if (['revoked', 'expired', 'unavailable'].includes(event?.type)) return typeof event.code === 'string'
  return event?.type === 'session' && Number.isInteger(event.user?.id) &&
    typeof event.user.role_code === 'string' && Array.isArray(event.user.permissions) &&
    event.user.permissions.every((permission) => typeof permission === 'string')
}

/** An authenticated stream through the same HTTP client used by the ERP. */
export async function watchSession({ signal, onEvent }) {
  const underlyingFetch = apiClient.defaults.env?.fetch || globalThis.fetch
  let abortAttempt = () => {}
  let response
  const fetch = async (request, options) => {
    abortAttempt()
    const controller = new AbortController()
    const sourceSignal = request.signal || options?.signal
    const abort = () => controller.abort()
    sourceSignal?.addEventListener('abort', abort, { once: true })
    if (sourceSignal?.aborted) abort()
    abortAttempt = () => { controller.abort(); sourceSignal?.removeEventListener('abort', abort) }
    return underlyingFetch(new Request(request, { signal: controller.signal }), { ...options, signal: controller.signal })
  }
  let reader
  const cancel = () => { abortAttempt(); reader?.cancel().catch(() => {}) }
  signal?.addEventListener('abort', cancel, { once: true })
  try {
    response = await apiClient.get('/auth/events', {
      adapter: 'fetch', responseType: 'stream', signal, timeout: 0,
      headers: { Accept: 'application/x-ndjson' },
      env: { ...apiClient.defaults.env, fetch }, _abortAuthFetch: () => abortAttempt(),
    })
    reader = response.data.getReader()
    const decoder = new TextDecoder('utf-8', { fatal: true })
    const encoder = new TextEncoder()
    let pending = ''
    let terminal = null
    const parse = (line) => {
      if (!line.trim()) return
      const event = JSON.parse(line)
      if (!validSessionEvent(event)) throw new Error('El aviso de sesión no es válido.')
      onEvent(event)
      if (['revoked', 'expired', 'unavailable'].includes(event.type)) terminal = event
    }
    while (!terminal && !signal?.aborted) {
      const { value, done } = await reader.read()
      if (done) {
        pending += decoder.decode()
        if (pending.trim()) parse(pending)
        break
      }
      pending += decoder.decode(value, { stream: true })
      let newline
      while ((newline = pending.indexOf('\n')) >= 0) {
        const line = pending.slice(0, newline)
        if (encoder.encode(line).byteLength > MAX_EVENT_BYTES) throw new Error('El aviso de sesión excedió el límite.')
        pending = pending.slice(newline + 1)
        parse(line)
        if (terminal) break
      }
      if (encoder.encode(pending).byteLength > MAX_EVENT_BYTES) throw new Error('El aviso de sesión excedió el límite.')
    }
    return terminal
  } finally {
    signal?.removeEventListener('abort', cancel)
    cancel()
    if (reader) {
      try { reader.releaseLock() } catch { /* Cancellation may still be settling. */ }
    }
    response?.config?._releaseSessionSignal?.()
  }
}

export function waitForSessionRetry(milliseconds, signal) {
  if (signal.aborted) return Promise.resolve()
  return new Promise((resolve) => {
    const finish = () => { clearTimeout(timer); signal.removeEventListener('abort', finish); resolve() }
    const timer = setTimeout(finish, milliseconds)
    signal.addEventListener('abort', finish, { once: true })
  })
}
