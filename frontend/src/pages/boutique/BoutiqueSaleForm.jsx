/* eslint-disable react/prop-types */
import { Alert, Button, Col, Form, Input, InputNumber, Row, Select, Typography } from 'antd'

import {
  FORM_COMMON_PROPS,
  FORM_DRAWER_SUBMIT_PROPS,
} from '../../components/forms/formConfig'
import { METODO_PAGO_OPTIONS, MOTIVO_DESCUENTO_VENTA_OPTIONS, formatBs } from './boutiqueConstants'

export function BoutiqueSaleForm({ form, items, clients, saving, onFinish, canPickClient = true }) {
  const selectedItemId = Form.useWatch('item_id', form)
  const quantity = Form.useWatch('quantity', form)
  const discount = Form.useWatch('discount', form)

  const selectedItem = items.find((item) => item.id === selectedItemId) || null
  const stock = Number(selectedItem?.stock || 0)
  const unitPrice = Number(selectedItem?.sale_price || 0)
  const quantityValue = Number(quantity || 0)
  const normalizedDiscount = Number(discount || 0)
  const subtotal = quantityValue > 0 ? quantityValue * unitPrice : 0
  const total = Math.max(subtotal - normalizedDiscount, 0)
  const requiresDiscountReason = normalizedDiscount > 0
  const quantityExceedsStock = Boolean(selectedItem && quantityValue > stock)

  return (
    <Form
      {...FORM_COMMON_PROPS}
      form={form}
      onFinish={(values) => {
        const payload = { ...values }
        payload.discount = payload.discount && Number(payload.discount) > 0 ? Number(payload.discount) : null
        payload.discount_reason = payload.discount ? payload.discount_reason : null
        payload.client_id = payload.client_id || null
        payload.observations = payload.observations || null
        onFinish(payload)
      }}
    >
      <Typography.Title level={5}>Datos de la venta</Typography.Title>

      <Row gutter={12}>
        <Col span={24}>
          <Form.Item
            label="Producto boutique"
            name="item_id"
            rules={[{ required: true, message: 'Debe seleccionar el Producto Boutique a vender.' }]}
            extra="Busca el producto por código o nombre y confirma el stock disponible antes de registrar la venta."
          >
            <Select
              showSearch
              placeholder="Busca y selecciona el producto a vender"
              optionFilterProp="label"
              options={items.map((item) => ({
                label: `${item.code} - ${item.name} | Stock: ${item.stock} | Bs. ${formatBs(item.sale_price)}`,
                value: item.id,
                disabled: Number(item.stock) <= 0 || !item.is_active,
              }))}
            />
          </Form.Item>
        </Col>
      </Row>

      {selectedItem ? (
        <Alert
          style={{ marginBottom: 16 }}
          type={quantityExceedsStock ? 'error' : Number(selectedItem.stock) <= Number(selectedItem.stock_min) ? 'warning' : 'info'}
          showIcon
          message={`${selectedItem.code} - ${selectedItem.name}`}
          description={`Tipo: ${selectedItem.type_name}. Stock actual: ${selectedItem.stock}. Stock mínimo: ${selectedItem.stock_min}. Precio unitario vigente: Bs. ${formatBs(selectedItem.sale_price)}.`}
        />
      ) : null}

      <Row gutter={12}>
        <Col span={12}>
          <Form.Item
            label="Cliente"
            name="client_id"
            extra={canPickClient ? 'Campo opcional. Si no eliges cliente, la venta se registrará sin asociación.' : 'Tu rol puede registrar la venta sin asociar cliente.'}
          >
            <Select
              showSearch
              allowClear
              disabled={!canPickClient}
              placeholder={canPickClient ? 'Busca un cliente o deja este campo vacío' : 'Cliente no disponible para tu rol'}
              optionFilterProp="label"
              options={clients.map((client) => ({
                label: `${client.codigo} - ${client.full_name} | ${client.celular}`,
                value: client.id,
              }))}
            />
          </Form.Item>
        </Col>
        <Col span={12}>
          <Form.Item
            label="Cantidad"
            name="quantity"
            rules={[
              { required: true, message: 'La Cantidad vendida es obligatoria.' },
              {
                validator(_, value) {
                  if (value === undefined || value === null || value === '') {
                    return Promise.resolve()
                  }
                  if (!selectedItem) {
                    return Promise.reject(new Error('Primero debe seleccionar el Producto Boutique.'))
                  }
                  if (Number(value) <= 0) {
                    return Promise.reject(new Error('La Cantidad vendida debe ser mayor a cero.'))
                  }
                  if (Number(value) > Number(selectedItem.stock)) {
                    return Promise.reject(new Error('La Cantidad vendida no puede ser mayor al Stock disponible.'))
                  }
                  return Promise.resolve()
                },
              },
            ]}
            extra="Debe ser un número entero mayor a cero y no puede superar el stock disponible."
            normalize={(value) => {
              if (value === null || value === undefined || value === '') return null
              return value.toString().replace(/[^0-9]/g, '')
            }}
          >
            <InputNumber
              min={1}
              max={selectedItem ? Number(selectedItem.stock) : undefined}
              precision={0}
              style={{ width: '100%' }}
              placeholder="Ej. 1, 2, 5"
            />
          </Form.Item>
        </Col>
      </Row>

      <Row gutter={12}>
        <Col span={12}>
          <Form.Item label="Precio unitario vigente">
            <Input value={selectedItem ? `Bs. ${formatBs(selectedItem.sale_price)}` : ''} placeholder="Se completa automáticamente al elegir el producto" readOnly />
          </Form.Item>
        </Col>
        <Col span={12}>
          <Form.Item
            label="Método de pago"
            name="payment_method"
            rules={[{ required: true, message: 'Debe seleccionar el Método de pago.' }]}
            extra="Selecciona solo una modalidad permitida en esta versión del sistema."
          >
            <Select placeholder="Selecciona el método de pago" options={METODO_PAGO_OPTIONS} />
          </Form.Item>
        </Col>
      </Row>

      <Row gutter={12}>
        <Col span={12}>
          <Form.Item
            label="Descuento"
            name="discount"
            normalize={(value) => {
              if (value === null || value === undefined || value === '') return null
              return value.toString().replace(/[^0-9.]/g, '')
            }}
            rules={[
              {
                validator(_, value) {
                  if (value === undefined || value === null || value === '') {
                    return Promise.resolve()
                  }
                  if (Number(value) < 0) {
                    return Promise.reject(new Error('El Descuento no puede ser negativo.'))
                  }
                  if (Number(value) > subtotal) {
                    return Promise.reject(new Error('El Descuento no puede ser mayor al subtotal de la venta.'))
                  }
                  return Promise.resolve()
                },
              },
            ]}
            extra="Opcional. Si registras descuento, no puede superar el subtotal."
          >
            <InputNumber min={0} precision={2} style={{ width: '100%' }} prefix="Bs." placeholder="Ej. 50.00" />
          </Form.Item>
        </Col>
        <Col span={12}>
          <Form.Item
            label="Motivo del descuento"
            name="discount_reason"
            rules={requiresDiscountReason ? [{ required: true, message: 'Debe seleccionar el Motivo del descuento.' }] : []}
            extra="Se habilita solo cuando registras un descuento."
          >
            <Select allowClear disabled={!requiresDiscountReason} placeholder="Selecciona el motivo del descuento" options={MOTIVO_DESCUENTO_VENTA_OPTIONS} />
          </Form.Item>
        </Col>
      </Row>

      <Form.Item
        label="Observaciones"
        name="observations"
        extra="Opcional. Registra solo información relevante para seguimiento comercial o aclaraciones de la venta."
        normalize={(value) => (value || '').toUpperCase()}
      >
        <Input.TextArea rows={3} placeholder="Ej. CLIENTE RETIRA EL PRODUCTO HOY O SOLICITA EMBALAJE ESPECIAL" />
      </Form.Item>

      <div className="glass-panel" style={{ padding: 16, marginBottom: 16 }}>
        <Typography.Title level={5} style={{ marginTop: 0 }}>
          Resumen de cobro
        </Typography.Title>
        <Row gutter={12}>
          <Col span={8}>
            <Typography.Text type="secondary">Subtotal</Typography.Text>
            <Typography.Title level={4} style={{ marginTop: 4, marginBottom: 0 }}>
              Bs. {formatBs(subtotal)}
            </Typography.Title>
          </Col>
          <Col span={8}>
            <Typography.Text type="secondary">Descuento</Typography.Text>
            <Typography.Title level={4} style={{ marginTop: 4, marginBottom: 0 }}>
              Bs. {formatBs(normalizedDiscount)}
            </Typography.Title>
          </Col>
          <Col span={8}>
            <Typography.Text type="secondary">Total final</Typography.Text>
            <Typography.Title level={4} style={{ marginTop: 4, marginBottom: 0, color: '#8f3d2e' }}>
              Bs. {formatBs(total)}
            </Typography.Title>
          </Col>
        </Row>
      </div>

      <Button {...FORM_DRAWER_SUBMIT_PROPS} loading={saving} disabled={quantityExceedsStock}>
        Registrar venta
      </Button>
    </Form>
  )
}
