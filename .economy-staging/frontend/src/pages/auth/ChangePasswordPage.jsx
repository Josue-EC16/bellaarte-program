import { App as AntdApp, Button, Card, Form, Input, Typography } from 'antd'
import { useState } from 'react'
import { useNavigate } from 'react-router-dom'

import { useAuth } from '../../auth/AuthProvider'
import {
  FORM_COMMON_PROPS,
  FORM_DRAWER_SUBMIT_PROPS,
} from '../../components/forms/formConfig'
import { applyFormApiError } from '../../components/forms/formErrorUtils'
import { FormProcessAlert } from '../../components/forms/FormProcessAlert'

export function ChangePasswordPage() {
  const [formError, setFormError] = useState(null)
  const [form] = Form.useForm()
  const navigate = useNavigate()
  const { changePassword, loading } = useAuth()
  const { message } = AntdApp.useApp()

  const handleSubmit = async (values) => {
    setFormError(null)
    try {
      await changePassword({
        current_password: values.current_password,
        new_password: values.new_password,
      })
      message.success('Contrasena actualizada correctamente.')
      navigate('/app', { replace: true })
    } catch (requestError) {
      const resolved = applyFormApiError(form, requestError, {
        messageFieldMap: [
          { test: /contrasena actual no es valida/i, field: 'current_password' },
          {
            test: /nueva contrasena no puede ser igual a la actual/i,
            field: 'new_password',
          },
        ],
        fallbackGlobalMessage: 'No fue posible actualizar la contraseña.',
      })
      setFormError(resolved.globalMessage)
    }
  }

  return (
    <Card className="glass-panel" style={{ maxWidth: 640, margin: '0 auto', borderRadius: 28 }}>
      <Typography.Title level={2}>Cambio obligatorio de clave</Typography.Title>
      <Typography.Paragraph type="secondary">
        Antes de continuar, debes definir una contraseña nueva para proteger tu cuenta.
      </Typography.Paragraph>

      <FormProcessAlert message={formError} title="No fue posible actualizar la contraseña." />

      <Form {...FORM_COMMON_PROPS} form={form} onFinish={handleSubmit} size="large">
        <Form.Item
          name="current_password"
          label="Contraseña actual"
          extra="Ingresa la contraseña con la que accedes hoy al sistema."
          rules={[{ required: true, message: 'Debe ingresar tu contraseña actual.' }]}
        >
          <Input.Password autoComplete="current-password" />
        </Form.Item>

        <Form.Item
          name="new_password"
          label="Nueva contraseña"
          extra="Debe tener al menos 8 caracteres, una mayúscula, una minúscula, un número y un carácter especial."
          rules={[
            { required: true, message: 'Debe ingresar tu nueva contraseña.' },
            {
              pattern: /^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[^A-Za-z0-9]).{8,}$/,
              message:
                'Debe tener al menos 8 caracteres, una mayúscula, una minúscula, un número y un carácter especial.',
            },
          ]}
        >
          <Input.Password autoComplete="new-password" />
        </Form.Item>

        <Form.Item
          name="confirm_password"
          label="Confirmar nueva contraseña"
          dependencies={['new_password']}
          rules={[
            { required: true, message: 'Debe confirmar tu nueva contraseña.' },
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

        <Button {...FORM_DRAWER_SUBMIT_PROPS} loading={loading}>
          Guardar nueva contraseña
        </Button>
      </Form>
    </Card>
  )
}
