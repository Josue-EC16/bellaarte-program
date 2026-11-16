/* eslint-disable react/prop-types */
import { Empty } from 'antd'

export function ReportEmptyState({ description = 'SIN DATOS DISPONIBLES PARA ESTE REPORTE.' }) {
  return <Empty description={description} image={Empty.PRESENTED_IMAGE_SIMPLE} />
}
