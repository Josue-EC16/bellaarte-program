// @vitest-environment jsdom
/* eslint-disable react/prop-types */
import { act, cleanup, fireEvent, render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

const mocks = vi.hoisted(() => ({
  get: vi.fn(), patch: vi.fn(), post: vi.fn(),
  message: { success: vi.fn(), error: vi.fn(), warning: vi.fn() },
  modal: { confirm: vi.fn() },
  user: { user_id: 71, permissions: ['notifications:list', 'notifications:view', 'notifications:list_all',
    'notifications:report', 'notifications:mark_read', 'notifications:mark_all_read', 'notifications:resolve', 'users:list', 'roles:list'] },
}))

vi.mock('../../api/client', () => ({ apiClient: { get: mocks.get, patch: mocks.patch, post: mocks.post } }))
vi.mock('../../auth/AuthProvider', () => ({ useAuth: () => ({ user: mocks.user }) }))
vi.mock('@ant-design/icons', () => ({ CheckOutlined: () => null, EyeOutlined: () => null,
  LinkOutlined: () => null, ReloadOutlined: () => null, SearchOutlined: () => null }))

// Render the real page state/effects. Presentation-only AntD adapters keep this
// suite independent of layout APIs (ResizeObserver, matchMedia) absent in jsdom.
vi.mock('antd', () => {
  const Box = ({ children }) => <div>{children}</div>
  const Descriptions = Object.assign(Box, { Item: Box })
  return {
    App: { useApp: () => ({ message: mocks.message, modal: mocks.modal }) },
    Alert: ({ message }) => <div role="alert">{message}</div>,
    Button: ({ children, onClick, disabled, loading }) => <button disabled={disabled || loading} onClick={onClick}>{children}</button>,
    Card: Box, Col: Box, Descriptions, Row: Box, Space: Box, Tag: Box,
    Typography: { Title: Box, Paragraph: Box, Text: Box },
    Drawer: ({ open, children }) => open ? <div>{children}</div> : null,
    Input: ({ placeholder, value, onChange }) => <input placeholder={placeholder} value={value} onChange={onChange} />,
    Select: ({ options, value, onChange, placeholder, disabled, 'aria-label': label }) => (
      <select aria-label={label || placeholder} value={value || ''} disabled={disabled} onChange={(event) => onChange(event.target.value || undefined)}>
        <option value="">{placeholder || 'SELECCIONAR'}</option>
        {options.map((option) => <option value={option.value} key={option.value}>{option.label}</option>)}
      </select>
    ),
    Switch: ({ checked, loading, onChange, 'aria-label': label }) => (
      <button role="switch" aria-label={label} aria-checked={checked} disabled={loading} onClick={() => onChange(!checked)}>ESCRITORIO</button>
    ),
    Tabs: ({ items, onChange }) => <div>{items.map((item) => <button key={item.key} onClick={() => onChange(item.key)}>{item.label}</button>)}</div>,
    Table: ({ dataSource, columns }) => <table><tbody>{dataSource.map((row) => (
      <tr key={row.id}>{columns.map((column) => <td key={column.key || column.dataIndex}>
        {column.render ? column.render(row[column.dataIndex], row) : row[column.dataIndex]}
      </td>)}</tr>
    ))}</tbody></table>,
  }
})

import { NotificationsPage } from './NotificationsPage'

const row = { id: 8, tipo: 'STOCK_BAJO_BOUTIQUE', titulo: 'STOCK SINTETICO QA', mensaje: 'BAJO MINIMO', modulo: 'BOUTIQUE',
  prioridad: 'alta', leida: false, resuelta: false, can_resolve: false, revision: 2,
  tabla_referencia: 'ITEM_BOUTIQUE', id_referencia: 5, fecha: '2026-10-18T12:00:00Z',
  recipient: { full_name: 'QA', role_code: 'ADMIN' } }

async function flush(milliseconds = 0) {
  await act(async () => { await vi.advanceTimersByTimeAsync(milliseconds) })
}

describe('real notifications page state and HTTP integration', () => {
  let requestPermission
  beforeEach(() => {
    vi.useFakeTimers()
    vi.clearAllMocks()
    requestPermission = vi.fn().mockResolvedValue('granted')
    vi.stubGlobal('Notification', { permission: 'default', requestPermission })
    mocks.get.mockImplementation(async (url) => {
      if (url === '/notificaciones/preferencias') return { data: { desktop_enabled: false } }
      if (url === '/users' || url === '/roles') return { data: [] }
      if (url === '/notificaciones/reportes/resumen') return { data: { total: 1, unread: 1, unresolved: 1, urgent_unresolved: 0 } }
      if (url === '/notificaciones' || url === '/notificaciones/supervision') {
        return { data: { items: [row], total: 1, page: 1, page_size: 25 } }
      }
      throw new Error(`Unexpected synthetic endpoint: ${url}`)
    })
    mocks.patch.mockImplementation(async (url, payload) => ({ data: url.endsWith('/preferencias')
      ? { desktop_enabled: payload.desktop_enabled } : { updated: 1 } }))
  })
  afterEach(() => { cleanup(); vi.useRealTimers(); vi.unstubAllGlobals() })

  function mount() {
    return render(<MemoryRouter initialEntries={['/app/notificaciones']}><NotificationsPage /></MemoryRouter>)
  }

  it('consumes the paginated envelope and keeps ADMIN personal on mount', async () => {
    mount()
    await flush()
    expect(screen.getByText('STOCK SINTETICO QA')).toBeTruthy()
    const listCalls = mocks.get.mock.calls.filter(([url]) => url === '/notificaciones')
    expect(listCalls).toHaveLength(1)
    expect(listCalls[0][1].params).toEqual({ page: 1, page_size: 25 })
    expect(mocks.get.mock.calls.some(([url]) => url === '/notificaciones/supervision')).toBe(false)
    expect(mocks.get.mock.calls.some(([url]) => url === '/notificaciones/reportes/resumen')).toBe(false)
    expect(requestPermission).not.toHaveBeenCalled()
    expect(screen.queryByRole('button', { name: 'RESOLVER' })).toBeNull()
  })

  it('offers only personal bulk reads and hides read mutations in supervision', async () => {
    mount()
    await flush()
    fireEvent.click(screen.getByRole('button', { name: 'MARCAR TODAS MIS ALERTAS COMO LEÍDAS' }))
    await flush()
    expect(mocks.patch).toHaveBeenCalledWith('/notificaciones/read-all')
    expect(mocks.get.mock.calls.some(([url]) => url.includes('undefined'))).toBe(false)
    expect(mocks.message.error).not.toHaveBeenCalled()
    fireEvent.change(screen.getByLabelText('Ámbito de notificaciones'), { target: { value: 'supervision' } })
    await flush()
    expect(mocks.get.mock.calls.some(([url]) => url === '/notificaciones/supervision')).toBe(true)
    expect(screen.queryByRole('button', { name: 'LEÍDA' })).toBeNull()
    expect(screen.queryByRole('button', { name: 'MARCAR TODAS MIS ALERTAS COMO LEÍDAS' })).toBeNull()
  })

  it('requests browser permission only after opt-in and saves explicit preference', async () => {
    mount()
    await flush()
    expect(requestPermission).not.toHaveBeenCalled()
    fireEvent.click(screen.getByRole('switch', { name: 'Activar avisos de escritorio' }))
    await flush()
    expect(requestPermission).toHaveBeenCalledOnce()
    expect(mocks.patch).toHaveBeenCalledWith('/notificaciones/preferencias', { desktop_enabled: true })
    expect(screen.getByRole('switch').getAttribute('aria-checked')).toBe('true')
  })

  it('does not enable desktop when browser permission is denied', async () => {
    requestPermission.mockResolvedValue('denied')
    mount()
    await flush()
    fireEvent.click(screen.getByRole('switch'))
    await flush()
    expect(mocks.patch).not.toHaveBeenCalled()
    expect(mocks.message.warning).toHaveBeenCalledOnce()
  })

  it('debounces search and does not reload user/role references per keystroke', async () => {
    mount()
    await flush()
    const input = screen.getByPlaceholderText('BUSCAR TÍTULO, MENSAJE O DESTINATARIA/O')
    fireEvent.change(input, { target: { value: 'S' } })
    fireEvent.change(input, { target: { value: 'ST' } })
    fireEvent.change(input, { target: { value: 'STO' } })
    await flush(299)
    expect(mocks.get.mock.calls.filter(([url]) => url === '/notificaciones')).toHaveLength(1)
    await flush(1)
    const lists = mocks.get.mock.calls.filter(([url]) => url === '/notificaciones')
    expect(lists).toHaveLength(2)
    expect(lists[1][1].params.search).toBe('STO')
    expect(mocks.get.mock.calls.filter(([url]) => url === '/users')).toHaveLength(1)
    expect(mocks.get.mock.calls.filter(([url]) => url === '/roles')).toHaveLength(1)
  })

  it('sends the observed revision and exposes a failed refresh after successful read', async () => {
    mount()
    await flush()
    mocks.get.mockImplementation(async (url) => {
      if (url === '/notificaciones') throw { response: { data: { detail: 'FALLO SINTETICO DE RECARGA' } } }
      return { data: { desktop_enabled: false } }
    })
    fireEvent.click(screen.getByRole('button', { name: 'LEÍDA' }))
    await flush()
    expect(mocks.patch).toHaveBeenCalledWith('/notificaciones/8/read', { revision: 2 })
    expect(mocks.message.success).toHaveBeenCalledOnce()
    expect(screen.getByRole('alert').textContent).toContain('La acción se completó, pero no se pudo recargar la lista')
  })

  it('ignores an old response after a newer filter has finished', async () => {
    const initialImplementation = mocks.get.getMockImplementation()
    let releaseOld
    let oldSignal
    const pending = new Promise((resolve) => { releaseOld = resolve })
    let first = true
    mocks.get.mockImplementation((url, options) => {
      if (url !== '/notificaciones') return initialImplementation(url, options)
      if (first) {
        first = false
        oldSignal = options.signal
        return pending
      }
      return Promise.resolve({ data: { items: [{ ...row, titulo: 'RESULTADO NUEVO' }], total: 1 } })
    })
    mount()
    await flush()
    fireEvent.change(screen.getByPlaceholderText('BUSCAR TÍTULO, MENSAJE O DESTINATARIA/O'), { target: { value: 'NUEVO' } })
    await flush(300)
    expect(screen.getByText('RESULTADO NUEVO')).toBeTruthy()
    expect(oldSignal.aborted).toBe(true)
    releaseOld({ data: { items: [{ ...row, titulo: 'RESULTADO VIEJO' }], total: 1 } })
    await flush()
    expect(screen.queryByText('RESULTADO VIEJO')).toBeNull()
    expect(screen.getByText('RESULTADO NUEVO')).toBeTruthy()
  })
})
