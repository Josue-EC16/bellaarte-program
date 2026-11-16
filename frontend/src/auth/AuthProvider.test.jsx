// @vitest-environment jsdom
import { act, cleanup, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

const mocks = vi.hoisted(() => ({ post: vi.fn(), get: vi.fn(), watch: vi.fn(), message: { success: vi.fn(), warning: vi.fn() } }))
vi.mock('../api/client', () => ({ apiClient: { post: mocks.post, get: mocks.get } }))
vi.mock('../api/sessionTransport', () => ({ watchSession: mocks.watch, waitForSessionRetry: () => new Promise(() => {}) }))
vi.mock('antd', () => ({ App: { useApp: () => ({ message: mocks.message }) } }))
import { AuthProvider, useAuth } from './AuthProvider'
import { clearAccessToken, clearLogoutRequest, getAccessToken, registerRefreshHandler, registerSessionHandler } from '../api/tokenStore'

const admin = { id: 1, role_code: 'ADMIN', full_name: 'QA', permissions: ['users:list'], must_change_password: false }
let emit
function Probe() {
  const auth = useAuth()
  return <div>
    <output>{auth.isAuthenticated ? auth.user.role_code : 'SIGNED_OUT'}</output>
    {auth.user?.permissions?.includes('users:list') ? <span>USERS_VISIBLE</span> : null}
    <button onClick={() => auth.clearSession()}>CLEAR</button>
    <button onClick={() => auth.login({ username: 'OTHER', password: 'synthetic' })}>LOGIN</button>
    <button onClick={() => auth.logout()}>LOGOUT</button>
    <button onClick={() => auth.changePassword({ current_password: 'old', new_password: 'new' })}>PASSWORD</button>
  </div>
}
async function flush() { await act(async () => { await Promise.resolve(); await Promise.resolve() }) }
beforeEach(() => {
  vi.clearAllMocks()
  mocks.post.mockResolvedValue({ data: { access_token: 'synthetic', user: admin } })
  mocks.get.mockResolvedValue({ data: { user: admin } })
  mocks.watch.mockImplementation(({ signal, onEvent }) => {
    emit = onEvent
    return new Promise((resolve) => signal.addEventListener('abort', () => resolve(), { once: true }))
  })
})
afterEach(() => { cleanup(); clearAccessToken(); clearLogoutRequest(); registerRefreshHandler(null); registerSessionHandler(null) })

describe('active session state', () => {
  it('applies a role change to the visible UI without signing out', async () => {
    render(<AuthProvider><Probe /></AuthProvider>); await flush()
    expect(screen.getByText('USERS_VISIBLE')).toBeTruthy()
    act(() => emit({ type: 'session', user: { ...admin, role_code: 'CAJA', permissions: ['dashboard:view'] } }))
    expect(screen.getByText('CAJA')).toBeTruthy()
    expect(screen.queryByText('USERS_VISIBLE')).toBeNull()
    expect(getAccessToken()).toBe('synthetic')
  })
  it.each(['revoked', 'unavailable'])('clears authentication and token on %s', async (type) => {
    render(<AuthProvider><Probe /></AuthProvider>); await flush()
    act(() => emit({ type, code: 'SESSION_REVOKED' }))
    expect(screen.getByText('SIGNED_OUT')).toBeTruthy()
    expect(getAccessToken()).toBeNull()
  })
  it('signs out after changing password instead of restoring the revoked session', async () => {
    render(<AuthProvider><Probe /></AuthProvider>); await flush()
    fireEvent.click(screen.getByText('PASSWORD')); await flush()
    expect(mocks.post).toHaveBeenCalledWith('/auth/change-password', { current_password: 'old', new_password: 'new' })
    expect(screen.getByText('SIGNED_OUT')).toBeTruthy()
    expect(getAccessToken()).toBeNull()
  })
  it('does not restore an obsolete refresh response after clearing the session', async () => {
    let resolve
    mocks.post.mockImplementation(() => new Promise((done) => { resolve = done }))
    render(<AuthProvider><Probe /></AuthProvider>); await flush()
    fireEvent.click(screen.getByText('CLEAR'))
    await act(async () => resolve({ data: { access_token: 'late', user: admin } }))
    expect(screen.getByText('SIGNED_OUT')).toBeTruthy()
    expect(getAccessToken()).toBeNull()
  })
  it('does not clear a new login when a previous password change finishes late', async () => {
    let finishPassword
    const nextUser = { ...admin, id: 2, role_code: 'CAJA', permissions: ['dashboard:view'] }
    mocks.post.mockImplementation(async (url) => {
      if (url === '/auth/change-password') return new Promise((resolve) => { finishPassword = resolve })
      if (url === '/auth/login') return { data: { access_token: 'new-session', user: nextUser } }
      return { data: { access_token: 'old-session', user: admin } }
    })
    mocks.get.mockImplementation(async () => ({ data: { user: getAccessToken() === 'new-session' ? nextUser : admin } }))
    render(<AuthProvider><Probe /></AuthProvider>); await flush()
    fireEvent.click(screen.getByText('PASSWORD')); await flush()
    fireEvent.click(screen.getByText('CLEAR'))
    fireEvent.click(screen.getByText('LOGIN')); await flush()
    expect(screen.getByText('CAJA')).toBeTruthy()
    await act(async () => finishPassword({ data: { user: admin } }))
    expect(screen.getByText('CAJA')).toBeTruthy()
    expect(getAccessToken()).toBe('new-session')
  })
  it('keeps an unsuccessful server logout closed across remount without automatic refresh', async () => {
    render(<AuthProvider><Probe /></AuthProvider>); await flush()
    mocks.post.mockRejectedValueOnce(new Error('Network unavailable'))
    fireEvent.click(screen.getByText('LOGOUT')); await flush()
    expect(screen.getByText('SIGNED_OUT')).toBeTruthy()
    expect(mocks.message.warning).toHaveBeenCalledOnce()
    expect(mocks.message.success).not.toHaveBeenCalled()
    const calls = mocks.post.mock.calls.length
    cleanup()
    render(<AuthProvider><Probe /></AuthProvider>); await flush()
    expect(screen.getByText('SIGNED_OUT')).toBeTruthy()
    expect(mocks.post.mock.calls).toHaveLength(calls)
  })
})
