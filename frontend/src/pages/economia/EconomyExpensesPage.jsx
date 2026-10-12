import {
  CloseCircleOutlined,
  DollarOutlined,
  EyeOutlined,
  ReloadOutlined,
  SearchOutlined,
} from '@ant-design/icons'
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
import { useLocation, useNavigate, useSearchParams } from 'react-router-dom'

import { apiClient } from '../../api/client'
import { useAuth } from '../../auth/AuthProvider'
import { FORM_COMMON_PROPS, FORM_DRAWER_SUBMIT_PROPS } from '../../components/forms/formConfig'
import { applyFormApiError } from '../../components/forms/formErrorUtils'
import { FormProcessAlert } from '../../components/forms/FormProcessAlert'
import { EconomySummaryCard } from './EconomySummaryCard'
import { ESTADO_EGRESO_OPTIONS, EXPENSE_TYPE_COLOR, REFUND_TARGET_STATE_OPTIONS, STORAGE_KEYS, TIPO_EGRESO_OPTIONS } from './economyConstants'
import {
  cutStateLabel,
  expenseStateColor,
  expenseStateLabel,
  expenseTypeLabel,
  formatBs,
  formatOriginAmount,
  getStoredFilters,
  incomeStateColor,
  incomeSourceLabel,
  storeFilters,
} from './economyUtils'

const DEFAULT_FILTERS = {
  search: '',
  type: undefined,
  state: undefined,
  cut_id: undefined,
}

export function EconomyExpensesPage() {
  const navigate = useNavigate()
  const location = useLocation()
  const { message } = AntdApp.useApp()
  const { user } = useAuth()
  const [searchParams, setSearchParams] = useSearchParams()
  const [filters, setFilters] = useState(() => getStoredFilters(STORAGE_KEYS.expenses, DEFAULT_FILTERS))
  const [expenses, setExpenses] = useState([])
  const [cuts, setCuts] = useState([])
  const [activeCut, setActiveCut] = useState(null)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState(null)
  const [detail, setDetail] = useState(null)
  const [manualOpen, setManualOpen] = useState(false)
  const [refundOpen, setRefundOpen] = useState(false)
  const [refundContext, setRefundContext] = useState(null)
  const [formError, setFormError] = useState(null)
  const [refundFormError, setRefundFormError] = useState(null)
  const [annullingExpense, setAnnullingExpense] = useState(null)
  const [manualForm] = Form.useForm()
  const [refundForm] = Form.useForm()
  const [annulForm] = Form.useForm()

  const isAdmin = user?.role_code === 'ADMIN'
  const canCreate = user?.permissions?.includes('economy_expenses:create')
  const canAnnul = user?.permissions?.includes('economy_expenses:annul')
  const canRefund = user?.permissions?.includes('economy_refunds:create')

  const refundMode = searchParams.get('mode') === 'refund'
  const refundOriginType = searchParams.get('origin_type')
  const refundOriginId = searchParams.get('origin_id')
  const refundTargetStatus = searchParams.get('target_status')
  const returnTo = searchParams.get('return_to')

  const syncFilterParams = useCallback((nextFilters) => {
    storeFilters(STORAGE_KEYS.expenses, nextFilters)
    const next = new URLSearchParams(searchParams)
    for (const key of ['search', 'type', 'state', 'cut_id']) {
      next.delete(key)
    }
    if (nextFilters.search) next.set('search', nextFilters.search)
    if (nextFilters.type) next.set('type', nextFilters.type)
    if (nextFilters.state) next.set('state', nextFilters.state)
    if (nextFilters.cut_id) next.set('cut_id', String(nextFilters.cut_id))
    setSearchParams(next, { replace: true })
  }, [searchParams, setSearchParams])

  const loadExpenses = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const params = {}
      if (filters.search) params.search = filters.search
      if (filters.type) params.type = filters.type
      if (filters.state) params.state = filters.state
      if (filters.cut_id) params.cut_id = filters.cut_id
      const response = await apiClient.get('/economia/egresos', { params })
      setExpenses(response.data)
    } catch (requestError) {
      setError(requestError.response?.data?.detail || 'NO FUE POSIBLE CARGAR LOS EGRESOS.')
    } finally {
      setLoading(false)
    }
  }, [filters])

  const loadReferences = useCallback(async () => {
    try {
      if (isAdmin) {
        const cutResponse = await apiClient.get('/economia/cortes-caja')
        setCuts(cutResponse.data)
        setActiveCut(null)
      } else {
        const ownCutResponse = await apiClient.get('/economia/cortes-caja/me')
        setActiveCut(ownCutResponse.data.cut)
        setCuts([])
      }
    } catch {
      return
    }
  }, [isAdmin])

  const loadRefundContext = useCallback(async () => {
    if (!refundMode || !refundOriginType || !refundOriginId || !canRefund) return
    setRefundFormError(null)
    try {
      const response = await apiClient.get(`/economia/ingresos/${refundOriginType}/${refundOriginId}/refund-context`)
      setRefundContext(response.data)
      refundForm.setFieldsValue({
        target_state:
          response.data.available_target_states.includes(refundTargetStatus)
            ? refundTargetStatus
            : response.data.available_target_states[0],
        refund_amount: response.data.refundable_balance_bob,
        reason: typeof location.state?.refundReason === 'string' ? location.state.refundReason : undefined,
        concepto: response.data.suggested_concept,
        beneficiario: response.data.suggested_beneficiary,
        observaciones: undefined,
      })
      setRefundOpen(true)
    } catch (requestError) {
      setRefundContext(null)
      setRefundOpen(false)
      setRefundFormError(requestError.response?.data?.detail || 'NO FUE POSIBLE PREPARAR EL FLUJO DE DEVOLUCIÓN.')
    }
  }, [canRefund, location.state, refundForm, refundMode, refundOriginId, refundOriginType, refundTargetStatus])

  useEffect(() => {
    const nextFilters = {
      search: searchParams.get('search') || filters.search,
      type: searchParams.get('type') || filters.type,
      state: searchParams.get('state') || filters.state,
      cut_id: searchParams.get('cut_id') ? Number(searchParams.get('cut_id')) : filters.cut_id,
    }
    setFilters(nextFilters)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  useEffect(() => {
    Promise.all([loadExpenses(), loadReferences(), loadRefundContext()]).catch(() => {
      setError('NO FUE POSIBLE CARGAR EL MÓDULO ECONÓMICO DE EGRESOS.')
      setLoading(false)
    })
  }, [loadExpenses, loadReferences, loadRefundContext])

  const openExpenseDetail = useCallback(async (expenseId) => {
    try {
      const response = await apiClient.get(`/economia/egresos/${expenseId}`)
      setDetail(response.data)
    } catch (requestError) {
      message.error(requestError.response?.data?.detail || 'NO FUE POSIBLE CARGAR EL DETALLE DEL EGRESO.')
    }
  }, [message])

  const submitManualExpense = async (values) => {
    setSaving(true)
    setFormError(null)
    try {
      await apiClient.post('/economia/egresos', values)
      message.success('SE REGISTRÓ EL EGRESO CORRECTAMENTE.')
      setManualOpen(false)
      manualForm.resetFields()
      await Promise.all([loadExpenses(), loadReferences()])
    } catch (requestError) {
      const resolved = applyFormApiError(manualForm, requestError, {
        fallbackGlobalMessage: 'NO FUE POSIBLE REGISTRAR EL EGRESO.',
      })
      setFormError(resolved.globalMessage)
    } finally {
      setSaving(false)
    }
  }

  const submitRefund = async (values) => {
    setSaving(true)
    setRefundFormError(null)
    try {
      await apiClient.post('/economia/devoluciones', {
        origin_type: refundContext.origin_type,
        origin_id: refundContext.origin_id,
        target_state: values.target_state,
        refund_amount: values.refund_amount,
        reason: values.reason,
        concepto: values.concepto,
        beneficiario: values.beneficiario,
        observaciones: values.observaciones,
      })
      message.success('SE REGISTRÓ LA DEVOLUCIÓN Y SE COMPLETÓ LA ANULACIÓN ECONÓMICA.')
      setRefundOpen(false)
      setRefundContext(null)
      refundForm.resetFields()
      const next = new URLSearchParams(searchParams)
      ;['mode', 'origin_type', 'origin_id', 'target_status', 'return_to'].forEach((key) => next.delete(key))
      setSearchParams(next, { replace: true })
      await Promise.all([loadExpenses(), loadReferences()])
      if (returnTo) {
        navigate(returnTo)
      }
    } catch (requestError) {
      const resolved = applyFormApiError(refundForm, requestError, {
        fallbackGlobalMessage: 'NO FUE POSIBLE COMPLETAR LA DEVOLUCIÓN ECONÓMICA.',
      })
      setRefundFormError(resolved.globalMessage)
    } finally {
      setSaving(false)
    }
  }

  const submitExpenseAnnul = async () => {
    setSaving(true)
    try {
      const values = await annulForm.validateFields()
      await apiClient.patch(`/economia/egresos/${annullingExpense.id}/annul`, values)
      message.success('SE ANULÓ EL EGRESO CORRECTAMENTE.')
      setAnnullingExpense(null)
      annulForm.resetFields()
      await loadExpenses()
    } catch (requestError) {
      if (requestError?.errorFields) {
        setSaving(false)
        return
      }
      message.error(requestError.response?.data?.detail || 'NO FUE POSIBLE ANULAR EL EGRESO.')
    } finally {
      setSaving(false)
    }
  }

  const cutOptions = useMemo(
    () => cuts.map((cut) => ({ label: `CORTE #${cut.id} · ${cut.cajero.full_name}`, value: cut.id })),
    [cuts],
  )

  const columns = [
    {
      title: 'FECHA',
      dataIndex: 'fecha',
      key: 'fecha',
      render: (value) => new Date(value).toLocaleString('es-BO'),
    },
    {
      title: 'TIPO',
      dataIndex: 'tipo',
      key: 'tipo',
      render: (value) => (
        <Tag color={EXPENSE_TYPE_COLOR[value] || 'default'}>
          {expenseTypeLabel(value)}
        </Tag>
      ),
    },
    { title: 'CONCEPTO', dataIndex: 'concepto', key: 'concepto' },
    { title: 'BENEFICIARIO', dataIndex: 'beneficiario', key: 'beneficiario', render: (value) => value || 'SIN REGISTRO' },
    { title: 'MONTO', dataIndex: 'monto', key: 'monto', render: (value) => formatBs(value) },
    {
      title: 'ESTADO',
      dataIndex: 'estado',
      key: 'estado',
      render: (value) => <Tag color={expenseStateColor(value)}>{expenseStateLabel(value)}</Tag>,
    },
    {
      title: 'CORTE',
      key: 'cut',
      render: (_, record) => (record.corte ? `#${record.corte.id} · ${cutStateLabel(record.corte.estado)}` : 'ADMIN / SIN CORTE'),
    },
    {
      title: 'REFERENCIA',
      key: 'reference',
      render: (_, record) =>
        record.tabla_referencia && record.id_referencia
          ? `${record.tabla_referencia.toUpperCase()} #${record.id_referencia}`
          : 'SIN REFERENCIA',
    },
    {
      title: 'ACCIONES',
      key: 'actions',
      render: (_, record) => (
        <Row gutter={[8, 8]}>
          <Col>
            <Button icon={<EyeOutlined />} onClick={() => openExpenseDetail(record.id)}>
              VER
            </Button>
          </Col>
          {canAnnul && record.estado === 'registrado' ? (
            <Col>
              <Button danger icon={<CloseCircleOutlined />} onClick={() => setAnnullingExpense(record)}>
                ANULAR
              </Button>
            </Col>
          ) : null}
        </Row>
      ),
    },
  ]

  return (
    <div>
      <div className="page-header">
        <div>
          <Typography.Title level={2} style={{ margin: 0 }}>
            Egresos
          </Typography.Title>
          <Typography.Paragraph type="secondary" style={{ marginBottom: 0 }}>
            Controla salidas de dinero, devoluciones obligatorias y trazabilidad económica del sistema.
          </Typography.Paragraph>
        </div>
        {canCreate ? (
          <Button type="primary" icon={<DollarOutlined />} onClick={() => { setFormError(null); manualForm.resetFields(); setManualOpen(true) }}>
            Nuevo egreso
          </Button>
        ) : null}
      </div>

      <Row gutter={[14, 14]} style={{ marginBottom: 16 }}>
        {isAdmin ? (
          <>
            <Col xs={24} md={8}>
              <EconomySummaryCard
                eyebrow="OPERACIÓN ADMIN"
                title="Egresos globales"
                value={String(expenses.length)}
                accent="#8f3d2e"
                helper="Puedes registrar egresos sin corte y gestionar devoluciones manuales."
              />
            </Col>
            <Col xs={24} md={8}>
              <EconomySummaryCard
                eyebrow="CORTE DE CAJA"
                title="Cortes disponibles"
                value={String(cuts.length)}
                accent="#4b7f5a"
                helper="Filtra egresos por corte cuando quieras revisar un período específico."
              />
            </Col>
          </>
        ) : (
          <Col xs={24} md={12}>
            <EconomySummaryCard
              eyebrow="TU PERÍODO ACTIVO"
              title={activeCut ? `CORTE #${activeCut.id}` : 'SIN CORTE ABIERTO'}
              value={activeCut ? cutStateLabel(activeCut.estado) : 'NO DISPONIBLE'}
              accent={activeCut ? '#4b7f5a' : '#b86c45'}
              helper={activeCut ? `FONDO ASIGNADO: ${formatBs(activeCut.fondo_asignado)}` : 'NO PUEDES REGISTRAR EGRESOS HASTA QUE EL ADMIN ABRA TU CORTE.'}
            />
          </Col>
        )}
      </Row>

      {refundMode ? (
        <Alert
          type="warning"
          showIcon
          style={{ marginBottom: 16 }}
          message="FLUJO ECONÓMICO OBLIGATORIO DE DEVOLUCIÓN"
          description="DEBES REGISTRAR EL MONTO DEVUELTO ANTES DE COMPLETAR LA ANULACIÓN O CANCELACIÓN DEL INGRESO ORIGEN."
        />
      ) : null}

      {!isAdmin && !activeCut ? (
        <Alert
          type="info"
          showIcon
          style={{ marginBottom: 16 }}
          message="NO TIENES UN CORTE DE CAJA ABIERTO."
          description="PUEDES CONSULTAR EGRESOS HISTÓRICOS, PERO NO REGISTRAR NUEVOS HASTA QUE EL ADMIN ABRA TU CORTE."
        />
      ) : null}

      {error ? <Alert type="error" showIcon message={error} style={{ marginBottom: 16 }} /> : null}

      <div className="glass-panel boutique-filter-bar" style={{ marginBottom: 16 }}>
        <Row gutter={[12, 12]}>
          <Col xs={24} md={8}>
            <Input
              allowClear
              prefix={<SearchOutlined />}
              placeholder="BUSCAR CONCEPTO, BENEFICIARIO O OBSERVACIÓN"
              value={filters.search}
              onChange={(event) => {
                const next = { ...filters, search: event.target.value.toUpperCase() }
                setFilters(next)
                syncFilterParams(next)
              }}
            />
          </Col>
          <Col xs={24} md={5}>
            <Select
              allowClear
              placeholder="TIPO DE EGRESO"
              options={TIPO_EGRESO_OPTIONS.filter((option) => option.value !== 'devolucion')}
              value={filters.type}
              onChange={(value) => {
                const next = { ...filters, type: value }
                setFilters(next)
                syncFilterParams(next)
              }}
              style={{ width: '100%' }}
            />
          </Col>
          <Col xs={24} md={4}>
            <Select
              allowClear
              placeholder="ESTADO"
              options={ESTADO_EGRESO_OPTIONS}
              value={filters.state}
              onChange={(value) => {
                const next = { ...filters, state: value }
                setFilters(next)
                syncFilterParams(next)
              }}
              style={{ width: '100%' }}
            />
          </Col>
          {isAdmin ? (
            <Col xs={24} md={7}>
              <Select
                allowClear
                showSearch
                optionFilterProp="label"
                placeholder="FILTRAR POR CORTE"
                options={cutOptions}
                value={filters.cut_id}
                onChange={(value) => {
                  const next = { ...filters, cut_id: value }
                  setFilters(next)
                  syncFilterParams(next)
                }}
                style={{ width: '100%' }}
              />
            </Col>
          ) : null}
        </Row>
      </div>

      <Table
        className="glass-panel"
        rowKey="id"
        columns={columns}
        dataSource={expenses}
        loading={loading}
        pagination={{ pageSize: 10 }}
        scroll={{ x: 'max-content' }}
        style={{ borderRadius: 24, overflow: 'hidden' }}
      />

      <Drawer
        title="Registrar egreso"
        width={680}
        open={manualOpen}
        onClose={() => {
          setManualOpen(false)
          setFormError(null)
          manualForm.resetFields()
        }}
        maskClosable={false}
        destroyOnClose
      >
        <Form {...FORM_COMMON_PROPS} form={manualForm} onFinish={submitManualExpense}>
          <FormProcessAlert message={formError} />
          <Row gutter={12}>
            <Col xs={24} md={12}>
              <Form.Item
                label="TIPO DE EGRESO"
                name="tipo"
                rules={[{ required: true, message: 'DEBE SELECCIONAR EL TIPO DE EGRESO.' }]}
              >
                <Select options={TIPO_EGRESO_OPTIONS.filter((option) => option.value !== 'devolucion')} placeholder="SELECCIONA EL TIPO" />
              </Form.Item>
            </Col>
            <Col xs={24} md={12}>
              <Form.Item
                label="BENEFICIARIO"
                name="beneficiario"
                normalize={(value) => (value || '').toUpperCase()}
              >
                <Input placeholder="EJ. PROVEEDOR, COSTURERA, SERVICIO" />
              </Form.Item>
            </Col>
            <Col xs={24}>
              <Form.Item
                label="CONCEPTO"
                name="concepto"
                rules={[{ required: true, message: 'DEBE REGISTRAR EL CONCEPTO.' }]}
                normalize={(value) => (value || '').toUpperCase()}
              >
                <Input placeholder="EJ. COMPRA DE INSUMOS, PAGO DE COSTURA, MANTENIMIENTO DE EQUIPO" />
              </Form.Item>
            </Col>
            <Col xs={24} md={12}>
              <Form.Item
                label="CANTIDAD"
                name="cantidad"
                rules={[{ required: true, message: 'DEBE REGISTRAR LA CANTIDAD.' }]}
              >
                <InputNumber min={0.01} precision={2} style={{ width: '100%' }} placeholder="EJ. 1" />
              </Form.Item>
            </Col>
            <Col xs={24} md={12}>
              <Form.Item
                label="PRECIO UNIDAD"
                name="precio_unidad"
                rules={[{ required: true, message: 'DEBE REGISTRAR EL PRECIO UNIDAD.' }]}
              >
                <InputNumber min={0.01} precision={2} style={{ width: '100%' }} placeholder="EJ. 250" />
              </Form.Item>
            </Col>
            <Col xs={24}>
              <Form.Item
                label="OBSERVACIÓN OPERATIVA"
                name="observaciones_1"
                normalize={(value) => (value || '').toUpperCase()}
              >
                <Input.TextArea rows={3} placeholder="DETALLA EL CONTEXTO DEL EGRESO" />
              </Form.Item>
            </Col>
            <Col xs={24}>
              <Form.Item
                label="OBSERVACIÓN COMPLEMENTARIA"
                name="observaciones_2"
                normalize={(value) => (value || '').toUpperCase()}
              >
                <Input.TextArea rows={2} placeholder="INFORMACIÓN ADICIONAL SI ES NECESARIA" />
              </Form.Item>
            </Col>
          </Row>
          <Row justify="end" gutter={12}>
            <Col><Button onClick={() => setManualOpen(false)}>CANCELAR</Button></Col>
            <Col><Button type="primary" htmlType="submit" loading={saving} {...FORM_DRAWER_SUBMIT_PROPS}>REGISTRAR EGRESO</Button></Col>
          </Row>
        </Form>
      </Drawer>

      <Drawer
        title="Flujo obligatorio de devolución"
        width={780}
        open={refundOpen}
        onClose={() => {
          if (refundMode) return
          setRefundOpen(false)
          setRefundContext(null)
          refundForm.resetFields()
        }}
        maskClosable={false}
        closable={!refundMode}
        destroyOnClose
      >
        <Form {...FORM_COMMON_PROPS} form={refundForm} onFinish={submitRefund}>
          <FormProcessAlert message={refundFormError} />
          {refundContext ? (
            <>
              <Descriptions bordered column={2} size="small" style={{ marginBottom: 16 }}>
                <Descriptions.Item label="ORIGEN">{incomeSourceLabel(refundContext.origin_type)}</Descriptions.Item>
                <Descriptions.Item label="CÓDIGO">{refundContext.source_code}</Descriptions.Item>
                <Descriptions.Item label="CLIENTE">{refundContext.client_name || 'SIN CLIENTE'}</Descriptions.Item>
                <Descriptions.Item label="REGISTRADO POR">{refundContext.registered_by}</Descriptions.Item>
                <Descriptions.Item label="ESTADO ACTUAL">
                  <Tag color={incomeStateColor(refundContext.current_state)}>{refundContext.current_state}</Tag>
                </Descriptions.Item>
                <Descriptions.Item label="MONTO ORIGINAL BS">{formatBs(refundContext.amount_bob)}</Descriptions.Item>
                <Descriptions.Item label="MONTO YA DEVUELTO">{formatBs(refundContext.refunded_amount_bob)}</Descriptions.Item>
                <Descriptions.Item label="SALDO REEMBOLSABLE">{formatBs(refundContext.refundable_balance_bob)}</Descriptions.Item>
                <Descriptions.Item label="MONEDA ORIGEN">
                  {formatOriginAmount(refundContext.amount_origin, refundContext.currency_code, refundContext.currency_symbol)}
                </Descriptions.Item>
                <Descriptions.Item label="TIPO DE CAMBIO USADO">{Number(refundContext.exchange_rate_used || 0).toFixed(4)}</Descriptions.Item>
                <Descriptions.Item label="MÉTODO DE PAGO">{refundContext.payment_method || 'SIN REGISTRO'}</Descriptions.Item>
              </Descriptions>

              <Alert
                type="warning"
                showIcon
                style={{ marginBottom: 16 }}
                message="ESTA DEVOLUCIÓN ES OBLIGATORIA PARA COMPLETAR LA ANULACIÓN O CANCELACIÓN DEL INGRESO."
                description="EL MONTO DEVUELTO SE REGISTRARÁ COMO EGRESO DE TIPO DEVOLUCIÓN Y EL INGRESO ORIGEN QUEDARÁ EN HISTÓRICO, PERO YA CON SU TRAZABILIDAD DE REEMBOLSO."
              />

              <Row gutter={12}>
                <Col xs={24} md={12}>
                  <Form.Item
                    label="ESTADO DESTINO DEL ORIGEN"
                    name="target_state"
                    rules={[{ required: true, message: 'DEBE SELECCIONAR EL ESTADO DESTINO.' }]}
                  >
                    <Select
                      options={REFUND_TARGET_STATE_OPTIONS.filter((option) => refundContext.available_target_states.includes(option.value))}
                      placeholder="SELECCIONA EL ESTADO DESTINO"
                    />
                  </Form.Item>
                </Col>
                <Col xs={24} md={12}>
                  <Form.Item
                    label="MONTO DEVUELTO (BS)"
                    name="refund_amount"
                    rules={[{ required: true, message: 'DEBE REGISTRAR EL MONTO DEVUELTO.' }]}
                  >
                    <InputNumber
                      min={0.01}
                      max={refundContext.refundable_balance_bob}
                      precision={2}
                      style={{ width: '100%' }}
                      placeholder="EJ. 150.00"
                    />
                  </Form.Item>
                </Col>
                <Col xs={24}>
                  <Form.Item
                    label="MOTIVO OPERATIVO"
                    name="reason"
                    rules={[{ required: true, message: 'DEBE REGISTRAR EL MOTIVO OPERATIVO.' }]}
                    normalize={(value) => (value || '').toUpperCase()}
                  >
                    <Input.TextArea rows={3} placeholder="EXPLICA POR QUÉ SE ESTÁ ANULANDO O CANCELANDO EL INGRESO" />
                  </Form.Item>
                </Col>
                <Col xs={24}>
                  <Form.Item
                    label="CONCEPTO DEL EGRESO"
                    name="concepto"
                    rules={[{ required: true, message: 'DEBE REGISTRAR EL CONCEPTO DEL EGRESO.' }]}
                    normalize={(value) => (value || '').toUpperCase()}
                  >
                    <Input placeholder="SE GENERARÁ COMO EGRESO ECONÓMICO DE DEVOLUCIÓN" />
                  </Form.Item>
                </Col>
                <Col xs={24} md={12}>
                  <Form.Item
                    label="BENEFICIARIO"
                    name="beneficiario"
                    normalize={(value) => (value || '').toUpperCase()}
                  >
                    <Input placeholder="EJ. NOMBRE DE LA CLIENTA" />
                  </Form.Item>
                </Col>
                <Col xs={24} md={12}>
                  <Form.Item
                    label="OBSERVACIONES"
                    name="observaciones"
                    normalize={(value) => (value || '').toUpperCase()}
                  >
                    <Input placeholder="DETALLE COMPLEMENTARIO DEL REEMBOLSO" />
                  </Form.Item>
                </Col>
              </Row>
            </>
          ) : (
            <Alert type="error" showIcon message={refundFormError || 'NO SE PUDO PREPARAR EL CONTEXTO DE DEVOLUCIÓN.'} />
          )}
          {refundContext ? (
            <Row justify="end" gutter={12}>
              {!refundMode ? <Col><Button onClick={() => setRefundOpen(false)}>CANCELAR</Button></Col> : null}
              <Col><Button type="primary" htmlType="submit" loading={saving} {...FORM_DRAWER_SUBMIT_PROPS}>REGISTRAR DEVOLUCIÓN Y CONTINUAR</Button></Col>
            </Row>
          ) : null}
        </Form>
      </Drawer>

      <Drawer
        title="Detalle del egreso"
        width={720}
        open={Boolean(detail)}
        onClose={() => setDetail(null)}
        maskClosable={false}
      >
        {detail ? (
          <Descriptions bordered column={2} size="small">
            <Descriptions.Item label="TIPO">
              <Tag color={EXPENSE_TYPE_COLOR[detail.tipo] || 'default'}>{expenseTypeLabel(detail.tipo)}</Tag>
            </Descriptions.Item>
            <Descriptions.Item label="ESTADO">
              <Tag color={expenseStateColor(detail.estado)}>{expenseStateLabel(detail.estado)}</Tag>
            </Descriptions.Item>
            <Descriptions.Item label="FECHA">{new Date(detail.fecha).toLocaleString('es-BO')}</Descriptions.Item>
            <Descriptions.Item label="MONTO">{formatBs(detail.monto)}</Descriptions.Item>
            <Descriptions.Item label="CONCEPTO" span={2}>{detail.concepto}</Descriptions.Item>
            <Descriptions.Item label="BENEFICIARIO">{detail.beneficiario || 'SIN REGISTRO'}</Descriptions.Item>
            <Descriptions.Item label="CANTIDAD">{Number(detail.cantidad || 0).toFixed(2)}</Descriptions.Item>
            <Descriptions.Item label="PRECIO UNIDAD">{formatBs(detail.precio_unidad)}</Descriptions.Item>
            <Descriptions.Item label="USUARIO">{detail.usuario?.full_name || 'SIN REGISTRO'}</Descriptions.Item>
            <Descriptions.Item label="CORTE">
              {detail.corte ? `#${detail.corte.id} · ${cutStateLabel(detail.corte.estado)}` : 'ADMIN / SIN CORTE'}
            </Descriptions.Item>
            <Descriptions.Item label="REFERENCIA" span={2}>
              {detail.tabla_referencia && detail.id_referencia
                ? `${detail.tabla_referencia.toUpperCase()} #${detail.id_referencia}`
                : 'SIN REFERENCIA'}
            </Descriptions.Item>
            <Descriptions.Item label="OBSERVACIÓN 1" span={2}>{detail.observaciones_1 || 'SIN OBSERVACIÓN'}</Descriptions.Item>
            <Descriptions.Item label="OBSERVACIÓN 2" span={2}>{detail.observaciones_2 || 'SIN OBSERVACIÓN'}</Descriptions.Item>
            <Descriptions.Item label="MOTIVO CAMBIO ESTADO" span={2}>{detail.motivo_cambio_estado || 'SIN CAMBIO DE ESTADO'}</Descriptions.Item>
          </Descriptions>
        ) : null}
      </Drawer>

      <Drawer
        title="Anular egreso"
        width={560}
        open={Boolean(annullingExpense)}
        onClose={() => {
          setAnnullingExpense(null)
          annulForm.resetFields()
        }}
        maskClosable={false}
      >
        {annullingExpense ? (
          <>
            <Alert
              type="warning"
              showIcon
              message={`SE ANULARÁ EL EGRESO #${annullingExpense.id} POR ${formatBs(annullingExpense.monto)}.`}
              style={{ marginBottom: 16 }}
            />
            <Form {...FORM_COMMON_PROPS} form={annulForm} onFinish={submitExpenseAnnul}>
              <Form.Item
                label="MOTIVO DE ANULACIÓN"
                name="motivo"
                rules={[{ required: true, message: 'DEBE REGISTRAR EL MOTIVO DE ANULACIÓN.' }]}
                normalize={(value) => (value || '').toUpperCase()}
              >
                <Input.TextArea rows={3} placeholder="EXPLICA POR QUÉ EL EGRESO DEBE QUEDAR ANULADO" />
              </Form.Item>
              <Row justify="end" gutter={12}>
                <Col><Button onClick={() => setAnnullingExpense(null)}>CANCELAR</Button></Col>
                <Col><Button type="primary" danger htmlType="submit" loading={saving} icon={<ReloadOutlined />}>ANULAR EGRESO</Button></Col>
              </Row>
            </Form>
          </>
        ) : null}
      </Drawer>
    </div>
  )
}
