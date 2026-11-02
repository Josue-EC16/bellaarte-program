// @vitest-environment jsdom
import { afterEach, describe, expect, it, vi } from 'vitest'
import { clearAccessToken, registerRefreshHandler, setAccessToken } from '../../../api/tokenStore'
import { lenyDocumentsApi } from '../../../api/lenyDocuments'

afterEach(() => { clearAccessToken(); registerRefreshHandler(null); vi.unstubAllGlobals() })

function installXHR(responder) {
  const seen = []
  class DocumentXHR {
    constructor() {
      this.headers = {}; this.onloadend = null
      this.upload = { addEventListener: vi.fn(), removeEventListener: vi.fn() }
    }
    open(method, url) { this.method = method; this.url = url }
    setRequestHeader(name, value) { this.headers[name] = value }
    addEventListener() {}
    removeEventListener() {}
    getAllResponseHeaders() { return 'content-type: application/json\r\n' }
    abort() { this.onabort?.() }
    send(body) {
      seen.push({ headers: { ...this.headers }, body, url: this.url })
      const status = responder(seen.length)
      if (!status) return
      this.status = status; this.statusText = status === 200 ? 'OK' : 'Error'
      this.responseText = status === 200 ? '{"id":"stored"}' : '{"detail":{"code":"SESSION_EXPIRED"}}'
      queueMicrotask(() => this.onloadend?.())
    }
  }
  vi.stubGlobal('XMLHttpRequest', DocumentXHR)
  return seen
}

describe('Document actual Axios XHR and authentication interceptors', () => {
  it('renews JWT once and replays the identical multipart idempotency without moving metadata after the file', async () => {
    const seen = installXHR((attempt) => attempt === 1 ? 401 : 200)
    setAccessToken('expired')
    const refresh = vi.fn(async () => { setAccessToken('fresh'); return { access_token: 'fresh' } })
    registerRefreshHandler(refresh)
    const metadata = { request_id: 'stable-request', sha256: 'a'.repeat(64), folder_id: 'folder', title: 'Contrato', description: '' }
    await expect(lenyDocumentsApi.upload(new File(['data'], 'contrato.pdf'), metadata)).resolves.toEqual({ id: 'stored' })
    expect(refresh).toHaveBeenCalledOnce()
    expect(seen).toHaveLength(2)
    expect(seen.map((request) => request.headers.Authorization)).toEqual(['Bearer expired', 'Bearer fresh'])
    for (const request of seen) {
      expect(Array.from(request.body.keys())).toEqual(['metadata', 'file'])
      expect(JSON.parse(request.body.get('metadata'))).toEqual(metadata)
      expect(request.body.get('file').name).toBe('contrato.pdf')
    }
  })
  it('cancels the active XHR and never retries or refreshes an aborted upload', async () => {
    const seen = installXHR(() => null)
    const refresh = vi.fn(); registerRefreshHandler(refresh)
    const controller = new AbortController()
    const pending = lenyDocumentsApi.upload(new File(['data'], 'contrato.pdf'), { request_id: 'one' }, { signal: controller.signal })
    await vi.waitFor(() => expect(seen).toHaveLength(1))
    controller.abort()
    await expect(pending).rejects.toMatchObject({ code: 'ERR_CANCELED' })
    expect(seen).toHaveLength(1); expect(refresh).not.toHaveBeenCalled()
  })
})
