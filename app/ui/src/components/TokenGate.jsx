import React, { createContext, useCallback, useContext, useState } from 'react'
import axios from 'axios'

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8002'
const Ctx = createContext(null)

export function TokenGateProvider({ children, onOpenChat }) {
  const [visible, setVisible] = useState(false)
  const [pendingRetry, setPendingRetry] = useState(null) // fn to retry with token
  const [token, setToken] = useState(() => sessionStorage.getItem('df_app_token') || '')
  const [requestForm, setRequestForm] = useState(false)
  const [reqName, setReqName] = useState('')
  const [reqEmail, setReqEmail] = useState('')
  const [reqReason, setReqReason] = useState('')
  const [reqSent, setReqSent] = useState(false)
  const [reqLoading, setReqLoading] = useState(false)

  const trigger = useCallback((retryFn) => {
    setPendingRetry(() => retryFn)
    setVisible(true)
  }, [])

  const dismiss = useCallback(() => {
    setVisible(false)
    setPendingRetry(null)
    setRequestForm(false)
    setReqSent(false)
  }, [])

  const applyToken = useCallback((t) => {
    const tok = t.trim()
    setToken(tok)
    sessionStorage.setItem('df_app_token', tok)
  }, [])

  const savedToken = token

  async function handleSubmitRequest(e) {
    e.preventDefault()
    setReqLoading(true)
    try {
      await axios.post(`${API_BASE}/api/v1/tokens/request`, {
        name: reqName, email: reqEmail, reason: reqReason,
      })
      setReqSent(true)
    } catch {
      setReqSent(true) // still show success to avoid spam
    } finally {
      setReqLoading(false)
    }
  }

  return (
    <Ctx.Provider value={{ trigger, dismiss, savedToken, applyToken }}>
      {children}
      {visible && (
        <div style={{
          position: 'fixed', inset: 0, zIndex: 8000,
          background: 'rgba(0,0,0,0.75)', backdropFilter: 'blur(4px)',
          display: 'flex', alignItems: 'center', justifyContent: 'center',
        }}>
          <div style={{
            background: '#0f1117', border: '1px solid #2d2d44',
            borderRadius: 16, padding: 32, width: 440, maxWidth: '95vw',
            boxShadow: '0 16px 60px rgba(0,0,0,0.7)',
          }}>
            <div style={{ textAlign: 'center', marginBottom: 20 }}>
              <div style={{ fontSize: 40, marginBottom: 8 }}>🔒</div>
              <h2 style={{ color: '#e2e8f0', margin: 0, fontSize: 20, fontWeight: 700 }}>Free Usage Limit Reached</h2>
              <p style={{ color: '#94a3b8', fontSize: 14, margin: '8px 0 0' }}>
                Your first crawl was on us. Further usage requires an access token.
              </p>
            </div>

            {!requestForm ? (
              <>
                <div style={{ marginBottom: 16 }}>
                  <label style={{ color: '#94a3b8', fontSize: 12, display: 'block', marginBottom: 6 }}>
                    Already have a token?
                  </label>
                  <div style={{ display: 'flex', gap: 8 }}>
                    <input
                      value={token}
                      onChange={e => applyToken(e.target.value)}
                      placeholder="Paste your access token…"
                      style={{
                        flex: 1, background: '#1a1a2e', border: '1px solid #3730a3',
                        borderRadius: 8, color: '#e2e8f0', padding: '9px 12px',
                        fontSize: 13, outline: 'none',
                      }}
                    />
                    <button
                      onClick={() => { dismiss(); pendingRetry && pendingRetry(token) }}
                      disabled={!token.trim()}
                      style={{
                        background: 'linear-gradient(135deg, #6366f1, #8b5cf6)',
                        border: 'none', borderRadius: 8, color: '#fff',
                        padding: '9px 16px', cursor: 'pointer', fontSize: 13,
                        fontWeight: 600, opacity: token.trim() ? 1 : 0.5,
                        whiteSpace: 'nowrap',
                      }}
                    >Use Token</button>
                  </div>
                </div>
                <div style={{ display: 'flex', gap: 8 }}>
                  <button
                    onClick={() => setRequestForm(true)}
                    style={{
                      flex: 1, background: '#1e1e3a', border: '1px solid #3730a3',
                      borderRadius: 8, color: '#a5b4fc', padding: '9px 12px',
                      fontSize: 13, cursor: 'pointer', fontWeight: 600,
                    }}
                  >Request a Token</button>
                  <button
                    onClick={() => { onOpenChat?.('Hi! I\'m hitting the DataForge usage limit and would like to request an access token.'); dismiss() }}
                    style={{
                      flex: 1, background: 'linear-gradient(135deg, #6366f1, #8b5cf6)',
                      border: 'none', borderRadius: 8, color: '#fff',
                      padding: '9px 12px', fontSize: 13, cursor: 'pointer', fontWeight: 600,
                    }}
                  >💬 Chat to Request</button>
                </div>
                <button onClick={dismiss} style={{
                  width: '100%', marginTop: 10, background: 'none',
                  border: 'none', color: '#64748b', cursor: 'pointer', fontSize: 12,
                }}>Cancel</button>
              </>
            ) : reqSent ? (
              <div style={{ textAlign: 'center' }}>
                <div style={{ fontSize: 36, marginBottom: 8 }}>✅</div>
                <p style={{ color: '#94a3b8', fontSize: 14 }}>
                  Request sent! Check your chat at <strong style={{ color: '#a5b4fc' }}>raybags.com</strong> for your token.
                </p>
                <button onClick={dismiss} style={{
                  marginTop: 12, background: 'linear-gradient(135deg, #6366f1, #8b5cf6)',
                  border: 'none', borderRadius: 8, color: '#fff', padding: '9px 20px',
                  cursor: 'pointer', fontSize: 13, fontWeight: 600,
                }}>Done</button>
              </div>
            ) : (
              <form onSubmit={handleSubmitRequest} style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
                <input required value={reqName} onChange={e => setReqName(e.target.value)}
                  placeholder="Your name" style={inputStyle} />
                <input required type="email" value={reqEmail} onChange={e => setReqEmail(e.target.value)}
                  placeholder="Your email" style={inputStyle} />
                <textarea value={reqReason} onChange={e => setReqReason(e.target.value)}
                  placeholder="What are you using DataForge for? (optional)"
                  rows={3} style={{ ...inputStyle, resize: 'vertical' }} />
                <div style={{ display: 'flex', gap: 8 }}>
                  <button type="button" onClick={() => setRequestForm(false)}
                    style={{ ...btnSecondary, flex: 1 }}>Back</button>
                  <button type="submit" disabled={reqLoading}
                    style={{ ...btnPrimary, flex: 1, opacity: reqLoading ? 0.7 : 1 }}>
                    {reqLoading ? 'Sending…' : 'Send Request'}
                  </button>
                </div>
              </form>
            )}
          </div>
        </div>
      )}
    </Ctx.Provider>
  )
}

export function useTokenGate() {
  return useContext(Ctx)
}

const inputStyle = {
  background: '#1a1a2e', border: '1px solid #3730a3', borderRadius: 8,
  color: '#e2e8f0', padding: '9px 12px', fontSize: 13, outline: 'none',
  width: '100%', boxSizing: 'border-box',
}
const btnPrimary = {
  background: 'linear-gradient(135deg, #6366f1, #8b5cf6)', border: 'none',
  borderRadius: 8, color: '#fff', padding: '9px 16px', cursor: 'pointer',
  fontSize: 13, fontWeight: 600,
}
const btnSecondary = {
  background: '#1e1e3a', border: '1px solid #3730a3', borderRadius: 8,
  color: '#a5b4fc', padding: '9px 16px', cursor: 'pointer', fontSize: 13, fontWeight: 600,
}
