import React, { useCallback, useEffect, useRef, useState } from 'react'

const PORTFOLIO_WS = 'wss://raybags.com/ws'
const LS_SID  = 'df_chat_sid'
const LS_NAME = 'df_chat_name'
const LS_MSGS = 'df_chat_msgs'

function genId() {
  return Math.random().toString(36).slice(2, 9) + Date.now().toString(36)
}
function getOrCreateSid() {
  let id = localStorage.getItem(LS_SID)
  if (!id) { id = genId(); localStorage.setItem(LS_SID, id) }
  return id
}
function loadCached() {
  try { return JSON.parse(localStorage.getItem(LS_MSGS) || '[]') } catch { return [] }
}
function saveCached(msgs) {
  try { localStorage.setItem(LS_MSGS, JSON.stringify(msgs.slice(-80))) } catch {}
}

function SendIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor">
      <path d="M2.01 21L23 12 2.01 3 2 10l15 2-15 2z" />
    </svg>
  )
}

export default function ChatWidget({ isOpen, onClose, onOpen, preMessage }) {
  const [msgs, setMsgs]       = useState(() => loadCached())
  const [input, setInput]     = useState('')
  const [name, setName]       = useState(() => localStorage.getItem(LS_NAME))
  const [nameFlow, setNameFlow] = useState(() => localStorage.getItem(LS_NAME) ? 'done' : 'idle')
  const [connected, setConnected] = useState(false)

  const wsRef          = useRef(null)
  const bottomRef      = useRef(null)
  const preSent        = useRef(false)
  const systemShown    = useRef(false)   // prevents duplicate "Connected" messages

  const addMsg = useCallback((msg) => {
    setMsgs(prev => {
      const next = [...prev, msg]
      saveCached(next)
      return next
    })
  }, [])

  // Stable connect — no dependency on msgs state
  const connect = useCallback((visitorName) => {
    // Guard: CONNECTING=0 or OPEN=1
    if (wsRef.current && wsRef.current.readyState <= WebSocket.OPEN) return
    const sid = getOrCreateSid()
    const url = visitorName && visitorName !== 'visitor'
      ? `${PORTFOLIO_WS}/${sid}?name=${encodeURIComponent(visitorName)}`
      : `${PORTFOLIO_WS}/${sid}`
    const ws = new WebSocket(url)
    wsRef.current = ws
    ws.onopen = () => {
      setConnected(true)
      if (!systemShown.current) {
        systemShown.current = true
        addMsg({ id: genId(), sender: 'system', content: "Connected to Raybags' chat.", ts: Date.now() / 1000 })
      }
    }
    ws.onmessage = (e) => {
      try {
        const data = JSON.parse(e.data)
        if (data.type === 'greeting' || data.type === 'message' || data.type === 'msg') {
          addMsg({ id: genId(), sender: data.sender ?? 'agent', content: data.content ?? data.message ?? '', ts: data.ts ?? Date.now() / 1000 })
        }
      } catch {
        addMsg({ id: genId(), sender: 'agent', content: e.data, ts: Date.now() / 1000 })
      }
    }
    ws.onclose = () => setConnected(false)
    ws.onerror = () => setConnected(false)
  }, [addMsg])

  useEffect(() => {
    if (isOpen && nameFlow === 'done') connect(name)
    return () => {
      if (!isOpen && wsRef.current) {
        wsRef.current.close()
        wsRef.current = null
        setConnected(false)
      }
    }
  }, [isOpen, nameFlow, name, connect])

  // Auto-send preMessage once connected
  useEffect(() => {
    if (connected && preMessage && !preSent.current) {
      preSent.current = true
      setTimeout(() => {
        if (wsRef.current?.readyState === WebSocket.OPEN) {
          wsRef.current.send(JSON.stringify({ type: 'message', content: preMessage }))
          addMsg({ id: genId(), sender: 'user', content: preMessage, ts: Date.now() / 1000 })
        }
      }, 600)
    }
  }, [connected, preMessage, addMsg])

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [msgs])

  function handleSend() {
    const text = input.trim()
    if (!text || wsRef.current?.readyState !== WebSocket.OPEN) return
    wsRef.current.send(JSON.stringify({ type: 'message', content: text }))
    addMsg({ id: genId(), sender: 'user', content: text, ts: Date.now() / 1000 })
    setInput('')
  }

  function handleNameSubmit(e) {
    e.preventDefault()
    const val = e.target.nameInput.value.trim()
    if (!val) return
    localStorage.setItem(LS_NAME, val)
    setName(val)
    setNameFlow('done')
  }

  // ── FAB ────────────────────────────────────────────────────────────────────
  if (!isOpen) {
    return (
      <button
        onClick={onOpen}
        title="Chat with Raybags"
        style={{
          position: 'fixed', bottom: 24, right: 24, zIndex: 9000,
          width: 56, height: 56, borderRadius: '50%',
          background: 'linear-gradient(135deg, #6366f1, #8b5cf6)',
          border: 'none', cursor: 'pointer',
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          boxShadow: '0 4px 20px rgba(99,102,241,0.5)',
          color: '#fff', fontSize: 22,
        }}
      >
        💬
      </button>
    )
  }

  // ── Chat panel ─────────────────────────────────────────────────────────────
  return (
    <div style={{
      position: 'fixed', bottom: 24, right: 24, zIndex: 9000,
      width: 360, height: 520, borderRadius: 16,
      background: '#0f1117', border: '1px solid #2d2d44',
      boxShadow: '0 8px 40px rgba(0,0,0,0.6)',
      display: 'flex', flexDirection: 'column',
      overflow: 'hidden',
    }}>

      {/* Header — fixed height */}
      <div style={{
        flexShrink: 0,
        padding: '12px 16px',
        background: 'linear-gradient(135deg, #6366f1, #8b5cf6)',
        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <div style={{
            width: 36, height: 36, borderRadius: '50%',
            background: 'rgba(255,255,255,0.2)',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            fontSize: 16,
          }}>💬</div>
          <div>
            <div style={{ color: '#fff', fontWeight: 600, fontSize: 14, lineHeight: 1.3 }}>Chat with Raybags</div>
            <div style={{ color: 'rgba(255,255,255,0.75)', fontSize: 11 }}>
              <span style={{ marginRight: 4, fontSize: 8 }}>{connected ? '●' : '○'}</span>
              {connected ? 'Online' : 'Connecting…'}
            </div>
          </div>
        </div>
        <button
          onClick={onClose}
          style={{
            background: 'rgba(255,255,255,0.15)', border: 'none', color: '#fff',
            cursor: 'pointer', width: 28, height: 28, borderRadius: '50%',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            fontSize: 16, lineHeight: 1,
          }}
        >×</button>
      </div>

      {/* Name prompt — fixed height, only shown when needed */}
      {nameFlow !== 'done' && (
        <form
          onSubmit={handleNameSubmit}
          style={{
            flexShrink: 0,
            padding: '12px 16px', borderBottom: '1px solid #2d2d44',
            display: 'flex', flexDirection: 'column', gap: 8,
          }}
        >
          <p style={{ color: '#a5b4fc', fontSize: 13, margin: 0 }}>What should I call you?</p>
          <div style={{ display: 'flex', gap: 8 }}>
            <input
              name="nameInput"
              autoFocus
              placeholder="Your name"
              style={{
                flex: 1, minWidth: 0,
                background: '#1a1a2e', border: '1px solid #3730a3', borderRadius: 8,
                color: '#e2e8f0', padding: '7px 11px', fontSize: 13, outline: 'none',
              }}
            />
            <button
              type="submit"
              style={{
                flexShrink: 0,
                background: 'linear-gradient(135deg, #6366f1, #8b5cf6)',
                border: 'none', borderRadius: 8, color: '#fff',
                padding: '7px 14px', fontSize: 13, cursor: 'pointer', fontWeight: 600,
              }}
            >Go</button>
          </div>
        </form>
      )}

      {/* Messages — flex: 1 + minHeight: 0 is the critical combo for overflow to work */}
      <div style={{
        flex: 1, minHeight: 0, overflowY: 'auto',
        padding: '12px 16px',
        display: 'flex', flexDirection: 'column', gap: 6,
      }}>
        {msgs.map(m => {
          if (m.sender === 'system') {
            return (
              <div key={m.id} style={{ display: 'flex', justifyContent: 'center', padding: '4px 0' }}>
                <span style={{
                  fontSize: 11, color: '#64748b', fontStyle: 'italic',
                  background: '#1a1a2e', border: '1px solid #2d2d44',
                  padding: '3px 10px', borderRadius: 20,
                }}>{m.content}</span>
              </div>
            )
          }
          const isUser = m.sender === 'user'
          return (
            <div key={m.id} style={{ display: 'flex', justifyContent: isUser ? 'flex-end' : 'flex-start' }}>
              <div style={{
                maxWidth: '78%', padding: '8px 12px', borderRadius: 14,
                borderBottomRightRadius: isUser ? 4 : 14,
                borderBottomLeftRadius: isUser ? 14 : 4,
                fontSize: 13, lineHeight: 1.45, wordBreak: 'break-word',
                background: isUser ? 'linear-gradient(135deg, #6366f1, #8b5cf6)' : '#1e1e3a',
                color: '#e2e8f0',
                border: isUser ? 'none' : '1px solid #2d2d44',
              }}>
                {m.content}
              </div>
            </div>
          )
        })}
        <div ref={bottomRef} />
      </div>

      {/* Input bar — fixed height, always at bottom */}
      <div style={{
        flexShrink: 0,
        padding: '10px 12px', borderTop: '1px solid #2d2d44',
        background: '#0d0f18',
        display: 'flex', alignItems: 'center', gap: 8,
      }}>
        <input
          value={input}
          onChange={e => setInput(e.target.value)}
          onKeyDown={e => e.key === 'Enter' && !e.shiftKey && handleSend()}
          placeholder={connected ? 'Type a message…' : 'Connecting…'}
          disabled={!connected || nameFlow !== 'done'}
          style={{
            flex: 1, minWidth: 0,
            background: '#1a1a2e', border: '1px solid #3730a3', borderRadius: 10,
            color: '#e2e8f0', padding: '9px 13px', fontSize: 13,
            outline: 'none',
            opacity: (connected && nameFlow === 'done') ? 1 : 0.45,
          }}
        />
        <button
          onClick={handleSend}
          disabled={!connected || !input.trim() || nameFlow !== 'done'}
          style={{
            flexShrink: 0,
            width: 38, height: 38, borderRadius: 10,
            background: 'linear-gradient(135deg, #6366f1, #8b5cf6)',
            border: 'none', color: '#fff',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            cursor: 'pointer', transition: 'opacity 0.15s',
            opacity: (!connected || !input.trim() || nameFlow !== 'done') ? 0.4 : 1,
          }}
        >
          <SendIcon />
        </button>
      </div>
    </div>
  )
}
