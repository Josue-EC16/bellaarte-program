import { ArrowRightOutlined, LockOutlined, TeamOutlined } from '@ant-design/icons'
import { Button, Card, Col, Row, Space, Tag, Typography } from 'antd'
import { Link } from 'react-router-dom'

import { useAuth } from '../../auth/AuthProvider'

export function DashboardHomePage() {
  const { user } = useAuth()
  const today = new Intl.DateTimeFormat('es-BO', {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
  }).format(new Date())

  return (
    <div className="dashboard-grid">
      <section className="dashboard-hero">
        <Typography.Text style={{ color: 'rgba(255,250,246,0.74)' }}>Resumen del dia</Typography.Text>
        <Typography.Title level={2} style={{ color: '#fffaf6', marginTop: 8, marginBottom: 8 }}>
          Bienvenida(o), {user?.full_name}
        </Typography.Title>
        <Typography.Paragraph style={{ color: 'rgba(255,250,246,0.86)', maxWidth: 720 }}>
          Hoy es {today}. Tu perfil activo es <strong>{user?.role_name}</strong> y el sistema ya esta listo para operar.
        </Typography.Paragraph>
        <Space wrap>
          <Tag color="gold-inverse">{user?.role_code}</Tag>
          {user?.must_change_password ? <Tag color="red-inverse">Cambio de clave pendiente</Tag> : null}
        </Space>
      </section>

      <div className="dashboard-actions">
        <Card className="glass-panel" bordered={false} style={{ borderRadius: 24 }}>
          <Space direction="vertical" size={8}>
            <Typography.Title level={4} style={{ margin: 0 }}>
              Seguridad de cuenta
            </Typography.Title>
            <Typography.Paragraph type="secondary">
              Mantiene tu acceso protegido y al dia.
            </Typography.Paragraph>
            <Button icon={<LockOutlined />} type="primary">
              <Link to="/app/cambiar-clave">Cambiar contrasena</Link>
            </Button>
          </Space>
        </Card>

        <Card className="glass-panel" bordered={false} style={{ borderRadius: 24 }}>
          <Space direction="vertical" size={8}>
            <Typography.Title level={4} style={{ margin: 0 }}>
              Estado del perfil
            </Typography.Title>
            <Typography.Paragraph type="secondary">
              Tus permisos actuales habilitan el acceso a los modulos iniciales definidos para tu rol.
            </Typography.Paragraph>
            <Tag color="volcano">{user?.role_name}</Tag>
          </Space>
        </Card>

        <Card className="glass-panel" bordered={false} style={{ borderRadius: 24 }}>
          <Space direction="vertical" size={8}>
            <Typography.Title level={4} style={{ margin: 0 }}>
              Accesos rapidos
            </Typography.Title>
            <Typography.Paragraph type="secondary">
              En esta primera fase tienes disponible el modulo base de seguridad y la navegacion principal.
            </Typography.Paragraph>
            {user?.permissions?.includes('users:list') ? (
              <Button icon={<TeamOutlined />} type="default">
                <Link to="/app/usuarios">Gestionar usuarios</Link>
              </Button>
            ) : (
              <Typography.Text type="secondary">Tu rol no administra usuarios en esta etapa.</Typography.Text>
            )}
          </Space>
        </Card>
      </div>

      <Row gutter={[16, 16]}>
        <Col xs={24} md={12}>
          <Card className="glass-panel" bordered={false} style={{ borderRadius: 24, height: '100%' }}>
            <Typography.Title level={4}>Siguiente paso funcional</Typography.Title>
            <Typography.Paragraph type="secondary">
              El sistema ya soporta autenticacion, cambio obligatorio de clave, control de roles y alta interna de usuarios.
            </Typography.Paragraph>
            <Button type="link" icon={<ArrowRightOutlined />} style={{ paddingInline: 0 }}>
              Modulo listo para crecer a inventarios, pedidos y finanzas
            </Button>
          </Card>
        </Col>
        <Col xs={24} md={12}>
          <Card className="glass-panel" bordered={false} style={{ borderRadius: 24, height: '100%' }}>
            <Typography.Title level={4}>Vista operativa</Typography.Title>
            <Typography.Paragraph type="secondary">
              Esta pantalla esta pensada como home operativo: identidad, accesos rapidos y contexto de sesion, sin KPI financieros complejos todavia.
            </Typography.Paragraph>
          </Card>
        </Col>
      </Row>
    </div>
  )
}
