import { EditOutlined, PlusOutlined } from '@ant-design/icons'
import { Alert, App as AntdApp, Button, Drawer, Form, Input, InputNumber, Row, Col, Select, Switch, Table, Tag, Typography } from 'antd'
import { useCallback, useEffect, useMemo, useState } from 'react'

import { apiClient } from '../../api/client'
import { useAuth } from '../../auth/AuthProvider'
import { FORM_COMMON_PROPS, FORM_DRAWER_SUBMIT_PROPS } from '../../components/forms/formConfig'
import { applyFormApiError } from '../../components/forms/formErrorUtils'
import { FormProcessAlert } from '../../components/forms/FormProcessAlert'
import { ReportSummaryStrip } from '../../components/reports/ReportSummaryStrip'
import { useListingSummary } from '../../components/reports/useListingSummary'

export function ExchangeRatesPage() {
  const [rates, setRates] = useState([])
  const [currencies, setCurrencies] = useState([])
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState(null)
  const [formError, setFormError] = useState(null)
  const [drawerOpen, setDrawerOpen] = useState(false)
  const [editingRate, setEditingRate] = useState(null)
  const [filters, setFilters] = useState({ moneda_id: undefined, is_active: undefined })
  const [form] = Form.useForm()
  const { message } = AntdApp.useApp()
  const { user } = useAuth()

  const canCreate = user?.permissions?.includes('exchange_rates:create')
  const canUpdate = user?.permissions?.includes('exchange_rates:update')
  const canChangeStatus = user?.permissions?.includes('exchange_rates:update_status')
  const { summary, loading: summaryLoading } = useListingSummary('/monedas/tipos-cambio/resumen', filters)

  const loadCurrencies = useCallback(async () => {
    const response = await apiClient.get('/monedas')
    setCurrencies(response.data)
  }, [])

  const loadRates = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const params = {}
      if (filters.moneda_id) params.moneda_id = filters.moneda_id
      if (filters.is_active !== undefined) params.is_active = filters.is_active
      const response = await apiClient.get('/monedas/tipos-cambio', { params })
      setRates(response.data)
    } catch (requestError) {
      setError(requestError.response?.data?.detail || 'No fue posible cargar los tipos de cambio.')
    } finally {
      setLoading(false)
    }
  }, [filters])

  useEffect(() => {
    Promise.all([loadCurrencies(), loadRates()]).catch(() => {
      setError('No fue posible cargar la información inicial de tipos de cambio.')
      setLoading(false)
    })
  }, [loadCurrencies, loadRates])

  useEffect(() => {
    loadRates()
  }, [loadRates])

  const currencyOptions = useMemo(
    () => currencies.map((currency) => ({ label: `${currency.codigo} - ${currency.nombre}`, value: currency.id })),
    [currencies],
  )

  const openCreate = () => {
    setEditingRate(null)
    setFormError(null)
    form.resetFields()
    form.setFieldsValue({ activo: true })
    setDrawerOpen(true)
  }

  const openEdit = async (record) => {
    try {
      const response = await apiClient.get(`/monedas/tipos-cambio/${record.id}`)
      const rate = response.data
      setEditingRate(rate)
      setFormError(null)
      form.setFieldsValue({
        moneda_id: rate.moneda.id,
        valor_bob: rate.valor_bob,
        observaciones: rate.observaciones,
        activo: rate.activo,
      })
      setDrawerOpen(true)
    } catch (requestError) {
      message.error(requestError.response?.data?.detail || 'No fue posible cargar el tipo de cambio.')
    }
  }

  const handleSubmit = async (values) => {
    setSaving(true)
    setFormError(null)
    try {
      if (editingRate) {
        await apiClient.patch(`/monedas/tipos-cambio/${editingRate.id}`, {
          valor_bob: values.valor_bob,
          observaciones: values.observaciones,
          activo: values.activo,
        })
        message.success('Se guardaron los cambios del tipo de cambio correctamente.')
      } else {
        await apiClient.post('/monedas/tipos-cambio', values)
        message.success('Se creó el tipo de cambio correctamente.')
      }
      setDrawerOpen(false)
      setEditingRate(null)
      form.resetFields()
      await loadRates()
    } catch (requestError) {
      const resolved = applyFormApiError(form, requestError, {
        fallbackGlobalMessage: 'No fue posible guardar la información del tipo de cambio.',
      })
      setFormError(resolved.globalMessage)
    } finally {
      setSaving(false)
    }
  }

  const handleStatusChange = async (record, checked) => {
    try {
      await apiClient.patch(`/monedas/tipos-cambio/${record.id}/status`, { activo: checked })
      message.success(`Tipo de cambio ${checked ? 'activado' : 'desactivado'} correctamente.`)
      await loadRates()
    } catch (requestError) {
      message.error(requestError.response?.data?.detail || 'No fue posible cambiar el estado del tipo de cambio.')
    }
  }

  const columns = [
    { title: 'Moneda', dataIndex: 'moneda_codigo', key: 'moneda_codigo' },
    { title: 'Nombre', dataIndex: 'moneda_nombre', key: 'moneda_nombre' },
    { title: 'Valor en Bs.', dataIndex: 'valor_bob', key: 'valor_bob' },
    { title: 'Registrado por', dataIndex: 'registrado_por', key: 'registrado_por' },
    { title: 'Fecha', dataIndex: 'fecha_registro', key: 'fecha_registro', render: (value) => new Date(value).toLocaleString() },
    {
      title: 'Estado',
      key: 'estado',
      render: (_, record) =>
        canChangeStatus ? (
          <Switch checked={record.activo} checkedChildren="Activo" unCheckedChildren="Inactivo" onChange={(checked) => handleStatusChange(record, checked)} />
        ) : (
          <Tag color={record.activo ? 'green' : 'default'}>{record.activo ? 'ACTIVO' : 'INACTIVO'}</Tag>
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
          <Typography.Title level={2} style={{ margin: 0 }}>Tipos de Cambio</Typography.Title>
          <Typography.Paragraph type="secondary" style={{ marginBottom: 0 }}>
            Gestiona el valor vigente de cada moneda respecto al boliviano.
          </Typography.Paragraph>
        </div>
        {canCreate ? <Button type="primary" icon={<PlusOutlined />} onClick={openCreate}>Nuevo tipo de cambio</Button> : null}
      </div>

      <div className="glass-panel boutique-filter-bar">
        <Row gutter={[12, 12]}>
          <Col xs={24} md={12}>
            <Select
              allowClear
              showSearch
              optionFilterProp="label"
              placeholder="Filtrar por moneda"
              options={currencyOptions}
              value={filters.moneda_id}
              onChange={(value) => setFilters((current) => ({ ...current, moneda_id: value }))}
              style={{ width: '100%' }}
            />
          </Col>
          <Col xs={24} md={12}>
            <Select
              allowClear
              placeholder="Estado"
              value={filters.is_active}
              onChange={(value) => setFilters((current) => ({ ...current, is_active: value }))}
              options={[{ label: 'Activos', value: true }, { label: 'Inactivos', value: false }]}
              style={{ width: '100%' }}
            />
          </Col>
        </Row>
      </div>

      {error ? <Alert type="error" showIcon message={error} style={{ marginBottom: 16 }} /> : null}
      <ReportSummaryStrip summary={summary} loading={summaryLoading} />

      <Table className="glass-panel" rowKey="id" columns={columns} dataSource={rates} loading={loading} pagination={{ pageSize: 8 }} />

      <Drawer
        title={editingRate ? 'Editar Tipo de Cambio' : 'Crear Tipo de Cambio'}
        width={560}
        open={drawerOpen}
        onClose={() => {
          setDrawerOpen(false)
          setEditingRate(null)
          setFormError(null)
          form.resetFields()
        }}
        destroyOnClose
        maskClosable={false}
      >
        <FormProcessAlert message={formError} title={editingRate ? 'No fue posible actualizar el tipo de cambio.' : 'No fue posible crear el tipo de cambio.'} />
        <Form {...FORM_COMMON_PROPS} form={form} onFinish={handleSubmit}>
          <Form.Item label="Moneda" name="moneda_id" rules={[{ required: true, message: 'Debe seleccionar la Moneda.' }]}>
            <Select disabled={Boolean(editingRate)} showSearch optionFilterProp="label" placeholder="Seleccionar moneda" options={currencyOptions} />
          </Form.Item>
          <Form.Item
            label="Valor en Bs."
            name="valor_bob"
            rules={[{ required: true, message: 'El Valor en Bs. es obligatorio.' }]}
            normalize={(value) => {
              if (value === null || value === undefined || value === '') return null
              return value.toString().replace(/[^0-9.]/g, '')
            }}
          >
            <InputNumber min={0.0001} precision={4} style={{ width: '100%' }} placeholder="Ej. 6.9600" />
          </Form.Item>
          <Form.Item label="Observaciones" name="observaciones" normalize={(value) => (value || '').toUpperCase()}>
            <Input.TextArea rows={3} placeholder="Ej. TIPO DE CAMBIO REFERENCIAL DEL DÍA" />
          </Form.Item>
          <Form.Item label="Activo" name="activo" valuePropName="checked">
            <Switch checkedChildren="Sí" unCheckedChildren="No" />
          </Form.Item>
          <Button {...FORM_DRAWER_SUBMIT_PROPS} loading={saving}>
            {editingRate ? 'Guardar cambios' : 'Crear tipo de cambio'}
          </Button>
        </Form>
      </Drawer>
    </div>
  )
}
