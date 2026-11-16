export const SYNC_BASE = '/monedas/tipos-cambio/sincronizacion'

export const SYNC_STATES = ['INICIADO', 'EXITOSO', 'ERROR_CONEXION', 'ERROR_API', 'ERROR_DATOS', 'ERROR_VIGENCIA', 'ERROR_EJECUCION', 'CARGA_HISTORICA']

export function bolivianTimestamp(value) {
  if (!value) return '—'
  const instant = new Date(value)
  return Number.isNaN(instant.getTime()) ? '—' : new Intl.DateTimeFormat('es-BO', {
    timeZone: 'America/La_Paz', dateStyle: 'short', timeStyle: 'short',
  }).format(instant)
}

export function calendarDate(value) {
  if (!/^\d{4}-\d{2}-\d{2}$/.test(value || '')) return '—'
  const [year, month, day] = value.split('-')
  return `${day}/${month}/${year}`
}

export function operationalAge(value, localDate) {
  if (!value || !localDate) return null
  const instant = new Date(value)
  if (Number.isNaN(instant.getTime())) return null
  const parts = new Intl.DateTimeFormat('en-CA', { timeZone: 'America/La_Paz', year: 'numeric', month: '2-digit', day: '2-digit' }).formatToParts(instant)
  const field = (type) => parts.find((part) => part.type === type)?.value
  const day = `${field('year')}-${field('month')}-${field('day')}`
  const age = Math.floor((Date.parse(`${localDate}T00:00:00Z`) - Date.parse(`${day}T00:00:00Z`)) / 86400000)
  return Number.isFinite(age) ? Math.max(age, 0) : null
}

export function canReadSyncRecords(user) {
  return user?.role_code === 'ADMIN' && user.permissions?.includes('exchange_rates_sync:list')
}

export function syncAlertType(status) {
  if (status === 'UPDATED') return 'success'
  if (status === 'NO_ACTIVE_RATE') return 'error'
  if (['ERROR', 'CONNECTION_ERROR', 'EXHAUSTED', 'MANUAL_FALLBACK'].includes(status)) return 'warning'
  return 'info'
}

export function validRecordId(value) {
  return /^[1-9]\d*$/.test(value || '') && Number.isSafeInteger(Number(value)) ? Number(value) : null
}
