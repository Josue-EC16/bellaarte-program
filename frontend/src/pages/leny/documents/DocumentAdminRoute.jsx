import { Navigate, Outlet } from 'react-router-dom'
import { useAuth } from '../../../auth/AuthProvider'
import { canManageDocuments } from './documentUtils'

export function DocumentAdminRoute() {
  const { user } = useAuth()
  return canManageDocuments(user) ? <Outlet /> : <Navigate to="/403" replace />
}
