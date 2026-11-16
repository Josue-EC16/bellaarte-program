// @vitest-environment jsdom
/* eslint-disable react/prop-types */
import { act, cleanup, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
const mocks = vi.hoisted(() => ({ contextualizations: vi.fn(), ragStatus: vi.fn(), contextualization: vi.fn(), contextualize: vi.fn(), cancelContextualization: vi.fn() }))
vi.mock('../../../api/lenyDocuments', () => ({ lenyDocumentsApi: mocks }))
vi.mock('antd', () => {
  const Container = ({ children }) => <div>{children}</div>
  const List = Object.assign(({ dataSource, renderItem }) => <div>{dataSource.map(renderItem)}</div>, { Item: Container })
  return {
    Alert: ({ message, description }) => <div role="alert">{message}{description}</div>,
    Button: ({ children, disabled, loading, onClick }) => <button disabled={disabled || loading} onClick={onClick}>{children}</button>,
    Card: ({ title, extra, children }) => <section>{title}{extra}{children}</section>,
    Descriptions: ({ items }) => <dl>{items.map((item) => <div key={item.key}><dt>{item.label}</dt><dd>{item.children}</dd></div>)}</dl>,
    List, Pagination: ({ onChange }) => <button onClick={() => onChange(2)}>Historial siguiente</button>, Space: Container, Spin: () => <span>Cargando</span>, Tag: Container,
    Typography: { Title: Container, Paragraph: Container, Text: Container },
  }
})
import { ContextualizationPanel } from './ContextualizationPanel'
import { contextualizationCounters, contextualizationStatus } from './contextualizationUtils'

const queued = { id: 'job-1', status: 'queued', stage: 'queued', progress: {}, attempts: 0 }
const version = { id: 'version-1', version_number: 2, status: 'pending_contextualization' }
const props = { documentId: 'document-1', version, onClose: vi.fn(), onChange: vi.fn() }
async function settle() { await act(async () => { await Promise.resolve(); await Promise.resolve() }) }

beforeEach(() => {
  vi.clearAllMocks(); vi.useFakeTimers()
  vi.spyOn(document, 'visibilityState', 'get').mockReturnValue('visible')
  vi.stubGlobal('crypto', { randomUUID: vi.fn().mockReturnValueOnce('request-1').mockReturnValueOnce('request-2') })
  mocks.contextualizations.mockResolvedValue({ items: [], total: 0 })
  mocks.ragStatus.mockResolvedValue({ enabled: true, ready: true, worker_available: true, model: 'qwen3-embedding:0.6b', dimension: 1024, cpu_only: true })
  mocks.contextualize.mockResolvedValue(queued)
  mocks.contextualization.mockResolvedValue({ ...queued, status: 'running', stage: 'embedding', progress: { chunks_total: 8, chunks_done: 2 } })
})
afterEach(() => { cleanup(); vi.restoreAllMocks(); vi.unstubAllGlobals(); vi.useRealTimers() })

describe('Durable contextualization tracking', () => {
  it('admits a version using server-owned configuration and an idempotency identifier', async () => {
    render(<ContextualizationPanel {...props} />); await settle()
    fireEvent.click(screen.getByText('Contextualizar versión')); await settle()
    expect(mocks.contextualize).toHaveBeenCalledWith('document-1', 'version-1', { request_id: 'request-1', action: 'contextualize' }, expect.anything())
    expect(screen.getByText('En espera del procesador')).toBeTruthy()
    expect(screen.queryByText('Contextualizar versión')).toBeNull()
    expect(screen.getByText(/revisión y aprobación ADMIN independiente/)).toBeTruthy()
  })
  it('retains the same request_id after uncertain communication instead of duplicating work', async () => {
    mocks.contextualize.mockRejectedValueOnce(new Error('private internal path'))
    render(<ContextualizationPanel {...props} />); await settle()
    fireEvent.click(screen.getByText('Contextualizar versión')); await settle()
    expect(screen.queryByText(/private internal/)).toBeNull()
    fireEvent.click(screen.getByText('Contextualizar versión')); await settle()
    expect(mocks.contextualize.mock.calls[0][2]).toEqual(mocks.contextualize.mock.calls[1][2])
  })
  it('requires explicit confirmation before replacing a validated index', async () => {
    render(<ContextualizationPanel {...props} version={{ ...version, status: 'pending_publication', validated_indexation_id: 'previous-index' }} />); await settle()
    fireEvent.click(screen.getByText('Contextualizar de nuevo'))
    expect(mocks.contextualize).not.toHaveBeenCalled()
    expect(screen.getByText(/El índice validado anterior se conservará/)).toBeTruthy()
    fireEvent.click(screen.getByRole('button', { name: 'Confirmar nueva contextualización' })); await settle()
    expect(mocks.contextualize.mock.calls[0][2]).toMatchObject({ action: 'recontextualize' })
  })
  it('retries a failed work item with a fresh request linked to that item', async () => {
    mocks.contextualizations.mockResolvedValue({ items: [{ ...queued, status: 'failed', safe_message: 'No se encontró texto utilizable.' }], total: 1 })
    render(<ContextualizationPanel {...props} />); await settle()
    expect(screen.getByText('No se encontró texto utilizable.')).toBeTruthy()
    fireEvent.click(screen.getByText('Reintentar trabajo')); await settle()
    expect(mocks.contextualize.mock.calls[0][2]).toEqual({ request_id: 'request-1', action: 'retry', retry_of: 'job-1' })
  })
  it('polls actual counters every two seconds and stops on completion', async () => {
    mocks.contextualizations.mockResolvedValueOnce({ items: [queued], total: 1 }).mockResolvedValue({ items: [{ ...queued, status: 'completed', stage: 'completed' }], total: 1 })
    mocks.contextualization.mockResolvedValueOnce({ ...queued, status: 'running', stage: 'embedding', progress: { chunks_total: 8, chunks_done: 2 } })
      .mockResolvedValueOnce({ ...queued, status: 'completed', stage: 'completed', progress: { chunks_total: 8, chunks_done: 8 } })
    render(<ContextualizationPanel {...props} />); await settle()
    await act(async () => { await vi.advanceTimersByTimeAsync(2000) })
    expect(screen.getByText('2 de 8')).toBeTruthy()
    expect(screen.queryByText(/%/)).toBeNull()
    await act(async () => { await vi.advanceTimersByTimeAsync(2000) })
    expect(screen.getByText(/Indexación verificada/)).toBeTruthy()
    expect(props.onChange).toHaveBeenCalledOnce()
    await act(async () => { await vi.advanceTimersByTimeAsync(10000) })
    expect(mocks.contextualization).toHaveBeenCalledTimes(2)
  })
  it('aborts in-flight observation on hide/unmount and resumes only when visible', async () => {
    mocks.contextualizations.mockResolvedValue({ items: [queued], total: 1 })
    mocks.contextualization.mockReturnValue(new Promise(() => {}))
    const { unmount } = render(<ContextualizationPanel {...props} />); await settle()
    await act(async () => { await vi.advanceTimersByTimeAsync(2000) })
    const firstSignal = mocks.contextualization.mock.calls[0][1]
    vi.spyOn(document, 'visibilityState', 'get').mockReturnValue('hidden')
    fireEvent(document, new Event('visibilitychange')); await settle()
    expect(firstSignal.aborted).toBe(true)
    await act(async () => { await vi.advanceTimersByTimeAsync(8000) })
    expect(mocks.contextualization).toHaveBeenCalledOnce()
    vi.spyOn(document, 'visibilityState', 'get').mockReturnValue('visible')
    fireEvent(document, new Event('visibilitychange')); await settle()
    await act(async () => { await vi.advanceTimersByTimeAsync(2000) })
    expect(mocks.contextualization).toHaveBeenCalledTimes(2)
    const lastSignal = mocks.contextualization.mock.calls[1][1]
    unmount(); expect(lastSignal.aborted).toBe(true)
    expect(mocks.cancelContextualization).not.toHaveBeenCalled()
  })
  it('requests cancellation explicitly and waits for safe completion', async () => {
    mocks.contextualizations.mockResolvedValue({ items: [queued], total: 1 })
    mocks.cancelContextualization.mockResolvedValue({ ...queued, cancel_requested: true })
    render(<ContextualizationPanel {...props} />); await settle()
    fireEvent.click(screen.getByText('Cancelar procesamiento')); await settle()
    expect(mocks.cancelContextualization).toHaveBeenCalledWith('job-1', expect.anything())
    expect(screen.getByText(/Cancelación solicitada/)).toBeTruthy()
    expect(screen.getByText('Cancelar procesamiento').disabled).toBe(true)
  })
  it('shows safe rate limiting and permits recovery without leaking exception details', async () => {
    mocks.contextualize.mockRejectedValue({ response: { status: 429, headers: { 'retry-after': '12' }, data: { detail: 'secret/path' } } })
    render(<ContextualizationPanel {...props} />); await settle()
    fireEvent.click(screen.getByText('Contextualizar versión')); await settle()
    expect(screen.getByText(/Reintenta en 12 segundos/)).toBeTruthy()
    expect(screen.queryByText(/secret/)).toBeNull()
    expect(screen.getByText('Actualizar procesamiento').disabled).toBe(false)
  })
  it.each([401, 403, 503])('handles HTTP %s safely during readiness loading', async (status) => {
    mocks.ragStatus.mockRejectedValue({ response: { status, data: { detail: 'jwt-or-internal-path' } } })
    render(<ContextualizationPanel {...props} />); await settle()
    expect(screen.getByText('Contextualizar versión').disabled).toBe(true)
    expect(screen.queryByText(/jwt-or-internal/)).toBeNull()
    expect(screen.getAllByRole('alert').length).toBeGreaterThan(1)
  })
  it('disables admission for unavailable dependencies and keeps history paginated', async () => {
    mocks.ragStatus.mockResolvedValue({ ready: false, worker_available: false, model: 'qwen3-embedding:0.6b' })
    render(<ContextualizationPanel {...props} />); await settle()
    expect(screen.getByText('Contextualizar versión').disabled).toBe(true)
    fireEvent.click(screen.getByText('Historial siguiente')); await settle()
    expect(mocks.contextualizations).toHaveBeenLastCalledWith('document-1', 'version-1', { page: 2, page_size: 5 }, expect.anything())
  })
})

it('does not invent progress when units are unknown and labels actual version states', () => {
  expect(contextualizationCounters({ pages_done: 2, chunks_total: 0, chunks_done: 0 })).toEqual([])
  expect(contextualizationCounters({ chunks_total: 4, chunks_done: 9 })).toEqual([{ key: 'chunks', label: 'Fragmentos', total: 4, done: 4 }])
  expect(contextualizationStatus('pending_publication')).toEqual({ text: 'Pendiente de publicación', color: 'success' })
  expect(contextualizationStatus('contextualization_error').color).toBe('error')
})
