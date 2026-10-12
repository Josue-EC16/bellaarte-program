/* eslint-disable react/prop-types */
import { useMemo } from 'react'
import { Alert, Button, Col, Form, Input, InputNumber, Row, Select, Typography } from 'antd'

import { ReceiptSnapshotFields } from '../../components/receipts/ReceiptSnapshotFields'
import { FORM_COMMON_PROPS, FORM_DRAWER_SUBMIT_PROPS } from '../../components/forms/formConfig'
import { METODO_PAGO_OPTIONS, MOTIVO_DESCUENTO_VENTA_OPTIONS, formatBs } from './boutiqueConstants'

export function BoutiqueSaleForm({ form, items, clients, currencies, exchangeRates, saving, onFinish, canPickClient = true }) {
  const selectedItemId = Form.useWatch('item_id', form)
  const selectedClientId = Form.useWatch('client_id', form)
  const selectedCurrencyId = Form.useWatch('currency_id', form)
  const quantity = Form.useWatch('quantity', form)
  const discount = Form.useWatch('discount', form)

  const selectedItem = items.find((item) => item.id === selectedItemId) || null
  const selectedClient = useMemo(
    () => clients.find((client) => client.id === selectedClientId) || null,
    [clients, selectedClientId],
  )
  const selectedCurrency = currencies.find((currency) => currency.id === selectedCurrencyId) || null
  const selectedRate = exchangeRates.find((rate) => rate.moneda_id === selectedCurrencyId && rate.activo) || null

  const stock = Number(selectedItem?.stock || 0)
  const unitPrice = Number(selectedItem?.sale_price || 0)
  const quantityValue = Number(quantity || 0)
  const normalizedDiscount = Number(discount || 0)
  const subtotal = quantityValue > 0 ? quantityValue * unitPrice : 0
  const total = Math.max(subtotal - normalizedDiscount, 0)
  const exchangeRateValue = selectedCurrency?.es_base ? 1 : Number(selectedRate?.valor_bob || 0)
  const totalCurrencyOrigin = exchangeRateValue > 0 ? total / exchangeRateValue : 0
  const requiresDiscountReason = normalizedDiscount > 0
  const quantityExceedsStock = Boolean(selectedItem && quantityValue > stock)
  const selectedCurrencyWithoutRate = Boolean(selectedCurrency && !selectedCurrency.es_base && !selectedRate)

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
        if (!payload.receipt_customer_snapshot?.full_name && !payload.receipt_customer_snapshot?.ci_nit && !payload.receipt_customer_snapshot?.cellphone) {
          payload.receipt_customer_snapshot = null
        }
        onFinish(payload)
      }}
    >
      <Typography.Title level={5}>Datos de la venta</Typography.Title>

      <Row gutter={12}>
        <Col span={24}>
          <Form.Item
            label="Producto boutique"
            name="item_id"
            rules={[{ required: true, message: 'Debe seleccionar el Producto boutique a vender.' }]}
          >
            <Select
              showSearch
              placeholder="Buscar y seleccionar el producto a vender"
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
            extra={canPickClient ? 'Opcional. Puedes registrar ventas sin asociar cliente.' : 'Tu rol no gestiona la selección de clientes.'}
          >
            <Select
              showSearch
              allowClear
              disabled={!canPickClient}
              optionFilterProp="label"
              placeholder={canPickClient ? 'Buscar cliente o dejar vacío' : 'Cliente no disponible para tu rol'}
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
              { required: true, message: 'La Cantidad es obligatoria.' },
              {
                validator(_, value) {
                  if (value === undefined || value === null || value === '') return Promise.resolve()
                  if (!selectedItem) return Promise.reject(new Error('Primero debe seleccionar el Producto boutique.'))
                  if (Number(value) <= 0) return Promise.reject(new Error('La Cantidad vendida debe ser mayor a cero.'))
                  if (Number(value) > Number(selectedItem.stock)) return Promise.reject(new Error('La Cantidad vendida no puede ser mayor al stock disponible.'))
                  return Promise.resolve()
                },
              },
            ]}
            normalize={(value) => {
              if (value === null || value === undefined || value === '') return null
              return value.toString().replace(/[^0-9]/g, '')
            }}
          >
            <InputNumber min={1} max={selectedItem ? Number(selectedItem.stock) : undefined} precision={0} style={{ width: '100%' }} placeholder="Ej. 1, 2, 3" />
          </Form.Item>
        </Col>
      </Row>

      <Row gutter={12}>
        <Col span={12}>
          <Form.Item label="Precio unitario vigente">
            <Input value={selectedItem ? `Bs. ${formatBs(selectedItem.sale_price)}` : ''} placeholder="Se completa al elegir el producto" readOnly />
          </Form.Item>
        </Col>
        <Col span={12}>
          <Form.Item
            label="Moneda"
            name="currency_id"
            rules={[{ required: true, message: 'Debe seleccionar la Moneda.' }]}
          >
            <Select
              showSearch
              optionFilterProp="label"
              placeholder="Seleccionar moneda de cobro"
              options={currencies.map((currency) => ({
                label: `${currency.codigo} - ${currency.nombre}`,
                value: currency.id,
              }))}
            />
          </Form.Item>
        </Col>
      </Row>

      {selectedCurrency ? (
        <Alert
          style={{ marginBottom: 16 }}
          type={selectedCurrencyWithoutRate ? 'error' : 'info'}
          showIcon
          message={selectedCurrencyWithoutRate ? 'La moneda seleccionada no tiene tipo de cambio activo.' : `Tipo de cambio activo: ${exchangeRateValue}`}
          description={
            selectedCurrency.es_base
              ? 'La moneda base usa tipo de cambio 1 automáticamente.'
              : selectedCurrencyWithoutRate
                ? 'No podrás registrar la venta hasta que exista un tipo de cambio activo para esta moneda.'
                : `El total en moneda original se calculará automáticamente con ${exchangeRateValue} Bs por unidad de moneda.`
          }
        />
      ) : null}

      <Row gutter={12}>
        <Col span={12}>
          <Form.Item
            label="Método de pago"
            name="payment_method"
            rules={[{ required: true, message: 'Debe seleccionar el Método de pago.' }]}
          >
            <Select placeholder="Seleccionar método de pago" options={METODO_PAGO_OPTIONS} />
          </Form.Item>
        </Col>
        <Col span={12}>
          <Form.Item label="Tipo de cambio usado">
            <Input value={selectedCurrency ? String(exchangeRateValue || '') : ''} placeholder="Se completa según la moneda seleccionada" readOnly />
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
                  if (value === undefined || value === null || value === '') return Promise.resolve()
                  if (Number(value) < 0) return Promise.reject(new Error('El Descuento no puede ser negativo.'))
                  if (Number(value) > subtotal) return Promise.reject(new Error('El Descuento no puede ser mayor al subtotal de la venta.'))
                  return Promise.resolve()
                },
              },
            ]}
          >
            <InputNumber min={0} precision={2} style={{ width: '100%' }} prefix="Bs." placeholder="Ej. 50.00" />
          </Form.Item>
        </Col>
        <Col span={12}>
          <Form.Item
            label="Motivo del descuento"
            name="discount_reason"
            rules={requiresDiscountReason ? [{ required: true, message: 'Debe seleccionar el Motivo del descuento.' }] : []}
          >
            <Select allowClear disabled={!requiresDiscountReason} placeholder="Seleccionar motivo de descuento" options={MOTIVO_DESCUENTO_VENTA_OPTIONS} />
          </Form.Item>
        </Col>
      </Row>

      <Form.Item label="Observaciones" name="observations" normalize={(value) => (value || '').toUpperCase()}>
        <Input.TextArea rows={3} placeholder="Ej. CLIENTE RETIRA EL PRODUCTO HOY O SOLICITA EMBALAJE ESPECIAL" />
      </Form.Item>

      <ReceiptSnapshotFields selectedClient={selectedClient} title="SNAPSHOT DOCUMENTAL PARA COMPROBANTE" />

      <div className="glass-panel" style={{ padding: 16, marginBottom: 16 }}>
        <Typography.Title level={5} style={{ marginTop: 0 }}>
          Resumen de cobro
        </Typography.Title>
        <Row gutter={12}>
          <Col span={6}>
            <Typography.Text type="secondary">Subtotal Bs.</Typography.Text>
            <Typography.Title level={4} style={{ marginTop: 4, marginBottom: 0 }}>
              {formatBs(subtotal)}
            </Typography.Title>
          </Col>
          <Col span={6}>
            <Typography.Text type="secondary">Descuento Bs.</Typography.Text>
            <Typography.Title level={4} style={{ marginTop: 4, marginBottom: 0 }}>
              {formatBs(normalizedDiscount)}
            </Typography.Title>
          </Col>
          <Col span={6}>
            <Typography.Text type="secondary">Total Bs.</Typography.Text>
            <Typography.Title level={4} style={{ marginTop: 4, marginBottom: 0, color: '#8f3d2e' }}>
              {formatBs(total)}
            </Typography.Title>
          </Col>
          <Col span={6}>
            <Typography.Text type="secondary">Total moneda origen</Typography.Text>
            <Typography.Title level={4} style={{ marginTop: 4, marginBottom: 0 }}>
              {selectedCurrency?.simbolo || selectedCurrency?.codigo || ''} {formatBs(totalCurrencyOrigin)}
            </Typography.Title>
          </Col>
        </Row>
      </div>

      <Button {...FORM_DRAWER_SUBMIT_PROPS} loading={saving} disabled={quantityExceedsStock || selectedCurrencyWithoutRate}>
        Registrar venta
      </Button>
    </Form>
  )
}
