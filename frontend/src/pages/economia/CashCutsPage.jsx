import { EyeOutlined, LockOutlined, PlusOutlined } from '@ant-design/icons'
import {
  Alert,
  App as AntdApp,
  Button,
  Col,
  Checkbox,
  Descriptions,
  DatePicker,
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
import { useCallback, useEffect, useMemo, useRef, useState } from 'react'

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
  const mutationPending = useRef(false)
  const request = useRef(null)
  const usersLoaded = useRef(false)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState(null)
  const [cuts, setCuts] = useState([])
  const [pagination, setPagination] = useState({ current: 1, pageSize: 25, total: 0 })
  const { current: currentPage, pageSize } = pagination
  const [counts, setCounts] = useState({ open_count: 0, closed_count: 0, observed_count: 0 })
  const [filters, setFilters] = useState({ state: undefined, cashier_id: undefined, dates: null })
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
    request.current?.abort()
    const controller = new AbortController()
    request.current = controller
    setLoading(true)
    setError(null)
    const params = { page: currentPage, page_size: pageSize, state: filters.state, cashier_id: filters.cashier_id,
      date_from: filters.dates?.[0]?.format('YYYY-MM-DD'), date_to: filters.dates?.[1]?.format('YYYY-MM-DD') }
    try {
      if (isAdmin) {
        const [cutsResponse, usersResponse] = await Promise.all([
          apiClient.get('/economia/cortes-caja', { params, signal: controller.signal }),
          usersLoaded.current ? Promise.resolve(null) : apiClient.get('/users', { signal: controller.signal }),
        ])
        if (controller.signal.aborted) return
        setCuts(cutsResponse.data.items)
        setPagination((current) => ({ ...current, total: cutsResponse.data.total }))
        setCounts(cutsResponse.data)
        if (usersResponse) {
          setUsers(usersResponse.data.filter((item) => item.role_code === 'CAJA' && item.user_is_active && item.account_is_active))
          usersLoaded.current = true
        }
        setMyCut(null)
        setMyHistory([])
      } else {
        const [cutResponse, historyResponse] = await Promise.all([
          apiClient.get('/economia/cortes-caja/me', { signal: controller.signal }),
          apiClient.get('/economia/cortes-caja/me/history', { params: { page: currentPage, page_size: pageSize }, signal: controller.signal }),
        ])
        if (controller.signal.aborted) return
        setMyCut(cutResponse.data.cut)
        setMyHistory(historyResponse.data.items)
        setPagination((current) => ({ ...current, total: historyResponse.data.total }))
        setCuts([])
        setUsers([])
      }
    } catch (requestError) {
      if (controller.signal.aborted) return
      setError(requestError.response?.data?.detail || 'NO FUE POSIBLE CARGAR LOS CORTES DE CAJA.')
    } finally {
      if (!controller.signal.aborted) setLoading(false)
    }
  }, [isAdmin, currentPage, pageSize, filters])

  useEffect(() => {
    loadData()
    return () => request.current?.abort()
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
    if (mutationPending.current) return
    mutationPending.current = true
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
      mutationPending.current = false
      setSaving(false)
    }
  }

  const submitClose = async () => {
    if (mutationPending.current) return
    mutationPending.current = true
    setSaving(true)
    try {
      const values = await closeForm.validateFields()
      await apiClient.patch(`/economia/cortes-caja/${closeCutTarget.id}/close`, {
        ...values,
        efectivo_recibido: closeCutTarget.control_version > 0 ? values.efectivo_recibido : {},
        cierre_legado: closeCutTarget.control_version > 0 ? false : values.cierre_legado,
      })
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
      mutationPending.current = false
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
              <Button icon={<LockOutlined />} onClick={async () => {
                try {
                  const { data } = await apiClient.get(`/economia/cortes-caja/${record.id}`)
                  closeForm.resetFields()
                  setCloseCutTarget(data)
                } catch (failure) { message.error(failure.response?.data?.detail || 'NO FUE POSIBLE LEER EL CORTE ACTUAL.') }
              }}>
                CERRAR
              </Button>
            </Col>
          ) : null}
        </Row>
      ),
    },
  ]

  const historyColumns = [
    { title: 'TRAZABILIDAD', dataIndex: 'certified', render: (value) => <Tag color={value ? 'green' : 'default'}>{value ? 'CIERRE CONTROLADO' : 'LEGADO / INFORMATIVO'}</Tag> },
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
              : 'Consulta tu corte activo y tu historial propio de períodos cerrados.'}
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
              <EconomySummaryCard eyebrow="CORTE ACTIVO" title="Períodos abiertos" value={String(counts.open_count)} accent="#4d2219" />
            </Col>
            <Col xs={24} md={8}>
              <EconomySummaryCard eyebrow="CORTES CERRADOS" title="Cierres normales" value={String(counts.closed_count)} accent="#4b7f5a" />
            </Col>
            <Col xs={24} md={8}>
              <EconomySummaryCard eyebrow="CORTES OBSERVADOS" title="Cierres con observación" value={String(counts.observed_count)} accent="#b86c45" />
            </Col>
          </Row>
          <Row gutter={[12, 12]} style={{ marginBottom: 16 }}>
            <Col xs={24} md={7}><Select allowClear aria-label="Estado del corte" placeholder="ESTADO DEL CORTE" options={[{ value: 'abierto', label: 'ABIERTO' }, ...CIERRE_CORTE_OPTIONS]} value={filters.state} onChange={(state) => { setPagination((previous) => ({ ...previous, current: 1 })); setFilters((previous) => ({ ...previous, state })) }} style={{ width: '100%' }} /></Col>
            <Col xs={24} md={7}><Select allowClear showSearch optionFilterProp="label" aria-label="Cajero del corte" placeholder="CAJERO" options={cajeroOptions} value={filters.cashier_id} onChange={(cashier_id) => { setPagination((previous) => ({ ...previous, current: 1 })); setFilters((previous) => ({ ...previous, cashier_id })) }} style={{ width: '100%' }} /></Col>
            <Col xs={24} md={10}><DatePicker.RangePicker format="DD/MM/YYYY" value={filters.dates} onChange={(dates) => { setPagination((previous) => ({ ...previous, current: 1 })); setFilters((previous) => ({ ...previous, dates })) }} style={{ width: '100%' }} /></Col>
          </Row>
          <Table className="glass-panel" rowKey="id" columns={adminColumns} dataSource={cuts} loading={loading} pagination={{ ...pagination, showSizeChanger: true, pageSizeOptions: [25, 50, 100], onChange: (current, pageSize) => setPagination((previous) => ({ ...previous, current, pageSize })) }} scroll={{ x: 'max-content' }} />
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
          <Table className="glass-panel" rowKey="id" columns={historyColumns} dataSource={myHistory} loading={loading} pagination={{ ...pagination, showSizeChanger: true, pageSizeOptions: [25, 50, 100], onChange: (current, pageSize) => setPagination((previous) => ({ ...previous, current, pageSize })) }} scroll={{ x: 'max-content' }} />
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
              {closeCutTarget.control_version > 0 ? <>
                <Alert type="info" showIcon message={`EFECTIVO LIBRE BOB: ${formatBs(closeCutTarget.efectivo_libre_bob)} · GARANTÍAS RESERVADAS: ${formatBs(closeCutTarget.garantias_reservadas_bob)}`} description="Cuenta el efectivo físico por moneda, incluyendo dinero en custodia. Los cobros electrónicos no se entregan como efectivo." style={{ marginBottom: 16 }} />
                {Object.entries(closeCutTarget.efectivo_esperado || {}).map(([currency, expected]) => <Form.Item key={currency} name={['efectivo_recibido', currency]} label={`EFECTIVO RECIBIDO ${currency} (ESPERADO ${Number(expected).toFixed(2)})`} rules={[{ required: true, message: 'REGISTRA EL CONTEO REAL, INCLUSO SI ES CERO.' }]}>
                  <InputNumber min={0} precision={2} style={{ width: '100%' }} />
                </Form.Item>)}
                <Alert type="warning" message="CUALQUIER DIFERENCIA EXIGE CIERRE OBSERVADO Y EXPLICACIÓN." style={{ marginBottom: 16 }} />
              </> : <>
                <Alert type="warning" showIcon message="CORTE LEGADO: INFORMACIÓN HISTÓRICA NO CERTIFICADA" description="El cierre manual no reconstruye métodos de pago ni certifica conteos anteriores. Debe cerrarse antes de operar con los controles nuevos." style={{ marginBottom: 16 }} />
                <Form.Item name="cierre_legado" valuePropName="checked" rules={[{ validator: (_, value) => value ? Promise.resolve() : Promise.reject(new Error('CONFIRMA EL CIERRE LEGADO.')) }]}>
                  <Checkbox>CONFIRMO EL CIERRE MANUAL DEL CORTE LEGADO</Checkbox>
                </Form.Item>
              </>}
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
                rules={[{ required: !closeCutTarget.control_version, message: 'EXPLICA EL CIERRE LEGADO.' }]}
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
              <Descriptions.Item label="CERTIFICACIÓN">{detail.certified ? 'CIERRE CERTIFICADO' : detail.control_version > 0 ? 'CONTROL ACTUAL / ABIERTO' : 'LEGADO NO CERTIFICADO'}</Descriptions.Item>
              <Descriptions.Item label="EFECTIVO LIBRE BOB">{formatBs(detail.efectivo_libre_bob)}</Descriptions.Item>
              <Descriptions.Item label="GARANTÍAS RESERVADAS">{formatBs(detail.garantias_reservadas_bob)}</Descriptions.Item>
              <Descriptions.Item label="FONDO / ANTICIPO">{formatBs(detail.fondo_asignado)}</Descriptions.Item>
              <Descriptions.Item label="INGRESOS">{formatBs(detail.ingresos_total_bob)}</Descriptions.Item>
              <Descriptions.Item label="EGRESOS">{formatBs(detail.egresos_total_bob)}</Descriptions.Item>
              <Descriptions.Item label="RESULTADO">{formatBs(detail.resultado_bob)}</Descriptions.Item>
              <Descriptions.Item label="OBS. APERTURA" span={2}>{detail.observaciones_apertura || 'SIN OBSERVACIÓN'}</Descriptions.Item>
              <Descriptions.Item label="OBS. CIERRE" span={2}>{detail.observaciones_cierre || 'SIN OBSERVACIÓN'}</Descriptions.Item>
            </Descriptions>
            <Table
              rowKey="currency" size="small" pagination={false}
              dataSource={Object.entries(detail.efectivo_esperado || {}).map(([currency, expected]) => ({ currency, expected, received: detail.efectivo_recibido?.[currency], difference: detail.diferencias_efectivo?.[currency] }))}
              columns={[{ title: 'MONEDA FÍSICA', dataIndex: 'currency' }, { title: 'ESPERADO', dataIndex: 'expected' }, { title: 'RECIBIDO', dataIndex: 'received' }, { title: 'DIFERENCIA', dataIndex: 'difference' }]}
              style={{ marginBottom: 16 }}
            />
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
