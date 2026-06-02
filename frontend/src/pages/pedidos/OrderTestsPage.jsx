import { EditOutlined, PlusOutlined, SearchOutlined } from '@ant-design/icons'
import { Alert, App as AntdApp, Badge, Button, Calendar, Card, Col, DatePicker, Descriptions, Drawer, Form, Input, InputNumber, Row, Select, Segmented, Table, Tag, TimePicker, Typography } from 'antd'
import dayjs from 'dayjs'
import { useCallback, useEffect, useMemo, useState } from 'react'

import { apiClient } from '../../api/client'
import { useAuth } from '../../auth/AuthProvider'
import { FORM_COMMON_PROPS, FORM_DRAWER_SUBMIT_PROPS } from '../../components/forms/formConfig'
import { ESTADO_PRUEBA_OPTIONS, TIPO_PEDIDO_OPTIONS, labelFromOptions, testNumberColor, testStateColor } from './orderConstants'

export function OrderTestsPage() {
  const [tests, setTests] = useState([])
  const [orders, setOrders] = useState([])
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState(null)
  const [filters, setFilters] = useState({ search: '', state: undefined })
  const [viewMode, setViewMode] = useState('mes')
  const [selectedDay, setSelectedDay] = useState(dayjs())
  const [drawerOpen, setDrawerOpen] = useState(false)
  const [editingTest, setEditingTest] = useState(null)
  const [detail, setDetail] = useState(null)
  const [form] = Form.useForm()
  const { message } = AntdApp.useApp()
  const { user } = useAuth()

  const canCreate = user?.permissions?.includes('order_tests:create')
  const canUpdate = user?.permissions?.includes('order_tests:update')

  const orderOptions = useMemo(
    () => orders.filter((order) => order.estado_general === 'activo').map((order) => ({ label: `${order.codigo} - ${order.client_name}`, value: order.id })),
    [orders],
  )

  const loadReferences = useCallback(async () => {
    const response = await apiClient.get('/pedidos', { params: { state: 'activo' } })
    setOrders(response.data)
  }, [])

  const loadTests = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const params = {}
      if (filters.search) params.search = filters.search
      if (filters.state) params.state = filters.state
      const response = await apiClient.get('/pedidos/pruebas', { params })
      setTests(response.data)
    } catch (requestError) {
      setError(requestError.response?.data?.detail || 'No fue posible cargar las pruebas.')
    } finally {
      setLoading(false)
    }
  }, [filters])

  useEffect(() => {
    loadReferences().catch(() => {
      setError('No fue posible cargar la agenda de pruebas.')
      setLoading(false)
    })
  }, [loadReferences])

  useEffect(() => {
    loadTests()
  }, [loadTests])

  const openCreate = () => {
    setEditingTest(null)
    form.resetFields()
    form.setFieldsValue({ numero: 1, estado: 'costurero_taller' })
    setDrawerOpen(true)
  }

  const openEdit = (record) => {
    setEditingTest(record)
    form.setFieldsValue({
      order_id: record.pedido_id,
      numero: record.numero,
      fecha: dayjs(record.fecha),
      hora: record.hora ? dayjs(record.hora, 'HH:mm:ss') : null,
      estado: record.estado,
      observaciones: record.observaciones,
    })
    setDrawerOpen(true)
  }

  const openDetail = (record) => {
    setDetail(record)
    setSelectedDay(dayjs(record.fecha))
  }

  const submitTest = async (values) => {
    setSaving(true)
    try {
      const payload = {
        numero: values.numero,
        fecha: values.fecha.format('YYYY-MM-DD'),
        hora: values.hora ? values.hora.format('HH:mm:ss') : null,
        estado: values.estado,
        observaciones: values.observaciones,
      }
      if (editingTest) {
        await apiClient.patch(`/pedidos/pruebas/${editingTest.id}`, payload)
        message.success('Se actualizó la prueba correctamente.')
      } else {
        await apiClient.post(`/pedidos/${values.order_id}/pruebas`, payload)
        message.success('Se registró la prueba correctamente.')
      }
      setDrawerOpen(false)
      form.resetFields()
      await loadTests()
    } catch (requestError) {
      message.error(requestError.response?.data?.detail || 'No fue posible guardar la prueba.')
    } finally {
      setSaving(false)
    }
  }

  const testsByDay = useMemo(() => {
    const grouped = new Map()
    tests.forEach((test) => {
      const key = test.fecha
      grouped.set(key, [...(grouped.get(key) || []), test])
    })
    return grouped
  }, [tests])

  const visibleDayKey = selectedDay.format('YYYY-MM-DD')
  const visibleDayTests = useMemo(() => testsByDay.get(visibleDayKey) || [], [testsByDay, visibleDayKey])
  const visibleWeekTests = useMemo(() => {
    const start = selectedDay.startOf('week')
    const end = selectedDay.endOf('week')
    return tests.filter((test) => {
      const current = dayjs(test.fecha)
      return current.isAfter(start.subtract(1, 'day')) && current.isBefore(end.add(1, 'day'))
    })
  }, [tests, selectedDay])
  const hourSlots = useMemo(() => {
    const grouped = new Map()
    visibleDayTests.forEach((test) => {
      const slot = test.hora ? test.hora.slice(0, 5) : 'SIN HORA'
      grouped.set(slot, [...(grouped.get(slot) || []), test])
    })
    return [...grouped.entries()].sort(([left], [right]) => left.localeCompare(right))
  }, [visibleDayTests])

  const columns = [
    { title: 'PEDIDO', dataIndex: 'pedido_codigo' },
    { title: 'CLIENTE', dataIndex: 'client_name' },
    { title: 'TIPO', dataIndex: 'tipo', render: (value) => labelFromOptions(TIPO_PEDIDO_OPTIONS, value) },
    { title: 'N°', dataIndex: 'numero', render: (value) => <Badge color={testNumberColor(value)} text={`${value}° PRUEBA`} /> },
    { title: 'FECHA', dataIndex: 'fecha' },
    { title: 'HORA', dataIndex: 'hora', render: (value) => value || 'SIN HORA' },
    { title: 'ESTADO', dataIndex: 'estado', render: (value) => <Tag color={testStateColor(value)}>{labelFromOptions(ESTADO_PRUEBA_OPTIONS, value)}</Tag> },
    {
      title: 'ACCIONES',
      render: (_, record) => (
        <Row gutter={[8, 8]}>
          <Col><Button onClick={() => openDetail(record)}>Ver</Button></Col>
          {canUpdate ? <Col><Button icon={<EditOutlined />} onClick={() => openEdit(record)}>Editar</Button></Col> : null}
        </Row>
      ),
    },
  ]

  return (
    <>
      <Row gutter={[16, 16]} align="middle" style={{ marginBottom: 16 }}>
        <Col flex="auto">
          <Typography.Title level={3} style={{ margin: 0 }}>Pruebas de pedidos</Typography.Title>
          <Typography.Text type="secondary">Agenda operativa con vista diaria, semanal, mensual y agrupación por horas.</Typography.Text>
        </Col>
        {canCreate ? <Col><Button type="primary" icon={<PlusOutlined />} onClick={openCreate}>Registrar prueba</Button></Col> : null}
      </Row>
      {error ? <Alert type="error" message={error} showIcon style={{ marginBottom: 16 }} /> : null}
      <Row gutter={[12, 12]} style={{ marginBottom: 16 }}>
        <Col xs={24} md={8}><Input prefix={<SearchOutlined />} placeholder="Buscar pedido o cliente" value={filters.search} onChange={(event) => setFilters((current) => ({ ...current, search: event.target.value }))} /></Col>
        <Col xs={24} md={6}><Select allowClear placeholder="Estado de prueba" options={ESTADO_PRUEBA_OPTIONS} value={filters.state} onChange={(value) => setFilters((current) => ({ ...current, state: value }))} style={{ width: '100%' }} /></Col>
        <Col xs={24} md={5}><Segmented options={[{ value: 'dia', label: 'DÍA' }, { value: 'semana', label: 'SEMANA' }, { value: 'mes', label: 'MES' }]} value={viewMode} onChange={setViewMode} block /></Col>
      </Row>

      <Calendar
        fullscreen={false}
        value={selectedDay}
        onSelect={setSelectedDay}
        cellRender={(current) => {
          const daily = testsByDay.get(current.format('YYYY-MM-DD')) || []
          return daily.slice(0, 4).map((test) => (
            <div
              key={test.id}
              onClick={() => openDetail(test)}
              style={{ fontSize: 11, color: testNumberColor(test.numero), whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis', cursor: 'pointer' }}
            >
              {test.numero}° {test.client_name}
            </div>
          ))
        }}
      />

      {viewMode === 'dia' ? (
        <Row gutter={[16, 16]} style={{ marginTop: 16 }}>
          <Col xs={24} lg={10}>
            <Card title={`Agenda del día ${selectedDay.format('DD/MM/YYYY')}`}>
              {hourSlots.length ? hourSlots.map(([slot, items]) => (
                <div key={slot} style={{ marginBottom: 16, borderBottom: '1px solid #f0d6cf', paddingBottom: 12 }}>
                  <Typography.Text strong>{slot}</Typography.Text>
                  {items.map((item) => (
                    <Card key={item.id} size="small" style={{ marginTop: 8, borderLeft: `4px solid ${testNumberColor(item.numero)}` }}>
                      <strong>{item.numero}° PRUEBA</strong> | {item.client_name} | {item.pedido_codigo}
                      <div>{labelFromOptions(ESTADO_PRUEBA_OPTIONS, item.estado)}</div>
                    </Card>
                  ))}
                </div>
              )) : <Alert type="info" showIcon message="No hay pruebas registradas para este día." />}
            </Card>
          </Col>
          <Col xs={24} lg={14}><Table rowKey="id" columns={columns} dataSource={visibleDayTests} loading={loading} scroll={{ x: 900 }} /></Col>
        </Row>
      ) : null}

      {viewMode === 'semana' ? <Table rowKey="id" columns={columns} dataSource={visibleWeekTests} loading={loading} scroll={{ x: 900 }} style={{ marginTop: 16 }} /> : null}
      {viewMode === 'mes' ? <Table rowKey="id" columns={columns} dataSource={tests} loading={loading} scroll={{ x: 900 }} style={{ marginTop: 16 }} /> : null}

      <Drawer title={editingTest ? 'Editar prueba' : 'Registrar prueba'} width={620} open={drawerOpen} onClose={() => setDrawerOpen(false)} maskClosable={false} destroyOnClose>
        <Form form={form} layout="vertical" onFinish={submitTest} {...FORM_COMMON_PROPS}>
          <Row gutter={16}>
            <Col xs={24}>{!editingTest ? <Form.Item name="order_id" label="Pedido" rules={[{ required: true, message: 'Debe seleccionar el pedido.' }]}><Select showSearch placeholder="Selecciona pedido activo" options={orderOptions} optionFilterProp="label" /></Form.Item> : null}</Col>
            <Col xs={24} md={8}><Form.Item name="numero" label="Número de prueba" rules={[{ required: true, message: 'Debe ingresar el número.' }]}><InputNumber disabled={Boolean(editingTest)} min={1} placeholder="Ej. 1" style={{ width: '100%' }} /></Form.Item></Col>
            <Col xs={24} md={8}><Form.Item name="fecha" label="Fecha" rules={[{ required: true, message: 'Debe seleccionar la fecha.' }]}><DatePicker disabledDate={(current) => current && current.startOf('day').isBefore(dayjs().startOf('day'))} format="DD/MM/YYYY" placeholder="Selecciona fecha" style={{ width: '100%' }} /></Form.Item></Col>
            <Col xs={24} md={8}><Form.Item name="hora" label="Hora"><TimePicker format="HH:mm" placeholder="Selecciona hora" style={{ width: '100%' }} /></Form.Item></Col>
            <Col xs={24}><Form.Item name="estado" label="Estado" rules={[{ required: true, message: 'Debe seleccionar el estado.' }]}><Select placeholder="Selecciona estado" options={ESTADO_PRUEBA_OPTIONS} /></Form.Item></Col>
            <Col xs={24}><Form.Item name="observaciones" label="Observaciones" normalize={(value) => (value || '').toUpperCase()}><Input.TextArea rows={3} placeholder="Observaciones de prueba" /></Form.Item></Col>
          </Row>
          <Row justify="end" gutter={12}>
            <Col><Button onClick={() => setDrawerOpen(false)}>Cancelar</Button></Col>
            <Col><Button type="primary" htmlType="submit" loading={saving} {...FORM_DRAWER_SUBMIT_PROPS}>Guardar</Button></Col>
          </Row>
        </Form>
      </Drawer>

      <Drawer title="Detalle de prueba" width={520} open={Boolean(detail)} onClose={() => setDetail(null)} maskClosable={false}>
        {detail ? (
          <Descriptions bordered column={1} size="small">
            <Descriptions.Item label="Pedido">{detail.pedido_codigo}</Descriptions.Item>
            <Descriptions.Item label="Cliente">{detail.client_name}</Descriptions.Item>
            <Descriptions.Item label="Tipo">{labelFromOptions(TIPO_PEDIDO_OPTIONS, detail.tipo)}</Descriptions.Item>
            <Descriptions.Item label="Número">{`${detail.numero}° PRUEBA`}</Descriptions.Item>
            <Descriptions.Item label="Fecha">{detail.fecha}</Descriptions.Item>
            <Descriptions.Item label="Hora">{detail.hora || 'SIN HORA'}</Descriptions.Item>
            <Descriptions.Item label="Estado"><Tag color={testStateColor(detail.estado)}>{labelFromOptions(ESTADO_PRUEBA_OPTIONS, detail.estado)}</Tag></Descriptions.Item>
            <Descriptions.Item label="Observaciones">{detail.observaciones || 'SIN OBSERVACIONES'}</Descriptions.Item>
          </Descriptions>
        ) : null}
      </Drawer>
    </>
  )
}
