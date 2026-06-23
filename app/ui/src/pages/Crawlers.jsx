import React, { useEffect, useRef, useState } from 'react'
import toast from 'react-hot-toast'
import { analyzeCrawl, getSources, triggerCrawl } from '../api/crawl.js'

const SOURCES = ['reddit', 'steam', 'imdb', 'news', 'custom']
const PAGINATION_MODES = ['none', 'page', 'cursor', 'scroll', 'button']
const SOURCE_MODES = ['dom', 'curl']
const ATTR_OPTIONS = ['text', 'href', 'src', 'data-id', 'data-value', 'datetime', 'title', 'alt']

const EMPTY_FIELD = () => ({
  id: Math.random().toString(36).slice(2),
  name: '',
  selector: '',
  attribute: 'text',
  multiple: false,
  children: [],
})

function FieldRow({ field, onChange, onRemove, depth = 0 }) {
  const [expanded, setExpanded] = useState(false)

  function updateField(key, value) {
    onChange({ ...field, [key]: value })
  }

  function addChild() {
    onChange({ ...field, children: [...(field.children || []), EMPTY_FIELD()] })
    setExpanded(true)
  }

  function updateChild(idx, updated) {
    const children = [...(field.children || [])]
    children[idx] = updated
    onChange({ ...field, children })
  }

  function removeChild(idx) {
    onChange({ ...field, children: (field.children || []).filter((_, i) => i !== idx) })
  }

  return (
    <div className={`border border-slate-700 rounded-lg p-3 ${depth > 0 ? 'ml-4 border-slate-600 bg-slate-800/30' : 'bg-slate-800/50'}`}>
      <div className="grid grid-cols-12 gap-2 items-center">
        <div className="col-span-3">
          <input
            value={field.name}
            onChange={e => updateField('name', e.target.value)}
            placeholder="field_name"
            className="w-full bg-slate-900 border border-slate-600 text-slate-200 rounded px-2 py-1 text-xs font-mono placeholder-slate-500"
          />
        </div>
        <div className="col-span-4">
          <input
            value={field.selector}
            onChange={e => updateField('selector', e.target.value)}
            placeholder=".css-selector, #id, tag"
            className="w-full bg-slate-900 border border-slate-600 text-slate-200 rounded px-2 py-1 text-xs font-mono placeholder-slate-500"
          />
        </div>
        <div className="col-span-2">
          <select
            value={field.attribute}
            onChange={e => updateField('attribute', e.target.value)}
            className="w-full bg-slate-900 border border-slate-600 text-slate-300 rounded px-2 py-1 text-xs"
          >
            {ATTR_OPTIONS.map(a => <option key={a} value={a}>{a}</option>)}
          </select>
        </div>
        <div className="col-span-1 flex items-center justify-center">
          <label className="flex items-center gap-1 text-xs text-slate-400 cursor-pointer">
            <input
              type="checkbox"
              checked={field.multiple}
              onChange={e => updateField('multiple', e.target.checked)}
              className="rounded"
            />
            <span>[ ]</span>
          </label>
        </div>
        <div className="col-span-2 flex items-center gap-1 justify-end">
          {depth < 2 && (
            <button
              onClick={addChild}
              title="Add nested field"
              className="px-1.5 py-1 text-xs bg-slate-700 hover:bg-slate-600 text-slate-300 rounded transition-colors"
            >
              +nest
            </button>
          )}
          <button
            onClick={onRemove}
            className="px-1.5 py-1 text-xs bg-red-900/40 hover:bg-red-800/60 text-red-400 rounded transition-colors"
          >
            ✕
          </button>
        </div>
      </div>

      {field.children && field.children.length > 0 && (
        <div className="mt-2 space-y-2">
          <button
            onClick={() => setExpanded(x => !x)}
            className="text-xs text-slate-400 hover:text-slate-200"
          >
            {expanded ? '▾' : '▸'} {field.children.length} nested field(s)
          </button>
          {expanded && field.children.map((child, idx) => (
            <FieldRow
              key={child.id}
              field={child}
              depth={depth + 1}
              onChange={updated => updateChild(idx, updated)}
              onRemove={() => removeChild(idx)}
            />
          ))}
        </div>
      )}
    </div>
  )
}

function JsonPreview({ data }) {
  const [collapsed, setCollapsed] = useState(false)
  if (!data || (Array.isArray(data) && data.length === 0)) return null
  const sample = Array.isArray(data) ? data.slice(0, 3) : data
  return (
    <div className="rounded-lg border border-slate-700 bg-slate-950 overflow-hidden">
      <div className="flex items-center justify-between px-3 py-2 border-b border-slate-700 bg-slate-900">
        <span className="text-xs font-mono text-slate-400">
          {Array.isArray(data) ? `${data.length} records` : 'result'} — preview (first 3)
        </span>
        <button onClick={() => setCollapsed(x => !x)} className="text-xs text-slate-500 hover:text-slate-300">
          {collapsed ? 'expand' : 'collapse'}
        </button>
      </div>
      {!collapsed && (
        <pre className="p-3 text-xs text-green-300 font-mono overflow-x-auto max-h-72 overflow-y-auto leading-relaxed">
          {JSON.stringify(sample, null, 2)}
        </pre>
      )}
    </div>
  )
}

function ConfidenceBadge({ level }) {
  const map = {
    high: 'bg-emerald-900/50 text-emerald-300 border-emerald-700',
    medium: 'bg-amber-900/50 text-amber-300 border-amber-700',
    low: 'bg-red-900/50 text-red-300 border-red-700',
  }
  return (
    <span className={`text-xs px-2 py-0.5 rounded border font-mono ${map[level] || map.low}`}>
      {level} confidence
    </span>
  )
}

export default function Crawlers() {
  const [source, setSource] = useState('reddit')
  const [mode, setMode] = useState('dom')
  const [pagination, setPagination] = useState('none')
  const [maxPages, setMaxPages] = useState(1)
  const [url, setUrl] = useState('')
  const [container, setContainer] = useState('')
  const [fields, setFields] = useState([])
  const [curlBody, setCurlBody] = useState('')
  const [curlHeaders, setCurlHeaders] = useState('')
  const [outputName, setOutputName] = useState('')
  const [llmAutoDetect, setLlmAutoDetect] = useState(true)
  const [extractAll, setExtractAll] = useState(false)
  const [analyzing, setAnalyzing] = useState(false)
  const [crawling, setCrawling] = useState(false)
  const [result, setResult] = useState(null)
  const [analyzeResult, setAnalyzeResult] = useState(null)
  const [sourceDefaults, setSourceDefaults] = useState({})
  const [activeTab, setActiveTab] = useState('config')
  const [dropdownOpen, setDropdownOpen] = useState(false)
  const dropdownRef = useRef(null)

  useEffect(() => {
    getSources().then(setSourceDefaults).catch(() => {})
  }, [])

  useEffect(() => {
    const handleClick = (e) => {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target)) {
        setDropdownOpen(false)
      }
    }
    document.addEventListener('mousedown', handleClick)
    return () => document.removeEventListener('mousedown', handleClick)
  }, [])

  function applyAnalyzeResult(ar) {
    if (!ar) return
    if (ar.container) setContainer(ar.container)
    if (ar.fields && ar.fields.length > 0) {
      setFields(ar.fields.map(f => ({
        id: Math.random().toString(36).slice(2),
        name: f.name || '',
        selector: f.selector || '',
        attribute: f.attribute || 'text',
        multiple: f.multiple || false,
        children: [],
      })))
    }
    if (ar.dataset_name_suggestion) setOutputName(ar.dataset_name_suggestion)
  }

  async function handleAnalyze() {
    if (!url) { toast.error('Enter a URL to analyze'); return }
    setAnalyzing(true)
    try {
      const ar = await analyzeCrawl({ url, source })
      setAnalyzeResult(ar)
      applyAnalyzeResult(ar)
      if (ar.confidence === 'high' || ar.confidence === 'medium') {
        toast.success(`LLM detected ${ar.fields?.length || 0} fields (${ar.confidence} confidence)`)
      } else {
        toast('Low confidence — review selectors manually', { icon: '⚠️' })
      }
    } catch (err) {
      toast.error(`Analysis failed: ${err.message}`)
    } finally {
      setAnalyzing(false)
    }
  }

  async function handleCrawl() {
    if (!url) { toast.error('Enter a URL'); return }
    setCrawling(true)
    setResult(null)

    let parsedCurlHeaders
    if (curlHeaders.trim()) {
      try {
        parsedCurlHeaders = JSON.parse(curlHeaders)
      } catch {
        toast.error('cURL headers must be valid JSON')
        setCrawling(false)
        return
      }
    }

    const payload = {
      source,
      url,
      mode,
      pagination,
      max_pages: parseInt(maxPages, 10) || 1,
      output_name: outputName || undefined,
      config: {
        container: container || undefined,
        fields: fields.map(({ id, ...f }) => f),
        llm_auto_detect: llmAutoDetect,
        extract_all_descendants: extractAll,
      },
      ...(mode === 'curl' && {
        curl_body: curlBody || undefined,
        curl_headers: parsedCurlHeaders,
      }),
    }

    try {
      const res = await triggerCrawl(payload)
      setResult(res)
      setActiveTab('results')
      if (res.status === 'success') {
        toast.success(`Extracted ${res.records_extracted} records — ${res.dataset_name}`)
      } else if (res.status === 'empty') {
        toast('Crawl finished — 0 records. Check selectors.', { icon: '⚠️' })
      } else {
        toast.error(`Crawl error: ${res.message}`)
      }
    } catch (err) {
      toast.error(`Crawl failed: ${err.message}`)
    } finally {
      setCrawling(false)
    }
  }

  const def = sourceDefaults[source]

  return (
    <div className="max-w-5xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white tracking-tight">Web Crawler</h1>
          <p className="text-sm text-slate-400 mt-1">
            Extract structured datasets from any web source — DOM or cURL, LLM-assisted or manual.
          </p>
        </div>
        <div className="relative" ref={dropdownRef}>
          <button
            onClick={() => setDropdownOpen(x => !x)}
            className="flex items-center gap-2 px-3 py-2 bg-slate-800 hover:bg-slate-700 border border-slate-600 rounded-lg text-sm text-slate-300 transition-colors"
          >
            Options
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
            </svg>
          </button>
          {dropdownOpen && (
            <div className="absolute right-0 mt-1 w-52 bg-slate-800 border border-slate-600 rounded-lg shadow-xl z-50 py-1">
              {[
                { label: 'Extract all descendants', value: extractAll, set: setExtractAll },
                { label: 'LLM auto-detect selectors', value: llmAutoDetect, set: setLlmAutoDetect },
              ].map(opt => (
                <label key={opt.label} className="flex items-center gap-3 px-4 py-2 text-sm text-slate-300 hover:bg-slate-700 cursor-pointer">
                  <input type="checkbox" checked={opt.value} onChange={e => opt.set(e.target.checked)} className="rounded" />
                  {opt.label}
                </label>
              ))}
              <hr className="border-slate-700 my-1" />
              <div className="px-4 py-2">
                <label className="text-xs text-slate-400 block mb-1">Max pages</label>
                <input
                  type="number" min={1} max={50} value={maxPages}
                  onChange={e => setMaxPages(e.target.value)}
                  className="w-full bg-slate-900 border border-slate-600 text-slate-200 rounded px-2 py-1 text-sm"
                />
              </div>
              <div className="px-4 py-2">
                <label className="text-xs text-slate-400 block mb-1">Dataset name</label>
                <input
                  value={outputName} onChange={e => setOutputName(e.target.value)}
                  placeholder="auto-detected"
                  className="w-full bg-slate-900 border border-slate-600 text-slate-200 rounded px-2 py-1 text-sm font-mono placeholder-slate-600"
                />
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Source + Mode row */}
      <div className="grid grid-cols-12 gap-3">
        <div className="col-span-3">
          <label className="block text-xs text-slate-400 mb-1 font-medium uppercase tracking-wider">Source</label>
          <select
            value={source} onChange={e => setSource(e.target.value)}
            className="w-full bg-slate-800 border border-slate-600 text-slate-200 rounded-lg px-3 py-2 text-sm"
          >
            {SOURCES.map(s => <option key={s} value={s}>{s}</option>)}
          </select>
        </div>
        <div className="col-span-3">
          <label className="block text-xs text-slate-400 mb-1 font-medium uppercase tracking-wider">Data Mode</label>
          <div className="flex rounded-lg overflow-hidden border border-slate-600">
            {SOURCE_MODES.map(m => (
              <button
                key={m} onClick={() => setMode(m)}
                className={`flex-1 py-2 text-sm font-medium transition-colors ${
                  mode === m ? 'bg-sky-700 text-white' : 'bg-slate-800 text-slate-400 hover:bg-slate-700'
                }`}
              >
                {m === 'dom' ? 'DOM / HTML' : 'cURL / API'}
              </button>
            ))}
          </div>
        </div>
        <div className="col-span-3">
          <label className="block text-xs text-slate-400 mb-1 font-medium uppercase tracking-wider">Pagination</label>
          <select
            value={pagination} onChange={e => setPagination(e.target.value)}
            className="w-full bg-slate-800 border border-slate-600 text-slate-200 rounded-lg px-3 py-2 text-sm"
          >
            {PAGINATION_MODES.map(p => <option key={p} value={p}>{p}</option>)}
          </select>
        </div>
        <div className="col-span-3">
          {def && def.field_count > 0 && (
            <div className="mt-5 px-3 py-2 rounded-lg bg-slate-800/40 border border-slate-700 text-xs text-slate-400">
              <span className="text-slate-300 font-medium">{source}</span> defaults ready —{' '}
              {def.field_count} fields:{' '}
              <span className="text-sky-400">{def.fields.slice(0, 3).join(', ')}{def.fields.length > 3 ? '…' : ''}</span>
            </div>
          )}
        </div>
      </div>

      {/* URL row */}
      <div className="flex gap-2">
        <div className="flex-1">
          <label className="block text-xs text-slate-400 mb-1 font-medium uppercase tracking-wider">
            {mode === 'curl' ? 'API Endpoint URL' : 'Seed URL'}
          </label>
          <input
            value={url} onChange={e => setUrl(e.target.value)}
            placeholder={mode === 'curl' ? 'https://api.example.com/v1/data' : 'https://www.reddit.com/r/MachineLearning/'}
            className="w-full bg-slate-800 border border-slate-600 text-slate-200 rounded-lg px-4 py-2.5 text-sm font-mono placeholder-slate-600 focus:border-sky-500 focus:outline-none transition-colors"
          />
        </div>
        {mode === 'dom' && (
          <button
            onClick={handleAnalyze} disabled={analyzing || !url}
            className="mt-5 px-4 py-2.5 bg-violet-700 hover:bg-violet-600 disabled:opacity-40 text-white rounded-lg text-sm font-medium flex items-center gap-2 transition-colors whitespace-nowrap"
          >
            {analyzing ? (
              <>
                <span className="inline-block w-3 h-3 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                Analyzing…
              </>
            ) : (
              <>
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                    d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.347.347a3.75 3.75 0 01-.53.53L12 21l-2.56-2.56a3.75 3.75 0 01-.53-.53l-.347-.347z" />
                </svg>
                LLM Analyze
              </>
            )}
          </button>
        )}
      </div>

      {/* Tabs */}
      <div className="border-b border-slate-700">
        <div className="flex gap-1">
          {['config', 'fields', ...(mode === 'curl' ? ['curl'] : []), 'results'].map(tab => (
            <button
              key={tab} onClick={() => setActiveTab(tab)}
              className={`px-4 py-2 text-sm font-medium rounded-t-lg transition-colors capitalize ${
                activeTab === tab
                  ? 'bg-slate-800 text-white border border-b-slate-800 border-slate-700 -mb-px'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              {tab}
              {tab === 'results' && result && (
                <span className={`ml-1.5 text-xs px-1.5 py-0.5 rounded-full ${
                  result.status === 'success' ? 'bg-emerald-700 text-emerald-100' : 'bg-slate-700 text-slate-300'
                }`}>
                  {result.records_extracted}
                </span>
              )}
            </button>
          ))}
        </div>
      </div>

      {/* Config tab */}
      {activeTab === 'config' && (
        <div className="space-y-4">
          {analyzeResult && (
            <div className="p-3 rounded-lg border border-violet-700/40 bg-violet-900/10">
              <div className="flex items-center gap-2 mb-1">
                <span className="text-xs font-medium text-violet-300">LLM Analysis</span>
                <ConfidenceBadge level={analyzeResult.confidence} />
              </div>
              {analyzeResult.notes && (
                <p className="text-xs text-slate-400">{analyzeResult.notes}</p>
              )}
            </div>
          )}
          <div>
            <label className="block text-xs text-slate-400 mb-1 font-medium uppercase tracking-wider">
              Container Selector
            </label>
            <input
              value={container} onChange={e => setContainer(e.target.value)}
              placeholder={def?.container || 'article, .item-row — leave blank for source defaults or LLM'}
              className="w-full bg-slate-800 border border-slate-600 text-slate-200 rounded-lg px-4 py-2.5 text-sm font-mono placeholder-slate-600 focus:border-sky-500 focus:outline-none"
            />
            <p className="text-xs text-slate-500 mt-1">
              CSS selector for repeating row/card containers. Leave blank to use source defaults or LLM auto-detect.
            </p>
          </div>
          <div className="grid grid-cols-2 gap-4">
            {[
              { label: 'LLM auto-detect', desc: 'Use Groq to detect selectors if none provided', value: llmAutoDetect, set: setLlmAutoDetect },
              { label: 'Extract all descendants', desc: 'Build cascading JSON tree of all child elements (excl. SVG)', value: extractAll, set: setExtractAll },
            ].map(opt => (
              <label key={opt.label} className="flex items-start gap-3 p-3 rounded-lg border border-slate-700 bg-slate-800/40 cursor-pointer hover:border-slate-600 transition-colors">
                <input type="checkbox" checked={opt.value} onChange={e => opt.set(e.target.checked)} className="mt-0.5 rounded" />
                <div>
                  <div className="text-sm text-slate-200 font-medium">{opt.label}</div>
                  <div className="text-xs text-slate-400 mt-0.5">{opt.desc}</div>
                </div>
              </label>
            ))}
          </div>
        </div>
      )}

      {/* Fields tab */}
      {activeTab === 'fields' && (
        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="text-sm font-medium text-slate-200">Field Definitions</h3>
              <p className="text-xs text-slate-400 mt-0.5">
                CSS selectors for each field. Nested fields produce cascading JSON objects.
              </p>
            </div>
            <button
              onClick={() => setFields(prev => [...prev, EMPTY_FIELD()])}
              className="px-3 py-1.5 bg-sky-700 hover:bg-sky-600 text-white text-sm rounded-lg font-medium transition-colors flex items-center gap-1.5"
            >
              + Add Field
            </button>
          </div>

          {fields.length === 0 ? (
            <div className="border border-dashed border-slate-700 rounded-lg p-8 text-center">
              <p className="text-slate-500 text-sm">No fields defined — source defaults or LLM will be used.</p>
              <p className="text-slate-600 text-xs mt-1">Add fields for granular extraction control.</p>
            </div>
          ) : (
            <>
              <div className="grid grid-cols-12 gap-2 px-3 text-xs text-slate-500 font-medium uppercase tracking-wider">
                <div className="col-span-3">Field name</div>
                <div className="col-span-4">CSS selector</div>
                <div className="col-span-2">Attribute</div>
                <div className="col-span-1 text-center">List</div>
                <div className="col-span-2 text-right">Actions</div>
              </div>
              <div className="space-y-2">
                {fields.map((field, idx) => (
                  <FieldRow
                    key={field.id}
                    field={field}
                    onChange={updated => setFields(prev => prev.map((f, i) => i === idx ? updated : f))}
                    onRemove={() => setFields(prev => prev.filter((_, i) => i !== idx))}
                  />
                ))}
              </div>
            </>
          )}
        </div>
      )}

      {/* cURL tab */}
      {activeTab === 'curl' && mode === 'curl' && (
        <div className="space-y-4">
          <div>
            <label className="block text-xs text-slate-400 mb-1 font-medium uppercase tracking-wider">
              Request Body (JSON)
            </label>
            <textarea
              value={curlBody} onChange={e => setCurlBody(e.target.value)} rows={8}
              placeholder={'{\n  "query": "machine learning",\n  "limit": 20,\n  "page": 1\n}'}
              className="w-full bg-slate-900 border border-slate-600 text-slate-200 rounded-lg px-4 py-3 text-sm font-mono placeholder-slate-600 focus:border-sky-500 focus:outline-none resize-y"
            />
            <p className="text-xs text-slate-500 mt-1">
              Pagination fields (page, offset, cursor) are auto-injected based on pagination mode.
            </p>
          </div>
          <div>
            <label className="block text-xs text-slate-400 mb-1 font-medium uppercase tracking-wider">
              Additional Headers (JSON)
            </label>
            <textarea
              value={curlHeaders} onChange={e => setCurlHeaders(e.target.value)} rows={3}
              placeholder={'{\n  "X-API-Key": "your-key"\n}'}
              className="w-full bg-slate-900 border border-slate-600 text-slate-200 rounded-lg px-4 py-3 text-sm font-mono placeholder-slate-600 focus:border-sky-500 focus:outline-none resize-y"
            />
          </div>
        </div>
      )}

      {/* Results tab */}
      {activeTab === 'results' && (
        <div className="space-y-4">
          {!result ? (
            <div className="border border-dashed border-slate-700 rounded-lg p-8 text-center text-slate-500 text-sm">
              No results yet — configure and run a crawl.
            </div>
          ) : (
            <>
              <div className="grid grid-cols-4 gap-3">
                {[
                  { label: 'Status', value: result.status, color: result.status === 'success' ? 'emerald' : result.status === 'empty' ? 'amber' : 'red' },
                  { label: 'Records', value: result.records_extracted.toLocaleString(), color: 'sky' },
                  { label: 'Pages', value: result.pages_fetched, color: 'violet' },
                  { label: 'Dataset', value: result.dataset_name || '—', color: 'slate' },
                ].map(m => (
                  <div key={m.label} className="bg-slate-800/60 border border-slate-700 rounded-lg p-3">
                    <div className="text-xs text-slate-400 mb-1">{m.label}</div>
                    <div className={`text-sm font-semibold text-${m.color}-300 font-mono truncate`}>{m.value}</div>
                  </div>
                ))}
              </div>

              {result.message && (
                <p className="text-sm text-slate-400 bg-slate-800/40 rounded-lg px-4 py-2 border border-slate-700">
                  {result.message}
                </p>
              )}

              {result.output_path && (
                <p className="text-xs font-mono text-slate-500">
                  → <span className="text-sky-400">{result.output_path}</span>
                </p>
              )}

              {result.suggested_selectors && (
                <div className="rounded-lg border border-violet-700/30 bg-violet-900/10 p-3">
                  <div className="flex items-center gap-2 mb-2">
                    <span className="text-xs font-medium text-violet-300">LLM-detected selectors</span>
                    <ConfidenceBadge level={result.suggested_selectors.llm_confidence} />
                  </div>
                  <pre className="text-xs font-mono text-slate-300 overflow-x-auto">
                    {JSON.stringify(result.suggested_selectors, null, 2)}
                  </pre>
                </div>
              )}

              <JsonPreview data={result.records_preview} />
            </>
          )}
        </div>
      )}

      {/* Run button */}
      <div className="flex items-center justify-between pt-2 border-t border-slate-800">
        <p className="text-xs text-slate-500">
          {mode === 'dom'
            ? 'Playwright headless browser — full JS rendering, auto-scroll, selector healing'
            : 'httpx async client — JSON API, paginated requests, auto-flatten'}
        </p>
        <button
          onClick={handleCrawl} disabled={crawling || !url}
          className="px-6 py-2.5 bg-sky-600 hover:bg-sky-500 disabled:opacity-40 text-white rounded-lg text-sm font-semibold flex items-center gap-2.5 transition-colors shadow-lg shadow-sky-900/30"
        >
          {crawling ? (
            <>
              <span className="inline-block w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
              Crawling…
            </>
          ) : (
            <>
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z" />
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              Run Crawl
            </>
          )}
        </button>
      </div>
    </div>
  )
}
