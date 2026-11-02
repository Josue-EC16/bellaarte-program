/* eslint-disable react/prop-types */
import { Typography } from 'antd'

export function ReportPrintSection({ title, subtitle, children }) {
  return (
    <section className="report-print-section">
      <header className="report-print-section-header">
        <div>
          <Typography.Title level={4} style={{ margin: 0, color: '#4d2219' }}>
            {title}
          </Typography.Title>
          {subtitle ? <Typography.Text type="secondary">{subtitle}</Typography.Text> : null}
        </div>
      </header>
      <div className="report-print-section-body">{children}</div>
    </section>
  )
}
