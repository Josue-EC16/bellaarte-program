// @vitest-environment jsdom
/* eslint-disable react/prop-types */
import { act, cleanup, fireEvent, render, renderHook, screen } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

const mocks = vi.hoisted(() => ({ get: vi.fn(), user: { role_code: 'ADMIN', permissions: ['exchange_rates_sync:list', 'exchange_rates_sync:view', 'exchange_rates:view'] } }))
vi.mock('../../api/client', () => ({ apiClient: { get: mocks.get } }))
vi.mock('../../auth/AuthProvider', () => ({ useAuth: () => ({ user: mocks.user }) }))
vi.mock('antd', () => {
  const Box = ({ children }) => <div>{children}</div>
  return {
    Typography: { Title: Box, Paragraph: Box, Text: Box }, Row: Box, Col: Box, Space: Box, Tag: Box,
    Alert: ({ message, action }) => <div role="alert">{message}{action}</div>,
    Button: ({ children, href, onClick, loading }) => href ? <a href={href}>{children}</a> : <button disabled={loading} onClick={onClick}>{children}</button>,
    Input: (props) => <input {...props} />,
    Select: ({ options, onChange, allowClear, ...props }) => <select {...props} data-clearable={String(allowClear)} onChange={(event) => onChange(event.target.value)}><option value="">Todos</option>{options.map(({ value, label }) => <option key={value} value={value}>{label}</option>)}</select>,
    Drawer: ({ open, children, onClose }) => open ? <div role="dialog"><button onClick={onClose}>Cerrar detalle</button>{children}</div> : null,
    Descriptions: ({ items }) => <dl>{items.map(({ key, label, children }) => <div key={key}><dt>{label}</dt><dd>{children}</dd></div>)}</dl>,
    Table: ({ columns, dataSource, pagination }) => <><table><tbody>{dataSource.map((row) => <tr key={row.id}>{columns.map((column) => <td key={column.key || column.dataIndex}>{column.render ? column.render(row[column.dataIndex], row) : row[column.dataIndex]}</td>)}</tr>)}</tbody></table><button onClick={() => pagination.onChange(2, 25)}>Página siguiente</button></>,
  }
})

import { ExchangeRateSyncStatus } from './ExchangeRateSyncStatus'
import { ExchangeRateSyncRecordsPage } from './ExchangeRateSyncRecordsPage'
import { ExchangeRateLinkDetail } from './ExchangeRateLinkDetail'
import { bolivianTimestamp, calendarDate, canReadSyncRecords, operationalAge, SYNC_BASE, validRecordId } from './exchangeRateSyncUtils'
import { useExchangeRateSyncStatus } from './useExchangeRateSyncStatus'
import { buildNotificationOriginPath, NOTIFICATION_MODULE_OPTIONS, NOTIFICATION_TYPE_OPTIONS } from '../notificaciones/notificationUtils'

const status = { enabled: true, local_date: '2026-11-04', status: 'MANUAL_AFTER_OFFICIAL', message: 'Cotización oficial consultada hoy; valor operativo actual: manual.', official_today: true,
  operational_rate: { id: 7, valor_bob: '7.1234', origen: 'MANUAL', fuente: 'MANUAL', fecha_registro: '2026-11-04T12:00:00Z' },
  last_official_date: '2026-11-04', attempts_used: 2, attempts_remaining: 8, next_attempt_at: null, consecutive_missing_days: 0, backlog_count: 0 }
const record = { id: 12, moneda_codigo: 'USD', fecha_objetivo: '2026-11-03', numero_intento: 3, fecha_intento: '2026-11-04T04:30:00Z', estado: 'ERROR_VIGENCIA', codigo_http: 200,
  proximo_intento: null, proveedor: 'FACTURA_BO_BCB', tipo_cambio_id: null, valor_bob: null, message: 'No fue posible demostrar la fecha de vigencia.' }
async function flush() { await act(async () => { await Promise.resolve(); await Promise.resolve(); await Promise.resolve() }) }
function renderRecords(path = '/records') {
  return render(<MemoryRouter initialEntries={[path]}><Routes><Route path="/records" element={<ExchangeRateSyncRecordsPage />} /><Route path="/403" element={<div>ACCESO DENEGADO</div>} /></Routes></MemoryRouter>)
}
beforeEach(() => {
  vi.clearAllMocks()
  mocks.user = { role_code: 'ADMIN', permissions: ['exchange_rates_sync:list', 'exchange_rates_sync:view', 'exchange_rates:view'] }
  vi.spyOn(document, 'visibilityState', 'get').mockReturnValue('visible')
  mocks.get.mockImplementation(async (url) => {
    if (url === `${SYNC_BASE}/estado`) return { data: status }
    if (url === `${SYNC_BASE}/registros`) return { data: { items: [record], total: 40, page: 1, page_size: 25 } }
    if (url === `${SYNC_BASE}/registros/12`) return { data: record }
    if (url === '/monedas/tipos-cambio/7') return { data: { ...status.operational_rate, moneda: { codigo: 'USD' }, activo: true, registrado_por: 'ADMIN' } }
    throw new Error('Unexpected synthetic request')
  })
})
afterEach(() => { cleanup(); vi.useRealTimers(); vi.restoreAllMocks() })

describe('synchronization semantics and links', () => {
  it('keeps calendar dates separate from UTC timestamps and measures age in Bolivia', () => {
    expect(calendarDate('2026-11-03')).toBe('03/11/2026')
    expect(bolivianTimestamp('2026-11-04T02:00:00Z')).toContain('3/11/26')
    expect(operationalAge('2026-11-04T02:00:00Z', '2026-11-04')).toBe(1)
    expect(bolivianTimestamp('broken')).toBe('—')
    expect(validRecordId('2foo')).toBeNull()
    expect(validRecordId('9007199254740993')).toBeNull()
    expect(validRecordId('12')).toBe(12)
  })
  it('requires both current ADMIN role and permission for technical records', () => {
    expect(canReadSyncRecords({ role_code: 'CAJA', permissions: ['exchange_rates_sync:list'] })).toBe(false)
    expect(canReadSyncRecords({ role_code: 'ADMIN', permissions: [] })).toBe(false)
    expect(canReadSyncRecords(mocks.user)).toBe(true)
  })
  it('provides domain-specific notification links without general audit routes', () => {
    expect(buildNotificationOriginPath({ tabla_referencia: 'TIPO_CAMBIO_REGISTROS', id_referencia: 12 })).toBe('/app/monedas/tipos-cambio/registros?record_id=12')
    expect(buildNotificationOriginPath({ tabla_referencia: 'TIPO_CAMBIO_MONEDA', id_referencia: 7 })).toBe('/app/monedas/tipos-cambio?rate_id=7')
    expect(NOTIFICATION_MODULE_OPTIONS.some((item) => item.value === 'MONEDAS')).toBe(true)
    expect(NOTIFICATION_TYPE_OPTIONS.some((item) => item.value === 'TC_SYNC_PROLONGADO')).toBe(true)
  })
  it('distinguishes manual active value from today verified official and preserves decimal text', () => {
    render(<ExchangeRateSyncStatus data={status} loading={false} recordsLink onReload={vi.fn()} />)
    expect(screen.getByText('Bs 7.1234')).toBeTruthy()
    expect(screen.getByText('MANUAL · Provisional')).toBeTruthy()
    expect(screen.getByText('Cotización oficial consultada hoy; valor operativo actual: manual.')).toBeTruthy()
    expect(screen.getByText('La tasa manual continúa vigente hasta la siguiente consulta automática válida.')).toBeTruthy()
    expect(screen.getByRole('link', { name: 'Registros de sincronización' }).getAttribute('href')).toBe('/app/monedas/tipos-cambio/registros')
  })
  it('shows no invented fallback when there is no active rate and no admin link for other roles', () => {
    render(<ExchangeRateSyncStatus data={{ ...status, operational_rate: null, status: 'NO_ACTIVE_RATE', message: 'Intervención requerida', consecutive_missing_days: 3 }} loading={false} onReload={vi.fn()} />)
    expect(screen.getByText('Sin cotización activa')).toBeTruthy()
    expect(screen.getByText(/3 días calendario cerrados/)).toBeTruthy()
    expect(screen.queryByRole('link')).toBeNull()
  })
})

describe('status polling', () => {
  it('polls only while visible, refreshes on focus and clears listeners/timer on unmount', async () => {
    vi.useFakeTimers()
    const visibility = vi.spyOn(document, 'visibilityState', 'get')
    const hook = renderHook(() => useExchangeRateSyncStatus())
    await flush()
    expect(mocks.get).toHaveBeenCalledTimes(1)
    await act(async () => { await vi.advanceTimersByTimeAsync(60000) })
    expect(mocks.get).toHaveBeenCalledTimes(2)
    visibility.mockReturnValue('hidden')
    await act(async () => { await vi.advanceTimersByTimeAsync(120000) })
    expect(mocks.get).toHaveBeenCalledTimes(2)
    visibility.mockReturnValue('visible')
    fireEvent.focus(window)
    await flush()
    expect(mocks.get).toHaveBeenCalledTimes(3)
    hook.unmount()
    await act(async () => { await vi.advanceTimersByTimeAsync(60000) })
    fireEvent.focus(window)
    expect(mocks.get).toHaveBeenCalledTimes(3)
  })
  it('retains last state with a visible error and allows recovery', async () => {
    const hook = renderHook(() => useExchangeRateSyncStatus())
    await flush()
    mocks.get.mockRejectedValueOnce(new Error('network'))
    await act(async () => { await hook.result.current.reload() })
    expect(hook.result.current.data.operational_rate.valor_bob).toBe('7.1234')
    expect(hook.result.current.error).toContain('desactualizado')
    await act(async () => { await hook.result.current.reload() })
    expect(hook.result.current.error).toBeNull()
  })
  it('replaces an in-flight old status after a manual save and ignores its late response', async () => {
    let finishOld
    let oldSignal
    mocks.get.mockImplementationOnce((url, options) => { oldSignal = options.signal; return new Promise((resolve) => { finishOld = resolve }) })
    const hook = renderHook(() => useExchangeRateSyncStatus())
    await flush()
    await act(async () => { await hook.result.current.reload({ force: true }) })
    expect(oldSignal.aborted).toBe(true)
    expect(hook.result.current.data.operational_rate.valor_bob).toBe('7.1234')
    await act(async () => { finishOld({ data: { ...status, operational_rate: { ...status.operational_rate, valor_bob: '6.9600' } } }); await Promise.resolve() })
    expect(hook.result.current.data.operational_rate.valor_bob).toBe('7.1234')
    expect(hook.result.current.loading).toBe(false)
  })
})

describe('read-only technical records', () => {
  it('does not fetch technical records or status for a nonADMIN even with stale permission', async () => {
    mocks.user.role_code = 'CAJA'
    renderRecords()
    await flush()
    expect(screen.getByText('ACCESO DENEGADO')).toBeTruthy()
    expect(mocks.get).not.toHaveBeenCalled()
  })
  it('requests server-side pagination and target/execution date filters', async () => {
    renderRecords()
    await flush()
    expect(screen.getByRole('cell', { name: 'ERROR VIGENCIA' })).toBeTruthy()
    fireEvent.click(screen.getByText('Página siguiente'))
    await flush()
    expect(mocks.get).toHaveBeenLastCalledWith(`${SYNC_BASE}/registros`, expect.objectContaining({ params: { page: 2, page_size: 25 } }))
    fireEvent.change(screen.getByLabelText('Objetivo desde'), { target: { value: '2026-11-01' } })
    fireEvent.change(screen.getByLabelText('Ejecución hasta'), { target: { value: '2026-11-04' } })
    await flush()
    expect(mocks.get).toHaveBeenLastCalledWith(`${SYNC_BASE}/registros`, expect.objectContaining({ params: { date_from: '2026-11-01', execution_to: '2026-11-04', page: 1, page_size: 25 } }))
    fireEvent.change(screen.getByLabelText('Estado'), { target: { value: 'ERROR_API' } })
    await flush()
    expect(mocks.get).toHaveBeenLastCalledWith(`${SYNC_BASE}/registros`, expect.objectContaining({ params: expect.objectContaining({ estado: 'ERROR_API' }) }))
    expect(screen.queryByText('Eliminar')).toBeNull()
    expect(screen.queryByText('Reintentar sincronización')).toBeNull()
  })
  it('opens a notification record using a fresh detail GET and displays normalized explanation', async () => {
    renderRecords('/records?record_id=12')
    await flush()
    expect(mocks.get).toHaveBeenCalledWith(`${SYNC_BASE}/registros/12`, expect.objectContaining({ signal: expect.any(AbortSignal) }))
    expect(screen.getByRole('dialog')).toBeTruthy()
    expect(screen.getByText('No fue posible demostrar la fecha de vigencia.')).toBeTruthy()
    fireEvent.click(screen.getByText('Cerrar detalle'))
    await flush()
    expect(screen.queryByRole('dialog')).toBeNull()
  })
  it('reports invalid deep-link ID without querying an arbitrary endpoint', async () => {
    renderRecords('/records?record_id=12abc')
    await flush()
    expect(screen.getByText('El identificador del registro no es válido.')).toBeTruthy()
    expect(mocks.get.mock.calls.some(([url]) => url.endsWith('/12abc'))).toBe(false)
  })
  it('does not load detail without the view permission', async () => {
    mocks.user.permissions = ['exchange_rates_sync:list']
    renderRecords('/records?record_id=12')
    await flush()
    expect(screen.getByText('No tienes permiso para consultar este detalle.')).toBeTruthy()
    expect(mocks.get.mock.calls.some(([url]) => url.endsWith('/12'))).toBe(false)
    expect(screen.queryByText('Ver detalle')).toBeNull()
  })
  it('displays a recoverable list failure and rejects an inverted filter period', async () => {
    mocks.get.mockImplementation(async (url) => { if (url.endsWith('/estado')) return { data: status }; throw new Error('unavailable') })
    renderRecords()
    await flush()
    expect(screen.getByText('No fue posible cargar los registros de sincronización.')).toBeTruthy()
    expect(screen.getByText('Reintentar')).toBeTruthy()
    fireEvent.change(screen.getByLabelText('Objetivo desde'), { target: { value: '2026-11-04' } })
    fireEvent.change(screen.getByLabelText('Objetivo hasta'), { target: { value: '2026-11-01' } })
    await flush()
    expect(screen.getByText('La fecha desde no puede ser posterior a la fecha hasta.')).toBeTruthy()
  })
  it('opens a read-only fresh rate detail from the successful notification link', async () => {
    render(<MemoryRouter initialEntries={['/rates?rate_id=7']}><ExchangeRateLinkDetail /></MemoryRouter>)
    await flush()
    expect(mocks.get).toHaveBeenCalledWith('/monedas/tipos-cambio/7', expect.objectContaining({ signal: expect.any(AbortSignal) }))
    expect(screen.getByText('7.1234')).toBeTruthy()
    expect(screen.queryByRole('button', { name: 'Editar' })).toBeNull()
  })
})
