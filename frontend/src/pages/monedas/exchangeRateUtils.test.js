import { describe, expect, it } from 'vitest'

import { canDeactivateRate, exchangeRatePayload, isManualRate, isValidExchangeRate } from './exchangeRateUtils'

describe('exact decimal exchange rate capture', () => {
  it.each(['0.0001', '6.9600', '99999999.9999', '1', '0006.96'])('accepts %s as a positive decimal string', (value) => {
    expect(isValidExchangeRate(value)).toBe(true)
  })
  it.each(['', ' ', '0', '0.0000', '-1', '6.96001', '100000000', '1e2', 'NaN', 'Infinity', '6,96', '6USD', '.5', '6.', null, 6.96])('rejects %s without changing its content', (value) => {
    expect(isValidExchangeRate(value)).toBe(false)
  })
  it('keeps decimal digits and activates only new manual inserts', () => {
    const values = { moneda_id: 12, valor_bob: '6.9600', observaciones: ' referencia ', activo: false, origen: 'AUTOMATICO' }
    expect(exchangeRatePayload(values)).toEqual({ moneda_id: 12, valor_bob: '6.9600', observaciones: 'REFERENCIA', activo: true })
    expect(exchangeRatePayload(values, { editing: true })).toEqual({ valor_bob: '6.9600', observaciones: 'REFERENCIA' })
  })
  it('allows deactivation only for an active manual non-BOB rate', () => {
    const manual = { origen: 'MANUAL', activo: true, moneda_codigo: 'USD' }
    expect(isManualRate(manual)).toBe(true)
    expect(canDeactivateRate(manual)).toBe(true)
    for (const value of [{ ...manual, origen: 'AUTOMATICO' }, { ...manual, activo: false }, { ...manual, moneda_codigo: 'BOB' }]) {
      expect(canDeactivateRate(value)).toBe(false)
    }
    expect(isManualRate({})).toBe(false)
  })
})
