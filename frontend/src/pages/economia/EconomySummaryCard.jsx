import { Card, Typography } from 'antd'

// eslint-disable-next-line react/prop-types
export function EconomySummaryCard({ eyebrow, title, value, accent, helper }) {
  return (
    <Card
      bodyStyle={{ padding: 18 }}
      style={{
        borderRadius: 24,
        border: `1px solid ${accent}2b`,
        background: `linear-gradient(145deg, ${accent}15, rgba(255,255,255,0.9))`,
        boxShadow: '0 22px 56px rgba(77, 34, 25, 0.08)',
        overflow: 'hidden',
      }}
    >
      <Typography.Text
        style={{
          display: 'block',
          fontSize: 12,
          letterSpacing: '0.08em',
          color: '#7c6a61',
        }}
      >
        {eyebrow}
      </Typography.Text>
      <Typography.Title level={4} style={{ margin: '8px 0 2px', color: accent }}>
        {value}
      </Typography.Title>
      <Typography.Text strong>{title}</Typography.Text>
      {helper ? (
        <Typography.Paragraph type="secondary" style={{ margin: '8px 0 0' }}>
          {helper}
        </Typography.Paragraph>
      ) : null}
    </Card>
  )
}
