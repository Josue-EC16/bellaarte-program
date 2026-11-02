const UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i

export function validLenySources(items) {
  return Array.isArray(items) && items.length <= 5 && items.every((item) => item && typeof item === 'object'
    && UUID.test(item.source_id) && typeof item.available === 'boolean' && /^S[1-5]$/.test(item.citation_id)
    && (item.label === undefined || item.label === null || typeof item.label === 'string' && item.label.length <= 500)
    && (item.version === undefined || item.version === null || Number.isInteger(item.version) && item.version > 0)
    && (item.locator === undefined || item.locator === null || typeof item.locator === 'object' && !Array.isArray(item.locator))
    && Array.isArray(item.warnings) && item.warnings.length <= 20 && item.warnings.every((warning) => typeof warning === 'string' && warning.length <= 500))
}

export function sourceLocator(locator, type) {
  if (!locator || typeof locator !== 'object') return 'Ubicación documental'
  const parts = []
  if (Number.isInteger(locator.page) && locator.page > 0) parts.push(`Página ${locator.page}`)
  if (Number.isInteger(locator.paragraph) && locator.paragraph > 0) parts.push(`Párrafo ${locator.paragraph}`)
  if (Number.isInteger(locator.table) && locator.table > 0) parts.push(`Tabla ${locator.table}`)
  if (Number.isInteger(locator.row) && locator.row > 0) parts.push(`Fila ${locator.row}`)
  if (typeof locator.section === 'string') parts.push(locator.section.slice(0, 200))
  if (!parts.length && /IMAGE|OCR/.test(type || '')) return 'Imagen · texto reconocido'
  return parts.join(' · ') || 'Ubicación documental'
}

export function sourceError(error) {
  const status = error?.response?.status
  if (status === 404 || status === 403) return 'Fuente no disponible'
  if (status === 401) return 'Tu sesión terminó. Vuelve a iniciar sesión para consultar fuentes.'
  if (status === 429) return 'Se alcanzó el límite de consultas. Espera antes de reintentar.'
  if (status === 503) return 'La consulta documental no está disponible temporalmente. Intenta más tarde.'
  return 'No se pudo consultar la fuente. Intenta nuevamente.'
}
