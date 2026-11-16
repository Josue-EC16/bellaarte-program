// @vitest-environment jsdom
/* eslint-disable react/prop-types */
import { act, cleanup, fireEvent, render, screen, within } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

const mocks = vi.hoisted(() => ({
  get: vi.fn(), patch: vi.fn(), post: vi.fn(), reload: vi.fn(), values: {}, setFields: vi.fn(),
  message: { success: vi.fn(), error: vi.fn() },
  user: { permissions: ['exchange_rates:create', 'exchange_rates:update', 'exchange_rates:update_status'] },
}))
vi.mock('../../api/client', () => ({ apiClient: { get: mocks.get, patch: mocks.patch, post: mocks.post } }))
vi.mock('../../auth/AuthProvider', () => ({ useAuth: () => ({ user: mocks.user }) }))
vi.mock('../../components/reports/useListingSummary', () => ({ useListingSummary: () => ({ summary: null, loading: false, reload: mocks.reload }) }))
vi.mock('../../components/reports/ReportSummaryStrip', () => ({ ReportSummaryStrip: () => null }))
vi.mock('../../components/forms/FormProcessAlert', () => ({ FormProcessAlert: ({ message }) => message ? <div role="alert">{message}</div> : null }))
vi.mock('@ant-design/icons', () => ({ EditOutlined: () => null, PlusOutlined: () => null }))
vi.mock('antd', async () => {
  const { cloneElement } = await import('react')
  const Box = ({ children }) => <div>{children}</div>
  const Input = ({ id, onChange }) => <input id={id} onChange={onChange} />
  Input.TextArea = Input
  const Form = ({ children, onFinish }) => <form onSubmit={(event) => { event.preventDefault(); onFinish(mocks.values) }}>{children}</form>
  Form.useForm = () => [{ setFieldsValue: (values) => { mocks.values = { ...values } }, resetFields: () => { mocks.values = {} }, setFields: mocks.setFields }]
  Form.Item = function FormItem({ name, label, children }) {
    return <label htmlFor={name}>{label}{cloneElement(children, { id: name, onChange: (value) => { mocks.values[name] = value?.target ? value.target.value : value } })}</label>
  }
  return {
    App: { useApp: () => ({ message: mocks.message }) },
    Button: ({ children, loading, disabled, onClick, htmlType }) => <button type={htmlType === 'submit' ? 'submit' : 'button'} disabled={disabled || loading} onClick={onClick}>{children}</button>,
    Alert: ({ message }) => <div role="alert">{message}</div>, Row: Box, Col: Box, Space: Box, Tag: Box,
    Typography: { Title: Box, Paragraph: Box, Text: Box },
    Drawer: ({ children, open, maskClosable }) => open ? <div data-testid="drawer" data-mask-closable={String(maskClosable)}>{children}</div> : null,
    Select: ({ id, options, onChange, disabled }) => <select id={id} disabled={disabled} onChange={(event) => onChange?.(Number(event.target.value))}><option value="">Seleccionar</option>{options.map((option) => <option key={option.value} value={option.value}>{option.label}</option>)}</select>,
    Input, Form,
    InputNumber: ({ id, onInput, onChange, stringMode, precision, changeOnBlur }) => <input id={id} data-string-mode={String(stringMode)} data-precision={precision} data-change-on-blur={String(changeOnBlur)} onChange={(event) => { onInput(event.target.value); onChange(event.target.value) }} />,
    Table: ({ columns, dataSource }) => <table><tbody>{dataSource.map((row) => <tr key={row.id}>{columns.map((column) => <td key={column.key || column.dataIndex}>{column.render ? column.render(row[column.dataIndex], row) : row[column.dataIndex]}</td>)}</tr>)}</tbody></table>,
  }
})

import { ExchangeRatesPage } from './ExchangeRatesPage'

const manual = { id: 1, moneda_id: 12, moneda_codigo: 'USD', moneda_nombre: 'DÓLAR MANUAL', valor_bob: '6.9600', origen: 'MANUAL', activo: true, registrado_por: 'ADMIN', fecha_registro: '2026-11-04T12:00:00Z' }
const automatic = { ...manual, id: 2, moneda_nombre: 'DÓLAR AUTOMÁTICO', origen: 'AUTOMATICO', registrado_por: 'SISTEMA' }
const inactive = { ...manual, id: 3, moneda_nombre: 'DÓLAR HISTÓRICO', activo: false }
const bob = { ...manual, id: 4, moneda_id: 1, moneda_codigo: 'BOB', moneda_nombre: 'BOLIVIANO', valor_bob: '1.0000' }
async function flush() { await act(async () => { await Promise.resolve(); await Promise.resolve() }) }
beforeEach(() => {
  vi.clearAllMocks(); mocks.values = {}
  mocks.user.permissions = ['exchange_rates:create', 'exchange_rates:update', 'exchange_rates:update_status']
  mocks.get.mockImplementation(async (url) => {
    if (url === '/monedas') return { data: [{ id: 12, codigo: 'USD', nombre: 'DÓLAR' }] }
    if (url === '/monedas/tipos-cambio') return { data: [manual, automatic, inactive, bob] }
    if (url === '/monedas/tipos-cambio/1') return { data: { ...manual, moneda: { id: 12 }, observaciones: 'REFERENCIA' } }
    throw new Error('Unexpected synthetic request')
  })
  mocks.patch.mockResolvedValue({ data: { ...manual, id: 5 } })
  mocks.post.mockResolvedValue({ data: manual })
  mocks.reload.mockResolvedValue()
})
afterEach(cleanup)

describe('manual rate history controls', () => {
  it('protects automatic/base rates and does not offer reactivation for historical rows', async () => {
    render(<ExchangeRatesPage />); await flush()
    const autoRow = screen.getByText('DÓLAR AUTOMÁTICO').closest('tr')
    const oldRow = screen.getByText('DÓLAR HISTÓRICO').closest('tr')
    const baseRow = screen.getByText('BOLIVIANO').closest('tr')
    expect(within(autoRow).queryByRole('button')).toBeNull()
    expect(within(autoRow).getByText('Solo lectura')).toBeTruthy()
    expect(within(oldRow).queryByText('Desactivar')).toBeNull()
    expect(within(baseRow).queryByText('Desactivar')).toBeNull()
    expect(screen.queryByRole('switch')).toBeNull()
    fireEvent.click(within(screen.getByText('DÓLAR MANUAL').closest('tr')).getByText('Desactivar')); await flush()
    expect(mocks.patch).toHaveBeenCalledWith('/monedas/tipos-cambio/1/status', { activo: false })
  })
  it('creates a positive exact decimal string as an active manual rate', async () => {
    render(<ExchangeRatesPage />); await flush()
    fireEvent.click(screen.getByText('Nuevo tipo de cambio'))
    fireEvent.change(screen.getByLabelText('Moneda'), { target: { value: '12' } })
    const input = screen.getByLabelText('Valor en Bs.')
    expect(input.getAttribute('data-string-mode')).toBe('true')
    expect(input.getAttribute('data-change-on-blur')).toBe('false')
    fireEvent.change(input, { target: { value: '6.9600' } })
    fireEvent.click(screen.getByText('Crear tipo de cambio')); await flush()
    expect(mocks.post).toHaveBeenCalledWith('/monedas/tipos-cambio', { moneda_id: 12, valor_bob: '6.9600', observaciones: null, activo: true })
    expect(mocks.get.mock.calls.filter(([url]) => url.endsWith('/sincronizacion/estado'))).toHaveLength(2)
  })
  it.each(['6.96001', '6USD', 'NaN', '0', ' '])('rejects %s without sending a rounded or cleaned rate', async (value) => {
    render(<ExchangeRatesPage />); await flush()
    fireEvent.click(screen.getByText('Nuevo tipo de cambio'))
    fireEvent.change(screen.getByLabelText('Valor en Bs.'), { target: { value } })
    fireEvent.click(screen.getByText('Crear tipo de cambio')); await flush()
    expect(mocks.post).not.toHaveBeenCalled()
    expect(mocks.setFields).toHaveBeenCalledWith([{ name: 'valor_bob', errors: [expect.stringContaining('cuatro decimales')] }])
  })
  it('gets fresh manual details and explains that a changed value creates another rate', async () => {
    render(<ExchangeRatesPage />); await flush()
    fireEvent.click(within(screen.getByText('DÓLAR MANUAL').closest('tr')).getByText('Editar')); await flush()
    expect(mocks.get).toHaveBeenCalledWith('/monedas/tipos-cambio/1')
    expect(screen.getByTestId('drawer').getAttribute('data-mask-closable')).toBe('false')
    expect(screen.getByText('Cambiar el valor creará una nueva cotización activa. Si conservas el valor, solo se actualizarán las observaciones.')).toBeTruthy()
    fireEvent.change(screen.getByLabelText('Valor en Bs.'), { target: { value: '7.0100' } })
    fireEvent.click(screen.getByText('Guardar cambios')); await flush()
    expect(mocks.patch).toHaveBeenCalledWith('/monedas/tipos-cambio/1', { valor_bob: '7.0100', observaciones: 'REFERENCIA' })
    expect(mocks.message.success).toHaveBeenCalledWith(expect.stringContaining('La cotización anterior se conserva'))
  })
  it('refuses to open editing when the fresh server row is automatic', async () => {
    mocks.get.mockImplementation(async (url) => {
      if (url === '/monedas') return { data: [] }
      if (url === '/monedas/tipos-cambio') return { data: [manual] }
      return { data: { ...automatic, moneda: { id: 12 } } }
    })
    render(<ExchangeRatesPage />); await flush()
    fireEvent.click(screen.getByText('Editar')); await flush()
    expect(screen.queryByTestId('drawer')).toBeNull()
    expect(mocks.message.error).toHaveBeenCalledWith('Las cotizaciones automáticas son de solo lectura.')
  })
})
