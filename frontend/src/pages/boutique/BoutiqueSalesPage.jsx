/* eslint-disable react-hooks/exhaustive-deps */
import { CloseCircleOutlined, EyeOutlined, PlusOutlined, RollbackOutlined, SearchOutlined, StopOutlined } from '@ant-design/icons'
import {
  Alert,
  App as AntdApp,
  Button,
  DatePicker,
  Drawer,
  Form,
  Input,
  Modal,
  Row,
  Col,
  Select,
  Table,
  Tag,
  Typography,
} from 'antd'
import { useCallback, useEffect, useMemo, useState } from 'react'
import { useSearchParams } from 'react-router-dom'

import { apiClient } from '../../api/client'
import { useAuth } from '../../auth/AuthProvider'
import { FORM_COMMON_PROPS } from '../../components/forms/formConfig'
import { applyFormApiError } from '../../components/forms/formErrorUtils'
import { FormProcessAlert } from '../../components/forms/FormProcessAlert'
import { BoutiqueSaleDetailCard } from './BoutiqueSaleDetailCard'
import { BoutiqueSaleForm } from './BoutiqueSaleForm'
import { ESTADO_VENTA_OPTIONS, METODO_PAGO_OPTIONS, formatBs, labelFromOptions } from './boutiqueConstants'
import { openReceiptPrintable } from '../comprobantes/receiptUtils'

const { RangePicker } = DatePicker

export function BoutiqueSalesPage() {
  const [sales, setSales] = useState([])
  const [items, setItems] = useState([])
  const [clients, setClients] = useState([])
  const [currencies, setCurrencies] = useState([])
  const [exchangeRates, setExchangeRates] = useState([])
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState(null)
  const [formError, setFormError] = useState(null)
  const [reasonFormError, setReasonFormError] = useState(null)
  const [filters, setFilters] = useState({
    search: '',
    item_id: undefined,
    client_id: undefined,
    currency_id: undefined,
    payment_method: undefined,
    state: undefined,
    date_from: undefined,
    date_to: undefined,
  })
  const [formOpen, setFormOpen] = useState(false)
  const [detailOpen, setDetailOpen] = useState(false)
  const [selectedSale, setSelectedSale] = useState(null)
  const [stateAction, setStateAction] = useState(null)
  const [form] = Form.useForm()
  const [reasonForm] = Form.useForm()
  const [searchParams, setSearchParams] = useSearchParams()
  const { message } = AntdApp.useApp()
  const { user } = useAuth()

  const canCreate = user?.permissions?.includes('boutique_sales:create')
  const canView = user?.permissions?.includes('boutique_sales:view')
  const canCancel = user?.permissions?.includes('boutique_sales:cancel')
  const canAnnul = user?.permissions?.includes('boutique_sales:annul')
  const canPickClient = user?.permissions?.includes('clients:list')
  const canViewReceipts = user?.permissions?.includes('receipts:view')
  const canPrintReceipts = user?.permissions?.includes('receipts:print')

  const loadReferenceData = useCallback(async () => {
    const [itemResponse, currencyResponse, rateResponse] = await Promise.all([
      apiClient.get('/boutique/items', { params: { is_active: true } }),
      apiClient.get('/monedas', { params: { is_active: true } }),
      apiClient.get('/monedas/tipos-cambio', { params: { is_active: true } }),
    ])
    setItems(itemResponse.data)
    setCurrencies(currencyResponse.data)
    setExchangeRates(rateResponse.data)

    if (canPickClient) {
      const clientResponse = await apiClient.get('/clientes', { params: { is_active: true } })
      setClients(clientResponse.data)
    } else {
      setClients([])
    }
  }, [canPickClient])

  const loadSales = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const params = {}
      if (filters.search) params.search = filters.search
      if (filters.item_id) params.item_id = filters.item_id
      if (filters.client_id) params.client_id = filters.client_id
      if (filters.currency_id) params.currency_id = filters.currency_id
      if (filters.payment_method) params.payment_method = filters.payment_method
      if (filters.state) params.state = filters.state
      if (filters.date_from) params.date_from = filters.date_from
      if (filters.date_to) params.date_to = filters.date_to
      const response = await apiClient.get('/boutique/sales', { params })
      setSales(response.data)
    } catch (requestError) {
      setError(requestError.response?.data?.detail || 'No fue posible cargar las ventas boutique.')
    } finally {
      setLoading(false)
    }
  }, [filters])

  useEffect(() => {
    Promise.all([loadReferenceData(), loadSales()]).catch(() => {
      setError('No fue posible cargar la información inicial del módulo de ventas boutique.')
      setLoading(false)
    })
  }, [])

  useEffect(() => {
    loadSales()
  }, [filters.search, filters.item_id, filters.client_id, filters.currency_id, filters.payment_method, filters.state, filters.date_from, filters.date_to])

  useEffect(() => {
    const saleId = searchParams.get('sale_id')
    if (!saleId || !canView) return
    openView({ id: Number(saleId) }).finally(() => {
      const next = new URLSearchParams(searchParams)
      next.delete('sale_id')
      setSearchParams(next, { replace: true })
    })
  }, [canView, searchParams, setSearchParams])

  const itemOptions = useMemo(
    () => items.map((item) => ({ label: `${item.code} - ${item.name}`, value: item.id })),
    [items],
  )
  const clientOptions = useMemo(
    () => clients.map((client) => ({ label: `${client.codigo} - ${client.full_name}`, value: client.id })),
    [clients],
  )
  const currencyOptions = useMemo(
    () => currencies.map((currency) => ({ label: `${currency.codigo} - ${currency.nombre}`, value: currency.id })),
    [currencies],
  )

  const openCreate = () => {
    form.resetFields()
    setFormError(null)
    setFormOpen(true)
  }

  const openView = async (record) => {
    try {
      const response = await apiClient.get(`/boutique/sales/${record.id}`)
      setSelectedSale(response.data)
      setDetailOpen(true)
    } catch (requestError) {
      message.error(requestError.response?.data?.detail || 'No fue posible cargar el detalle de la venta.')
    }
  }

  const handleCreate = async (values) => {
    setSaving(true)
    setFormError(null)
    try {
      const response = await apiClient.post('/boutique/sales', values)
      message.success('Se registró la venta correctamente.')
      if (response.data?.receipt?.id && canPrintReceipts) {
        await openReceiptPrintable(apiClient, response.data.receipt.id, message)
      }
      setFormOpen(false)
      form.resetFields()
      await Promise.all([loadSales(), loadReferenceData()])
    } catch (requestError) {
      const resolved = applyFormApiError(form, requestError, {
        messageFieldMap: [
          { test: /cliente.*inactivo/i, field: 'client_id' },
          { test: /cliente no encontrado/i, field: 'client_id' },
          { test: /producto boutique.*no encontrado/i, field: 'item_id' },
          { test: /producto boutique.*inactivo/i, field: 'item_id' },
          { test: /stock disponible/i, field: 'quantity' },
          { test: /moneda seleccionada no tiene un tipo de cambio activo/i, field: 'currency_id' },
          { test: /descuento no puede ser mayor/i, field: 'discount' },
          { test: /motivo del descuento/i, field: 'discount_reason' },
        ],
        fallbackGlobalMessage: 'No fue posible registrar la venta.',
      })
      setFormError(resolved.globalMessage)
    } finally {
      setSaving(false)
    }
  }

  const openStateModal = (record, action) => {
    setStateAction({ sale: record, action })
    setReasonFormError(null)
    reasonForm.resetFields()
  }

  const submitStateChange = async () => {
    setSaving(true)
    setReasonFormError(null)
    try {
      const values = await reasonForm.validateFields()
      const endpoint = stateAction.action === 'cancel' ? 'cancel' : 'annul'
      await apiClient.patch(`/boutique/sales/${stateAction.sale.id}/${endpoint}`, values)
      message.success(`Se ${stateAction.action === 'cancel' ? 'canceló' : 'anuló'} la venta correctamente.`)
      setStateAction(null)
      reasonForm.resetFields()
      if (selectedSale?.id === stateAction.sale.id) {
        const response = await apiClient.get(`/boutique/sales/${stateAction.sale.id}`)
        setSelectedSale(response.data)
      }
      await Promise.all([loadSales(), loadReferenceData()])
    } catch (requestError) {
      if (requestError?.errorFields) return
      const resolved = applyFormApiError(reasonForm, requestError, {
        fallbackGlobalMessage: 'No fue posible actualizar el estado de la venta.',
      })
      setReasonFormError(resolved.globalMessage)
    } finally {
      setSaving(false)
    }
  }

  const columns = [
    {
      title: 'Fecha',
      dataIndex: 'fecha',
      key: 'fecha',
      render: (value) => new Date(value).toLocaleString(),
    },
    { title: 'Producto', dataIndex: 'item_name', key: 'item_name' },
    { title: 'Código', dataIndex: 'item_code', key: 'item_code' },
    {
      title: 'Cliente',
      key: 'client_name',
      render: (_, record) => record.client_name || 'VENTA SIN CLIENTE',
    },
    { title: 'Moneda', dataIndex: 'currency_code', key: 'currency_code' },
    { title: 'Cantidad', dataIndex: 'quantity', key: 'quantity' },
    {
      title: 'P. Unitario (Bs)',
      dataIndex: 'unit_price',
      key: 'unit_price',
      render: (value) => formatBs(value),
    },
    {
      title: 'Total (Bs)',
      dataIndex: 'total',
      key: 'total',
      render: (value) => <Typography.Text strong>{formatBs(value)}</Typography.Text>,
    },
    {
      title: 'Total moneda origen',
      dataIndex: 'total_currency_origin',
      key: 'total_currency_origin',
      render: (value) => formatBs(value),
    },
    {
      title: 'Método',
      dataIndex: 'payment_method',
      key: 'payment_method',
      render: (value) => <Tag color="gold">{labelFromOptions(METODO_PAGO_OPTIONS, value)}</Tag>,
    },
    {
      title: 'Estado',
      dataIndex: 'estado',
      key: 'estado',
      render: (value) => (
        <Tag color={value === 'activa' ? 'green' : value === 'cancelada' ? 'orange' : 'red'}>
          {labelFromOptions(ESTADO_VENTA_OPTIONS, value)}
        </Tag>
      ),
    },
    { title: 'Registrado por', dataIndex: 'registered_by', key: 'registered_by' },
    {
      title: 'Acciones',
      key: 'acciones',
      render: (_, record) => (
        <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
          {canView ? (
            <Button icon={<EyeOutlined />} onClick={() => openView(record)}>
              Ver
            </Button>
          ) : null}
          {canCancel && record.estado === 'activa' ? (
            <Button icon={<RollbackOutlined />} onClick={() => openStateModal(record, 'cancel')}>
              Cancelar
            </Button>
          ) : null}
          {canAnnul && record.estado === 'activa' ? (
            <Button danger icon={<StopOutlined />} onClick={() => openStateModal(record, 'annul')}>
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
            Ventas Boutique
          </Typography.Title>
          <Typography.Paragraph type="secondary" style={{ marginBottom: 0 }}>
            Registra ventas directas, usa moneda activa y conserva la trazabilidad del tipo de cambio aplicado.
          </Typography.Paragraph>
        </div>
        {canCreate ? (
          <Button type="primary" icon={<PlusOutlined />} onClick={openCreate}>
            Nueva venta
          </Button>
        ) : null}
      </div>

      <div className="glass-panel boutique-filter-bar">
        <Row gutter={[12, 12]}>
          <Col xs={24} md={8}>
            <Input
              allowClear
              prefix={<SearchOutlined />}
              placeholder="Buscar por producto o cliente"
              value={filters.search}
              onChange={(event) => setFilters((current) => ({ ...current, search: event.target.value }))}
            />
          </Col>
          <Col xs={24} md={4}>
            <Select
              allowClear
              showSearch
              optionFilterProp="label"
              placeholder="Producto"
              options={itemOptions}
              value={filters.item_id}
              onChange={(value) => setFilters((current) => ({ ...current, item_id: value }))}
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
              options={ESTADO_VENTA_OPTIONS}
              value={filters.state}
              onChange={(value) => setFilters((current) => ({ ...current, state: value }))}
              style={{ width: '100%' }}
            />
          </Col>
          <Col xs={24} md={6}>
            <Select
              allowClear
              placeholder="Método de pago"
              options={METODO_PAGO_OPTIONS}
              value={filters.payment_method}
              onChange={(value) => setFilters((current) => ({ ...current, payment_method: value }))}
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
        dataSource={sales}
        loading={loading}
        pagination={{ pageSize: 8 }}
        scroll={{ x: 'max-content' }}
        style={{ borderRadius: 24, overflow: 'hidden' }}
      />

      <Drawer
        title="Registrar Venta Boutique"
        width={840}
        open={formOpen}
        onClose={() => {
          setFormOpen(false)
          setFormError(null)
          form.resetFields()
        }}
        destroyOnClose
        maskClosable={false}
      >
        <FormProcessAlert message={formError} title="No fue posible registrar la venta." />
        <BoutiqueSaleForm
          form={form}
          items={items.filter((item) => item.is_active)}
          clients={clients}
          currencies={currencies}
          exchangeRates={exchangeRates}
          saving={saving}
          canPickClient={canPickClient}
          onFinish={handleCreate}
        />
      </Drawer>

      <Modal
        title="Detalle de Venta Boutique"
        open={detailOpen}
        onCancel={() => {
          setDetailOpen(false)
          setSelectedSale(null)
        }}
        maskClosable={false}
        footer={[
          selectedSale?.receipt && canPrintReceipts ? (
            <Button key="print-receipt" type="primary" onClick={() => openReceiptPrintable(apiClient, selectedSale.receipt.id, message)}>
              Imprimir comprobante
            </Button>
          ) : null,
          selectedSale?.receipt && canViewReceipts ? (
            <Button key="view-receipt" onClick={() => window.open(`/app/comprobantes?receipt_id=${selectedSale.receipt.id}`, '_self')}>
              Ver comprobante
            </Button>
          ) : null,
          <Button key="close" onClick={() => { setDetailOpen(false); setSelectedSale(null) }}>
            Cerrar
          </Button>,
        ].filter(Boolean)}
        width={900}
      >
        <BoutiqueSaleDetailCard sale={selectedSale} />
      </Modal>

      <Modal
        title={stateAction?.action === 'cancel' ? 'Cancelar venta' : 'Anular venta'}
        open={Boolean(stateAction)}
        onCancel={() => {
          setStateAction(null)
          setReasonFormError(null)
          reasonForm.resetFields()
        }}
        onOk={submitStateChange}
        confirmLoading={saving}
        maskClosable={false}
        okText={stateAction?.action === 'cancel' ? 'Confirmar cancelación' : 'Confirmar anulación'}
        cancelText="Cerrar"
      >
        {stateAction ? (
          <>
            <Alert
              type={stateAction.action === 'cancel' ? 'warning' : 'error'}
              showIcon
              icon={stateAction.action === 'cancel' ? <CloseCircleOutlined /> : undefined}
              message={`La venta #${stateAction.sale.id} devolverá la cantidad vendida al stock del producto.`}
              style={{ marginBottom: 16 }}
            />
            <FormProcessAlert
              message={reasonFormError}
              title="No fue posible completar la reversión."
              style={{ marginBottom: 16 }}
            />
            <Form {...FORM_COMMON_PROPS} form={reasonForm}>
              <Row gutter={12}>
                <Col span={24}>
                  <Form.Item
                    label="Motivo operativo"
                    name="reason"
                    rules={[{ required: true, message: 'Debe registrar el Motivo operativo de la reversión.' }]}
                    normalize={(value) => (value || '').toUpperCase()}
                  >
                    <Input.TextArea rows={3} placeholder="Ej. CLIENTE DESISTIÓ DE LA COMPRA O SE REGISTRÓ LA VENTA POR ERROR" />
                  </Form.Item>
                </Col>
              </Row>
            </Form>
          </>
        ) : null}
      </Modal>
    </div>
  )
}
