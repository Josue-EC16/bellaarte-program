/* eslint-disable react/prop-types */
import { Space, Tag, Typography } from 'antd'

export function ReportLegendNumeric({ items = [], colorKey = 'color', valueFormatter = (value) => value }) {
  if (!items.length) {
    return (
      <Typography.Text type="secondary">
        SIN DATOS COMPLEMENTARIOS.
      </Typography.Text>
    )
  }

  return (
    <Space direction="vertical" size={8} style={{ width: '100%' }}>
      {items.map((item) => (
        <div key={item.key || item.label} className="report-legend-row">
          <Space>
            <Tag color={item[colorKey] || 'default'} style={{ borderRadius: 999 }}>
              {item.label}
            </Tag>
          </Space>
          <Typography.Text strong>{valueFormatter(item.value)}</Typography.Text>
        </div>
      ))}
    </Space>
  )
}
