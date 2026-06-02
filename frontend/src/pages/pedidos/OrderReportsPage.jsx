import { FilePdfOutlined, ReloadOutlined, SearchOutlined } from '@ant-design/icons'
import {
  Alert,
  App as AntdApp,
  Button,
  Card,
  Col,
  DatePicker,
  Descriptions,
  Empty,
  Row,
  Select,
  Statistic,
  Table,
  Tag,
  Typography,
} from 'antd'
import { useCallback, useEffect, useMemo, useState } from 'react'

import { apiClient } from '../../api/client'
import { ESTADO_PRUEBA_OPTIONS, ESTADO_PAGO_OPTIONS, METODO_PAGO_OPTIONS, formatBs, labelFromOptions, testStateColor } from './orderConstants'

const { RangePicker } = DatePicker

export function OrderReportsPage() {
  const [clients, setClients] = useState([])
  const [balances, setBalances] = useState([])
  const [deliveries, setDeliveries] = useState([])
  const [paymentReport, setPaymentReport] = useState(null)
  const [testReport, setTestReport] = useState(null)
  const [selectedClient, setSelectedClient] = useState(null)
  const [clientSummary, setClientSummary] = useState(null)
  const [dateRange, setDateRange] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const { message } = AntdApp.useApp()

  const clientOptions = useMemo(
    () => clients.map((client) => ({ label: `${client.codigo} - ${client.full_name}`, value: client.id })),
    [clients],
  )

  const loadReports = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const params = {}
      if (dateRange?.[0]) params.date_from = dateRange[0].format('YYYY-MM-DD')
      if (dateRange?.[1]) params.date_to = dateRange[1].format('YYYY-MM-DD')
      const [clientResponse, balanceResponse, paymentResponse, testResponse, deliveryResponse] = await Promise.all([
        apiClient.get('/clientes', { params: { is_active: true } }),
        apiClient.get('/pedidos/reportes/saldos'),
        apiClient.get('/pedidos/reportes/pagos', { params }),
        apiClient.get('/pedidos/reportes/pruebas', { params }),
        apiClient.get('/pedidos/reportes/entregas', { params }),
      ])
      setClients(clientResponse.data)
      setBalances(balanceResponse.data)
      setPaymentReport(paymentResponse.data)
      setTestReport(testResponse.data)
      setDeliveries(deliveryResponse.data)
    } catch (requestError) {
      setError(requestError.response?.data?.detail || 'No fue posible cargar reportes de pedidos.')
    } finally {
      setLoading(false)
    }
  }, [dateRange])

  useEffect(() => {
    loadReports()
  }, [loadReports])

  const loadClientSummary = async (clientId) => {
    setSelectedClient(clientId)
    setClientSummary(null)
    if (!clientId) return
    try {
      const response = await apiClient.get(`/pedidos/reportes/clientes/${clientId}/resumen`)
      setClientSummary(response.data)
    } catch (requestError) {
      message.error(requestError.response?.data?.detail || 'No fue posible cargar resumen del cliente.')
    }
  }

  const openPrintable = async () => {
    if (!selectedClient) return
    try {
      const response = await apiClient.get(`/pedidos/reportes/clientes/${selectedClient}/imprimible`, { responseType: 'text' })
      const popup = window.open('', '_blank')
      if (!popup) {
        message.error('El navegador bloqueó la ventana de impresión.')
        return
      }
      popup.document.write(response.data)
      popup.document.close()
    } catch (requestError) {
      message.error(requestError.response?.data?.detail || 'No fue posible generar el reporte imprimible.')
    }
  }

  const balanceColumns = [
    { title: 'CLIENTE', dataIndex: 'client_name' },
    { title: 'CONTRATADO', dataIndex: 'total_contratado', render: formatBs },
    { title: 'PAGADO', dataIndex: 'total_pagado', render: formatBs },
    { title: 'SALDO', dataIndex: 'saldo_pendiente', render: formatBs },
    { title: 'PEDIDOS ACTIVOS', dataIndex: 'active_orders' },
  ]

  const paymentColumns = [
    { title: 'FECHA', dataIndex: 'fecha', render: (value) => new Date(value).toLocaleString('es-BO') },
    { title: 'PEDIDO', dataIndex: 'pedido_codigo' },
    { title: 'CLIENTE', dataIndex: 'client_name' },
    { title: 'MÉTODO', dataIndex: 'metodo_pago', render: (value) => labelFromOptions(METODO_PAGO_OPTIONS, value) },
    { title: 'MONEDA', dataIndex: ['currency', 'codigo'] },
    { title: 'MONTO ORIGEN', dataIndex: 'monto', render: (value) => Number(value || 0).toFixed(2) },
    { title: 'MONTO BS', dataIndex: 'monto_bob', render: formatBs },
    { title: 'ESTADO', dataIndex: 'estado', render: (value) => <Tag color={value === 'registrado' ? 'green' : 'red'}>{labelFromOptions(ESTADO_PAGO_OPTIONS, value)}</Tag> },
    { title: 'REGISTRADO POR', dataIndex: 'registered_by' },
  ]

  const deliveryColumns = [
    { title: 'PEDIDO', dataIndex: 'codigo' },
    { title: 'CLIENTE', dataIndex: 'client_name' },
    { title: 'ENTREGA', dataIndex: 'fecha_entrega' },
    { title: 'SALDO', dataIndex: 'saldo', render: formatBs },
  ]

  const testColumns = [
    { title: 'PEDIDO', dataIndex: 'pedido_codigo' },
    { title: 'CLIENTE', dataIndex: 'client_name' },
    { title: 'PRUEBA', dataIndex: 'numero', render: (value) => `${value}° PRUEBA` },
    { title: 'FECHA', dataIndex: 'fecha' },
    { title: 'HORA', dataIndex: 'hora', render: (value) => value || 'SIN HORA' },
    {
      title: 'ESTADO',
      dataIndex: 'estado',
      render: (value) => <Tag color={testStateColor(value)}>{labelFromOptions(ESTADO_PRUEBA_OPTIONS, value)}</Tag>,
    },
    { title: 'ENTREGA', dataIndex: 'fecha_entrega' },
  ]

  const aggregateColumns = [
    { title: 'CRITERIO', dataIndex: 'label' },
    { title: 'TOTAL BS', dataIndex: 'total_bob', render: formatBs },
  ]

  return (
    <>
      <Row gutter={[16, 16]} align="middle" style={{ marginBottom: 16 }}>
        <Col flex="auto">
          <Typography.Title level={3} style={{ margin: 0 }}>Reportes de pedidos</Typography.Title>
          <Typography.Text type="secondary">Saldos, pagos, pruebas, entregas próximas y resumen imprimible por cliente.</Typography.Text>
        </Col>
        <Col><Button icon={<ReloadOutlined />} onClick={loadReports}>Actualizar</Button></Col>
      </Row>
      {error ? <Alert type="error" message={error} showIcon style={{ marginBottom: 16 }} /> : null}
      <Row gutter={[12, 12]} style={{ marginBottom: 16 }}>
        <Col xs={24} md={8}>
          <RangePicker
            placeholder={['Desde', 'Hasta']}
            format="DD/MM/YYYY"
            style={{ width: '100%' }}
            value={dateRange}
            onChange={(value) => setDateRange(value || [])}
          />
        </Col>
        <Col xs={24} md={10}>
          <Select
            allowClear
            showSearch
            prefix={<SearchOutlined />}
            placeholder="Selecciona cliente para resumen imprimible"
            options={clientOptions}
            optionFilterProp="label"
            value={selectedClient}
            onChange={loadClientSummary}
            style={{ width: '100%' }}
          />
        </Col>
        <Col xs={24} md={6}>
          <Button type="primary" icon={<FilePdfOutlined />} disabled={!selectedClient} onClick={openPrintable} style={{ width: '100%' }}>
            Imprimir cliente
          </Button>
        </Col>
      </Row>
      <Row gutter={[16, 16]} style={{ marginBottom: 16 }}>
        <Col xs={24} md={6}><Statistic title="SALDO PENDIENTE ACTIVO" value={balances.reduce((total, row) => total + Number(row.saldo_pendiente || 0), 0)} precision={2} prefix="Bs" /></Col>
        <Col xs={24} md={6}><Statistic title="PAGOS DEL PERIODO" value={paymentReport?.total_bob || 0} precision={2} prefix="Bs" /></Col>
        <Col xs={24} md={6}><Statistic title="PRUEBAS PRÓXIMAS" value={testReport?.upcoming?.length || 0} /></Col>
        <Col xs={24} md={6}><Statistic title="ENTREGAS PRÓXIMAS" value={deliveries.length} /></Col>
      </Row>

      {clientSummary ? (
        <Card title={`Resumen de ${clientSummary.client.full_name}`} style={{ marginBottom: 16 }}>
          <Row gutter={[16, 16]} style={{ marginBottom: 12 }}>
            <Col xs={24} md={6}><Statistic title="TOTAL CONTRATADO" value={clientSummary.total_contratado} precision={2} prefix="Bs" /></Col>
            <Col xs={24} md={6}><Statistic title="TOTAL PAGADO" value={clientSummary.total_pagado} precision={2} prefix="Bs" /></Col>
            <Col xs={24} md={6}><Statistic title="SALDO PENDIENTE" value={clientSummary.saldo_pendiente} precision={2} prefix="Bs" /></Col>
            <Col xs={24} md={6}><Statistic title="PEDIDOS ACTIVOS" value={clientSummary.pedidos_activos} /></Col>
          </Row>
          <Descriptions bordered size="small" column={2}>
            <Descriptions.Item label="CLIENTE">{clientSummary.client.full_name}</Descriptions.Item>
            <Descriptions.Item label="CÓDIGO">{clientSummary.client.codigo}</Descriptions.Item>
            <Descriptions.Item label="PEDIDOS INACTIVOS">{clientSummary.pedidos_inactivos}</Descriptions.Item>
            <Descriptions.Item label="PEDIDOS ENTREGADOS">{clientSummary.pedidos_entregados}</Descriptions.Item>
            <Descriptions.Item label="PEDIDOS CANCELADOS">{clientSummary.pedidos_cancelados}</Descriptions.Item>
            <Descriptions.Item label="CELULAR">{clientSummary.client.celular || 'SIN REGISTRO'}</Descriptions.Item>
          </Descriptions>
          <Typography.Title level={5} style={{ marginTop: 20 }}>Pedidos del cliente</Typography.Title>
          <Table
            rowKey="id"
            columns={[
              { title: 'CÓDIGO', dataIndex: 'codigo' },
              { title: 'TIPO', dataIndex: 'tipo', render: (value) => String(value || '').toUpperCase() },
              { title: 'ESTADO', dataIndex: 'estado_general', render: (value) => <Tag>{String(value || '').toUpperCase()}</Tag> },
              { title: 'TOTAL', dataIndex: 'precio_total', render: formatBs },
              { title: 'PAGADO', dataIndex: 'total_pagado', render: formatBs },
              { title: 'SALDO', dataIndex: 'saldo', render: formatBs },
            ]}
            dataSource={clientSummary.orders}
            pagination={false}
            size="small"
            scroll={{ x: 700 }}
          />
        </Card>
      ) : null}

      <Typography.Title level={4}>Saldos por cliente</Typography.Title>
      <Table rowKey="client_id" columns={balanceColumns} dataSource={balances} loading={loading} pagination={{ pageSize: 6 }} scroll={{ x: 700 }} />

      <Typography.Title level={4}>Pagos del periodo</Typography.Title>
      <Table rowKey="id" columns={paymentColumns} dataSource={paymentReport?.payments || []} loading={loading} pagination={{ pageSize: 6 }} scroll={{ x: 1200 }} />

      <Row gutter={[16, 16]} style={{ marginBottom: 16 }}>
        <Col xs={24} lg={8}>
          <Card title="Pagos por método" size="small">
            <Table rowKey="label" columns={aggregateColumns} dataSource={paymentReport?.by_method || []} pagination={false} size="small" locale={{ emptyText: 'SIN DATOS' }} />
          </Card>
        </Col>
        <Col xs={24} lg={8}>
          <Card title="Pagos por moneda" size="small">
            <Table rowKey="label" columns={aggregateColumns} dataSource={paymentReport?.by_currency || []} pagination={false} size="small" locale={{ emptyText: 'SIN DATOS' }} />
          </Card>
        </Col>
        <Col xs={24} lg={8}>
          <Card title="Pagos por usuario" size="small">
            <Table rowKey="label" columns={aggregateColumns} dataSource={paymentReport?.by_user || []} pagination={false} size="small" locale={{ emptyText: 'SIN DATOS' }} />
          </Card>
        </Col>
      </Row>

      <Typography.Title level={4}>Pruebas de hoy y próximas</Typography.Title>
      <Row gutter={[16, 16]} style={{ marginBottom: 16 }}>
        <Col xs={24} md={8}><Statistic title="PRUEBAS DE HOY" value={testReport?.today?.length || 0} /></Col>
        <Col xs={24} md={8}><Statistic title="PRUEBAS LISTAS" value={testReport?.ready_count || 0} /></Col>
        <Col xs={24} md={8}><Statistic title="PRUEBAS ATRASADAS" value={testReport?.late_count || 0} /></Col>
      </Row>
      <Table rowKey="id" columns={testColumns} dataSource={testReport?.upcoming || []} loading={loading} pagination={{ pageSize: 6 }} scroll={{ x: 900 }} />

      <Typography.Title level={4}>Pruebas pendientes o no listas</Typography.Title>
      {(testReport?.pending_or_not_ready || []).length ? (
        <Table rowKey="id" columns={testColumns} dataSource={testReport?.pending_or_not_ready || []} loading={loading} pagination={{ pageSize: 6 }} scroll={{ x: 900 }} />
      ) : (
        <Card><Empty description="No hay pruebas pendientes o con estado distinto a LISTO en el rango consultado." /></Card>
      )}

      <Typography.Title level={4}>Entregas próximas</Typography.Title>
      <Table rowKey="id" columns={deliveryColumns} dataSource={deliveries} loading={loading} pagination={{ pageSize: 6 }} />
    </>
  )
}
