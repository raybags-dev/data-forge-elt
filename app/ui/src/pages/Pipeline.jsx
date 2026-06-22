import React, { useCallback, useEffect, useRef, useState } from 'react'
import toast from 'react-hot-toast'
import { fetchRunStatus, fetchRuns, triggerRun } from '../api/pipeline.js'
import StatusBadge from '../components/StatusBadge.jsx'

const POLL_INTERVAL_MS = 3000
const PORTFOLIO = import.meta.env.VITE_PORTFOLIO_API_URL ?? ''

function recordRun() {
  const count = parseInt(localStorage.getItem('df_runs') ?? '0', 10)
  localStorage.setItem('df_runs', String(count + 1))
}

function isAccessGranted() {
  if (localStorage.getItem('df_token_ok') === '1') return true
  const count = parseInt(localStorage.getItem('df_runs') ?? '0', 10)
  return count < 1
}

async function serverCheckAccess(token) {
  if (!PORTFOLIO) return { allowed: true }
  const r = await fetch(`${PORTFOLIO}/api/v1/pipeline-requests/check-access`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ token: token ?? null }),
  })
  return r.json()
}

export default function Pipeline() {
  const [runs, setRuns] = useState([])
  const [loading, setLoading] = useState(true)
  const [triggering, setTriggering] = useState(false)
  const [activeRunId, setActiveRunId] = useState(null)
  const pollRef = useRef(null)

  // Token gate state
  const [showTokenModal, setShowTokenModal] = useState(false)
  const [tokenInput, setTokenInput] = useState('')
  const [tokenError, setTokenError] = useState('')
  const [validating, setValidating] = useState(false)

  const loadRuns = useCallback(async () => {
    try {
      const data = await fetchRuns()
      setRuns(Array.isArray(data) ? data : [])
    } catch {
      // silently ignore fetch errors
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    loadRuns()
    return () => clearInterval(pollRef.current)
  }, [loadRuns])

  useEffect(() => {
    if (!activeRunId) return
    pollRef.current = setInterval(async () => {
      try {
        const status = await fetchRunStatus(activeRunId)
        if (status?.status !== 'running') {
          clearInterval(pollRef.current)
          setActiveRunId(null)
          await loadRuns()
          toast.success(`Run ${activeRunId} finished: ${status?.status}`)
        }
      } catch {
        clearInterval(pollRef.current)
        setActiveRunId(null)
      }
    }, POLL_INTERVAL_MS)
    return () => clearInterval(pollRef.current)
  }, [activeRunId, loadRuns])

  async function executeTrigger() {
    setTriggering(true)
    try {
      const result = await triggerRun({ pipeline_id: 'default', name: 'manual' })
      const runId = result?.run_id ?? result?.id
      recordRun()
      if (runId) {
        setActiveRunId(runId)
        toast.success(`Pipeline run ${runId} started`)
      }
      await loadRuns()
    } catch (err) {
      toast.error(`Failed to start pipeline: ${err.message}`)
    } finally {
      setTriggering(false)
    }
  }

  async function handleTrigger() {
    if (isAccessGranted()) {
      await executeTrigger()
      return
    }
    setShowTokenModal(true)
  }

  async function handleValidateToken() {
    setValidating(true)
    setTokenError('')
    try {
      const result = await serverCheckAccess(tokenInput.trim() || null)
      if (result.allowed) {
        localStorage.setItem('df_token_ok', '1')
        setShowTokenModal(false)
        setTokenInput('')
        await executeTrigger()
      } else {
        setTokenError(
          result.reason === 'invalid_token'
            ? 'Invalid or expired token. Check the email we sent you.'
            : 'Access requires a valid token.',
        )
      }
    } catch {
      setTokenError('Could not validate token. Please try again.')
    } finally {
      setValidating(false)
    }
  }

  const tableRows = runs.map((r) => ({
    run_id: r.run_id,
    status: r.status,
    duration: r.duration ?? '—',
    rows: r.rows_processed ?? '—',
    started_at: r.started_at ?? '—',
  }))

  return (
    <div>
      {/* Token gate modal */}
      {showTokenModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm p-4">
          <div className="bg-slate-800 border border-slate-700 rounded-xl p-6 w-full max-w-sm shadow-2xl">
            <h2 className="text-white font-semibold text-lg mb-1">Access token required</h2>
            <p className="text-slate-400 text-sm mb-4">
              You've used your free run. Enter your access token to continue, or{' '}
              <a
                href="https://raybags.com/dataforge"
                target="_blank"
                rel="noopener noreferrer"
                className="text-sky-400 hover:underline"
              >
                request one here
              </a>
              .
            </p>
            <input
              type="text"
              value={tokenInput}
              onChange={(e) => setTokenInput(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && handleValidateToken()}
              placeholder="Paste your token…"
              className="w-full bg-slate-900 border border-slate-600 rounded-lg px-3 py-2 text-sm text-white placeholder-slate-500 outline-none focus:border-sky-500 mb-3"
            />
            {tokenError && (
              <p className="text-red-400 text-xs mb-3">{tokenError}</p>
            )}
            <div className="flex gap-2">
              <button
                onClick={handleValidateToken}
                disabled={validating || !tokenInput.trim()}
                className="flex-1 py-2 bg-sky-600 hover:bg-sky-500 disabled:opacity-50 text-white rounded-lg text-sm font-medium transition-colors"
              >
                {validating ? 'Validating…' : 'Validate & Run'}
              </button>
              <button
                onClick={() => { setShowTokenModal(false); setTokenError(''); setTokenInput('') }}
                className="px-3 py-2 bg-slate-700 hover:bg-slate-600 text-slate-300 rounded-lg text-sm transition-colors"
              >
                Cancel
              </button>
            </div>
          </div>
        </div>
      )}

      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold text-white">Pipeline Runs</h1>
        <button
          onClick={handleTrigger}
          disabled={triggering || !!activeRunId}
          className="px-4 py-2 bg-sky-600 hover:bg-sky-500 disabled:opacity-50 text-white rounded-lg text-sm font-medium transition-colors"
        >
          {triggering ? 'Starting…' : activeRunId ? 'Running…' : 'Run Pipeline'}
        </button>
      </div>

      {loading ? (
        <p className="text-slate-400">Loading runs…</p>
      ) : runs.length === 0 ? (
        <p className="text-slate-400">No pipeline runs yet. Trigger one above.</p>
      ) : (
        <div className="bg-slate-800 border border-slate-700 rounded-lg p-4">
          <table className="w-full text-sm">
            <thead className="text-xs text-slate-400 uppercase">
              <tr>
                <th className="text-left py-2 px-3">Run ID</th>
                <th className="text-left py-2 px-3">Status</th>
                <th className="text-left py-2 px-3">Duration</th>
                <th className="text-left py-2 px-3">Rows</th>
                <th className="text-left py-2 px-3">Started</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-700">
              {tableRows.map((row) => (
                <tr key={row.run_id} className="hover:bg-slate-700/50">
                  <td className="py-2 px-3 font-mono text-slate-300">{row.run_id}</td>
                  <td className="py-2 px-3"><StatusBadge status={row.status} /></td>
                  <td className="py-2 px-3 text-slate-300">{row.duration}</td>
                  <td className="py-2 px-3 text-slate-300">{row.rows}</td>
                  <td className="py-2 px-3 text-slate-400">{row.started_at}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
