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
import { REPORT_PERIOD_OPTIONS, applyDateRangeToFilters, buildReportQuery, formatBs, formatCount, getSessionFilters, parseDateRange, setSessionFilters } from '../../components/reports/reportUtils'
import { useAutoPrint } from '../../components/reports/useAutoPrint'

const { RangePicker } = DatePicker
const STORAGE_KEY = 'reportes-boutique-v1'
const DEFAULT_FILTERS = { period: 'all', date_from: undefined, date_to: undefined }
const PIE_COLORS = ['#8f3d2e', '#d6a56f', '#4f6d63', '#7f9c94', '#6b4b3e', '#cf9a7f']

export function BoutiqueReportsPage() {
  return <BoutiqueReportsView printMode={false} />
}

export function BoutiqueReportsPrintPage() {
  return <BoutiqueReportsView printMode />
}

function BoutiqueReportsView({ printMode }) {
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
      const response = await apiClient.get('/boutique/reportes/panel', { params: activeFilters })
      setReport(response.data)
      if (!printMode) setSessionFilters(STORAGE_KEY, activeFilters)
    } catch (requestError) {
      setError(requestError.response?.data?.detail || 'NO FUE POSIBLE CARGAR LOS REPORTES DE BOUTIQUE.')
    } finally {
      setLoading(false)
    }
  }, [filters, printMode])

  useEffect(() => {
    loadReport(filters)
  }, [filters, loadReport])

  useAutoPrint(printMode, !loading && Boolean(report))

  const kpiMap = useMemo(() => Object.fromEntries((report?.kpis || []).map((item) => [item.key, item])), [report])
  const categoryBreakdown = report?.table_rows?.category_breakdown || []
  const soldItems = report?.rankings?.sold_items || []
  const soldTypes = report?.rankings?.sold_types || []
  const cheapestRows = report?.table_rows?.cheapest_provider_by_item || []
  const paymentByCurrency = report?.table_rows?.payment_methods_by_currency || []
  const salesSeries = report?.series?.sales_by_period || []

  const content = (
    <>
      {error ? <Alert type="error" showIcon message={error} style={{ marginBottom: 16 }} /> : null}
      {!printMode ? (
        <Card className="glass-panel boutique-filter-bar" styles={{ body: { padding: 18 } }}>
          <Row gutter={[12, 12]}>
            <Col xs={24} md={8}>
              <Typography.Text strong>PERÍODO</Typography.Text>
              <select value={filters.period} onChange={(event) => setFilters((current) => ({ ...current, period: event.target.value }))} style={nativeSelectStyle}>
                {REPORT_PERIOD_OPTIONS.map((option) => <option key={option.value} value={option.value}>{option.label}</option>)}
              </select>
            </Col>
            <Col xs={24} md={10}>
              <Typography.Text strong>RANGO LIBRE</Typography.Text>
              <RangePicker format="DD/MM/YYYY" style={{ width: '100%' }} value={parseDateRange(filters)} onChange={(values) => setFilters((current) => applyDateRangeToFilters(current, values))} />
            </Col>
            <Col xs={24} md={6} style={{ display: 'flex', alignItems: 'end' }}>
              <Button icon={<ReloadOutlined />} onClick={() => loadReport(filters)} style={{ width: '100%' }}>ACTUALIZAR</Button>
            </Col>
          </Row>
        </Card>
      ) : null}

      <Row gutter={[12, 12]} style={{ marginBottom: 18 }}>
        <Col xs={24} md={12} xl={4}><ReportKpiCard title="PRODUCTOS" value={formatCount(kpiMap.BOUTIQUE_ITEMS?.value)} accent="#8f3d2e" /></Col>
        <Col xs={24} md={12} xl={4}><ReportKpiCard title="CATEGORÍAS" value={formatCount(kpiMap.BOUTIQUE_TYPES?.value)} accent="#4f6d63" /></Col>
        <Col xs={24} md={12} xl={4}><ReportKpiCard title="PROVEEDORES" value={formatCount(kpiMap.BOUTIQUE_PROVIDERS?.value)} accent="#6b4b3e" /></Col>
        <Col xs={24} md={12} xl={4}><ReportKpiCard title="VENTAS PERÍODO" value={formatCount(kpiMap.BOUTIQUE_SALES_COUNT?.value)} accent="#d6a56f" /></Col>
        <Col xs={24} md={12} xl={4}><ReportKpiCard title="INGRESO VENTAS" value={formatBs(kpiMap.BOUTIQUE_SALES_TOTAL?.value)} accent="#b55d43" /></Col>
        <Col xs={24} md={12} xl={4}><ReportKpiCard title="ENTRADAS PERÍODO" value={formatCount(kpiMap.BOUTIQUE_ENTRIES_COUNT?.value)} accent="#7f9c94" /></Col>
      </Row>

      <Row gutter={[16, 16]} style={{ marginBottom: 16 }}>
        <Col xs={24} xl={10}>
          <ReportChartCard title="CATEGORÍAS BOUTIQUE" description="Participación de productos por tipo" empty={!categoryBreakdown.length}>
            <div style={{ width: '100%', minWidth: 0, height: 320 }}>
              <ResponsiveContainer width="100%" height="100%" minWidth={0} minHeight={320}>
                <PieChart>
                  <Pie data={categoryBreakdown} dataKey="value" nameKey="label" outerRadius={110} label={({ label, value }) => `${label}: ${value}`}>
                    {categoryBreakdown.map((entry, index) => <Cell key={entry.label} fill={PIE_COLORS[index % PIE_COLORS.length]} />)}
                  </Pie>
                  <Tooltip formatter={(value) => formatCount(value)} />
                  <Legend />
                </PieChart>
              </ResponsiveContainer>
            </div>
          </ReportChartCard>
        </Col>
        <Col xs={24} xl={14}>
          <ReportChartCard title="VENTAS POR PERÍODO" description="Ingreso agregado de ventas" empty={!salesSeries.length}>
            <div style={{ width: '100%', minWidth: 0, height: 320 }}>
              <ResponsiveContainer width="100%" height="100%" minWidth={0} minHeight={320}>
                <BarChart data={salesSeries}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#eadbd2" />
                  <XAxis dataKey="label" stroke="#7c6a61" />
                  <YAxis stroke="#7c6a61" />
                  <Tooltip formatter={(value) => formatBs(value)} />
                  <Bar dataKey="value" fill="#8f3d2e" radius={[10, 10, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </ReportChartCard>
        </Col>
      </Row>

      <Row gutter={[16, 16]}>
        <Col xs={24} xl={12}>
          <Card className="glass-panel report-chart-card" styles={{ body: { padding: 20 } }} title="PRODUCTOS MÁS VENDIDOS">
            <Table
              rowKey="label"
              size="small"
              pagination={false}
              dataSource={soldItems}
              columns={[
                { title: 'PRODUCTO', dataIndex: 'label' },
                { title: 'CANTIDAD', dataIndex: 'quantity', render: formatCount },
                { title: 'TOTAL BS', dataIndex: 'total_bob', render: formatBs },
              ]}
            />
          </Card>
        </Col>
        <Col xs={24} xl={12}>
          <Card className="glass-panel report-chart-card" styles={{ body: { padding: 20 } }} title="TIPOS DE PRODUCTO MÁS VENDIDOS">
            <Table
              rowKey="label"
              size="small"
              pagination={false}
              dataSource={soldTypes}
              columns={[
                { title: 'TIPO', dataIndex: 'label' },
                { title: 'CANTIDAD', dataIndex: 'quantity', render: formatCount },
                { title: 'TOTAL BS', dataIndex: 'total_bob', render: formatBs },
              ]}
            />
          </Card>
        </Col>
      </Row>

      <Row gutter={[16, 16]} style={{ marginTop: 16 }}>
        <Col xs={24} xl={12}>
          <Card className="glass-panel report-chart-card" styles={{ body: { padding: 20 } }} title="PROVEEDOR MÁS BARATO POR PRODUCTO">
            <Table
              rowKey={(row) => `${row.item}-${row.provider}`}
              size="small"
              pagination={{ pageSize: 8 }}
              dataSource={cheapestRows}
              columns={[
                { title: 'PRODUCTO', dataIndex: 'item' },
                { title: 'PROVEEDOR', dataIndex: 'provider' },
                { title: 'COSTO MÍNIMO', dataIndex: 'min_cost', render: formatBs },
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
              dataSource={paymentByCurrency}
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
      <ReportPrintSection title="RESUMEN EJECUTIVO" subtitle="INDICADORES PRINCIPALES DE BOUTIQUE">
        <Row gutter={[12, 12]}>
          <Col span={8}><ReportKpiCard title="PRODUCTOS" value={formatCount(kpiMap.BOUTIQUE_ITEMS?.value)} accent="#8f3d2e" /></Col>
          <Col span={8}><ReportKpiCard title="CATEGORÍAS" value={formatCount(kpiMap.BOUTIQUE_TYPES?.value)} accent="#4f6d63" /></Col>
          <Col span={8}><ReportKpiCard title="PROVEEDORES" value={formatCount(kpiMap.BOUTIQUE_PROVIDERS?.value)} accent="#6b4b3e" /></Col>
          <Col span={8}><ReportKpiCard title="VENTAS PERÍODO" value={formatCount(kpiMap.BOUTIQUE_SALES_COUNT?.value)} accent="#d6a56f" /></Col>
          <Col span={8}><ReportKpiCard title="INGRESO VENTAS" value={formatBs(kpiMap.BOUTIQUE_SALES_TOTAL?.value)} accent="#b55d43" /></Col>
          <Col span={8}><ReportKpiCard title="ENTRADAS PERÍODO" value={formatCount(kpiMap.BOUTIQUE_ENTRIES_COUNT?.value)} accent="#7f9c94" /></Col>
        </Row>
      </ReportPrintSection>

      <ReportPrintSection title="CATEGORÍAS Y VENTAS" subtitle="DISTRIBUCIÓN POR TIPO Y SERIE DE VENTAS">
        <ReportPrintStatList items={categoryBreakdown.map((item, index) => ({ ...item, color: PIE_COLORS[index % PIE_COLORS.length] }))} valueFormatter={formatCount} />
        <div style={{ marginTop: 16 }}>
          <ReportPrintTable
            rows={salesSeries}
            columns={[
              { title: 'PERÍODO', dataIndex: 'label' },
              { title: 'TOTAL BS', dataIndex: 'value', render: formatBs },
            ]}
          />
        </div>
      </ReportPrintSection>

      <ReportPrintSection title="RANKINGS COMERCIALES" subtitle="PRODUCTOS Y TIPOS MÁS VENDIDOS">
        <ReportPrintTable
          rows={soldItems}
          columns={[
            { title: 'PRODUCTO', dataIndex: 'label' },
            { title: 'CANTIDAD', dataIndex: 'quantity', render: formatCount },
            { title: 'TOTAL BS', dataIndex: 'total_bob', render: formatBs },
          ]}
        />
        <div style={{ marginTop: 16 }}>
          <ReportPrintTable
            rows={soldTypes}
            columns={[
              { title: 'TIPO', dataIndex: 'label' },
              { title: 'CANTIDAD', dataIndex: 'quantity', render: formatCount },
              { title: 'TOTAL BS', dataIndex: 'total_bob', render: formatBs },
            ]}
          />
        </div>
      </ReportPrintSection>

      <ReportPrintSection title="COSTOS Y COBROS" subtitle="REFERENCIAS POR PROVEEDOR Y MÉTODO DE PAGO">
        <ReportPrintTable
          rows={cheapestRows}
          columns={[
            { title: 'PRODUCTO', dataIndex: 'item' },
            { title: 'PROVEEDOR', dataIndex: 'provider' },
            { title: 'COSTO MÍNIMO', dataIndex: 'min_cost', render: formatBs },
          ]}
        />
        <div style={{ marginTop: 16 }}>
          <ReportPrintTable
            rows={paymentByCurrency}
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
        title="REPORTE DE BOUTIQUE"
        subtitle="VENTAS, CATEGORÍAS, ENTRADAS Y COSTOS POR PROVEEDOR"
        filtersLabel={describeFilters(filters)}
        onBack={() => navigate('/app/boutique/reportes')}
        onPrint={() => window.print()}
      >
        {printableContent}
      </ReportPrintableLayout>
    )
  }

  return (
    <div>
      <ReportPageHeader
        title="Reportes de Boutique"
        description="Consolida ventas, comportamiento de productos, entradas y referencias de costo por proveedor."
        onPrint={() => navigate(`/app/boutique/reportes/imprimir?${buildReportQuery(filters)}`)}
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
