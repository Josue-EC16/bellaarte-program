export const RECEIPT_ORIGIN_OPTIONS = [
  { value: 'VENTA_BOUTIQUE', label: 'VENTA BOUTIQUE' },
  { value: 'PAGO_PEDIDO', label: 'PAGO PEDIDO' },
  { value: 'SALIDA_FLETE', label: 'SALIDA FLETE' },
]

export const RECEIPT_STATE_OPTIONS = [
  { value: 'emitido', label: 'EMITIDO' },
  { value: 'anulado', label: 'ANULADO' },
]

export function receiptStateColor(value) {
  return value === 'emitido' ? 'green' : 'red'
}

export function receiptOriginLabel(value) {
  return RECEIPT_ORIGIN_OPTIONS.find((option) => option.value === value)?.label || value
}

export function formatReceiptMoney(value) {
  return new Intl.NumberFormat('es-BO', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(Number(value || 0))
}

export function buildReceiptOriginPath(receipt) {
  if (receipt.origin_type === 'VENTA_BOUTIQUE') {
    return `/app/boutique/ventas?sale_id=${receipt.origin_id}`
  }
  if (receipt.origin_type === 'PAGO_PEDIDO') {
    return `/app/pedidos/pagos?payment_id=${receipt.origin_id}`
  }
  if (receipt.origin_type === 'SALIDA_FLETE') {
    return `/app/fletes/salidas?output_id=${receipt.origin_id}`
  }
  return '/app'
}

function withBaseHref(html) {
  if (html.includes('<base ')) {
    return html
  }
  return html.replace('<head>', `<head><base href="${window.location.origin}/" />`)
}

export async function openPrintableHtml(apiClient, path, messageApi) {
  try {
    const response = await apiClient.get(path, { responseType: 'text' })
    const popup = window.open('', '_blank')
    if (!popup) {
      messageApi?.error('EL NAVEGADOR BLOQUEÓ LA VENTANA DE IMPRESIÓN.')
      return
    }
    popup.document.write(withBaseHref(response.data))
    popup.document.close()
  } catch (error) {
    messageApi?.error(error.response?.data?.detail || 'NO FUE POSIBLE GENERAR EL DOCUMENTO IMPRIMIBLE.')
  }
}

export async function openReceiptPrintable(apiClient, receiptId, messageApi) {
  if (!receiptId) return
  await openPrintableHtml(apiClient, `/comprobantes/${receiptId}/printable`, messageApi)
}
