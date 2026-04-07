import React, { useEffect, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { motion, AnimatePresence } from 'framer-motion'
import { Plus, BookOpen, Trash2, ArrowRight, Search, Clock } from 'lucide-react'
import useNotebookStore from '../store/notebookStore'
import useAuthStore from '../store/authStore'
import NotebookEditor from '../components/editor/NotebookEditor'
import { formatDistanceToNow } from 'date-fns'

const statusColors = {
  draft:            { text: 'text-amber-400',  bg: 'bg-amber-500/10',  border: 'border-amber-500/20' },
  published:        { text: 'text-mint-500',    bg: 'bg-mint-500/10',   border: 'border-mint-500/20'  },
  pending_approval: { text: 'text-violet-400', bg: 'bg-violet-500/10', border: 'border-violet-500/20' },
}

export default function EditorPage() {
  const { id } = useParams()
  const navigate = useNavigate()
  const { notebooks, currentNotebook, fetchNotebooks, fetchNotebook, createNotebook, deleteNotebook, setCurrentNotebook } = useNotebookStore()
  const { isCreator } = useAuthStore()
  const [search, setSearch] = useState('')
  const [showList, setShowList] = useState(!id)

  useEffect(() => {
    fetchNotebooks()
    if (id) {
      fetchNotebook(Number(id))
      setShowList(false)
    }
  }, [id])

  const handleSelect = async (nb) => {
    const full = await fetchNotebook(nb.id)
    if (full) {
      navigate(`/editor/${nb.id}`)
      setShowList(false)
    }
  }

  const handleNew = async () => {
    const nb = await createNotebook()
    if (nb) navigate(`/editor/${nb.id}`)
  }

  const filtered = notebooks.filter((n) =>
    n.name.toLowerCase().includes(search.toLowerCase()) ||
    n.description?.toLowerCase().includes(search.toLowerCase())
  )

  return (
    <div className="flex h-full">
      {/* Notebooks list panel */}
      <AnimatePresence>
        {(showList || !id) && (
          <motion.div
            initial={{ x: -280, opacity: 0 }} animate={{ x: 0, opacity: 1 }} exit={{ x: -280, opacity: 0 }}
            className="w-72 border-r border-white/5 flex flex-col flex-shrink-0"
            style={{ background: 'rgba(5,5,21,0.7)' }}
          >
            {/* Panel header */}
            <div className="px-4 py-4 border-b border-white/5">
              <div className="flex items-center justify-between mb-3">
                <div className="flex items-center gap-2">
                  <BookOpen size={15} className="text-primary" />
                  <span className="text-sm font-semibold text-slate-200">Notebooks</span>
                  <span className="badge-cyan text-[10px] py-0">{notebooks.length}</span>
                </div>
                {isCreator() && (
                  <button onClick={handleNew} className="btn-primary py-1.5 px-2.5 text-xs gap-1">
                    <Plus size={11} /> New
                  </button>
                )}
              </div>
              <div className="relative">
                <Search size={13} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-500" />
                <input
                  type="text"
                  placeholder="Search notebooks..."
                  value={search}
                  onChange={(e) => setSearch(e.target.value)}
                  className="input-field pl-8 py-2 text-xs"
                />
              </div>
            </div>

            {/* Notebook list */}
            <div className="flex-1 overflow-y-auto p-2">
              {filtered.map((nb) => {
                const sc = statusColors[nb.status] || statusColors.draft
                const isActive = currentNotebook?.id === nb.id
                return (
                  <div key={nb.id}
                    className={`group flex items-start gap-3 px-3 py-3 rounded-xl cursor-pointer mb-1 transition-all duration-200 ${isActive ? 'bg-primary/10 border border-primary/20' : 'hover:bg-white/5 border border-transparent'}`}
                    onClick={() => handleSelect(nb)}
                  >
                    <div className="flex-1 min-w-0">
                      <p className={`text-xs font-semibold truncate ${isActive ? 'text-primary' : 'text-slate-300'}`}>{nb.name}</p>
                      {nb.description && <p className="text-[11px] text-slate-600 truncate mt-0.5">{nb.description}</p>}
                      <div className="flex items-center gap-2 mt-2">
                        <span className={`text-[10px] font-medium capitalize px-1.5 py-0.5 rounded-md ${sc.text} ${sc.bg} border ${sc.border}`}>
                          {nb.status?.replace('_', ' ')}
                        </span>
                        <span className="text-[10px] text-slate-600 flex items-center gap-1">
                          <Clock size={9} />
                          {formatDistanceToNow(new Date(nb.updated_at || nb.created_at), { addSuffix: true })}
                        </span>
                      </div>
                    </div>
                    <div className="flex gap-1 opacity-0 group-hover:opacity-100 transition-opacity mt-0.5">
                      <button onClick={(e) => { e.stopPropagation(); deleteNotebook(nb.id) }}
                        className="p-1 rounded text-slate-600 hover:text-rose-400 hover:bg-rose-500/10 transition-all">
                        <Trash2 size={11} />
                      </button>
                    </div>
                  </div>
                )
              })}

              {filtered.length === 0 && (
                <div className="text-center py-12">
                  <BookOpen size={28} className="text-slate-700 mx-auto mb-2" />
                  <p className="text-slate-600 text-xs">{search ? 'No matches found' : 'No notebooks yet'}</p>
                </div>
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Editor area */}
      <div className="flex-1 min-w-0 flex flex-col">
        {currentNotebook ? (
          <>
            {!showList && (
              <div className="flex-shrink-0 px-4 py-2 border-b border-white/5 flex items-center gap-2"
                style={{ background: 'rgba(5,5,21,0.4)' }}>
                <button onClick={() => setShowList(!showList)} className="btn-ghost py-1 px-2.5 text-xs gap-1.5">
                  <BookOpen size={11} /> Notebooks
                </button>
                <span className="text-slate-700">/</span>
                <span className="text-xs text-slate-400">{currentNotebook.name}</span>
              </div>
            )}
            <NotebookEditor notebook={currentNotebook} />
          </>
        ) : (
          <div className="flex items-center justify-center h-full">
            <div className="text-center">
              <div className="w-20 h-20 rounded-2xl flex items-center justify-center mx-auto mb-4"
                style={{ background: 'rgba(0,212,255,0.06)', border: '1px solid rgba(0,212,255,0.15)' }}>
                <BookOpen size={32} className="text-primary/50" />
              </div>
              <p className="text-slate-400 font-medium mb-1">Select a notebook</p>
              <p className="text-slate-600 text-sm mb-4">Choose from the panel or create a new one</p>
              {isCreator() && (
                <button onClick={handleNew} className="btn-primary gap-2">
                  <Plus size={14} /> New Notebook
                </button>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
