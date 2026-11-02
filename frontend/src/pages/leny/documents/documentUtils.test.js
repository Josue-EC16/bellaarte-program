import { describe, expect, it } from 'vitest'
import { buildFolderTree, canManageDocuments, DOCUMENT_ROLES, documentError, folderBreadcrumbs, folderOptions, hashDocumentFile, safeDownloadName, validateDocumentFile } from './documentUtils'

describe('Document library security boundaries', () => {
  it('requires both the authenticated ADMIN role and the actual permission', () => {
    expect(canManageDocuments({ role_code: 'ADMIN', permissions: ['leny:admin'] })).toBe(true)
    for (const role_code of ['CAJA', 'INV_BOUTIQUE', 'INV_TALLER', 'MODISTA', 'DOC']) expect(canManageDocuments({ role_code, permissions: ['leny:admin'] })).toBe(false)
    expect(canManageDocuments({ role_code: 'ADMIN', permissions: ['leny:chat'] })).toBe(false)
    expect(canManageDocuments(null)).toBe(false)
    expect(DOCUMENT_ROLES.map((role) => role.value)).not.toContain('DOC')
  })
  it('shows safe status-specific failures without server internals', () => {
    for (const status of [401, 403, 404, 409, 413, 415, 422, 429, 500, 503]) {
      const result = documentError({ response: { status, data: { detail: { message: 'secret-token C:\\backend' } } } })
      expect(result).not.toContain('secret-token'); expect(result).not.toContain('backend')
      expect(result.length).toBeGreaterThan(15)
    }
    expect(documentError({ response: { status: 429, headers: { 'retry-after': '21' } } })).toContain('21 segundos')
    expect(documentError({ code: 'ERR_CANCELED' })).toContain('cancelada')
  })
  it('checks supported extensions, empty files and separate image limits before upload', () => {
    expect(validateDocumentFile({ name: 'contrato.PDF', size: 10 * 1024 * 1024 })).toBeNull()
    expect(validateDocumentFile({ name: 'foto.jpg', size: 5 * 1024 * 1024 + 1 })).toContain('5 MiB')
    expect(validateDocumentFile({ name: 'contrato.docm', size: 100 })).toContain('Solo')
    expect(validateDocumentFile({ name: 'vacio.docx', size: 0 })).toContain('vacío')
  })
  it('computes SHA-256 over bytes, retaining Unicode filenames as metadata', async () => {
    const hash = await hashDocumentFile(new Blob(['abc']))
    expect(hash).toBe('ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad')
  })
  it('excludes the current folder and descendants from move destinations and terminates on cycles', () => {
    const folders = [{ id: 'a', parent_id: null, name: 'A' }, { id: 'b', parent_id: 'a', name: 'B' }, { id: 'c', parent_id: null, name: 'C' }]
    expect(buildFolderTree(folders)[0].children[0].key).toBe('b')
    expect(folderOptions(folders, 'a').map((option) => option.value)).toEqual(['', 'c'])
    expect(folderBreadcrumbs([{ id: 'x', parent_id: 'y' }, { id: 'y', parent_id: 'x' }], 'x')).toHaveLength(2)
  })
  it('sanitizes browser download names and supports UTF-8 disposition', () => {
    expect(safeDownloadName("attachment; filename*=UTF-8''confecci%C3%B3n.pdf")).toBe('confección.pdf')
    expect(safeDownloadName('attachment; filename="../../contrato.pdf"')).toBe('.._.._contrato.pdf')
    expect(safeDownloadName('')).toBe('documento')
  })
})
