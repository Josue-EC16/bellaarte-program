/* eslint-disable react/prop-types */
import { Alert, Button, Col, Row, Space, Typography } from 'antd'

import { bolivianTimestamp, calendarDate, operationalAge, syncAlertType } from './exchangeRateSyncUtils'

export function ExchangeRateSyncStatus({ data, error, loading, onReload, recordsLink = false }) {
  const rate = data?.operational_rate
  const age = operationalAge(rate?.fecha_registro, data?.local_date)
  return (
    <section className="glass-panel" aria-label="Estado de sincronización USD/BOB" style={{ padding: 20, marginBottom: 20, borderTop: '3px solid #8f3d2e' }}>
      <Row justify="space-between" align="middle" gutter={[12, 12]}>
        <Col><Typography.Title level={4} style={{ margin: 0 }}>Dólar · USD / BOB</Typography.Title></Col>
        <Col><Space wrap>
          {recordsLink ? <Button href="/app/monedas/tipos-cambio/registros">Registros de sincronización</Button> : null}
          <Button onClick={onReload} loading={loading}>Consultar estado</Button>
        </Space></Col>
      </Row>
      {error ? <Alert type="warning" showIcon message={error} style={{ marginTop: 12 }} /> : null}
      {data ? <>
        <Alert type={syncAlertType(data.status)} showIcon message={data.message} style={{ marginTop: 12 }} />
        {data.official_today && rate?.origen === 'MANUAL' ? <Typography.Paragraph style={{ marginTop: 12 }}>
          La tasa manual continúa vigente hasta la siguiente consulta automática válida.
        </Typography.Paragraph> : null}
        <Row gutter={[20, 12]} style={{ marginTop: 16 }}>
          <Col xs={24} md={8}><Typography.Text type="secondary">Valor operativo de 1 USD</Typography.Text><Typography.Title level={3} style={{ margin: '4px 0' }}>{rate ? `Bs ${rate.valor_bob}` : 'Sin cotización activa'}</Typography.Title><Typography.Text>{rate?.origen === 'AUTOMATICO' ? 'AUTOMÁTICO · SISTEMA' : rate ? 'MANUAL · Provisional' : 'Intervención ADMIN requerida'}</Typography.Text></Col>
          <Col xs={24} md={8}><Typography.Text type="secondary">Procedencia y registro operativo</Typography.Text><Typography.Paragraph style={{ margin: '4px 0' }}>{rate?.fuente || (rate ? 'MANUAL · Fuente histórica no documentada' : '—')}</Typography.Paragraph><Typography.Text>{bolivianTimestamp(rate?.fecha_registro)} (Bolivia)</Typography.Text>{rate?.fecha_oficial ? <Typography.Paragraph style={{ margin: '4px 0' }}>Vigencia oficial operativa: {calendarDate(rate.fecha_oficial)}</Typography.Paragraph> : null}<Typography.Paragraph type="secondary" style={{ margin: '4px 0' }}>{age === null ? '' : `Antigüedad del registro operativo: ${age} ${age === 1 ? 'día' : 'días'}.`}</Typography.Paragraph></Col>
          <Col xs={24} md={8}><Typography.Text type="secondary">Última fecha oficial verificada</Typography.Text><Typography.Paragraph style={{ margin: '4px 0' }}>{calendarDate(data.last_official_date)}</Typography.Paragraph><Typography.Text>{data.attempts_used} / 10 intentos utilizados hoy · {data.attempts_remaining} disponibles</Typography.Text><Typography.Paragraph style={{ margin: '4px 0' }}>Próxima ejecución: {data.next_attempt_at ? `${bolivianTimestamp(data.next_attempt_at)} (Bolivia)` : data.status === 'EXHAUSTED' ? 'Mañana a las 05:00 (Bolivia)' : 'Sin ejecución pendiente'}</Typography.Paragraph></Col>
        </Row>
        {data.consecutive_missing_days >= 3 ? <Alert type="warning" showIcon message={`El tipo de cambio oficial acumula ${data.consecutive_missing_days} días calendario cerrados consecutivos sin verificación. Contacta a soporte técnico.`} style={{ marginTop: 12 }} /> : null}
        {recordsLink && data.backlog_count > 0 ? <Typography.Paragraph type="secondary" style={{ margin: '12px 0 0' }}>{data.backlog_count} fechas anteriores pendientes de recuperación; su carga no sustituirá el valor operativo actual.</Typography.Paragraph> : null}
      </> : !error ? <Typography.Paragraph style={{ margin: '12px 0 0' }}>Consultando estado de actualización…</Typography.Paragraph> : null}
    </section>
  )
}
