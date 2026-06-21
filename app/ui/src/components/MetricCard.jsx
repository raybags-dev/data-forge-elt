import React from 'react'

/**
 * KPI card displaying an icon, label, and value.
 *
 * @param {{ icon: string, label: string, value: string|number, sub?: string }} props
 */
export default function MetricCard({ icon, label, value, sub }) {
  return (
    <div className="bg-slate-800 border border-slate-700 rounded-lg p-4 flex items-start gap-4">
      <div className="text-3xl select-none" aria-hidden="true">
        {icon}
      </div>
      <div className="min-w-0">
        <p className="text-sm text-slate-400 truncate">{label}</p>
        <p className="text-2xl font-bold text-white mt-0.5 truncate">{value ?? '—'}</p>
        {sub && <p className="text-xs text-slate-500 mt-0.5 truncate">{sub}</p>}
      </div>
    </div>
  )
}
