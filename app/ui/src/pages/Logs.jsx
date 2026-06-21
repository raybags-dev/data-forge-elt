import { useState, useEffect, useRef } from 'react'
import { getLogs } from '../api/logs'

const LEVELS = ['ALL', 'INFO', 'WARNING', 'ERROR']

const levelColors = {
  INFO: 'text-blue-400',
  WARNING: 'text-yellow-400',
  ERROR: 'text-red-400',
  DEBUG: 'text-gray-400',
}

export default function Logs() {
  const [logs, setLogs] = useState([])
  const [level, setLevel] = useState('ALL')
  const [pipelineId, setPipelineId] = useState('')
  const [autoRefresh, setAutoRefresh] = useState(false)
  const [loading, setLoading] = useState(false)
  const bottomRef = useRef(null)

  const fetchLogs = async () => {
    setLoading(true)
    try {
      const params = { limit: 200 }
      if (level !== 'ALL') params.level = level
      if (pipelineId.trim()) params.pipeline_id = pipelineId.trim()
      const data = await getLogs(params)
      setLogs(data.entries || [])
    } catch (err) {
      console.error('Failed to fetch logs:', err)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { fetchLogs() }, [level, pipelineId])

  useEffect(() => {
    if (!autoRefresh) return
    const interval = setInterval(fetchLogs, 30_000)
    return () => clearInterval(interval)
  }, [autoRefresh, level, pipelineId])

  useEffect(() => {
    if (autoRefresh) bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [logs])

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-white">Pipeline Logs</h1>
        <div className="flex items-center gap-3">
          <label className="flex items-center gap-2 text-sm text-slate-300 cursor-pointer">
            <input
              type="checkbox"
              checked={autoRefresh}
              onChange={e => setAutoRefresh(e.target.checked)}
              className="rounded"
            />
            Auto-refresh (30s)
          </label>
          <button
            onClick={fetchLogs}
            disabled={loading}
            className="px-3 py-1 bg-slate-700 hover:bg-slate-600 text-white rounded text-sm disabled:opacity-50"
          >
            {loading ? 'Loading…' : 'Refresh'}
          </button>
        </div>
      </div>

      {/* Filters */}
      <div className="flex gap-4 flex-wrap">
        <div className="flex gap-1">
          {LEVELS.map(l => (
            <button
              key={l}
              onClick={() => setLevel(l)}
              className={`px-3 py-1 rounded text-sm font-medium transition-colors ${
                level === l
                  ? 'bg-indigo-600 text-white'
                  : 'bg-slate-700 text-slate-300 hover:bg-slate-600'
              }`}
            >
              {l}
            </button>
          ))}
        </div>
        <input
          type="text"
          placeholder="Filter by pipeline_id…"
          value={pipelineId}
          onChange={e => setPipelineId(e.target.value)}
          className="px-3 py-1 bg-slate-700 border border-slate-600 rounded text-sm text-white placeholder-slate-400 focus:outline-none focus:border-indigo-500 w-56"
        />
        <span className="text-slate-400 text-sm self-center">
          {logs.length} entries
        </span>
      </div>

      {/* Log viewer */}
      <div className="bg-slate-900 rounded-lg border border-slate-700 h-[600px] overflow-y-auto font-mono text-xs p-4 space-y-0.5">
        {logs.length === 0 ? (
          <div className="flex items-center justify-center h-full text-slate-500">
            {loading ? 'Loading logs…' : 'No log entries found.'}
          </div>
        ) : (
          logs.map((entry, i) => (
            <div key={i} className="flex gap-3 hover:bg-slate-800 px-1 rounded">
              <span className="text-slate-500 shrink-0 w-48">
                {entry.timestamp ? new Date(entry.timestamp).toLocaleTimeString() : '—'}
              </span>
              <span className={`shrink-0 w-16 font-semibold ${levelColors[entry.level] || 'text-slate-300'}`}>
                {entry.level || 'INFO'}
              </span>
              {entry.pipeline_id && (
                <span className="text-purple-400 shrink-0 truncate max-w-[120px]">
                  [{entry.pipeline_id}]
                </span>
              )}
              <span className="text-slate-200 break-all">{entry.message}</span>
            </div>
          ))
        )}
        <div ref={bottomRef} />
      </div>
    </div>
  )
}
