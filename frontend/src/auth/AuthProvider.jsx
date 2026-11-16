/* eslint-disable react/prop-types, react-refresh/only-export-components */
import { createContext, useCallback, useContext, useEffect, useReducer, useRef } from 'react'
import { App as AntdApp } from 'antd'

import { apiClient } from '../api/client'
import {
  clearAccessToken, clearLogoutRequest, getAccessToken, getSessionGeneration, invalidateSession,
  isLogoutRequested, LOGOUT_REQUESTED_KEY, markLogoutRequested,
  registerRefreshHandler, registerSessionHandler, runRefreshHandler, setAccessToken,
} from '../api/tokenStore'
import { waitForSessionRetry, watchSession } from '../api/sessionTransport'

const AuthContext = createContext(null)

const initialState = {
  initialized: false,
  loading: false,
  user: null,
  tokenRevision: 0,
}

function authReducer(state, action) {
  switch (action.type) {
    case 'SET_LOADING':
      return { ...state, loading: action.payload }
    case 'SET_SESSION':
      return {
        ...state,
        initialized: true,
        loading: false,
        user: action.payload,
        tokenRevision: state.tokenRevision + 1,
      }
    case 'UPDATE_USER':
      return state.user?.id === action.payload.id ? { ...state, user: action.payload } : state
    case 'CLEAR_SESSION':
      return {
        ...state,
        initialized: true,
        loading: false,
        user: null,
      }
    default:
      return state
  }
}

export function AuthProvider({ children }) {
  const [state, dispatch] = useReducer(authReducer, initialState)
  const { message } = AntdApp.useApp()
  const mounted = useRef(true)
  const currentUser = useRef(state.user)
  const accountId = state.user?.id
  currentUser.current = state.user

  const applySession = useCallback((session, generation) => {
    if (!mounted.current || generation !== getSessionGeneration()) throw new Error('La sesión terminó.')
    setAccessToken(session.access_token)
    dispatch({ type: 'SET_SESSION', payload: session.user })
    return session
  }, [])

  const clearSession = useCallback(() => {
    clearAccessToken()
    dispatch({ type: 'CLEAR_SESSION' })
  }, [])

  const refreshSession = useCallback(async () => {
    const generation = getSessionGeneration()
    const expectedAccount = currentUser.current?.id
    try {
      const response = await apiClient.post('/auth/refresh')
      if (expectedAccount && expectedAccount !== response.data.user.id) throw new Error('La cuenta de la sesión cambió.')
      return applySession(response.data, generation)
    } catch (error) {
      if (generation === getSessionGeneration()) clearSession()
      throw error
    }
  }, [applySession, clearSession])

  useEffect(() => {
    mounted.current = true
    registerRefreshHandler(refreshSession)
    registerSessionHandler((event) => {
      if (!mounted.current) return
      if (event.type === 'revoked') dispatch({ type: 'CLEAR_SESSION' })
      else if (event.type === 'session') dispatch({ type: 'UPDATE_USER', payload: event.user })
    })
    const storageChanged = (event) => {
      if (event.key === LOGOUT_REQUESTED_KEY && event.newValue === 'true') {
        markLogoutRequested()
        clearSession()
      }
    }
    window.addEventListener('storage', storageChanged)
    if (isLogoutRequested()) clearSession()
    else runRefreshHandler().catch(() => {})
    return () => {
      mounted.current = false
      registerSessionHandler(null)
      registerRefreshHandler(null)
      window.removeEventListener('storage', storageChanged)
    }
  }, [clearSession, refreshSession])

  useEffect(() => {
    if (!accountId || !getAccessToken()) return undefined
    const controller = new AbortController()
    const generation = getSessionGeneration()
    const update = (event) => {
      if (controller.signal.aborted || generation !== getSessionGeneration()) return
      if (event.type === 'session') dispatch({ type: 'UPDATE_USER', payload: event.user })
      else if (['revoked', 'unavailable'].includes(event.type)) invalidateSession(event.code)
    }
    const connect = async () => {
      let retryMilliseconds = 500
      while (!controller.signal.aborted && generation === getSessionGeneration()) {
        try {
          // A lost notification cannot preserve old menu permissions after
          // reconnecting; the server also revalidates the stream itself.
          const response = await apiClient.get('/auth/me', { signal: controller.signal })
          update({ type: 'session', user: response.data.user })
          const terminal = await watchSession({ signal: controller.signal, onEvent: update })
          if (terminal?.type === 'expired' && !controller.signal.aborted) await runRefreshHandler()
          retryMilliseconds = 500
        } catch {
          // Connectivity failures do not grant permissions or destroy a valid
          // session. Revocation/expiry responses are handled by the client.
        }
        await waitForSessionRetry(retryMilliseconds, controller.signal)
        retryMilliseconds = Math.min(retryMilliseconds * 2, 15000)
      }
    }
    connect()
    return () => controller.abort()
  }, [accountId, state.tokenRevision])

  const login = useCallback(async (payload) => {
    clearSession()
    const generation = getSessionGeneration()
    dispatch({ type: 'SET_LOADING', payload: true })
    try {
      const response = await apiClient.post('/auth/login', payload)
      const session = applySession(response.data, generation)
      clearLogoutRequest()
      return session
    } catch (error) {
      if (generation === getSessionGeneration()) clearSession()
      throw error
    }
  }, [applySession, clearSession])

  const logout = useCallback(async () => {
    const token = getAccessToken()
    markLogoutRequested()
    clearSession()
    try {
      await apiClient.post('/auth/logout', undefined, {
        headers: token ? { Authorization: `Bearer ${token}` } : {},
        _sessionControl: true, _skipAuthRefresh: true, _preserveAuthorization: true,
      })
      message.success('Sesión cerrada correctamente.')
    } catch {
      message.warning('Se cerró la sesión en este navegador. No se pudo confirmar la revocación en el servidor; vuelve a ingresar explícitamente para continuar.')
    }
  }, [clearSession, message])

  const changePassword = useCallback(async (payload) => {
    const generation = getSessionGeneration()
    dispatch({ type: 'SET_LOADING', payload: true })
    try {
      const response = await apiClient.post('/auth/change-password', payload)
      if (generation === getSessionGeneration()) clearSession()
      return response.data.user
    } finally {
      if (mounted.current && generation === getSessionGeneration()) dispatch({ type: 'SET_LOADING', payload: false })
    }
  }, [clearSession])

  const value = {
    ...state,
    isAuthenticated: Boolean(state.user),
    login,
    logout,
    refreshSession,
    changePassword,
    clearSession,
  }

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth() {
  const context = useContext(AuthContext)
  if (!context) {
    throw new Error('useAuth debe usarse dentro de AuthProvider')
  }
  return context
}
