/* eslint-disable react-hooks/exhaustive-deps */
import { CheckCircleOutlined, EditOutlined, EyeOutlined, PauseCircleOutlined, PlusOutlined, SearchOutlined, StopOutlined, SwapOutlined } from '@ant-design/icons'
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
  Modal,
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
import { ReportSummaryStrip } from '../../components/reports/ReportSummaryStrip'
import { useListingSummary } from '../../components/reports/useListingSummary'
import { ESTADO_FLETE_OPTIONS, REVIEW_RESOLUTION_OPTIONS, fleteStateColor, formatMoney, labelFromOptions } from './fleteConstants'

function inferUsedCodePreview(baseCode, allCodes) {
  let suffix = 1
  while (allCodes.includes(`${baseCode}-USADO-${`${suffix}`.padStart(2, '0')}`)) {
    suffix += 1
  }
  return `${baseCode}-USADO-${`${suffix}`.padStart(2, '0')}`
}

export function FletesPage() {
  const [fletes, setFletes] = useState([])
  const [eligibleItems, setEligibleItems] = useState([])
  const [allBoutiqueItems, setAllBoutiqueItems] = useState([])
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState(null)
  const [formError, setFormError] = useState(null)
  const [detail, setDetail] = useState(null)
  const [detailOpen, setDetailOpen] = useState(false)
  const [formOpen, setFormOpen] = useState(false)
  const [editingFlete, setEditingFlete] = useState(null)
  const [actionModal, setActionModal] = useState(null)
  const [filters, setFilters] = useState({
    search: '',
    state: undefined,
    is_enabled: undefined,
  })
  const [form] = Form.useForm()
  const [actionForm] = Form.useForm()
  const { message } = AntdApp.useApp()
  const { user } = useAuth()

  const canCreate = user?.permissions?.includes('fletes:create')
  const canUpdate = user?.permissions?.includes('fletes:update')
  const canDisable = user?.permissions?.includes('fletes:disable')
  const canResolveReview = user?.permissions?.includes('fletes:resolve_review')
  const canPassToSale = user?.permissions?.includes('fletes:pass_to_sale')
  const canRetire = user?.permissions?.includes('fletes:retire')
  const canView = user?.permissions?.includes('fletes:view')
  const { summary, loading: summaryLoading } = useListingSummary('/fletes/resumen', filters)

  const loadReferences = useCallback(async () => {
    const [eligibleResponse, itemsResponse] = await Promise.all([
      apiClient.get('/fletes/eligible-items'),
      apiClient.get('/boutique/items'),
    ])
    setEligibleItems(eligibleResponse.data)
    setAllBoutiqueItems(itemsResponse.data)
  }, [])

  const loadFletes = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const params = {}
      if (filters.search) params.search = filters.search
      if (filters.state) params.state = filters.state
      if (typeof filters.is_enabled === 'boolean') params.is_enabled = filters.is_enabled
      const response = await apiClient.get('/fletes', { params })
      setFletes(response.data)
    } catch (requestError) {
      setError(requestError.response?.data?.detail || 'No fue posible cargar los vestidos habilitados para flete.')
    } finally {
      setLoading(false)
    }
  }, [filters])

  useEffect(() => {
    Promise.all([loadReferences(), loadFletes()]).catch(() => {
      setError('No fue posible cargar la información inicial del módulo de fletes.')
      setLoading(false)
    })
  }, [])

  useEffect(() => {
    loadFletes()
  }, [filters.search, filters.state, filters.is_enabled])

  const eligibleOptions = useMemo(
    () => eligibleItems.map((item) => ({ label: `${item.code} - ${item.name}`, value: item.id })),
    [eligibleItems],
  )
  const allCodes = useMemo(() => allBoutiqueItems.map((item) => item.code), [allBoutiqueItems])

  const openCreate = () => {
    setEditingFlete(null)
    setFormError(null)
    form.resetFields()
    form.setFieldsValue({ max_salidas: 3 })
    setFormOpen(true)
  }

  const openEdit = async (record) => {
    try {
      const response = await apiClient.get(`/fletes/${record.id}`)
      setEditingFlete(response.data)
      form.setFieldsValue({
        precio_flete_ref: response.data.precio_flete_ref,
        max_salidas: response.data.max_salidas,
        observaciones: response.data.observaciones,
      })
      setFormError(null)
      setFormOpen(true)
    } catch (requestError) {
      message.error(requestError.response?.data?.detail || 'No fue posible cargar el flete para edición.')
    }
  }

  const openDetail = async (record) => {
    try {
      const response = await apiClient.get(`/fletes/${record.id}`)
      setDetail(response.data)
      setDetailOpen(true)
    } catch (requestError) {
      message.error(requestError.response?.data?.detail || 'No fue posible cargar el detalle del flete.')
    }
  }

  const openAction = (record, type) => {
    setActionModal({ type, record })
    actionForm.resetFields()
  }

  const closeForm = () => {
    setFormOpen(false)
    setEditingFlete(null)
    setFormError(null)
    form.resetFields()
  }

  const closeAction = () => {
    setActionModal(null)
    actionForm.resetFields()
  }

  const submitForm = async (values) => {
    setSaving(true)
    setFormError(null)
    try {
      if (editingFlete) {
        await apiClient.patch(`/fletes/${editingFlete.id}`, values)
        message.success('Se actualizó el vestido en flete correctamente.')
      } else {
        await apiClient.post('/fletes', values)
        message.success('Se habilitó el vestido para flete correctamente.')
      }
      closeForm()
      await Promise.all([loadFletes(), loadReferences()])
    } catch (requestError) {
      const resolved = applyFormApiError(form, requestError, {
        messageFieldMap: [
          { test: /solo puedes habilitar.*vestido/i, field: 'item_id' },
          { test: /no tiene stock/i, field: 'item_id' },
          { test: /ya está relacionado/i, field: 'item_id' },
          { test: /máximo de salidas/i, field: 'max_salidas' },
        ],
        fallbackGlobalMessage: editingFlete
          ? 'No fue posible actualizar el vestido en flete.'
          : 'No fue posible habilitar el vestido para flete.',
      })
      setFormError(resolved.globalMessage)
    } finally {
      setSaving(false)
    }
  }

  const submitAction = async () => {
    setSaving(true)
    try {
      const values = await actionForm.validateFields()
      const { record, type } = actionModal
      if (type === 'disable') {
        await apiClient.patch(`/fletes/${record.id}/disable`, values)
        message.success('Se deshabilitó el vestido de flete correctamente.')
      }
      if (type === 'resolve-review') {
        await apiClient.patch(`/fletes/${record.id}/resolve-review`, values)
        message.success('Se resolvió la revisión del vestido correctamente.')
      }
      if (type === 'pass-to-sale') {
        const response = await apiClient.patch(`/fletes/${record.id}/pass-to-sale`, values)
        message.success(`El vestido pasó a venta y se creó el item ${response.data.new_item_code}.`)
      }
      if (type === 'retire') {
        await apiClient.patch(`/fletes/${record.id}/retire`, values)
        message.success('Se retiró el vestido del circuito de flete.')
      }
      closeAction()
      if (detail?.id === record.id) {
        const response = await apiClient.get(`/fletes/${record.id}`)
        setDetail(response.data)
      }
      await Promise.all([loadFletes(), loadReferences()])
    } catch (requestError) {
      if (requestError?.errorFields) {
        setSaving(false)
        return
      }
      const resolved = applyFormApiError(actionForm, requestError, {
        fallbackGlobalMessage: 'No fue posible completar la acción sobre el vestido en flete.',
      })
      message.error(resolved.globalMessage)
    } finally {
      setSaving(false)
    }
  }

  const columns = [
    {
      title: 'Vestido',
      key: 'item',
      render: (_, record) => `${record.item.code} - ${record.item.name}`,
    },
    {
      title: 'Color',
      key: 'color',
      render: (_, record) => record.item.color_primary,
    },
    {
      title: 'Precio ref. (Bs)',
      dataIndex: 'precio_flete_ref',
      key: 'precio_flete_ref',
      render: (value) => formatMoney(value),
    },
    {
      title: 'Salidas',
      key: 'salidas',
      render: (_, record) => `${record.salidas_actuales}/${record.max_salidas}`,
    },
    {
      title: 'Estado',
      dataIndex: 'estado',
      key: 'estado',
      render: (value) => <Tag color={fleteStateColor(value)}>{labelFromOptions(ESTADO_FLETE_OPTIONS, value)}</Tag>,
    },
    {
      title: 'Activo',
      dataIndex: 'habilitado',
      key: 'habilitado',
      render: (value) => <Tag color={value ? 'green' : 'default'}>{value ? 'SÍ' : 'NO'}</Tag>,
    },
    {
      title: 'Acciones',
      key: 'acciones',
      render: (_, record) => (
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
          {canView ? (
            <Button icon={<EyeOutlined />} onClick={() => openDetail(record)}>
              Ver
            </Button>
          ) : null}
          {canUpdate && record.habilitado ? (
            <Button icon={<EditOutlined />} onClick={() => openEdit(record)}>
              Editar
            </Button>
          ) : null}
          {canDisable && record.habilitado && record.salidas_actuales === 0 ? (
            <Button icon={<PauseCircleOutlined />} onClick={() => openAction(record, 'disable')}>
              Deshabilitar
            </Button>
          ) : null}
          {canResolveReview && record.estado === 'en_revision' ? (
            <Button icon={<CheckCircleOutlined />} onClick={() => openAction(record, 'resolve-review')}>
              Resolver revisión
            </Button>
          ) : null}
          {canPassToSale && record.habilitado && record.salidas_actuales > 0 && record.estado !== 'en_flete' ? (
            <Button icon={<SwapOutlined />} onClick={() => openAction(record, 'pass-to-sale')}>
              Pasar a venta
            </Button>
          ) : null}
          {canRetire && record.habilitado && record.estado !== 'en_flete' ? (
            <Button danger icon={<StopOutlined />} onClick={() => openAction(record, 'retire')}>
              Retirar
            </Button>
          ) : null}
        </div>
      ),
    },
  ]

  const previewCode =
    actionModal?.type === 'pass-to-sale' && actionModal?.record
      ? inferUsedCodePreview(actionModal.record.item.code, allCodes)
      : null

  return (
    <div>
      <div className="page-header">
        <div>
          <Typography.Title level={2} style={{ margin: 0 }}>
            Vestidos en Flete
          </Typography.Title>
          <Typography.Paragraph type="secondary" style={{ marginBottom: 0 }}>
            Habilita vestidos del inventario boutique para alquiler, controla sus salidas y decide cuándo vuelven a venta o salen del circuito.
          </Typography.Paragraph>
        </div>
        {canCreate ? (
          <Button type="primary" icon={<PlusOutlined />} onClick={openCreate}>
            Habilitar vestido
          </Button>
        ) : null}
      </div>

      <div className="glass-panel boutique-filter-bar">
        <Row gutter={[12, 12]}>
          <Col xs={24} md={10}>
            <Input
              allowClear
              prefix={<SearchOutlined />}
              placeholder="Buscar por código, nombre o color"
              value={filters.search}
              onChange={(event) => setFilters((current) => ({ ...current, search: event.target.value }))}
            />
          </Col>
          <Col xs={24} md={7}>
            <Select
              allowClear
              placeholder="Filtrar por estado"
              options={ESTADO_FLETE_OPTIONS}
              value={filters.state}
              onChange={(value) => setFilters((current) => ({ ...current, state: value }))}
              style={{ width: '100%' }}
            />
          </Col>
          <Col xs={24} md={7}>
            <Select
              allowClear
              placeholder="Filtrar por habilitación"
              options={[
                { value: true, label: 'SOLO ACTIVOS' },
                { value: false, label: 'SOLO INACTIVOS' },
              ]}
              value={filters.is_enabled}
              onChange={(value) => setFilters((current) => ({ ...current, is_enabled: value }))}
              style={{ width: '100%' }}
            />
          </Col>
        </Row>
      </div>

      {error ? <Alert type="error" showIcon message={error} style={{ marginBottom: 16 }} /> : null}
      <ReportSummaryStrip summary={summary} loading={summaryLoading} />

      <Table
        className="glass-panel"
        rowKey="id"
        columns={columns}
        dataSource={fletes}
        loading={loading}
        pagination={{ pageSize: 8 }}
        scroll={{ x: 'max-content' }}
        style={{ borderRadius: 24, overflow: 'hidden' }}
      />

      <Drawer
        title={editingFlete ? 'Editar Flete' : 'Habilitar Vestido para Flete'}
        width={720}
        open={formOpen}
        onClose={closeForm}
        maskClosable={false}
        destroyOnClose
      >
        <FormProcessAlert
          message={formError}
          title={editingFlete ? 'No fue posible actualizar el flete.' : 'No fue posible habilitar el vestido para flete.'}
        />
        <Form {...FORM_COMMON_PROPS} form={form} onFinish={submitForm}>
          <Row gutter={12}>
            {!editingFlete ? (
              <Col xs={24} md={24}>
                <Form.Item
                  label="Vestido elegible"
                  name="item_id"
                  rules={[{ required: true, message: 'Debe seleccionar el vestido elegible para flete.' }]}
                >
                  <Select
                    showSearch
                    optionFilterProp="label"
                    placeholder="Selecciona un vestido disponible y con stock"
                    options={eligibleOptions}
                  />
                </Form.Item>
              </Col>
            ) : null}
            <Col xs={24} md={12}>
              <Form.Item
                label="Precio referencial de flete (Bs)"
                name="precio_flete_ref"
                rules={[{ required: true, message: 'Debe registrar el precio referencial del flete.' }]}
              >
                <InputNumber min={0.01} precision={2} placeholder="Ej. 350.00" style={{ width: '100%' }} />
              </Form.Item>
            </Col>
            <Col xs={24} md={12}>
              <Form.Item
                label="Máximo de salidas"
                name="max_salidas"
                rules={[{ required: true, message: 'Debe registrar el máximo de salidas permitidas.' }]}
              >
                <InputNumber min={1} max={4} precision={0} placeholder="Entre 1 y 4" style={{ width: '100%' }} />
              </Form.Item>
            </Col>
            <Col span={24}>
              <Form.Item label="Observaciones" name="observaciones" normalize={(value) => (value || '').toUpperCase()}>
                <Input.TextArea rows={3} placeholder="Ej. VESTIDO RESERVADO PARA ALQUILER DE ALTA ROTACIÓN" />
              </Form.Item>
            </Col>
          </Row>
          <Button type="primary" htmlType="submit" loading={saving} {...FORM_DRAWER_SUBMIT_PROPS}>
            {editingFlete ? 'Actualizar flete' : 'Habilitar flete'}
          </Button>
        </Form>
      </Drawer>

      <Modal
        title="Detalle del Vestido en Flete"
        open={detailOpen}
        onCancel={() => {
          setDetailOpen(false)
          setDetail(null)
        }}
        footer={[
          <Button key="close" onClick={() => { setDetailOpen(false); setDetail(null) }}>
            Cerrar
          </Button>,
        ]}
        maskClosable={false}
        width={980}
      >
        {detail ? (
          <Row gutter={[16, 16]}>
            <Col span={24}>
              <Descriptions bordered column={2} size="small">
                <Descriptions.Item label="Vestido">{`${detail.item.code} - ${detail.item.name}`}</Descriptions.Item>
                <Descriptions.Item label="Estado">
                  <Tag color={fleteStateColor(detail.estado)}>{labelFromOptions(ESTADO_FLETE_OPTIONS, detail.estado)}</Tag>
                </Descriptions.Item>
                <Descriptions.Item label="Precio ref. (Bs)">{formatMoney(detail.precio_flete_ref)}</Descriptions.Item>
                <Descriptions.Item label="Salidas válidas">{`${detail.salidas_actuales}/${detail.max_salidas}`}</Descriptions.Item>
                <Descriptions.Item label="Color principal">{detail.item.color_primary}</Descriptions.Item>
                <Descriptions.Item label="Material">{detail.item.material}</Descriptions.Item>
                <Descriptions.Item label="Registrado por">{detail.registered_by.full_name}</Descriptions.Item>
                <Descriptions.Item label="Activo">{detail.habilitado ? 'SÍ' : 'NO'}</Descriptions.Item>
                <Descriptions.Item label="Salida activa">
                  {detail.tiene_salida_activa ? `SÍ (ID ${detail.active_output_id})` : 'NO'}
                </Descriptions.Item>
                <Descriptions.Item label="Observaciones">{detail.observaciones || 'SIN OBSERVACIONES'}</Descriptions.Item>
              </Descriptions>
            </Col>
            <Col span={24}>
              <Typography.Title level={5}>Historial resumido de salidas</Typography.Title>
              <Table
                rowKey="id"
                size="small"
                pagination={false}
                dataSource={detail.salidas}
                columns={[
                  { title: 'N°', dataIndex: 'numero_salida', key: 'numero_salida' },
                  { title: 'Cliente', dataIndex: 'client_name', key: 'client_name' },
                  { title: 'Salida', dataIndex: 'fecha_salida', key: 'fecha_salida' },
                  { title: 'Prev. devolución', dataIndex: 'fecha_devolucion_prevista', key: 'fecha_devolucion_prevista' },
                  {
                    title: 'Estado',
                    dataIndex: 'estado_salida',
                    key: 'estado_salida',
                    render: (value) => <Tag>{value.toUpperCase()}</Tag>,
                  },
                  {
                    title: 'Total (Bs)',
                    dataIndex: 'total_flete',
                    key: 'total_flete',
                    render: (value) => formatMoney(value),
                  },
                ]}
              />
            </Col>
          </Row>
        ) : null}
      </Modal>

      <Modal
        title={
          actionModal?.type === 'disable'
            ? 'Deshabilitar vestido en flete'
            : actionModal?.type === 'resolve-review'
              ? 'Resolver revisión'
              : actionModal?.type === 'pass-to-sale'
                ? 'Pasar vestido usado a venta'
                : 'Retirar vestido de flete'
        }
        open={Boolean(actionModal)}
        onCancel={closeAction}
        onOk={submitAction}
        confirmLoading={saving}
        maskClosable={false}
        okText="Confirmar"
        cancelText="Cerrar"
      >
        {actionModal ? (
          <>
            {actionModal.type === 'pass-to-sale' ? (
              <Alert
                type="info"
                showIcon
                message={`Código sugerido para el nuevo item usado: ${previewCode}`}
                description="Si ese código ya existiera al confirmar, el backend ajustará el sufijo automáticamente para mantener unicidad."
                style={{ marginBottom: 16 }}
              />
            ) : null}
            <Form {...FORM_COMMON_PROPS} form={actionForm}>
              <Row gutter={12}>
                {actionModal.type === 'resolve-review' ? (
                  <Col span={24}>
                    <Form.Item
                      label="Resolución final"
                      name="resolution"
                      rules={[{ required: true, message: 'Debe elegir la resolución final del vestido.' }]}
                    >
                      <Select placeholder="Selecciona cómo debe quedar el vestido" options={REVIEW_RESOLUTION_OPTIONS} />
                    </Form.Item>
                  </Col>
                ) : null}
                {actionModal.type === 'pass-to-sale' ? (
                  <Col xs={24} md={12}>
                    <Form.Item
                      label="Nuevo precio de venta (Bs)"
                      name="new_sale_price"
                      rules={[{ required: true, message: 'Debe registrar el nuevo precio de venta del vestido usado.' }]}
                    >
                      <InputNumber min={0.01} precision={2} placeholder="Ej. 980.00" style={{ width: '100%' }} />
                    </Form.Item>
                  </Col>
                ) : null}
                <Col span={24}>
                  <Form.Item
                    label={actionModal.type === 'pass-to-sale' ? 'Observaciones del nuevo item' : 'Motivo operativo'}
                    name={actionModal.type === 'pass-to-sale' ? 'observaciones' : 'motivo'}
                    rules={[
                      {
                        required: actionModal.type !== 'pass-to-sale' ? true : false,
                        message:
                          actionModal.type === 'pass-to-sale'
                            ? ' '
                            : 'Debe registrar el motivo operativo de la acción.',
                      },
                    ]}
                    normalize={(value) => (value || '').toUpperCase()}
                  >
                    <Input.TextArea
                      rows={3}
                      placeholder={
                        actionModal.type === 'pass-to-sale'
                          ? 'Ej. VESTIDO USADO DE FLETE, LISTO PARA VENTA EN LIQUIDACIÓN'
                          : 'Ej. YA NO ESTARÁ DISPONIBLE PARA ALQUILER O SE TRATÓ DE UNA HABILITACIÓN ERRÓNEA'
                      }
                    />
                  </Form.Item>
                </Col>
              </Row>
            </Form>
          </>
        ) : null}
      </Modal>
    </div>
  )
}
