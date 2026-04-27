/* eslint-disable react/prop-types */
import { Descriptions, Tag, Typography } from 'antd'

import { formatBs } from './boutiqueConstants'

export function BoutiqueSaleDetailCard({ sale }) {
  if (!sale) return null

  return (
    <div>
      <Typography.Title level={4} style={{ marginTop: 0 }}>
        Detalle de la venta
      </Typography.Title>
      <Descriptions bordered column={2} size="small" layout="vertical">
        <Descriptions.Item label="ID Venta">#{sale.id}</Descriptions.Item>
        <Descriptions.Item label="Fecha">{new Date(sale.fecha).toLocaleString()}</Descriptions.Item>
        <Descriptions.Item label="Estado">
          <Tag color={sale.estado === 'ACTIVA' ? 'green' : sale.estado === 'CANCELADA' ? 'orange' : 'red'}>
            {sale.estado}
          </Tag>
        </Descriptions.Item>
        <Descriptions.Item label="Método de pago">{String(sale.payment_method || '').replaceAll('_', ' ')}</Descriptions.Item>
        <Descriptions.Item label="Producto">{sale.item?.code} - {sale.item?.name}</Descriptions.Item>
        <Descriptions.Item label="Tipo">{sale.item?.type_name}</Descriptions.Item>
        <Descriptions.Item label="Cliente">
          {sale.client ? `${sale.client.codigo} - ${sale.client.full_name}` : 'VENTA SIN CLIENTE'}
        </Descriptions.Item>
        <Descriptions.Item label="Registrado por">
          {sale.registered_by?.full_name} {sale.registered_by?.username ? `(${sale.registered_by.username})` : ''}
        </Descriptions.Item>
        <Descriptions.Item label="Cantidad">{sale.quantity}</Descriptions.Item>
        <Descriptions.Item label="Precio unitario">Bs. {formatBs(sale.unit_price)}</Descriptions.Item>
        <Descriptions.Item label="Descuento">Bs. {formatBs(sale.discount || 0)}</Descriptions.Item>
        <Descriptions.Item label="Motivo descuento">{sale.discount_reason || 'SIN DESCUENTO'}</Descriptions.Item>
        <Descriptions.Item label="Total final">Bs. {formatBs(sale.total)}</Descriptions.Item>
        <Descriptions.Item label="Observaciones" span={2}>{sale.observations || 'SIN OBSERVACIONES'}</Descriptions.Item>
      </Descriptions>
    </div>
  )
}
