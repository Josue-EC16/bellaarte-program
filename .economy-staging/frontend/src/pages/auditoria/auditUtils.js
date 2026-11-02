export const AUDIT_ACTION_OPTIONS = [
  { value: 'insert', label: 'INSERT' },
  { value: 'update', label: 'UPDATE' },
  { value: 'delete', label: 'DELETE' },
  { value: 'login', label: 'LOGIN' },
  { value: 'logout', label: 'LOGOUT' },
  { value: 'cancelacion', label: 'CANCELACION' },
  { value: 'anulacion', label: 'ANULACION' },
  { value: 'cambio_estado', label: 'CAMBIO_ESTADO' },
  { value: 'otro', label: 'OTRO' },
]

export function auditActionLabel(value) {
  return AUDIT_ACTION_OPTIONS.find((item) => item.value === value)?.label || String(value || '').toUpperCase()
}

export function auditActionColor(value) {
  switch (value) {
    case 'insert':
      return '#4f7f4f'
    case 'update':
      return '#5977a8'
    case 'delete':
      return '#8c5a54'
    case 'login':
      return '#6a7a43'
    case 'logout':
      return '#875b91'
    case 'cancelacion':
      return '#a15d2e'
    case 'anulacion':
      return '#b8475c'
    case 'cambio_estado':
      return '#8c6d22'
    default:
      return '#6f4c31'
  }
}

export function auditActionSurface(value) {
  return `${auditActionColor(value)}18`
}

export function formatAuditDate(value) {
  return value ? new Date(value).toLocaleString('es-BO') : 'SIN FECHA'
}

function withBaseHref(html) {
  if (html.includes('<base ')) {
    return html
  }
  return html.replace('<head>', `<head><base href="${window.location.origin}/" />`)
}

export async function openAuditPrintable(apiClient, params, messageApi) {
  try {
    const response = await apiClient.get('/auditoria/export', {
      params: { ...params, format: 'html' },
      responseType: 'text',
    })
    const popup = window.open('', '_blank')
    if (!popup) {
      messageApi?.error('EL NAVEGADOR BLOQUEÓ LA VISTA DE IMPRESIÓN.')
      return
    }
    popup.document.write(withBaseHref(response.data))
    popup.document.close()
  } catch (error) {
    messageApi?.error(error.response?.data?.detail || 'NO FUE POSIBLE GENERAR LA VISTA IMPRIMIBLE DE AUDITORÍA.')
  }
}

export function downloadAuditCsv(apiClient, params) {
  const query = new URLSearchParams({ ...params, format: 'csv' })
  window.open(`${apiClient.defaults.baseURL}/auditoria/export?${query.toString()}`, '_blank', 'noopener,noreferrer')
}
