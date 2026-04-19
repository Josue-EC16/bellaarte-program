import { EditOutlined, PlusOutlined, SearchOutlined } from '@ant-design/icons'
import { Alert, App as AntdApp, Button, Drawer, Form, Input, Select, Space, Switch, Table, Tag, Typography } from 'antd'
import { useCallback, useEffect, useState } from 'react'

import { apiClient } from '../../api/client'
import { useAuth } from '../../auth/AuthProvider'

export function ClientsPage() {
  const [clients, setClients] = useState([])
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState(null)
  const [drawerOpen, setDrawerOpen] = useState(false)
  const [editingClient, setEditingClient] = useState(null)
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
    form.resetFields()
    form.setFieldsValue({ correo: '@gmail.com' })
    setDrawerOpen(true)
  }

  const openEdit = async (record) => {
    try {
      const response = await apiClient.get(`/clientes/${record.id}`)
      const item = response.data
      setEditingClient(item)
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

  const handleSubmit = async (values) => {
    setSaving(true)
    const payload = { ...values }
    if (!payload.codigo) delete payload.codigo
    try {
      if (editingClient) {
        await apiClient.patch(`/clientes/${editingClient.id}`, payload)
        message.success('Cliente actualizado correctamente.')
      } else {
        await apiClient.post('/clientes', payload)
        message.success('Cliente creado correctamente.')
      }
      setDrawerOpen(false)
      setEditingClient(null)
      form.resetFields()
      await loadClients()
    } catch (requestError) {
      message.error(requestError.response?.data?.detail || 'No fue posible guardar el cliente.')
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
    { title: 'Codigo', dataIndex: 'codigo', key: 'codigo' },
    { title: 'Nombre completo', dataIndex: 'full_name', key: 'full_name' },
    { title: 'Celular', dataIndex: 'celular', key: 'celular' },
    { title: 'CI', dataIndex: 'ci', key: 'ci', render: (value) => value || 'Sin dato' },
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
      render: (_, record) =>
        canUpdate ? (
          <Button icon={<EditOutlined />} onClick={() => openEdit(record)}>
            Editar
          </Button>
        ) : (
          <Typography.Text type="secondary">Solo lectura</Typography.Text>
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
        title={editingClient ? 'Editar cliente' : 'Crear cliente'}
        width={560}
        onClose={() => {
          setDrawerOpen(false)
          setEditingClient(null)
          form.resetFields()
        }}
        open={drawerOpen}
        destroyOnClose
      >
        <Form layout="vertical" form={form} onFinish={handleSubmit}>
          <Form.Item
            label="Codigo"
            name="codigo"
            extra="Si lo dejas vacio, el backend generara uno automaticamente."
            rules={[
              {
                pattern: /^CLI-\d{5}$/,
                message: 'Debe seguir el formato CLI-00001.',
              },
            ]}
            normalize={(value) => (value || '').toUpperCase().replace(/[^C-LI\-\d]/g, '')}
          >
            <Input placeholder="Ej. CLI-00001" />
          </Form.Item>
          <Form.Item 
            label="Nombres" 
            name="nombres" 
            rules={[{ required: true }]}
            normalize={(value) => (value || '').replace(/[^a-zA-ZáéíóúÁÉÍÓÚñÑ\s]/g, '').toUpperCase()}  
          >
            <Input placeholder="Introducir el o los Nombres del Cliente" />
          </Form.Item>
          <Form.Item 
            label="Apellido paterno" 
            name="apellido_paterno" 
            rules={[{ required: true }]}
            normalize={(value) => (value || '').replace(/[^a-zA-ZáéíóúÁÉÍÓÚñÑ\s]/g, '').toUpperCase()}
          >
            <Input placeholder="Introducir el Apellido Paterno del Cliente" />
          </Form.Item>
          <Form.Item 
            label="Apellido materno" 
            name="apellido_materno"
            normalize={(value) => (value || '').replace(/[^a-zA-ZáéíóúÁÉÍÓÚñÑ\s]/g, '').toUpperCase()}
          >
            <Input placeholder="Introducir el Apellido Materno del Cliente (Opcional)" />
          </Form.Item>
          <Space style={{ display: 'flex' }} size={12}>
            <Form.Item 
              label="Celular" 
              name="celular" 
              rules={[{ required: true }]} 
              style={{ flex: 1 }}
              normalize={(value) => (value || '').replace(/[^0-9]/g, '')}
            >
              <Input placeholder="Ej. 70000000" />
            </Form.Item>
            <Form.Item 
              label="CI" 
              name="ci" 
              style={{ flex: 1 }}
              normalize={(value) => (value || '').replace(/[^0-9A-Z]/g, '').toUpperCase()}
            >
              <Input placeholder="Ej. 1234567" />
            </Form.Item>
          </Space>
          <Space style={{ display: 'flex' }} size={12}>
            <Form.Item 
              label="Celular referencia" 
              name="celular_referencia" 
              style={{ flex: 1 }}
              normalize={(value) => (value || '').replace(/[^0-9]/g, '')}
            >
              <Input placeholder="Ej. 70000000" />
            </Form.Item>
            <Form.Item 
              label="Nombre referencia" 
              name="nombre_referencia" 
              style={{ flex: 1 }}
              normalize={(value) => (value || '').replace(/[^a-zA-ZáéíóúÁÉÍÓÚñÑ\s]/g, '').toUpperCase()}
            >
              <Input placeholder="Ej. JUAN PEREZ" />
            </Form.Item>
          </Space>
          <Form.Item 
            label="Correo" 
            name="correo" 
            rules={[
              { type: 'email', message: 'Ingrese un formato de correo válido' },
              {
                pattern: /^[a-zA-Z0-9._%+-]+@gmail\.com$/,
                message: 'Solo se permiten correos @gmail.com',
              },
            ]}
            normalize={(value) => (value || '').replace(/\s/g, '').toLowerCase()}
          >
            <Input placeholder="cliente@gmail.com" />
          </Form.Item>
          <Space style={{ display: 'flex' }} size={12}>
            <Form.Item 
              label="Nacionalidad" 
              name="nacionalidad" 
              style={{ flex: 1 }}
              normalize={(value) => (value || '').replace(/[^a-zA-ZáéíóúÁÉÍÓÚñÑ\s]/g, '').toUpperCase()}
            >
              <Input placeholder="Ej. BOLIVIANA" />
            </Form.Item>
            <Form.Item 
              label="Zona" 
              name="zona" 
              style={{ flex: 1 }}
              normalize={(value) => (value || '').toUpperCase()}
            >
              <Input placeholder="Ej. ZONA SUR" />
            </Form.Item>
          </Space>
          <Form.Item 
            label="Calle o direccion" 
            name="calle"
            normalize={(value) => (value || '').toUpperCase()}
          >
            <Input placeholder="Descripción detallada de la calle o dirección" />
          </Form.Item>
          <Form.Item 
            label="Observaciones" 
            name="observaciones"
            normalize={(value) => (value || '').toUpperCase()}
          >
            <Input.TextArea rows={3} placeholder="Información adicional relevante del cliente" />
          </Form.Item>
          <Button type="primary" htmlType="submit" loading={saving}>
            Guardar cliente
          </Button>
        </Form>
      </Drawer>
    </div>
  )
}
