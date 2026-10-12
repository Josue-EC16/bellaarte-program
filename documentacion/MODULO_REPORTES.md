# MODULO REPORTES

## RESUMEN

Esta v1 incorpora una capa transversal de reportes operativos y analiticos para:

- `CLIENTES`
- `BOUTIQUE`
- `FLETES`
- `TALLER`
- `MONEDAS`

La solucion sigue dos niveles:

1. `RESUMENES EMBEBIDOS` dentro de las pantallas operativas ya existentes.
2. `PANELES ANALITICOS` en subrutas `/reportes` con impresion HTML profesional y exportacion PDF mediante navegador.

## ALCANCE FUNCIONAL

### Indicadores basicos en listados

Cada pagina operativa dentro del alcance muestra ahora:

- `TOTAL GLOBAL`
- `TOTAL FILTRADO`
- desglose principal por estado o clasificacion

Los indicadores consumen endpoints `GET /resumen` y reutilizan exactamente los mismos filtros activos del listado para evitar diferencias entre tabla y KPI.

### Reportes profundos nuevos

#### Clientes

- clientes por pais
- clientes por ciudad
- activos vs inactivos
- registros por periodo
- clientes con mas pedidos activos

#### Boutique

- cantidades vendidas por item
- cantidades vendidas por tipo
- productos mas vendidos
- categorias en distribucion pastel
- entradas por item y proveedor
- proveedor mas barato por producto
- metodos de pago por moneda

#### Fletes

- vestidos por estado
- salidas por periodo
- salidas por estado
- vestidos con mas salidas
- devoluciones criticas

#### Taller

- materiales por tipo
- materiales con mas salidas
- materiales con mas entradas
- salidas por destino
- referencia mas barata por material

#### Monedas

- monedas activas vs inactivas
- moneda base
- evolucion de tipos de cambio
- uso comercial por moneda
- metodos de pago por moneda

## ARQUITECTURA IMPLEMENTADA

### Backend

Se agrego una capa compartida:

- `backend/app/schemas/reporting.py`
- `backend/app/services/module_report_service.py`

Responsabilidades:

- normalizacion de `period`
- resolucion index-friendly de `date_from/date_to`
- construccion uniforme de:
  - `filters_applied`
  - `kpis`
  - `series`
  - `rankings`
  - `table_rows`

### Frontend

Se agrego un kit reutilizable:

- `ReportPageHeader`
- `ReportKpiCard`
- `ReportChartCard`
- `ReportLegendNumeric`
- `ReportEmptyState`
- `ReportSummaryStrip`
- `ReportPrintableLayout`
- `useListingSummary`

## ENDPOINTS NUEVOS

### Resumenes de listados

- `GET /api/v1/clientes/resumen`
- `GET /api/v1/boutique/types/resumen`
- `GET /api/v1/boutique/proveedores/resumen`
- `GET /api/v1/boutique/items/resumen`
- `GET /api/v1/boutique/entries/resumen`
- `GET /api/v1/boutique/sales/resumen`
- `GET /api/v1/fletes/resumen`
- `GET /api/v1/fletes/salidas/resumen`
- `GET /api/v1/taller/types/resumen`
- `GET /api/v1/taller/inventory/resumen`
- `GET /api/v1/taller/entries/resumen`
- `GET /api/v1/taller/outputs/resumen`
- `GET /api/v1/monedas/resumen`
- `GET /api/v1/monedas/tipos-cambio/resumen`

### Paneles analiticos

- `GET /api/v1/clientes/reportes/panel`
- `GET /api/v1/boutique/reportes/panel`
- `GET /api/v1/fletes/reportes/panel`
- `GET /api/v1/taller/reportes/panel`
- `GET /api/v1/monedas/reportes/panel`

## RUTAS FRONTEND

- `/app/clientes/reportes`
- `/app/clientes/reportes/imprimir`
- `/app/boutique/reportes`
- `/app/boutique/reportes/imprimir`
- `/app/fletes/reportes`
- `/app/fletes/reportes/imprimir`
- `/app/taller/reportes`
- `/app/taller/reportes/imprimir`
- `/app/monedas/reportes`
- `/app/monedas/reportes/imprimir`

## PERMISOS

- `clients_reports:view`
- `clients_reports:print`
- `boutique_reports:view`
- `boutique_reports:print`
- `flete_reports:view`
- `flete_reports:print`
- `workshop_reports:view`
- `workshop_reports:print`
- `currency_reports:view`
- `currency_reports:print`

## REGLAS TECNICAS IMPORTANTES

- `date_from/date_to` tienen prioridad sobre `period`
- `period=all` no restringe por fecha
- el `WHERE` usa rangos crudos y no funciones sobre columnas indexadas
- las vistas imprimibles usan los mismos endpoints del panel interactivo
- la exportacion PDF se resuelve con HTML + `window.print()`

## VALIDACION REALIZADA

- `frontend`: `pnpm lint`
- `backend`: `.\venv\Scripts\python -m pytest`

Pendiente de entorno:

- `pnpm build` puede requerir salir del sandbox para que `esbuild` levante su proceso en esta sesion de trabajo.
