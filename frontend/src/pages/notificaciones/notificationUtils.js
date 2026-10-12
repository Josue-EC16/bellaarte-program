export const NOTIFICATION_PRIORITY_OPTIONS = [
  { label: 'BAJA', value: 'baja' },
  { label: 'MEDIA', value: 'media' },
  { label: 'ALTA', value: 'alta' },
  { label: 'URGENTE', value: 'urgente' },
]

export const NOTIFICATION_MODULE_OPTIONS = [
  { label: 'BOUTIQUE', value: 'BOUTIQUE' },
  { label: 'TALLER', value: 'TALLER' },
  { label: 'PEDIDOS', value: 'PEDIDOS' },
  { label: 'PRUEBAS', value: 'PRUEBAS' },
  { label: 'FLETES', value: 'FLETES' },
  { label: 'SEGURIDAD', value: 'SEGURIDAD' },
  { label: 'SISTEMA', value: 'SISTEMA' },
]

export const NOTIFICATION_TYPE_OPTIONS = [
  'STOCK_BAJO_BOUTIQUE',
  'STOCK_BAJO_TALLER',
  'ENTREGA_PEDIDO_2_DIAS',
  'ENTREGA_PEDIDO_1_DIA',
  'ENTREGA_PEDIDO_HOY',
  'PRUEBA_PEDIDO_2_DIAS',
  'PRUEBA_PEDIDO_1_DIA',
  'PRUEBA_PEDIDO_HOY',
  'PRUEBA_1_ALISTAR_MATERIAL',
  'PRUEBA_2_ALISTAR_MATERIAL',
  'DEVOLUCION_FLETE_2_DIAS',
  'DEVOLUCION_FLETE_1_DIA',
  'DEVOLUCION_FLETE_HOY',
  'DEVOLUCION_FLETE_VENCIDA',
  'FLETE_MAX_SALIDAS',
  'ERROR_ENVIO_CORREO',
  'SISTEMA',
].map((value) => ({ label: value.replaceAll('_', ' '), value }))

export function notificationPriorityColor(priority) {
  switch (priority) {
    case 'urgente':
      return '#b8475c'
    case 'alta':
      return '#b87b2f'
    case 'media':
      return '#5278a3'
    default:
      return '#7d7a87'
  }
}

export function notificationPrioritySurface(priority) {
  switch (priority) {
    case 'urgente':
      return 'linear-gradient(135deg, rgba(184,71,92,0.16), rgba(184,71,92,0.06))'
    case 'alta':
      return 'linear-gradient(135deg, rgba(184,123,47,0.16), rgba(184,123,47,0.06))'
    case 'media':
      return 'linear-gradient(135deg, rgba(82,120,163,0.16), rgba(82,120,163,0.06))'
    default:
      return 'linear-gradient(135deg, rgba(125,122,135,0.14), rgba(125,122,135,0.05))'
  }
}

export function notificationPriorityLabel(priority) {
  return (priority || '').toUpperCase()
}

export function notificationStatusLabel(record) {
  if (record.resuelta) return 'RESUELTA'
  if (record.leida) return 'LEÍDA'
  return 'PENDIENTE'
}

export function buildNotificationOriginPath(record) {
  if (record.action_path) return record.action_path
  const tableRef = record.tabla_referencia?.toLowerCase()
  const recordId = record.id_referencia
  if (tableRef === 'item_boutique') return recordId ? `/app/boutique/inventario?item_id=${recordId}` : '/app/boutique/inventario'
  if (tableRef === 'inventario_taller') return recordId ? `/app/taller/inventario?item_id=${recordId}` : '/app/taller/inventario'
  if (tableRef === 'pedido') return recordId ? `/app/pedidos?order_id=${recordId}` : '/app/pedidos'
  if (tableRef === 'prueba_pedido') return recordId ? `/app/pedidos/pruebas?test_id=${recordId}` : '/app/pedidos/pruebas'
  if (tableRef === 'salida_flete') return recordId ? `/app/fletes/salidas?output_id=${recordId}` : '/app/fletes/salidas'
  if (tableRef === 'flete_vestido') return recordId ? `/app/fletes?flete_id=${recordId}` : '/app/fletes'
  if (tableRef === 'usuarios') return recordId ? `/app/seguridad/usuarios?user_id=${recordId}` : '/app/seguridad/usuarios'
  return '/app'
}
