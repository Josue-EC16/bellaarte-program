import { Alert, Col, Empty, Row, Table, Tag, Typography } from 'antd'
import { useCallback, useEffect, useState } from 'react'
import { Bar, BarChart, CartesianGrid, Cell, Line, LineChart, Pie, PieChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'

import { apiClient } from '../../api/client'
import { useAuth } from '../../auth/AuthProvider'
import { EconomyChartCard } from './EconomyChartCard'
import { ECONOMY_CHART_COLORS } from './economyConstants'
import { cutStateColor, cutStateLabel, expenseTypeLabel, formatBs, incomeSourceLabel } from './economyUtils'
import { EconomySummaryCard } from './EconomySummaryCard'

const PIE_COLORS = ['#4b7f5a', '#b86c45', '#7a9cc6', '#8f5aa8', '#d4933d']

export function EconomyDashboardPage() {
  const { user } = useAuth()
  const isAdmin = user?.role_code === 'ADMIN'
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [incomeStatement, setIncomeStatement] = useState(null)
  const [cashFlow, setCashFlow] = useState(null)
  const [cashCuts, setCashCuts] = useState([])
  const [myPeriod, setMyPeriod] = useState(null)
  const [myCut, setMyCut] = useState(null)

  const loadDashboard = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      if (isAdmin) {
        const [incomeResponse, flowResponse, cutsResponse] = await Promise.all([
          apiClient.get('/economia/reportes/estado-resultados'),
          apiClient.get('/economia/reportes/flujo-efectivo'),
          apiClient.get('/economia/cortes-caja', { params: { state: 'abierto' } }),
        ])
        setIncomeStatement(incomeResponse.data)
        setCashFlow(flowResponse.data)
        setCashCuts(cutsResponse.data)
        setMyPeriod(null)
        setMyCut(null)
      } else {
        const [periodResponse, myCutResponse] = await Promise.all([
          apiClient.get('/economia/reportes/mi-periodo'),
          apiClient.get('/economia/cortes-caja/me'),
        ])
        setMyPeriod(periodResponse.data)
        setMyCut(myCutResponse.data.cut)
        setIncomeStatement(null)
        setCashFlow(null)
        setCashCuts([])
      }
    } catch (requestError) {
      setError(requestError.response?.data?.detail || 'NO FUE POSIBLE CARGAR EL RESUMEN ECONÓMICO.')
    } finally {
      setLoading(false)
    }
  }, [isAdmin])

  useEffect(() => {
    loadDashboard()
  }, [loadDashboard])

  if (error) {
    return <Alert type="error" showIcon message={error} />
  }

  if (!isAdmin && myPeriod && !myPeriod.has_active_cut) {
    return (
      <div>
        <div className="page-header">
          <div>
            <Typography.Title level={2} style={{ margin: 0 }}>
              Economía
            </Typography.Title>
            <Typography.Paragraph type="secondary" style={{ marginBottom: 0 }}>
              Vista económica operativa para tu período de caja.
            </Typography.Paragraph>
          </div>
        </div>
        <Alert
          type="info"
          showIcon
          message="NO TIENES UN CORTE ACTIVO."
          description="CUANDO EL ADMIN ABRA TU CORTE DE CAJA, AQUÍ VERÁS TU RESUMEN OPERATIVO EN TIEMPO REAL."
        />
      </div>
    )
  }

  return (
    <div>
      <div className="page-header">
        <div>
          <Typography.Title level={2} style={{ margin: 0 }}>
            Economía
          </Typography.Title>
          <Typography.Paragraph type="secondary" style={{ marginBottom: 0 }}>
            {isAdmin
              ? 'Panorama financiero de ingresos, egresos y cortes de caja del sistema.'
              : 'Seguimiento en tiempo real de tu período activo de caja y tus egresos registrados.'}
          </Typography.Paragraph>
        </div>
      </div>

      {isAdmin ? (
        <>
          <Row gutter={[14, 14]} style={{ marginBottom: 16 }}>
            <Col xs={24} md={8}>
              <EconomySummaryCard eyebrow="INGRESOS" title="Ingresos brutos históricos" value={formatBs(incomeStatement?.ingresos_total_bob)} accent="#4b7f5a" />
            </Col>
            <Col xs={24} md={8}>
              <EconomySummaryCard eyebrow="EGRESOS" title="Salidas registradas" value={formatBs(incomeStatement?.egresos_total_bob)} accent="#b86c45" />
            </Col>
            <Col xs={24} md={8}>
              <EconomySummaryCard eyebrow="RESULTADO" title="Resultado neto" value={formatBs(incomeStatement?.resultado_bob)} accent="#4d2219" />
            </Col>
          </Row>

          <Row gutter={[16, 16]}>
            <Col xs={24} xl={14}>
              <EconomyChartCard title="Serie mensual" subtitle="Compara ingresos, egresos y resultado neto en BOB." empty={!incomeStatement?.serie_mensual?.length}>
                <div style={{ height: 320 }}>
                  <ResponsiveContainer width="100%" height="100%">
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
              <EconomyChartCard title="Ingresos por fuente" subtitle="Ventas, pagos y fletes se mantienen como ingresos históricos." empty={!incomeStatement?.ingresos_por_fuente?.length}>
                <div style={{ height: 320 }}>
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={(incomeStatement?.ingresos_por_fuente || []).map((item) => ({ ...item, label: incomeSourceLabel(item.label) }))}>
                      <CartesianGrid strokeDasharray="3 3" stroke="#eadbd2" />
                      <XAxis dataKey="label" stroke="#7c6a61" tick={{ fontSize: 11 }} />
                      <YAxis stroke="#7c6a61" />
                      <Tooltip formatter={(value) => formatBs(value)} />
                      <Bar dataKey="total_bob" radius={[10, 10, 0, 0]} fill={ECONOMY_CHART_COLORS.income} />
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              </EconomyChartCard>
            </Col>
            <Col xs={24} xl={10}>
              <EconomyChartCard title="Flujo por método de pago" subtitle="Distribución monetaria del ingreso cobrado." empty={!cashFlow?.entradas_por_metodo?.length}>
                <div style={{ height: 320 }}>
                  <ResponsiveContainer width="100%" height="100%">
                    <PieChart>
                      <Pie data={cashFlow?.entradas_por_metodo || []} dataKey="total_bob" nameKey="label" innerRadius={62} outerRadius={108} paddingAngle={3}>
                        {(cashFlow?.entradas_por_metodo || []).map((entry, index) => (
                          <Cell key={entry.label} fill={PIE_COLORS[index % PIE_COLORS.length]} />
                        ))}
                      </Pie>
                      <Tooltip formatter={(value) => formatBs(value)} />
                    </PieChart>
                  </ResponsiveContainer>
                </div>
              </EconomyChartCard>
            </Col>
            <Col xs={24} xl={14}>
              <EconomyChartCard title="Cortes de caja abiertos" subtitle="Seguimiento inmediato de los períodos que aún no se cerraron." empty={!cashCuts.length}>
                {cashCuts.length ? (
                  <Table
                    rowKey="id"
                    pagination={false}
                    dataSource={cashCuts}
                    columns={[
                      { title: 'CORTE', dataIndex: 'id', render: (value) => `#${value}` },
                      { title: 'CAJERO', key: 'cajero', render: (_, record) => record.cajero.full_name },
                      { title: 'APERTURA', dataIndex: 'fecha_apertura', render: (value) => new Date(value).toLocaleString('es-BO') },
                      { title: 'ESTADO', dataIndex: 'estado', render: (value) => <Tag color={cutStateColor(value)}>{cutStateLabel(value)}</Tag> },
                    ]}
                  />
                ) : (
                  <div style={{ minHeight: 220, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                    <Empty description="NO HAY CORTES ABIERTOS." />
                  </div>
                )}
              </EconomyChartCard>
            </Col>
          </Row>
        </>
      ) : (
        <>
          <Row gutter={[14, 14]} style={{ marginBottom: 16 }}>
            <Col xs={24} md={8}>
              <EconomySummaryCard eyebrow="MI CORTE" title="Período activo" value={myCut ? `#${myCut.id}` : 'SIN CORTE'} accent="#4d2219" helper={myCut ? cutStateLabel(myCut.estado) : 'NO DISPONIBLE'} />
            </Col>
            <Col xs={24} md={8}>
              <EconomySummaryCard eyebrow="INGRESOS DEL PERÍODO" title="Monto visible solo mientras el corte está activo" value={formatBs(myPeriod?.ingresos_total_bob)} accent="#4b7f5a" />
            </Col>
            <Col xs={24} md={8}>
              <EconomySummaryCard eyebrow="RESULTADO" title="FONDO + INGRESOS - EGRESOS" value={formatBs(myPeriod?.resultado_bob)} accent="#b86c45" />
            </Col>
          </Row>

          <Row gutter={[16, 16]}>
            <Col xs={24} xl={12}>
              <EconomyChartCard title="Ingresos por fuente" subtitle="Así se compone tu período actual." empty={!myPeriod?.ingresos_por_fuente?.length}>
                <div style={{ height: 300 }}>
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={(myPeriod?.ingresos_por_fuente || []).map((item) => ({ ...item, label: incomeSourceLabel(item.label) }))}>
                      <CartesianGrid strokeDasharray="3 3" stroke="#eadbd2" />
                      <XAxis dataKey="label" stroke="#7c6a61" />
                      <YAxis stroke="#7c6a61" />
                      <Tooltip formatter={(value) => formatBs(value)} />
                      <Bar dataKey="total_bob" fill={ECONOMY_CHART_COLORS.income} radius={[10, 10, 0, 0]} />
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              </EconomyChartCard>
            </Col>
            <Col xs={24} xl={12}>
              <EconomyChartCard title="Egresos por tipo" subtitle="Salidas activas registradas en tu corte actual." empty={!myPeriod?.egresos_por_tipo?.length}>
                <div style={{ height: 300 }}>
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={(myPeriod?.egresos_por_tipo || []).map((item) => ({ ...item, label: expenseTypeLabel(item.label.toLowerCase()) }))}>
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
      )}

      {loading ? <Alert style={{ marginTop: 16 }} type="info" showIcon message="ACTUALIZANDO RESUMEN ECONÓMICO..." /> : null}
    </div>
  )
}
