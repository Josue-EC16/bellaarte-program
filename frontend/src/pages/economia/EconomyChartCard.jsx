import { Card, Empty, Typography } from 'antd'

// eslint-disable-next-line react/prop-types
export function EconomyChartCard({ title, subtitle, children, empty }) {
  return (
    <Card
      bodyStyle={{ padding: 20 }}
      style={{
        borderRadius: 28,
        border: '1px solid rgba(143, 61, 46, 0.12)',
        background: 'linear-gradient(180deg, rgba(255,255,255,0.96), rgba(255,247,241,0.86))',
        boxShadow: '0 28px 70px rgba(77, 34, 25, 0.08)',
        height: '100%',
      }}
    >
      <Typography.Title level={4} style={{ marginTop: 0, marginBottom: 4 }}>
        {title}
      </Typography.Title>
      {subtitle ? (
        <Typography.Paragraph type="secondary" style={{ marginTop: 0 }}>
          {subtitle}
        </Typography.Paragraph>
      ) : null}
      {empty ? (
        <div style={{ minHeight: 280, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
          <Empty description="NO HAY DATOS PARA MOSTRAR." />
        </div>
      ) : (
        children
      )}
    </Card>
  )
}
