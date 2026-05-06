import { EditOutlined, PlusOutlined } from '@ant-design/icons'
import { Alert, App as AntdApp, Button, Drawer, Form, Input, Switch, Table, Tag, Typography } from 'antd'
import { useEffect, useState } from 'react'

import { apiClient } from '../../api/client'
import { useAuth } from '../../auth/AuthProvider'
import {
  FORM_COMMON_PROPS,
  FORM_DRAWER_SUBMIT_PROPS,
} from '../../components/forms/formConfig'
import { applyFormApiError } from '../../components/forms/formErrorUtils'
import { FormProcessAlert } from '../../components/forms/FormProcessAlert'

export function RolesPage() {
  const [roles, setRoles] = useState([])
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState(null)
  const [formError, setFormError] = useState(null)
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
    setFormError(null)
    form.resetFields()
    setDrawerOpen(true)
  }

  const openEdit = (record) => {
    setEditingRole(record)
    setFormError(null)
    form.setFieldsValue({
      codigo: record.codigo,
      nombre: record.nombre,
      descripcion: record.descripcion,
    })
    setDrawerOpen(true)
  }

  const handleSubmit = async (values) => {
    setSaving(true)
    setFormError(null)
    try {
      if (editingRole) {
        await apiClient.patch(`/roles/${editingRole.id}`, {
          nombre: values.nombre,
          descripcion: values.descripcion,
        })
        message.success('Se guardaron los cambios del rol correctamente.')
      } else {
        await apiClient.post('/roles', values)
        message.success('Se creó el rol correctamente.')
      }
      setDrawerOpen(false)
      setEditingRole(null)
      form.resetFields()
      await loadRoles()
    } catch (requestError) {
      const resolved = applyFormApiError(form, requestError, {
        fallbackGlobalMessage: 'No fue posible guardar la información del rol.',
      })
      setFormError(resolved.globalMessage)
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
    { title: 'Código', dataIndex: 'codigo', key: 'codigo' },
    { title: 'Nombre', dataIndex: 'nombre', key: 'nombre' },
    { title: 'Descripción', dataIndex: 'descripcion', key: 'descripcion', render: (value) => value || 'Sin descripción' },
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
            Administra catálogo, estado y descripciones de roles operativos.
          </Typography.Paragraph>
        </div>

        {canCreate ? (
          <Button type="primary" icon={<PlusOutlined />} onClick={openCreate}>
            Nuevo Rol
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
          setFormError(null)
          form.resetFields()
        }}
        open={drawerOpen}
        destroyOnClose
      >
        <FormProcessAlert
          message={formError}
          title={editingRole ? 'No fue posible actualizar el rol.' : 'No fue posible crear el rol.'}
        />

        <Form {...FORM_COMMON_PROPS} form={form} onFinish={handleSubmit}>
          <Form.Item
            label="Código"
            name="codigo"
            rules={[{ required: true, message: 'Debe ingresar el código del rol.' }]}
            extra="Usa solo letras mayúsculas y guiones bajos. No se podrá cambiar después de crear."
            normalize={(value) => (value || '').toUpperCase().replace(/[^A-Z_]/g, '')}
          >
            <Input disabled={Boolean(editingRole)} placeholder="Ej. ADMIN o INV_BOUTIQUE" />
          </Form.Item>
          <Form.Item
            label="Nombre"
            name="nombre"
            rules={[{ required: true, message: 'Debe ingresar el nombre del rol.' }]}
            extra="Escribe un nombre claro para identificar la función operativa del rol."
            normalize={(value) => (value || '').replace(/[^a-zA-ZáéíóúÁÉÍÓÚñÑ\s]/g, '').toUpperCase()}
          >
            <Input placeholder="Ej. ADMINISTRACIÓN GENERAL" />
          </Form.Item>
          <Form.Item
            label="Descripción"
            name="descripcion"
            extra="Opcional. Describe brevemente las responsabilidades del rol."
            normalize={(value) => (value || '').toUpperCase()}
          >
            <Input.TextArea rows={3} placeholder="Ej. GESTIONA USUARIOS, ROLES Y CONFIGURACIONES CLAVE" />
          </Form.Item>
          <Button {...FORM_DRAWER_SUBMIT_PROPS} loading={saving}>
            {editingRole ? 'Guardar cambios' : 'Crear rol'}
          </Button>
        </Form>
      </Drawer>
    </div>
  )
}
