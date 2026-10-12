import { apiClient } from '../../api/client'

import {
  ESTADO_CORTE_OPTIONS,
  ESTADO_EGRESO_OPTIONS,
  INCOME_SOURCE_OPTIONS,
  TIPO_EGRESO_OPTIONS,
} from './economyConstants'

export function formatBs(value) {
  return `Bs ${Number(value || 0).toFixed(2)}`
}

export function formatOriginAmount(value, currencyCode, symbol) {
  if (value === null || value === undefined) return 'SIN REGISTRO'
  const prefix = symbol || currencyCode || ''
  return `${prefix} ${Number(value || 0).toFixed(2)}`.trim()
}

export function labelFromOptions(options, value) {
  return options.find((item) => item.value === value)?.label || value || 'SIN REGISTRO'
}

export function expenseTypeLabel(value) {
  return labelFromOptions(TIPO_EGRESO_OPTIONS, value)
}

export function expenseStateLabel(value) {
  return labelFromOptions(ESTADO_EGRESO_OPTIONS, value)
}

export function cutStateLabel(value) {
  return labelFromOptions(ESTADO_CORTE_OPTIONS, value)
}

export function incomeSourceLabel(value) {
  return labelFromOptions(INCOME_SOURCE_OPTIONS, value)
}

export function expenseStateColor(value) {
  if (value === 'registrado') return 'green'
  if (value === 'anulado') return 'red'
  return 'default'
}

export function cutStateColor(value) {
  if (value === 'abierto') return 'processing'
  if (value === 'cerrado') return 'green'
  if (value === 'cerrado_observado') return 'orange'
  return 'default'
}

export function incomeStateColor(value) {
  if (value === 'ACTIVA' || value === 'REGISTRADO' || value === 'RESERVADO' || value === 'EN_FLETE') {
    return 'green'
  }
  if (value === 'CANCELADA') return 'orange'
  if (value === 'ANULADA') return 'red'
  return 'default'
}

export function buildRefundPath({ originType, originId, targetState, returnTo }) {
  const params = new URLSearchParams({
    mode: 'refund',
    origin_type: originType,
    origin_id: String(originId),
    target_status: targetState,
  })
  if (returnTo) {
    params.set('return_to', returnTo)
  }
  return `/app/economia/egresos?${params.toString()}`
}

export async function downloadEconomyCsv(path, params = {}) {
  const response = await apiClient.get(path, {
    params: { ...params, format: 'csv' },
    responseType: 'blob',
  })
  const blob = new Blob([response.data], { type: 'text/csv;charset=utf-8;' })
  const url = window.URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  const header = response.headers['content-disposition'] || ''
  const fileMatch = /filename="?([^"]+)"?/.exec(header)
  link.download = fileMatch?.[1] || 'reporte.csv'
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
  window.URL.revokeObjectURL(url)
}

export function getStoredFilters(key, fallback) {
  try {
    const raw = window.sessionStorage.getItem(key)
    if (!raw) return fallback
    return { ...fallback, ...JSON.parse(raw) }
  } catch {
    return fallback
  }
}

export function storeFilters(key, value) {
  try {
    window.sessionStorage.setItem(key, JSON.stringify(value))
  } catch {
    return
  }
}
