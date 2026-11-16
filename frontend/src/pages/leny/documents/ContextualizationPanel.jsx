/* eslint-disable react/prop-types */
import { useEffect, useRef, useState } from 'react'
import { Alert, Button, Card, Descriptions, List, Pagination, Space, Spin, Tag, Typography } from 'antd'
import { lenyDocumentsApi } from '../../../api/lenyDocuments'
import { documentError, formatDocumentDate } from './documentUtils'
import { ACTIVE_CONTEXTUALIZATION, contextualizationCounters, contextualizationStage } from './contextualizationUtils'

// This panel observes durable backend jobs. Closing it stops observation, not
// processing; cancellation is an explicit server operation.
export function ContextualizationPanel({ documentId, version, onClose, onChange }) {
  const [job, setJob] = useState(null)
  const [history, setHistory] = useState({ items: [], total: 0 })
  const [page, setPage] = useState(1)
  const [status, setStatus] = useState(null)
  const [loading, setLoading] = useState(true)
  const [working, setWorking] = useState(false)
  const [loaded, setLoaded] = useState(false)
  const [error, setError] = useState(null)
  const [confirmAgain, setConfirmAgain] = useState(false)
  const [generation, setGeneration] = useState(0)
  const [visible, setVisible] = useState(() => document.visibilityState !== 'hidden')
  const mutation = useRef(null)
  const request = useRef(null)
  const jobId = job?.id
  const jobStatus = job?.status
  const changed = useRef(onChange)
  useEffect(() => { changed.current = onChange }, [onChange])
  useEffect(() => {
    const listener = () => setVisible(document.visibilityState !== 'hidden')
    document.addEventListener('visibilitychange', listener)
    return () => { document.removeEventListener('visibilitychange', listener); mutation.current?.abort() }
  }, [])

  useEffect(() => {
    if (!visible) return
    const controller = new AbortController()
    setLoading(true); setError(null); setLoaded(false)
    Promise.all([
      lenyDocumentsApi.contextualizations(documentId, version.id, { page, page_size: 5 }, controller.signal),
      lenyDocumentsApi.ragStatus(controller.signal),
    ]).then(([result, readiness]) => {
      if (controller.signal.aborted) return
      setHistory(result); setStatus(readiness); setLoaded(true)
      // Only the newest history page chooses the current job. Pagination never
      // replaces an actively observed job with an unrelated historical one.
      if (page === 1) setJob(result.items?.[0] || null)
    }).catch((failure) => { if (!controller.signal.aborted) setError(documentError(failure)) })
      .finally(() => { if (!controller.signal.aborted) setLoading(false) })
    return () => controller.abort()
  }, [documentId, version.id, page, generation, visible])

  useEffect(() => {
    if (!visible || !jobId || !ACTIVE_CONTEXTUALIZATION.has(jobStatus)) return
    const controller = new AbortController()
    let timer
    const poll = async () => {
      try {
        const result = await lenyDocumentsApi.contextualization(jobId, controller.signal)
        if (controller.signal.aborted) return
        setJob(result)
        if (!ACTIVE_CONTEXTUALIZATION.has(result.status)) {
          changed.current?.()
          setGeneration((value) => value + 1)
        } else timer = setTimeout(poll, 2000)
      } catch (failure) { if (!controller.signal.aborted) setError(documentError(failure)) }
    }
    timer = setTimeout(poll, 2000)
    return () => { clearTimeout(timer); controller.abort() }
  }, [jobId, jobStatus, visible, generation]) // Stage updates do not restart the polling clock.

  const active = ACTIVE_CONTEXTUALIZATION.has(job?.status)
  const validated = Boolean(version.validated_indexation_id) || version.status === 'pending_publication'
  const canRetry = ['failed', 'cancelled', 'invalidated'].includes(job?.status)

  async function submit(action) {
    if (working || active || !loaded || !status?.ready) return
    const controller = new AbortController(); mutation.current = controller
    const signature = `${action}:${action === 'retry' ? job?.id : ''}`
    if (request.current?.signature !== signature) request.current = { signature, request_id: crypto.randomUUID() }
    setWorking(true); setError(null)
    try {
      const result = await lenyDocumentsApi.contextualize(documentId, version.id, {
        request_id: request.current.request_id, action, ...(action === 'retry' ? { retry_of: job.id } : {}),
      }, controller.signal)
      if (controller.signal.aborted) return
      request.current = null; setConfirmAgain(false); setJob(result); setPage(1)
      changed.current?.()
    } catch (failure) { if (!controller.signal.aborted) setError(documentError(failure)) }
    finally { if (!controller.signal.aborted) setWorking(false) }
  }

  async function cancel() {
    if (working || !active || job.cancel_requested) return
    const controller = new AbortController(); mutation.current = controller
    setWorking(true); setError(null)
    try {
      const result = await lenyDocumentsApi.cancelContextualization(job.id, controller.signal)
      if (!controller.signal.aborted) {
        setJob(result); changed.current?.()
        if (!ACTIVE_CONTEXTUALIZATION.has(result.status)) setGeneration((value) => value + 1)
      }
    } catch (failure) { if (!controller.signal.aborted) setError(documentError(failure)) }
    finally { if (!controller.signal.aborted) setWorking(false) }
  }

  const counters = contextualizationCounters(job?.progress)
  const warnings = Array.isArray(job?.progress?.warnings) ? job.progress.warnings : []
  return <Card size="small" title={`Contextualización · Versión ${version.version_number || version.number}`} extra={<Button size="small" onClick={onClose}>Cerrar seguimiento</Button>} style={{ margin: '20px 0' }}>
    <Alert type="info" showIcon message="La contextualización prepara un índice privado. Publicarlo requiere una revisión y aprobación ADMIN independiente." />
    {error && <Alert role="alert" type="error" showIcon message={error} style={{ marginTop: 12 }} />}
    {loading && <Spin aria-label="Consultando contextualización" style={{ margin: 12 }} />}
    {status && <>
      <Typography.Paragraph style={{ marginTop: 12 }}><Tag color={status.ready ? 'success' : 'warning'}>{status.ready ? 'Procesamiento disponible' : 'Procesamiento no disponible'}</Tag>Modelo: {status.model || 'No configurado'} · Dimensión: {status.dimension || 'No verificada'} · CPU</Typography.Paragraph>
      {!status.ready && <Alert type="warning" message="El procesamiento no está preparado. Revisa el worker y las dependencias locales antes de reintentar." />}
      {status.ready && status.worker_available === false && <Alert type="warning" message="El worker no está disponible. Los trabajos admitidos permanecerán en espera hasta iniciarlo." />}
    </>}
    {job ? <section aria-label="Progreso de contextualización" aria-live="polite" aria-atomic="true" style={{ marginTop: 16 }}>
      <Typography.Title level={5}>{contextualizationStage(job)}</Typography.Title>
      <Descriptions size="small" column={1} items={[
        { key: 'created', label: 'Solicitado', children: formatDocumentDate(job.created_at) },
        { key: 'attempts', label: 'Intentos', children: job.attempts ?? 0 },
        ...counters.map((counter) => ({ key: counter.key, label: counter.label, children: `${counter.done} de ${counter.total}` })),
        ...(job.finished_at ? [{ key: 'finished', label: 'Finalizado', children: formatDocumentDate(job.finished_at) }] : []),
      ]} />
      {job.status === 'completed' && <Alert type="success" showIcon message="Indexación verificada. Revisa su publicación para habilitarla en el chat. La publicación anterior, si existe, se conserva." />}
      {['failed', 'invalidated'].includes(job.status) && <Alert type="warning" showIcon message={job.safe_message || 'El trabajo no pudo completarse. El original y cualquier índice validado anterior se conservan.'} />}
      {job.cancel_requested && active && <Alert type="info" message="Cancelación solicitada. Se está esperando una interrupción segura del procesamiento." />}
      {warnings.length > 0 && <Alert type="warning" message="Revisión recomendada" description={<ul>{warnings.slice(0, 20).map((warning, index) => <li key={index}>{typeof warning === 'string' ? warning : 'Advertencia de procesamiento. Revisa el resultado antes de publicar.'}</li>)}</ul>} />}
    </section> : loaded && <Typography.Paragraph style={{ marginTop: 16 }}>Esta versión todavía no tiene trabajos de contextualización.</Typography.Paragraph>}
    {confirmAgain && <Alert type="warning" showIcon message="Confirmar nueva contextualización" description="Se generará otra indexación. El índice validado anterior se conservará hasta que la nueva indexación sea verificada." style={{ marginTop: 12 }} />}
    <Space wrap style={{ margin: '16px 0' }}>
      {active ? <Button disabled={working || job.cancel_requested} loading={working} onClick={cancel}>Cancelar procesamiento</Button> : <>
        {confirmAgain ? <><Button type="primary" loading={working} disabled={working || !loaded || !status?.ready} onClick={() => submit('recontextualize')}>Confirmar nueva contextualización</Button><Button disabled={working} onClick={() => setConfirmAgain(false)}>Volver</Button></>
          : (!canRetry || validated) && <Button type="primary" disabled={working || !loaded || !status?.ready} loading={working} onClick={() => validated ? setConfirmAgain(true) : submit('contextualize')}>{validated ? 'Contextualizar de nuevo' : 'Contextualizar versión'}</Button>}
        {canRetry && !confirmAgain && <Button type={validated ? 'default' : 'primary'} disabled={working || !loaded || !status?.ready} loading={working} onClick={() => submit('retry')}>Reintentar trabajo</Button>}
      </>}
      <Button disabled={loading || working} onClick={() => setGeneration((value) => value + 1)}>Actualizar procesamiento</Button>
    </Space>
    <Typography.Title level={5}>Historial de trabajos</Typography.Title>
    <List size="small" dataSource={history.items} locale={{ emptyText: 'Sin trabajos registrados.' }} renderItem={(item) => <List.Item key={item.id}>
      <Space wrap><Typography.Text>{formatDocumentDate(item.created_at)} · {contextualizationStage(item)}</Typography.Text>{item.id === job?.id && <Tag>Actual</Tag>}</Space>
    </List.Item>} />
    <Pagination size="small" current={page} pageSize={5} total={history.total} onChange={setPage} showSizeChanger={false} />
  </Card>
}
