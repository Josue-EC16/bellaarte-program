import {
  DownloadOutlined,
  EyeOutlined,
  FileSearchOutlined,
  PrinterOutlined,
  ReloadOutlined,
  SearchOutlined,
} from '@ant-design/icons'
import {
  Alert,
  App as AntdApp,
  Button,
  Card,
  Col,
  Descriptions,
  Drawer,
  Input,
  Row,
  Select,
  Space,
  Table,
  Tag,
  Typography,
} from 'antd'
import { useCallback, useEffect, useMemo, useState } from 'react'

import { apiClient } from '../../api/client'
import {
  AUDIT_ACTION_OPTIONS,
  auditActionColor,
  auditActionLabel,
  auditActionSurface,
  downloadAuditCsv,
  formatAuditDate,
  openAuditPrintable,
} from './auditUtils'

const MODULE_OPTIONS = [
  'SEGURIDAD',
  'CLIENTES',
  'PROVEEDORES',
  'MONEDAS',
  'TIPO_CAMBIO',
  'INVENTARIO_BOUTIQUE',
  'VENTAS_BOUTIQUE',
  'FLETES',
  'INVENTARIO_TALLER',
  'PEDIDOS',
  'PAGOS_PEDIDO',
  'PRUEBAS_PEDIDO',
  'COMPROBANTES',
  'EGRESOS',
  'CORTE_CAJA',
  'NOTIFICACIONES',
  'SISTEMA',
].map((value) => ({ value, label: value }))

const QUICK_FILTERS = [
  { key: 'all', label: 'TODOS' },
  { key: 'security', label: 'SEGURIDAD' },
  { key: 'status', label: 'CAMBIOS DE ESTADO' },
  { key: 'annul', label: 'ANULACIONES' },
  { key: 'cancel', label: 'CANCELACIONES' },
]

function buildQuickFilteredRows(rows, quickFilter) {
  if (quickFilter === 'security') {
    return rows.filter((row) => row.modulo === 'SEGURIDAD' || row.accion === 'login' || row.accion === 'logout')
  }
  if (quickFilter === 'status') {
    return rows.filter((row) => row.accion === 'cambio_estado')
  }
  if (quickFilter === 'annul') {
    return rows.filter((row) => row.accion === 'anulacion')
  }
  if (quickFilter === 'cancel') {
    return rows.filter((row) => row.accion === 'cancelacion')
  }
  return rows
}

function summaryFromRows(rows) {
  return {
    total: rows.length,
    critical: rows.filter((row) => ['anulacion', 'cancelacion', 'cambio_estado'].includes(row.accion)).length,
    security: rows.filter((row) => row.modulo === 'SEGURIDAD').length,
    events: new Set(rows.map((row) => row.id_evento).filter(Boolean)).size,
  }
}

// eslint-disable-next-line react/prop-types
function SummaryCard({ title, value, accent }) {
  return (
    <Card
      bodyStyle={{ padding: 18 }}
      style={{
        borderRadius: 22,
        border: `1px solid ${accent}22`,
        background: `linear-gradient(135deg, ${accent}18, rgba(255,255,255,0.8))`,
        boxShadow: '0 22px 60px rgba(111, 76, 49, 0.08)',
      }}
    >
      <Typography.Text type="secondary">{title}</Typography.Text>
      <Typography.Title level={3} style={{ margin: '8px 0 0', color: accent }}>
        {value}
      </Typography.Title>
    </Card>
  )
}

export function AuditPage() {
  const [rows, setRows] = useState([])
  const [users, setUsers] = useState([])
  const [loading, setLoading] = useState(true)
  const [detailLoading, setDetailLoading] = useState(false)
  const [eventLoading, setEventLoading] = useState(false)
  const [detailOpen, setDetailOpen] = useState(false)
  const [detail, setDetail] = useState(null)
  const [eventRows, setEventRows] = useState([])
  const [quickFilter, setQuickFilter] = useState('all')
  const [error, setError] = useState(null)
  const [filters, setFilters] = useState(() => {
    try {
      return JSON.parse(window.sessionStorage.getItem('audit-filters') || '{}')
    } catch {
      return {}
    }
  })
  const { message } = AntdApp.useApp()

  const queryParams = useMemo(() => {
    const params = {}
    Object.entries(filters || {}).forEach(([key, value]) => {
      if (value !== undefined && value !== null && value !== '') {
        params[key] = value
      }
    })
    return params
  }, [filters])

  useEffect(() => {
    window.sessionStorage.setItem('audit-filters', JSON.stringify(filters))
  }, [filters])

  const loadRows = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const response = await apiClient.get('/auditoria', { params: queryParams })
      setRows(response.data)
    } catch (requestError) {
      setError(requestError.response?.data?.detail || 'NO FUE POSIBLE CARGAR LA AUDITORÍA DEL SISTEMA.')
    } finally {
      setLoading(false)
    }
  }, [queryParams])

  const loadUsers = useCallback(async () => {
    try {
      const response = await apiClient.get('/users')
      setUsers(response.data)
    } catch {
      setUsers([])
    }
  }, [])

  useEffect(() => {
    Promise.all([loadRows(), loadUsers()]).catch(() => {
      setError('NO FUE POSIBLE INICIALIZAR EL PANEL DE AUDITORÍA.')
      setLoading(false)
    })
  }, [loadRows, loadUsers])

  const openDetail = useCallback(async (auditId) => {
    setDetailLoading(true)
    setEventRows([])
    try {
      const response = await apiClient.get(`/auditoria/${auditId}`)
      setDetail(response.data)
      setDetailOpen(true)
      if (response.data.id_evento) {
        setEventLoading(true)
        const eventResponse = await apiClient.get(`/auditoria/eventos/${response.data.id_evento}`)
        setEventRows(eventResponse.data.records)
      }
    } catch (requestError) {
      message.error(requestError.response?.data?.detail || 'NO FUE POSIBLE CARGAR EL DETALLE DE AUDITORÍA.')
    } finally {
      setDetailLoading(false)
      setEventLoading(false)
    }
  }, [message])

  const filteredRows = useMemo(() => buildQuickFilteredRows(rows, quickFilter), [quickFilter, rows])
  const summary = useMemo(() => summaryFromRows(rows), [rows])

  const userOptions = useMemo(
    () =>
      users.map((item) => ({
        value: item.user_id,
        label: `${item.full_name} (${item.role_code})`,
      })),
    [users],
  )

  const columns = [
    {
      title: 'ACCIÓN',
      dataIndex: 'accion',
      key: 'accion',
      render: (value) => (
        <Tag
          style={{
            borderRadius: 999,
            borderColor: `${auditActionColor(value)}44`,
            color: auditActionColor(value),
            background: auditActionSurface(value),
          }}
        >
          {auditActionLabel(value)}
        </Tag>
      ),
    },
    {
      title: 'FECHA',
      dataIndex: 'fecha',
      key: 'fecha',
      render: formatAuditDate,
      sorter: (a, b) => new Date(a.fecha) - new Date(b.fecha),
      defaultSortOrder: 'descend',
    },
    {
      title: 'USUARIO',
      key: 'usuario',
      render: (_, record) => record.usuario?.full_name || 'SISTEMA',
    },
    { title: 'MÓDULO', dataIndex: 'modulo', key: 'modulo' },
    { title: 'TABLA', dataIndex: 'tabla', key: 'tabla' },
    { title: 'ID REGISTRO', dataIndex: 'id_registro', key: 'id_registro' },
    {
      title: 'ACCIÓN FUNCIONAL',
      dataIndex: 'accion_funcional',
      key: 'accion_funcional',
      render: (value) => <Typography.Text ellipsis={{ tooltip: value }}>{value || 'SIN ACCIÓN FUNCIONAL'}</Typography.Text>,
    },
    {
      title: 'CAMPO',
      dataIndex: 'campo',
      key: 'campo',
      render: (value) => value || 'RESUMEN',
    },
    {
      title: 'VALOR NUEVO',
      dataIndex: 'valor_nuevo',
      key: 'valor_nuevo',
      render: (value) => <Typography.Text ellipsis={{ tooltip: value }}>{value || '-'}</Typography.Text>,
    },
    {
      title: 'IP',
      dataIndex: 'ip',
      key: 'ip',
      render: (value) => value || '-',
    },
    {
      title: 'ACCIONES',
      key: 'actions',
      fixed: 'right',
      render: (_, record) => (
        <Space wrap>
          <Button icon={<EyeOutlined />} onClick={() => openDetail(record.id)}>
            VER
          </Button>
        </Space>
      ),
    },
  ]

  return (
    <div>
      <div className="page-header">
        <div>
          <Typography.Title level={2} style={{ margin: 0 }}>
            Auditoría del Sistema
          </Typography.Title>
          <Typography.Paragraph type="secondary" style={{ marginBottom: 0 }}>
            Trazabilidad administrativa completa de acciones sensibles, cambios de estado, anulaciones y eventos de seguridad.
          </Typography.Paragraph>
        </div>
        <Space wrap>
          <Button icon={<ReloadOutlined />} onClick={loadRows}>
            RECARGAR
          </Button>
          <Button icon={<DownloadOutlined />} onClick={() => downloadAuditCsv(apiClient, queryParams)}>
            EXPORTAR CSV
          </Button>
          <Button icon={<PrinterOutlined />} onClick={() => openAuditPrintable(apiClient, queryParams, message)}>
            IMPRIMIR / PDF
          </Button>
        </Space>
      </div>

      <Row gutter={[14, 14]} style={{ marginBottom: 18 }}>
        <Col xs={24} sm={12} xl={6}>
          <SummaryCard title="REGISTROS VISIBLES" value={summary.total} accent="#6f4c31" />
        </Col>
        <Col xs={24} sm={12} xl={6}>
          <SummaryCard title="EVENTOS AGRUPADOS" value={summary.events} accent="#5278a3" />
        </Col>
        <Col xs={24} sm={12} xl={6}>
          <SummaryCard title="EVENTOS SENSIBLES" value={summary.critical} accent="#b8475c" />
        </Col>
        <Col xs={24} sm={12} xl={6}>
          <SummaryCard title="SEGURIDAD" value={summary.security} accent="#7a6a2d" />
        </Col>
      </Row>

      <div
        className="glass-panel"
        style={{
          marginBottom: 16,
          padding: 18,
          borderRadius: 26,
          background: 'linear-gradient(135deg, rgba(255,252,247,0.96), rgba(247,238,229,0.88))',
        }}
      >
        <Row gutter={[12, 12]}>
          <Col xs={24} md={6}>
            <Input
              allowClear
              prefix={<SearchOutlined />}
              placeholder="DESCRIPCIÓN"
              value={filters.search_description}
              onChange={(event) => setFilters((current) => ({ ...current, search_description: event.target.value.toUpperCase() }))}
            />
          </Col>
          <Col xs={24} md={4}>
            <Select
              allowClear
              placeholder="MÓDULO"
              options={MODULE_OPTIONS}
              value={filters.module}
              onChange={(value) => setFilters((current) => ({ ...current, module: value }))}
              style={{ width: '100%' }}
            />
          </Col>
          <Col xs={24} md={4}>
            <Select
              allowClear
              placeholder="ACCIÓN"
              options={AUDIT_ACTION_OPTIONS}
              value={filters.action}
              onChange={(value) => setFilters((current) => ({ ...current, action: value }))}
              style={{ width: '100%' }}
            />
          </Col>
          <Col xs={24} md={4}>
            <Select
              allowClear
              showSearch
              optionFilterProp="label"
              placeholder="USUARIO"
              options={userOptions}
              value={filters.user_id}
              onChange={(value) => setFilters((current) => ({ ...current, user_id: value }))}
              style={{ width: '100%' }}
            />
          </Col>
          <Col xs={24} md={3}>
            <Input
              allowClear
              placeholder="TABLA"
              value={filters.table}
              onChange={(event) => setFilters((current) => ({ ...current, table: event.target.value.toUpperCase() }))}
            />
          </Col>
          <Col xs={24} md={3}>
            <Input
              allowClear
              placeholder="IP"
              value={filters.ip}
              onChange={(event) => setFilters((current) => ({ ...current, ip: event.target.value }))}
            />
          </Col>
          <Col xs={24} md={4}>
            <Input
              allowClear
              placeholder="CAMPO"
              value={filters.search_field}
              onChange={(event) => setFilters((current) => ({ ...current, search_field: event.target.value.toUpperCase() }))}
            />
          </Col>
          <Col xs={24} md={4}>
            <Input
              allowClear
              placeholder="VALOR NUEVO"
              value={filters.search_new_value}
              onChange={(event) => setFilters((current) => ({ ...current, search_new_value: event.target.value.toUpperCase() }))}
            />
          </Col>
          <Col xs={24} md={4}>
            <Input
              allowClear
              placeholder="ID EVENTO"
              value={filters.event_id}
              onChange={(event) => setFilters((current) => ({ ...current, event_id: event.target.value }))}
            />
          </Col>
          <Col xs={24} md={4}>
            <Input
              allowClear
              placeholder="ID REGISTRO"
              value={filters.record_id}
              onChange={(event) => setFilters((current) => ({ ...current, record_id: event.target.value }))}
            />
          </Col>
          <Col xs={24} md={4}>
            <Input
              allowClear
              placeholder="NAVEGADOR"
              value={filters.browser}
              onChange={(event) => setFilters((current) => ({ ...current, browser: event.target.value.toUpperCase() }))}
            />
          </Col>
          <Col xs={24} md={4}>
            <Input
              allowClear
              placeholder="DISPOSITIVO"
              value={filters.device}
              onChange={(event) => setFilters((current) => ({ ...current, device: event.target.value.toUpperCase() }))}
            />
          </Col>
        </Row>

        <Space wrap style={{ marginTop: 14 }}>
          {QUICK_FILTERS.map((item) => (
            <Button
              key={item.key}
              type={quickFilter === item.key ? 'primary' : 'default'}
              onClick={() => setQuickFilter(item.key)}
            >
              {item.label}
            </Button>
          ))}
          <Button
            onClick={() => {
              setFilters({})
              setQuickFilter('all')
            }}
          >
            LIMPIAR FILTROS
          </Button>
        </Space>
      </div>

      {error ? <Alert type="error" showIcon message={error} style={{ marginBottom: 16 }} /> : null}

      <Table
        className="glass-panel"
        rowKey="id"
        columns={columns}
        dataSource={filteredRows}
        loading={loading}
        pagination={{ pageSize: 12 }}
        scroll={{ x: 'max-content' }}
        style={{ borderRadius: 24, overflow: 'hidden' }}
      />

      <Drawer
        title="Detalle de Auditoría"
        width={980}
        open={detailOpen}
        onClose={() => {
          setDetailOpen(false)
          setDetail(null)
          setEventRows([])
        }}
        maskClosable={false}
      >
        {detailLoading ? (
          <Typography.Text>CARGANDO DETALLE...</Typography.Text>
        ) : detail ? (
          <>
            <Descriptions bordered column={2} size="small" style={{ marginBottom: 20 }}>
              <Descriptions.Item label="ACCIÓN">
                <Tag
                  style={{
                    borderRadius: 999,
                    borderColor: `${auditActionColor(detail.accion)}44`,
                    color: auditActionColor(detail.accion),
                    background: auditActionSurface(detail.accion),
                  }}
                >
                  {auditActionLabel(detail.accion)}
                </Tag>
              </Descriptions.Item>
              <Descriptions.Item label="FECHA">{formatAuditDate(detail.fecha)}</Descriptions.Item>
              <Descriptions.Item label="USUARIO">{detail.usuario?.full_name || 'SISTEMA'}</Descriptions.Item>
              <Descriptions.Item label="USERNAME">{detail.usuario?.username || 'SIN CUENTA'}</Descriptions.Item>
              <Descriptions.Item label="MÓDULO">{detail.modulo}</Descriptions.Item>
              <Descriptions.Item label="SUBMÓDULO">{detail.submodulo || 'SIN SUBMÓDULO'}</Descriptions.Item>
              <Descriptions.Item label="TABLA">{detail.tabla}</Descriptions.Item>
              <Descriptions.Item label="ID REGISTRO">{detail.id_registro}</Descriptions.Item>
              <Descriptions.Item label="CAMPO">{detail.campo || 'RESUMEN'}</Descriptions.Item>
              <Descriptions.Item label="HTTP">{detail.metodo_http || 'SIN MÉTODO'}</Descriptions.Item>
              <Descriptions.Item label="IP">{detail.ip || 'SIN IP'}</Descriptions.Item>
              <Descriptions.Item label="NAVEGADOR">{detail.navegador || 'SIN NAVEGADOR'}</Descriptions.Item>
              <Descriptions.Item label="DISPOSITIVO">{detail.dispositivo || 'SIN DISPOSITIVO'}</Descriptions.Item>
              <Descriptions.Item label="SISTEMA OPERATIVO">{detail.sistema_operativo || 'SIN SISTEMA OPERATIVO'}</Descriptions.Item>
              <Descriptions.Item label="ID EVENTO">{detail.id_evento || 'SIN EVENTO'}</Descriptions.Item>
              <Descriptions.Item label="DESCRIPCIÓN" span={2}>
                {detail.descripcion || 'SIN DESCRIPCIÓN'}
              </Descriptions.Item>
              <Descriptions.Item label="VALOR ANTERIOR" span={2}>
                <Typography.Text code>{detail.valor_anterior || 'SIN VALOR ANTERIOR'}</Typography.Text>
              </Descriptions.Item>
              <Descriptions.Item label="VALOR NUEVO" span={2}>
                <Typography.Text code>{detail.valor_nuevo || 'SIN VALOR NUEVO'}</Typography.Text>
              </Descriptions.Item>
              <Descriptions.Item label="USER AGENT" span={2}>
                {detail.user_agent || 'SIN USER AGENT'}
              </Descriptions.Item>
            </Descriptions>

            <div
              style={{
                borderRadius: 22,
                padding: 18,
                background: 'linear-gradient(135deg, rgba(255,247,241,0.92), rgba(247,239,231,0.88))',
                border: '1px solid rgba(143, 61, 46, 0.12)',
              }}
            >
              <Space style={{ justifyContent: 'space-between', width: '100%', marginBottom: 12 }} wrap>
                <div>
                  <Typography.Title level={5} style={{ margin: 0 }}>
                    Evento Lógico Asociado
                  </Typography.Title>
                  <Typography.Text type="secondary">
                    {detail.event_records_count} REGISTROS RELACIONADOS A ESTE EVENTO
                  </Typography.Text>
                </div>
                {detail.id_evento ? (
                  <Button icon={<FileSearchOutlined />} onClick={() => openAuditPrintable(apiClient, { event_id: detail.id_evento }, message)}>
                    IMPRIMIR EVENTO
                  </Button>
                ) : null}
              </Space>

              <Table
                rowKey="id"
                size="small"
                loading={eventLoading}
                pagination={false}
                dataSource={eventRows}
                columns={[
                  { title: 'FECHA', dataIndex: 'fecha', key: 'fecha', render: formatAuditDate },
                  { title: 'TABLA', dataIndex: 'tabla', key: 'tabla' },
                  { title: 'ACCIÓN', dataIndex: 'accion', key: 'accion', render: auditActionLabel },
                  { title: 'CAMPO', dataIndex: 'campo', key: 'campo', render: (value) => value || 'RESUMEN' },
                  { title: 'VALOR NUEVO', dataIndex: 'valor_nuevo', key: 'valor_nuevo', render: (value) => value || '-' },
                ]}
                scroll={{ x: 'max-content' }}
              />
            </div>
          </>
        ) : null}
      </Drawer>
    </div>
  )
}
