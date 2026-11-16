/* eslint-disable react/prop-types */
import { Navigate, Outlet, useLocation } from 'react-router-dom'

import { FullScreenLoader } from '../components/FullScreenLoader'
import { useAuth } from '../auth/AuthProvider'

export function ProtectedRoute() {
  const { initialized, isAuthenticated, user } = useAuth()
  const location = useLocation()

  if (!initialized) {
    return <FullScreenLoader />
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" replace state={{ from: location }} />
  }

  if (user.must_change_password && location.pathname !== '/app/cambiar-clave') {
    return <Navigate to="/app/cambiar-clave" replace />
  }

  return <Outlet />
}

export function PublicRoute() {
  const { initialized, isAuthenticated, user } = useAuth()

  if (!initialized) {
    return <FullScreenLoader />
  }

  if (isAuthenticated) {
    return <Navigate to={user.must_change_password ? '/app/cambiar-clave' : '/app'} replace />
  }

  return <Outlet />
}

export function PermissionRoute({ permission }) {
  const { user } = useAuth()
  if (!user?.permissions?.includes(permission)) {
    return <Navigate to="/403" replace />
  }
  return <Outlet />
}
