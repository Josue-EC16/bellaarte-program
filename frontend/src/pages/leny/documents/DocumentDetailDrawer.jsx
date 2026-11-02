/* eslint-disable react/prop-types */
import { useEffect, useRef, useState } from 'react'
import { Alert, Button, Descriptions, Drawer, Empty, Pagination, Space, Spin, Table, Tag, Typography } from 'antd'
import { lenyDocumentsApi } from '../../../api/lenyDocuments'
import { documentError, documentSize, formatDocumentDate, saveDocumentBlob } from './documentUtils'
import { ContextualizationPanel } from './ContextualizationPanel'
import { contextualizationStatus } from './contextualizationUtils'
import { PublicationPanel } from './PublicationPanel'

export function DocumentDetailDrawer({ id, onClose, onEdit, onVersion, onChange }) {
  const [detail, setDetail] = useState(null)
  const [versions, setVersions] = useState({ items: [], total: 0 })
  const [page, setPage] = useState(1)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState(null)
  const [preview, setPreview] = useState(null)
  const [processingVersionId, setProcessingVersionId] = useState(null)
  const [publicationVersionId, setPublicationVersionId] = useState(null)
  const imageUrl = useRef(null)
  const active = useRef(null)
  const refreshRequest = useRef(null)
  function releasePreview() {
    if (imageUrl.current) URL.revokeObjectURL(imageUrl.current)
    imageUrl.current = null
  }
  useEffect(() => {
    if (!id) return
    const controller = new AbortController()
    setBusy(true); setError(null); setDetail(null); setPage(1); setPreview(null); setProcessingVersionId(null); setPublicationVersionId(null); releasePreview()
    lenyDocumentsApi.detail(id, controller.signal).then(setDetail).catch((failure) => { if (!controller.signal.aborted) setError(documentError(failure)) })
      .finally(() => { if (!controller.signal.aborted) setBusy(false) })
    return () => { controller.abort(); active.current?.abort(); refreshRequest.current?.abort(); releasePreview() }
  }, [id])
  useEffect(() => {
    if (!id) return
    const controller = new AbortController()
    setVersions({ items: [], total: 0 })
    lenyDocumentsApi.versions(id, { page, page_size: 10 }, controller.signal).then(setVersions)
      .catch((failure) => { if (!controller.signal.aborted) setError(documentError(failure)) })
    return () => controller.abort()
  }, [id, page])

  async function refreshProcessing() {
    refreshRequest.current?.abort()
    const controller = new AbortController(); refreshRequest.current = controller
    try {
      const [fresh, history] = await Promise.all([lenyDocumentsApi.detail(id, controller.signal), lenyDocumentsApi.versions(id, { page, page_size: 10 }, controller.signal)])
      if (!controller.signal.aborted) { setDetail(fresh); setVersions(history); onChange?.() }
    } catch (failure) { if (!controller.signal.aborted) setError(documentError(failure)) }
  }

  async function openVersion(version, download) {
    active.current?.abort()
    const controller = new AbortController(); active.current = controller
    setBusy(true); setError(null); setPreview(null); releasePreview()
    try {
      const response = await (download ? lenyDocumentsApi.content : lenyDocumentsApi.preview)(id, version.id, controller.signal)
      if (controller.signal.aborted) return
      if (download) { saveDocumentBlob(response, version.original_name || `${detail.title}-v${version.version_number || version.number}`); return }
      const mime = response.headers?.['content-type']?.split(';')[0]
      if (mime === 'image/png' || mime === 'image/jpeg') {
        imageUrl.current = URL.createObjectURL(response.data); setPreview({ kind: 'image', url: imageUrl.current })
      } else if (mime === 'application/json') {
        const result = JSON.parse(await response.data.text())
        if (controller.signal.aborted) return
        if (!['docx', 'download'].includes(result.kind)) throw new Error('UNEXPECTED_PREVIEW')
        setPreview(result)
      } else throw new Error('UNEXPECTED_PREVIEW')
    } catch (failure) { if (!controller.signal.aborted) setError(documentError(failure)) }
    finally { if (!controller.signal.aborted) setBusy(false) }
  }

  const status = contextualizationStatus(detail?.status, Boolean(detail?.published_version_id))
  const processingVersion = versions.items.find((version) => version.id === processingVersionId)
  const publicationVersion = versions.items.find((version) => version.id === publicationVersionId)
  return <Drawer title="Detalle documental" width={860} open={Boolean(id)} onClose={onClose} destroyOnHidden>
    {error && <Alert type="error" showIcon message={error} style={{ marginBottom: 16 }} />}
    {busy && <Spin aria-label="Cargando documento" />}
    {detail ? <>
      <Typography.Title level={3}>{detail.title}</Typography.Title>
      <Tag color={['trash', 'purging', 'PAPELERA'].includes(detail.state) ? 'warning' : status.color}>{detail.state === 'purging' ? 'Eliminación en curso' : ['trash', 'PAPELERA'].includes(detail.state) ? 'En papelera' : status.text}</Tag>
      {detail.published_version_id && <Tag color="success">Publicación vigente</Tag>}
      <Typography.Paragraph style={{ whiteSpace: 'pre-wrap' }}>{detail.description || 'Sin descripción.'}</Typography.Paragraph>
      <Descriptions size="small" column={{ xs: 1, sm: 2 }} items={[
        { key: 'created', label: 'Creado', children: formatDocumentDate(detail.created_at) },
        { key: 'updated', label: 'Actualizado', children: formatDocumentDate(detail.updated_at) },
        { key: 'roles', label: 'Roles de lectura', children: detail.role_codes?.join(', ') || 'Sin roles seleccionados' },
        ...(detail.published_at ? [{ key: 'published', label: 'Publicado', children: formatDocumentDate(detail.published_at) }] : []),
        { key: 'author', label: 'Creador', children: `Usuario #${detail.created_by || '—'}` },
        ...(detail.purge_after ? [{ key: 'expires', label: 'Vence en papelera', children: formatDocumentDate(detail.purge_after) }] : []),
      ]} />
      <Alert type="info" showIcon message="La contextualización y la publicación son aprobaciones diferentes."
        description="Solo la versión e índice publicados alimentan el chat según los roles de lectura. Recontextualizar o subir otra versión conserva la publicación anterior hasta una nueva aprobación." style={{ margin: '20px 0' }} />
      {['active', 'ACTIVO'].includes(detail.state) && <Space wrap style={{ marginBottom: 20 }}>
        <Button onClick={() => onEdit(detail)}>Editar metadatos y permisos</Button>
        <Button onClick={() => onVersion(detail)}>Nueva versión</Button>
      </Space>}
      <Typography.Title level={5}>Versiones conservadas</Typography.Title>
      <Table rowKey="id" size="small" pagination={false} dataSource={versions.items} scroll={{ x: 530 }} columns={[
        { title: 'Versión', key: 'number', render: (_, version) => version.version_number || version.number },
        { title: 'Archivo', key: 'filename', render: (_, version) => <div>
          <div>{version.original_name || version.filename || version.format || 'Original'}</div>
          <Typography.Text type="secondary">{documentSize(version.size_bytes)} · Autor #{version.created_by || '—'}</Typography.Text>
          {version.sha256 && <div><Typography.Text copyable={{ text: version.sha256 }} title={version.sha256}>SHA-256: {version.sha256.slice(0, 12)}…</Typography.Text></div>}
        </div> },
        { title: 'Fecha', dataIndex: 'created_at', render: formatDocumentDate },
        { title: 'Contextualización', key: 'contextualization', render: (_, version) => {
          const state = contextualizationStatus(version.status, detail.published_version_id === version.id)
          return <><Tag color={state.color}>{state.text}</Tag>{detail.published_version_id === version.id && <Tag color="success">{detail.published_indexation_id === version.validated_indexation_id ? 'Publicado' : 'Publicación anterior vigente'}</Tag>}</>
        } },
        { title: 'Acciones', key: 'actions', render: (_, version) => <Space wrap>
          <Button size="small" disabled={busy} onClick={() => openVersion(version, false)}>Vista previa</Button>
          <Button size="small" disabled={busy} onClick={() => openVersion(version, true)}>Descargar</Button>
          {['active', 'ACTIVO'].includes(detail.state) && <Button size="small" onClick={() => setProcessingVersionId(version.id)}>{version.status === 'contextualizing' ? 'Ver progreso' : version.validated_indexation_id || version.status === 'pending_publication' ? 'Contextualizar de nuevo' : version.status === 'contextualization_error' ? 'Revisar y reintentar' : 'Contextualizar'}</Button>}
          {['active', 'ACTIVO'].includes(detail.state) && <Button size="small" disabled={busy} onClick={() => setPublicationVersionId(version.id)}>Revisar publicación</Button>}
        </Space> },
      ]} />
      <Pagination current={page} pageSize={10} total={versions.total} onChange={(value) => { setPage(value); setProcessingVersionId(null); setPublicationVersionId(null) }} showSizeChanger={false} style={{ margin: '16px 0' }} />
      {publicationVersion && ['active', 'ACTIVO'].includes(detail.state) && <PublicationPanel document={detail} version={publicationVersion} onChange={refreshProcessing} onClose={() => setPublicationVersionId(null)} />}
      {processingVersion && ['active', 'ACTIVO'].includes(detail.state) && <ContextualizationPanel key={`${id}:${processingVersion.id}`} documentId={id} version={processingVersion} onClose={() => setProcessingVersionId(null)} onChange={refreshProcessing} />}
      {preview && <section aria-label="Vista previa del documento" className="leny-doc-preview">
        {preview.kind === 'image' && <img src={preview.url} alt={`Vista previa de ${detail.title}`} />}
        {preview.kind === 'download' && <Alert type="info" showIcon message="Este formato se ofrece mediante descarga autenticada. Utiliza Descargar en la versión correspondiente." />}
        {preview.kind === 'docx' && <>
          <Typography.Text type="secondary">Vista simplificada: texto y tablas. El formato original puede variar.</Typography.Text>
          {(Array.isArray(preview.blocks) ? preview.blocks : []).slice(0, 5000).map((block, index) => block.type === 'table'
            ? <div className="leny-doc-preview-table" key={index}><table><tbody>{(Array.isArray(block.rows) ? block.rows : []).slice(0, 2000).map((row, rowIndex) => <tr key={rowIndex}>{(Array.isArray(row) ? row : []).slice(0, 100).map((cell, cellIndex) => <td key={cellIndex}>{typeof cell === 'string' ? cell : ''}</td>)}</tr>)}</tbody></table></div>
            : block.type === 'paragraph' && <p key={index}>{typeof block.text === 'string' ? block.text : ''}</p>)}
          {preview.truncated && <Alert type="warning" message="La vista previa está truncada. Descarga el original para revisar el contenido completo." />}
        </>}
      </section>}
    </> : !busy && !error && <Empty description="No se encontró el documento." />}
  </Drawer>
}
