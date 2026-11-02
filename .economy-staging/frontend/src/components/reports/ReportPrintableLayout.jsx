/* eslint-disable react/prop-types */
import { useEffect } from 'react'
import { Button, Col, Divider, Row, Space, Typography } from 'antd'

export function ReportPrintableLayout({ title, subtitle, filtersLabel, children, onBack, onPrint }) {
  useEffect(() => {
    document.body.classList.add('report-print-active')
    return () => {
      document.body.classList.remove('report-print-active')
    }
  }, [])

  return (
    <div className="report-print-layout report-print-page">
      <div className="report-print-toolbar">
        <Space wrap>
          <Button onClick={onBack}>VOLVER ATRÁS</Button>
          <Button type="primary" onClick={onPrint}>
            IMPRIMIR ESTO
          </Button>
        </Space>
      </div>
      <header className="report-print-header">
        <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
          <img src="/logo_bellaarte2.png" alt="BellaArte Boutique" style={{ width: 88, height: 'auto' }} />
          <div>
            <Typography.Title level={2} style={{ margin: 0, color: '#4d2219' }}>
              BELLAARTE BOUTIQUE
            </Typography.Title>
            <Typography.Text>{title}</Typography.Text>
            <br />
            <Typography.Text type="secondary">{subtitle}</Typography.Text>
          </div>
        </div>
        <div style={{ textAlign: 'right' }}>
          <Typography.Text strong>EMISIÓN</Typography.Text>
          <br />
          <Typography.Text>{new Date().toLocaleString('es-BO')}</Typography.Text>
        </div>
      </header>
      <Divider />
      <Row gutter={[12, 12]} style={{ marginBottom: 16 }}>
        <Col span={24}>
          <Typography.Text strong>FILTROS APLICADOS:</Typography.Text>{' '}
          <Typography.Text>{filtersLabel || 'SIN FILTROS ESPECÍFICOS'}</Typography.Text>
        </Col>
      </Row>
      {children}
    </div>
  )
}
