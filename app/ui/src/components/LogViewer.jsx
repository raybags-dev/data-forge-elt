import React, { useEffect, useRef } from 'react'

const LEVEL_STYLES = {
  ERROR: 'text-red-400',
  WARNING: 'text-yellow-400',
  WARN: 'text-yellow-400',
  INFO: 'text-green-400',
  DEBUG: 'text-slate-400',
}

/**
 * Scrollable log stream viewer with per-level color coding.
 *
 * @param {{ lines: string[], autoScroll?: boolean }} props
 */
export default function LogViewer({ lines = [], autoScroll = true }) {
  const bottomRef = useRef(null)

  useEffect(() => {
    if (autoScroll && bottomRef.current) {
      bottomRef.current.scrollIntoView({ behavior: 'smooth' })
    }
  }, [lines, autoScroll])

  function lineClass(line) {
    for (const [level, cls] of Object.entries(LEVEL_STYLES)) {
      if (line.toUpperCase().includes(level)) return cls
    }
    return 'text-slate-300'
  }

  return (
    <div className="bg-slate-950 border border-slate-700 rounded-lg p-4 h-96 overflow-y-auto font-mono text-xs">
      {lines.length === 0 ? (
        <p className="text-slate-500">No log lines to display.</p>
      ) : (
        lines.map((line, i) => (
          <div key={i} className={`whitespace-pre-wrap break-all leading-5 ${lineClass(line)}`}>
            {line}
          </div>
        ))
      )}
      <div ref={bottomRef} />
    </div>
  )
}
