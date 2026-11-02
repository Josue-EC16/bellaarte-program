function translateBackendValidationMessage(message) {
  if (!message) return 'Hay un dato no válido.'

  const normalized = `${message}`.trim()
  const lower = normalized.toLowerCase()

  if (lower === 'field required') {
    return 'Debe completar este campo.'
  }

  if (lower.startsWith('value error, ')) {
    return normalized.slice('Value error, '.length)
  }

  let match = normalized.match(/^String should have at least (\d+) characters$/i)
  if (match) {
    return `Debe tener al menos ${match[1]} caracteres.`
  }

  match = normalized.match(/^String should have at most (\d+) characters$/i)
  if (match) {
    return `No puede superar ${match[1]} caracteres.`
  }

  match = normalized.match(/^Input should be greater than or equal to (.+)$/i)
  if (match) {
    return `Debe ser mayor o igual a ${match[1]}.`
  }

  match = normalized.match(/^Input should be greater than (.+)$/i)
  if (match) {
    return `Debe ser mayor a ${match[1]}.`
  }

  match = normalized.match(/^Input should be less than or equal to (.+)$/i)
  if (match) {
    return `Debe ser menor o igual a ${match[1]}.`
  }

  match = normalized.match(/^Input should be less than (.+)$/i)
  if (match) {
    return `Debe ser menor a ${match[1]}.`
  }

  if (lower === 'input should be a valid email address') {
    return 'Debe ingresar un correo electrónico válido.'
  }

  if (lower === 'input should be a valid number') {
    return 'Debe ingresar un número válido.'
  }

  if (lower === 'input should be a valid integer') {
    return 'Debe ingresar un número entero válido.'
  }

  if (lower === 'input should be a valid string') {
    return 'Debe ingresar un texto válido.'
  }

  if (lower === 'input should be a valid boolean') {
    return 'Debe ingresar un valor válido.'
  }

  return normalized
}

function cleanIssueLocation(location) {
  if (!Array.isArray(location)) return []

  return location.filter(
    (segment) =>
      segment !== 'body' &&
      segment !== 'query' &&
      segment !== 'path' &&
      segment !== 'response' &&
      segment !== 'header',
  )
}

function normalizeApiIssues(detail) {
  if (!Array.isArray(detail)) {
    return []
  }

  return detail.map((issue) => {
    const location = cleanIssueLocation(issue?.loc)
    return {
      location,
      dottedPath: location.join('.'),
      message: translateBackendValidationMessage(issue?.msg),
      type: issue?.type || null,
    }
  })
}

export function normalizeApiError(error) {
  const detail = error?.response?.data?.detail
  const status = error?.response?.status || null

  if (Array.isArray(detail)) {
    const issues = normalizeApiIssues(detail)
    return {
      status,
      rawDetail: detail,
      issues,
      summary:
        issues.length > 0
          ? 'Hay campos con información incompleta o no válida. Revísalos y vuelve a intentarlo.'
          : 'No fue posible validar la información enviada.',
      globalMessage: null,
    }
  }

  if (typeof detail === 'string' && detail.trim()) {
    return {
      status,
      rawDetail: detail,
      issues: [],
      summary: detail,
      globalMessage: detail,
    }
  }

  return {
    status,
    rawDetail: detail,
    issues: [],
    summary: 'No fue posible procesar la solicitud.',
    globalMessage: 'No fue posible procesar la solicitud.',
  }
}

function matchesFieldRule(message, rule) {
  if (!rule?.test) return false
  if (rule.test instanceof RegExp) {
    return rule.test.test(message)
  }
  return `${rule.test}`.toLowerCase() === `${message}`.toLowerCase()
}

function toNamePath(name) {
  if (Array.isArray(name)) return name
  if (typeof name === 'string') return name.split('.')
  return []
}

function getMappedName(path, fieldAliases) {
  const dottedPath = path.join('.')
  const alias = fieldAliases?.[dottedPath]
  if (alias) {
    return toNamePath(alias)
  }

  if (path.length === 1 && ['item', 'detail'].includes(path[0])) {
    return []
  }

  return path
}

function pushFieldError(fieldMap, namePath, message) {
  const key = namePath.join('.')
  if (!fieldMap.has(key)) {
    fieldMap.set(key, { name: namePath, errors: [] })
  }
  const fieldError = fieldMap.get(key)
  if (!fieldError.errors.includes(message)) {
    fieldError.errors.push(message)
  }
}

export function resolveFormApiError(
  error,
  { fieldAliases = {}, messageFieldMap = [], fallbackGlobalMessage } = {},
) {
  const normalized = error?.normalizedError || normalizeApiError(error)
  const fieldMap = new Map()
  const unmatchedMessages = []

  normalized.issues.forEach((issue) => {
    if (!issue.location.length) {
      unmatchedMessages.push(issue.message)
      return
    }

    const mappedName = getMappedName(issue.location, fieldAliases)
    if (!mappedName.length) {
      unmatchedMessages.push(issue.message)
      return
    }

    pushFieldError(fieldMap, mappedName, issue.message)
  })

  if (!normalized.issues.length && normalized.globalMessage) {
    const matchedRule = messageFieldMap.find((rule) =>
      matchesFieldRule(normalized.globalMessage, rule),
    )

    if (matchedRule?.field) {
      pushFieldError(fieldMap, toNamePath(matchedRule.field), normalized.globalMessage)
    } else {
      unmatchedMessages.push(normalized.globalMessage)
    }
  }

  const fieldErrors = Array.from(fieldMap.values())
  const globalMessage =
    unmatchedMessages[0] ||
    (!fieldErrors.length ? normalized.summary || fallbackGlobalMessage : null) ||
    fallbackGlobalMessage ||
    null

  return {
    normalized,
    fieldErrors,
    globalMessage,
  }
}

export function applyFormApiError(
  form,
  error,
  { fieldAliases = {}, messageFieldMap = [], fallbackGlobalMessage } = {},
) {
  const resolved = resolveFormApiError(error, {
    fieldAliases,
    messageFieldMap,
    fallbackGlobalMessage,
  })

  if (resolved.fieldErrors.length) {
    form.setFields(resolved.fieldErrors)
  }

  return resolved
}
