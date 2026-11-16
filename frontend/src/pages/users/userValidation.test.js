import { describe, expect, it } from 'vitest'
import { collaboratorPayload, requiredText, validCollaboratorCi } from './userValidation'

describe('collaborator input validation', () => {
  it.each(['', '   ', '\u00a0', '\u200b', 'A\u200bNA', '\u202eANA', '\tANA', '\u0301ANA', 'ANA \u0301PÉREZ'])('rejects empty or invisible required content: %j', (value) => {
    expect(requiredText(value, { name: true, min: 2 })).toBe(false)
  })
  it.each(['A', 'A  ', ' A \u0301 '])('does not count spaces or marks as a second letter: %j', (value) => {
    expect(requiredText(value, { name: true, min: 2 })).toBe(false)
  })
  it('accepts composed names, accented initials and normalizes payload without changing CI zeros', () => {
    expect(requiredText('  MARI\u0301A   JOSÉ  ', { name: true, min: 2 })).toBe(true)
    expect(collaboratorPayload({ nombres: '  MARI\u0301A   JOSÉ ', apellido_paterno: ' PÉREZ ',
      apellido_materno: ' ', direccion: '', zona: ' VILLA   FÁTIMA ', correo: ' QA@gmail.com ', ci: '0012345',
    })).toMatchObject({ nombres: 'MARÍA JOSÉ', apellido_paterno: 'PÉREZ', apellido_materno: null,
      direccion: null, zona: 'VILLA FÁTIMA', correo: 'qa@gmail.com', ci: '0012345' })
  })
  it.each(['123456', '1234567A', '123 4567', ' 1234567', '\u200b1234567', '１１２３４５６７'])('rejects CI %j', (value) => {
    expect(validCollaboratorCi(value)).toBe(false)
  })
  it('accepts numeric CI from seven through thirty digits', () => {
    expect(validCollaboratorCi('0012345')).toBe(true)
    expect(validCollaboratorCi('1'.repeat(30))).toBe(true)
    expect(validCollaboratorCi('1'.repeat(31))).toBe(false)
  })
})
