/* eslint-disable react-hooks/exhaustive-deps */
import { EyeOutlined, PlusOutlined, SearchOutlined } from '@ant-design/icons'
import { Alert, App as AntdApp, Button, Descriptions, Drawer, Form, Input, InputNumber, Modal, Row, Col, Select, Switch, Table, Tag, Typography } from 'antd'
import { useCallback, useEffect, useMemo, useState } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'

import { apiClient } from '../../api/client'
import { useAuth } from '../../auth/AuthProvider'
import { FORM_COMMON_PROPS, FORM_DRAWER_SUBMIT_PROPS } from '../../components/forms/formConfig'
import { applyFormApiError } from '../../components/forms/formErrorUtils'
import { FormProcessAlert } from '../../components/forms/FormProcessAlert'
import { MOTIVO_ENTRADA_ITEM_OPTIONS } from './boutiqueConstants'

export function BoutiqueEntriesPage() {
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
  const location = useLocation()
  const navigate = useNavigate()

  const canCreate = user?.permissions?.includes('boutique_entries:create')
  const canChangeStatus = user?.permissions?.includes('boutique_entries:update_status')

  const selectedItemId = Form.useWatch('item_id', form)
  const selectedItem = items.find((item) => item.id === selectedItemId)

  const loadReferences = useCallback(async () => {
    const [itemsResponse, providersResponse] = await Promise.all([
      apiClient.get('/boutique/items', { params: { is_active: true } }),
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
      const response = await apiClient.get('/boutique/entries', { params })
      setEntries(response.data)
    } catch (requestError) {
      setError(requestError.response?.data?.detail || 'No fue posible cargar las entradas de boutique.')
    } finally {
      setLoading(false)
    }
  }, [filters])

  useEffect(() => {
    Promise.all([loadReferences(), loadEntries()]).catch(() => {
      setError('No fue posible cargar la información inicial de entradas boutique.')
      setLoading(false)
    })
  }, [])

  useEffect(() => {
    loadEntries()
  }, [filters.search, filters.item_id, filters.is_active])

  useEffect(() => {
    if (!location.state?.prefillItemId || !items.length || !canCreate) return
    form.resetFields()
    form.setFieldsValue({
      item_id: location.state.prefillItemId,
      quantity: 1,
      unit_cost: selectedItem?.purchase_price || 0,
      reason: 'entrada_stock',
    })
    setFormError(null)
    setDrawerOpen(true)
    navigate(location.pathname, { replace: true, state: null })
  }, [location.state, items, canCreate])

  const openCreate = () => {
    form.resetFields()
    form.setFieldsValue({ quantity: 1, unit_cost: 0, reason: 'entrada_stock' })
    setFormError(null)
    setDrawerOpen(true)
  }

  const openView = async (record) => {
    try {
      const response = await apiClient.get(`/boutique/entries/${record.id}`)
      setViewingEntry(response.data)
    } catch (requestError) {
      message.error(requestError.response?.data?.detail || 'No fue posible cargar la entrada.')
    }
  }

  const handleSubmit = async (values) => {
    setSaving(true)
    setFormError(null)
    try {
      await apiClient.post('/boutique/entries', values)
      message.success('Se registró la entrada boutique correctamente.')
      setDrawerOpen(false)
      form.resetFields()
      await Promise.all([loadEntries(), loadReferences()])
    } catch (requestError) {
      const resolved = applyFormApiError(form, requestError, {
        messageFieldMap: [
          { test: /producto boutique no encontrado/i, field: 'item_id' },
          { test: /proveedor.*deshabilitado/i, field: 'provider_id' },
        ],
        fallbackGlobalMessage: 'No fue posible registrar la entrada boutique.',
      })
      setFormError(resolved.globalMessage)
    } finally {
      setSaving(false)
    }
  }

  const handleStatusChange = async (record, checked) => {
    try {
      await apiClient.patch(`/boutique/entries/${record.id}/status`, { is_active: checked })
      message.success(`Entrada ${checked ? 'activada' : 'desactivada'} correctamente.`)
      await Promise.all([loadEntries(), loadReferences()])
    } catch (requestError) {
      message.error(requestError.response?.data?.detail || 'No fue posible cambiar el estado de la entrada.')
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
    { title: 'Producto', key: 'item', render: (_, record) => `${record.item.code} - ${record.item.name}` },
    { title: 'Proveedor', dataIndex: 'provider_name', key: 'provider_name', render: (value) => value || 'SIN PROVEEDOR' },
    { title: 'Cantidad', dataIndex: 'quantity', key: 'quantity' },
    { title: 'Costo unitario', dataIndex: 'unit_cost', key: 'unit_cost', render: (value) => `Bs. ${value}` },
    { title: 'Motivo', dataIndex: 'reason', key: 'reason', render: (value) => MOTIVO_ENTRADA_ITEM_OPTIONS.find((option) => option.value === value)?.label || value },
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
          <Typography.Title level={2} style={{ margin: 0 }}>Entradas Boutique</Typography.Title>
          <Typography.Paragraph type="secondary" style={{ marginBottom: 0 }}>
            Registra nuevas existencias para productos boutique ya creados y actualiza su costo base.
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
            <Select allowClear showSearch optionFilterProp="label" placeholder="Filtrar por producto" options={itemOptions} value={filters.item_id} onChange={(value) => setFilters((current) => ({ ...current, item_id: value }))} style={{ width: '100%' }} />
          </Col>
          <Col xs={24} md={6}>
            <Select allowClear placeholder="Estado" value={filters.is_active} onChange={(value) => setFilters((current) => ({ ...current, is_active: value }))} options={[{ label: 'Activas', value: true }, { label: 'Inactivas', value: false }]} style={{ width: '100%' }} />
          </Col>
        </Row>
      </div>

      {error ? <Alert type="error" showIcon message={error} style={{ marginBottom: 16 }} /> : null}

      <Table className="glass-panel" rowKey="id" columns={columns} dataSource={entries} loading={loading} pagination={{ pageSize: 8 }} scroll={{ x: 'max-content' }} />

      <Drawer
        title="Registrar Entrada Boutique"
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
        <FormProcessAlert message={formError} title="No fue posible registrar la entrada boutique." />
        <Form {...FORM_COMMON_PROPS} form={form} onFinish={handleSubmit}>
          {selectedItem ? (
            <Alert
              type="info"
              showIcon
              style={{ marginBottom: 16 }}
              message={`${selectedItem.code} - ${selectedItem.name}`}
              description={`Stock actual: ${selectedItem.stock}. Stock mínimo: ${selectedItem.stock_min}. Precio compra actual: Bs. ${selectedItem.purchase_price}.`}
            />
          ) : null}

          <Row gutter={12}>
            <Col span={12}>
              <Form.Item label="Producto" name="item_id" rules={[{ required: true, message: 'Debe seleccionar el Producto boutique.' }]}>
                <Select showSearch optionFilterProp="label" placeholder="Buscar y seleccionar producto boutique" options={itemOptions} />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item label="Proveedor" name="provider_id">
                <Select allowClear showSearch optionFilterProp="label" placeholder="Seleccionar proveedor si corresponde" options={providerOptions} />
              </Form.Item>
            </Col>
          </Row>

          <Row gutter={12}>
            <Col span={8}>
              <Form.Item
                label="Cantidad"
                name="quantity"
                rules={[{ required: true, message: 'La Cantidad es obligatoria.' }]}
                normalize={(value) => {
                  if (value === null || value === undefined || value === '') return null
                  return value.toString().replace(/[^0-9]/g, '')
                }}
              >
                <InputNumber min={1} precision={0} style={{ width: '100%' }} placeholder="Ej. 1, 2 o 5" />
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item
                label="Costo unitario"
                name="unit_cost"
                rules={[{ required: true, message: 'El Costo Unitario es obligatorio.' }]}
                normalize={(value) => {
                  if (value === null || value === undefined || value === '') return null
                  return value.toString().replace(/[^0-9.]/g, '')
                }}
              >
                <InputNumber min={0} precision={2} prefix="Bs." style={{ width: '100%' }} placeholder="Ej. 120.00" />
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item label="Motivo" name="reason" rules={[{ required: true, message: 'Debe seleccionar el Motivo de entrada.' }]}>
                <Select options={MOTIVO_ENTRADA_ITEM_OPTIONS} placeholder="Seleccionar motivo de entrada" />
              </Form.Item>
            </Col>
          </Row>

          <Row gutter={12}>
            <Col span={12}>
              <Form.Item label="Documento de referencia" name="document_reference" normalize={(value) => (value || '').toUpperCase()}>
                <Input placeholder="Ej. FACTURA, RECIBO O GUÍA DE COMPRA" />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item label="Observaciones" name="observations" normalize={(value) => (value || '').toUpperCase()}>
                <Input.TextArea rows={2} placeholder="Ej. INGRESO DE NUEVA COLECCIÓN O AJUSTE POR COMPRA LOCAL" />
              </Form.Item>
            </Col>
          </Row>

          <Button {...FORM_DRAWER_SUBMIT_PROPS} loading={saving}>Registrar entrada</Button>
        </Form>
      </Drawer>

      <Modal
        title="Detalle de Entrada Boutique"
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
            <Descriptions.Item label="Producto">{`${viewingEntry.item.code} - ${viewingEntry.item.name}`}</Descriptions.Item>
            <Descriptions.Item label="Tipo">{viewingEntry.item.type_name}</Descriptions.Item>
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
            <Descriptions.Item label="Motivo">{MOTIVO_ENTRADA_ITEM_OPTIONS.find((option) => option.value === viewingEntry.reason)?.label || viewingEntry.reason}</Descriptions.Item>
            <Descriptions.Item label="Documento de referencia">{viewingEntry.document_reference || 'SIN DOCUMENTO'}</Descriptions.Item>
            <Descriptions.Item label="Observaciones" span={2}>{viewingEntry.observations || 'SIN OBSERVACIONES'}</Descriptions.Item>
          </Descriptions>
        ) : null}
      </Modal>
    </div>
  )
}
