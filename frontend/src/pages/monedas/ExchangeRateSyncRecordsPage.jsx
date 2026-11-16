import { Alert, Button, Col, Descriptions, Drawer, Input, Row, Select, Space, Table, Tag, Typography } from 'antd'
import { useCallback, useEffect, useRef, useState } from 'react'
import { Navigate, useSearchParams } from 'react-router-dom'

import { apiClient } from '../../api/client'
import { useAuth } from '../../auth/AuthProvider'
import { ExchangeRateSyncStatus } from './ExchangeRateSyncStatus'
import { bolivianTimestamp, calendarDate, canReadSyncRecords, SYNC_BASE, SYNC_STATES, validRecordId } from './exchangeRateSyncUtils'
import { exchangeRateActionError } from './exchangeRateUtils'
import { useExchangeRateSyncStatus } from './useExchangeRateSyncStatus'

const EMPTY = { date_from: '', date_to: '', execution_from: '', execution_to: '', estado: undefined, proveedor: undefined }
const PROVIDERS = ['FACTURA_BO_BCB', 'BCB_CARGA_INICIAL']

export function ExchangeRateSyncRecordsPage() {
  const { user } = useAuth()
  return canReadSyncRecords(user) ? <RecordsContent canView={user.permissions.includes('exchange_rates_sync:view')} /> : <Navigate to="/403" replace />
}

/* eslint-disable react/prop-types */
function RecordsContent({ canView }) {
  const [params, setParams] = useSearchParams()
  const [filters, setFilters] = useState(EMPTY)
  const [page, setPage] = useState(1)
  const [pageSize, setPageSize] = useState(25)
  const [result, setResult] = useState({ items: [], total: 0 })
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [detail, setDetail] = useState(null)
  const [detailError, setDetailError] = useState(null)
  const [detailLoading, setDetailLoading] = useState(false)
  const [reloadKey, setReloadKey] = useState(0)
  const listRequest = useRef(0)
  const status = useExchangeRateSyncStatus()
  const reloadStatus = status.reload
  const recordText = params.get('record_id')
  const recordId = validRecordId(recordText)

  const reload = useCallback(() => { setReloadKey((key) => key + 1); reloadStatus() }, [reloadStatus])

  useEffect(() => {
    const controller = new AbortController()
    const requestId = ++listRequest.current
    setResult({ items: [], total: 0 })
    setError(null)
    if ((filters.date_from && filters.date_to && filters.date_from > filters.date_to) ||
      (filters.execution_from && filters.execution_to && filters.execution_from > filters.execution_to)) {
      setError('La fecha desde no puede ser posterior a la fecha hasta.')
      setLoading(false)
      return () => controller.abort()
    }
    setLoading(true)
    const query = Object.fromEntries(Object.entries(filters).filter(([, value]) => Boolean(value)))
    apiClient.get(`${SYNC_BASE}/registros`, { params: { ...query, page, page_size: pageSize }, signal: controller.signal })
      .then(({ data }) => { if (!controller.signal.aborted && requestId === listRequest.current) setResult(data) })
      .catch((requestError) => { if (!controller.signal.aborted && requestId === listRequest.current) setError(exchangeRateActionError(requestError, 'No fue posible cargar los registros de sincronización.')) })
      .finally(() => { if (!controller.signal.aborted && requestId === listRequest.current) setLoading(false) })
    return () => controller.abort()
  }, [filters, page, pageSize, reloadKey])

  useEffect(() => {
    setDetail(null)
    setDetailError(null)
    setDetailLoading(false)
    if (!recordText) return
    if (!recordId || !canView) {
      setDetailError(!canView ? 'No tienes permiso para consultar este detalle.' : 'El identificador del registro no es válido.')
      return
    }
    const controller = new AbortController()
    setDetailLoading(true)
    apiClient.get(`${SYNC_BASE}/registros/${recordId}`, { signal: controller.signal })
      .then(({ data }) => { if (!controller.signal.aborted) setDetail(data) })
      .catch((requestError) => { if (!controller.signal.aborted) setDetailError(exchangeRateActionError(requestError, 'No fue posible consultar el detalle del registro.')) })
      .finally(() => { if (!controller.signal.aborted) setDetailLoading(false) })
    return () => controller.abort()
  }, [recordId, recordText, canView, reloadKey])

  const setFilter = (key, value) => { setPage(1); setFilters((current) => ({ ...current, [key]: value })) }
  const closeDetail = () => setParams((current) => { const next = new URLSearchParams(current); next.delete('record_id'); return next }, { replace: true })
  const columns = [
    { title: 'Moneda', dataIndex: 'moneda_codigo' },
    { title: 'Fecha objetivo', dataIndex: 'fecha_objetivo', render: calendarDate },
    { title: 'Intento', dataIndex: 'numero_intento', render: (value) => value === 0 ? 'Carga histórica (0)' : value },
    { title: 'Ejecución · Bolivia', dataIndex: 'fecha_intento', render: bolivianTimestamp },
    { title: 'Estado', dataIndex: 'estado', render: (value) => <Tag color={value === 'EXITOSO' ? 'green' : value.startsWith('ERROR') ? 'orange' : 'default'}>{value.replaceAll('_', ' ')}</Tag> },
    { title: 'HTTP', dataIndex: 'codigo_http', render: (value) => value ?? '—' },
    { title: 'Proveedor', dataIndex: 'proveedor' },
    { title: 'Próxima ejecución · Bolivia', dataIndex: 'proximo_intento', render: bolivianTimestamp },
    { title: 'Valor Bs', dataIndex: 'valor_bob', render: (value) => value ?? '—' },
    ...(canView ? [{ title: 'Acción', key: 'action', render: (_, row) => <Button onClick={() => setParams({ record_id: String(row.id) })}>Ver detalle</Button> }] : []),
  ]
  const detailItems = detail ? [
    { key: 'currency', label: 'Moneda', children: detail.moneda_codigo },
    { key: 'target', label: 'Fecha objetivo', children: calendarDate(detail.fecha_objetivo) },
    { key: 'attempt', label: 'Número de intento', children: detail.numero_intento },
    { key: 'executed', label: 'Ejecución · Bolivia', children: bolivianTimestamp(detail.fecha_intento) },
    { key: 'state', label: 'Estado', children: detail.estado },
    { key: 'http', label: 'Código HTTP', children: detail.codigo_http ?? 'Sin respuesta HTTP registrada' },
    { key: 'provider', label: 'Proveedor', children: detail.proveedor },
    { key: 'next', label: 'Próxima ejecución · Bolivia', children: bolivianTimestamp(detail.proximo_intento) },
    { key: 'value', label: 'Cotización asociada', children: detail.tipo_cambio_id ? <a href={`/app/monedas/tipos-cambio?rate_id=${detail.tipo_cambio_id}`}>#{detail.tipo_cambio_id} · Bs {detail.valor_bob}</a> : 'Sin cotización asociada' },
  ] : []
  return <div>
    <div className="page-header"><div><Typography.Title level={2} style={{ margin: 0 }}>Registros de sincronización</Typography.Title><Typography.Paragraph type="secondary">USD / BOB · Consultas a factura.bo y carga histórica verificada. Solo lectura.</Typography.Paragraph></div><Space wrap><Button href="/app/monedas/tipos-cambio">Tipos de Cambio</Button><Button onClick={reload} loading={loading}>Actualizar registros</Button></Space></div>
    <ExchangeRateSyncStatus {...status} onReload={status.reload} />
    <div className="glass-panel boutique-filter-bar">
      <Row gutter={[12, 12]}>
        {[['date_from', 'Objetivo desde'], ['date_to', 'Objetivo hasta'], ['execution_from', 'Ejecución desde'], ['execution_to', 'Ejecución hasta']].map(([key, label]) => <Col xs={24} sm={12} lg={6} key={key}><label htmlFor={`tc-${key}`}>{label}</label><Input id={`tc-${key}`} type="date" value={filters[key]} onChange={(event) => setFilter(key, event.target.value)} /></Col>)}
        <Col xs={24} sm={12} lg={9}><label htmlFor="tc-state">Estado</label><Select id="tc-state" aria-label="Estado" allowClear value={filters.estado} options={SYNC_STATES.map((value) => ({ value, label: value.replaceAll('_', ' ') }))} onChange={(value) => setFilter('estado', value)} style={{ width: '100%' }} /></Col>
        <Col xs={24} sm={12} lg={9}><label htmlFor="tc-provider">Proveedor</label><Select id="tc-provider" aria-label="Proveedor" allowClear value={filters.proveedor} options={PROVIDERS.map((value) => ({ value, label: value }))} onChange={(value) => setFilter('proveedor', value)} style={{ width: '100%' }} /></Col>
        <Col xs={24} lg={6} style={{ display: 'flex', alignItems: 'end' }}><Button onClick={() => { setFilters(EMPTY); setPage(1) }}>Limpiar filtros</Button></Col>
      </Row>
    </div>
    {error ? <Alert type="error" showIcon message={error} action={<Button onClick={reload}>Reintentar</Button>} style={{ marginBottom: 12 }} /> : null}
    <Typography.Paragraph type="secondary">Los filtros de objetivo usan fecha oficial esperada; los de ejecución usan el calendario de Bolivia. Un intento fallido no modifica la cotización operativa.</Typography.Paragraph>
    <Table className="glass-panel" rowKey="id" dataSource={result.items} columns={columns} loading={loading} scroll={{ x: 1350 }} locale={{ emptyText: error ? 'No se pudieron obtener los registros.' : 'No existen registros para los filtros elegidos.' }} pagination={{ current: page, pageSize, total: result.total, showSizeChanger: true, pageSizeOptions: [10, 25, 50, 100], onChange: (nextPage, nextSize) => { setPage(nextSize !== pageSize ? 1 : nextPage); setPageSize(nextSize) } }} />
    <Drawer title="Detalle del registro de sincronización" width={640} open={Boolean(recordText)} onClose={closeDetail} maskClosable={false} destroyOnClose>
      {detailLoading ? <Typography.Paragraph>Cargando registro…</Typography.Paragraph> : null}
      {detailError ? <Alert type="error" showIcon message={detailError} /> : null}
      {detail ? <><Alert type={detail.estado.startsWith('ERROR') ? 'warning' : 'info'} showIcon message={detail.message} style={{ marginBottom: 20 }} /><Descriptions column={1} bordered items={detailItems} /></> : null}
    </Drawer>
  </div>
}
