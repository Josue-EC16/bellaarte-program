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

## Stack

- React
- Vite
- Ant Design
- React Router
- Axios
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
- `/app/boutique/ventas`
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

## Reglas UI/UX que ya sigue el frontend

- formularios con `Row` y `Col` para inputs en la misma fila
- `Drawer` y `Modal` con `maskClosable={false}` en flujos críticos
- placeholders descriptivos
- normalización de texto en frontend donde mejora la captura
- el detalle de lectura usa `GET` fresco al backend
- el resumen de venta se recalcula en tiempo real

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
