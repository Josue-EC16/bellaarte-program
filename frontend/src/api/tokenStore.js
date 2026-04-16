let accessToken = null
let refreshHandler = null

export function getAccessToken() {
  return accessToken
}

export function setAccessToken(token) {
  accessToken = token
}

export function clearAccessToken() {
  accessToken = null
}

export function registerRefreshHandler(handler) {
  refreshHandler = handler
}

export async function runRefreshHandler() {
  if (!refreshHandler) {
    throw new Error('No existe un handler de refresh registrado')
  }

  return refreshHandler()
}
