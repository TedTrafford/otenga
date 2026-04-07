import React, { useEffect, useRef, useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { BarChart3, Plus, Trash2, Edit3, Clock, Send, X, ArrowRight, Layers, CheckCircle2, Eye } from 'lucide-react'
import { dashboardsApi } from '../api/client'
import useAuthStore from '../store/authStore'
import DashboardBuilder from '../components/dashboard/DashboardBuilder'
import toast from 'react-hot-toast'
import { formatDistanceToNow } from 'date-fns'

// ── Create Dashboard Modal ───────────────────────────────────────────────────
function CreateModal({ onConfirm, onClose }) {
  const [name, setName]         = useState('')
  const [desc, setDesc]         = useState('')
  const [loading, setLoading]   = useState(false)
  const inputRef                = useRef(null)

  useEffect(() => { inputRef.current?.focus() }, [])
  useEffect(() => {
    const handler = (e) => { if (e.key === 'Escape') onClose() }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [onClose])

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (!name.trim()) return
    setLoading(true)
    await onConfirm(name.trim(), desc.trim())
    setLoading(false)
  }

  return (
    <motion.div
      initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
      className="fixed inset-0 z-[100] flex items-center justify-center px-4"
      style={{ background: 'rgba(3,3,16,0.75)', backdropFilter: 'blur(8px)' }}
      onClick={onClose}
    >
      <motion.div
        initial={{ y: 20, opacity: 0, scale: 0.96 }}
        animate={{ y: 0, opacity: 1, scale: 1 }}
        exit={{ y: 20, opacity: 0, scale: 0.96 }}
        transition={{ duration: 0.2, ease: 'easeOut' }}
        className="w-full max-w-md rounded-2xl overflow-hidden"
        style={{
          background: 'rgba(10,10,37,0.98)',
          border: '1px solid rgba(124,58,237,0.3)',
          boxShadow: '0 24px 64px rgba(0,0,0,0.6), 0 0 40px rgba(124,58,237,0.08)',
        }}
        onClick={e => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4" style={{ borderBottom: '1px solid rgba(255,255,255,0.07)' }}>
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-xl flex items-center justify-center"
              style={{ background: 'rgba(124,58,237,0.15)', border: '1px solid rgba(124,58,237,0.3)' }}>
              <Layers size={17} className="text-violet-400" />
            </div>
            <div>
              <h2 className="text-sm font-bold text-slate-100">New Dashboard</h2>
              <p className="text-[11px] text-slate-500 mt-0.5">Name your dashboard to get started</p>
            </div>
          </div>
          <button onClick={onClose} className="p-1.5 rounded-lg text-slate-600 hover:text-slate-400 hover:bg-white/5 transition-all">
            <X size={15} />
          </button>
        </div>

        {/* Form */}
        <form onSubmit={handleSubmit} className="px-6 py-5 space-y-4">
          <div>
            <label className="block text-xs font-medium text-slate-400 mb-1.5">
              Dashboard name <span className="text-rose-400">*</span>
            </label>
            <input
              ref={inputRef}
              type="text"
              value={name}
              onChange={e => setName(e.target.value)}
              placeholder="e.g. Sales Overview, Monthly KPIs..."
              className="input-field"
              maxLength={120}
              required
            />
          </div>

          <div>
            <label className="block text-xs font-medium text-slate-400 mb-1.5">
              Description <span className="text-slate-600">(optional)</span>
            </label>
            <textarea
              value={desc}
              onChange={e => setDesc(e.target.value)}
              placeholder="What does this dashboard show?"
              rows={2}
              className="input-field resize-none"
              maxLength={300}
            />
          </div>

          <div className="flex gap-3 pt-1">
            <button type="button" onClick={onClose} className="btn-ghost flex-1 justify-center py-2.5">
              Cancel
            </button>
            <button
              type="submit"
              disabled={!name.trim() || loading}
              className="btn-violet flex-1 justify-center py-2.5 disabled:opacity-50 disabled:cursor-not-allowed gap-2"
            >
              {loading
                ? <span className="w-3.5 h-3.5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                : <ArrowRight size={14} />}
              {loading ? 'Creating...' : 'Create Dashboard'}
            </button>
          </div>
        </form>
      </motion.div>
    </motion.div>
  )
}

// ── Main Page ────────────────────────────────────────────────────────────────
export default function DashboardPage() {
  const [dashboards, setDashboards]   = useState([])
  const [loading, setLoading]         = useState(true)
  const [selected, setSelected]       = useState(null)
  const [mode, setMode]               = useState('list')   // 'list' | 'build'
  const [showCreate, setShowCreate]   = useState(false)
  const { isCreator, isSuperuser }    = useAuthStore()

  useEffect(() => {
    dashboardsApi.list().then(r => setDashboards(r.data)).finally(() => setLoading(false))
  }, [])

  const handleCreate = async (name, description) => {
    try {
      const { data } = await dashboardsApi.create({ name, description })
      setDashboards(d => [data, ...d])
      setSelected(data)
      setMode('build')
      setShowCreate(false)
      toast.success(`"${name}" created`)
    } catch {
      toast.error('Failed to create dashboard')
    }
  }

  const handleDelete = async (id, e) => {
    e.stopPropagation()
    try {
      await dashboardsApi.delete(id)
      setDashboards(d => d.filter(x => x.id !== id))
      if (selected?.id === id) { setSelected(null); setMode('list') }
      toast.success('Dashboard deleted')
    } catch {
      toast.error('Failed to delete dashboard')
    }
  }

  const handleSubmit = async (id, e) => {
    e.stopPropagation()
    try {
      const { data } = await dashboardsApi.submit(id)
      setDashboards(d => d.map(x => x.id === id ? data : x))
      toast.success('Submitted for review! A superuser will approve it.')
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to submit')
    }
  }

  const handlePublish = async (id, e) => {
    e.stopPropagation()
    try {
      const { data } = await dashboardsApi.publish(id)
      setDashboards(d => d.map(x => x.id === id ? data : x))
      toast.success('Dashboard published — viewers can now see it!')
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to publish')
    }
  }

  const statusStyle = {
    draft:            { text: '#FFB800', bg: 'rgba(255,184,0,0.1)',   border: 'rgba(255,184,0,0.2)'   },
    published:        { text: '#06FFA5', bg: 'rgba(6,255,165,0.1)',   border: 'rgba(6,255,165,0.2)'   },
    pending_approval: { text: '#A78BFA', bg: 'rgba(124,58,237,0.12)', border: 'rgba(124,58,237,0.25)' },
  }

  // ── Builder view ────────────────────────────────────────────────────────
  if (mode === 'build' && selected) {
    return (
      <div className="flex flex-col h-full">
        <div className="px-4 py-2.5 border-b border-white/5 flex items-center gap-2 flex-shrink-0"
          style={{ background: 'rgba(5,5,21,0.5)' }}>
          <button onClick={() => setMode('list')} className="btn-ghost py-1 px-2.5 text-xs gap-1.5">
            <BarChart3 size={11} /> Dashboards
          </button>
          <span className="text-slate-700">/</span>
          <span className="text-xs text-slate-400 truncate max-w-xs">{selected.name}</span>
        </div>
        <div className="flex-1 min-h-0">
          <DashboardBuilder
            dashboard={selected}
            onSave={(updates) => {
              const merged = { ...selected, ...updates }
              setSelected(merged)
              setDashboards(d => d.map(x => x.id === selected.id ? merged : x))
            }}
          />
        </div>
      </div>
    )
  }

  // ── List view ───────────────────────────────────────────────────────────
  return (
    <>
      <div className="p-6">
        {/* Header */}
        <div className="flex items-center justify-between mb-6">
          <div>
            <h1 className="text-lg font-bold text-slate-100">Dashboards</h1>
            <p className="text-xs text-slate-500 mt-0.5">Build and share interactive data dashboards</p>
          </div>
          {isCreator() && (
            <button onClick={() => setShowCreate(true)} className="btn-violet gap-2">
              <Plus size={14} /> New Dashboard
            </button>
          )}
        </div>

        {/* Content */}
        {loading ? (
          <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
            {[...Array(6)].map((_, i) => <div key={i} className="skeleton h-44 rounded-2xl" />)}
          </div>
        ) : dashboards.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-36 gap-5">
            <div className="w-20 h-20 rounded-2xl flex items-center justify-center"
              style={{ background: 'rgba(124,58,237,0.08)', border: '1px solid rgba(124,58,237,0.2)' }}>
              <BarChart3 size={32} className="text-violet-400" />
            </div>
            <div className="text-center">
              <p className="text-slate-300 font-semibold mb-1">No dashboards yet</p>
              <p className="text-slate-600 text-sm">Create your first dashboard to get started</p>
            </div>
            {isCreator() && (
              <button onClick={() => setShowCreate(true)} className="btn-violet gap-2">
                <Plus size={14} /> Create Dashboard
              </button>
            )}
          </div>
        ) : (
          <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
            {dashboards.map((dash, i) => {
              const s = statusStyle[dash.status] || statusStyle.draft
              return (
                <motion.div
                  key={dash.id}
                  initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: i * 0.05 }}
                  onClick={() => { setSelected(dash); setMode('build') }}
                  className="glass-hover rounded-2xl p-5 cursor-pointer group relative overflow-hidden"
                >
                  {/* Subtle ambient glow */}
                  <div className="absolute inset-0 opacity-[0.04] rounded-2xl pointer-events-none"
                    style={{ background: `radial-gradient(circle at 80% 0%, ${s.text}, transparent 60%)` }} />

                  <div className="flex items-start justify-between gap-3 mb-4">
                    <div className="w-11 h-11 rounded-xl flex items-center justify-center flex-shrink-0"
                      style={{ background: `${s.text}10`, border: `1px solid ${s.text}25` }}>
                      <BarChart3 size={18} style={{ color: s.text }} />
                    </div>
                    <span className="text-[10px] px-2 py-1 rounded-full font-medium capitalize flex-shrink-0"
                      style={{ background: s.bg, color: s.text, border: `1px solid ${s.border}` }}>
                      {dash.status?.replace('_', ' ')}
                    </span>
                  </div>

                  <h3 className="text-sm font-semibold text-slate-200 mb-1 truncate">{dash.name}</h3>
                  {dash.description && (
                    <p className="text-xs text-slate-500 mb-3 line-clamp-2">{dash.description}</p>
                  )}

                  <div className="flex items-center gap-2 text-[11px] text-slate-600">
                    <Clock size={10} />
                    {formatDistanceToNow(new Date(dash.updated_at || dash.created_at), { addSuffix: true })}
                    <span className="ml-auto">{(dash.widgets || []).length} widget{(dash.widgets || []).length !== 1 ? 's' : ''}</span>
                  </div>

                  {/* Hover action buttons */}
                  <div className="absolute top-3 right-3 flex gap-1.5 opacity-0 group-hover:opacity-100 transition-all duration-200">
                    {/* Edit — creator on draft/pending, superuser always */}
                    {(isCreator() && dash.status !== 'published') || isSuperuser() ? (
                      <button
                        onClick={e => { e.stopPropagation(); setSelected(dash); setMode('build') }}
                        className="p-1.5 rounded-lg text-slate-500 hover:text-primary hover:bg-primary/10 transition-all"
                        title="Open builder">
                        <Edit3 size={12} />
                      </button>
                    ) : (
                      /* Viewer: view-only */
                      <button
                        onClick={e => { e.stopPropagation(); setSelected(dash); setMode('build') }}
                        className="p-1.5 rounded-lg text-slate-500 hover:text-primary hover:bg-primary/10 transition-all"
                        title="View dashboard">
                        <Eye size={12} />
                      </button>
                    )}

                    {/* Creator: submit draft for review */}
                    {isCreator() && dash.status === 'draft' && (
                      <button
                        onClick={e => handleSubmit(dash.id, e)}
                        className="p-1.5 rounded-lg text-slate-500 hover:text-violet-400 hover:bg-violet-500/10 transition-all"
                        title="Submit for review">
                        <Send size={12} />
                      </button>
                    )}

                    {/* Superuser: publish pending dashboards */}
                    {isSuperuser() && (dash.status === 'pending_approval' || dash.status === 'draft') && (
                      <button
                        onClick={e => handlePublish(dash.id, e)}
                        className="p-1.5 rounded-lg text-slate-500 hover:text-mint-500 hover:bg-mint-500/10 transition-all"
                        title="Publish dashboard">
                        <CheckCircle2 size={12} />
                      </button>
                    )}

                    {/* Delete — creator and superuser */}
                    {(isCreator() || isSuperuser()) && (
                      <button
                        onClick={e => handleDelete(dash.id, e)}
                        className="p-1.5 rounded-lg text-slate-500 hover:text-rose-400 hover:bg-rose-500/10 transition-all"
                        title="Delete">
                        <Trash2 size={12} />
                      </button>
                    )}
                  </div>
                </motion.div>
              )
            })}
          </div>
        )}
      </div>

      {/* Create Modal */}
      <AnimatePresence>
        {showCreate && (
          <CreateModal
            onConfirm={handleCreate}
            onClose={() => setShowCreate(false)}
          />
        )}
      </AnimatePresence>
    </>
  )
}
