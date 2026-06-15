/* eslint-disable react-hooks/exhaustive-deps, react/prop-types */
import { BgColorsOutlined, CheckCircleOutlined, CloseCircleOutlined, EditOutlined, EyeOutlined, PlusOutlined, SearchOutlined, StopOutlined } from '@ant-design/icons'
import { Alert, App as AntdApp, Button, Card, Col, DatePicker, Descriptions, Drawer, Form, Input, InputNumber, Modal, Row, Select, Space, Switch, Table, Tag, Typography } from 'antd'
import dayjs from 'dayjs'
import { useCallback, useEffect, useMemo, useState } from 'react'

import { apiClient } from '../../api/client'
import { useAuth } from '../../auth/AuthProvider'
import { FORM_COMMON_PROPS, FORM_DRAWER_SUBMIT_PROPS } from '../../components/forms/formConfig'
import { applyFormApiError } from '../../components/forms/formErrorUtils'
import { FormProcessAlert } from '../../components/forms/FormProcessAlert'
import { ColorPickerModal, COLOR_MAP } from '../boutique/ColorPickerModal'
import {
  ESTADO_PEDIDO_OPTIONS,
  MOTIVO_DESCUENTO_OPTIONS,
  TIPO_PEDIDO_OPTIONS,
  TIPO_VESTIDO_OPTIONS,
  TRAVEL_DESTINATIONS,
  formatBs,
  formatConvertedMoney,
  labelFromOptions,
  orderStateColor,
} from './orderConstants'

const uppercaseText = (value) => (value || '').toUpperCase()
const uppercaseCode = (value) => (value || '').replace(/[^A-Z0-9-]/gi, '').toUpperCase()

export function OrdersPage() {
  const [orders, setOrders] = useState([])
  const [clients, setClients] = useState([])
  const [currencies, setCurrencies] = useState([])
  const [exchangeRates, setExchangeRates] = useState([])
  const [visualCurrencyId, setVisualCurrencyId] = useState(null)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState(null)
  const [formError, setFormError] = useState(null)
  const [filters, setFilters] = useState({ search: '', state: undefined, type: undefined, only_travel: undefined })
  const [drawerOpen, setDrawerOpen] = useState(false)
  const [editingOrder, setEditingOrder] = useState(null)
  const [detail, setDetail] = useState(null)
  const [detailOpen, setDetailOpen] = useState(false)
  const [action, setAction] = useState(null)
  const [form] = Form.useForm()
  const [actionForm] = Form.useForm()
  const { message, modal } = AntdApp.useApp()
  const { user } = useAuth()

  const canCreate = user?.permissions?.includes('orders:create')
  const canUpdate = user?.permissions?.includes('orders:update')
  const canStatus = user?.permissions?.includes('orders:update_status')
  const canDeliver = user?.permissions?.includes('orders:deliver')
  const canView = user?.permissions?.includes('orders:view')

  const selectedType = Form.useWatch(['order', 'tipo'], form) || 'vestido'
  const discount = Form.useWatch(['order', 'descuento'], form)
  const isTravel = Form.useWatch(['order', 'viaje'], form)
  const selectedCountry = Form.useWatch(['order', 'pais_destino'], form)

  const clientOptions = useMemo(
    () => clients.map((client) => ({ label: `${client.codigo} - ${client.full_name}`, value: client.id })),
    [clients],
  )
  const currencyOptions = useMemo(
    () => currencies.map((currency) => ({ label: `${currency.codigo} - ${currency.nombre}`, value: currency.id })),
    [currencies],
  )
  const countryOptions = useMemo(
    () => TRAVEL_DESTINATIONS.map((item) => ({ label: item.country, value: item.country })),
    [],
  )
  const cityOptions = useMemo(() => {
    const selected = TRAVEL_DESTINATIONS.find((item) => item.country === selectedCountry)
    return (selected?.cities || []).map((city) => ({ label: city, value: city }))
  }, [selectedCountry])
  const visualCurrency = useMemo(
    () => currencies.find((currency) => currency.id === visualCurrencyId) || currencies.find((currency) => currency.es_base) || null,
    [currencies, visualCurrencyId],
  )
  const visualExchangeRate = useMemo(() => {
    if (!visualCurrency || visualCurrency.es_base) return 1
    return exchangeRates.find((rate) => rate.moneda?.id === visualCurrency.id && rate.activo)?.valor_bob || 1
  }, [exchangeRates, visualCurrency])

  const loadReferences = useCallback(async () => {
    const [clientResponse, currencyResponse, exchangeRateResponse] = await Promise.all([
      apiClient.get('/clientes', { params: { is_active: true } }),
      apiClient.get('/monedas', { params: { is_active: true } }),
      apiClient.get('/monedas/tipos-cambio', { params: { is_active: true } }),
    ])
    setClients(clientResponse.data)
    setCurrencies(currencyResponse.data)
    setExchangeRates(exchangeRateResponse.data)
    if (!visualCurrencyId) {
      const baseCurrency = currencyResponse.data.find((currency) => currency.es_base)
      setVisualCurrencyId(baseCurrency?.id || null)
    }
  }, [visualCurrencyId])

  const loadOrders = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const params = {}
      if (filters.search) params.search = filters.search
      if (filters.state) params.state = filters.state
      if (filters.type) params.type = filters.type
      if (typeof filters.only_travel === 'boolean') params.only_travel = filters.only_travel
      const response = await apiClient.get('/pedidos', { params })
      setOrders(response.data)
    } catch (requestError) {
      setError(requestError.response?.data?.detail || 'No fue posible cargar los pedidos.')
    } finally {
      setLoading(false)
    }
  }, [filters])

  useEffect(() => {
    Promise.all([loadReferences(), loadOrders()]).catch(() => {
      setError('No fue posible cargar la información inicial de pedidos.')
      setLoading(false)
    })
  }, [])

  useEffect(() => {
    loadOrders()
  }, [filters.search, filters.state, filters.type, filters.only_travel])

  const openCreate = () => {
    setEditingOrder(null)
    setFormError(null)
    form.resetFields()
    form.setFieldsValue({ order: { tipo: 'vestido', precio: 0, viaje: false }, detail: {} })
    setDrawerOpen(true)
  }

  const openEdit = async (record) => {
    try {
      const response = await apiClient.get(`/pedidos/${record.id}`)
      const order = response.data
      setEditingOrder(order)
      form.setFieldsValue({
        order: {
          codigo: order.codigo,
          client_id: order.client.id,
          tipo: order.tipo,
          fecha_entrega: order.fecha_entrega ? dayjs(order.fecha_entrega) : null,
          viaje: order.viaje,
          pais_destino: order.pais_destino,
          ciudad_destino: order.ciudad_destino,
          precio: order.precio,
          descuento: order.descuento,
          motivo_descuento: order.motivo_descuento,
          observaciones: order.observaciones,
        },
        detail: order.detail || {},
      })
      setFormError(null)
      setDrawerOpen(true)
    } catch (requestError) {
      message.error(requestError.response?.data?.detail || 'No fue posible cargar el pedido.')
    }
  }

  const openDetail = async (record) => {
    try {
      const response = await apiClient.get(`/pedidos/${record.id}`)
      setDetail(response.data)
      setDetailOpen(true)
    } catch (requestError) {
      message.error(requestError.response?.data?.detail || 'No fue posible cargar el detalle del pedido.')
    }
  }

  const closeDrawer = () => {
    setDrawerOpen(false)
    setEditingOrder(null)
    setFormError(null)
    form.resetFields()
  }

  const submitOrder = async (values) => {
    setSaving(true)
    setFormError(null)
    try {
      const payload = {
        order: {
          ...values.order,
          fecha_entrega: values.order.fecha_entrega.format('YYYY-MM-DD'),
          descuento: values.order.descuento ?? null,
          motivo_descuento: values.order.descuento ? values.order.motivo_descuento : null,
          ciudad_destino: values.order.viaje ? values.order.ciudad_destino || null : null,
          pais_destino: values.order.viaje ? values.order.pais_destino || null : null,
        },
        detail: values.detail,
      }
      if (editingOrder) {
        await apiClient.patch(`/pedidos/${editingOrder.id}`, payload)
        message.success('Se actualizó el pedido correctamente.')
      } else {
        await apiClient.post('/pedidos', payload)
        message.success('Se registró el pedido correctamente.')
      }
      closeDrawer()
      await loadOrders()
    } catch (requestError) {
      const resolved = applyFormApiError(form, requestError, {
        messageFieldMap: [
          { test: /cliente/i, field: ['order', 'client_id'] },
          { test: /descuento/i, field: ['order', 'descuento'] },
          { test: /detalle/i, field: ['detail'] },
          { test: /código|codigo/i, field: ['order', 'codigo'] },
          { test: /fecha de entrega/i, field: ['order', 'fecha_entrega'] },
          { test: /país|pais/i, field: ['order', 'pais_destino'] },
          { test: /ciudad/i, field: ['order', 'ciudad_destino'] },
        ],
      })
      setFormError(resolved.message)
    } finally {
      setSaving(false)
    }
  }

  const executeStatusChange = async (payload, successMessage) => {
    await apiClient.patch(`/pedidos/${action.record.id}/status`, payload)
    message.success(successMessage)
    setAction(null)
    actionForm.resetFields()
    await loadOrders()
  }

  const submitAction = async (values) => {
    if (!action) return
    setSaving(true)
    try {
      if (action.type === 'deliver') {
        await apiClient.patch(`/pedidos/${action.record.id}/deliver`, {
          fecha_entrega_final: values.fecha_entrega_final.format('YYYY-MM-DD'),
          observaciones: values.observaciones,
        })
        message.success('Se marcó el pedido como entregado correctamente.')
        setAction(null)
        actionForm.resetFields()
        await loadOrders()
      } else if (action.type === 'cancelado' && Number(action.record.total_pagado || 0) > 0) {
        const reason = values.reason
        modal.confirm({
          title: 'Confirmación final de cancelación',
          content: 'Este pedido tiene pagos registrados. Si continúas, quedará cancelado y la acción no se podrá revertir.',
          okText: 'Sí, cancelar pedido',
          cancelText: 'Volver',
          okButtonProps: { danger: true },
          centered: true,
          onOk: async () => {
            await executeStatusChange({ target_state: action.type, reason }, 'Se canceló el pedido correctamente.')
          },
        })
      } else {
        await executeStatusChange(
          { target_state: action.type, reason: values.reason },
          action.type === 'cancelado' ? 'Se canceló el pedido correctamente.' : 'Se actualizó el estado del pedido correctamente.',
        )
      }
    } catch (requestError) {
      message.error(requestError.response?.data?.detail || 'No fue posible completar la acción.')
    } finally {
      setSaving(false)
    }
  }

  const columns = [
    { title: 'CÓDIGO', dataIndex: 'codigo' },
    { title: 'CLIENTE', dataIndex: 'client_name' },
    { title: 'TIPO', dataIndex: 'tipo', render: (value) => labelFromOptions(TIPO_PEDIDO_OPTIONS, value) },
    { title: 'ENTREGA', dataIndex: 'fecha_entrega' },
    {
      title: `TOTAL ${visualCurrency?.codigo || 'BOB'}`,
      dataIndex: 'precio_total',
      render: (value) => formatConvertedMoney(value, visualCurrency, visualExchangeRate),
    },
    {
      title: `PAGADO ${visualCurrency?.codigo || 'BOB'}`,
      dataIndex: 'total_pagado',
      render: (value) => formatConvertedMoney(value, visualCurrency, visualExchangeRate),
    },
    {
      title: `SALDO ${visualCurrency?.codigo || 'BOB'}`,
      dataIndex: 'saldo',
      render: (value) => formatConvertedMoney(value, visualCurrency, visualExchangeRate),
    },
    { title: 'ESTADO', dataIndex: 'estado_general', render: (value) => <Tag color={orderStateColor(value)}>{labelFromOptions(ESTADO_PEDIDO_OPTIONS, value)}</Tag> },
    {
      title: 'ACCIONES',
      render: (_, record) => (
        <Row gutter={[8, 8]}>
          {canView ? <Col><Button icon={<EyeOutlined />} onClick={() => openDetail(record)}>Ver</Button></Col> : null}
          {canUpdate && record.estado_general === 'activo' ? <Col><Button icon={<EditOutlined />} onClick={() => openEdit(record)}>Editar</Button></Col> : null}
          {canDeliver && record.estado_general === 'activo' ? <Col><Button icon={<CheckCircleOutlined />} onClick={() => setAction({ type: 'deliver', record })}>Entregar</Button></Col> : null}
          {canStatus && record.estado_general === 'activo' ? <Col><Button danger icon={<CloseCircleOutlined />} onClick={() => setAction({ type: 'cancelado', record })}>Cancelar</Button></Col> : null}
          {canStatus && record.estado_general === 'activo' ? <Col><Button icon={<StopOutlined />} onClick={() => setAction({ type: 'inactivo', record })}>Inactivar</Button></Col> : null}
        </Row>
      ),
    },
  ]

  return (
    <>
      <Row gutter={[16, 16]} align="middle" style={{ marginBottom: 16 }}>
        <Col flex="auto">
          <Typography.Title level={3} style={{ margin: 0 }}>Pedidos</Typography.Title>
          <Typography.Text type="secondary">Contratos, detalles de confección, pruebas, pagos y saldo del cliente.</Typography.Text>
        </Col>
        <Col xs={24} md={6}>
          <Select
            placeholder="Moneda visual"
            options={currencyOptions}
            value={visualCurrencyId}
            onChange={setVisualCurrencyId}
            style={{ width: '100%' }}
          />
        </Col>
        {canCreate ? <Col><Button type="primary" icon={<PlusOutlined />} onClick={openCreate}>Nuevo pedido</Button></Col> : null}
      </Row>
      {error ? <Alert type="error" message={error} showIcon style={{ marginBottom: 16 }} /> : null}
      <Row gutter={[12, 12]} style={{ marginBottom: 16 }}>
        <Col xs={24} md={8}><Input prefix={<SearchOutlined />} placeholder="Buscar por código, cliente o CI" value={filters.search} onChange={(event) => setFilters((current) => ({ ...current, search: event.target.value }))} /></Col>
        <Col xs={24} md={5}><Select allowClear placeholder="Filtrar por estado" options={ESTADO_PEDIDO_OPTIONS} value={filters.state} onChange={(value) => setFilters((current) => ({ ...current, state: value }))} style={{ width: '100%' }} /></Col>
        <Col xs={24} md={5}><Select allowClear placeholder="Filtrar por tipo" options={TIPO_PEDIDO_OPTIONS} value={filters.type} onChange={(value) => setFilters((current) => ({ ...current, type: value }))} style={{ width: '100%' }} /></Col>
        <Col xs={24} md={4}><Select allowClear placeholder="Viaje" options={[{ value: true, label: 'SOLO VIAJE' }, { value: false, label: 'SIN VIAJE' }]} value={filters.only_travel} onChange={(value) => setFilters((current) => ({ ...current, only_travel: value }))} style={{ width: '100%' }} /></Col>
      </Row>
      {visualCurrency && !visualCurrency.es_base ? (
        <Alert
          type="info"
          showIcon
          style={{ marginBottom: 16 }}
          message={`Visualización convertida a ${visualCurrency.codigo}. Tipo de cambio usado solo para consulta: 1 ${visualCurrency.codigo} = ${Number(visualExchangeRate).toFixed(4)} Bs.`}
        />
      ) : null}
      <Table rowKey="id" columns={columns} dataSource={orders} loading={loading} scroll={{ x: 1300 }} />

      <Drawer title={editingOrder ? 'Editar pedido' : 'Nuevo pedido'} width={980} open={drawerOpen} onClose={closeDrawer} maskClosable={false} destroyOnClose>
        <Form form={form} layout="vertical" onFinish={submitOrder} {...FORM_COMMON_PROPS}>
          <FormProcessAlert error={formError} />
          <Typography.Title level={5}>Datos principales</Typography.Title>
          <Row gutter={16}>
            <Col xs={24} md={8}>
              <Form.Item
                name={['order', 'codigo']}
                label="Código"
                extra="Si lo dejas vacío, el sistema generará el código automáticamente."
                normalize={uppercaseCode}
              >
                <Input placeholder="Ej. PED-00001" />
              </Form.Item>
            </Col>
            <Col xs={24} md={8}><Form.Item name={['order', 'client_id']} label="Cliente" rules={[{ required: true, message: 'Debe seleccionar el cliente.' }]}><Select showSearch placeholder="Busca y selecciona cliente" options={clientOptions} optionFilterProp="label" /></Form.Item></Col>
            <Col xs={24} md={8}><Form.Item name={['order', 'tipo']} label="Tipo de pedido" rules={[{ required: true, message: 'Debe seleccionar el tipo.' }]}><Select disabled={Boolean(editingOrder)} placeholder="Selecciona el tipo" options={TIPO_PEDIDO_OPTIONS} /></Form.Item></Col>
            <Col xs={24} md={8}><Form.Item name={['order', 'fecha_entrega']} label="Fecha de entrega" rules={[{ required: true, message: 'Debe seleccionar la entrega.' }]}><DatePicker disabledDate={(current) => current && current.startOf('day').isBefore(dayjs().startOf('day'))} format="DD/MM/YYYY" placeholder="Selecciona fecha de entrega" style={{ width: '100%' }} /></Form.Item></Col>
            <Col xs={24} md={8}><Form.Item name={['order', 'precio']} label="Precio base Bs" rules={[{ required: true, message: 'Debe ingresar el precio.' }]}><InputNumber min={0} placeholder="Ej. 2500" style={{ width: '100%' }} /></Form.Item></Col>
            <Col xs={24} md={8}><Form.Item name={['order', 'descuento']} label="Descuento Bs" extra="Se habilita solo cuando registras un descuento real."><InputNumber min={0} placeholder="Ej. 100" style={{ width: '100%' }} /></Form.Item></Col>
            {discount ? <Col xs={24} md={8}><Form.Item name={['order', 'motivo_descuento']} label="Motivo del descuento" rules={[{ required: true, message: 'Debe seleccionar el motivo.' }]}><Select placeholder="Selecciona motivo" options={MOTIVO_DESCUENTO_OPTIONS} /></Form.Item></Col> : null}
            <Col xs={24} md={8}><Form.Item name={['order', 'viaje']} label="Pedido de viaje" valuePropName="checked"><Switch checkedChildren="SI" unCheckedChildren="NO" /></Form.Item></Col>
            {isTravel ? <Col xs={24} md={8}><Form.Item name={['order', 'pais_destino']} label="País destino" rules={[{ required: true, message: 'Debe seleccionar el país destino.' }]}><Select showSearch placeholder="Selecciona país destino" options={countryOptions} optionFilterProp="label" onChange={() => form.setFieldValue(['order', 'ciudad_destino'], undefined)} /></Form.Item></Col> : null}
            {isTravel ? <Col xs={24} md={8}><Form.Item name={['order', 'ciudad_destino']} label="Ciudad destino" rules={[{ required: true, message: 'Debe seleccionar la ciudad destino.' }]}><Select showSearch placeholder="Selecciona ciudad destino" options={cityOptions} optionFilterProp="label" /></Form.Item></Col> : null}
            <Col xs={24}><Form.Item name={['order', 'observaciones']} label="Observaciones" normalize={uppercaseText}><Input.TextArea rows={2} placeholder="Observaciones del pedido" /></Form.Item></Col>
          </Row>
          <Typography.Title level={5}>Detalle especializado</Typography.Title>
          <DetailFields type={selectedType} form={form} />
          <Row justify="end" gutter={12}>
            <Col><Button onClick={closeDrawer}>Cancelar</Button></Col>
            <Col><Button type="primary" htmlType="submit" loading={saving} {...FORM_DRAWER_SUBMIT_PROPS}>Guardar</Button></Col>
          </Row>
        </Form>
      </Drawer>

      <Drawer title="Detalle del pedido" width={900} open={detailOpen} onClose={() => setDetailOpen(false)} maskClosable={false}>
        {detail ? <OrderDetail detail={detail} visualCurrency={visualCurrency} visualExchangeRate={visualExchangeRate} /> : null}
      </Drawer>

      <Modal title={action?.type === 'deliver' ? 'Confirmar entrega' : 'Confirmar cambio de estado'} open={Boolean(action)} onCancel={() => setAction(null)} onOk={() => actionForm.submit()} confirmLoading={saving} maskClosable={false}>
        <Form form={actionForm} layout="vertical" onFinish={submitAction}>
          {action?.type === 'deliver' ? (
            <>
              <Alert type="info" showIcon message="La entrega exige saldo 0 y cerrará el pedido como ENTREGADO." style={{ marginBottom: 12 }} />
              <Form.Item name="fecha_entrega_final" label="Fecha final de entrega" rules={[{ required: true, message: 'Debe seleccionar la fecha final.' }]}><DatePicker disabledDate={(current) => current && current.startOf('day').isBefore(dayjs().startOf('day'))} format="DD/MM/YYYY" placeholder="Selecciona fecha final" style={{ width: '100%' }} /></Form.Item>
              <Form.Item name="observaciones" label="Observaciones" normalize={uppercaseText}><Input.TextArea rows={3} placeholder="Observaciones de entrega" /></Form.Item>
            </>
          ) : (
            <>
              <Alert type="warning" showIcon message={action?.type === 'cancelado' && Number(action?.record?.total_pagado || 0) > 0 ? 'Este pedido tiene pagos registrados. Después del motivo se pedirá una confirmación final irreversible.' : 'Esta acción queda auditada en el sistema.'} style={{ marginBottom: 12 }} />
              <Form.Item name="reason" label="Motivo" rules={[{ required: true, message: 'Debe escribir el motivo.' }, { min: 5, message: 'El motivo debe ser más específico.' }]} normalize={uppercaseText}><Input.TextArea rows={3} placeholder="Describe el motivo del cambio" /></Form.Item>
            </>
          )}
        </Form>
      </Modal>
    </>
  )
}

function DetailFields({ type, form }) {
  if (type === 'vestido') {
    return (
      <Row gutter={16}>
        <Col xs={24} md={8}><Form.Item name={['detail', 'tipo_vestido']} label="Tipo de vestido" rules={[{ required: true, message: 'Debe seleccionar el tipo de vestido.' }]}><Select placeholder="Selecciona tipo de vestido" options={TIPO_VESTIDO_OPTIONS} /></Form.Item></Col>
        <Col xs={24} md={8}><ColorPickerItem form={form} namePath={['detail', 'color_principal']} label="Color principal" required /></Col>
        <Col xs={24} md={8}><ColorPickerItem form={form} namePath={['detail', 'color_secundario']} label="Color secundario" isSecondary /></Col>
        <Col xs={24} md={12}><Form.Item name={['detail', 'descripcion_material']} label="Material" rules={[{ required: true, message: 'Debe describir el material.' }]} normalize={uppercaseText}><Input.TextArea rows={2} placeholder="Materiales principales" /></Form.Item></Col>
        <Col xs={24} md={12}><Form.Item name={['detail', 'descripcion_diseno']} label="Diseño" rules={[{ required: true, message: 'Debe describir el diseño.' }]} normalize={uppercaseText}><Input.TextArea rows={2} placeholder="Diseño solicitado" /></Form.Item></Col>
        <Col xs={24}><Form.Item name={['detail', 'descripcion_adicional']} label="Descripción adicional" normalize={uppercaseText}><Input.TextArea rows={2} placeholder="Detalle adicional del modelo" /></Form.Item></Col>
        {[
          ['ancho_espalda', 'ANCHO ESPALDA'],
          ['talle_espalda', 'TALLE ESPALDA'],
          ['talle_delantero', 'TALLE DELANTERO'],
          ['contorno_cintura', 'CONTORNO CINTURA'],
          ['contorno_cadera', 'CONTORNO CADERA'],
          ['largo_falda', 'LARGO FALDA'],
          ['sisa', 'SISA'],
          ['ancho_busto', 'ANCHO BUSTO'],
          ['separacion_busto', 'SEPARACION BUSTO'],
          ['talle_busto', 'TALLE BUSTO'],
          ['talle_costado', 'TALLE COSTADO'],
        ].map(([field, label]) => (
          <Col xs={12} md={6} key={field}>
            <Form.Item name={['detail', field]} label={label}>
              <InputNumber min={0} placeholder="0" style={{ width: '100%' }} />
            </Form.Item>
          </Col>
        ))}
        <Col xs={24}><Form.Item name={['detail', 'observaciones']} label="Observaciones" normalize={uppercaseText}><Input.TextArea rows={2} placeholder="Observaciones del detalle de vestido" /></Form.Item></Col>
      </Row>
    )
  }

  if (type === 'otro') {
    return (
      <Row gutter={16}>
        <Col xs={24} md={8}><Form.Item name={['detail', 'nombre']} label="Nombre" rules={[{ required: true, message: 'Debe ingresar el nombre.' }]} normalize={uppercaseText}><Input placeholder="Ej. ACCESORIO ESPECIAL" /></Form.Item></Col>
        <CommonColorAndMeasures form={form} />
        <Col xs={24}><Form.Item name={['detail', 'descripcion']} label="Descripción" normalize={uppercaseText}><Input.TextArea rows={2} placeholder="Descripción del pedido" /></Form.Item></Col>
        <Col xs={24}><Form.Item name={['detail', 'observaciones']} label="Observaciones" normalize={uppercaseText}><Input.TextArea rows={2} placeholder="Observaciones del detalle" /></Form.Item></Col>
      </Row>
    )
  }

  return (
    <Row gutter={16}>
      <Col xs={24} md={8}><Form.Item name={['detail', 'tipo']} label={`Tipo de ${labelFromOptions(TIPO_PEDIDO_OPTIONS, type)}`} rules={[{ required: type === 'bouquet', message: 'Debe ingresar el tipo.' }]} normalize={uppercaseText}><Input placeholder="Ej. CATEDRAL, REDONDO, LARGO" /></Form.Item></Col>
      <CommonColorAndMeasures lengthField={type === 'manga' ? 'largo_manga' : 'largo'} form={form} />
      {type === 'manga' ? <Col xs={24} md={8}><Form.Item name={['detail', 'brazo']} label="Brazo" rules={[{ required: true, message: 'Debe ingresar la medida del brazo.' }]}><InputNumber min={0} placeholder="0" style={{ width: '100%' }} /></Form.Item></Col> : null}
      {type === 'manga' ? <Col xs={24} md={8}><Form.Item name={['detail', 'puno']} label="Puño" rules={[{ required: true, message: 'Debe ingresar la medida del puño.' }]}><InputNumber min={0} placeholder="0" style={{ width: '100%' }} /></Form.Item></Col> : null}
      {type === 'velo' ? <Col xs={24} md={8}><Form.Item name={['detail', 'capas']} label="Capas"><InputNumber min={1} placeholder="Ej. 2" style={{ width: '100%' }} /></Form.Item></Col> : null}
      {type === 'velo' ? <Col xs={24} md={8}><Form.Item name={['detail', 'borde']} label="Borde" normalize={uppercaseText}><Input placeholder="Ej. ENCAJE FINO" /></Form.Item></Col> : null}
      <Col xs={24} md={8}><Form.Item name={['detail', 'material']} label="Material" normalize={uppercaseText}><Input placeholder="Ej. TUL, SATEN" /></Form.Item></Col>
      <Col xs={24} md={8}><Form.Item name={['detail', 'decoracion']} label="Decoración" normalize={uppercaseText}><Input placeholder="Ej. PERLAS" /></Form.Item></Col>
      {type === 'bouquet' ? <Col xs={24} md={8}><Form.Item name={['detail', 'tipo_flor']} label="Tipo de flor" normalize={uppercaseText}><Input placeholder="Ej. ROSAS" /></Form.Item></Col> : null}
      <Col xs={24}><Form.Item name={['detail', 'observaciones']} label="Observaciones" normalize={uppercaseText}><Input.TextArea rows={2} placeholder="Observaciones del detalle" /></Form.Item></Col>
    </Row>
  )
}

function CommonColorAndMeasures({ lengthField = 'largo', form } = {}) {
  return (
    <>
      <Col xs={24} md={8}><ColorPickerItem form={form} namePath={['detail', 'color_principal']} label="Color principal" required /></Col>
      <Col xs={24} md={8}><ColorPickerItem form={form} namePath={['detail', 'color_secundario']} label="Color secundario" isSecondary /></Col>
      <Col xs={24} md={8}><Form.Item name={['detail', lengthField]} label={lengthField === 'largo_manga' ? 'Largo manga' : 'Largo'} rules={[{ required: true, message: 'Debe ingresar el largo.' }]}><InputNumber min={0} placeholder="0" style={{ width: '100%' }} /></Form.Item></Col>
      <Col xs={24} md={8}><Form.Item name={['detail', 'ancho']} label="Ancho"><InputNumber min={0} placeholder="0" style={{ width: '100%' }} /></Form.Item></Col>
    </>
  )
}

function OrderDetail({ detail, visualCurrency, visualExchangeRate }) {
  return (
    <>
      <Row gutter={[16, 16]} style={{ marginBottom: 16 }}>
        <Col xs={24} md={8}><Card size="small"><strong>TOTAL</strong><div>{formatBs(detail.precio_total)}</div><div>{formatConvertedMoney(detail.precio_total, visualCurrency, visualExchangeRate)}</div></Card></Col>
        <Col xs={24} md={8}><Card size="small"><strong>PAGADO</strong><div>{formatBs(detail.total_pagado)}</div><div>{formatConvertedMoney(detail.total_pagado, visualCurrency, visualExchangeRate)}</div></Card></Col>
        <Col xs={24} md={8}><Card size="small"><strong>SALDO</strong><div>{formatBs(detail.saldo)}</div><div>{formatConvertedMoney(detail.saldo, visualCurrency, visualExchangeRate)}</div></Card></Col>
      </Row>
      <Descriptions bordered column={2} size="small">
        <Descriptions.Item label="Código">{detail.codigo}</Descriptions.Item>
        <Descriptions.Item label="Cliente">{detail.client.full_name}</Descriptions.Item>
        <Descriptions.Item label="Tipo">{labelFromOptions(TIPO_PEDIDO_OPTIONS, detail.tipo)}</Descriptions.Item>
        <Descriptions.Item label="Estado"><Tag color={orderStateColor(detail.estado_general)}>{labelFromOptions(ESTADO_PEDIDO_OPTIONS, detail.estado_general)}</Tag></Descriptions.Item>
        <Descriptions.Item label="Fecha contrato">{detail.fecha_contrato}</Descriptions.Item>
        <Descriptions.Item label="Fecha entrega">{detail.fecha_entrega}</Descriptions.Item>
        <Descriptions.Item label="Viaje">{detail.viaje ? 'SI' : 'NO'}</Descriptions.Item>
        <Descriptions.Item label="Destino">{[detail.pais_destino, detail.ciudad_destino].filter(Boolean).join(' / ') || 'SIN REGISTRO'}</Descriptions.Item>
        <Descriptions.Item label="Observaciones" span={2}>{detail.observaciones || 'SIN OBSERVACIONES'}</Descriptions.Item>
      </Descriptions>
      <Typography.Title level={5} style={{ marginTop: 20 }}>Detalle especializado</Typography.Title>
      <Descriptions bordered column={2} size="small">
        {Object.entries(detail.detail || {}).map(([key, value]) => (
          <Descriptions.Item key={key} label={key.replaceAll('_', ' ').toUpperCase()}>
            {String(value ?? 'SIN REGISTRO').toUpperCase()}
          </Descriptions.Item>
        ))}
      </Descriptions>
      <Typography.Title level={5} style={{ marginTop: 20 }}>Pagos registrados</Typography.Title>
      <Space direction="vertical" style={{ width: '100%' }} size={8}>
        {detail.pagos.length ? detail.pagos.map((payment) => (
          <Card key={payment.id} size="small">
            <strong>{payment.metodo_pago.toUpperCase()}</strong> | {payment.fecha} | {formatBs(payment.monto_bob)} | {payment.estado.toUpperCase()}
          </Card>
        )) : <Alert type="info" showIcon message="Este pedido todavía no tiene pagos registrados." />}
      </Space>
      <Typography.Title level={5} style={{ marginTop: 20 }}>Pruebas registradas</Typography.Title>
      <Space direction="vertical" style={{ width: '100%' }} size={8}>
        {detail.pruebas.length ? detail.pruebas.map((test) => (
          <Card key={test.id} size="small">
            <strong>{test.numero}° PRUEBA</strong> | {test.fecha} {test.hora || ''} | {test.estado.toUpperCase()}
          </Card>
        )) : <Alert type="info" showIcon message="Este pedido todavía no tiene pruebas registradas." />}
      </Space>
    </>
  )
}

function ColorPickerItem({ form, namePath, label, required = false, isSecondary = false }) {
  const [modalOpen, setModalOpen] = useState(false)
  const selectedColor = Form.useWatch(namePath, form)
  const fieldErrors = form.getFieldError(namePath)

  return (
    <Form.Item
      label={label}
      required={required}
      validateStatus={fieldErrors.length ? 'error' : undefined}
      help={fieldErrors[0]}
    >
      <>
        <Form.Item
          name={namePath}
          rules={required ? [{ required: true, message: `Debe ingresar el ${label.toLowerCase()}.` }] : undefined}
          hidden
          preserve
        >
          <Input />
        </Form.Item>
        <div
          onClick={() => setModalOpen(true)}
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: 10,
            border: `1px solid ${fieldErrors.length ? '#ff4d4f' : '#d9d9d9'}`,
            borderRadius: 8,
            padding: '6px 12px',
            cursor: 'pointer',
            background: '#fff',
            transition: 'border-color 0.2s',
            minHeight: 40,
          }}
          onMouseEnter={(e) => {
            if (!fieldErrors.length) {
              e.currentTarget.style.borderColor = '#8f3d2e'
            }
          }}
          onMouseLeave={(e) => {
            e.currentTarget.style.borderColor = fieldErrors.length ? '#ff4d4f' : '#d9d9d9'
          }}
        >
          {selectedColor ? (
            <>
              <div
                style={{
                  width: 26,
                  height: 26,
                  borderRadius: 6,
                  background: COLOR_MAP[selectedColor] || '#e0e0e0',
                  border: '1.5px solid rgba(0,0,0,0.15)',
                  flexShrink: 0,
                }}
              />
              <span style={{ fontWeight: 500 }}>{selectedColor}</span>
            </>
          ) : (
            <span style={{ color: '#aaa' }}>
              <BgColorsOutlined style={{ marginRight: 6 }} />
              {isSecondary ? 'Opcional' : 'Seleccionar color'}
            </span>
          )}
          {isSecondary && selectedColor ? (
            <Button
              size="small"
              type="text"
              danger
              onClick={(e) => {
                e.stopPropagation()
                form.setFieldValue(namePath, null)
                form.validateFields([namePath])
              }}
            >
              Quitar
            </Button>
          ) : null}
          <Button
            size="small"
            type="link"
            style={{ marginLeft: isSecondary && selectedColor ? '0' : 'auto', fontSize: 12 }}
            onClick={(e) => {
              e.stopPropagation()
              setModalOpen(true)
            }}
          >
            {selectedColor ? 'Cambiar' : 'Seleccionar'}
          </Button>
        </div>
        <ColorPickerModal
          open={modalOpen}
          onSelect={(colorName) => {
            form.setFieldValue(namePath, colorName)
            form.validateFields([namePath])
            setModalOpen(false)
          }}
          onCancel={() => setModalOpen(false)}
        />
      </>
    </Form.Item>
  )
}
