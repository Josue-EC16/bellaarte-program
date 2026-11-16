/* eslint-disable react/prop-types */
import { Flex, Spin, Typography } from 'antd'

export function FullScreenLoader({ title = 'Cargando sesion...' }) {
  return (
    <Flex
      vertical
      align="center"
      justify="center"
      gap={16}
      style={{ minHeight: '100vh', background: 'var(--app-bg)' }}
    >
      <Spin size="large" />
      <Typography.Text type="secondary">{title}</Typography.Text>
    </Flex>
  )
}
