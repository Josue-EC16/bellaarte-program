const INVISIBLE = /[\p{Cc}\p{Cf}]/u
const NAME = /^\p{L}[\p{L}\p{M}]*(?: +\p{L}[\p{L}\p{M}]*)*$/u

export function cleanText(value) {
  return typeof value === 'string' ? value.normalize('NFC').trim().replace(/\s+/gu, ' ') : ''
}

export function requiredText(value, { name = false, min = 1, max = 120 } = {}) {
  const clean = cleanText(value)
  if (!clean || INVISIBLE.test(value || '') || !/[\p{L}\p{N}]/u.test(clean)) return false
  const contentLength = (clean.match(name ? /\p{L}/gu : /[\p{L}\p{N}]/gu) || []).length
  return contentLength >= min && clean.length <= max && (!name || NAME.test(clean))
}

export function validateRequiredText(options = {}) {
  return (_, value) => requiredText(value, options)
    ? Promise.resolve() : Promise.reject(new Error(options.name
      ? 'Ingresa al menos dos letras; usa espacios solo para separar nombres o apellidos.'
      : 'Ingresa contenido válido; los espacios y caracteres invisibles no cuentan.'))
}

export function validCollaboratorCi(value) {
  return typeof value === 'string' && /^[0-9]{7,30}$/.test(value)
}

export function collaboratorPayload(values) {
  const result = { ...values }
  for (const field of ['nombres', 'apellido_paterno', 'zona']) result[field] = cleanText(values[field]).toUpperCase()
  for (const field of ['apellido_materno', 'direccion']) result[field] = cleanText(values[field]).toUpperCase() || null
  result.correo = (values.correo || '').trim().toLowerCase()
  return result
}
