/* eslint-disable react/prop-types */
import { Button, Typography } from 'antd'
import { renderToStaticMarkup } from 'react-dom/server'
import { formatBs, incomeSourceLabel } from './economyUtils'

export function RefundReceiptDocument({ document }) {
  const snapshot = document.snapshot || {}
  const content = <article aria-label="Constancia interna de devolución">
      <h2>BELLAARTE BOUTIQUE</h2>
      <h3>Constancia de devolución #{document.id}</h3>
      <p><strong>DOCUMENTO INTERNO — NO FISCAL</strong></p>
      <dl>
        <dt>Fecha de emisión</dt><dd>{new Date(document.fecha).toLocaleString('es-BO', { timeZone: 'America/La_Paz' })}</dd>
        <dt>Origen</dt><dd>{incomeSourceLabel(snapshot.origin_type)} #{snapshot.origin_id}</dd>
        <dt>Comprobante original</dt><dd>{snapshot.original_receipt_id ? `#${snapshot.original_receipt_id}` : 'SIN REFERENCIA'}</dd>
        <dt>Egreso</dt><dd>#{snapshot.expense_id}</dd>
        <dt>Importe devuelto</dt><dd>{formatBs(snapshot.amount_bob)}</dd>
        <dt>Método real de devolución</dt><dd>{snapshot.payment_method === 'transaccion' ? 'TRANSFERENCIA' : snapshot.payment_method?.toUpperCase()}</dd>
        <dt>Responsable</dt><dd>{snapshot.responsible} (#{snapshot.responsible_id})</dd>
        <dt>Beneficiario</dt><dd>{snapshot.beneficiary || 'SIN REGISTRO'}</dd>
        <dt>Motivo</dt><dd style={{ whiteSpace: 'pre-wrap' }}>{snapshot.reason}</dd>
        <dt>Total devuelto a la fecha de emisión</dt><dd>{formatBs(snapshot.refunded_total_bob)}</dd>
        <dt>Saldo reembolsable a la fecha de emisión</dt><dd>{formatBs(snapshot.refundable_balance_bob)}</dd>
      </dl>
      <p>Esta constancia conserva los datos de su emisión. La devolución de dinero es independiente del estado operativo y no modifica el comprobante original.</p>
    </article>

  const print = () => {
    const popup = window.open('', '_blank')
    if (!popup) return
    popup.opener = null
    // Snapshot values only enter the document through React's text escaping.
    popup.document.write(`<!doctype html><html lang="es"><head><meta charset="utf-8"><title>Constancia de devolución</title><style>body{font:14px Arial,sans-serif;margin:32px;color:#111}dt{font-weight:bold;margin-top:12px}dd{margin:4px 0;overflow-wrap:anywhere}@page{margin:16mm}</style></head><body>${renderToStaticMarkup(content)}</body></html>`)
    popup.document.close()
    popup.focus()
    popup.print()
  }
  return <>
    {content}
    <Typography.Paragraph type="secondary">Si el navegador bloquea la ventana, habilita las ventanas emergentes para imprimir esta constancia.</Typography.Paragraph>
    <Button onClick={print}>IMPRIMIR CONSTANCIA</Button>
  </>
}
