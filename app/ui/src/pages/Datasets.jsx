import React, { useEffect, useState } from 'react'
import { fetchDatasets, fetchPreview, fetchTables } from '../api/datasets.js'
import DataTable from '../components/DataTable.jsx'

/**
 * Datasets page: lists tables from the warehouse and provides row preview.
 */
export default function Datasets() {
  const [datasets, setDatasets] = useState([])
  const [tables, setTables] = useState([])
  const [loading, setLoading] = useState(true)
  const [selectedTable, setSelectedTable] = useState('')
  const [preview, setPreview] = useState([])
  const [previewLoading, setPreviewLoading] = useState(false)

  useEffect(() => {
    Promise.all([fetchDatasets(), fetchTables()])
      .then(([ds, tbls]) => {
        setDatasets(Array.isArray(ds) ? ds : [])
        const tblList = Array.isArray(tbls) ? tbls : []
        setTables(tblList)
        if (tblList.length > 0) {
          setSelectedTable(tblList[0].name ?? tblList[0])
        }
      })
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [])

  useEffect(() => {
    if (!selectedTable) return
    setPreviewLoading(true)
    fetchPreview(selectedTable, 100)
      .then((data) => {
        const rows = Array.isArray(data) ? data : (data?.rows ?? [])
        setPreview(rows)
      })
      .catch(() => setPreview([]))
      .finally(() => setPreviewLoading(false))
  }, [selectedTable])

  return (
    <div>
      <h1 className="text-2xl font-bold text-white mb-6">Datasets</h1>

      {loading ? (
        <p className="text-slate-400">Loading datasets…</p>
      ) : (
        <>
          <h2 className="text-lg font-semibold text-slate-200 mb-3">Metadata</h2>
          {datasets.length === 0 ? (
            <p className="text-slate-400 mb-6">No datasets found.</p>
          ) : (
            <div className="bg-slate-800 border border-slate-700 rounded-lg p-4 mb-6">
              <DataTable rows={datasets} />
            </div>
          )}

          <h2 className="text-lg font-semibold text-slate-200 mb-3">Table Preview</h2>
          {tables.length === 0 ? (
            <p className="text-slate-400">No warehouse tables available.</p>
          ) : (
            <>
              <select
                value={selectedTable}
                onChange={(e) => setSelectedTable(e.target.value)}
                className="mb-4 bg-slate-700 border border-slate-600 text-slate-200 rounded-md px-3 py-2 text-sm"
              >
                {tables.map((t) => {
                  const name = typeof t === 'string' ? t : t.name
                  return <option key={name} value={name}>{name}</option>
                })}
              </select>

              {previewLoading ? (
                <p className="text-slate-400">Loading preview…</p>
              ) : (
                <div className="bg-slate-800 border border-slate-700 rounded-lg p-4">
                  <DataTable rows={preview} />
                </div>
              )}
            </>
          )}
        </>
      )}
    </div>
  )
}
