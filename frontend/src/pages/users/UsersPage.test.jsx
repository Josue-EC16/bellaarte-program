// @vitest-environment jsdom
/* eslint-disable react/prop-types */
import { act, cleanup, fireEvent, render, screen, within } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

const mocks = vi.hoisted(() => ({
  get: vi.fn(), post: vi.fn(), patch: vi.fn(), clearSession: vi.fn(), setFieldsValue: vi.fn(),
  message: { success: vi.fn(), error: vi.fn() }, modal: { confirm: vi.fn() },
  user: { id: 1, permissions: ['users:list', 'users:view', 'users:create', 'users:update', 'users:update_status', 'users:reset_password', 'roles:update'] },
}))
vi.mock('../../api/client', () => ({ apiClient: { get: mocks.get, post: mocks.post, patch: mocks.patch } }))
vi.mock('../../auth/AuthProvider', () => ({ useAuth: () => ({ user: mocks.user, clearSession: mocks.clearSession }) }))
vi.mock('@ant-design/icons', () => ({ EditOutlined: () => null, KeyOutlined: () => null, PlusOutlined: () => null, EyeOutlined: () => null }))
vi.mock('antd', async () => {
  const { cloneElement } = await import('react')
  const Box = ({ children }) => <div>{children}</div>
  const Input = ({ placeholder, id }) => <input placeholder={placeholder} id={id} />
  Input.TextArea = Input
  const Form = ({ children }) => <form>{children}</form>
  Form.useForm = () => [{ setFieldsValue: mocks.setFieldsValue, resetFields: () => {} }]
  Form.Item = function FormItem({ children, name, label }) { return <label htmlFor={name}>{label}{cloneElement(children, { id: name })}</label> }
  return {
    App: { useApp: () => ({ message: mocks.message, modal: mocks.modal }) },
    Button: ({ children, disabled, loading, onClick }) => <button type="button" disabled={disabled || loading} onClick={onClick}>{children}</button>,
    Alert: ({ message }) => <div role="alert">{message}</div>, Col: Box, Row: Box, Space: Box, Tag: Box,
    Typography: { Title: Box, Paragraph: Box, Text: Box },
    Drawer: ({ open, children, maskClosable }) => open ? <div data-testid="drawer" data-mask-closable={String(maskClosable)}>{children}</div> : null,
    Modal: ({ open, children }) => open ? <div>{children}</div> : null,
    Descriptions: Object.assign(Box, { Item: Box }), Input, Form,
    Select: ({ options, disabled, id }) => <select id={id} disabled={disabled}>{options.map((option) => <option key={option.value} value={option.value}>{option.label}</option>)}</select>,
    Switch: ({ checked, disabled, loading, onChange, 'aria-label': label, id }) => <button type="button" role="switch" id={id} aria-label={label} aria-checked={checked} disabled={disabled || loading} onClick={() => onChange?.(!checked)}>ESTADO</button>,
    Table: ({ columns, dataSource }) => <table><tbody>{dataSource.map((row) => <tr key={row.id}>{columns.map((column) => <td key={column.key || column.dataIndex}>{column.render ? column.render(row[column.dataIndex], row) : row[column.dataIndex]}</td>)}</tr>)}</tbody></table>,
  }
})

import { UsersPage } from './UsersPage'
import { RolesPage } from '../roles/RolesPage'
import { clearAccessToken, setAccessToken } from '../../api/tokenStore'
const own = { id: 1, user_id: 31, full_name: 'ANA PÉREZ', username: 'AP1234567', role_code: 'ADMIN', role_name: 'ADMIN', account_is_active: true, user_is_active: true, ci: '1234567' }
const other = { ...own, id: 2, user_id: 32, full_name: 'MARÍA LÓPEZ', username: 'ML1234568', ci: '1234568' }
async function flush() { await act(async () => { await Promise.resolve(); await Promise.resolve() }) }
beforeEach(() => {
  vi.clearAllMocks()
  mocks.get.mockImplementation(async (url) => {
    if (url === '/users') return { data: [own, other] }
    if (url === '/roles') return { data: [{ id: 5, codigo: 'ADMIN', nombre: 'ADMIN', activo: true }] }
    if (url === '/roles/5') return { data: { id: 5, codigo: 'ADMIN', nombre: 'ADMIN ACTUALIZADO', activo: true, descripcion: 'NUEVO' } }
    if (url === '/users/31') return { data: { ...own, nombres: 'ANA', apellido_paterno: 'PÉREZ', zona: 'CENTRO', correo: 'qa@gmail.com' } }
    throw new Error('Unexpected synthetic request')
  })
  mocks.patch.mockResolvedValue({ data: {} }); mocks.post.mockResolvedValue({ data: {} })
})
afterEach(() => { cleanup(); clearAccessToken() })

describe('collaborator safety controls', () => {
  it('disables its own status switch while allowing another ADMIN account', async () => {
    render(<UsersPage />); await flush()
    const ownRow = screen.getByText(own.username).closest('tr')
    const otherRow = screen.getByText(other.username).closest('tr')
    expect(within(ownRow).getByRole('switch').disabled).toBe(true)
    expect(within(otherRow).getByRole('switch').disabled).toBe(false)
    fireEvent.click(within(ownRow).getByRole('switch'))
    expect(mocks.patch).not.toHaveBeenCalled()
    fireEvent.click(within(otherRow).getByRole('switch')); await flush()
    expect(mocks.patch).toHaveBeenCalledWith('/users/2/status', { is_active: false })
  })
  it('loads fresh details and prevents self role or status changes in the edit drawer', async () => {
    render(<UsersPage />); await flush()
    fireEvent.click(within(screen.getByText(own.username).closest('tr')).getByText('Editar')); await flush()
    expect(mocks.get).toHaveBeenCalledWith('/users/31')
    expect(screen.getByLabelText('Rol').disabled).toBe(true)
    expect(screen.getByLabelText('Usuario activo').disabled).toBe(true)
    expect(screen.getByLabelText('Cuenta activa').disabled).toBe(true)
    expect(screen.getByTestId('drawer').getAttribute('data-mask-closable')).toBe('false')
  })
  it('allows explicit autoreset, sends no credential and clears its session after success', async () => {
    render(<UsersPage />); await flush()
    fireEvent.click(within(screen.getByText(own.username).closest('tr')).getByText('Reset clave'))
    const confirmation = mocks.modal.confirm.mock.calls[0][0]
    expect(confirmation.content).toContain('inicial del nombre')
    expect(confirmation.content).toContain('Se cerrarán todas las sesiones')
    await act(async () => confirmation.onOk())
    expect(mocks.post).toHaveBeenCalledWith('/users/1/reset-password', {}, { _sessionControl: true })
    expect(mocks.clearSession).toHaveBeenCalledOnce()
  })
  it('loads the current role detail before editing instead of using the summary row', async () => {
    render(<RolesPage />); await flush()
    fireEvent.click(screen.getByText('Editar')); await flush()
    expect(mocks.get).toHaveBeenCalledWith('/roles/5')
    expect(mocks.setFieldsValue).toHaveBeenCalledWith({ nombre: 'ADMIN ACTUALIZADO', descripcion: 'NUEVO' })
  })
  it('does not close a new session when an old autoreset confirmation finishes late', async () => {
    let finishReset
    mocks.post.mockImplementation(() => new Promise((resolve) => { finishReset = resolve }))
    render(<UsersPage />); await flush()
    fireEvent.click(within(screen.getByText(own.username).closest('tr')).getByText('Reset clave'))
    const confirmation = mocks.modal.confirm.mock.calls[0][0]
    const pending = confirmation.onOk()
    clearAccessToken(); setAccessToken('new-session')
    await act(async () => { finishReset({ data: {} }); await pending })
    expect(mocks.clearSession).not.toHaveBeenCalled()
    expect(mocks.message.success).not.toHaveBeenCalled()
    expect(mocks.get.mock.calls.filter(([url]) => url === '/users')).toHaveLength(1)
  })
})
