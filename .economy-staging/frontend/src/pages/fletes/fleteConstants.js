export const ESTADO_FLETE_OPTIONS = [
  ['disponible', 'DISPONIBLE'],
  ['en_flete', 'EN FLETE'],
  ['en_revision', 'EN REVISIÓN'],
  ['agotado', 'AGOTADO'],
  ['pasado_para_venta', 'PASADO A VENTA'],
  ['retirado', 'RETIRADO'],
].map(([value, label]) => ({ value, label }))

export const ESTADO_SALIDA_FLETE_OPTIONS = [
  ['reservado', 'RESERVADO'],
  ['en_flete', 'EN FLETE'],
  ['devuelto', 'DEVUELTO'],
  ['devuelto_con_observacion', 'DEVUELTO CON OBSERVACIÓN'],
  ['devuelto_con_arreglo', 'DEVUELTO CON ARREGLO'],
  ['anulado', 'ANULADO'],
].map(([value, label]) => ({ value, label }))

export const MOTIVO_DESCUENTO_FLETE_OPTIONS = [
  ['rebaja', 'REBAJA'],
  ['promocion', 'PROMOCIÓN'],
  ['bonificacion', 'BONIFICACIÓN'],
  ['administrativo', 'ADMINISTRATIVO'],
].map(([value, label]) => ({ value, label }))

export const ESTADO_ENTREGA_OPTIONS = [
  ['bueno', 'BUENO'],
  ['regular', 'REGULAR'],
  ['con_observacion', 'CON OBSERVACIÓN'],
].map(([value, label]) => ({ value, label }))

export const ESTADO_DEVOLUCION_OPTIONS = [
  ['bueno', 'BUENO'],
  ['regular', 'REGULAR'],
  ['dañado', 'DAÑADO'],
  ['incompleto', 'INCOMPLETO'],
].map(([value, label]) => ({ value, label }))

export const DEVOLUCION_RESULT_OPTIONS = [
  ['devuelto', 'DEVOLUCIÓN NORMAL'],
  ['devuelto_con_observacion', 'DEVOLUCIÓN CON OBSERVACIÓN'],
  ['devuelto_con_arreglo', 'DEVOLUCIÓN CON ARREGLO'],
].map(([value, label]) => ({ value, label }))

export const REVIEW_RESOLUTION_OPTIONS = [
  ['disponible', 'VOLVER A DISPONIBLE'],
  ['agotado', 'PASAR A AGOTADO'],
].map(([value, label]) => ({ value, label }))

export function labelFromOptions(options, value) {
  return options.find((option) => option.value === value)?.label || value || 'SIN REGISTRO'
}

export function formatMoney(value) {
  return new Intl.NumberFormat('es-BO', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(Number(value || 0))
}

export function fleteStateColor(value) {
  if (value === 'disponible') return 'green'
  if (value === 'en_flete') return 'blue'
  if (value === 'en_revision') return 'orange'
  if (value === 'agotado') return 'red'
  if (value === 'pasado_para_venta') return 'purple'
  if (value === 'retirado') return 'default'
  return 'default'
}

export function salidaStateColor(value) {
  if (value === 'reservado') return 'gold'
  if (value === 'en_flete') return 'blue'
  if (value === 'devuelto') return 'green'
  if (value === 'devuelto_con_observacion') return 'orange'
  if (value === 'devuelto_con_arreglo') return 'volcano'
  if (value === 'anulado') return 'red'
  return 'default'
}
