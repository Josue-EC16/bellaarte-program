export const TIPO_VESTIDO_OPTIONS = [
  ['vestido_de_novia', 'VESTIDO DE NOVIA'],
  ['vestido_de_civil', 'VESTIDO DE CIVIL'],
  ['vestido_de_15_años', 'VESTIDO DE 15 AÑOS'],
  ['vestido_de_fiesta_o_evento', 'VESTIDO DE FIESTA O EVENTO'],
  ['vestido_de_niña', 'VESTIDO DE NIÑA'],
  ['damas', 'DAMAS'],
  ['otro', 'OTRO'],
].map(([value, label]) => ({ label, value }))

export const COPA_OPTIONS = [
  ['copa_aa', 'COPA AA'],
  ['copa_a', 'COPA A'],
  ['copa_b', 'COPA B'],
  ['copa_c', 'COPA C'],
  ['copa_d', 'COPA D'],
  ['copa_dd', 'COPA DD'],
  ['copa_e', 'COPA E'],
  ['copa_f', 'COPA F'],
  ['copa_g', 'COPA G'],
].map(([value, label]) => ({ label, value }))

export const TALLA_OPTIONS = [
  ['talla_xxs', 'TALLA XXS'],
  ['talla_xs', 'TALLA XS'],
  ['talla_s', 'TALLA S'],
  ['talla_m', 'TALLA M'],
  ['talla_l', 'TALLA L'],
  ['talla_xl', 'TALLA XL'],
  ['talla_xxl', 'TALLA XXL'],
  ['talla_xxxl', 'TALLA XXXL'],
].map(([value, label]) => ({ label, value }))

export const METODO_PAGO_OPTIONS = [
  ['efectivo', 'EFECTIVO'],
  ['qr', 'QR'],
  ['transaccion', 'TRANSACCIÓN'],
  ['tarjeta', 'TARJETA'],
  ['ticket_o_vale', 'TICKET O VALE'],
].map(([value, label]) => ({ label, value }))

export const MOTIVO_DESCUENTO_VENTA_OPTIONS = [
  ['rebaja', 'REBAJA'],
  ['promocion', 'PROMOCIÓN'],
  ['bonificacion', 'BONIFICACIÓN'],
  ['administrativo', 'ADMINISTRATIVO'],
].map(([value, label]) => ({ label, value }))

export const ESTADO_VENTA_OPTIONS = [
  ['activa', 'ACTIVA'],
  ['cancelada', 'CANCELADA'],
  ['anulada', 'ANULADA'],
].map(([value, label]) => ({ label, value }))

export const MOTIVO_ENTRADA_ITEM_OPTIONS = [
  ['entrada_stock', 'ENTRADA DE STOCK'],
  ['produccion_interna', 'PRODUCCIÓN INTERNA'],
  ['devolucion', 'DEVOLUCIÓN'],
  ['ajuste_positivo', 'AJUSTE POSITIVO'],
  ['registro_inicial', 'REGISTRO INICIAL'],
  ['otro', 'OTRO'],
].map(([value, label]) => ({ label, value }))

export const UNIDAD_MEDIDA_OPTIONS = [
  ['metro', 'METRO'],
  ['centimetro', 'CENTÍMETRO'],
  ['rollo', 'ROLLO'],
  ['caja', 'CAJA'],
  ['kilogramo', 'KILOGRAMO'],
  ['gramo', 'GRAMO'],
  ['yarda', 'YARDA'],
  ['randa', 'RANDA'],
  ['unidad', 'UNIDAD'],
  ['otro', 'OTRO'],
].map(([value, label]) => ({ label, value }))

export const MOTIVO_ENTRADA_TALLER_OPTIONS = [
  ['entrada_stock', 'ENTRADA DE STOCK'],
  ['devolucion', 'DEVOLUCIÓN'],
  ['ajuste_positivo', 'AJUSTE POSITIVO'],
  ['registro_inicial', 'REGISTRO INICIAL'],
  ['otro', 'OTRO'],
].map(([value, label]) => ({ label, value }))

export function inferDetailKindFromTypeName(typeName) {
  const normalized = `${typeName || ''}`.trim().toUpperCase()
  if (normalized === 'VESTIDO') return 'VESTIDO'
  if (normalized === 'VELO') return 'VELO'
  if (normalized === 'BOUQUET') return 'BOUQUET'
  if (normalized === 'BRASIER') return 'BRASIER'
  return 'OTRO'
}

export function formatBs(value) {
  const numeric = Number(value || 0)
  return new Intl.NumberFormat('es-BO', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(numeric)
}

export function labelFromOptions(options, value) {
  return options.find((option) => option.value === value)?.label || value || 'SIN REGISTRO'
}
