/* eslint-disable react/prop-types */
import { Alert, Col, Form, Input, Row, Typography } from 'antd'


export function ReceiptSnapshotFields({ selectedClient, title = 'DATOS DOCUMENTALES DEL COMPROBANTE' }) {
  const requireName = !selectedClient
  const requireCi = !selectedClient?.ci
  const requireCellphone = !selectedClient?.celular
  const needsSnapshot = requireName || requireCi || requireCellphone

  if (!needsSnapshot) {
    return null
  }

  return (
    <>
      <Alert
        type="warning"
        showIcon
        style={{ marginBottom: 16 }}
        message="EL COMPROBANTE REQUIERE SNAPSHOT DOCUMENTAL COMPLETO"
        description={
          selectedClient
            ? 'LA CLIENTA SELECCIONADA NO TIENE TODOS SUS DATOS DOCUMENTALES COMPLETOS. COMPLETA SOLO LOS CAMPOS FALTANTES PARA EMITIR EL COMPROBANTE.'
            : 'LA OPERACIÓN NO ESTÁ ASOCIADA A UNA CLIENTA REGISTRADA. COMPLETA NOMBRE, CI/NIT Y CELULAR PARA PODER EMITIR EL COMPROBANTE.'
        }
      />

      <Typography.Title level={5}>{title}</Typography.Title>

      <Row gutter={12}>
        <Col xs={24} md={12}>
          <Form.Item
            label="NOMBRE PARA COMPROBANTE"
            name={['receipt_customer_snapshot', 'full_name']}
            rules={requireName ? [{ required: true, message: 'DEBE REGISTRAR EL NOMBRE DOCUMENTAL DEL CLIENTE.' }] : []}
            normalize={(value) => (value || '').toUpperCase()}
          >
            <Input
              placeholder={
                requireName
                  ? 'EJ. MARIA FERNANDA PEREZ'
                  : `YA EXISTE NOMBRE REGISTRADO: ${selectedClient?.full_name || 'CLIENTE SELECCIONADO'}`
              }
            />
          </Form.Item>
        </Col>
        <Col xs={24} md={6}>
          <Form.Item
            label="CI / NIT"
            name={['receipt_customer_snapshot', 'ci_nit']}
            rules={requireCi ? [{ required: true, message: 'DEBE REGISTRAR EL CI O NIT PARA EL COMPROBANTE.' }] : []}
            normalize={(value) => (value || '').toUpperCase()}
          >
            <Input placeholder={requireCi ? 'EJ. 1234567 LP' : `YA REGISTRADO: ${selectedClient?.ci || 'OK'}`} />
          </Form.Item>
        </Col>
        <Col xs={24} md={6}>
          <Form.Item
            label="CELULAR"
            name={['receipt_customer_snapshot', 'cellphone']}
            rules={requireCellphone ? [{ required: true, message: 'DEBE REGISTRAR EL CELULAR PARA EL COMPROBANTE.' }] : []}
            normalize={(value) => (value || '').toUpperCase()}
          >
            <Input placeholder={requireCellphone ? 'EJ. 70000000' : `YA REGISTRADO: ${selectedClient?.celular || 'OK'}`} />
          </Form.Item>
        </Col>
      </Row>
    </>
  )
}
