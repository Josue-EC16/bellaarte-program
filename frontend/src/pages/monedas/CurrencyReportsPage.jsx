/* eslint-disable react/prop-types */
import { ReloadOutlined } from '@ant-design/icons'
import { Alert, Button, Card, Col, DatePicker, Row, Select, Table, Typography } from 'antd'
import { useCallback, useEffect, useMemo, useState } from 'react'
import { Bar, BarChart, CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { useNavigate, useSearchParams } from 'react-router-dom'

import { apiClient } from '../../api/client'
import { ReportChartCard } from '../../components/reports/ReportChartCard'
import { ReportKpiCard } from '../../components/reports/ReportKpiCard'
import { ReportPageHeader } from '../../components/reports/ReportPageHeader'
import { ReportPrintSection } from '../../components/reports/ReportPrintSection'
import { ReportPrintStatList } from '../../components/reports/ReportPrintStatList'
import { ReportPrintTable } from '../../components/reports/ReportPrintTable'
import { ReportPrintableLayout } from '../../components/reports/ReportPrintableLayout'
import { REPORT_PERIOD_OPTIONS, applyDateRangeToFilters, buildReportQuery, formatBs, formatCount, getSessionFilters, parseDateRange, setSessionFilters } from '../../components/reports/reportUtils'
import { useAutoPrint } from '../../components/reports/useAutoPrint'

const { RangePicker } = DatePicker
const STORAGE_KEY = 'reportes-monedas-v1'
const DEFAULT_FILTERS = { period: 'all', date_from: undefined, date_to: undefined, currency_id: undefined }

export function CurrencyReportsPage() {
  return <CurrencyReportsView printMode={false} />
}

export function CurrencyReportsPrintPage() {
  return <CurrencyReportsView printMode />
}

function CurrencyReportsView({ printMode }) {
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const initialFilters = useMemo(() => {
    const queryFilters = {
      period: searchParams.get('period') || undefined,
      date_from: searchParams.get('date_from') || undefined,
      date_to: searchParams.get('date_to') || undefined,
      currency_id: searchParams.get('currency_id') || undefined,
    }
    if (printMode) return { ...DEFAULT_FILTERS, ...queryFilters }
    return getSessionFilters(STORAGE_KEY, { ...DEFAULT_FILTERS, ...queryFilters })
  }, [printMode, searchParams])
  const [filters, setFilters] = useState(initialFilters)
  const [report, setReport] = useState(null)
  const [currencies, setCurrencies] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  const loadReport = useCallback(async (activeFilters = filters) => {
    setLoading(true)
    setError(null)
    try {
      const [currenciesResponse, reportResponse] = await Promise.all([
        apiClient.get('/monedas'),
        apiClient.get('/monedas/reportes/panel', { params: activeFilters }),
      ])
      setCurrencies(currenciesResponse.data)
      setReport(reportResponse.data)
      if (!printMode) setSessionFilters(STORAGE_KEY, activeFilters)
    } catch (requestError) {
      setError(requestError.response?.data?.detail || 'NO FUE POSIBLE CARGAR LOS REPORTES DE MONEDAS.')
    } finally {
      setLoading(false)
    }
  }, [filters, printMode])

  useEffect(() => {
    loadReport(filters)
  }, [filters, loadReport])

  useAutoPrint(printMode, !loading && Boolean(report))

  const currencyOptions = useMemo(() => currencies.map((item) => ({ label: `${item.codigo} - ${item.nombre}`, value: item.id })), [currencies])
  const kpiMap = useMemo(() => Object.fromEntries((report?.kpis || []).map((item) => [item.key, item])), [report])
  const latestRates = report?.table_rows?.latest_rates || []
  const usageRows = report?.table_rows?.commercial_usage || []
  const methodsRows = report?.table_rows?.methods_by_currency || []
  const rateSeries = report?.series?.exchange_rate_series || []

  const content = (
    <>
      {error ? <Alert type="error" showIcon message={error} style={{ marginBottom: 16 }} /> : null}
      {!printMode ? (
        <Card className="glass-panel boutique-filter-bar" styles={{ body: { padding: 18 } }}>
          <Row gutter={[12, 12]}>
            <Col xs={24} md={6}>
              <Typography.Text strong>PERÍODO</Typography.Text>
              <select value={filters.period} onChange={(event) => setFilters((current) => ({ ...current, period: event.target.value }))} style={nativeSelectStyle}>
                {REPORT_PERIOD_OPTIONS.map((option) => <option key={option.value} value={option.value}>{option.label}</option>)}
              </select>
            </Col>
            <Col xs={24} md={8}>
              <Typography.Text strong>RANGO LIBRE</Typography.Text>
              <RangePicker format="DD/MM/YYYY" style={{ width: '100%' }} value={parseDateRange(filters)} onChange={(values) => setFilters((current) => applyDateRangeToFilters(current, values))} />
            </Col>
            <Col xs={24} md={6}>
              <Typography.Text strong>MONEDA</Typography.Text>
              <Select allowClear placeholder="MONEDA PARA SERIE" options={currencyOptions} value={filters.currency_id} onChange={(value) => setFilters((current) => ({ ...current, currency_id: value }))} style={{ width: '100%', marginTop: 6 }} />
            </Col>
            <Col xs={24} md={4} style={{ display: 'flex', alignItems: 'end' }}>
              <Button icon={<ReloadOutlined />} onClick={() => loadReport(filters)} style={{ width: '100%' }}>ACTUALIZAR</Button>
            </Col>
          </Row>
        </Card>
      ) : null}

      <Row gutter={[12, 12]} style={{ marginBottom: 18 }}>
        <Col xs={24} md={12} xl={3}><ReportKpiCard title="MONEDAS" value={formatCount(kpiMap.CURRENCIES_TOTAL?.value)} accent="#8f3d2e" /></Col>
        <Col xs={24} md={12} xl={4}><ReportKpiCard title="ACTIVAS" value={formatCount(kpiMap.CURRENCIES_ACTIVE?.value)} accent="#4f6d63" /></Col>
        <Col xs={24} md={12} xl={5}><ReportKpiCard title="MONEDA BASE" value={kpiMap.CURRENCIES_BASE?.value || 'SIN BASE'} accent="#d6a56f" /></Col>
        <Col xs={24} md={12} xl={4}><ReportKpiCard title="TIPOS DE CAMBIO" value={formatCount(kpiMap.RATES_PERIOD?.value)} accent="#7f9c94" /></Col>
      </Row>

      <Row gutter={[16, 16]} style={{ marginBottom: 16 }}>
        <Col xs={24} xl={14}>
          <ReportChartCard title="EVOLUCIÓN DEL TIPO DE CAMBIO" description="Serie según la moneda seleccionada" empty={!rateSeries.length}>
            <div style={{ width: '100%', minWidth: 0, height: 320 }}>
              <ResponsiveContainer width="100%" height="100%" minWidth={0} minHeight={320}>
                <LineChart data={rateSeries}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#eadbd2" />
                  <XAxis dataKey="label" stroke="#7c6a61" />
                  <YAxis stroke="#7c6a61" />
                  <Tooltip formatter={(value) => Number(value || 0).toFixed(4)} />
                  <Line type="monotone" dataKey="value" stroke="#8f3d2e" strokeWidth={3} />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </ReportChartCard>
        </Col>
        <Col xs={24} xl={10}>
          <ReportChartCard title="USO COMERCIAL POR MONEDA" description="Ventas, pagos y fletes agregados en BOB" empty={!usageRows.length}>
            <div style={{ width: '100%', minWidth: 0, height: 320 }}>
              <ResponsiveContainer width="100%" height="100%" minWidth={0} minHeight={320}>
                <BarChart data={usageRows}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#eadbd2" />
                  <XAxis dataKey="label" stroke="#7c6a61" />
                  <YAxis stroke="#7c6a61" />
                  <Tooltip formatter={(value) => formatBs(value)} />
                  <Bar dataKey="value" fill="#4f6d63" radius={[10, 10, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </ReportChartCard>
        </Col>
      </Row>

      <Row gutter={[16, 16]}>
        <Col xs={24} xl={12}>
          <Card className="glass-panel report-chart-card" styles={{ body: { padding: 20 } }} title="ÚLTIMAS COTIZACIONES">
            <Table
              rowKey="currency"
              size="small"
              pagination={false}
              dataSource={latestRates}
              columns={[
                { title: 'MONEDA', dataIndex: 'currency' },
                { title: 'NOMBRE', dataIndex: 'name' },
                { title: 'VALOR EN BOB', dataIndex: 'value_bob', render: (value) => Number(value || 0).toFixed(4) },
                { title: 'ACTIVO', dataIndex: 'active', render: (value) => value ? 'SÍ' : 'NO' },
              ]}
            />
          </Card>
        </Col>
        <Col xs={24} xl={12}>
          <Card className="glass-panel report-chart-card" styles={{ body: { padding: 20 } }} title="MÉTODOS DE PAGO POR MONEDA">
            <Table
              rowKey={(row) => `${row.currency}-${row.method}`}
              size="small"
              pagination={{ pageSize: 8 }}
              dataSource={methodsRows}
              columns={[
                { title: 'MONEDA', dataIndex: 'currency' },
                { title: 'MÉTODO', dataIndex: 'method' },
                { title: 'TOTAL BS', dataIndex: 'total_bob', render: formatBs },
              ]}
            />
          </Card>
        </Col>
      </Row>
    </>
  )

  const printableContent = (
    <>
      <ReportPrintSection title="RESUMEN EJECUTIVO" subtitle="ESTADO ACTUAL DEL SISTEMA MONETARIO">
        <Row gutter={[12, 12]}>
          <Col span={6}><ReportKpiCard title="MONEDAS" value={formatCount(kpiMap.CURRENCIES_TOTAL?.value)} accent="#8f3d2e" /></Col>
          <Col span={6}><ReportKpiCard title="ACTIVAS" value={formatCount(kpiMap.CURRENCIES_ACTIVE?.value)} accent="#4f6d63" /></Col>
          <Col span={6}><ReportKpiCard title="MONEDA BASE" value={kpiMap.CURRENCIES_BASE?.value || 'SIN BASE'} accent="#d6a56f" /></Col>
          <Col span={6}><ReportKpiCard title="TIPOS DE CAMBIO" value={formatCount(kpiMap.RATES_PERIOD?.value)} accent="#7f9c94" /></Col>
        </Row>
      </ReportPrintSection>

      <ReportPrintSection title="USO Y EVOLUCIÓN" subtitle="USO COMERCIAL Y SERIE DEL TIPO DE CAMBIO">
        <ReportPrintStatList items={usageRows.map((item, index) => ({ ...item, color: index % 2 === 0 ? '#4f6d63' : '#8f3d2e' }))} valueFormatter={formatBs} />
        <div style={{ marginTop: 16 }}>
          <ReportPrintTable
            rows={rateSeries}
            columns={[
              { title: 'PERÍODO', dataIndex: 'label' },
              { title: 'VALOR', dataIndex: 'value', render: (value) => Number(value || 0).toFixed(4) },
            ]}
          />
        </div>
      </ReportPrintSection>

      <ReportPrintSection title="COTIZACIONES Y MÉTODOS" subtitle="REFERENCIAS VIGENTES Y COBRO POR MONEDA">
        <ReportPrintTable
          rows={latestRates}
          columns={[
            { title: 'MONEDA', dataIndex: 'currency' },
            { title: 'NOMBRE', dataIndex: 'name' },
            { title: 'VALOR EN BOB', dataIndex: 'value_bob', render: (value) => Number(value || 0).toFixed(4) },
            { title: 'ACTIVO', dataIndex: 'active', render: (value) => (value ? 'SÍ' : 'NO') },
          ]}
        />
        <div style={{ marginTop: 16 }}>
          <ReportPrintTable
            rows={methodsRows}
            columns={[
              { title: 'MONEDA', dataIndex: 'currency' },
              { title: 'MÉTODO', dataIndex: 'method' },
              { title: 'TOTAL BS', dataIndex: 'total_bob', render: formatBs },
            ]}
          />
        </div>
      </ReportPrintSection>
    </>
  )

  if (printMode) {
    return (
      <ReportPrintableLayout
        title="REPORTE DE MONEDAS"
        subtitle="MONEDAS ACTIVAS, COTIZACIONES Y USO COMERCIAL"
        filtersLabel={describeFilters(filters)}
        onBack={() => navigate('/app/monedas/reportes')}
        onPrint={() => window.print()}
      >
        {printableContent}
      </ReportPrintableLayout>
    )
  }

  return (
    <div>
      <ReportPageHeader
        title="Reportes de Monedas"
        description="Revisa la evolución del tipo de cambio y el uso comercial de cada moneda del sistema."
        onPrint={() => navigate(`/app/monedas/reportes/imprimir?${buildReportQuery(filters)}`)}
      />
      {content}
    </div>
  )
}

function describeFilters(filters) {
  const parts = []
  if (filters.period && filters.period !== 'all') parts.push(`PERÍODO: ${filters.period.toUpperCase()}`)
  if (filters.date_from) parts.push(`DESDE: ${filters.date_from}`)
  if (filters.date_to) parts.push(`HASTA: ${filters.date_to}`)
  if (filters.currency_id) parts.push(`MONEDA ID: ${filters.currency_id}`)
  return parts.length ? parts.join(' | ') : 'TODO EL HISTORIAL'
}

const nativeSelectStyle = {
  width: '100%',
  height: 40,
  borderRadius: 10,
  border: '1px solid #d9d9d9',
  marginTop: 6,
  padding: '0 12px',
  background: '#fff',
}
