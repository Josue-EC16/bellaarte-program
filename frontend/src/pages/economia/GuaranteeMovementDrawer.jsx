/* eslint-disable react/prop-types */
import { Alert, App, Button, Descriptions, Drawer, Form, Input, InputNumber, Select } from 'antd'
import { useEffect, useRef, useState } from 'react'

import { apiClient } from '../../api/client'
import { FORM_COMMON_PROPS } from '../../components/forms/formConfig'
import { FormProcessAlert } from '../../components/forms/FormProcessAlert'
import { applyFormApiError } from '../../components/forms/formErrorUtils'
import { formatBs } from './economyUtils'

const METHODS = [
  { value: 'efectivo', label: 'EFECTIVO' }, { value: 'qr', label: 'QR' },
  { value: 'transaccion', label: 'TRANSFERENCIA' }, { value: 'tarjeta', label: 'TARJETA' },
  { value: 'ticket_o_vale', label: 'TICKET O VALE' },
]

export function GuaranteeMovementDrawer({ outputId, isAdmin, onClose, onSaved }) {
  const [form] = Form.useForm()
  const { message } = App.useApp()
  const [balance, setBalance] = useState(null)
  const [error, setError] = useState(null)
  const [saving, setSaving] = useState(false)
  const pending = useRef(false)
  useEffect(() => {
    setBalance(null)
    setError(null)
    form.resetFields()
    if (!outputId) return
    const controller = new AbortController()
    apiClient.get(`/economia/garantias/${outputId}`, { signal: controller.signal })
      .then(({ data }) => { if (!controller.signal.aborted) setBalance(data) })
      .catch((failure) => { if (!controller.signal.aborted) setError(failure.response?.data?.detail || 'NO FUE POSIBLE LEER LA CUSTODIA.') })
    return () => controller.abort()
  }, [outputId, form])

  const submit = async (values) => {
    if (pending.current) return
    pending.current = true
    setSaving(true)
    setError(null)
    try {
      await apiClient.post(`/economia/garantias/${outputId}/movimientos`, values)
      message.success('MOVIMIENTO DE CUSTODIA REGISTRADO. NO ES INGRESO COMERCIAL.')
      onClose()
      onSaved?.()
    } catch (failure) {
      setError(applyFormApiError(form, failure, { fallbackGlobalMessage: 'NO FUE POSIBLE REGISTRAR EL MOVIMIENTO.' }).globalMessage)
    } finally {
      pending.current = false
      setSaving(false)
    }
  }

  return <Drawer title={`Custodia de garantía — salida #${outputId || ''}`} width={640} open={Boolean(outputId)} onClose={() => { if (!saving) onClose() }} maskClosable={false}>
    <Alert type="info" showIcon message="DINERO EN CUSTODIA, SEPARADO DEL COBRO DEL FLETE" description="La devolución física del vestido no paga la garantía. Una retención requiere autorización del administrador y queda pendiente de liquidación." style={{ marginBottom: 16 }} />
    <FormProcessAlert message={error} />
    {balance ? <Descriptions bordered column={1} size="small" style={{ marginBottom: 16 }}>
      <Descriptions.Item label="RECIBIDO">{formatBs(balance.received_bob)}</Descriptions.Item>
      <Descriptions.Item label="DEVUELTO">{formatBs(balance.returned_bob)}</Descriptions.Item>
      <Descriptions.Item label="RETENIDO PENDIENTE">{formatBs(balance.retained_pending_bob)}</Descriptions.Item>
      <Descriptions.Item label="DISPONIBLE PARA DEVOLVER">{formatBs(balance.available_return_bob)}</Descriptions.Item>
    </Descriptions> : null}
    <Form {...FORM_COMMON_PROPS} form={form} onFinish={submit}>
      <Form.Item name="action" label="MOVIMIENTO REAL" rules={[{ required: true }]}>
        <Select options={[{ value: 'RECEIVE', label: 'RECIBIR GARANTÍA' }, { value: 'RETURN', label: 'DEVOLVER GARANTÍA' }, ...(isAdmin ? [{ value: 'RETAIN', label: 'AUTORIZAR RETENCIÓN PENDIENTE' }] : [])]} />
      </Form.Item>
      <Form.Item name="amount" label="MONTO (BOB)" rules={[{ required: true }]}><InputNumber min={0.01} precision={2} style={{ width: '100%' }} /></Form.Item>
      <Form.Item name="payment_method" label="MÉTODO REAL" rules={[{ required: true }]}><Select options={METHODS} /></Form.Item>
      <Form.Item name="reason" label="MOTIVO / AUTORIZACIÓN" rules={[{ required: true }, { min: 5 }]}><Input.TextArea rows={3} maxLength={300} /></Form.Item>
      <Button type="primary" htmlType="submit" loading={saving} disabled={!balance}>REGISTRAR MOVIMIENTO</Button>
    </Form>
  </Drawer>
}
