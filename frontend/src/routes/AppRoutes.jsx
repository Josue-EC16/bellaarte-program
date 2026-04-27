import { Navigate, Route, Routes } from 'react-router-dom'

import { AuthenticatedLayout } from '../layout/AuthenticatedLayout'
import { ChangePasswordPage } from '../pages/auth/ChangePasswordPage'
import { LoginPage } from '../pages/auth/LoginPage'
import { BoutiqueInventoryPage } from '../pages/boutique/BoutiqueInventoryPage'
import { BoutiqueSalesPage } from '../pages/boutique/BoutiqueSalesPage'
import { BoutiqueTypesPage } from '../pages/boutique/BoutiqueTypesPage'
import { ClientsPage } from '../pages/clients/ClientsPage'
import { DashboardHomePage } from '../pages/dashboard/DashboardHomePage'
import { ForbiddenPage } from '../pages/ForbiddenPage'
import { NotFoundPage } from '../pages/NotFoundPage'
import { RolesPage } from '../pages/roles/RolesPage'
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
          <Route element={<PermissionRoute permission="roles:list" />}>
            <Route path="seguridad/roles" element={<RolesPage />} />
          </Route>
          <Route element={<PermissionRoute permission="users:list" />}>
            <Route path="seguridad/usuarios" element={<UsersPage />} />
          </Route>
          <Route element={<PermissionRoute permission="clients:update" />}>
            <Route path="clientes" element={<ClientsPage />} />
          </Route>
          <Route element={<PermissionRoute permission="boutique_types:list" />}>
            <Route path="boutique/tipos" element={<BoutiqueTypesPage />} />
          </Route>
          <Route element={<PermissionRoute permission="boutique_items:list" />}>
            <Route path="boutique/inventario" element={<BoutiqueInventoryPage />} />
          </Route>
          <Route element={<PermissionRoute permission="boutique_sales:list" />}>
            <Route path="boutique/ventas" element={<BoutiqueSalesPage />} />
          </Route>
        </Route>
      </Route>

      <Route path="/403" element={<ForbiddenPage />} />
      <Route path="/" element={<Navigate to="/app" replace />} />
      <Route path="*" element={<NotFoundPage />} />
    </Routes>
  )
}
