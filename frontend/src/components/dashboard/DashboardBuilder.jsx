import React, { useState, useEffect, useCallback, lazy, Suspense } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import GridLayout from 'react-grid-layout'
import 'react-grid-layout/css/styles.css'
import 'react-resizable/css/styles.css'
import {
  BarChart3, Plus, Save, Trash2, Settings2, GripVertical,
  AreaChart, PieChart, TableProperties, SlidersHorizontal, Type,
  Play, X, TrendingUp, ScatterChart, Loader,
  BarChart2, LineChart, CheckCircle2, AlignStartVertical, Send,
} from 'lucide-react'
import Editor from '@monaco-editor/react'
import { dashboardsApi, executionApi } from '../../api/client'
import useAuthStore from '../../store/authStore'
import toast from 'react-hot-toast'
import { nanoid } from '../../utils/nanoid'

const Plot = lazy(() =>
  Promise.all([
    import('react-plotly.js/factory'),
    import('plotly.js-dist-min'),
  ]).then(([{ default: factory }, { default: Plotly }]) => ({ default: factory(Plotly) }))
)

// ── Colour palette for chart traces ─────────────────────────────────────────
const PALETTE = ['#00D4FF','#7C3AED','#06FFA5','#FF4D6D','#FFB800','#EC4899','#34D399','#F97316']

const CHART_TYPES = [
  { type: 'bar',         label: 'Bar',     icon: BarChart2          },
  { type: 'stacked_bar', label: 'Stacked', icon: AlignStartVertical },
  { type: 'line',        label: 'Line',    icon: LineChart          },
  { type: 'area',        label: 'Area',    icon: AreaChart          },
  { type: 'scatter',     label: 'Scatter', icon: ScatterChart       },
  { type: 'pie',         label: 'Pie',     icon: PieChart           },
]

const WIDGET_TYPES = [
  { type: 'chart',   icon: AreaChart,         label: 'Chart',   desc: 'Bar, line, pie & more' },
  { type: 'table',   icon: TableProperties,   label: 'Table',   desc: 'Paginated data table'  },
  { type: 'metric',  icon: TrendingUp,        label: 'KPI',     desc: 'Single value metric'   },
  { type: 'text',    icon: Type,              label: 'Text',    desc: 'Markdown / HTML text'   },
  { type: 'filter',  icon: SlidersHorizontal, label: 'Filter',  desc: 'Dropdown input control' },
]

// ── Build a Plotly figure from raw row data ──────────────────────────────────
function buildFigure(rows, columns, chartType, xCol, yCols, title) {
  if (!rows?.length || !xCol || !yCols?.length) return null

  // Sort rows by X value so time-series charts render in order
  const sorted = [...rows].sort((a, b) => {
    const av = a[xCol], bv = b[xCol]
    if (av == null) return 1
    if (bv == null) return -1
    return String(av).localeCompare(String(bv), undefined, { numeric: true })
  })

  const xVals = sorted.map(r => String(r[xCol] ?? ''))

  let traces
  if (chartType === 'pie') {
    traces = [{
      type: 'pie',
      labels: xVals,
      values: sorted.map(r => Number(r[yCols[0]]) || 0),
      name: yCols[0],
      marker: { colors: PALETTE },
      textinfo: 'label+percent',
      hovertemplate: '%{label}: %{value}<extra></extra>',
    }]
  } else {
    traces = yCols.map((yCol, i) => {
      const yVals = sorted.map(r => {
        const v = r[yCol]
        return v === null || v === '' ? null : Number(v) || 0
      })
      const color = PALETTE[i % PALETTE.length]
      const base = { x: xVals, y: yVals, name: yCol, hovertemplate: `%{x}: %{y:,.2f}<extra>${yCol}</extra>` }

      if (chartType === 'bar' || chartType === 'stacked_bar')
        return { ...base, type: 'bar', marker: { color, opacity: 0.9 } }
      if (chartType === 'line')
        return { ...base, type: 'scatter', mode: 'lines+markers', line: { color, width: 2.5 }, marker: { color, size: 5 } }
      if (chartType === 'area')
        return { ...base, type: 'scatter', mode: 'lines', fill: i === 0 ? 'tozeroy' : 'tonexty', line: { color, width: 2 }, fillcolor: `${color}22` }
      if (chartType === 'scatter')
        return { ...base, type: 'scatter', mode: 'markers', marker: { color, size: 9, opacity: 0.8 } }
      return { ...base, type: 'bar', marker: { color } }
    })
  }

  const barmode = chartType === 'stacked_bar' ? 'stack' : chartType === 'bar' ? 'group' : undefined

  return {
    data: traces,
    layout: {
      title: { text: title || '', font: { color: '#94A3B8', size: 13 } },
      barmode,
      showlegend: yCols.length > 1 || chartType === 'stacked_bar',
    },
  }
}

// ── Widget Config Modal ──────────────────────────────────────────────────────
function WidgetConfigModal({ widget, onSave, onClose, onLiveTitleChange }) {
  const [title,     setTitle]     = useState(widget.title || 'New Widget')
  const [sql,       setSql]       = useState(widget.sql   || '-- Write your SQL query here\nSELECT * FROM information_schema.tables LIMIT 20;')
  const [running,   setRunning]   = useState(false)
  const [rows,      setRows]      = useState(widget.rows    || null)
  const [columns,   setColumns]   = useState(widget.columns || [])
  const [chartType, setChartType] = useState(widget.chartType || 'bar')
  const [xCol,      setXCol]      = useState(widget.xCol  || '')
  const [yCols,     setYCols]     = useState(widget.yCols || [])
  const [content,   setContent]   = useState(widget.content || '')
  const [metaCol,   setMetaCol]   = useState(widget.metaCol || '')
  const [step,      setStep]      = useState(rows ? 2 : 1)  // 1=query, 2=config

  // Close on Escape
  useEffect(() => {
    const h = (e) => { if (e.key === 'Escape') onClose() }
    window.addEventListener('keydown', h)
    return () => window.removeEventListener('keydown', h)
  }, [onClose])

  const runQuery = async () => {
    if (!sql.trim()) return
    setRunning(true)
    try {
      const { data } = await executionApi.executeCell({
        cell_id: `widget-${widget.id}`,
        cell_type: 'sql',
        code: sql,
        notebook_id: null,
        context: {},
      })
      if (!data.success) { toast.error(data.error || 'Query failed'); return }
      const newRows = data.data || []
      const newCols = data.columns || []
      setRows(newRows)
      setColumns(newCols)
      // Auto-detect best columns for axes
      if (newCols.length) {
        // A column is numeric if its first non-null value parses as a finite number
        const numericCols = newCols.filter(c => {
          const s = newRows.find(r => r[c] !== null && r[c] !== '')?.[c]
          return s !== undefined && isFinite(Number(s))
        })
        const nonNumericCols = newCols.filter(c => !numericCols.includes(c))

        // Prefer X columns whose name looks like a dimension / time period
        // e.g. "submission_month", "date", "region", "category" — not raw timestamps
        const DIMENSION_HINTS = ['month', 'date', 'period', 'year', 'week', 'quarter',
          'day', 'category', 'name', 'region', 'type', 'status', 'group', 'label', 'segment']
        const TIMESTAMP_HINTS = ['created_at', 'updated_at', 'deleted_at', 'timestamp', '_time']

        const preferredX = nonNumericCols.find(c => {
          const lower = c.toLowerCase()
          return DIMENSION_HINTS.some(h => lower.includes(h))
        }) || nonNumericCols.find(c => {
          // Exclude raw timestamp columns
          const lower = c.toLowerCase()
          return !TIMESTAMP_HINTS.some(h => lower.includes(h))
        }) || nonNumericCols[0] || newCols[0]

        if (!xCol) setXCol(preferredX)
        if (!yCols.length && numericCols.length) setYCols([numericCols[0]])
      }
      toast.success(`${newRows.length.toLocaleString()} rows · ${newCols.length} columns`)
      setStep(2)
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Query failed')
    } finally {
      setRunning(false)
    }
  }

  const toggleYCol = (col) =>
    setYCols(prev => prev.includes(col) ? prev.filter(c => c !== col) : [...prev, col])

  const preview = rows?.length && widget.type === 'chart'
    ? buildFigure(rows, columns, chartType, xCol, yCols, '')
    : null

  const handleSave = () => {
    const figData = widget.type === 'chart' ? preview : null
    const numericValue = rows?.length && metaCol
      ? rows.reduce((s, r) => s + (Number(r[metaCol]) || 0), 0)
      : null
    onSave({
      ...widget, title, sql, rows, columns, chartType, xCol, yCols,
      figData, content, metaCol,
      value: numericValue !== null ? numericValue.toLocaleString() : widget.value,
      label: metaCol || widget.label,
    })
    onClose()
  }

  const PLOT_LAYOUT = {
    paper_bgcolor: 'transparent', plot_bgcolor: 'rgba(255,255,255,0.015)',
    font: { color: '#94A3B8', family: 'Inter', size: 11 },
    margin: { t: 20, b: 40, l: 50, r: 10 },
    xaxis: { gridcolor: 'rgba(255,255,255,0.05)', linecolor: 'rgba(255,255,255,0.08)', zerolinecolor: 'rgba(255,255,255,0.05)', tickfont: { size: 10 } },
    yaxis: { gridcolor: 'rgba(255,255,255,0.05)', linecolor: 'rgba(255,255,255,0.08)', zerolinecolor: 'rgba(255,255,255,0.05)', tickfont: { size: 10 } },
    legend: { bgcolor: 'rgba(0,0,0,0)', bordercolor: 'rgba(255,255,255,0.08)' },
    hoverlabel: { bgcolor: 'rgba(10,10,37,0.95)', bordercolor: 'rgba(0,212,255,0.3)', font: { color: '#E2E8F0', size: 12 } },
    autosize: true,
  }

  return (
    <motion.div
      initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
      className="fixed inset-0 z-[100] flex items-center justify-center p-4"
      style={{ background: 'rgba(3,3,16,0.82)', backdropFilter: 'blur(10px)' }}
      onClick={onClose}
    >
      <motion.div
        initial={{ y: 28, opacity: 0, scale: 0.96 }}
        animate={{ y: 0, opacity: 1, scale: 1 }}
        exit={{ y: 28, opacity: 0, scale: 0.96 }}
        transition={{ duration: 0.22, ease: 'easeOut' }}
        style={{
          width: '100%', maxWidth: '860px',
          background: 'rgba(8,8,30,0.99)',
          border: '1px solid rgba(0,212,255,0.22)',
          boxShadow: '0 32px 80px rgba(0,0,0,0.75), 0 0 60px rgba(0,212,255,0.07)',
          borderRadius: '20px',
          overflow: 'hidden',
          display: 'flex',
          flexDirection: 'column',
        }}
        onClick={e => e.stopPropagation()}
      >

        {/* ── Header ── */}
        <div style={{ borderBottom: '1px solid rgba(255,255,255,0.08)', padding: '18px 24px', display: 'flex', alignItems: 'center', gap: '14px', flexShrink: 0 }}>
          <div style={{ width: 38, height: 38, borderRadius: 12, background: 'rgba(0,212,255,0.1)', border: '1px solid rgba(0,212,255,0.25)', display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0 }}>
            <Settings2 size={16} color="#00D4FF" />
          </div>
          <div style={{ flex: 1 }}>
            <p style={{ fontSize: 11, color: '#475569', marginBottom: 4, textTransform: 'uppercase', letterSpacing: '0.06em', fontWeight: 600 }}>
              Widget Name
            </p>
            <input
              value={title}
              onChange={e => { setTitle(e.target.value); onLiveTitleChange?.(e.target.value) }}
              placeholder="e.g. Monthly Sales, Top Regions..."
              style={{
                width: '100%', background: 'rgba(255,255,255,0.06)',
                border: '1px solid rgba(0,212,255,0.3)', borderRadius: 8,
                padding: '7px 12px', color: '#E2E8F0', fontSize: 14,
                fontWeight: 600, outline: 'none',
              }}
              onFocus={e => { e.target.style.borderColor = 'rgba(0,212,255,0.6)'; e.target.style.boxShadow = '0 0 0 3px rgba(0,212,255,0.1)' }}
              onBlur={e  => { e.target.style.borderColor = 'rgba(0,212,255,0.3)'; e.target.style.boxShadow = 'none' }}
            />
          </div>
          <button onClick={onClose} style={{ padding: 8, borderRadius: 8, background: 'rgba(255,255,255,0.05)', border: '1px solid rgba(255,255,255,0.08)', cursor: 'pointer', color: '#64748B' }}
            onMouseEnter={e => e.target.style.color = '#94A3B8'} onMouseLeave={e => e.target.style.color = '#64748B'}>
            <X size={15} />
          </button>
        </div>

        {/* ── Step pills ── */}
        <div style={{ display: 'flex', gap: 8, padding: '14px 24px 0', flexShrink: 0 }}>
          {[
            { n: 1, label: 'Write SQL Query' },
            { n: 2, label: 'Configure & Preview', disabled: !rows },
          ].map(({ n, label, disabled }) => (
            <button
              key={n}
              onClick={() => !disabled && setStep(n)}
              disabled={disabled}
              style={{
                display: 'flex', alignItems: 'center', gap: 8, padding: '8px 16px',
                borderRadius: 8, border: 'none', cursor: disabled ? 'not-allowed' : 'pointer',
                fontSize: 12, fontWeight: 600, transition: 'all 0.15s',
                background: step === n ? 'rgba(0,212,255,0.12)' : 'rgba(255,255,255,0.04)',
                color: step === n ? '#00D4FF' : disabled ? '#334155' : '#64748B',
                borderBottom: step === n ? '2px solid #00D4FF' : '2px solid transparent',
              }}
            >
              <span style={{
                width: 20, height: 20, borderRadius: '50%', display: 'flex', alignItems: 'center', justifyContent: 'center',
                background: step === n ? '#00D4FF' : rows && n === 2 ? 'rgba(6,255,165,0.2)' : 'rgba(255,255,255,0.08)',
                color: step === n ? '#020D14' : rows && n === 2 ? '#06FFA5' : '#475569',
                fontSize: 10, fontWeight: 700, flexShrink: 0,
              }}>{rows && n === 2 ? '✓' : n}</span>
              {label}
              {n === 2 && rows && <span style={{ marginLeft: 4, fontSize: 10, padding: '1px 6px', borderRadius: 99, background: 'rgba(0,212,255,0.15)', color: '#00D4FF' }}>{rows.length.toLocaleString()}</span>}
            </button>
          ))}
        </div>

        {/* ── Step 1: SQL editor ── */}
        {step === 1 && (
          <div style={{ display: 'flex', flexDirection: 'column', padding: '16px 24px 0' }}>
            <div style={{ borderRadius: 12, overflow: 'hidden', border: '1px solid rgba(255,255,255,0.08)', background: 'rgba(0,0,0,0.35)' }}>
              <Editor
                height="240px"
                language="sql"
                value={sql}
                onChange={v => setSql(v || '')}
                theme="vs-dark"
                options={{
                  minimap: { enabled: false },
                  fontSize: 13,
                  fontFamily: "'JetBrains Mono', 'Fira Code', monospace",
                  lineNumbers: 'on',
                  wordWrap: 'on',
                  scrollBeyondLastLine: false,
                  padding: { top: 14, bottom: 14 },
                  renderLineHighlight: 'line',
                }}
                onMount={(editor, monacoInstance) => {
                  editor.addCommand(monacoInstance.KeyMod.CtrlCmd | monacoInstance.KeyCode.Enter, runQuery)
                }}
              />
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 12, padding: '14px 0', flexShrink: 0 }}>
              <button
                onClick={runQuery}
                disabled={running || !sql.trim()}
                className="btn-primary gap-2 py-2.5 px-6 disabled:opacity-60"
              >
                {running
                  ? <span style={{ width: 14, height: 14, border: '2px solid rgba(2,13,20,0.3)', borderTop: '2px solid #020D14', borderRadius: '50%', display: 'inline-block', animation: 'spin 0.8s linear infinite' }} />
                  : <Play size={13} fill="currentColor" />}
                {running ? 'Running query...' : 'Run Query'}
              </button>
              <span style={{ fontSize: 11, color: '#334155' }}>Ctrl + Enter to run</span>
              {rows && (
                <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginLeft: 'auto', fontSize: 12, color: '#06FFA5' }}>
                  <CheckCircle2 size={14} />
                  {rows.length.toLocaleString()} rows · {columns.length} columns
                  <button onClick={() => setStep(2)} style={{ marginLeft: 8, color: '#00D4FF', background: 'none', border: 'none', cursor: 'pointer', fontSize: 12, textDecoration: 'underline' }}>
                    Configure →
                  </button>
                </div>
              )}
            </div>
          </div>
        )}

        {/* ── Step 2: Config + Preview ── */}
        {step === 2 && rows && (
          <div style={{ display: 'flex', gap: 0, overflow: 'hidden' }}>

            {/* Left: controls */}
            <div style={{ width: 260, flexShrink: 0, borderRight: '1px solid rgba(255,255,255,0.06)', overflowY: 'auto', padding: '16px 20px', maxHeight: 440, display: 'flex', flexDirection: 'column', gap: 20 }}>

              {/* Chart type buttons */}
              {widget.type === 'chart' && (
                <div>
                  <p style={{ fontSize: 10, fontWeight: 700, color: '#475569', textTransform: 'uppercase', letterSpacing: '0.07em', marginBottom: 10 }}>Chart Type</p>
                  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 6 }}>
                    {CHART_TYPES.map(({ type, label, icon: Icon }) => (
                      <button key={type} onClick={() => setChartType(type)} title={label}
                        style={{
                          display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 4,
                          padding: '8px 4px', borderRadius: 8, border: 'none', cursor: 'pointer', fontSize: 10, fontWeight: 600,
                          background: chartType === type ? 'rgba(0,212,255,0.15)' : 'rgba(255,255,255,0.04)',
                          color: chartType === type ? '#00D4FF' : '#64748B',
                          outline: chartType === type ? '1px solid rgba(0,212,255,0.4)' : '1px solid transparent',
                          transition: 'all 0.12s',
                        }}>
                        <Icon size={15} />
                        {label}
                      </button>
                    ))}
                  </div>
                </div>
              )}

              {/* X axis */}
              {widget.type === 'chart' && (
                <div>
                  <p style={{ fontSize: 10, fontWeight: 700, color: '#475569', textTransform: 'uppercase', letterSpacing: '0.07em', marginBottom: 8 }}>
                    {chartType === 'pie' ? 'Labels Column' : 'X Axis Column'}
                  </p>
                  <select value={xCol} onChange={e => setXCol(e.target.value)} className="input-field text-xs py-2">
                    <option value="">— select column —</option>
                    {columns.map(c => <option key={c} value={c}>{c}</option>)}
                  </select>
                </div>
              )}

              {/* Y axis */}
              {widget.type === 'chart' && (
                <div>
                  <p style={{ fontSize: 10, fontWeight: 700, color: '#475569', textTransform: 'uppercase', letterSpacing: '0.07em', marginBottom: 8 }}>
                    {chartType === 'pie' ? 'Values Column' : 'Y Axis (tick to include)'}
                  </p>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: 4, maxHeight: 160, overflowY: 'auto' }}>
                    {columns.filter(c => c !== xCol).map(c => {
                      const sample = rows[0]?.[c]
                      const isNum  = sample !== null && sample !== '' && !isNaN(Number(sample))
                      const active = yCols.includes(c)
                      return (
                        <label key={c} style={{
                          display: 'flex', alignItems: 'center', gap: 10, padding: '7px 10px', borderRadius: 8, cursor: 'pointer',
                          background: active ? 'rgba(0,212,255,0.1)' : 'rgba(255,255,255,0.03)',
                          border: `1px solid ${active ? 'rgba(0,212,255,0.3)' : 'rgba(255,255,255,0.06)'}`,
                          transition: 'all 0.12s',
                        }}>
                          <input type="checkbox" checked={active} onChange={() => toggleYCol(c)} style={{ accentColor: '#00D4FF', flexShrink: 0 }} />
                          <span style={{ fontSize: 12, color: active ? '#E2E8F0' : '#94A3B8', flex: 1, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{c}</span>
                          {isNum && <span style={{ fontSize: 9, color: '#00D4FF', opacity: 0.6, fontFamily: 'monospace', flexShrink: 0 }}>123</span>}
                        </label>
                      )
                    })}
                  </div>
                </div>
              )}

              {/* Metric */}
              {widget.type === 'metric' && (
                <div>
                  <p style={{ fontSize: 10, fontWeight: 700, color: '#475569', textTransform: 'uppercase', letterSpacing: '0.07em', marginBottom: 8 }}>Aggregate Column</p>
                  <select value={metaCol} onChange={e => setMetaCol(e.target.value)} className="input-field text-xs py-2">
                    <option value="">— select column —</option>
                    {columns.map(c => <option key={c} value={c}>{c}</option>)}
                  </select>
                  {metaCol && (
                    <div style={{ marginTop: 12, padding: '12px 16px', borderRadius: 10, background: 'rgba(0,212,255,0.06)', border: '1px solid rgba(0,212,255,0.15)', textAlign: 'center' }}>
                      <p style={{ fontSize: 28, fontWeight: 800, background: 'linear-gradient(135deg,#00D4FF,#06FFA5)', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent' }}>
                        {rows.reduce((s, r) => s + (Number(r[metaCol]) || 0), 0).toLocaleString()}
                      </p>
                      <p style={{ fontSize: 11, color: '#64748B', marginTop: 2 }}>{metaCol}</p>
                    </div>
                  )}
                </div>
              )}

              {/* Text */}
              {widget.type === 'text' && (
                <div>
                  <p style={{ fontSize: 10, fontWeight: 700, color: '#475569', textTransform: 'uppercase', letterSpacing: '0.07em', marginBottom: 8 }}>Text Content</p>
                  <textarea value={content} onChange={e => setContent(e.target.value)} rows={8}
                    className="input-field text-xs font-mono resize-none"
                    placeholder="Write text or markdown here..." />
                </div>
              )}

              {/* Table — just shows info */}
              {widget.type === 'table' && (
                <div style={{ fontSize: 12, color: '#64748B', padding: '12px', background: 'rgba(255,255,255,0.03)', borderRadius: 10, border: '1px solid rgba(255,255,255,0.06)' }}>
                  All {columns.length} columns from the query will be shown in the table widget.
                </div>
              )}
            </div>

            {/* Right: preview */}
            <div style={{ flex: 1, padding: '16px 20px', overflowY: 'auto', maxHeight: 440 }}>
              <p style={{ fontSize: 10, fontWeight: 700, color: '#475569', textTransform: 'uppercase', letterSpacing: '0.07em', marginBottom: 12 }}>Live Preview</p>
              {widget.type === 'chart' && preview ? (
                <div style={{ borderRadius: 12, overflow: 'hidden', border: '1px solid rgba(255,255,255,0.07)' }}>
                  <Suspense fallback={<div className="skeleton w-full" style={{ height: 280 }} />}>
                    <Plot
                      data={preview.data}
                      layout={{ ...PLOT_LAYOUT, ...(preview.layout || {}), title: { text: title, font: { color: '#94A3B8', size: 12 } }, autosize: true }}
                      config={{ displayModeBar: false, responsive: true }}
                      style={{ width: '100%', height: 280 }}
                      useResizeHandler
                    />
                  </Suspense>
                </div>
              ) : widget.type === 'chart' ? (
                <div style={{ height: 200, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', gap: 8, borderRadius: 12, border: '1px dashed rgba(255,255,255,0.08)' }}>
                  <AreaChart size={28} color="#334155" />
                  <p style={{ fontSize: 12, color: '#334155' }}>Select X and Y columns to preview</p>
                </div>
              ) : widget.type === 'table' ? (
                <div style={{ borderRadius: 12, overflow: 'auto', border: '1px solid rgba(255,255,255,0.07)', maxHeight: 360 }}>
                  <table className="data-table min-w-full">
                    <thead className="sticky top-0"><tr>{columns.map(c => <th key={c}>{c}</th>)}</tr></thead>
                    <tbody>
                      {rows.slice(0, 15).map((row, i) => (
                        <tr key={i}>{columns.map(c => <td key={c} style={{ maxWidth: 140 }} className="truncate">{String(row[c] ?? '')}</td>)}</tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              ) : (
                <div style={{ height: 160, display: 'flex', alignItems: 'center', justifyContent: 'center', borderRadius: 12, border: '1px dashed rgba(255,255,255,0.07)' }}>
                  <p style={{ fontSize: 12, color: '#334155' }}>Configure on the left</p>
                </div>
              )}
            </div>
          </div>
        )}

        {/* ── Footer ── */}
        <div style={{ borderTop: '1px solid rgba(255,255,255,0.07)', padding: '14px 24px', display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexShrink: 0, gap: 12 }}>
          <button onClick={onClose} className="btn-ghost py-2 px-5">Cancel</button>
          <div style={{ display: 'flex', gap: 10, alignItems: 'center' }}>
            {step === 1 && (
              <button onClick={runQuery} disabled={running || !sql.trim()} className="btn-ghost py-2 px-4 gap-2 disabled:opacity-60">
                {running ? <Loader size={13} className="animate-spin" /> : <Play size={13} fill="currentColor" />}
                {running ? 'Running...' : 'Run Query'}
              </button>
            )}
            {step === 2 && (
              <button onClick={() => setStep(1)} className="btn-ghost py-2 px-4 gap-2">
                ← Back to Query
              </button>
            )}
            <button
              onClick={handleSave}
              disabled={!title.trim() || (widget.type === 'chart' && step < 2)}
              className="btn-primary py-2 px-6 gap-2 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <CheckCircle2 size={14} /> Save Widget
            </button>
          </div>
        </div>
      </motion.div>
    </motion.div>
  )
}

// ── Widget Card ──────────────────────────────────────────────────────────────
function WidgetCard({ widget, onRemove, onEdit }) {
  const darkLayout = {
    paper_bgcolor: 'transparent', plot_bgcolor: 'rgba(255,255,255,0.01)',
    font: { color: '#94A3B8', family: 'Inter', size: 10 },
    margin: { t: 10, b: 30, l: 40, r: 10 },
    xaxis: { gridcolor: 'rgba(255,255,255,0.04)', tickfont: { size: 9 } },
    yaxis: { gridcolor: 'rgba(255,255,255,0.04)', tickfont: { size: 9 } },
    showlegend: false, autosize: true,
  }

  return (
    <div className="h-full rounded-xl overflow-hidden flex flex-col group"
      style={{ background: 'rgba(255,255,255,0.025)', border: '1px solid rgba(255,255,255,0.07)' }}>

      {/* Header */}
      <div className="flex items-center gap-2 px-3 py-2 flex-shrink-0"
        style={{ borderBottom: '1px solid rgba(255,255,255,0.05)' }}>
        <GripVertical size={13} className="text-slate-700 cursor-grab flex-shrink-0" />
        <span className="text-xs font-semibold text-slate-300 flex-1 truncate">{widget.title}</span>
        <div className="flex gap-0.5 opacity-0 group-hover:opacity-100 transition-opacity">
          <button onClick={() => onEdit(widget.id)} className="p-1.5 rounded text-slate-600 hover:text-primary hover:bg-primary/10 transition-all" title="Configure">
            <Settings2 size={11} />
          </button>
          <button onClick={() => onRemove(widget.id)} className="p-1.5 rounded text-slate-600 hover:text-rose-400 hover:bg-rose-500/10 transition-all" title="Remove">
            <Trash2 size={11} />
          </button>
        </div>
      </div>

      {/* Content */}
      <div className="flex-1 min-h-0 overflow-hidden">
        {widget.type === 'chart' && widget.figData ? (
          <Suspense fallback={<div className="skeleton w-full h-full" />}>
            <Plot
              data={widget.figData.data}
              layout={{ ...darkLayout, ...(widget.figData.layout || {}), autosize: true }}
              config={{ displayModeBar: false, responsive: true }}
              style={{ width: '100%', height: '100%' }}
              useResizeHandler
            />
          </Suspense>
        ) : widget.type === 'chart' && !widget.figData ? (
          <div className="flex flex-col items-center justify-center h-full gap-2 cursor-pointer" onClick={() => onEdit(widget.id)}>
            <AreaChart size={28} className="text-slate-700" />
            <p className="text-xs text-slate-600">Click to configure chart</p>
          </div>
        ) : widget.type === 'table' && widget.rows?.length ? (
          <div className="overflow-auto h-full">
            <table className="data-table min-w-full text-[11px]">
              <thead className="sticky top-0"><tr>{widget.columns?.map(c => <th key={c} className="py-1.5 px-3 text-[10px]">{c}</th>)}</tr></thead>
              <tbody>
                {widget.rows.slice(0, 50).map((row, i) => (
                  <tr key={i}>{widget.columns?.map(c => <td key={c} className="py-1.5 px-3 max-w-[120px] truncate text-[11px]">{String(row[c] ?? '')}</td>)}</tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : widget.type === 'metric' ? (
          <div className="flex flex-col items-center justify-center h-full">
            <div className="text-3xl font-black text-gradient-cyan mb-1">{widget.value || '—'}</div>
            <div className="text-xs text-slate-500">{widget.label || widget.title}</div>
          </div>
        ) : widget.type === 'text' ? (
          <div className="p-3 text-slate-400 text-xs whitespace-pre-wrap overflow-auto h-full">{widget.content || <span className="text-slate-700 italic">Click ⚙ to add text</span>}</div>
        ) : widget.type === 'filter' ? (
          <div className="flex flex-col gap-2 p-3">
            <label className="text-[11px] text-slate-500">{widget.label || 'Filter'}</label>
            <select className="input-field text-xs py-1.5">
              {(widget.options || ['All']).map(opt => <option key={opt}>{opt}</option>)}
            </select>
          </div>
        ) : (
          <div className="flex items-center justify-center h-full cursor-pointer" onClick={() => onEdit(widget.id)}>
            <p className="text-xs text-slate-700">Click ⚙ to configure</p>
          </div>
        )}
      </div>
    </div>
  )
}

// ── Add Widget Panel ─────────────────────────────────────────────────────────
function AddPanel({ onAdd, onClose }) {
  return (
    <motion.div
      initial={{ opacity: 0, x: 20 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0, x: 20 }}
      className="w-60 border-l border-white/5 flex flex-col flex-shrink-0"
      style={{ background: 'rgba(5,5,21,0.8)' }}
    >
      <div className="flex items-center justify-between px-4 py-3 border-b border-white/5">
        <span className="text-xs font-semibold text-slate-300">Add Widget</span>
        <button onClick={onClose} className="text-slate-600 hover:text-slate-400 transition-colors text-lg leading-none">×</button>
      </div>
      <div className="flex-1 overflow-y-auto p-3 space-y-2">
        {WIDGET_TYPES.map(({ type, icon: Icon, label, desc }) => (
          <button key={type} onClick={() => { onAdd(type); onClose() }}
            className="w-full flex items-center gap-3 px-3 py-3 rounded-xl text-left transition-all duration-200 group"
            style={{ background: 'rgba(255,255,255,0.04)', border: '1px solid rgba(255,255,255,0.07)' }}
            onMouseEnter={e => { e.currentTarget.style.borderColor = 'rgba(0,212,255,0.3)'; e.currentTarget.style.background = 'rgba(0,212,255,0.06)' }}
            onMouseLeave={e => { e.currentTarget.style.borderColor = 'rgba(255,255,255,0.07)'; e.currentTarget.style.background = 'rgba(255,255,255,0.04)' }}
          >
            <div className="w-9 h-9 rounded-lg flex items-center justify-center flex-shrink-0"
              style={{ background: 'rgba(0,212,255,0.1)', border: '1px solid rgba(0,212,255,0.2)' }}>
              <Icon size={16} className="text-primary" />
            </div>
            <div>
              <p className="text-sm font-medium text-slate-200">{label}</p>
              <p className="text-[11px] text-slate-500">{desc}</p>
            </div>
          </button>
        ))}
      </div>
    </motion.div>
  )
}

const STATUS_BADGE = {
  draft:            { label: 'Draft',         color: '#FFB800', bg: 'rgba(255,184,0,0.12)',   border: 'rgba(255,184,0,0.25)'   },
  pending_approval: { label: 'Pending Review', color: '#A78BFA', bg: 'rgba(124,58,237,0.12)', border: 'rgba(124,58,237,0.25)' },
  published:        { label: 'Published',      color: '#06FFA5', bg: 'rgba(6,255,165,0.12)',  border: 'rgba(6,255,165,0.25)'  },
}

// ── Main DashboardBuilder ────────────────────────────────────────────────────
export default function DashboardBuilder({ dashboard: initialDashboard, onSave }) {
  const [dashboard,  setDashboard]  = useState(initialDashboard)
  const [widgets,    setWidgets]    = useState(initialDashboard?.widgets || [])
  const [layout,     setLayout]     = useState(initialDashboard?.layout  || [])
  const [showAdd,    setShowAdd]    = useState(false)
  const [configId,   setConfigId]   = useState(null)
  const [saving,     setSaving]     = useState(false)
  const [submitting, setSubmitting] = useState(false)
  const { isCreator, isSuperuser }  = useAuthStore()
  const cols = 12

  const addWidget = (type) => {
    const id = nanoid()
    const newWidget = { id, type, title: `${type.charAt(0).toUpperCase() + type.slice(1)} Widget`, figData: null }
    const newLayout = { i: id, x: (widgets.length * 4) % cols, y: Infinity, w: 6, h: 8, minW: 3, minH: 4 }
    setWidgets(w => [...w, newWidget])
    setLayout(l => [...l, newLayout])
    setConfigId(id)
  }

  const removeWidget = (id) => {
    setWidgets(w => w.filter(x => x.id !== id))
    setLayout(l => l.filter(x => x.i !== id))
  }

  const saveWidgetConfig = (updated) => {
    setWidgets(w => w.map(x => x.id === updated.id ? updated : x))
    toast.success('Widget saved')
  }

  // Stable callback so the modal input onChange never captures a stale closure
  const handleWidgetLiveTitle = useCallback((newTitle) => {
    setWidgets(w => w.map(x => x.id === configId ? { ...x, title: newTitle } : x))
  }, [configId])

  const saveDashboard = async () => {
    setSaving(true)
    try {
      if (dashboard?.id) {
        const { data } = await dashboardsApi.update(dashboard.id, { layout, widgets })
        setDashboard(data)
        toast.success('Dashboard saved')
        onSave?.({ layout, widgets, status: data.status })
      }
    } catch {
      toast.error('Failed to save dashboard')
    } finally {
      setSaving(false)
    }
  }

  const submitForReview = async () => {
    // Auto-save first, then submit
    setSubmitting(true)
    try {
      if (dashboard?.id) {
        await dashboardsApi.update(dashboard.id, { layout, widgets })
        const { data } = await dashboardsApi.submit(dashboard.id)
        setDashboard(data)
        onSave?.({ layout, widgets, status: data.status })
        toast.success('Dashboard submitted for review! A superuser will approve it.')
      }
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to submit for review')
    } finally {
      setSubmitting(false)
    }
  }

  const publishDashboard = async () => {
    setSaving(true)
    try {
      if (dashboard?.id) {
        const { data } = await dashboardsApi.publish(dashboard.id)
        setDashboard(data)
        onSave?.({ layout, widgets, status: data.status })
        toast.success('Dashboard published! Viewers can now see it.')
      }
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to publish dashboard')
    } finally {
      setSaving(false)
    }
  }

  const editingWidget = configId ? widgets.find(w => w.id === configId) : null
  const statusInfo    = STATUS_BADGE[dashboard?.status] || STATUS_BADGE.draft
  const isDraft       = dashboard?.status === 'draft'     || !dashboard?.status
  const isPending     = dashboard?.status === 'pending_approval'
  const isPublished   = dashboard?.status === 'published'

  return (
    <div className="flex h-full">
      <div className="flex-1 flex flex-col min-w-0">
        {/* Toolbar */}
        <div className="flex items-center gap-3 px-6 py-3 border-b border-white/5 flex-shrink-0"
          style={{ background: 'rgba(5,5,21,0.5)' }}>
          <h2 className="text-sm font-semibold text-slate-200 truncate" style={{ maxWidth: '200px' }}>
            {dashboard?.name || 'Dashboard'}
          </h2>

          {/* Status badge */}
          <span className="text-[10px] font-semibold px-2 py-0.5 rounded-full flex-shrink-0"
            style={{ background: statusInfo.bg, color: statusInfo.color, border: `1px solid ${statusInfo.border}` }}>
            {statusInfo.label}
          </span>

          <span className="text-xs text-slate-600 flex-shrink-0">{widgets.length} widget{widgets.length !== 1 ? 's' : ''}</span>
          <div className="flex-1" />

          {/* Creator: add widget + save + submit */}
          {isCreator() && !isPublished && (
            <>
              <button onClick={() => setShowAdd(!showAdd)} className="btn-ghost py-1.5 px-3 text-xs gap-1.5">
                <Plus size={12} /> Add Widget
              </button>
              <button onClick={saveDashboard} disabled={saving || isPending} className="btn-ghost py-1.5 px-3 text-xs gap-1.5 disabled:opacity-50">
                {saving ? <Loader size={12} className="animate-spin" /> : <Save size={12} />}
                {saving ? 'Saving...' : 'Save'}
              </button>
              {isDraft && (
                <button onClick={submitForReview} disabled={submitting || widgets.length === 0}
                  className="btn-violet py-1.5 px-4 text-xs gap-1.5 disabled:opacity-50 disabled:cursor-not-allowed"
                  title={widgets.length === 0 ? 'Add at least one widget before submitting' : 'Submit for superuser review'}>
                  {submitting ? <Loader size={12} className="animate-spin" /> : <Send size={12} />}
                  {submitting ? 'Submitting...' : 'Submit for Review'}
                </button>
              )}
              {isPending && (
                <span className="text-xs text-violet-400 flex items-center gap-1.5 px-3">
                  <Loader size={11} className="animate-spin" /> Awaiting approval…
                </span>
              )}
            </>
          )}

          {/* Superuser: publish or unpublish */}
          {isSuperuser() && (
            <>
              {!isPublished && (
                <button onClick={() => setShowAdd(!showAdd)} className="btn-ghost py-1.5 px-3 text-xs gap-1.5">
                  <Plus size={12} /> Add Widget
                </button>
              )}
              <button onClick={saveDashboard} disabled={saving} className="btn-ghost py-1.5 px-3 text-xs gap-1.5 disabled:opacity-50">
                {saving ? <Loader size={12} className="animate-spin" /> : <Save size={12} />}
                Save
              </button>
              {!isPublished && (
                <button onClick={publishDashboard} disabled={saving}
                  className="btn-primary py-1.5 px-4 text-xs gap-1.5 disabled:opacity-60">
                  {saving ? <Loader size={12} className="animate-spin" /> : <CheckCircle2 size={12} />}
                  Publish
                </button>
              )}
              {isPublished && (
                <span className="text-xs text-mint-400 flex items-center gap-1.5 px-3">
                  <CheckCircle2 size={11} /> Live — viewers can see this
                </span>
              )}
            </>
          )}
        </div>

        {/* Canvas */}
        <div className="flex-1 overflow-auto p-5">
          {widgets.length === 0 ? (
            <div className="flex flex-col items-center justify-center h-full gap-6">
              <div className="w-20 h-20 rounded-2xl flex items-center justify-center"
                style={{ background: 'rgba(124,58,237,0.08)', border: '1px solid rgba(124,58,237,0.2)' }}>
                <BarChart3 size={32} className="text-violet-400" />
              </div>
              <div className="text-center">
                <p className="text-slate-300 font-semibold mb-1">Empty canvas</p>
                <p className="text-slate-600 text-sm">Add a widget to start building your dashboard</p>
              </div>
              <button onClick={() => setShowAdd(true)} className="btn-violet gap-2">
                <Plus size={14} /> Add first widget
              </button>
            </div>
          ) : (
            <GridLayout
              className="layout"
              layout={layout}
              cols={cols}
              rowHeight={40}
              width={1100}
              onLayoutChange={setLayout}
              draggableHandle=".cursor-grab"
              resizeHandles={['se']}
            >
              {widgets.map(widget => (
                <div key={widget.id}>
                  <WidgetCard
                    widget={widget}
                    onRemove={removeWidget}
                    onEdit={setConfigId}
                  />
                </div>
              ))}
            </GridLayout>
          )}
        </div>
      </div>

      {/* Add panel */}
      <AnimatePresence>
        {showAdd && <AddPanel onAdd={addWidget} onClose={() => setShowAdd(false)} />}
      </AnimatePresence>

      {/* Widget config modal */}
      <AnimatePresence>
        {editingWidget && (
          <WidgetConfigModal
            key={configId}
            widget={editingWidget}
            onSave={saveWidgetConfig}
            onClose={() => setConfigId(null)}
            onLiveTitleChange={handleWidgetLiveTitle}
          />
        )}
      </AnimatePresence>
    </div>
  )
}
