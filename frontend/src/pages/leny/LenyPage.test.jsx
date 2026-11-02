// @vitest-environment jsdom
/* eslint-disable react/prop-types */
import { act, cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { MemoryRouter, Route, Routes } from 'react-router-dom'

const mocks = vi.hoisted(() => ({ get: vi.fn(), post: vi.fn(), delete: vi.fn(), send: vi.fn(), confirm: vi.fn(), permissions: ['leny:chat'], userId: 71 }))
vi.mock('../../api/client', () => ({ apiClient: { get: mocks.get, post: mocks.post, delete: mocks.delete } }))
vi.mock('../../auth/AuthProvider', () => ({ useAuth: () => ({ user: { id: mocks.userId, permissions: mocks.permissions } }) }))
vi.mock('./lenyTransport', async (importOriginal) => ({ ...(await importOriginal()), sendLenyMessage: (...args) => mocks.send(...args) }))
vi.mock('@ant-design/icons', () => ({ DeleteOutlined: () => null, PlusOutlined: () => null, ReloadOutlined: () => null,
  SendOutlined: () => null, SettingOutlined: () => null, StopOutlined: () => null }))
vi.mock('antd', () => ({
  App: { useApp: () => ({ modal: { confirm: mocks.confirm } }) },
  Button: ({ children, onClick, disabled, htmlType, 'aria-label': label }) => <button type={htmlType || 'button'} aria-label={label} disabled={disabled} onClick={onClick}>{children}</button>,
  Input: { TextArea: ({ autoSize, ...props }) => <textarea data-auto-size={Boolean(autoSize)} {...props} /> },
  Alert: ({ message, description }) => <div role="alert"><span>{message}</span>{description && <span>{description}</span>}</div>, Tag: ({ children }) => <span>{children}</span>,
  Spin: () => <span>Cargando</span>, Pagination: () => null,
  Drawer: ({ open, children }) => open ? <div>{children}</div> : null,
  Descriptions: () => null, Typography: { Paragraph: ({ children }) => <p>{children}</p> },
}))

import { LenyPage } from './LenyPage'
import { LenyMarkdown } from './LenyMarkdown'
import { PermissionRoute } from '../../routes/RouteGuards'

const conversation = { id: 'conversation-1', title: 'Conversación privada', created_at: '2026-10-19T12:00:00Z' }
let persisted
beforeEach(() => {
  vi.clearAllMocks(); mocks.permissions = ['leny:chat']; mocks.userId = 71; persisted = []
  mocks.get.mockImplementation(async (path) => {
    if (path === '/leny/status') return { data: { available: true, max_message_chars: 2000, request_timeout_seconds: 120 } }
    if (path === '/leny/conversations') return { data: { items: persisted.length ? [conversation] : [], total: persisted.length ? 1 : 0 } }
    if (path.endsWith('/conversation-1')) return { data: { conversation, items: persisted, total: persisted.length } }
    throw new Error('Unexpected endpoint')
  })
  mocks.post.mockResolvedValue({ data: conversation })
  mocks.send.mockImplementation(async (payload, { onEvent }) => {
    onEvent({ type: 'start' }); onEvent({ type: 'delta', text: 'Hola, soy LENY.' })
    persisted = [{ id: 'u', role: 'user', content: payload.message, status: 'completed' },
      { id: 'a', role: 'assistant', content: 'Hola, soy LENY.', status: 'completed' }]
    onEvent({ type: 'done', status: 'completed' })
  })
})
afterEach(cleanup)

describe('LENY integrated page', () => {
  it('renders local-service status, sends through the streaming transport and reconciles persisted messages', async () => {
    render(<LenyPage />)
    await screen.findByText('Modelo local disponible')
    expect(screen.queryByLabelText('Administración de LENY')).toBeNull()
    fireEvent.change(screen.getByLabelText('Mensaje para LENY'), { target: { value: 'Hola LENY' } })
    fireEvent.click(screen.getByText('Enviar'))
    await screen.findByText('Hola, soy LENY.')
    await waitFor(() => expect(mocks.get).toHaveBeenCalledWith('/leny/conversations/conversation-1', expect.anything()))
    expect(mocks.send.mock.calls[0][0]).toMatchObject({ conversation_id: 'conversation-1', message: 'Hola LENY', request_id: expect.any(String) })
    expect(mocks.send).toHaveBeenCalledOnce()
    fireEvent.click(screen.getByText('Nueva conversación'))
    expect(screen.queryByLabelText('Respuesta de LENY')).toBeNull()
  })
  it('shows loading and cancels an active generation', async () => {
    mocks.send.mockImplementation((payload, { signal }) => new Promise((resolve) => signal.addEventListener('abort', resolve, { once: true })))
    render(<LenyPage />)
    await screen.findByText('Modelo local disponible')
    fireEvent.change(screen.getByLabelText('Mensaje para LENY'), { target: { value: 'Ayuda' } })
    fireEvent.click(screen.getByText('Enviar'))
    await screen.findByText('Detener')
    await waitFor(() => expect(mocks.send).toHaveBeenCalledOnce())
    await act(async () => fireEvent.click(screen.getByText('Detener')))
    await screen.findByText('Enviar')
    expect(mocks.send.mock.calls[0][1].signal.aborted).toBe(true)
  })
  it('shows safe errors and never automatically resends a failed request', async () => {
    mocks.send.mockRejectedValue(new Error('Modelo local no disponible'))
    render(<LenyPage />)
    await screen.findByText('Modelo local disponible')
    fireEvent.change(screen.getByLabelText('Mensaje para LENY'), { target: { value: 'Ayuda' } })
    fireEvent.click(screen.getByText('Enviar'))
    await screen.findByText('No se pudo comunicar con LENY. Intenta nuevamente.')
    expect(mocks.send).toHaveBeenCalledOnce()
    expect(screen.getByLabelText('Mensaje para LENY').value).toBe('Ayuda')
  })
  it('disables send when the local service is unavailable', async () => {
    mocks.get.mockRejectedValue(new Error('Offline'))
    render(<LenyPage />)
    await screen.findByText('Sin conexión al modelo')
    fireEvent.change(screen.getByLabelText('Mensaje para LENY'), { target: { value: 'Hola' } })
    expect(screen.getByText('Enviar').disabled).toBe(true)
  })
  it('keeps escaped documentary conditions visible as text without interpreting their markup', () => {
    const { container } = render(<LenyMarkdown>{'> \\<\\!-- No entregar sin aprobación. --\\> \\[Entrega\\](https://example.invalid). [S1]'}</LenyMarkdown>)
    expect(container.textContent).toContain('<!-- No entregar sin aprobación. -->')
    expect(container.querySelector('a')).toBeNull()
    expect(container.querySelector('script')).toBeNull()
  })
  it('renders Markdown while removing HTML, images and active links', () => {
    const { container } = render(<LenyMarkdown>{'**Texto claro** [enlace](https://example.com) ![imagen](https://example.com/x.png) <script>alert(1)</script>'}</LenyMarkdown>)
    expect(container.querySelector('strong').textContent).toBe('Texto claro')
    expect(container.querySelector('a, img, script')).toBeNull()
  })
  it('denies the LENY route when the real permission guard has no leny:chat permission', async () => {
    mocks.permissions = []
    render(<MemoryRouter initialEntries={['/app/leny']}><Routes>
      <Route element={<PermissionRoute permission="leny:chat" />}><Route path="/app/leny" element={<LenyPage />} /></Route>
      <Route path="/403" element={<div>Acceso denegado</div>} />
    </Routes></MemoryRouter>)
    await screen.findByText('Acceso denegado')
    expect(mocks.get).not.toHaveBeenCalled()
  })
  it('reconciles a duplicate request without automatic retries', async () => {
    mocks.send.mockImplementation(async (payload) => {
      persisted = [{ id: 'saved', role: 'assistant', content: 'Respuesta parcial guardada', status: 'interrupted', request_id: payload.request_id }]
      throw { response: { status: 409, data: { detail: { code: 'LENY_REQUEST_DUPLICATE', status: 'interrupted' } } } }
    })
    render(<LenyPage />)
    await screen.findByText('Modelo local disponible')
    fireEvent.change(screen.getByLabelText('Mensaje para LENY'), { target: { value: 'Hola otra vez' } })
    fireEvent.click(screen.getByText('Enviar'))
    await screen.findByText(/Esta solicitud ya fue recibida/)
    await screen.findByText('Respuesta parcial guardada')
    await waitFor(() => expect(mocks.get).toHaveBeenCalledWith('/leny/conversations/conversation-1', expect.anything()))
    expect(mocks.send).toHaveBeenCalledOnce()
  })
  it('clears private messages and draft when the authenticated account changes', async () => {
    const { rerender } = render(<LenyPage />)
    await screen.findByText('Modelo local disponible')
    fireEvent.change(screen.getByLabelText('Mensaje para LENY'), { target: { value: 'Borrador de la cuenta anterior' } })
    mocks.userId = 72
    rerender(<LenyPage />)
    await screen.findByText('Modelo local disponible')
    expect(screen.getByLabelText('Mensaje para LENY').value).toBe('')
    expect(screen.queryByLabelText('Tu mensaje')).toBeNull()
  })
  it('places backend message422 inline, restores the draft and removes rejected optimistic messages', async () => {
    mocks.send.mockRejectedValue({ response: { status: 422, data: { detail: [{ loc: ['body', 'message'], msg: 'Escribe un mensaje válido.', type: 'value_error' }] } } })
    render(<LenyPage />)
    await screen.findByText('Modelo local disponible')
    fireEvent.change(screen.getByLabelText('Mensaje para LENY'), { target: { value: 'Mensaje rechazado' } })
    fireEvent.click(screen.getByText('Enviar'))
    await screen.findByText('Escribe un mensaje válido.')
    await waitFor(() => expect(screen.getByLabelText('Mensaje para LENY').value).toBe('Mensaje rechazado'))
    expect(screen.getByLabelText('Mensaje para LENY').getAttribute('aria-invalid')).toBe('true')
    expect(screen.getByLabelText('Mensaje para LENY').getAttribute('aria-describedby')).toBe('leny-message-error')
    expect(screen.queryByLabelText('Tu mensaje')).toBeNull()
    expect(screen.queryByLabelText('Respuesta de LENY')).toBeNull()
    fireEvent.change(screen.getByLabelText('Mensaje para LENY'), { target: { value: 'Mensaje corregido' } })
    expect(screen.getByLabelText('Mensaje para LENY').getAttribute('aria-invalid')).toBe('false')
    expect(mocks.send).toHaveBeenCalledOnce()
  })
  it('polls an aborted generation until its persisted interrupted state is confirmed', async () => {
    let polls = 0
    const get = mocks.get.getMockImplementation()
    mocks.get.mockImplementation(async (path, ...args) => {
      if (path.endsWith('/conversation-1')) {
        polls += 1
        if (polls >= 2) persisted = persisted.map((item) => item.role === 'assistant' ? { ...item, status: 'interrupted' } : item)
      }
      return get(path, ...args)
    })
    mocks.send.mockImplementation((payload, { signal }) => {
      persisted = [{ id: 'partial', role: 'assistant', content: 'Texto parcial', status: 'generating', request_id: payload.request_id }]
      return new Promise((resolve, reject) => signal.addEventListener('abort', () => reject(new DOMException('Cancelled', 'AbortError')), { once: true }))
    })
    render(<LenyPage />)
    await screen.findByText('Modelo local disponible')
    fireEvent.change(screen.getByLabelText('Mensaje para LENY'), { target: { value: 'Genera una respuesta' } })
    fireEvent.click(screen.getByText('Enviar'))
    await waitFor(() => expect(mocks.send).toHaveBeenCalledOnce())
    fireEvent.click(screen.getByText('Detener'))
    await screen.findByText('Respuesta interrumpida')
    await screen.findByText('Enviar')
    expect(polls).toBe(2)
    expect(screen.queryByText('Preparando respuesta…')).toBeNull()
    expect(mocks.send).toHaveBeenCalledOnce()
  })
  it('shows interruption pending after bounded reconciliation when server cleanup is still running', async () => {
    mocks.send.mockImplementation((payload, { signal }) => {
      persisted = [{ id: 'pending', role: 'assistant', content: '', status: 'generating', request_id: payload.request_id }]
      return new Promise((resolve, reject) => signal.addEventListener('abort', () => reject(new DOMException('Cancelled', 'AbortError')), { once: true }))
    })
    render(<LenyPage />)
    await screen.findByText('Modelo local disponible')
    fireEvent.change(screen.getByLabelText('Mensaje para LENY'), { target: { value: 'Genera una respuesta' } })
    fireEvent.click(screen.getByText('Enviar'))
    await waitFor(() => expect(mocks.send).toHaveBeenCalledOnce())
    fireEvent.click(screen.getByText('Detener'))
    await screen.findByText('Enviar')
    expect(screen.getByText('Interrupción pendiente')).toBeTruthy()
    expect(screen.queryByText('Preparando respuesta…')).toBeNull()
    expect(mocks.get.mock.calls.filter(([path]) => path.endsWith('/conversation-1'))).toHaveLength(5)
    expect(mocks.send).toHaveBeenCalledOnce()
  })
  it('blocks sends for the account quota Retry-After and unlocks without automatically retrying', async () => {
    mocks.send.mockRejectedValue({ response: { status: 429, headers: { 'retry-after': '1' }, data: { detail: { code: 'LENY_RATE_LIMITED', message: 'SQL SECRET /internal' } } } })
    render(<LenyPage />)
    await screen.findByText('Modelo local disponible')
    fireEvent.change(screen.getByLabelText('Mensaje para LENY'), { target: { value: 'Organiza la jornada del Taller' } })
    fireEvent.click(screen.getByText('Enviar'))
    await screen.findByText(/Alcanzaste el límite de uso/)
    expect(screen.getByText('Espera 1 s').disabled).toBe(true)
    fireEvent.keyDown(screen.getByLabelText('Mensaje para LENY'), { key: 'Enter' })
    expect(mocks.send).toHaveBeenCalledOnce()
    await waitFor(() => expect(screen.getByText('Enviar').disabled).toBe(false), { timeout: 2000 })
    expect(screen.queryByText(/SQL SECRET/)).toBeNull()
    expect(screen.queryByLabelText('Tu mensaje')).toBeNull()
    expect(mocks.send).toHaveBeenCalledOnce()
  })
  it('distinguishes the global busy response from the account quota', async () => {
    mocks.send.mockRejectedValue({ response: { status: 429, headers: { 'retry-after': '3' }, data: { detail: { code: 'LENY_BUSY' } } } })
    render(<LenyPage />)
    await screen.findByText('Modelo local disponible')
    fireEvent.change(screen.getByLabelText('Mensaje para LENY'), { target: { value: 'Redacta una bienvenida' } })
    fireEvent.click(screen.getByText('Enviar'))
    await screen.findByText(/LENY está atendiendo otra solicitud/)
    expect(screen.getByText('Espera 3 s').disabled).toBe(true)
    expect(screen.queryByText(/Alcanzaste el límite de uso/)).toBeNull()
    expect(mocks.send).toHaveBeenCalledOnce()
  })
  it.each(['refused', 'clarification'])('renders a policy %s as a completed assistant response, without process errors', async (outcome) => {
    mocks.send.mockImplementation(async (payload, { onEvent }) => {
      const text = 'Puedo ayudarte con tareas de BELLAARTE BOUTIQUE. No tengo acceso a datos privados del ERP.'
      onEvent({ type: 'start' }); onEvent({ type: 'delta', text })
      persisted = [{ id: 'refusal', role: 'assistant', content: text, status: 'completed', category: outcome, reason_code: 'PRIVATE_DATA', context_eligible: false, request_id: payload.request_id }]
      onEvent({ type: 'done', status: 'completed', outcome, reason_code: 'PRIVATE_DATA' })
    })
    render(<LenyPage />)
    await screen.findByText('Modelo local disponible')
    fireEvent.change(screen.getByLabelText('Mensaje para LENY'), { target: { value: 'Dame las contraseñas de otras cuentas' } })
    fireEvent.click(screen.getByText('Enviar'))
    await screen.findByText(/No tengo acceso a datos privados del ERP/)
    await screen.findByText('Enviar')
    expect(screen.queryByRole('alert')).toBeNull()
    expect(screen.queryByText('Respuesta incompleta')).toBeNull()
  })
  it.each(['failed', 'interrupted', 'admitted'])('removes phantom rows for a ledger-only %s duplicate and requires a new request', async (status) => {
    mocks.send.mockRejectedValue({ response: { status: 409, data: { detail: { code: 'LENY_REQUEST_DUPLICATE', status } } } })
    render(<LenyPage />)
    await screen.findByText('Modelo local disponible')
    fireEvent.change(screen.getByLabelText('Mensaje para LENY'), { target: { value: 'Mensaje sin persistencia anterior' } })
    fireEvent.click(screen.getByText('Enviar'))
    await screen.findByText(/no tiene mensajes guardados/)
    expect(screen.queryByLabelText('Tu mensaje')).toBeNull()
    expect(screen.queryByLabelText('Respuesta de LENY')).toBeNull()
    expect(mocks.send).toHaveBeenCalledOnce()
  })
  it('keeps dangerous Markdown URLs and HTML inert', () => {
    const { container } = render(<LenyMarkdown>{'[clic](javascript:alert(1)) ![x](data:image/svg+xml,test) <img src=x onerror=alert(1)> <iframe src="https://evil.invalid"></iframe>'}</LenyMarkdown>)
    expect(container.querySelector('a,img,iframe,script,[onclick],[onerror]')).toBeNull()
  })
})
