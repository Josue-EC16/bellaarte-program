/* eslint-disable react/prop-types */
import { Button, Form, Input } from 'antd'

export function BoutiqueTypeForm({ form, onFinish, saving }) {
  return (
    <Form layout="vertical" form={form} onFinish={onFinish}>
      <Form.Item label="Nombre del tipo" name="nombre" rules={[{ required: true, min: 2 }]}>
        <Input placeholder="Ej. VESTIDO" />
      </Form.Item>

      <Form.Item label="Descripcion" name="descripcion">
        <Input.TextArea rows={3} placeholder="Describe el uso del tipo boutique" />
      </Form.Item>

      <Button type="primary" htmlType="submit" loading={saving}>
        Guardar tipo
      </Button>
    </Form>
  )
}
