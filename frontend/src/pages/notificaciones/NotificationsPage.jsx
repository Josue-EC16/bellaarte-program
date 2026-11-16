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
  Switch,
  Table,
  Tag,
  Tabs,
  Typography,
} from 'antd'
import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'

import { apiClient } from '../../api/client'
import { useAuth } from '../../auth/AuthProvider'
import { notifyNotificationsChanged } from './notificationTransport'
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
      styles={{ body: { padding: 18 } }}
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
  const [scope, setScope] = useState('personal')
  const [page, setPage] = useState(1)
  const [pageSize, setPageSize] = useState(25)
  const [total, setTotal] = useState(0)
  const [search, setSearch] = useState('')
  const [desktopEnabled, setDesktopEnabled] = useState(false)
  const [preferenceLoading, setPreferenceLoading] = useState(true)
  const [actionLoading, setActionLoading] = useState(null)
  const actionInFlight = useRef(false)
  const listRequest = useRef(null)
  const listGeneration = useRef(0)
  const detailGeneration = useRef(0)
  const latestListLoader = useRef(null)
  const latestReportLoader = useRef(null)
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

  const canSupervise = Boolean(user?.permissions?.includes('notifications:list_all'))
  const canReport = Boolean(user?.permissions?.includes('notifications:report'))
  const isAdmin = scope === 'supervision' && canSupervise
  const canResolve = user?.permissions?.includes('notifications:resolve')
  const canRetryEmail = user?.permissions?.includes('notifications:retry_email')
  const canMarkAllRead = user?.permissions?.includes('notifications:mark_all_read')
  const { module, type, priority, is_read: isRead, is_resolved: isResolved, role_code: roleCode, user_id: recipientId } = filters

  useEffect(() => {
    const timer = window.setTimeout(() => { setSearch(filters.search.trim()); setPage(1) }, 300)
    return () => window.clearTimeout(timer)
  }, [filters.search])

  useEffect(() => {
    const controller = new AbortController()
    const requests = []
    if (canSupervise && user?.permissions?.includes('users:list')) {
      requests.push(apiClient.get('/users', { signal: controller.signal }).then((response) => setUsers(response.data)))
    }
    if (canSupervise && user?.permissions?.includes('roles:list')) {
      requests.push(apiClient.get('/roles', { signal: controller.signal }).then((response) => setRoles(response.data)))
    }
    Promise.all(requests).catch((requestError) => {
      if (requestError.code !== 'ERR_CANCELED') setError('No se pudieron cargar los filtros de destinatarios.')
    })
    return () => controller.abort()
  }, [canSupervise, user?.permissions])

  useEffect(() => {
    let active = true
    apiClient.get('/notificaciones/preferencias')
      .then((response) => { if (active) setDesktopEnabled(response.data.desktop_enabled) })
      .catch(() => { if (active) setError('No se pudo consultar la preferencia de escritorio.') })
      .finally(() => { if (active) setPreferenceLoading(false) })
    return () => { active = false }
  }, [])

  const queryParams = useMemo(() => {
    const params = {}
    if (search) params.search = search
    if (module !== undefined) params.module = module
    if (type !== undefined) params.type = type
    if (priority !== undefined) params.priority = priority
    if (isRead !== undefined) params.is_read = isRead
    if (isResolved !== undefined) params.is_resolved = isResolved
    if (isAdmin && roleCode) params.role_code = roleCode
    if (isAdmin && recipientId) params.user_id = recipientId
    if (quickFilter === 'unread') { params.is_read = false; params.is_resolved = false }
    if (quickFilter === 'pending') params.is_resolved = false
    if (quickFilter === 'resolved') params.is_resolved = true
    if (quickFilter === 'urgent') { params.priority = 'urgente'; params.is_resolved = false }
    return params
  }, [search, module, type, priority, isRead, isResolved, roleCode, recipientId, isAdmin, quickFilter])

  const loadReportSummary = useCallback(async () => {
    if (!isAdmin || !canReport) return
    const response = await apiClient.get('/notificaciones/reportes/resumen', { params: queryParams })
    setReportSummary(response.data)
  }, [isAdmin, canReport, queryParams])

  const loadNotifications = useCallback(async () => {
    setLoading(true)
    setError(null)
    listRequest.current?.abort()
    const controller = new AbortController()
    listRequest.current = controller
    const generation = ++listGeneration.current
    try {
      const response = await apiClient.get(isAdmin ? '/notificaciones/supervision' : '/notificaciones', {
        params: { ...queryParams, page, page_size: pageSize }, signal: controller.signal,
      })
      if (generation === listGeneration.current) {
        setNotifications(response.data.items)
        setTotal(response.data.total)
      }
      return true
    } catch (requestError) {
      if (generation === listGeneration.current && requestError.code !== 'ERR_CANCELED') {
        setError(requestError.response?.data?.detail || 'NO FUE POSIBLE CARGAR LAS NOTIFICACIONES.')
      }
      return false
    } finally {
      if (generation === listGeneration.current) setLoading(false)
    }
  }, [isAdmin, queryParams, page, pageSize])
  latestListLoader.current = loadNotifications
  latestReportLoader.current = loadReportSummary

  useEffect(() => {
    loadNotifications()
    return () => listRequest.current?.abort()
  }, [loadNotifications])

  useEffect(() => {
    let active = true
    if (isAdmin && canReport) {
      apiClient.get('/notificaciones/reportes/resumen', { params: queryParams })
        .then((response) => { if (active) setReportSummary(response.data) })
        .catch(() => { if (active) setError('No se pudo actualizar el resumen administrativo.') })
    } else setReportSummary(null)
    return () => { active = false }
  }, [isAdmin, canReport, queryParams])

  const openDetail = useCallback(async (notificationId) => {
    setDetailLoading(true)
    const generation = ++detailGeneration.current
    try {
      const response = await apiClient.get(isAdmin ? `/notificaciones/supervision/${notificationId}` : `/notificaciones/${notificationId}`)
      if (generation === detailGeneration.current) {
        setDetail(response.data)
        setDetailOpen(true)
      }
    } catch (requestError) {
      message.error(requestError.response?.data?.detail || 'NO FUE POSIBLE CARGAR EL DETALLE DE LA NOTIFICACIÓN.')
    } finally {
      if (generation === detailGeneration.current) setDetailLoading(false)
    }
  }, [isAdmin, message])

  useEffect(() => {
    const notificationId = searchParams.get('notification_id')
    if (!notificationId) return
    openDetail(Number(notificationId)).finally(() => {
      const next = new URLSearchParams(searchParams)
      next.delete('notification_id')
      setSearchParams(next, { replace: true })
    })
  }, [openDetail, searchParams, setSearchParams])

  const runMutation = useCallback(async (key, write, successMessage, recordId) => {
    if (actionInFlight.current) return
    actionInFlight.current = true
    setActionLoading(key)
    try {
      await write()
      notifyNotificationsChanged()
      message.success(successMessage)
      const refreshed = await latestListLoader.current()
      try {
        await latestReportLoader.current()
        if (recordId != null && detail?.id === recordId) await openDetail(recordId)
      } catch {
        setError('La acción se completó, pero no se pudo actualizar todo el panel. Reintenta la consulta.')
      }
      if (!refreshed) setError('La acción se completó, pero no se pudo recargar la lista. Reintenta la consulta.')
    } catch (requestError) {
      message.error(requestError.response?.data?.detail || 'NO FUE POSIBLE COMPLETAR LA ACCIÓN.')
    } finally {
      actionInFlight.current = false
      setActionLoading(null)
    }
  }, [detail?.id, message, openDetail])

  const handleMarkRead = useCallback((record) => runMutation(
    `read:${record.id}`,
    () => apiClient.patch(`/notificaciones/${record.id}/read`, { revision: record.revision }),
    'SE MARCÓ LA NOTIFICACIÓN COMO LEÍDA.', record.id,
  ), [runMutation])

  const handleResolve = useCallback((record) => {
    modal.confirm({
      title: 'RESOLVER NOTIFICACIÓN',
      content: 'Confirma que esta tarea fue atendida. Las alertas por condición se cierran automáticamente desde su origen.',
      okText: 'RESOLVER',
      cancelText: 'CANCELAR',
      onOk: () => runMutation(`resolve:${record.id}`,
        () => apiClient.patch(`/notificaciones/${record.id}/resolve`, { motivo: 'TAREA ATENDIDA DESDE EL PANEL DE NOTIFICACIONES' }),
        'LA NOTIFICACIÓN QUEDÓ RESUELTA.', record.id),
    })
  }, [modal, runMutation])

  const handleRetryEmail = useCallback((record) => {
    modal.confirm({
      title: 'Reintentar correo de bienvenida',
      content: 'Si el resultado anterior fue incierto, el correo podría haberse enviado. Este reintento puede repetir el mensaje y no cambiará la contraseña de la cuenta.',
      okText: 'Confirmar reintento', cancelText: 'Cancelar',
      onOk: () => runMutation(`retry:${record.id}`,
        () => apiClient.post(`/notificaciones/${record.id}/retry-email`, { confirm_uncertain: true }),
        'CORREO ENVIADO CORRECTAMENTE.', record.id),
    })
  }, [modal, runMutation])

  const handleMarkAllRead = useCallback(() => runMutation('read-all',
    () => apiClient.patch('/notificaciones/read-all'), 'SE MARCARON TUS NOTIFICACIONES COMO LEÍDAS.'), [runMutation])

  const changeDesktopPreference = async (enabled) => {
    if (preferenceLoading) return
    if (enabled) {
      if (!window.Notification) { message.warning('Este navegador no admite avisos de escritorio.'); return }
      let permission = window.Notification.permission
      if (permission === 'default') permission = await window.Notification.requestPermission()
      if (permission !== 'granted') { message.warning('Debes permitir los avisos en el navegador para activarlos.'); return }
    }
    setPreferenceLoading(true)
    try {
      const response = await apiClient.patch('/notificaciones/preferencias', { desktop_enabled: enabled })
      setDesktopEnabled(response.data.desktop_enabled)
      notifyNotificationsChanged()
    } catch (requestError) {
      message.error(requestError.response?.data?.detail || 'No se pudo guardar la preferencia.')
    } finally { setPreferenceLoading(false) }
  }

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
          {!isAdmin && !record.leida && !record.resuelta ? <Button loading={actionLoading === `read:${record.id}`} disabled={Boolean(actionLoading)} icon={<CheckOutlined />} onClick={() => handleMarkRead(record)}>LEÍDA</Button> : null}
          <Button icon={<LinkOutlined />} onClick={() => navigate(buildNotificationOriginPath(record))}>IR AL ORIGEN</Button>
          {canResolve && record.can_resolve && !record.resuelta ? <Button disabled={Boolean(actionLoading)} onClick={() => handleResolve(record)}>RESOLVER</Button> : null}
          {canRetryEmail && !record.resuelta && record.tipo === 'ERROR_ENVIO_CORREO' ? (
            <Button disabled={Boolean(actionLoading)} loading={actionLoading === `retry:${record.id}`} icon={<ReloadOutlined />} onClick={() => handleRetryEmail(record)}>
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
        {canMarkAllRead && !isAdmin ? (
          <Button loading={actionLoading === 'read-all'} disabled={Boolean(actionLoading)} icon={<CheckOutlined />} onClick={handleMarkAllRead}>
            MARCAR TODAS MIS ALERTAS COMO LEÍDAS
          </Button>
        ) : null}
      </div>

      <Space wrap style={{ marginBottom: 16 }}>
        {canSupervise ? <Select aria-label="Ámbito de notificaciones" disabled={Boolean(actionLoading)} value={scope} style={{ width: 220 }}
          options={[{ value: 'personal', label: 'Mis notificaciones' }, { value: 'supervision', label: 'Supervisión de destinatarios' }]}
          onChange={(value) => { setScope(value); setPage(1); setDetailOpen(false); setDetail(null); detailGeneration.current += 1 }} /> : null}
        <Switch aria-label="Activar avisos de escritorio" checked={desktopEnabled} loading={preferenceLoading}
          onChange={changeDesktopPreference} />
        <Typography.Text>Avisos de escritorio opcionales</Typography.Text>
        <Button icon={<ReloadOutlined />} onClick={() => { loadNotifications(); loadReportSummary().catch(() => setError('No se pudo recargar el resumen.')) }}>Actualizar</Button>
      </Space>
      <Typography.Paragraph type="secondary">
        {isAdmin ? 'Supervisión global: las lecturas de otros destinatarios no se modifican desde esta vista.' : 'Las alertas por stock, fechas y fletes se cierran automáticamente al corregirse su condición. Leerlas no las resuelve.'}
        {' '}El escritorio avisa solo novedades recientes posteriores a su activación, con la aplicación abierta.
      </Typography.Paragraph>

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
              onChange={(value) => { setPage(1); setFilters((current) => ({ ...current, module: value })) }}
              style={{ width: '100%' }}
            />
          </Col>
          <Col xs={24} md={4}>
            <Select
              allowClear
              placeholder="TIPO"
              options={NOTIFICATION_TYPE_OPTIONS}
              value={filters.type}
              onChange={(value) => { setPage(1); setFilters((current) => ({ ...current, type: value })) }}
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
              onChange={(value) => { setPage(1); setFilters((current) => ({ ...current, priority: value })) }}
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
                onChange={(value) => { setPage(1); setFilters((current) => ({ ...current, role_code: value })) }}
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
                onChange={(value) => { setPage(1); setFilters((current) => ({ ...current, user_id: value })) }}
                style={{ width: '100%' }}
              />
            </Col>
          ) : null}
        </Row>
      </div>

      <Tabs
        activeKey={quickFilter}
        onChange={(value) => { setQuickFilter(value); setPage(1) }}
        items={QUICK_FILTERS.map((item) => ({ key: item.key, label: item.label }))}
        style={{ marginBottom: 12 }}
      />

      {error ? <Alert type="error" showIcon message={error} style={{ marginBottom: 16 }} /> : null}

      <Table
        className="glass-panel"
        rowKey="id"
        columns={columns}
        dataSource={notifications}
        loading={loading}
        pagination={{ current: page, pageSize, total, showSizeChanger: true, pageSizeOptions: [25, 50, 100],
          onChange: (nextPage, nextSize) => { setPage(nextSize !== pageSize ? 1 : nextPage); setPageSize(nextSize) } }}
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
          detailGeneration.current += 1
        }}
        maskClosable={false}
      >
        {detail ? (
          <>
            <Row gutter={[12, 12]} style={{ marginBottom: 16 }}>
              {!isAdmin && !detail.leida && !detail.resuelta ? (
                <Col>
                  <Button disabled={Boolean(actionLoading)} loading={actionLoading === `read:${detail.id}`} icon={<CheckOutlined />} onClick={() => handleMarkRead(detail)}>
                    Marcar como leída
                  </Button>
                </Col>
              ) : null}
              <Col>
                <Button icon={<LinkOutlined />} onClick={() => navigate(buildNotificationOriginPath(detail))}>
                  Ir al origen
                </Button>
              </Col>
              {canResolve && detail.can_resolve && !detail.resuelta ? (
                <Col>
                  <Button disabled={Boolean(actionLoading)} onClick={() => handleResolve(detail)}>Resolver</Button>
                </Col>
              ) : null}
              {canRetryEmail && !detail.resuelta && detail.tipo === 'ERROR_ENVIO_CORREO' ? (
                <Col>
                  <Button disabled={Boolean(actionLoading)} icon={<ReloadOutlined />} onClick={() => handleRetryEmail(detail)}>
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
