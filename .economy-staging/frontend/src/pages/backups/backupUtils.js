import { apiClient } from '../../api/client'

export const BACKUP_TYPE_OPTIONS = [
  { value: 'LOGICO_COMPLETO', label: 'LÓGICO COMPLETO' },
  { value: 'SEMANAL', label: 'SEMANAL' },
  { value: 'MANUAL', label: 'MANUAL' },
]

export const BACKUP_STATE_OPTIONS = [
  { value: 'EN_PROCESO', label: 'EN PROCESO' },
  { value: 'EXITOSO', label: 'EXITOSO' },
  { value: 'FALLIDO', label: 'FALLIDO' },
]

export const BACKUP_ORIGIN_OPTIONS = [
  { value: 'AUTOMATICO', label: 'AUTOMÁTICO' },
  { value: 'MANUAL', label: 'MANUAL' },
]

export function backupTypeLabel(value) {
  return BACKUP_TYPE_OPTIONS.find((item) => item.value === value)?.label || value || 'SIN TIPO'
}

export function backupStateColor(value) {
  if (value === 'EXITOSO') return 'green'
  if (value === 'FALLIDO') return 'red'
  if (value === 'EN_PROCESO') return 'processing'
  return 'default'
}

export function backupOriginLabel(value) {
  return BACKUP_ORIGIN_OPTIONS.find((item) => item.value === value)?.label || value || 'SIN ORIGEN'
}

export function formatBackupDate(value) {
  return value ? new Date(value).toLocaleString('es-BO') : 'SIN FECHA'
}

export function formatBytes(value) {
  const size = Number(value || 0)
  if (!size) return '0 B'
  const units = ['B', 'KB', 'MB', 'GB', 'TB']
  let current = size
  let unitIndex = 0
  while (current >= 1024 && unitIndex < units.length - 1) {
    current /= 1024
    unitIndex += 1
  }
  return `${current.toFixed(unitIndex === 0 ? 0 : 2)} ${units[unitIndex]}`
}

export function shortenHash(value) {
  if (!value) return 'SIN HASH'
  if (value.length <= 18) return value
  return `${value.slice(0, 10)}...${value.slice(-8)}`
}

export async function downloadBackupFile(backupId) {
  const response = await apiClient.get(`/backups/${backupId}/download`, {
    responseType: 'blob',
  })
  const blob = new Blob([response.data], { type: 'application/octet-stream' })
  const url = window.URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  const header = response.headers['content-disposition'] || ''
  const fileMatch = /filename="?([^"]+)"?/.exec(header)
  link.download = fileMatch?.[1] || `backup_${backupId}.dump`
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
  window.URL.revokeObjectURL(url)
}
