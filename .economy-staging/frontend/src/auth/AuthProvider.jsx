/* eslint-disable react/prop-types, react-refresh/only-export-components */
import { createContext, useCallback, useContext, useEffect, useReducer } from 'react'
import { App as AntdApp } from 'antd'

import { apiClient } from '../api/client'
import { clearAccessToken, registerRefreshHandler, setAccessToken } from '../api/tokenStore'

const AuthContext = createContext(null)

const initialState = {
  initialized: false,
  loading: false,
  user: null,
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
      }
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

  const applySession = useCallback((session) => {
    setAccessToken(session.access_token)
    dispatch({ type: 'SET_SESSION', payload: session.user })
    return session
  }, [])

  const clearSession = useCallback(() => {
    clearAccessToken()
    dispatch({ type: 'CLEAR_SESSION' })
  }, [])

  const refreshSession = useCallback(async () => {
    try {
      const response = await apiClient.post('/auth/refresh')
      return applySession(response.data)
    } catch (error) {
      clearSession()
      throw error
    }
  }, [applySession, clearSession])

  useEffect(() => {
    registerRefreshHandler(refreshSession)
    refreshSession().catch(() => {
      clearSession()
    })
  }, [clearSession, refreshSession])

  const login = useCallback(async (payload) => {
    dispatch({ type: 'SET_LOADING', payload: true })
    try {
      const response = await apiClient.post('/auth/login', payload)
      return applySession(response.data)
    } catch (error) {
      clearSession()
      throw error
    }
  }, [applySession, clearSession])

  const logout = useCallback(async () => {
    try {
      await apiClient.post('/auth/logout')
    } catch {
      // Ignorado para permitir cierre local de sesion.
    } finally {
      clearSession()
      message.success('Sesion cerrada correctamente.')
    }
  }, [clearSession, message])

  const changePassword = useCallback(async (payload) => {
    dispatch({ type: 'SET_LOADING', payload: true })
    const response = await apiClient.post('/auth/change-password', payload)
    dispatch({ type: 'SET_SESSION', payload: response.data.user })
    return response.data.user
  }, [])

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
