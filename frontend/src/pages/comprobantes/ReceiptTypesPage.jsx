import { EditOutlined, PlusOutlined } from '@ant-design/icons'
import { Alert, App as AntdApp, Button, Drawer, Form, Switch, Table, Tag, Typography } from 'antd'
import { useEffect, useState } from 'react'

import { apiClient } from '../../api/client'
import { useAuth } from '../../auth/AuthProvider'
import { applyFormApiError } from '../../components/forms/formErrorUtils'
import { FormProcessAlert } from '../../components/forms/FormProcessAlert'
import { ReceiptTypeForm } from './ReceiptTypeForm'

const SYSTEM_RECEIPT_TYPE_NAMES = new Set([
  'VENTA_BOUTIQUE_INTERNO',
  'PAGO_PEDIDO_INTERNO',
  'FLETE_INTERNO',
])

function isSystemType(record) {
  return SYSTEM_RECEIPT_TYPE_NAMES.has(record.nombre)
}

export function ReceiptTypesPage() {
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

  const canCreate = user?.permissions?.includes('receipt_types:create')
  const canEdit = user?.permissions?.includes('receipt_types:update')
  const canChangeStatus = user?.permissions?.includes('receipt_types:update_status')

  const loadTypes = async () => {
    setLoading(true)
    setError(null)
    try {
      const response = await apiClient.get('/comprobantes/tipos')
      setTypes(response.data)
    } catch (requestError) {
      setError(requestError.response?.data?.detail || 'NO FUE POSIBLE CARGAR LOS TIPOS DE COMPROBANTE.')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadTypes()
  }, [])

  const resetDrawer = () => {
    setDrawerOpen(false)
    setEditingType(null)
    setFormError(null)
    form.resetFields()
  }

  const openCreate = () => {
    setEditingType(null)
    setFormError(null)
    form.setFieldsValue({
      nombre: undefined,
      descripcion: undefined,
      es_fiscal: false,
    })
    setDrawerOpen(true)
  }

  const openEdit = (record) => {
    setEditingType(record)
    setFormError(null)
    form.setFieldsValue({
      nombre: record.nombre,
      descripcion: record.descripcion,
      es_fiscal: record.es_fiscal,
    })
    setDrawerOpen(true)
  }

  const handleSubmit = async (values) => {
    setSaving(true)
    setFormError(null)
    try {
      if (editingType) {
        await apiClient.patch(`/comprobantes/tipos/${editingType.id}`, {
          descripcion: values.descripcion,
          es_fiscal: values.es_fiscal,
        })
        message.success('SE GUARDARON LOS CAMBIOS DEL TIPO DE COMPROBANTE.')
      } else {
        await apiClient.post('/comprobantes/tipos', values)
        message.success('SE CREÓ EL TIPO DE COMPROBANTE CORRECTAMENTE.')
      }
      resetDrawer()
      await loadTypes()
    } catch (requestError) {
      const resolved = applyFormApiError(form, requestError, {
        messageFieldMap: [
          { test: /tipo de comprobante con ese nombre/i, field: 'nombre' },
        ],
        fallbackGlobalMessage: 'NO FUE POSIBLE GUARDAR EL TIPO DE COMPROBANTE.',
      })
      setFormError(resolved.globalMessage)
    } finally {
      setSaving(false)
    }
  }

  const handleStatusChange = async (record, nextValue) => {
    try {
      await apiClient.patch(`/comprobantes/tipos/${record.id}/status`, { habilitado: nextValue })
      message.success(`TIPO DE COMPROBANTE ${nextValue ? 'ACTIVADO' : 'DESACTIVADO'} CORRECTAMENTE.`)
      await loadTypes()
    } catch (requestError) {
      message.error(requestError.response?.data?.detail || 'NO FUE POSIBLE CAMBIAR EL ESTADO DEL TIPO DE COMPROBANTE.')
    }
  }

  const columns = [
    {
      title: 'NOMBRE TÉCNICO',
      dataIndex: 'nombre',
      key: 'nombre',
      render: (value, record) => (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
          <span>{value}</span>
          {isSystemType(record) ? <Tag color="geekblue">BASE DEL SISTEMA</Tag> : <Tag>CUSTOM</Tag>}
        </div>
      ),
    },
    {
      title: 'DESCRIPCIÓN',
      dataIndex: 'descripcion',
      key: 'descripcion',
      render: (value) => value || 'SIN DESCRIPCIÓN',
    },
    {
      title: 'NATURALEZA',
      dataIndex: 'es_fiscal',
      key: 'es_fiscal',
      render: (value) => <Tag color={value ? 'gold' : 'purple'}>{value ? 'FISCAL' : 'NO FISCAL'}</Tag>,
    },
    {
      title: 'ESTADO',
      key: 'estado',
      render: (_, record) =>
        canChangeStatus ? (
          <Switch
            checked={record.habilitado}
            checkedChildren="ACTIVO"
            unCheckedChildren="INACTIVO"
            disabled={isSystemType(record)}
            onChange={(checked) => handleStatusChange(record, checked)}
          />
        ) : (
          <Tag color={record.habilitado ? 'green' : 'default'}>{record.habilitado ? 'ACTIVO' : 'INACTIVO'}</Tag>
        ),
    },
    {
      title: 'REGISTRO',
      dataIndex: 'fecha_registro',
      key: 'fecha_registro',
      render: (value) => new Date(value).toLocaleString('es-BO'),
    },
    {
      title: 'ACCIONES',
      key: 'acciones',
      render: (_, record) =>
        canEdit ? (
          <Button icon={<EditOutlined />} onClick={() => openEdit(record)}>
            Editar
          </Button>
        ) : (
          <Typography.Text type="secondary">SOLO LECTURA</Typography.Text>
        ),
    },
  ]

  return (
    <div>
      <div className="page-header">
        <div>
          <Typography.Title level={2} style={{ margin: 0 }}>
            Tipos de Comprobante
          </Typography.Title>
          <Typography.Paragraph type="secondary" style={{ marginBottom: 0 }}>
            Administra el catálogo técnico de tipos de comprobante interno y protege los tipos base de emisión automática.
          </Typography.Paragraph>
        </div>

        {canCreate ? (
          <Button type="primary" icon={<PlusOutlined />} onClick={openCreate}>
            Nuevo tipo
          </Button>
        ) : null}
      </div>

      <Alert
        type="info"
        showIcon
        style={{ marginBottom: 16 }}
        message="LOS TIPOS BASE DEL SISTEMA NO SE PUEDEN DESACTIVAR"
        description="VENTA_BOUTIQUE_INTERNO, PAGO_PEDIDO_INTERNO y FLETE_INTERNO se usan para la emisión automática de comprobantes."
      />

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
        title={editingType ? 'Editar tipo de comprobante' : 'Crear tipo de comprobante'}
        width={460}
        open={drawerOpen}
        onClose={resetDrawer}
        destroyOnClose
        maskClosable={false}
      >
        <FormProcessAlert
          message={formError}
          title={editingType ? 'No fue posible actualizar el tipo de comprobante.' : 'No fue posible crear el tipo de comprobante.'}
        />
        <ReceiptTypeForm
          form={form}
          onFinish={handleSubmit}
          saving={saving}
          submitLabel={editingType ? 'Guardar cambios' : 'Crear tipo'}
          editingType={editingType}
          isSystemType={isSystemType}
        />
      </Drawer>
    </div>
  )
}
