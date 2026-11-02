import { apiClient } from './client'

const path = (id) => `/leny/rag/sources/${encodeURIComponent(id)}`

// Sources remain private HTTP reads through the shared JWT/refresh client.
export const lenySourcesApi = {
  detail: (id, signal) => apiClient.get(path(id), { signal, timeout: 15000 }).then(({ data }) => data),
  download: (id, signal) => apiClient.get(`${path(id)}/download`, { signal, responseType: 'blob', timeout: 30000 }),
}
