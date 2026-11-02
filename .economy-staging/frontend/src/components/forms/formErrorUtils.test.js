import { describe, expect, it, vi } from 'vitest'

import {
  applyFormApiError,
  normalizeApiError,
  resolveFormApiError,
} from './formErrorUtils'

describe('normalizeApiError', () => {
  it('preserva los errores 422 y los traduce a un resumen útil', () => {
    const error = {
      response: {
        status: 422,
        data: {
          detail: [
            { loc: ['body', 'item', 'sale_price'], msg: 'Value error, El precio de venta no puede ser menor o igual al precio de compra.' },
            { loc: ['body', 'item', 'code'], msg: 'Field required' },
          ],
        },
      },
    }

    const normalized = normalizeApiError(error)

    expect(normalized.status).toBe(422)
    expect(normalized.issues).toHaveLength(2)
    expect(normalized.issues[0].location).toEqual(['item', 'sale_price'])
    expect(normalized.issues[0].message).toBe(
      'El precio de venta no puede ser menor o igual al precio de compra.',
    )
    expect(normalized.issues[1].message).toBe('Debe completar este campo.')
    expect(normalized.summary).toContain('Hay campos con información incompleta')
  })
})

describe('resolveFormApiError', () => {
  it('mapea errores de backend a campos concretos cuando la relación es clara', () => {
    const error = {
      normalizedError: {
        status: 409,
        rawDetail: 'Ya existe un cliente con ese codigo.',
        issues: [],
        summary: 'Ya existe un cliente con ese codigo.',
        globalMessage: 'Ya existe un cliente con ese codigo.',
      },
    }

    const resolved = resolveFormApiError(error, {
      messageFieldMap: [{ test: /cliente con ese codigo/i, field: 'codigo' }],
    })

    expect(resolved.fieldErrors).toEqual([
      { name: ['codigo'], errors: ['Ya existe un cliente con ese codigo.'] },
    ])
    expect(resolved.globalMessage).toBeNull()
  })

  it('aplica errores al formulario usando rutas anidadas de Ant Design', () => {
    const form = { setFields: vi.fn() }
    const error = {
      response: {
        status: 422,
        data: {
          detail: [
            {
              loc: ['body', 'detail', 'dress_type'],
              msg: 'Field required',
            },
          ],
        },
      },
    }

    const resolved = applyFormApiError(form, error)

    expect(form.setFields).toHaveBeenCalledWith([
      {
        name: ['detail', 'dress_type'],
        errors: ['Debe completar este campo.'],
      },
    ])
    expect(resolved.globalMessage).toBeNull()
  })
})
