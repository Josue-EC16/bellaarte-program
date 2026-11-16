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
import { getSessionGeneration } from '../../api/tokenStore'
import { useAuth } from '../../auth/AuthProvider'
import {
  FORM_COMMON_PROPS,
  FORM_DRAWER_SUBMIT_PROPS,
} from '../../components/forms/formConfig'
import { applyFormApiError } from '../../components/forms/formErrorUtils'
import { FormProcessAlert } from '../../components/forms/FormProcessAlert'
import { collaboratorPayload, validCollaboratorCi, validateRequiredText } from './userValidation'

function actionError(error, fallback) {
  const detail = error.response?.data?.detail
  return typeof detail === 'string' ? detail : error.normalizedError?.summary || fallback
}

export function UsersPage() {
  const [users, setUsers] = useState([])
  const [roles, setRoles] = useState([])
  const [loading, setLoading] = useState(true)
  const [drawerOpen, setDrawerOpen] = useState(false)
  const [saving, setSaving] = useState(false)
  const [statusPending, setStatusPending] = useState(null)
  const [error, setError] = useState(null)
  const [formError, setFormError] = useState(null)
  const [editingUser, setEditingUser] = useState(null)
  const [viewingUser, setViewingUser] = useState(null)
  const [form] = Form.useForm()
  const { message, modal } = AntdApp.useApp()
  const { user, clearSession } = useAuth()

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
        disabled: !role.activo,
      })),
    [roles],
  )

  const handleSubmitUser = async (values) => {
    setSaving(true)
    setFormError(null)
    try {
      if (editingUser) {
        await apiClient.patch(`/users/${editingUser.id}`, collaboratorPayload(values))
        message.success('Se guardaron los cambios del usuario correctamente.')
      } else {
        await apiClient.post('/users', collaboratorPayload(values))
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
    if (record.id === user?.id || statusPending !== null) return
    setStatusPending(record.id)
    try {
      await apiClient.patch(`/users/${record.id}/status`, { is_active: nextStatus })
      message.success(`Cuenta ${nextStatus ? 'activada' : 'desactivada'} correctamente.`)
      await loadData()
    } catch (requestError) {
      message.error(actionError(requestError, 'No fue posible actualizar el estado.'))
    } finally {
      setStatusPending(null)
    }
  }

  const confirmResetPassword = (record) => {
    const generation = getSessionGeneration()
    modal.confirm({
      title: `¿Estás seguro que quieres restablecer la contraseña del usuario ${record.full_name} (${record.ci})?`,
      content: 'La clave temporal será la inicial del nombre + la inicial del apellido paterno + el CI, en mayúsculas. Se cerrarán todas las sesiones de esta cuenta y deberá cambiar la clave al ingresar.',
      okText: 'Sí',
      cancelText: 'No',
      onOk: async () => {
        if (generation !== getSessionGeneration()) return
        try {
          await apiClient.post(`/users/${record.id}/reset-password`, {}, { _sessionControl: record.id === user?.id })
          if (generation !== getSessionGeneration()) return
          message.success('Contraseña temporal restablecida correctamente.')
          if (record.id === user?.id) clearSession()
          else await loadData()
        } catch (requestError) {
          if (generation !== getSessionGeneration()) return
          message.error(actionError(requestError, 'No fue posible resetear la contraseña.'))
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
            disabled={record.id === user?.id || statusPending !== null}
            loading={statusPending === record.id}
            aria-label={`Estado de la cuenta ${record.username}${record.id === user?.id ? ' (tu cuenta)' : ''}`}
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
            Colaboradores
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
        maskClosable={false}
        closable={!saving}
        keyboard={!saving}
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
            rules={[{ required: true, whitespace: true, message: 'Debe ingresar los nombres del usuario.' },
              { validator: validateRequiredText({ name: true, min: 2 }) }]}
            extra="Escribe el nombre o los nombres tal como deben quedar registrados."
            normalize={(value) => (value || '').normalize('NFC').toUpperCase()}
          >
            <Input placeholder="Ej. MARÍA JOSÉ" />
          </Form.Item>

          <Form.Item
            label="Apellido paterno"
            name="apellido_paterno"
            rules={[{ required: true, whitespace: true, message: 'Debe ingresar el apellido paterno del usuario.' },
              { validator: validateRequiredText({ name: true, min: 2 }) }]}
            normalize={(value) => (value || '').normalize('NFC').toUpperCase()}
          >
            <Input placeholder="Ej. PÉREZ" />
          </Form.Item>

          <Form.Item
            label="Apellido materno"
            name="apellido_materno"
            extra="Opcional. Complétalo solo si aplica."
            normalize={(value) => (value || '').normalize('NFC').toUpperCase()}
            rules={[{ validator: (_, value) => !value?.trim()
              ? Promise.resolve() : validateRequiredText({ name: true, min: 1 })(_, value) }]}
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
                  { validator: (_, value) => validCollaboratorCi(value) ? Promise.resolve()
                    : Promise.reject(new Error('La Cédula de Identidad debe tener entre 7 y 30 dígitos, sin letras ni espacios.')) },
                ]}
                extra="Usa solo números. Se conservan los ceros iniciales."
              >
                <Input placeholder="Ej. 1234567" inputMode="numeric" maxLength={30} />
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
                <Input placeholder="Ej. 70000000" inputMode="numeric" maxLength={30} />
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
            normalize={(value) => (value || '').toLowerCase()}
          >
            <Input placeholder="usuario@gmail.com" />
          </Form.Item>

          <Form.Item
            label="Zona"
            name="zona"
            rules={[{ required: true, whitespace: true, message: 'Debe ingresar la zona del usuario.' },
              { validator: validateRequiredText({ min: 2 }) }]}
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
            extra={editingUser?.id === user?.id ? 'Otro ADMIN debe cambiar tu rol.' : 'El rol actualiza los permisos de las sesiones abiertas.'}
          >
            <Select options={roleOptions} placeholder="Selecciona el rol operativo" disabled={editingUser?.id === user?.id} />
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
                  <Switch disabled={editingUser?.id === user?.id} />
                </Form.Item>
              </Col>
              <Col span={12}>
                <Form.Item
                  label="Cuenta activa"
                  name="account_is_active"
                  valuePropName="checked"
                  extra="Controla si puede iniciar sesión con su cuenta."
                >
                  <Switch disabled={editingUser?.id === user?.id} />
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
