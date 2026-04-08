import { Button, Result } from 'antd'
import { Link } from 'react-router-dom'

export function NotFoundPage() {
  return (
    <main className="forbidden-wrap">
      <Result
        status="404"
        title="404"
        subTitle="La ruta solicitada no existe dentro del sistema."
        extra={
          <Button type="primary">
            <Link to="/app">Ir al panel principal</Link>
          </Button>
        }
      />
    </main>
  )
}

