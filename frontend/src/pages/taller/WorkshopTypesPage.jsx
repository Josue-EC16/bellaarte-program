import { EditOutlined, PlusOutlined } from '@ant-design/icons'
import { Alert, App as AntdApp, Button, Drawer, Form, Input, Switch, Table, Tag, Typography } from 'antd'
import { useCallback, useEffect, useState } from 'react'

import { apiClient } from '../../api/client'
import { useAuth } from '../../auth/AuthProvider'
import { FORM_COMMON_PROPS, FORM_DRAWER_SUBMIT_PROPS } from '../../components/forms/formConfig'
import { applyFormApiError } from '../../components/forms/formErrorUtils'
import { FormProcessAlert } from '../../components/forms/FormProcessAlert'

export function WorkshopTypesPage() {
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

  const canCreate = user?.permissions?.includes('workshop_types:create')
  const canUpdate = user?.permissions?.includes('workshop_types:update')
  const canChangeStatus = user?.permissions?.includes('workshop_types:update_status')

  const loadTypes = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const response = await apiClient.get('/taller/types')
      setTypes(response.data)
    } catch (requestError) {
      setError(requestError.response?.data?.detail || 'No fue posible cargar los tipos de inventario del taller.')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    loadTypes()
  }, [loadTypes])

  const openCreate = () => {
    setEditingType(null)
    setFormError(null)
    form.resetFields()
    setDrawerOpen(true)
  }

  const openEdit = async (record) => {
    try {
      const response = await apiClient.get(`/taller/types/${record.id}`)
      const type = response.data
      setEditingType(type)
      setFormError(null)
      form.setFieldsValue({ nombre: type.nombre, descripcion: type.descripcion })
      setDrawerOpen(true)
    } catch (requestError) {
      message.error(requestError.response?.data?.detail || 'No fue posible cargar el tipo del taller.')
    }
  }

  const handleSubmit = async (values) => {
    setSaving(true)
    setFormError(null)
    try {
      if (editingType) {
        await apiClient.patch(`/taller/types/${editingType.id}`, values)
        message.success('Se guardaron los cambios del tipo de taller correctamente.')
      } else {
        await apiClient.post('/taller/types', values)
        message.success('Se creó el tipo de taller correctamente.')
      }
      setDrawerOpen(false)
      setEditingType(null)
      form.resetFields()
      await loadTypes()
    } catch (requestError) {
      const resolved = applyFormApiError(form, requestError, {
        fallbackGlobalMessage: 'No fue posible guardar el tipo de inventario del taller.',
      })
      setFormError(resolved.globalMessage)
    } finally {
      setSaving(false)
    }
  }

  const handleStatusChange = async (record, checked) => {
    try {
      await apiClient.patch(`/taller/types/${record.id}/status`, { habilitado: checked })
      message.success(`Tipo ${checked ? 'activado' : 'desactivado'} correctamente.`)
      await loadTypes()
    } catch (requestError) {
      message.error(requestError.response?.data?.detail || 'No fue posible cambiar el estado del tipo de taller.')
    }
  }

  const columns = [
    { title: 'Nombre', dataIndex: 'nombre', key: 'nombre' },
    { title: 'Descripción', dataIndex: 'descripcion', key: 'descripcion', render: (value) => value || 'SIN DESCRIPCIÓN' },
    {
      title: 'Estado',
      key: 'estado',
      render: (_, record) =>
        canChangeStatus ? (
          <Switch checked={record.habilitado} checkedChildren="Activo" unCheckedChildren="Inactivo" onChange={(checked) => handleStatusChange(record, checked)} />
        ) : (
          <Tag color={record.habilitado ? 'green' : 'default'}>{record.habilitado ? 'ACTIVO' : 'INACTIVO'}</Tag>
        ),
    },
    {
      title: 'Acciones',
      key: 'acciones',
      render: (_, record) => (canUpdate ? <Button icon={<EditOutlined />} onClick={() => openEdit(record)}>Editar</Button> : <Typography.Text type="secondary">Solo lectura</Typography.Text>),
    },
  ]

  return (
    <div>
      <div className="page-header">
        <div>
          <Typography.Title level={2} style={{ margin: 0 }}>Tipos Inventario Taller</Typography.Title>
          <Typography.Paragraph type="secondary" style={{ marginBottom: 0 }}>
            Administra las categorías base del inventario del taller.
          </Typography.Paragraph>
        </div>
        {canCreate ? <Button type="primary" icon={<PlusOutlined />} onClick={openCreate}>Nuevo tipo</Button> : null}
      </div>

      {error ? <Alert type="error" showIcon message={error} style={{ marginBottom: 16 }} /> : null}

      <Table className="glass-panel" rowKey="id" columns={columns} dataSource={types} loading={loading} pagination={{ pageSize: 8 }} />

      <Drawer
        title={editingType ? 'Editar Tipo de Inventario Taller' : 'Crear Tipo de Inventario Taller'}
        width={520}
        open={drawerOpen}
        onClose={() => {
          setDrawerOpen(false)
          setEditingType(null)
          setFormError(null)
          form.resetFields()
        }}
        destroyOnClose
        maskClosable={false}
      >
        <FormProcessAlert message={formError} title={editingType ? 'No fue posible actualizar el tipo.' : 'No fue posible crear el tipo.'} />
        <Form {...FORM_COMMON_PROPS} form={form} onFinish={handleSubmit}>
          <Form.Item label="Nombre" name="nombre" rules={[{ required: true, message: 'El Nombre del tipo es obligatorio.' }]} normalize={(value) => (value || '').toUpperCase()}>
            <Input placeholder="Ej. ENCAJE, TUL, FORRO O INSUMOS VARIOS" />
          </Form.Item>
          <Form.Item label="Descripción" name="descripcion" normalize={(value) => (value || '').toUpperCase()}>
            <Input.TextArea rows={3} placeholder="Ej. CATEGORÍA BASE PARA MATERIALES DE COSTURA Y PRODUCCIÓN" />
          </Form.Item>
          <Button {...FORM_DRAWER_SUBMIT_PROPS} loading={saving}>{editingType ? 'Guardar cambios' : 'Crear tipo'}</Button>
        </Form>
      </Drawer>
    </div>
  )
}
