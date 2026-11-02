import { LockOutlined, UserOutlined } from '@ant-design/icons'
import { App as AntdApp, Button, Card, Form, Input, Typography } from 'antd'
import { useLocation, useNavigate } from 'react-router-dom'

import { useAuth } from '../../auth/AuthProvider'
import { FORM_COMMON_PROPS, FORM_SUBMIT_PROPS } from '../../components/forms/formConfig'

export function LoginPage() {
  const [form] = Form.useForm()
  const navigate = useNavigate()
  const location = useLocation()
  const { login, loading } = useAuth()
  const { message } = AntdApp.useApp()

  const handleSubmit = async (values) => {
    try {
      const session = await login(values)
      message.success(`Bienvenida(o), ${session.user.full_name}.`)
      const nextPath = session.user.must_change_password
        ? '/app/cambiar-clave'
        : location.state?.from?.pathname || '/app'
      navigate(nextPath, { replace: true })
    } catch (requestError) {
      message.error(requestError.response?.data?.detail || 'No fue posible iniciar sesión. Credenciales inválidas.')
    }
  }

  return (
    <main className="auth-page">
      <Card className="auth-card glass-panel" styles={{ body: { padding: 0 } }}>
        <div className="auth-grid">
          <section className="auth-brand">
            <img
              src="/logo_bellaarte1.png"
              alt="Logo BellaArte"
              style={{
                marginTop: 10,
                maxWidth: '420px',
                height: 'auto',
                display: 'block',
                marginLeft: 'auto',
                marginRight: 'auto',
              }}
            />
          </section>

          <section className="auth-form-panel">
            <Typography.Title level={2}>INICIAR SESIÓN</Typography.Title>
            <Typography.Paragraph type="secondary">
              Ingresa con tu nombre de usuario y tu contraseña interna para acceder al sistema.
            </Typography.Paragraph>

            <Form {...FORM_COMMON_PROPS} form={form} onFinish={handleSubmit} size="large">
              <Form.Item
                label="Usuario"
                name="username"
                extra="Usa el nombre de usuario que te asignó administración."
                rules={[{ required: true, message: 'Debe ingresar tu nombre de usuario.' }]}
              >
                <Input
                  prefix={<UserOutlined />}
                  placeholder="Ej. ADMIN o MARIA.PEREZ"
                  autoComplete="username"
                />
              </Form.Item>

              <Form.Item
                label="Contraseña"
                name="password"
                extra="Respeta mayúsculas, minúsculas y caracteres especiales."
                rules={[{ required: true, message: 'Debe ingresar tu contraseña.' }]}
              >
                <Input.Password
                  prefix={<LockOutlined />}
                  placeholder="Ingresa tu contraseña"
                  autoComplete="current-password"
                />
              </Form.Item>

              <Button {...FORM_SUBMIT_PROPS} block loading={loading}>
                Entrar al sistema
              </Button>
            </Form>
          </section>
        </div>
      </Card>
    </main>
  )
}
