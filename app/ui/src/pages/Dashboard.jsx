import React, { useEffect, useState } from 'react'
import { fetchDatasets } from '../api/datasets.js'
import { fetchRuns } from '../api/pipeline.js'
import MetricCard from '../components/MetricCard.jsx'
import StatusBadge from '../components/StatusBadge.jsx'

/**
 * Overview dashboard page with top-level KPI metrics and recent runs.
 */
export default function Dashboard() {
  const [runs, setRuns] = useState([])
  const [datasets, setDatasets] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    Promise.all([fetchRuns(), fetchDatasets()])
      .then(([r, d]) => {
        setRuns(Array.isArray(r) ? r : [])
        setDatasets(Array.isArray(d) ? d : [])
      })
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [])

  const totalRows = datasets.reduce((acc, d) => acc + (Number(d.row_count) || 0), 0)
  const lastRun = runs[0]?.started_at ?? '—'
  const successCount = runs.filter((r) => r.status === 'success').length
  const freshness = datasets.length
    ? Math.round((successCount / Math.max(runs.length, 1)) * 100)
    : 0

  return (
    <div>
      <h1 className="text-2xl font-bold text-white mb-6">Overview</h1>

      {loading ? (
        <p className="text-slate-400">Loading metrics…</p>
      ) : (
        <>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
            <MetricCard icon="📦" label="Total Datasets" value={datasets.length} />
            <MetricCard icon="📊" label="Total Rows" value={totalRows.toLocaleString()} />
            <MetricCard icon="🕐" label="Last Pipeline Run" value={lastRun} />
            <MetricCard icon="✅" label="Freshness Score" value={`${freshness}%`} />
          </div>

          <h2 className="text-lg font-semibold text-slate-200 mb-3">Recent Runs</h2>
          {runs.length === 0 ? (
            <p className="text-slate-400">No pipeline runs yet.</p>
          ) : (
            <div className="space-y-2">
              {runs.slice(0, 5).map((run) => (
                <div
                  key={run.run_id}
                  className="flex items-center justify-between bg-slate-800 border border-slate-700 rounded-lg px-4 py-3"
                >
                  <span className="font-mono text-sm text-slate-300">{run.run_id}</span>
                  <StatusBadge status={run.status ?? 'unknown'} />
                  <span className="text-xs text-slate-500">{run.started_at}</span>
                </div>
              ))}
            </div>
          )}
        </>
      )}
    </div>
  )
}
