import axios from 'axios'

import { API_URL } from '../config/env'
import { normalizeApiError } from '../components/forms/formErrorUtils'
import { clearAccessToken, getAccessToken, runRefreshHandler } from './tokenStore'

export const apiClient = axios.create({
  baseURL: API_URL,
  withCredentials: true,
})

apiClient.interceptors.request.use((config) => {
  const token = getAccessToken()
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

apiClient.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config
    const requestPath = originalRequest?.url || ''

    if (
      error.response?.status === 401 &&
      !originalRequest?._retry &&
      !requestPath.includes('/auth/login') &&
      !requestPath.includes('/auth/refresh')
    ) {
      originalRequest._retry = true

      try {
        const session = await runRefreshHandler()
        originalRequest.headers.Authorization = `Bearer ${session.access_token}`
        return apiClient(originalRequest)
      } catch (refreshError) {
        clearAccessToken()
        return Promise.reject(refreshError)
      }
    }

    error.normalizedError = normalizeApiError(error)

    return Promise.reject(error)
  },
)
