import { useCallback, useEffect, useRef, useState } from 'react'
import { Alert, App, Breadcrumb, Button, Card, Col, DatePicker, Empty, Form, Input, InputNumber, Modal, Row, Select, Space, Table, Tabs, Tag, Tree, Typography } from 'antd'
import { DeleteOutlined, FolderAddOutlined, FolderOpenOutlined, ReloadOutlined, UploadOutlined } from '@ant-design/icons'
import { lenyDocumentsApi } from '../../../api/lenyDocuments'
import { FORM_COMMON_PROPS, FORM_VALIDATE_MESSAGES } from '../../../components/forms/formConfig'
import { FormProcessAlert } from '../../../components/forms/FormProcessAlert'
import { applyFormApiError } from '../../../components/forms/formErrorUtils'
import { DocumentUploadModal } from './DocumentUploadModal'
import { DocumentDetailDrawer } from './DocumentDetailDrawer'
import { contextualizationStatus } from './contextualizationUtils'
import { buildFolderTree, DOCUMENT_ROLES, documentError, documentFormat, documentSize, folderBreadcrumbs, folderOptions, formatDocumentDate } from './documentUtils'
import './documents.css'

export function LenyDocumentsPage() {
  const { modal, message } = App.useApp()
  const [folders, setFolders] = useState([])
  const [folderId, setFolderId] = useState(null)
  const [tab, setTab] = useState('active')
  const [filters, setFilters] = useState({})
  const [pagination, setPagination] = useState({ page: 1, page_size: 20 })
  const [result, setResult] = useState({ items: [], total: 0 })
  const [loading, setLoading] = useState(false)
  const [working, setWorking] = useState(false)
  const [error, setError] = useState(null)
  const [formError, setFormError] = useState(null)
  const [generation, setGeneration] = useState(0)
  const [selected, setSelected] = useState([])
  const [detailId, setDetailId] = useState(null)
  const [upload, setUpload] = useState(null)
  const [editor, setEditor] = useState(null)
  const [form] = Form.useForm()
  const editorRequest = useRef(null)
  const refresh = useCallback(() => setGeneration((value) => value + 1), [])

  useEffect(() => {
    const controller = new AbortController()
    lenyDocumentsApi.folders(controller.signal).then((data) => setFolders(data.items || []))
      .catch((failure) => { if (!controller.signal.aborted) setError(documentError(failure)) })
    return () => controller.abort()
  }, [generation])
  useEffect(() => {
    const controller = new AbortController()
    setLoading(true); setError(null); setSelected([])
    const params = { ...pagination, ...filters, ...(tab === 'active' ? { folder_id: folderId || undefined } : {}) }
    ;(tab === 'trash' ? lenyDocumentsApi.trash : lenyDocumentsApi.list)(params, controller.signal)
      .then(setResult).catch((failure) => { if (!controller.signal.aborted) { setResult({ items: [], total: 0 }); setError(documentError(failure)) } })
      .finally(() => { if (!controller.signal.aborted) setLoading(false) })
    return () => controller.abort()
  }, [pagination, filters, folderId, tab, generation])
  useEffect(() => () => editorRequest.current?.abort(), [])

  function changeFolder(id) { setFolderId(id || null); setPagination((current) => ({ ...current, page: 1 })) }
  function changeFilter(key, value) { setFilters((current) => ({ ...current, [key]: value || undefined })); setPagination((current) => ({ ...current, page: 1 })) }
  function confirm(options) {
    return new Promise((resolve) => modal.confirm({ ...options, maskClosable: false, onOk: () => resolve(true), onCancel: () => resolve(false) }))
  }
  function openFolderEditor(folder = null) {
    form.resetFields(); setFormError(null)
    form.setFieldsValue(folder ? { ...folder, parent_id: folder.parent_id || '' } : { name: '', description: '', parent_id: folderId || '', role_codes: ['ADMIN'] })
    setEditor({ kind: 'folder', record: folder })
  }
  async function openDocumentEditor(record, restore = false) {
    editorRequest.current?.abort()
    const controller = new AbortController(); editorRequest.current = controller
    setWorking(true); setError(null)
    try {
      const fresh = await lenyDocumentsApi.detail(record.id, controller.signal)
      if (controller.signal.aborted) return
      const defaults = folders.find((folder) => folder.id === fresh.folder_id)?.role_codes || []
      form.resetFields(); setFormError(null); form.setFieldsValue({ ...fresh, folder_id: fresh.folder_id || '',
        role_codes: restore ? (fresh.role_codes || []).filter((role) => defaults.includes(role)) : fresh.role_codes })
      setEditor({ kind: restore ? 'restore' : 'document', record: fresh })
    } catch (failure) { if (!controller.signal.aborted) setError(documentError(failure)) }
    finally { if (!controller.signal.aborted) setWorking(false) }
  }
  async function submitEditor(values) {
    setWorking(true); setFormError(null)
    try {
      if (editor.kind === 'folder') {
        const payload = { name: values.name.trim(), description: values.description?.trim() || '', parent_id: values.parent_id || null, role_codes: values.role_codes || [] }
        if (editor.record) await lenyDocumentsApi.updateFolder(editor.record.id, payload)
        else await lenyDocumentsApi.createFolder(payload)
      } else {
        const record = editor.record
        const changes = { revision: record.revision, folder_id: values.folder_id || null, role_codes: values.role_codes || [] }
        const review = await lenyDocumentsApi.changePreview(record.id, changes)
        const accepted = await confirm({ title: editor.kind === 'restore' ? 'Revisar restauración y permisos' : 'Revisar destino y permisos',
          content: <><Typography.Paragraph>{review.broadens ? 'La selección amplía los permisos preparados. Confirma expresamente que autorizas esta ampliación.' : 'Confirma los permisos y el destino que se aplicarán al documento.'}</Typography.Paragraph>
            <Typography.Paragraph>Roles resultantes: {review.role_codes?.join(', ') || 'Ninguno'}</Typography.Paragraph>
            <Typography.Text type="secondary">Todavía no concede acceso documental a otros roles en esta etapa.</Typography.Text></>, okText: 'Confirmar cambios', cancelText: 'Volver' })
        if (!accepted) return
        const payload = { ...changes, role_codes: review.role_codes || [], confirmation: review.token }
        if (editor.kind === 'restore') await lenyDocumentsApi.restore(record.id, payload)
        else await lenyDocumentsApi.update(record.id, { ...payload, title: values.title.trim(), description: values.description?.trim() || '' })
      }
      setEditor(null); setDetailId(null); refresh(); message.success('Cambios guardados.')
    } catch (failure) {
      if (failure.response?.status === 422) applyFormApiError(form, failure)
      setFormError(documentError(failure))
    } finally { setWorking(false) }
  }
  async function trashDocument(record) {
    if (!await confirm({ title: 'Enviar a la papelera', content: `“${record.title}” se conservará durante diez días. Después vencerá el plazo de restauración y podrá eliminarse definitivamente.`, okText: 'Enviar a papelera', cancelText: 'Cancelar' })) return
    setWorking(true); setError(null)
    try {
      const fresh = await lenyDocumentsApi.detail(record.id)
      await lenyDocumentsApi.moveToTrash(record.id, fresh.revision)
      setDetailId(null); refresh(); message.success('Documento enviado a la papelera.')
    } catch (failure) { setError(documentError(failure)) } finally { setWorking(false) }
  }
  async function purge(ids, all = false) {
    setWorking(true); setError(null)
    try {
      const review = await lenyDocumentsApi.purgePreview(all ? { all: true } : { ids })
      if (!review.count) { message.info('No hay documentos para eliminar.'); return }
      if (!await confirm({ title: 'Eliminar documentos definitivamente', okButtonProps: { danger: true }, okText: `Eliminar ${review.count} documento(s)`, cancelText: 'Cancelar',
        content: <><Typography.Paragraph>Se eliminarán sus originales, versiones y metadatos. Esta acción no se puede deshacer.</Typography.Paragraph>
          {all && <Typography.Paragraph>El vaciado se procesa en lotes de hasta 1.000 documentos.{review.remaining > 0 ? ` Quedarán ${review.remaining} documento(s) para revisar en un nuevo lote.` : ''}</Typography.Paragraph>}
          <ul>{review.items?.map((item) => <li key={item.id}>{item.title || item.id}</li>)}</ul>
          <Typography.Text type="secondary">Los respaldos históricos conservan su propia política de retención.</Typography.Text></> })) return
      const payload = { confirmation: review.token, request_id: crypto.randomUUID() }
      if (all || ids.length > 1) await lenyDocumentsApi.emptyTrash(payload)
      else await lenyDocumentsApi.purge(ids[0], payload)
      setDetailId(null); refresh(); message.success(review.remaining > 0 ? `Lote eliminado. Quedan ${review.remaining} documento(s) en la papelera.` : 'Eliminación procesada.')
    } catch (failure) { setError(documentError(failure)) } finally { setWorking(false) }
  }
  async function deleteFolder() {
    const folder = folders.find((item) => item.id === folderId)
    if (!folder || !await confirm({ title: 'Eliminar carpeta vacía', content: `¿Eliminar “${folder.name}”? Debe estar vacía, sin documentos en papelera ni subcarpetas.`, okText: 'Eliminar carpeta', cancelText: 'Cancelar', okButtonProps: { danger: true } })) return
    setWorking(true); setError(null)
    try { await lenyDocumentsApi.deleteFolder(folder.id); changeFolder(folder.parent_id); refresh() }
    catch (failure) { setError(documentError(failure)) } finally { setWorking(false) }
  }
  const breadcrumbs = [{ title: <Button type="link" size="small" onClick={() => changeFolder(null)}>Biblioteca</Button> }, ...folderBreadcrumbs(folders, folderId).map((folder) => ({ title: <Button type="link" size="small" onClick={() => changeFolder(folder.id)}>{folder.name}</Button> }))]
  const columns = [
    { title: 'Documento', dataIndex: 'title', render: (title, record) => <div>
      <Button type="link" className="leny-doc-title-button" onClick={() => setDetailId(record.id)}>{title}</Button>
      <div><Typography.Text type="secondary">{documentFormat(record.latest_media_type)} · {documentSize(record.latest_size_bytes)} · {folders.find((folder) => folder.id === record.folder_id)?.name || 'Carpeta'}</Typography.Text></div>
      <div><Typography.Text type="secondary">Roles de lectura: {record.role_codes?.join(', ') || 'Sin roles'} · Creador #{record.created_by || '—'}</Typography.Text></div>
    </div> },
    { title: 'Estado', key: 'state', render: (_, record) => <><Tag color={tab === 'trash' ? 'warning' : contextualizationStatus(record.status).color}>{record.state === 'purging' ? 'Eliminación en curso' : tab === 'trash' ? 'En papelera' : contextualizationStatus(record.status, Boolean(record.published_version_id)).text}</Tag>{tab !== 'trash' && record.published_version_id && <Tag color="success">Publicación vigente</Tag>}</> },
    { title: 'Versiones', key: 'versions', render: (_, record) => record.version_count ?? record.latest_version_number ?? '—' },
    { title: tab === 'trash' ? 'Vence' : 'Actualizado', key: 'date', render: (_, record) => formatDocumentDate(tab === 'trash' ? record.purge_after : record.updated_at) },
    { title: 'Acciones', key: 'actions', render: (_, record) => <Space wrap>
      {tab === 'trash' ? <><Button size="small" disabled={working || record.state === 'purging' || new Date(record.purge_after) <= new Date()} onClick={() => openDocumentEditor(record, true)}>Restaurar</Button><Button size="small" danger disabled={working || record.state === 'purging'} onClick={() => purge([record.id])}>Eliminar</Button></>
        : <><Button size="small" disabled={working} onClick={() => openDocumentEditor(record)}>Editar</Button><Button size="small" danger disabled={working} onClick={() => trashDocument(record)}>Papelera</Button></>}
    </Space> },
  ]
  return <div className="leny-documents">
    <div className="leny-doc-heading"><div><Typography.Text className="leny-doc-eyebrow">LENY · BIBLIOTECA PRIVADA</Typography.Text><Typography.Title level={2}>Gestión documental</Typography.Title><Typography.Paragraph type="secondary">Organiza los documentos de BELLAARTE BOUTIQUE y conserva cada versión.</Typography.Paragraph></div>
      <Space wrap><Button icon={<ReloadOutlined />} onClick={refresh} disabled={loading || working}>Actualizar</Button><Button type="primary" icon={<UploadOutlined />} onClick={() => setUpload({ document: null })} disabled={working || tab === 'trash' || !folders.length}>Almacenar archivos</Button></Space></div>
    <Alert type="info" showIcon message="Administración exclusiva de ADMIN · Contextualización documental local"
      description="Los documentos requieren contextualización y publicación explícita. El chat consulta únicamente publicaciones vigentes según los roles de lectura." />
    {error && <Alert role="alert" type="error" message={error} showIcon action={<Button size="small" onClick={refresh}>Reintentar</Button>} style={{ marginTop: 16 }} />}
    <Tabs activeKey={tab} onChange={(key) => { setTab(key); setPagination((current) => ({ ...current, page: 1 })); setDetailId(null) }} items={[{ key: 'active', label: 'Biblioteca' }, { key: 'trash', label: 'Papelera · 10 días' }]} />
    <Row gutter={[20, 20]}>
      {tab === 'active' && <Col xs={24} lg={6}><Card size="small" title={<Space><FolderOpenOutlined />Carpetas</Space>}>
        <Space wrap><Button size="small" icon={<FolderAddOutlined />} onClick={() => openFolderEditor()} disabled={working}>Nueva</Button>{folderId && <><Button size="small" onClick={() => openFolderEditor(folders.find((item) => item.id === folderId))} disabled={working}>Editar</Button><Button aria-label="Eliminar carpeta vacía" size="small" danger icon={<DeleteOutlined />} onClick={deleteFolder} disabled={working} /></>}</Space>
        <Button type={folderId ? 'text' : 'link'} block onClick={() => changeFolder(null)} style={{ marginTop: 14 }}>Raíz de la biblioteca</Button>
        {folders.length ? <Tree treeData={buildFolderTree(folders)} selectedKeys={folderId ? [folderId] : []} onSelect={(keys) => changeFolder(keys[0])} aria-label="Carpetas documentales" /> : <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="Crea una carpeta para comenzar a almacenar documentos." />}
      </Card></Col>}
      <Col xs={24} lg={tab === 'active' ? 18 : 24}><Card className="leny-doc-list-card">
        {tab === 'active' ? <Breadcrumb items={breadcrumbs} style={{ marginBottom: 20 }} /> : <Typography.Paragraph type="secondary">La restauración está disponible durante diez días. La eliminación definitiva también puede ejecutarse antes del vencimiento, con confirmación.</Typography.Paragraph>}
        <div className="leny-doc-filters">
          <Input.Search aria-label="Buscar documentos" placeholder="Buscar por título" allowClear onSearch={(value) => changeFilter('search', value.trim())} />
          <Select aria-label="Filtrar formato" placeholder="Todos los formatos" allowClear options={['pdf', 'docx', 'jpg', 'jpeg', 'png'].map((value) => ({ value, label: value.toUpperCase() }))} onChange={(value) => changeFilter('format', value)} />
          <InputNumber aria-label="Filtrar identificador del creador" placeholder="ID del creador" min={1} precision={0} onChange={(value) => changeFilter('creator_id', value)} style={{ width: '100%' }} />
          <DatePicker.RangePicker aria-label="Rango de fechas de creación" format="DD/MM/YYYY" onChange={(dates) => { setFilters((current) => ({ ...current, date_from: dates?.[0]?.format('YYYY-MM-DD'), date_to: dates?.[1]?.format('YYYY-MM-DD') })); setPagination((current) => ({ ...current, page: 1 })) }} />
        </div>
        {tab === 'trash' && <Space wrap style={{ marginBottom: 16 }}><Button danger disabled={!selected.length || working} onClick={() => purge(selected)}>Eliminar seleccionados ({selected.length})</Button><Button danger disabled={!result.total || working} onClick={() => purge([], true)}>Vaciar papelera</Button></Space>}
        <Table rowKey="id" loading={loading} columns={columns} dataSource={result.items} scroll={{ x: 850 }}
          rowSelection={tab === 'trash' ? { selectedRowKeys: selected, onChange: setSelected, getCheckboxProps: (record) => ({ disabled: record.state === 'purging' }) } : undefined}
          locale={{ emptyText: <Empty description={tab === 'trash' ? 'La papelera está vacía.' : 'No hay documentos en esta ubicación.'} /> }}
          pagination={{ current: pagination.page, pageSize: pagination.page_size, total: result.total, showSizeChanger: true, pageSizeOptions: [20, 50, 100], showTotal: (total) => `${total} documento(s)`, onChange: (page, page_size) => setPagination({ page, page_size }) }} />
      </Card></Col>
    </Row>
    <DocumentUploadModal open={Boolean(upload)} folders={folders} folderId={folderId} document={upload?.document} onClose={() => setUpload(null)} onComplete={() => { setDetailId(null); refresh() }} />
    <DocumentDetailDrawer id={detailId} onClose={() => setDetailId(null)} onEdit={openDocumentEditor} onVersion={(document) => setUpload({ document })} onChange={refresh} />
    <Modal open={Boolean(editor)} title={editor?.kind === 'folder' ? editor.record ? 'Editar carpeta' : 'Nueva carpeta' : editor?.kind === 'restore' ? 'Restaurar documento' : 'Editar documento'} maskClosable={false} closable={!working} keyboard={!working} onCancel={() => setEditor(null)} footer={null} destroyOnHidden>
      <Form {...FORM_COMMON_PROPS} form={form} validateMessages={FORM_VALIDATE_MESSAGES} onFinish={submitEditor} disabled={working}>
        <FormProcessAlert message={formError} />
        {editor?.kind === 'folder' ? <><Form.Item name="name" label="Nombre" rules={[{ required: true, whitespace: true }, { max: 120 }]}><Input maxLength={120} /></Form.Item><Form.Item name="parent_id" label="Carpeta superior"><Select options={folderOptions(folders, editor.record?.id)} showSearch optionFilterProp="label" /></Form.Item></>
          : <><Form.Item name="title" label="Título" rules={[{ required: true, whitespace: true }, { max: 200 }]}><Input maxLength={200} disabled={editor?.kind === 'restore'} /></Form.Item><Form.Item name="folder_id" label="Carpeta de destino" rules={[{ required: true }]}><Select options={folderOptions(folders).filter((option) => option.value)} showSearch optionFilterProp="label" onChange={(id) => {
            const defaults = folders.find((folder) => folder.id === id)?.role_codes || ['ADMIN']
            form.setFieldValue('role_codes', (editor?.record.role_codes || []).filter((role) => defaults.includes(role)))
          }} /></Form.Item></>}
        <Form.Item name="description" label="Descripción"><Input.TextArea maxLength={2000} rows={3} disabled={editor?.kind === 'restore'} /></Form.Item>
      <Form.Item name="role_codes" label={editor?.kind === 'folder' ? 'Roles predeterminados de lectura' : 'Roles de lectura'}><Select mode="multiple" options={DOCUMENT_ROLES} /></Form.Item>
      <Alert type="info" showIcon message={editor?.kind === 'folder' ? 'Los roles de la carpeta se copiarán únicamente a documentos nuevos. Cambiarlos no modifica los documentos existentes.' : 'El destino y los permisos se revisarán antes de confirmar. La administración es exclusiva de ADMIN; la lectura de publicaciones autoriza fragmentos y original completo.'} style={{ marginBottom: 20 }} />
        <Space><Button onClick={() => setEditor(null)} disabled={working}>Cancelar</Button><Button type="primary" htmlType="submit" loading={working}>{editor?.kind === 'folder' ? 'Guardar' : 'Revisar cambios'}</Button></Space>
      </Form>
    </Modal>
  </div>
}
