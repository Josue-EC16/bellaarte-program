import { EditOutlined } from '@ant-design/icons'
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

  const openEdit = (record) => {
    setEditingRole(record)
    setFormError(null)
    form.setFieldsValue({
      nombre: record.nombre,
      descripcion: record.descripcion,
    })
    setDrawerOpen(true)
  }

  const handleSubmit = async (values) => {
    if (!editingRole) return
    setSaving(true)
    setFormError(null)
    try {
      await apiClient.patch(`/roles/${editingRole.id}`, {
        nombre: values.nombre,
        descripcion: values.descripcion,
      })
      message.success('Se guardaron los cambios del rol correctamente.')
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
      render: (value) =>
        value
          ? new Date(value).toLocaleString('es-BO', {
              year: 'numeric',
              month: 'numeric',
              day: 'numeric',
              hour: '2-digit',
              minute: '2-digit',
            })
          : 'Sin dato',
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
            Roles del Sistema
          </Typography.Title>
          <Typography.Paragraph type="secondary" style={{ marginBottom: 0 }}>
          </Typography.Paragraph>
        </div>

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
        title="Editar rol"
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
          title="No fue posible actualizar el rol."
        />

        <Form {...FORM_COMMON_PROPS} form={form} onFinish={handleSubmit}>
          <Form.Item
            label="Nombre"
            name="nombre"
            rules={[{ required: true, message: 'Debe ingresar el nombre del rol.' }]}
            normalize={(value) => (value || '').replace(/[^a-zA-ZáéíóúÁÉÍÓÚñÑ\s]/g, '').toUpperCase()}
          >
            <Input placeholder="Ej. ADMINISTRACIÓN GENERAL" />
          </Form.Item>
          <Form.Item
            label="Descripción"
            name="descripcion"
            normalize={(value) => (value || '').toUpperCase()}
          >
            <Input.TextArea rows={3} placeholder="Ej. GESTIONA USUARIOS, ROLES Y CONFIGURACIONES CLAVE" />
          </Form.Item>
          <Button {...FORM_DRAWER_SUBMIT_PROPS} loading={saving}>
            Guardar cambios
          </Button>
        </Form>
      </Drawer>
    </div>
  )
}
