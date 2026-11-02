import { describe, expect, it, vi } from 'vitest'
import { lenyErrorMessage, lenyRetrySeconds, lenyStreamErrorMessage, readLenyStream, sendLenyMessage } from './lenyTransport'
import { apiClient } from '../../api/client'

function stream(text, size = 1) {
  const bytes = new TextEncoder().encode(text)
  let index = 0
  return new ReadableStream({ pull(controller) {
    if (index >= bytes.length) controller.close()
    else { controller.enqueue(bytes.slice(index, index + size)); index += size }
  } })
}

describe('LENY NDJSON streaming boundaries and cancellation', () => {
  it('explains output protection and local availability without echoing server details', () => {
    expect(lenyStreamErrorMessage({ code: 'LENY_RAG_CONTEXT_LIMIT', message: 'private detail' })).toContain('no significa que falte documentación')
    expect(lenyStreamErrorMessage({ code: 'LENY_RAG_REVIEW_INVALID', message: 'private detail' })).toContain('pertinencia')
    expect(lenyStreamErrorMessage({ code: 'LENY_RAG_CITATION_MISSING', message: 'private detail' })).toContain('referencias verificables')
    expect(lenyStreamErrorMessage({ code: 'LENY_RAG_SOURCE_REVOKED', message: 'private detail' })).toContain('interrumpió')
    expect(lenyStreamErrorMessage({ code: 'LENY_OUTPUT_BLOCKED', message: 'private detail' })).toContain('seguridad')
    expect(lenyStreamErrorMessage({ code: 'LENY_IDLE_TIMEOUT' })).toContain('tiempo de espera')
    expect(lenyStreamErrorMessage({ code: 'UNKNOWN', message: 'private detail' })).not.toContain('private')
    expect(lenyErrorMessage({ response: { status: 503, data: { detail: { code: 'LENY_STORAGE_UNAVAILABLE', message: 'private detail' } } } })).toContain('historial')
  })
  it('uses Retry-After seconds or dates and keeps quota errors safe', () => {
    const now = Date.UTC(2026, 9, 19)
    const failure = { response: { status: 429, headers: { 'retry-after': '17' }, data: { detail: { code: 'LENY_RATE_LIMITED', message: 'secret' } } } }
    expect(lenyRetrySeconds(failure, now)).toBe(17)
    failure.response.headers = new Headers({ 'Retry-After': new Date(now + 12000).toUTCString() })
    expect(lenyRetrySeconds(failure, now)).toBe(12)
    failure.response.headers = { 'retry-after': 'invalid' }
    expect(lenyRetrySeconds(failure, now)).toBe(3)
    expect(lenyErrorMessage(failure)).toContain('límite de uso')
    for (const status of [401, 403, 429, 500]) {
      expect(lenyErrorMessage({ response: { status, data: { detail: { message: 'secret internal path' } } } })).not.toContain('secret')
    }
  })
  it('decodes accented UTF-8 split byte by byte and an unterminated final line', async () => {
    const events = []
    await readLenyStream(stream('{"type":"start"}\n{"type":"delta","text":"¡Sí, confección!"}\n{"type":"done","status":"completed"}'), (event) => events.push(event))
    expect(events.map((event) => event.type)).toEqual(['start', 'delta', 'done'])
    expect(events[1].text).toBe('¡Sí, confección!')
  })
  it('rejects premature EOF, malformed fragments, and oversized lines', async () => {
    await expect(readLenyStream(stream('{"type":"delta","text":"Parcial"}\n'), () => {})).rejects.toThrow('antes de completar')
    await expect(readLenyStream(stream('{"type":"delta","text":7}\n'), () => {})).rejects.toThrow('fragmento')
    await expect(readLenyStream(stream('a'.repeat(65537), 65537), () => {})).rejects.toThrow('límite')
  })
  it('cancels the reader on server errors and local aborts', async () => {
    const cancel = vi.fn()
    const controller = new AbortController()
    const waiting = new ReadableStream({ cancel })
    const reading = readLenyStream(waiting, () => {}, controller.signal)
    controller.abort()
    await expect(reading).rejects.toThrow()
    expect(cancel).toHaveBeenCalledOnce()
    const errors = []
    await readLenyStream(stream('{"type":"error","code":"LENY_TIMEOUT","message":"Tiempo agotado"}\n'), (event) => errors.push(event))
    expect(errors[0].code).toBe('LENY_TIMEOUT')
  })
  it('retains the request id, fetch adapter and AbortSignal through the shared client', async () => {
    const post = vi.spyOn(apiClient, 'post').mockResolvedValue({ data: stream('{"type":"done","status":"completed"}\n') })
    const payload = { conversation_id: 'conversation', request_id: 'stable-request', message: 'Hola' }
    try {
      await sendLenyMessage(payload, { signal: new AbortController().signal, onEvent: () => {} })
      expect(post.mock.calls[0][0]).toBe('/leny/chat')
      expect(post.mock.calls[0][1]).toBe(payload)
      expect(post.mock.calls[0][2]).toMatchObject({ adapter: 'fetch', responseType: 'stream' })
      expect(post.mock.calls[0][2].signal).toBeInstanceOf(AbortSignal)
    } finally { post.mockRestore() }
  })
  it('decodes bounded HTTP conflict details without retrying the generation', async () => {
    const failure = { response: { status: 409, data: stream('{"detail":{"code":"LENY_REQUEST_DUPLICATE","status":"interrupted"}}') } }
    const post = vi.spyOn(apiClient, 'post').mockRejectedValue(failure)
    try {
      await expect(sendLenyMessage({}, { onEvent: () => {} })).rejects.toMatchObject({ response: { data: { detail: { code: 'LENY_REQUEST_DUPLICATE' } } } })
      expect(post).toHaveBeenCalledOnce()
    } finally { post.mockRestore() }
  })
  it('renormalizes decoded stream422 details for the existing form field resolver', async () => {
    const failure = { response: { status: 422, data: stream('{"detail":[{"loc":["body","message"],"msg":"Mensaje demasiado largo","type":"value_error"}]}') } }
    const post = vi.spyOn(apiClient, 'post').mockRejectedValue(failure)
    try {
      await expect(sendLenyMessage({}, { onEvent: () => {} })).rejects.toMatchObject({
        normalizedError: { status: 422, issues: [{ location: ['message'], message: 'Mensaje demasiado largo' }] },
      })
    } finally { post.mockRestore() }
  })
})
