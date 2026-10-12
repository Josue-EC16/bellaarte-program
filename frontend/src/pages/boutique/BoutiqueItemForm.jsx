/* eslint-disable react/prop-types */
import { BgColorsOutlined } from '@ant-design/icons'
import { Button, Col, Form, Input, InputNumber, Row, Select, Switch, Typography } from 'antd'
import { useState } from 'react'

import { FORM_COMMON_PROPS, FORM_DRAWER_SUBMIT_PROPS } from '../../components/forms/formConfig'
import { COPA_OPTIONS, TALLA_OPTIONS, TIPO_VESTIDO_OPTIONS, inferDetailKindFromTypeName } from './boutiqueConstants'
import { ColorPickerModal, COLOR_MAP } from './ColorPickerModal'

export function BoutiqueItemForm({ form, types, providers, mode = 'create', onFinish, saving }) {
  const selectedTypeId = Form.useWatch('type_id', form)
  const selectedType = types.find((type) => type.id === selectedTypeId)
  const detailKind = inferDetailKindFromTypeName(selectedType?.nombre)

  const [colorPrimaryModalOpen, setColorPrimaryModalOpen] = useState(false)
  const [colorSecondaryModalOpen, setColorSecondaryModalOpen] = useState(false)

  const selectedColorPrimary = Form.useWatch(['item', 'color_primary'], form)
  const selectedColorSecondary = Form.useWatch(['item', 'color_secondary'], form)

  return (
    <Form {...FORM_COMMON_PROPS} form={form} onFinish={onFinish}>
      <Typography.Title level={5}>Datos base</Typography.Title>

      <Row gutter={12}>
        <Col span={12}>
          <Form.Item
            label="Tipo de producto"
            name="type_id"
            rules={[{ required: true, message: 'Debe seleccionar el Tipo de producto.' }]}
            extra={mode === 'edit' ? 'El tipo no se modifica para mantener la integridad del detalle.' : 'Selecciona primero la categoría del producto.'}
          >
            <Select
              showSearch
              optionFilterProp="label"
              disabled={mode === 'edit'}
              placeholder="Seleccionar el tipo de producto"
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
            normalize={(value) => (value || '').replace(/[^a-zA-Z0-9-]/g, '').toUpperCase()}
          >
            <Input placeholder="Ej. VES-001, VEL-002 o BOU-003" />
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
            <Input placeholder="Introducir el nombre del producto boutique" />
          </Form.Item>
        </Col>
        <Col span={12}>
          <Form.Item
            label="Proveedor"
            name={['item', 'provider_id']}
            extra="Opcional. Selecciona un proveedor habilitado si el artículo lo tiene asociado."
          >
            <Select
              allowClear
              showSearch
              optionFilterProp="label"
              placeholder="Buscar y seleccionar proveedor"
              options={providers.map((provider) => ({
                label: provider.nombre_comercial
                  ? `${provider.full_name} - ${provider.nombre_comercial}`
                  : provider.full_name,
                value: provider.id,
              }))}
            />
          </Form.Item>
        </Col>
      </Row>

      <Row gutter={12}>
        <Col span={12}>
          <Form.Item
            label="Color primario"
            name={['item', 'color_primary']}
            rules={[{ required: true, message: 'El Color primario es obligatorio.' }]}
          >
            <div
              onClick={() => setColorPrimaryModalOpen(true)}
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
              {selectedColorPrimary ? (
                <>
                  <div
                    style={{
                      width: 26,
                      height: 26,
                      borderRadius: 6,
                      background: COLOR_MAP[selectedColorPrimary] || '#e0e0e0',
                      border: '1.5px solid rgba(0,0,0,0.15)',
                      flexShrink: 0,
                    }}
                  />
                  <span style={{ fontWeight: 500 }}>{selectedColorPrimary}</span>
                </>
              ) : (
                <span style={{ color: '#aaa' }}>
                  <BgColorsOutlined style={{ marginRight: 6 }} />
                  Seleccionar color
                </span>
              )}
              <Button
                size="small"
                type="link"
                style={{ marginLeft: 'auto', fontSize: 12 }}
                onClick={(e) => {
                  e.stopPropagation()
                  setColorPrimaryModalOpen(true)
                }}
              >
                Cambiar
              </Button>
            </div>
          </Form.Item>
          
          <ColorPickerModal
            open={colorPrimaryModalOpen}
            onSelect={(colorName) => {
              form.setFieldValue(['item', 'color_primary'], colorName)
              form.validateFields([['item', 'color_primary']])
              setColorPrimaryModalOpen(false)
            }}
            onCancel={() => setColorPrimaryModalOpen(false)}
          />
        </Col>
        
        <Col span={12}>
          <Form.Item
            label="Color secundario"
            name={['item', 'color_secondary']}
          >
            <div
              onClick={() => setColorSecondaryModalOpen(true)}
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
              {selectedColorSecondary ? (
                <>
                  <div
                    style={{
                      width: 26,
                      height: 26,
                      borderRadius: 6,
                      background: COLOR_MAP[selectedColorSecondary] || '#e0e0e0',
                      border: '1.5px solid rgba(0,0,0,0.15)',
                      flexShrink: 0,
                    }}
                  />
                  <span style={{ fontWeight: 500 }}>{selectedColorSecondary}</span>
                </>
              ) : (
                <span style={{ color: '#aaa' }}>
                  <BgColorsOutlined style={{ marginRight: 6 }} />
                  Opcional
                </span>
              )}
              {selectedColorSecondary && (
                <Button
                  size="small"
                  type="text"
                  danger
                  onClick={(e) => {
                    e.stopPropagation()
                    form.setFieldValue(['item', 'color_secondary'], null)
                  }}
                >
                  Quitar
                </Button>
              )}
              <Button
                size="small"
                type="link"
                style={{ marginLeft: selectedColorSecondary ? '0' : 'auto', fontSize: 12 }}
                onClick={(e) => {
                  e.stopPropagation()
                  setColorSecondaryModalOpen(true)
                }}
              >
                {selectedColorSecondary ? 'Cambiar' : 'Seleccionar'}
              </Button>
            </div>
          </Form.Item>
          
          <ColorPickerModal
            open={colorSecondaryModalOpen}
            onSelect={(colorName) => {
              form.setFieldValue(['item', 'color_secondary'], colorName)
              form.validateFields([['item', 'color_secondary']])
              setColorSecondaryModalOpen(false)
            }}
            onCancel={() => setColorSecondaryModalOpen(false)}
          />
        </Col>
      </Row>

      <Row gutter={12}>
        <Col span={12}>
          <Form.Item
            label="Material"
            name={['item', 'material']}
            rules={[{ required: true, message: 'El Material es obligatorio.' }]}
            normalize={(value) => (value || '').toUpperCase()}
          >
            <Input placeholder="Ej. SATÉN, TUL, FLORES ARTIFICIALES" />
          </Form.Item>
        </Col>
        <Col span={6}>
          <Form.Item
            label="Largo"
            name={['item', 'length']}
            normalize={(value) => {
              if (value === null || value === undefined || value === '') return null
              return value.toString().replace(/[^0-9.]/g, '')
            }}
          >
            <InputNumber min={0} precision={2} style={{ width: '100%' }} placeholder="Ej. 120.50" />
          </Form.Item>
        </Col>
        <Col span={6}>
          <Form.Item
            label="Ancho"
            name={['item', 'width']}
            normalize={(value) => {
              if (value === null || value === undefined || value === '') return null
              return value.toString().replace(/[^0-9.]/g, '')
            }}
          >
            <InputNumber min={0} precision={2} style={{ width: '100%' }} placeholder="Ej. 45.00" />
          </Form.Item>
        </Col>
      </Row>

      <Row gutter={12}>
        <Col span={12}>
          <Form.Item
            label="Precio de compra"
            name={['item', 'purchase_price']}
            rules={[{ required: true, message: 'El Precio de compra es obligatorio.' }]}
            normalize={(value) => {
              if (value === null || value === undefined || value === '') return null
              return value.toString().replace(/[^0-9.]/g, '')
            }}
          >
            <InputNumber min={0} precision={2} prefix="Bs." style={{ width: '100%' }} placeholder="Ej. 1500.00" />
          </Form.Item>
        </Col>
        <Col span={12}>
          <Form.Item
            label="Precio de venta"
            name={['item', 'sale_price']}
            rules={[
              { required: true, message: 'El Precio de venta es obligatorio.' },
              ({ getFieldValue }) => ({
                validator(_, value) {
                  const purchasePrice = Number(getFieldValue(['item', 'purchase_price']) || 0)
                  if (value === undefined || value === null || value === '') return Promise.resolve()
                  if (Number(value) < purchasePrice) {
                    return Promise.reject(new Error('El precio de venta no puede ser menor al precio de compra.'))
                  }
                  return Promise.resolve()
                },
              }),
            ]}
            normalize={(value) => {
              if (value === null || value === undefined || value === '') return null
              return value.toString().replace(/[^0-9.]/g, '')
            }}
          >
            <InputNumber min={0} precision={2} prefix="Bs." style={{ width: '100%' }} placeholder="Ej. 2500.00" />
          </Form.Item>
        </Col>
      </Row>

      <Row gutter={12}>
        <Col span={12}>
          <Form.Item
            label="Stock"
            name={['item', 'stock']}
            rules={[{ required: true, message: 'El Stock es obligatorio.' }]}
            normalize={(value) => {
              if (value === null || value === undefined || value === '') return null
              return value.toString().replace(/[^0-9]/g, '')
            }}
          >
            <InputNumber min={0} precision={0} style={{ width: '100%' }} placeholder="Ej. 1, 2, 5" />
          </Form.Item>
        </Col>
        <Col span={12}>
          <Form.Item
            label="Stock mínimo"
            name={['item', 'stock_min']}
            rules={[{ required: true, message: 'El Stock mínimo es obligatorio.' }]}
            normalize={(value) => {
              if (value === null || value === undefined || value === '') return null
              return value.toString().replace(/[^0-9]/g, '')
            }}
          >
            <InputNumber min={0} precision={0} style={{ width: '100%' }} placeholder="Ej. 0, 1, 2" />
          </Form.Item>
        </Col>
      </Row>

      <Form.Item
        label="Detalle general"
        name={['item', 'detail']}
        normalize={(value) => (value || '').toUpperCase()}
        extra="Opcional. Registra información general útil del artículo."
      >
        <Input.TextArea rows={3} placeholder="Ej. MODELO DE EXHIBICIÓN, INCLUYE ACCESORIOS O PRESENTA DETALLES ESPECIALES" />
      </Form.Item>

      {detailKind !== 'OTRO' ? (
        <>
          <Typography.Title level={5}>Detalle especializado</Typography.Title>
          {detailKind === 'VESTIDO' ? <VestidoFields /> : null}
          {detailKind === 'VELO' ? <VeloFields /> : null}
          {detailKind === 'BOUQUET' ? <BouquetFields /> : null}
          {detailKind === 'BRASIER' ? <BrassierFields /> : null}
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
          <Form.Item
            label="Tipo de vestido"
            name={['detail', 'dress_type']}
            rules={[{ required: true, message: 'Debe seleccionar el Tipo de vestido.' }]}
          >
            <Select options={TIPO_VESTIDO_OPTIONS} placeholder="Seleccionar el tipo de vestido" />
          </Form.Item>
        </Col>
        <Col span={12}>
          <Form.Item
            label="Talla"
            name={['detail', 'dress_size']}
            rules={[{ required: true, message: 'Debe seleccionar la Talla del vestido.' }]}
          >
            <Select options={TALLA_OPTIONS} placeholder="Seleccionar la talla del vestido" />
          </Form.Item>
        </Col>
      </Row>

      <Row gutter={12}>
        <Col span={12}>
          <Form.Item
            label="Corte de falda"
            name={['detail', 'skirt_cut']}
            normalize={(value) => (value || '').toUpperCase()}
          >
            <Input placeholder="Ej. PRINCESA, LÍNEA A O RECTA" />
          </Form.Item>
        </Col>
        <Col span={12}>
          <Form.Item
            label="Tipo de escote"
            name={['detail', 'neckline_type']}
            normalize={(value) => (value || '').toUpperCase()}
          >
            <Input placeholder="Ej. CORAZÓN, BARCO O RECTO" />
          </Form.Item>
        </Col>
      </Row>

      <Row gutter={12}>
        <Col span={12}>
          <Form.Item label="Copa" name={['detail', 'cup_size']}>
            <Select allowClear options={COPA_OPTIONS} placeholder="Seleccionar la copa" />
          </Form.Item>
        </Col>
        <Col span={12}>
          <Form.Item
            label="Largo de falda"
            name={['detail', 'skirt_length']}
            normalize={(value) => {
              if (value === null || value === undefined || value === '') return null
              return value.toString().replace(/[^0-9.]/g, '')
            }}
          >
            <InputNumber min={0} precision={2} style={{ width: '100%' }} placeholder="Ej. 115.00" />
          </Form.Item>
        </Col>
      </Row>

      <Row gutter={12}>
        <Col span={8}>
          <Form.Item label="Tiene cola" name={['detail', 'has_train']} valuePropName="checked">
            <Switch />
          </Form.Item>
        </Col>
        <Col span={8}>
          <Form.Item label="Tiene manga" name={['detail', 'has_sleeves']} valuePropName="checked">
            <Switch />
          </Form.Item>
        </Col>
        <Col span={8}>
          <Form.Item label="Tiene pedrería" name={['detail', 'has_stoning']} valuePropName="checked">
            <Switch />
          </Form.Item>
        </Col>
      </Row>

      <Form.Item label="Observaciones del vestido" name={['detail', 'notes']} normalize={(value) => (value || '').toUpperCase()}>
        <Input.TextArea rows={2} placeholder="Ej. CUENTA CON PEDRERÍA EN BUSTO O FALDA EN CAPAS" />
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
            rules={[{ required: true, message: 'Debe introducir el Tipo de velo.' }]}
            normalize={(value) => (value || '').toUpperCase()}
          >
            <Input placeholder="Ej. MANTILLA, CATEDRAL O CORTO" />
          </Form.Item>
        </Col>
        <Col span={12}>
          <Form.Item
            label="Capas"
            name={['detail', 'layers']}
            normalize={(value) => {
              if (value === null || value === undefined || value === '') return null
              return value.toString().replace(/[^0-9]/g, '')
            }}
          >
            <InputNumber min={1} precision={0} style={{ width: '100%' }} placeholder="Ej. 1, 2 o 3" />
          </Form.Item>
        </Col>
      </Row>

      <Row gutter={12}>
        <Col span={12}>
          <Form.Item label="Borde" name={['detail', 'edge']} normalize={(value) => (value || '').toUpperCase()}>
            <Input placeholder="Ej. ONDULADO, LISO O ENCAJE" />
          </Form.Item>
        </Col>
        <Col span={12}>
          <Form.Item label="Decoración" name={['detail', 'decoration']} normalize={(value) => (value || '').toUpperCase()}>
            <Input.TextArea rows={2} placeholder="Ej. ENCAJE, PERLAS O PEDRERÍA" />
          </Form.Item>
        </Col>
      </Row>

      <Form.Item label="Observaciones del velo" name={['detail', 'notes']} normalize={(value) => (value || '').toUpperCase()}>
        <Input.TextArea rows={2} placeholder="Ej. VELO LIVIANO O IDEAL PARA FOTOGRAFÍA EXTERIOR" />
      </Form.Item>
    </>
  )
}

function BouquetFields() {
  return (
    <>
      <Row gutter={12}>
        <Col span={12}>
          <Form.Item label="Tipo de bouquet" name={['detail', 'bouquet_type']} normalize={(value) => (value || '').toUpperCase()}>
            <Input placeholder="Ej. REDONDO, CASCADA O SILVESTRE" />
          </Form.Item>
        </Col>
        <Col span={12}>
          <Form.Item label="Forma" name={['detail', 'shape']} normalize={(value) => (value || '').toUpperCase()}>
            <Input placeholder="Ej. OVALADO, COMPACTO O DESPEINADO" />
          </Form.Item>
        </Col>
      </Row>

      <Row gutter={12}>
        <Col span={12}>
          <Form.Item label="Tipo de flor" name={['detail', 'flower_type']} normalize={(value) => (value || '').toUpperCase()}>
            <Input placeholder="Ej. ROSAS, PEONÍAS O FLORES MIXTAS" />
          </Form.Item>
        </Col>
        <Col span={12}>
          <Form.Item label="Decoración" name={['detail', 'decoration']} normalize={(value) => (value || '').toUpperCase()}>
            <Input.TextArea rows={2} placeholder="Ej. CINTA DE SATÉN, PERLAS O HOJAS SECAS" />
          </Form.Item>
        </Col>
      </Row>

      <Form.Item label="Observaciones del bouquet" name={['detail', 'notes']} normalize={(value) => (value || '').toUpperCase()}>
        <Input.TextArea rows={2} placeholder="Ej. REQUIERE BASE DE AGUA O EMBALAJE ESPECIAL" />
      </Form.Item>
    </>
  )
}

function BrassierFields() {
  return (
    <>
      <Row gutter={12}>
        <Col span={12}>
          <Form.Item
            label="Copa"
            name={['detail', 'cup_size']}
            rules={[{ required: true, message: 'Debe seleccionar la Copa del brassier.' }]}
          >
            <Select options={COPA_OPTIONS} placeholder="Seleccionar la copa del brassier" />
          </Form.Item>
        </Col>
        <Col span={12}>
          <Form.Item label="Marca" name={['detail', 'brand']} normalize={(value) => (value || '').toUpperCase()}>
            <Input placeholder="Ej. LEONISA, INTIME O MARCA PROPIA" />
          </Form.Item>
        </Col>
      </Row>

      <Row gutter={12}>
        <Col span={12}>
          <Form.Item label="Tiene encaje" name={['detail', 'has_lace']} valuePropName="checked">
            <Switch />
          </Form.Item>
        </Col>
      </Row>

      <Form.Item label="Observaciones del brassier" name={['detail', 'notes']} normalize={(value) => (value || '').toUpperCase()}>
        <Input.TextArea rows={2} placeholder="Ej. MODELO REFORZADO, CON ARO O DISEÑO PARA EXHIBICIÓN" />
      </Form.Item>
    </>
  )
}
