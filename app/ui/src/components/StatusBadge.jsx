import React from 'react'

const STATUS_STYLES = {
  success: 'bg-green-700 text-green-100',
  failed: 'bg-red-700 text-red-100',
  running: 'bg-blue-700 text-blue-100',
  pending: 'bg-yellow-700 text-yellow-100',
  cancelled: 'bg-slate-600 text-slate-200',
}

/**
 * Colored badge component for displaying pipeline/crawler status values.
 *
 * @param {{ status: string }} props
 */
export default function StatusBadge({ status }) {
  const normalised = String(status).toLowerCase()
  const style = STATUS_STYLES[normalised] ?? 'bg-slate-600 text-slate-200'
  return (
    <span className={`inline-block px-2 py-0.5 rounded text-xs font-semibold uppercase tracking-wide ${style}`}>
      {status}
    </span>
  )
}
