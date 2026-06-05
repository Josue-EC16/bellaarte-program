import { Navigate, Route, Routes } from 'react-router-dom'

import { AuthenticatedLayout } from '../layout/AuthenticatedLayout'
import { ChangePasswordPage } from '../pages/auth/ChangePasswordPage'
import { LoginPage } from '../pages/auth/LoginPage'
import { AuditPage } from '../pages/auditoria/AuditPage'
import { BoutiqueEntriesPage } from '../pages/boutique/BoutiqueEntriesPage'
import { BoutiqueInventoryPage } from '../pages/boutique/BoutiqueInventoryPage'
import { ProvidersPage } from '../pages/boutique/ProvidersPage'
import { BoutiqueSalesPage } from '../pages/boutique/BoutiqueSalesPage'
import { BoutiqueTypesPage } from '../pages/boutique/BoutiqueTypesPage'
import { ClientsPage } from '../pages/clients/ClientsPage'
import { ReceiptsPage } from '../pages/comprobantes/ReceiptsPage'
import { ReceiptTypesPage } from '../pages/comprobantes/ReceiptTypesPage'
import { DashboardHomePage } from '../pages/dashboard/DashboardHomePage'
import { CashCutsPage } from '../pages/economia/CashCutsPage'
import { EconomyDashboardPage } from '../pages/economia/EconomyDashboardPage'
import { EconomyExpensesPage } from '../pages/economia/EconomyExpensesPage'
import { EconomyReportsPage } from '../pages/economia/EconomyReportsPage'
import { FleteOutputsPage } from '../pages/fletes/FleteOutputsPage'
import { FletesPage } from '../pages/fletes/FletesPage'
import { CurrenciesPage } from '../pages/monedas/CurrenciesPage'
import { ExchangeRatesPage } from '../pages/monedas/ExchangeRatesPage'
import { NotificationsPage } from '../pages/notificaciones/NotificationsPage'
import { OrderPaymentsPage } from '../pages/pedidos/OrderPaymentsPage'
import { OrderReportsPage } from '../pages/pedidos/OrderReportsPage'
import { OrdersPage } from '../pages/pedidos/OrdersPage'
import { OrderTestsPage } from '../pages/pedidos/OrderTestsPage'
import { ForbiddenPage } from '../pages/ForbiddenPage'
import { NotFoundPage } from '../pages/NotFoundPage'
import { RolesPage } from '../pages/roles/RolesPage'
import { WorkshopEntriesPage } from '../pages/taller/WorkshopEntriesPage'
import { WorkshopInventoryPage } from '../pages/taller/WorkshopInventoryPage'
import { WorkshopOutputsPage } from '../pages/taller/WorkshopOutputsPage'
import { WorkshopTypesPage } from '../pages/taller/WorkshopTypesPage'
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
          <Route element={<PermissionRoute permission="clients:list" />}>
            <Route path="clientes" element={<ClientsPage />} />
          </Route>
          <Route element={<PermissionRoute permission="boutique_types:list" />}>
            <Route path="boutique/tipos" element={<BoutiqueTypesPage />} />
          </Route>
          <Route element={<PermissionRoute permission="boutique_providers:list" />}>
            <Route path="boutique/proveedores" element={<ProvidersPage />} />
          </Route>
          <Route element={<PermissionRoute permission="boutique_items:list" />}>
            <Route path="boutique/inventario" element={<BoutiqueInventoryPage />} />
          </Route>
          <Route element={<PermissionRoute permission="boutique_entries:list" />}>
            <Route path="boutique/entradas" element={<BoutiqueEntriesPage />} />
          </Route>
          <Route element={<PermissionRoute permission="boutique_sales:list" />}>
            <Route path="boutique/ventas" element={<BoutiqueSalesPage />} />
          </Route>
          <Route element={<PermissionRoute permission="fletes:list" />}>
            <Route path="fletes" element={<FletesPage />} />
          </Route>
          <Route element={<PermissionRoute permission="flete_outputs:list" />}>
            <Route path="fletes/salidas" element={<FleteOutputsPage />} />
          </Route>
          <Route element={<PermissionRoute permission="receipts:list" />}>
            <Route path="comprobantes" element={<ReceiptsPage />} />
          </Route>
          <Route element={<PermissionRoute permission="notifications:list" />}>
            <Route path="notificaciones" element={<NotificationsPage />} />
          </Route>
          <Route element={<PermissionRoute permission="audit:list" />}>
            <Route path="auditoria" element={<AuditPage />} />
          </Route>
          <Route element={<PermissionRoute permission="receipt_types:list" />}>
            <Route path="comprobantes/tipos" element={<ReceiptTypesPage />} />
          </Route>
          <Route element={<PermissionRoute permission="economy_income:view" />}>
            <Route path="economia" element={<EconomyDashboardPage />} />
          </Route>
          <Route element={<PermissionRoute permission="economy_expenses:list" />}>
            <Route path="economia/egresos" element={<EconomyExpensesPage />} />
          </Route>
          <Route element={<PermissionRoute permission="cash_cuts:view_own" />}>
            <Route path="economia/cortes-caja" element={<CashCutsPage />} />
          </Route>
          <Route element={<PermissionRoute permission="economy_reports:view" />}>
            <Route path="economia/reportes" element={<EconomyReportsPage />} />
          </Route>
          <Route element={<PermissionRoute permission="orders:list" />}>
            <Route path="pedidos" element={<OrdersPage />} />
          </Route>
          <Route element={<PermissionRoute permission="order_payments:list" />}>
            <Route path="pedidos/pagos" element={<OrderPaymentsPage />} />
          </Route>
          <Route element={<PermissionRoute permission="order_tests:list" />}>
            <Route path="pedidos/pruebas" element={<OrderTestsPage />} />
          </Route>
          <Route element={<PermissionRoute permission="order_reports:view" />}>
            <Route path="pedidos/reportes" element={<OrderReportsPage />} />
          </Route>
          <Route element={<PermissionRoute permission="workshop_types:list" />}>
            <Route path="taller/tipos" element={<WorkshopTypesPage />} />
          </Route>
          <Route element={<PermissionRoute permission="workshop_inventory:list" />}>
            <Route path="taller/inventario" element={<WorkshopInventoryPage />} />
          </Route>
          <Route element={<PermissionRoute permission="workshop_entries:list" />}>
            <Route path="taller/entradas" element={<WorkshopEntriesPage />} />
          </Route>
          <Route element={<PermissionRoute permission="workshop_outputs:list" />}>
            <Route path="taller/salidas" element={<WorkshopOutputsPage />} />
          </Route>
          <Route element={<PermissionRoute permission="currencies:list" />}>
            <Route path="monedas" element={<CurrenciesPage />} />
          </Route>
          <Route element={<PermissionRoute permission="exchange_rates:list" />}>
            <Route path="monedas/tipos-cambio" element={<ExchangeRatesPage />} />
          </Route>
        </Route>
      </Route>

      <Route path="/403" element={<ForbiddenPage />} />
      <Route path="/" element={<Navigate to="/app" replace />} />
      <Route path="*" element={<NotFoundPage />} />
    </Routes>
  )
}
