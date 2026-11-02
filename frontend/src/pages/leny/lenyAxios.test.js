import { afterEach, describe, expect, it, vi } from 'vitest'
import { apiClient } from '../../api/client'
import { clearAccessToken, registerRefreshHandler, setAccessToken } from '../../api/tokenStore'
import { lenyErrorMessage, lenyRetrySeconds, sendLenyMessage } from './lenyTransport'

const originalEnv = apiClient.defaults.env
afterEach(() => { apiClient.defaults.env = originalEnv; clearAccessToken(); registerRefreshHandler(null); vi.useRealTimers() })

describe('LENY actual Axios fetch adapter and shared interceptors', () => {
  it('preserves the quota Retry-After after JWT renewal and never retries the quota response', async () => {
    const seen = []
    const payload = { request_id: 'one-admission', conversation_id: 'private', message: 'Ayuda al Taller' }
    apiClient.defaults.env = { ...originalEnv, fetch: async (request) => {
      seen.push(JSON.parse(await request.text()))
      return seen.length === 1
        ? new Response('{"detail":"Session expired"}', { status: 401 })
        : new Response('{"detail":{"code":"LENY_RATE_LIMITED","message":"private-internal"}}', { status: 429, headers: { 'Retry-After': '27' } })
    } }
    registerRefreshHandler(async () => { setAccessToken('fresh'); return { access_token: 'fresh' } })
    let failure
    try { await sendLenyMessage(payload, { onEvent: () => {} }) } catch (error) { failure = error }
    expect(seen).toEqual([payload, payload])
    expect(lenyRetrySeconds(failure)).toBe(27)
    expect(lenyErrorMessage(failure)).toContain('límite de uso')
    expect(lenyErrorMessage(failure)).not.toContain('private-internal')
  })
  it('handles the real finite 401 JSON response, renews JWT and replays the exact idempotent payload once', async () => {
    const seen = []
    const payload = { conversation_id: 'private-1', request_id: 'stable-uuid', message: 'Hola' }
    apiClient.defaults.env = { ...originalEnv, fetch: async (request) => {
      seen.push({ authorization: request.headers.get('Authorization'), payload: JSON.parse(await request.text()) })
      if (seen.length === 1) return new Response('{"detail":"Sesión vencida"}', { status: 401, headers: { 'Content-Type': 'application/json' } })
      return new Response('{"type":"start"}\n{"type":"delta","text":"Hola"}\n{"type":"done","status":"completed"}\n', { headers: { 'Content-Type': 'application/x-ndjson' } })
    } }
    setAccessToken('expired-token')
    const refresh = vi.fn(async () => { setAccessToken('renewed-token'); return { access_token: 'renewed-token' } })
    registerRefreshHandler(refresh)
    const events = []
    await sendLenyMessage(payload, { onEvent: (event) => events.push(event) })
    expect(refresh).toHaveBeenCalledOnce()
    expect(seen).toEqual([
      { authorization: 'Bearer expired-token', payload }, { authorization: 'Bearer renewed-token', payload },
    ])
    expect(events.map((event) => event.type)).toEqual(['start', 'delta', 'done'])
  })
  it('aborts actual fetch stream consumption without refreshing or retrying', async () => {
    const closed = vi.fn()
    const fetch = vi.fn(async () => new Response(new ReadableStream({
      start(controller) { controller.enqueue(new TextEncoder().encode('{"type":"start"}\n')) }, cancel: closed,
    }), { headers: { 'Content-Type': 'application/x-ndjson' } }))
    apiClient.defaults.env = { ...originalEnv, fetch }
    const controller = new AbortController()
    const refresh = vi.fn()
    registerRefreshHandler(refresh)
    await expect(sendLenyMessage({ request_id: 'one-attempt' }, { signal: controller.signal,
      onEvent: () => controller.abort(),
    })).rejects.toThrow()
    expect(closed).toHaveBeenCalledOnce()
    expect(fetch).toHaveBeenCalledOnce()
    expect(refresh).not.toHaveBeenCalled()
  })
  it('aborts an open 401 response network before JWT refresh without aborting its retry', async () => {
    const closed = vi.fn()
    const seen = []
    const caller = new AbortController()
    apiClient.defaults.env = { ...originalEnv, fetch: async (request) => {
      seen.push(request.signal)
      if (seen.length === 1) return new Response(new ReadableStream({ start(controller) {
        request.signal.addEventListener('abort', () => { closed(); controller.error(new DOMException('Closed network', 'AbortError')) }, { once: true })
      } }), { status: 401 })
      return new Response('{"type":"done","status":"completed"}\n')
    } }
    setAccessToken('expired')
    registerRefreshHandler(async () => {
      expect(closed).toHaveBeenCalledOnce()
      expect(caller.signal.aborted).toBe(false)
      setAccessToken('fresh'); return { access_token: 'fresh' }
    })
    await sendLenyMessage({ request_id: 'same-request' }, { signal: caller.signal, onEvent: () => {} })
    expect(seen).toHaveLength(2)
    expect(seen[0].aborted).toBe(true)
    expect(caller.signal.aborted).toBe(false)
  })
})
