import { Alert, App as AntdApp, Button, Card, Form, Input, Typography } from 'antd'
import { useState } from 'react'
import { useNavigate } from 'react-router-dom'

import { useAuth } from '../../auth/AuthProvider'

export function ChangePasswordPage() {
  const [error, setError] = useState(null)
  const [form] = Form.useForm()
  const navigate = useNavigate()
  const { changePassword, loading } = useAuth()
  const { message } = AntdApp.useApp()

  const handleSubmit = async (values) => {
    setError(null)
    try {
      await changePassword({
        current_password: values.current_password,
        new_password: values.new_password,
      })
      message.success('Contrasena actualizada correctamente.')
      navigate('/app', { replace: true })
    } catch (requestError) {
      setError(requestError.response?.data?.detail || 'No fue posible actualizar la contrasena.')
    }
  }

  return (
    <Card className="glass-panel" style={{ maxWidth: 640, margin: '0 auto', borderRadius: 28 }}>
      <Typography.Title level={2}>Cambio obligatorio de clave</Typography.Title>
      <Typography.Paragraph type="secondary">
        Antes de continuar, debes definir una contrasena nueva para proteger tu cuenta.
      </Typography.Paragraph>

      {error ? <Alert type="error" message={error} showIcon style={{ marginBottom: 20 }} /> : null}

      <Form form={form} layout="vertical" onFinish={handleSubmit} size="large">
        <Form.Item
          name="current_password"
          label="Contrasena actual"
          rules={[{ required: true, message: 'Ingresa tu contrasena actual.' }]}
        >
          <Input.Password autoComplete="current-password" />
        </Form.Item>

        <Form.Item
          name="new_password"
          label="Nueva contrasena"
          rules={[
            { required: true, message: 'Ingresa la nueva contrasena.' },
            { 
              pattern: /^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[^A-Za-z0-9]).{8,}$/, 
              message: 'Mínimo 8 caracteres, 1 mayúscula, 1 minúscula, 1 número y 1 carácter especial.' 
            },
          ]}
        >
          <Input.Password autoComplete="new-password" />
        </Form.Item>

        <Form.Item
          name="confirm_password"
          label="Confirmar nueva contrasena"
          dependencies={['new_password']}
          rules={[
            { required: true, message: 'Confirma la nueva contrasena.' },
            ({ getFieldValue }) => ({
              validator(_, value) {
                if (!value || getFieldValue('new_password') === value) {
                  return Promise.resolve()
                }
                return Promise.reject(new Error('Las contrasenas no coinciden.'))
              },
            }),
          ]}
        >
          <Input.Password autoComplete="new-password" />
        </Form.Item>

        <Button type="primary" htmlType="submit" loading={loading}>
          Guardar nueva contrasena
        </Button>
      </Form>
    </Card>
  )
}

