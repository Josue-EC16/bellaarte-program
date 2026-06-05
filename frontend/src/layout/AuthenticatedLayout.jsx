import {
  AppstoreOutlined,
  BellOutlined,
  CheckOutlined,
  IdcardOutlined,
  CalendarOutlined,
  DatabaseOutlined,
  DashboardOutlined,
  DollarOutlined,
  EyeOutlined,
  FileTextOutlined,
  LinkOutlined,
  SkinOutlined,
  LockOutlined,
  LogoutOutlined,
  ScissorOutlined,
  ShoppingCartOutlined,
  SafetyOutlined,
  TeamOutlined,
  UserOutlined,
} from '@ant-design/icons'
import { Avatar, Badge, Button, Dropdown, Layout, Menu, Popover, Space, Tag, Typography } from 'antd'
import { useCallback, useEffect, useMemo, useState } from 'react'
import { Link, Outlet, useLocation, useNavigate } from 'react-router-dom'

import { apiClient } from '../api/client'
import { useAuth } from '../auth/AuthProvider'
import { FooterBar } from '../components/FooterBar'
import {
  buildNotificationOriginPath,
  notificationPriorityColor,
  notificationPriorityLabel,
  notificationPrioritySurface,
} from '../pages/notificaciones/notificationUtils'

const { Header, Content, Sider } = Layout

export function AuthenticatedLayout() {
  const location = useLocation()
  const navigate = useNavigate()
  const { logout, user } = useAuth()
  const [notificationSummary, setNotificationSummary] = useState({
    unread_count: 0,
    unresolved_count: 0,
    urgent_count: 0,
    latest: [],
  })
  const [notificationsOpen, setNotificationsOpen] = useState(false)
  const canUseNotifications = user?.permissions?.includes('notifications:list')

  const loadNotificationSummary = useCallback(async () => {
    if (!canUseNotifications) return
    try {
      const response = await apiClient.get('/notificaciones/resumen')
      setNotificationSummary(response.data)
    } catch {
      setNotificationSummary((current) => ({ ...current, latest: current.latest || [] }))
    }
  }, [canUseNotifications])

  useEffect(() => {
    if (!canUseNotifications) return undefined
    loadNotificationSummary()
    const intervalId = window.setInterval(loadNotificationSummary, 60000)
    const handleFocus = () => {
      loadNotificationSummary()
    }
    window.addEventListener('focus', handleFocus)
    return () => {
      window.clearInterval(intervalId)
      window.removeEventListener('focus', handleFocus)
    }
  }, [canUseNotifications, loadNotificationSummary])

  const markNotificationAsRead = useCallback(async (notificationId) => {
    try {
      await apiClient.patch(`/notificaciones/${notificationId}/read`)
      await loadNotificationSummary()
    } catch {
      return
    }
  }, [loadNotificationSummary])

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
      user?.permissions?.includes('fletes:list') ||
      user?.permissions?.includes('flete_outputs:list')
    ) {
      baseItems.push({
        key: 'fletes',
        icon: <SkinOutlined />,
        label: 'Fletes',
        children: [
          user?.permissions?.includes('fletes:list')
            ? {
                key: '/app/fletes',
                icon: <SkinOutlined />,
                label: <Link to="/app/fletes">Vestidos en Flete</Link>,
              }
            : null,
          user?.permissions?.includes('flete_outputs:list')
            ? {
                key: '/app/fletes/salidas',
                icon: <ShoppingCartOutlined />,
                label: <Link to="/app/fletes/salidas">Salidas de Flete</Link>,
              }
            : null,
        ].filter(Boolean),
      })
    }

    if (user?.permissions?.includes('notifications:list')) {
      baseItems.push({
        key: '/app/notificaciones',
        icon: <BellOutlined />,
        label: <Link to="/app/notificaciones">Notificaciones</Link>,
      })
    }

    if (user?.permissions?.includes('audit:list')) {
      baseItems.push({
        key: '/app/auditoria',
        icon: <SafetyOutlined />,
        label: <Link to="/app/auditoria">Auditoría del Sistema</Link>,
      })
    }

    if (
      user?.permissions?.includes('receipts:list') ||
      user?.permissions?.includes('receipt_types:list')
    ) {
      baseItems.push({
        key: 'comprobantes',
        icon: <FileTextOutlined />,
        label: 'Comprobantes Internos',
        children: [
          user?.permissions?.includes('receipts:list')
            ? {
                key: '/app/comprobantes',
                icon: <FileTextOutlined />,
                label: <Link to="/app/comprobantes">Historial</Link>,
              }
            : null,
          user?.permissions?.includes('receipt_types:list')
            ? {
                key: '/app/comprobantes/tipos',
                icon: <DatabaseOutlined />,
                label: <Link to="/app/comprobantes/tipos">Tipos de Comprobante</Link>,
              }
            : null,
        ].filter(Boolean),
      })
    }

    if (
      user?.permissions?.includes('economy_income:view') ||
      user?.permissions?.includes('economy_expenses:list') ||
      user?.permissions?.includes('cash_cuts:view_own') ||
      user?.permissions?.includes('economy_reports:view')
    ) {
      baseItems.push({
        key: 'economia',
        icon: <DollarOutlined />,
        label: 'Economía',
        children: [
          user?.permissions?.includes('economy_income:view')
            ? {
                key: '/app/economia',
                icon: <DashboardOutlined />,
                label: <Link to="/app/economia">Resumen</Link>,
              }
            : null,
          user?.permissions?.includes('economy_expenses:list')
            ? {
                key: '/app/economia/egresos',
                icon: <DollarOutlined />,
                label: <Link to="/app/economia/egresos">Egresos</Link>,
              }
            : null,
          user?.permissions?.includes('cash_cuts:view_own')
            ? {
                key: '/app/economia/cortes-caja',
                icon: <DatabaseOutlined />,
                label: <Link to="/app/economia/cortes-caja">Cortes de Caja</Link>,
              }
            : null,
          user?.permissions?.includes('economy_reports:view')
            ? {
                key: '/app/economia/reportes',
                icon: <AppstoreOutlined />,
                label: <Link to="/app/economia/reportes">Reportes</Link>,
              }
            : null,
        ].filter(Boolean),
      })
    }

    if (
      user?.permissions?.includes('orders:list') ||
      user?.permissions?.includes('order_payments:list') ||
      user?.permissions?.includes('order_tests:list') ||
      user?.permissions?.includes('order_reports:view')
    ) {
      baseItems.push({
        key: 'pedidos',
        icon: <CalendarOutlined />,
        label: 'Pedidos',
        children: [
          user?.permissions?.includes('orders:list')
            ? {
                key: '/app/pedidos',
                icon: <DatabaseOutlined />,
                label: <Link to="/app/pedidos">Pedidos</Link>,
              }
            : null,
          user?.permissions?.includes('order_payments:list')
            ? {
                key: '/app/pedidos/pagos',
                icon: <DollarOutlined />,
                label: <Link to="/app/pedidos/pagos">Pagos</Link>,
              }
            : null,
          user?.permissions?.includes('order_tests:list')
            ? {
                key: '/app/pedidos/pruebas',
                icon: <CalendarOutlined />,
                label: <Link to="/app/pedidos/pruebas">Pruebas</Link>,
              }
            : null,
          user?.permissions?.includes('order_reports:view')
            ? {
                key: '/app/pedidos/reportes',
                icon: <AppstoreOutlined />,
                label: <Link to="/app/pedidos/reportes">Reportes</Link>,
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

  const notificationPopoverContent = canUseNotifications ? (
    <div style={{ width: 360 }}>
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'flex-start',
          marginBottom: 14,
        }}
      >
        <div>
          <Typography.Title level={5} style={{ margin: 0 }}>
            NOTIFICACIONES
          </Typography.Title>
          <Typography.Text type="secondary">
            {notificationSummary.unread_count} NO LEÍDAS · {notificationSummary.unresolved_count} PENDIENTES
          </Typography.Text>
        </div>
        <Button type="link" onClick={() => navigate('/app/notificaciones')}>
          VER TODAS
        </Button>
      </div>

      <div style={{ display: 'grid', gap: 10 }}>
        {notificationSummary.latest?.length ? notificationSummary.latest.map((notification) => (
          <div
            key={notification.id}
            style={{
              borderRadius: 18,
              padding: 14,
              background: notificationPrioritySurface(notification.prioridad),
              border: `1px solid ${notificationPriorityColor(notification.prioridad)}33`,
            }}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', gap: 12 }}>
              <div style={{ minWidth: 0 }}>
                <Tag
                  style={{
                    borderRadius: 999,
                    marginBottom: 8,
                    color: notificationPriorityColor(notification.prioridad),
                    borderColor: `${notificationPriorityColor(notification.prioridad)}44`,
                    background: 'rgba(255,255,255,0.55)',
                  }}
                >
                  {notificationPriorityLabel(notification.prioridad)}
                </Tag>
                <Typography.Text strong style={{ display: 'block' }}>
                  {notification.titulo}
                </Typography.Text>
                <Typography.Text type="secondary" style={{ display: 'block' }}>
                  {notification.mensaje}
                </Typography.Text>
                <Typography.Text type="secondary" style={{ fontSize: 12 }}>
                  {new Date(notification.fecha).toLocaleString('es-BO')}
                </Typography.Text>
              </div>
            </div>
            <Space style={{ marginTop: 10 }} wrap>
              <Button
                size="small"
                icon={<EyeOutlined />}
                onClick={() => {
                  setNotificationsOpen(false)
                  navigate(`/app/notificaciones?notification_id=${notification.id}`)
                }}
              >
                VER
              </Button>
              {!notification.leida ? (
                <Button size="small" icon={<CheckOutlined />} onClick={() => markNotificationAsRead(notification.id)}>
                  LEÍDA
                </Button>
              ) : null}
              <Button
                size="small"
                icon={<LinkOutlined />}
                onClick={() => {
                  setNotificationsOpen(false)
                  navigate(buildNotificationOriginPath(notification))
                }}
              >
                ORIGEN
              </Button>
            </Space>
          </div>
        )) : (
          <Typography.Text type="secondary">NO TIENES NOTIFICACIONES RECIENTES.</Typography.Text>
        )}
      </div>
    </div>
  ) : null

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
          defaultOpenKeys={['seguridad', 'boutique', 'fletes', 'comprobantes', 'economia', 'pedidos', 'taller', 'monedas']}
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
            {canUseNotifications ? (
              <Popover
                trigger="click"
                placement="bottomRight"
                open={notificationsOpen}
                onOpenChange={(open) => {
                  setNotificationsOpen(open)
                  if (open) {
                    loadNotificationSummary()
                  }
                }}
                content={notificationPopoverContent}
              >
                <Badge count={notificationSummary.unread_count} size="small" offset={[-6, 4]}>
                  <Button
                    type="text"
                    aria-label="Abrir notificaciones"
                    style={{
                      width: 46,
                      height: 46,
                      borderRadius: 18,
                      background: notificationSummary.urgent_count
                        ? 'linear-gradient(135deg, rgba(184,71,92,0.18), rgba(255,255,255,0.72))'
                        : 'rgba(255,255,255,0.72)',
                      border: '1px solid rgba(143, 61, 46, 0.12)',
                    }}
                    icon={<BellOutlined style={{ fontSize: 18, color: '#8f3d2e' }} />}
                  />
                </Badge>
              </Popover>
            ) : null}
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
  if (pathname === '/app/fletes') return 'Vestidos en Flete'
  if (pathname === '/app/fletes/salidas') return 'Salidas de Flete'
  if (pathname === '/app/notificaciones') return 'Notificaciones'
  if (pathname === '/app/auditoria') return 'Auditoría del Sistema'
  if (pathname === '/app/comprobantes') return 'Comprobantes Internos'
  if (pathname === '/app/comprobantes/tipos') return 'Tipos de Comprobante'
  if (pathname === '/app/economia') return 'Economía'
  if (pathname === '/app/economia/egresos') return 'Egresos'
  if (pathname === '/app/economia/cortes-caja') return 'Cortes de Caja'
  if (pathname === '/app/economia/reportes') return 'Reportes Económicos'
  if (pathname === '/app/pedidos') return 'Pedidos'
  if (pathname === '/app/pedidos/pagos') return 'Pagos de Pedidos'
  if (pathname === '/app/pedidos/pruebas') return 'Pruebas de Pedidos'
  if (pathname === '/app/pedidos/reportes') return 'Reportes de Pedidos'
  if (pathname === '/app/taller/tipos') return 'Tipos Inventario Taller'
  if (pathname === '/app/taller/inventario') return 'Inventario Taller'
  if (pathname === '/app/taller/entradas') return 'Entradas Taller'
  if (pathname === '/app/taller/salidas') return 'Salidas Taller'
  if (pathname === '/app/monedas') return 'Monedas'
  if (pathname === '/app/monedas/tipos-cambio') return 'Tipos de Cambio'
  if (pathname === '/app/cambiar-clave') return 'Cambiar contrasena'
  return 'Panel principal'
}
