/* eslint-disable react/prop-types */
import { BgColorsOutlined } from '@ant-design/icons'
import { Button, Col, Form, Input, InputNumber, Row, Select, Space, Switch, Typography } from 'antd'
import { useState } from 'react'

import {
  FORM_COMMON_PROPS,
  FORM_DRAWER_SUBMIT_PROPS,
} from '../../components/forms/formConfig'
import { COPA_OPTIONS, TAMANO_OPTIONS, TALLA_OPTIONS, TIPO_VESTIDO_OPTIONS, inferDetailKindFromTypeName } from './boutiqueConstants'
import { ColorPickerModal, COLOR_MAP } from './ColorPickerModal'

export function BoutiqueItemForm({ form, types, mode = 'create', onFinish, saving }) {
  const selectedTypeId = Form.useWatch('type_id', form)
  const selectedType = types.find((type) => type.id === selectedTypeId)
  const detailKind = inferDetailKindFromTypeName(selectedType?.nombre)
  const [colorModalOpen, setColorModalOpen] = useState(false)
  const selectedColor = Form.useWatch(['item', 'color'], form)

  return (
    <Form {...FORM_COMMON_PROPS} form={form} onFinish={onFinish}>
      <Typography.Title level={5}>Datos base</Typography.Title>
      <Row gutter={12}>
        <Col span={12}>
          <Form.Item
            label="Tipo de producto"
            name="type_id"
            rules={[{ required: true, message: 'Debe seleccionar el tipo de producto.' }]}
            extra={mode === 'edit' ? 'El tipo queda bloqueado para conservar la consistencia del detalle.' : 'Selecciona primero la categoría para habilitar el detalle correcto.'}
          >
            <Select
              disabled={mode === 'edit'}
              placeholder="Selecciona la categoría del producto"
              options={types.map((type) => ({
                label: type.nombre,
                value: type.id,
                disabled: !type.habilitado && mode === 'create',
              }))}
            />
          </Form.Item>
        </Col>
        <Col span={12}>
          <Form.Item
            label="Código"
            name={['item', 'code']}
            rules={[{ required: true, message: 'El Código del producto es obligatorio.' }]}
            extra="Usa un código único y fácil de identificar en inventario."
            normalize={(value) => (value || '').replace(/[^a-zA-Z0-9-]/g, '').toUpperCase()}
          >
            <Input placeholder="Ej. VES-001 o BOU-015" />
          </Form.Item>
        </Col>
      </Row>

      <Row gutter={12}>
        <Col span={12}>
          <Form.Item
            label="Nombre"
            name={['item', 'name']}
            rules={[{ required: true, message: 'El Nombre del producto es obligatorio.' }]}
            normalize={(value) => (value || '').replace(/[^a-zA-ZáéíóúÁÉÍÓÚñÑ\s]/g, '').toUpperCase()}
          >
            <Input placeholder="Ej. VESTIDO PRINCESA BLANCO" />
          </Form.Item>
        </Col>
        <Col span={12}>
          <Form.Item
            label="Color"
            name={['item', 'color']}
            rules={[{ required: true, message: 'El Color del producto es obligatorio.' }]}
          >
            <div
              onClick={() => setColorModalOpen(true)}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: 10,
                border: '1px solid #d9d9d9',
                borderRadius: 8,
                padding: '6px 12px',
                cursor: 'pointer',
                background: '#fff',
                transition: 'border-color 0.2s',
                minHeight: 40,
              }}
              onMouseEnter={(e) => (e.currentTarget.style.borderColor = '#8f3d2e')}
              onMouseLeave={(e) => (e.currentTarget.style.borderColor = '#d9d9d9')}
            >
              {selectedColor ? (
                <>
                  <div
                    style={{
                      width: 26,
                      height: 26,
                      borderRadius: 6,
                      background: COLOR_MAP[selectedColor] || '#e0e0e0',
                      border: '1.5px solid rgba(0,0,0,0.15)',
                      flexShrink: 0,
                    }}
                  />
                  <span style={{ fontWeight: 500 }}>{selectedColor}</span>
                </>
              ) : (
                <span style={{ color: '#aaa' }}>
                  <BgColorsOutlined style={{ marginRight: 6 }} />
                  Haz clic para seleccionar un color
                </span>
              )}
              <Button
                size="small"
                type="link"
                style={{ marginLeft: 'auto', fontSize: 12 }}
                onClick={(e) => {
                  e.stopPropagation()
                  setColorModalOpen(true)
                }}
              >
                Cambiar
              </Button>
            </div>
          </Form.Item>

          <ColorPickerModal
            open={colorModalOpen}
            onSelect={(colorName) => {
              form.setFieldValue(['item', 'color'], colorName)
              form.validateFields([['item', 'color']]) // Forzar re-validación al seleccionar
              setColorModalOpen(false)
            }}
            onCancel={() => setColorModalOpen(false)}
          />
        </Col>
      </Row>

      <Row gutter={12}>
        <Col span={12}>
          <Form.Item
            label="Forma"
            name={['item', 'shape']}
            extra="Opcional. Úsalo si la forma o estilo ayuda a identificar el producto."
            normalize={(value) => (value || '').replace(/[^a-zA-ZáéíóúÁÉÍÓÚñÑ\s]/g, '').toUpperCase()}
          >
            <Input placeholder="Ej. CORTE A, REDONDO O RECTO" />
          </Form.Item>
        </Col>
        <Col span={12}>
          <Form.Item
            label="Material"
            name={['item', 'material']}
            rules={[{ required: true, message: 'El Material del producto es obligatorio.' }]}
            normalize={(value) => (value || '').replace(/[^a-zA-ZáéíóúÁÉÍÓÚñÑ\s]/g, '').toUpperCase()}
          >
            <Input placeholder="Ej. SATÉN, TUL O FLORES ARTIFICIALES" />
          </Form.Item>
        </Col>
      </Row>

      <Form.Item
        label="Medidas (cm)"
        name={['item', 'measurements']}
        extra="Opcional. Registra medidas generales si el artículo las necesita."
        normalize={(value) => (value || '').toUpperCase()}
      >
        <Input.TextArea rows={2} placeholder="Ej. LARGO 120 CM, CINTURA 68 CM, CONTORNO 88 CM" />
      </Form.Item>

      <Row gutter={12}>
        <Col span={12}>
          <Form.Item
            label="Proveedor"
            name={['item', 'supplier']}
            normalize={(value) => (value || '').replace(/[^a-zA-ZáéíóúÁÉÍÓÚñÑ\s]/g, '').toUpperCase()}
          >
            <Input placeholder="Ej. PROVEEDOR CENTRAL O IMPORTADORA SUR" />
          </Form.Item>
        </Col>
        <Col span={12}>
          <Form.Item
            label="Descripción"
            name={['item', 'description']}
            extra="Opcional. Resume un rasgo distintivo útil para venta o consulta."
            normalize={(value) => (value || '').toUpperCase()}
          >
            <Input placeholder="Ej. MODELO DE EXHIBICIÓN CON APLICACIONES DE ENCAJE" />
          </Form.Item>
        </Col>
      </Row>

      <Row gutter={12}>
        <Col span={12}>
          <Form.Item label="Precio de compra" name={['item', 'purchase_price']} rules={[{ required: true, message: 'El Precio de compra es obligatorio.' }]} extra="Ingresa el costo referencial pagado por la boutique." normalize={(value) => {
              if (value === null || value === undefined || value === '') return null;
              return value.toString().replace(/[^0-9.]/g, '')
            }}>
            <InputNumber min={0} style={{ width: '100%' }} prefix="Bs." placeholder="Ej. 1500.50" decimalSeparator="." />
          </Form.Item>
        </Col>
        <Col span={12}>
          <Form.Item 
            label="Precio de venta"
            name={['item', 'sale_price']} 
            extra="Debe ser mayor al precio de compra para respetar la regla comercial."
            normalize={(value) => {
              if (value === null || value === undefined || value === '') return null;
              return value.toString().replace(/[^0-9.]/g, '')
            }}
            rules={[
              { required: true, message: 'El Precio de venta es obligatorio.' },
              ({ getFieldValue }) => ({
                validator(_, value) {
                  const purchasePrice = getFieldValue(['item', 'purchase_price'])
                  if (value !== undefined && value !== null && purchasePrice !== undefined && purchasePrice !== null) {
                    if (value <= purchasePrice) {
                      return Promise.reject(new Error('El precio de venta no puede ser menor o igual al de compra.'))
                    }
                  }
                  return Promise.resolve()
                },
              }),
            ]}
          >
            <InputNumber min={0} style={{ width: '100%' }} prefix="Bs." placeholder="Ej. 3000.00" decimalSeparator="." />
          </Form.Item>
        </Col>
      </Row>

      <Row gutter={12}>
        <Col span={12}>
          <Form.Item label="Stock" name={['item', 'stock']} rules={[{ required: true, message: 'El Stock es obligatorio.' }]} extra="Registra la cantidad disponible para vender hoy." normalize={(value) => {
              if (value === null || value === undefined || value === '') return null;
              return value.toString().replace(/[^0-9]/g, '')
            }}>
            <InputNumber min={1} style={{ width: '100%' }} placeholder="Ej. 5" />
          </Form.Item>
        </Col>
        <Col span={12}>
          <Form.Item label="Stock mínimo" name={['item', 'stock_min']} rules={[{ required: true, message: 'El Stock mínimo es obligatorio.' }]} extra="Define desde qué cantidad debe considerarse stock bajo." normalize={(value) => {
              if (value === null || value === undefined || value === '') return null;
              return value.toString().replace(/[^0-9]/g, '')
            }}>
            <InputNumber min={1} style={{ width: '100%' }} placeholder="Ej. 1" />
          </Form.Item>
        </Col>
      </Row>

      <Form.Item
        label="Observaciones"
        name={['item', 'notes']}
        extra="Opcional. Agrega datos útiles para ventas, control o reposición."
        normalize={(value) => (value || '').toUpperCase()}
      >
        <Input.TextArea rows={2} placeholder="Ej. REQUIERE FUNDA ESPECIAL O PRESENTA DETALLES DE EXHIBICIÓN" />
      </Form.Item>

      {detailKind !== 'OTRO' ? (
        <>
          <Typography.Title level={5}>Detalle especializado</Typography.Title>
          <Typography.Paragraph type="secondary">
            Completa solo el detalle que corresponde al tipo seleccionado. Esto ayuda a mantener la información consistente con la base de datos.
          </Typography.Paragraph>
          {detailKind === 'VESTIDO' ? <VestidoFields /> : null}
          {detailKind === 'VELO' ? <VeloFields /> : null}
          {detailKind === 'BOUQUET' ? <BouquetFields /> : null}
        </>
      ) : null}

      <Button {...FORM_DRAWER_SUBMIT_PROPS} loading={saving}>
        {mode === 'edit' ? 'Guardar cambios' : 'Crear producto'}
      </Button>
    </Form>
  )
}

function VestidoFields() {
  return (
    <>
      <Row gutter={12}>
        <Col span={12}>
          <Form.Item label="Tipo de vestido" name={['detail', 'dress_type']} rules={[{ required: true, message: 'Debe seleccionar un tipo de vestido.' }]} extra="Selecciona la categoría documental que mejor describe el vestido.">
            <Select options={TIPO_VESTIDO_OPTIONS} placeholder="Selecciona el tipo de vestido"/>
          </Form.Item>
        </Col>
        <Col span={12}>
          <Form.Item label="Talla" name={['detail', 'dress_size']} rules={[{ required: true, message: 'Debe seleccionar una talla de vestido.' }]} extra="Elige la talla base más cercana al producto registrado.">
            <Select options={TALLA_OPTIONS} placeholder="Selecciona la talla del vestido"/>
          </Form.Item>
        </Col>
      </Row>

      <Row gutter={12}>
        <Col span={12}>
          <Form.Item 
            label="Corte de falda" 
            name={['detail', 'skirt_cut']}
            normalize={(value) => (value || '').replace(/[^a-zA-ZáéíóúÁÉÍÓÚñÑ\s]/g, '').toUpperCase()}
          >
            <Input placeholder="Ej. PRINCESA" />
          </Form.Item>
        </Col>
        <Col span={12}>
          <Form.Item 
            label="Tipo de escote" 
            name={['detail', 'neckline_type']}
            normalize={(value) => (value || '').replace(/[^a-zA-ZáéíóúÁÉÍÓÚñÑ\s]/g, '').toUpperCase()}
          >
            <Input placeholder="Ej. CORAZON" />
          </Form.Item>
        </Col>
      </Row>

      <Row gutter={12}>
        <Col span={12}>
          <Form.Item label="Copa" name={['detail', 'cup_size']}>
            <Select allowClear options={COPA_OPTIONS} placeholder="Selecciona la talla de copa"/>
          </Form.Item>
        </Col>
        <Col span={12}>
          <Form.Item label="Largo de falda (cm)" name={['detail', 'skirt_length']} normalize={(value) => {
              if (value === null || value === undefined || value === '') return null;
              return value.toString().replace(/[^0-9.]/g, '')
            }}>
            <InputNumber min={0} style={{ width: '100%' }} placeholder="Ej. 120" />
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
        <Form.Item label="Tiene pedrería" name={['detail', 'has_stoning']} valuePropName="checked">
          <Switch />
        </Form.Item>
      </Space>

      <Form.Item 
        label="Observaciones del detalle" 
        name={['detail', 'notes']}
        normalize={(value) => (value || '').toUpperCase()}
      >
        <Input.TextArea rows={2} placeholder="Observaciones específicas del vestido" />
      </Form.Item>
    </>
  )
}

function VeloFields() {
  return (
    <>
      <Row gutter={12}>
        <Col span={12}>
          <Form.Item 
            label="Tipo de velo" 
            name={['detail', 'veil_type']} 
            rules={[{ required: true, message: 'Debe especificar el tipo de velo.' }]}
            normalize={(value) => (value || '').replace(/[^a-zA-ZáéíóúÁÉÍÓÚñÑ\s]/g, '').toUpperCase()}
          >
            <Input placeholder="Ej. MANTILLA" />
          </Form.Item>
        </Col>
        <Col span={12}>
          <Form.Item label="Tamaño" name={['detail', 'size']} rules={[{ required: true, message: 'Debe seleccionar un tamaño para el velo.' }]} extra="Selecciona la categoría de tamaño según el documento base.">
            <Select options={TAMANO_OPTIONS} placeholder="Selecciona el tamaño del velo"/>
          </Form.Item>
        </Col>
      </Row>

      <Row gutter={12}>
        <Col span={12}>
          <Form.Item label="Largo (cm)" name={['detail', 'length']} normalize={(value) => {
              if (value === null || value === undefined || value === '') return null;
              return value.toString().replace(/[^0-9]/g, '')
            }}>
            <InputNumber min={0} style={{ width: '100%' }} placeholder="Ej. 300" />
          </Form.Item>
        </Col>
        <Col span={12}>
          <Form.Item label="Capas" name={['detail', 'layers']} normalize={(value) => {
              if (value === null || value === undefined || value === '') return null;
              return value.toString().replace(/[^0-9]/g, '')
            }}>
            <InputNumber min={1} style={{ width: '100%' }} placeholder="Introducir el numero de capas del velo" />
          </Form.Item>
        </Col>
      </Row>

      <Row gutter={12}>
        <Col span={12}>
          <Form.Item 
            label="Borde" 
            name={['detail', 'edge']}
            normalize={(value) => (value || '').replace(/[^a-zA-ZáéíóúÁÉÍÓÚñÑ\s]/g, '').toUpperCase()}
          >
            <Input placeholder="Ej. ONDULADO" />
          </Form.Item>
        </Col>
        <Col span={12}>
          <Form.Item 
            label="Decoración" 
            name={['detail', 'decoration']} 
            rules={[{ required: true, message: 'Debe describir la decoración del velo.' }]}
            normalize={(value) => (value || '').replace(/[^a-zA-ZáéíóúÁÉÍÓÚñÑ\s]/g, '').toUpperCase()}  
          >
            <Input placeholder="Ej. ENCAJE Y PEDRERIA" />
          </Form.Item>
        </Col>
      </Row>

      <Form.Item 
        label="Observaciones del detalle" 
        name={['detail', 'notes']}
        normalize={(value) => (value || '').toUpperCase()}
      >
        <Input.TextArea rows={2} placeholder="Observaciones específicas del velo" />
      </Form.Item>
    </>
  )
}

function BouquetFields() {
  return (
    <>
      <Row gutter={12}>
        <Col span={12}>
          <Form.Item 
            label="Tipo de bouquet" 
            name={['detail', 'bouquet_type']}
            normalize={(value) => (value || '').replace(/[^a-zA-ZáéíóúÁÉÍÓÚñÑ\s]/g, '').toUpperCase()}
          >
            <Input placeholder="Ej. REDONDO" />
          </Form.Item>
        </Col>
        <Col span={12}>
          <Form.Item label="Tamaño" name={['detail', 'size']} rules={[{ required: true, message: 'Debe seleccionar un tamaño para el bouquet.' }]} extra="Selecciona la categoría de tamaño que mejor represente el bouquet.">
            <Select options={TAMANO_OPTIONS} placeholder="Selecciona el tamaño del bouquet"/>
          </Form.Item>
        </Col>
      </Row>

      <Row gutter={12}>
        <Col span={12}>
          <Form.Item 
            label="Tipo de flor" 
            name={['detail', 'flower_type']}
            normalize={(value) => (value || '').replace(/[^a-zA-ZáéíóúÁÉÍÓÚñÑ\s]/g, '').toUpperCase()}
          >
            <Input placeholder="Ej. ROSAS BLANCAS" />
          </Form.Item>
        </Col>
        <Col span={12}>
          <Form.Item 
            label="Decoración" 
            name={['detail', 'decoration']}
            normalize={(value) => (value || '').replace(/[^a-zA-ZáéíóúÁÉÍÓÚñÑ\s]/g, '').toUpperCase()}
          >
            <Input placeholder="Ej. CINTA DE SEDA" />
          </Form.Item>
        </Col>
      </Row>

      <Form.Item 
        label="Observaciones del detalle" 
        name={['detail', 'notes']}
        normalize={(value) => (value || '').toUpperCase()}
      >
        <Input.TextArea rows={2} placeholder="Observaciones específicas del bouquet" />
      </Form.Item>
    </>
  )
}
