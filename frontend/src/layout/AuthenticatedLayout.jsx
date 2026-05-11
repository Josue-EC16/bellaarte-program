import {
  AppstoreOutlined,
  IdcardOutlined,
  DatabaseOutlined,
  DashboardOutlined,
  DollarOutlined,
  LockOutlined,
  LogoutOutlined,
  ScissorOutlined,
  ShoppingCartOutlined,
  SafetyOutlined,
  TeamOutlined,
  UserOutlined,
} from '@ant-design/icons'
import { Avatar, Button, Dropdown, Layout, Menu, Space, Tag, Typography } from 'antd'
import { useMemo } from 'react'
import { Link, Outlet, useLocation, useNavigate } from 'react-router-dom'

import { useAuth } from '../auth/AuthProvider'
import { FooterBar } from '../components/FooterBar'

const { Header, Content, Sider } = Layout

export function AuthenticatedLayout() {
  const location = useLocation()
  const navigate = useNavigate()
  const { logout, user } = useAuth()

  const items = useMemo(() => {
    const baseItems = [
      {
        key: '/app',
        icon: <DashboardOutlined />,
        label: <Link to="/app">Inicio</Link>,
      },
    ]

    if (user?.permissions?.includes('roles:list') || user?.permissions?.includes('users:list')) {
      baseItems.push({
        key: 'seguridad',
        icon: <SafetyOutlined />,
        label: 'Seguridad',
        children: [
          user?.permissions?.includes('roles:list')
            ? {
                key: '/app/seguridad/roles',
                icon: <SafetyOutlined />,
                label: <Link to="/app/seguridad/roles">Roles</Link>,
              }
            : null,
          user?.permissions?.includes('users:list')
            ? {
                key: '/app/seguridad/usuarios',
                icon: <TeamOutlined />,
                label: <Link to="/app/seguridad/usuarios">Usuarios</Link>,
              }
            : null,
        ].filter(Boolean),
      })
    }

    if (user?.permissions?.includes('clients:list')) {
      baseItems.push({
        key: '/app/clientes',
        icon: <IdcardOutlined />,
        label: <Link to="/app/clientes">Clientes</Link>,
      })
    }

    if (
      user?.permissions?.includes('boutique_types:list') ||
      user?.permissions?.includes('boutique_providers:list') ||
      user?.permissions?.includes('boutique_items:list') ||
      user?.permissions?.includes('boutique_entries:list') ||
      user?.permissions?.includes('boutique_sales:list')
    ) {
      baseItems.push({
        key: 'boutique',
        icon: <AppstoreOutlined />,
        label: 'Boutique',
        children: [
          user?.permissions?.includes('boutique_types:list')
            ? {
                key: '/app/boutique/tipos',
                icon: <DatabaseOutlined />,
                label: <Link to="/app/boutique/tipos">Categorías Productos</Link>,
              }
            : null,
          user?.permissions?.includes('boutique_providers:list')
            ? {
                key: '/app/boutique/proveedores',
                icon: <TeamOutlined />,
                label: <Link to="/app/boutique/proveedores">Proveedores</Link>,
              }
            : null,
          user?.permissions?.includes('boutique_items:list')
            ? {
                key: '/app/boutique/inventario',
                icon: <AppstoreOutlined />,
                label: <Link to="/app/boutique/inventario">Inventario Boutique</Link>,
              }
            : null,
          user?.permissions?.includes('boutique_entries:list')
            ? {
                key: '/app/boutique/entradas',
                icon: <DatabaseOutlined />,
                label: <Link to="/app/boutique/entradas">Entradas Boutique</Link>,
              }
            : null,
          user?.permissions?.includes('boutique_sales:list')
            ? {
                key: '/app/boutique/ventas',
                icon: <ShoppingCartOutlined />,
                label: <Link to="/app/boutique/ventas">Ventas Boutique</Link>,
              }
            : null,
        ].filter(Boolean),
      })
    }

    if (
      user?.permissions?.includes('workshop_types:list') ||
      user?.permissions?.includes('workshop_inventory:list') ||
      user?.permissions?.includes('workshop_entries:list') ||
      user?.permissions?.includes('workshop_outputs:list')
    ) {
      baseItems.push({
        key: 'taller',
        icon: <ScissorOutlined />,
        label: 'Taller',
        children: [
          user?.permissions?.includes('workshop_types:list')
            ? {
                key: '/app/taller/tipos',
                icon: <DatabaseOutlined />,
                label: <Link to="/app/taller/tipos">Tipos Taller</Link>,
              }
            : null,
          user?.permissions?.includes('workshop_inventory:list')
            ? {
                key: '/app/taller/inventario',
                icon: <AppstoreOutlined />,
                label: <Link to="/app/taller/inventario">Inventario Taller</Link>,
              }
            : null,
          user?.permissions?.includes('workshop_entries:list')
            ? {
                key: '/app/taller/entradas',
                icon: <DatabaseOutlined />,
                label: <Link to="/app/taller/entradas">Entradas Taller</Link>,
              }
            : null,
          user?.permissions?.includes('workshop_outputs:list')
            ? {
                key: '/app/taller/salidas',
                icon: <ScissorOutlined />,
                label: <Link to="/app/taller/salidas">Salidas Taller</Link>,
              }
            : null,
        ].filter(Boolean),
      })
    }

    if (
      user?.permissions?.includes('currencies:list') ||
      user?.permissions?.includes('exchange_rates:list')
    ) {
      baseItems.push({
        key: 'monedas',
        icon: <DollarOutlined />,
        label: 'Monedas',
        children: [
          user?.permissions?.includes('currencies:list')
            ? {
                key: '/app/monedas',
                icon: <DollarOutlined />,
                label: <Link to="/app/monedas">Monedas</Link>,
              }
            : null,
          user?.permissions?.includes('exchange_rates:list')
            ? {
                key: '/app/monedas/tipos-cambio',
                icon: <DatabaseOutlined />,
                label: <Link to="/app/monedas/tipos-cambio">Tipos de Cambio</Link>,
              }
            : null,
        ].filter(Boolean),
      })
    }

    baseItems.push({
      key: '/app/cambiar-clave',
      icon: <LockOutlined />,
      label: <Link to="/app/cambiar-clave">Cambiar clave</Link>,
    })

    return baseItems
  }, [user])

  const dropdownItems = [
    {
      key: 'profile',
      label: (
        <Space direction="vertical" size={0}>
          <Typography.Text strong>{user?.full_name}</Typography.Text>
          <Typography.Text type="secondary">{user?.username}</Typography.Text>
        </Space>
      ),
      disabled: true,
    },
    {
      key: 'logout',
      icon: <LogoutOutlined />,
      label: 'Cerrar sesion',
      onClick: logout,
    },
  ]

  return (
    <Layout className="app-shell" style={{ height: '100vh', overflow: 'hidden' }}>
      <Sider
        breakpoint="lg"
        collapsedWidth="0"
        width={260}
        style={{ 
          background: 'rgba(77, 34, 25, 0.96)', 
          paddingTop: 12,
          height: '100vh',
          overflowY: 'auto'
        }}
      >
      <div style={{ padding: '16px 16px 24px', display: 'flex', alignItems: 'center', gap: 12 }}>
         <div style={{ width: 80, flexShrink: 0 }}>
          <img
           src="/logo_bellaarte2.png"
           alt="BellaArte"
           style={{ width: '100%', height: 'auto', display: 'block', objectFit: 'contain' }}
          />
         </div>
         <div style={{ lineHeight: 1.1 }}>
          <Typography.Title level={4} style={{ color: '#fff7f1', margin: 0, wordBreak: 'normal', fontSize: '1.2rem' }}>
           BELLAARTE BOUTIQUE
          </Typography.Title>
          <Typography.Text style={{ color: 'rgba(255,247,241,0.7)', fontSize: '0.85rem' }}>
           Sistema interno
          </Typography.Text>
         </div>
       </div>

        <Menu
          theme="dark"
          mode="inline"
          selectedKeys={[location.pathname]}
          defaultOpenKeys={['seguridad', 'boutique', 'taller', 'monedas']}
          items={items}
          style={{ background: 'transparent' }}
        />
      </Sider>

      <Layout style={{ background: 'transparent', height: '100vh', overflowY: 'auto', display: 'flex', flexDirection: 'column' }}>
        <Header
          style={{
            background: 'transparent',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            padding: '18px 24px 0',
            height: 'auto',
          }}
        >
          <Space direction="vertical" size={2}>
            <Typography.Text type="secondary">Panel operativo</Typography.Text>
            <Typography.Title level={4} style={{ margin: 0 }}>
              {pageTitle(location.pathname)}
            </Typography.Title>
          </Space>

          <Space size={16}>
            <Tag color="volcano">{user?.role_name}</Tag>
            <Dropdown menu={{ items: dropdownItems }} placement="bottomRight" trigger={['click']}>
              <Button
                type="text"
                style={{ height: 'auto', padding: 8 }}
                onClick={() => navigate('/app')}
              >
                <Space>
                  <Avatar icon={<UserOutlined />} style={{ backgroundColor: '#8f3d2e' }} />
                  <Space direction="vertical" size={0}>
                    <Typography.Text strong>{user?.full_name}</Typography.Text>
                    <Typography.Text type="secondary">{user?.username}</Typography.Text>
                  </Space>
                </Space>
              </Button>
            </Dropdown>
          </Space>
        </Header>

        <Content className="page-wrapper" style={{ flex: '1 0 auto' }}>
          <Outlet />
        </Content>
        <FooterBar />
      </Layout>
    </Layout>
  )
}

function pageTitle(pathname) {
  if (pathname === '/app/seguridad/roles') return 'Gestion de Roles'
  if (pathname === '/app/seguridad/usuarios') return 'Gestion de Usuarios'
  if (pathname === '/app/clientes') return 'Gestion de Clientes'
  if (pathname === '/app/boutique/tipos') return 'Categorías Productos'
  if (pathname === '/app/boutique/proveedores') return 'Proveedores Boutique'
  if (pathname === '/app/boutique/inventario') return 'Inventario Boutique'
  if (pathname === '/app/boutique/entradas') return 'Entradas Boutique'
  if (pathname === '/app/boutique/ventas') return 'Ventas Boutique'
  if (pathname === '/app/taller/tipos') return 'Tipos Inventario Taller'
  if (pathname === '/app/taller/inventario') return 'Inventario Taller'
  if (pathname === '/app/taller/entradas') return 'Entradas Taller'
  if (pathname === '/app/taller/salidas') return 'Salidas Taller'
  if (pathname === '/app/monedas') return 'Monedas'
  if (pathname === '/app/monedas/tipos-cambio') return 'Tipos de Cambio'
  if (pathname === '/app/cambiar-clave') return 'Cambiar contrasena'
  return 'Panel principal'
}
