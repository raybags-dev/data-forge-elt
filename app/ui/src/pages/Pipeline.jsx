import React, { useCallback, useEffect, useRef, useState } from 'react'
import toast from 'react-hot-toast'
import { fetchRunStatus, fetchRuns, triggerRun } from '../api/pipeline.js'
import DataTable from '../components/DataTable.jsx'
import StatusBadge from '../components/StatusBadge.jsx'

const POLL_INTERVAL_MS = 3000

/**
 * Pipeline page: list runs, trigger new runs, and poll for status updates.
 */
export default function Pipeline() {
  const [runs, setRuns] = useState([])
  const [loading, setLoading] = useState(true)
  const [triggering, setTriggering] = useState(false)
  const [activeRunId, setActiveRunId] = useState(null)
  const pollRef = useRef(null)

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

  async function handleTrigger() {
    setTriggering(true)
    try {
      const result = await triggerRun({ pipeline_id: 'default', name: 'manual' })
      const runId = result?.run_id ?? result?.id
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

  const tableRows = runs.map((r) => ({
    run_id: r.run_id,
    status: r.status,
    duration: r.duration ?? '—',
    rows: r.rows_processed ?? '—',
    started_at: r.started_at ?? '—',
  }))

  return (
    <div>
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
