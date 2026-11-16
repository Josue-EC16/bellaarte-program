import { afterEach, describe, expect, it, vi } from 'vitest'
import { apiClient } from './client'
import {
  clearAccessToken, getAccessToken, getSessionSignal, invalidateSession,
  registerRefreshHandler, registerSessionHandler, runRefreshHandler, setAccessToken,
} from './tokenStore'
import { watchSession } from './sessionTransport'

const originalEnv = apiClient.defaults.env
afterEach(() => {
  apiClient.defaults.env = originalEnv
  clearAccessToken(); registerRefreshHandler(null); registerSessionHandler(null)
  vi.unstubAllGlobals()
})

describe('session requests and refresh coordination', () => {
  it('serializes concurrent refresh calls and uses the cross-tab browser lock', async () => {
    let resolve
    const pending = new Promise((done) => { resolve = done })
    const refresh = vi.fn(() => pending)
    const request = vi.fn((_name, callback) => callback())
    vi.stubGlobal('navigator', { locks: { request } })
    registerRefreshHandler(refresh)
    const first = runRefreshHandler(); const second = runRefreshHandler()
    expect(refresh).toHaveBeenCalledOnce()
    resolve({ access_token: 'one-rotation' })
    await expect(Promise.all([first, second])).resolves.toEqual([
      { access_token: 'one-rotation' }, { access_token: 'one-rotation' },
    ])
    expect(request).toHaveBeenCalledWith('bab-vdos-session-refresh', expect.any(Function))
    await runRefreshHandler()
    expect(refresh).toHaveBeenCalledTimes(2)
  })

  it('revokes pending requests without poisoning the next session signal', () => {
    const handler = vi.fn(); registerSessionHandler(handler); setAccessToken('old')
    const signal = getSessionSignal()
    invalidateSession('PASSWORD_RESET')
    expect(signal.aborted).toBe(true)
    expect(getSessionSignal().aborted).toBe(false)
    expect(getAccessToken()).toBeNull()
    expect(handler).toHaveBeenCalledWith({ type: 'revoked', code: 'PASSWORD_RESET' })
  })

  it('does not run a queued browser-lock refresh after logout or a new login', async () => {
    let acquire
    vi.stubGlobal('navigator', { locks: { request: (_name, callback) => new Promise((resolve, reject) => {
      acquire = () => { try { resolve(callback()) } catch (error) { reject(error) } }
    }) } })
    const refresh = vi.fn()
    registerRefreshHandler(refresh)
    const pending = runRefreshHandler()
    const assertion = expect(pending).rejects.toThrow('sesión terminó')
    clearAccessToken(); setAccessToken('another-session'); acquire()
    await assertion
    expect(refresh).not.toHaveBeenCalled()
    expect(getAccessToken()).toBe('another-session')
  })

  it('does not refresh revoked tokens and does not log out on ordinary 403', async () => {
    const refresh = vi.fn(); const handler = vi.fn()
    registerRefreshHandler(refresh); registerSessionHandler(handler); setAccessToken('old')
    apiClient.defaults.env = { ...originalEnv, fetch: async () => new Response(
      '{"detail":{"code":"SESSION_REVOKED","message":"Sesión terminada"}}',
      { status: 401, headers: { 'Content-Type': 'application/json' } },
    ) }
    await expect(apiClient.get('/users', { adapter: 'fetch' })).rejects.toMatchObject({ response: { status: 401 } })
    expect(refresh).not.toHaveBeenCalled(); expect(getAccessToken()).toBeNull()
    expect(handler).toHaveBeenCalledOnce()
    setAccessToken('active')
    apiClient.defaults.env = { ...originalEnv, fetch: async () => new Response('{"detail":"Sin permiso"}', { status: 403 }) }
    await expect(apiClient.get('/users', { adapter: 'fetch' })).rejects.toMatchObject({ response: { status: 403 } })
    expect(getAccessToken()).toBe('active'); expect(handler).toHaveBeenCalledOnce()
  })

  it('never replays a request if the session ended during refresh', async () => {
    let finish
    const refresh = vi.fn(() => new Promise((resolve) => { finish = resolve }))
    registerRefreshHandler(refresh); setAccessToken('expired')
    const fetch = vi.fn(async () => new Response('{"detail":"Vencido"}', { status: 401 }))
    apiClient.defaults.env = { ...originalEnv, fetch }
    const pending = apiClient.post('/users', { nombres: 'QA' }, { adapter: 'fetch' })
    const result = expect(pending).rejects.toMatchObject({ code: 'ERR_CANCELED' })
    await vi.waitFor(() => expect(refresh).toHaveBeenCalledOnce())
    clearAccessToken(); finish({ access_token: 'too-late' })
    await result
    expect(fetch).toHaveBeenCalledOnce()
  })
})

describe('session event transport', () => {
  it('decodes chunk boundaries, updates role and closes a revoked stream', async () => {
    const closed = vi.fn()
    const user = { id: 3, role_code: 'CAJA', permissions: ['dashboard:view'], full_name: 'MARÍA' }
    const bytes = new TextEncoder().encode(`${JSON.stringify({ type: 'session', user })}\n{"type":"heartbeat"}\n{"type":"revoked","code":"PASSWORD_RESET"}\n`)
    apiClient.defaults.env = { ...originalEnv, fetch: async () => new Response(new ReadableStream({
      start(controller) { controller.enqueue(bytes.slice(0, 57)); controller.enqueue(bytes.slice(57)) }, cancel: closed,
    }), { headers: { 'Content-Type': 'application/x-ndjson' } }) }
    setAccessToken('active')
    const events = []
    await expect(watchSession({ signal: new AbortController().signal, onEvent: (event) => events.push(event) }))
      .resolves.toEqual({ type: 'revoked', code: 'PASSWORD_RESET' })
    expect(events[0].user).toEqual(user)
    expect(events.map(({ type }) => type)).toEqual(['session', 'heartbeat', 'revoked'])
    expect(closed).toHaveBeenCalledOnce()
  })

  it('finishes an unavailable event so the provider can fail closed', async () => {
    apiClient.defaults.env = { ...originalEnv, fetch: async () => new Response('{"type":"unavailable","code":"AUTH_STATE_UNAVAILABLE"}\n') }
    await expect(watchSession({ signal: new AbortController().signal, onEvent: () => {} }))
      .resolves.toEqual({ type: 'unavailable', code: 'AUTH_STATE_UNAVAILABLE' })
  })
})
