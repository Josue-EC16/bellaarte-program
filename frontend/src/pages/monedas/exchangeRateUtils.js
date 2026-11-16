const RATE = /^[0-9]+(?:\.[0-9]{1,4})?$/

export function isValidExchangeRate(value) {
  if (typeof value !== 'string' || !RATE.test(value)) return false
  const integer = value.split('.')[0].replace(/^0+/, '')
  return integer.length <= 8 && /[1-9]/.test(value)
}

export function exchangeRateText(value) {
  return value === null || value === undefined ? '' : String(value)
}

export function exchangeRatePayload(values, { editing = false } = {}) {
  const result = {
    valor_bob: exchangeRateText(values.valor_bob),
    observaciones: values.observaciones?.trim().toUpperCase() || null,
  }
  if (!editing) {
    result.moneda_id = values.moneda_id
    result.activo = true
  }
  return result
}

export function isManualRate(rate) {
  return rate.origen === 'MANUAL'
}

export function canDeactivateRate(rate) {
  return isManualRate(rate) && rate.activo && rate.moneda_codigo !== 'BOB'
}

export function exchangeRateActionError(error, fallback) {
  const detail = error?.response?.data?.detail
  if (typeof detail === 'string') return detail
  return detail?.message || error?.normalizedError?.summary || fallback
}
