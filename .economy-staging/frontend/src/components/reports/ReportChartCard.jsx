/* eslint-disable react/prop-types */
import { Card, Empty, Typography } from 'antd'

export function ReportChartCard({ title, description, empty, children }) {
  return (
    <Card
      className="glass-panel report-chart-card"
      styles={{ body: { padding: 20 } }}
      title={<span style={{ color: '#4d2219', fontWeight: 700 }}>{title}</span>}
      extra={description ? <Typography.Text type="secondary">{description}</Typography.Text> : null}
    >
      {empty ? <Empty description="SIN DATOS PARA ESTE FILTRO" image={Empty.PRESENTED_IMAGE_SIMPLE} /> : children}
    </Card>
  )
}
