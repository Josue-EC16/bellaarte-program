// @vitest-environment jsdom
/* eslint-disable react/prop-types */
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
const mocks = vi.hoisted(() => ({ ragStatus: vi.fn(), contextualizations: vi.fn(), publish: vi.fn(), unpublish: vi.fn(), changed: vi.fn() }))
vi.mock('../../../api/lenyDocuments', () => ({ lenyDocumentsApi: mocks }))
vi.mock('antd', () => {
  const Container = ({ children }) => <div>{children}</div>
  return { Alert: ({ message, description }) => <div role="alert">{message}{description}</div>,
    Button: ({ children, onClick, disabled, loading }) => <button disabled={disabled || loading} onClick={onClick}>{children}</button>,
    Card: ({ title, extra, children }) => <section>{title}{extra}{children}</section>,
    Descriptions: ({ items }) => <dl>{items.map((item) => <div key={item.key}><dt>{item.label}</dt><dd>{item.children}</dd></div>)}</dl>,
    Space: Container, Spin: () => <span>Cargando</span>, Typography: { Text: Container },
  }
})
import { PublicationPanel } from './PublicationPanel'
const doc = { id: 'document-1', revision: 7, role_codes: ['ADMIN', 'CAJA'] }
const version = { id: 'version-1', number: 2, status: 'pending_publication', validated_indexation_id: 'index-2' }
const props = { document: doc, version, onChange: mocks.changed, onClose: vi.fn() }
beforeEach(() => {
  vi.clearAllMocks()
  mocks.ragStatus.mockResolvedValue({ publication_ready: true, ready: false })
  mocks.contextualizations.mockResolvedValue({ items: [{ status: 'completed', indexation_id: 'index-2', warnings: ['Revisar OCR'] }] })
  mocks.publish.mockResolvedValue({ revision: 8 }); mocks.unpublish.mockResolvedValue({ revision: 8 })
})
afterEach(cleanup)

describe('Explicit index publication', () => {
  it('requires confirmation and sends the precise version, index and reviewed revision without depending on Ollama', async () => {
    render(<PublicationPanel {...props} />)
    await waitFor(() => expect(screen.getByText('Publicar esta indexación').disabled).toBe(false))
    expect(screen.getByText('Revisar OCR')).toBeTruthy()
    expect(mocks.publish).not.toHaveBeenCalled()
    fireEvent.click(screen.getByText('Publicar esta indexación'))
    fireEvent.click(screen.getByText('Confirmar publicación'))
    await waitFor(() => expect(mocks.changed).toHaveBeenCalledOnce())
    expect(mocks.publish).toHaveBeenCalledWith('document-1', { request_id: expect.any(String), expected_revision: 7, version_id: 'version-1', indexation_id: 'index-2', confirm: true }, expect.any(AbortSignal))
  })
  it('retains a request id after uncertain communication and does not retry automatically', async () => {
    mocks.publish.mockRejectedValueOnce(new Error('offline'))
    render(<PublicationPanel {...props} />)
    await waitFor(() => expect(screen.getByText('Publicar esta indexación').disabled).toBe(false))
    fireEvent.click(screen.getByText('Publicar esta indexación')); fireEvent.click(screen.getByText('Confirmar publicación'))
    await screen.findByText('No fue posible completar la operación. Intenta nuevamente.')
    expect(mocks.publish).toHaveBeenCalledOnce()
    fireEvent.click(screen.getByText('Confirmar publicación'))
    await waitFor(() => expect(mocks.publish).toHaveBeenCalledTimes(2))
    expect(mocks.publish.mock.calls[0][1].request_id).toBe(mocks.publish.mock.calls[1][1].request_id)
  })
  it('requires another review after a conflict, without automatically approving newer state', async () => {
    mocks.publish.mockRejectedValue({ response: { status: 409 } })
    render(<PublicationPanel {...props} />)
    await waitFor(() => expect(screen.getByText('Publicar esta indexación').disabled).toBe(false))
    fireEvent.click(screen.getByText('Publicar esta indexación')); fireEvent.click(screen.getByText('Confirmar publicación'))
    await waitFor(() => expect(mocks.changed).toHaveBeenCalledOnce())
    expect(screen.queryByText('Confirmar publicación')).toBeNull()
    expect(mocks.publish).toHaveBeenCalledOnce()
  })
  it('does not publish when readiness is absent, there is no index, or a worker is processing this version', async () => {
    mocks.ragStatus.mockResolvedValue({ ready: true })
    const { rerender } = render(<PublicationPanel {...props} />)
    await screen.findByText(/La publicación no está habilitada/)
    expect(screen.getByText('Publicar esta indexación').disabled).toBe(true)
    mocks.ragStatus.mockResolvedValue({ publication_ready: true })
    mocks.contextualizations.mockResolvedValue({ items: [{ status: 'running' }] })
    rerender(<PublicationPanel {...props} document={{ ...doc, revision: 8 }} />)
    await screen.findByText(/Existe un procesamiento activo/)
    expect(screen.getByText('Publicar esta indexación').disabled).toBe(true)
    rerender(<PublicationPanel {...props} version={{ ...version, validated_indexation_id: null }} />)
    await screen.findByText('Sin índice validado')
    expect(screen.getByText('Publicar esta indexación').disabled).toBe(true)
  })
  it('does not replace an old published index without approval and permits confirmed unpublication', async () => {
    render(<PublicationPanel {...props} document={{ ...doc, published_version_id: 'version-1', published_indexation_id: 'index-1' }} />)
    await waitFor(() => expect(screen.getByText('Despublicar documento').disabled).toBe(false))
    expect(mocks.publish).not.toHaveBeenCalled()
    fireEvent.click(screen.getByText('Despublicar documento'))
    expect(mocks.unpublish).not.toHaveBeenCalled()
    fireEvent.click(screen.getByText('Confirmar despublicación'))
    await waitFor(() => expect(mocks.unpublish).toHaveBeenCalledOnce())
    expect(mocks.unpublish.mock.calls[0][1]).toEqual({ request_id: expect.any(String), expected_revision: 7, confirm: true })
  })
})
