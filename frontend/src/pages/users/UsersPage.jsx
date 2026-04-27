import { EditOutlined, KeyOutlined, PlusOutlined, EyeOutlined } from '@ant-design/icons'
import {
  Alert,
  App as AntdApp,
  Button,
  Col,
  Drawer,
  Form,
  Input,
  Row,
  Select,
  Space,
  Switch,
  Table,
  Tag,
  Typography,
  Modal,
  Descriptions,
} from 'antd'
import { useCallback, useEffect, useMemo, useState } from 'react'

import { apiClient } from '../../api/client'
import { useAuth } from '../../auth/AuthProvider'
import {
  FORM_COMMON_PROPS,
  FORM_DRAWER_SUBMIT_PROPS,
} from '../../components/forms/formConfig'
import { applyFormApiError } from '../../components/forms/formErrorUtils'
import { FormProcessAlert } from '../../components/forms/FormProcessAlert'

export function UsersPage() {
  const [users, setUsers] = useState([])
  const [roles, setRoles] = useState([])
  const [loading, setLoading] = useState(true)
  const [drawerOpen, setDrawerOpen] = useState(false)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState(null)
  const [formError, setFormError] = useState(null)
  const [editingUser, setEditingUser] = useState(null)
  const [viewingUser, setViewingUser] = useState(null)
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
    setFormError(null)
    try {
      if (editingUser) {
        await apiClient.patch(`/users/${editingUser.id}`, values)
        message.success('Se guardaron los cambios del usuario correctamente.')
      } else {
        await apiClient.post('/users', values)
        message.success('Se creó el usuario correctamente.')
      }
      form.resetFields()
      setDrawerOpen(false)
      setEditingUser(null)
      await loadData()
    } catch (requestError) {
      const resolved = applyFormApiError(form, requestError, {
        messageFieldMap: [
          { test: /rol asignado esta deshabilitado/i, field: 'role_code' },
        ],
        fallbackGlobalMessage: 'No fue posible guardar la información del usuario.',
      })
      setFormError(resolved.globalMessage)
    } finally {
      setSaving(false)
    }
  }

  const openCreate = () => {
    setEditingUser(null)
    setFormError(null)
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
      setFormError(null)
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

  const openView = async (record) => {
    try {
      const response = await apiClient.get(`/users/${record.user_id}`)
      setViewingUser(response.data)
    } catch (requestError) {
      message.error(requestError.response?.data?.detail || 'No fue posible cargar el detalle del usuario.')
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
          <Button icon={<EyeOutlined />} onClick={() => openView(record)}>
            Ver
          </Button>
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
          setFormError(null)
          form.resetFields()
        }}
        open={drawerOpen}
        destroyOnClose
      >
        <FormProcessAlert
          message={formError}
          title={editingUser ? 'No fue posible actualizar el usuario.' : 'No fue posible crear el usuario.'}
        />

        <Form {...FORM_COMMON_PROPS} form={form} onFinish={handleSubmitUser}>
          <Form.Item
            label="Nombres"
            name="nombres"
            rules={[{ required: true, message: 'Debe ingresar los nombres del usuario.' }]}
            extra="Escribe el nombre o los nombres tal como deben quedar registrados."
            normalize={(value) => (value || '').replace(/[^a-zA-ZáéíóúÁÉÍÓÚñÑ\s]/g, '').toUpperCase()}
          >
            <Input placeholder="Ej. MARÍA JOSÉ" />
          </Form.Item>

          <Form.Item
            label="Apellido paterno"
            name="apellido_paterno"
            rules={[{ required: true, message: 'Debe ingresar el apellido paterno del usuario.' }]}
            normalize={(value) => (value || '').replace(/[^a-zA-ZáéíóúÁÉÍÓÚñÑ\s]/g, '').toUpperCase()}
          >
            <Input placeholder="Ej. PÉREZ" />
          </Form.Item>

          <Form.Item
            label="Apellido materno"
            name="apellido_materno"
            extra="Opcional. Complétalo solo si aplica."
            normalize={(value) => (value || '').replace(/[^a-zA-ZáéíóúÁÉÍÓÚñÑ\s]/g, '').toUpperCase()}
          >
            <Input placeholder="Ej. GARCÍA" />
          </Form.Item>

          <Row gutter={12}>
            <Col span={12}>
              <Form.Item
                label="Cédula de identidad"
                name="ci"
                rules={[
                  { required: true, message: 'La Cédula de Identidad es obligatoria.' },
                  { min: 6, message: 'La Cédula de Identidad debe tener al menos 6 caracteres.' },
                ]}
                extra="Usa solo números y letras válidas del documento."
                normalize={(value) => (value || '').replace(/[^0-9A-Z]/g, '').toUpperCase()}
              >
                <Input placeholder="Ej. 1234567" />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item
                label="Celular"
                name="celular"
                rules={[
                  { required: true, message: 'El número de Celular es obligatorio.' },
                  { min: 8, message: 'El número de Celular debe tener al menos 8 dígitos.' },
                ]}
                extra="Ingresa un número activo para contacto operativo."
                normalize={(value) => (value || '').replace(/[^0-9]/g, '')}
              >
                <Input placeholder="Ej. 70000000" />
              </Form.Item>
            </Col>
          </Row>

          <Form.Item
            label="Correo electrónico"
            name="correo"
            rules={[
              { required: true, message: 'Debe ingresar el correo electrónico del usuario.' },
              { type: 'email', message: 'Debe ingresar un correo electrónico válido.' },
              {
                pattern: /^[a-zA-Z0-9._%+-]+@gmail\.com$/,
                message: 'Solo se permiten correos @gmail.com.',
              },
            ]}
            extra="Por política interna solo se aceptan correos con dominio @gmail.com."
            normalize={(value) => (value || '').replace(/\s/g, '').toLowerCase()}
          >
            <Input placeholder="usuario@gmail.com" />
          </Form.Item>

          <Form.Item
            label="Zona"
            name="zona"
            rules={[{ required: true, message: 'Debe ingresar la zona del usuario.' }]}
            extra="Describe la zona principal donde reside el usuario."
            normalize={(value) => (value || '').toUpperCase()}
          >
            <Input placeholder="Ej. VILLA FÁTIMA" />
          </Form.Item>

          <Form.Item
            label="Dirección"
            name="direccion"
            extra="Opcional. Agrega una referencia útil para ubicar al usuario."
            normalize={(value) => (value || '').toUpperCase()}
          >
            <Input.TextArea rows={2} placeholder="Ej. AV. PRINCIPAL, CALLE 10, CASA AZUL" />
          </Form.Item>

          <Form.Item
            label="Rol"
            name="role_code"
            rules={[{ required: true, message: 'Debe seleccionar el rol del usuario.' }]}
            extra="El rol define los permisos que tendrá el usuario dentro del sistema."
          >
            <Select options={roleOptions} placeholder="Selecciona el rol operativo" />
          </Form.Item>

          {editingUser ? (
            <Row gutter={12}>
              <Col span={12}>
                <Form.Item
                  label="Usuario activo"
                  name="user_is_active"
                  valuePropName="checked"
                  extra="Controla si la ficha personal del usuario permanece habilitada."
                >
                  <Switch />
                </Form.Item>
              </Col>
              <Col span={12}>
                <Form.Item
                  label="Cuenta activa"
                  name="account_is_active"
                  valuePropName="checked"
                  extra="Controla si puede iniciar sesión con su cuenta."
                >
                  <Switch />
                </Form.Item>
              </Col>
            </Row>
          ) : null}

          <Button {...FORM_DRAWER_SUBMIT_PROPS} loading={saving}>
            {editingUser ? 'Guardar cambios' : 'Guardar usuario'}
          </Button>
        </Form>
      </Drawer>

      <Modal
        title="Detalles del Usuario"
        open={!!viewingUser}
        onCancel={() => setViewingUser(null)}
        maskClosable={false}
        footer={[
          <Button key="close" onClick={() => setViewingUser(null)}>
            Cerrar
          </Button>,
        ]}
        width={700}
      >
        {viewingUser && (
          <Descriptions bordered column={2} size="small" layout="vertical">
            <Descriptions.Item label="Usuario (Login)">{viewingUser.username}</Descriptions.Item>
            <Descriptions.Item label="Nombre Completo">{viewingUser.nombres} {viewingUser.apellido_paterno} {viewingUser.apellido_materno}</Descriptions.Item>
            <Descriptions.Item label="Rol">{viewingUser.role_name}</Descriptions.Item>
            <Descriptions.Item label="Correo Electrónico">{viewingUser.correo}</Descriptions.Item>
            <Descriptions.Item label="Celular">{viewingUser.celular}</Descriptions.Item>
            <Descriptions.Item label="Cédula de Identidad">{viewingUser.ci || 'Ninguna'}</Descriptions.Item>
            <Descriptions.Item label="Zona">{viewingUser.zona || 'Ninguna'}</Descriptions.Item>
            <Descriptions.Item label="Dirección" span={2}>{viewingUser.direccion || 'Ninguna'}</Descriptions.Item>
            <Descriptions.Item label="Estado de Usuario">
              <Tag color={viewingUser.user_is_active ? 'green' : 'default'}>{viewingUser.user_is_active ? 'Activo' : 'Inactivo'}</Tag>
            </Descriptions.Item>
            <Descriptions.Item label="Estado de Cuenta">
              <Tag color={viewingUser.account_is_active ? 'blue' : 'default'}>{viewingUser.account_is_active ? 'Activa' : 'Inactiva'}</Tag>
            </Descriptions.Item>
            <Descriptions.Item label="Último Acceso" span={2}>
              {viewingUser.last_login_at ? new Date(viewingUser.last_login_at).toLocaleString() : 'Sin registro'}
            </Descriptions.Item>
          </Descriptions>
        )}
      </Modal>
    </div>
  )
}
