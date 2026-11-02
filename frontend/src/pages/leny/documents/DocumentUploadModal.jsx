/* eslint-disable react/prop-types */
import { useEffect, useRef, useState } from 'react'
import { Alert, Button, Form, Input, Modal, Progress, Select, Space, Tag, Typography } from 'antd'
import { lenyDocumentsApi } from '../../../api/lenyDocuments'
import { FormProcessAlert } from '../../../components/forms/FormProcessAlert'
import { FORM_COMMON_PROPS, FORM_VALIDATE_MESSAGES } from '../../../components/forms/formConfig'
import { documentError, folderOptions, hashDocumentFile, validateDocumentFile } from './documentUtils'

export function DocumentUploadModal({ open, folders, folderId, document, onClose, onComplete }) {
  const [form] = Form.useForm()
  const [entries, setEntries] = useState([])
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState(null)
  const [limits, setLimits] = useState({ batch_size: 5, max_file_bytes: 10 * 1024 ** 2, image_bytes: 5 * 1024 ** 2, max_pixels: 12000000, pdf_pages: 50 })
  const controller = useRef(null)
  const input = useRef(null)
  const editEntries = (id, patch) => setEntries((current) => current.map((entry) => entry.id === id ? { ...entry, ...patch } : entry))
  useEffect(() => () => controller.current?.abort(), [])
  useEffect(() => {
    if (!open) return
    const request = new AbortController()
    lenyDocumentsApi.options(request.signal).then(setLimits).catch((failure) => { if (!request.signal.aborted) setError(documentError(failure)) })
    return () => request.abort()
  }, [open])
  useEffect(() => {
    if (open) { form.resetFields(); form.setFieldsValue({ folder_id: folderId || folders[0]?.id, title: '', description: '' }); setEntries([]); setError(null) }
    // Folder refreshes must not reset an in-flight intent or selected files.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open, folderId, form])

  function chooseFiles(event) {
    const files = Array.from(event.target.files || [])
    if (files.length > (document ? 1 : limits.batch_size)) { setError(document ? 'Selecciona un archivo para la nueva versión.' : `Selecciona un máximo de ${limits.batch_size} archivos.`); return }
    setError(null)
    setEntries(files.map((file) => { const error = validateDocumentFile(file, limits); return { file, id: crypto.randomUUID(), status: error ? 'invalid' : 'pending', progress: null, error } }))
    if (files.length === 1 && !document) form.setFieldValue('title', files[0].name.replace(/\.[^.]+$/, ''))
  }

  async function submit(values) {
    if (!entries.some((entry) => !['done', 'invalid', 'restart'].includes(entry.status))) return
    controller.current = new AbortController()
    setBusy(true); setError(null)
    let completed = false
    for (const entry of entries) {
      if (['done', 'invalid', 'restart'].includes(entry.status) || controller.current.signal.aborted) continue
      editEntries(entry.id, { status: 'hashing', error: null })
      try {
        // Retain the same immutable intent across manual retries and JWT refresh.
        const metadata = entry.metadata || (document
          ? { request_id: entry.id, sha256: await hashDocumentFile(entry.file), revision: document.revision }
          : { request_id: entry.id, sha256: await hashDocumentFile(entry.file), folder_id: values.folder_id || null,
            title: entries.length === 1 ? values.title.trim() : entry.file.name.replace(/\.[^.]+$/, ''), description: values.description?.trim() || '' })
        editEntries(entry.id, { metadata, status: 'uploading', progress: 0 })
        if (controller.current.signal.aborted) break
        await lenyDocumentsApi.upload(entry.file, metadata, { documentId: document?.id, signal: controller.current.signal,
          onProgress: (progress) => editEntries(entry.id, { progress }) })
        editEntries(entry.id, { status: 'done', progress: 100 }); completed = true
      } catch (failure) {
        editEntries(entry.id, { status: failure.response?.data?.detail?.code === 'DOCUMENT_REQUEST_INTERRUPTED' ? 'restart' : 'error', error: failure.message === 'SECURE_CONTEXT_REQUIRED'
          ? 'La carga requiere HTTPS o localhost para verificar el archivo.' : documentError(failure) })
        if (failure.response?.status === 401 || failure.response?.status === 403) break
      }
    }
    setBusy(false)
    if (completed) onComplete()
  }

  const hasIntent = entries.some((entry) => entry.metadata)
  return <Modal open={open} title={document ? `Nueva versión · ${document.title}` : 'Almacenar documentos'} onCancel={onClose}
    maskClosable={false} closable={!busy} keyboard={!busy} footer={null} destroyOnHidden>
    <Alert type="info" showIcon message="Los archivos se almacenan de forma privada. Todavía no serán utilizados por el chat."
      description={`PDF y DOCX: ${limits.max_file_bytes / 1024 ** 2} MiB. Imágenes: ${limits.image_bytes / 1024 ** 2} MiB y ${limits.max_pixels / 1000000} megapíxeles. PDF: hasta ${limits.pdf_pages} páginas.`} style={{ marginBottom: 20 }} />
    <Form {...FORM_COMMON_PROPS} validateMessages={FORM_VALIDATE_MESSAGES} form={form} onFinish={submit} disabled={busy || hasIntent}>
      {!document && <>
        <Form.Item name="folder_id" label="Carpeta" rules={[{ required: true }]}><Select options={folderOptions(folders).filter((option) => option.value)} showSearch optionFilterProp="label" /></Form.Item>
        {entries.length <= 1 && <Form.Item name="title" label="Título" rules={[{ required: true, whitespace: true }, { max: 200 }]}><Input maxLength={200} /></Form.Item>}
        <Form.Item name="description" label="Descripción"><Input.TextArea maxLength={2000} rows={2} /></Form.Item>
      </>}
      <input ref={input} type="file" aria-label={document ? 'Archivo de la nueva versión' : 'Archivos para almacenar'} accept=".pdf,.docx,.jpg,.jpeg,.png"
        multiple={!document} disabled={busy || hasIntent} onChange={chooseFiles} />
      <Typography.Paragraph type="secondary">{document ? 'La versión anterior se conservará.' : `Hasta ${limits.batch_size} archivos por lote. Se enviarán uno a uno; cada archivo tendrá su propio resultado.`}</Typography.Paragraph>
      {entries.map((entry) => <div className="leny-doc-upload-entry" key={entry.id}>
        <Typography.Text strong>{entry.file.name}</Typography.Text>{' '}
        <Tag color={entry.status === 'done' ? 'success' : entry.error ? 'error' : 'default'}>{entry.status === 'done' ? 'Almacenado' : entry.status === 'hashing' ? 'Verificando huella…' : entry.status === 'uploading' && entry.progress === 100 ? 'Transferido · validando archivo…' : entry.status === 'uploading' ? 'Transfiriendo…' : entry.error ? 'No almacenado' : 'Pendiente'}</Tag>
        {entry.status === 'uploading' && <Progress percent={entry.progress || 0} size="small" aria-label={`Transferencia de ${entry.file.name}`} />}
        {entry.error && <Alert type="error" message={entry.error} showIcon />}
        {entry.status === 'restart' && <Button disabled={busy} onClick={() => {
          setEntries((current) => current.map((item) => item.id === entry.id ? { ...item, id: crypto.randomUUID(), status: 'pending', metadata: undefined, error: null, progress: null } : item))
        }}>Confirmar solicitud nueva para este archivo</Button>}
      </div>)}
      <FormProcessAlert message={error} />
      {hasIntent && <Typography.Paragraph type="secondary">Los reintentos conservan los datos originales para evitar duplicados. Cierra y abre una carga nueva si necesitas cambiarlos.</Typography.Paragraph>}
      <Space wrap style={{ marginTop: 18 }}>
        {busy ? <Button disabled={false} onClick={() => controller.current?.abort()}>Cancelar transferencia</Button>
          : <><Button disabled={false} onClick={onClose}>Cerrar</Button><Button type="primary" htmlType="submit" disabled={!entries.some((entry) => !['done', 'invalid', 'restart'].includes(entry.status))}>{hasIntent ? 'Reintentar pendientes' : 'Almacenar'}</Button></>}
      </Space>
    </Form>
  </Modal>
}
