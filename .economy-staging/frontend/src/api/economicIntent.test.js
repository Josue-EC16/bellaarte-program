import { beforeEach, describe, expect, it } from 'vitest'
import { clearEconomicIntents, completeEconomicIntent, economicIntent, isEconomicWrite } from './economicIntent'

beforeEach(() => clearEconomicIntents())
const request = (amount = 100) => ({ method: 'post', url: '/economia/devoluciones', data: { origin_id: 1, refund_amount: amount } })

describe('Intentos económicos', () => {
  it('conserva la clave tras una respuesta incierta y el reordenamiento del JSON', () => {
    const initial = economicIntent(request(), 'cashier-1')
    const retry = economicIntent({ ...request(), data: JSON.stringify({ refund_amount: 100, origin_id: 1 }) }, 'cashier-1')
    expect(retry.key).toBe(initial.key)
  })
  it('renueva después del éxito y separa actores y payloads', () => {
    const initial = economicIntent(request(), 'cashier-1')
    expect(economicIntent(request(), 'cashier-2').key).not.toBe(initial.key)
    completeEconomicIntent(initial.signature)
    expect(economicIntent(request(), 'cashier-1').key).not.toBe(initial.key)
    const changed = economicIntent(request(50), 'cashier-1')
    expect(changed.key).not.toBe(initial.key)
    expect(economicIntent(request(), 'cashier-1').key).not.toBe(initial.key)
  })
  it('una respuesta anterior no completa un intento nuevo con distinto importe', () => {
    const first = economicIntent(request(), 'cashier-1')
    const changed = economicIntent(request(50), 'cashier-1')
    completeEconomicIntent(first.signature)
    expect(economicIntent(request(50), 'cashier-1').key).toBe(changed.key)
  })
  it('incluye cobros, custodia y cierres sin asignar claves a consultas', () => {
    for (const url of ['/boutique/sales', '/pedidos/5/pagos', '/fletes/salidas', '/economia/garantias/4/movimientos', '/economia/cortes-caja/1/close']) {
      expect(isEconomicWrite({ method: 'post', url })).toBe(true)
      expect(isEconomicWrite({ method: 'get', url })).toBe(false)
    }
    expect(isEconomicWrite({ method: 'post', url: '/auth/login' })).toBe(false)
  })
})
