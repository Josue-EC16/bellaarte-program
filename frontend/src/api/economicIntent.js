// Memory only: preserve the intent after an uncertain network failure. A confirmed
// success completes it, so an identical subsequent operation receives a new key.
const pending = new Map()

function canonical(value) {
  if (Array.isArray(value)) return value.map(canonical)
  if (value && typeof value === 'object') {
    return Object.fromEntries(Object.keys(value).sort().map((key) => [key, canonical(value[key])]))
  }
  return value
}

export function isEconomicWrite(config) {
  const method = (config.method || 'get').toLowerCase()
  if (!['post', 'patch'].includes(method)) return false
  return /^\/(economia\/|boutique\/sales(?:\/|$)|pedidos\/\d+\/pagos(?:\/|$)|fletes\/salidas(?:\/|$))/.test(config.url || '')
}

export function economicIntent(config, actor = 'session') {
  let data = config.data
  if (typeof data === 'string') {
    try { data = JSON.parse(data) } catch { /* Keep the literal body. */ }
  }
  const signature = JSON.stringify([actor, config.method?.toLowerCase(), config.url, canonical(data)])
  const scope = JSON.stringify([actor, config.method?.toLowerCase(), config.url])
  const previous = pending.get(scope)
  if (previous?.signature !== signature) pending.set(scope, { signature, key: crypto.randomUUID() })
  return { signature, key: pending.get(scope).key }
}

export function completeEconomicIntent(signature) {
  for (const [scope, intent] of pending) {
    if (intent.signature === signature) pending.delete(scope)
  }
}

export function clearEconomicIntents() {
  pending.clear()
}
