import { EditOutlined, PlusOutlined, SearchOutlined, EyeOutlined } from '@ant-design/icons'
import { Alert, App as AntdApp, Button, Drawer, Form, Input, Select, Space, Switch, Table, Tag, Typography, Row, Col, Modal, Descriptions } from 'antd'
import { useCallback, useEffect, useState } from 'react'

import { apiClient } from '../../api/client'
import { useAuth } from '../../auth/AuthProvider'
import {
  FORM_COMMON_PROPS,
  FORM_DRAWER_SUBMIT_PROPS,
} from '../../components/forms/formConfig'
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
  }, [filters.is_active, filters.search])

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
        nacionalidad: item.nacionalidad,
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
          { test: /cliente con ese codigo/i, field: 'codigo' },
          { test: /cliente con esa cédula de identidad/i, field: 'ci' },
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
    { title: 'Cédula de Identidad', dataIndex: 'ci', key: 'ci', render: (value) => value || 'Sin dato' },
    { title: 'Zona', dataIndex: 'zona', key: 'zona', render: (value) => value || 'Sin dato' },
    {
      title: 'Estado',
      key: 'estado',
      render: (_, record) =>
        canChangeStatus ? (
          <Switch
            checked={record.is_active}
            checkedChildren="Activo"
            unCheckedChildren="Inactivo"
            onChange={(checked) => handleStatusChange(record, checked)}
          />
        ) : (
          <Tag color={record.is_active ? 'green' : 'default'}>{record.is_active ? 'Activo' : 'Inactivo'}</Tag>
        ),
    },
    {
      title: 'Acciones',
      key: 'acciones',
      render: (_, record) => (
        <Space wrap>
          <Button icon={<EyeOutlined />} onClick={() => openView(record)}>
            Ver
          </Button>
          {canUpdate ? (
            <Button icon={<EditOutlined />} onClick={() => openEdit(record)}>
              Editar
            </Button>
          ) : null}
        </Space>
      ),
    },
  ]

  return (
    <div>
      <div className="page-header">
        <div>
          <Typography.Title level={2} style={{ margin: 0 }}>
            Clientes
          </Typography.Title>
          <Typography.Paragraph type="secondary" style={{ marginBottom: 0 }}>
            Registra y administra la informacion comercial de clientes.
          </Typography.Paragraph>
        </div>
        {canCreate ? (
          <Button type="primary" icon={<PlusOutlined />} onClick={openCreate}>
            Nuevo cliente
          </Button>
        ) : null}
      </div>

      <div className="glass-panel boutique-filter-bar">
        <Space wrap style={{ width: '100%', justifyContent: 'space-between' }}>
          <Space wrap>
            <Input
              allowClear
              prefix={<SearchOutlined />}
              placeholder="Buscar por codigo, nombre, CI o celular"
              value={filters.search}
              onChange={(event) => setFilters((current) => ({ ...current, search: event.target.value }))}
              style={{ width: 320 }}
            />
            <Select
              allowClear
              placeholder="Estado"
              value={filters.is_active}
              onChange={(value) => setFilters((current) => ({ ...current, is_active: value }))}
              options={[
                { label: 'Activos', value: true },
                { label: 'Inactivos', value: false },
              ]}
              style={{ width: 160 }}
            />
          </Space>
        </Space>
      </div>

      {error ? <Alert type="error" showIcon message={error} style={{ marginBottom: 16 }} /> : null}

      <Table
        className="glass-panel"
        rowKey="id"
        columns={columns}
        dataSource={clients}
        loading={loading}
        pagination={{ pageSize: 8 }}
        style={{ borderRadius: 24, overflow: 'hidden' }}
      />

      <Drawer
        title={editingClient ? 'Editar Cliente' : 'Crear Cliente'}
        width={560}
        onClose={() => {
          setDrawerOpen(false)
          setEditingClient(null)
          setFormError(null)
          form.resetFields()
        }}
        open={drawerOpen}
        destroyOnClose
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
          <Form.Item
            label="Nombres"
            name="nombres"
            rules={[{ required: true, message: 'El o los Nombres del cliente son obligatorios.' }]}
            extra="Escribe el nombre o los nombres tal como deben quedar registrados."
            normalize={(value) => (value || '').replace(/[^a-zA-ZáéíóúÁÉÍÓÚñÑ\s]/g, '').toUpperCase()}  
          >
            <Input placeholder="Ej. ANA LUCÍA" />
          </Form.Item>
          <Form.Item
            label="Apellido paterno"
            name="apellido_paterno"
            rules={[{ required: true, message: 'El Apellido Paterno del cliente es obligatorio.' }]}
            normalize={(value) => (value || '').replace(/[^a-zA-ZáéíóúÁÉÍÓÚñÑ\s]/g, '').toUpperCase()}
          >
            <Input placeholder="Ej. QUISPE" />
          </Form.Item>
          <Form.Item
            label="Apellido materno"
            name="apellido_materno"
            extra="Opcional. Complétalo solo si aplica."
            normalize={(value) => (value || '').replace(/[^a-zA-ZáéíóúÁÉÍÓÚñÑ\s]/g, '').toUpperCase()}
          >
            <Input placeholder="Ej. MAMANI" />
          </Form.Item>
          <Row gutter={12}>
            <Col span={12}>
              <Form.Item
                label="Celular"
                name="celular"
                rules={[
                  { required: true, message: 'El número de Celular es obligatorio.' },
                  { min: 8, message: 'El número de Celular debe tener al menos 8 dígitos.' },
                ]}
                extra="Ingresa un número activo para contacto principal."
                normalize={(value) => (value || '').replace(/[^0-9]/g, '')}
              >
                <Input placeholder="Ej. 70000000" />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item
                label="Cédula de identidad"
                name="ci"
                rules={[{ min: 6, message: 'La Cédula de Identidad debe tener al menos 6 caracteres.' }]}
                extra="Opcional. Si la registras, evita abreviaturas o símbolos no permitidos."
                normalize={(value) => (value || '').replace(/[^0-9A-Z]/g, '').toUpperCase()}
              >
                <Input placeholder="Ej. 1234567" />
              </Form.Item>
            </Col>
          </Row>
          <Row gutter={12}>
            <Col span={12}>
              <Form.Item
                label="Celular de referencia"
                name="celular_referencia"
                rules={[{ min: 8, message: 'El número de Celular debe tener al menos 8 dígitos.' }]}
                extra="Opcional. Úsalo si existe una persona de apoyo o contacto adicional."
                normalize={(value) => (value || '').replace(/[^0-9]/g, '')}
              >
                <Input placeholder="Ej. 80000000" />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item
                label="Nombre de referencia"
                name="nombre_referencia"
                extra="Opcional. Registra el nombre de la persona asociada al celular de referencia."
                normalize={(value) => (value || '').replace(/[^a-zA-ZáéíóúÁÉÍÓÚñÑ\s]/g, '').toUpperCase()}
              >
                <Input placeholder="Ej. MADRE, HERMANA O APODERADA" />
              </Form.Item>
            </Col>
          </Row>
          <Form.Item
            label="Correo electrónico"
            name="correo"
            rules={[
              { type: 'email', message: 'Debe ingresar un correo electrónico válido.' },
              {
                pattern: /^[a-zA-Z0-9._%+-]+@gmail\.com$/,
                message: 'Solo se permiten correos electrónicos @gmail.com.',
              },
            ]}
            extra="Opcional. Si lo registras, por política interna debe usar el dominio @gmail.com."
            normalize={(value) => (value || '').replace(/\s/g, '').toLowerCase()}
          >
            <Input placeholder="cliente@gmail.com" />
          </Form.Item>
          <Row gutter={12}>
            <Col span={12}>
              <Form.Item
                label="Nacionalidad"
                name="nacionalidad"
                normalize={(value) => (value || '').replace(/[^a-zA-ZáéíóúÁÉÍÓÚñÑ\s]/g, '').toUpperCase()}
              >
                <Input placeholder="Ej. BOLIVIANA" />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item
                label="Zona"
                name="zona"
                extra="Opcional. Ayuda a ubicar al cliente de forma rápida."
                normalize={(value) => (value || '').toUpperCase()}
              >
                <Input placeholder="Ej. SOPHOCACHI" />
              </Form.Item>
            </Col>
          </Row>
          <Form.Item
            label="Calle o dirección"
            name="calle"
            extra="Opcional. Agrega una referencia breve y útil para contacto o entrega."
            normalize={(value) => (value || '').toUpperCase()}
          >
            <Input placeholder="Ej. AV. PRINCIPAL, ESQ. CALLE 8, CASA BLANCA" />
          </Form.Item>
          <Form.Item
            label="Observaciones"
            name="observaciones"
            extra="Opcional. Registra información comercial o de seguimiento que deba quedar visible."
            normalize={(value) => (value || '').toUpperCase()}
          >
            <Input.TextArea rows={3} placeholder="Ej. CLIENTE REFERIDA POR REDES O CON HORARIO PREFERENTE DE CONTACTO" />
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
        footer={[
          <Button key="close" onClick={() => setViewingClient(null)}>
            Cerrar
          </Button>,
        ]}
        width={700}
      >
        {viewingClient && (
          <Descriptions bordered column={2} size="small" layout="vertical">
            <Descriptions.Item label="Código">{viewingClient.codigo}</Descriptions.Item>
            <Descriptions.Item label="Nombre Completo">{viewingClient.nombres} {viewingClient.apellido_paterno} {viewingClient.apellido_materno}</Descriptions.Item>
            <Descriptions.Item label="Celular">{viewingClient.celular}</Descriptions.Item>
            <Descriptions.Item label="Cédula de Identidad">{viewingClient.ci || 'Ninguno'}</Descriptions.Item>
            <Descriptions.Item label="Correo Electrónico">{viewingClient.correo || 'Ninguno'}</Descriptions.Item>
            <Descriptions.Item label="Nacionalidad">{viewingClient.nacionalidad || 'Ninguna'}</Descriptions.Item>
            <Descriptions.Item label="Zona">{viewingClient.zona || 'Ninguna'}</Descriptions.Item>
            <Descriptions.Item label="Dirección">{viewingClient.calle || 'Ninguna'}</Descriptions.Item>
            <Descriptions.Item label="Celular Referencia">{viewingClient.celular_referencia || 'Ninguno'}</Descriptions.Item>
            <Descriptions.Item label="Contacto Referencia">{viewingClient.nombre_referencia || 'Ninguno'}</Descriptions.Item>
            <Descriptions.Item label="Observaciones" span={2}>{viewingClient.observaciones || 'Ninguna'}</Descriptions.Item>
          </Descriptions>
        )}
      </Modal>
    </div>
  )
}
