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
import { REPORT_PERIOD_OPTIONS, applyDateRangeToFilters, buildReportQuery, formatCount, getSessionFilters, parseDateRange, setSessionFilters } from '../../components/reports/reportUtils'
import { useAutoPrint } from '../../components/reports/useAutoPrint'

const { RangePicker } = DatePicker
const STORAGE_KEY = 'reportes-fletes-v1'
const DEFAULT_FILTERS = { period: 'all', date_from: undefined, date_to: undefined }
const PIE_COLORS = ['#8f3d2e', '#4f6d63', '#d6a56f', '#7f9c94', '#6b4b3e', '#cf9a7f']

export function FleteReportsPage() {
  return <FleteReportsView printMode={false} />
}

export function FleteReportsPrintPage() {
  return <FleteReportsView printMode />
}

function FleteReportsView({ printMode }) {
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
      const response = await apiClient.get('/fletes/reportes/panel', { params: activeFilters })
      setReport(response.data)
      if (!printMode) setSessionFilters(STORAGE_KEY, activeFilters)
    } catch (requestError) {
      setError(requestError.response?.data?.detail || 'NO FUE POSIBLE CARGAR LOS REPORTES DE FLETES.')
    } finally {
      setLoading(false)
    }
  }, [filters, printMode])

  useEffect(() => {
    loadReport(filters)
  }, [filters, loadReport])

  useAutoPrint(printMode, !loading && Boolean(report))

  const kpiMap = useMemo(() => Object.fromEntries((report?.kpis || []).map((item) => [item.key, item])), [report])
  const stateBreakdown = report?.table_rows?.state_breakdown || []
  const outputStateBreakdown = report?.table_rows?.output_state_breakdown || []
  const topFletes = report?.table_rows?.top_fletes_by_outputs || []
  const criticalReturns = report?.table_rows?.critical_returns || []
  const outputsSeries = report?.series?.outputs_by_period || []

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
        <Col xs={24} md={12} xl={4}><ReportKpiCard title="VESTIDOS" value={formatCount(kpiMap.FLETES_TOTAL?.value)} accent="#8f3d2e" /></Col>
        <Col xs={24} md={12} xl={4}><ReportKpiCard title="DISPONIBLES" value={formatCount(kpiMap.FLETES_AVAILABLE?.value)} accent="#4f6d63" /></Col>
        <Col xs={24} md={12} xl={4}><ReportKpiCard title="EN FLETE" value={formatCount(kpiMap.FLETES_IN_USE?.value)} accent="#d6a56f" /></Col>
        <Col xs={24} md={12} xl={4}><ReportKpiCard title="SALIDAS PERÍODO" value={formatCount(kpiMap.OUTPUTS_PERIOD?.value)} accent="#7f9c94" /></Col>
        <Col xs={24} md={12} xl={4}><ReportKpiCard title="ANULADAS" value={formatCount(kpiMap.OUTPUTS_ANNULLED?.value)} accent="#6b4b3e" /></Col>
        <Col xs={24} md={12} xl={4}><ReportKpiCard title="DEV. VENCIDAS" value={formatCount(kpiMap.RETURNS_OVERDUE?.value)} accent="#b64f3f" /></Col>
      </Row>

      <Row gutter={[16, 16]} style={{ marginBottom: 16 }}>
        <Col xs={24} xl={10}>
          <ReportChartCard title="ESTADO DE VESTIDOS EN FLETE" description="Disponibilidad general del módulo" empty={!stateBreakdown.length}>
            <div style={{ width: '100%', minWidth: 0, height: 320 }}>
              <ResponsiveContainer width="100%" height="100%" minWidth={0} minHeight={320}>
                <PieChart>
                  <Pie data={stateBreakdown} dataKey="value" nameKey="label" outerRadius={110} label={({ label, value }) => `${label}: ${value}`}>
                    {stateBreakdown.map((entry, index) => <Cell key={entry.label} fill={PIE_COLORS[index % PIE_COLORS.length]} />)}
                  </Pie>
                  <Tooltip formatter={(value) => formatCount(value)} />
                </PieChart>
              </ResponsiveContainer>
            </div>
          </ReportChartCard>
        </Col>
        <Col xs={24} xl={14}>
          <ReportChartCard title="SALIDAS POR PERÍODO" description="Carga operativa del circuito de flete" empty={!outputsSeries.length}>
            <div style={{ width: '100%', minWidth: 0, height: 320 }}>
              <ResponsiveContainer width="100%" height="100%" minWidth={0} minHeight={320}>
                <BarChart data={outputsSeries}>
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
          <Card className="glass-panel report-chart-card" styles={{ body: { padding: 20 } }} title="VESTIDOS CON MÁS SALIDAS">
            <Table
              rowKey="label"
              size="small"
              pagination={false}
              dataSource={topFletes}
              columns={[
                { title: 'VESTIDO', dataIndex: 'label' },
                { title: 'SALIDAS', dataIndex: 'value', render: formatCount },
                { title: 'ESTADO', dataIndex: 'state' },
              ]}
            />
          </Card>
        </Col>
        <Col xs={24} xl={12}>
          <Card className="glass-panel report-chart-card" styles={{ body: { padding: 20 } }} title="ESTADO DE SALIDAS">
            <Table
              rowKey="label"
              size="small"
              pagination={false}
              dataSource={outputStateBreakdown}
              columns={[
                { title: 'ESTADO', dataIndex: 'label' },
                { title: 'CANTIDAD', dataIndex: 'value', render: formatCount },
              ]}
            />
          </Card>
        </Col>
      </Row>

      <Card className="glass-panel report-chart-card" styles={{ body: { padding: 20 } }} title="DEVOLUCIONES CRÍTICAS" style={{ marginTop: 16 }}>
        <Table
          rowKey="id"
          size="small"
          pagination={{ pageSize: 8 }}
          dataSource={criticalReturns}
          columns={[
            { title: 'VESTIDO', dataIndex: 'item' },
            { title: 'CLIENTA', dataIndex: 'client_name' },
            { title: 'FECHA PREVISTA', dataIndex: 'fecha_devolucion_prevista' },
            { title: 'ESTADO', dataIndex: 'estado_salida' },
            { title: 'CRITICIDAD', dataIndex: 'criticidad' },
          ]}
        />
      </Card>
    </>
  )

  const printableContent = (
    <>
      <ReportPrintSection title="RESUMEN EJECUTIVO" subtitle="ESTADO GENERAL DEL CIRCUITO DE FLETES">
        <Row gutter={[12, 12]}>
          <Col span={8}><ReportKpiCard title="VESTIDOS" value={formatCount(kpiMap.FLETES_TOTAL?.value)} accent="#8f3d2e" /></Col>
          <Col span={8}><ReportKpiCard title="DISPONIBLES" value={formatCount(kpiMap.FLETES_AVAILABLE?.value)} accent="#4f6d63" /></Col>
          <Col span={8}><ReportKpiCard title="EN FLETE" value={formatCount(kpiMap.FLETES_IN_USE?.value)} accent="#d6a56f" /></Col>
          <Col span={8}><ReportKpiCard title="SALIDAS PERÍODO" value={formatCount(kpiMap.OUTPUTS_PERIOD?.value)} accent="#7f9c94" /></Col>
          <Col span={8}><ReportKpiCard title="ANULADAS" value={formatCount(kpiMap.OUTPUTS_ANNULLED?.value)} accent="#6b4b3e" /></Col>
          <Col span={8}><ReportKpiCard title="DEV. VENCIDAS" value={formatCount(kpiMap.RETURNS_OVERDUE?.value)} accent="#b64f3f" /></Col>
        </Row>
      </ReportPrintSection>

      <ReportPrintSection title="ESTADOS Y SALIDAS" subtitle="DISTRIBUCIÓN DE VESTIDOS Y MOVIMIENTO DEL PERÍODO">
        <ReportPrintStatList items={stateBreakdown.map((item, index) => ({ ...item, color: PIE_COLORS[index % PIE_COLORS.length] }))} valueFormatter={formatCount} />
        <div style={{ marginTop: 16 }}>
          <ReportPrintTable
            rows={outputsSeries}
            columns={[
              { title: 'PERÍODO', dataIndex: 'label' },
              { title: 'SALIDAS', dataIndex: 'value', render: formatCount },
            ]}
          />
        </div>
      </ReportPrintSection>

      <ReportPrintSection title="ROTACIÓN Y ESTADOS DE SALIDA" subtitle="TOP DE USO Y DISTRIBUCIÓN OPERATIVA">
        <ReportPrintTable
          rows={topFletes}
          columns={[
            { title: 'VESTIDO', dataIndex: 'label' },
            { title: 'SALIDAS', dataIndex: 'value', render: formatCount },
            { title: 'ESTADO', dataIndex: 'state' },
          ]}
        />
        <div style={{ marginTop: 16 }}>
          <ReportPrintTable
            rows={outputStateBreakdown}
            columns={[
              { title: 'ESTADO', dataIndex: 'label' },
              { title: 'CANTIDAD', dataIndex: 'value', render: formatCount },
            ]}
          />
        </div>
      </ReportPrintSection>

      <ReportPrintSection title="DEVOLUCIONES CRÍTICAS" subtitle="CONTROL DE CASOS PRIORITARIOS">
        <ReportPrintTable
          rows={criticalReturns}
          columns={[
            { title: 'VESTIDO', dataIndex: 'item' },
            { title: 'CLIENTA', dataIndex: 'client_name' },
            { title: 'FECHA PREVISTA', dataIndex: 'fecha_devolucion_prevista' },
            { title: 'ESTADO', dataIndex: 'estado_salida' },
            { title: 'CRITICIDAD', dataIndex: 'criticidad' },
          ]}
        />
      </ReportPrintSection>
    </>
  )

  if (printMode) {
    return (
      <ReportPrintableLayout
        title="REPORTE DE FLETES"
        subtitle="ESTADOS, SALIDAS, DEVOLUCIONES Y VESTIDOS CON MAYOR ROTACIÓN"
        filtersLabel={describeFilters(filters)}
        onBack={() => navigate('/app/fletes/reportes')}
        onPrint={() => window.print()}
      >
        {printableContent}
      </ReportPrintableLayout>
    )
  }

  return (
    <div>
      <ReportPageHeader
        title="Reportes de Fletes"
        description="Monitorea disponibilidad, salidas, vencimientos de devolución y vestidos con mayor uso."
        onPrint={() => navigate(`/app/fletes/reportes/imprimir?${buildReportQuery(filters)}`)}
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
