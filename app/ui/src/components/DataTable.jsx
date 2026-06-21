import React, { useState } from 'react'

const PAGE_SIZE = 20

/**
 * Generic paginated data table component.
 *
 * @param {{ rows: object[], columns?: string[] }} props
 */
export default function DataTable({ rows = [], columns }) {
  const [page, setPage] = useState(0)

  if (!rows.length) {
    return <p className="text-slate-400 text-sm py-4">No data available.</p>
  }

  const cols = columns ?? Object.keys(rows[0])
  const pageCount = Math.ceil(rows.length / PAGE_SIZE)
  const visible = rows.slice(page * PAGE_SIZE, (page + 1) * PAGE_SIZE)

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm text-left">
        <thead className="bg-slate-700 text-slate-300 uppercase text-xs">
          <tr>
            {cols.map((col) => (
              <th key={col} className="px-4 py-2 font-semibold whitespace-nowrap">
                {col}
              </th>
            ))}
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-700">
          {visible.map((row, i) => (
            <tr key={i} className="hover:bg-slate-800 transition-colors">
              {cols.map((col) => (
                <td key={col} className="px-4 py-2 text-slate-300 whitespace-nowrap max-w-xs truncate">
                  {String(row[col] ?? '')}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
      {pageCount > 1 && (
        <div className="flex items-center justify-between mt-3 text-sm text-slate-400">
          <span>
            Page {page + 1} of {pageCount} ({rows.length} rows)
          </span>
          <div className="flex gap-2">
            <button
              disabled={page === 0}
              onClick={() => setPage((p) => p - 1)}
              className="px-3 py-1 rounded bg-slate-700 disabled:opacity-40 hover:bg-slate-600 transition-colors"
            >
              Prev
            </button>
            <button
              disabled={page >= pageCount - 1}
              onClick={() => setPage((p) => p + 1)}
              className="px-3 py-1 rounded bg-slate-700 disabled:opacity-40 hover:bg-slate-600 transition-colors"
            >
              Next
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
