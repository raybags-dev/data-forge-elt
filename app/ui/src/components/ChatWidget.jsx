import React, { useCallback, useEffect, useRef, useState } from 'react'

const PORTFOLIO_WS   = 'wss://raybags.com/ws'
const CHAT_REST_BASE = '/chat/api/v1/sessions'
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
function clearSession(keepName) {
  localStorage.removeItem(LS_MSGS)
  localStorage.removeItem(LS_SID)
  if (!keepName) localStorage.removeItem(LS_NAME)
}

function SendIcon() {
  return (
    <svg width="15" height="15" viewBox="0 0 24 24" fill="currentColor">
      <path d="M2.01 21L23 12 2.01 3 2 10l15 2-15 2z" />
    </svg>
  )
}

export default function ChatWidget({ isOpen, onClose, onOpen, preMessage }) {
  const [msgs, setMsgs]         = useState(() => loadCached())
  const [input, setInput]       = useState('')
  const [name, setName]         = useState(() => localStorage.getItem(LS_NAME))
  const [nameFlow, setNameFlow] = useState(() => localStorage.getItem(LS_NAME) ? 'done' : 'idle')
  const [endFlow, setEndFlow]   = useState('idle')  // 'idle' | 'confirming'
  const [connected, setConnected] = useState(false)

  const wsRef       = useRef(null)
  const sidRef      = useRef(getOrCreateSid())
  const bottomRef   = useRef(null)
  const preSent     = useRef(false)
  const systemShown = useRef(false)

  const addMsg = useCallback((msg) => {
    setMsgs(prev => {
      const next = [...prev, msg]
      saveCached(next)
      return next
    })
  }, [])

  const connect = useCallback((visitorName) => {
    if (wsRef.current && wsRef.current.readyState <= WebSocket.OPEN) return
    const sid = sidRef.current
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
        // Server sends type:"msg" — also accept legacy "greeting"/"message" variants
        if (data.type === 'msg' || data.type === 'greeting' || data.type === 'message') {
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

  useEffect(() => {
    if (connected && preMessage && !preSent.current) {
      preSent.current = true
      setTimeout(() => {
        if (wsRef.current?.readyState === WebSocket.OPEN) {
          // Must use type:"msg" — server ignores any other type
          wsRef.current.send(JSON.stringify({ type: 'msg', content: preMessage }))
          addMsg({ id: genId(), sender: 'user', content: preMessage, ts: Date.now() / 1000 })
        }
      }, 600)
    }
  }, [connected, preMessage, addMsg])

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [msgs, endFlow])

  function handleSend() {
    const text = input.trim()
    if (!text || wsRef.current?.readyState !== WebSocket.OPEN) return
    // Server only processes type:"msg" — "message" or "greeting" are silently dropped
    wsRef.current.send(JSON.stringify({ type: 'msg', content: text }))
    addMsg({ id: genId(), sender: 'user', content: text, ts: Date.now() / 1000 })
    setInput('')
    setEndFlow('idle')
  }

  function handleNameSubmit(e) {
    e.preventDefault()
    const val = e.target.nameInput.value.trim()
    if (!val) return
    localStorage.setItem(LS_NAME, val)
    setName(val)
    setNameFlow('done')
  }

  function handleEndSession() {
    wsRef.current?.close()
    wsRef.current = null
    clearSession(true)
    const newSid = genId()
    localStorage.setItem(LS_SID, newSid)
    sidRef.current = newSid
    systemShown.current = false
    preSent.current = false
    setMsgs([])
    setConnected(false)
    setEndFlow('idle')
    onClose()
  }

  function handleDeleteData() {
    const sid = sidRef.current
    fetch(`${CHAT_REST_BASE}/${sid}/messages`, { method: 'DELETE' }).catch(() => {})
    wsRef.current?.close()
    wsRef.current = null
    clearSession(false)
    const newSid = genId()
    localStorage.setItem(LS_SID, newSid)
    sidRef.current = newSid
    systemShown.current = false
    preSent.current = false
    setMsgs([])
    setName(null)
    setNameFlow('idle')
    setConnected(false)
    setEndFlow('idle')
    onClose()
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

      {/* Header */}
      <div style={{
        flexShrink: 0,
        padding: '11px 14px',
        background: 'linear-gradient(135deg, #6366f1, #8b5cf6)',
        display: 'flex', alignItems: 'center', gap: 10,
      }}>
        <div style={{
          width: 34, height: 34, borderRadius: '50%',
          background: 'rgba(255,255,255,0.2)',
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          fontSize: 16, flexShrink: 0,
        }}>💬</div>
        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{ color: '#fff', fontWeight: 600, fontSize: 13, lineHeight: 1.3 }}>Chat with Raybags</div>
          <div style={{ color: 'rgba(255,255,255,0.75)', fontSize: 11 }}>
            <span style={{ marginRight: 3, fontSize: 8 }}>{connected ? '●' : '○'}</span>
            {connected ? 'Online' : 'Connecting…'}
          </div>
        </div>
        {/* End chat button */}
        <button
          onClick={() => setEndFlow(f => f === 'confirming' ? 'idle' : 'confirming')}
          style={{
            background: 'rgba(255,255,255,0.15)', border: 'none', color: '#fff',
            cursor: 'pointer', borderRadius: 6,
            padding: '4px 8px', fontSize: 11, fontWeight: 500,
            flexShrink: 0,
          }}
        >End chat</button>
        <button
          onClick={onClose}
          style={{
            background: 'rgba(255,255,255,0.15)', border: 'none', color: '#fff',
            cursor: 'pointer', width: 26, height: 26, borderRadius: '50%',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            fontSize: 15, lineHeight: 1, flexShrink: 0,
          }}
        >×</button>
      </div>

      {/* Name prompt */}
      {nameFlow !== 'done' && (
        <form
          onSubmit={handleNameSubmit}
          style={{
            flexShrink: 0,
            padding: '10px 14px', borderBottom: '1px solid #2d2d44',
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
            <button type="submit" style={{
              flexShrink: 0,
              background: 'linear-gradient(135deg, #6366f1, #8b5cf6)',
              border: 'none', borderRadius: 8, color: '#fff',
              padding: '7px 14px', fontSize: 13, cursor: 'pointer', fontWeight: 600,
            }}>Go</button>
          </div>
        </form>
      )}

      {/* Messages — flex:1 + minHeight:0 is required for overflow scroll to work */}
      <div style={{
        flex: 1, minHeight: 0, overflowY: 'auto',
        padding: '12px 14px',
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
                maxWidth: '78%', padding: '8px 12px', fontSize: 13,
                lineHeight: 1.45, wordBreak: 'break-word',
                borderRadius: 14,
                borderBottomRightRadius: isUser ? 4 : 14,
                borderBottomLeftRadius: isUser ? 14 : 4,
                background: isUser ? 'linear-gradient(135deg, #6366f1, #8b5cf6)' : '#1e1e3a',
                color: '#e2e8f0',
                border: isUser ? 'none' : '1px solid #2d2d44',
              }}>
                {m.content}
              </div>
            </div>
          )
        })}

        {/* End-session confirmation card (inline in message area) */}
        {endFlow === 'confirming' && (
          <div style={{
            margin: '4px 0',
            background: '#1e1e3a', border: '1px solid #3730a3',
            borderRadius: 12, padding: '12px 14px',
            display: 'flex', flexDirection: 'column', gap: 10,
          }}>
            <p style={{ margin: 0, fontSize: 12, color: '#94a3b8', textAlign: 'center' }}>
              How would you like to end this chat?
            </p>
            <div style={{ display: 'flex', gap: 8 }}>
              <button
                onClick={handleEndSession}
                style={{
                  flex: 1, padding: '8px 0', borderRadius: 8, fontSize: 12, fontWeight: 600,
                  background: '#1a1a2e', border: '1px solid #3730a3',
                  color: '#e2e8f0', cursor: 'pointer',
                }}
              >End session</button>
              <button
                onClick={handleDeleteData}
                style={{
                  flex: 1, padding: '8px 0', borderRadius: 8, fontSize: 12, fontWeight: 600,
                  background: 'rgba(239,68,68,0.1)', border: '1px solid rgba(239,68,68,0.35)',
                  color: '#f87171', cursor: 'pointer',
                }}
              >Delete my data</button>
            </div>
            <button
              onClick={() => setEndFlow('idle')}
              style={{
                background: 'none', border: 'none', color: '#64748b',
                fontSize: 12, cursor: 'pointer', textAlign: 'center', padding: '2px 0',
              }}
            >Cancel</button>
          </div>
        )}

        <div ref={bottomRef} />
      </div>

      {/* Input bar — always anchored at bottom */}
      <div style={{
        flexShrink: 0,
        padding: '9px 12px', borderTop: '1px solid #2d2d44',
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
            cursor: 'pointer',
            opacity: (!connected || !input.trim() || nameFlow !== 'done') ? 0.4 : 1,
          }}
        >
          <SendIcon />
        </button>
      </div>
    </div>
  )
}
