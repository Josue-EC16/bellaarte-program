# Frontend BellaArte

Frontend SPA del sistema `bellaarte-program`, construido con React 19, Vite 6, Ant Design y React Router.

Este frontend implementa la primera fase del sistema:

- login interno por `username + password`
- renovacion de sesion por `refresh token` en cookie `HttpOnly`
- cambio obligatorio de contrasena en primer ingreso
- home operativo segun sesion
- gestion interna de usuarios solo para `ADMIN`
- proteccion de rutas segun permisos entregados por backend

## Stack

- React 19
- Vite 6
- Ant Design 5
- React Router DOM 7
- Axios
- ESLint
- Vitest

## Variables de entorno

Crear un archivo `.env` en `frontend/` a partir de `.env.example`.

Variables disponibles:

- `VITE_API_URL`: URL base de la API.

Ejemplo:

```env
VITE_API_URL=http://localhost:8000/api/v1
```

## Comandos

Instalacion:

```powershell
cd frontend
pnpm install
```

Desarrollo:

```powershell
pnpm dev
```

Lint:

```powershell
pnpm lint
```

Build:

```powershell
pnpm build
```

Preview local del build:

```powershell
pnpm preview
```

## Estructura oficial

```text
frontend/
├─ src/
│  ├─ api/          # cliente HTTP, interceptores, token store
│  ├─ auth/         # contexto global de autenticacion
│  ├─ components/   # componentes reutilizables simples
│  ├─ config/       # variables y configuracion de entorno
│  ├─ layout/       # layouts compartidos de la app autenticada
│  ├─ pages/        # pantallas por dominio
│  ├─ routes/       # definicion de rutas y guards
│  ├─ App.jsx
│  ├─ App.css
│  ├─ index.css
│  └─ main.jsx
├─ .env.example
├─ package.json
└─ README.md
```

## Flujo de autenticacion

### 1. Login

La vista de login llama a:

```http
POST /auth/login
```

Backend responde con:

- `access_token`
- `token_type`
- `user`

Ademas el backend envia el `refresh token` como cookie `HttpOnly`.

### 2. Sesion activa

El `access_token` vive solo en memoria del navegador mediante `tokenStore`.

No se guarda en:

- `localStorage`
- `sessionStorage`

Esto es una regla de seguridad del proyecto.

### 3. Refresh automatico

Si una request recibe `401`, el interceptor de Axios intenta:

```http
POST /auth/refresh
```

Si funciona:

- obtiene un nuevo `access_token`
- reintenta la peticion original

Si falla:

- limpia sesion local
- redirige al login

### 4. Cambio obligatorio de contrasena

Si `user.must_change_password === true`, el usuario autenticado no puede navegar libremente y es redirigido a:

```text
/app/cambiar-clave
```

## Rutas actuales

Publicas:

- `/login`

Protegidas:

- `/app`
- `/app/cambiar-clave`
- `/app/usuarios`

Rutas auxiliares:

- `/403`

## Reglas para agregar nuevos modulos

### 1. No romper el flujo de auth

Todo nuevo modulo debe integrarse con:

- `AuthProvider`
- `api/client.js`
- guards de rutas

No crear clientes Axios alternos ni duplicar logica de autenticacion.

### 2. Cada modulo entra por `pages/`

Si se crea un nuevo modulo, su carpeta debe vivir en `src/pages/<modulo>/`.

Ejemplos:

- `src/pages/inventario-boutique/`
- `src/pages/pedidos/`
- `src/pages/finanzas/`

### 3. Navegacion desde layout

Los accesos a modulos deben agregarse en:

- `src/layout/AuthenticatedLayout.jsx`

El item de menu solo debe mostrarse si el usuario tiene el permiso correspondiente.

### 4. La proteccion real no depende del menu

Ocultar una opcion visual no es seguridad.

Toda ruta nueva debe:

- tener guard en frontend si corresponde
- validarse tambien en backend mediante permisos

### 5. Formularios

Usar componentes de Ant Design y validaciones basicas en frontend, pero la validacion final siempre pertenece al backend.

### 6. Estado global

En esta fase solo existe un contexto global oficial:

- `AuthProvider`

No agregar stores globales nuevos sin necesidad real.

Si un modulo requiere estado complejo, primero intentar:

- estado local
- hooks propios del modulo

### 7. API por dominio

Cada nuevo modulo debe consumir endpoints agrupados por dominio.

Ejemplos esperados a futuro:

- `/inventario-boutique`
- `/inventario-taller`
- `/pedidos`
- `/pagos-pedido`
- `/ingresos`
- `/egresos`

### 8. Componentes compartidos

Si un componente se reutiliza en mas de un modulo, moverlo a:

- `src/components/`

Si es exclusivo de un modulo, mantenerlo dentro del modulo.

## Convenciones del frontend

- usar JavaScript, no TypeScript, mientras el proyecto siga en esta fase
- mantener nombres de archivos por responsabilidad clara
- componentes de pagina en PascalCase
- hooks y helpers en camelCase
- no guardar tokens en almacenamiento persistente
- no duplicar permisos en constantes dispersas; tomar la verdad del backend
- no llamar a la API con URLs hardcodeadas fuera de `config/env.js`

## Contrato actual con el backend

### Login

```http
POST /api/v1/auth/login
```

Body:

```json
{
  "username": "admin",
  "password": "Admin12345!"
}
```

### Sesion actual

```http
GET /api/v1/auth/me
```

### Cambio de contrasena

```http
POST /api/v1/auth/change-password
```

### Roles

```http
GET /api/v1/roles
```

### Usuarios

```http
GET /api/v1/users
POST /api/v1/users
PATCH /api/v1/users/{id}/status
```

## Problemas comunes

### El login carga pero no entra

Revisar:

- que el backend este corriendo en `localhost:8000`
- que `VITE_API_URL` apunte a `/api/v1`
- que el navegador permita cookies para localhost

### El frontend recibe `401` todo el tiempo

Revisar:

- `FRONTEND_URL` en backend
- CORS con `allow_credentials=True`
- que el backend este enviando la cookie del refresh

### Un usuario ve el menu pero backend responde `403`

Eso significa que la proteccion real del backend esta funcionando y el frontend necesita sincronizar mejor el permiso mostrado.

## Siguiente extension recomendada

Los proximos modulos deben construirse sobre esta base:

1. inventario boutique
2. inventario taller
3. pedidos
4. pagos
5. ingresos y egresos

Cada uno debe:

- tener sus propias paginas
- tener rutas protegidas
- tener endpoints por dominio
- integrarse al layout autenticado
