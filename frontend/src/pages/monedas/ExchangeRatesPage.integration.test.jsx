// @vitest-environment jsdom
import { cleanup, render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { App } from 'antd'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

const mocks = vi.hoisted(() => ({ get: vi.fn(), patch: vi.fn(), reload: vi.fn() }))
vi.mock('../../api/client', () => ({ apiClient: { get: mocks.get, patch: mocks.patch } }))
vi.mock('../../auth/AuthProvider', () => ({ useAuth: () => ({ user: { permissions: ['exchange_rates:update'] } }) }))
vi.mock('../../components/reports/useListingSummary', () => ({ useListingSummary: () => ({ summary: null, loading: false, reload: mocks.reload }) }))
vi.mock('../../components/reports/ReportSummaryStrip', () => ({ ReportSummaryStrip: () => null }))

import { ExchangeRatesPage } from './ExchangeRatesPage'

const manual = { id: 1, moneda_id: 12, moneda_codigo: 'USD', moneda_nombre: 'DÓLAR', valor_bob: '6.9600', origen: 'MANUAL', activo: true, registrado_por: 'ADMIN', fecha_registro: '2026-11-04T12:00:00Z' }
beforeEach(() => {
  vi.clearAllMocks()
  const originalComputedStyle = window.getComputedStyle
  vi.spyOn(window, 'getComputedStyle').mockImplementation((element) => originalComputedStyle(element))
  vi.stubGlobal('matchMedia', () => ({ matches: false, addListener: () => {}, removeListener: () => {}, addEventListener: () => {}, removeEventListener: () => {} }))
  mocks.get.mockImplementation(async (url) => {
    if (url === '/monedas') return { data: [{ id: 12, codigo: 'USD', nombre: 'DÓLAR' }] }
    if (url === '/monedas/tipos-cambio') return { data: [manual] }
    if (url === '/monedas/tipos-cambio/1') return { data: { ...manual, moneda: { id: 12 }, observaciones: null } }
    throw new Error('Unexpected synthetic request')
  })
  mocks.patch.mockResolvedValue({ data: { ...manual, id: 2 } })
})
afterEach(() => { cleanup(); vi.restoreAllMocks(); vi.unstubAllGlobals() })

describe('Ant Design decimal capture', () => {
  it('does not round excessive decimal input into a valid submission on blur', async () => {
    const user = userEvent.setup()
    render(<App><ExchangeRatesPage /></App>)
    const row = (await screen.findByText('DÓLAR')).closest('tr')
    await user.click(within(row).getByRole('button', { name: /Editar/ }))
    const input = await screen.findByPlaceholderText('Ej. 6.9600')
    await user.clear(input)
    await user.type(input, '6.96001')
    await user.tab()
    await user.click(screen.getByRole('button', { name: 'Guardar cambios' }))
    await screen.findByText('Ingresa un valor positivo de hasta ocho enteros y cuatro decimales.')
    expect(mocks.patch).not.toHaveBeenCalled()
    await user.clear(input)
    await user.type(input, '7.0100')
    await user.click(screen.getByRole('button', { name: 'Guardar cambios' }))
    await waitFor(() => expect(mocks.patch).toHaveBeenCalledWith('/monedas/tipos-cambio/1', { valor_bob: '7.01', observaciones: null }))
  }, 20000)
})
