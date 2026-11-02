import { DeleteOutlined, PlusOutlined, ReloadOutlined, SendOutlined, SettingOutlined, StopOutlined } from '@ant-design/icons'
import { Alert, App, Button, Descriptions, Drawer, Input, Pagination, Spin, Tag, Typography } from 'antd'
import { useEffect, useRef, useState } from 'react'
import { apiClient } from '../../api/client'
import { useAuth } from '../../auth/AuthProvider'
import { FormProcessAlert } from '../../components/forms/FormProcessAlert'
import { LenyMarkdown } from './LenyMarkdown'
import { LenySources } from './LenySources'
import { lenyErrorMessage } from './lenyTransport'
import { useLenyChat } from './useLenyChat'
import './leny.css'

const messageState = { generating: 'Preparando respuesta…', interrupted: 'Respuesta interrumpida', failed: 'Respuesta incompleta' }

export function LenyPage() {
  const { user } = useAuth()
  return <LenySession key={user?.id ?? user?.username ?? 'session'} />
}

function LenySession() {
  const chat = useLenyChat()
  const { user } = useAuth()
  const { modal } = App.useApp()
  const [draft, setDraft] = useState('')
  const [adminOpen, setAdminOpen] = useState(false)
  const [adminConfig, setAdminConfig] = useState(null)
  const [adminError, setAdminError] = useState('')
  const [followBottom, setFollowBottom] = useState(true)
  const scroll = useRef(null)
  const composer = useRef(null)
  const composing = useRef(false)
  const conversationView = useRef(0)
  const limit = chat.status?.max_message_chars || 2000

  useEffect(() => {
    if (followBottom && scroll.current) scroll.current.scrollTop = scroll.current.scrollHeight
  }, [chat.messages, followBottom])

  async function submit(event) {
    event?.preventDefault()
    if (chat.busy || chat.loading || chat.retrySeconds > 0 || !draft.trim() || draft.length > limit) return
    const text = draft
    const view = conversationView.current
    setDraft(''); setFollowBottom(true)
    const sent = await chat.send(text)
    if (view === conversationView.current) {
      if (!sent) setDraft((current) => current || text)
      composer.current?.focus()
    }
  }

  function remove(item) {
    modal.confirm({ title: '¿Eliminar esta conversación?',
      content: 'Se eliminarán definitivamente sus mensajes. Esta acción no se puede deshacer.',
      okText: 'Eliminar', cancelText: 'Conservar', okButtonProps: { danger: true },
      onOk: () => chat.deleteConversation(item),
    })
  }

  async function openAdmin() {
    setAdminOpen(true); setAdminConfig(null); setAdminError('')
    try { setAdminConfig((await apiClient.get('/leny/admin/config')).data) }
    catch (error) { setAdminError(lenyErrorMessage(error)) }
  }

  return <section className="leny" aria-label="Asistente LENY">
    <aside className="leny-history" aria-label="Mis conversaciones">
      <div className="leny-history-heading"><span className="leny-eyebrow">TU ESPACIO</span>
        <Button type="text" icon={<ReloadOutlined />} aria-label="Actualizar conversaciones" onClick={() => chat.loadHistory(chat.historyPage)} />
      </div>
      <Button type="primary" block icon={<PlusOutlined />} onClick={() => { conversationView.current += 1; chat.newConversation(); setDraft(''); setFollowBottom(true); composer.current?.focus() }}>Nueva conversación</Button>
      <div className="leny-history-list">
        {chat.conversations.map((item) => <div key={item.id} className={`leny-history-item ${chat.conversation?.id === item.id ? 'is-selected' : ''}`}>
          <button className="leny-history-select" onClick={() => { conversationView.current += 1; chat.selectConversation(item); setDraft(''); setFollowBottom(true) }} aria-current={chat.conversation?.id === item.id ? 'true' : undefined}>
            <span>{item.title || 'Conversación'}</span>
            <small>{new Date(item.updated_at || item.created_at).toLocaleDateString('es-BO', { day: 'numeric', month: 'short' })}</small>
          </button>
          <Button type="text" size="small" icon={<DeleteOutlined />} aria-label={`Eliminar ${item.title || 'conversación'}`} disabled={chat.busy && chat.conversation?.id === item.id} onClick={() => remove(item)} />
        </div>)}
        {!chat.conversations.length && <p className="leny-history-empty">Tus conversaciones aparecerán aquí.</p>}
      </div>
      {chat.totalConversations > 20 && <Pagination size="small" simple current={chat.historyPage} total={chat.totalConversations} pageSize={20} onChange={chat.loadHistory} />}
      <p className="leny-history-note">Historial privado de tu cuenta.<br />Puedes eliminarlo cuando lo necesites.</p>
    </aside>

    <div className="leny-workspace">
      <header className="leny-header">
        <div className="leny-brand"><span className="leny-monogram" aria-hidden="true">L</span><div><h1>LENY</h1><span>Asistente de BELLAARTE BOUTIQUE</span></div></div>
        <div className="leny-header-actions">
          <Tag color={chat.status?.available ? 'success' : 'default'}>{chat.status === null ? 'Conectando' : chat.status.available ? 'Modelo local disponible' : 'Sin conexión al modelo'}</Tag>
          <Button type="text" icon={<ReloadOutlined />} aria-label="Comprobar servicio" onClick={chat.refreshStatus} />
          {user?.permissions?.includes('leny:admin') && <Button type="text" icon={<SettingOutlined />} aria-label="Administración de LENY" onClick={openAdmin} />}
        </div>
      </header>

      {chat.error && <div className="leny-alert"><FormProcessAlert title="LENY no pudo completar la solicitud." message={chat.error} style={{ marginBottom: 8 }} />
        {chat.conversation && <Button size="small" disabled={chat.busy} onClick={chat.refreshConversation}>Consultar historial</Button>}</div>}
      <div ref={scroll} className="leny-messages" role="log" aria-label="Mensajes de la conversación" aria-busy={chat.busy}
        onScroll={() => { const element = scroll.current; setFollowBottom(element.scrollHeight - element.scrollTop - element.clientHeight < 80) }}>
        {chat.totalMessages > chat.messages.length && <Button className="leny-older" size="small" loading={chat.loading} disabled={chat.busy} onClick={() => { setFollowBottom(false); chat.loadOlderMessages() }}>Ver mensajes anteriores</Button>}
        {chat.loading && <div className="leny-loading"><Spin size="small" /> Recuperando conversación…</div>}
        {!chat.messages.length && !chat.loading && <div className="leny-welcome">
          <span className="leny-eyebrow">UNA CONVERSACIÓN, NUEVAS IDEAS</span>
          <h2>Hola, soy LENY.<br /><span>¿En qué te puedo ayudar?</span></h2>
          <p>Podemos organizar tareas de la Boutique y el Taller, redactar mensajes para clientas y preparar ideas para el trabajo de BELLAARTE BOUTIQUE.</p>
          <div className="leny-suggestions">
            {['Ayúdame a redactar un mensaje de bienvenida para una clienta.', '¿Cómo puedo organizar las tareas de mi jornada?'].map((suggestion) => <button key={suggestion} onClick={() => { setDraft(suggestion); composer.current?.focus() }}>{suggestion}<span aria-hidden="true">↗</span></button>)}
          </div>
          <p className="leny-limit-note">Puedo consultar documentos publicados para tu rol. No consulto tablas del ERP ni realizo operaciones administrativas.</p>
        </div>}
        {chat.messages.map((item) => <article key={item.id} className={`leny-message leny-message-${item.role}`} aria-label={item.role === 'user' ? 'Tu mensaje' : 'Respuesta de LENY'}>
          <div className="leny-message-author">{item.role === 'user' ? 'TÚ' : 'LENY'}</div>
          <div className="leny-message-body">{item.role === 'assistant'
            ? <LenyMarkdown>{item.content || (item.cancellationPending ? 'Esperando confirmación del servidor…' : item.status === 'generating' ? 'Preparando respuesta…' : 'No se recibió texto de respuesta.')}</LenyMarkdown>
            : <p>{item.content}</p>}</div>
          {item.status !== 'completed' && messageState[item.status] && <small className="leny-message-state">{item.cancellationPending ? 'Interrupción pendiente' : messageState[item.status]}</small>}
          {item.role === 'assistant' && <LenySources key={`${chat.conversation?.id}:${item.id}`} sources={item.sources} status={item.status} />}
        </article>)}
      </div>

      <div className="leny-composer-area">
        {!followBottom && chat.messages.length > 0 && <Button size="small" className="leny-jump" onClick={() => setFollowBottom(true)}>Ir al final ↓</Button>}
        <form className="leny-composer" onSubmit={submit}>
          <Input.TextArea ref={composer} value={draft} onChange={(event) => { setDraft(event.target.value); chat.clearFieldError() }} autoSize={{ minRows: 2, maxRows: 6 }} maxLength={limit} aria-label="Mensaje para LENY" placeholder="Escribe tu mensaje a LENY…"
            aria-invalid={Boolean(chat.fieldError)} aria-describedby={chat.fieldError ? 'leny-message-error' : 'leny-composer-help'} status={chat.fieldError ? 'error' : undefined}
            onCompositionStart={() => { composing.current = true }} onCompositionEnd={() => { composing.current = false }}
            onKeyDown={(event) => { if (event.key === 'Enter' && !event.shiftKey && !composing.current && !event.nativeEvent.isComposing) { event.preventDefault(); submit() } }} />
          {chat.fieldError && <p id="leny-message-error" className="leny-field-error" role="alert">{chat.fieldError}</p>}
          <div className="leny-composer-bottom"><span>{draft.length}/{limit}<span className="leny-keyboard-help"> · Enter envía · Mayús + Enter nueva línea</span></span>
            {chat.busy ? <Button icon={<StopOutlined />} onClick={chat.stop}>Detener</Button>
              : <Button htmlType="submit" type="primary" icon={<SendOutlined />} disabled={chat.loading || chat.retrySeconds > 0 || !draft.trim() || draft.length > limit || !chat.status?.available}>{chat.retrySeconds > 0 ? `Espera ${chat.retrySeconds} s` : 'Enviar'}</Button>}
          </div>
        </form>
        <p id="leny-composer-help" className="leny-disclaimer">LENY puede equivocarse. Verifica la información y evita compartir contraseñas o datos sensibles.</p>
      </div>
    </div>

    <Drawer title="Administración de LENY" open={adminOpen} onClose={() => setAdminOpen(false)} width={480}>
      <Typography.Paragraph>Configuración efectiva del servicio local. Los cambios se realizan mediante la configuración del backend.</Typography.Paragraph>
      {adminError ? <Alert type="error" message={adminError} showIcon /> : adminConfig ? <Descriptions column={1} bordered size="small"
        items={Object.entries(adminConfig).map(([key, value]) => ({ key, label: key, children: String(value) }))} /> : <Spin />}
    </Drawer>
  </section>
}
