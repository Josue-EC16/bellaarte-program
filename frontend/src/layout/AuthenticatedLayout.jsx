import {
  AppstoreOutlined,
  IdcardOutlined,
  DatabaseOutlined,
  DashboardOutlined,
  LockOutlined,
  LogoutOutlined,
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

    if (user?.permissions?.includes('clients:update')) {
      baseItems.push({
        key: '/app/clientes',
        icon: <IdcardOutlined />,
        label: <Link to="/app/clientes">Clientes</Link>,
      })
    }

    if (
      user?.permissions?.includes('boutique_types:list') ||
      user?.permissions?.includes('boutique_items:list')
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
          user?.permissions?.includes('boutique_items:list')
            ? {
                key: '/app/boutique/inventario',
                icon: <AppstoreOutlined />,
                label: <Link to="/app/boutique/inventario">Inventario Boutique</Link>,
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
      <div style={{ position: 'relative', padding: '16px 20px 24px', 
                    display: 'flex', alignItems: 'center', overflow: 'hidden', minHeight: 100}}>
         <div style={{ position: 'absolute', top: 0, left: 0, width: 125, overflow: 'hidden'}}>
          <img
           src="/logo_bellaarte2.png"
           alt="BellaArte"
           style={{ width: '100%', height: '100%', objectFit: 'contain', display: 'block' }}
          />
         </div>
         <div style={{ marginLeft: 95, lineHeight: 1.1 }}>
          <Typography.Title level={3} style={{ color: '#fff7f1', margin: 0 }}>
           BELLAARTE BOUTIQUE
          </Typography.Title>
          <Typography.Text style={{ color: 'rgba(255,247,241,0.7)' }}>
           Sistema interno
          </Typography.Text>
         </div>
       </div>

        <Menu
          theme="dark"
          mode="inline"
          selectedKeys={[location.pathname]}
          defaultOpenKeys={['seguridad', 'boutique']}
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
  if (pathname === '/app/boutique/inventario') return 'Inventario Boutique'
  if (pathname === '/app/boutique/ventas') return 'Ventas Boutique'
  if (pathname === '/app/cambiar-clave') return 'Cambiar contrasena'
  return 'Panel principal'
}
