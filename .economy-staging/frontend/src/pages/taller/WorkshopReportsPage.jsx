/* eslint-disable react/prop-types */
import { ReloadOutlined } from '@ant-design/icons'
import { Alert, Button, Card, Col, DatePicker, Row, Table, Typography } from 'antd'
import { useCallback, useEffect, useMemo, useState } from 'react'
import { Bar, BarChart, CartesianGrid, Cell, Pie, PieChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
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
const STORAGE_KEY = 'reportes-taller-v1'
const DEFAULT_FILTERS = { period: 'all', date_from: undefined, date_to: undefined }
const PIE_COLORS = ['#8f3d2e', '#4f6d63', '#d6a56f', '#7f9c94', '#6b4b3e', '#cf9a7f']

export function WorkshopReportsPage() {
  return <WorkshopReportsView printMode={false} />
}

export function WorkshopReportsPrintPage() {
  return <WorkshopReportsView printMode />
}

function WorkshopReportsView({ printMode }) {
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
      const response = await apiClient.get('/taller/reportes/panel', { params: activeFilters })
      setReport(response.data)
      if (!printMode) setSessionFilters(STORAGE_KEY, activeFilters)
    } catch (requestError) {
      setError(requestError.response?.data?.detail || 'NO FUE POSIBLE CARGAR LOS REPORTES DEL TALLER.')
    } finally {
      setLoading(false)
    }
  }, [filters, printMode])

  useEffect(() => {
    loadReport(filters)
  }, [filters, loadReport])

  useAutoPrint(printMode, !loading && Boolean(report))

  const kpiMap = useMemo(() => Object.fromEntries((report?.kpis || []).map((item) => [item.key, item])), [report])
  const typeBreakdown = report?.table_rows?.type_breakdown || []
  const topOutputs = report?.rankings?.top_outputs || []
  const topEntries = report?.rankings?.top_entries || []
  const destinations = report?.table_rows?.destinations || []
  const cheapestByItem = report?.table_rows?.cheapest_by_item || []
  const entriesByPeriod = report?.series?.entries_by_period || []
  const outputsByPeriod = report?.series?.outputs_by_period || []

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
        <Col xs={24} md={12} xl={4}><ReportKpiCard title="MATERIALES" value={formatCount(kpiMap.WORKSHOP_ITEMS?.value)} accent="#8f3d2e" /></Col>
        <Col xs={24} md={12} xl={4}><ReportKpiCard title="TIPOS" value={formatCount(kpiMap.WORKSHOP_TYPES?.value)} accent="#4f6d63" /></Col>
        <Col xs={24} md={12} xl={4}><ReportKpiCard title="STOCK BAJO" value={formatCount(kpiMap.WORKSHOP_LOW_STOCK?.value)} accent="#b64f3f" /></Col>
        <Col xs={24} md={12} xl={4}><ReportKpiCard title="ENTRADAS" value={formatCount(kpiMap.WORKSHOP_ENTRIES?.value)} accent="#d6a56f" /></Col>
        <Col xs={24} md={12} xl={4}><ReportKpiCard title="SALIDAS" value={formatCount(kpiMap.WORKSHOP_OUTPUTS?.value)} accent="#7f9c94" /></Col>
      </Row>

      <Row gutter={[16, 16]} style={{ marginBottom: 16 }}>
        <Col xs={24} xl={10}>
          <ReportChartCard title="TIPOS DE INVENTARIO TALLER" description="Distribución de materiales por categoría" empty={!typeBreakdown.length}>
            <div style={{ width: '100%', minWidth: 0, height: 320 }}>
              <ResponsiveContainer width="100%" height="100%" minWidth={0} minHeight={320}>
                <PieChart>
                  <Pie data={typeBreakdown} dataKey="value" nameKey="label" outerRadius={110} label={({ label, value }) => `${label}: ${value}`}>
                    {typeBreakdown.map((entry, index) => <Cell key={entry.label} fill={PIE_COLORS[index % PIE_COLORS.length]} />)}
                  </Pie>
                  <Tooltip formatter={(value) => formatCount(value)} />
                </PieChart>
              </ResponsiveContainer>
            </div>
          </ReportChartCard>
        </Col>
        <Col xs={24} xl={14}>
          <ReportChartCard title="MOVIMIENTOS POR PERÍODO" description="Entradas y salidas del taller" empty={!entriesByPeriod.length && !outputsByPeriod.length}>
            <div style={{ width: '100%', minWidth: 0, height: 320 }}>
              <ResponsiveContainer width="100%" height="100%" minWidth={0} minHeight={320}>
                <BarChart data={mergeSeries(entriesByPeriod, outputsByPeriod)}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#eadbd2" />
                  <XAxis dataKey="label" stroke="#7c6a61" />
                  <YAxis stroke="#7c6a61" />
                  <Tooltip formatter={(value) => formatCount(value)} />
                  <Bar dataKey="entradas" fill="#4f6d63" radius={[8, 8, 0, 0]} />
                  <Bar dataKey="salidas" fill="#8f3d2e" radius={[8, 8, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </ReportChartCard>
        </Col>
      </Row>

      <Row gutter={[16, 16]}>
        <Col xs={24} xl={12}>
          <Card className="glass-panel report-chart-card" styles={{ body: { padding: 20 } }} title="MATERIALES CON MÁS SALIDAS">
            <Table rowKey="label" size="small" pagination={false} dataSource={topOutputs} columns={[{ title: 'MATERIAL', dataIndex: 'label' }, { title: 'CANTIDAD', dataIndex: 'value', render: formatCount }]} />
          </Card>
        </Col>
        <Col xs={24} xl={12}>
          <Card className="glass-panel report-chart-card" styles={{ body: { padding: 20 } }} title="MATERIALES CON MÁS ENTRADAS">
            <Table rowKey="label" size="small" pagination={false} dataSource={topEntries} columns={[{ title: 'MATERIAL', dataIndex: 'label' }, { title: 'CANTIDAD', dataIndex: 'value', render: formatCount }]} />
          </Card>
        </Col>
      </Row>

      <Row gutter={[16, 16]} style={{ marginTop: 16 }}>
        <Col xs={24} xl={12}>
          <Card className="glass-panel report-chart-card" styles={{ body: { padding: 20 } }} title="SALIDAS POR DESTINO">
            <Table rowKey="label" size="small" pagination={{ pageSize: 8 }} dataSource={destinations} columns={[{ title: 'DESTINO', dataIndex: 'label' }, { title: 'CANTIDAD', dataIndex: 'value', render: formatCount }]} />
          </Card>
        </Col>
        <Col xs={24} xl={12}>
          <Card className="glass-panel report-chart-card" styles={{ body: { padding: 20 } }} title="REFERENCIA MÁS BARATA POR MATERIAL">
            <Table rowKey={(row) => `${row.item}-${row.provider}`} size="small" pagination={{ pageSize: 8 }} dataSource={cheapestByItem} columns={[{ title: 'MATERIAL', dataIndex: 'item' }, { title: 'PROVEEDOR', dataIndex: 'provider' }, { title: 'COSTO', dataIndex: 'unit_cost', render: formatBs }]} />
          </Card>
        </Col>
      </Row>
    </>
  )

  const printableContent = (
    <>
      <ReportPrintSection title="RESUMEN EJECUTIVO" subtitle="ESTADO GENERAL DEL TALLER">
        <Row gutter={[12, 12]}>
          <Col span={8}><ReportKpiCard title="MATERIALES" value={formatCount(kpiMap.WORKSHOP_ITEMS?.value)} accent="#8f3d2e" /></Col>
          <Col span={8}><ReportKpiCard title="TIPOS" value={formatCount(kpiMap.WORKSHOP_TYPES?.value)} accent="#4f6d63" /></Col>
          <Col span={8}><ReportKpiCard title="STOCK BAJO" value={formatCount(kpiMap.WORKSHOP_LOW_STOCK?.value)} accent="#b64f3f" /></Col>
          <Col span={12}><ReportKpiCard title="ENTRADAS" value={formatCount(kpiMap.WORKSHOP_ENTRIES?.value)} accent="#d6a56f" /></Col>
          <Col span={12}><ReportKpiCard title="SALIDAS" value={formatCount(kpiMap.WORKSHOP_OUTPUTS?.value)} accent="#7f9c94" /></Col>
        </Row>
      </ReportPrintSection>

      <ReportPrintSection title="TIPOS Y MOVIMIENTOS" subtitle="DISTRIBUCIÓN DE INVENTARIO Y FLUJO DEL PERÍODO">
        <ReportPrintStatList items={typeBreakdown.map((item, index) => ({ ...item, color: PIE_COLORS[index % PIE_COLORS.length] }))} valueFormatter={formatCount} />
        <div style={{ marginTop: 16 }}>
          <ReportPrintTable
            rows={mergeSeries(entriesByPeriod, outputsByPeriod)}
            columns={[
              { title: 'PERÍODO', dataIndex: 'label' },
              { title: 'ENTRADAS', dataIndex: 'entradas', render: formatCount },
              { title: 'SALIDAS', dataIndex: 'salidas', render: formatCount },
            ]}
          />
        </div>
      </ReportPrintSection>

      <ReportPrintSection title="RANKINGS Y DESTINOS" subtitle="MATERIALES MÁS MOVILIZADOS Y DESTINO DE SALIDA">
        <ReportPrintTable
          rows={topOutputs}
          columns={[
            { title: 'MATERIAL', dataIndex: 'label' },
            { title: 'SALIDAS', dataIndex: 'value', render: formatCount },
          ]}
        />
        <div style={{ marginTop: 16 }}>
          <ReportPrintTable
            rows={topEntries}
            columns={[
              { title: 'MATERIAL', dataIndex: 'label' },
              { title: 'ENTRADAS', dataIndex: 'value', render: formatCount },
            ]}
          />
        </div>
        <div style={{ marginTop: 16 }}>
          <ReportPrintTable
            rows={destinations}
            columns={[
              { title: 'DESTINO', dataIndex: 'label' },
              { title: 'CANTIDAD', dataIndex: 'value', render: formatCount },
            ]}
          />
        </div>
      </ReportPrintSection>

      <ReportPrintSection title="REFERENCIAS DE COSTO" subtitle="PROVEEDOR MÁS ECONÓMICO POR MATERIAL">
        <ReportPrintTable
          rows={cheapestByItem}
          columns={[
            { title: 'MATERIAL', dataIndex: 'item' },
            { title: 'PROVEEDOR', dataIndex: 'provider' },
            { title: 'COSTO', dataIndex: 'unit_cost', render: formatBs },
          ]}
        />
      </ReportPrintSection>
    </>
  )

  if (printMode) {
    return (
      <ReportPrintableLayout
        title="REPORTE DE TALLER"
        subtitle="INVENTARIO, MOVIMIENTOS, DESTINOS Y REFERENCIAS DE COSTO"
        filtersLabel={describeFilters(filters)}
        onBack={() => navigate('/app/taller/reportes')}
        onPrint={() => window.print()}
      >
        {printableContent}
      </ReportPrintableLayout>
    )
  }

  return (
    <div>
      <ReportPageHeader
        title="Reportes de Taller"
        description="Analiza inventario, entradas, salidas, destinos y referencias de costo del taller."
        onPrint={() => navigate(`/app/taller/reportes/imprimir?${buildReportQuery(filters)}`)}
      />
      {content}
    </div>
  )
}

function mergeSeries(entriesSeries, outputsSeries) {
  const map = new Map()
  entriesSeries.forEach((item) => {
    map.set(item.label, { label: item.label, entradas: item.value, salidas: 0 })
  })
  outputsSeries.forEach((item) => {
    const current = map.get(item.label) || { label: item.label, entradas: 0, salidas: 0 }
    current.salidas = item.value
    map.set(item.label, current)
  })
  return [...map.values()].sort((a, b) => a.label.localeCompare(b.label))
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
