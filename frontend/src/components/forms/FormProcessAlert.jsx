/* eslint-disable react/prop-types */
import { Alert } from 'antd'

export function FormProcessAlert({
  message,
  description,
  title = 'Revisa la información del formulario.',
  style,
}) {
  if (!message && !description) {
    return null
  }

  return (
    <Alert
      type="error"
      showIcon
      message={title}
      description={description || message}
      style={{ marginBottom: 20, ...style }}
    />
  )
}
