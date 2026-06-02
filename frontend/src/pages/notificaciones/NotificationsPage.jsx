import {
  CheckOutlined,
  EyeOutlined,
  LinkOutlined,
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
  Tabs,
  Typography,
} from 'antd'
import { useCallback, useEffect, useMemo, useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'

import { apiClient } from '../../api/client'
import { useAuth } from '../../auth/AuthProvider'
import {
  buildNotificationOriginPath,
  NOTIFICATION_MODULE_OPTIONS,
  NOTIFICATION_PRIORITY_OPTIONS,
  NOTIFICATION_TYPE_OPTIONS,
  notificationPriorityColor,
  notificationPriorityLabel,
  notificationPrioritySurface,
  notificationStatusLabel,
} from './notificationUtils'

const QUICK_FILTERS = [
  { key: 'all', label: 'TODAS' },
  { key: 'unread', label: 'NO LEÍDAS' },
  { key: 'pending', label: 'PENDIENTES' },
  { key: 'resolved', label: 'RESUELTAS' },
  { key: 'urgent', label: 'URGENTES' },
]

function formatNotificationDate(value) {
  return value ? new Date(value).toLocaleString('es-BO') : 'SIN FECHA'
}

// eslint-disable-next-line react/prop-types
function SummaryMiniCard({ title, value, accent }) {
  return (
    <Card
      bodyStyle={{ padding: 18 }}
      style={{
        borderRadius: 22,
        border: `1px solid ${accent}22`,
        background: `linear-gradient(135deg, ${accent}18, rgba(255,255,255,0.78))`,
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

export function NotificationsPage() {
  const [notifications, setNotifications] = useState([])
  const [users, setUsers] = useState([])
  const [roles, setRoles] = useState([])
  const [reportSummary, setReportSummary] = useState(null)
  const [loading, setLoading] = useState(true)
  const [detailLoading, setDetailLoading] = useState(false)
  const [detailOpen, setDetailOpen] = useState(false)
  const [detail, setDetail] = useState(null)
  const [error, setError] = useState(null)
  const [quickFilter, setQuickFilter] = useState('all')
  const [filters, setFilters] = useState({
    search: '',
    module: undefined,
    type: undefined,
    priority: undefined,
    is_read: undefined,
    is_resolved: undefined,
    role_code: undefined,
    user_id: undefined,
  })
  const { message, modal } = AntdApp.useApp()
  const { user } = useAuth()
  const navigate = useNavigate()
  const [searchParams, setSearchParams] = useSearchParams()

  const isAdmin = user?.permissions?.includes('notifications:report')
  const canResolve = user?.permissions?.includes('notifications:resolve')
  const canRetryEmail = user?.permissions?.includes('notifications:retry_email')
  const canMarkAllRead = user?.permissions?.includes('notifications:mark_all_read')

  const loadReferences = useCallback(async () => {
    if (!isAdmin) return
    const [usersResponse, rolesResponse] = await Promise.all([apiClient.get('/users'), apiClient.get('/roles')])
    setUsers(usersResponse.data)
    setRoles(rolesResponse.data)
  }, [isAdmin])

  const loadReportSummary = useCallback(async () => {
    if (!isAdmin) return
    const response = await apiClient.get('/notificaciones/reportes/resumen')
    setReportSummary(response.data)
  }, [isAdmin])

  const loadNotifications = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const params = {}
      if (filters.search) params.search = filters.search
      if (filters.module) params.module = filters.module
      if (filters.type) params.type = filters.type
      if (filters.priority) params.priority = filters.priority
      if (filters.is_read !== undefined) params.is_read = filters.is_read
      if (filters.is_resolved !== undefined) params.is_resolved = filters.is_resolved
      if (filters.role_code) params.role_code = filters.role_code
      if (filters.user_id) params.user_id = filters.user_id
      const response = await apiClient.get('/notificaciones', { params })
      setNotifications(response.data)
    } catch (requestError) {
      setError(requestError.response?.data?.detail || 'NO FUE POSIBLE CARGAR LAS NOTIFICACIONES.')
    } finally {
      setLoading(false)
    }
  }, [filters])

  useEffect(() => {
    Promise.all([loadNotifications(), loadReferences(), loadReportSummary()]).catch(() => {
      setError('NO FUE POSIBLE CARGAR EL MÓDULO DE NOTIFICACIONES.')
      setLoading(false)
    })
  }, [loadNotifications, loadReferences, loadReportSummary])

  const openDetail = useCallback(async (notificationId) => {
    setDetailLoading(true)
    try {
      const response = await apiClient.get(`/notificaciones/${notificationId}`)
      setDetail(response.data)
      setDetailOpen(true)
    } catch (requestError) {
      message.error(requestError.response?.data?.detail || 'NO FUE POSIBLE CARGAR EL DETALLE DE LA NOTIFICACIÓN.')
    } finally {
      setDetailLoading(false)
    }
  }, [message])

  useEffect(() => {
    const notificationId = searchParams.get('notification_id')
    if (!notificationId) return
    openDetail(Number(notificationId)).finally(() => {
      const next = new URLSearchParams(searchParams)
      next.delete('notification_id')
      setSearchParams(next, { replace: true })
    })
  }, [openDetail, searchParams, setSearchParams])

  const handleMarkRead = useCallback(async (record) => {
    try {
      await apiClient.patch(`/notificaciones/${record.id}/read`)
      await loadNotifications()
      if (detail?.id === record.id) {
        await openDetail(record.id)
      }
      message.success('SE MARCÓ LA NOTIFICACIÓN COMO LEÍDA.')
    } catch (requestError) {
      message.error(requestError.response?.data?.detail || 'NO FUE POSIBLE MARCAR LA NOTIFICACIÓN.')
    }
  }, [detail?.id, loadNotifications, message, openDetail])

  const handleResolve = useCallback((record) => {
    modal.confirm({
      title: 'RESOLVER NOTIFICACIÓN',
      content: 'SE MARCARÁ LA NOTIFICACIÓN COMO RESUELTA. ASEGÚRATE DE QUE LA CONDICIÓN YA FUE ATENDIDA.',
      okText: 'RESOLVER',
      cancelText: 'CANCELAR',
      onOk: async () => {
        await apiClient.patch(`/notificaciones/${record.id}/resolve`, { motivo: 'RESUELTA DESDE EL PANEL DE NOTIFICACIONES' })
        await Promise.all([loadNotifications(), loadReportSummary()])
        if (detail?.id === record.id) {
          await openDetail(record.id)
        }
        message.success('LA NOTIFICACIÓN QUEDÓ RESUELTA.')
      },
    })
  }, [detail?.id, loadNotifications, loadReportSummary, message, modal, openDetail])

  const handleRetryEmail = useCallback(async (record) => {
    try {
      await apiClient.post(`/notificaciones/${record.id}/retry-email`)
      await Promise.all([loadNotifications(), loadReportSummary()])
      if (detail?.id === record.id) {
        await openDetail(record.id)
      }
      message.success('SE REINTENTÓ EL ENVÍO DEL CORREO CORRECTAMENTE.')
    } catch (requestError) {
      message.error(requestError.response?.data?.detail || 'NO FUE POSIBLE REINTENTAR EL ENVÍO DEL CORREO.')
    }
  }, [detail?.id, loadNotifications, loadReportSummary, message, openDetail])

  const handleMarkAllRead = useCallback(async () => {
    try {
      await apiClient.patch('/notificaciones/read-all')
      await loadNotifications()
      if (isAdmin) {
        await loadReportSummary()
      }
      message.success('SE MARCARON LAS NOTIFICACIONES COMO LEÍDAS.')
    } catch (requestError) {
      message.error(requestError.response?.data?.detail || 'NO FUE POSIBLE MARCAR TODAS LAS NOTIFICACIONES.')
    }
  }, [isAdmin, loadNotifications, loadReportSummary, message])

  const userOptions = useMemo(
    () =>
      users.map((item) => ({
        label: `${item.full_name} (${item.role_code})`,
        value: item.user_id,
      })),
    [users],
  )

  const roleOptions = useMemo(
    () =>
      roles.map((role) => ({
        label: role.nombre,
        value: role.codigo,
      })),
    [roles],
  )

  const filteredNotifications = useMemo(() => {
    if (quickFilter === 'unread') return notifications.filter((item) => !item.leida)
    if (quickFilter === 'pending') return notifications.filter((item) => !item.resuelta)
    if (quickFilter === 'resolved') return notifications.filter((item) => item.resuelta)
    if (quickFilter === 'urgent') return notifications.filter((item) => item.prioridad === 'urgente')
    return notifications
  }, [notifications, quickFilter])

  const columns = [
    {
      title: 'PRIORIDAD',
      dataIndex: 'prioridad',
      key: 'prioridad',
      render: (value) => (
        <Tag
          style={{
            borderRadius: 999,
            borderColor: `${notificationPriorityColor(value)}44`,
            color: notificationPriorityColor(value),
            background: notificationPrioritySurface(value),
          }}
        >
          {notificationPriorityLabel(value)}
        </Tag>
      ),
    },
    { title: 'TÍTULO', dataIndex: 'titulo', key: 'titulo' },
    {
      title: 'MENSAJE',
      dataIndex: 'mensaje',
      key: 'mensaje',
      render: (value) => <Typography.Text ellipsis={{ tooltip: value }}>{value}</Typography.Text>,
    },
    { title: 'MÓDULO', dataIndex: 'modulo', key: 'modulo', render: (value) => value || 'SIN MÓDULO' },
    isAdmin
      ? {
          title: 'DESTINATARIA/O',
          key: 'recipient',
          render: (_, record) => `${record.recipient.full_name} (${record.recipient.role_code || 'SIN ROL'})`,
        }
      : null,
    {
      title: 'ESTADO',
      key: 'estado',
      render: (_, record) => (
        <Tag color={record.resuelta ? 'green' : record.leida ? 'blue' : 'gold'}>
          {notificationStatusLabel(record)}
        </Tag>
      ),
    },
    { title: 'FECHA', dataIndex: 'fecha', key: 'fecha', render: formatNotificationDate },
    {
      title: 'ACCIONES',
      key: 'acciones',
      render: (_, record) => (
        <Space wrap>
          <Button icon={<EyeOutlined />} onClick={() => openDetail(record.id)}>VER</Button>
          {!record.leida ? <Button icon={<CheckOutlined />} onClick={() => handleMarkRead(record)}>LEÍDA</Button> : null}
          <Button icon={<LinkOutlined />} onClick={() => navigate(buildNotificationOriginPath(record))}>IR AL ORIGEN</Button>
          {canResolve && !record.resuelta ? <Button onClick={() => handleResolve(record)}>RESOLVER</Button> : null}
          {canRetryEmail && record.tipo === 'ERROR_ENVIO_CORREO' ? (
            <Button icon={<ReloadOutlined />} onClick={() => handleRetryEmail(record)}>
              REINTENTAR CORREO
            </Button>
          ) : null}
        </Space>
      ),
    },
  ].filter(Boolean)

  return (
    <div>
      <div className="page-header">
        <div>
          <Typography.Title level={2} style={{ margin: 0 }}>
            Notificaciones
          </Typography.Title>
          <Typography.Paragraph type="secondary" style={{ marginBottom: 0 }}>
            Centro operativo de alertas internas por stock, pruebas, entregas, fletes y seguridad.
          </Typography.Paragraph>
        </div>
        {canMarkAllRead ? (
          <Button icon={<CheckOutlined />} onClick={handleMarkAllRead}>
            MARCAR TODAS COMO LEÍDAS
          </Button>
        ) : null}
      </div>

      {isAdmin && reportSummary ? (
        <Row gutter={[14, 14]} style={{ marginBottom: 18 }}>
          <Col xs={24} sm={12} xl={6}>
            <SummaryMiniCard title="TOTAL REGISTRADAS" value={reportSummary.total} accent="#6f4c31" />
          </Col>
          <Col xs={24} sm={12} xl={6}>
            <SummaryMiniCard title="NO LEÍDAS" value={reportSummary.unread} accent="#5278a3" />
          </Col>
          <Col xs={24} sm={12} xl={6}>
            <SummaryMiniCard title="NO RESUELTAS" value={reportSummary.unresolved} accent="#b87b2f" />
          </Col>
          <Col xs={24} sm={12} xl={6}>
            <SummaryMiniCard title="URGENTES ABIERTAS" value={reportSummary.urgent_unresolved} accent="#b8475c" />
          </Col>
        </Row>
      ) : null}

      <div className="glass-panel boutique-filter-bar" style={{ marginBottom: 16 }}>
        <Row gutter={[12, 12]}>
          <Col xs={24} md={6}>
            <Input
              allowClear
              prefix={<SearchOutlined />}
              placeholder="BUSCAR TÍTULO, MENSAJE O DESTINATARIA/O"
              value={filters.search}
              onChange={(event) => setFilters((current) => ({ ...current, search: event.target.value.toUpperCase() }))}
            />
          </Col>
          <Col xs={24} md={4}>
            <Select
              allowClear
              placeholder="MÓDULO"
              options={NOTIFICATION_MODULE_OPTIONS}
              value={filters.module}
              onChange={(value) => setFilters((current) => ({ ...current, module: value }))}
              style={{ width: '100%' }}
            />
          </Col>
          <Col xs={24} md={4}>
            <Select
              allowClear
              placeholder="TIPO"
              options={NOTIFICATION_TYPE_OPTIONS}
              value={filters.type}
              onChange={(value) => setFilters((current) => ({ ...current, type: value }))}
              style={{ width: '100%' }}
              showSearch
              optionFilterProp="label"
            />
          </Col>
          <Col xs={24} md={3}>
            <Select
              allowClear
              placeholder="PRIORIDAD"
              options={NOTIFICATION_PRIORITY_OPTIONS}
              value={filters.priority}
              onChange={(value) => setFilters((current) => ({ ...current, priority: value }))}
              style={{ width: '100%' }}
            />
          </Col>
          {isAdmin ? (
            <Col xs={24} md={3}>
              <Select
                allowClear
                placeholder="ROL"
                options={roleOptions}
                value={filters.role_code}
                onChange={(value) => setFilters((current) => ({ ...current, role_code: value }))}
                style={{ width: '100%' }}
              />
            </Col>
          ) : null}
          {isAdmin ? (
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
          ) : null}
        </Row>
      </div>

      <Tabs
        activeKey={quickFilter}
        onChange={setQuickFilter}
        items={QUICK_FILTERS.map((item) => ({ key: item.key, label: item.label }))}
        style={{ marginBottom: 12 }}
      />

      {error ? <Alert type="error" showIcon message={error} style={{ marginBottom: 16 }} /> : null}

      <Table
        className="glass-panel"
        rowKey="id"
        columns={columns}
        dataSource={filteredNotifications}
        loading={loading}
        pagination={{ pageSize: 10 }}
        scroll={{ x: 'max-content' }}
        style={{ borderRadius: 24, overflow: 'hidden' }}
      />

      <Drawer
        title="Detalle de la Notificación"
        width={860}
        open={detailOpen}
        onClose={() => {
          setDetailOpen(false)
          setDetail(null)
        }}
        maskClosable={false}
      >
        {detail ? (
          <>
            <Row gutter={[12, 12]} style={{ marginBottom: 16 }}>
              {!detail.leida ? (
                <Col>
                  <Button icon={<CheckOutlined />} onClick={() => handleMarkRead(detail)}>
                    Marcar como leída
                  </Button>
                </Col>
              ) : null}
              <Col>
                <Button icon={<LinkOutlined />} onClick={() => navigate(buildNotificationOriginPath(detail))}>
                  Ir al origen
                </Button>
              </Col>
              {canResolve && !detail.resuelta ? (
                <Col>
                  <Button onClick={() => handleResolve(detail)}>Resolver</Button>
                </Col>
              ) : null}
              {canRetryEmail && detail.tipo === 'ERROR_ENVIO_CORREO' ? (
                <Col>
                  <Button icon={<ReloadOutlined />} onClick={() => handleRetryEmail(detail)}>
                    Reintentar correo
                  </Button>
                </Col>
              ) : null}
            </Row>

            <Descriptions bordered column={2} size="small">
              <Descriptions.Item label="TÍTULO">{detail.titulo}</Descriptions.Item>
              <Descriptions.Item label="PRIORIDAD">
                <Tag
                  style={{
                    borderRadius: 999,
                    borderColor: `${notificationPriorityColor(detail.prioridad)}44`,
                    color: notificationPriorityColor(detail.prioridad),
                    background: notificationPrioritySurface(detail.prioridad),
                  }}
                >
                  {notificationPriorityLabel(detail.prioridad)}
                </Tag>
              </Descriptions.Item>
              <Descriptions.Item label="TIPO">{detail.tipo}</Descriptions.Item>
              <Descriptions.Item label="MÓDULO">{detail.modulo || 'SIN MÓDULO'}</Descriptions.Item>
              <Descriptions.Item label="DESTINATARIA/O">{detail.recipient.full_name}</Descriptions.Item>
              <Descriptions.Item label="ROL">{detail.recipient.role_name || 'SIN ROL'}</Descriptions.Item>
              <Descriptions.Item label="ESTADO">{notificationStatusLabel(detail)}</Descriptions.Item>
              <Descriptions.Item label="FECHA">{formatNotificationDate(detail.fecha)}</Descriptions.Item>
              <Descriptions.Item label="LEÍDA">{detail.leida ? formatNotificationDate(detail.fecha_leida) : 'NO'}</Descriptions.Item>
              <Descriptions.Item label="RESUELTA">{detail.resuelta ? formatNotificationDate(detail.fecha_resuelta) : 'NO'}</Descriptions.Item>
              <Descriptions.Item label="TABLA REFERENCIA">{detail.tabla_referencia || 'SIN REFERENCIA'}</Descriptions.Item>
              <Descriptions.Item label="ID REFERENCIA">{detail.id_referencia || 'SIN REFERENCIA'}</Descriptions.Item>
              <Descriptions.Item label="MENSAJE" span={2}>
                {detail.mensaje}
              </Descriptions.Item>
            </Descriptions>
          </>
        ) : detailLoading ? (
          <Typography.Text>CARGANDO DETALLE...</Typography.Text>
        ) : null}
      </Drawer>
    </div>
  )
}
