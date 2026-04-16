/* eslint-disable react/prop-types */
import { Descriptions, Tag, Typography } from 'antd'

export function BoutiqueItemDetailCard({ item }) {
  if (!item) return null

  const detailEntries = item.detail
    ? Object.entries(item.detail).filter(([, value]) => value !== null && value !== undefined && value !== '')
    : []

  return (
    <div>
      <Typography.Title level={4}>Detalle del item</Typography.Title>
      <Descriptions bordered column={1} size="small">
        <Descriptions.Item label="Tipo">{item.type?.nombre}</Descriptions.Item>
        <Descriptions.Item label="Codigo">{item.code}</Descriptions.Item>
        <Descriptions.Item label="Nombre">{item.name}</Descriptions.Item>
        <Descriptions.Item label="Color">{item.color}</Descriptions.Item>
        <Descriptions.Item label="Forma">{item.shape || 'No registrado'}</Descriptions.Item>
        <Descriptions.Item label="Material">{item.material}</Descriptions.Item>
        <Descriptions.Item label="Proveedor">{item.supplier || 'No registrado'}</Descriptions.Item>
        <Descriptions.Item label="Precio compra">{item.purchase_price}</Descriptions.Item>
        <Descriptions.Item label="Precio venta">{item.sale_price}</Descriptions.Item>
        <Descriptions.Item label="Stock">{item.stock}</Descriptions.Item>
        <Descriptions.Item label="Stock minimo">{item.stock_min}</Descriptions.Item>
        <Descriptions.Item label="Estado">
          <Tag color={item.is_active ? 'green' : 'default'}>{item.is_active ? 'Activo' : 'Inactivo'}</Tag>
        </Descriptions.Item>
        <Descriptions.Item label="Descripcion">{item.description || 'Sin descripcion'}</Descriptions.Item>
      </Descriptions>

      {detailEntries.length ? (
        <>
          <Typography.Title level={5} style={{ marginTop: 24 }}>
            Detalle especializado
          </Typography.Title>
          <Descriptions bordered column={1} size="small">
            {detailEntries.map(([key, value]) => (
              <Descriptions.Item key={key} label={key}>
                {typeof value === 'boolean' ? (value ? 'Si' : 'No') : value}
              </Descriptions.Item>
            ))}
          </Descriptions>
        </>
      ) : null}
    </div>
  )
}
