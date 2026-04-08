import { Navigate, Route, Routes } from 'react-router-dom'

import { AuthenticatedLayout } from '../layout/AuthenticatedLayout'
import { ChangePasswordPage } from '../pages/auth/ChangePasswordPage'
import { LoginPage } from '../pages/auth/LoginPage'
import { DashboardHomePage } from '../pages/dashboard/DashboardHomePage'
import { ForbiddenPage } from '../pages/ForbiddenPage'
import { NotFoundPage } from '../pages/NotFoundPage'
import { UsersPage } from '../pages/users/UsersPage'
import { PermissionRoute, ProtectedRoute, PublicRoute } from './RouteGuards'

export function AppRoutes() {
  return (
    <Routes>
      <Route element={<PublicRoute />}>
        <Route path="/login" element={<LoginPage />} />
      </Route>

      <Route element={<ProtectedRoute />}>
        <Route path="/app" element={<AuthenticatedLayout />}>
          <Route index element={<DashboardHomePage />} />
          <Route path="cambiar-clave" element={<ChangePasswordPage />} />
          <Route element={<PermissionRoute permission="users:list" />}>
            <Route path="usuarios" element={<UsersPage />} />
          </Route>
        </Route>
      </Route>

      <Route path="/403" element={<ForbiddenPage />} />
      <Route path="/" element={<Navigate to="/app" replace />} />
      <Route path="*" element={<NotFoundPage />} />
    </Routes>
  )
}

