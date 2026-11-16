# TÉCNICAS, REPORTES Y BUENAS PRÁCTICAS
## Guía de Referencia para el Desarrollo de Reportes Administrativos con React y Recharts

**Proyecto:** Sistema Web Administrativo y de Gestión del Conocimiento Organizacional  
**Caso:** BELLAARTE BOUTIQUE  
**Autor:** Marcelo Josué Escobar Chipana  
**Versión:** 1.0 — Gestión 2026

---

## ÍNDICE

1. [Fundamentos de los Reportes Administrativos](#1-fundamentos-de-los-reportes-administrativos)
2. [Taxonomía de Reportes para un Sistema Administrativo](#2-taxonomía-de-reportes-para-un-sistema-administrativo)
3. [Principios de Diseño UX/UI para Reportes](#3-principios-de-diseño-uxui-para-reportes)
4. [Recharts: Arquitectura, Componentes y Patrones](#4-recharts-arquitectura-componentes-y-patrones)
5. [Catálogo de Gráficos: Cuándo Usar Cada Uno](#5-catálogo-de-gráficos-cuándo-usar-cada-uno)
6. [Buenas Prácticas de Implementación con React + Recharts](#6-buenas-prácticas-de-implementación-con-react--recharts)
7. [Estructura de Componentes Reutilizables](#7-estructura-de-componentes-reutilizables)
8. [Paleta de Colores y Accesibilidad en Reportes](#8-paleta-de-colores-y-accesibilidad-en-reportes)
9. [Manejo de Datos: Transformación y Normalización](#9-manejo-de-datos-transformación-y-normalización)
10. [Patrones Anti-Reporte: Qué Evitar](#10-patrones-anti-reporte-qué-evitar)
11. [Plantillas de Código para Reportes Comunes](#11-plantillas-de-código-para-reportes-comunes)
12. [Checklist de Calidad para Reportes](#12-checklist-de-calidad-para-reportes)
13. [Referencias y Recursos](#13-referencias-y-recursos)

---

## 1. Fundamentos de los Reportes Administrativos

### 1.1 ¿Qué es un Reporte Administrativo?

Un reporte administrativo es una representación estructurada de datos operativos o financieros que tiene como propósito apoyar la **toma de decisiones** gerenciales. No es simplemente una tabla de datos: es una narrativa visual que responde a una pregunta de negocio específica.

Todo reporte administrativo responde a una de estas tres preguntas fundamentales:

- **¿Qué pasó?** → Reporte descriptivo (histórico)
- **¿Por qué pasó?** → Reporte diagnóstico (análisis de causas)
- **¿Qué pasará?** → Reporte predictivo (proyecciones)

En el contexto de BELLAARTE BOUTIQUE, los reportes deben responder preguntas como:
> ¿Cuántos pedidos se procesaron este mes? ¿Cuál es el saldo pendiente de cobro? ¿Qué tipo de vestido genera más ingresos? ¿Qué semana tiene mayor saturación de agenda?

### 1.2 Ciclo de Vida de un Reporte

```
[Fuente de Datos]
     ↓
[Extracción (API FastAPI)]
     ↓
[Transformación (lógica React/JS)]
     ↓
[Visualización (Recharts)]
     ↓
[Interpretación (usuario final)]
     ↓
[Decisión / Acción]
```

### 1.3 Regla de Oro: Una Pregunta, Un Gráfico

Cada componente visual dentro de un reporte debe responder **exactamente una pregunta de negocio**. Si un gráfico intenta responder dos preguntas simultáneamente, debe dividirse en dos gráficos separados.

**Incorrecto:**
> Gráfico que muestra ingresos totales, egresos, saldo neto y cantidad de pedidos en un solo chart.

**Correcto:**
> - Gráfico 1: Ingresos vs Egresos por mes
> - Gráfico 2: Cantidad de pedidos por estado

---

## 2. Taxonomía de Reportes para un Sistema Administrativo

Los reportes se clasifican según su dominio funcional y su frecuencia de consulta.

### 2.1 Reportes Operativos (Frecuencia: Diaria / Semanal)

| Reporte | Pregunta que responde | Tipo de gráfico recomendado |
|---|---|---|
| Agenda del día | ¿Qué pruebas y entregas hay hoy? | Timeline / Lista estructurada |
| Estado de pedidos activos | ¿Cuántos pedidos están en cada estado? | Donut chart / Horizontal bar |
| Pagos pendientes | ¿Quién tiene saldo por pagar? | Tabla ordenada con indicadores |
| Movimientos de inventario del día | ¿Qué salió o entró hoy? | Tabla con filtros de fecha |

### 2.2 Reportes Comerciales (Frecuencia: Semanal / Mensual)

| Reporte | Pregunta que responde | Tipo de gráfico recomendado |
|---|---|---|
| Ingresos por tipo de servicio | ¿Qué genera más dinero: confección, venta o flete? | Pie chart / Stacked bar |
| Pedidos por tipo de vestido | ¿Qué tipo de vestido se pide más? | Bar chart horizontal |
| Clientas nuevas vs recurrentes | ¿Cuánto estamos fidelizando? | Area chart comparativo |
| Días con mayor demanda | ¿Qué días de la semana tienen más actividad? | Heatmap / Bar chart agrupado |

### 2.3 Reportes Financieros (Frecuencia: Mensual / Por Período de Caja)

| Reporte | Pregunta que responde | Tipo de gráfico recomendado |
|---|---|---|
| Estado de Resultados | ¿Cuánto se ganó y se gastó en el período? | Composed chart (bar + line) |
| Flujo de caja por período | ¿Cómo evolucionó el saldo en el tiempo? | Area chart |
| Egresos por categoría | ¿En qué se gastó más? | Treemap / Pie chart |
| Comparativo mensual | ¿Mejoró o empeoró respecto al mes anterior? | Bar chart agrupado |

### 2.4 Reportes de Inventario (Frecuencia: Semanal)

| Reporte | Pregunta que responde | Tipo de gráfico recomendado |
|---|---|---|
| Niveles de stock por categoría | ¿Qué materiales están por agotarse? | Bar chart con línea de umbral |
| Rotación de inventario boutique | ¿Qué vestidos se mueven más? | Ranking (horizontal bar) |
| Fletes activos y disponibilidad | ¿Qué vestidos están alquilados ahora? | Tabla con estado de color |

### 2.5 Reportes de Conocimiento (KMS-RAG) (Frecuencia: Semanal / Mensual)

| Reporte | Pregunta que responde | Tipo de gráfico recomendado |
|---|---|---|
| Consultas por rol de usuario | ¿Quiénes usan más el sistema de consulta? | Bar chart |
| Temas más consultados | ¿Qué procesos generan más dudas? | Word cloud / Horizontal bar |
| Vacíos de conocimiento detectados | ¿Qué preguntas no pudieron responderse? | Lista priorizada con badge de frecuencia |
| Evolución de documentación | ¿Cuánto conocimiento se ha formalizado? | Line chart de progreso |

---

## 3. Principios de Diseño UX/UI para Reportes

### 3.1 La Jerarquía Visual en Dashboards

Un dashboard bien diseñado sigue la regla de **lectura en Z o en F**: el ojo recorre primero de izquierda a derecha por la parte superior, luego baja en diagonal. Las métricas más importantes deben ocupar la zona superior izquierda.

```
+------------------+------------------+------------------+
|  KPI PRINCIPAL   |   KPI SECUNDARIO |   KPI TERCIARIO  |  ← Zona de alta atención
|  Ingresos netos  |  Pedidos activos |  Saldo pendiente |
+------------------+------------------+------------------+
|                                                        |
|         GRÁFICO PRINCIPAL (más espacio)                |  ← Zona de análisis
|         Estado de Resultados — Últimos 6 meses         |
|                                                        |
+----------------------------+---------------------------+
|  Gráfico secundario A      |  Gráfico secundario B     |  ← Zona de detalle
|  Pedidos por tipo          |  Egresos por categoría    |
+----------------------------+---------------------------+
|         TABLA DE DETALLE CON FILTROS                   |  ← Zona de datos crudos
+--------------------------------------------------------+
```

### 3.2 KPI Cards: El Primer Nivel de Información

Las KPI Cards (tarjetas de indicador clave) son el primer elemento que el usuario ve. Deben seguir estas reglas:

**Anatomía de una KPI Card bien diseñada:**

```
+------------------------------------+
|  ÍCONO   LABEL (pequeño, mayúsc.) |
|          INGRESOS DEL MES          |
|                                    |
|    Bs. 24,850.00  ← valor grande   |
|    ↑ +12.4% vs mes anterior        |  ← comparador con color (verde/rojo)
+------------------------------------+
```

**Reglas para KPI Cards:**
- El valor numérico debe ser el elemento más grande visualmente (mínimo 28–32px)
- El label debe estar en mayúsculas pequeñas o peso ligero (no compita con el número)
- Siempre incluir un comparador: vs período anterior, vs meta, vs promedio
- El color del comparador indica dirección: verde = positivo, rojo = negativo, gris = neutro
- Máximo 4-6 KPI Cards en la pantalla al mismo tiempo

### 3.3 Densidad de Información: La Regla del Contexto

El nivel de detalle debe adaptarse al rol del usuario:

| Rol | Nivel de detalle recomendado | ¿Puede exportar? |
|---|---|---|
| Administrador | Alto (todas las métricas y filtros) | Sí |
| Encargada de Boutique | Medio (operativo, agenda, pedidos) | Limitado |
| Cajero | Bajo (solo financiero del período) | No |
| Modista | Mínimo (solo agenda y pedidos propios) | No |

### 3.4 Principio de Progresión: De lo General a lo Específico

Los reportes deben seguir el flujo **Summary → Detail → Raw Data**:

1. **Nivel 1 — Summary:** KPI cards con un solo número
2. **Nivel 2 — Detail:** Gráfico que muestra la distribución o tendencia
3. **Nivel 3 — Raw Data:** Tabla con filas individuales y filtros

El usuario debe poder "perforar" (drill-down) desde el resumen hasta el dato individual sin perder el contexto.

### 3.5 Estados de Carga y Vacío

Todo componente de reporte debe manejar tres estados visuales:

```
Estado LOADING:     Skeleton loader (no spinner genérico)
Estado VACÍO:       Mensaje contextual + acción sugerida
Estado CON DATOS:   El gráfico/tabla real
Estado ERROR:       Mensaje claro + botón de reintentar
```

**Nunca mostrar un gráfico vacío sin contexto.** Si no hay datos, explicar por qué y qué debe hacer el usuario.

### 3.6 Filtros: Posición y Comportamiento

Los filtros son la herramienta de exploración del usuario. Reglas:

- **Posición:** Siempre en la parte superior del reporte, antes del contenido
- **Feedback inmediato:** Los gráficos deben actualizarse en tiempo real al cambiar filtros
- **Estado visible:** El usuario siempre debe saber qué filtro está activo (badge o label destacado)
- **Resetear fácil:** Botón "Limpiar filtros" siempre visible cuando hay filtros activos
- **Filtros comunes para BELLAARTE BOUTIQUE:**
  - Rango de fechas (selector de período: día, semana, mes, personalizado)
  - Tipo de servicio (confección, venta directa, flete)
  - Estado del pedido
  - Período de caja (corte_caja)

### 3.7 Tipografía en Reportes

| Elemento | Tamaño | Peso | Color |
|---|---|---|---|
| Título de sección | 18–20px | 700 (Bold) | #1A1A2E |
| Subtítulo / label de KPI | 11–12px | 500 | #6B7280 |
| Valor KPI | 28–36px | 700 | #111827 |
| Etiquetas de ejes | 11–12px | 400 | #9CA3AF |
| Valores en tooltips | 13–14px | 600 | #111827 |
| Texto de tabla (datos) | 13–14px | 400 | #374151 |
| Texto de tabla (cabecera) | 12px | 600 | #6B7280 |

### 3.8 Espaciado y Grillas

Usar un sistema de grilla de 8px. Los espaciados deben ser múltiplos de 8:

- Padding interno de cards: 24px (3 × 8)
- Gap entre cards: 16px (2 × 8)
- Margen de sección: 32px (4 × 8)
- Padding de tabla: 12px vertical, 16px horizontal

---

## 4. Recharts: Arquitectura, Componentes y Patrones

### 4.1 ¿Por Qué Recharts?

Recharts es la librería de visualización más utilizada en el ecosistema React por las siguientes razones técnicas:

- Construida completamente sobre **componentes React** y **SVG nativo**
- Diseño **declarativo**: los gráficos se construyen como JSX, no como configuración imperativa
- **Responsive por diseño** mediante `ResponsiveContainer`
- Soporte completo para animaciones con control granular
- Compatibilidad con **React 19** y entornos modernos de Vite
- Ecosistema maduro con documentación detallada

**Versión recomendada:** `recharts@2.12+` (compatible con React 18/19)

```bash
npm install recharts
```

### 4.2 Arquitectura de Componentes en Recharts

Recharts sigue una **arquitectura composicional**: los gráficos se construyen anidando componentes especializados dentro de un componente contenedor.

```
<ResponsiveContainer>         ← Hace el gráfico responsive
  <[TipoDeGrafico]>           ← Define el tipo (LineChart, BarChart, etc.)
    <CartesianGrid />          ← Cuadrícula del fondo (opcional)
    <XAxis />                  ← Eje horizontal
    <YAxis />                  ← Eje vertical
    <Tooltip />                ← Info al hover
    <Legend />                 ← Leyenda
    <[SeriesDeData] />         ← Los datos reales (Line, Bar, Area, Pie, etc.)
  </[TipoDeGrafico]>
</ResponsiveContainer>
```

### 4.3 Componentes Principales de Recharts

#### Contenedores de Gráficos

| Componente | Uso | Cuándo usarlo |
|---|---|---|
| `LineChart` | Líneas de tendencia | Evolución en el tiempo (ingresos mes a mes) |
| `BarChart` | Barras verticales u horizontales | Comparaciones entre categorías |
| `AreaChart` | Área bajo la curva | Acumulados o volúmenes en el tiempo |
| `PieChart` | Torta / Donut | Distribución de partes de un todo (máx. 5-6 segmentos) |
| `ComposedChart` | Combinación | Cuando necesitas bars + lines en el mismo gráfico |
| `RadarChart` | Tela de araña | Evaluaciones multidimensionales |
| `ScatterChart` | Puntos dispersos | Correlación entre dos variables |
| `Treemap` | Bloques anidados | Distribución jerárquica (egresos por categoría) |

#### Componentes de Soporte

| Componente | Propósito clave |
|---|---|
| `ResponsiveContainer` | Adapta el gráfico al ancho del contenedor padre |
| `CartesianGrid` | Líneas de referencia horizontales/verticales |
| `XAxis` / `YAxis` | Configuración de ejes (formato, etiquetas, ticks) |
| `Tooltip` | Popup informativo al hacer hover |
| `Legend` | Leyenda de series |
| `ReferenceLine` | Línea de referencia fija (ej: meta de ventas) |
| `ReferenceArea` | Área sombreada de referencia (ej: rango objetivo) |
| `Brush` | Control deslizante para zoom en el eje X |
| `Cell` | Colorización individual de segmentos en Pie/Bar |
| `LabelList` | Etiquetas de valor sobre las barras/puntos |
| `ErrorBar` | Barras de error estadístico |

### 4.4 Flujo de Datos en Recharts

Recharts espera que los datos estén en formato de **array de objetos planos**. Cada objeto representa un punto de datos.

```javascript
// Formato estándar para LineChart y BarChart
const data = [
  { mes: "Ene", ingresos: 15200, egresos: 8400 },
  { mes: "Feb", ingresos: 18500, egresos: 9200 },
  { mes: "Mar", ingresos: 22100, egresos: 11500 },
];

// Formato para PieChart
const dataPie = [
  { name: "Confección", value: 65000, color: "#6366F1" },
  { name: "Venta Directa", value: 18000, color: "#10B981" },
  { name: "Flete", value: 8500, color: "#F59E0B" },
];
```

---

## 5. Catálogo de Gráficos: Cuándo Usar Cada Uno

### 5.1 LineChart — Tendencias Temporales

**Usar cuando:** Mostrar cómo cambia una métrica a lo largo del tiempo.

**Ideal para BELLAARTE BOUTIQUE:**
- Ingresos mensuales de los últimos 6 / 12 meses
- Evolución de pedidos registrados por semana
- Crecimiento de clientas a lo largo del año

**Reglas:**
- Mínimo 5 puntos de datos para que la línea tenga sentido
- No usar más de 3-4 líneas simultáneas (la legibilidad cae drásticamente)
- Siempre incluir la línea de 0 en el eje Y si los valores pueden ser negativos
- Usar `dot={false}` cuando hay muchos puntos (más de 20) para no saturar el gráfico

```jsx
// Ejemplo mínimo funcional
<ResponsiveContainer width="100%" height={300}>
  <LineChart data={data}>
    <CartesianGrid strokeDasharray="3 3" stroke="#F3F4F6" />
    <XAxis dataKey="mes" tick={{ fontSize: 12, fill: "#9CA3AF" }} />
    <YAxis tickFormatter={(v) => `Bs. ${v.toLocaleString()}`} />
    <Tooltip formatter={(value) => [`Bs. ${value.toLocaleString()}`, "Ingresos"]} />
    <Line 
      type="monotone" 
      dataKey="ingresos" 
      stroke="#6366F1" 
      strokeWidth={2}
      dot={{ r: 4 }}
      activeDot={{ r: 6 }}
    />
  </LineChart>
</ResponsiveContainer>
```

### 5.2 BarChart — Comparaciones entre Categorías

**Usar cuando:** Comparar magnitudes entre diferentes categorías discretas.

**Ideal para BELLAARTE BOUTIQUE:**
- Cantidad de pedidos por tipo de vestido (novia, 15 años, fiesta)
- Egresos por categoría de gasto
- Pedidos por estado actual

**Reglas:**
- Barras **verticales** para comparar categorías (hasta 8-10 elementos)
- Barras **horizontales** (`layout="vertical"`) cuando los labels son largos
- No usar más de 3 series agrupadas (usa `BarChart` con múltiples `<Bar>`)
- Ordenar las barras de mayor a menor cuando el orden no es temporal

```jsx
// Barras horizontales (mejor para categorías con nombres largos)
<ResponsiveContainer width="100%" height={250}>
  <BarChart data={dataPorTipo} layout="vertical" margin={{ left: 80 }}>
    <CartesianGrid strokeDasharray="3 3" horizontal={false} stroke="#F3F4F6" />
    <XAxis type="number" tick={{ fontSize: 12 }} />
    <YAxis type="category" dataKey="tipo" tick={{ fontSize: 12, fill: "#374151" }} />
    <Tooltip />
    <Bar dataKey="cantidad" fill="#6366F1" radius={[0, 4, 4, 0]} barSize={20}>
      <LabelList dataKey="cantidad" position="right" style={{ fontSize: 12 }} />
    </Bar>
  </BarChart>
</ResponsiveContainer>
```

### 5.3 AreaChart — Volúmenes Acumulados

**Usar cuando:** Mostrar el volumen o masa de datos a lo largo del tiempo, especialmente cuando el área bajo la curva tiene significado (dinero acumulado, stock acumulado).

**Ideal para BELLAARTE BOUTIQUE:**
- Flujo de caja acumulado en el período
- Ingresos acumulados vs egresos acumulados
- Evolución del saldo neto

```jsx
// Area con gradiente para mayor impacto visual
<defs>
  <linearGradient id="colorIngresos" x1="0" y1="0" x2="0" y2="1">
    <stop offset="5%" stopColor="#6366F1" stopOpacity={0.2} />
    <stop offset="95%" stopColor="#6366F1" stopOpacity={0} />
  </linearGradient>
</defs>
<Area 
  type="monotone" 
  dataKey="saldo" 
  stroke="#6366F1"
  strokeWidth={2}
  fill="url(#colorIngresos)" 
/>
```

### 5.4 PieChart / DonutChart — Distribución de Partes

**Usar cuando:** Mostrar cómo se distribuye un total entre categorías. **Nunca usar con más de 6 segmentos.**

**Ideal para BELLAARTE BOUTIQUE:**
- Distribución de ingresos por tipo de servicio
- Proporción de pedidos por estado
- Distribución de egresos por categoría principal

**Reglas críticas:**
- Si tienes más de 6 categorías, agrupa las menores en "Otros"
- El **donut** (con `innerRadius`) es visualmente superior al pie clásico porque permite mostrar un KPI en el centro
- Nunca usar 3D en gráficos de torta — distorsiona la percepción de área
- Las etiquetas dentro de los segmentos solo si el segmento es suficientemente grande (>10%)

```jsx
// DonutChart con valor central
const renderCenterLabel = ({ viewBox }) => {
  const { cx, cy } = viewBox;
  return (
    <text x={cx} y={cy} textAnchor="middle" dominantBaseline="central">
      <tspan fontSize={24} fontWeight={700} fill="#111827">Bs. 91,500</tspan>
      <tspan fontSize={12} fill="#9CA3AF" x={cx} dy={24}>Total ingresos</tspan>
    </text>
  );
};

<PieChart>
  <Pie
    data={dataPie}
    cx="50%"
    cy="50%"
    innerRadius={70}
    outerRadius={110}
    paddingAngle={3}
    dataKey="value"
  >
    {dataPie.map((entry, index) => (
      <Cell key={index} fill={entry.color} />
    ))}
    <Label content={renderCenterLabel} position="center" />
  </Pie>
  <Tooltip formatter={(value) => `Bs. ${value.toLocaleString()}`} />
</PieChart>
```

### 5.5 ComposedChart — Combinación de Tipos

**Usar cuando:** Necesitas combinar barras (volúmenes) con líneas (tendencia o acumulado) en el mismo espacio visual. Es el gráfico del **Estado de Resultados** por excelencia.

**Ideal para BELLAARTE BOUTIQUE:**
- Estado de Resultados: barras de ingresos y egresos + línea de saldo neto
- Pedidos procesados (barras) con línea de tendencia (media móvil)

```jsx
<ComposedChart data={dataEstadoResultados}>
  <CartesianGrid strokeDasharray="3 3" stroke="#F3F4F6" />
  <XAxis dataKey="mes" />
  <YAxis yAxisId="left" />
  <YAxis yAxisId="right" orientation="right" />
  <Tooltip />
  <Legend />
  <Bar yAxisId="left" dataKey="ingresos" fill="#10B981" name="Ingresos" />
  <Bar yAxisId="left" dataKey="egresos" fill="#EF4444" name="Egresos" />
  <Line yAxisId="right" type="monotone" dataKey="saldoNeto" stroke="#6366F1" 
        strokeWidth={2} name="Saldo Neto" dot={false} />
</ComposedChart>
```

---

## 6. Buenas Prácticas de Implementación con React + Recharts

### 6.1 Separación de Responsabilidades

Nunca mezclar lógica de datos con lógica de presentación. Seguir este patrón de tres capas:

```
hooks/
  useReporteIngresos.js    ← Lógica de datos (fetch, transform, state)
  useReporteEgresos.js

utils/
  reporteFormatters.js     ← Funciones de formateo (fechas, moneda, %)
  reporteTransformers.js   ← Transformación de datos de API → formato Recharts

components/
  reportes/
    KPICard.jsx            ← Componente visual puro
    LineChartIngresos.jsx  ← Gráfico específico
    TablaDetallePedidos.jsx
    ReporteEstadoResultados.jsx  ← Composición de todo lo anterior
```

### 6.2 Custom Hook para Reportes

```javascript
// hooks/useReporteFinanciero.js
import { useState, useEffect, useCallback } from "react";

export const useReporteFinanciero = (periodoId) => {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const fetchData = useCallback(async () => {
    if (!periodoId) return;
    
    setLoading(true);
    setError(null);
    
    try {
      const response = await fetch(`/api/v1/reportes/financiero?periodo=${periodoId}`);
      if (!response.ok) throw new Error("Error al cargar datos del reporte");
      const json = await response.json();
      setData(transformarDatosFinancieros(json)); // función de transformación
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, [periodoId]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  return { data, loading, error, refetch: fetchData };
};
```

### 6.3 Formateo Consistente de Valores

Centralizar todas las funciones de formato en un único archivo de utilidades:

```javascript
// utils/reporteFormatters.js

// Formato de moneda boliviana
export const formatBoliviano = (valor, decimales = 2) => {
  if (valor === null || valor === undefined) return "—";
  return `Bs. ${Number(valor).toLocaleString("es-BO", {
    minimumFractionDigits: decimales,
    maximumFractionDigits: decimales,
  })}`;
};

// Formato de porcentaje con signo de dirección
export const formatPorcentaje = (valor, mostrarSigno = true) => {
  if (valor === null || valor === undefined) return "—";
  const signo = mostrarSigno && valor > 0 ? "+" : "";
  return `${signo}${Number(valor).toFixed(1)}%`;
};

// Formato de fecha para eje X de gráficos
export const formatFechaEje = (fechaStr, granularidad = "mes") => {
  const fecha = new Date(fechaStr);
  if (granularidad === "mes") return fecha.toLocaleDateString("es-BO", { month: "short" });
  if (granularidad === "dia") return fecha.toLocaleDateString("es-BO", { day: "2-digit", month: "2-digit" });
  if (granularidad === "semana") return `Sem ${getWeekNumber(fecha)}`;
  return fechaStr;
};

// Formato de número corto para etiquetas de ejes (1200 → 1.2k)
export const formatNumeroCorto = (valor) => {
  if (valor >= 1000000) return `${(valor / 1000000).toFixed(1)}M`;
  if (valor >= 1000) return `${(valor / 1000).toFixed(1)}k`;
  return valor.toString();
};

// Color según variación porcentual
export const colorVariacion = (valor) => {
  if (valor > 0) return "#10B981"; // verde
  if (valor < 0) return "#EF4444"; // rojo
  return "#9CA3AF"; // gris neutro
};

// Ícono de flecha según variación
export const iconoVariacion = (valor) => {
  if (valor > 0) return "↑";
  if (valor < 0) return "↓";
  return "→";
};
```

### 6.4 ResponsiveContainer: Uso Correcto

`ResponsiveContainer` requiere un elemento padre con dimensiones definidas. Un error común es colocarlo en un contenedor sin altura.

```jsx
// ❌ INCORRECTO: el div padre no tiene altura
<div>
  <ResponsiveContainer width="100%" height="100%">
    <LineChart />
  </ResponsiveContainer>
</div>

// ✅ CORRECTO: siempre dar altura explícita en px
<div style={{ width: "100%", height: 300 }}>
  <ResponsiveContainer width="100%" height="100%">
    <LineChart />
  </ResponsiveContainer>
</div>

// ✅ TAMBIÉN CORRECTO: altura directamente en ResponsiveContainer
<ResponsiveContainer width="100%" height={300}>
  <LineChart />
</ResponsiveContainer>
```

### 6.5 Tooltip Personalizado

El tooltip por defecto de Recharts es funcional pero genérico. Para reportes profesionales, siempre personalizar:

```jsx
// components/reportes/CustomTooltip.jsx
const CustomTooltip = ({ active, payload, label, tipo = "moneda" }) => {
  if (!active || !payload || !payload.length) return null;

  return (
    <div style={{
      backgroundColor: "#FFFFFF",
      border: "1px solid #E5E7EB",
      borderRadius: 8,
      padding: "12px 16px",
      boxShadow: "0 4px 12px rgba(0,0,0,0.1)",
      minWidth: 160,
    }}>
      <p style={{ fontSize: 12, color: "#6B7280", marginBottom: 8, fontWeight: 600 }}>
        {label}
      </p>
      {payload.map((item, idx) => (
        <div key={idx} style={{ display: "flex", justifyContent: "space-between", gap: 16, marginBottom: 4 }}>
          <span style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 13, color: "#374151" }}>
            <span style={{ width: 8, height: 8, borderRadius: "50%", backgroundColor: item.color, display: "inline-block" }} />
            {item.name}
          </span>
          <span style={{ fontSize: 13, fontWeight: 700, color: "#111827" }}>
            {tipo === "moneda" ? formatBoliviano(item.value) : item.value}
          </span>
        </div>
      ))}
    </div>
  );
};

// Uso:
<Tooltip content={<CustomTooltip tipo="moneda" />} />
```

### 6.6 Manejo de Estados de Carga con Skeleton

```jsx
// components/reportes/GraficoSkeleton.jsx
const GraficoSkeleton = ({ height = 300 }) => (
  <div style={{ 
    width: "100%", 
    height, 
    backgroundColor: "#F3F4F6",
    borderRadius: 8,
    animation: "pulse 1.5s ease-in-out infinite",
    display: "flex",
    alignItems: "flex-end",
    padding: 16,
    gap: 8,
  }}>
    {[60, 80, 45, 90, 70, 55, 85].map((h, i) => (
      <div
        key={i}
        style={{
          flex: 1,
          height: `${h}%`,
          backgroundColor: "#E5E7EB",
          borderRadius: "4px 4px 0 0",
        }}
      />
    ))}
  </div>
);
```

### 6.7 Animaciones: Cuándo y Cómo

Las animaciones en reportes deben ser **sutiles y funcionales**, no decorativas. Recharts tiene animaciones por defecto:

```jsx
// Controlar la animación por motivos de performance
<Line 
  dataKey="ingresos"
  isAnimationActive={true}           // true por defecto
  animationBegin={0}                 // delay antes de empezar (ms)
  animationDuration={800}            // duración total (ms)
  animationEasing="ease-out"         // tipo de easing
/>

// Para tablas de datos con muchas filas, desactivar animaciones:
<Bar dataKey="valor" isAnimationActive={false} />
```

**Regla:** Desactivar animaciones si el usuario está filtrando activamente (cada cambio de filtro no debería re-animar todo).

---

## 7. Estructura de Componentes Reutilizables

### 7.1 Componente KPICard

```jsx
// components/reportes/KPICard.jsx
import { formatBoliviano, formatPorcentaje, colorVariacion, iconoVariacion } from "@/utils/reporteFormatters";

const KPICard = ({
  titulo,
  valor,
  unidad = "moneda",     // "moneda" | "numero" | "porcentaje"
  variacion = null,      // número porcentual vs período anterior
  descripcionVariacion = "vs. período anterior",
  icono,
  loading = false,
}) => {
  const valorFormateado = 
    unidad === "moneda" ? formatBoliviano(valor) :
    unidad === "porcentaje" ? formatPorcentaje(valor) :
    valor?.toLocaleString("es-BO") ?? "—";

  if (loading) {
    return (
      <div style={estilos.card}>
        <div style={{ width: "60%", height: 12, backgroundColor: "#F3F4F6", borderRadius: 4 }} />
        <div style={{ width: "80%", height: 36, backgroundColor: "#F3F4F6", borderRadius: 4, marginTop: 12 }} />
      </div>
    );
  }

  return (
    <div style={estilos.card}>
      <div style={estilos.encabezado}>
        {icono && <span style={estilos.icono}>{icono}</span>}
        <span style={estilos.titulo}>{titulo}</span>
      </div>
      <div style={estilos.valor}>{valorFormateado}</div>
      {variacion !== null && (
        <div style={{ color: colorVariacion(variacion), fontSize: 13, marginTop: 8, fontWeight: 500 }}>
          {iconoVariacion(variacion)} {formatPorcentaje(variacion, true)} {descripcionVariacion}
        </div>
      )}
    </div>
  );
};

const estilos = {
  card: {
    backgroundColor: "#FFFFFF",
    border: "1px solid #E5E7EB",
    borderRadius: 12,
    padding: 24,
    minWidth: 200,
  },
  encabezado: {
    display: "flex",
    alignItems: "center",
    gap: 8,
    marginBottom: 12,
  },
  icono: {
    fontSize: 18,
  },
  titulo: {
    fontSize: 12,
    fontWeight: 600,
    color: "#6B7280",
    textTransform: "uppercase",
    letterSpacing: "0.05em",
  },
  valor: {
    fontSize: 32,
    fontWeight: 700,
    color: "#111827",
    lineHeight: 1.1,
  },
};

export default KPICard;
```

### 7.2 Componente de Tabla de Reporte

```jsx
// components/reportes/TablaReporte.jsx
const TablaReporte = ({
  columnas,    // [{ key, label, format, align }]
  datos,       // array de objetos
  loading,
  emptyMessage = "No hay datos para el período seleccionado.",
  onRowClick,  // opcional: acción al hacer click en una fila
}) => {
  if (loading) return <TablaReporteSkeleton columnas={columnas.length} />;

  return (
    <div style={{ overflowX: "auto" }}>
      <table style={estilosTabla.tabla}>
        <thead>
          <tr>
            {columnas.map((col) => (
              <th key={col.key} style={{ ...estilosTabla.th, textAlign: col.align || "left" }}>
                {col.label}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {datos.length === 0 ? (
            <tr>
              <td colSpan={columnas.length} style={estilosTabla.celda_vacia}>
                {emptyMessage}
              </td>
            </tr>
          ) : (
            datos.map((fila, idx) => (
              <tr 
                key={idx} 
                style={{ 
                  ...estilosTabla.tr,
                  cursor: onRowClick ? "pointer" : "default",
                }}
                onClick={() => onRowClick?.(fila)}
              >
                {columnas.map((col) => (
                  <td key={col.key} style={{ ...estilosTabla.td, textAlign: col.align || "left" }}>
                    {col.format ? col.format(fila[col.key], fila) : fila[col.key] ?? "—"}
                  </td>
                ))}
              </tr>
            ))
          )}
        </tbody>
      </table>
    </div>
  );
};

// Definición de columnas ejemplo para tabla de pedidos:
const columnasPedidos = [
  { key: "codigo", label: "Código", align: "left" },
  { key: "clienta", label: "Clienta", align: "left" },
  { key: "tipoVestido", label: "Tipo", align: "left" },
  { key: "fechaEntrega", label: "Entrega", format: (v) => new Date(v).toLocaleDateString("es-BO") },
  { key: "total", label: "Total", align: "right", format: (v) => formatBoliviano(v) },
  { key: "saldo", label: "Saldo", align: "right", format: (v) => formatBoliviano(v) },
  { 
    key: "estado", 
    label: "Estado", 
    format: (v) => <EstadoBadge estado={v} />
  },
];
```

### 7.3 Componente de Filtros de Rango de Fechas

```jsx
// components/reportes/FiltrosFecha.jsx
const PERIODOS_RAPIDOS = [
  { label: "Hoy", dias: 0 },
  { label: "Esta semana", dias: 7 },
  { label: "Este mes", dias: 30 },
  { label: "Últimos 3 meses", dias: 90 },
  { label: "Este año", dias: 365 },
];

const FiltrosFecha = ({ onChange, valorInicial }) => {
  const [periodoActivo, setPeriodoActivo] = useState("Este mes");
  const [fechaInicio, setFechaInicio] = useState("");
  const [fechaFin, setFechaFin] = useState("");

  const aplicarPeriodo = (periodo) => {
    setPeriodoActivo(periodo.label);
    const hoy = new Date();
    const inicio = new Date();
    inicio.setDate(hoy.getDate() - periodo.dias);
    const fi = inicio.toISOString().split("T")[0];
    const ff = hoy.toISOString().split("T")[0];
    setFechaInicio(fi);
    setFechaFin(ff);
    onChange({ fechaInicio: fi, fechaFin: ff });
  };

  return (
    <div style={{ display: "flex", gap: 8, alignItems: "center", flexWrap: "wrap" }}>
      {PERIODOS_RAPIDOS.map((p) => (
        <button
          key={p.label}
          onClick={() => aplicarPeriodo(p)}
          style={{
            padding: "6px 14px",
            borderRadius: 20,
            border: "1px solid",
            borderColor: periodoActivo === p.label ? "#6366F1" : "#E5E7EB",
            backgroundColor: periodoActivo === p.label ? "#EEF2FF" : "#FFF",
            color: periodoActivo === p.label ? "#6366F1" : "#374151",
            fontSize: 13,
            fontWeight: 500,
            cursor: "pointer",
          }}
        >
          {p.label}
        </button>
      ))}
      <input type="date" value={fechaInicio} onChange={(e) => setFechaInicio(e.target.value)} style={estiloInput} />
      <span style={{ color: "#9CA3AF" }}>→</span>
      <input type="date" value={fechaFin} onChange={(e) => setFechaFin(e.target.value)} style={estiloInput} />
    </div>
  );
};
```

---

## 8. Paleta de Colores y Accesibilidad en Reportes

### 8.1 Sistema de Color para Gráficos

Definir un sistema de colores semántico y consistente para todos los reportes del sistema:

```javascript
// constants/reporteColores.js

// Colores primarios para series de datos (hasta 6 series)
export const COLORES_SERIES = [
  "#6366F1",  // Índigo    — Serie principal
  "#10B981",  // Esmeralda — Serie secundaria
  "#F59E0B",  // Ámbar     — Serie terciaria
  "#EF4444",  // Rojo      — Serie cuarta
  "#8B5CF6",  // Violeta   — Serie quinta
  "#06B6D4",  // Cian      — Serie sexta
];

// Colores semánticos (significado universal)
export const COLORES_SEMANTICOS = {
  ingresos: "#10B981",      // verde → positivo
  egresos: "#EF4444",       // rojo → negativo
  saldo: "#6366F1",         // índigo → neutral/total
  meta: "#9CA3AF",          // gris → referencia
  pendiente: "#F59E0B",     // ámbar → atención
};

// Colores por estado de pedido
export const COLORES_ESTADO = {
  registrado: "#9CA3AF",         // gris
  en_proceso: "#3B82F6",         // azul
  primera_prueba: "#F59E0B",     // ámbar
  segunda_prueba: "#F97316",     // naranja
  tercera_prueba: "#8B5CF6",     // violeta
  listo_entrega: "#10B981",      // verde
  entregado: "#6B7280",          // gris oscuro
  cancelado: "#EF4444",          // rojo
};

// Fondo de área con transparencia (para AreaChart)
export const colorConOpacidad = (hex, opacidad) => {
  const r = parseInt(hex.slice(1, 3), 16);
  const g = parseInt(hex.slice(3, 5), 16);
  const b = parseInt(hex.slice(5, 7), 16);
  return `rgba(${r}, ${g}, ${b}, ${opacidad})`;
};
```

### 8.2 Reglas de Accesibilidad en Visualizaciones

**Ratio de contraste mínimo:** Los colores de texto sobre fondo deben cumplir WCAG AA:
- Texto normal: mínimo 4.5:1
- Texto grande (>18px bold): mínimo 3:1

**No depender solo del color:** Siempre complementar el color con forma, patrón o texto:

```jsx
// ❌ INCORRECTO: solo el color diferencia las categorías
<Pie data={data}>
  {data.map((entry, i) => <Cell key={i} fill={COLORES_SERIES[i]} />)}
</Pie>

// ✅ CORRECTO: color + etiqueta + tooltip con texto
<Pie data={data} label={({ name, percent }) => `${name}: ${(percent * 100).toFixed(0)}%`}>
  {data.map((entry, i) => <Cell key={i} fill={COLORES_SERIES[i]} />)}
</Pie>
```

**Atributos ARIA para gráficos:**

```jsx
// Siempre incluir rol y descripción para lectores de pantalla
<div role="img" aria-label="Gráfico de ingresos vs egresos de los últimos 6 meses">
  <ResponsiveContainer width="100%" height={300}>
    <ComposedChart data={data}>
      {/* ... */}
    </ComposedChart>
  </ResponsiveContainer>
</div>
```

### 8.3 Tabla de Verificación de Contraste

| Combinación | Ratio | ¿Pasa WCAG AA? |
|---|---|---|
| Texto #111827 sobre #FFFFFF | 18.1:1 | ✅ Sí |
| Texto #6B7280 sobre #FFFFFF | 5.9:1 | ✅ Sí |
| Texto #9CA3AF sobre #FFFFFF | 2.9:1 | ❌ No (solo decorativo) |
| Texto #FFFFFF sobre #6366F1 | 4.7:1 | ✅ Sí |
| Texto #FFFFFF sobre #10B981 | 3.0:1 | ⚠️ Solo texto grande |
| Texto #FFFFFF sobre #EF4444 | 4.5:1 | ✅ Sí (límite exacto) |

---

## 9. Manejo de Datos: Transformación y Normalización

### 9.1 El Problema del Dato Crudo vs. Dato de Visualización

Los datos que llegan de la API de FastAPI raramente están en el formato exacto que Recharts espera. Siempre existe una capa de **transformación** entre la respuesta de la API y el componente gráfico.

```javascript
// utils/reporteTransformers.js

// Transformación: respuesta API → formato para ComposedChart de Estado de Resultados
export const transformarEstadoResultados = (apiResponse) => {
  // apiResponse = { meses: [{ periodo: "2026-01", total_ingresos: 18500, total_egresos: 9200 }] }
  
  return apiResponse.meses.map((mes) => ({
    mes: formatFechaEje(mes.periodo + "-01", "mes"),
    ingresos: Number(mes.total_ingresos),
    egresos: Number(mes.total_egresos),
    saldoNeto: Number(mes.total_ingresos) - Number(mes.total_egresos),
    margen: mes.total_ingresos > 0 
      ? ((mes.total_ingresos - mes.total_egresos) / mes.total_ingresos * 100).toFixed(1)
      : 0,
  }));
};

// Transformación: pedidos por estado → formato para DonutChart
export const transformarPedidosPorEstado = (pedidos) => {
  const conteo = pedidos.reduce((acc, pedido) => {
    acc[pedido.estado] = (acc[pedido.estado] || 0) + 1;
    return acc;
  }, {});

  return Object.entries(conteo)
    .map(([estado, cantidad]) => ({
      name: LABELS_ESTADO[estado] ?? estado,
      value: cantidad,
      color: COLORES_ESTADO[estado] ?? "#9CA3AF",
    }))
    .sort((a, b) => b.value - a.value); // ordenar de mayor a menor
};

// Transformación: ingresos por tipo → formato para PieChart
export const transformarIngresosPorTipo = (ingresos) => [
  { name: "Confección", value: ingresos.confeccion, color: COLORES_SERIES[0] },
  { name: "Venta Directa", value: ingresos.venta_directa, color: COLORES_SERIES[1] },
  { name: "Flete", value: ingresos.flete, color: COLORES_SERIES[2] },
].filter((item) => item.value > 0);
```

### 9.2 Manejo de Valores Nulos y Casos Borde

```javascript
// Siempre defensivo con datos de API
export const normalizarValorNumerico = (valor) => {
  if (valor === null || valor === undefined) return 0;
  const num = Number(valor);
  return isNaN(num) ? 0 : num;
};

// Para datos de series temporales con gaps (meses sin datos)
export const rellenarSeriesTiempo = (datos, fechaInicio, fechaFin, granularidad = "mes") => {
  const meses = generarRangoMeses(fechaInicio, fechaFin);
  const mapaExistente = new Map(datos.map((d) => [d.periodo, d]));
  
  return meses.map((mes) => ({
    mes: formatFechaEje(mes, "mes"),
    ingresos: normalizarValorNumerico(mapaExistente.get(mes)?.ingresos),
    egresos: normalizarValorNumerico(mapaExistente.get(mes)?.egresos),
    // Si no hay dato para ese mes, se rellenan con 0 (no se dejan huecos)
  }));
};
```

### 9.3 Memoización para Performance

Los gráficos con muchos datos pueden causar re-renders innecesarios. Usar `useMemo` para transformaciones costosas:

```jsx
import { useMemo } from "react";

const ReporteEstadoResultados = ({ datos, periodo }) => {
  // Esta transformación solo se recalcula cuando cambian los datos o el período
  const datosGrafico = useMemo(() => 
    transformarEstadoResultados(datos), 
    [datos]
  );

  const totales = useMemo(() => ({
    ingresos: datosGrafico.reduce((sum, d) => sum + d.ingresos, 0),
    egresos: datosGrafico.reduce((sum, d) => sum + d.egresos, 0),
    saldo: datosGrafico.reduce((sum, d) => sum + d.saldoNeto, 0),
  }), [datosGrafico]);

  return (
    <>
      <KPICard titulo="Ingresos Totales" valor={totales.ingresos} />
      <KPICard titulo="Egresos Totales" valor={totales.egresos} />
      {/* ... */}
    </>
  );
};
```

---

## 10. Patrones Anti-Reporte: Qué Evitar

### 10.1 ❌ El Gráfico de Torta con Demasiados Segmentos

```
PROBLEMA: Un PieChart con 12 categorías es ilegible.
SOLUCIÓN: Agrupar las categorías menores en "Otros" hasta tener máximo 6 segmentos.
```

### 10.2 ❌ Gráfico de Líneas con Datos Insuficientes

```
PROBLEMA: Un LineChart con 2 puntos de datos parece una barra.
REGLA: Si tienes menos de 5 puntos de datos, usa un BarChart en su lugar.
```

### 10.3 ❌ Ejes Y que No Empiezan en Cero

```
PROBLEMA: Un eje Y que empieza en Bs. 14,000 (no en 0) exagera visualmente
          las diferencias entre valores y engaña al usuario.
EXCEPCIÓN: Solo es válido cuando los valores son muy cercanos entre sí y la
           variación relativa (%) es lo importante, no el valor absoluto.
```

### 10.4 ❌ Tablas sin Paginación con Cientos de Filas

```
PROBLEMA: Renderizar 500 filas en una tabla sin paginación bloquea el navegador.
SOLUCIÓN: Implementar paginación del lado del servidor o virtualización
          con react-window para datasets grandes.
```

### 10.5 ❌ KPI Cards sin Comparador

```
PROBLEMA: "Ingresos del mes: Bs. 24,850" no dice nada por sí solo.
SOLUCIÓN: Siempre agregar comparador: "↑ +12.4% vs mes anterior".
```

### 10.6 ❌ Colores sin Semántica Consistente

```
PROBLEMA: En el gráfico A el rojo significa "vestidos de novia" y en el
          gráfico B el rojo significa "egresos". El usuario se confunde.
SOLUCIÓN: Definir un sistema de color semántico y respetarlo en TODOS
          los gráficos del sistema.
```

### 10.7 ❌ Sobrecargar un Solo Dashboard

```
PROBLEMA: Mostrar 15 gráficos en una sola pantalla es cognitivamente abrumador.
SOLUCIÓN: Máximo 6-8 elementos visuales por pantalla. El resto, en sub-reportes
          accesibles con navegación clara.
```

### 10.8 ❌ Reportes sin Filtros

```
PROBLEMA: Un reporte sin filtros de fecha o categoría obliga al usuario a
          ver siempre todos los datos históricos mezclados.
SOLUCIÓN: Todo reporte debe tener al menos un selector de rango de fechas.
```

---

## 11. Plantillas de Código para Reportes Comunes

### 11.1 Plantilla: Reporte de Estado de Resultados (Específico para BELLAARTE BOUTIQUE)

```jsx
// pages/reportes/ReporteEstadoResultados.jsx
import { useState } from "react";
import { ComposedChart, Bar, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, ReferenceLine } from "recharts";
import { useReporteFinanciero } from "@/hooks/useReporteFinanciero";
import { transformarEstadoResultados } from "@/utils/reporteTransformers";
import { formatBoliviano, formatNumeroCorto } from "@/utils/reporteFormatters";
import KPICard from "@/components/reportes/KPICard";
import FiltrosFecha from "@/components/reportes/FiltrosFecha";
import CustomTooltip from "@/components/reportes/CustomTooltip";
import GraficoSkeleton from "@/components/reportes/GraficoSkeleton";

const ReporteEstadoResultados = () => {
  const [filtros, setFiltros] = useState({ fechaInicio: "", fechaFin: "" });
  const { data, loading, error } = useReporteFinanciero(filtros);

  const datosGrafico = data ? transformarEstadoResultados(data) : [];
  
  const totales = {
    ingresos: datosGrafico.reduce((s, d) => s + d.ingresos, 0),
    egresos: datosGrafico.reduce((s, d) => s + d.egresos, 0),
    saldo: datosGrafico.reduce((s, d) => s + d.saldoNeto, 0),
  };

  if (error) {
    return (
      <div style={{ padding: 32, textAlign: "center", color: "#EF4444" }}>
        <p>Error al cargar el reporte: {error}</p>
        <button onClick={() => window.location.reload()}>Reintentar</button>
      </div>
    );
  }

  return (
    <div style={{ padding: 24, display: "flex", flexDirection: "column", gap: 24 }}>
      
      {/* Encabezado y filtros */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", flexWrap: "wrap", gap: 16 }}>
        <div>
          <h2 style={{ fontSize: 20, fontWeight: 700, color: "#111827", margin: 0 }}>Estado de Resultados</h2>
          <p style={{ fontSize: 14, color: "#6B7280", margin: "4px 0 0 0" }}>
            Comparativa de ingresos y egresos por período
          </p>
        </div>
        <FiltrosFecha onChange={setFiltros} />
      </div>

      {/* KPI Cards */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))", gap: 16 }}>
        <KPICard titulo="Ingresos Totales" valor={totales.ingresos} loading={loading} />
        <KPICard titulo="Egresos Totales" valor={totales.egresos} loading={loading} />
        <KPICard 
          titulo="Saldo Neto" 
          valor={totales.saldo} 
          loading={loading}
          variacion={totales.ingresos > 0 ? (totales.saldo / totales.ingresos * 100) : 0}
          descripcionVariacion="margen neto"
        />
      </div>

      {/* Gráfico principal */}
      <div style={{ backgroundColor: "#FFFFFF", border: "1px solid #E5E7EB", borderRadius: 12, padding: 24 }}>
        <h3 style={{ fontSize: 16, fontWeight: 600, color: "#111827", marginBottom: 16 }}>
          Ingresos vs Egresos
        </h3>
        
        {loading ? (
          <GraficoSkeleton height={320} />
        ) : (
          <div role="img" aria-label="Gráfico comparativo de ingresos y egresos mensuales">
            <ResponsiveContainer width="100%" height={320}>
              <ComposedChart data={datosGrafico} margin={{ top: 10, right: 30, left: 0, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#F3F4F6" vertical={false} />
                <XAxis 
                  dataKey="mes" 
                  tick={{ fontSize: 12, fill: "#9CA3AF" }}
                  axisLine={false}
                  tickLine={false}
                />
                <YAxis 
                  tickFormatter={formatNumeroCorto}
                  tick={{ fontSize: 12, fill: "#9CA3AF" }}
                  axisLine={false}
                  tickLine={false}
                />
                <Tooltip content={<CustomTooltip tipo="moneda" />} />
                <Legend 
                  formatter={(value) => (
                    <span style={{ fontSize: 13, color: "#374151" }}>{value}</span>
                  )}
                />
                <ReferenceLine y={0} stroke="#E5E7EB" />
                <Bar dataKey="ingresos" name="Ingresos" fill="#10B981" radius={[4, 4, 0, 0]} barSize={24} />
                <Bar dataKey="egresos" name="Egresos" fill="#EF4444" radius={[4, 4, 0, 0]} barSize={24} />
                <Line 
                  type="monotone" 
                  dataKey="saldoNeto" 
                  name="Saldo Neto"
                  stroke="#6366F1" 
                  strokeWidth={2.5}
                  dot={{ fill: "#6366F1", r: 4 }}
                  activeDot={{ r: 6 }}
                />
              </ComposedChart>
            </ResponsiveContainer>
          </div>
        )}
      </div>

    </div>
  );
};

export default ReporteEstadoResultados;
```

### 11.2 Plantilla: Reporte de Pedidos por Estado (DonutChart)

```jsx
// Componente de distribución de pedidos por estado
import { PieChart, Pie, Cell, Tooltip, Label, ResponsiveContainer } from "recharts";

const ReportePedidosPorEstado = ({ datos, loading }) => {
  const dataPie = transformarPedidosPorEstado(datos ?? []);
  const totalPedidos = dataPie.reduce((sum, d) => sum + d.value, 0);

  const renderLabelCentral = ({ viewBox }) => {
    const { cx, cy } = viewBox;
    return (
      <>
        <text x={cx} y={cy - 8} textAnchor="middle" fill="#111827" fontSize={28} fontWeight={700}>
          {totalPedidos}
        </text>
        <text x={cx} y={cy + 16} textAnchor="middle" fill="#9CA3AF" fontSize={12}>
          pedidos activos
        </text>
      </>
    );
  };

  return (
    <div style={{ backgroundColor: "#FFFFFF", border: "1px solid #E5E7EB", borderRadius: 12, padding: 24 }}>
      <h3 style={{ fontSize: 16, fontWeight: 600, color: "#111827", marginBottom: 8 }}>
        Pedidos por Estado
      </h3>
      <ResponsiveContainer width="100%" height={260}>
        <PieChart>
          <Pie
            data={dataPie}
            cx="50%"
            cy="50%"
            innerRadius={75}
            outerRadius={110}
            paddingAngle={3}
            dataKey="value"
            startAngle={90}
            endAngle={-270}
          >
            {dataPie.map((entry, index) => (
              <Cell key={index} fill={entry.color} stroke="none" />
            ))}
            <Label content={renderLabelCentral} position="center" />
          </Pie>
          <Tooltip 
            formatter={(value, name) => [value, name]}
            contentStyle={{ borderRadius: 8, border: "1px solid #E5E7EB" }}
          />
        </PieChart>
      </ResponsiveContainer>
      
      {/* Leyenda personalizada */}
      <div style={{ display: "flex", flexDirection: "column", gap: 8, marginTop: 8 }}>
        {dataPie.map((item) => (
          <div key={item.name} style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
            <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
              <div style={{ width: 10, height: 10, borderRadius: 2, backgroundColor: item.color }} />
              <span style={{ fontSize: 13, color: "#374151" }}>{item.name}</span>
            </div>
            <div style={{ display: "flex", gap: 12 }}>
              <span style={{ fontSize: 13, fontWeight: 700, color: "#111827" }}>{item.value}</span>
              <span style={{ fontSize: 12, color: "#9CA3AF", minWidth: 36, textAlign: "right" }}>
                {totalPedidos > 0 ? `${(item.value / totalPedidos * 100).toFixed(0)}%` : "—"}
              </span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};
```

---

## 12. Checklist de Calidad para Reportes

Antes de considerar un reporte como terminado, verificar todos los puntos de esta lista:

### 12.1 Funcionalidad

- [ ] El reporte carga datos desde la API correctamente
- [ ] Los filtros de fecha funcionan y actualizan los gráficos en tiempo real
- [ ] El estado de carga muestra skeleton loaders (no spinners desnudos)
- [ ] El estado vacío muestra un mensaje contextual y útil
- [ ] El estado de error muestra el mensaje y un botón de reintentar
- [ ] Los tooltips muestran valores formateados correctamente (Bs. X,XXX.XX)
- [ ] Los valores nulos o indefinidos no rompen los gráficos

### 12.2 Diseño UX/UI

- [ ] La jerarquía visual está clara (KPIs > Gráficos > Tablas)
- [ ] Cada KPI Card tiene un comparador con período anterior
- [ ] Los colores son semánticamente consistentes con el resto del sistema
- [ ] El contraste de colores cumple WCAG AA (mínimo 4.5:1 para texto normal)
- [ ] La información no depende solo del color (siempre hay texto complementario)
- [ ] Las fuentes respetan la escala tipográfica definida
- [ ] El espaciado es consistente (múltiplos de 8px)
- [ ] Los gráficos no están sobrecargados (máximo 4-6 series por gráfico)

### 12.3 Performance

- [ ] Las transformaciones de datos costosas están dentro de `useMemo`
- [ ] Los fetch de datos no se repiten en cada re-render (useCallback + useEffect con dependencias correctas)
- [ ] Los gráficos grandes tienen animaciones desactivadas o reducidas
- [ ] Las tablas con más de 50 filas tienen paginación

### 12.4 Accesibilidad

- [ ] Los contenedores de gráficos tienen `role="img"` y `aria-label` descriptivo
- [ ] Las tablas tienen `<caption>` o `aria-label`
- [ ] Los botones de filtro tienen texto descriptivo (no solo íconos)
- [ ] Los elementos interactivos tienen focus visible

### 12.5 Control de Acceso (Específico del Sistema)

- [ ] El reporte solo es accesible para los roles autorizados (verificado con PyCasbin)
- [ ] Los datos sensibles (montos financieros) están enmascarados para roles sin permiso
- [ ] El período de caja cerrado muestra datos read-only correctamente

---

## 13. Referencias y Recursos

### 13.1 Documentación Oficial

- **Recharts:** https://recharts.org/en-US/api
- **React 19 Docs:** https://react.dev
- **Vite:** https://vitejs.dev/guide/

### 13.2 Estándares de Diseño

- **WCAG 2.1 Accessibility Guidelines:** https://www.w3.org/WAI/WCAG21/quickref/
- **Nielsen Norman Group — Dashboard Design:** https://www.nngroup.com/articles/dashboards/

### 13.3 Librerías Complementarias Recomendadas

| Librería | Propósito | NPM |
|---|---|---|
| `date-fns` | Manipulación de fechas en formato ES | `npm install date-fns` |
| `react-window` | Virtualización de tablas grandes | `npm install react-window` |
| `@tanstack/react-table` | Tablas avanzadas con sorting y filtros | `npm install @tanstack/react-table` |
| `react-to-print` | Impresión de reportes desde el navegador | `npm install react-to-print` |

### 13.4 Fuentes Académicas Relevantes para la Tesis

- Few, S. (2012). *Show Me the Numbers: Designing Tables and Graphs to Enlighten* (2nd ed.). Analytics Press.
- Tufte, E. R. (2001). *The Visual Display of Quantitative Information* (2nd ed.). Graphics Press.
- Ware, C. (2019). *Information Visualization: Perception for Design* (4th ed.). Morgan Kaufmann.
- Nielsen, J., & Loranger, H. (2006). *Prioritizing Web Usability*. New Riders.

---

*Documento generado para el proyecto de grado "Sistema Web Administrativo y de Gestión del Conocimiento Organizacional — BELLAARTE BOUTIQUE". La Paz, Bolivia, 2026.*

*Este archivo debe mantenerse actualizado conforme avance el desarrollo del sistema y se implementen nuevos módulos de reporte.*
