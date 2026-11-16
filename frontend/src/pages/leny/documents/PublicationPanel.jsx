/* eslint-disable react/prop-types */
import { useEffect, useRef, useState } from 'react'
import { Alert, Button, Card, Descriptions, Space, Spin, Typography } from 'antd'
import { lenyDocumentsApi } from '../../../api/lenyDocuments'
import { documentError } from './documentUtils'

export function PublicationPanel({ document, version, onChange, onClose }) {
  const [readiness, setReadiness] = useState(null)
  const [jobs, setJobs] = useState([])
  const [loading, setLoading] = useState(true)
  const [working, setWorking] = useState(false)
  const [error, setError] = useState('')
  const [confirmation, setConfirmation] = useState(null)
  const [generation, setGeneration] = useState(0)
  const request = useRef(null)
  const mutation = useRef(null)
  useEffect(() => {
    const controller = new AbortController()
    setLoading(true); setError(''); setConfirmation(null); request.current = null
    Promise.all([
      lenyDocumentsApi.ragStatus(controller.signal),
      lenyDocumentsApi.contextualizations(document.id, version.id, { page: 1, page_size: 20 }, controller.signal),
    ]).then(([status, history]) => {
      if (!controller.signal.aborted) { setReadiness(status); setJobs(history.items || []) }
    }).catch((failure) => { if (!controller.signal.aborted) setError(documentError(failure)) })
      .finally(() => { if (!controller.signal.aborted) setLoading(false) })
    return () => { controller.abort(); mutation.current?.abort() }
  }, [document.id, document.revision, version.id, version.validated_indexation_id, generation])

  const published = Boolean(document.published_version_id)
  const exact = document.published_version_id === version.id && document.published_indexation_id === version.validated_indexation_id
  const active = jobs.some((job) => ['queued', 'running'].includes(job.status))
  const valid = Boolean(version.validated_indexation_id) && version.status === 'pending_publication'
  const canPublish = !loading && readiness?.publication_ready === true && valid && !active && !exact
  const indexed = jobs.find((job) => job.indexation_id === version.validated_indexation_id && job.status === 'completed')
  const warnings = indexed?.warnings?.length ? indexed.warnings : indexed?.progress?.warnings || []

  async function submit(action) {
    if (working || loading || confirmation !== action || action === 'publish' && !canPublish) return
    const signature = `${action}:${document.id}:${document.revision}:${version.id}:${version.validated_indexation_id}`
    if (request.current?.signature !== signature) request.current = { signature, request_id: crypto.randomUUID() }
    const controller = new AbortController(); mutation.current = controller
    setWorking(true); setError('')
    try {
      await lenyDocumentsApi[action](document.id, {
        request_id: request.current.request_id, expected_revision: document.revision, confirm: true,
        ...(action === 'publish' ? { version_id: version.id, indexation_id: version.validated_indexation_id } : {}),
      }, controller.signal)
      if (controller.signal.aborted) return
      request.current = null; setConfirmation(null)
      await onChange?.()
    } catch (failure) {
      if (!controller.signal.aborted) {
        setError(documentError(failure))
        if (failure?.response?.status === 409) { request.current = null; setConfirmation(null); await onChange?.() }
      }
    } finally { if (!controller.signal.aborted) setWorking(false) }
  }

  return <Card size="small" title="Revisión de publicación" extra={<Button size="small" disabled={working} onClick={onClose}>Cerrar revisión</Button>} style={{ margin: '20px 0' }}>
    {loading && <Spin aria-label="Revisando publicación" />}
    {error && <Alert type="error" showIcon message={error} />}
    <Descriptions size="small" column={1} items={[
      { key: 'version', label: 'Versión a revisar', children: version.version_number || version.number },
      { key: 'index', label: 'Índice validado elegido', children: <Typography.Text className="leny-doc-index">{version.validated_indexation_id || 'Sin índice validado'}</Typography.Text> },
      { key: 'published', label: 'Publicación vigente', children: published ? <Typography.Text className="leny-doc-index">Versión {document.published_version_id} · Índice {document.published_indexation_id}</Typography.Text> : 'Sin publicación vigente' },
      { key: 'roles', label: 'Lectura autorizada', children: document.role_codes?.join(', ') || 'Sin roles seleccionados' },
    ]} />
    <Alert type="info" showIcon message="Publicar autoriza la consulta de esta versión e índice concretos." description="La lectura permite consultar fragmentos y descargar el original completo. Nuevas versiones o contextualizaciones requieren otra aprobación y no reemplazan esta publicación automáticamente." />
    {!loading && !readiness?.publication_ready && <Alert type="warning" message="La publicación no está habilitada en este entorno. Solicita al administrador revisar la configuración del recuperador." />}
    {active && <Alert type="warning" message="Existe un procesamiento activo para esta versión. Espera su finalización antes de publicar." />}
    {warnings.length > 0 && <Alert type="warning" message="Revisa las advertencias antes de publicar" description={<ul>{warnings.slice(0, 20).map((warning, index) => <li key={index}>{typeof warning === 'string' ? warning : 'Advertencia de extracción u OCR. Revisa el original antes de publicar.'}</li>)}</ul>} />}
    {confirmation && <Alert type="warning" message={confirmation === 'publish' ? 'Confirmar publicación de la versión e índice indicados' : 'Confirmar despublicación'} description={confirmation === 'publish' ? 'Verifica el original, los permisos y las advertencias. Esta publicación reemplazará la anterior, si existe.' : 'Las nuevas consultas y aperturas de fuentes dejarán de tener acceso. El contenido ya recibido puede permanecer en el historial.'} />}
    <Space wrap style={{ marginTop: 16 }}>
      {confirmation ? <><Button type="primary" danger={confirmation === 'unpublish'} disabled={working || confirmation === 'publish' && !canPublish} loading={working} onClick={() => submit(confirmation)}>{confirmation === 'publish' ? 'Confirmar publicación' : 'Confirmar despublicación'}</Button><Button disabled={working} onClick={() => setConfirmation(null)}>Volver</Button></>
        : <><Button type="primary" disabled={!canPublish || working} onClick={() => setConfirmation('publish')}>{exact ? 'Índice publicado' : 'Publicar esta indexación'}</Button>{published && <Button danger disabled={working || loading} onClick={() => setConfirmation('unpublish')}>Despublicar documento</Button>}</>}
      <Button disabled={working || loading} onClick={() => setGeneration((value) => value + 1)}>Actualizar revisión</Button>
    </Space>
  </Card>
}
