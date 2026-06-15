import { EditOutlined, EyeOutlined, PlusOutlined, SearchOutlined } from '@ant-design/icons'
import { Alert, App as AntdApp, Button, Col, DatePicker, Descriptions, Drawer, Form, Input, Modal, Row, Select, Space, Switch, Table, Tag, Typography } from 'antd'
import dayjs from 'dayjs'
import { useCallback, useEffect, useMemo, useState } from 'react'

import { apiClient } from '../../api/client'
import { TRAVEL_DESTINATIONS } from '../pedidos/orderConstants'
import { useAuth } from '../../auth/AuthProvider'
import { FORM_COMMON_PROPS, FORM_DRAWER_SUBMIT_PROPS } from '../../components/forms/formConfig'
import { applyFormApiError } from '../../components/forms/formErrorUtils'
import { FormProcessAlert } from '../../components/forms/FormProcessAlert'

export function ClientsPage() {
  const [clients, setClients] = useState([])
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState(null)
  const [formError, setFormError] = useState(null)
  const [drawerOpen, setDrawerOpen] = useState(false)
  const [editingClient, setEditingClient] = useState(null)
  const [viewingClient, setViewingClient] = useState(null)
  const [filters, setFilters] = useState({ search: '', is_active: undefined })
  const [form] = Form.useForm()
  const { message } = AntdApp.useApp()
  const { user } = useAuth()

  const canCreate = user?.permissions?.includes('clients:create')
  const canUpdate = user?.permissions?.includes('clients:update')
  const canChangeStatus = user?.permissions?.includes('clients:update_status')

  const selectedCountry = Form.useWatch('pais', form)

  const countryOptions = useMemo(
    () => TRAVEL_DESTINATIONS.map((item) => ({ label: item.country, value: item.country })),
    [],
  )

  const cityOptions = useMemo(() => {
    const selected = TRAVEL_DESTINATIONS.find((item) => item.country === selectedCountry)
    return (selected?.cities || []).map((city) => ({ label: city, value: city }))
  }, [selectedCountry])

  const loadClients = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const params = {}
      if (filters.search) params.search = filters.search
      if (filters.is_active !== undefined) params.is_active = filters.is_active
      const response = await apiClient.get('/clientes', { params })
      setClients(response.data)
    } catch (requestError) {
      setError(requestError.response?.data?.detail || 'No fue posible cargar los clientes.')
    } finally {
      setLoading(false)
    }
  }, [filters])

  useEffect(() => {
    loadClients()
  }, [loadClients])

  const openCreate = () => {
    setEditingClient(null)
    setFormError(null)
    form.resetFields()
    form.setFieldsValue({ correo: '@gmail.com' })
    setDrawerOpen(true)
  }

  const openEdit = async (record) => {
    try {
      const response = await apiClient.get(`/clientes/${record.id}`)
      const item = response.data
      setEditingClient(item)
      setFormError(null)
      form.setFieldsValue({
        codigo: item.codigo,
        nombres: item.nombres,
        apellido_paterno: item.apellido_paterno,
        apellido_materno: item.apellido_materno,
        celular: item.celular,
        celular_referencia: item.celular_referencia,
        nombre_referencia: item.nombre_referencia,
        correo: item.correo,
        ci: item.ci,
        fecha_nacimiento: item.fecha_nacimiento ? dayjs(item.fecha_nacimiento) : null,
        pais: item.pais,
        ciudad: item.ciudad,
        zona: item.zona,
        calle: item.calle,
        observaciones: item.observaciones,
      })
      setDrawerOpen(true)
    } catch (requestError) {
      message.error(requestError.response?.data?.detail || 'No fue posible cargar el cliente.')
    }
  }

  const openView = async (record) => {
    try {
      const response = await apiClient.get(`/clientes/${record.id}`)
      setViewingClient(response.data)
    } catch (requestError) {
      message.error(requestError.response?.data?.detail || 'No fue posible cargar el detalle del cliente.')
    }
  }

  const handleSubmit = async (values) => {
    setSaving(true)
    setFormError(null)
    const payload = { ...values }
    if (!payload.codigo) delete payload.codigo
    if (payload.fecha_nacimiento) {
      payload.fecha_nacimiento = dayjs(payload.fecha_nacimiento).format('YYYY-MM-DD')
    }
    if (payload.correo === '@gmail.com') {
      payload.correo = null
    }
    try {
      if (editingClient) {
        await apiClient.patch(`/clientes/${editingClient.id}`, payload)
        message.success('Se guardaron los cambios del cliente correctamente.')
      } else {
        await apiClient.post('/clientes', payload)
        message.success('Se creó el cliente correctamente.')
      }
      setDrawerOpen(false)
      setEditingClient(null)
      form.resetFields()
      await loadClients()
    } catch (requestError) {
      const resolved = applyFormApiError(form, requestError, {
        messageFieldMap: [
          { test: /cliente con ese código/i, field: 'codigo' },
          { test: /cédula de identidad ya está en uso/i, field: 'ci' },
          { test: /correo electrónico ya está en uso/i, field: 'correo' },
        ],
        fallbackGlobalMessage: 'No fue posible guardar la información del cliente.',
      })
      setFormError(resolved.globalMessage)
    } finally {
      setSaving(false)
    }
  }

  const handleStatusChange = async (record, checked) => {
    try {
      await apiClient.patch(`/clientes/${record.id}/status`, { habilitado: checked })
      message.success(`Cliente ${checked ? 'activado' : 'desactivado'} correctamente.`)
      await loadClients()
    } catch (requestError) {
      message.error(requestError.response?.data?.detail || 'No fue posible cambiar el estado del cliente.')
    }
  }

  const columns = [
    { title: 'Código', dataIndex: 'codigo', key: 'codigo' },
    { title: 'Nombre completo', dataIndex: 'full_name', key: 'full_name' },
    { title: 'Celular', dataIndex: 'celular', key: 'celular' },
    { title: 'Cédula de Identidad', dataIndex: 'ci', key: 'ci', render: (value) => value || 'SIN DATO' },
    { title: 'Ciudad', dataIndex: 'ciudad', key: 'ciudad', render: (value) => value || 'SIN DATO' },
    { title: 'Zona', dataIndex: 'zona', key: 'zona', render: (value) => value || 'SIN DATO' },
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
        <Space wrap>
          <Button icon={<EyeOutlined />} onClick={() => openView(record)}>Ver</Button>
          {canUpdate ? <Button icon={<EditOutlined />} onClick={() => openEdit(record)}>Editar</Button> : null}
        </Space>
      ),
    },
  ]

  return (
    <div>
      <div className="page-header">
        <div>
          <Typography.Title level={2} style={{ margin: 0 }}>Clientes</Typography.Title>
          <Typography.Paragraph type="secondary" style={{ marginBottom: 0 }}>
            Registra y administra la información comercial y de contacto de clientes.
          </Typography.Paragraph>
        </div>
        {canCreate ? <Button type="primary" icon={<PlusOutlined />} onClick={openCreate}>Nuevo cliente</Button> : null}
      </div>

      <div className="glass-panel boutique-filter-bar">
        <Row gutter={[12, 12]}>
          <Col xs={24} md={16}>
            <Input
              allowClear
              prefix={<SearchOutlined />}
              placeholder="Buscar por código, nombre, CI, celular o ciudad"
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

      <Table className="glass-panel" rowKey="id" columns={columns} dataSource={clients} loading={loading} pagination={{ pageSize: 8 }} />

      <Drawer
        title={editingClient ? 'Editar Cliente' : 'Crear Cliente'}
        width={760}
        onClose={() => {
          setDrawerOpen(false)
          setEditingClient(null)
          setFormError(null)
          form.resetFields()
        }}
        open={drawerOpen}
        destroyOnClose
        maskClosable={false}
      >
        <FormProcessAlert
          message={formError}
          title={editingClient ? 'No fue posible actualizar el cliente.' : 'No fue posible crear el cliente.'}
        />

        <Form {...FORM_COMMON_PROPS} form={form} onFinish={handleSubmit}>
          <Form.Item
            label="Código"
            name="codigo"
            extra="Si lo dejas vacío, el sistema generará el código automáticamente con el formato oficial."
            normalize={(value) => (value || '').toUpperCase().replace(/[^A-Z0-9-]/g, '')}
          >
            <Input placeholder="Ej. CLI-00001" />
          </Form.Item>

          <Row gutter={12}>
            <Col span={12}>
              <Form.Item label="Nombres" name="nombres" rules={[{ required: true, message: 'El o los Nombres del cliente son obligatorios.' }]} normalize={(value) => (value || '').replace(/[^a-zA-ZáéíóúÁÉÍÓÚñÑ\s]/g, '').toUpperCase()}>
                <Input placeholder="Introducir el o los Nombres del cliente" />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item label="Apellido paterno" name="apellido_paterno" rules={[{ required: true, message: 'El Apellido Paterno del cliente es obligatorio.' }]} normalize={(value) => (value || '').replace(/[^a-zA-ZáéíóúÁÉÍÓÚñÑ\s]/g, '').toUpperCase()}>
                <Input placeholder="Introducir el Apellido Paterno del cliente" />
              </Form.Item>
            </Col>
          </Row>

          <Row gutter={12}>
            <Col span={12}>
              <Form.Item label="Apellido materno" name="apellido_materno" normalize={(value) => (value || '').replace(/[^a-zA-ZáéíóúÁÉÍÓÚñÑ\s]/g, '').toUpperCase()}>
                <Input placeholder="Introducir el Apellido Materno del cliente" />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item label="Fecha de nacimiento" name="fecha_nacimiento">
                <DatePicker
                  style={{ width: '100%' }}
                  format="DD/MM/YYYY"
                  valueFormat="YYYY-MM-DD"
                  placeholder="Seleccionar la fecha de nacimiento"
                />
              </Form.Item>
            </Col>
          </Row>

          <Row gutter={12}>
            <Col span={12}>
              <Form.Item label="Celular" name="celular" rules={[{ required: true, message: 'El número de Celular es obligatorio.' }, { min: 8, message: 'El número de Celular debe tener al menos 8 dígitos.' }]} normalize={(value) => (value || '').replace(/[^0-9]/g, '')}>
                <Input placeholder="Ej. 70000000" />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item label="Cédula de identidad" name="ci" normalize={(value) => (value || '').replace(/[^0-9A-Z]/g, '').toUpperCase()}>
                <Input placeholder="Ej. 1234567" />
              </Form.Item>
            </Col>
          </Row>

          <Row gutter={12}>
            <Col span={12}>
              <Form.Item label="Celular de referencia" name="celular_referencia" normalize={(value) => (value || '').replace(/[^0-9]/g, '')}>
                <Input placeholder="Ej. 71234567" />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item label="Nombre de referencia" name="nombre_referencia" normalize={(value) => (value || '').replace(/[^a-zA-ZáéíóúÁÉÍÓÚñÑ\s]/g, '').toUpperCase()}>
                <Input placeholder="Introducir el nombre del contacto de referencia" />
              </Form.Item>
            </Col>
          </Row>

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
            <Input placeholder="cliente@gmail.com" />
          </Form.Item>

          <Row gutter={12}>
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
          </Row>

          <Row gutter={12}>
            <Col span={12}>
              <Form.Item label="Zona" name="zona" normalize={(value) => (value || '').toUpperCase()}>
                <Input placeholder="Ej. ZONA SUR" />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item label="Calle o dirección" name="calle" normalize={(value) => (value || '').toUpperCase()}>
                <Input placeholder="Ej. AV. PRINCIPAL, CALLE 10 O CASA 45" />
              </Form.Item>
            </Col>
          </Row>

          <Form.Item label="Observaciones" name="observaciones" normalize={(value) => (value || '').toUpperCase()}>
            <Input.TextArea rows={3} placeholder="Ej. CLIENTE REFERIDA POR REDES O PREFIERE CONTACTO SOLO EN LA TARDE" />
          </Form.Item>

          <Button {...FORM_DRAWER_SUBMIT_PROPS} loading={saving}>
            {editingClient ? 'Guardar cambios' : 'Crear cliente'}
          </Button>
        </Form>
      </Drawer>

      <Modal
        title="Detalles del Cliente"
        open={!!viewingClient}
        onCancel={() => setViewingClient(null)}
        maskClosable={false}
        footer={[<Button key="close" onClick={() => setViewingClient(null)}>Cerrar</Button>]}
        width={760}
      >
        {viewingClient && (
          <Descriptions bordered column={2} size="small" layout="vertical">
            <Descriptions.Item label="Código">{viewingClient.codigo}</Descriptions.Item>
            <Descriptions.Item label="Nombre completo">{viewingClient.full_name}</Descriptions.Item>
            <Descriptions.Item label="Celular">{viewingClient.celular}</Descriptions.Item>
            <Descriptions.Item label="Cédula de Identidad">{viewingClient.ci || 'NINGUNO'}</Descriptions.Item>
            <Descriptions.Item label="Correo Electrónico">{viewingClient.correo || 'NINGUNO'}</Descriptions.Item>
            <Descriptions.Item label="Fecha de nacimiento">{viewingClient.fecha_nacimiento || 'SIN REGISTRO'}</Descriptions.Item>
            <Descriptions.Item label="País">{viewingClient.pais || 'SIN REGISTRO'}</Descriptions.Item>
            <Descriptions.Item label="Ciudad">{viewingClient.ciudad || 'SIN REGISTRO'}</Descriptions.Item>
            <Descriptions.Item label="Zona">{viewingClient.zona || 'SIN REGISTRO'}</Descriptions.Item>
            <Descriptions.Item label="Dirección">{viewingClient.calle || 'SIN REGISTRO'}</Descriptions.Item>
            <Descriptions.Item label="Celular Referencia">{viewingClient.celular_referencia || 'SIN REGISTRO'}</Descriptions.Item>
            <Descriptions.Item label="Contacto Referencia">{viewingClient.nombre_referencia || 'SIN REGISTRO'}</Descriptions.Item>
            <Descriptions.Item label="Observaciones" span={2}>{viewingClient.observaciones || 'SIN OBSERVACIONES'}</Descriptions.Item>
          </Descriptions>
        )}
      </Modal>
    </div>
  )
}
