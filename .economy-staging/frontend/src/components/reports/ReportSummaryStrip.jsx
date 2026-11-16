/* eslint-disable react/prop-types */
import { Col, Row } from 'antd'

import { buildBreakdownMap, formatCount } from './reportUtils'
import { ReportKpiCard } from './ReportKpiCard'

export function ReportSummaryStrip({ summary, loading = false }) {
  const breakdown = buildBreakdownMap(summary)

  return (
    <Row gutter={[12, 12]} style={{ marginBottom: 18 }}>
      <Col xs={24} sm={12} lg={6}>
        <ReportKpiCard title="TOTAL GLOBAL" value={loading ? '...' : formatCount(summary?.global_total || 0)} accent="#8f3d2e" />
      </Col>
      <Col xs={24} sm={12} lg={6}>
        <ReportKpiCard title="TOTAL FILTRADO" value={loading ? '...' : formatCount(summary?.filtered_total || 0)} accent="#5c7468" />
      </Col>
      {breakdown.slice(0, 4).map((item, index) => (
        <Col key={item.key} xs={24} sm={12} lg={6}>
          <ReportKpiCard
            title={item.label}
            value={loading ? '...' : formatCount(item.count)}
            accent={['#a24d39', '#7a5c44', '#8a713f', '#5b677f'][index % 4]}
          />
        </Col>
      ))}
    </Row>
  )
}
