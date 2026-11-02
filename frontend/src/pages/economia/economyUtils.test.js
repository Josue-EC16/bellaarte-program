import { describe, expect, it } from 'vitest'
import { buildRefundPath, formatBs } from './economyUtils'

describe('Representación económica', () => {
  it('distingue un saldo no comparable de un cero real', () => {
    expect(formatBs(null)).not.toBe('Bs 0.00')
    expect(formatBs(undefined)).not.toBe('Bs 0.00')
    expect(formatBs(0)).toBe('Bs 0.00')
    expect(formatBs(400)).toBe('Bs 400.00')
  })
  it('el enlace de devolución no solicita anular el origen', () => {
    const url = new URL(buildRefundPath({ originType: 'PAGO_PEDIDO', originId: 5, targetState: 'ANULADA', returnTo: '/app/pedidos/pagos' }), 'http://localhost')
    expect(url.searchParams.get('origin_id')).toBe('5')
    expect(url.searchParams.has('target_status')).toBe(false)
    expect(url.searchParams.get('return_to')).toBe('/app/pedidos/pagos')
  })
})
