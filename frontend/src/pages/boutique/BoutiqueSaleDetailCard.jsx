/* eslint-disable react/prop-types */
import { Descriptions, Tag, Typography } from 'antd'

import { ESTADO_VENTA_OPTIONS, METODO_PAGO_OPTIONS, MOTIVO_DESCUENTO_VENTA_OPTIONS, formatBs, labelFromOptions } from './boutiqueConstants'

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
          <Tag color={sale.estado === 'activa' ? 'green' : sale.estado === 'cancelada' ? 'orange' : 'red'}>
            {labelFromOptions(ESTADO_VENTA_OPTIONS, sale.estado)}
          </Tag>
        </Descriptions.Item>
        <Descriptions.Item label="Método de pago">
          {labelFromOptions(METODO_PAGO_OPTIONS, sale.payment_method)}
        </Descriptions.Item>
        <Descriptions.Item label="Producto">{sale.item?.code} - {sale.item?.name}</Descriptions.Item>
        <Descriptions.Item label="Tipo">{sale.item?.type_name}</Descriptions.Item>
        <Descriptions.Item label="Cliente">
          {sale.client ? `${sale.client.codigo} - ${sale.client.full_name}` : 'VENTA SIN CLIENTE'}
        </Descriptions.Item>
        <Descriptions.Item label="Registrado por">
          {sale.registered_by?.full_name} {sale.registered_by?.username ? `(${sale.registered_by.username})` : ''}
        </Descriptions.Item>
        <Descriptions.Item label="Moneda">
          {sale.currency?.codigo} - {sale.currency?.nombre}
        </Descriptions.Item>
        <Descriptions.Item label="Tipo de cambio usado">{sale.exchange_rate_used}</Descriptions.Item>
        <Descriptions.Item label="Cantidad">{sale.quantity}</Descriptions.Item>
        <Descriptions.Item label="Precio unitario">Bs. {formatBs(sale.unit_price)}</Descriptions.Item>
        <Descriptions.Item label="Descuento">Bs. {formatBs(sale.discount || 0)}</Descriptions.Item>
        <Descriptions.Item label="Motivo descuento">
          {sale.discount_reason ? labelFromOptions(MOTIVO_DESCUENTO_VENTA_OPTIONS, sale.discount_reason) : 'SIN DESCUENTO'}
        </Descriptions.Item>
        <Descriptions.Item label="Total en Bs.">Bs. {formatBs(sale.total)}</Descriptions.Item>
        <Descriptions.Item label="Total en moneda origen">
          {sale.currency?.simbolo || sale.currency?.codigo} {formatBs(sale.total_currency_origin)}
        </Descriptions.Item>
        <Descriptions.Item label="Fecha cambio estado">
          {sale.changed_at ? new Date(sale.changed_at).toLocaleString() : 'SIN CAMBIO'}
        </Descriptions.Item>
        <Descriptions.Item label="Motivo cambio estado">
          {sale.state_change_reason || 'SIN CAMBIO'}
        </Descriptions.Item>
        <Descriptions.Item label="Observaciones" span={2}>
          {sale.observations || 'SIN OBSERVACIONES'}
        </Descriptions.Item>
      </Descriptions>
    </div>
  )
}
