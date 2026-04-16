import { LockOutlined, UserOutlined } from '@ant-design/icons'
import { Alert, App as AntdApp, Button, Card, Form, Input, Typography } from 'antd'
import { useState } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'

import { useAuth } from '../../auth/AuthProvider'

export function LoginPage() {
  const [error, setError] = useState(null)
  const [form] = Form.useForm()
  const navigate = useNavigate()
  const location = useLocation()
  const { login, loading } = useAuth()
  const { message } = AntdApp.useApp()

  const handleSubmit = async (values) => {
    setError(null)
    try {
      const session = await login(values)
      message.success(`Bienvenida(o), ${session.user.full_name}.`)
      const nextPath = session.user.must_change_password
        ? '/app/cambiar-clave'
        : location.state?.from?.pathname || '/app'
      navigate(nextPath, { replace: true })
    } catch (requestError) {
      setError(requestError.response?.data?.detail || 'No fue posible iniciar sesion.')
    }
  }

  return (
    <main className="auth-page">
      <Card className="auth-card glass-panel" bodyStyle={{ padding: 0 }}>
        <div className="auth-grid">
          <section className="auth-brand">
           <img
           src="/logo_bellaarte1.png"
           alt="Logo BellaArte"
           style={{ marginTop: 10, maxWidth: '420px', height: 'auto', display: 'block', marginLeft: 'auto',
            marginRight: 'auto'}}
           />
          </section>

          <section className="auth-form-panel">
            <Typography.Title level={2}>INICIAR SESION</Typography.Title>
            <Typography.Paragraph type="secondary">
              Ingresa con tu nombre de usuario y contraseña interna.
            </Typography.Paragraph>

            {error ? <Alert type="error" message={error} showIcon style={{ marginBottom: 20 }} /> : null}

            <Form form={form} layout="vertical" onFinish={handleSubmit} size="large">
              <Form.Item
                label="Usuario"
                name="username"
                rules={[{ required: true, message: 'Ingresa tu nombre de usuario.' }]}
              >
                <Input prefix={<UserOutlined />} placeholder="admin" autoComplete="username" />
              </Form.Item>

              <Form.Item
                label="Contraseña"
                name="password"
                rules={[{ required: true, message: 'Ingresa tu contrasena.' }]}
              >
                <Input.Password
                  prefix={<LockOutlined />}
                  placeholder="********"
                  autoComplete="current-password"
                />
              </Form.Item>

              <Button type="primary" htmlType="submit" block loading={loading}>
                Entrar al sistema
              </Button>
            </Form>
          </section>
        </div>
      </Card>
    </main>
  )
}
