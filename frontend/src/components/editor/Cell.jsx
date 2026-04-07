import React, { useState, useCallback } from 'react'
import { motion } from 'framer-motion'
import { Play, Trash2, ChevronUp, ChevronDown, Plus, Database, Code, FileText, MoreHorizontal, Copy, GripVertical } from 'lucide-react'
import Editor from '@monaco-editor/react'
import useNotebookStore from '../../store/notebookStore'
import ResultViewer from './ResultViewer'

const CELL_TYPES = {
  sql:      { label: 'SQL',      icon: Database, color: '#00D4FF', bg: 'rgba(0,212,255,0.08)',  border: 'rgba(0,212,255,0.2)',  lang: 'sql'    },
  python:   { label: 'Python',   icon: Code,     color: '#7C3AED', bg: 'rgba(124,58,237,0.08)', border: 'rgba(124,58,237,0.2)', lang: 'python' },
  markdown: { label: 'Markdown', icon: FileText,  color: '#06FFA5', bg: 'rgba(6,255,165,0.06)',  border: 'rgba(6,255,165,0.15)', lang: 'markdown' },
}

const monacoOptions = {
  minimap:            { enabled: false },
  lineNumbers:        'on',
  scrollBeyondLastLine: false,
  wordWrap:           'on',
  fontSize:           13,
  fontFamily:         "'JetBrains Mono', 'Fira Code', monospace",
  fontLigatures:      true,
  padding:            { top: 12, bottom: 12 },
  scrollbar:          { vertical: 'hidden', horizontal: 'hidden' },
  overviewRulerLanes: 0,
  renderLineHighlight:'line',
  lineHeight:         20,
  suggestFontSize:    12,
}

export default function Cell({ cell, index, total }) {
  const [menuOpen, setMenuOpen]   = useState(false)
  const [editorH,  setEditorH]    = useState(Math.max(80, Math.min(400, cell.code.split('\n').length * 20 + 24)))
  const { runCell, removeCell, addCell, updateCellCode, updateCellType, moveCellUp, moveCellDown, runningCells } = useNotebookStore()

  const isRunning = runningCells.has(cell.id)
  const config    = CELL_TYPES[cell.type] || CELL_TYPES.sql

  const handleEditorChange = useCallback((val) => {
    updateCellCode(cell.id, val || '')
    const lines = (val || '').split('\n').length
    setEditorH(Math.max(80, Math.min(500, lines * 20 + 24)))
  }, [cell.id, updateCellCode])

  const handleEditorMount = (editor, monacoInstance) => {
    editor.addCommand(
      monacoInstance.KeyMod.CtrlCmd | monacoInstance.KeyCode.Enter,
      () => runCell(cell.id)
    )
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -10 }}
      transition={{ duration: 0.2 }}
      className="group relative"
    >
      {/* Cell container */}
      <div className="relative rounded-xl overflow-visible transition-all duration-200"
        style={{
          background: isRunning ? `${config.bg}` : 'rgba(255,255,255,0.025)',
          border: `1px solid ${isRunning ? config.border : 'rgba(255,255,255,0.07)'}`,
          boxShadow: isRunning ? `0 0 20px ${config.color}20` : 'none',
        }}
      >
        {/* Left accent bar */}
        <div className="absolute left-0 top-0 bottom-0 w-0.5 rounded-l-xl"
          style={{ background: `linear-gradient(180deg, ${config.color}AA, ${config.color}44)` }} />

        {/* Cell header */}
        <div className="flex items-center gap-3 px-4 py-2.5 pl-5" style={{ borderBottom: '1px solid rgba(255,255,255,0.05)' }}>
          <div className="flex items-center gap-2 flex-1">
            {/* Cell type selector */}
            <div className="relative">
              <select
                value={cell.type}
                onChange={(e) => updateCellType(cell.id, e.target.value)}
                className="text-xs font-semibold px-2.5 py-1 rounded-md cursor-pointer outline-none appearance-none pr-6 transition-all duration-200"
                style={{ background: config.bg, color: config.color, border: `1px solid ${config.border}` }}
              >
                <option value="sql">SQL</option>
                <option value="python">Python</option>
                <option value="markdown">Markdown</option>
              </select>
              <ChevronDown size={10} className="absolute right-1.5 top-1/2 -translate-y-1/2 pointer-events-none" style={{ color: config.color }} />
            </div>

            <span className="text-slate-600 text-[10px] font-mono">In [{index + 1}]</span>
          </div>

          {/* Actions */}
          <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity duration-200">
            <button onClick={() => moveCellUp(cell.id)} disabled={index === 0}
              className="p-1.5 rounded-md text-slate-600 hover:text-slate-300 hover:bg-white/5 transition-all duration-150 disabled:opacity-30" title="Move up">
              <ChevronUp size={13} />
            </button>
            <button onClick={() => moveCellDown(cell.id)} disabled={index === total - 1}
              className="p-1.5 rounded-md text-slate-600 hover:text-slate-300 hover:bg-white/5 transition-all duration-150 disabled:opacity-30" title="Move down">
              <ChevronDown size={13} />
            </button>
            <button onClick={() => addCell(cell.type, index)}
              className="p-1.5 rounded-md text-slate-600 hover:text-primary hover:bg-primary/10 transition-all duration-150" title="Insert cell below">
              <Plus size={13} />
            </button>
            <button onClick={() => removeCell(cell.id)}
              className="p-1.5 rounded-md text-slate-600 hover:text-rose-400 hover:bg-rose-500/10 transition-all duration-150" title="Delete cell">
              <Trash2 size={13} />
            </button>
          </div>

          {/* Run button */}
          <button
            onClick={() => runCell(cell.id)}
            disabled={isRunning}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold transition-all duration-200 disabled:opacity-60"
            style={{
              background: isRunning ? `${config.bg}` : `linear-gradient(135deg, ${config.color}DD, ${config.color}99)`,
              color: isRunning ? config.color : '#020D14',
              border: `1px solid ${config.border}`,
              boxShadow: isRunning ? 'none' : `0 0 12px ${config.color}33`,
            }}
          >
            {isRunning ? (
              <span className="w-3 h-3 border-2 rounded-full animate-spin" style={{ borderColor: `${config.color}40`, borderTopColor: config.color }} />
            ) : (
              <Play size={11} fill="currentColor" />
            )}
            {isRunning ? 'Running' : 'Run'}
          </button>
        </div>

        {/* Code editor */}
        <div className="pl-5">
          <Editor
            height={`${editorH}px`}
            language={config.lang}
            value={cell.code}
            onChange={handleEditorChange}
            onMount={handleEditorMount}
            theme="vs-dark"
            options={monacoOptions}
          />
        </div>
      </div>

      {/* Result */}
      <ResultViewer result={cell.result} isRunning={isRunning} />

      {/* Insert cell divider (appears on hover between cells) */}
      <div className="flex items-center gap-3 py-1 opacity-0 group-hover:opacity-100 transition-opacity duration-300 mt-2">
        <div className="flex-1 h-px" style={{ background: 'linear-gradient(90deg, transparent, rgba(0,212,255,0.15), transparent)' }} />
        <div className="flex gap-1.5">
          {['sql', 'python', 'markdown'].map((t) => (
            <button key={t} onClick={() => addCell(t, index)}
              className="text-[10px] px-2 py-0.5 rounded font-medium transition-all duration-150"
              style={{
                background: `${CELL_TYPES[t].bg}`,
                color: CELL_TYPES[t].color,
                border: `1px solid ${CELL_TYPES[t].border}`,
              }}>
              + {t.toUpperCase()}
            </button>
          ))}
        </div>
        <div className="flex-1 h-px" style={{ background: 'linear-gradient(90deg, rgba(0,212,255,0.15), transparent)' }} />
      </div>
    </motion.div>
  )
}
