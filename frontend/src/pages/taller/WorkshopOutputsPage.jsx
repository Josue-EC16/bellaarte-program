/* eslint-disable react-hooks/exhaustive-deps */
import { EyeOutlined, PlusOutlined, SearchOutlined } from '@ant-design/icons'
import { Alert, App as AntdApp, Button, Descriptions, Drawer, Form, Input, InputNumber, Modal, Row, Col, Select, Switch, Table, Tag, Typography } from 'antd'
import { useCallback, useEffect, useMemo, useState } from 'react'

import { apiClient } from '../../api/client'
import { useAuth } from '../../auth/AuthProvider'
import { FORM_COMMON_PROPS, FORM_DRAWER_SUBMIT_PROPS } from '../../components/forms/formConfig'
import { applyFormApiError } from '../../components/forms/formErrorUtils'
import { FormProcessAlert } from '../../components/forms/FormProcessAlert'
import { labelFromOptions, UNIDAD_MEDIDA_OPTIONS, getCategoryColor } from './workshopConstants'

export function WorkshopOutputsPage() {
  const [outputs, setOutputs] = useState([])
  const [items, setItems] = useState([])
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState(null)
  const [formError, setFormError] = useState(null)
  const [drawerOpen, setDrawerOpen] = useState(false)
  const [viewingOutput, setViewingOutput] = useState(null)
  const [filters, setFilters] = useState({ search: '', item_id: undefined, is_active: undefined })
  const [form] = Form.useForm()
  const { message } = AntdApp.useApp()
  const { user } = useAuth()

  const canCreate = user?.permissions?.includes('workshop_outputs:create')
  const canChangeStatus = user?.permissions?.includes('workshop_outputs:update_status')

  const selectedItemId = Form.useWatch('item_id', form)
  const selectedItem = items.find((item) => item.id === selectedItemId)

  const loadItems = useCallback(async () => {
    const response = await apiClient.get('/taller/inventory', { params: { is_active: true } })
    setItems(response.data)
  }, [])

  const loadOutputs = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const params = {}
      if (filters.search) params.search = filters.search
      if (filters.item_id) params.item_id = filters.item_id
      if (filters.is_active !== undefined) params.is_active = filters.is_active
      const response = await apiClient.get('/taller/outputs', { params })
      setOutputs(response.data)
    } catch (requestError) {
      setError(requestError.response?.data?.detail || 'No fue posible cargar las salidas del taller.')
    } finally {
      setLoading(false)
    }
  }, [filters])

  useEffect(() => {
    Promise.all([loadItems(), loadOutputs()]).catch(() => {
      setError('No fue posible cargar la información inicial de salidas del taller.')
      setLoading(false)
    })
  }, [])

  useEffect(() => {
    loadOutputs()
  }, [filters.search, filters.item_id, filters.is_active])

  useEffect(() => {
    if (!selectedItem) return
    form.setFieldValue('unit_measure', selectedItem.unit_measure)
  }, [selectedItemId, selectedItem, form])

  const openCreate = () => {
    form.resetFields()
    form.setFieldsValue({ quantity: 1 })
    setFormError(null)
    setDrawerOpen(true)
  }

  const openView = async (record) => {
    try {
      const response = await apiClient.get(`/taller/outputs/${record.id}`)
      setViewingOutput(response.data)
    } catch (requestError) {
      message.error(requestError.response?.data?.detail || 'No fue posible cargar la salida del taller.')
    }
  }

  const handleSubmit = async (values) => {
    setSaving(true)
    setFormError(null)
    try {
      await apiClient.post('/taller/outputs', values)
      message.success('Se registró la salida del taller correctamente.')
      setDrawerOpen(false)
      form.resetFields()
      await Promise.all([loadOutputs(), loadItems()])
    } catch (requestError) {
      const resolved = applyFormApiError(form, requestError, {
        messageFieldMap: [
          { test: /material de taller no encontrado/i, field: 'item_id' },
          { test: /stock disponible/i, field: 'quantity' },
          { test: /unidad de medida.*salida/i, field: 'unit_measure' },
        ],
        fallbackGlobalMessage: 'No fue posible registrar la salida del taller.',
      })
      setFormError(resolved.globalMessage)
    } finally {
      setSaving(false)
    }
  }

  const handleStatusChange = async (record, checked) => {
    try {
      await apiClient.patch(`/taller/outputs/${record.id}/status`, { is_active: checked })
      message.success(`Salida ${checked ? 'activada' : 'desactivada'} correctamente.`)
      await Promise.all([loadOutputs(), loadItems()])
    } catch (requestError) {
      message.error(requestError.response?.data?.detail || 'No fue posible cambiar el estado de la salida del taller.')
    }
  }

  const itemOptions = useMemo(
    () => items.map((item) => ({ label: `${item.code} - ${item.name}`, value: item.id })),
    [items],
  )

  const columns = [
    { title: 'Fecha', dataIndex: 'fecha', key: 'fecha', render: (value) => new Date(value).toLocaleString() },
    { title: 'Material', key: 'item', render: (_, record) => `${record.item.code} - ${record.item.name}` },
    { title: 'Cantidad', dataIndex: 'quantity', key: 'quantity' },
    { title: 'Unidad', dataIndex: 'unit_measure', key: 'unit_measure', render: (value) => labelFromOptions(UNIDAD_MEDIDA_OPTIONS, value) },
    { title: 'Destino', dataIndex: 'destination', key: 'destination' },
    { title: 'Registrado por', dataIndex: 'registered_by', key: 'registered_by', render: (value) => value || 'SIN USUARIO' },
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
          <Typography.Title level={2} style={{ margin: 0 }}>Salidas Taller</Typography.Title>
          <Typography.Paragraph type="secondary" style={{ marginBottom: 0 }}>
            Registra el consumo o destino de materiales del taller con control de stock.
          </Typography.Paragraph>
        </div>
        {canCreate ? <Button type="primary" icon={<PlusOutlined />} onClick={openCreate}>Nueva salida</Button> : null}
      </div>

      <div className="glass-panel boutique-filter-bar">
        <Row gutter={[12, 12]}>
          <Col xs={24} md={10}>
            <Input allowClear prefix={<SearchOutlined />} placeholder="Buscar por código, nombre o destino" value={filters.search} onChange={(event) => setFilters((current) => ({ ...current, search: event.target.value }))} />
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

      <Table className="glass-panel" rowKey="id" columns={columns} dataSource={outputs} loading={loading} pagination={{ pageSize: 8 }} scroll={{ x: 'max-content' }} />

      <Drawer
        title="Registrar Salida Taller"
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
        <FormProcessAlert message={formError} title="No fue posible registrar la salida del taller." />
        <Form {...FORM_COMMON_PROPS} form={form} onFinish={handleSubmit}>
          {selectedItem ? (
            <Alert
              type="info"
              showIcon
              style={{ marginBottom: 16 }}
              message={`${selectedItem.code} - ${selectedItem.name}`}
              description={`Stock actual: ${selectedItem.stock}. Unidad: ${labelFromOptions(UNIDAD_MEDIDA_OPTIONS, selectedItem.unit_measure)}. Stock mínimo: ${selectedItem.stock_min}.`}
            />
          ) : null}

          <Row gutter={12}>
            <Col span={12}>
              <Form.Item label="Material" name="item_id" rules={[{ required: true, message: 'Debe seleccionar el Material del taller.' }]}>
                <Select showSearch optionFilterProp="label" placeholder="Buscar y seleccionar material del taller" options={itemOptions} />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item label="Destino" name="destination" rules={[{ required: true, message: 'El Destino es obligatorio.' }]} normalize={(value) => (value || '').toUpperCase()}>
                <Input placeholder="Ej. CORTE DE FALDA, PRUEBA DE MUESTRA O PEDIDO CLIENTE" />
              </Form.Item>
            </Col>
          </Row>

          <Row gutter={12}>
            <Col span={12}>
              <Form.Item
                label="Cantidad"
                name="quantity"
                rules={[{ required: true, message: 'La Cantidad es obligatoria.' }]}
                normalize={(value) => {
                  if (value === null || value === undefined || value === '') return null
                  return value.toString().replace(/[^0-9.]/g, '')
                }}
              >
                <InputNumber min={0.01} precision={2} style={{ width: '100%' }} placeholder="Ej. 1.50" />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item label="Unidad" name="unit_measure" rules={[{ required: true, message: 'La Unidad es obligatoria.' }]}>
                <Select disabled options={UNIDAD_MEDIDA_OPTIONS} placeholder="Unidad del material base" />
              </Form.Item>
            </Col>
          </Row>

          <Row gutter={12}>
            <Col span={12}>
              <Form.Item label="Observación 1" name="observations_1" normalize={(value) => (value || '').toUpperCase()}>
                <Input.TextArea rows={2} placeholder="Ej. DESTINADO A AJUSTE DE PRENDA O PRODUCCIÓN INTERNA" />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item label="Observación 2" name="observations_2" normalize={(value) => (value || '').toUpperCase()}>
                <Input.TextArea rows={2} placeholder="Ej. SALIDA CONTROLADA POR MODISTA RESPONSABLE DEL TALLER" />
              </Form.Item>
            </Col>
          </Row>

          <Button {...FORM_DRAWER_SUBMIT_PROPS} loading={saving}>Registrar salida</Button>
        </Form>
      </Drawer>

      <Modal
        title="Detalle de Salida Taller"
        open={!!viewingOutput}
        onCancel={() => setViewingOutput(null)}
        maskClosable={false}
        footer={[<Button key="close" onClick={() => setViewingOutput(null)}>Cerrar</Button>]}
        width={760}
      >
        {viewingOutput ? (
          <Descriptions bordered column={2} size="small" layout="vertical">
            <Descriptions.Item label="Fecha">{new Date(viewingOutput.fecha).toLocaleString()}</Descriptions.Item>
            <Descriptions.Item label="Estado">{viewingOutput.is_active ? 'ACTIVA' : 'INACTIVA'}</Descriptions.Item>
            <Descriptions.Item label="Material">{`${viewingOutput.item.code} - ${viewingOutput.item.name}`}</Descriptions.Item>
            <Descriptions.Item label="Tipo"><Tag color={getCategoryColor(viewingOutput.item.type_name)}>{viewingOutput.item.type_name || 'SIN TIPO'}</Tag></Descriptions.Item>
            <Descriptions.Item label="Unidad">{labelFromOptions(UNIDAD_MEDIDA_OPTIONS, viewingOutput.item.unit_measure)}</Descriptions.Item>
            <Descriptions.Item label="Cantidad">{viewingOutput.quantity}</Descriptions.Item>
            <Descriptions.Item label="Destino">{viewingOutput.destination}</Descriptions.Item>
            <Descriptions.Item label="Registrado por">{viewingOutput.registered_by?.full_name || 'SIN USUARIO'}</Descriptions.Item>
            <Descriptions.Item label="Usuario" span={2}>{viewingOutput.registered_by?.username || 'SIN CUENTA'}</Descriptions.Item>
            <Descriptions.Item label="Observación 1" span={2}>{viewingOutput.observations_1 || 'SIN OBSERVACIONES'}</Descriptions.Item>
            <Descriptions.Item label="Observación 2" span={2}>{viewingOutput.observations_2 || 'SIN OBSERVACIONES'}</Descriptions.Item>
          </Descriptions>
        ) : null}
      </Modal>
    </div>
  )
}
