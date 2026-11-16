/* eslint-disable react-hooks/exhaustive-deps */
import { EyeOutlined, PlusOutlined, SearchOutlined } from '@ant-design/icons'
import { Alert, App as AntdApp, Button, Descriptions, Drawer, Form, Input, InputNumber, Modal, Row, Col, Select, Switch, Table, Tag, Typography } from 'antd'
import { useCallback, useEffect, useMemo, useState } from 'react'

import { apiClient } from '../../api/client'
import { useAuth } from '../../auth/AuthProvider'
import { FORM_COMMON_PROPS, FORM_DRAWER_SUBMIT_PROPS } from '../../components/forms/formConfig'
import { applyFormApiError } from '../../components/forms/formErrorUtils'
import { FormProcessAlert } from '../../components/forms/FormProcessAlert'
import { ReportSummaryStrip } from '../../components/reports/ReportSummaryStrip'
import { useListingSummary } from '../../components/reports/useListingSummary'
import { labelFromOptions, MOTIVO_ENTRADA_TALLER_OPTIONS, UNIDAD_MEDIDA_OPTIONS, getCategoryColor } from './workshopConstants'

export function WorkshopEntriesPage() {
  const [entries, setEntries] = useState([])
  const [items, setItems] = useState([])
  const [providers, setProviders] = useState([])
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState(null)
  const [formError, setFormError] = useState(null)
  const [drawerOpen, setDrawerOpen] = useState(false)
  const [viewingEntry, setViewingEntry] = useState(null)
  const [filters, setFilters] = useState({ search: '', item_id: undefined, is_active: undefined })
  const [form] = Form.useForm()
  const { message } = AntdApp.useApp()
  const { user } = useAuth()

  const canCreate = user?.permissions?.includes('workshop_entries:create')
  const canChangeStatus = user?.permissions?.includes('workshop_entries:update_status')
  const { summary, loading: summaryLoading } = useListingSummary('/taller/entries/resumen', filters)

  const selectedItemId = Form.useWatch('item_id', form)
  const selectedItem = items.find((item) => item.id === selectedItemId)

  const loadReferences = useCallback(async () => {
    const [itemsResponse, providersResponse] = await Promise.all([
      apiClient.get('/taller/inventory', { params: { is_active: true } }),
      apiClient.get('/boutique/proveedores', { params: { is_active: true } }),
    ])
    setItems(itemsResponse.data)
    setProviders(providersResponse.data)
  }, [])

  const loadEntries = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const params = {}
      if (filters.search) params.search = filters.search
      if (filters.item_id) params.item_id = filters.item_id
      if (filters.is_active !== undefined) params.is_active = filters.is_active
      const response = await apiClient.get('/taller/entries', { params })
      setEntries(response.data)
    } catch (requestError) {
      setError(requestError.response?.data?.detail || 'No fue posible cargar las entradas del taller.')
    } finally {
      setLoading(false)
    }
  }, [filters])

  useEffect(() => {
    Promise.all([loadReferences(), loadEntries()]).catch(() => {
      setError('No fue posible cargar la información inicial de entradas del taller.')
      setLoading(false)
    })
  }, [])

  useEffect(() => {
    loadEntries()
  }, [filters.search, filters.item_id, filters.is_active])

  useEffect(() => {
    if (!selectedItem) return
    form.setFieldValue('unit_measure', selectedItem.unit_measure)
    if (form.getFieldValue('unit_cost') === undefined) {
      form.setFieldValue('unit_cost', selectedItem.reference_cost ?? 0)
    }
  }, [selectedItemId, selectedItem, form])

  const openCreate = () => {
    form.resetFields()
    form.setFieldsValue({
      quantity: 1,
      unit_cost: 0,
      reason: 'entrada_stock',
    })
    setFormError(null)
    setDrawerOpen(true)
  }

  const openView = async (record) => {
    try {
      const response = await apiClient.get(`/taller/entries/${record.id}`)
      setViewingEntry(response.data)
    } catch (requestError) {
      message.error(requestError.response?.data?.detail || 'No fue posible cargar la entrada del taller.')
    }
  }

  const handleSubmit = async (values) => {
    setSaving(true)
    setFormError(null)
    try {
      await apiClient.post('/taller/entries', values)
      message.success('Se registró la entrada del taller correctamente.')
      setDrawerOpen(false)
      form.resetFields()
      await Promise.all([loadEntries(), loadReferences()])
    } catch (requestError) {
      const resolved = applyFormApiError(form, requestError, {
        messageFieldMap: [
          { test: /material de taller no encontrado/i, field: 'item_id' },
          { test: /proveedor.*deshabilitado/i, field: 'provider_id' },
          { test: /unidad de medida.*entrada/i, field: 'unit_measure' },
        ],
        fallbackGlobalMessage: 'No fue posible registrar la entrada del taller.',
      })
      setFormError(resolved.globalMessage)
    } finally {
      setSaving(false)
    }
  }

  const handleStatusChange = async (record, checked) => {
    try {
      await apiClient.patch(`/taller/entries/${record.id}/status`, { is_active: checked })
      message.success(`Entrada ${checked ? 'activada' : 'desactivada'} correctamente.`)
      await Promise.all([loadEntries(), loadReferences()])
    } catch (requestError) {
      message.error(requestError.response?.data?.detail || 'No fue posible cambiar el estado de la entrada del taller.')
    }
  }

  const itemOptions = useMemo(
    () => items.map((item) => ({ label: `${item.code} - ${item.name}`, value: item.id })),
    [items],
  )

  const providerOptions = useMemo(
    () =>
      providers.map((provider) => ({
        label: provider.nombre_comercial ? `${provider.full_name} - ${provider.nombre_comercial}` : provider.full_name,
        value: provider.id,
      })),
    [providers],
  )

  const columns = [
    { title: 'Fecha', dataIndex: 'fecha', key: 'fecha', render: (value) => new Date(value).toLocaleString() },
    { title: 'Material', key: 'item', render: (_, record) => `${record.item.code} - ${record.item.name}` },
    { title: 'Proveedor', dataIndex: 'provider_name', key: 'provider_name', render: (value) => value || 'SIN PROVEEDOR' },
    { title: 'Cantidad', dataIndex: 'quantity', key: 'quantity' },
    { title: 'Unidad', dataIndex: 'unit_measure', key: 'unit_measure', render: (value) => labelFromOptions(UNIDAD_MEDIDA_OPTIONS, value) },
    { title: 'Costo unitario', dataIndex: 'unit_cost', key: 'unit_cost', render: (value) => `Bs. ${value}` },
    { title: 'Motivo', dataIndex: 'reason', key: 'reason', render: (value) => labelFromOptions(MOTIVO_ENTRADA_TALLER_OPTIONS, value) || value },
    {
      title: 'Estado',
      key: 'estado',
      render: (_, record) =>
        canChangeStatus ? (
          <Switch checked={record.is_active} checkedChildren="Activa" unCheckedChildren="Inactiva" onChange={(checked) => handleStatusChange(record, checked)} />
        ) : (
          <Tag color={record.is_active ? 'green' : 'default'}>{record.is_active ? 'ACTIVA' : 'INACTIVA'}</Tag>
        ),
    },
    {
      title: 'Acciones',
      key: 'acciones',
      render: (_, record) => (
        <Button icon={<EyeOutlined />} onClick={() => openView(record)}>
          Ver
        </Button>
      ),
    },
  ]

  return (
    <div>
      <div className="page-header">
        <div>
          <Typography.Title level={2} style={{ margin: 0 }}>Entradas Taller</Typography.Title>
          <Typography.Paragraph type="secondary" style={{ marginBottom: 0 }}>
            Registra ingresos de materiales del taller y actualiza su costo de referencia.
          </Typography.Paragraph>
        </div>
        {canCreate ? <Button type="primary" icon={<PlusOutlined />} onClick={openCreate}>Nueva entrada</Button> : null}
      </div>

      <div className="glass-panel boutique-filter-bar">
        <Row gutter={[12, 12]}>
          <Col xs={24} md={10}>
            <Input allowClear prefix={<SearchOutlined />} placeholder="Buscar por código, nombre o proveedor" value={filters.search} onChange={(event) => setFilters((current) => ({ ...current, search: event.target.value }))} />
          </Col>
          <Col xs={24} md={8}>
            <Select allowClear showSearch optionFilterProp="label" placeholder="Filtrar por material" options={itemOptions} value={filters.item_id} onChange={(value) => setFilters((current) => ({ ...current, item_id: value }))} style={{ width: '100%' }} />
          </Col>
          <Col xs={24} md={6}>
            <Select allowClear placeholder="Estado" value={filters.is_active} onChange={(value) => setFilters((current) => ({ ...current, is_active: value }))} options={[{ label: 'Activas', value: true }, { label: 'Inactivas', value: false }]} style={{ width: '100%' }} />
          </Col>
        </Row>
      </div>

      {error ? <Alert type="error" showIcon message={error} style={{ marginBottom: 16 }} /> : null}
      <ReportSummaryStrip summary={summary} loading={summaryLoading} />

      <Table className="glass-panel" rowKey="id" columns={columns} dataSource={entries} loading={loading} pagination={{ pageSize: 8 }} scroll={{ x: 'max-content' }} />

      <Drawer
        title="Registrar Entrada Taller"
        width={760}
        open={drawerOpen}
        onClose={() => {
          setDrawerOpen(false)
          setFormError(null)
          form.resetFields()
        }}
        destroyOnClose
        maskClosable={false}
      >
        <FormProcessAlert message={formError} title="No fue posible registrar la entrada del taller." />
        <Form {...FORM_COMMON_PROPS} form={form} onFinish={handleSubmit}>
          {selectedItem ? (
            <Alert
              type="info"
              showIcon
              style={{ marginBottom: 16 }}
              message={`${selectedItem.code} - ${selectedItem.name}`}
              description={`Stock actual: ${selectedItem.stock}. Unidad: ${labelFromOptions(UNIDAD_MEDIDA_OPTIONS, selectedItem.unit_measure)}. Costo referencia actual: Bs. ${selectedItem.reference_cost}.`}
            />
          ) : null}

          <Row gutter={12}>
            <Col span={12}>
              <Form.Item label="Material" name="item_id" rules={[{ required: true, message: 'Debe seleccionar el Material del taller.' }]}>
                <Select showSearch optionFilterProp="label" placeholder="Buscar y seleccionar material del taller" options={itemOptions} />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item label="Proveedor" name="provider_id">
                <Select allowClear showSearch optionFilterProp="label" placeholder="Seleccionar proveedor si corresponde" options={providerOptions} />
              </Form.Item>
            </Col>
          </Row>

          <Row gutter={12}>
            <Col span={6}>
              <Form.Item
                label="Cantidad"
                name="quantity"
                rules={[{ required: true, message: 'La Cantidad es obligatoria.' }]}
                normalize={(value) => {
                  if (value === null || value === undefined || value === '') return null
                  return value.toString().replace(/[^0-9.]/g, '')
                }}
              >
                <InputNumber min={0.01} precision={2} style={{ width: '100%' }} placeholder="Ej. 2.50" />
              </Form.Item>
            </Col>
            <Col span={6}>
              <Form.Item label="Unidad" name="unit_measure" rules={[{ required: true, message: 'La Unidad es obligatoria.' }]}>
                <Select disabled options={UNIDAD_MEDIDA_OPTIONS} placeholder="Unidad del material base" />
              </Form.Item>
            </Col>
            <Col span={6}>
              <Form.Item
                label="Costo unitario"
                name="unit_cost"
                rules={[{ required: true, message: 'El Costo Unitario es obligatorio.' }]}
                normalize={(value) => {
                  if (value === null || value === undefined || value === '') return null
                  return value.toString().replace(/[^0-9.]/g, '')
                }}
              >
                <InputNumber min={0} precision={2} prefix="Bs." style={{ width: '100%' }} placeholder="Ej. 18.50" />
              </Form.Item>
            </Col>
            <Col span={6}>
              <Form.Item label="Motivo" name="reason" rules={[{ required: true, message: 'Debe seleccionar el Motivo de entrada.' }]}>
                <Select options={MOTIVO_ENTRADA_TALLER_OPTIONS} placeholder="Seleccionar motivo de entrada" />
              </Form.Item>
            </Col>
          </Row>

          <Row gutter={12}>
            <Col span={12}>
              <Form.Item label="Documento de referencia" name="document_reference" normalize={(value) => (value || '').toUpperCase()}>
                <Input placeholder="Ej. FACTURA DE COMPRA O DOCUMENTO DE ENTREGA" />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item label="Observaciones" name="observations" normalize={(value) => (value || '').toUpperCase()}>
                <Input.TextArea rows={2} placeholder="Ej. INGRESO DE MATERIAL PARA PRODUCCIÓN DE NUEVA COLECCIÓN" />
              </Form.Item>
            </Col>
          </Row>

          <Button {...FORM_DRAWER_SUBMIT_PROPS} loading={saving}>Registrar entrada</Button>
        </Form>
      </Drawer>

      <Modal
        title="Detalle de Entrada Taller"
        open={!!viewingEntry}
        onCancel={() => setViewingEntry(null)}
        maskClosable={false}
        footer={[<Button key="close" onClick={() => setViewingEntry(null)}>Cerrar</Button>]}
        width={760}
      >
        {viewingEntry ? (
          <Descriptions bordered column={2} size="small" layout="vertical">
            <Descriptions.Item label="Fecha">{new Date(viewingEntry.fecha).toLocaleString()}</Descriptions.Item>
            <Descriptions.Item label="Estado">{viewingEntry.is_active ? 'ACTIVA' : 'INACTIVA'}</Descriptions.Item>
            <Descriptions.Item label="Material">{`${viewingEntry.item.code} - ${viewingEntry.item.name}`}</Descriptions.Item>
            <Descriptions.Item label="Tipo"><Tag color={getCategoryColor(viewingEntry.item.type_name)}>{viewingEntry.item.type_name || 'SIN TIPO'}</Tag></Descriptions.Item>
            <Descriptions.Item label="Unidad">{labelFromOptions(UNIDAD_MEDIDA_OPTIONS, viewingEntry.item.unit_measure)}</Descriptions.Item>
            <Descriptions.Item label="Proveedor">
              {viewingEntry.provider
                ? viewingEntry.provider.nombre_comercial
                  ? `${viewingEntry.provider.full_name} - ${viewingEntry.provider.nombre_comercial}`
                  : viewingEntry.provider.full_name
                : 'SIN PROVEEDOR'}
            </Descriptions.Item>
            <Descriptions.Item label="Registrado por">{viewingEntry.registered_by.full_name}</Descriptions.Item>
            <Descriptions.Item label="Cantidad">{viewingEntry.quantity}</Descriptions.Item>
            <Descriptions.Item label="Costo unitario">Bs. {viewingEntry.unit_cost}</Descriptions.Item>
            <Descriptions.Item label="Motivo">{labelFromOptions(MOTIVO_ENTRADA_TALLER_OPTIONS, viewingEntry.reason) || viewingEntry.reason}</Descriptions.Item>
            <Descriptions.Item label="Documento de referencia" span={2}>{viewingEntry.document_reference || 'SIN DOCUMENTO'}</Descriptions.Item>
            <Descriptions.Item label="Observaciones" span={2}>{viewingEntry.observations || 'SIN OBSERVACIONES'}</Descriptions.Item>
          </Descriptions>
        ) : null}
      </Modal>
    </div>
  )
}
