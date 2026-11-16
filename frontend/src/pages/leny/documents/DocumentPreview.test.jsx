// @vitest-environment jsdom
/* eslint-disable react/prop-types */
import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
const mocks = vi.hoisted(() => ({ detail: vi.fn(), versions: vi.fn(), preview: vi.fn(), content: vi.fn() }))
vi.mock('../../../api/lenyDocuments', () => ({ lenyDocumentsApi: mocks }))
vi.mock('antd', () => {
  const Container = ({ children }) => <div>{children}</div>
  return { Alert: ({ message }) => <div role="alert">{message}</div>, Button: ({ children, onClick, disabled }) => <button onClick={onClick} disabled={disabled}>{children}</button>,
    Descriptions: () => null, Drawer: ({ open, children }) => open ? <div>{children}</div> : null,
    Empty: ({ description }) => <p>{description}</p>, Pagination: () => null, Space: Container, Spin: () => <span>Cargando</span>, Tag: Container,
    Typography: { Title: Container, Paragraph: Container, Text: Container },
    Table: ({ dataSource, columns }) => <div>{dataSource.map((record) => <div key={record.id}>{columns.map((column, index) => <span key={index}>{column.render ? column.render(record[column.dataIndex], record) : record[column.dataIndex]}</span>)}</div>)}</div>,
  }
})
import { DocumentDetailDrawer } from './DocumentDetailDrawer'
beforeEach(() => {
  vi.clearAllMocks()
  mocks.detail.mockResolvedValue({ id: 'd', title: 'Contrato', state: 'ACTIVO', description: 'Documento privado', role_codes: ['ADMIN'] })
  mocks.versions.mockResolvedValue({ items: [{ id: 'v', number: 1, original_name: 'contrato.docx' }], total: 1 })
})
afterEach(() => { cleanup(); vi.unstubAllGlobals() })

describe('Authenticated document previews', () => {
  it('shows the real validated version status and offers a separate publication review', async () => {
    mocks.detail.mockResolvedValue({ id: 'd', title: 'Contrato', state: 'active', status: 'pending_publication' })
    mocks.versions.mockResolvedValue({ items: [{ id: 'v', number: 1, original_name: 'contrato.docx', status: 'pending_publication', validated_indexation_id: 'verified-index' }], total: 1 })
    render(<DocumentDetailDrawer id="d" onClose={() => {}} onEdit={() => {}} onVersion={() => {}} />)
    await screen.findByText('Contextualizar de nuevo')
    expect(screen.getAllByText('Pendiente de publicación')).toHaveLength(2)
    expect(screen.queryByText('Pendiente de contextualización')).toBeNull()
    expect(screen.getByText('Revisar publicación').disabled).toBe(false)
    expect(screen.queryByText('Confirmar publicación')).toBeNull()
  })
  it('renders DOCX as escaped text and tables without executing user HTML or code', async () => {
    mocks.preview.mockResolvedValue({ headers: { 'content-type': 'application/json' }, data: { text: async () => JSON.stringify({ kind: 'docx', blocks: [
      { type: 'paragraph', text: '<script>window.secret = 1</script>' }, { type: 'table', rows: [['<img src=x onerror=alert(1)>', 'Tabla segura']] },
    ], truncated: true }) } })
    const { container } = render(<DocumentDetailDrawer id="d" onClose={() => {}} onEdit={() => {}} onVersion={() => {}} />)
    fireEvent.click(await screen.findByText('Vista previa'))
    await screen.findByText('<script>window.secret = 1</script>')
    expect(container.querySelector('script, img, iframe')).toBeNull()
    expect(screen.getByText('<img src=x onerror=alert(1)>')).toBeTruthy()
    expect(screen.getByText(/vista previa está truncada/)).toBeTruthy()
    expect(screen.queryByText('Confirmar publicación')).toBeNull()
  })
  it('never embeds PDF or arbitrary response types', async () => {
    mocks.preview.mockResolvedValue({ headers: { 'content-type': 'text/html' }, data: '<script>malicious</script>' })
    const { container } = render(<DocumentDetailDrawer id="d" onClose={() => {}} onEdit={() => {}} onVersion={() => {}} />)
    fireEvent.click(await screen.findByText('Vista previa'))
    await screen.findByText('No fue posible completar la operación. Intenta nuevamente.')
    expect(container.querySelector('iframe, object, embed, script')).toBeNull()
  })
  it('revokes authenticated image URLs when the document closes', async () => {
    const createObjectURL = vi.fn(() => 'blob:private-image'), revokeObjectURL = vi.fn()
    const OriginalURL = URL
    vi.stubGlobal('URL', Object.assign(OriginalURL, { createObjectURL, revokeObjectURL }))
    mocks.preview.mockResolvedValue({ headers: { 'content-type': 'image/png' }, data: new Blob(['image']) })
    const { rerender } = render(<DocumentDetailDrawer id="d" onClose={() => {}} onEdit={() => {}} onVersion={() => {}} />)
    fireEvent.click(await screen.findByText('Vista previa'))
    await screen.findByAltText('Vista previa de Contrato')
    rerender(<DocumentDetailDrawer id={null} onClose={() => {}} onEdit={() => {}} onVersion={() => {}} />)
    expect(revokeObjectURL).toHaveBeenCalledWith('blob:private-image')
  })
})
