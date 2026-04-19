/* eslint-disable react-hooks/exhaustive-deps */
import { EditOutlined, EyeOutlined, PlusOutlined, SearchOutlined } from '@ant-design/icons'
import {
  Alert,
  App as AntdApp,
  Button,
  Drawer,
  Form,
  Input,
  Select,
  Space,
  Switch,
  Table,
  Tag,
  Typography,
} from 'antd'
import { useCallback, useEffect, useMemo, useState } from 'react'

import { apiClient } from '../../api/client'
import { useAuth } from '../../auth/AuthProvider'
import { BoutiqueItemDetailCard } from './BoutiqueItemDetailCard'
import { BoutiqueItemForm } from './BoutiqueItemForm'
import { inferDetailKindFromTypeName } from './boutiqueConstants'

export function BoutiqueInventoryPage() {
  const [items, setItems] = useState([])
  const [types, setTypes] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
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

  const canCreate = user?.permissions?.includes('boutique_items:create')
  const canUpdate = user?.permissions?.includes('boutique_items:update')
  const canUpdateStatus = user?.permissions?.includes('boutique_items:update_status')

  const loadTypes = useCallback(async () => {
    const response = await apiClient.get('/boutique/types')
    setTypes(response.data)
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
  }, [filters.is_active, filters.low_stock, filters.search, filters.type_id])

  useEffect(() => {
    Promise.all([loadTypes(), loadItems()]).catch(() => {
      setError('No fue posible cargar la informacion inicial del modulo boutique.')
      setLoading(false)
    })
  }, [])

  useEffect(() => {
    loadItems()
  }, [filters.search, filters.type_id, filters.is_active, filters.low_stock])

  const typeOptions = useMemo(
    () => types.map((type) => ({ label: type.nombre, value: type.id })),
    [types],
  )

  const openCreate = () => {
    setEditingItem(null)
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
      form.setFieldsValue({
        type_id: item.type.id,
        item: {
          code: item.code,
          name: item.name,
          color: item.color,
          shape: item.shape,
          material: item.material,
          measurements: item.measurements,
          supplier: item.supplier,
          description: item.description,
          purchase_price: item.purchase_price,
          sale_price: item.sale_price,
          stock: item.stock,
          stock_min: item.stock_min,
          notes: item.notes,
        },
        detail: item.detail || {},
      })
      setFormOpen(true)
    } catch (requestError) {
      message.error(requestError.response?.data?.detail || 'No fue posible cargar el item.')
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
      message.error(requestError.response?.data?.detail || 'No fue posible cargar el detalle del item.')
    }
  }

  const handleSubmit = async (values) => {
    setSaving(true)
    try {
      const selectedType = types.find((type) => type.id === values.type_id)
      const detailKind = inferDetailKindFromTypeName(selectedType?.nombre)

      if (editingItem) {
        await apiClient.patch(`/boutique/items/${editingItem.id}`, {
          item: values.item,
          detail: detailKind === 'OTRO' ? null : values.detail,
        })
        message.success('Item boutique actualizado correctamente.')
      } else {
        await apiClient.post('/boutique/items', {
          type_id: values.type_id,
          item: values.item,
          detail_kind: detailKind,
          detail: detailKind === 'OTRO' ? null : values.detail,
        })
        message.success('Item boutique creado correctamente.')
      }

      setFormOpen(false)
      setEditingItem(null)
      form.resetFields()
      await loadItems()
    } catch (requestError) {
      message.error(requestError.response?.data?.detail || 'No fue posible guardar el item boutique.')
    } finally {
      setSaving(false)
    }
  }

  const handleStatusChange = async (record, nextValue) => {
    try {
      await apiClient.patch(`/boutique/items/${record.id}/status`, { is_active: nextValue })
      message.success(`Item ${nextValue ? 'activado' : 'desactivado'} correctamente.`)
      await loadItems()
    } catch (requestError) {
      message.error(requestError.response?.data?.detail || 'No fue posible actualizar el estado del item.')
    }
  }

  const columns = [
    { title: 'Codigo', dataIndex: 'code', key: 'code' },
    { title: 'Nombre', dataIndex: 'name', key: 'name' },
    { title: 'Tipo', dataIndex: 'type_name', key: 'type_name', render: (value) => <Tag color="gold">{value}</Tag> },
    { title: 'Color', dataIndex: 'color', key: 'color' },
    { title: 'Material', dataIndex: 'material', key: 'material' },
    { title: 'P. Venta', dataIndex: 'sale_price', key: 'sale_price' },
    {
      title: 'Stock',
      key: 'stock',
      render: (_, record) => (
        <Space>
          <Typography.Text>{record.stock}</Typography.Text>
          {record.is_low_stock ? <Tag color="red">Stock bajo</Tag> : null}
        </Space>
      ),
    },
    { title: 'Stock min', dataIndex: 'stock_min', key: 'stock_min' },
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
          <Tag color={record.is_active ? 'green' : 'default'}>{record.is_active ? 'Activo' : 'Inactivo'}</Tag>
        ),
    },
    {
      title: 'Acciones',
      key: 'acciones',
      render: (_, record) => (
        <Space wrap>
          <Button icon={<EyeOutlined />} onClick={() => openView(record)}>
            Ver
          </Button>
          {canUpdate ? (
            <Button icon={<EditOutlined />} onClick={() => openEdit(record)}>
              Editar
            </Button>
          ) : null}
        </Space>
      ),
    },
  ]

  return (
    <div>
      <div className="page-header">
        <div>
          <Typography.Title level={2} style={{ margin: 0 }}>
            Inventario boutique
          </Typography.Title>
          <Typography.Paragraph type="secondary" style={{ marginBottom: 0 }}>
            Gestiona articulos boutique con detalle especializado y control de stock.
          </Typography.Paragraph>
        </div>

        {canCreate ? (
          <Button type="primary" icon={<PlusOutlined />} onClick={openCreate}>
            Nuevo item
          </Button>
        ) : null}
      </div>

      <div className="glass-panel boutique-filter-bar">
        <Space wrap style={{ width: '100%', justifyContent: 'space-between' }}>
          <Space wrap>
            <Input
              allowClear
              prefix={<SearchOutlined />}
              placeholder="Buscar por codigo, nombre o color"
              value={filters.search}
              onChange={(event) => setFilters((current) => ({ ...current, search: event.target.value }))}
              style={{ width: 280 }}
            />

            <Select
              allowClear
              placeholder="Filtrar por tipo"
              options={typeOptions}
              value={filters.type_id}
              onChange={(value) => setFilters((current) => ({ ...current, type_id: value }))}
              style={{ width: 220 }}
            />

            <Select
              allowClear
              placeholder="Estado"
              value={filters.is_active}
              onChange={(value) => setFilters((current) => ({ ...current, is_active: value }))}
              options={[
                { label: 'Activos', value: true },
                { label: 'Inactivos', value: false },
              ]}
              style={{ width: 160 }}
            />
          </Space>

          <Switch
            checked={filters.low_stock}
            checkedChildren="Stock bajo"
            unCheckedChildren="Todos"
            onChange={(checked) => setFilters((current) => ({ ...current, low_stock: checked }))}
          />
        </Space>
      </div>

      {error ? <Alert type="error" showIcon message={error} style={{ marginBottom: 16 }} /> : null}

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
        title={editingItem ? 'Editar item boutique' : 'Crear item boutique'}
        width={780}
        open={formOpen}
        onClose={() => {
          setFormOpen(false)
          setEditingItem(null)
          form.resetFields()
        }}
        destroyOnClose
      >
        <BoutiqueItemForm
          form={form}
          types={types}
          mode={editingItem ? 'edit' : 'create'}
          onFinish={handleSubmit}
          saving={saving}
        />
      </Drawer>

      <Drawer
        title="Detalle del item boutique"
        width={620}
        open={detailOpen}
        onClose={() => {
          setDetailOpen(false)
          setSelectedItem(null)
        }}
      >
        <BoutiqueItemDetailCard item={selectedItem} />
      </Drawer>
    </div>
  )
}
