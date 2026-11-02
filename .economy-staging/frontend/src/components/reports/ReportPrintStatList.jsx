/* eslint-disable react/prop-types */
import { Typography } from 'antd'

export function ReportPrintStatList({ items = [], valueFormatter = (value) => value }) {
  if (!items.length) {
    return <Typography.Text type="secondary">SIN DATOS DISPONIBLES.</Typography.Text>
  }

  const maxValue = Math.max(...items.map((item) => Number(item.value || 0)), 1)

  return (
    <div className="report-print-stat-list">
      {items.map((item, index) => {
        const numericValue = Number(item.value || 0)
        const widthPercent = Math.max((numericValue / maxValue) * 100, 4)
        return (
          <div key={item.key || item.label || index} className="report-print-stat-row">
            <div className="report-print-stat-head">
              <Typography.Text strong>{item.label}</Typography.Text>
              <Typography.Text>{valueFormatter(item.value)}</Typography.Text>
            </div>
            <div className="report-print-stat-track">
              <div
                className="report-print-stat-fill"
                style={{ width: `${widthPercent}%`, background: item.color || '#8f3d2e' }}
              />
            </div>
          </div>
        )
      })}
    </div>
  )
}
