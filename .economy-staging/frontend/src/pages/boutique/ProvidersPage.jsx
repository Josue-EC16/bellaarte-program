import { EditOutlined, EyeOutlined, PlusOutlined, SearchOutlined } from '@ant-design/icons'
import { Alert, App as AntdApp, Button, Col, Descriptions, Drawer, Form, Input, Modal, Row, Select, Switch, Table, Tag, Typography } from 'antd'
import { useCallback, useEffect, useMemo, useState } from 'react'

import { apiClient } from '../../api/client'
import { TRAVEL_DESTINATIONS } from '../pedidos/orderConstants'
import { useAuth } from '../../auth/AuthProvider'
import { FORM_COMMON_PROPS, FORM_DRAWER_SUBMIT_PROPS } from '../../components/forms/formConfig'
import { applyFormApiError } from '../../components/forms/formErrorUtils'
import { FormProcessAlert } from '../../components/forms/FormProcessAlert'
import { ReportSummaryStrip } from '../../components/reports/ReportSummaryStrip'
import { useListingSummary } from '../../components/reports/useListingSummary'

export function ProvidersPage() {
  const [providers, setProviders] = useState([])
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState(null)
  const [formError, setFormError] = useState(null)
  const [drawerOpen, setDrawerOpen] = useState(false)
  const [editingProvider, setEditingProvider] = useState(null)
  const [viewingProvider, setViewingProvider] = useState(null)
  const [filters, setFilters] = useState({ search: '', is_active: undefined })
  const [form] = Form.useForm()
  const { message } = AntdApp.useApp()
  const { user } = useAuth()

  const canCreate = user?.permissions?.includes('boutique_providers:create')
  const canUpdate = user?.permissions?.includes('boutique_providers:update')
  const canChangeStatus = user?.permissions?.includes('boutique_providers:update_status')
  const { summary, loading: summaryLoading } = useListingSummary('/boutique/proveedores/resumen', filters)

  const selectedCountry = Form.useWatch('pais', form)

  const countryOptions = useMemo(
    () => TRAVEL_DESTINATIONS.map((item) => ({ label: item.country, value: item.country })),
    [],
  )

  const cityOptions = useMemo(() => {
    const selected = TRAVEL_DESTINATIONS.find((item) => item.country === selectedCountry)
    return (selected?.cities || []).map((city) => ({ label: city, value: city }))
  }, [selectedCountry])

  const loadProviders = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const params = {}
      if (filters.search) params.search = filters.search
      if (filters.is_active !== undefined) params.is_active = filters.is_active
      const response = await apiClient.get('/boutique/proveedores', { params })
      setProviders(response.data)
    } catch (requestError) {
      setError(requestError.response?.data?.detail || 'No fue posible cargar los proveedores.')
    } finally {
      setLoading(false)
    }
  }, [filters])

  useEffect(() => {
    loadProviders()
  }, [loadProviders])

  const openCreate = () => {
    setEditingProvider(null)
    setFormError(null)
    form.resetFields()
    form.setFieldsValue({ correo: '@gmail.com' })
    setDrawerOpen(true)
  }

  const openEdit = async (record) => {
    try {
      const response = await apiClient.get(`/boutique/proveedores/${record.id}`)
      const provider = response.data
      setEditingProvider(provider)
      setFormError(null)
      form.setFieldsValue({
        nombres: provider.nombres,
        apellido_paterno: provider.apellido_paterno,
        apellido_materno: provider.apellido_materno,
        nombre_comercial: provider.nombre_comercial,
        celular: provider.celular,
        celular_secundario: provider.celular_secundario,
        correo: provider.correo,
        pais: provider.pais,
        ciudad: provider.ciudad,
        direccion: provider.direccion,
        observaciones: provider.observaciones,
      })
      setDrawerOpen(true)
    } catch (requestError) {
      message.error(requestError.response?.data?.detail || 'No fue posible cargar el proveedor.')
    }
  }

  const openView = async (record) => {
    try {
      const response = await apiClient.get(`/boutique/proveedores/${record.id}`)
      setViewingProvider(response.data)
    } catch (requestError) {
      message.error(requestError.response?.data?.detail || 'No fue posible cargar el detalle del proveedor.')
    }
  }

  const handleSubmit = async (values) => {
    setSaving(true)
    setFormError(null)
    const payload = { ...values }
    if (payload.correo === '@gmail.com') {
      payload.correo = null
    }
    try {
      if (editingProvider) {
        await apiClient.patch(`/boutique/proveedores/${editingProvider.id}`, payload)
        message.success('Se guardaron los cambios del proveedor correctamente.')
      } else {
        await apiClient.post('/boutique/proveedores', payload)
        message.success('Se creó el proveedor correctamente.')
      }
      setDrawerOpen(false)
      setEditingProvider(null)
      form.resetFields()
      await loadProviders()
    } catch (requestError) {
      const resolved = applyFormApiError(form, requestError, {
        messageFieldMap: [
          { test: /celular principal ya está en uso/i, field: 'celular' },
          { test: /correo electrónico ya está en uso/i, field: 'correo' },
        ],
        fallbackGlobalMessage: 'No fue posible guardar la información del proveedor.',
      })
      setFormError(resolved.globalMessage)
    } finally {
      setSaving(false)
    }
  }

  const handleStatusChange = async (record, checked) => {
    try {
      await apiClient.patch(`/boutique/proveedores/${record.id}/status`, { habilitado: checked })
      message.success(`Proveedor ${checked ? 'activado' : 'desactivado'} correctamente.`)
      await loadProviders()
    } catch (requestError) {
      message.error(requestError.response?.data?.detail || 'No fue posible cambiar el estado del proveedor.')
    }
  }

  const columns = [
    { title: 'Nombre', dataIndex: 'full_name', key: 'full_name' },
    { title: 'Nombre comercial', dataIndex: 'nombre_comercial', key: 'nombre_comercial', render: (value) => value || 'SIN REGISTRO' },
    { title: 'Celular', dataIndex: 'celular', key: 'celular', render: (value) => value || 'SIN REGISTRO' },
    { title: 'Correo', dataIndex: 'correo', key: 'correo', render: (value) => value || 'SIN REGISTRO' },
    { title: 'Ciudad', dataIndex: 'ciudad', key: 'ciudad', render: (value) => value || 'SIN REGISTRO' },
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
          <Typography.Title level={2} style={{ margin: 0 }}>Proveedores Boutique</Typography.Title>
          <Typography.Paragraph type="secondary" style={{ marginBottom: 0 }}>
            Centraliza la información de proveedores y evita capturas de texto libre en inventario.
          </Typography.Paragraph>
        </div>
        {canCreate ? <Button type="primary" icon={<PlusOutlined />} onClick={openCreate}>Nuevo proveedor</Button> : null}
      </div>

      <div className="glass-panel boutique-filter-bar">
        <Row gutter={[12, 12]}>
          <Col xs={24} md={16}>
            <Input
              allowClear
              prefix={<SearchOutlined />}
              placeholder="Buscar por nombre, comercial, celular o ciudad"
              value={filters.search}
              onChange={(event) => setFilters((current) => ({ ...current, search: event.target.value }))}
            />
          </Col>
          <Col xs={24} md={8}>
            <Select
              allowClear
              placeholder="Estado"
              value={filters.is_active}
              onChange={(value) => setFilters((current) => ({ ...current, is_active: value }))}
              options={[{ label: 'Activos', value: true }, { label: 'Inactivos', value: false }]}
              style={{ width: '100%' }}
            />
          </Col>
        </Row>
      </div>

      {error ? <Alert type="error" showIcon message={error} style={{ marginBottom: 16 }} /> : null}
      <ReportSummaryStrip summary={summary} loading={summaryLoading} />

      <Table className="glass-panel" rowKey="id" columns={columns} dataSource={providers} loading={loading} pagination={{ pageSize: 8 }} />

      <Drawer
        title={editingProvider ? 'Editar Proveedor' : 'Crear Proveedor'}
        width={760}
        open={drawerOpen}
        onClose={() => {
          setDrawerOpen(false)
          setEditingProvider(null)
          setFormError(null)
          form.resetFields()
        }}
        destroyOnClose
        maskClosable={false}
      >
        <FormProcessAlert message={formError} title={editingProvider ? 'No fue posible actualizar el proveedor.' : 'No fue posible crear el proveedor.'} />
        <Form {...FORM_COMMON_PROPS} form={form} onFinish={handleSubmit}>
          <Row gutter={12}>
            <Col span={12}>
              <Form.Item label="Nombres" name="nombres" rules={[{ required: true, message: 'Los Nombres del proveedor son obligatorios.' }]} normalize={(value) => (value || '').replace(/[^a-zA-ZáéíóúÁÉÍÓÚñÑ\s]/g, '').toUpperCase()}>
                <Input placeholder="Introducir el nombre o nombres del proveedor" />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item label="Nombre comercial" name="nombre_comercial" normalize={(value) => (value || '').toUpperCase()}>
                <Input placeholder="Ej. IMPORTADORA CENTRAL O FLORES DORADAS" />
              </Form.Item>
            </Col>
          </Row>
          <Row gutter={12}>
            <Col span={12}>
              <Form.Item label="Apellido paterno" name="apellido_paterno" normalize={(value) => (value || '').replace(/[^a-zA-ZáéíóúÁÉÍÓÚñÑ\s]/g, '').toUpperCase()}>
                <Input placeholder="Introducir el Apellido Paterno del proveedor" />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item label="Apellido materno" name="apellido_materno" normalize={(value) => (value || '').replace(/[^a-zA-ZáéíóúÁÉÍÓÚñÑ\s]/g, '').toUpperCase()}>
                <Input placeholder="Introducir el Apellido Materno del proveedor" />
              </Form.Item>
            </Col>
          </Row>
          <Row gutter={12}>
            <Col span={12}>
              <Form.Item label="Celular principal" name="celular" normalize={(value) => (value || '').replace(/[^0-9]/g, '')}>
                <Input placeholder="Ej. 70000000" />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item label="Celular secundario" name="celular_secundario" normalize={(value) => (value || '').replace(/[^0-9]/g, '')}>
                <Input placeholder="Ej. 71234567" />
              </Form.Item>
            </Col>
          </Row>
          <Row gutter={12}>
            <Col span={12}>
              <Form.Item
                label="Correo electrónico"
                name="correo"
                rules={[
                  { type: 'email', message: 'Debe ingresar un Correo Electrónico válido.' },
                  {
                    pattern: /^[a-zA-Z0-9._%+-]+@gmail\.com$/,
                    message: 'Solo se permiten correos @gmail.com.',
                  },
                ]}
                extra="Solo se aceptan correos con dominio @gmail.com."
                normalize={(value) => (value || '').replace(/\s/g, '').toLowerCase()}
              >
                <Input placeholder="proveedor@gmail.com" />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item label="País" name="pais">
                <Select
                  showSearch
                  allowClear
                  placeholder="Selecciona el país"
                  options={countryOptions}
                  optionFilterProp="label"
                  onChange={() => form.setFieldValue('ciudad', undefined)}
                />
              </Form.Item>
            </Col>
          </Row>
          <Row gutter={12}>
            <Col span={12}>
              <Form.Item label="Ciudad" name="ciudad">
                <Select
                  showSearch
                  allowClear
                  placeholder="Selecciona la ciudad"
                  options={cityOptions}
                  optionFilterProp="label"
                />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item label="Dirección" name="direccion" normalize={(value) => (value || '').toUpperCase()}>
                <Input placeholder="Ej. AV. CENTRAL, GALPÓN 5 O CALLE 10" />
              </Form.Item>
            </Col>
          </Row>
          <Form.Item label="Observaciones" name="observaciones" normalize={(value) => (value || '').toUpperCase()}>
            <Input.TextArea rows={3} placeholder="Ej. PROVEEDOR DE ENTREGAS RÁPIDAS O CONTACTO SOLO POR LAS MAÑANAS" />
          </Form.Item>
          <Button {...FORM_DRAWER_SUBMIT_PROPS} loading={saving}>
            {editingProvider ? 'Guardar cambios' : 'Crear proveedor'}
          </Button>
        </Form>
      </Drawer>

      <Modal
        title="Detalles del Proveedor"
        open={!!viewingProvider}
        onCancel={() => setViewingProvider(null)}
        maskClosable={false}
        footer={[<Button key="close" onClick={() => setViewingProvider(null)}>Cerrar</Button>]}
        width={760}
      >
        {viewingProvider ? (
          <Descriptions bordered column={2} size="small" layout="vertical">
            <Descriptions.Item label="Nombre completo">{viewingProvider.full_name}</Descriptions.Item>
            <Descriptions.Item label="Nombre comercial">{viewingProvider.nombre_comercial || 'SIN REGISTRO'}</Descriptions.Item>
            <Descriptions.Item label="Celular principal">{viewingProvider.celular || 'SIN REGISTRO'}</Descriptions.Item>
            <Descriptions.Item label="Celular secundario">{viewingProvider.celular_secundario || 'SIN REGISTRO'}</Descriptions.Item>
            <Descriptions.Item label="Correo">{viewingProvider.correo || 'SIN REGISTRO'}</Descriptions.Item>
            <Descriptions.Item label="País">{viewingProvider.pais || 'SIN REGISTRO'}</Descriptions.Item>
            <Descriptions.Item label="Ciudad">{viewingProvider.ciudad || 'SIN REGISTRO'}</Descriptions.Item>
            <Descriptions.Item label="Dirección">{viewingProvider.direccion || 'SIN REGISTRO'}</Descriptions.Item>
            <Descriptions.Item label="Observaciones" span={2}>{viewingProvider.observaciones || 'SIN OBSERVACIONES'}</Descriptions.Item>
          </Descriptions>
        ) : null}
      </Modal>
    </div>
  )
}
