/* eslint-disable react-hooks/exhaustive-deps */
import { CheckCircleOutlined, EyeOutlined, InboxOutlined, PlusOutlined, SearchOutlined, StopOutlined } from '@ant-design/icons'
import {
  Alert,
  App as AntdApp,
  Button,
  Col,
  DatePicker,
  Descriptions,
  Drawer,
  Form,
  Input,
  InputNumber,
  Modal,
  Row,
  Select,
  Table,
  Tag,
  Typography,
} from 'antd'
import { useCallback, useEffect, useMemo, useState } from 'react'
import { useLocation, useNavigate, useSearchParams } from 'react-router-dom'

import { apiClient } from '../../api/client'
import { useAuth } from '../../auth/AuthProvider'
import { FORM_COMMON_PROPS, FORM_DRAWER_SUBMIT_PROPS } from '../../components/forms/formConfig'
import { applyFormApiError } from '../../components/forms/formErrorUtils'
import { FormProcessAlert } from '../../components/forms/FormProcessAlert'
import { ReceiptSnapshotFields } from '../../components/receipts/ReceiptSnapshotFields'
import { METODO_PAGO_OPTIONS } from '../boutique/boutiqueConstants'
import { openReceiptPrintable } from '../comprobantes/receiptUtils'
import { buildRefundPath } from '../economia/economyUtils'
import {
  DEVOLUCION_RESULT_OPTIONS,
  ESTADO_DEVOLUCION_OPTIONS,
  ESTADO_ENTREGA_OPTIONS,
  ESTADO_SALIDA_FLETE_OPTIONS,
  MOTIVO_DESCUENTO_FLETE_OPTIONS,
  formatMoney,
  labelFromOptions,
  salidaStateColor,
} from './fleteConstants'

const { RangePicker } = DatePicker

export function FleteOutputsPage() {
  const [outputs, setOutputs] = useState([])
  const [fletes, setFletes] = useState([])
  const [clients, setClients] = useState([])
  const [currencies, setCurrencies] = useState([])
  const [exchangeRates, setExchangeRates] = useState([])
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState(null)
  const [formError, setFormError] = useState(null)
  const [detail, setDetail] = useState(null)
  const [detailOpen, setDetailOpen] = useState(false)
  const [createOpen, setCreateOpen] = useState(false)
  const [actionModal, setActionModal] = useState(null)
  const [filters, setFilters] = useState({
    search: '',
    flete_id: undefined,
    client_id: undefined,
    currency_id: undefined,
    state: undefined,
    date_from: undefined,
    date_to: undefined,
  })
  const [form] = Form.useForm()
  const [actionForm] = Form.useForm()
  const [searchParams, setSearchParams] = useSearchParams()
  const navigate = useNavigate()
  const location = useLocation()
  const { message } = AntdApp.useApp()
  const { user } = useAuth()

  const canCreate = user?.permissions?.includes('flete_outputs:create')
  const canView = user?.permissions?.includes('flete_outputs:view')
  const canDeliver = user?.permissions?.includes('flete_outputs:deliver')
  const canReturn = user?.permissions?.includes('flete_outputs:return')
  const canAnnul = user?.permissions?.includes('flete_outputs:annul')
  const canPrintReceipts = user?.permissions?.includes('receipts:print')

  const selectedFleteId = Form.useWatch('flete_id', form)
  const selectedClientId = Form.useWatch('client_id', form)
  const selectedCurrencyId = Form.useWatch('currency_id', form)
  const watchedPrice = Form.useWatch('precio', form)
  const watchedDiscount = Form.useWatch('descuento', form)
  const watchedGuarantee = Form.useWatch('garantia', form)
  const actionReturnState = Form.useWatch('estado_salida', actionForm)
  const actionRequiresRepair = Form.useWatch('requiere_arreglo', actionForm)

  const loadReferences = useCallback(async () => {
    const [fleteResponse, clientResponse, currencyResponse, rateResponse] = await Promise.all([
      apiClient.get('/fletes', { params: { is_enabled: true } }),
      apiClient.get('/clientes', { params: { is_active: true } }),
      apiClient.get('/monedas', { params: { is_active: true } }),
      apiClient.get('/monedas/tipos-cambio', { params: { is_active: true } }),
    ])
    setFletes(fleteResponse.data)
    setClients(clientResponse.data)
    setCurrencies(currencyResponse.data)
    setExchangeRates(rateResponse.data)
  }, [])

  const loadOutputs = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const params = {}
      if (filters.search) params.search = filters.search
      if (filters.flete_id) params.flete_id = filters.flete_id
      if (filters.client_id) params.client_id = filters.client_id
      if (filters.currency_id) params.currency_id = filters.currency_id
      if (filters.state) params.state = filters.state
      if (filters.date_from) params.date_from = filters.date_from
      if (filters.date_to) params.date_to = filters.date_to
      const response = await apiClient.get('/fletes/salidas', { params })
      setOutputs(response.data)
    } catch (requestError) {
      setError(requestError.response?.data?.detail || 'No fue posible cargar las salidas de flete.')
    } finally {
      setLoading(false)
    }
  }, [filters])

  useEffect(() => {
    Promise.all([loadReferences(), loadOutputs()]).catch(() => {
      setError('No fue posible cargar la información inicial de salidas de flete.')
      setLoading(false)
    })
  }, [])

  useEffect(() => {
    loadOutputs()
  }, [filters.search, filters.flete_id, filters.client_id, filters.currency_id, filters.state, filters.date_from, filters.date_to])

  useEffect(() => {
    const outputId = searchParams.get('output_id')
    if (!outputId || !canView) return
    openDetail({ id: Number(outputId) }).finally(() => {
      const next = new URLSearchParams(searchParams)
      next.delete('output_id')
      setSearchParams(next, { replace: true })
    })
  }, [canView, searchParams, setSearchParams])

  const activeFletes = useMemo(
    () => fletes.filter((flete) => flete.habilitado),
    [fletes],
  )
  const fleteOptions = useMemo(
    () => activeFletes.map((flete) => ({ label: `${flete.item.code} - ${flete.item.name}`, value: flete.id })),
    [activeFletes],
  )
  const clientOptions = useMemo(
    () => clients.map((client) => ({ label: `${client.codigo} - ${client.full_name}`, value: client.id })),
    [clients],
  )
  const currencyOptions = useMemo(
    () => currencies.map((currency) => ({ label: `${currency.codigo} - ${currency.nombre}`, value: currency.id })),
    [currencies],
  )
  const selectedFlete = useMemo(
    () => activeFletes.find((flete) => flete.id === selectedFleteId),
    [activeFletes, selectedFleteId],
  )
  const selectedCurrency = useMemo(
    () => currencies.find((currency) => currency.id === selectedCurrencyId),
    [currencies, selectedCurrencyId],
  )
  const selectedRate = useMemo(
    () => exchangeRates.find((rate) => rate.moneda_id === selectedCurrencyId && rate.activo),
    [exchangeRates, selectedCurrencyId],
  )
  const selectedClient = useMemo(
    () => clients.find((client) => client.id === selectedClientId) || null,
    [clients, selectedClientId],
  )
  const subtotal = Number(watchedPrice || 0)
  const discount = Number(watchedDiscount || 0)
  const totalBs = Math.max(subtotal - discount, 0)
  const exchangeRateUsed = selectedCurrency?.es_base ? 1 : Number(selectedRate?.valor_bob || 0)
  const totalOrigin = exchangeRateUsed > 0 ? (selectedCurrency?.es_base ? totalBs : totalBs / exchangeRateUsed) : 0

  const openCreate = () => {
    setFormError(null)
    form.resetFields()
    form.setFieldsValue({ garantia: 0, estado_entrega: 'bueno' })
    setCreateOpen(true)
  }

  const openDetail = async (record) => {
    try {
      const response = await apiClient.get(`/fletes/salidas/${record.id}`)
      setDetail(response.data)
      setDetailOpen(true)
    } catch (requestError) {
      message.error(requestError.response?.data?.detail || 'No fue posible cargar el detalle de la salida de flete.')
    }
  }

  const openAction = (record, type) => {
    setActionModal({ record, type })
    actionForm.resetFields()
    if (type === 'return') {
      actionForm.setFieldsValue({
        estado_salida: 'devuelto',
        requiere_arreglo: false,
        monto_arreglo: 0,
        garantia_devuelta: Number(record.garantia || 0),
      })
    }
  }

  const closeCreate = () => {
    setCreateOpen(false)
    setFormError(null)
    form.resetFields()
  }

  const closeAction = () => {
    setActionModal(null)
    actionForm.resetFields()
  }

  const submitCreate = async (values) => {
    setSaving(true)
    setFormError(null)
    try {
      const response = await apiClient.post('/fletes/salidas', {
        ...values,
        fecha_salida: values.fecha_salida.format('YYYY-MM-DD'),
        fecha_devolucion_prevista: values.fecha_devolucion_prevista.format('YYYY-MM-DD'),
      })
      message.success('Se registró la salida de flete correctamente.')
      if (response.data?.comprobante?.id && canPrintReceipts) {
        await openReceiptPrintable(apiClient, response.data.comprobante.id, message)
      }
      closeCreate()
      await Promise.all([loadOutputs(), loadReferences()])
    } catch (requestError) {
      const resolved = applyFormApiError(form, requestError, {
        messageFieldMap: [
          { test: /ya tiene una salida activa o reservada/i, field: 'flete_id' },
          { test: /máximo de salidas/i, field: 'flete_id' },
          { test: /cliente.*inactivo/i, field: 'client_id' },
          { test: /cliente no encontrado/i, field: 'client_id' },
          { test: /moneda seleccionada no tiene un tipo de cambio activo/i, field: 'currency_id' },
          { test: /total del flete debe ser mayor a cero/i, field: 'descuento' },
        ],
        fallbackGlobalMessage: 'No fue posible registrar la salida de flete.',
      })
      setFormError(resolved.globalMessage)
    } finally {
      setSaving(false)
    }
  }

  const submitAction = async () => {
    setSaving(true)
    try {
      const values = await actionForm.validateFields()
      const { record, type } = actionModal
      if (type === 'deliver') {
        await apiClient.patch(`/fletes/salidas/${record.id}/deliver`, values)
        message.success('La salida quedó marcada como entregada.')
      }
      if (type === 'return') {
        await apiClient.patch(`/fletes/salidas/${record.id}/return`, {
          ...values,
          fecha_devolucion_real: values.fecha_devolucion_real.format('YYYY-MM-DD'),
        })
        message.success('La devolución del flete se registró correctamente.')
      }
      if (type === 'annul') {
        closeAction()
        navigate(
          buildRefundPath({
            originType: 'SALIDA_FLETE',
            originId: record.id,
            targetState: 'ANULADA',
            returnTo: `${location.pathname}${location.search}`,
          }),
          { state: { refundReason: values.motivo } },
        )
        return
      }
      closeAction()
      if (detail?.id === record.id) {
        const response = await apiClient.get(`/fletes/salidas/${record.id}`)
        setDetail(response.data)
      }
      await Promise.all([loadOutputs(), loadReferences()])
    } catch (requestError) {
      if (requestError?.errorFields) {
        setSaving(false)
        return
      }
      const resolved = applyFormApiError(actionForm, requestError, {
        fallbackGlobalMessage: 'No fue posible completar la acción sobre la salida de flete.',
      })
      message.error(resolved.globalMessage)
    } finally {
      setSaving(false)
    }
  }

  const columns = [
    {
      title: 'Vestido',
      key: 'item',
      render: (_, record) => `${record.item_code} - ${record.item_name}`,
    },
    {
      title: 'Cliente',
      dataIndex: 'client_name',
      key: 'client_name',
    },
    {
      title: 'N° salida',
      dataIndex: 'numero_salida',
      key: 'numero_salida',
    },
    {
      title: 'Salida',
      dataIndex: 'fecha_salida',
      key: 'fecha_salida',
    },
    {
      title: 'Prev. devolución',
      dataIndex: 'fecha_devolucion_prevista',
      key: 'fecha_devolucion_prevista',
    },
    {
      title: 'Total (Bs)',
      dataIndex: 'total_flete',
      key: 'total_flete',
      render: (value) => formatMoney(value),
    },
    {
      title: 'Garantía',
      dataIndex: 'garantia',
      key: 'garantia',
      render: (value) => formatMoney(value),
    },
    {
      title: 'Estado',
      dataIndex: 'estado_salida',
      key: 'estado_salida',
      render: (value) => <Tag color={salidaStateColor(value)}>{labelFromOptions(ESTADO_SALIDA_FLETE_OPTIONS, value)}</Tag>,
    },
    {
      title: 'Acciones',
      key: 'acciones',
      render: (_, record) => (
        <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
          {canView ? (
            <Button icon={<EyeOutlined />} onClick={() => openDetail(record)}>
              Ver
            </Button>
          ) : null}
          {canDeliver && record.estado_salida === 'reservado' ? (
            <Button icon={<InboxOutlined />} onClick={() => openAction(record, 'deliver')}>
              Entregar
            </Button>
          ) : null}
          {canReturn && record.estado_salida === 'en_flete' ? (
            <Button icon={<CheckCircleOutlined />} onClick={() => openAction(record, 'return')}>
              Devolver
            </Button>
          ) : null}
          {canAnnul && record.estado_salida !== 'anulado' ? (
            <Button danger icon={<StopOutlined />} onClick={() => openAction(record, 'annul')}>
              Anular
            </Button>
          ) : null}
        </div>
      ),
    },
  ]

  return (
    <div>
      <div className="page-header">
        <div>
          <Typography.Title level={2} style={{ margin: 0 }}>
            Salidas de Flete
          </Typography.Title>
          <Typography.Paragraph type="secondary" style={{ marginBottom: 0 }}>
            Registra reservas, entregas, devoluciones y anulaciones del circuito de fletes, conservando garantía, moneda y comprobante interno.
          </Typography.Paragraph>
        </div>
        {canCreate ? (
          <Button type="primary" icon={<PlusOutlined />} onClick={openCreate}>
            Nueva salida
          </Button>
        ) : null}
      </div>

      <div className="glass-panel boutique-filter-bar">
        <Row gutter={[12, 12]}>
          <Col xs={24} md={8}>
            <Input
              allowClear
              prefix={<SearchOutlined />}
              placeholder="Buscar por vestido o cliente"
              value={filters.search}
              onChange={(event) => setFilters((current) => ({ ...current, search: event.target.value }))}
            />
          </Col>
          <Col xs={24} md={4}>
            <Select
              allowClear
              showSearch
              optionFilterProp="label"
              placeholder="Vestido"
              options={fleteOptions}
              value={filters.flete_id}
              onChange={(value) => setFilters((current) => ({ ...current, flete_id: value }))}
              style={{ width: '100%' }}
            />
          </Col>
          <Col xs={24} md={4}>
            <Select
              allowClear
              showSearch
              optionFilterProp="label"
              placeholder="Cliente"
              options={clientOptions}
              value={filters.client_id}
              onChange={(value) => setFilters((current) => ({ ...current, client_id: value }))}
              style={{ width: '100%' }}
            />
          </Col>
          <Col xs={24} md={4}>
            <Select
              allowClear
              placeholder="Moneda"
              options={currencyOptions}
              value={filters.currency_id}
              onChange={(value) => setFilters((current) => ({ ...current, currency_id: value }))}
              style={{ width: '100%' }}
            />
          </Col>
          <Col xs={24} md={4}>
            <Select
              allowClear
              placeholder="Estado"
              options={ESTADO_SALIDA_FLETE_OPTIONS}
              value={filters.state}
              onChange={(value) => setFilters((current) => ({ ...current, state: value }))}
              style={{ width: '100%' }}
            />
          </Col>
          <Col xs={24} md={6}>
            <RangePicker
              format="DD/MM/YYYY"
              style={{ width: '100%' }}
              onChange={(dates) =>
                setFilters((current) => ({
                  ...current,
                  date_from: dates?.[0] ? dates[0].format('YYYY-MM-DD') : undefined,
                  date_to: dates?.[1] ? dates[1].format('YYYY-MM-DD') : undefined,
                }))
              }
            />
          </Col>
        </Row>
      </div>

      {error ? <Alert type="error" showIcon message={error} style={{ marginBottom: 16 }} /> : null}

      <Table
        className="glass-panel"
        rowKey="id"
        columns={columns}
        dataSource={outputs}
        loading={loading}
        pagination={{ pageSize: 8 }}
        scroll={{ x: 'max-content' }}
        style={{ borderRadius: 24, overflow: 'hidden' }}
      />

      <Drawer
        title="Registrar Salida de Flete"
        width={900}
        open={createOpen}
        onClose={closeCreate}
        maskClosable={false}
        destroyOnClose
      >
        <FormProcessAlert message={formError} title="No fue posible registrar la salida de flete." />
        <Form {...FORM_COMMON_PROPS} form={form} onFinish={submitCreate}>
          <Row gutter={12}>
            <Col xs={24} md={12}>
              <Form.Item
                label="Vestido habilitado para flete"
                name="flete_id"
                rules={[{ required: true, message: 'Debe seleccionar el vestido habilitado para flete.' }]}
              >
                <Select
                  showSearch
                  optionFilterProp="label"
                  placeholder="Selecciona el vestido disponible"
                  options={fleteOptions}
                />
              </Form.Item>
            </Col>
            <Col xs={24} md={12}>
              <Form.Item
                label="Cliente"
                name="client_id"
                rules={[{ required: true, message: 'Debe seleccionar la clienta del flete.' }]}
              >
                <Select
                  showSearch
                  optionFilterProp="label"
                  placeholder="Selecciona la clienta asociada"
                  options={clientOptions}
                />
              </Form.Item>
            </Col>
            <Col xs={24} md={8}>
                  <Form.Item
                    label="Fecha de salida"
                    name="fecha_salida"
                    rules={[{ required: true, message: 'Debe registrar la fecha de salida del flete.' }]}
                  >
                    <DatePicker format="DD/MM/YYYY" placeholder="Selecciona la fecha de salida" style={{ width: '100%' }} />
                  </Form.Item>
            </Col>
            <Col xs={24} md={8}>
                  <Form.Item
                    label="Fecha prevista de devolución"
                    name="fecha_devolucion_prevista"
                    rules={[{ required: true, message: 'Debe registrar la fecha prevista de devolución.' }]}
                  >
                    <DatePicker format="DD/MM/YYYY" placeholder="Selecciona la devolución prevista" style={{ width: '100%' }} />
                  </Form.Item>
            </Col>
            <Col xs={24} md={8}>
              <Form.Item
                label="Estado al entregar"
                name="estado_entrega"
                rules={[{ required: true, message: 'Debe registrar el estado del vestido al entregarlo.' }]}
              >
                <Select placeholder="Selecciona el estado físico" options={ESTADO_ENTREGA_OPTIONS} />
              </Form.Item>
            </Col>
            <Col xs={24} md={8}>
              <Form.Item
                label="Precio del flete (Bs)"
                name="precio"
                rules={[{ required: true, message: 'Debe registrar el precio del flete.' }]}
              >
                <InputNumber min={0.01} precision={2} placeholder="Ej. 350.00" style={{ width: '100%' }} />
              </Form.Item>
            </Col>
            <Col xs={24} md={8}>
              <Form.Item label="Descuento (Bs)" name="descuento">
                <InputNumber min={0} precision={2} placeholder="Ej. 20.00" style={{ width: '100%' }} />
              </Form.Item>
            </Col>
            <Col xs={24} md={8}>
              <Form.Item
                label="Motivo del descuento"
                name="motivo_desc"
                rules={[
                  ({ getFieldValue }) => ({
                    validator(_, value) {
                      if (!getFieldValue('descuento') || value) {
                        return Promise.resolve()
                      }
                      return Promise.reject(new Error('Debe indicar el motivo del descuento aplicado.'))
                    },
                  }),
                ]}
              >
                <Select allowClear placeholder="Selecciona el motivo si hubo descuento" options={MOTIVO_DESCUENTO_FLETE_OPTIONS} />
              </Form.Item>
            </Col>
            <Col xs={24} md={8}>
              <Form.Item
                label="Moneda"
                name="currency_id"
                rules={[{ required: true, message: 'Debe seleccionar la moneda del cobro.' }]}
              >
                <Select placeholder="Selecciona la moneda" options={currencyOptions} />
              </Form.Item>
            </Col>
            <Col xs={24} md={8}>
              <Form.Item
                label="Método de pago"
                name="metodo_pago"
                rules={[{ required: true, message: 'Debe registrar el método de pago.' }]}
              >
                <Select placeholder="Selecciona el método de pago" options={METODO_PAGO_OPTIONS} />
              </Form.Item>
            </Col>
            <Col xs={24} md={8}>
              <Form.Item label="Garantía recibida" name="garantia">
                <InputNumber min={0} precision={2} placeholder="Ej. 200.00" style={{ width: '100%' }} />
              </Form.Item>
            </Col>
            <Col span={24}>
              <Form.Item
                label="Observaciones de entrega"
                name="observaciones_entrega"
                normalize={(value) => (value || '').toUpperCase()}
              >
                <Input.TextArea rows={3} placeholder="Ej. VESTIDO ENTREGADO EN BUEN ESTADO Y CON FALDA COMPLETA" />
              </Form.Item>
            </Col>
          </Row>

          {selectedFlete ? (
            <Alert
              type="info"
              showIcon
              style={{ marginBottom: 16 }}
              message={`Resumen del flete: ${selectedFlete.item.code} - ${selectedFlete.item.name}`}
              description={
                <>
                  <div>Precio referencial: Bs {formatMoney(selectedFlete.precio_flete_ref)}</div>
                  <div>Salidas válidas acumuladas: {selectedFlete.salidas_actuales}/{selectedFlete.max_salidas}</div>
                  <div>Estado actual: {selectedFlete.estado.toUpperCase()}</div>
                </>
              }
            />
          ) : null}

          {selectedCurrency ? (
            <Alert
              type={selectedCurrency.es_base || selectedRate ? 'success' : 'warning'}
              showIcon
              style={{ marginBottom: 16 }}
              message="Resumen de cobro"
              description={
                <>
                  <div>Moneda elegida: {selectedCurrency.codigo}</div>
                  <div>Tipo de cambio usado: {exchangeRateUsed ? formatMoney(exchangeRateUsed) : 'SIN TIPO DE CAMBIO ACTIVO'}</div>
                  <div>Subtotal en Bs: {formatMoney(subtotal)}</div>
                  <div>Descuento en Bs: {formatMoney(discount)}</div>
                  <div>Total del flete en Bs: {formatMoney(totalBs)}</div>
                  <div>Total en moneda origen: {formatMoney(totalOrigin)}</div>
                  <div>Garantía registrada: {formatMoney(watchedGuarantee || 0)}</div>
                </>
              }
            />
          ) : null}

          <ReceiptSnapshotFields selectedClient={selectedClient} title="SNAPSHOT DOCUMENTAL PARA COMPROBANTE" />

          <Button
            type="primary"
            htmlType="submit"
            loading={saving}
            disabled={selectedCurrency && !selectedCurrency.es_base && !selectedRate}
            {...FORM_DRAWER_SUBMIT_PROPS}
          >
            Registrar salida de flete
          </Button>
        </Form>
      </Drawer>

      <Modal
        title="Detalle de Salida de Flete"
        open={detailOpen}
        onCancel={() => {
          setDetailOpen(false)
          setDetail(null)
        }}
        footer={[
          <Button key="close" onClick={() => { setDetailOpen(false); setDetail(null) }}>
            Cerrar
          </Button>,
        ]}
        maskClosable={false}
        width={980}
      >
        {detail ? (
          <>
            {detail.comprobante?.id && canPrintReceipts ? (
              <div style={{ marginBottom: 16 }}>
                <Button type="primary" onClick={() => openReceiptPrintable(apiClient, detail.comprobante.id, message)}>
                  Imprimir comprobante
                </Button>
              </div>
            ) : null}
            <Descriptions bordered column={2} size="small">
              <Descriptions.Item label="Vestido">{`${detail.item.code} - ${detail.item.name}`}</Descriptions.Item>
              <Descriptions.Item label="Cliente">{detail.client.full_name}</Descriptions.Item>
              <Descriptions.Item label="Estado">
                <Tag color={salidaStateColor(detail.estado_salida)}>{labelFromOptions(ESTADO_SALIDA_FLETE_OPTIONS, detail.estado_salida)}</Tag>
              </Descriptions.Item>
              <Descriptions.Item label="N° salida">{detail.numero_salida}</Descriptions.Item>
              <Descriptions.Item label="Fecha de salida">{detail.fecha_salida}</Descriptions.Item>
              <Descriptions.Item label="Prev. devolución">{detail.fecha_devolucion_prevista}</Descriptions.Item>
              <Descriptions.Item label="Fecha real devolución">{detail.fecha_devolucion_real || 'PENDIENTE'}</Descriptions.Item>
              <Descriptions.Item label="Registrado por">{detail.registered_by.full_name}</Descriptions.Item>
              <Descriptions.Item label="Precio del flete (Bs)">{formatMoney(detail.precio)}</Descriptions.Item>
              <Descriptions.Item label="Descuento (Bs)">{formatMoney(detail.descuento || 0)}</Descriptions.Item>
              <Descriptions.Item label="Total del flete (Bs)">{formatMoney(detail.total_flete)}</Descriptions.Item>
              <Descriptions.Item label="Total moneda origen">{formatMoney(detail.total_flete_moneda_origen)}</Descriptions.Item>
              <Descriptions.Item label="Garantía">{formatMoney(detail.garantia)}</Descriptions.Item>
              <Descriptions.Item label="Garantía devuelta">{formatMoney(detail.garantia_devuelta)}</Descriptions.Item>
              <Descriptions.Item label="Método de pago">{labelFromOptions(METODO_PAGO_OPTIONS, detail.metodo_pago)}</Descriptions.Item>
              <Descriptions.Item label="Moneda">{detail.currency.codigo}</Descriptions.Item>
              <Descriptions.Item label="Estado de entrega">{labelFromOptions(ESTADO_ENTREGA_OPTIONS, detail.estado_entrega)}</Descriptions.Item>
              <Descriptions.Item label="Estado de devolución">
                {detail.estado_devolucion ? labelFromOptions(ESTADO_DEVOLUCION_OPTIONS, detail.estado_devolucion) : 'PENDIENTE'}
              </Descriptions.Item>
              <Descriptions.Item label="Requiere arreglo">{detail.requiere_arreglo ? 'SÍ' : 'NO'}</Descriptions.Item>
              <Descriptions.Item label="Monto arreglo">{formatMoney(detail.monto_arreglo)}</Descriptions.Item>
              <Descriptions.Item label="Descripción arreglo">{detail.descripcion_arreglo || 'SIN REGISTRO'}</Descriptions.Item>
              <Descriptions.Item label="Obs. entrega">{detail.observaciones_entrega || 'SIN OBSERVACIONES'}</Descriptions.Item>
              <Descriptions.Item label="Obs. devolución">{detail.observaciones_devolucion || 'SIN OBSERVACIONES'}</Descriptions.Item>
              <Descriptions.Item label="Comprobante">
                {detail.comprobante ? `${detail.comprobante.codigo} (${detail.comprobante.estado.toUpperCase()})` : 'SIN REGISTRO'}
              </Descriptions.Item>
            </Descriptions>
          </>
        ) : null}
      </Modal>

      <Modal
        title={
          actionModal?.type === 'deliver'
            ? 'Confirmar entrega física'
            : actionModal?.type === 'return'
              ? 'Registrar devolución'
              : 'Anular salida de flete'
        }
        open={Boolean(actionModal)}
        onCancel={closeAction}
        onOk={submitAction}
        confirmLoading={saving}
        maskClosable={false}
        okText="Confirmar"
        cancelText="Cerrar"
        width={actionModal?.type === 'return' ? 860 : 620}
      >
        {actionModal ? (
          <Form {...FORM_COMMON_PROPS} form={actionForm}>
            <Row gutter={12}>
              {actionModal.type === 'deliver' ? (
                <Col span={24}>
                  <Form.Item
                    label="Observaciones de entrega"
                    name="observaciones_entrega"
                    normalize={(value) => (value || '').toUpperCase()}
                  >
                    <Input.TextArea rows={3} placeholder="Ej. ENTREGA FÍSICA CONFIRMADA A LA CLIENTA EN BUEN ESTADO" />
                  </Form.Item>
                </Col>
              ) : null}

              {actionModal.type === 'return' ? (
                <>
                  <Col xs={24} md={12}>
                    <Form.Item
                      label="Resultado de devolución"
                      name="estado_salida"
                      rules={[{ required: true, message: 'Debe indicar el resultado de la devolución.' }]}
                    >
                      <Select placeholder="Selecciona el resultado final" options={DEVOLUCION_RESULT_OPTIONS} />
                    </Form.Item>
                  </Col>
                  <Col xs={24} md={12}>
                    <Form.Item
                      label="Estado recibido"
                      name="estado_devolucion"
                      rules={[{ required: true, message: 'Debe registrar el estado del vestido al devolverlo.' }]}
                    >
                      <Select placeholder="Selecciona el estado recibido" options={ESTADO_DEVOLUCION_OPTIONS} />
                    </Form.Item>
                  </Col>
                  <Col xs={24} md={12}>
                    <Form.Item
                      label="Fecha real de devolución"
                      name="fecha_devolucion_real"
                      rules={[{ required: true, message: 'Debe registrar la fecha real de devolución.' }]}
                    >
                      <DatePicker format="DD/MM/YYYY" placeholder="Selecciona la fecha real" style={{ width: '100%' }} />
                    </Form.Item>
                  </Col>
                  <Col xs={24} md={12}>
                    <Form.Item
                      label="Garantía devuelta"
                      name="garantia_devuelta"
                      rules={[{ required: true, message: 'Debe indicar cuánto de la garantía se devolvió.' }]}
                    >
                      <InputNumber min={0} precision={2} placeholder="Ej. 150.00" style={{ width: '100%' }} />
                    </Form.Item>
                  </Col>
                  <Col xs={24} md={12}>
                    <Form.Item label="Requiere arreglo" name="requiere_arreglo" initialValue={false}>
                      <Select
                        placeholder="Selecciona si requiere arreglo"
                        options={[
                          { value: false, label: 'NO REQUIERE ARREGLO' },
                          { value: true, label: 'SÍ REQUIERE ARREGLO' },
                        ]}
                      />
                    </Form.Item>
                  </Col>
                  <Col xs={24} md={12}>
                    <Form.Item label="Monto de arreglo" name="monto_arreglo">
                      <InputNumber
                        min={0}
                        precision={2}
                        placeholder="Ej. 60.00"
                        style={{ width: '100%' }}
                        disabled={!actionRequiresRepair}
                      />
                    </Form.Item>
                  </Col>
                  <Col span={24}>
                    <Form.Item
                      label="Descripción del arreglo"
                      name="descripcion_arreglo"
                      normalize={(value) => (value || '').toUpperCase()}
                    >
                      <Input
                        placeholder="Describe el daño o arreglo requerido"
                        disabled={!actionRequiresRepair && actionReturnState !== 'devuelto_con_arreglo'}
                      />
                    </Form.Item>
                  </Col>
                  <Col span={24}>
                    <Form.Item
                      label="Observaciones de devolución"
                      name="observaciones_devolucion"
                      normalize={(value) => (value || '').toUpperCase()}
                    >
                      <Input.TextArea rows={3} placeholder="Ej. VESTIDO DEVUELTO CON MANCHA EN LA PARTE BAJA DE LA FALDA" />
                    </Form.Item>
                  </Col>
                </>
              ) : null}

              {actionModal.type === 'annul' ? (
                <>
                  <Col span={24}>
                    <Alert
                      type="warning"
                      showIcon
                      message="La anulación continuará con el flujo económico obligatorio para registrar cuánto dinero se devuelve a la clienta."
                      style={{ marginBottom: 12 }}
                    />
                  </Col>
                  <Col span={24}>
                    <Form.Item
                      label="Motivo operativo de anulación"
                      name="motivo"
                      rules={[{ required: true, message: 'Debe registrar el motivo de anulación.' }]}
                      normalize={(value) => (value || '').toUpperCase()}
                    >
                      <Input.TextArea rows={3} placeholder="Ej. LA RESERVA SE REGISTRÓ POR ERROR O LA CLIENTA CANCELÓ ANTES DE LA ENTREGA" />
                    </Form.Item>
                  </Col>
                </>
              ) : null}
            </Row>
          </Form>
        ) : null}
      </Modal>
    </div>
  )
}
