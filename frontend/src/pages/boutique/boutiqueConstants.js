export const TIPO_VESTIDO_OPTIONS = [
  'VESTIDO DE NOVIA',
  'VESTIDO DE CIVIL',
  'VESTIDO DE 15 AÑOS',
  'VESTIDO DE FIESTA O EVENTO',
  'VESTIDO DE NIÑA',
  'DAMAS',
  'OTRO',
].map((value) => ({ label: value, value }))

export const TAMANO_OPTIONS = ['PEQUEÑO', 'MEDIANO', 'GRANDE'].map((value) => ({ label: value, value }))

export const COPA_OPTIONS = [
  'COPA AA',
  'COPA A',
  'COPA B',
  'COPA C',
  'COPA D',
  'COPA DD',
  'COPA E',
  'COPA F',
  'COPA G',
].map((value) => ({ label: value, value }))

export const TALLA_OPTIONS = [
  'TALLA XXS',
  'TALLA XS',
  'TALLA S',
  'TALLA M',
  'TALLA L',
  'TALLA XL',
  'TALLA XXL',
  'TALLA XXXL',
].map((value) => ({ label: value, value }))

export const METODO_PAGO_OPTIONS = [
  'EFECTIVO',
  'QR',
  'TRANSACCION',
  'TARJETA',
  'TICKET_O_VALE',
].map((value) => ({ label: value.replaceAll('_', ' '), value }))

export const MOTIVO_DESCUENTO_VENTA_OPTIONS = ['REBAJA', 'PROMOCION'].map((value) => ({ label: value, value }))

export const ESTADO_VENTA_OPTIONS = ['ACTIVA', 'CANCELADA', 'ANULADA'].map((value) => ({ label: value, value }))

export function inferDetailKindFromTypeName(typeName) {
  const normalized = `${typeName || ''}`.trim().toUpperCase()
  if (normalized === 'VESTIDO') return 'VESTIDO'
  if (normalized === 'VELO') return 'VELO'
  if (normalized === 'BOUQUET') return 'BOUQUET'
  return 'OTRO'
}

export function formatBs(value) {
  const numeric = Number(value || 0)
  return new Intl.NumberFormat('es-BO', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(numeric)
}
