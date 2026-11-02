export function documentSize(bytes) {
  if (!Number.isFinite(bytes)) return '—'
  return bytes < 1024 ? `${bytes} B` : bytes < 1024 ** 2 ? `${(bytes / 1024).toFixed(1)} KiB` : `${(bytes / 1024 ** 2).toFixed(1)} MiB`
}

export function documentFormat(mime) {
  return ({ 'application/pdf': 'PDF', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document': 'DOCX', 'image/jpeg': 'JPG', 'image/png': 'PNG' })[mime] || 'Archivo'
}

export const DOCUMENT_ROLES = [
  { value: 'ADMIN', label: 'Administración' },
  { value: 'CAJA', label: 'Caja' },
  { value: 'INV_BOUTIQUE', label: 'Inventario Boutique' },
  { value: 'INV_TALLER', label: 'Inventario Taller' },
  { value: 'MODISTA', label: 'Modista' },
]

export function canManageDocuments(user) {
  return user?.role_code === 'ADMIN' && Boolean(user?.permissions?.includes('leny:admin'))
}

export function documentError(error) {
  if (error?.code === 'ERR_CANCELED' || error?.name === 'AbortError') return 'Solicitud cancelada. Puedes volver a intentarlo.'
  const status = error?.response?.status
  const code = error?.response?.data?.detail?.code
  const reasons = {
    DOCUMENT_REQUEST_INTERRUPTED: 'La solicitud anterior quedó interrumpida. Revisa la biblioteca y confirma una solicitud nueva si el archivo no se almacenó.',
    DOCUMENT_REQUEST_IN_PROGRESS: 'La solicitud anterior todavía se está procesando. Actualiza la biblioteca antes de reintentar.',
    DOCUMENT_IDEMPOTENCY_CONFLICT: 'El identificador de la solicitud corresponde a otros datos. Inicia una carga nueva.',
    DOCUMENT_REVISION_CONFLICT: 'El documento cambió. Cierra esta edición y vuelve a abrirlo para revisar la versión actual.',
    DOCUMENT_CONFIRMATION_REQUIRED: 'La confirmación venció o los datos cambiaron. Revisa nuevamente los cambios antes de confirmar.',
    DOCUMENT_BUSY: 'La biblioteca está procesando otra operación. Espera un momento antes de reintentar.',
    DOCUMENT_RATE_LIMITED: 'Se alcanzó el límite de cargas por usuario. Espera antes de reintentar.',
    DOCUMENT_FOLDER_NOT_EMPTY: 'La carpeta contiene documentos o subcarpetas. Reubícalos antes de eliminarla, incluidos los documentos en papelera.',
    DOCUMENT_FOLDER_DUPLICATE: 'Ya existe una carpeta con ese nombre en el destino.',
    DOCUMENT_FOLDER_CYCLE: 'El cambio crea un ciclo o supera la profundidad permitida de carpetas.',
    DOCUMENT_VALIDATOR_MISSING: 'Los validadores documentales todavía no están instalados. Solicita su configuración al administrador.',
    DOCUMENT_LIBRARY_DISABLED: 'La biblioteca documental todavía no está habilitada en este entorno.',
    DOCUMENT_INVALID_FILE: 'El archivo es inválido, no está permitido o supera los límites de complejidad.',
    DOCUMENT_VALIDATION_TIMEOUT: 'El archivo superó el tiempo permitido de validación.',
    DOCUMENT_IN_TRASH: 'El documento está en papelera. Restáuralo antes de añadir una versión.',
    DOCUMENT_PURGING: 'El documento se está eliminando definitivamente y ya no se puede restaurar.',
  }
  if (reasons[code]) return reasons[code]
  const messages = {
    401: 'Tu sesión ha vencido. Inicia sesión nuevamente.',
    403: 'No tienes autorización para administrar la biblioteca documental.',
    404: 'El documento o la carpeta ya no está disponible. Actualiza la biblioteca.',
    409: 'La operación no puede completarse con el estado actual. Actualiza los datos y revisa los permisos o límites de la biblioteca antes de reintentar.',
    413: 'El archivo o la solicitud supera el tamaño permitido.',
    415: 'El formato o la estructura del archivo no está permitido.',
    422: 'Hay datos o un archivo no válidos. Revisa la información enviada.',
    429: 'Se alcanzó el límite de solicitudes. Espera antes de volver a intentarlo.',
    503: 'La biblioteca no está disponible temporalmente. Intenta nuevamente más tarde.',
  }
  const wait = Number(error?.response?.headers?.['retry-after'])
  if (status === 429 && Number.isFinite(wait) && wait > 0) return `${messages[429]} Reintenta en ${Math.ceil(wait)} segundos.`
  return messages[status] || 'No fue posible completar la operación. Intenta nuevamente.'
}

export function validateDocumentFile(file, limits = {}) {
  const extension = file.name.split('.').pop().toLowerCase()
  if (!['pdf', 'docx', 'jpg', 'jpeg', 'png'].includes(extension)) return 'Solo se permiten PDF, DOCX, JPG, JPEG y PNG.'
  const limit = (['jpg', 'jpeg', 'png'].includes(extension) ? limits.image_bytes || 5 * 1024 ** 2 : limits.max_file_bytes || 10 * 1024 ** 2) / 1024 ** 2
  if (!file.size) return 'El archivo está vacío.'
  if (file.size > limit * 1024 * 1024) return `El archivo supera el límite de ${limit} MiB.`
  return null
}

export async function hashDocumentFile(file) {
  if (!globalThis.crypto?.subtle) throw new Error('SECURE_CONTEXT_REQUIRED')
  const hash = await globalThis.crypto.subtle.digest('SHA-256', await file.arrayBuffer())
  return Array.from(new Uint8Array(hash), (value) => value.toString(16).padStart(2, '0')).join('')
}

export function buildFolderTree(folders, parent = null, ancestors = new Set()) {
  return folders.filter((folder) => (folder.parent_id || null) === parent && !ancestors.has(folder.id)).map((folder) => ({
    key: folder.id, title: folder.name,
    children: buildFolderTree(folders, folder.id, new Set([...ancestors, folder.id])),
  }))
}

export function folderBreadcrumbs(folders, id) {
  const path = [], seen = new Set()
  let current = folders.find((folder) => folder.id === id)
  while (current && !seen.has(current.id)) {
    seen.add(current.id); path.unshift(current)
    current = folders.find((folder) => folder.id === current.parent_id)
  }
  return path
}

export function folderOptions(folders, excludedId) {
  return [{ value: '', label: 'Raíz de la biblioteca' }, ...folders.filter((folder) =>
    folder.id !== excludedId && !folderBreadcrumbs(folders, folder.id).some((ancestor) => ancestor.id === excludedId),
  ).map((folder) => ({ value: folder.id, label: folderBreadcrumbs(folders, folder.id).map((part) => part.name).join(' / ') }))]
}

export function formatDocumentDate(value) {
  return value ? new Date(value).toLocaleString('es-BO', { timeZone: 'America/La_Paz' }) : '—'
}

export function safeDownloadName(header, fallback = 'documento') {
  let name = /filename\*=UTF-8''([^;]+)/i.exec(header || '')?.[1]
  try { if (name) name = decodeURIComponent(name) } catch { name = null }
  name ||= /filename="([^"]+)"|filename=([^;]+)/i.exec(header || '')?.slice(1).find(Boolean) || fallback
  return Array.from(name, (character) => character === '/' || character === '\\' || character.charCodeAt(0) < 32 || character.charCodeAt(0) === 127 ? '_' : character).join('').slice(0, 200)
}

export function saveDocumentBlob(response, fallback) {
  const url = URL.createObjectURL(response.data)
  const link = document.createElement('a')
  link.href = url; link.download = safeDownloadName(response.headers?.['content-disposition'], fallback)
  document.body.appendChild(link)
  try { link.click() } finally { link.remove(); setTimeout(() => URL.revokeObjectURL(url), 1000) }
}
