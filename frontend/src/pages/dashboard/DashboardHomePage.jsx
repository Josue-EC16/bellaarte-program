import {
  AppstoreOutlined,
  ArrowRightOutlined,
  DollarOutlined,
  SkinOutlined,
  IdcardOutlined,
  LockOutlined,
  ScissorOutlined,
  ShoppingCartOutlined,
  TeamOutlined,
} from '@ant-design/icons'
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
  const quickLinks = [
    user?.permissions?.includes('users:list')
      ? {
          key: 'users',
          to: '/app/seguridad/usuarios',
          label: 'Gestionar Usuarios',
          icon: <TeamOutlined />,
        }
      : null,
    user?.permissions?.includes('clients:list')
      ? {
          key: 'clients',
          to: '/app/clientes',
          label: 'Ir a Clientes',
          icon: <IdcardOutlined />,
        }
      : null,
    user?.permissions?.includes('boutique_items:list')
      ? {
          key: 'inventory',
          to: '/app/boutique/inventario',
          label: 'Inventario Boutique',
          icon: <AppstoreOutlined />,
        }
      : null,
    user?.permissions?.includes('boutique_entries:list')
      ? {
          key: 'boutique-entries',
          to: '/app/boutique/entradas',
          label: 'Entradas Boutique',
          icon: <AppstoreOutlined />,
        }
      : null,
    user?.permissions?.includes('boutique_sales:list')
      ? {
          key: 'sales',
          to: '/app/boutique/ventas',
          label: 'Ir a Ventas Boutique',
          icon: <ShoppingCartOutlined />,
        }
      : null,
    user?.permissions?.includes('fletes:list')
      ? {
          key: 'fletes',
          to: '/app/fletes',
          label: 'Vestidos en Flete',
          icon: <SkinOutlined />,
        }
      : null,
    user?.permissions?.includes('flete_outputs:list')
      ? {
          key: 'flete-outputs',
          to: '/app/fletes/salidas',
          label: 'Salidas de Flete',
          icon: <ShoppingCartOutlined />,
        }
      : null,
    user?.permissions?.includes('workshop_inventory:list')
      ? {
          key: 'workshop-inventory',
          to: '/app/taller/inventario',
          label: 'Inventario Taller',
          icon: <ScissorOutlined />,
        }
      : null,
    user?.permissions?.includes('workshop_outputs:list')
      ? {
          key: 'workshop-outputs',
          to: '/app/taller/salidas',
          label: 'Salidas Taller',
          icon: <ScissorOutlined />,
        }
      : null,
    user?.permissions?.includes('currencies:list')
      ? {
          key: 'currencies',
          to: '/app/monedas',
          label: 'Catalogo de Monedas',
          icon: <DollarOutlined />,
        }
      : null,
  ].filter(Boolean)

  return (
    <div className="dashboard-grid">
      <section className="dashboard-hero">
        <Typography.Text style={{ color: 'rgba(255,250,246,0.74)' }}>Resumen del día</Typography.Text>
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
        <Card className="glass-panel" variant="borderless" style={{ borderRadius: 24 }}>
          <Space direction="vertical" size={8}>
            <Typography.Title level={4} style={{ margin: 0 }}>
              Seguridad de cuenta
            </Typography.Title>
            <Typography.Paragraph type="secondary">
              Mantiene tu acceso protegido y al día.
            </Typography.Paragraph>
            <Button icon={<LockOutlined />} type="primary">
              <Link to="/app/cambiar-clave">Cambiar clave</Link>
            </Button>
          </Space>
        </Card>

        <Card className="glass-panel" variant="borderless" style={{ borderRadius: 24 }}>
          <Space direction="vertical" size={8}>
            <Typography.Title level={4} style={{ margin: 0 }}>
              Estado del perfil
            </Typography.Title>
            <Typography.Paragraph type="secondary">
              Tus permisos actuales habilitan el acceso a los módulos iniciales definidos para tu rol.
            </Typography.Paragraph>
            <Tag color="volcano">{user?.role_name}</Tag>
          </Space>
        </Card>

        <Card className="glass-panel" variant="borderless" style={{ borderRadius: 24 }}>
          <Space direction="vertical" size={8}>
            <Typography.Title level={4} style={{ margin: 0 }}>
              Accesos rápidos
            </Typography.Title>
            <Typography.Paragraph type="secondary">
              El home ya refleja los módulos operativos habilitados para tu rol actual.
            </Typography.Paragraph>
            {quickLinks.map((link) => (
              <Button key={link.key} icon={link.icon} type="default">
                <Link to={link.to}>{link.label}</Link>
              </Button>
            ))}
            {quickLinks.length === 0 ? (
              <Typography.Text type="secondary">
                Tu rol no tiene accesos operativos directos adicionales en esta etapa.
              </Typography.Text>
            ) : null}
          </Space>
        </Card>
      </div>

      <Row gutter={[16, 16]}>
        <Col xs={24} md={12}>
          <Card className="glass-panel" variant="borderless" style={{ borderRadius: 24, height: '100%' }}>
            <Typography.Title level={4}>Siguiente paso funcional</Typography.Title>
            <Typography.Paragraph type="secondary">
              El sistema ya soporta seguridad, clientes, proveedores, inventario boutique, ventas, fletes y operación inicial del taller.
            </Typography.Paragraph>
            <Button type="link" icon={<ArrowRightOutlined />} style={{ paddingInline: 0 }}>
              Base lista para crecer hacia pedidos, pagos y finanzas
            </Button>
          </Card>
        </Col>
        <Col xs={24} md={12}>
          <Card className="glass-panel" variant="borderless" style={{ borderRadius: 24, height: '100%' }}>
            <Typography.Title level={4}>Vista operativa</Typography.Title>
            <Typography.Paragraph type="secondary">
              Esta pantalla esta pensada como home operativo: identidad, accesos rápidos y contexto de sesión, sin KPI financieros complejos todavía.
            </Typography.Paragraph>
          </Card>
        </Col>
      </Row>
    </div>
  )
}
