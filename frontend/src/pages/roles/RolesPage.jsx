import { EditOutlined, PlusOutlined } from '@ant-design/icons'
import { Alert, App as AntdApp, Button, Drawer, Form, Input, Switch, Table, Tag, Typography } from 'antd'
import { useEffect, useState } from 'react'

import { apiClient } from '../../api/client'
import { useAuth } from '../../auth/AuthProvider'

export function RolesPage() {
  const [roles, setRoles] = useState([])
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState(null)
  const [drawerOpen, setDrawerOpen] = useState(false)
  const [editingRole, setEditingRole] = useState(null)
  const [form] = Form.useForm()
  const { message } = AntdApp.useApp()
  const { user } = useAuth()

  const canCreate = user?.permissions?.includes('roles:create')
  const canUpdate = user?.permissions?.includes('roles:update')
  const canChangeStatus = user?.permissions?.includes('roles:update_status')

  const loadRoles = async () => {
    setLoading(true)
    setError(null)
    try {
      const response = await apiClient.get('/roles')
      setRoles(response.data)
    } catch (requestError) {
      setError(requestError.response?.data?.detail || 'No fue posible cargar los roles.')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadRoles()
  }, [])

  const openCreate = () => {
    setEditingRole(null)
    form.resetFields()
    setDrawerOpen(true)
  }

  const openEdit = (record) => {
    setEditingRole(record)
    form.setFieldsValue({
      codigo: record.codigo,
      nombre: record.nombre,
      descripcion: record.descripcion,
    })
    setDrawerOpen(true)
  }

  const handleSubmit = async (values) => {
    setSaving(true)
    try {
      if (editingRole) {
        await apiClient.patch(`/roles/${editingRole.id}`, {
          nombre: values.nombre,
          descripcion: values.descripcion,
        })
        message.success('Rol actualizado correctamente.')
      } else {
        await apiClient.post('/roles', values)
        message.success('Rol creado correctamente.')
      }
      setDrawerOpen(false)
      setEditingRole(null)
      form.resetFields()
      await loadRoles()
    } catch (requestError) {
      message.error(requestError.response?.data?.detail || 'No fue posible guardar el rol.')
    } finally {
      setSaving(false)
    }
  }

  const handleStatusChange = async (record, checked) => {
    try {
      await apiClient.patch(`/roles/${record.id}/status`, { activo: checked })
      message.success(`Rol ${checked ? 'activado' : 'desactivado'} correctamente.`)
      await loadRoles()
    } catch (requestError) {
      message.error(requestError.response?.data?.detail || 'No fue posible actualizar el estado del rol.')
    }
  }

  const columns = [
    { title: 'Codigo', dataIndex: 'codigo', key: 'codigo' },
    { title: 'Nombre', dataIndex: 'nombre', key: 'nombre' },
    { title: 'Descripcion', dataIndex: 'descripcion', key: 'descripcion', render: (value) => value || 'Sin descripcion' },
    {
      title: 'Estado',
      key: 'activo',
      render: (_, record) =>
        canChangeStatus ? (
          <Switch
            checked={record.activo}
            checkedChildren="Activo"
            unCheckedChildren="Inactivo"
            onChange={(checked) => handleStatusChange(record, checked)}
          />
        ) : (
          <Tag color={record.activo ? 'green' : 'default'}>{record.activo ? 'Activo' : 'Inactivo'}</Tag>
        ),
    },
    {
      title: 'Registro',
      dataIndex: 'created_at',
      key: 'created_at',
      render: (value) => (value ? new Date(value).toLocaleString() : 'Sin dato'),
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
            Roles del sistema
          </Typography.Title>
          <Typography.Paragraph type="secondary" style={{ marginBottom: 0 }}>
            Administra catalogo, estado y descripciones de roles operativos.
          </Typography.Paragraph>
        </div>

        {canCreate ? (
          <Button type="primary" icon={<PlusOutlined />} onClick={openCreate}>
            Nuevo rol
          </Button>
        ) : null}
      </div>

      {error ? <Alert type="error" showIcon message={error} style={{ marginBottom: 16 }} /> : null}

      <Table
        className="glass-panel"
        rowKey="id"
        columns={columns}
        dataSource={roles}
        loading={loading}
        pagination={{ pageSize: 8 }}
        style={{ borderRadius: 24, overflow: 'hidden' }}
      />

      <Drawer
        title={editingRole ? 'Editar rol' : 'Crear rol'}
        width={420}
        onClose={() => {
          setDrawerOpen(false)
          setEditingRole(null)
          form.resetFields()
        }}
        open={drawerOpen}
        destroyOnClose
      >
        <Form layout="vertical" form={form} onFinish={handleSubmit}>
          <Form.Item label="Codigo" name="codigo" rules={[{ required: true }]} extra="No se podra cambiar despues de crear.">
            <Input disabled={Boolean(editingRole)} />
          </Form.Item>
          <Form.Item label="Nombre" name="nombre" rules={[{ required: true }]}>
            <Input />
          </Form.Item>
          <Form.Item label="Descripcion" name="descripcion">
            <Input.TextArea rows={3} />
          </Form.Item>
          <Button type="primary" htmlType="submit" loading={saving}>
            Guardar rol
          </Button>
        </Form>
      </Drawer>
    </div>
  )
}
