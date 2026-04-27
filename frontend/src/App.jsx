import { App as AntdApp, ConfigProvider } from 'antd'
import esES from 'antd/locale/es_ES'
import { BrowserRouter } from 'react-router-dom'

import './App.css'
import { AuthProvider } from './auth/AuthProvider'
import { FORM_VALIDATE_MESSAGES } from './components/forms/formConfig'
import { AppRoutes } from './routes/AppRoutes'

const theme = {
  token: {
    colorPrimary: '#8f3d2e',
    colorInfo: '#8f3d2e',
    borderRadius: 16,
    fontFamily: `"Segoe UI", "Trebuchet MS", sans-serif`,
  },
}

function App() {
  return (
    <ConfigProvider
      locale={esES}
      theme={theme}
      form={{ validateMessages: FORM_VALIDATE_MESSAGES }}
    >
      <AntdApp>
        <BrowserRouter>
          <AuthProvider>
            <AppRoutes />
          </AuthProvider>
        </BrowserRouter>
      </AntdApp>
    </ConfigProvider>
  )
}

export default App
