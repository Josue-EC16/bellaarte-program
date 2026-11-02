export const TIPO_EGRESO_OPTIONS = [
  { value: 'almuerzo', label: 'ALMUERZO' },
  { value: 'merienda', label: 'MERIENDA' },
  { value: 'alquiler', label: 'ALQUILER' },
  { value: 'alimentos_en_general', label: 'ALIMENTOS EN GENERAL' },
  { value: 'costura', label: 'COSTURA' },
  { value: 'decorado', label: 'DECORADO' },
  { value: 'devolucion', label: 'DEVOLUCIÓN' },
  { value: 'inventario_boutique', label: 'INVENTARIO BOUTIQUE' },
  { value: 'inventario_taller', label: 'INVENTARIO TALLER' },
  { value: 'mantenimiento', label: 'MANTENIMIENTO' },
  { value: 'marketing', label: 'MARKETING' },
  { value: 'servicio_basico', label: 'SERVICIO BÁSICO' },
  { value: 'sueldo', label: 'SUELDO' },
  { value: 'tecnologia', label: 'TECNOLOGÍA' },
  { value: 'otro', label: 'OTRO' },
]

export const ESTADO_EGRESO_OPTIONS = [
  { value: 'registrado', label: 'REGISTRADO' },
  { value: 'anulado', label: 'ANULADO' },
]

export const ESTADO_CORTE_OPTIONS = [
  { value: 'abierto', label: 'ABIERTO' },
  { value: 'cerrado', label: 'CERRADO' },
  { value: 'cerrado_observado', label: 'CERRADO OBSERVADO' },
]

export const CIERRE_CORTE_OPTIONS = [
  { value: 'cerrado', label: 'CERRAR NORMAL' },
  { value: 'cerrado_observado', label: 'CERRAR CON OBSERVACIÓN' },
]

export const INCOME_SOURCE_OPTIONS = [
  { value: 'VENTA_BOUTIQUE', label: 'VENTAS BOUTIQUE' },
  { value: 'PAGO_PEDIDO', label: 'PAGOS DE PEDIDOS' },
  { value: 'SALIDA_FLETE', label: 'SALIDAS DE FLETE' },
]

export const REFUND_TARGET_STATE_OPTIONS = [
  { value: 'CANCELADA', label: 'CANCELADA' },
  { value: 'ANULADA', label: 'ANULADA' },
]

export const ECONOMY_CHART_COLORS = {
  income: '#4b7f5a',
  expense: '#b86c45',
  result: '#4d2219',
  cash: '#7a9cc6',
  qr: '#8f5aa8',
  transfer: '#b66a8b',
  card: '#d4933d',
  voucher: '#7b6d61',
}

export const EXPENSE_TYPE_COLOR = {
  devolucion: 'volcano',
  inventario_boutique: 'gold',
  inventario_taller: 'geekblue',
  tecnologia: 'cyan',
  otro: 'default',
}

export const STORAGE_KEYS = {
  expenses: 'economy-expenses-filters',
  reports: 'economy-reports-filters',
  cuts: 'economy-cuts-filters',
}
