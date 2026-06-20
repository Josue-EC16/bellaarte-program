/* eslint-disable react/prop-types */
import {
  CheckCircleOutlined,
  ClockCircleOutlined,
  DatabaseOutlined,
  DownloadOutlined,
  EyeOutlined,
  ReloadOutlined,
  SearchOutlined,
} from '@ant-design/icons'
import {
  Alert,
  App as AntdApp,
  Button,
  Card,
  Col,
  DatePicker,
  Descriptions,
  Drawer,
  Input,
  Modal,
  Row,
  Select,
  Space,
  Spin,
  Table,
  Tag,
  Typography,
} from 'antd'
import { useCallback, useEffect, useMemo, useState } from 'react'

import { apiClient } from '../../api/client'
import {
  BACKUP_ORIGIN_OPTIONS,
  BACKUP_STATE_OPTIONS,
  BACKUP_TYPE_OPTIONS,
  backupOriginLabel,
  backupStateColor,
  backupTypeLabel,
  downloadBackupFile,
  formatBackupDate,
  formatBytes,
  shortenHash,
} from './backupUtils'

const { RangePicker } = DatePicker

function SummaryCard({ title, value, subtitle, icon, accent }) {
  return (
    <Card
      styles={{ body: { padding: 18 } }}
      style={{
        borderRadius: 22,
        border: `1px solid ${accent}22`,
        background: `linear-gradient(135deg, ${accent}18, rgba(255,255,255,0.92))`,
        boxShadow: '0 22px 60px rgba(111, 76, 49, 0.08)',
      }}
    >
      <Space align="start" size={14}>
        <div
          style={{
            width: 42,
            height: 42,
            borderRadius: 14,
            display: 'grid',
            placeItems: 'center',
            background: `${accent}18`,
            color: accent,
            fontSize: 18,
          }}
        >
          {icon}
        </div>
        <div>
          <Typography.Text type="secondary">{title}</Typography.Text>
          <Typography.Title level={4} style={{ margin: '6px 0 4px', color: accent }}>
            {value}
          </Typography.Title>
          <Typography.Text type="secondary" style={{ fontSize: 12 }}>
            {subtitle}
          </Typography.Text>
        </div>
      </Space>
    </Card>
  )
}

export function BackupsPage() {
  const [backups, setBackups] = useState([])
  const [users, setUsers] = useState([])
  const [loading, setLoading] = useState(true)
  const [runningBackup, setRunningBackup] = useState(false)
  const [detailLoading, setDetailLoading] = useState(false)
  const [error, setError] = useState(null)
  const [detail, setDetail] = useState(null)
  const [detailOpen, setDetailOpen] = useState(false)
  const [activeStatus, setActiveStatus] = useState({ active: false })
  const [filters, setFilters] = useState({
    search: '',
    tipo: undefined,
    estado: undefined,
    origen: undefined,
    usuario_id: undefined,
    date_from: undefined,
    date_to: undefined,
  })
  const { message } = AntdApp.useApp()

  const queryParams = useMemo(() => {
    const params = {}
    Object.entries(filters).forEach(([key, value]) => {
      if (value !== undefined && value !== null && value !== '') {
        params[key] = value
      }
    })
    return params
  }, [filters])

  const loadBackups = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const response = await apiClient.get('/backups', { params: queryParams })
      setBackups(response.data)
    } catch (requestError) {
      setError(requestError.response?.data?.detail || 'NO FUE POSIBLE CARGAR EL HISTORIAL DE BACKUPS.')
    } finally {
      setLoading(false)
    }
  }, [queryParams])

  const loadActiveStatus = useCallback(async () => {
    try {
      const response = await apiClient.get('/backups/status/active')
      setActiveStatus(response.data)
    } catch {
      setActiveStatus({ active: false })
    }
  }, [])

  const loadUsers = useCallback(async () => {
    try {
      const response = await apiClient.get('/users')
      setUsers(response.data)
    } catch {
      setUsers([])
    }
  }, [])

  const reloadPage = useCallback(async () => {
    await Promise.all([loadBackups(), loadActiveStatus(), loadUsers()])
  }, [loadActiveStatus, loadBackups, loadUsers])

  useEffect(() => {
    reloadPage().catch(() => {
      setError('NO FUE POSIBLE INICIALIZAR EL MÓDULO DE BACKUPS.')
      setLoading(false)
    })
  }, [reloadPage])

  useEffect(() => {
    if (!activeStatus.active && !runningBackup) return undefined
    const intervalId = window.setInterval(() => {
      loadActiveStatus()
      loadBackups()
    }, 8000)
    return () => window.clearInterval(intervalId)
  }, [activeStatus.active, loadActiveStatus, loadBackups, runningBackup])

  const openDetail = useCallback(async (backupId) => {
    setDetailLoading(true)
    try {
      const response = await apiClient.get(`/backups/${backupId}`)
      setDetail(response.data)
      setDetailOpen(true)
    } catch (requestError) {
      message.error(requestError.response?.data?.detail || 'NO FUE POSIBLE CARGAR EL DETALLE DEL BACKUP.')
    } finally {
      setDetailLoading(false)
    }
  }, [message])

  const handleRunBackup = useCallback(async () => {
    setRunningBackup(true)
    try {
      const response = await apiClient.post('/backups/run')
      message.success(response.data.message || 'BACKUP GENERADO CORRECTAMENTE.')
      setDetail(response.data)
      setDetailOpen(true)
      await reloadPage()
    } catch (requestError) {
      message.error(requestError.response?.data?.detail || 'NO FUE POSIBLE GENERAR EL BACKUP.')
      await loadActiveStatus()
    } finally {
      setRunningBackup(false)
    }
  }, [loadActiveStatus, message, reloadPage])

  const handleVerifyFile = useCallback(async (backupId) => {
    try {
      const response = await apiClient.get(`/backups/${backupId}/check-file`)
      if (response.data.exists) {
        message.success(`EL ARCHIVO EXISTE Y MIDE ${formatBytes(response.data.tamano_actual_bytes)}.`)
      } else {
        message.error('EL ARCHIVO YA NO EXISTE EN EL ALMACENAMIENTO.')
      }
      if (detail?.id === backupId) {
        const detailResponse = await apiClient.get(`/backups/${backupId}`)
        setDetail(detailResponse.data)
      }
      await loadBackups()
    } catch (requestError) {
      message.error(requestError.response?.data?.detail || 'NO FUE POSIBLE VERIFICAR EL ARCHIVO DEL BACKUP.')
    }
  }, [detail?.id, loadBackups, message])

  const handleDownload = useCallback(async (backupId) => {
    try {
      await downloadBackupFile(backupId)
      message.success('LA DESCARGA DEL BACKUP SE INICIÓ CORRECTAMENTE.')
      await loadBackups()
    } catch (requestError) {
      message.error(requestError.response?.data?.detail || 'NO FUE POSIBLE DESCARGAR EL BACKUP.')
    }
  }, [loadBackups, message])

  const userOptions = useMemo(
    () =>
      users.map((item) => ({
        value: item.user_id,
        label: item.full_name,
      })),
    [users],
  )

  const summary = useMemo(() => {
    const latestSuccessful = backups.find((item) => item.estado === 'EXITOSO') || null
    const latestFailed = backups.find((item) => item.estado === 'FALLIDO') || null
    return {
      total: backups.length,
      latestSuccessful,
      latestFailed,
    }
  }, [backups])

  const columns = [
    {
      title: 'ID',
      dataIndex: 'id',
      key: 'id',
      width: 90,
    },
    {
      title: 'TIPO',
      dataIndex: 'tipo',
      key: 'tipo',
      render: backupTypeLabel,
    },
    {
      title: 'ORIGEN',
      dataIndex: 'origen',
      key: 'origen',
      render: backupOriginLabel,
    },
    {
      title: 'ESTADO',
      dataIndex: 'estado',
      key: 'estado',
      render: (value) => <Tag color={backupStateColor(value)}>{value}</Tag>,
    },
    {
      title: 'ARCHIVO',
      dataIndex: 'nombre_archivo',
      key: 'nombre_archivo',
      render: (value) => <Typography.Text ellipsis={{ tooltip: value }}>{value}</Typography.Text>,
    },
    {
      title: 'TAMAÑO',
      dataIndex: 'tamano_bytes',
      key: 'tamano_bytes',
      render: formatBytes,
    },
    {
      title: 'HASH',
      dataIndex: 'hash_sha256',
      key: 'hash_sha256',
      render: shortenHash,
    },
    {
      title: 'USUARIO',
      dataIndex: 'usuario',
      key: 'usuario',
      render: (value) => value?.full_name || 'SISTEMA',
    },
    {
      title: 'INICIO',
      dataIndex: 'fecha_inicio',
      key: 'fecha_inicio',
      render: formatBackupDate,
    },
    {
      title: 'FIN',
      dataIndex: 'fecha_fin',
      key: 'fecha_fin',
      render: formatBackupDate,
    },
    {
      title: 'ARCHIVO DISPONIBLE',
      dataIndex: 'file_exists',
      key: 'file_exists',
      render: (value) => <Tag color={value ? 'green' : 'red'}>{value ? 'SÍ' : 'NO'}</Tag>,
    },
    {
      title: 'ACCIONES',
      key: 'acciones',
      fixed: 'right',
      render: (_, record) => (
        <Space wrap>
          <Button icon={<EyeOutlined />} onClick={() => openDetail(record.id)}>
            VER
          </Button>
          <Button onClick={() => handleVerifyFile(record.id)}>VERIFICAR</Button>
          <Button
            icon={<DownloadOutlined />}
            disabled={record.estado !== 'EXITOSO' || !record.file_exists}
            onClick={() => handleDownload(record.id)}
          >
            DESCARGAR
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
            Backups de Base de Datos
          </Typography.Title>
          <Typography.Paragraph type="secondary" style={{ marginBottom: 0 }}>
            Gestión administrativa de respaldos completos vía PG_DUMP con historial, verificación y descarga segura.
          </Typography.Paragraph>
        </div>
        <Space wrap>
          <Button icon={<ReloadOutlined />} onClick={reloadPage}>
            RECARGAR
          </Button>
          <Button
            type="primary"
            icon={<DatabaseOutlined />}
            loading={runningBackup}
            disabled={activeStatus.active}
            onClick={handleRunBackup}
          >
            GENERAR BACKUP AHORA
          </Button>
        </Space>
      </div>

      {activeStatus.active ? (
        <Alert
          type="warning"
          showIcon
          style={{ marginBottom: 16 }}
          message={activeStatus.message || 'HAY UN BACKUP EN PROCESO.'}
          description={
            activeStatus.backup_id
              ? `BACKUP EN PROCESO #${activeStatus.backup_id}${activeStatus.origen ? ` - ${activeStatus.origen}` : ''}`
              : 'EL SISTEMA SE ENCUENTRA TEMPORALMENTE BLOQUEADO POR SEGURIDAD MIENTRAS FINALIZA EL RESPALDO.'
          }
        />
      ) : null}

      {error ? <Alert type="error" showIcon style={{ marginBottom: 16 }} message={error} /> : null}

      <Row gutter={[14, 14]} style={{ marginBottom: 18 }}>
        <Col xs={24} sm={12} xl={8}>
          <SummaryCard
            title="TOTAL GENERADOS"
            value={summary.total}
            subtitle="HISTORIAL VISIBLE SEGÚN FILTROS APLICADOS"
            icon={<DatabaseOutlined />}
            accent="#6f4c31"
          />
        </Col>
        <Col xs={24} sm={12} xl={8}>
          <SummaryCard
            title="ÚLTIMO EXITOSO"
            value={summary.latestSuccessful ? `#${summary.latestSuccessful.id}` : 'SIN REGISTRO'}
            subtitle={summary.latestSuccessful ? formatBackupDate(summary.latestSuccessful.fecha_fin || summary.latestSuccessful.fecha_inicio) : 'TODAVÍA NO HAY RESPALDOS EXITOSOS'}
            icon={<CheckCircleOutlined />}
            accent="#4f7f4f"
          />
        </Col>
        <Col xs={24} sm={12} xl={8}>
          <SummaryCard
            title="ÚLTIMO FALLIDO"
            value={summary.latestFailed ? `#${summary.latestFailed.id}` : 'SIN REGISTRO'}
            subtitle={summary.latestFailed ? formatBackupDate(summary.latestFailed.fecha_fin || summary.latestFailed.fecha_inicio) : 'SIN FALLAS REGISTRADAS'}
            icon={<ClockCircleOutlined />}
            accent="#b8475c"
          />
        </Col>
      </Row>

      <div className="glass-panel boutique-filter-bar">
        <Row gutter={[12, 12]}>
          <Col xs={24} md={6}>
            <Input
              allowClear
              prefix={<SearchOutlined />}
              placeholder="BUSCAR ARCHIVO, HASH O ERROR"
              value={filters.search}
              onChange={(event) => setFilters((current) => ({ ...current, search: event.target.value.toUpperCase() }))}
            />
          </Col>
          <Col xs={24} md={4}>
            <Select
              allowClear
              placeholder="TIPO"
              options={BACKUP_TYPE_OPTIONS}
              value={filters.tipo}
              onChange={(value) => setFilters((current) => ({ ...current, tipo: value }))}
              style={{ width: '100%' }}
            />
          </Col>
          <Col xs={24} md={4}>
            <Select
              allowClear
              placeholder="ESTADO"
              options={BACKUP_STATE_OPTIONS}
              value={filters.estado}
              onChange={(value) => setFilters((current) => ({ ...current, estado: value }))}
              style={{ width: '100%' }}
            />
          </Col>
          <Col xs={24} md={4}>
            <Select
              allowClear
              placeholder="ORIGEN"
              options={BACKUP_ORIGIN_OPTIONS}
              value={filters.origen}
              onChange={(value) => setFilters((current) => ({ ...current, origen: value }))}
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
              value={filters.usuario_id}
              onChange={(value) => setFilters((current) => ({ ...current, usuario_id: value }))}
              style={{ width: '100%' }}
            />
          </Col>
          <Col xs={24} md={6}>
            <RangePicker
              format="DD/MM/YYYY"
              style={{ width: '100%' }}
              onChange={(dates) =>
                setFilters((current) => ({
                  ...current,
                  date_from: dates?.[0] ? dates[0].format('YYYY-MM-DD') : undefined,
                  date_to: dates?.[1] ? dates[1].format('YYYY-MM-DD') : undefined,
                }))
              }
            />
          </Col>
        </Row>
      </div>

      <Table
        className="glass-panel"
        rowKey="id"
        columns={columns}
        dataSource={backups}
        loading={loading}
        pagination={{ pageSize: 8 }}
        scroll={{ x: 1400 }}
        style={{ borderRadius: 24, overflow: 'hidden' }}
      />

      <Drawer
        title="Detalle del Backup"
        width={980}
        open={detailOpen}
        onClose={() => {
          setDetailOpen(false)
          setDetail(null)
        }}
        maskClosable={false}
      >
        {detailLoading ? (
          <div style={{ padding: 24, textAlign: 'center' }}>
            <Spin />
          </div>
        ) : detail ? (
          <>
            <Row gutter={[12, 12]} style={{ marginBottom: 16 }}>
              <Col>
                <Button onClick={() => handleVerifyFile(detail.id)}>VERIFICAR ARCHIVO</Button>
              </Col>
              <Col>
                <Button
                  type="primary"
                  icon={<DownloadOutlined />}
                  disabled={detail.estado !== 'EXITOSO' || !detail.file_exists}
                  onClick={() => handleDownload(detail.id)}
                >
                  DESCARGAR BACKUP
                </Button>
              </Col>
            </Row>

            <Descriptions bordered size="small" column={2}>
              <Descriptions.Item label="ID">#{detail.id}</Descriptions.Item>
              <Descriptions.Item label="ESTADO">
                <Tag color={backupStateColor(detail.estado)}>{detail.estado}</Tag>
              </Descriptions.Item>
              <Descriptions.Item label="TIPO">{backupTypeLabel(detail.tipo)}</Descriptions.Item>
              <Descriptions.Item label="ORIGEN">{backupOriginLabel(detail.origen)}</Descriptions.Item>
              <Descriptions.Item label="USUARIO">{detail.usuario?.full_name || 'SISTEMA'}</Descriptions.Item>
              <Descriptions.Item label="ARCHIVO DISPONIBLE">
                <Tag color={detail.file_exists ? 'green' : 'red'}>{detail.file_exists ? 'SÍ' : 'NO'}</Tag>
              </Descriptions.Item>
              <Descriptions.Item label="FECHA INICIO">{formatBackupDate(detail.fecha_inicio)}</Descriptions.Item>
              <Descriptions.Item label="FECHA FIN">{formatBackupDate(detail.fecha_fin)}</Descriptions.Item>
              <Descriptions.Item label="NOMBRE ARCHIVO" span={2}>
                {detail.nombre_archivo}
              </Descriptions.Item>
              <Descriptions.Item label="RUTA ARCHIVO" span={2}>
                <Typography.Text copyable>{detail.ruta_archivo}</Typography.Text>
              </Descriptions.Item>
              <Descriptions.Item label="TAMAÑO">{formatBytes(detail.tamano_bytes)}</Descriptions.Item>
              <Descriptions.Item label="BASE DE DATOS">{detail.db_nombre || 'SIN REGISTRO'}</Descriptions.Item>
              <Descriptions.Item label="SHA-256" span={2}>
                <Typography.Text copyable>{detail.hash_sha256 || 'SIN HASH'}</Typography.Text>
              </Descriptions.Item>
              <Descriptions.Item label="VERSIÓN PG_DUMP" span={2}>
                {detail.pg_dump_version || 'SIN REGISTRO'}
              </Descriptions.Item>
              <Descriptions.Item label="OBSERVACIÓN" span={2}>
                {detail.observacion || 'SIN OBSERVACIÓN'}
              </Descriptions.Item>
              <Descriptions.Item label="ERROR" span={2}>
                {detail.error || 'SIN ERROR'}
              </Descriptions.Item>
            </Descriptions>
          </>
        ) : null}
      </Drawer>

      <Modal open={runningBackup} footer={null} closable={false} maskClosable={false} centered>
        <div style={{ textAlign: 'center', padding: '24px 8px' }}>
          <Spin size="large" />
          <Typography.Title level={4} style={{ marginTop: 18, marginBottom: 8 }}>
            ESPERA HASTA QUE TERMINE DE GENERAR EL BACKUP
          </Typography.Title>
          <Typography.Paragraph type="secondary" style={{ marginBottom: 0 }}>
            EL SISTEMA ESTÁ TEMPORALMENTE BLOQUEADO POR SEGURIDAD MIENTRAS SE CREA EL RESPALDO COMPLETO DE LA BASE DE DATOS.
          </Typography.Paragraph>
        </div>
      </Modal>
    </div>
  )
}
