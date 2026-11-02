// @vitest-environment jsdom
/* eslint-disable react/prop-types */
import { act, cleanup, fireEvent, render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

const mocks = vi.hoisted(() => ({
  get: vi.fn(), post: vi.fn(), patch: vi.fn(),
  message: { success: vi.fn(), error: vi.fn(), warning: vi.fn() },
  form: { resetFields: vi.fn(), setFieldsValue: vi.fn(), setFields: vi.fn(), validateFields: vi.fn() },
  values: {},
  user: { role_code: 'ADMIN', permissions: ['economy_expenses:create', 'economy_expenses:annul', 'economy_refunds:create'] },
}))
vi.mock('../../api/client', () => ({ apiClient: { get: mocks.get, post: mocks.post, patch: mocks.patch } }))
vi.mock('../../auth/AuthProvider', () => ({ useAuth: () => ({ user: mocks.user }) }))
vi.mock('@ant-design/icons', () => ({ CloseCircleOutlined: () => null, DollarOutlined: () => null, EyeOutlined: () => null, ReloadOutlined: () => null, SearchOutlined: () => null }))
vi.mock('antd', () => {
  const Box = ({ children }) => <div>{children}</div>
  const Form = ({ children, onFinish }) => <form onSubmit={(event) => { event.preventDefault(); onFinish?.(mocks.values) }}>{children}</form>
  Form.Item = function FormItem({ label, children }) { return <label>{label}{children}</label> }
  Form.useForm = () => [mocks.form]
  const Input = ({ placeholder, value, onChange }) => <input placeholder={placeholder} value={value} onChange={onChange} />
  Input.TextArea = Input
  return {
    App: { useApp: () => ({ message: mocks.message }) },
    Alert: ({ message, description }) => <div role="alert">{message}{description}</div>,
    Button: ({ children, onClick, disabled, loading, htmlType }) => <button type={htmlType || 'button'} onClick={onClick} disabled={disabled || loading}>{children}</button>,
    Card: Box, Col: Box, Row: Box, Tag: Box,
    Typography: { Title: Box, Paragraph: Box, Text: Box },
    Descriptions: Object.assign(Box, { Item: ({ label, children }) => <div>{label}: {children}</div> }),
    Drawer: ({ open, children }) => open ? <section>{children}</section> : null,
    Form, Input, InputNumber: () => <input type="number" />,
    Checkbox: ({ children }) => <label><input type="checkbox" />{children}</label>,
    Select: ({ options, value, onChange, placeholder }) => <select aria-label={placeholder} value={value || ''} onChange={(event) => onChange?.(event.target.value || undefined)}><option value="">{placeholder}</option>{options.map((option) => <option key={option.value} value={option.value}>{option.label}</option>)}</select>,
    Table: ({ dataSource, pagination }) => <div><span>RESULTADOS {pagination.total}</span>{dataSource.map((row) => <div key={row.id}>{row.concepto}</div>)}<button onClick={() => pagination.onChange(pagination.current + 1, pagination.pageSize)}>PÁGINA SIGUIENTE</button></div>,
  }
})
import { EconomyExpensesPage } from './EconomyExpensesPage'
import { RefundReceiptDocument } from './RefundReceiptDocument'

async function flush(milliseconds = 0) {
  await act(async () => { await vi.advanceTimersByTimeAsync(milliseconds) })
}
const row = { id: 1, concepto: 'EGRESO SINTÉTICO' }
const context = { origin_type: 'VENTA_BOUTIQUE', origin_id: 9, source_code: 'QA-9', current_state: 'ACTIVA',
  amount_bob: 100, refunded_amount_bob: 0, refundable_balance_bob: 100, net_collected_bob: 100,
  pending_refund_bob: 0, can_refund: true }

describe('Integración del estado de egresos con los contratos económicos', () => {
  beforeEach(() => {
    vi.useFakeTimers()
    vi.clearAllMocks()
    window.sessionStorage.clear()
    mocks.get.mockImplementation(async (path) => {
      if (path === '/economia/cortes-caja') return { data: { items: [], total: 0 } }
      if (path.includes('refund-context')) return { data: context }
      if (path === '/economia/egresos') return { data: { items: [row], total: 76, total_bob: 900, page: 1, page_size: 25 } }
      throw new Error(`Unexpected synthetic endpoint: ${path}`)
    })
    mocks.post.mockResolvedValue({ data: { expense_id: 7, constancia_id: null } })
    mocks.values = { refund_amount: 25, payment_method: 'qr', reason: 'REEMBOLSO PARCIAL QA', concepto: 'DEVOLUCIÓN QA' }
  })
  afterEach(() => { cleanup(); vi.useRealTimers(); vi.restoreAllMocks() })
  const mount = (path = '/app/economia/egresos') => render(<MemoryRouter initialEntries={[path]}><EconomyExpensesPage /></MemoryRouter>)

  it('consume la página y los agregados completos; pagina en servidor y no recarga referencias al buscar', async () => {
    mount()
    await flush(300)
    expect(screen.getByText('EGRESO SINTÉTICO')).toBeTruthy()
    expect(screen.getByText('RESULTADOS 76')).toBeTruthy()
    expect(screen.getByText(/Total de todos los resultados filtrados: Bs 900.00/)).toBeTruthy()
    fireEvent.click(screen.getByText('PÁGINA SIGUIENTE'))
    await flush(300)
    expect(mocks.get.mock.calls.filter(([path]) => path === '/economia/egresos').at(-1)[1].params.page).toBe(2)
    fireEvent.change(screen.getByPlaceholderText('BUSCAR CONCEPTO, BENEFICIARIO O OBSERVACIÓN'), { target: { value: 'Q' } })
    fireEvent.change(screen.getByPlaceholderText('BUSCAR CONCEPTO, BENEFICIARIO O OBSERVACIÓN'), { target: { value: 'QA' } })
    await flush(299)
    expect(mocks.get.mock.calls.filter(([path]) => path === '/economia/egresos')).toHaveLength(2)
    await flush(1)
    expect(mocks.get.mock.calls.filter(([path]) => path === '/economia/egresos').at(-1)[1].params).toEqual({ page: 1, page_size: 25, search: 'QA' })
    expect(mocks.get.mock.calls.filter(([path]) => path === '/economia/cortes-caja')).toHaveLength(1)
  })

  it('envía devolución financiera con método real y sin cambio de estado operativo', async () => {
    mount('/app/economia/egresos?mode=refund&origin_type=VENTA_BOUTIQUE&origin_id=9&target_status=ANULADA')
    await flush(300)
    expect(screen.queryByText('ESTADO DESTINO DEL ORIGEN')).toBeNull()
    fireEvent.click(screen.getByRole('button', { name: 'REGISTRAR DEVOLUCIÓN' }))
    await flush()
    const [path, body] = mocks.post.mock.calls[0]
    expect(path).toBe('/economia/devoluciones')
    expect(body).toMatchObject({ origin_type: 'VENTA_BOUTIQUE', origin_id: 9, refund_amount: 25, payment_method: 'qr' })
    expect(body).not.toHaveProperty('target_state')
    expect(mocks.post.mock.calls.some(([url]) => url.includes('anulaciones-operativas'))).toBe(false)
  })

  it('respeta el bloqueo de devolución indicado por el servidor', async () => {
    mocks.get.mockImplementation(async (path) => path.includes('refund-context')
      ? { data: { ...context, can_refund: false, refund_block_reason: 'PEDIDO YA ENTREGADO' } }
      : { data: path === '/economia/egresos' ? { items: [], total: 0, total_bob: 0 } : [] })
    mount('/app/economia/egresos?mode=refund&origin_type=VENTA_BOUTIQUE&origin_id=9')
    await flush(300)
    expect(screen.getByText('PEDIDO YA ENTREGADO')).toBeTruthy()
    expect(screen.getByRole('button', { name: 'REGISTRAR DEVOLUCIÓN' }).disabled).toBe(true)
    expect(mocks.post).not.toHaveBeenCalled()
  })

  it('imprime solamente la constancia y escapa texto del snapshot', () => {
    const popup = { opener: {}, document: { write: vi.fn(), close: vi.fn() }, focus: vi.fn(), print: vi.fn() }
    vi.spyOn(window, 'open').mockReturnValue(popup)
    render(<RefundReceiptDocument document={{ id: 7, fecha: '2026-10-18T12:00:00Z', snapshot: { ...context, reason: '<script>alert(1)</script>', responsible: 'QA', amount_bob: '25.00', refundable_balance_bob: '75.00' } }} />)
    fireEvent.click(screen.getByRole('button', { name: 'IMPRIMIR CONSTANCIA' }))
    const html = popup.document.write.mock.calls[0][0]
    expect(html).toContain('&lt;script&gt;alert(1)&lt;/script&gt;')
    expect(html).not.toContain('<script>')
    expect(html).toContain('NO FISCAL')
    expect(popup.print).toHaveBeenCalledOnce()
    expect(popup.opener).toBeNull()
  })
})
