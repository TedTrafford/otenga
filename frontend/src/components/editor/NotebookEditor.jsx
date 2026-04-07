import React, { useEffect, useRef, useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { Play, Save, Plus, Trash2, Send, CheckCircle, Clock, Database, ChevronDown, ChevronRight, Table2, Loader } from 'lucide-react'
import useNotebookStore from '../../store/notebookStore'
import useAuthStore from '../../store/authStore'
import { executionApi } from '../../api/client'
import Cell from './Cell'

function DbSchemaPanel({ tables, loading, onInsert }) {
  const [expanded, setExpanded] = useState({})
  const [tableSchemas, setTableSchemas] = useState({})

  const toggleTable = async (table) => {
    setExpanded((p) => ({ ...p, [table]: !p[table] }))
    if (!tableSchemas[table]) {
      try {
        const { data } = await executionApi.getSchema(table)
        setTableSchemas((p) => ({ ...p, [table]: data.columns || [] }))
      } catch {}
    }
  }

  return (
    <div className="flex flex-col h-full">
      <div className="px-4 py-3 border-b border-white/5">
        <div className="flex items-center gap-2">
          <Database size={14} className="text-primary" />
          <span className="text-xs font-semibold text-slate-300">Data Sources</span>
          {loading && <Loader size={12} className="animate-spin text-slate-500 ml-auto" />}
        </div>
      </div>

      <div className="flex-1 overflow-y-auto px-2 py-2 space-y-0.5">
        {tables.map((table) => (
          <div key={table}>
            <button
              onClick={() => toggleTable(table)}
              className="w-full flex items-center gap-2 px-2 py-1.5 rounded-lg text-xs text-slate-400 hover:text-slate-200 hover:bg-white/5 transition-all duration-150"
            >
              {expanded[table] ? <ChevronDown size={12} /> : <ChevronRight size={12} />}
              <Table2 size={12} className="text-primary/60" />
              <span className="font-mono truncate">{table}</span>
            </button>
            <AnimatePresence>
              {expanded[table] && tableSchemas[table] && (
                <motion.div initial={{ height: 0, opacity: 0 }} animate={{ height: 'auto', opacity: 1 }} exit={{ height: 0, opacity: 0 }}
                  className="overflow-hidden ml-6">
                  {tableSchemas[table].map((col) => (
                    <div key={col.field}
                      onClick={() => onInsert(col.field)}
                      className="flex items-center gap-2 px-2 py-1 rounded text-[11px] text-slate-500 hover:text-slate-300 cursor-pointer hover:bg-white/5 transition-all">
                      <span className="text-violet-400 font-mono">{col.field}</span>
                      <span className="text-slate-600 truncate">{col.type}</span>
                    </div>
                  ))}
                </motion.div>
              )}
            </AnimatePresence>
          </div>
        ))}

        {!loading && tables.length === 0 && (
          <p className="text-xs text-slate-600 text-center py-8">No tables found</p>
        )}
      </div>
    </div>
  )
}

export default function NotebookEditor({ notebook }) {
  const { currentNotebook, saveNotebook, runAllCells, addCell, publishNotebook, isSaving, dbTables, dbTablesLoading, fetchDbTables, updateNotebookName } = useNotebookStore()
  const { isSuperuser } = useAuthStore()
  const [showSchema, setShowSchema] = useState(true)
  const [editingName, setEditingName] = useState(false)
  const bottomRef = useRef(null)

  const nb = currentNotebook || notebook

  useEffect(() => {
    fetchDbTables()
  }, [])

  const handleKeyboardSave = (e) => {
    if ((e.ctrlKey || e.metaKey) && e.key === 's') {
      e.preventDefault()
      saveNotebook()
    }
  }

  useEffect(() => {
    window.addEventListener('keydown', handleKeyboardSave)
    return () => window.removeEventListener('keydown', handleKeyboardSave)
  }, [])

  if (!nb) return (
    <div className="flex items-center justify-center h-full text-slate-500">
      <p>Select or create a notebook to start</p>
    </div>
  )

  const statusConfig = {
    draft:            { label: 'Draft',            cls: 'badge-amber' },
    published:        { label: 'Published',        cls: 'badge-mint'  },
    pending_approval: { label: 'Pending Approval', cls: 'badge-violet' },
  }
  const status = statusConfig[nb.status] || statusConfig.draft

  return (
    <div className="flex h-full" onKeyDown={handleKeyboardSave}>
      {/* Schema sidebar */}
      <AnimatePresence>
        {showSchema && (
          <motion.div
            initial={{ width: 0, opacity: 0 }}
            animate={{ width: 220, opacity: 1 }}
            exit={{ width: 0, opacity: 0 }}
            transition={{ duration: 0.25 }}
            className="border-r border-white/5 overflow-hidden flex-shrink-0"
            style={{ background: 'rgba(5,5,21,0.6)' }}
          >
            <DbSchemaPanel tables={dbTables} loading={dbTablesLoading} onInsert={(col) => {}} />
          </motion.div>
        )}
      </AnimatePresence>

      {/* Main editor area */}
      <div className="flex-1 flex flex-col min-w-0">
        {/* Notebook toolbar */}
        <div className="flex items-center gap-3 px-6 py-3 border-b border-white/5 flex-shrink-0"
          style={{ background: 'rgba(5,5,21,0.5)' }}>
          {/* Name */}
          {editingName ? (
            <input
              autoFocus
              value={nb.name}
              onChange={(e) => updateNotebookName(e.target.value)}
              onBlur={() => setEditingName(false)}
              onKeyDown={(e) => { if (e.key === 'Enter') { setEditingName(false); saveNotebook() } }}
              className="text-sm font-semibold bg-transparent border-b border-primary/50 outline-none text-slate-100 px-1"
            />
          ) : (
            <h2 className="text-sm font-semibold text-slate-200 cursor-pointer hover:text-primary transition-colors" onClick={() => setEditingName(true)}>
              {nb.name}
            </h2>
          )}

          <span className={status.cls}>{status.label}</span>

          <div className="flex-1" />

          {/* Actions */}
          <button onClick={() => setShowSchema(!showSchema)} className="btn-ghost py-1.5 px-2.5 text-xs gap-1.5">
            <Database size={12} /> Schema
          </button>

          <button onClick={runAllCells} className="btn-ghost py-1.5 px-2.5 text-xs gap-1.5">
            <Play size={12} fill="currentColor" /> Run All
          </button>

          <button onClick={saveNotebook} disabled={isSaving} className="btn-ghost py-1.5 px-2.5 text-xs gap-1.5 disabled:opacity-60">
            {isSaving ? <Loader size={12} className="animate-spin" /> : <Save size={12} />}
            {isSaving ? 'Saving...' : 'Save'}
          </button>

          <button onClick={() => publishNotebook(nb.id)} className="btn-primary py-1.5 px-3 text-xs gap-1.5">
            <Send size={12} />
            {isSuperuser() ? 'Publish' : 'Submit for Review'}
          </button>
        </div>

        {/* Cells */}
        <div className="flex-1 overflow-y-auto px-6 py-6 space-y-2">
          <AnimatePresence>
            {nb.cells?.length > 0 ? (
              nb.cells.map((cell, i) => (
                <Cell key={cell.id} cell={cell} index={i} total={nb.cells.length} />
              ))
            ) : (
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                className="flex flex-col items-center justify-center py-24 gap-6"
              >
                <div className="w-16 h-16 rounded-2xl flex items-center justify-center"
                  style={{ background: 'rgba(0,212,255,0.08)', border: '1px solid rgba(0,212,255,0.2)' }}>
                  <Play size={24} className="text-primary ml-1" />
                </div>
                <div className="text-center">
                  <p className="text-slate-300 font-medium mb-1">Empty notebook</p>
                  <p className="text-slate-600 text-sm">Add your first cell to start building</p>
                </div>
                <div className="flex gap-3">
                  {['sql', 'python', 'markdown'].map((t) => (
                    <button key={t} onClick={() => addCell(t)} className="btn-ghost py-2 px-4 text-sm gap-2">
                      + {t.toUpperCase()}
                    </button>
                  ))}
                </div>
              </motion.div>
            )}
          </AnimatePresence>

          {/* Add cell at bottom */}
          {nb.cells?.length > 0 && (
            <div className="flex justify-center gap-3 pt-4">
              {['sql', 'python', 'markdown'].map((t) => (
                <button key={t} onClick={() => addCell(t)} className="btn-ghost py-1.5 px-3 text-xs gap-1.5">
                  <Plus size={11} /> {t.toUpperCase()}
                </button>
              ))}
            </div>
          )}

          <div ref={bottomRef} />
        </div>
      </div>
    </div>
  )
}
