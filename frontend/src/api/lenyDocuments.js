import { apiClient } from './client'

const root = '/leny/documents'
const data = (promise) => promise.then((response) => response.data)

// Keep Axios' shared authentication/refresh interceptors and an XHR upload so
// progress represents transferred bytes. FormData can be replayed on JWT refresh.
export const lenyDocumentsApi = {
  options: (signal) => data(apiClient.get(`${root}/options`, { signal })),
  folders: (signal) => data(apiClient.get(`${root}/folders`, { signal })),
  createFolder: (payload) => data(apiClient.post(`${root}/folders`, payload)),
  updateFolder: (id, payload) => data(apiClient.patch(`${root}/folders/${id}`, payload)),
  deleteFolder: (id) => data(apiClient.delete(`${root}/folders/${id}`)),
  list: (params, signal) => data(apiClient.get(root, { params, signal })),
  trash: (params, signal) => data(apiClient.get(`${root}/trash`, { params, signal })),
  detail: (id, signal) => data(apiClient.get(`${root}/${id}`, { signal })),
  versions: (id, params, signal) => data(apiClient.get(`${root}/${id}/versions`, { params, signal })),
  contextualizations: (id, versionId, params, signal) => data(apiClient.get(`${root}/${id}/versions/${versionId}/contextualizations`, { params, signal })),
  contextualize: (id, versionId, payload, signal) => data(apiClient.post(`${root}/${id}/versions/${versionId}/contextualizations`, payload, { signal })),
  contextualization: (jobId, signal) => data(apiClient.get(`/leny/contextualizations/${jobId}`, { signal })),
  cancelContextualization: (jobId, signal) => data(apiClient.post(`/leny/contextualizations/${jobId}/cancel`, {}, { signal })),
  ragStatus: (signal) => data(apiClient.get('/leny/admin/rag/status', { signal })),
  update: (id, payload) => data(apiClient.patch(`${root}/${id}`, payload)),
  publish: (id, payload, signal) => data(apiClient.post(`${root}/${id}/publish`, payload, { signal })),
  unpublish: (id, payload, signal) => data(apiClient.post(`${root}/${id}/unpublish`, payload, { signal })),
  changePreview: (id, payload) => data(apiClient.post(`${root}/${id}/change-preview`, payload)),
  moveToTrash: (id, revision) => data(apiClient.delete(`${root}/${id}`, { params: { revision } })),
  restore: (id, payload) => data(apiClient.post(`${root}/${id}/restore`, payload)),
  purgePreview: (payload) => data(apiClient.post(`${root}/trash/purge-preview`, payload)),
  purge: (id, payload) => data(apiClient.delete(`${root}/${id}/purge`, { data: payload })),
  emptyTrash: (payload) => data(apiClient.post(`${root}/trash/empty`, payload)),
  content: (id, versionId, signal) => apiClient.get(`${root}/${id}/versions/${versionId}/content`, { responseType: 'blob', signal }),
  preview: (id, versionId, signal) => apiClient.get(`${root}/${id}/versions/${versionId}/preview`, { responseType: 'blob', signal }),
  upload: (file, metadata, { documentId, signal, onProgress } = {}) => {
    const body = new FormData()
    body.append('metadata', JSON.stringify(metadata))
    body.append('file', file)
    return data(apiClient.post(documentId ? `${root}/${documentId}/versions` : root, body, {
      adapter: 'xhr', signal, timeout: 210000,
      headers: { 'Content-Type': undefined },
      onUploadProgress: (event) => onProgress?.(event.total ? Math.min(100, Math.round(event.loaded / event.total * 100)) : null),
    }))
  },
}
