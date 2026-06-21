import React, { useEffect, useState } from 'react'
import toast from 'react-hot-toast'
import { downloadKaggle, fetchCrawlerStatus, triggerCrawl } from '../api/crawl.js'
import DataTable from '../components/DataTable.jsx'

/**
 * Crawlers page: shows crawler status per source and provides action buttons.
 */
export default function Crawlers() {
  const [statuses, setStatuses] = useState([])
  const [loading, setLoading] = useState(true)
  const [crawling, setCrawling] = useState(false)
  const [downloading, setDownloading] = useState(false)
  const [selectedSource, setSelectedSource] = useState('reddit')

  useEffect(() => {
    fetchCrawlerStatus()
      .then((data) => setStatuses(Array.isArray(data) ? data : []))
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [])

  async function handleCrawl() {
    setCrawling(true)
    try {
      await triggerCrawl({ source: selectedSource })
      toast.success(`Crawl started for source: ${selectedSource}`)
    } catch (err) {
      toast.error(`Crawl failed: ${err.message}`)
    } finally {
      setCrawling(false)
    }
  }

  async function handleKaggleDownload() {
    setDownloading(true)
    try {
      await downloadKaggle({ dataset: 'default' })
      toast.success('Kaggle download triggered')
    } catch (err) {
      toast.error(`Kaggle download failed: ${err.message}`)
    } finally {
      setDownloading(false)
    }
  }

  const SOURCES = ['reddit', 'steam', 'imdb', 'news']

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold text-white">Crawlers</h1>
        <div className="flex items-center gap-3">
          <select
            value={selectedSource}
            onChange={(e) => setSelectedSource(e.target.value)}
            className="bg-slate-700 border border-slate-600 text-slate-200 rounded-md px-3 py-2 text-sm"
          >
            {SOURCES.map((s) => (
              <option key={s} value={s}>{s}</option>
            ))}
          </select>
          <button
            onClick={handleCrawl}
            disabled={crawling}
            className="px-4 py-2 bg-sky-600 hover:bg-sky-500 disabled:opacity-50 text-white rounded-lg text-sm font-medium transition-colors"
          >
            {crawling ? 'Crawling…' : 'Run Crawl'}
          </button>
          <button
            onClick={handleKaggleDownload}
            disabled={downloading}
            className="px-4 py-2 bg-purple-600 hover:bg-purple-500 disabled:opacity-50 text-white rounded-lg text-sm font-medium transition-colors"
          >
            {downloading ? 'Downloading…' : 'Download Kaggle'}
          </button>
        </div>
      </div>

      {loading ? (
        <p className="text-slate-400">Loading crawler status…</p>
      ) : statuses.length === 0 ? (
        <p className="text-slate-400">No crawler data available yet.</p>
      ) : (
        <div className="bg-slate-800 border border-slate-700 rounded-lg p-4">
          <DataTable rows={statuses} />
        </div>
      )}
    </div>
  )
}
