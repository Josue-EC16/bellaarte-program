# Frontend BellaArte

Frontend SPA del sistema `bellaarte-program`, construido con React, Vite, Ant Design y React Router.

La versión actual ya integra:

- login interno con refresh de sesión
- cambio obligatorio de contraseña
- CRUD de roles y usuarios
- CRUD de clientes
- CRUD de tipos boutique, proveedores e inventario
- CRUD de monedas y tipos de cambio
- ventas boutique con resumen en tiempo real y reversión de stock
- fletes con habilitación de vestidos, salidas, devoluciones y pase a venta
- comprobantes internos con historial, detalle, impresión y navegación al origen
- catálogo visual de tipos de comprobante
- módulo de notificaciones con campana, panel desplegable, filtros y navegación al origen
- módulo de economía con ingresos, egresos, devoluciones obligatorias y corte de caja
- módulo de auditoría administrativa con filtros avanzados, detalle por evento y exportación

## Stack

- React
- Vite
- Ant Design
- React Router
- Axios
- Recharts
- ESLint

## Variables de entorno

Crear `.env` en `frontend/` a partir de `.env.example`.

Variables:

- `VITE_API_URL`

Ejemplo:

```env
VITE_API_URL=http://localhost:8000/api/v1
```

## Comandos

```powershell
cd frontend
pnpm install
pnpm dev
pnpm lint
pnpm build
```

## Estructura oficial

```text
frontend/
├─ src/
│  ├─ api/
│  ├─ auth/
│  ├─ components/
│  ├─ config/
│  ├─ layout/
│  ├─ pages/
│  ├─ routes/
│  ├─ App.jsx
│  ├─ App.css
│  ├─ index.css
│  └─ main.jsx
├─ .env.example
├─ package.json
└─ README.md
```

## Flujo de autenticación

1. `POST /auth/login`
2. backend devuelve `access_token` y usuario resumido
3. backend deja `refresh token` en cookie `HttpOnly`
4. el `access_token` vive solo en memoria
5. ante `401`, Axios intenta `POST /auth/refresh`
6. si `must_change_password` es `true`, el usuario es redirigido a `/app/cambiar-clave`

## Rutas actuales

Públicas:

- `/login`

Protegidas:

- `/app`
- `/app/cambiar-clave`
- `/app/seguridad/roles`
- `/app/seguridad/usuarios`
- `/app/clientes`
- `/app/boutique/tipos`
- `/app/boutique/proveedores`
- `/app/boutique/inventario`
- `/app/boutique/entradas`
- `/app/boutique/ventas`
- `/app/fletes`
- `/app/fletes/salidas`
- `/app/comprobantes`
- `/app/comprobantes/tipos`
- `/app/notificaciones`
- `/app/auditoria`
- `/app/economia`
- `/app/economia/egresos`
- `/app/economia/cortes-caja`
- `/app/economia/reportes`
- `/app/taller/tipos`
- `/app/taller/inventario`
- `/app/taller/entradas`
- `/app/taller/salidas`
- `/app/monedas`
- `/app/monedas/tipos-cambio`

Auxiliares:

- `/403`

## Menú y permisos

El layout autenticado muestra opciones según permisos reales del usuario.

Bloques actuales:

- `Seguridad`
- `Clientes`
- `Boutique`
- `Fletes`
- `Comprobantes Internos`
- `Notificaciones`
- `Auditoría del Sistema`
- `Economía`
- `Taller`
- `Monedas`

Regla:

- el frontend oculta acciones no permitidas
- el backend sigue siendo la autoridad final

## Módulos de página actuales

### Seguridad

- `src/pages/roles/RolesPage.jsx`
- `src/pages/users/UsersPage.jsx`

### Clientes

- `src/pages/clients/ClientsPage.jsx`

Soporta:

- código editable o autogenerado
- fecha de nacimiento
- país
- ciudad
- alta, edición, vista y cambio de estado

### Boutique

- `src/pages/boutique/BoutiqueTypesPage.jsx`
- `src/pages/boutique/ProvidersPage.jsx`
- `src/pages/boutique/BoutiqueInventoryPage.jsx`
- `src/pages/boutique/BoutiqueEntriesPage.jsx`
- `src/pages/boutique/BoutiqueSalesPage.jsx`

Componentes principales:

- `BoutiqueTypeForm`
- `BoutiqueItemForm`
- `BoutiqueItemDetailCard`
- `BoutiqueSaleForm`
- `BoutiqueSaleDetailCard`
- `boutiqueConstants.js`

### Monedas

- `src/pages/monedas/CurrenciesPage.jsx`
- `src/pages/monedas/ExchangeRatesPage.jsx`

### Fletes

- `src/pages/fletes/FletesPage.jsx`
- `src/pages/fletes/FleteOutputsPage.jsx`
- `src/pages/fletes/fleteConstants.js`

### Comprobantes internos

- `src/pages/comprobantes/ReceiptsPage.jsx`
- `src/pages/comprobantes/ReceiptTypesPage.jsx`
- `src/pages/comprobantes/ReceiptTypeForm.jsx`
- `src/pages/comprobantes/receiptUtils.js`
- `src/components/receipts/ReceiptSnapshotFields.jsx`

### Notificaciones

- `src/pages/notificaciones/NotificationsPage.jsx`
- `src/pages/notificaciones/notificationUtils.js`
- campana integrada en `src/layout/AuthenticatedLayout.jsx`

### Auditoría

- `src/pages/auditoria/AuditPage.jsx`
- `src/pages/auditoria/auditUtils.js`

### Economía

- `src/pages/economia/EconomyDashboardPage.jsx`
- `src/pages/economia/EconomyExpensesPage.jsx`
- `src/pages/economia/CashCutsPage.jsx`
- `src/pages/economia/EconomyReportsPage.jsx`
- `src/pages/economia/EconomySummaryCard.jsx`
- `src/pages/economia/EconomyChartCard.jsx`
- `src/pages/economia/economyConstants.js`
- `src/pages/economia/economyUtils.js`

### Pedidos

- `src/pages/pedidos/OrdersPage.jsx`
- `src/pages/pedidos/OrderPaymentsPage.jsx`
- `src/pages/pedidos/OrderTestsPage.jsx`
- `src/pages/pedidos/OrderReportsPage.jsx`
- `src/pages/pedidos/orderConstants.js`

### Taller

- `src/pages/taller/WorkshopTypesPage.jsx`
- `src/pages/taller/WorkshopInventoryPage.jsx`
- `src/pages/taller/WorkshopEntriesPage.jsx`
- `src/pages/taller/WorkshopOutputsPage.jsx`

## Reglas UI/UX que ya sigue el frontend

- formularios con `Row` y `Col` para inputs en la misma fila
- `Drawer` y `Modal` con `maskClosable={false}` en flujos críticos
- placeholders descriptivos
- normalización de texto en frontend donde mejora la captura
- el detalle de lectura usa `GET` fresco al backend
- el resumen de venta se recalcula en tiempo real
- la impresión de documentos usa HTML servida por backend + `window.print()`

## Contrato funcional actual por módulo

### Clientes

- `MODISTA` y `ADMIN` tienen CRUD completo
- `CAJA` solo tiene lectura técnica para selección en ventas

### Proveedores

- `ADMIN` e `INV_BOUTIQUE` tienen CRUD completo

### Monedas

- `ADMIN` tiene CRUD completo
- `CAJA` e `INV_BOUTIQUE` tienen lectura

### Tipos de cambio

- `ADMIN` tiene CRUD completo
- `CAJA` e `INV_BOUTIQUE` tienen lectura

### Inventario boutique

- `ADMIN` e `INV_BOUTIQUE` tienen CRUD completo
- `CAJA` tiene lectura
- el formulario usa el contrato nuevo:
  - `color_primary`
  - `color_secondary`
  - `length`
  - `width`
  - `provider_id`
  - `detail`

### Ventas boutique

- `ADMIN` y `CAJA` pueden vender, cancelar y anular
- `INV_BOUTIQUE` solo puede listar y ver
- la venta exige moneda
- si la moneda no es base, se usa el tipo de cambio activo
- si faltan datos documentales del cliente, el formulario exige snapshot para el comprobante
- las anulaciones y cancelaciones ya no se cierran directo; la UI redirige al flujo económico obligatorio de devolución

### Fletes

- `ADMIN` y `CAJA` operan el módulo completo
- el alta de flete solo permite vestidos elegibles
- las salidas se crean en `RESERVADO`
- la entrega cambia la salida a `EN_FLETE`
- la devolución permite retorno normal, con observación o con arreglo
- pasar a venta exige nuevo precio y crea un item boutique usado con nuevo código
- la garantía se muestra como bloque de control separado del total comercial
- si faltan datos documentales del cliente, la salida exige snapshot para el comprobante
- la anulación de salida se redirige al flujo económico obligatorio de devolución

### Comprobantes internos

- `ADMIN` y `CAJA` pueden listar, ver e imprimir comprobantes
- `ADMIN` puede crear, editar y cambiar estado de tipos de comprobante
- `CAJA` puede consultar el catálogo de tipos
- no existe alta manual
- no existe anulación manual desde el módulo
- el estado se refleja automáticamente desde el origen
- se puede navegar al movimiento que emitió el comprobante

### Pedidos, pagos y pruebas

- `ADMIN` opera el módulo completo
- `MODISTA` crea y edita pedidos, registra pruebas y consulta pagos/reportes
- `CAJA` consulta pedidos, registra/anula pagos y consulta reportes
- `INV_TALLER` e `INV_BOUTIQUE` no tienen acceso por defecto
- el calendario usa componentes propios de Ant Design sin dependencia externa nueva
- el reporte imprimible por cliente usa HTML y `window.print()`
- la anulación de pagos redirige al flujo económico obligatorio de devolución

### Economía

- `ADMIN` y `CAJA` son los únicos roles con acceso
- `ADMIN` ve resumen global, egresos, cortes y reportes completos
- `CAJA` opera su corte activo y su historial propio
- los ingresos anulados siguen visibles como histórico bruto
- la devolución de dinero se registra siempre como `EGRESO`
- el módulo usa `Recharts` para visualización financiera
- los filtros principales persisten en `sessionStorage`
- el historial cerrado del cajero enmascara ingresos y resultados con `***`

## Reglas para seguir creciendo

1. cada módulo nuevo entra por `src/pages/<modulo>/`
2. rutas nuevas se registran en `src/routes/AppRoutes.jsx`
3. menú nuevo se integra en `src/layout/AuthenticatedLayout.jsx`
4. no crear clientes Axios alternos
5. no guardar tokens en `localStorage` ni `sessionStorage`
6. la validación final siempre pertenece al backend

## Validación recomendada después de cambios

```powershell
pnpm lint
pnpm build
```

Después conviene probar manualmente:

- login
- cambio de contraseña
- alta de cliente
- alta de proveedor
- alta de item boutique
- venta boutique con moneda base y no base
- habilitación de vestido a flete
- flujo de reserva, entrega, devolución y anulación de salida de flete
- alta de pedido, prueba, pago parcial/final, entrega y reporte imprimible
- emisión, consulta e impresión de comprobantes internos desde venta, pago y salida de flete
- apertura y cierre de corte de caja
- egreso manual y devolución económica obligatoria
- reportes económicos para admin y caja
