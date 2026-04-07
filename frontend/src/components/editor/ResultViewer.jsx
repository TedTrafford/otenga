import React, { useState, lazy, Suspense } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { Table2, BarChart3, AlertCircle, Clock, ChevronDown, ChevronUp, Download } from 'lucide-react'

const Plot = lazy(() =>
  Promise.all([
    import('react-plotly.js/factory'),
    import('plotly.js-dist-min'),
  ]).then(([{ default: createPlotlyComponent }, { default: Plotly }]) => ({
    default: createPlotlyComponent(Plotly),
  }))
)

const StatPill = ({ label, value, color = 'text-primary' }) => (
  <div className="flex items-center gap-1.5 text-xs">
    <span className="text-slate-500">{label}:</span>
    <span className={`font-semibold ${color}`}>{value}</span>
  </div>
)

function DataTable({ data, columns }) {
  const [page, setPage] = useState(0)
  const pageSize = 50
  const pageData = data.slice(page * pageSize, (page + 1) * pageSize)
  const totalPages = Math.ceil(data.length / pageSize)

  const downloadCsv = () => {
    const header = columns.join(',')
    const rows = data.map(row => columns.map(c => JSON.stringify(row[c] ?? '')).join(','))
    const csv = [header, ...rows].join('\n')
    const blob = new Blob([csv], { type: 'text/csv' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = 'result.csv'
    a.click()
  }

  return (
    <div className="flex flex-col gap-3">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <StatPill label="Rows"    value={data.length.toLocaleString()} />
          <StatPill label="Columns" value={columns.length} color="text-violet-400" />
        </div>
        <button onClick={downloadCsv} className="btn-ghost py-1 px-2.5 text-xs gap-1.5">
          <Download size={12} /> CSV
        </button>
      </div>

      <div className="overflow-auto rounded-lg" style={{ border: '1px solid rgba(255,255,255,0.06)', maxHeight: '360px' }}>
        <table className="data-table min-w-full">
          <thead className="sticky top-0 z-10">
            <tr>{columns.map((col) => <th key={col}>{col}</th>)}</tr>
          </thead>
          <tbody>
            {pageData.map((row, i) => (
              <tr key={i}>
                {columns.map((col) => (
                  <td key={col} className="max-w-[200px] truncate" title={String(row[col] ?? '')}>
                    {row[col] === null || row[col] === undefined
                      ? <span className="text-slate-600 italic text-[10px]">null</span>
                      : String(row[col])
                    }
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {totalPages > 1 && (
        <div className="flex items-center gap-3 text-xs text-slate-500">
          <button onClick={() => setPage(p => Math.max(0, p - 1))} disabled={page === 0} className="btn-ghost py-1 px-2.5 text-xs disabled:opacity-40">Prev</button>
          <span>Page {page + 1} of {totalPages}</span>
          <button onClick={() => setPage(p => Math.min(totalPages - 1, p + 1))} disabled={page === totalPages - 1} className="btn-ghost py-1 px-2.5 text-xs disabled:opacity-40">Next</button>
        </div>
      )}
    </div>
  )
}

function PlotlyChart({ data: figData }) {
  const layout = {
    ...(figData.layout || {}),
    paper_bgcolor: 'transparent',
    plot_bgcolor:  'rgba(255,255,255,0.02)',
    font: { color: '#94A3B8', family: 'Inter, sans-serif', size: 11 },
    margin: { t: 40, b: 40, l: 50, r: 20 },
    xaxis: { ...(figData.layout?.xaxis || {}), gridcolor: 'rgba(255,255,255,0.05)', linecolor: 'rgba(255,255,255,0.1)', zerolinecolor: 'rgba(255,255,255,0.1)' },
    yaxis: { ...(figData.layout?.yaxis || {}), gridcolor: 'rgba(255,255,255,0.05)', linecolor: 'rgba(255,255,255,0.1)', zerolinecolor: 'rgba(255,255,255,0.1)' },
    legend: { bgcolor: 'rgba(0,0,0,0)', bordercolor: 'rgba(255,255,255,0.1)' },
  }

  return (
    <Suspense fallback={<div className="skeleton w-full h-64 rounded-lg" />}>
      <Plot
        data={figData.data || []}
        layout={layout}
        config={{ displayModeBar: true, displaylogo: false, modeBarButtonsToRemove: ['lasso2d', 'select2d'] }}
        style={{ width: '100%', minHeight: '320px' }}
        useResizeHandler
      />
    </Suspense>
  )
}

export default function ResultViewer({ result, isRunning }) {
  const [collapsed, setCollapsed] = useState(false)

  if (isRunning) {
    return (
      <motion.div initial={{ opacity: 0, height: 0 }} animate={{ opacity: 1, height: 'auto' }}
        className="mt-2 rounded-xl overflow-hidden"
        style={{ background: 'rgba(0,212,255,0.03)', border: '1px solid rgba(0,212,255,0.1)' }}>
        <div className="p-4 flex items-center gap-3">
          <div className="w-5 h-5 border-2 border-primary/30 border-t-primary rounded-full animate-spin flex-shrink-0" />
          <span className="text-slate-400 text-sm">Executing...</span>
        </div>
      </motion.div>
    )
  }

  if (!result) return null

  return (
    <AnimatePresence>
      <motion.div
        initial={{ opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        exit={{ opacity: 0, y: -8 }}
        transition={{ duration: 0.25 }}
        className="mt-2 rounded-xl overflow-hidden"
        style={{
          background: result.success ? 'rgba(0,212,255,0.02)' : 'rgba(255,77,109,0.05)',
          border: `1px solid ${result.success ? 'rgba(0,212,255,0.12)' : 'rgba(255,77,109,0.2)'}`,
        }}
      >
        {/* Result header */}
        <div
          className="flex items-center justify-between px-4 py-2.5 cursor-pointer select-none"
          style={{ borderBottom: '1px solid rgba(255,255,255,0.05)' }}
          onClick={() => setCollapsed(!collapsed)}
        >
          <div className="flex items-center gap-3">
            {result.success ? (
              <span className="w-2 h-2 rounded-full bg-mint-500 flex-shrink-0" style={{ boxShadow: '0 0 6px rgba(6,255,165,0.6)' }} />
            ) : (
              <AlertCircle size={14} className="text-rose-400 flex-shrink-0" />
            )}
            <span className="text-xs font-medium text-slate-400">
              {result.success ? (
                result.type === 'dataframe' ? `${result.data?.length?.toLocaleString() || 0} rows × ${result.columns?.length || 0} cols`
                  : result.type === 'plotly' ? 'Chart output'
                  : 'Text output'
              ) : 'Execution error'}
            </span>
            {result.execution_time_ms && (
              <span className="flex items-center gap-1 text-[10px] text-slate-600">
                <Clock size={10} />{result.execution_time_ms.toFixed(0)}ms
              </span>
            )}
          </div>
          <button className="text-slate-600 hover:text-slate-400 transition-colors">
            {collapsed ? <ChevronDown size={14} /> : <ChevronUp size={14} />}
          </button>
        </div>

        {/* Result body */}
        <AnimatePresence>
          {!collapsed && (
            <motion.div
              initial={{ height: 0, opacity: 0 }}
              animate={{ height: 'auto', opacity: 1 }}
              exit={{ height: 0, opacity: 0 }}
              className="overflow-hidden"
            >
              <div className="p-4">
                {!result.success ? (
                  <div>
                    <p className="text-rose-400 text-sm font-medium mb-2">{result.error}</p>
                    {result.traceback && (
                      <pre className="text-xs text-slate-500 font-mono overflow-auto p-3 rounded-lg" style={{ background: 'rgba(255,77,109,0.05)', maxHeight: '200px' }}>
                        {result.traceback}
                      </pre>
                    )}
                  </div>
                ) : result.type === 'dataframe' ? (
                  <DataTable data={result.data} columns={result.columns} />
                ) : result.type === 'plotly' ? (
                  <PlotlyChart data={result.data} />
                ) : (
                  <pre className="text-slate-300 text-xs font-mono whitespace-pre-wrap">{result.data || result.stdout || '(no output)'}</pre>
                )}
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </motion.div>
    </AnimatePresence>
  )
}
