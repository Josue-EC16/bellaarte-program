/* eslint-disable react/prop-types */
import { Descriptions, Tag, Typography } from 'antd'

import { COPA_OPTIONS, TALLA_OPTIONS, TIPO_VESTIDO_OPTIONS, labelFromOptions } from './boutiqueConstants'

const LABEL_MAP = {
  dress_type: 'Tipo de vestido',
  dress_size: 'Talla',
  skirt_cut: 'Corte de falda',
  neckline_type: 'Tipo de escote',
  cup_size: 'Copa',
  skirt_length: 'Largo de falda',
  has_train: 'Tiene cola',
  has_sleeves: 'Tiene manga',
  has_stoning: 'Tiene pedrería',
  veil_type: 'Tipo de velo',
  layers: 'Capas',
  edge: 'Borde',
  decoration: 'Decoración',
  bouquet_type: 'Tipo de bouquet',
  shape: 'Forma',
  flower_type: 'Tipo de flor',
  brand: 'Marca',
  has_lace: 'Tiene encaje',
  notes: 'Observaciones',
}

function normalizeDetailValue(key, value) {
  if (key === 'dress_type') return labelFromOptions(TIPO_VESTIDO_OPTIONS, value)
  if (key === 'dress_size') return labelFromOptions(TALLA_OPTIONS, value)
  if (key === 'cup_size') return labelFromOptions(COPA_OPTIONS, value)
  if (typeof value === 'boolean') return value ? 'SÍ' : 'NO'
  return value
}

export function BoutiqueItemDetailCard({ item }) {
  if (!item) return null

  const detailEntries = item.detail
    ? Object.entries(item.detail).filter(([, value]) => value !== null && value !== undefined && value !== '')
    : []

  return (
    <div>
      <Typography.Title level={4} style={{ marginTop: 0 }}>
        Información base
      </Typography.Title>
      <Descriptions bordered column={2} size="small" layout="vertical">
        <Descriptions.Item label="Tipo">{item.type?.nombre}</Descriptions.Item>
        <Descriptions.Item label="Código">{item.code}</Descriptions.Item>
        <Descriptions.Item label="Nombre">{item.name}</Descriptions.Item>
        <Descriptions.Item label="Proveedor">
          {item.provider
            ? item.provider.nombre_comercial
              ? `${item.provider.full_name} - ${item.provider.nombre_comercial}`
              : item.provider.full_name
            : 'SIN PROVEEDOR'}
        </Descriptions.Item>
        <Descriptions.Item label="Color primario">{item.color_primary}</Descriptions.Item>
        <Descriptions.Item label="Color secundario">{item.color_secondary || 'SIN REGISTRO'}</Descriptions.Item>
        <Descriptions.Item label="Material">{item.material}</Descriptions.Item>
        <Descriptions.Item label="Largo">{item.length ?? 'SIN REGISTRO'}</Descriptions.Item>
        <Descriptions.Item label="Ancho">{item.width ?? 'SIN REGISTRO'}</Descriptions.Item>
        <Descriptions.Item label="Precio compra">Bs. {item.purchase_price}</Descriptions.Item>
        <Descriptions.Item label="Precio venta">Bs. {item.sale_price}</Descriptions.Item>
        <Descriptions.Item label="Stock">{item.stock}</Descriptions.Item>
        <Descriptions.Item label="Stock mínimo">{item.stock_min}</Descriptions.Item>
        <Descriptions.Item label="Estado">
          <Tag color={item.is_active ? 'green' : 'default'}>{item.is_active ? 'ACTIVO' : 'INACTIVO'}</Tag>
        </Descriptions.Item>
        <Descriptions.Item label="Detalle general" span={2}>
          {item.detail_text || 'SIN DETALLE GENERAL'}
        </Descriptions.Item>
      </Descriptions>

      {detailEntries.length ? (
        <>
          <Typography.Title level={5} style={{ marginTop: 24 }}>
            Detalle especializado
          </Typography.Title>
          <Descriptions bordered column={2} size="small" layout="vertical">
            {detailEntries.map(([key, value]) => (
              <Descriptions.Item key={key} label={LABEL_MAP[key] || key}>
                {normalizeDetailValue(key, value)}
              </Descriptions.Item>
            ))}
          </Descriptions>
        </>
      ) : null}
    </div>
  )
}
