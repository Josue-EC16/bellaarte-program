/* eslint-disable react/prop-types */
import { Alert, Button, Form, Input, Switch } from 'antd'

import {
  FORM_COMMON_PROPS,
  FORM_DRAWER_SUBMIT_PROPS,
} from '../../components/forms/formConfig'

export function ReceiptTypeForm({ form, onFinish, saving, submitLabel, editingType, isSystemType }) {
  const systemType = editingType ? isSystemType(editingType) : false

  return (
    <Form {...FORM_COMMON_PROPS} form={form} onFinish={onFinish}>
      {editingType ? (
        <Alert
          type="info"
          showIcon
          style={{ marginBottom: 16 }}
          message={systemType ? 'TIPO BASE DEL SISTEMA' : 'TIPO PERSONALIZADO'}
          description={
            systemType
              ? 'El nombre técnico se conserva porque este tipo participa en la emisión automática de comprobantes.'
              : 'La edición se concentra en la descripción y en la naturaleza fiscal del tipo.'
          }
        />
      ) : null}

      <Form.Item
        label="Nombre técnico"
        name="nombre"
        rules={[
          { required: true, message: 'Debe ingresar el nombre técnico del tipo.' },
          { min: 3, message: 'El nombre técnico debe tener al menos 3 caracteres.' },
        ]}
        extra="Usa un identificador interno claro. Se convertirá automáticamente a MAYÚSCULAS con guiones bajos."
        normalize={(value) =>
          (value || '')
            .toUpperCase()
            .replace(/\s+/g, '_')
            .replace(/[^A-Z0-9_]/g, '')
        }
      >
        <Input
          placeholder="Ej. COMPROBANTE_INTERNO_CONTROL"
          disabled={Boolean(editingType)}
        />
      </Form.Item>

      <Form.Item
        label="Descripción"
        name="descripcion"
        extra="Opcional. Ayuda a identificar cuándo se usa este tipo dentro del control interno."
        normalize={(value) => (value || '').toUpperCase()}
      >
        <Input.TextArea
          rows={3}
          placeholder="Ej. RESPALDO COMERCIAL DE COBROS Y MOVIMIENTOS INTERNOS"
        />
      </Form.Item>

      <Form.Item
        label="¿Es fiscal?"
        name="es_fiscal"
        valuePropName="checked"
        extra="En esta v1 normalmente los tipos del sistema nacen como NO FISCALES."
      >
        <Switch checkedChildren="SÍ" unCheckedChildren="NO" />
      </Form.Item>

      <Button {...FORM_DRAWER_SUBMIT_PROPS} loading={saving}>
        {submitLabel}
      </Button>
    </Form>
  )
}
