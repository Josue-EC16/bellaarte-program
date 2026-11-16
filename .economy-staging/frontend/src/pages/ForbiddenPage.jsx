import { Button, Result } from 'antd'
import { Link } from 'react-router-dom'

export function ForbiddenPage() {
  return (
    <main className="forbidden-wrap">
      <Result
        status="403"
        title="403"
        subTitle="No tienes permisos para acceder a esta seccion del sistema."
        extra={
          <Button type="primary">
            <Link to="/app">Volver al inicio</Link>
          </Button>
        }
      />
    </main>
  )
}

