import { EyeOutlined, LockOutlined, PlusOutlined } from '@ant-design/icons'
import {
  Alert,
  App as AntdApp,
  Button,
  Col,
  Descriptions,
  Drawer,
  Form,
  Input,
  InputNumber,
  Row,
  Select,
  Table,
  Tag,
  Typography,
} from 'antd'
import { useCallback, useEffect, useMemo, useState } from 'react'

import { apiClient } from '../../api/client'
import { useAuth } from '../../auth/AuthProvider'
import { FORM_COMMON_PROPS, FORM_DRAWER_SUBMIT_PROPS } from '../../components/forms/formConfig'
import { applyFormApiError } from '../../components/forms/formErrorUtils'
import { FormProcessAlert } from '../../components/forms/FormProcessAlert'
import { EconomySummaryCard } from './EconomySummaryCard'
import { CIERRE_CORTE_OPTIONS } from './economyConstants'
import { cutStateColor, cutStateLabel, expenseTypeLabel, formatBs } from './economyUtils'

export function CashCutsPage() {
  const { user } = useAuth()
  const { message } = AntdApp.useApp()
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState(null)
  const [cuts, setCuts] = useState([])
  const [users, setUsers] = useState([])
  const [myCut, setMyCut] = useState(null)
  const [myHistory, setMyHistory] = useState([])
  const [detail, setDetail] = useState(null)
  const [openCreate, setOpenCreate] = useState(false)
  const [closeCutTarget, setCloseCutTarget] = useState(null)
  const [formError, setFormError] = useState(null)
  const [form] = Form.useForm()
  const [closeForm] = Form.useForm()

  const isAdmin = user?.role_code === 'ADMIN'

  const loadData = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      if (isAdmin) {
        const [cutsResponse, usersResponse] = await Promise.all([
          apiClient.get('/economia/cortes-caja'),
          apiClient.get('/users'),
        ])
        setCuts(cutsResponse.data)
        setUsers(usersResponse.data.filter((item) => item.role_code === 'CAJA' && item.is_active))
        setMyCut(null)
        setMyHistory([])
      } else {
        const [cutResponse, historyResponse] = await Promise.all([
          apiClient.get('/economia/cortes-caja/me'),
          apiClient.get('/economia/cortes-caja/me/history'),
        ])
        setMyCut(cutResponse.data.cut)
        setMyHistory(historyResponse.data)
        setCuts([])
        setUsers([])
      }
    } catch (requestError) {
      setError(requestError.response?.data?.detail || 'NO FUE POSIBLE CARGAR LOS CORTES DE CAJA.')
    } finally {
      setLoading(false)
    }
  }, [isAdmin])

  useEffect(() => {
    loadData()
  }, [loadData])

  const cajeroOptions = useMemo(
    () => users.map((item) => ({ label: `${item.full_name} (${item.username})`, value: item.user_id })),
    [users],
  )

  const openCutDetail = async (cutId) => {
    try {
      const response = await apiClient.get(`/economia/cortes-caja/${cutId}`)
      setDetail(response.data)
    } catch (requestError) {
      message.error(requestError.response?.data?.detail || 'NO FUE POSIBLE CARGAR EL DETALLE DEL CORTE.')
    }
  }

  const submitCreate = async (values) => {
    setSaving(true)
    setFormError(null)
    try {
      await apiClient.post('/economia/cortes-caja', values)
      message.success('SE ABRIÓ EL CORTE DE CAJA CORRECTAMENTE.')
      setOpenCreate(false)
      form.resetFields()
      await loadData()
    } catch (requestError) {
      const resolved = applyFormApiError(form, requestError, {
        fallbackGlobalMessage: 'NO FUE POSIBLE ABRIR EL CORTE DE CAJA.',
      })
      setFormError(resolved.globalMessage)
    } finally {
      setSaving(false)
    }
  }

  const submitClose = async () => {
    setSaving(true)
    try {
      const values = await closeForm.validateFields()
      await apiClient.patch(`/economia/cortes-caja/${closeCutTarget.id}/close`, values)
      message.success('SE CERRÓ EL CORTE DE CAJA CORRECTAMENTE.')
      setCloseCutTarget(null)
      closeForm.resetFields()
      if (detail?.id === closeCutTarget.id) {
        const response = await apiClient.get(`/economia/cortes-caja/${closeCutTarget.id}`)
        setDetail(response.data)
      }
      await loadData()
    } catch (requestError) {
      if (requestError?.errorFields) {
        setSaving(false)
        return
      }
      message.error(requestError.response?.data?.detail || 'NO FUE POSIBLE CERRAR EL CORTE DE CAJA.')
    } finally {
      setSaving(false)
    }
  }

  const adminColumns = [
    { title: 'CORTE', dataIndex: 'id', render: (value) => `#${value}` },
    { title: 'CAJERO', key: 'cajero', render: (_, record) => record.cajero.full_name },
    { title: 'ADMIN', key: 'admin', render: (_, record) => record.admin.full_name },
    { title: 'APERTURA', dataIndex: 'fecha_apertura', render: (value) => new Date(value).toLocaleString('es-BO') },
    { title: 'ESTADO', dataIndex: 'estado', render: (value) => <Tag color={cutStateColor(value)}>{cutStateLabel(value)}</Tag> },
    { title: 'FONDO', dataIndex: 'fondo_asignado', render: formatBs },
    { title: 'INGRESOS', dataIndex: 'ingresos_total_bob', render: formatBs },
    { title: 'EGRESOS', dataIndex: 'egresos_total_bob', render: formatBs },
    { title: 'RESULTADO', dataIndex: 'resultado_bob', render: formatBs },
    {
      title: 'ACCIONES',
      key: 'actions',
      render: (_, record) => (
        <Row gutter={[8, 8]}>
          <Col>
            <Button icon={<EyeOutlined />} onClick={() => openCutDetail(record.id)}>
              VER
            </Button>
          </Col>
          {record.estado === 'abierto' ? (
            <Col>
              <Button icon={<LockOutlined />} onClick={() => { setCloseCutTarget(record); closeForm.resetFields(); }}>
                CERRAR
              </Button>
            </Col>
          ) : null}
        </Row>
      ),
    },
  ]

  const historyColumns = [
    { title: 'CORTE', dataIndex: 'id', render: (value) => `#${value}` },
    { title: 'APERTURA', dataIndex: 'fecha_apertura', render: (value) => new Date(value).toLocaleString('es-BO') },
    { title: 'CIERRE', dataIndex: 'fecha_cierre', render: (value) => (value ? new Date(value).toLocaleString('es-BO') : 'PENDIENTE') },
    { title: 'ESTADO', dataIndex: 'estado', render: (value) => <Tag color={cutStateColor(value)}>{cutStateLabel(value)}</Tag> },
    { title: 'INGRESOS', dataIndex: 'ingresos_display' },
    { title: 'VENTAS', dataIndex: 'ventas_display' },
    { title: 'PAGOS', dataIndex: 'pagos_display' },
    { title: 'FLETES', dataIndex: 'fletes_display' },
    { title: 'RESULTADO', dataIndex: 'resultado_display' },
    { title: 'EGRESOS', dataIndex: 'egresos_total_bob', render: formatBs },
  ]

  return (
    <div>
      <div className="page-header">
        <div>
          <Typography.Title level={2} style={{ margin: 0 }}>
            Cortes de Caja
          </Typography.Title>
          <Typography.Paragraph type="secondary" style={{ marginBottom: 0 }}>
            {isAdmin
              ? 'Abre, cierra y supervisa períodos operativos de caja por cajero.'
              : 'Consulta tu corte activo y tu historial enmascarado de períodos cerrados.'}
          </Typography.Paragraph>
        </div>
        {isAdmin ? (
          <Button type="primary" icon={<PlusOutlined />} onClick={() => { setFormError(null); form.resetFields(); setOpenCreate(true) }}>
            Abrir corte
          </Button>
        ) : null}
      </div>

      {error ? <Alert type="error" showIcon message={error} style={{ marginBottom: 16 }} /> : null}

      {isAdmin ? (
        <>
          <Row gutter={[14, 14]} style={{ marginBottom: 16 }}>
            <Col xs={24} md={8}>
              <EconomySummaryCard eyebrow="CORTE ACTIVO" title="Períodos abiertos" value={String(cuts.filter((item) => item.estado === 'abierto').length)} accent="#4d2219" />
            </Col>
            <Col xs={24} md={8}>
              <EconomySummaryCard eyebrow="INGRESOS VISIBLES" title="Suma de ingresos por corte" value={formatBs(cuts.reduce((acc, item) => acc + Number(item.ingresos_total_bob || 0), 0))} accent="#4b7f5a" />
            </Col>
            <Col xs={24} md={8}>
              <EconomySummaryCard eyebrow="RESULTADO GLOBAL" title="Suma de resultados" value={formatBs(cuts.reduce((acc, item) => acc + Number(item.resultado_bob || 0), 0))} accent="#b86c45" />
            </Col>
          </Row>
          <Table className="glass-panel" rowKey="id" columns={adminColumns} dataSource={cuts} loading={loading} scroll={{ x: 'max-content' }} />
        </>
      ) : (
        <>
          <Row gutter={[14, 14]} style={{ marginBottom: 16 }}>
            <Col xs={24} md={12}>
              <EconomySummaryCard
                eyebrow="MI CORTE ACTIVO"
                title={myCut ? `CORTE #${myCut.id}` : 'SIN CORTE ABIERTO'}
                value={myCut ? cutStateLabel(myCut.estado) : 'NO DISPONIBLE'}
                accent={myCut ? '#4b7f5a' : '#b86c45'}
                helper={myCut ? `FONDO ASIGNADO ${formatBs(myCut.fondo_asignado)}` : 'EL ADMIN DEBE ABRIR TU CORTE PARA EMPEZAR A OPERAR.'}
              />
            </Col>
          </Row>
          <Table className="glass-panel" rowKey="id" columns={historyColumns} dataSource={myHistory} loading={loading} scroll={{ x: 'max-content' }} />
        </>
      )}

      <Drawer
        title="Abrir corte de caja"
        width={620}
        open={openCreate}
        onClose={() => {
          setOpenCreate(false)
          setFormError(null)
          form.resetFields()
        }}
        maskClosable={false}
      >
        <Form {...FORM_COMMON_PROPS} form={form} onFinish={submitCreate}>
          <FormProcessAlert message={formError} />
          <Row gutter={12}>
            <Col span={24}>
              <Form.Item
                label="CAJERO"
                name="cajero_id"
                rules={[{ required: true, message: 'DEBE SELECCIONAR EL CAJERO.' }]}
              >
                <Select
                  showSearch
                  optionFilterProp="label"
                  options={cajeroOptions}
                  placeholder="SELECCIONA EL USUARIO CAJA"
                />
              </Form.Item>
            </Col>
            <Col span={24}>
              <Form.Item label="FONDO ASIGNADO" name="fondo_asignado" initialValue={0}>
                <InputNumber min={0} precision={2} style={{ width: '100%' }} placeholder="EJ. 100.00" />
              </Form.Item>
            </Col>
            <Col span={24}>
              <Form.Item label="OBSERVACIONES DE APERTURA" name="observaciones_apertura" normalize={(value) => (value || '').toUpperCase()}>
                <Input.TextArea rows={3} placeholder="DETALLE CUALQUIER ACLARACIÓN DEL PERÍODO" />
              </Form.Item>
            </Col>
          </Row>
          <Row justify="end" gutter={12}>
            <Col><Button onClick={() => setOpenCreate(false)}>CANCELAR</Button></Col>
            <Col><Button type="primary" htmlType="submit" loading={saving} {...FORM_DRAWER_SUBMIT_PROPS}>ABRIR CORTE</Button></Col>
          </Row>
        </Form>
      </Drawer>

      <Drawer
        title="Cerrar corte de caja"
        width={580}
        open={Boolean(closeCutTarget)}
        onClose={() => {
          setCloseCutTarget(null)
          closeForm.resetFields()
        }}
        maskClosable={false}
      >
        {closeCutTarget ? (
          <>
            <Alert
              type="warning"
              showIcon
              style={{ marginBottom: 16 }}
              message={`SE CERRARÁ EL CORTE #${closeCutTarget.id}.`}
              description="UNA VEZ CERRADO, EL PERÍODO YA NO DEBE SEGUIR RECIBIENDO EGRESOS OPERATIVOS DEL CAJERO."
            />
            <Form {...FORM_COMMON_PROPS} form={closeForm} onFinish={submitClose}>
              <Form.Item
                label="ESTADO DE CIERRE"
                name="estado"
                rules={[{ required: true, message: 'DEBE SELECCIONAR EL ESTADO DE CIERRE.' }]}
              >
                <Select options={CIERRE_CORTE_OPTIONS} placeholder="SELECCIONA EL TIPO DE CIERRE" />
              </Form.Item>
              <Form.Item
                label="OBSERVACIONES DE CIERRE"
                name="observaciones_cierre"
                normalize={(value) => (value || '').toUpperCase()}
              >
                <Input.TextArea rows={3} placeholder="OBLIGATORIO SI EL CIERRE ES OBSERVADO" />
              </Form.Item>
              <Row justify="end" gutter={12}>
                <Col><Button onClick={() => setCloseCutTarget(null)}>CANCELAR</Button></Col>
                <Col><Button type="primary" htmlType="submit" loading={saving} {...FORM_DRAWER_SUBMIT_PROPS}>CERRAR CORTE</Button></Col>
              </Row>
            </Form>
          </>
        ) : null}
      </Drawer>

      <Drawer
        title="Detalle del corte"
        width={860}
        open={Boolean(detail)}
        onClose={() => setDetail(null)}
        maskClosable={false}
      >
        {detail ? (
          <>
            <Descriptions bordered column={2} size="small" style={{ marginBottom: 16 }}>
              <Descriptions.Item label="CORTE">#{detail.id}</Descriptions.Item>
              <Descriptions.Item label="ESTADO">
                <Tag color={cutStateColor(detail.estado)}>{cutStateLabel(detail.estado)}</Tag>
              </Descriptions.Item>
              <Descriptions.Item label="CAJERO">{detail.cajero.full_name}</Descriptions.Item>
              <Descriptions.Item label="ADMIN">{detail.admin.full_name}</Descriptions.Item>
              <Descriptions.Item label="APERTURA">{new Date(detail.fecha_apertura).toLocaleString('es-BO')}</Descriptions.Item>
              <Descriptions.Item label="CIERRE">{detail.fecha_cierre ? new Date(detail.fecha_cierre).toLocaleString('es-BO') : 'PENDIENTE'}</Descriptions.Item>
              <Descriptions.Item label="FONDO">{formatBs(detail.fondo_asignado)}</Descriptions.Item>
              <Descriptions.Item label="INGRESOS">{formatBs(detail.ingresos_total_bob)}</Descriptions.Item>
              <Descriptions.Item label="EGRESOS">{formatBs(detail.egresos_total_bob)}</Descriptions.Item>
              <Descriptions.Item label="RESULTADO">{formatBs(detail.resultado_bob)}</Descriptions.Item>
              <Descriptions.Item label="OBS. APERTURA" span={2}>{detail.observaciones_apertura || 'SIN OBSERVACIÓN'}</Descriptions.Item>
              <Descriptions.Item label="OBS. CIERRE" span={2}>{detail.observaciones_cierre || 'SIN OBSERVACIÓN'}</Descriptions.Item>
            </Descriptions>
            <Table
              rowKey="id"
              pagination={false}
              size="small"
              dataSource={detail.egresos}
              columns={[
                { title: 'FECHA', dataIndex: 'fecha', render: (value) => new Date(value).toLocaleString('es-BO') },
                { title: 'TIPO', dataIndex: 'tipo', render: expenseTypeLabel },
                { title: 'CONCEPTO', dataIndex: 'concepto' },
                { title: 'MONTO', dataIndex: 'monto', render: formatBs },
              ]}
            />
          </>
        ) : null}
      </Drawer>
    </div>
  )
}
