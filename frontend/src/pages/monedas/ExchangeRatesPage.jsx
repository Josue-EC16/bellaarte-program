import { EditOutlined, PlusOutlined } from '@ant-design/icons'
import { Alert, App as AntdApp, Button, Drawer, Form, Input, InputNumber, Row, Col, Select, Space, Table, Tag, Typography } from 'antd'
import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { useInRouterContext } from 'react-router-dom'

import { apiClient } from '../../api/client'
import { useAuth } from '../../auth/AuthProvider'
import { FORM_COMMON_PROPS, FORM_DRAWER_SUBMIT_PROPS } from '../../components/forms/formConfig'
import { applyFormApiError } from '../../components/forms/formErrorUtils'
import { FormProcessAlert } from '../../components/forms/FormProcessAlert'
import { ReportSummaryStrip } from '../../components/reports/ReportSummaryStrip'
import { useListingSummary } from '../../components/reports/useListingSummary'
import { canDeactivateRate, exchangeRateActionError, exchangeRatePayload, exchangeRateText, isManualRate, isValidExchangeRate } from './exchangeRateUtils'
import { ExchangeRateSyncStatus } from './ExchangeRateSyncStatus'
import { ExchangeRateLinkDetail } from './ExchangeRateLinkDetail'
import { canReadSyncRecords } from './exchangeRateSyncUtils'
import { useExchangeRateSyncStatus } from './useExchangeRateSyncStatus'

export function ExchangeRatesPage() {
  const [rates, setRates] = useState([])
  const [currencies, setCurrencies] = useState([])
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState(null)
  const [formError, setFormError] = useState(null)
  const [drawerOpen, setDrawerOpen] = useState(false)
  const [editingRate, setEditingRate] = useState(null)
  const [statusPending, setStatusPending] = useState(null)
  const rawRateValue = useRef(null)
  const submitting = useRef(false)
  const [filters, setFilters] = useState({ moneda_id: undefined, is_active: undefined })
  const [form] = Form.useForm()
  const { message } = AntdApp.useApp()
  const { user } = useAuth()
  const inRouter = useInRouterContext()
  const sync = useExchangeRateSyncStatus()
  const previousOperationalId = useRef(undefined)

  const canCreate = user?.permissions?.includes('exchange_rates:create')
  const canUpdate = user?.permissions?.includes('exchange_rates:update')
  const canChangeStatus = user?.permissions?.includes('exchange_rates:update_status')
  const { summary, loading: summaryLoading, reload: reloadSummary } = useListingSummary('/monedas/tipos-cambio/resumen', filters)

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
      setError(exchangeRateActionError(requestError, 'No fue posible cargar los tipos de cambio.'))
    } finally {
      setLoading(false)
    }
  }, [filters])

  useEffect(() => {
    loadCurrencies().catch(() => {
      setError('No fue posible cargar la información inicial de tipos de cambio.')
      setLoading(false)
    })
  }, [loadCurrencies])

  useEffect(() => {
    loadRates()
  }, [loadRates])

  const operationalId = sync.data?.operational_rate?.id
  const hasSyncData = Boolean(sync.data)
  useEffect(() => {
    if (!hasSyncData) return
    const currentId = operationalId ?? null
    if (previousOperationalId.current !== undefined && currentId !== previousOperationalId.current) {
      loadRates()
      reloadSummary()
    }
    previousOperationalId.current = currentId
  }, [hasSyncData, operationalId, loadRates, reloadSummary])

  const currencyOptions = useMemo(
    () => currencies.map((currency) => ({ label: `${currency.codigo} - ${currency.nombre}`, value: currency.id })),
    [currencies],
  )

  const openCreate = () => {
    setEditingRate(null)
    setFormError(null)
    form.resetFields()
    rawRateValue.current = null
    setDrawerOpen(true)
  }

  const openEdit = async (record) => {
    try {
      const response = await apiClient.get(`/monedas/tipos-cambio/${record.id}`)
      const rate = response.data
      if (!isManualRate(rate)) {
        message.error('Las cotizaciones automáticas son de solo lectura.')
        return
      }
      setEditingRate(rate)
      setFormError(null)
      form.setFieldsValue({
        moneda_id: rate.moneda.id,
        valor_bob: exchangeRateText(rate.valor_bob),
        observaciones: rate.observaciones,
      })
      rawRateValue.current = null
      setDrawerOpen(true)
    } catch (requestError) {
      message.error(exchangeRateActionError(requestError, 'No fue posible cargar el tipo de cambio.'))
    }
  }

  const handleSubmit = async (values) => {
    if (submitting.current) return
    if (!isValidExchangeRate(exchangeRateText(values.valor_bob)) ||
      (rawRateValue.current !== null && !isValidExchangeRate(rawRateValue.current))) {
      form.setFields([{ name: 'valor_bob', errors: ['Ingresa un valor positivo de hasta ocho enteros y cuatro decimales.'] }])
      return
    }
    submitting.current = true
    setSaving(true)
    setFormError(null)
    try {
      if (editingRate) {
        const response = await apiClient.patch(`/monedas/tipos-cambio/${editingRate.id}`, exchangeRatePayload(values, { editing: true }))
        message.success(response.data.id !== editingRate.id
          ? 'Se registró una nueva cotización activa. La cotización anterior se conserva en el historial.'
          : 'Se actualizaron las observaciones de la cotización.')
      } else {
        await apiClient.post('/monedas/tipos-cambio', exchangeRatePayload(values))
        message.success('Se creó una nueva cotización activa para esta moneda.')
      }
      setDrawerOpen(false)
      setEditingRate(null)
      form.resetFields()
      await loadRates()
      await reloadSummary()
      await sync.reload({ force: true })
    } catch (requestError) {
      const resolved = applyFormApiError(form, requestError, {
        fallbackGlobalMessage: 'No fue posible guardar la información del tipo de cambio.',
      })
      setFormError(resolved.globalMessage)
    } finally {
      submitting.current = false
      setSaving(false)
    }
  }

  const handleDeactivate = async (record) => {
    if (!canDeactivateRate(record) || statusPending !== null) return
    setStatusPending(record.id)
    try {
      await apiClient.patch(`/monedas/tipos-cambio/${record.id}/status`, { activo: false })
      message.success('Tipo de cambio desactivado. Para recuperar su valor, registra una nueva cotización.')
      await loadRates()
      await reloadSummary()
      await sync.reload({ force: true })
    } catch (requestError) {
      message.error(exchangeRateActionError(requestError, 'No fue posible cambiar el estado del tipo de cambio.'))
    } finally {
      setStatusPending(null)
    }
  }

  const columns = [
    { title: 'Moneda', dataIndex: 'moneda_codigo', key: 'moneda_codigo' },
    { title: 'Nombre', dataIndex: 'moneda_nombre', key: 'moneda_nombre' },
    { title: 'Valor en Bs.', dataIndex: 'valor_bob', key: 'valor_bob' },
    { title: 'Origen', dataIndex: 'origen', key: 'origen', render: (value) => value === 'AUTOMATICO' ? 'AUTOMÁTICO' : value },
    { title: 'Registrado por', dataIndex: 'registrado_por', key: 'registrado_por' },
    { title: 'Registro', dataIndex: 'fecha_registro', key: 'fecha_registro', render: (value) => new Date(value).toLocaleString() },
    {
      title: 'Estado',
      key: 'estado',
      render: (_, record) => <Tag color={record.activo ? 'green' : 'default'}>{record.activo ? 'ACTIVO' : 'INACTIVO'}</Tag>,
    },
    {
      title: 'Acciones',
      key: 'acciones',
      render: (_, record) => (
        <Space wrap>
          {canUpdate && isManualRate(record) ? <Button icon={<EditOutlined />} onClick={() => openEdit(record)}>Editar</Button> : null}
          {canChangeStatus && canDeactivateRate(record)
            ? <Button danger loading={statusPending === record.id} disabled={statusPending !== null} onClick={() => handleDeactivate(record)}>Desactivar</Button> : null}
          {(!isManualRate(record) || (!canUpdate && !canChangeStatus)) ? <Typography.Text type="secondary">Solo lectura</Typography.Text> : null}
        </Space>
      ),
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

      <ExchangeRateSyncStatus {...sync} onReload={sync.reload} recordsLink={canReadSyncRecords(user)} />
      {inRouter ? <ExchangeRateLinkDetail /> : null}

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
      <Typography.Paragraph type="secondary">
        Una nueva cotización manual queda activa. Los registros anteriores conservan su valor y no se pueden reactivar; para recuperar un valor, crea una nueva cotización.
      </Typography.Paragraph>

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
        {editingRate ? <Alert type="info" showIcon message="Cambiar el valor creará una nueva cotización activa. Si conservas el valor, solo se actualizarán las observaciones." style={{ marginBottom: 16 }} /> : null}
        <Form {...FORM_COMMON_PROPS} form={form} onFinish={handleSubmit}>
          <Form.Item label="Moneda" name="moneda_id" rules={[{ required: true, message: 'Debe seleccionar la Moneda.' }]}>
            <Select disabled={Boolean(editingRate)} showSearch optionFilterProp="label" placeholder="Seleccionar moneda" options={currencyOptions} />
          </Form.Item>
          <Form.Item
            label="Valor en Bs."
            name="valor_bob"
            rules={[{ required: true, message: 'El Valor en Bs. es obligatorio.' }, {
              validator: (_, value) => isValidExchangeRate(exchangeRateText(value)) &&
                (rawRateValue.current === null || isValidExchangeRate(rawRateValue.current))
                ? Promise.resolve() : Promise.reject(new Error('Ingresa un valor positivo de hasta ocho enteros y cuatro decimales.')),
            }]}
          >
            <InputNumber stringMode min="0.0001" max="99999999.9999" precision={4} changeOnBlur={false}
              onInput={(value) => { rawRateValue.current = value }}
              style={{ width: '100%' }} placeholder="Ej. 6.9600" />
          </Form.Item>
          <Form.Item label="Observaciones" name="observaciones" normalize={(value) => (value || '').toUpperCase()}>
            <Input.TextArea rows={3} placeholder="Ej. TIPO DE CAMBIO REFERENCIAL DEL DÍA" />
          </Form.Item>
          <Button {...FORM_DRAWER_SUBMIT_PROPS} loading={saving}>
            {editingRate ? 'Guardar cambios' : 'Crear tipo de cambio'}
          </Button>
        </Form>
      </Drawer>
    </div>
  )
}
