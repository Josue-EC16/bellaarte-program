/* eslint-disable react/prop-types */
import { useEffect, useRef, useState } from 'react'
import { Alert, Button, Drawer, Space, Spin, Typography } from 'antd'
import { lenySourcesApi } from '../../api/lenySources'
import { saveDocumentBlob } from './documents/documentUtils'
import { sourceError, sourceLocator, validLenySources } from './lenySourceUtils'

export function LenySources({ sources, status }) {
  const [selected, setSelected] = useState(null)
  const [unavailable, setUnavailable] = useState(new Set())
  if (status !== 'completed' || !validLenySources(sources) || !sources.length) return null
  return <section className="leny-sources" aria-label="Fuentes consultadas">
    <h3>Fuentes consultadas</h3>
    <ul>{sources.map((source) => <li key={source.source_id}>
      {source.available && !unavailable.has(source.source_id) ? <>
        <span className="leny-source-title">[{source.citation_id}] {source.label || 'Documento publicado'}</span>
        <span className="leny-source-location">Versión {source.version} · {sourceLocator(source.locator, source.source_type)}</span>
        <Button size="small" onClick={() => setSelected(source.source_id)} aria-label={`Ver fuente ${source.citation_id}`}>Ver fuente</Button>
      </> : <span>Fuente no disponible</span>}
    </li>)}</ul>
    <LenySourceDrawer sourceId={selected} onClose={() => setSelected(null)} onUnavailable={(id) => setUnavailable((previous) => new Set([...previous, id]))} />
  </section>
}

export function LenySourceDrawer({ sourceId, onClose, onUnavailable }) {
  const [source, setSource] = useState(null)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const [downloading, setDownloading] = useState(false)
  const [refresh, setRefresh] = useState(0)
  const active = useRef(null)
  const unavailable = useRef(onUnavailable)
  useEffect(() => { unavailable.current = onUnavailable }, [onUnavailable])
  useEffect(() => {
    setSource(null); setError(''); setDownloading(false)
    if (!sourceId) return
    const controller = new AbortController()
    setLoading(true)
    lenySourcesApi.detail(sourceId, controller.signal).then((result) => {
      if (controller.signal.aborted) return
      if (!validLenySources([result]) || result.source_id !== sourceId || !result.available || typeof result.text !== 'string' || new TextEncoder().encode(result.text).byteLength > 3072) {
        throw new Error('INVALID_SOURCE')
      }
      setSource(result)
    }).catch((failure) => {
      if (!controller.signal.aborted) {
        setError(sourceError(failure))
        if ([403, 404].includes(failure?.response?.status)) unavailable.current?.(sourceId)
      }
    }).finally(() => { if (!controller.signal.aborted) setLoading(false) })
    return () => { controller.abort(); active.current?.abort() }
  }, [sourceId, refresh])

  async function download() {
    if (!source || downloading) return
    const controller = new AbortController(); active.current = controller
    setDownloading(true); setError('')
    try {
      const response = await lenySourcesApi.download(sourceId, controller.signal)
      if (!controller.signal.aborted) saveDocumentBlob(response, `${source.label || 'Documento'}-v${source.version}`)
    } catch (failure) {
      if (!controller.signal.aborted) {
        setError(sourceError(failure))
        if ([403, 404].includes(failure?.response?.status)) { setSource(null); unavailable.current?.(sourceId) }
      }
    } finally { if (!controller.signal.aborted) setDownloading(false) }
  }

  return <Drawer title="Fuente documental" width={560} open={Boolean(sourceId)} onClose={onClose} destroyOnHidden>
    {loading && <Spin aria-label="Consultando fuente" />}
    {error && <Alert type="warning" showIcon message={error} action={error !== 'Fuente no disponible' && <Button size="small" onClick={() => setRefresh((value) => value + 1)}>Reintentar</Button>} />}
    {source && <div className="leny-source-detail">
      <Typography.Title level={4}>{source.label || 'Documento publicado'}</Typography.Title>
      <Typography.Paragraph>Versión {source.version} · {sourceLocator(source.locator, source.source_type)}</Typography.Paragraph>
      {source.warnings.length > 0 && <Alert type="warning" message="Revisión recomendada" description={<ul>{source.warnings.map((warning, index) => <li key={index}>{warning}</li>)}</ul>} />}
      <h3>Fragmento consultado</h3><p className="leny-source-text">{source.text}</p>
      <Space wrap><Button onClick={download} loading={downloading} disabled={downloading}>Descargar original publicado</Button></Space>
      <Typography.Paragraph type="secondary">La descarga incluye el archivo completo de esta publicación. El acceso se comprueba en cada solicitud.</Typography.Paragraph>
    </div>}
  </Drawer>
}
