// @vitest-environment jsdom
/* eslint-disable react/prop-types */
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
const mocks = vi.hoisted(() => ({ detail: vi.fn(), download: vi.fn(), save: vi.fn() }))
vi.mock('../../api/lenySources', () => ({ lenySourcesApi: mocks }))
vi.mock('./documents/documentUtils', () => ({ saveDocumentBlob: mocks.save }))
vi.mock('antd', () => {
  const Container = ({ children }) => <div>{children}</div>
  return { Alert: ({ message, description, action }) => <div role="alert">{message}{description}{action}</div>,
    Button: ({ children, onClick, disabled, 'aria-label': label }) => <button disabled={disabled} onClick={onClick} aria-label={label}>{children}</button>,
    Drawer: ({ open, children, onClose }) => open ? <aside><button onClick={onClose}>Cerrar fuente</button>{children}</aside> : null,
    Space: Container, Spin: () => <span>Cargando fuente</span>, Typography: { Title: Container, Paragraph: Container },
  }
})
import { LenySources } from './LenySources'
import { sourceLocator, validLenySources } from './lenySourceUtils'

const source = { source_id: '12345678-1234-1234-1234-123456789abc', citation_id: 'S1', available: true, label: 'Procedimiento de boutique', version: 2, locator: { page: 4 }, source_type: 'PDF_TEXT', warnings: [] }
beforeEach(() => { vi.clearAllMocks(); mocks.detail.mockResolvedValue({ ...source, text: 'Paso seguro\n<script>no ejecutar</script>' }); mocks.download.mockResolvedValue({ data: new Blob(['original']) }) })
afterEach(cleanup)

describe('Private structured document sources', () => {
  it('renders sources separately, resolves escaped text and downloads only through the authenticated API', async () => {
    const { container } = render(<LenySources status="completed" sources={[source]} />)
    expect(screen.getByText('Fuentes consultadas')).toBeTruthy()
    expect(screen.getByText('Versión 2 · Página 4')).toBeTruthy()
    fireEvent.click(screen.getByLabelText('Ver fuente S1'))
    await screen.findByText(/<script>no ejecutar<\/script>/)
    expect(container.querySelector('script,iframe,a,img')).toBeNull()
    fireEvent.click(screen.getByText('Descargar original publicado'))
    await waitFor(() => expect(mocks.download).toHaveBeenCalledWith(source.source_id, expect.any(AbortSignal)))
    expect(mocks.save).toHaveBeenCalledOnce()
  })
  it('removes previously visible source metadata after a revoked read without removing the historic response', async () => {
    mocks.detail.mockRejectedValue({ response: { status: 404, data: { detail: '/private/secret' } } })
    render(<LenySources status="completed" sources={[source]} />)
    fireEvent.click(screen.getByLabelText('Ver fuente S1'))
    await waitFor(() => expect(screen.queryByText(/Procedimiento de boutique/)).toBeNull())
    expect(screen.getAllByText('Fuente no disponible').length).toBeGreaterThan(0)
    expect(screen.queryByText(/private\/secret/)).toBeNull()
    expect(screen.queryByText('Descargar original publicado')).toBeNull()
  })
  it.each(['generating', 'failed', 'interrupted'])('never labels a %s answer with consulted sources', (status) => {
    render(<LenySources status={status} sources={[source]} />)
    expect(screen.queryByText('Fuentes consultadas')).toBeNull()
  })
  it('does not reveal metadata from an unavailable historical reference', () => {
    render(<LenySources status="completed" sources={[{ ...source, available: false }]} />)
    expect(screen.getByText('Fuente no disponible')).toBeTruthy()
    expect(screen.queryByText(/Procedimiento de boutique/)).toBeNull()
  })
  it('aborts private reads when the source closes', async () => {
    let signal
    mocks.detail.mockImplementation((id, incoming) => { signal = incoming; return new Promise(() => {}) })
    render(<LenySources status="completed" sources={[source]} />)
    fireEvent.click(screen.getByLabelText('Ver fuente S1'))
    await waitFor(() => expect(signal).toBeTruthy())
    fireEvent.click(screen.getByText('Cerrar fuente'))
    expect(signal.aborted).toBe(true)
  })
  it('invalidates the open fragment if download permission was revoked', async () => {
    mocks.download.mockRejectedValue({ response: { status: 404 } })
    render(<LenySources status="completed" sources={[source]} />)
    fireEvent.click(screen.getByLabelText('Ver fuente S1'))
    fireEvent.click(await screen.findByText('Descargar original publicado'))
    await waitFor(() => expect(screen.queryByText(/Paso seguro/)).toBeNull())
    expect(mocks.save).not.toHaveBeenCalled()
  })
  it('formats DOCX structural locations without inventing page numbers and rejects excessive source arrays', () => {
    expect(sourceLocator({ table: 2, row: 3 }, 'DOCX_TABLE')).toBe('Tabla 2 · Fila 3')
    expect(validLenySources([source])).toBe(true)
    expect(validLenySources(Array(6).fill(source))).toBe(false)
    expect(validLenySources([{ ...source, source_id: '/private/file' }])).toBe(false)
  })
})
