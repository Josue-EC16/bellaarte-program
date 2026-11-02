/* eslint-disable react/prop-types */
import { Typography } from 'antd'

export function ReportPrintTable({ columns = [], rows = [], emptyText = 'SIN DATOS DISPONIBLES.' }) {
  if (!rows.length) {
    return <Typography.Text type="secondary">{emptyText}</Typography.Text>
  }

  return (
    <div className="report-print-table-wrap">
      <table className="report-print-table">
        <thead>
          <tr>
            {columns.map((column) => (
              <th key={column.key || column.title}>{column.title}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, rowIndex) => (
            <tr key={row.id || row.key || rowIndex}>
              {columns.map((column) => {
                const rawValue = typeof column.dataIndex === 'function'
                  ? column.dataIndex(row)
                  : row[column.dataIndex]
                const value = column.render ? column.render(rawValue, row) : rawValue
                return <td key={column.key || column.title}>{value ?? 'SIN DATO'}</td>
              })}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
