// @vitest-environment jsdom
/* eslint-disable react/prop-types */
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
const mocks = vi.hoisted(() => ({ list: vi.fn(), folders: vi.fn(), trash: vi.fn(), detail: vi.fn(), update: vi.fn(), changePreview: vi.fn(), confirm: vi.fn(), values: {}, user: { role_code: 'ADMIN', permissions: ['leny:admin'] }, form: { resetFields: vi.fn(), setFieldsValue: vi.fn(), setFieldValue: vi.fn(), setFields: vi.fn() } }))
vi.mock('../../../auth/AuthProvider', () => ({ useAuth: () => ({ user: mocks.user }) }))
vi.mock('../../../api/lenyDocuments', () => ({ lenyDocumentsApi: { list: mocks.list, folders: mocks.folders, trash: mocks.trash, detail: mocks.detail, update: mocks.update, changePreview: mocks.changePreview } }))
vi.mock('./DocumentDetailDrawer', () => ({ DocumentDetailDrawer: () => null }))
vi.mock('./DocumentUploadModal', () => ({ DocumentUploadModal: ({ open }) => open ? <div>Carga documental</div> : null }))
vi.mock('@ant-design/icons', () => ({ DeleteOutlined: () => null, FolderAddOutlined: () => null, FolderOpenOutlined: () => null, ReloadOutlined: () => null, UploadOutlined: () => null }))
vi.mock('antd', () => {
  const Container = ({ children }) => <div>{children}</div>
  const Button = ({ children, disabled, onClick, htmlType, 'aria-label': label }) => <button type={htmlType || 'button'} disabled={disabled} onClick={onClick} aria-label={label}>{children}</button>
  const Form = Object.assign(({ children, onFinish }) => <form aria-label="Edición documental" onSubmit={(event) => { event.preventDefault(); onFinish(mocks.values) }}>{children}</form>, { useForm: () => [mocks.form], Item: Container })
  const Input = Object.assign((props) => <input {...props} />, { Search: ({ onSearch, 'aria-label': label }) => <input aria-label={label} onChange={(event) => onSearch(event.target.value)} />, TextArea: () => null })
  return { App: { useApp: () => ({ modal: { confirm: mocks.confirm }, message: { success: vi.fn(), info: vi.fn() } }) },
    Alert: ({ message, description, action }) => <div role="alert">{message}{description}{action}</div>,
    Button, Form, Input, InputNumber: () => null, Card: Container, Col: Container, Row: Container, Space: Container, Tag: Container,
    Modal: ({ open, children }) => open ? <div>{children}</div> : null,
    Empty: ({ description }) => <p>{description}</p>, Breadcrumb: () => null,
    Select: ({ options, onChange, 'aria-label': label }) => <select aria-label={label} onChange={(event) => onChange?.(event.target.value)}><option value="">Todos</option>{options?.map((item) => <option key={item.value} value={item.value}>{item.label}</option>)}</select>,
    Tree: ({ treeData, onSelect }) => <div>{treeData.map((item) => <Button key={item.key} onClick={() => onSelect([item.key])}>{item.title}</Button>)}</div>,
    Tabs: ({ items, onChange }) => <div>{items.map((item) => <Button key={item.key} onClick={() => onChange(item.key)}>{item.label}</Button>)}</div>,
    DatePicker: { RangePicker: () => null }, Typography: { Text: Container, Title: Container, Paragraph: Container },
    Table: ({ dataSource, columns, loading, locale }) => <div>{loading && <span>Cargando</span>}{!dataSource.length && locale.emptyText}{dataSource.map((record) => <div key={record.id}>{columns.map((column, index) => <span key={index}>{column.render ? column.render(record[column.dataIndex], record) : record[column.dataIndex]}</span>)}</div>)}</div>,
  }
})
import { LenyDocumentsPage } from './LenyDocumentsPage'
import { DocumentAdminRoute } from './DocumentAdminRoute'

beforeEach(() => {
  vi.clearAllMocks()
  mocks.user = { role_code: 'ADMIN', permissions: ['leny:admin'] }
  mocks.folders.mockResolvedValue({ items: [{ id: 'folder-1', name: 'Contratos', parent_id: null }] })
  mocks.list.mockResolvedValue({ items: [{ id: 'doc-1', title: 'Contrato de confección', state: 'ACTIVO', version_count: 2, updated_at: '2026-10-20T13:00:00Z' }], total: 1 })
  mocks.trash.mockResolvedValue({ items: [], total: 0 })
  mocks.detail.mockResolvedValue({ id: 'doc-1', title: 'Contrato de confección', description: 'Descripción original', state: 'active', revision: 4, folder_id: 'folder-1', role_codes: ['ADMIN'] })
  mocks.changePreview.mockResolvedValue({ token: 'review-token', role_codes: ['ADMIN'], broadens: false })
  mocks.update.mockResolvedValue({ id: 'doc-1' })
  mocks.form.setFieldsValue.mockImplementation((value) => { mocks.values = { ...value } })
  mocks.confirm.mockImplementation((options) => options.onOk())
})
afterEach(cleanup)

describe('Document library integrated page', () => {
  it('uses the latest version processing status instead of an unconditional pending label', async () => {
    mocks.list.mockResolvedValue({ items: [{ id: 'doc-1', title: 'Documento contextualizado', state: 'active', status: 'pending_publication' }], total: 1 })
    render(<LenyDocumentsPage />)
    await screen.findByText('Documento contextualizado')
    expect(screen.getByText('Pendiente de publicación')).toBeTruthy()
    expect(screen.queryByText('Pendiente de contextualización')).toBeNull()
  })
  it('shows a validated index and an active publication without a contradictory pending badge', async () => {
    mocks.list.mockResolvedValue({ items: [{ id: 'doc-1', title: 'Documento publicado', state: 'active', status: 'pending_publication', published_version_id: 'version-1' }], total: 1 })
    render(<LenyDocumentsPage />)
    await screen.findByText('Documento publicado')
    expect(screen.getByText('Indexación validada')).toBeTruthy()
    expect(screen.getByText('Publicación vigente')).toBeTruthy()
    expect(screen.queryByText('Pendiente de publicación')).toBeNull()
  })
  it('loads the library, exposes true pending capability and filters by folder and format', async () => {
    render(<LenyDocumentsPage />)
    await screen.findByText('Contrato de confección')
    expect(screen.getByText('Pendiente de contextualización')).toBeTruthy()
    fireEvent.click(await screen.findByText('Contratos'))
    await waitFor(() => expect(mocks.list).toHaveBeenLastCalledWith(expect.objectContaining({ folder_id: 'folder-1', page: 1 }), expect.anything()))
    fireEvent.change(screen.getByLabelText('Filtrar formato'), { target: { value: 'pdf' } })
    await waitFor(() => expect(mocks.list).toHaveBeenLastCalledWith(expect.objectContaining({ format: 'pdf' }), expect.anything()))
    fireEvent.click(screen.getByText('Almacenar archivos'))
    expect(screen.getByText('Carga documental')).toBeTruthy()
  })
  it('loads trash independently and keeps irreversible actions unavailable when empty', async () => {
    render(<LenyDocumentsPage />)
    await screen.findByText('Contrato de confección')
    fireEvent.click(screen.getByText('Papelera · 10 días'))
    await screen.findByText('La papelera está vacía.')
    expect(mocks.trash).toHaveBeenCalled()
    expect(screen.getByText('Vaciar papelera').disabled).toBe(true)
    expect(screen.getByText('Almacenar archivos').disabled).toBe(true)
  })
  it('shows rate limiting with recovery and does not expose backend error details', async () => {
    mocks.list.mockRejectedValueOnce({ response: { status: 429, headers: { 'retry-after': '9' }, data: { detail: 'internal-secret' } } })
    render(<LenyDocumentsPage />)
    await screen.findByText(/Reintenta en 9 segundos/)
    expect(screen.queryByText(/internal-secret/)).toBeNull()
    fireEvent.click(screen.getByText('Reintentar'))
    await screen.findByText('Contrato de confección')
  })
  it('denies DOC and non-admin users even if a manipulated permission contains leny:admin', () => {
    mocks.user = { role_code: 'DOC', permissions: ['leny:admin'] }
    render(<MemoryRouter initialEntries={['/documents']}><Routes><Route element={<DocumentAdminRoute />}><Route path="/documents" element={<LenyDocumentsPage />} /></Route><Route path="/403" element={<div>Acceso denegado</div>} /></Routes></MemoryRouter>)
    expect(screen.getByText('Acceso denegado')).toBeTruthy()
    expect(mocks.list).not.toHaveBeenCalled()
  })
  it('fetches current metadata and requires reviewed ACL confirmation before sending its revision', async () => {
    render(<LenyDocumentsPage />)
    fireEvent.click(await screen.findByText('Editar'))
    await screen.findByText('Revisar cambios')
    expect(mocks.detail).toHaveBeenCalledWith('doc-1', expect.anything())
    fireEvent.click(screen.getByText('Revisar cambios'))
    await waitFor(() => expect(mocks.update).toHaveBeenCalledWith('doc-1', { revision: 4, title: 'Contrato de confección', description: 'Descripción original', folder_id: 'folder-1', role_codes: ['ADMIN'], confirmation: 'review-token' }))
    expect(mocks.changePreview).toHaveBeenCalledBefore(mocks.update)
    expect(mocks.confirm).toHaveBeenCalledOnce()
  })
  it('keeps metadata in the editor when a concurrent update invalidates the reviewed revision', async () => {
    mocks.update.mockRejectedValueOnce({ response: { status: 409 } })
    render(<LenyDocumentsPage />)
    fireEvent.click(await screen.findByText('Editar'))
    fireEvent.click(await screen.findByText('Revisar cambios'))
    await screen.findByText(/La operación no puede completarse con el estado actual/)
    expect(screen.getByRole('form', { name: 'Edición documental' })).toBeTruthy()
    expect(mocks.values).toMatchObject({ title: 'Contrato de confección', description: 'Descripción original', revision: 4 })
  })
})
