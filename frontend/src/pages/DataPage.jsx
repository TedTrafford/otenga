import React, { useEffect, useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { Database, Table2, RefreshCw, ChevronRight, ChevronDown, Search, Info } from 'lucide-react'
import { executionApi } from '../api/client'
import toast from 'react-hot-toast'

export default function DataPage() {
  const [tables, setTables]     = useState([])
  const [schemas, setSchemas]   = useState({})
  const [loading, setLoading]   = useState(true)
  const [expanded, setExpanded] = useState({})
  const [search, setSearch]     = useState('')
  const [preview, setPreview]   = useState(null)
  const [previewLoading, setPreviewLoading] = useState(false)

  const loadTables = async () => {
    setLoading(true)
    try {
      const { data } = await executionApi.getTables()
      setTables(data.tables || [])
    } catch (err) {
      toast.error('Failed to connect to database')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { loadTables() }, [])

  const toggleTable = async (table) => {
    setExpanded(p => ({ ...p, [table]: !p[table] }))
    if (!schemas[table]) {
      const { data } = await executionApi.getSchema(table)
      setSchemas(p => ({ ...p, [table]: data.columns || [] }))
    }
  }

  const loadPreview = async (table) => {
    setPreviewLoading(true)
    setPreview(null)
    try {
      const { data } = await executionApi.executeCell({
        cell_id: 'preview',
        cell_type: 'sql',
        code: `SELECT * FROM \`${table}\` LIMIT 20`,
        notebook_id: null,
        context: {},
      })
      setPreview({ table, ...data })
    } catch {
      toast.error('Preview failed')
    } finally {
      setPreviewLoading(false)
    }
  }

  const filtered = tables.filter(t => t.toLowerCase().includes(search.toLowerCase()))

  return (
    <div className="flex h-full">
      {/* Table list */}
      <div className="w-72 border-r border-white/5 flex flex-col flex-shrink-0" style={{ background: 'rgba(5,5,21,0.7)' }}>
        <div className="px-4 py-4 border-b border-white/5">
          <div className="flex items-center justify-between mb-3">
            <div className="flex items-center gap-2">
              <Database size={15} className="text-primary" />
              <span className="text-sm font-semibold text-slate-200">Database</span>
            </div>
            <button onClick={loadTables} className="p-1.5 rounded-lg text-slate-500 hover:text-primary hover:bg-primary/10 transition-all" title="Refresh">
              <RefreshCw size={13} className={loading ? 'animate-spin' : ''} />
            </button>
          </div>

          {/* Connection info */}
          <div className="rounded-lg px-3 py-2 mb-3" style={{ background: 'rgba(6,255,165,0.05)', border: '1px solid rgba(6,255,165,0.15)' }}>
            <div className="flex items-center gap-2">
              <span className="w-2 h-2 rounded-full bg-mint-500 animate-pulse" />
              <span className="text-xs text-mint-500 font-medium">Connected</span>
            </div>
            <p className="text-[11px] text-slate-500 mt-0.5 font-mono">Data_Science @ 65.20.86.247</p>
          </div>

          <div className="relative">
            <Search size={12} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-500" />
            <input type="text" placeholder="Search tables..." value={search} onChange={e => setSearch(e.target.value)} className="input-field pl-8 py-2 text-xs" />
          </div>
        </div>

        <div className="flex-1 overflow-y-auto px-2 py-2">
          {loading ? (
            [...Array(8)].map((_, i) => <div key={i} className="skeleton h-8 rounded-lg mb-1.5" />)
          ) : filtered.map((table) => (
            <div key={table}>
              <div
                className="flex items-center gap-2 px-2 py-2 rounded-lg cursor-pointer text-xs text-slate-400 hover:text-slate-200 hover:bg-white/5 transition-all group"
                onClick={() => toggleTable(table)}
              >
                {expanded[table] ? <ChevronDown size={12} /> : <ChevronRight size={12} />}
                <Table2 size={12} className="text-primary/50 flex-shrink-0" />
                <span className="font-mono flex-1 truncate">{table}</span>
                <button onClick={(e) => { e.stopPropagation(); loadPreview(table) }}
                  className="opacity-0 group-hover:opacity-100 p-0.5 rounded text-slate-600 hover:text-primary transition-all" title="Preview data">
                  <Info size={11} />
                </button>
              </div>

              <AnimatePresence>
                {expanded[table] && schemas[table] && (
                  <motion.div initial={{ height: 0, opacity: 0 }} animate={{ height: 'auto', opacity: 1 }} exit={{ height: 0, opacity: 0 }} className="overflow-hidden ml-6">
                    {schemas[table].map((col) => (
                      <div key={col.field} className="flex items-center gap-2 px-2 py-1 text-[11px] text-slate-600 hover:bg-white/5 rounded transition-all cursor-default">
                        <span className="text-violet-400/70 font-mono truncate">{col.field}</span>
                        <span className="text-slate-700 ml-auto text-[10px] font-mono">{col.type}</span>
                        {col.key === 'PRI' && <span className="text-[9px] px-1 rounded text-amber-500 bg-amber-500/10">PK</span>}
                      </div>
                    ))}
                  </motion.div>
                )}
              </AnimatePresence>
            </div>
          ))}

          {!loading && filtered.length === 0 && (
            <p className="text-xs text-slate-600 text-center py-8">No tables found</p>
          )}
        </div>

        {!loading && (
          <div className="px-4 py-3 border-t border-white/5">
            <p className="text-[11px] text-slate-600">{tables.length} tables</p>
          </div>
        )}
      </div>

      {/* Preview pane */}
      <div className="flex-1 flex flex-col min-w-0">
        {previewLoading ? (
          <div className="flex items-center justify-center h-full gap-3">
            <div className="w-5 h-5 border-2 border-primary/30 border-t-primary rounded-full animate-spin" />
            <span className="text-slate-400 text-sm">Loading preview...</span>
          </div>
        ) : preview ? (
          <div className="p-6 flex flex-col gap-4 h-full">
            <div>
              <h2 className="text-base font-bold text-slate-200 flex items-center gap-2">
                <Table2 size={16} className="text-primary" />
                {preview.table}
              </h2>
              <p className="text-xs text-slate-500 mt-1">{preview.data?.length} rows (preview) · {preview.columns?.length} columns</p>
            </div>

            <div className="flex-1 overflow-auto rounded-xl" style={{ border: '1px solid rgba(255,255,255,0.07)' }}>
              <table className="data-table min-w-full">
                <thead className="sticky top-0 z-10">
                  <tr>{preview.columns?.map(c => <th key={c}>{c}</th>)}</tr>
                </thead>
                <tbody>
                  {preview.data?.map((row, i) => (
                    <tr key={i}>
                      {preview.columns?.map(c => (
                        <td key={c} className="max-w-xs truncate" title={String(row[c] ?? '')}>
                          {row[c] === null ? <span className="text-slate-600 italic text-[10px]">null</span> : String(row[c])}
                        </td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        ) : (
          <div className="flex flex-col items-center justify-center h-full gap-4">
            <div className="w-20 h-20 rounded-2xl flex items-center justify-center"
              style={{ background: 'rgba(0,212,255,0.06)', border: '1px solid rgba(0,212,255,0.15)' }}>
              <Database size={32} className="text-primary/50" />
            </div>
            <div className="text-center">
              <p className="text-slate-400 font-medium">Select a table to preview</p>
              <p className="text-slate-600 text-sm mt-1">Click the <Info size={12} className="inline" /> icon next to any table</p>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
