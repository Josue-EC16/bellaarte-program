/* eslint-disable react/prop-types */
import { Button, Form, Input } from 'antd'

import {
  FORM_COMMON_PROPS,
  FORM_DRAWER_SUBMIT_PROPS,
} from '../../components/forms/formConfig'

export function BoutiqueTypeForm({ form, onFinish, saving, submitLabel }) {
  return (
    <Form {...FORM_COMMON_PROPS} form={form} onFinish={onFinish}>
      <Form.Item
        label="Nombre del tipo"
        name="nombre"
        rules={[
          { required: true, message: 'Debe ingresar el nombre del tipo.' },
          { min: 2, message: 'El nombre del tipo debe tener al menos 2 caracteres.' },
        ]}
        extra="Usa un nombre corto y claro para identificar la categoría base del producto."
        normalize={(value) => (value || '').replace(/[^a-zA-ZáéíóúÁÉÍÓÚñÑ\s]/g, '').toUpperCase()}
      >
        <Input placeholder="Ej. VESTIDO, VELO, BOUQUET" />
      </Form.Item>

      <Form.Item
        label="Descripción"
        name="descripcion"
        extra="Opcional. Describe el uso de la categoría dentro de la boutique."
        normalize={(value) => (value || '').toUpperCase()}
      >
        <Input.TextArea rows={3} placeholder="Ej. PRODUCTOS RELACIONADOS CON VESTIDOS DE EXHIBICIÓN O VENTA" />
      </Form.Item>

      <Button {...FORM_DRAWER_SUBMIT_PROPS} loading={saving}>
        {submitLabel}
      </Button>
    </Form>
  )
}
