import { DownloadOutlined, FilterOutlined } from '@ant-design/icons'
import { Alert, Button, Col, DatePicker, Row, Select, Table, Tabs, Tag, Typography } from 'antd'
import { useCallback, useEffect, useMemo, useState } from 'react'
import { Bar, BarChart, CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'

import { apiClient } from '../../api/client'
import { useAuth } from '../../auth/AuthProvider'
import { EconomyChartCard } from './EconomyChartCard'
import { EconomySummaryCard } from './EconomySummaryCard'
import { ECONOMY_CHART_COLORS, STORAGE_KEYS } from './economyConstants'
import { cutStateColor, cutStateLabel, downloadEconomyCsv, expenseTypeLabel, formatBs, getStoredFilters, incomeSourceLabel, storeFilters } from './economyUtils'

const { RangePicker } = DatePicker

const DEFAULT_REPORT_FILTERS = {
  date_from: undefined,
  date_to: undefined,
  cashier_id: undefined,
}

export function EconomyReportsPage() {
  const { user } = useAuth()
  const isAdmin = user?.role_code === 'ADMIN'
  const [filters, setFilters] = useState(() => getStoredFilters(STORAGE_KEYS.reports, DEFAULT_REPORT_FILTERS))
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [cashiers, setCashiers] = useState([])
  const [incomeStatement, setIncomeStatement] = useState(null)
  const [cashFlow, setCashFlow] = useState(null)
  const [cashierReport, setCashierReport] = useState(null)
  const [myPeriod, setMyPeriod] = useState(null)
  const [myIncomeStatement, setMyIncomeStatement] = useState(null)
  const [myHistory, setMyHistory] = useState(null)

  const syncStoredFilters = useCallback((nextFilters) => {
    storeFilters(STORAGE_KEYS.reports, nextFilters)
    setFilters(nextFilters)
  }, [])

  const loadAdminReports = useCallback(async () => {
    const params = {}
    if (filters.date_from) params.date_from = filters.date_from
    if (filters.date_to) params.date_to = filters.date_to
    if (filters.cashier_id) params.cashier_id = filters.cashier_id
    const [usersResponse, stateResponse, flowResponse] = await Promise.all([
      apiClient.get('/users'),
      apiClient.get('/economia/reportes/estado-resultados', { params }),
      apiClient.get('/economia/reportes/flujo-efectivo', { params }),
    ])
    setCashiers(usersResponse.data.filter((item) => item.role_code === 'CAJA'))
    setIncomeStatement(stateResponse.data)
    setCashFlow(flowResponse.data)
    if (filters.cashier_id) {
      const cashierResponse = await apiClient.get(`/economia/reportes/cajeros/${filters.cashier_id}`)
      setCashierReport(cashierResponse.data)
    } else {
      setCashierReport(null)
    }
  }, [filters.cashier_id, filters.date_from, filters.date_to])

  const loadCajaReports = useCallback(async () => {
    const [periodResponse, stateResponse, historyResponse] = await Promise.all([
      apiClient.get('/economia/reportes/mi-periodo'),
      apiClient.get('/economia/reportes/mi-estado-resultados'),
      apiClient.get('/economia/reportes/mi-historial'),
    ])
    setMyPeriod(periodResponse.data)
    setMyIncomeStatement(stateResponse.data)
    setMyHistory(historyResponse.data)
  }, [])

  const loadReports = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      if (isAdmin) {
        await loadAdminReports()
      } else {
        await loadCajaReports()
      }
    } catch (requestError) {
      setError(requestError.response?.data?.detail || 'NO FUE POSIBLE CARGAR LOS REPORTES ECONÓMICOS.')
    } finally {
      setLoading(false)
    }
  }, [isAdmin, loadAdminReports, loadCajaReports])

  useEffect(() => {
    loadReports()
  }, [loadReports])

  const cashierOptions = useMemo(
    () => cashiers.map((item) => ({ label: `${item.full_name} (${item.username})`, value: item.user_id })),
    [cashiers],
  )

  const exportAdmin = async (path) => {
    const params = {}
    if (filters.date_from) params.date_from = filters.date_from
    if (filters.date_to) params.date_to = filters.date_to
    if (filters.cashier_id) params.cashier_id = filters.cashier_id
    await downloadEconomyCsv(path, params)
  }

  const adminItems = [
    {
      key: 'estado',
      label: 'Estado de resultados',
      children: (
        <>
          <Row gutter={[14, 14]} style={{ marginBottom: 16 }}>
            <Col xs={24} md={8}><EconomySummaryCard eyebrow="INGRESOS" title="Ingresos brutos" value={formatBs(incomeStatement?.ingresos_total_bob)} accent="#4b7f5a" /></Col>
            <Col xs={24} md={8}><EconomySummaryCard eyebrow="EGRESOS" title="Salidas registradas" value={formatBs(incomeStatement?.egresos_total_bob)} accent="#b86c45" /></Col>
            <Col xs={24} md={8}><EconomySummaryCard eyebrow="RESULTADO" title="Neto del período" value={formatBs(incomeStatement?.resultado_bob)} accent="#4d2219" /></Col>
          </Row>
          <Row gutter={[16, 16]}>
            <Col xs={24} xl={14}>
              <EconomyChartCard title="Serie mensual" empty={!incomeStatement?.serie_mensual?.length}>
                <div style={{ width: '100%', minWidth: 0, height: 320 }}>
                  <ResponsiveContainer width="100%" height="100%" minWidth={0} minHeight={320}>
                    <LineChart data={incomeStatement?.serie_mensual || []}>
                      <CartesianGrid strokeDasharray="3 3" stroke="#eadbd2" />
                      <XAxis dataKey="period" stroke="#7c6a61" />
                      <YAxis stroke="#7c6a61" />
                      <Tooltip formatter={(value) => formatBs(value)} />
                      <Line type="monotone" dataKey="ingresos_total_bob" stroke={ECONOMY_CHART_COLORS.income} strokeWidth={3} />
                      <Line type="monotone" dataKey="egresos_total_bob" stroke={ECONOMY_CHART_COLORS.expense} strokeWidth={3} />
                      <Line type="monotone" dataKey="resultado_bob" stroke={ECONOMY_CHART_COLORS.result} strokeWidth={3} />
                    </LineChart>
                  </ResponsiveContainer>
                </div>
              </EconomyChartCard>
            </Col>
            <Col xs={24} xl={10}>
              <EconomyChartCard title="Egresos por tipo" empty={!incomeStatement?.egresos_por_tipo?.length}>
                <div style={{ width: '100%', minWidth: 0, height: 320 }}>
                  <ResponsiveContainer width="100%" height="100%" minWidth={0} minHeight={320}>
                    <BarChart data={(incomeStatement?.egresos_por_tipo || []).map((item) => ({ ...item, label: expenseTypeLabel(item.label.toLowerCase()) }))}>
                      <CartesianGrid strokeDasharray="3 3" stroke="#eadbd2" />
                      <XAxis dataKey="label" stroke="#7c6a61" tick={{ fontSize: 11 }} />
                      <YAxis stroke="#7c6a61" />
                      <Tooltip formatter={(value) => formatBs(value)} />
                      <Bar dataKey="total_bob" fill={ECONOMY_CHART_COLORS.expense} radius={[10, 10, 0, 0]} />
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              </EconomyChartCard>
            </Col>
          </Row>
        </>
      ),
    },
    {
      key: 'flujo',
      label: 'Flujo de efectivo',
      children: (
        <>
          <Row gutter={[14, 14]} style={{ marginBottom: 16 }}>
            <Col xs={24} md={8}><EconomySummaryCard eyebrow="ENTRADAS" title="Total de ingresos" value={formatBs(cashFlow?.entradas_total_bob)} accent="#4b7f5a" /></Col>
            <Col xs={24} md={8}><EconomySummaryCard eyebrow="EGRESOS" title="Total de salidas" value={formatBs(cashFlow?.egresos_total_bob)} accent="#b86c45" /></Col>
            <Col xs={24} md={8}><EconomySummaryCard eyebrow="FLUJO NETO" title="Resultado del flujo" value={formatBs(cashFlow?.flujo_neto_bob)} accent="#4d2219" /></Col>
          </Row>
          <Row gutter={[16, 16]}>
            <Col xs={24} xl={12}>
              <EconomyChartCard title="Métodos de pago" empty={!cashFlow?.entradas_por_metodo?.length}>
                <div style={{ width: '100%', minWidth: 0, height: 320 }}>
                  <ResponsiveContainer width="100%" height="100%" minWidth={0} minHeight={320}>
                    <BarChart data={cashFlow?.entradas_por_metodo || []}>
                      <CartesianGrid strokeDasharray="3 3" stroke="#eadbd2" />
                      <XAxis dataKey="label" stroke="#7c6a61" tick={{ fontSize: 11 }} />
                      <YAxis stroke="#7c6a61" />
                      <Tooltip formatter={(value) => formatBs(value)} />
                      <Bar dataKey="total_bob" fill={ECONOMY_CHART_COLORS.cash} radius={[10, 10, 0, 0]} />
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              </EconomyChartCard>
            </Col>
            <Col xs={24} xl={12}>
              <EconomyChartCard title="Fuentes de ingreso" empty={!cashFlow?.entradas_por_fuente?.length}>
                <div style={{ width: '100%', minWidth: 0, height: 320 }}>
                  <ResponsiveContainer width="100%" height="100%" minWidth={0} minHeight={320}>
                    <BarChart data={(cashFlow?.entradas_por_fuente || []).map((item) => ({ ...item, label: incomeSourceLabel(item.label) }))}>
                      <CartesianGrid strokeDasharray="3 3" stroke="#eadbd2" />
                      <XAxis dataKey="label" stroke="#7c6a61" tick={{ fontSize: 11 }} />
                      <YAxis stroke="#7c6a61" />
                      <Tooltip formatter={(value) => formatBs(value)} />
                      <Bar dataKey="total_bob" fill={ECONOMY_CHART_COLORS.income} radius={[10, 10, 0, 0]} />
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              </EconomyChartCard>
            </Col>
          </Row>
        </>
      ),
    },
    {
      key: 'cajeros',
      label: 'Cajeros',
      children: cashierReport ? (
        <>
          <Row gutter={[14, 14]} style={{ marginBottom: 16 }}>
            <Col xs={24} md={8}><EconomySummaryCard eyebrow="CAJERO" title="Reporte individual" value={cashierReport.cajero.full_name} accent="#4d2219" /></Col>
            <Col xs={24} md={8}><EconomySummaryCard eyebrow="CORTES" title="Períodos registrados" value={String(cashierReport.cortes.length)} accent="#4b7f5a" /></Col>
          </Row>
          <Table
            rowKey="id"
            dataSource={cashierReport.cortes}
            columns={[
              { title: 'CORTE', dataIndex: 'id', render: (value) => `#${value}` },
              { title: 'APERTURA', dataIndex: 'fecha_apertura', render: (value) => new Date(value).toLocaleString('es-BO') },
              { title: 'CIERRE', dataIndex: 'fecha_cierre', render: (value) => (value ? new Date(value).toLocaleString('es-BO') : 'PENDIENTE') },
              { title: 'ESTADO', dataIndex: 'estado', render: (value) => <Typography.Text>{cutStateLabel(value)}</Typography.Text> },
              { title: 'INGRESOS', dataIndex: 'ingresos_total_bob', render: formatBs },
              { title: 'EGRESOS', dataIndex: 'egresos_total_bob', render: formatBs },
              { title: 'RESULTADO', dataIndex: 'resultado_bob', render: formatBs },
            ]}
          />
        </>
      ) : (
        <Alert type="info" showIcon message="SELECCIONA UN CAJERO PARA VER SU REPORTE COMPARATIVO." />
      ),
    },
  ]

  const cajaItems = [
    {
      key: 'mi-periodo',
      label: 'Mi período',
      children: myPeriod ? (
        <>
          <Row gutter={[14, 14]} style={{ marginBottom: 16 }}>
            <Col xs={24} md={8}><EconomySummaryCard eyebrow="INGRESOS" title="Período activo" value={formatBs(myPeriod.ingresos_total_bob)} accent="#4b7f5a" /></Col>
            <Col xs={24} md={8}><EconomySummaryCard eyebrow="EGRESOS" title="Período activo" value={formatBs(myPeriod.egresos_total_bob)} accent="#b86c45" /></Col>
            <Col xs={24} md={8}><EconomySummaryCard eyebrow="RESULTADO" title="Período activo" value={formatBs(myPeriod.resultado_bob)} accent="#4d2219" /></Col>
          </Row>
          <Table
            rowKey="id"
            dataSource={myPeriod.egresos}
            columns={[
              { title: 'FECHA', dataIndex: 'fecha', render: (value) => new Date(value).toLocaleString('es-BO') },
              { title: 'TIPO', dataIndex: 'tipo', render: expenseTypeLabel },
              { title: 'CONCEPTO', dataIndex: 'concepto' },
              { title: 'MONTO', dataIndex: 'monto', render: formatBs },
            ]}
          />
        </>
      ) : null,
    },
    {
      key: 'mi-estado',
      label: 'Mi estado de resultados',
      children: myIncomeStatement ? (
        <Row gutter={[14, 14]}>
          <Col xs={24} md={8}><EconomySummaryCard eyebrow="INGRESOS" title="Visible solo con corte activo" value={formatBs(myIncomeStatement.ingresos_total_bob)} accent="#4b7f5a" /></Col>
          <Col xs={24} md={8}><EconomySummaryCard eyebrow="EGRESOS" title="Visible solo con corte activo" value={formatBs(myIncomeStatement.egresos_total_bob)} accent="#b86c45" /></Col>
          <Col xs={24} md={8}><EconomySummaryCard eyebrow="RESULTADO" title="Visible solo con corte activo" value={formatBs(myIncomeStatement.resultado_bob)} accent="#4d2219" /></Col>
        </Row>
      ) : null,
    },
    {
      key: 'mi-historial',
      label: 'Mi historial',
      children: myHistory ? (
        <Table
          rowKey="id"
          dataSource={myHistory.cuts}
          columns={[
            { title: 'CORTE', dataIndex: 'id', render: (value) => `#${value}` },
            { title: 'APERTURA', dataIndex: 'fecha_apertura', render: (value) => new Date(value).toLocaleString('es-BO') },
            { title: 'CIERRE', dataIndex: 'fecha_cierre', render: (value) => (value ? new Date(value).toLocaleString('es-BO') : 'PENDIENTE') },
            { title: 'ESTADO', dataIndex: 'estado', render: (value) => <Tag color={cutStateColor(value)}>{cutStateLabel(value)}</Tag> },
            { title: 'INGRESOS', dataIndex: 'ingresos_display' },
            { title: 'VENTAS', dataIndex: 'ventas_display' },
            { title: 'PAGOS', dataIndex: 'pagos_display' },
            { title: 'FLETES', dataIndex: 'fletes_display' },
            { title: 'RESULTADO', dataIndex: 'resultado_display' },
            { title: 'EGRESOS', dataIndex: 'egresos_total_bob', render: formatBs },
          ]}
        />
      ) : null,
    },
  ]

  return (
    <div>
      <div className="page-header">
        <div>
          <Typography.Title level={2} style={{ margin: 0 }}>
            Reportes Económicos
          </Typography.Title>
          <Typography.Paragraph type="secondary" style={{ marginBottom: 0 }}>
            {isAdmin
              ? 'Analiza ingresos, egresos, flujo y desempeño por cajero con enfoque financiero en BOB.'
              : 'Consulta tu período activo y tu historial enmascarado de cortes cerrados.'}
          </Typography.Paragraph>
        </div>
      </div>

      {error ? <Alert type="error" showIcon message={error} style={{ marginBottom: 16 }} /> : null}

      {isAdmin ? (
        <div className="glass-panel boutique-filter-bar" style={{ marginBottom: 16 }}>
          <Row gutter={[12, 12]}>
            <Col xs={24} md={8}>
              <RangePicker
                format="DD/MM/YYYY"
                style={{ width: '100%' }}
                onChange={(values) =>
                  syncStoredFilters({
                    ...filters,
                    date_from: values?.[0] ? values[0].format('YYYY-MM-DD') : undefined,
                    date_to: values?.[1] ? values[1].format('YYYY-MM-DD') : undefined,
                  })
                }
              />
            </Col>
            <Col xs={24} md={8}>
              <Select
                allowClear
                showSearch
                optionFilterProp="label"
                placeholder="FILTRAR POR CAJERO"
                options={cashierOptions}
                value={filters.cashier_id}
                onChange={(value) => syncStoredFilters({ ...filters, cashier_id: value })}
                style={{ width: '100%' }}
              />
            </Col>
            <Col xs={24} md={8} style={{ display: 'flex', justifyContent: 'flex-end', gap: 8 }}>
              <Button icon={<FilterOutlined />} onClick={loadReports}>Actualizar</Button>
              <Button icon={<DownloadOutlined />} onClick={() => exportAdmin('/economia/reportes/estado-resultados')}>Exportar estado</Button>
              <Button icon={<DownloadOutlined />} onClick={() => exportAdmin('/economia/reportes/flujo-efectivo')}>Exportar flujo</Button>
            </Col>
          </Row>
        </div>
      ) : (
        <Row justify="end" style={{ marginBottom: 16 }}>
          <Button icon={<DownloadOutlined />} onClick={() => downloadEconomyCsv('/economia/reportes/mi-historial')}>
            Exportar mi historial
          </Button>
        </Row>
      )}

      <Tabs
        destroyOnHidden
        items={isAdmin ? adminItems : cajaItems}
      />

      {loading ? <Alert type="info" showIcon message="ACTUALIZANDO REPORTES..." style={{ marginTop: 16 }} /> : null}
    </div>
  )
}
