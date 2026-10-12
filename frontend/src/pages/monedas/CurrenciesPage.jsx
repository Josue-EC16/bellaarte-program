import { EditOutlined, PlusOutlined } from '@ant-design/icons'
import { Alert, App as AntdApp, Button, Drawer, Form, Input, Switch, Table, Tag, Typography } from 'antd'
import { useCallback, useEffect, useState } from 'react'

import { apiClient } from '../../api/client'
import { useAuth } from '../../auth/AuthProvider'
import { FORM_COMMON_PROPS, FORM_DRAWER_SUBMIT_PROPS } from '../../components/forms/formConfig'
import { applyFormApiError } from '../../components/forms/formErrorUtils'
import { FormProcessAlert } from '../../components/forms/FormProcessAlert'
import { ReportSummaryStrip } from '../../components/reports/ReportSummaryStrip'
import { useListingSummary } from '../../components/reports/useListingSummary'

export function CurrenciesPage() {
  const [currencies, setCurrencies] = useState([])
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState(null)
  const [formError, setFormError] = useState(null)
  const [drawerOpen, setDrawerOpen] = useState(false)
  const [editingCurrency, setEditingCurrency] = useState(null)
  const [form] = Form.useForm()
  const { message } = AntdApp.useApp()
  const { user } = useAuth()

  const canCreate = user?.permissions?.includes('currencies:create')
  const canUpdate = user?.permissions?.includes('currencies:update')
  const canChangeStatus = user?.permissions?.includes('currencies:update_status')
  const { summary, loading: summaryLoading } = useListingSummary('/monedas/resumen')

  const loadCurrencies = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const response = await apiClient.get('/monedas')
      setCurrencies(response.data)
    } catch (requestError) {
      setError(requestError.response?.data?.detail || 'No fue posible cargar las monedas.')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    loadCurrencies()
  }, [loadCurrencies])

  const openCreate = () => {
    setEditingCurrency(null)
    setFormError(null)
    form.resetFields()
    form.setFieldsValue({ habilitado: true, es_base: false })
    setDrawerOpen(true)
  }

  const openEdit = async (record) => {
    try {
      const response = await apiClient.get(`/monedas/${record.id}`)
      const currency = response.data
      setEditingCurrency(currency)
      setFormError(null)
      form.setFieldsValue({
        codigo: currency.codigo,
        nombre: currency.nombre,
        simbolo: currency.simbolo,
        es_base: currency.es_base,
        habilitado: currency.habilitado,
      })
      setDrawerOpen(true)
    } catch (requestError) {
      message.error(requestError.response?.data?.detail || 'No fue posible cargar la moneda.')
    }
  }

  const handleSubmit = async (values) => {
    setSaving(true)
    setFormError(null)
    try {
      if (editingCurrency) {
        await apiClient.patch(`/monedas/${editingCurrency.id}`, values)
        message.success('Se guardaron los cambios de la moneda correctamente.')
      } else {
        await apiClient.post('/monedas', values)
        message.success('Se creó la moneda correctamente.')
      }
      setDrawerOpen(false)
      setEditingCurrency(null)
      form.resetFields()
      await loadCurrencies()
    } catch (requestError) {
      const resolved = applyFormApiError(form, requestError, {
        messageFieldMap: [{ test: /moneda con ese código/i, field: 'codigo' }],
        fallbackGlobalMessage: 'No fue posible guardar la información de la moneda.',
      })
      setFormError(resolved.globalMessage)
    } finally {
      setSaving(false)
    }
  }

  const handleStatusChange = async (record, checked) => {
    try {
      await apiClient.patch(`/monedas/${record.id}/status`, { habilitado: checked })
      message.success(`Moneda ${checked ? 'activada' : 'desactivada'} correctamente.`)
      await loadCurrencies()
    } catch (requestError) {
      message.error(requestError.response?.data?.detail || 'No fue posible cambiar el estado de la moneda.')
    }
  }

  const columns = [
    { title: 'Código', dataIndex: 'codigo', key: 'codigo' },
    { title: 'Nombre', dataIndex: 'nombre', key: 'nombre' },
    { title: 'Símbolo', dataIndex: 'simbolo', key: 'simbolo', render: (value) => value || 'SIN REGISTRO' },
    { title: 'Base', dataIndex: 'es_base', key: 'es_base', render: (value) => value ? <Tag color="gold">BASE</Tag> : <Tag>NO</Tag> },
    {
      title: 'Estado',
      key: 'estado',
      render: (_, record) =>
        canChangeStatus ? (
          <Switch checked={record.habilitado} checkedChildren="Activa" unCheckedChildren="Inactiva" onChange={(checked) => handleStatusChange(record, checked)} />
        ) : (
          <Tag color={record.habilitado ? 'green' : 'default'}>{record.habilitado ? 'ACTIVA' : 'INACTIVA'}</Tag>
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
          <Typography.Title level={2} style={{ margin: 0 }}>Monedas</Typography.Title>
          <Typography.Paragraph type="secondary" style={{ marginBottom: 0 }}>
            Administra la moneda base del sistema y las monedas habilitadas para cobros.
          </Typography.Paragraph>
        </div>
        {canCreate ? <Button type="primary" icon={<PlusOutlined />} onClick={openCreate}>Nueva moneda</Button> : null}
      </div>

      {error ? <Alert type="error" showIcon message={error} style={{ marginBottom: 16 }} /> : null}
      <ReportSummaryStrip summary={summary} loading={summaryLoading} />

      <Table className="glass-panel" rowKey="id" columns={columns} dataSource={currencies} loading={loading} pagination={{ pageSize: 8 }} />

      <Drawer
        title={editingCurrency ? 'Editar Moneda' : 'Crear Moneda'}
        width={520}
        open={drawerOpen}
        onClose={() => {
          setDrawerOpen(false)
          setEditingCurrency(null)
          setFormError(null)
          form.resetFields()
        }}
        destroyOnClose
        maskClosable={false}
      >
        <FormProcessAlert message={formError} title={editingCurrency ? 'No fue posible actualizar la moneda.' : 'No fue posible crear la moneda.'} />
        <Form {...FORM_COMMON_PROPS} form={form} onFinish={handleSubmit}>
          <Form.Item label="Código" name="codigo" rules={[{ required: true, message: 'El Código de moneda es obligatorio.' }]} normalize={(value) => (value || '').replace(/[^a-zA-Z]/g, '').toUpperCase()}>
            <Input placeholder="Ej. BOB, USD, EUR O PEN" />
          </Form.Item>
          <Form.Item label="Nombre" name="nombre" rules={[{ required: true, message: 'El Nombre de moneda es obligatorio.' }]} normalize={(value) => (value || '').toUpperCase()}>
            <Input placeholder="Ej. BOLIVIANO, DÓLAR O EURO" />
          </Form.Item>
          <Form.Item label="Símbolo" name="simbolo">
            <Input placeholder="Ej. Bs, $, € o S/" />
          </Form.Item>
          <Form.Item label="Es moneda base" name="es_base" valuePropName="checked">
            <Switch checkedChildren="Sí" unCheckedChildren="No" />
          </Form.Item>
          <Form.Item label="Habilitada" name="habilitado" valuePropName="checked">
            <Switch checkedChildren="Sí" unCheckedChildren="No" />
          </Form.Item>
          <Button {...FORM_DRAWER_SUBMIT_PROPS} loading={saving}>
            {editingCurrency ? 'Guardar cambios' : 'Crear moneda'}
          </Button>
        </Form>
      </Drawer>
    </div>
  )
}
