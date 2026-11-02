/* eslint-disable react/prop-types */
import { Card, Statistic, Typography } from 'antd'

export function ReportKpiCard({ title, value, suffix, accent = '#8f3d2e', helper }) {
  return (
    <Card
      className="glass-panel report-kpi-card"
      styles={{ body: { padding: 20 } }}
    >
      <Typography.Text className="report-kpi-eyebrow" style={{ color: accent }}>
        {title}
      </Typography.Text>
      <Statistic value={value} suffix={suffix} valueStyle={{ color: '#2f1d18', fontWeight: 700 }} />
      {helper ? (
        <Typography.Text type="secondary" style={{ display: 'block', marginTop: 8 }}>
          {helper}
        </Typography.Text>
      ) : null}
    </Card>
  )
}
