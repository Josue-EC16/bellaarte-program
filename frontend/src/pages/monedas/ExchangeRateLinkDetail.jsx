import { Alert, Button, Descriptions, Drawer, Typography } from 'antd'
import { useEffect, useState } from 'react'
import { useSearchParams } from 'react-router-dom'

import { apiClient } from '../../api/client'
import { useAuth } from '../../auth/AuthProvider'
import { bolivianTimestamp, validRecordId } from './exchangeRateSyncUtils'
import { exchangeRateActionError } from './exchangeRateUtils'

export function ExchangeRateLinkDetail() {
  const [params, setParams] = useSearchParams()
  const { user } = useAuth()
  const [detail, setDetail] = useState(null)
  const [error, setError] = useState(null)
  const [loading, setLoading] = useState(false)
  const [revision, setRevision] = useState(0)
  const requested = params.get('rate_id')
  const id = validRecordId(requested)
  const allowed = user?.permissions?.includes('exchange_rates:view')
  useEffect(() => {
    setDetail(null)
    setError(null)
    setLoading(false)
    if (!requested) return
    if (!id || !allowed) {
      setError(!allowed ? 'No tienes permiso para consultar esta cotización.' : 'El identificador de cotización no es válido.')
      return
    }
    const controller = new AbortController()
    setLoading(true)
    apiClient.get(`/monedas/tipos-cambio/${id}`, { signal: controller.signal })
      .then(({ data }) => { if (!controller.signal.aborted) setDetail(data) })
      .catch((requestError) => { if (!controller.signal.aborted) setError(exchangeRateActionError(requestError, 'No fue posible consultar la cotización.')) })
      .finally(() => { if (!controller.signal.aborted) setLoading(false) })
    return () => controller.abort()
  }, [requested, id, allowed, revision])
  const close = () => setParams((current) => { const next = new URLSearchParams(current); next.delete('rate_id'); return next }, { replace: true })
  return <Drawer title="Detalle de cotización" open={Boolean(requested)} onClose={close} maskClosable={false} width={560} destroyOnClose>
    {loading ? <Typography.Paragraph>Cargando cotización…</Typography.Paragraph> : null}
    {error ? <Alert type="error" showIcon message={error} action={id && allowed ? <Button onClick={() => setRevision((value) => value + 1)}>Reintentar</Button> : null} /> : null}
    {detail ? <Descriptions column={1} bordered items={[
      { key: 'id', label: 'Registro', children: `#${detail.id}` },
      { key: 'currency', label: 'Moneda', children: detail.moneda?.codigo },
      { key: 'value', label: 'Valor Bs', children: detail.valor_bob },
      { key: 'origin', label: 'Origen', children: detail.origen },
      { key: 'source', label: 'Fuente', children: detail.fuente || 'Sin fuente documentada' },
      { key: 'active', label: 'Estado', children: detail.activo ? 'ACTIVO' : 'HISTÓRICO INACTIVO' },
      { key: 'recorded', label: 'Registro · Bolivia', children: bolivianTimestamp(detail.fecha_registro) },
      { key: 'consulted', label: 'Captura · Bolivia', children: bolivianTimestamp(detail.fecha_consulta) },
      { key: 'actor', label: 'Registrado por', children: detail.registrado_por },
      { key: 'note', label: 'Observaciones', children: detail.observaciones || '—' },
    ]} /> : null}
  </Drawer>
}
