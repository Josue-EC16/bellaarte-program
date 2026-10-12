/* eslint-disable react/prop-types */
import { ReloadOutlined } from '@ant-design/icons'
import { Alert, Button, Card, Col, DatePicker, Row, Table, Typography } from 'antd'
import { useCallback, useEffect, useMemo, useState } from 'react'
import { Bar, BarChart, CartesianGrid, Cell, Legend, Pie, PieChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { useNavigate, useSearchParams } from 'react-router-dom'

import { apiClient } from '../../api/client'
import { ReportChartCard } from '../../components/reports/ReportChartCard'
import { ReportKpiCard } from '../../components/reports/ReportKpiCard'
import { ReportPageHeader } from '../../components/reports/ReportPageHeader'
import { ReportPrintSection } from '../../components/reports/ReportPrintSection'
import { ReportPrintStatList } from '../../components/reports/ReportPrintStatList'
import { ReportPrintTable } from '../../components/reports/ReportPrintTable'
import { ReportPrintableLayout } from '../../components/reports/ReportPrintableLayout'
import { REPORT_PERIOD_OPTIONS, applyDateRangeToFilters, buildReportQuery, formatCount, getSessionFilters, parseDateRange, setSessionFilters } from '../../components/reports/reportUtils'
import { useAutoPrint } from '../../components/reports/useAutoPrint'

const { RangePicker } = DatePicker

const STORAGE_KEY = 'reportes-clientes-v1'
const DEFAULT_FILTERS = { period: 'all', date_from: undefined, date_to: undefined }
const PIE_COLORS = ['#8f3d2e', '#d6a56f', '#4f6d63', '#b36a5e', '#6b4b3e', '#d7c1a5']

export function ClientReportsPage() {
  return <ClientReportsView printMode={false} />
}

export function ClientReportsPrintPage() {
  return <ClientReportsView printMode />
}

function ClientReportsView({ printMode }) {
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const initialFilters = useMemo(() => {
    const queryFilters = {
      period: searchParams.get('period') || undefined,
      date_from: searchParams.get('date_from') || undefined,
      date_to: searchParams.get('date_to') || undefined,
    }
    if (printMode) return { ...DEFAULT_FILTERS, ...queryFilters }
    return getSessionFilters(STORAGE_KEY, { ...DEFAULT_FILTERS, ...queryFilters })
  }, [printMode, searchParams])
  const [filters, setFilters] = useState(initialFilters)
  const [report, setReport] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  const loadReport = useCallback(async (activeFilters = filters) => {
    setLoading(true)
    setError(null)
    try {
      const response = await apiClient.get('/clientes/reportes/panel', { params: activeFilters })
      setReport(response.data)
      if (!printMode) {
        setSessionFilters(STORAGE_KEY, activeFilters)
      }
    } catch (requestError) {
      setError(requestError.response?.data?.detail || 'NO FUE POSIBLE CARGAR LOS REPORTES DE CLIENTES.')
    } finally {
      setLoading(false)
    }
  }, [filters, printMode])

  useEffect(() => {
    loadReport(filters)
  }, [filters, loadReport])

  useAutoPrint(printMode, !loading && Boolean(report))

  const kpiMap = useMemo(() => Object.fromEntries((report?.kpis || []).map((item) => [item.key, item])), [report])
  const chartCountry = report?.table_rows?.by_country || []
  const chartCity = report?.table_rows?.by_city || []
  const topClients = report?.table_rows?.top_active_orders || []
  const registrationSeries = report?.series?.registrations || []

  const content = (
    <>
      {error ? <Alert type="error" showIcon message={error} style={{ marginBottom: 16 }} /> : null}
      {!printMode ? (
        <Card className="glass-panel boutique-filter-bar" styles={{ body: { padding: 18 } }}>
          <Row gutter={[12, 12]}>
            <Col xs={24} md={8}>
              <Typography.Text strong>PERÍODO</Typography.Text>
              <select
                value={filters.period}
                onChange={(event) => setFilters((current) => ({ ...current, period: event.target.value }))}
                style={nativeSelectStyle}
              >
                {REPORT_PERIOD_OPTIONS.map((option) => (
                  <option key={option.value} value={option.value}>{option.label}</option>
                ))}
              </select>
            </Col>
            <Col xs={24} md={10}>
              <Typography.Text strong>RANGO LIBRE</Typography.Text>
              <RangePicker
                format="DD/MM/YYYY"
                style={{ width: '100%' }}
                value={parseDateRange(filters)}
                onChange={(values) => setFilters((current) => applyDateRangeToFilters(current, values))}
              />
            </Col>
            <Col xs={24} md={6} style={{ display: 'flex', alignItems: 'end' }}>
              <Button icon={<ReloadOutlined />} onClick={() => loadReport(filters)} style={{ width: '100%' }}>
                ACTUALIZAR
              </Button>
            </Col>
          </Row>
        </Card>
      ) : null}

      <Row gutter={[12, 12]} style={{ marginBottom: 18 }}>
        <Col xs={24} md={12} xl={6}><ReportKpiCard title="CLIENTES TOTALES" value={formatCount(kpiMap.CLIENTS_TOTAL?.value)} accent="#8f3d2e" /></Col>
        <Col xs={24} md={12} xl={6}><ReportKpiCard title="ACTIVOS" value={formatCount(kpiMap.CLIENTS_ACTIVE?.value)} accent="#4f6d63" /></Col>
        <Col xs={24} md={12} xl={6}><ReportKpiCard title="INACTIVOS" value={formatCount(kpiMap.CLIENTS_INACTIVE?.value)} accent="#8b786a" /></Col>
        <Col xs={24} md={12} xl={6}><ReportKpiCard title="REGISTRADOS EN PERÍODO" value={formatCount(kpiMap.CLIENTS_PERIOD?.value)} accent="#d6a56f" /></Col>
      </Row>

      <Row gutter={[16, 16]} style={{ marginBottom: 16 }}>
        <Col xs={24} xl={10}>
          <ReportChartCard title="CLIENTES POR PAÍS" description="Distribución geográfica principal" empty={!chartCountry.length}>
            <div style={{ width: '100%', minWidth: 0, height: 320 }}>
              <ResponsiveContainer width="100%" height="100%" minWidth={0} minHeight={320}>
                <PieChart>
                  <Pie data={chartCountry} dataKey="value" nameKey="label" outerRadius={110} label={({ label, value }) => `${label}: ${value}`}>
                    {chartCountry.map((entry, index) => <Cell key={entry.label} fill={PIE_COLORS[index % PIE_COLORS.length]} />)}
                  </Pie>
                  <Tooltip formatter={(value) => formatCount(value)} />
                  <Legend />
                </PieChart>
              </ResponsiveContainer>
            </div>
          </ReportChartCard>
        </Col>
        <Col xs={24} xl={14}>
          <ReportChartCard title="REGISTROS DE CLIENTES" description="Serie temporal del período consultado" empty={!registrationSeries.length}>
            <div style={{ width: '100%', minWidth: 0, height: 320 }}>
              <ResponsiveContainer width="100%" height="100%" minWidth={0} minHeight={320}>
                <BarChart data={registrationSeries}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#eadbd2" />
                  <XAxis dataKey="label" stroke="#7c6a61" />
                  <YAxis stroke="#7c6a61" />
                  <Tooltip formatter={(value) => formatCount(value)} />
                  <Bar dataKey="value" fill="#8f3d2e" radius={[10, 10, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </ReportChartCard>
        </Col>
      </Row>

      <Row gutter={[16, 16]}>
        <Col xs={24} xl={12}>
          <ReportChartCard title="CLIENTES POR CIUDAD" description="Top de ciudades registradas" empty={!chartCity.length}>
            <div style={{ width: '100%', minWidth: 0, height: 320 }}>
              <ResponsiveContainer width="100%" height="100%" minWidth={0} minHeight={320}>
                <BarChart data={chartCity.slice(0, 10)} layout="vertical" margin={{ left: 22 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#eadbd2" />
                  <XAxis type="number" stroke="#7c6a61" />
                  <YAxis dataKey="label" type="category" stroke="#7c6a61" width={120} />
                  <Tooltip formatter={(value) => formatCount(value)} />
                  <Bar dataKey="value" fill="#4f6d63" radius={[0, 10, 10, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </ReportChartCard>
        </Col>
        <Col xs={24} xl={12}>
          <Card className="glass-panel report-chart-card" styles={{ body: { padding: 20 } }} title="CLIENTES CON MÁS PEDIDOS ACTIVOS">
            <Table
              rowKey="client_id"
              size="small"
              pagination={false}
              dataSource={topClients}
              columns={[
                { title: 'CLIENTE', dataIndex: 'full_name' },
                { title: 'CÓDIGO', dataIndex: 'codigo' },
                { title: 'PAÍS', dataIndex: 'pais', render: (value) => value || 'SIN DATO' },
                { title: 'PEDIDOS ACTIVOS', dataIndex: 'active_orders', render: formatCount },
              ]}
              locale={{ emptyText: 'SIN DATOS' }}
            />
          </Card>
        </Col>
      </Row>
    </>
  )

  const printableContent = (
    <>
      <ReportPrintSection title="RESUMEN EJECUTIVO" subtitle="KPIS PRINCIPALES DEL MÓDULO">
        <Row gutter={[12, 12]}>
          <Col span={12}><ReportKpiCard title="CLIENTES TOTALES" value={formatCount(kpiMap.CLIENTS_TOTAL?.value)} accent="#8f3d2e" /></Col>
          <Col span={12}><ReportKpiCard title="ACTIVOS" value={formatCount(kpiMap.CLIENTS_ACTIVE?.value)} accent="#4f6d63" /></Col>
          <Col span={12}><ReportKpiCard title="INACTIVOS" value={formatCount(kpiMap.CLIENTS_INACTIVE?.value)} accent="#8b786a" /></Col>
          <Col span={12}><ReportKpiCard title="REGISTRADOS EN PERÍODO" value={formatCount(kpiMap.CLIENTS_PERIOD?.value)} accent="#d6a56f" /></Col>
        </Row>
      </ReportPrintSection>

      <ReportPrintSection title="DISTRIBUCIÓN GEOGRÁFICA" subtitle="PAÍSES Y CIUDADES CON MAYOR REGISTRO">
        <ReportPrintStatList items={chartCountry.map((item, index) => ({ ...item, color: PIE_COLORS[index % PIE_COLORS.length] }))} valueFormatter={formatCount} />
        <div style={{ marginTop: 16 }}>
          <ReportPrintTable
            rows={chartCity.slice(0, 12)}
            columns={[
              { title: 'CIUDAD', dataIndex: 'label' },
              { title: 'CANTIDAD', dataIndex: 'value', render: formatCount },
            ]}
          />
        </div>
      </ReportPrintSection>

      <ReportPrintSection title="REGISTROS Y CLIENTES ACTIVOS" subtitle="SERIE RESUMIDA Y TOP OPERATIVO">
        <ReportPrintTable
          rows={registrationSeries}
          columns={[
            { title: 'PERÍODO', dataIndex: 'label' },
            { title: 'REGISTROS', dataIndex: 'value', render: formatCount },
          ]}
        />
        <div style={{ marginTop: 16 }}>
          <ReportPrintTable
            rows={topClients}
            columns={[
              { title: 'CLIENTE', dataIndex: 'full_name' },
              { title: 'CÓDIGO', dataIndex: 'codigo' },
              { title: 'PAÍS', dataIndex: 'pais', render: (value) => value || 'SIN DATO' },
              { title: 'PEDIDOS ACTIVOS', dataIndex: 'active_orders', render: formatCount },
            ]}
          />
        </div>
      </ReportPrintSection>
    </>
  )

  if (printMode) {
    return (
      <ReportPrintableLayout
        title="REPORTE DE CLIENTES"
        subtitle="DISTRIBUCIÓN, REGISTROS Y CLIENTES CON MÁS PEDIDOS ACTIVOS"
        filtersLabel={describeFilters(filters)}
        onBack={() => navigate('/app/clientes/reportes')}
        onPrint={() => window.print()}
      >
        {printableContent}
      </ReportPrintableLayout>
    )
  }

  return (
    <div>
      <ReportPageHeader
        title="Reportes de Clientes"
        description="Visualiza distribución geográfica, evolución de registros y clientas con mayor carga operativa."
        onPrint={() => navigate(`/app/clientes/reportes/imprimir?${buildReportQuery(filters)}`)}
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
