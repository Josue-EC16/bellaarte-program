/* eslint-disable react/prop-types */
import { Button, Space, Typography } from 'antd'

export function ReportPageHeader({ title, description, onPrint, extra }) {
  return (
    <div className="page-header">
      <div>
        <Typography.Title level={2} style={{ margin: 0 }}>
          {title}
        </Typography.Title>
        <Typography.Paragraph type="secondary" style={{ marginBottom: 0 }}>
          {description}
        </Typography.Paragraph>
      </div>
      <Space wrap>
        {extra}
        {onPrint ? (
          <Button type="primary" onClick={onPrint}>
            IMPRIMIR / PDF
          </Button>
        ) : null}
      </Space>
    </div>
  )
}
