import { CloseCircleOutlined, EyeOutlined, PlusOutlined, SearchOutlined } from '@ant-design/icons'
import { Alert, App as AntdApp, Button, Col, DatePicker, Descriptions, Drawer, Form, Input, InputNumber, Modal, Row, Select, Table, Tag, Typography } from 'antd'
import { useCallback, useEffect, useMemo, useState } from 'react'
import { useLocation, useNavigate, useSearchParams } from 'react-router-dom'

import { apiClient } from '../../api/client'
import { useAuth } from '../../auth/AuthProvider'
import { FORM_COMMON_PROPS, FORM_DRAWER_SUBMIT_PROPS } from '../../components/forms/formConfig'
import { FormProcessAlert } from '../../components/forms/FormProcessAlert'
import { ReceiptSnapshotFields } from '../../components/receipts/ReceiptSnapshotFields'
import { ESTADO_PAGO_OPTIONS, METODO_PAGO_OPTIONS, TIPO_PEDIDO_OPTIONS, formatBs, labelFromOptions, paymentStateColor } from './orderConstants'
import { openReceiptPrintable } from '../comprobantes/receiptUtils'
import { buildRefundPath } from '../economia/economyUtils'

const { RangePicker } = DatePicker

export function OrderPaymentsPage() {
  const [payments, setPayments] = useState([])
  const [orders, setOrders] = useState([])
  const [clients, setClients] = useState([])
  const [currencies, setCurrencies] = useState([])
  const [exchangeRates, setExchangeRates] = useState([])
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState(null)
  const [formError, setFormError] = useState(null)
  const [filters, setFilters] = useState({ search: '', state: undefined, payment_method: undefined, currency_id: undefined, date_from: undefined, date_to: undefined })
  const [drawerOpen, setDrawerOpen] = useState(false)
  const [detail, setDetail] = useState(null)
  const [annulPayment, setAnnulPayment] = useState(null)
  const [form] = Form.useForm()
  const [annulForm] = Form.useForm()
  const [searchParams, setSearchParams] = useSearchParams()
  const navigate = useNavigate()
  const location = useLocation()
  const { message } = AntdApp.useApp()
  const { user } = useAuth()

  const canCreate = user?.permissions?.includes('order_payments:create')
  const canAnnul = user?.permissions?.includes('order_payments:annul')
  const canView = user?.permissions?.includes('order_payments:view')
  const canPrintReceipts = user?.permissions?.includes('receipts:print')
  const selectedOrderId = Form.useWatch('order_id', form)
  const watchedAmount = Form.useWatch('monto', form)
  const selectedCurrencyId = Form.useWatch('currency_id', form)

  const selectedOrder = useMemo(
    () => orders.find((order) => order.id === selectedOrderId) || null,
    [orders, selectedOrderId],
  )
  const selectedClient = useMemo(
    () => clients.find((client) => client.id === selectedOrder?.client_id) || null,
    [clients, selectedOrder],
  )
  const selectedCurrency = useMemo(
    () => currencies.find((c) => c.id === selectedCurrencyId) || null,
    [currencies, selectedCurrencyId]
  )
  const selectedRate = useMemo(
    () => exchangeRates.find((r) => r.moneda_id === selectedCurrencyId && r.activo) || null,
    [exchangeRates, selectedCurrencyId]
  )

  const amountOrigin = Number(watchedAmount || 0)
  const exchangeRateUsed = selectedCurrency?.es_base ? 1 : Number(selectedRate?.valor_bob || 0)
  const amountBs = amountOrigin * exchangeRateUsed
  const saldoPrevio = Number(selectedOrder?.saldo || 0)
  const nuevoSaldo = Math.max(saldoPrevio - amountBs, 0)
  const selectedCurrencyWithoutRate = Boolean(selectedCurrency && !selectedCurrency.es_base && !selectedRate)

  const orderOptions = useMemo(
    () => orders.filter((order) => order.estado_general === 'activo' && order.saldo > 0).map((order) => ({ label: `${order.codigo} - ${labelFromOptions(TIPO_PEDIDO_OPTIONS, order.tipo)} - ${order.client_name} (Saldo: Bs. ${formatBs(order.saldo)})`, value: order.id })),
    [orders],
  )
  const currencyOptions = useMemo(
    () => currencies.map((currency) => ({ label: `${currency.codigo} - ${currency.nombre}`, value: currency.id })),
    [currencies],
  )

  const loadReferences = useCallback(async () => {
    const [orderResponse, currencyResponse, rateResponse] = await Promise.all([
      apiClient.get('/pedidos', { params: { state: 'activo' } }),
      apiClient.get('/monedas', { params: { is_active: true } }),
      apiClient.get('/monedas/tipos-cambio', { params: { is_active: true } }),
    ])
    setOrders(orderResponse.data)
    setCurrencies(currencyResponse.data)
    setExchangeRates(rateResponse.data)
    const clientResponse = await apiClient.get('/clientes', { params: { is_active: true } })
    setClients(clientResponse.data)
  }, [])

  const loadPayments = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const params = {}
      if (filters.search) params.search = filters.search
      if (filters.state) params.state = filters.state
      if (filters.payment_method) params.payment_method = filters.payment_method
      if (filters.currency_id) params.currency_id = filters.currency_id
      if (filters.date_from) params.date_from = filters.date_from
      if (filters.date_to) params.date_to = filters.date_to
      const response = await apiClient.get('/pedidos/pagos', { params })
      setPayments(response.data)
    } catch (requestError) {
      setError(requestError.response?.data?.detail || 'No fue posible cargar pagos de pedidos.')
    } finally {
      setLoading(false)
    }
  }, [filters])

  useEffect(() => {
    loadReferences().catch(() => {
      setError('No fue posible cargar la información inicial de pagos.')
      setLoading(false)
    })
  }, [loadReferences])

  useEffect(() => {
    loadPayments()
  }, [loadPayments])

  const submitPayment = async (values) => {
    setSaving(true)
    setFormError(null)
    try {
      const response = await apiClient.post(`/pedidos/${values.order_id}/pagos`, {
        currency_id: values.currency_id,
        monto: values.monto,
        metodo_pago: values.metodo_pago,
        observaciones: values.observaciones,
        receipt_customer_snapshot: values.receipt_customer_snapshot || null,
      })
      message.success('Se registró el pago correctamente.')
      if (response.data?.receipt?.id && canPrintReceipts) {
        await openReceiptPrintable(apiClient, response.data.receipt.id, message)
      }
      setDrawerOpen(false)
      form.resetFields()
      await Promise.all([loadPayments(), loadReferences()])
    } catch (requestError) {
      setFormError(requestError.response?.data?.detail || 'No fue posible registrar el pago.')
    } finally {
      setSaving(false)
    }
  }

  const openDetail = useCallback(async (record) => {
    try {
      const response = await apiClient.get(`/pedidos/pagos/${record.id}`)
      setDetail(response.data)
    } catch (requestError) {
      message.error(requestError.response?.data?.detail || 'No fue posible cargar el pago.')
    }
  }, [message])

  useEffect(() => {
    const paymentId = searchParams.get('payment_id')
    if (!paymentId || !canView) return
    openDetail({ id: Number(paymentId) }).finally(() => {
      const next = new URLSearchParams(searchParams)
      next.delete('payment_id')
      setSearchParams(next, { replace: true })
    })
  }, [canView, openDetail, searchParams, setSearchParams])

  const columns = [
    { title: 'PEDIDO', dataIndex: 'pedido_codigo' },
    { title: 'CLIENTE', dataIndex: 'client_name' },
    { title: 'FECHA', dataIndex: 'fecha', render: (value) => new Date(value).toLocaleString() },
    { title: 'MONEDA', render: (_, record) => record.currency?.codigo },
    { title: 'MONTO ORIGEN', dataIndex: 'monto', render: (value, record) => `${Number(value).toFixed(2)} ${record.currency?.codigo}` },
    { title: 'MONTO Bs', dataIndex: 'monto_bob', render: formatBs },
    { title: 'MÉTODO', dataIndex: 'metodo_pago', render: (value) => labelFromOptions(METODO_PAGO_OPTIONS, value) },
    { title: 'ESTADO', dataIndex: 'estado', render: (value) => <Tag color={paymentStateColor(value)}>{labelFromOptions(ESTADO_PAGO_OPTIONS, value)}</Tag> },
    {
      title: 'ACCIONES',
      render: (_, record) => (
        <Row gutter={[8, 8]}>
          {canView ? <Col><Button icon={<EyeOutlined />} onClick={() => openDetail(record)}>Ver</Button></Col> : null}
          {canAnnul && record.estado === 'registrado' ? <Col><Button danger icon={<CloseCircleOutlined />} onClick={() => setAnnulPayment(record)}>Anular</Button></Col> : null}
        </Row>
      ),
    },
  ]

  return (
    <>
      <Row gutter={[16, 16]} align="middle" style={{ marginBottom: 16 }}>
        <Col flex="auto">
          <Typography.Title level={3} style={{ margin: 0 }}>Pagos de pedidos</Typography.Title>
          <Typography.Text type="secondary">Pagos parciales, finales, multi-moneda y anulaciones auditadas.</Typography.Text>
        </Col>
        {canCreate ? <Col><Button type="primary" icon={<PlusOutlined />} onClick={() => setDrawerOpen(true)}>Registrar pago</Button></Col> : null}
      </Row>
      {error ? <Alert type="error" message={error} showIcon style={{ marginBottom: 16 }} /> : null}
      <Row gutter={[12, 12]} style={{ marginBottom: 16 }}>
        <Col xs={24} md={7}><Input prefix={<SearchOutlined />} placeholder="Buscar pedido o cliente" value={filters.search} onChange={(event) => setFilters((current) => ({ ...current, search: event.target.value }))} /></Col>
        <Col xs={24} md={4}><Select allowClear placeholder="Estado del pago" options={ESTADO_PAGO_OPTIONS} value={filters.state} onChange={(value) => setFilters((current) => ({ ...current, state: value }))} style={{ width: '100%' }} /></Col>
        <Col xs={24} md={4}><Select allowClear placeholder="Método de pago" options={METODO_PAGO_OPTIONS} value={filters.payment_method} onChange={(value) => setFilters((current) => ({ ...current, payment_method: value }))} style={{ width: '100%' }} /></Col>
        <Col xs={24} md={4}><Select allowClear placeholder="Moneda" options={currencyOptions} value={filters.currency_id} onChange={(value) => setFilters((current) => ({ ...current, currency_id: value }))} style={{ width: '100%' }} /></Col>
        <Col xs={24} md={5}>
          <RangePicker
            format="DD/MM/YYYY"
            style={{ width: '100%' }}
            onChange={(values) =>
              setFilters((current) => ({
                ...current,
                date_from: values?.[0] ? values[0].format('YYYY-MM-DD') : undefined,
                date_to: values?.[1] ? values[1].format('YYYY-MM-DD') : undefined,
              }))
            }
          />
        </Col>
      </Row>
      <Table rowKey="id" columns={columns} dataSource={payments} loading={loading} scroll={{ x: 1200 }} />

      <Drawer title="Registrar pago" width={620} open={drawerOpen} onClose={() => setDrawerOpen(false)} maskClosable={false} destroyOnClose>
        <Form form={form} layout="vertical" onFinish={submitPayment} {...FORM_COMMON_PROPS}>
          <FormProcessAlert message={formError} />
          <Row gutter={16}>
            <Col xs={24}><Form.Item name="order_id" label="Pedido" rules={[{ required: true, message: 'Debe seleccionar el pedido.' }]}><Select showSearch placeholder="Selecciona pedido con saldo" options={orderOptions} optionFilterProp="label" /></Form.Item></Col>
            <Col xs={24} md={12}><Form.Item name="currency_id" label="Moneda" rules={[{ required: true, message: 'Debe seleccionar la moneda.' }]}><Select placeholder="Selecciona moneda" options={currencyOptions} /></Form.Item></Col>
            <Col xs={24} md={12}><Form.Item name="monto" label="Monto" rules={[{ required: true, message: 'Debe ingresar el monto.' }]}><InputNumber min={0.01} placeholder="Ej. 500" style={{ width: '100%' }} /></Form.Item></Col>
            <Col xs={24}><Form.Item name="metodo_pago" label="Método de pago" rules={[{ required: true, message: 'Debe seleccionar el método.' }]}><Select placeholder="Selecciona método" options={METODO_PAGO_OPTIONS} /></Form.Item></Col>
            <Col xs={24}><Form.Item name="observaciones" label="Observaciones" normalize={(value) => (value || '').toUpperCase()}><Input.TextArea rows={3} placeholder="Observaciones del pago" /></Form.Item></Col>
          </Row>
          {selectedOrder ? (
            <Alert
              type="info"
              showIcon
              style={{ marginBottom: 16 }}
              message={`Pedido ${selectedOrder.codigo}: ${selectedOrder.client_name}`}
              description={`El precio total del pedido es de Bs. ${formatBs(selectedOrder.precio_total)} y el cliente ya pagó Bs. ${formatBs(selectedOrder.total_pagado)}.`}
            />
          ) : null}

          {selectedCurrency ? (
            <Alert
              style={{ marginBottom: 16 }}
              type={selectedCurrencyWithoutRate ? 'error' : 'info'}
              showIcon
              message={selectedCurrencyWithoutRate ? 'La moneda seleccionada no tiene tipo de cambio activo.' : `Tipo de cambio activo: ${exchangeRateUsed}`}
            />
          ) : null}

          <div className="glass-panel" style={{ padding: 16, marginBottom: 16 }}>
            <Typography.Title level={5} style={{ marginTop: 0 }}>
              Resumen de cobro
            </Typography.Title>
            <Row gutter={[12, 12]}>
              <Col xs={12} md={8}>
                <Typography.Text type="secondary">Pago equivalente Bs.</Typography.Text>
                <Typography.Title level={4} style={{ marginTop: 4, marginBottom: 0 }}>
                  {formatBs(amountBs)}
                </Typography.Title>
              </Col>
              <Col xs={12} md={8}>
                <Typography.Text type="secondary">Saldo previo Bs.</Typography.Text>
                <Typography.Title level={4} style={{ marginTop: 4, marginBottom: 0 }}>
                  {formatBs(saldoPrevio)}
                </Typography.Title>
              </Col>
              <Col xs={12} md={8}>
                <Typography.Text type="secondary">Nuevo saldo Bs.</Typography.Text>
                <Typography.Title level={4} style={{ marginTop: 4, marginBottom: 0, color: '#8f3d2e' }}>
                  {formatBs(nuevoSaldo)}
                </Typography.Title>
              </Col>
              <Col span={24}>
                <div style={{ background: 'rgba(255,255,255,0.5)', padding: '8px 12px', borderRadius: 8, display: 'inline-block' }}>
                  <Typography.Text type="secondary">Monto ingresado ({selectedCurrency?.codigo || ''}): </Typography.Text>
                  <Typography.Text strong style={{ fontSize: 16, color: '#8f3d2e', marginLeft: 8 }}>
                    {selectedCurrency?.simbolo || selectedCurrency?.codigo || ''} {formatBs(amountOrigin)}
                  </Typography.Text>
                </div>
              </Col>
            </Row>
          </div>

          <ReceiptSnapshotFields selectedClient={selectedClient} title="SNAPSHOT DOCUMENTAL PARA COMPROBANTE" />
          <Row justify="end" gutter={12}>
            <Col><Button onClick={() => setDrawerOpen(false)}>Cancelar</Button></Col>
            <Col><Button type="primary" htmlType="submit" loading={saving} disabled={selectedCurrencyWithoutRate} {...FORM_DRAWER_SUBMIT_PROPS}>Registrar</Button></Col>
          </Row>
        </Form>
      </Drawer>

      <Drawer title="Detalle del pago" width={620} open={Boolean(detail)} onClose={() => setDetail(null)} maskClosable={false}>
        {detail ? (
          <>
            {detail.receipt?.id && canPrintReceipts ? (
              <div style={{ marginBottom: 16 }}>
                <Button type="primary" onClick={() => openReceiptPrintable(apiClient, detail.receipt.id, message)}>
                  Imprimir comprobante
                </Button>
              </div>
            ) : null}
            <Descriptions bordered column={1} size="small">
              <Descriptions.Item label="Pedido">{detail.pedido_codigo}</Descriptions.Item>
              <Descriptions.Item label="Cliente">{detail.client_name}</Descriptions.Item>
              <Descriptions.Item label="Fecha">{new Date(detail.fecha).toLocaleString()}</Descriptions.Item>
              <Descriptions.Item label="Moneda">{detail.currency?.codigo}</Descriptions.Item>
              <Descriptions.Item label="Monto origen">{`${Number(detail.monto || 0).toFixed(2)} ${detail.currency?.codigo}`}</Descriptions.Item>
              <Descriptions.Item label="Monto en Bs">{formatBs(detail.monto_bob)}</Descriptions.Item>
              <Descriptions.Item label="Método">{labelFromOptions(METODO_PAGO_OPTIONS, detail.metodo_pago)}</Descriptions.Item>
              <Descriptions.Item label="Estado"><Tag color={paymentStateColor(detail.estado)}>{labelFromOptions(ESTADO_PAGO_OPTIONS, detail.estado)}</Tag></Descriptions.Item>
              <Descriptions.Item label="Comprobante interno">
                {detail.receipt ? `${detail.receipt.codigo} (${detail.receipt.estado.toUpperCase()})` : 'SIN REGISTRO'}
              </Descriptions.Item>
              <Descriptions.Item label="Observaciones">{detail.observaciones || 'SIN OBSERVACIONES'}</Descriptions.Item>
              <Descriptions.Item label="Motivo cambio estado">{detail.motivo_cambio_estado || 'SIN REGISTRO'}</Descriptions.Item>
            </Descriptions>
          </>
        ) : null}
      </Drawer>

      <Modal title="Anular pago" open={Boolean(annulPayment)} onCancel={() => setAnnulPayment(null)} onOk={async () => {
        try {
          const values = await annulForm.validateFields()
          setAnnulPayment(null)
          annulForm.resetFields()
          navigate(
            buildRefundPath({
              originType: 'PAGO_PEDIDO',
              originId: annulPayment.id,
              targetState: 'ANULADA',
              returnTo: `${location.pathname}${location.search}`,
            }),
            { state: { refundReason: values.reason } },
          )
        } catch (requestError) {
          if (requestError?.errorFields) return
          message.error('NO FUE POSIBLE INICIAR EL FLUJO ECONÓMICO DE DEVOLUCIÓN.')
        }
      }} confirmLoading={saving} okButtonProps={{ danger: true }} maskClosable={false}>
        <Alert type="warning" showIcon message="La anulación del pago te redirigirá al flujo económico obligatorio para registrar cuánto dinero se devuelve a la clienta." style={{ marginBottom: 12 }} />
        <Form form={annulForm} layout="vertical">
          <Form.Item name="reason" label="Motivo de anulación" rules={[{ required: true, message: 'Debe escribir el motivo.' }, { min: 5, message: 'El motivo debe ser más específico.' }]} normalize={(value) => (value || '').toUpperCase()}><Input.TextArea rows={3} placeholder="Describe el motivo de anulación" /></Form.Item>
        </Form>
      </Modal>
    </>
  )
}
