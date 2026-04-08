import { LockOutlined, UserOutlined } from '@ant-design/icons'
import { Alert, App as AntdApp, Button, Card, Form, Input, Space, Typography } from 'antd'
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
            <Typography.Text style={{ color: 'rgba(255,250,246,0.75)' }}>
              Boutique y taller
            </Typography.Text>
            <Typography.Title level={1} style={{ color: '#fffaf6', marginTop: 12 }}>
              BellaArte
            </Typography.Title>
            <Typography.Paragraph>
              Controla accesos, usuarios y operaciones desde un panel seguro pensado para el flujo real de la boutique.
            </Typography.Paragraph>
            <Space direction="vertical" size="middle" style={{ marginTop: 32 }}>
              <Typography.Text className="card-muted">Login con usuario interno</Typography.Text>
              <Typography.Text className="card-muted">Roles protegidos con permisos por modulo</Typography.Text>
              <Typography.Text className="card-muted">Cambio obligatorio de clave en primer acceso</Typography.Text>
            </Space>
          </section>

          <section className="auth-form-panel">
            <Typography.Title level={2}>Iniciar sesion</Typography.Title>
            <Typography.Paragraph type="secondary">
              Ingresa con tu nombre de usuario y contrasena interna.
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
                label="Contrasena"
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

