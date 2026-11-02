import { apiClient } from '../../api/client'
import { normalizeApiError } from '../../components/forms/formErrorUtils'
import { validLenySources } from './lenySourceUtils'

const MAX_LINE_BYTES = 65536
const MAX_OUTPUT_BYTES = 65536

export function lenyStreamErrorMessage(event) {
  if (['LENY_RAG_CONTEXT_LIMIT', 'LENY_CONTEXT_LIMIT'].includes(event?.code)) return 'Las fuentes no caben íntegramente en el contexto disponible. Precisa la sección que necesitas; esto no significa que falte documentación.'
  if (event?.code === 'LENY_RAG_REVIEW_INVALID') return 'No se pudo verificar la pertinencia de las fuentes. La consulta documental no se completó.'
  if (event?.code === 'LENY_RAG_CITATION_MISSING') return 'La respuesta no incluyó referencias verificables y no pudo completarse.'
  if (['LENY_RAG_SOURCE_REVOKED', 'LENY_RAG_ACCESS_REVOKED'].includes(event?.code)) return 'La fuente o tu autorización dejó de estar disponible. La respuesta se interrumpió.'
  if (event?.code === 'LENY_OUTPUT_BLOCKED') return 'La respuesta se interrumpió por seguridad. Reformula tu consulta empresarial.'
  if (['LENY_TOTAL_TIMEOUT', 'LENY_FIRST_TOKEN_TIMEOUT', 'LENY_IDLE_TIMEOUT', 'LENY_COMMUNICATION_TIMEOUT'].includes(event?.code)) {
    return 'El modelo superó el tiempo de espera. Consulta el historial antes de enviar una nueva solicitud.'
  }
  if (['LENY_UNAVAILABLE', 'LENY_CONNECT_TIMEOUT', 'LENY_MODEL_MISSING'].includes(event?.code)) return 'El modelo local no está disponible. Comprueba el servicio e intenta más tarde.'
  return 'La respuesta no pudo completarse. Consulta el historial para revisar su estado.'
}

async function cancelReader(reader) {
  let timer
  try {
    await Promise.race([reader.cancel().catch(() => {}), new Promise((resolve) => { timer = setTimeout(resolve, 250) })])
  } finally { clearTimeout(timer) }
}

export function lenyErrorMessage(error) {
  if (error?.code === 'ERR_CANCELED' || error?.name === 'AbortError') return 'La respuesta se interrumpió.'
  const status = error?.response?.status
  if (status === 401) return 'Tu sesión terminó. Vuelve a iniciar sesión para utilizar LENY.'
  if (status === 403) return 'Tu cuenta no tiene autorización para esta operación de LENY.'
  const detail = error?.response?.data?.detail
  if (status === 503) return detail?.code === 'LENY_STORAGE_UNAVAILABLE'
    ? 'El historial de LENY no está disponible. Solicita al administrador que revise el servicio.'
    : 'El servicio local de LENY no está disponible. Comprueba su estado e intenta más tarde.'
  if (status === 429) return detail?.code === 'LENY_RATE_LIMITED'
    ? 'Alcanzaste el límite de uso de LENY. Espera antes de enviar otro mensaje.'
    : 'LENY está atendiendo otra solicitud. Espera antes de volver a enviar.'
  if (status && status !== 422) return 'No se pudo completar la solicitud de LENY. Consulta el historial antes de volver a enviarla.'
  if (typeof detail === 'string') return detail
  if (typeof detail?.message === 'string') return detail.message
  return error?.normalizedError?.summary || 'No se pudo comunicar con LENY. Intenta nuevamente.'
}

export function lenyRetrySeconds(error, now = Date.now()) {
  if (error?.response?.status !== 429) return 0
  const headers = error.response.headers
  const raw = headers?.get?.('retry-after') ?? headers?.['retry-after'] ?? headers?.['Retry-After']
  const seconds = typeof raw === 'string' && !/^\s*\d+(\.\d+)?\s*$/.test(raw)
    ? (Date.parse(raw) - now) / 1000 : Number(raw)
  return Number.isFinite(seconds) && seconds > 0 ? Math.min(86400, Math.ceil(seconds)) : 3
}

/** Decode NDJSON across arbitrary UTF-8/chunk boundaries, with bounded buffers. */
export async function readLenyStream(stream, onEvent, signal, beforeCancel) {
  const reader = stream.getReader()
  const decoder = new TextDecoder('utf-8', { fatal: true })
  const encoder = new TextEncoder()
  let pending = ''
  let outputBytes = 0
  let terminal = false
  const aborted = () => reader.cancel().catch(() => {})
  signal?.addEventListener('abort', aborted, { once: true })
  function parse(line) {
    if (!line.trim()) return
    if (encoder.encode(line).byteLength > MAX_LINE_BYTES) throw new Error('La respuesta excedió el límite permitido.')
    const event = JSON.parse(line)
    if (!['start', 'delta', 'done', 'error'].includes(event.type)) throw new Error('LENY devolvió una respuesta no válida.')
    if (event.type === 'done' && event.sources !== undefined && !validLenySources(event.sources)) throw new Error('LENY devolvió fuentes no válidas.')
    if (event.type === 'delta') {
      if (typeof event.text !== 'string') throw new Error('LENY devolvió un fragmento no válido.')
      outputBytes += encoder.encode(event.text).byteLength
      if (outputBytes > MAX_OUTPUT_BYTES) throw new Error('La respuesta excedió el límite permitido.')
    }
    terminal = event.type === 'done' || event.type === 'error'
    onEvent(event)
  }
  try {
    while (!terminal) {
      if (signal?.aborted) throw new DOMException('Solicitud interrumpida', 'AbortError')
      const { done, value } = await reader.read()
      if (done) {
        pending += decoder.decode()
        if (pending.trim()) parse(pending)
        if (!terminal) throw new Error('La conexión terminó antes de completar la respuesta.')
        break
      }
      pending += decoder.decode(value, { stream: true })
      let newline
      while ((newline = pending.indexOf('\n')) !== -1) {
        const line = pending.slice(0, newline)
        pending = pending.slice(newline + 1)
        parse(line)
        if (terminal) break
      }
      if (encoder.encode(pending).byteLength > MAX_LINE_BYTES) throw new Error('La respuesta excedió el límite permitido.')
    }
  } finally {
    signal?.removeEventListener('abort', aborted)
    beforeCancel?.()
    await cancelReader(reader)
    reader.releaseLock()
  }
}

export async function sendLenyMessage(payload, { signal, onEvent, timeoutSeconds = 120 }) {
  const controller = new AbortController()
  const underlyingFetch = apiClient.defaults.env?.fetch || globalThis.fetch
  let abortAttempt = () => {}
  // Every authenticated HTTP attempt owns its network signal. The shared 401
  // interceptor can close the old response without cancelling the JWT retry.
  const lenyFetch = async (request, options) => {
    abortAttempt()
    const attempt = new AbortController()
    const sourceSignal = request.signal || options?.signal
    const abort = () => attempt.abort()
    sourceSignal?.addEventListener('abort', abort, { once: true })
    if (sourceSignal?.aborted) attempt.abort()
    abortAttempt = () => { attempt.abort(); sourceSignal?.removeEventListener('abort', abort) }
    const isolatedRequest = new Request(request, { signal: attempt.signal })
    return underlyingFetch(isolatedRequest, { ...options, signal: attempt.signal })
  }
  const onAbort = () => controller.abort()
  if (signal?.aborted) controller.abort()
  signal?.addEventListener('abort', onAbort, { once: true })
  let timedOut = false
  const timeout = setTimeout(() => { timedOut = true; controller.abort() }, (timeoutSeconds + 10) * 1000)
  try {
    const response = await apiClient.post('/leny/chat', payload, {
      adapter: 'fetch', responseType: 'stream', signal: controller.signal,
      headers: { Accept: 'application/x-ndjson' },
      env: { ...apiClient.defaults.env, fetch: lenyFetch },
      _abortLenyFetch: () => abortAttempt(),
    })
    await readLenyStream(response.data, onEvent, controller.signal, () => abortAttempt())
  } catch (error) {
    // Axios fetch returns error bodies as streams too. Read JSON only for bounded,
    // local HTTP errors; the shared interceptor has already handled JWT refresh.
    const body = error?.response?.data
    if (body?.getReader && !controller.signal.aborted) {
      const reader = body.getReader()
      const decoder = new TextDecoder()
      const cancelErrorReader = () => { abortAttempt(); reader.cancel().catch(() => {}) }
      controller.signal.addEventListener('abort', cancelErrorReader, { once: true })
      const errorDeadline = setTimeout(cancelErrorReader, 3000)
      let text = ''
      let size = 0
      try {
        while (true) {
          const { value, done } = await reader.read()
          if (done) break
          size += value.byteLength
          if (size > MAX_LINE_BYTES) break
          text += decoder.decode(value, { stream: true })
        }
        if (size <= MAX_LINE_BYTES) error.response.data = JSON.parse(text + decoder.decode())
      } catch { /* Keep the safe fallback error. */ }
      finally {
        controller.signal.removeEventListener('abort', cancelErrorReader)
        clearTimeout(errorDeadline)
        abortAttempt()
        await cancelReader(reader); reader.releaseLock()
      }
      error.normalizedError = normalizeApiError(error)
    }
    if (timedOut) throw new Error('LENY superó el tiempo de respuesta. El historial conservará el resultado disponible.')
    throw error
  } finally {
    clearTimeout(timeout)
    abortAttempt()
    signal?.removeEventListener('abort', onAbort)
  }
}
