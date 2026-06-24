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
function getSavedName() { return localStorage.getItem(LS_NAME) }
function persistName(n) { localStorage.setItem(LS_NAME, n) }
function loadCached() {
  try { return JSON.parse(localStorage.getItem(LS_MSGS) || '[]') } catch { return [] }
}
function saveCached(msgs) {
  try { localStorage.setItem(LS_MSGS, JSON.stringify(msgs.slice(-80))) } catch {}
}

export default function ChatWidget({ isOpen, onClose, onOpen, preMessage }) {
  const [msgs, setMsgs] = useState(() => loadCached())
  const [input, setInput] = useState('')
  const [name, setName] = useState(() => getSavedName())
  const [nameFlow, setNameFlow] = useState(getSavedName() ? 'done' : 'idle')
  const [connected, setConnected] = useState(false)
  const wsRef = useRef(null)
  const bottomRef = useRef(null)
  const preSent = useRef(false)

  const addMsg = useCallback((msg) => {
    setMsgs(prev => {
      const next = [...prev, msg]
      saveCached(next)
      return next
    })
  }, [])

  const connect = useCallback((visitorName) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) return
    const sid = getOrCreateSid()
    const url = visitorName && visitorName !== 'visitor'
      ? `${PORTFOLIO_WS}/${sid}?name=${encodeURIComponent(visitorName)}`
      : `${PORTFOLIO_WS}/${sid}`
    const ws = new WebSocket(url)
    ws.onopen = () => {
      setConnected(true)
      if (msgs.length === 0) {
        addMsg({ id: genId(), sender: 'system', content: "Connected to Raybags' chat.", ts: Date.now() / 1000 })
      }
    }
    ws.onmessage = (e) => {
      try {
        const data = JSON.parse(e.data)
        if (data.type === 'greeting' || data.type === 'message') {
          addMsg({ id: genId(), sender: data.sender ?? 'agent', content: data.content ?? data.message ?? '', ts: data.ts ?? Date.now() / 1000 })
        }
      } catch {
        addMsg({ id: genId(), sender: 'agent', content: e.data, ts: Date.now() / 1000 })
      }
    }
    ws.onclose = () => setConnected(false)
    ws.onerror = () => setConnected(false)
    wsRef.current = ws
  }, [msgs.length, addMsg])

  useEffect(() => {
    if (isOpen && nameFlow === 'done') {
      connect(name)
    }
    return () => {
      if (!isOpen && wsRef.current) {
        wsRef.current.close()
        wsRef.current = null
        setConnected(false)
      }
    }
  }, [isOpen, nameFlow, name, connect])

  // Send pre-message once connected
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
    if (!text || !wsRef.current) return
    wsRef.current.send(JSON.stringify({ type: 'message', content: text }))
    addMsg({ id: genId(), sender: 'user', content: text, ts: Date.now() / 1000 })
    setInput('')
  }

  function handleNameSubmit(e) {
    e.preventDefault()
    const val = e.target.nameInput.value.trim()
    if (!val) return
    persistName(val)
    setName(val)
    setNameFlow('done')
    connect(val)
  }

  if (!isOpen) {
    return (
      <button
        onClick={onOpen}
        title="Chat with Raybags"
        style={{
          position: 'fixed', bottom: 24, right: 24, zIndex: 9000,
          width: 56, height: 56, borderRadius: '50%',
          background: 'linear-gradient(135deg, #6366f1, #8b5cf6)',
          border: 'none', cursor: 'pointer', display: 'flex',
          alignItems: 'center', justifyContent: 'center',
          boxShadow: '0 4px 20px rgba(99,102,241,0.5)',
          color: '#fff', fontSize: 22,
        }}
      >
        💬
      </button>
    )
  }

  return (
    <div style={{
      position: 'fixed', bottom: 24, right: 24, zIndex: 9000,
      width: 360, height: 520, borderRadius: 16,
      background: '#0f1117', border: '1px solid #2d2d44',
      boxShadow: '0 8px 40px rgba(0,0,0,0.6)',
      display: 'flex', flexDirection: 'column', overflow: 'hidden',
    }}>
      {/* Header */}
      <div style={{
        padding: '12px 16px', background: 'linear-gradient(135deg, #6366f1, #8b5cf6)',
        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <span style={{ fontSize: 18 }}>💬</span>
          <div>
            <div style={{ color: '#fff', fontWeight: 600, fontSize: 14 }}>Chat with Raybags</div>
            <div style={{ color: 'rgba(255,255,255,0.7)', fontSize: 11 }}>
              {connected ? '● Online' : '○ Connecting…'}
            </div>
          </div>
        </div>
        <button onClick={onClose} style={{ background: 'none', border: 'none', color: '#fff', cursor: 'pointer', fontSize: 18, lineHeight: 1 }}>×</button>
      </div>

      {/* Name prompt */}
      {nameFlow !== 'done' && (
        <form onSubmit={handleNameSubmit} style={{ padding: 16, display: 'flex', flexDirection: 'column', gap: 8 }}>
          <p style={{ color: '#a5b4fc', fontSize: 13, margin: 0 }}>What should I call you?</p>
          <input
            name="nameInput"
            autoFocus
            placeholder="Your name"
            style={{
              background: '#1a1a2e', border: '1px solid #3730a3', borderRadius: 8,
              color: '#e2e8f0', padding: '8px 12px', fontSize: 13, outline: 'none',
            }}
          />
          <button type="submit" style={{
            background: 'linear-gradient(135deg, #6366f1, #8b5cf6)',
            border: 'none', borderRadius: 8, color: '#fff', padding: '8px 12px',
            fontSize: 13, cursor: 'pointer', fontWeight: 600,
          }}>Start chat</button>
        </form>
      )}

      {/* Messages */}
      {nameFlow === 'done' && (
        <>
          <div style={{ flex: 1, overflowY: 'auto', padding: '12px 16px', display: 'flex', flexDirection: 'column', gap: 8 }}>
            {msgs.map(m => (
              <div key={m.id} style={{ display: 'flex', justifyContent: m.sender === 'user' ? 'flex-end' : 'flex-start' }}>
                <div style={{
                  maxWidth: '80%', padding: '8px 12px', borderRadius: 12, fontSize: 13,
                  background: m.sender === 'user' ? 'linear-gradient(135deg, #6366f1, #8b5cf6)' : m.sender === 'system' ? 'transparent' : '#1e1e3a',
                  color: m.sender === 'system' ? '#64748b' : '#e2e8f0',
                  border: m.sender === 'system' ? '1px solid #2d2d44' : 'none',
                  fontStyle: m.sender === 'system' ? 'italic' : 'normal',
                  fontSize: m.sender === 'system' ? 11 : 13,
                }}>
                  {m.content}
                </div>
              </div>
            ))}
            <div ref={bottomRef} />
          </div>
          <div style={{ padding: '8px 12px', borderTop: '1px solid #2d2d44', display: 'flex', gap: 8 }}>
            <input
              value={input}
              onChange={e => setInput(e.target.value)}
              onKeyDown={e => e.key === 'Enter' && !e.shiftKey && handleSend()}
              placeholder="Type a message…"
              disabled={!connected}
              style={{
                flex: 1, background: '#1a1a2e', border: '1px solid #3730a3',
                borderRadius: 8, color: '#e2e8f0', padding: '8px 12px', fontSize: 13,
                outline: 'none', opacity: connected ? 1 : 0.5,
              }}
            />
            <button
              onClick={handleSend}
              disabled={!connected || !input.trim()}
              style={{
                background: 'linear-gradient(135deg, #6366f1, #8b5cf6)',
                border: 'none', borderRadius: 8, color: '#fff',
                padding: '8px 14px', cursor: 'pointer', fontSize: 13, fontWeight: 600,
                opacity: (!connected || !input.trim()) ? 0.5 : 1,
              }}
            >Send</button>
          </div>
        </>
      )}
    </div>
  )
}
