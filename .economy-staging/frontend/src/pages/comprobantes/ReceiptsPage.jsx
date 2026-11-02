import { EyeOutlined, FilePdfOutlined, LinkOutlined, SearchOutlined } from '@ant-design/icons'
import { Alert, App as AntdApp, Button, Col, DatePicker, Descriptions, Drawer, Input, Row, Select, Table, Tag, Typography } from 'antd'
import { useCallback, useEffect, useMemo, useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'

import { apiClient } from '../../api/client'
import { METODO_PAGO_OPTIONS, labelFromOptions } from '../boutique/boutiqueConstants'
import {
  buildReceiptOriginPath,
  formatReceiptMoney,
  openReceiptPrintable,
  RECEIPT_ORIGIN_OPTIONS,
  RECEIPT_STATE_OPTIONS,
  receiptOriginLabel,
  receiptStateColor,
} from './receiptUtils'

const { RangePicker } = DatePicker

export function ReceiptsPage() {
  const [receipts, setReceipts] = useState([])
  const [clients, setClients] = useState([])
  const [currencies, setCurrencies] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [detail, setDetail] = useState(null)
  const [detailOpen, setDetailOpen] = useState(false)
  const [filters, setFilters] = useState({
    search: '',
    origin_type: undefined,
    state: undefined,
    currency_id: undefined,
    payment_method: undefined,
    client_id: undefined,
    date_from: undefined,
    date_to: undefined,
  })
  const { message } = AntdApp.useApp()
  const navigate = useNavigate()
  const [searchParams, setSearchParams] = useSearchParams()

  const loadReferences = useCallback(async () => {
    const [clientResponse, currencyResponse] = await Promise.all([
      apiClient.get('/clientes'),
      apiClient.get('/monedas'),
    ])
    setClients(clientResponse.data)
    setCurrencies(currencyResponse.data)
  }, [])

  const loadReceipts = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const params = {}
      if (filters.search) params.search = filters.search
      if (filters.origin_type) params.origin_type = filters.origin_type
      if (filters.state) params.state = filters.state
      if (filters.currency_id) params.currency_id = filters.currency_id
      if (filters.payment_method) params.payment_method = filters.payment_method
      if (filters.client_id) params.client_id = filters.client_id
      if (filters.date_from) params.date_from = filters.date_from
      if (filters.date_to) params.date_to = filters.date_to
      const response = await apiClient.get('/comprobantes', { params })
      setReceipts(response.data)
    } catch (requestError) {
      setError(requestError.response?.data?.detail || 'NO FUE POSIBLE CARGAR EL HISTORIAL DE COMPROBANTES INTERNOS.')
    } finally {
      setLoading(false)
    }
  }, [filters])

  useEffect(() => {
    Promise.all([loadReferences(), loadReceipts()]).catch(() => {
      setError('NO FUE POSIBLE CARGAR LA INFORMACIÓN INICIAL DE COMPROBANTES INTERNOS.')
      setLoading(false)
    })
  }, [loadReferences, loadReceipts])

  const openDetail = useCallback(async (record) => {
    try {
      const response = await apiClient.get(`/comprobantes/${record.id}`)
      setDetail(response.data)
      setDetailOpen(true)
    } catch (requestError) {
      message.error(requestError.response?.data?.detail || 'NO FUE POSIBLE CARGAR EL DETALLE DEL COMPROBANTE.')
    }
  }, [message])

  useEffect(() => {
    const receiptId = searchParams.get('receipt_id')
    if (!receiptId) return
    openDetail({ id: Number(receiptId) }).finally(() => {
      const next = new URLSearchParams(searchParams)
      next.delete('receipt_id')
      setSearchParams(next, { replace: true })
    })
  }, [openDetail, searchParams, setSearchParams])

  const clientOptions = useMemo(
    () => clients.map((client) => ({ label: `${client.codigo} - ${client.full_name}`, value: client.id })),
    [clients],
  )
  const currencyOptions = useMemo(
    () => currencies.map((currency) => ({ label: `${currency.codigo} - ${currency.nombre}`, value: currency.id })),
    [currencies],
  )

  const columns = [
    { title: 'CÓDIGO', dataIndex: 'codigo', key: 'codigo' },
    { title: 'FECHA', dataIndex: 'fecha', key: 'fecha', render: (value) => new Date(value).toLocaleString('es-BO') },
    { title: 'ORIGEN', dataIndex: 'origin_type', key: 'origin_type', render: receiptOriginLabel },
    { title: 'CLIENTE', dataIndex: 'client_name', key: 'client_name' },
    { title: 'MONEDA', dataIndex: 'currency_code', key: 'currency_code', render: (value) => value || 'SIN MONEDA' },
    { title: 'TOTAL BS', dataIndex: 'total', key: 'total', render: (value) => `Bs ${formatReceiptMoney(value)}` },
    { title: 'TOTAL MONEDA ORIGEN', dataIndex: 'total_moneda_original', key: 'total_moneda_original', render: (value) => formatReceiptMoney(value) },
    {
      title: 'MÉTODO',
      dataIndex: 'payment_method',
      key: 'payment_method',
      render: (value) => value ? labelFromOptions(METODO_PAGO_OPTIONS, value) : 'SIN REGISTRO',
    },
    {
      title: 'ESTADO',
      dataIndex: 'estado',
      key: 'estado',
      render: (value) => <Tag color={receiptStateColor(value)}>{value.toUpperCase()}</Tag>,
    },
    {
      title: 'ACCIONES',
      key: 'acciones',
      render: (_, record) => (
        <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
          <Button icon={<EyeOutlined />} onClick={() => openDetail(record)}>Ver</Button>
          <Button icon={<FilePdfOutlined />} onClick={() => openReceiptPrintable(apiClient, record.id, message)}>Imprimir</Button>
          <Button icon={<LinkOutlined />} onClick={() => navigate(buildReceiptOriginPath(record))}>Ir al origen</Button>
        </div>
      ),
    },
  ]

  return (
    <div>
      <div className="page-header">
        <div>
          <Typography.Title level={2} style={{ margin: 0 }}>
            Comprobantes Internos
          </Typography.Title>
          <Typography.Paragraph type="secondary" style={{ marginBottom: 0 }}>
            Historial documental no fiscal de ventas boutique, pagos de pedidos y salidas de flete.
          </Typography.Paragraph>
        </div>
      </div>

      <div className="glass-panel boutique-filter-bar">
        <Row gutter={[12, 12]}>
          <Col xs={24} md={6}>
            <Input
              allowClear
              prefix={<SearchOutlined />}
              placeholder="Buscar código, cliente, CI/NIT o celular"
              value={filters.search}
              onChange={(event) => setFilters((current) => ({ ...current, search: event.target.value }))}
            />
          </Col>
          <Col xs={24} md={4}>
            <Select
              allowClear
              placeholder="Origen"
              options={RECEIPT_ORIGIN_OPTIONS}
              value={filters.origin_type}
              onChange={(value) => setFilters((current) => ({ ...current, origin_type: value }))}
              style={{ width: '100%' }}
            />
          </Col>
          <Col xs={24} md={4}>
            <Select
              allowClear
              placeholder="Estado"
              options={RECEIPT_STATE_OPTIONS}
              value={filters.state}
              onChange={(value) => setFilters((current) => ({ ...current, state: value }))}
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
          <Col xs={24} md={3}>
            <Select
              allowClear
              placeholder="Moneda"
              options={currencyOptions}
              value={filters.currency_id}
              onChange={(value) => setFilters((current) => ({ ...current, currency_id: value }))}
              style={{ width: '100%' }}
            />
          </Col>
          <Col xs={24} md={3}>
            <Select
              allowClear
              placeholder="Método"
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
        dataSource={receipts}
        loading={loading}
        pagination={{ pageSize: 8 }}
        scroll={{ x: 'max-content' }}
        style={{ borderRadius: 24, overflow: 'hidden' }}
      />

      <Drawer
        title="Detalle del Comprobante Interno"
        width={920}
        open={detailOpen}
        onClose={() => {
          setDetailOpen(false)
          setDetail(null)
        }}
        maskClosable={false}
      >
        {detail ? (
          <div style={{ position: 'relative' }}>
            {detail.estado === 'anulado' ? (
              <div
                style={{
                  position: 'absolute',
                  inset: 0,
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  fontSize: 54,
                  fontWeight: 900,
                  color: 'rgba(143, 61, 46, 0.12)',
                  transform: 'rotate(-22deg)',
                  pointerEvents: 'none',
                  zIndex: 1,
                }}
              >
                ANULADO
              </div>
            ) : null}

            <Row gutter={[12, 12]} style={{ marginBottom: 16 }}>
              <Col>
                <Button type="primary" icon={<FilePdfOutlined />} onClick={() => openReceiptPrintable(apiClient, detail.id, message)}>
                  Imprimir comprobante
                </Button>
              </Col>
              <Col>
                <Button icon={<LinkOutlined />} onClick={() => navigate(buildReceiptOriginPath(detail))}>
                  Ir al origen
                </Button>
              </Col>
            </Row>

            <Descriptions bordered size="small" column={2}>
              <Descriptions.Item label="Código">{detail.codigo}</Descriptions.Item>
              <Descriptions.Item label="Estado">
                <Tag color={receiptStateColor(detail.estado)}>{detail.estado.toUpperCase()}</Tag>
              </Descriptions.Item>
              <Descriptions.Item label="Fecha">{new Date(detail.fecha).toLocaleString('es-BO')}</Descriptions.Item>
              <Descriptions.Item label="Tipo">{detail.tipo_comprobante}</Descriptions.Item>
              <Descriptions.Item label="Origen">{receiptOriginLabel(detail.origin_type)}</Descriptions.Item>
              <Descriptions.Item label="ID origen">#{detail.origin_id}</Descriptions.Item>
              <Descriptions.Item label="Cliente">{detail.client.full_name}</Descriptions.Item>
              <Descriptions.Item label="CI / NIT">{detail.client.ci_nit}</Descriptions.Item>
              <Descriptions.Item label="Celular">{detail.client.cellphone}</Descriptions.Item>
              <Descriptions.Item label="Registrado por">{detail.registered_by.full_name}</Descriptions.Item>
              <Descriptions.Item label="Usuario">{detail.registered_by.username || 'SIN USUARIO'}</Descriptions.Item>
              <Descriptions.Item label="Moneda">{detail.currency?.codigo || 'SIN MONEDA'}</Descriptions.Item>
              <Descriptions.Item label="Método de pago">
                {detail.payment_method ? labelFromOptions(METODO_PAGO_OPTIONS, detail.payment_method) : 'SIN REGISTRO'}
              </Descriptions.Item>
              <Descriptions.Item label="Tipo de cambio usado">{formatReceiptMoney(detail.tipo_cambio_usado)}</Descriptions.Item>
              <Descriptions.Item label="Subtotal">Bs {formatReceiptMoney(detail.subtotal)}</Descriptions.Item>
              <Descriptions.Item label="Descuento">Bs {formatReceiptMoney(detail.descuento)}</Descriptions.Item>
              <Descriptions.Item label="Total">Bs {formatReceiptMoney(detail.total)}</Descriptions.Item>
              <Descriptions.Item label="Total moneda origen">
                {detail.currency?.simbolo || detail.currency?.codigo || ''} {formatReceiptMoney(detail.total_moneda_original)}
              </Descriptions.Item>
              <Descriptions.Item label="Saldo posterior">Bs {formatReceiptMoney(detail.saldo_posterior)}</Descriptions.Item>
              <Descriptions.Item label="Garantía">Bs {formatReceiptMoney(detail.garantia)}</Descriptions.Item>
              <Descriptions.Item label="Motivo cambio estado" span={2}>
                {detail.state_change_reason || 'SIN CAMBIO DE ESTADO'}
              </Descriptions.Item>
            </Descriptions>

            <Typography.Title level={5} style={{ marginTop: 20 }}>
              Detalle comercial
            </Typography.Title>
            <Table
              rowKey="id"
              pagination={false}
              size="small"
              columns={[
                { title: 'CONCEPTO', dataIndex: 'concepto', key: 'concepto' },
                { title: 'CANTIDAD', dataIndex: 'cantidad', key: 'cantidad', render: (value) => formatReceiptMoney(value) },
                { title: 'PRECIO UNIDAD', dataIndex: 'precio_unidad', key: 'precio_unidad', render: (value) => `Bs ${formatReceiptMoney(value)}` },
                { title: 'DESCUENTO', dataIndex: 'descuento', key: 'descuento', render: (value) => `Bs ${formatReceiptMoney(value)}` },
                { title: 'SUBTOTAL', dataIndex: 'subtotal', key: 'subtotal', render: (value) => `Bs ${formatReceiptMoney(value)}` },
                { title: 'OBSERVACIONES', dataIndex: 'observaciones', key: 'observaciones', render: (value) => value || 'SIN OBSERVACIONES' },
              ]}
              dataSource={detail.details}
            />

            <Alert
              type="info"
              showIcon
              style={{ marginTop: 16 }}
              message="ESTE DOCUMENTO ES UN COMPROBANTE INTERNO NO FISCAL Y NO SUSTITUYE FACTURA."
            />
          </div>
        ) : null}
      </Drawer>
    </div>
  )
}
