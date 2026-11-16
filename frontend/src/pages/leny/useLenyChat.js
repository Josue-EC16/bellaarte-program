import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { apiClient } from '../../api/client'
import { resolveFormApiError } from '../../components/forms/formErrorUtils'
import { lenyErrorMessage, lenyRetrySeconds, lenyStreamErrorMessage, sendLenyMessage } from './lenyTransport'

// Presentation of server-rendered scope, not a semantic quality score. Use
// freshly fetched source availability so revocation never keeps an old badge.
function persistedResponseScope(item) {
  if (item.role !== 'assistant' || item.status !== 'completed') return undefined
  const content = item.content || ''
  if (content.startsWith('**Orientación general — sin respaldo documental empresarial**')) return 'general'
  if ((content.startsWith('**Según la documentación**') || content.startsWith('La evidencia disponible es parcial;')) && item.sources?.some((source) => source.available)) {
    return content.includes('**Alcance:**') || content.includes('No he podido verificar') ? 'partial' : 'documented'
  }
  return undefined
}

export function useLenyChat() {
  const [status, setStatus] = useState(null)
  const [conversations, setConversations] = useState([])
  const [conversation, setConversation] = useState(null)
  const [draftProvider, setDraftProvider] = useState('ollama')
  const [messages, setMessages] = useState([])
  const [totalConversations, setTotalConversations] = useState(0)
  const [totalMessages, setTotalMessages] = useState(0)
  const [historyPage, setHistoryPage] = useState(1)
  const [messagePage, setMessagePage] = useState(1)
  const [busy, setBusy] = useState(false)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [fieldError, setFieldError] = useState('')
  const [retryAt, setRetryAt] = useState(0)
  const [retrySeconds, setRetrySeconds] = useState(0)
  const [retryProvider, setRetryProvider] = useState(null)
  const mounted = useRef(true)
  const generation = useRef(null)
  const selection = useRef(0)
  const historySelection = useRef(0)
  const activeConversation = useRef(null)
  const interruptedRequests = useRef(new Set())
  const provider = conversation?.llm_provider || (conversation ? 'ollama' : draftProvider)
  const providerStatus = useMemo(() => status?.providers?.find((item) => item.provider === provider)
    || (provider === 'ollama' ? status : { available: false, code: 'LENY_GEMINI_DISABLED', request_timeout_seconds: 300 }), [status, provider])
  const applicableRetrySeconds = !retryProvider || retryProvider === provider ? retrySeconds : 0

  useEffect(() => {
    if (!retryAt) return
    const update = () => {
      const seconds = Math.max(0, Math.ceil((retryAt - Date.now()) / 1000))
      setRetrySeconds(seconds)
      if (!seconds) setRetryAt(0)
    }
    update()
    const timer = setInterval(update, 250)
    return () => clearInterval(timer)
  }, [retryAt])

  const refreshStatus = useCallback(async () => {
    try {
      const response = await apiClient.get('/leny/status')
      if (mounted.current) setStatus(response.data)
    } catch {
      if (mounted.current) setStatus({ available: false, code: 'unavailable' })
    }
  }, [])

  const loadHistory = useCallback(async (page = 1) => {
    const current = ++historySelection.current
    try {
      const { data } = await apiClient.get('/leny/conversations', { params: { page, page_size: 20 } })
      if (mounted.current && current === historySelection.current) {
        setConversations(data.items); setTotalConversations(data.total); setHistoryPage(page)
      }
    } catch (failure) { if (mounted.current) setError(lenyErrorMessage(failure)) }
  }, [])

  const loadMessages = useCallback(async (id, page = 1, append = false, timeout = 2000) => {
    const current = ++selection.current
    setLoading(true)
    try {
      const { data } = await apiClient.get(`/leny/conversations/${id}`, { params: { page, page_size: 50 }, timeout })
      if (mounted.current && current === selection.current && activeConversation.current === id) {
        const items = data.items.map((record) => {
          const item = { ...record, responseScope: persistedResponseScope(record) }
          if (item.role !== 'assistant' || !interruptedRequests.current.has(item.request_id)) return item
          if (item.status !== 'generating') { interruptedRequests.current.delete(item.request_id); return item }
          return { ...item, cancellationPending: true }
        })
        setConversation(data.conversation)
        setMessages((previous) => append ? [...items, ...previous] : items)
        setTotalMessages(data.total); setMessagePage(page)
      }
      return data
    } catch (failure) {
      if (mounted.current && current === selection.current) setError(lenyErrorMessage(failure))
    } finally { if (mounted.current && current === selection.current) setLoading(false) }
  }, [])

  useEffect(() => {
    mounted.current = true
    refreshStatus(); loadHistory()
    return () => {
      mounted.current = false
      generation.current?.abort()
      selection.current += 1
      historySelection.current += 1
    }
  }, [loadHistory, refreshStatus])

  const stop = useCallback(() => generation.current?.abort(), [])
  const selectConversation = useCallback((item) => {
    stop(); selection.current += 1
    activeConversation.current = item.id
    setConversation(item); setMessages([]); setTotalMessages(0); setMessagePage(1); setError(''); setFieldError('')
    loadMessages(item.id)
  }, [loadMessages, stop])
  const newConversation = useCallback(() => {
    stop(); selection.current += 1
    activeConversation.current = null
    setDraftProvider('ollama')
    setConversation(null); setMessages([]); setTotalMessages(0); setMessagePage(1); setError(''); setFieldError(''); setLoading(false)
  }, [stop])

  const send = useCallback(async (text) => {
    if (generation.current || (retryAt > Date.now() && (!retryProvider || retryProvider === provider)) || !text.trim() || !providerStatus?.available) return false
    const controller = new AbortController()
    generation.current = controller
    setBusy(true); setError(''); setFieldError('')
    const requestId = crypto.randomUUID()
    let target = activeConversation.current
    let duplicateStatus = null
    const stillHere = () => mounted.current && activeConversation.current === target
    try {
      if (!target) {
        const options = provider === 'ollama' ? {} : { provider }
        const { data } = await apiClient.post('/leny/conversations', options, { signal: controller.signal })
        if (controller.signal.aborted || !mounted.current) return false
        target = data.id
        activeConversation.current = target
        setConversation(data)
        loadHistory()
      }
      const assistantId = `pending-${requestId}`
      setMessages((previous) => [...previous,
        { id: `user-${requestId}`, role: 'user', content: text.trim(), status: 'completed', request_id: requestId },
        { id: assistantId, role: 'assistant', content: '', status: 'generating', request_id: requestId },
      ])
      await sendLenyMessage({ conversation_id: target, request_id: requestId, message: text.trim() }, {
        signal: controller.signal, timeoutSeconds: providerStatus?.request_timeout_seconds || (provider === 'gemini' ? 300 : 120),
        onEvent: (event) => {
          if (!stillHere()) return
          if (event.type === 'delta') setMessages((previous) => previous.map((item) => item.id === assistantId
            ? { ...item, content: item.content + event.text } : item))
          if (event.type === 'done' || event.type === 'error') {
            setMessages((previous) => previous.map((item) => item.id === assistantId
              ? { ...item, status: event.type === 'error' ? 'failed' : event.status, outcome: event.outcome, reason_code: event.reason_code,
                responseScope: event.type === 'done' ? event.response_scope : undefined,
                sources: event.type === 'done' && event.status === 'completed' ? event.sources || [] : [] } : item))
          }
          if (event.type === 'error') setError(lenyStreamErrorMessage(event))
        },
      })
      return true
    } catch (failure) {
      if (controller.signal.aborted) interruptedRequests.current.add(requestId)
      if (stillHere()) {
        const duplicate = failure?.response?.data?.detail?.code === 'LENY_REQUEST_DUPLICATE'
        duplicateStatus = duplicate ? failure.response.data.detail.status : null
        const wait = lenyRetrySeconds(failure)
        if (wait) {
          setRetryProvider(failure?.response?.data?.detail?.code?.startsWith('LENY_GEMINI_') ? 'gemini' : null)
          setRetryAt(Date.now() + wait * 1000); setRetrySeconds(wait)
        }
        const validation = failure?.response?.status === 422 ? resolveFormApiError(failure) : null
        const messageIssue = validation?.fieldErrors.find((item) => item.name.join('.') === 'message')
        setFieldError(messageIssue?.errors.join(' ') || '')
        setError(messageIssue ? '' : duplicate
          ? 'Esta solicitud ya fue recibida. Se recuperó su estado del historial; no se generará de nuevo.'
          : controller.signal.aborted ? 'Se solicitó detener la respuesta. Su estado se confirmará en el historial.'
            : validation?.globalMessage || lenyErrorMessage(failure))
        setMessages((previous) => validation || failure?.response?.status ? previous.filter((item) => item.request_id !== requestId)
          : previous.map((item) => item.request_id === requestId && item.role === 'assistant'
            ? { ...item, status: controller.signal.aborted ? 'generating' : 'failed', cancellationPending: controller.signal.aborted } : item))
      }
      return false
    } finally {
      if (mounted.current) {
        // Closing the HTTP stream precedes server cleanup. Poll only the same
        // cancelled request, within a short deadline; never regenerate it.
        if (target && stillHere()) {
          if (controller.signal.aborted) interruptedRequests.current.add(requestId)
          const deadline = Date.now() + 2000
          if (duplicateStatus) await loadHistory()
          let data = await loadMessages(target)
          if (stillHere() && ['failed', 'interrupted', 'admitted'].includes(duplicateStatus)
            && data && !data.items.some((item) => item.request_id === requestId)) {
            setError(`La solicitud anterior ${duplicateStatus === 'failed' ? 'falló' : duplicateStatus === 'interrupted' ? 'se interrumpió' : 'fue recibida'} y no tiene mensajes guardados. Para intentarlo otra vez, envía un nuevo mensaje; se creará una nueva solicitud.`)
          }
          for (let attempt = 0; controller.signal.aborted && attempt < 4 && stillHere(); attempt += 1) {
            const assistant = data?.items.find((item) => item.request_id === requestId && item.role === 'assistant')
            if (assistant?.status !== 'generating' || Date.now() >= deadline) break
            await new Promise((resolve) => setTimeout(resolve, 150))
            if (!stillHere()) break
            data = await loadMessages(target, 1, false, Math.max(1, deadline - Date.now()))
          }
        }
        loadHistory(); refreshStatus()
      }
      generation.current = null
      if (mounted.current) setBusy(false)
    }
  }, [loadHistory, loadMessages, refreshStatus, provider, providerStatus, retryAt, retryProvider])

  const deleteConversation = useCallback(async (item) => {
    try {
      await apiClient.delete(`/leny/conversations/${item.id}`)
      if (activeConversation.current === item.id) newConversation()
      await loadHistory(1)
    } catch (failure) { if (mounted.current) setError(lenyErrorMessage(failure)) }
  }, [loadHistory, newConversation])

  return { status, provider, providerStatus, conversations, conversation, messages, busy, loading, error, fieldError, retrySeconds: applicableRetrySeconds,
    selectProvider: (value) => {
      if (!conversation && !generation.current && ['ollama', 'gemini'].includes(value)
          && (value === 'ollama' || status?.providers?.some((item) => item.provider === value && item.available))) {
        setDraftProvider(value)
      }
    },
    clearFieldError: () => setFieldError(''),
    totalConversations, totalMessages, historyPage, refreshStatus, loadHistory,
    selectConversation, newConversation, send, stop, deleteConversation,
    refreshConversation: () => conversation && loadMessages(conversation.id),
    loadOlderMessages: () => conversation && loadMessages(conversation.id, messagePage + 1, true),
  }
}
