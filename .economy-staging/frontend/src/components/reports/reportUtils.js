import dayjs from 'dayjs'

export const REPORT_PERIOD_OPTIONS = [
  { label: 'TODO', value: 'all' },
  { label: 'DÍA', value: 'day' },
  { label: 'SEMANA', value: 'week' },
  { label: 'MES', value: 'month' },
  { label: 'AÑO', value: 'year' },
]

export function formatBs(value) {
  const amount = Number(value || 0)
  return `Bs ${amount.toFixed(2)}`
}

export function formatCount(value) {
  return new Intl.NumberFormat('es-BO').format(Number(value || 0))
}

export function formatPercent(value) {
  return `${Number(value || 0).toFixed(1)}%`
}

export function parseDateRange(filters) {
  return filters.date_from && filters.date_to ? [dayjs(filters.date_from), dayjs(filters.date_to)] : null
}

export function applyDateRangeToFilters(filters, values) {
  return {
    ...filters,
    date_from: values?.[0] ? values[0].format('YYYY-MM-DD') : undefined,
    date_to: values?.[1] ? values[1].format('YYYY-MM-DD') : undefined,
  }
}

export function buildReportQuery(filters) {
  const params = new URLSearchParams()
  Object.entries(filters || {}).forEach(([key, value]) => {
    if (value === undefined || value === null || value === '') return
    params.set(key, String(value))
  })
  return params.toString()
}

export function buildBreakdownMap(summary) {
  return (summary?.breakdown || []).map((item) => ({
    ...item,
    count: Number(item.count || 0),
  }))
}

export function getSessionFilters(key, defaults) {
  try {
    const raw = window.sessionStorage.getItem(key)
    if (!raw) return defaults
    return { ...defaults, ...JSON.parse(raw) }
  } catch {
    return defaults
  }
}

export function setSessionFilters(key, value) {
  try {
    window.sessionStorage.setItem(key, JSON.stringify(value))
  } catch {
    return
  }
}
