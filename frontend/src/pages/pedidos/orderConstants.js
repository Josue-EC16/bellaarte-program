export const TIPO_PEDIDO_OPTIONS = [
  { value: 'vestido', label: 'VESTIDO' },
  { value: 'velo', label: 'VELO' },
  { value: 'cola', label: 'COLA' },
  { value: 'manga', label: 'MANGA' },
  { value: 'bouquet', label: 'BOUQUET' },
  { value: 'otro', label: 'OTRO' },
]

export const TIPO_VESTIDO_OPTIONS = [
  { value: 'vestido_de_novia', label: 'VESTIDO DE NOVIA' },
  { value: 'vestido_de_civil', label: 'VESTIDO DE CIVIL' },
  { value: 'vestido_de_15_años', label: 'VESTIDO DE 15 AÑOS' },
  { value: 'vestido_de_fiesta_o_evento', label: 'VESTIDO DE FIESTA O EVENTO' },
  { value: 'vestido_de_niña', label: 'VESTIDO DE NIÑA' },
  { value: 'damas', label: 'DAMAS' },
  { value: 'otro', label: 'OTRO' },
]

export const MOTIVO_DESCUENTO_OPTIONS = [
  { value: 'rebaja', label: 'REBAJA' },
  { value: 'promocion', label: 'PROMOCION' },
  { value: 'bonificacion', label: 'BONIFICACION' },
  { value: 'administrativo', label: 'ADMINISTRATIVO' },
]

export const ESTADO_PEDIDO_OPTIONS = [
  { value: 'activo', label: 'ACTIVO' },
  { value: 'inactivo', label: 'INACTIVO' },
  { value: 'entregado', label: 'ENTREGADO' },
  { value: 'cancelado', label: 'CANCELADO' },
]

export const ESTADO_PRUEBA_OPTIONS = [
  { value: 'listo', label: 'LISTO' },
  { value: 'costurero_taller', label: 'COSTURERO TALLER' },
  { value: 'decoracion', label: 'DECORACION' },
  { value: 'costurero_externo', label: 'COSTURERO EXTERNO' },
  { value: 'otro', label: 'OTRO' },
]

export const ESTADO_PAGO_OPTIONS = [
  { value: 'registrado', label: 'REGISTRADO' },
  { value: 'anulado', label: 'ANULADO' },
]

export const METODO_PAGO_OPTIONS = [
  { value: 'efectivo', label: 'EFECTIVO' },
  { value: 'qr', label: 'QR' },
  { value: 'transaccion', label: 'TRANSACCION' },
  { value: 'tarjeta', label: 'TARJETA' },
  { value: 'ticket_o_vale', label: 'TICKET O VALE' },
]

export const TRAVEL_DESTINATIONS = [
  { country: 'BOLIVIA', cities: ['LA PAZ', 'EL ALTO', 'COCHABAMBA', 'SANTA CRUZ', 'SUCRE', 'ORURO', 'POTOSI', 'TARIJA', 'TRINIDAD', 'COBIJA'] },
  { country: 'PERU', cities: ['LIMA', 'AREQUIPA', 'CUSCO', 'PUNO', 'TACNA'] },
  { country: 'CHILE', cities: ['SANTIAGO', 'ARICA', 'IQUIQUE', 'ANTOFAGASTA'] },
  { country: 'ARGENTINA', cities: ['BUENOS AIRES', 'SALTA', 'JUJUY', 'CORDOBA', 'MENDOZA'] },
  { country: 'BRASIL', cities: ['SAO PAULO', 'RIO DE JANEIRO', 'CURITIBA', 'PORTO ALEGRE'] },
  { country: 'PARAGUAY', cities: ['ASUNCION', 'CIUDAD DEL ESTE', 'ENCARNACION'] },
  { country: 'URUGUAY', cities: ['MONTEVIDEO', 'SALTO', 'PUNTA DEL ESTE'] },
  { country: 'ECUADOR', cities: ['QUITO', 'GUAYAQUIL', 'CUENCA'] },
  { country: 'COLOMBIA', cities: ['BOGOTA', 'MEDELLIN', 'CALI', 'BARRANQUILLA'] },
  { country: 'VENEZUELA', cities: ['CARACAS', 'MARACAIBO', 'VALENCIA'] },
  { country: 'MEXICO', cities: ['CIUDAD DE MEXICO', 'GUADALAJARA', 'MONTERREY'] },
  { country: 'ESTADOS UNIDOS', cities: ['MIAMI', 'NUEVA YORK', 'LOS ANGELES', 'WASHINGTON'] },
  { country: 'ESPANA', cities: ['MADRID', 'BARCELONA', 'VALENCIA', 'SEVILLA'] },
]

export function labelFromOptions(options, value) {
  return options.find((option) => option.value === value)?.label || value || '-'
}

export function formatBs(value) {
  return `Bs ${Number(value || 0).toFixed(2)}`
}

export function orderStateColor(value) {
  return {
    activo: 'green',
    inactivo: 'default',
    entregado: 'blue',
    cancelado: 'red',
  }[value] || 'default'
}

export function paymentStateColor(value) {
  return value === 'registrado' ? 'green' : 'red'
}

export function testStateColor(value) {
  return {
    listo: 'green',
    costurero_taller: 'orange',
    decoracion: 'magenta',
    costurero_externo: 'cyan',
    otro: 'default',
  }[value] || 'default'
}

export function testNumberColor(number) {
  const palette = ['#111827', '#2563eb', '#dc2626', '#f97316', '#eab308', '#16a34a', '#9333ea']
  return palette[(Number(number || 1) - 1) % palette.length]
}

export function formatConvertedMoney(amountBob, currency, exchangeRate) {
  if (!currency) {
    return formatBs(amountBob)
  }
  if (currency.es_base || Number(exchangeRate || 1) === 1) {
    return `${currency.simbolo || currency.codigo} ${Number(amountBob || 0).toFixed(2)}`
  }
  const converted = Number(amountBob || 0) / Number(exchangeRate || 1)
  return `${currency.simbolo || currency.codigo} ${converted.toFixed(2)}`
}
