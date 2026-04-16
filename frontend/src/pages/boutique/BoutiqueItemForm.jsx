/* eslint-disable react/prop-types */
import { Col, Form, Input, InputNumber, Row, Select, Space, Switch, Typography } from 'antd'

import { COPA_OPTIONS, TAMANO_OPTIONS, TALLA_OPTIONS, TIPO_VESTIDO_OPTIONS, inferDetailKindFromTypeName } from './boutiqueConstants'

export function BoutiqueItemForm({ form, types, mode = 'create', onFinish, saving }) {
  const selectedTypeId = Form.useWatch('type_id', form)
  const selectedType = types.find((type) => type.id === selectedTypeId)
  const detailKind = inferDetailKindFromTypeName(selectedType?.nombre)

  return (
    <Form layout="vertical" form={form} onFinish={onFinish}>
      <Typography.Title level={5}>Datos base</Typography.Title>
      <Row gutter={12}>
        <Col span={12}>
          <Form.Item label="Tipo boutique" name="type_id" rules={[{ required: true }]}>
            <Select
              disabled={mode === 'edit'}
              options={types.map((type) => ({
                label: type.nombre,
                value: type.id,
                disabled: !type.habilitado && mode === 'create',
              }))}
            />
          </Form.Item>
        </Col>
        <Col span={12}>
          <Form.Item label="Codigo" name={['item', 'code']} rules={[{ required: true }]}>
            <Input />
          </Form.Item>
        </Col>
      </Row>

      <Row gutter={12}>
        <Col span={12}>
          <Form.Item label="Nombre" name={['item', 'name']} rules={[{ required: true }]}>
            <Input />
          </Form.Item>
        </Col>
        <Col span={12}>
          <Form.Item label="Color" name={['item', 'color']} rules={[{ required: true }]}>
            <Input />
          </Form.Item>
        </Col>
      </Row>

      <Row gutter={12}>
        <Col span={12}>
          <Form.Item label="Forma" name={['item', 'shape']}>
            <Input />
          </Form.Item>
        </Col>
        <Col span={12}>
          <Form.Item label="Material" name={['item', 'material']} rules={[{ required: true }]}>
            <Input />
          </Form.Item>
        </Col>
      </Row>

      <Form.Item label="Medidas" name={['item', 'measurements']}>
        <Input.TextArea rows={2} />
      </Form.Item>

      <Row gutter={12}>
        <Col span={12}>
          <Form.Item label="Proveedor" name={['item', 'supplier']}>
            <Input />
          </Form.Item>
        </Col>
        <Col span={12}>
          <Form.Item label="Descripcion" name={['item', 'description']}>
            <Input />
          </Form.Item>
        </Col>
      </Row>

      <Row gutter={12}>
        <Col span={12}>
          <Form.Item label="Precio compra" name={['item', 'purchase_price']} rules={[{ required: true }]}>
            <InputNumber min={0} style={{ width: '100%' }} />
          </Form.Item>
        </Col>
        <Col span={12}>
          <Form.Item label="Precio venta" name={['item', 'sale_price']} rules={[{ required: true }]}>
            <InputNumber min={0} style={{ width: '100%' }} />
          </Form.Item>
        </Col>
      </Row>

      <Row gutter={12}>
        <Col span={12}>
          <Form.Item label="Stock" name={['item', 'stock']} rules={[{ required: true }]}>
            <InputNumber min={0} style={{ width: '100%' }} />
          </Form.Item>
        </Col>
        <Col span={12}>
          <Form.Item label="Stock minimo" name={['item', 'stock_min']} rules={[{ required: true }]}>
            <InputNumber min={0} style={{ width: '100%' }} />
          </Form.Item>
        </Col>
      </Row>

      <Form.Item label="Observaciones" name={['item', 'notes']}>
        <Input.TextArea rows={2} />
      </Form.Item>

      {detailKind !== 'OTRO' ? (
        <>
          <Typography.Title level={5}>Detalle especializado</Typography.Title>
          {detailKind === 'VESTIDO' ? <VestidoFields /> : null}
          {detailKind === 'VELO' ? <VeloFields /> : null}
          {detailKind === 'BOUQUET' ? <BouquetFields /> : null}
        </>
      ) : null}

      <button
        type="submit"
        style={{
          border: 'none',
          background: '#8f3d2e',
          color: 'white',
          padding: '10px 18px',
          borderRadius: 12,
          cursor: saving ? 'wait' : 'pointer',
          opacity: saving ? 0.75 : 1,
        }}
        disabled={saving}
      >
        {saving ? 'Guardando...' : mode === 'edit' ? 'Guardar cambios' : 'Crear item'}
      </button>
    </Form>
  )
}

function VestidoFields() {
  return (
    <>
      <Row gutter={12}>
        <Col span={12}>
          <Form.Item label="Tipo de vestido" name={['detail', 'dress_type']} rules={[{ required: true }]}>
            <Select options={TIPO_VESTIDO_OPTIONS} />
          </Form.Item>
        </Col>
        <Col span={12}>
          <Form.Item label="Talla" name={['detail', 'dress_size']} rules={[{ required: true }]}>
            <Select options={TALLA_OPTIONS} />
          </Form.Item>
        </Col>
      </Row>

      <Row gutter={12}>
        <Col span={12}>
          <Form.Item label="Corte de falda" name={['detail', 'skirt_cut']}>
            <Input />
          </Form.Item>
        </Col>
        <Col span={12}>
          <Form.Item label="Tipo de escote" name={['detail', 'neckline_type']}>
            <Input />
          </Form.Item>
        </Col>
      </Row>

      <Row gutter={12}>
        <Col span={12}>
          <Form.Item label="Copa" name={['detail', 'cup_size']}>
            <Select allowClear options={COPA_OPTIONS} />
          </Form.Item>
        </Col>
        <Col span={12}>
          <Form.Item label="Largo de falda" name={['detail', 'skirt_length']}>
            <InputNumber min={0} style={{ width: '100%' }} />
          </Form.Item>
        </Col>
      </Row>

      <Space size={24} wrap style={{ marginBottom: 12 }}>
        <Form.Item label="Tiene cola" name={['detail', 'has_train']} valuePropName="checked">
          <Switch />
        </Form.Item>
        <Form.Item label="Tiene manga" name={['detail', 'has_sleeves']} valuePropName="checked">
          <Switch />
        </Form.Item>
        <Form.Item label="Tiene pedreria" name={['detail', 'has_stoning']} valuePropName="checked">
          <Switch />
        </Form.Item>
      </Space>

      <Form.Item label="Observaciones del detalle" name={['detail', 'notes']}>
        <Input.TextArea rows={2} />
      </Form.Item>
    </>
  )
}

function VeloFields() {
  return (
    <>
      <Row gutter={12}>
        <Col span={12}>
          <Form.Item label="Tipo de velo" name={['detail', 'veil_type']} rules={[{ required: true }]}>
            <Input />
          </Form.Item>
        </Col>
        <Col span={12}>
          <Form.Item label="Tamaño" name={['detail', 'size']} rules={[{ required: true }]}>
            <Select options={TAMANO_OPTIONS} />
          </Form.Item>
        </Col>
      </Row>

      <Row gutter={12}>
        <Col span={12}>
          <Form.Item label="Largo" name={['detail', 'length']}>
            <InputNumber min={0} style={{ width: '100%' }} />
          </Form.Item>
        </Col>
        <Col span={12}>
          <Form.Item label="Capas" name={['detail', 'layers']}>
            <InputNumber min={1} style={{ width: '100%' }} />
          </Form.Item>
        </Col>
      </Row>

      <Row gutter={12}>
        <Col span={12}>
          <Form.Item label="Borde" name={['detail', 'edge']}>
            <Input />
          </Form.Item>
        </Col>
        <Col span={12}>
          <Form.Item label="Decoracion" name={['detail', 'decoration']} rules={[{ required: true }]}>
            <Input />
          </Form.Item>
        </Col>
      </Row>

      <Form.Item label="Observaciones del detalle" name={['detail', 'notes']}>
        <Input.TextArea rows={2} />
      </Form.Item>
    </>
  )
}

function BouquetFields() {
  return (
    <>
      <Row gutter={12}>
        <Col span={12}>
          <Form.Item label="Tipo de bouquet" name={['detail', 'bouquet_type']}>
            <Input />
          </Form.Item>
        </Col>
        <Col span={12}>
          <Form.Item label="Tamaño" name={['detail', 'size']} rules={[{ required: true }]}>
            <Select options={TAMANO_OPTIONS} />
          </Form.Item>
        </Col>
      </Row>

      <Row gutter={12}>
        <Col span={12}>
          <Form.Item label="Tipo de flor" name={['detail', 'flower_type']}>
            <Input />
          </Form.Item>
        </Col>
        <Col span={12}>
          <Form.Item label="Decoracion" name={['detail', 'decoration']}>
            <Input />
          </Form.Item>
        </Col>
      </Row>

      <Form.Item label="Observaciones del detalle" name={['detail', 'notes']}>
        <Input.TextArea rows={2} />
      </Form.Item>
    </>
  )
}
