import {
  DashboardOutlined,
  LockOutlined,
  LogoutOutlined,
  TeamOutlined,
  UserOutlined,
} from '@ant-design/icons'
import { Avatar, Button, Dropdown, Layout, Menu, Space, Tag, Typography } from 'antd'
import { useMemo } from 'react'
import { Link, Outlet, useLocation, useNavigate } from 'react-router-dom'

import { useAuth } from '../auth/AuthProvider'

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

    if (user?.permissions?.includes('users:list')) {
      baseItems.push({
        key: '/app/usuarios',
        icon: <TeamOutlined />,
        label: <Link to="/app/usuarios">Usuarios</Link>,
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
    <Layout className="app-shell">
      <Sider
        breakpoint="lg"
        collapsedWidth="0"
        width={260}
        style={{ background: 'rgba(77, 34, 25, 0.96)', paddingTop: 12 }}
      >
        <div style={{ padding: '16px 20px 24px' }}>
          <Typography.Title level={3} style={{ color: '#fff7f1', margin: 0 }}>
            BellaArte
          </Typography.Title>
          <Typography.Text style={{ color: 'rgba(255,247,241,0.7)' }}>
            Sistema interno
          </Typography.Text>
        </div>

        <Menu
          theme="dark"
          mode="inline"
          selectedKeys={[location.pathname]}
          items={items}
          style={{ background: 'transparent' }}
        />
      </Sider>

      <Layout style={{ background: 'transparent' }}>
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
              {location.pathname === '/app/usuarios' ? 'Gestion de usuarios' : 'Panel principal'}
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

        <Content className="page-wrapper">
          <Outlet />
        </Content>
      </Layout>
    </Layout>
  )
}

