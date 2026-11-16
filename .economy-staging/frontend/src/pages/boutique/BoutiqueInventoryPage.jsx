/* eslint-disable react-hooks/exhaustive-deps */
import { EditOutlined, EyeOutlined, PlusOutlined, SearchOutlined } from '@ant-design/icons'
import {
  Alert,
  App as AntdApp,
  Button,
  Drawer,
  Form,
  Input,
  Modal,
  Row,
  Col,
  Select,
  Switch,
  Table,
  Tag,
  Typography,
} from 'antd'
import { useCallback, useEffect, useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'

import { apiClient } from '../../api/client'
import { useAuth } from '../../auth/AuthProvider'
import { applyFormApiError } from '../../components/forms/formErrorUtils'
import { FormProcessAlert } from '../../components/forms/FormProcessAlert'
import { ReportSummaryStrip } from '../../components/reports/ReportSummaryStrip'
import { useListingSummary } from '../../components/reports/useListingSummary'
import { BoutiqueItemDetailCard } from './BoutiqueItemDetailCard'
import { BoutiqueItemForm } from './BoutiqueItemForm'
import { getCategoryColor, inferDetailKindFromTypeName } from './boutiqueConstants'

export function BoutiqueInventoryPage() {
  const [items, setItems] = useState([])
  const [types, setTypes] = useState([])
  const [providers, setProviders] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [formError, setFormError] = useState(null)
  const [saving, setSaving] = useState(false)
  const [detailOpen, setDetailOpen] = useState(false)
  const [formOpen, setFormOpen] = useState(false)
  const [selectedItem, setSelectedItem] = useState(null)
  const [editingItem, setEditingItem] = useState(null)
  const [filters, setFilters] = useState({
    search: '',
    type_id: undefined,
    is_active: undefined,
    low_stock: false,
  })
  const [form] = Form.useForm()
  const { message } = AntdApp.useApp()
  const { user } = useAuth()
  const navigate = useNavigate()

  const canCreate = user?.permissions?.includes('boutique_items:create')
  const canUpdate = user?.permissions?.includes('boutique_items:update')
  const canUpdateStatus = user?.permissions?.includes('boutique_items:update_status')
  const canCreateEntry = user?.permissions?.includes('boutique_entries:create')
  const { summary, loading: summaryLoading } = useListingSummary('/boutique/items/resumen', filters)

  const loadReferences = useCallback(async () => {
    const [typesResponse, providersResponse] = await Promise.all([
      apiClient.get('/boutique/types'),
      apiClient.get('/boutique/proveedores', { params: { is_active: true } }),
    ])
    setTypes(typesResponse.data)
    setProviders(providersResponse.data)
  }, [])

  const loadItems = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const params = {}
      if (filters.search) params.search = filters.search
      if (filters.type_id) params.type_id = filters.type_id
      if (filters.is_active !== undefined) params.is_active = filters.is_active
      if (filters.low_stock) params.low_stock = true
      const response = await apiClient.get('/boutique/items', { params })
      setItems(response.data)
    } catch (requestError) {
      setError(requestError.response?.data?.detail || 'No fue posible cargar el inventario boutique.')
    } finally {
      setLoading(false)
    }
  }, [filters])

  useEffect(() => {
    Promise.all([loadReferences(), loadItems()]).catch(() => {
      setError('No fue posible cargar la información inicial del módulo boutique.')
      setLoading(false)
    })
  }, [])

  useEffect(() => {
    loadItems()
  }, [filters.search, filters.type_id, filters.is_active, filters.low_stock])

  const typeOptions = useMemo(() => types.map((type) => ({ label: type.nombre, value: type.id })), [types])

  const openCreate = () => {
    setEditingItem(null)
    setFormError(null)
    form.resetFields()
    form.setFieldsValue({
      item: { purchase_price: 0, sale_price: 0, stock: 0, stock_min: 0 },
    })
    setFormOpen(true)
  }

  const openEdit = async (record) => {
    setSaving(true)
    try {
      const response = await apiClient.get(`/boutique/items/${record.id}`)
      const item = response.data
      setEditingItem(item)
      setFormError(null)
      form.setFieldsValue({
        type_id: item.type.id,
        item: {
          code: item.code,
          name: item.name,
          provider_id: item.provider?.id,
          color_primary: item.color_primary,
          color_secondary: item.color_secondary,
          material: item.material,
          length: item.length,
          width: item.width,
          purchase_price: item.purchase_price,
          sale_price: item.sale_price,
          stock: item.stock,
          stock_min: item.stock_min,
          detail: item.detail_text,
        },
        detail: item.detail || {},
      })
      setFormOpen(true)
    } catch (requestError) {
      message.error(requestError.response?.data?.detail || 'No fue posible cargar el producto.')
    } finally {
      setSaving(false)
    }
  }

  const openView = async (record) => {
    try {
      const response = await apiClient.get(`/boutique/items/${record.id}`)
      setSelectedItem(response.data)
      setDetailOpen(true)
    } catch (requestError) {
      message.error(requestError.response?.data?.detail || 'No fue posible cargar el detalle del producto.')
    }
  }

  const handleSubmit = async (values) => {
    setSaving(true)
    setFormError(null)
    try {
      const selectedType = types.find((type) => type.id === values.type_id)
      const detailKind = inferDetailKindFromTypeName(selectedType?.nombre)

      if (editingItem) {
        await apiClient.patch(`/boutique/items/${editingItem.id}`, {
          item: values.item,
          detail: detailKind === 'OTRO' ? null : values.detail,
        })
        message.success('Se guardaron los cambios del producto correctamente.')
      } else {
        await apiClient.post('/boutique/items', {
          type_id: values.type_id,
          item: values.item,
          detail_kind: detailKind,
          detail: detailKind === 'OTRO' ? null : values.detail,
        })
        message.success('Se creó el producto correctamente.')
      }

      setFormOpen(false)
      setEditingItem(null)
      form.resetFields()
      await Promise.all([loadItems(), loadReferences()])
    } catch (requestError) {
      const resolved = applyFormApiError(form, requestError, {
        messageFieldMap: [
          { test: /item boutique con ese código/i, field: ['item', 'code'] },
          { test: /proveedor.*deshabilitado/i, field: ['item', 'provider_id'] },
          { test: /stock no puede editarse/i, field: ['item', 'stock'] },
          { test: /precio de venta no puede ser menor/i, field: ['item', 'sale_price'] },
        ],
        fallbackGlobalMessage: 'No fue posible guardar la información del producto.',
      })
      setFormError(resolved.globalMessage)
    } finally {
      setSaving(false)
    }
  }

  const handleStatusChange = async (record, nextValue) => {
    try {
      await apiClient.patch(`/boutique/items/${record.id}/status`, { is_active: nextValue })
      message.success(`Producto ${nextValue ? 'activado' : 'desactivado'} correctamente.`)
      await loadItems()
    } catch (requestError) {
      message.error(requestError.response?.data?.detail || 'No fue posible actualizar el estado del producto.')
    }
  }

  const columns = [
    { title: 'Código', dataIndex: 'code', key: 'code' },
    { title: 'Nombre', dataIndex: 'name', key: 'name' },
    { title: 'Tipo', dataIndex: 'type_name', key: 'type_name', render: (value) => <Tag color={getCategoryColor(value)}>{value}</Tag> },
    {
      title: 'Color',
      key: 'color',
      render: (_, record) => (
        <div>
          <div>{record.color_primary}</div>
          {record.color_secondary ? <Typography.Text type="secondary">{record.color_secondary}</Typography.Text> : null}
        </div>
      ),
    },
    { title: 'Material', dataIndex: 'material', key: 'material' },
    { title: 'Proveedor', dataIndex: 'provider_name', key: 'provider_name', render: (value) => value || 'SIN PROVEEDOR' },
    { title: 'P. Venta (Bs)', dataIndex: 'sale_price', key: 'sale_price' },
    {
      title: 'Stock',
      key: 'stock',
      render: (_, record) => (
        <div>
          <Typography.Text>{record.stock}</Typography.Text>
          {record.is_low_stock ? <Tag color="red" style={{ marginLeft: 8 }}>Stock bajo</Tag> : null}
        </div>
      ),
    },
    { title: 'Stock mín.', dataIndex: 'stock_min', key: 'stock_min' },
    {
      title: 'Estado',
      key: 'estado',
      render: (_, record) =>
        canUpdateStatus ? (
          <Switch
            checked={record.is_active}
            checkedChildren="Activo"
            unCheckedChildren="Inactivo"
            onChange={(checked) => handleStatusChange(record, checked)}
          />
        ) : (
          <Tag color={record.is_active ? 'green' : 'default'}>{record.is_active ? 'ACTIVO' : 'INACTIVO'}</Tag>
        ),
    },
    {
      title: 'Acciones',
      key: 'acciones',
      render: (_, record) => (
        <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
          <Button icon={<EyeOutlined />} onClick={() => openView(record)}>
            Ver
          </Button>
          {canUpdate ? (
            <Button icon={<EditOutlined />} onClick={() => openEdit(record)}>
              Editar
            </Button>
          ) : null}
          {canCreateEntry ? (
            <Button onClick={() => navigate('/app/boutique/entradas', { state: { prefillItemId: record.id } })}>
              Registrar entrada
            </Button>
          ) : null}
        </div>
      ),
    },
  ]

  return (
    <div>
      <div className="page-header">
        <div>
          <Typography.Title level={2} style={{ margin: 0 }}>
            Inventario Boutique
          </Typography.Title>
          <Typography.Paragraph type="secondary" style={{ marginBottom: 0 }}>
            Gestiona productos de la boutique con proveedor, detalle especializado y control de stock.
          </Typography.Paragraph>
        </div>

        {canCreate ? (
          <Button type="primary" icon={<PlusOutlined />} onClick={openCreate}>
            Nuevo producto
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
          <Col xs={24} md={6}>
            <Select
              allowClear
              showSearch
              optionFilterProp="label"
              placeholder="Filtrar por tipo"
              options={typeOptions}
              value={filters.type_id}
              onChange={(value) => setFilters((current) => ({ ...current, type_id: value }))}
              style={{ width: '100%' }}
            />
          </Col>
          <Col xs={24} md={4}>
            <Select
              allowClear
              placeholder="Estado"
              value={filters.is_active}
              onChange={(value) => setFilters((current) => ({ ...current, is_active: value }))}
              options={[
                { label: 'Activos', value: true },
                { label: 'Inactivos', value: false },
              ]}
              style={{ width: '100%' }}
            />
          </Col>
          <Col xs={24} md={4}>
            <Switch
              checked={filters.low_stock}
              checkedChildren="Stock bajo"
              unCheckedChildren="Todos"
              onChange={(checked) => setFilters((current) => ({ ...current, low_stock: checked }))}
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
        dataSource={items}
        loading={loading}
        pagination={{ pageSize: 8 }}
        scroll={{ x: 'max-content' }}
        style={{ borderRadius: 24, overflow: 'hidden' }}
      />

      <Drawer
        title={editingItem ? 'Editar Producto Boutique' : 'Crear Producto Boutique'}
        width={860}
        open={formOpen}
        onClose={() => {
          setFormOpen(false)
          setEditingItem(null)
          setFormError(null)
          form.resetFields()
        }}
        destroyOnClose
        maskClosable={false}
      >
        <FormProcessAlert
          message={formError}
          title={editingItem ? 'No fue posible actualizar el producto.' : 'No fue posible crear el producto.'}
        />
        <BoutiqueItemForm
          form={form}
          types={types}
          providers={providers}
          mode={editingItem ? 'edit' : 'create'}
          onFinish={handleSubmit}
          saving={saving}
        />
      </Drawer>

      <Modal
        title={null}
        width={840}
        open={detailOpen}
        onCancel={() => {
          setDetailOpen(false)
          setSelectedItem(null)
        }}
        maskClosable={false}
        footer={[
          <Button key="close" onClick={() => { setDetailOpen(false); setSelectedItem(null) }}>
            Cerrar
          </Button>,
        ]}
      >
        <BoutiqueItemDetailCard item={selectedItem} />
      </Modal>
    </div>
  )
}
