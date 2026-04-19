import { EditOutlined, KeyOutlined, PlusOutlined } from '@ant-design/icons'
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
import { useCallback, useEffect, useMemo, useState } from 'react'

import { apiClient } from '../../api/client'
import { useAuth } from '../../auth/AuthProvider'

export function UsersPage() {
  const [users, setUsers] = useState([])
  const [roles, setRoles] = useState([])
  const [loading, setLoading] = useState(true)
  const [drawerOpen, setDrawerOpen] = useState(false)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState(null)
  const [editingUser, setEditingUser] = useState(null)
  const [form] = Form.useForm()
  const { message, modal } = AntdApp.useApp()
  const { user } = useAuth()

  const canCreate = user?.permissions?.includes('users:create')
  const canUpdate = user?.permissions?.includes('users:update')
  const canStatus = user?.permissions?.includes('users:update_status')
  const canResetPassword = user?.permissions?.includes('users:reset_password')

  const loadData = useCallback(async () => {
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
  }, [])

  useEffect(() => {
    loadData()
  }, [loadData])

  const roleOptions = useMemo(
    () =>
      roles.map((role) => ({
        label: role.nombre,
        value: role.codigo,
      })),
    [roles],
  )

  const handleSubmitUser = async (values) => {
    setSaving(true)
    try {
      if (editingUser) {
        await apiClient.patch(`/users/${editingUser.id}`, values)
        message.success('Usuario actualizado correctamente.')
      } else {
        await apiClient.post('/users', values)
        message.success('Usuario creado correctamente.')
      }
      form.resetFields()
      setDrawerOpen(false)
      setEditingUser(null)
      await loadData()
    } catch (requestError) {
      message.error(requestError.response?.data?.detail || 'No fue posible guardar el usuario.')
    } finally {
      setSaving(false)
    }
  }

  const openCreate = () => {
    setEditingUser(null)
    form.resetFields()
    form.setFieldsValue({
      user_is_active: true,
      account_is_active: true,
      correo: '@gmail.com',
    })
    setDrawerOpen(true)
  }

  const openEdit = async (record) => {
    try {
      const response = await apiClient.get(`/users/${record.user_id}`)
      const item = response.data
      setEditingUser(item)
      form.setFieldsValue({
        nombres: item.nombres,
        apellido_paterno: item.apellido_paterno,
        apellido_materno: item.apellido_materno,
        ci: item.ci,
        celular: item.celular,
        correo: item.correo,
        zona: item.zona,
        direccion: item.direccion,
        role_code: item.role_code,
        user_is_active: item.user_is_active,
        account_is_active: item.account_is_active,
      })
      setDrawerOpen(true)
    } catch (requestError) {
      message.error(requestError.response?.data?.detail || 'No fue posible cargar el usuario.')
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

  const confirmResetPassword = (record) => {
    modal.confirm({
      title: `¿Estás seguro que quieres restablecer la contraseña del usuario ${record.full_name} (${record.ci})?`,
      content: 'La contraseña volverá a ser la predeterminada (El número de CI).',
      okText: 'Sí',
      cancelText: 'No',
      onOk: async () => {
        try {
          await apiClient.post(`/users/${record.id}/reset-password`, {})
          message.success('Contraseña temporal restablecida correctamente.')
          await loadData()
        } catch (requestError) {
          message.error(requestError.response?.data?.detail || 'No fue posible resetear la contrasena.')
        }
      },
    })
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
      title: 'Usuario',
      key: 'user_status',
      render: (_, record) => (
        <Tag color={record.user_is_active ? 'green' : 'default'}>
          {record.user_is_active ? 'Usuario activo' : 'Usuario inactivo'}
        </Tag>
      ),
    },
    {
      title: 'Cuenta',
      key: 'status',
      render: (_, record) => (
        canStatus ? (
          <Switch
            checked={record.account_is_active}
            checkedChildren="Activa"
            unCheckedChildren="Inactiva"
            onChange={(nextValue) => handleToggleStatus(record, nextValue)}
          />
        ) : (
          <Tag color={record.account_is_active ? 'green' : 'default'}>
            {record.account_is_active ? 'Cuenta activa' : 'Cuenta inactiva'}
          </Tag>
        )
      ),
    },
    {
      title: 'Ultimo acceso',
      dataIndex: 'last_login_at',
      key: 'last_login_at',
      render: (value) => (value ? new Date(value).toLocaleString() : 'Sin ingreso'),
    },
    {
      title: 'Acciones',
      key: 'actions',
      render: (_, record) => (
        <Space wrap>
          {canUpdate ? (
            <Button icon={<EditOutlined />} onClick={() => openEdit(record)}>
              Editar
            </Button>
          ) : null}
          {canResetPassword ? (
            <Button
              icon={<KeyOutlined />}
              onClick={() => confirmResetPassword(record)}
            >
              Reset clave
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
            Usuarios internos
          </Typography.Title>
          <Typography.Paragraph type="secondary" style={{ marginBottom: 0 }}>
            Administra datos personales, cuenta, rol operativo y credenciales temporales del personal.
          </Typography.Paragraph>
        </div>

        {canCreate ? (
          <Button type="primary" icon={<PlusOutlined />} onClick={openCreate}>
            Nuevo usuario
          </Button>
        ) : null}
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
        title={editingUser ? 'Editar Usuario Interno' : 'Crear Usuario Interno'}
        width={520}
        onClose={() => {
          setDrawerOpen(false)
          setEditingUser(null)
          form.resetFields()
        }}
        open={drawerOpen}
        destroyOnClose
      >
        <Form layout="vertical" form={form} onFinish={handleSubmitUser}>
          <Form.Item 
            label="Nombres" 
            name="nombres" 
            rules={[{ required: true }]}
            normalize={(value) => (value || '').replace(/[^a-zA-ZáéíóúÁÉÍÓÚñÑ\s]/g, '').toUpperCase()}
          >
            <Input placeholder="Introducir el o los Nombres del Usuario" />
          </Form.Item>

          <Form.Item 
            label="Apellido Paterno" 
            name="apellido_paterno" 
            rules={[{ required: true }]}
            normalize={(value) => (value || '').replace(/[^a-zA-ZáéíóúÁÉÍÓÚñÑ\s]/g, '').toUpperCase()}
          >
            <Input placeholder="Introducir el Apellido Paterno del Usuario" />
          </Form.Item>

          <Form.Item 
            label="Apellido Materno" 
            name="apellido_materno"
            normalize={(value) => (value || '').replace(/[^a-zA-ZáéíóúÁÉÍÓÚñÑ\s]/g, '').toUpperCase()}
          >
            <Input placeholder="Introducir el Apellido Materno del Usuario (Si aplica)" />
          </Form.Item>

          <Space style={{ display: 'flex' }} size={12}>
            <Form.Item 
              label="Cédula de Identidad" 
              name="ci" 
              rules={[{ required: true }]} 
              style={{ flex: 1 }}
              normalize={(value) => (value || '').replace(/[^0-9A-Z]/g, '').toUpperCase()}
            >
              <Input placeholder="Ej. 1234567" />
            </Form.Item>
            <Form.Item 
              label="Celular" 
              name="celular" 
              rules={[{ required: true }]} 
              style={{ flex: 1 }}
              normalize={(value) => (value || '').replace(/[^0-9]/g, '')}
            >
              <Input placeholder="Ej. 70000000" />
            </Form.Item>
          </Space>

          <Form.Item 
            label="Correo Electrónico" 
            name="correo" 
            rules={[
              { required: true, message: 'El correo es obligatorio' },
              { type: 'email', message: 'Ingrese un formato de correo válido' },
              {
                pattern: /^[a-zA-Z0-9._%+-]+@gmail\.com$/,
                message: 'Solo se permiten correos @gmail.com',
              },
            ]}
            normalize={(value) => (value || '').replace(/\s/g, '').toLowerCase()}
          >
            <Input placeholder="usuario@gmail.com" />
          </Form.Item>

          <Form.Item 
            label="Zona" 
            name="zona" 
            rules={[{ required: true }]}
            normalize={(value) => (value || '').toUpperCase()}
          >
            <Input placeholder="Ej. ZONA SUR" />
          </Form.Item>

          <Form.Item 
            label="Dirección" 
            name="direccion"
            normalize={(value) => (value || '').toUpperCase()}
          >
            <Input.TextArea rows={2} placeholder="Descripción detallada de la dirección" />
          </Form.Item>

          <Form.Item label="Rol" name="role_code" rules={[{ required: true }]}>
            <Select options={roleOptions} placeholder="Selecciona un rol" />
          </Form.Item>

          {editingUser ? (
            <Space style={{ display: 'flex' }} size={16}>
              <Form.Item label="Usuario Activo" name="user_is_active" valuePropName="checked">
                <Switch />
              </Form.Item>
              <Form.Item label="Cuenta Activa" name="account_is_active" valuePropName="checked">
                <Switch />
              </Form.Item>
            </Space>
          ) : null}

          <Button type="primary" htmlType="submit" loading={saving}>
            {editingUser ? 'Guardar cambios' : 'Guardar usuario'}
          </Button>
        </Form>
      </Drawer>
    </div>
  )
}
