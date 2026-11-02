// @vitest-environment jsdom
/* eslint-disable react/prop-types */
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
const mocks = vi.hoisted(() => ({ upload: vi.fn(), values: {}, complete: vi.fn(), close: vi.fn() }))
vi.mock('../../../api/lenyDocuments', () => ({ lenyDocumentsApi: { upload: mocks.upload, options: vi.fn(async () => ({batch_size:5,max_file_bytes:10485760,image_bytes:5242880,max_pixels:12000000,pdf_pages:50})) } }))
vi.mock('./documentUtils', async (original) => ({ ...(await original()), hashDocumentFile: vi.fn(async () => 'a'.repeat(64)) }))
vi.mock('antd', () => {
  const Container = ({ children }) => <div>{children}</div>
  const form = { resetFields: () => { mocks.values = {} }, setFieldsValue: (value) => Object.assign(mocks.values, value), setFieldValue: (key, value) => { mocks.values[key] = value } }
  const Form = Object.assign(({ children, onFinish }) => <form onSubmit={(event) => { event.preventDefault(); onFinish({ ...mocks.values }) }}>{children}</form>, { useForm: () => [form], Item: Container })
  return { Form, Alert: ({ message, description }) => <div role="alert">{message}{description}</div>,
    Button: ({ children, onClick, disabled, htmlType }) => <button type={htmlType || 'button'} onClick={onClick} disabled={disabled}>{children}</button>,
    Input: Object.assign(() => null, { TextArea: () => null }), Select: () => null, Space: Container, Tag: Container,
    Modal: ({ open, children }) => open ? <div>{children}</div> : null, Progress: ({ percent }) => <div>Transferencia: {percent}%</div>,
    Typography: { Paragraph: Container, Text: Container },
  }
})
import { DocumentUploadModal } from './DocumentUploadModal'
beforeEach(() => { vi.clearAllMocks(); mocks.values = {} })
afterEach(cleanup)
const props = { open: true, folders: [{ id: 'folder', name: 'Carpeta' }], folderId: 'folder', onClose: mocks.close, onComplete: mocks.complete }

describe('Document upload lifecycle', () => {
  it('retains request_id, hash and original metadata on manual retries after failed communication', async () => {
    mocks.upload.mockRejectedValueOnce({ response: { status: 503 } }).mockResolvedValueOnce({ id: 'document' })
    render(<DocumentUploadModal {...props} />)
    fireEvent.change(screen.getByLabelText('Archivos para almacenar'), { target: { files: [new File(['data'], 'Contrato.pdf', { type: 'application/pdf' })] } })
    fireEvent.click(screen.getByText('Almacenar'))
    await screen.findByText(/biblioteca no está disponible temporalmente/)
    const firstMetadata = mocks.upload.mock.calls[0][1]
    expect(firstMetadata).toMatchObject({ title: 'Contrato', folder_id: 'folder', sha256: 'a'.repeat(64), request_id: expect.any(String) })
    fireEvent.click(screen.getByText('Reintentar pendientes'))
    await screen.findByText('Almacenado')
    expect(mocks.upload.mock.calls[1][1]).toEqual(firstMetadata)
    expect(mocks.complete).toHaveBeenCalledOnce()
    expect(screen.getByText('Reintentar pendientes').disabled).toBe(true)
  })
  it('aborts the active upload and stops subsequent files without claiming success', async () => {
    mocks.upload.mockImplementation((file, metadata, { signal }) => new Promise((resolve, reject) => signal.addEventListener('abort', () => reject({ code: 'ERR_CANCELED' }), { once: true })))
    render(<DocumentUploadModal {...props} />)
    fireEvent.change(screen.getByLabelText('Archivos para almacenar'), { target: { files: [new File(['a'], 'uno.pdf'), new File(['b'], 'dos.pdf')] } })
    fireEvent.click(screen.getByText('Almacenar'))
    await waitFor(() => expect(mocks.upload).toHaveBeenCalledOnce())
    fireEvent.click(screen.getByText('Cancelar transferencia'))
    await screen.findByText('Solicitud cancelada. Puedes volver a intentarlo.')
    expect(mocks.upload.mock.calls[0][2].signal.aborted).toBe(true)
    expect(mocks.upload).toHaveBeenCalledOnce()
    expect(mocks.complete).not.toHaveBeenCalled()
  })
  it('isolates invalid files and reports per-file outcomes instead of discarding valid uploads', async () => {
    mocks.upload.mockResolvedValue({ id: 'document' })
    render(<DocumentUploadModal {...props} />)
    fireEvent.change(screen.getByLabelText('Archivos para almacenar'), { target: { files: [new File(['bad'], 'macro.docm'), new File(['ok'], 'valido.pdf')] } })
    fireEvent.click(screen.getByText('Almacenar'))
    await screen.findByText('Almacenado')
    expect(screen.getByText('Solo se permiten PDF, DOCX, JPG, JPEG y PNG.')).toBeTruthy()
    expect(mocks.upload).toHaveBeenCalledOnce()
    expect(mocks.upload.mock.calls[0][0].name).toBe('valido.pdf')
  })
  it('requires explicit confirmation before replacing a request that the backend has marked interrupted', async () => {
    mocks.upload.mockRejectedValueOnce({ response: { status: 409, data: { detail: { code: 'DOCUMENT_REQUEST_INTERRUPTED' } } } }).mockResolvedValueOnce({ id: 'document' })
    render(<DocumentUploadModal {...props} />)
    fireEvent.change(screen.getByLabelText('Archivos para almacenar'), { target: { files: [new File(['data'], 'Contrato.pdf')] } })
    fireEvent.click(screen.getByText('Almacenar'))
    const confirmation = await screen.findByText('Confirmar solicitud nueva para este archivo')
    const oldId = mocks.upload.mock.calls[0][1].request_id
    expect(screen.getByText('Reintentar pendientes').disabled).toBe(true)
    fireEvent.click(confirmation)
    fireEvent.click(screen.getByText('Almacenar'))
    await screen.findByText('Almacenado')
    expect(mocks.upload.mock.calls[1][1].request_id).not.toBe(oldId)
  })
})
