export const ACTIVE_CONTEXTUALIZATION = new Set(['queued', 'running'])

const statuses = {
  pending_contextualization: { text: 'Pendiente de contextualización', color: 'default' },
  contextualizing: { text: 'Contextualizando', color: 'processing' },
  contextualization_error: { text: 'Error de contextualización', color: 'error' },
  pending_publication: { text: 'Pendiente de publicación', color: 'success' },
}

export function contextualizationStatus(status, hasPublication = false) {
  if (status === 'pending_publication' && hasPublication) return { text: 'Indexación validada', color: 'success' }
  return statuses[status] || statuses.pending_contextualization
}

export function contextualizationStage(job) {
  if (!job) return 'Sin trabajo seleccionado'
  const terminal = { completed: 'Contextualización completada', failed: 'Procesamiento fallido', cancelled: 'Trabajo cancelado', invalidated: 'Trabajo invalidado' }
  if (terminal[job.status]) return terminal[job.status]
  return ({ queued: 'En espera del procesador', waiting_resources: 'Esperando recursos de IA', extracting: 'Extrayendo texto', ocr: 'Reconociendo texto mediante OCR', chunking: 'Preparando fragmentos', loading_model: 'Cargando el modelo local', embedding: 'Generando embeddings', verifying: 'Verificando la indexación' })[job.stage] || 'Procesando documento'
}

export function contextualizationCounters(progress = {}) {
  return [['pages', 'Páginas'], ['ocr_pages', 'Páginas OCR'], ['chunks', 'Fragmentos']].flatMap(([key, label]) => {
    const total = progress[`${key}_total`], done = progress[`${key}_done`]
    return Number.isInteger(total) && total > 0 && Number.isInteger(done) && done >= 0
      ? [{ key, label, total, done: Math.min(done, total) }] : []
  })
}
