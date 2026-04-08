import { PlusOutlined } from '@ant-design/icons'
import {
  Alert,
  App as AntdApp,
  Button,
  Drawer,
  Form,
  Input,
  Select,
  Space,
  Switch,
  Table,
  Tag,
  Typography,
} from 'antd'
import { useEffect, useMemo, useState } from 'react'

import { apiClient } from '../../api/client'

export function UsersPage() {
  const [users, setUsers] = useState([])
  const [roles, setRoles] = useState([])
  const [loading, setLoading] = useState(true)
  const [drawerOpen, setDrawerOpen] = useState(false)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState(null)
  const [form] = Form.useForm()
  const { message } = AntdApp.useApp()

  const loadData = async () => {
    setLoading(true)
    setError(null)
    try {
      const [usersResponse, rolesResponse] = await Promise.all([
        apiClient.get('/users'),
        apiClient.get('/roles'),
      ])
      setUsers(usersResponse.data)
      setRoles(rolesResponse.data)
    } catch (requestError) {
      setError(requestError.response?.data?.detail || 'No fue posible cargar los usuarios.')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadData()
  }, [])

  const roleOptions = useMemo(
    () =>
      roles.map((role) => ({
        label: role.nombre,
        value: role.codigo,
      })),
    [roles],
  )

  const handleCreateUser = async (values) => {
    setSaving(true)
    try {
      await apiClient.post('/users', values)
      message.success('Usuario creado correctamente.')
      form.resetFields()
      setDrawerOpen(false)
      await loadData()
    } catch (requestError) {
      message.error(requestError.response?.data?.detail || 'No fue posible crear el usuario.')
    } finally {
      setSaving(false)
    }
  }

  const handleToggleStatus = async (record, nextStatus) => {
    try {
      await apiClient.patch(`/users/${record.id}/status`, { is_active: nextStatus })
      message.success(`Cuenta ${nextStatus ? 'activada' : 'desactivada'} correctamente.`)
      await loadData()
    } catch (requestError) {
      message.error(requestError.response?.data?.detail || 'No fue posible actualizar el estado.')
    }
  }

  const columns = [
    {
      title: 'Nombre completo',
      dataIndex: 'full_name',
      key: 'full_name',
    },
    {
      title: 'Usuario',
      dataIndex: 'username',
      key: 'username',
    },
    {
      title: 'Rol',
      key: 'role',
      render: (_, record) => <Tag color="volcano">{record.role_name}</Tag>,
    },
    {
      title: 'Estado',
      key: 'status',
      render: (_, record) => (
        <Switch
          checked={record.is_active}
          checkedChildren="Activo"
          unCheckedChildren="Inactivo"
          onChange={(nextValue) => handleToggleStatus(record, nextValue)}
        />
      ),
    },
    {
      title: 'Ultimo acceso',
      dataIndex: 'last_login_at',
      key: 'last_login_at',
      render: (value) => value || 'Sin ingreso',
    },
  ]

  return (
    <div>
      <div className="page-header">
        <div>
          <Typography.Title level={2} style={{ margin: 0 }}>
            Usuarios internos
          </Typography.Title>
          <Typography.Paragraph type="secondary" style={{ marginBottom: 0 }}>
            Solo ADMIN puede crear, revisar y activar o desactivar cuentas del sistema.
          </Typography.Paragraph>
        </div>

        <Button type="primary" icon={<PlusOutlined />} onClick={() => setDrawerOpen(true)}>
          Nuevo usuario
        </Button>
      </div>

      {error ? <Alert type="error" showIcon message={error} style={{ marginBottom: 16 }} /> : null}

      <Table
        className="glass-panel"
        rowKey="id"
        columns={columns}
        dataSource={users}
        loading={loading}
        pagination={{ pageSize: 8 }}
        style={{ borderRadius: 24, overflow: 'hidden' }}
      />

      <Drawer
        title="Crear usuario interno"
        width={460}
        onClose={() => setDrawerOpen(false)}
        open={drawerOpen}
        destroyOnClose
      >
        <Form layout="vertical" form={form} onFinish={handleCreateUser}>
          <Form.Item label="Nombres" name="nombres" rules={[{ required: true }]}>
            <Input />
          </Form.Item>

          <Form.Item label="Apellido paterno" name="apellido_paterno" rules={[{ required: true }]}>
            <Input />
          </Form.Item>

          <Form.Item label="Apellido materno" name="apellido_materno">
            <Input />
          </Form.Item>

          <Space style={{ display: 'flex' }} size={12}>
            <Form.Item label="CI" name="ci" rules={[{ required: true }]} style={{ flex: 1 }}>
              <Input />
            </Form.Item>
            <Form.Item label="Celular" name="celular" rules={[{ required: true }]} style={{ flex: 1 }}>
              <Input />
            </Form.Item>
          </Space>

          <Form.Item label="Correo" name="correo" rules={[{ required: true, type: 'email' }]}>
            <Input />
          </Form.Item>

          <Form.Item label="Zona" name="zona" rules={[{ required: true }]}>
            <Input />
          </Form.Item>

          <Form.Item label="Direccion" name="direccion">
            <Input.TextArea rows={2} />
          </Form.Item>

          <Form.Item label="Nombre de usuario" name="username" rules={[{ required: true }]}>
            <Input />
          </Form.Item>

          <Form.Item
            label="Contrasena temporal"
            name="password_temporal"
            rules={[{ required: true }, { min: 8, message: 'Debe tener al menos 8 caracteres.' }]}
          >
            <Input.Password />
          </Form.Item>

          <Form.Item label="Rol" name="role_code" rules={[{ required: true }]}>
            <Select options={roleOptions} placeholder="Selecciona un rol" />
          </Form.Item>

          <Button type="primary" htmlType="submit" loading={saving}>
            Guardar usuario
          </Button>
        </Form>
      </Drawer>
    </div>
  )
}

