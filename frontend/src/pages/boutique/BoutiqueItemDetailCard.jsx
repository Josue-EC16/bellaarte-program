/* eslint-disable react/prop-types */
import { Descriptions, Tag, Typography } from 'antd'

const LABEL_MAP = {
  dress_type: 'Tipo de vestido',
  dress_size: 'Talla',
  skirt_cut: 'Corte de falda',
  neckline_type: 'Tipo de escote',
  cup_size: 'Copa',
  skirt_length: 'Largo de falda',
  has_train: 'Tiene cola',
  has_sleeves: 'Tiene manga',
  has_stoning: 'Tiene pedreria',
  veil_type: 'Tipo de velo',
  size: 'Tamaño',
  length: 'Largo',
  layers: 'Capas',
  edge: 'Borde',
  decoration: 'Decoración',
  bouquet_type: 'Tipo de bouquet',
  flower_type: 'Tipo de flor',
  notes: 'Notas de detalle',
}

export function BoutiqueItemDetailCard({ item }) {
  if (!item) return null

  const detailEntries = item.detail
    ? Object.entries(item.detail).filter(([, value]) => value !== null && value !== undefined && value !== '')
    : []

  return (
    <div>
      <Typography.Title level={4} style={{ marginTop: 0 }}>Información Base</Typography.Title>
      <Descriptions bordered column={2} size="small" layout="vertical">
        <Descriptions.Item label="Tipo de Familia">{item.type?.nombre}</Descriptions.Item>
        <Descriptions.Item label="Codigo">{item.code}</Descriptions.Item>
        <Descriptions.Item label="Nombre">{item.name}</Descriptions.Item>
        <Descriptions.Item label="Color">{item.color}</Descriptions.Item>
        <Descriptions.Item label="Forma">{item.shape || 'No registrado'}</Descriptions.Item>
        <Descriptions.Item label="Material">{item.material}</Descriptions.Item>
        <Descriptions.Item label="Proveedor">{item.supplier || 'No registrado'}</Descriptions.Item>
        <Descriptions.Item label="Precio compra">Bs. {item.purchase_price}</Descriptions.Item>
        <Descriptions.Item label="Precio venta">Bs. {item.sale_price}</Descriptions.Item>
        <Descriptions.Item label="Stock">{item.stock}</Descriptions.Item>
        <Descriptions.Item label="Stock minimo">{item.stock_min}</Descriptions.Item>
        <Descriptions.Item label="Estado">
          <Tag color={item.is_active ? 'green' : 'default'}>{item.is_active ? 'Activo' : 'Inactivo'}</Tag>
        </Descriptions.Item>
        <Descriptions.Item label="Descripción">{item.description || 'Sin descripción'}</Descriptions.Item>
      </Descriptions>

      {detailEntries.length ? (
        <>
          <Typography.Title level={5} style={{ marginTop: 24 }}>
            Detalles Específicos
          </Typography.Title>
          <Descriptions bordered column={2} size="small" layout="vertical">
            {detailEntries.map(([key, value]) => (
              <Descriptions.Item key={key} label={LABEL_MAP[key] || key}>
                {typeof value === 'boolean' ? (value ? 'Si' : 'No') : value}
              </Descriptions.Item>
            ))}
          </Descriptions>
        </>
      ) : null}
    </div>
  )
}
