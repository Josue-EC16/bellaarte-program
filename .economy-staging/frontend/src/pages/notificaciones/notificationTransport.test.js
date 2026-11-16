import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import {
  createNotificationPoller,
  NOTIFICATIONS_CHANGED,
  notifyNotificationsChanged,
  presentDesktopNotifications,
} from './notificationTransport'

function surfaces() {
  const target = new EventTarget()
  target.setInterval = (...args) => setInterval(...args)
  target.clearInterval = (id) => clearInterval(id)
  const documentRef = new EventTarget()
  documentRef.visibilityState = 'visible'
  return { target, documentRef }
}

function deferred() {
  let resolve
  let reject
  const promise = new Promise((res, rej) => { resolve = res; reject = rej })
  return { promise, resolve, reject }
}

describe('notification polling lifecycle', () => {
  const pollers = []
  beforeEach(() => vi.useFakeTimers())
  afterEach(() => {
    pollers.splice(0).forEach((poller) => poller.stop())
    vi.useRealTimers()
    vi.restoreAllMocks()
  })
  function start(options) {
    const poller = createNotificationPoller(options)
    pollers.push(poller)
    return poller
  }

  it('loads once, waits 60 seconds, and clears timers/listeners on stop', async () => {
    const env = surfaces()
    const load = vi.fn().mockResolvedValue({ unread_count: 1 })
    const onData = vi.fn()
    const poller = start({ ...env, load, onData, onError: vi.fn() })
    await vi.advanceTimersByTimeAsync(0)
    expect(load).toHaveBeenCalledTimes(1)
    await vi.advanceTimersByTimeAsync(59999)
    expect(load).toHaveBeenCalledTimes(1)
    await vi.advanceTimersByTimeAsync(1)
    expect(load).toHaveBeenCalledTimes(2)
    poller.stop()
    env.target.dispatchEvent(new Event('focus'))
    notifyNotificationsChanged(env.target)
    await vi.advanceTimersByTimeAsync(120000)
    expect(load).toHaveBeenCalledTimes(2)
    expect(vi.getTimerCount()).toBe(0)
    expect(onData).toHaveBeenCalledTimes(2)
  })

  it('coalesces focus and change events while one request is in flight', async () => {
    const env = surfaces()
    const first = deferred()
    const load = vi.fn().mockReturnValueOnce(first.promise).mockResolvedValue('latest')
    start({ ...env, load, onData: vi.fn(), onError: vi.fn() })
    await vi.advanceTimersByTimeAsync(0)
    env.target.dispatchEvent(new Event('focus'))
    notifyNotificationsChanged(env.target)
    notifyNotificationsChanged(env.target)
    expect(load).toHaveBeenCalledTimes(1)
    first.resolve('initial')
    await vi.advanceTimersByTimeAsync(0)
    expect(load).toHaveBeenCalledTimes(2)
  })

  it('pauses while hidden and refreshes once on visibility return', async () => {
    const env = surfaces()
    env.documentRef.visibilityState = 'hidden'
    const load = vi.fn().mockResolvedValue('data')
    start({ ...env, load, onData: vi.fn(), onError: vi.fn() })
    await vi.advanceTimersByTimeAsync(120000)
    expect(load).not.toHaveBeenCalled()
    env.documentRef.visibilityState = 'visible'
    env.documentRef.dispatchEvent(new Event('visibilitychange'))
    await vi.advanceTimersByTimeAsync(0)
    expect(load).toHaveBeenCalledTimes(1)
  })

  it('aborts pending work and ignores its result after unmount/remount', async () => {
    const env = surfaces()
    const pending = deferred()
    let signal
    const oldData = vi.fn()
    const oldError = vi.fn()
    const first = start({ ...env, load: (value) => { signal = value; return pending.promise },
      onData: oldData, onError: oldError })
    await vi.advanceTimersByTimeAsync(0)
    first.stop()
    const nextData = vi.fn()
    start({ ...env, load: vi.fn().mockResolvedValue('new session'), onData: nextData, onError: vi.fn() })
    pending.resolve('stale session')
    await vi.advanceTimersByTimeAsync(0)
    expect(signal.aborted).toBe(true)
    expect(oldData).not.toHaveBeenCalled()
    expect(oldError).not.toHaveBeenCalled()
    expect(nextData).toHaveBeenCalledWith('new session')
    expect(vi.getTimerCount()).toBe(1)
  })

  it('exposes request failures and permits a later recovery', async () => {
    const env = surfaces()
    const failure = new Error('synthetic network failure')
    const load = vi.fn().mockRejectedValueOnce(failure).mockResolvedValueOnce('recovered')
    const onError = vi.fn()
    const onData = vi.fn()
    const poller = start({ ...env, load, onData, onError })
    await vi.advanceTimersByTimeAsync(0)
    expect(onError).toHaveBeenCalledWith(failure)
    await poller.refresh()
    expect(onData).toHaveBeenCalledWith('recovered')
  })

  it('notifies two mounted centers without multiplying either interval', async () => {
    const env = surfaces()
    const loads = [vi.fn().mockResolvedValue([]), vi.fn().mockResolvedValue([])]
    loads.forEach((load) => start({ ...env, load, onData: vi.fn(), onError: vi.fn() }))
    await vi.advanceTimersByTimeAsync(0)
    env.target.dispatchEvent(new Event(NOTIFICATIONS_CHANGED))
    await vi.advanceTimersByTimeAsync(0)
    loads.forEach((load) => expect(load).toHaveBeenCalledTimes(2))
    expect(vi.getTimerCount()).toBe(2)
  })
})

describe('claimed desktop presentation', () => {
  function descriptor(permission = 'granted') {
    const notices = []
    class NotificationApi {
      static permission = permission
      constructor(title, options) {
        Object.assign(this, { title, options, close: vi.fn() })
        notices.push(this)
      }
    }
    return { NotificationApi, notices }
  }
  const items = Array.from({ length: 5 }, (_, index) => ({ id: index + 1, revision: 2, titulo: 'QA', mensaje: 'SYNTHETIC' }))

  it.each(['default', 'denied'])('does not present or request permission when %s', (permission) => {
    const { NotificationApi, notices } = descriptor(permission)
    presentDesktopNotifications(items, NotificationApi, vi.fn())
    expect(notices).toEqual([])
    expect(() => presentDesktopNotifications(items, undefined, vi.fn())).not.toThrow()
  })

  it('bounds a batch to three and uses identity/revision tags', () => {
    const { NotificationApi, notices } = descriptor()
    const open = vi.fn()
    presentDesktopNotifications(items, NotificationApi, open)
    expect(notices).toHaveLength(3)
    expect(notices[0].options).toEqual({ body: 'SYNTHETIC', tag: 'bab-1-2' })
    notices[0].onclick()
    expect(notices[0].close).toHaveBeenCalledOnce()
    expect(open).toHaveBeenCalledWith(items[0])
  })

  it('does not retry or throw when native presentation fails', () => {
    const NotificationApi = vi.fn(() => { throw new Error('unsupported platform') })
    NotificationApi.permission = 'granted'
    expect(() => presentDesktopNotifications(items.slice(0, 1), NotificationApi, vi.fn())).not.toThrow()
    expect(NotificationApi).toHaveBeenCalledOnce()
  })
})
