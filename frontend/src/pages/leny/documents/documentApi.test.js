import { afterEach, describe, expect, it, vi } from 'vitest'
const mocks = vi.hoisted(() => ({ post: vi.fn(), get: vi.fn(), delete: vi.fn(), patch: vi.fn() }))
vi.mock('../../../api/client', () => ({ apiClient: mocks }))
import { lenyDocumentsApi } from '../../../api/lenyDocuments'
afterEach(() => vi.clearAllMocks())

describe('Document Axios contract', () => {
  it('keeps contextualization requests cancellable and uses the shared JWT client', async () => {
    mocks.post.mockResolvedValue({ data: { id: 'job' } }); mocks.get.mockResolvedValue({ data: {} })
    const signal = new AbortController().signal
    const payload = { request_id: 'stable-request', action: 'retry', retry_of: 'failed-job' }
    await lenyDocumentsApi.contextualize('d', 'v', payload, signal)
    await lenyDocumentsApi.contextualizations('d', 'v', { page: 1, page_size: 5 }, signal)
    await lenyDocumentsApi.contextualization('job', signal)
    await lenyDocumentsApi.cancelContextualization('job', signal)
    await lenyDocumentsApi.ragStatus(signal)
    expect(mocks.post.mock.calls).toEqual([
      ['/leny/documents/d/versions/v/contextualizations', payload, { signal }],
      ['/leny/contextualizations/job/cancel', {}, { signal }],
    ])
    expect(mocks.get.mock.calls).toEqual([
      ['/leny/documents/d/versions/v/contextualizations', { params: { page: 1, page_size: 5 }, signal }],
      ['/leny/contextualizations/job', { signal }],
      ['/leny/admin/rag/status', { signal }],
    ])
  })
  it('sends metadata before the file with stable idempotency and real XHR progress', async () => {
    mocks.post.mockResolvedValue({ data: { id: 'document' } })
    const metadata = { request_id: 'fixed-request', sha256: 'a'.repeat(64), title: 'Contrato', folder_id: null, description: '' }
    const file = new Blob(['data'], { type: 'application/pdf' })
    const signal = new AbortController().signal
    const onProgress = vi.fn()
    await lenyDocumentsApi.upload(file, metadata, { signal, onProgress })
    const [path, body, options] = mocks.post.mock.calls[0]
    expect(path).toBe('/leny/documents')
    expect(Array.from(body.keys())).toEqual(['metadata', 'file'])
    expect(JSON.parse(body.get('metadata'))).toEqual(metadata)
    expect(options).toMatchObject({ adapter: 'xhr', signal, timeout: 210000 })
    options.onUploadProgress({ loaded: 10, total: 20 }); expect(onProgress).toHaveBeenCalledWith(50)
    options.onUploadProgress({ loaded: 20 }); expect(onProgress).toHaveBeenCalledWith(null)
  })
  it('keeps versions separate and protects binary reads through the shared client', async () => {
    mocks.post.mockResolvedValue({ data: {} }); mocks.get.mockResolvedValue({ data: new Blob(['x']) })
    const controller = new AbortController()
    await lenyDocumentsApi.upload(new Blob(['x']), { request_id: 'same', sha256: 'b'.repeat(64), revision: 2 }, { documentId: 'd', signal: controller.signal })
    expect(mocks.post.mock.calls[0][0]).toBe('/leny/documents/d/versions')
    await lenyDocumentsApi.preview('d', 'v', controller.signal)
    expect(mocks.get).toHaveBeenCalledWith('/leny/documents/d/versions/v/preview', { responseType: 'blob', signal: controller.signal })
  })
  it('sends revision and explicit confirmation in destructive requests', async () => {
    mocks.delete.mockResolvedValue({ data: {} })
    await lenyDocumentsApi.moveToTrash('d', 3)
    await lenyDocumentsApi.purge('d', { confirmation: 'reviewed', request_id: 'purge-once' })
    expect(mocks.delete.mock.calls).toEqual([
      ['/leny/documents/d', { params: { revision: 3 } }],
      ['/leny/documents/d/purge', { data: { confirmation: 'reviewed', request_id: 'purge-once' } }],
    ])
  })
})
