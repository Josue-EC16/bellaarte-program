import { EditOutlined, PlusOutlined } from '@ant-design/icons'
import { Alert, App as AntdApp, Button, Drawer, Form, Switch, Table, Tag, Typography } from 'antd'
import { useEffect, useState } from 'react'

import { apiClient } from '../../api/client'
import { useAuth } from '../../auth/AuthProvider'
import { applyFormApiError } from '../../components/forms/formErrorUtils'
import { FormProcessAlert } from '../../components/forms/FormProcessAlert'
import { BoutiqueTypeForm } from './BoutiqueTypeForm'

export function BoutiqueTypesPage() {
  const [types, setTypes] = useState([])
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState(null)
  const [formError, setFormError] = useState(null)
  const [drawerOpen, setDrawerOpen] = useState(false)
  const [editingType, setEditingType] = useState(null)
  const [form] = Form.useForm()
  const { message } = AntdApp.useApp()
  const { user } = useAuth()

  const canEdit = user?.permissions?.includes('boutique_types:update')
  const canCreate = user?.permissions?.includes('boutique_types:create')
  const canChangeStatus = user?.permissions?.includes('boutique_types:update_status')

  const loadTypes = async () => {
    setLoading(true)
    setError(null)
    try {
      const response = await apiClient.get('/boutique/types')
      setTypes(response.data)
    } catch (requestError) {
      setError(requestError.response?.data?.detail || 'No fue posible cargar los Tipos de Categoría.')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadTypes()
  }, [])

  const openCreate = () => {
    setEditingType(null)
    setFormError(null)
    form.resetFields()
    setDrawerOpen(true)
  }

  const openEdit = (record) => {
    setEditingType(record)
    setFormError(null)
    form.setFieldsValue({
      nombre: record.nombre,
      descripcion: record.descripcion,
    })
    setDrawerOpen(true)
  }

  const handleSubmit = async (values) => {
    setSaving(true)
    setFormError(null)
    try {
      if (editingType) {
        await apiClient.patch(`/boutique/types/${editingType.id}`, values)
        message.success('Se guardaron los cambios del tipo correctamente.')
      } else {
        await apiClient.post('/boutique/types', values)
        message.success('Se creó el tipo correctamente.')
      }
      setDrawerOpen(false)
      setEditingType(null)
      form.resetFields()
      await loadTypes()
    } catch (requestError) {
      const resolved = applyFormApiError(form, requestError, {
        messageFieldMap: [
          { test: /tipo boutique con ese nombre/i, field: 'nombre' },
        ],
        fallbackGlobalMessage: 'No fue posible guardar la información del tipo.',
      })
      setFormError(resolved.globalMessage)
    } finally {
      setSaving(false)
    }
  }

  const handleStatusChange = async (record, nextValue) => {
    try {
      await apiClient.patch(`/boutique/types/${record.id}/status`, { habilitado: nextValue })
      message.success(`Tipo ${nextValue ? 'activado' : 'desactivado'} correctamente.`)
      await loadTypes()
    } catch (requestError) {
      message.error(requestError.response?.data?.detail || 'No fue posible cambiar el estado del tipo.')
    }
  }

  const columns = [
    { title: 'Nombre', dataIndex: 'nombre', key: 'nombre' },
    {
      title: 'Descripción',
      dataIndex: 'descripcion',
      key: 'descripcion',
      render: (value) => value || 'Sin descripción',
    },
    {
      title: 'Estado',
      key: 'estado',
      render: (_, record) =>
        canChangeStatus ? (
          <Switch
            checked={record.habilitado}
            checkedChildren="Activo"
            unCheckedChildren="Inactivo"
            onChange={(checked) => handleStatusChange(record, checked)}
          />
        ) : (
          <Tag color={record.habilitado ? 'green' : 'default'}>{record.habilitado ? 'Activo' : 'Inactivo'}</Tag>
        ),
    },
    {
      title: 'Registro',
      dataIndex: 'fecha_registro',
      key: 'fecha_registro',
      render: (value) => new Date(value).toLocaleString(),
    },
    {
      title: 'Acciones',
      key: 'acciones',
      render: (_, record) =>
        canEdit ? (
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
            Categorías Productos
          </Typography.Title>
          <Typography.Paragraph type="secondary" style={{ marginBottom: 0 }}>
            Administra el catálogo base de clasificaciones del inventario boutique.
          </Typography.Paragraph>
        </div>

        {canCreate ? (
          <Button type="primary" icon={<PlusOutlined />} onClick={openCreate}>
            Nuevo tipo
          </Button>
        ) : null}
      </div>

      {error ? <Alert type="error" showIcon message={error} style={{ marginBottom: 16 }} /> : null}

      <Table
        className="glass-panel"
        rowKey="id"
        columns={columns}
        dataSource={types}
        loading={loading}
        pagination={{ pageSize: 8 }}
        style={{ borderRadius: 24, overflow: 'hidden' }}
      />

      <Drawer
        title={editingType ? 'Editar Tipos de Categoria' : 'Crear Tipos de Categoria'}
        width={420}
        open={drawerOpen}
        onClose={() => {
          setDrawerOpen(false)
          setEditingType(null)
          setFormError(null)
          form.resetFields()
        }}
        destroyOnClose
      >
        <FormProcessAlert
          message={formError}
          title={editingType ? 'No fue posible actualizar el tipo.' : 'No fue posible crear el tipo.'}
        />
        <BoutiqueTypeForm
          form={form}
          onFinish={handleSubmit}
          saving={saving}
          submitLabel={editingType ? 'Guardar cambios' : 'Crear tipo'}
        />
      </Drawer>
    </div>
  )
}
