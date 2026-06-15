/* eslint-disable react-hooks/exhaustive-deps */
import { BgColorsOutlined, EditOutlined, EyeOutlined, PlusOutlined, SearchOutlined } from '@ant-design/icons'
import { Alert, App as AntdApp, Button, Descriptions, Drawer, Form, Input, InputNumber, Modal, Row, Col, Select, Switch, Table, Tag, Typography } from 'antd'
import { useCallback, useEffect, useMemo, useState } from 'react'

import { apiClient } from '../../api/client'
import { useAuth } from '../../auth/AuthProvider'
import { FORM_COMMON_PROPS, FORM_DRAWER_SUBMIT_PROPS } from '../../components/forms/formConfig'
import { applyFormApiError } from '../../components/forms/formErrorUtils'
import { FormProcessAlert } from '../../components/forms/FormProcessAlert'
import { labelFromOptions, UNIDAD_MEDIDA_OPTIONS, getCategoryColor } from './workshopConstants'
import { ColorPickerModal, COLOR_MAP } from '../boutique/ColorPickerModal'

export function WorkshopInventoryPage() {
  const [items, setItems] = useState([])
  const [types, setTypes] = useState([])
  const [providers, setProviders] = useState([])
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState(null)
  const [formError, setFormError] = useState(null)
  const [drawerOpen, setDrawerOpen] = useState(false)
  const [editingItem, setEditingItem] = useState(null)
  const [viewingItem, setViewingItem] = useState(null)
  const [filters, setFilters] = useState({ search: '', type_id: undefined, is_active: undefined, low_stock: false })
  const [colorModalOpen, setColorModalOpen] = useState(false)
  const [form] = Form.useForm()
  const selectedColor = Form.useWatch('color', form)
  const { message } = AntdApp.useApp()
  const { user } = useAuth()

  const canCreate = user?.permissions?.includes('workshop_inventory:create')
  const canUpdate = user?.permissions?.includes('workshop_inventory:update')
  const canChangeStatus = user?.permissions?.includes('workshop_inventory:update_status')

  const loadReferences = useCallback(async () => {
    const [typesResponse, providersResponse] = await Promise.all([
      apiClient.get('/taller/types'),
      apiClient.get('/boutique/proveedores', { params: { is_active: true } }),
    ])
    setTypes(typesResponse.data)
    setProviders(providersResponse.data)
  }, [])

  const loadItems = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const params = {}
      if (filters.search) params.search = filters.search
      if (filters.type_id) params.type_id = filters.type_id
      if (filters.is_active !== undefined) params.is_active = filters.is_active
      if (filters.low_stock) params.low_stock = true
      const response = await apiClient.get('/taller/inventory', { params })
      setItems(response.data)
    } catch (requestError) {
      setError(requestError.response?.data?.detail || 'No fue posible cargar el inventario del taller.')
    } finally {
      setLoading(false)
    }
  }, [filters])

  useEffect(() => {
    Promise.all([loadReferences(), loadItems()]).catch(() => {
      setError('No fue posible cargar la información inicial del inventario del taller.')
      setLoading(false)
    })
  }, [])

  useEffect(() => {
    loadItems()
  }, [filters.search, filters.type_id, filters.is_active, filters.low_stock])

  const typeOptions = useMemo(() => types.map((type) => ({ label: type.nombre, value: type.id })), [types])
  const providerOptions = useMemo(
    () =>
      providers.map((provider) => ({
        label: provider.nombre_comercial ? `${provider.full_name} - ${provider.nombre_comercial}` : provider.full_name,
        value: provider.id,
      })),
    [providers],
  )

  const openCreate = () => {
    setEditingItem(null)
    setFormError(null)
    form.resetFields()
    form.setFieldsValue({ reference_cost: 0, stock: 0, stock_min: 0, unit_measure: 'metro' })
    setDrawerOpen(true)
  }

  const openEdit = async (record) => {
    try {
      const response = await apiClient.get(`/taller/inventory/${record.id}`)
      const item = response.data
      setEditingItem(item)
      setFormError(null)
      form.setFieldsValue({
        type_id: item.type.id,
        provider_id: item.provider?.id,
        code: item.code,
        name: item.name,
        color: item.color,
        length: item.length,
        width: item.width,
        material: item.material,
        description: item.description,
        reference_cost: item.reference_cost,
        stock: item.stock,
        unit_measure: item.unit_measure,
        stock_min: item.stock_min,
        observations: item.observations,
      })
      setDrawerOpen(true)
    } catch (requestError) {
      message.error(requestError.response?.data?.detail || 'No fue posible cargar el material del taller.')
    }
  }

  const openView = async (record) => {
    try {
      const response = await apiClient.get(`/taller/inventory/${record.id}`)
      setViewingItem(response.data)
    } catch (requestError) {
      message.error(requestError.response?.data?.detail || 'No fue posible cargar el detalle del material.')
    }
  }

  const handleSubmit = async (values) => {
    setSaving(true)
    setFormError(null)
    try {
      if (editingItem) {
        await apiClient.patch(`/taller/inventory/${editingItem.id}`, values)
        message.success('Se guardaron los cambios del material correctamente.')
      } else {
        await apiClient.post('/taller/inventory', values)
        message.success('Se creó el material del taller correctamente.')
      }
      setDrawerOpen(false)
      setEditingItem(null)
      form.resetFields()
      await Promise.all([loadItems(), loadReferences()])
    } catch (requestError) {
      const resolved = applyFormApiError(form, requestError, {
        fallbackGlobalMessage: 'No fue posible guardar la información del material de taller.',
      })
      setFormError(resolved.globalMessage)
    } finally {
      setSaving(false)
    }
  }

  const handleStatusChange = async (record, checked) => {
    try {
      await apiClient.patch(`/taller/inventory/${record.id}/status`, { is_active: checked })
      message.success(`Material ${checked ? 'activado' : 'desactivado'} correctamente.`)
      await loadItems()
    } catch (requestError) {
      message.error(requestError.response?.data?.detail || 'No fue posible cambiar el estado del material.')
    }
  }

  const columns = [
    { title: 'Código', dataIndex: 'code', key: 'code' },
    { title: 'Nombre', dataIndex: 'name', key: 'name' },
    { title: 'Tipo', dataIndex: 'type_name', key: 'type_name', render: (value) => <Tag color={getCategoryColor(value)}>{value}</Tag> },
    { title: 'Color', dataIndex: 'color', key: 'color' },
    { title: 'Material', dataIndex: 'material', key: 'material', render: (value) => value || 'SIN DATO' },
    { title: 'Proveedor', dataIndex: 'provider_name', key: 'provider_name', render: (value) => value || 'SIN PROVEEDOR' },
    { title: 'Stock', key: 'stock', render: (_, record) => <span>{record.stock} {record.is_low_stock ? ' - STOCK BAJO' : ''}</span> },
    { title: 'Unidad', dataIndex: 'unit_measure', key: 'unit_measure', render: (value) => labelFromOptions(UNIDAD_MEDIDA_OPTIONS, value) },
    {
      title: 'Estado',
      key: 'estado',
      render: (_, record) =>
        canChangeStatus ? (
          <Switch checked={record.is_active} checkedChildren="Activo" unCheckedChildren="Inactivo" onChange={(checked) => handleStatusChange(record, checked)} />
        ) : (
          <Tag color={record.is_active ? 'green' : 'default'}>{record.is_active ? 'ACTIVO' : 'INACTIVO'}</Tag>
        ),
    },
    {
      title: 'Acciones',
      key: 'acciones',
      render: (_, record) => (
        <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
          <Button icon={<EyeOutlined />} onClick={() => openView(record)}>Ver</Button>
          {canUpdate ? <Button icon={<EditOutlined />} onClick={() => openEdit(record)}>Editar</Button> : null}
        </div>
      ),
    },
  ]

  return (
    <div>
      <div className="page-header">
        <div>
          <Typography.Title level={2} style={{ margin: 0 }}>Inventario Taller</Typography.Title>
          <Typography.Paragraph type="secondary" style={{ marginBottom: 0 }}>
            Gestiona materiales del taller con unidad de medida, stock y proveedor de referencia.
          </Typography.Paragraph>
        </div>
        {canCreate ? <Button type="primary" icon={<PlusOutlined />} onClick={openCreate}>Nuevo material</Button> : null}
      </div>

      <div className="glass-panel boutique-filter-bar">
        <Row gutter={[12, 12]}>
          <Col xs={24} md={10}>
            <Input allowClear prefix={<SearchOutlined />} placeholder="Buscar por código, nombre, color o material" value={filters.search} onChange={(event) => setFilters((current) => ({ ...current, search: event.target.value }))} />
          </Col>
          <Col xs={24} md={6}>
            <Select allowClear placeholder="Filtrar por tipo" options={typeOptions} value={filters.type_id} onChange={(value) => setFilters((current) => ({ ...current, type_id: value }))} style={{ width: '100%' }} />
          </Col>
          <Col xs={24} md={4}>
            <Select allowClear placeholder="Estado" value={filters.is_active} onChange={(value) => setFilters((current) => ({ ...current, is_active: value }))} options={[{ label: 'Activos', value: true }, { label: 'Inactivos', value: false }]} style={{ width: '100%' }} />
          </Col>
          <Col xs={24} md={4}>
            <Switch checked={filters.low_stock} checkedChildren="Stock bajo" unCheckedChildren="Todos" onChange={(checked) => setFilters((current) => ({ ...current, low_stock: checked }))} />
          </Col>
        </Row>
      </div>

      {error ? <Alert type="error" showIcon message={error} style={{ marginBottom: 16 }} /> : null}
      <Table className="glass-panel" rowKey="id" columns={columns} dataSource={items} loading={loading} pagination={{ pageSize: 8 }} scroll={{ x: 'max-content' }} />

      <Drawer
        title={editingItem ? 'Editar Material Taller' : 'Crear Material Taller'}
        width={820}
        open={drawerOpen}
        onClose={() => {
          setDrawerOpen(false)
          setEditingItem(null)
          setFormError(null)
          form.resetFields()
        }}
        destroyOnClose
        maskClosable={false}
      >
        <FormProcessAlert message={formError} title={editingItem ? 'No fue posible actualizar el material.' : 'No fue posible crear el material.'} />
        <Form {...FORM_COMMON_PROPS} form={form} onFinish={handleSubmit}>
          <Row gutter={12}>
            <Col span={12}>
              <Form.Item label="Tipo" name="type_id" rules={[{ required: true, message: 'Debe seleccionar el Tipo de inventario taller.' }]}>
                <Select options={typeOptions} placeholder="Seleccionar tipo de inventario taller" />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item label="Proveedor" name="provider_id">
                <Select allowClear showSearch optionFilterProp="label" placeholder="Seleccionar proveedor si corresponde" options={providerOptions} />
              </Form.Item>
            </Col>
          </Row>
          <Row gutter={12}>
            <Col span={12}>
              <Form.Item label="Código" name="code" rules={[{ required: true, message: 'El Código del material es obligatorio.' }]} normalize={(value) => (value || '').replace(/[^a-zA-Z0-9-]/g, '').toUpperCase()}>
                <Input placeholder="Ej. TEL-001, ENC-002 O INS-003" />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item label="Nombre" name="name" rules={[{ required: true, message: 'El Nombre del material es obligatorio.' }]} normalize={(value) => (value || '').toUpperCase()}>
                <Input placeholder="Introducir el nombre del material del taller" />
              </Form.Item>
            </Col>
          </Row>
          <Row gutter={12}>
            <Col span={12}>
              <Form.Item label="Color" name="color" rules={[{ required: true, message: 'El Color del material es obligatorio.' }]}>
                <div
                  onClick={() => setColorModalOpen(true)}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: 10,
                    border: '1px solid #d9d9d9',
                    borderRadius: 8,
                    padding: '6px 12px',
                    cursor: 'pointer',
                    background: '#fff',
                    transition: 'border-color 0.2s',
                    minHeight: 40,
                  }}
                  onMouseEnter={(e) => (e.currentTarget.style.borderColor = '#8f3d2e')}
                  onMouseLeave={(e) => (e.currentTarget.style.borderColor = '#d9d9d9')}
                >
                  {selectedColor ? (
                    <>
                      <div
                        style={{
                          width: 26,
                          height: 26,
                          borderRadius: 6,
                          background: COLOR_MAP[selectedColor] || '#e0e0e0',
                          border: '1.5px solid rgba(0,0,0,0.15)',
                          flexShrink: 0,
                        }}
                      />
                      <span style={{ fontWeight: 500 }}>{selectedColor}</span>
                    </>
                  ) : (
                    <span style={{ color: '#aaa' }}>
                      <BgColorsOutlined style={{ marginRight: 6 }} />
                      Seleccionar color
                    </span>
                  )}
                  <Button
                    size="small"
                    type="link"
                    style={{ marginLeft: 'auto', fontSize: 12 }}
                    onClick={(e) => {
                      e.stopPropagation()
                      setColorModalOpen(true)
                    }}
                  >
                    Cambiar
                  </Button>
                </div>
              </Form.Item>

              <ColorPickerModal
                open={colorModalOpen}
                onSelect={(colorName) => {
                  form.setFieldValue('color', colorName)
                  form.validateFields(['color'])
                  setColorModalOpen(false)
                }}
                onCancel={() => setColorModalOpen(false)}
              />
            </Col>
            <Col span={12}>
              <Form.Item label="Material" name="material" normalize={(value) => (value || '').toUpperCase()}>
                <Input placeholder="Ej. TUL, SATÉN, ENCAJE O FORRO" />
              </Form.Item>
            </Col>
          </Row>
          <Row gutter={12}>
            <Col span={6}>
              <Form.Item label="Largo" name="length" normalize={(value) => value === null || value === undefined || value === '' ? null : value.toString().replace(/[^0-9.]/g, '')}>
                <InputNumber min={0} precision={2} style={{ width: '100%' }} placeholder="Ej. 5.00" />
              </Form.Item>
            </Col>
            <Col span={6}>
              <Form.Item label="Ancho" name="width" normalize={(value) => value === null || value === undefined || value === '' ? null : value.toString().replace(/[^0-9.]/g, '')}>
                <InputNumber min={0} precision={2} style={{ width: '100%' }} placeholder="Ej. 1.50" />
              </Form.Item>
            </Col>
            <Col span={6}>
              <Form.Item label="Costo referencia" name="reference_cost" rules={[{ required: true, message: 'El Costo de referencia es obligatorio.' }]} normalize={(value) => value === null || value === undefined || value === '' ? null : value.toString().replace(/[^0-9.]/g, '')}>
                <InputNumber min={0} precision={2} prefix="Bs." style={{ width: '100%' }} placeholder="Ej. 35.00" />
              </Form.Item>
            </Col>
            <Col span={6}>
              <Form.Item label="Unidad" name="unit_measure" rules={[{ required: true, message: 'Debe seleccionar la Unidad de Medida.' }]}>
                <Select options={UNIDAD_MEDIDA_OPTIONS} placeholder="Seleccionar unidad de medida" />
              </Form.Item>
            </Col>
          </Row>
          <Row gutter={12}>
            <Col span={12}>
              <Form.Item label="Stock" name="stock" rules={[{ required: true, message: 'El Stock es obligatorio.' }]} normalize={(value) => value === null || value === undefined || value === '' ? null : value.toString().replace(/[^0-9.]/g, '')}>
                <InputNumber min={0} precision={2} style={{ width: '100%' }} placeholder="Ej. 10.00" />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item label="Stock mínimo" name="stock_min" rules={[{ required: true, message: 'El Stock mínimo es obligatorio.' }]} normalize={(value) => value === null || value === undefined || value === '' ? null : value.toString().replace(/[^0-9.]/g, '')}>
                <InputNumber min={0} precision={2} style={{ width: '100%' }} placeholder="Ej. 2.00" />
              </Form.Item>
            </Col>
          </Row>
          <Form.Item label="Descripción" name="description" normalize={(value) => (value || '').toUpperCase()}>
            <Input.TextArea rows={2} placeholder="Ej. MATERIAL BASE PARA CORPIÑOS, FALDAS O FORROS INTERNOS" />
          </Form.Item>
          <Form.Item label="Observaciones" name="observations" normalize={(value) => (value || '').toUpperCase()}>
            <Input.TextArea rows={2} placeholder="Ej. MATERIAL DELICADO O REQUIERE CORTE EN MESA AMPLIA" />
          </Form.Item>
          <Button {...FORM_DRAWER_SUBMIT_PROPS} loading={saving}>{editingItem ? 'Guardar cambios' : 'Crear material'}</Button>
        </Form>
      </Drawer>

      <Modal
        title="Detalle Material Taller"
        open={!!viewingItem}
        onCancel={() => setViewingItem(null)}
        maskClosable={false}
        footer={[<Button key="close" onClick={() => setViewingItem(null)}>Cerrar</Button>]}
        width={800}
      >
        {viewingItem ? (
          <Descriptions bordered column={2} size="small" layout="vertical">
            <Descriptions.Item label="Tipo"><Tag color={getCategoryColor(viewingItem.type.nombre)}>{viewingItem.type.nombre}</Tag></Descriptions.Item>
            <Descriptions.Item label="Código">{viewingItem.code}</Descriptions.Item>
            <Descriptions.Item label="Nombre">{viewingItem.name}</Descriptions.Item>
            <Descriptions.Item label="Color">{viewingItem.color}</Descriptions.Item>
            <Descriptions.Item label="Material">{viewingItem.material || 'SIN DATO'}</Descriptions.Item>
            <Descriptions.Item label="Proveedor">
              {viewingItem.provider ? (viewingItem.provider.nombre_comercial ? `${viewingItem.provider.full_name} - ${viewingItem.provider.nombre_comercial}` : viewingItem.provider.full_name) : 'SIN PROVEEDOR'}
            </Descriptions.Item>
            <Descriptions.Item label="Largo">{viewingItem.length ?? 'SIN DATO'}</Descriptions.Item>
            <Descriptions.Item label="Ancho">{viewingItem.width ?? 'SIN DATO'}</Descriptions.Item>
            <Descriptions.Item label="Costo referencia">Bs. {viewingItem.reference_cost}</Descriptions.Item>
            <Descriptions.Item label="Stock">{viewingItem.stock}</Descriptions.Item>
            <Descriptions.Item label="Unidad">{labelFromOptions(UNIDAD_MEDIDA_OPTIONS, viewingItem.unit_measure)}</Descriptions.Item>
            <Descriptions.Item label="Stock mínimo">{viewingItem.stock_min}</Descriptions.Item>
            <Descriptions.Item label="Estado" span={2}>{viewingItem.is_active ? 'ACTIVO' : 'INACTIVO'}</Descriptions.Item>
            <Descriptions.Item label="Descripción" span={2}>{viewingItem.description || 'SIN DESCRIPCIÓN'}</Descriptions.Item>
            <Descriptions.Item label="Observaciones" span={2}>{viewingItem.observations || 'SIN OBSERVACIONES'}</Descriptions.Item>
          </Descriptions>
        ) : null}
      </Modal>
    </div>
  )
}
