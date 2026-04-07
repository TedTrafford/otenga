import React, { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { motion } from 'framer-motion'
import {
  Activity, BookOpen, BarChart3, ArrowRight, Clock,
  CheckCircle2, Eye, Layers,
} from 'lucide-react'
import useNotebookStore from '../store/notebookStore'
import useAuthStore from '../store/authStore'
import { dashboardsApi } from '../api/client'
import toast from 'react-hot-toast'
import { formatDistanceToNow } from 'date-fns'

// ── Notebook report card ──────────────────────────────────────────────────────
function NotebookCard({ nb, onApprove }) {
  const navigate = useNavigate()
  const { isSuperuser } = useAuthStore()

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }}
      className="glass-hover rounded-2xl p-5 cursor-pointer group"
      onClick={() => navigate(`/editor/${nb.id}`)}
    >
      <div className="flex items-start justify-between gap-3">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-2">
            {nb.status === 'published'        && <CheckCircle2 size={14} className="text-mint-500 flex-shrink-0" />}
            {nb.status === 'pending_approval' && <Clock size={14} className="text-violet-400 flex-shrink-0" />}
            {nb.status === 'draft'            && <Activity size={14} className="text-amber-400 flex-shrink-0" />}
            <h3 className="text-sm font-semibold text-slate-200 truncate">{nb.name}</h3>
          </div>
          {nb.description && <p className="text-xs text-slate-500 mb-2 truncate">{nb.description}</p>}
          <div className="flex items-center gap-3 text-[11px] text-slate-600">
            <span>By: {nb.owner?.username || 'Unknown'}</span>
            <span>·</span>
            <span className="flex items-center gap-1">
              <Clock size={9} />
              {formatDistanceToNow(new Date(nb.updated_at || nb.created_at), { addSuffix: true })}
            </span>
            <span>· {nb.cells?.length || 0} cells</span>
          </div>
        </div>
        <div className="flex flex-col items-end gap-2 flex-shrink-0">
          {nb.status === 'published'        && <span className="badge-mint capitalize">Published</span>}
          {nb.status === 'pending_approval' && <span className="badge-violet">Pending</span>}
          {nb.status === 'draft'            && <span className="badge-amber">Draft</span>}
          <ArrowRight size={14} className="text-slate-600 group-hover:text-primary transition-colors" />
        </div>
      </div>

      {isSuperuser() && nb.status === 'pending_approval' && (
        <div className="mt-4 pt-4 border-t border-white/5 flex gap-3">
          <button
            onClick={e => { e.stopPropagation(); onApprove(nb.id) }}
            className="btn-primary py-1.5 px-3 text-xs gap-1.5">
            <CheckCircle2 size={11} /> Approve & Publish
          </button>
          <button
            onClick={e => { e.stopPropagation(); navigate(`/editor/${nb.id}`) }}
            className="btn-ghost py-1.5 px-3 text-xs gap-1.5">
            <Eye size={11} /> Review
          </button>
        </div>
      )}
    </motion.div>
  )
}

// ── Dashboard report card ─────────────────────────────────────────────────────
function DashboardCard({ dash, onPublish }) {
  const navigate    = useNavigate()
  const { isSuperuser } = useAuthStore()

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }}
      className="glass-hover rounded-2xl p-5 cursor-pointer group"
      onClick={() => navigate('/dashboards')}
    >
      <div className="flex items-start justify-between gap-3">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-2">
            <BarChart3 size={14} className="text-violet-400 flex-shrink-0" />
            <h3 className="text-sm font-semibold text-slate-200 truncate">{dash.name}</h3>
          </div>
          {dash.description && <p className="text-xs text-slate-500 mb-2 truncate">{dash.description}</p>}
          <div className="flex items-center gap-3 text-[11px] text-slate-600">
            <span>{(dash.widgets || []).length} widget{(dash.widgets || []).length !== 1 ? 's' : ''}</span>
            <span>·</span>
            <span className="flex items-center gap-1">
              <Clock size={9} />
              {formatDistanceToNow(new Date(dash.updated_at || dash.created_at), { addSuffix: true })}
            </span>
          </div>
        </div>
        <div className="flex flex-col items-end gap-2 flex-shrink-0">
          {dash.status === 'published'        && <span className="badge-mint capitalize">Published</span>}
          {dash.status === 'pending_approval' && <span className="badge-violet">Pending</span>}
          {dash.status === 'draft'            && <span className="badge-amber">Draft</span>}
          <ArrowRight size={14} className="text-slate-600 group-hover:text-primary transition-colors" />
        </div>
      </div>

      {isSuperuser() && dash.status === 'pending_approval' && (
        <div className="mt-4 pt-4 border-t border-white/5 flex gap-3">
          <button
            onClick={e => { e.stopPropagation(); onPublish(dash.id) }}
            className="btn-primary py-1.5 px-3 text-xs gap-1.5">
            <CheckCircle2 size={11} /> Approve & Publish
          </button>
          <button
            onClick={e => { e.stopPropagation(); navigate('/dashboards') }}
            className="btn-ghost py-1.5 px-3 text-xs gap-1.5">
            <Eye size={11} /> Review
          </button>
        </div>
      )}
    </motion.div>
  )
}

// ── Section header ─────────────────────────────────────────────────────────────
function SectionHeader({ icon: Icon, iconClass, label, badge, badgeClass }) {
  return (
    <h2 className="text-sm font-semibold text-slate-300 mb-3 flex items-center gap-2">
      <Icon size={14} className={iconClass} />
      {label}
      {badge != null && <span className={badgeClass}>{badge}</span>}
    </h2>
  )
}

// ── Main page ──────────────────────────────────────────────────────────────────
export default function ReportsPage() {
  const { notebooks, fetchNotebooks } = useNotebookStore()
  const { isSuperuser }               = useAuthStore()
  const [pendingDashboards, setPendingDashboards] = useState([])

  useEffect(() => {
    fetchNotebooks()
    if (isSuperuser()) {
      dashboardsApi.pending()
        .then(r => setPendingDashboards(r.data))
        .catch(() => {})
    }
  }, [isSuperuser])

  const approveNotebook = (id) => {
    useNotebookStore.getState().publishNotebook(id)
  }

  const publishDashboard = async (id) => {
    try {
      await dashboardsApi.publish(id)
      setPendingDashboards(d => d.filter(x => x.id !== id))
      toast.success('Dashboard published!')
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to publish dashboard')
    }
  }

  const published        = notebooks.filter(n => n.status === 'published')
  const pendingNotebooks = notebooks.filter(n => n.status === 'pending_approval')

  const totalPending = pendingNotebooks.length + pendingDashboards.length

  return (
    <div className="p-6 space-y-8">
      <div>
        <h1 className="text-lg font-bold text-slate-100">Reports</h1>
        <p className="text-xs text-slate-500 mt-0.5">Published content and approval queue</p>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-3 gap-4">
        {[
          { label: 'Published Reports',   value: published.length,       color: '#06FFA5' },
          { label: 'Pending Approval',    value: totalPending,            color: '#7C3AED' },
          { label: 'Total Notebooks',     value: notebooks.length,        color: '#00D4FF' },
        ].map(({ label, value, color }) => (
          <div key={label} className="glass rounded-xl p-4 text-center">
            <p className="text-2xl font-bold mb-0.5" style={{ color }}>{value}</p>
            <p className="text-xs text-slate-500">{label}</p>
          </div>
        ))}
      </div>

      {/* ── Pending approval (superuser only) ───────────────────────────── */}
      {isSuperuser() && totalPending > 0 && (
        <div className="space-y-6">
          <div className="rounded-2xl overflow-hidden"
            style={{ border: '1px solid rgba(124,58,237,0.25)', background: 'rgba(124,58,237,0.04)' }}>
            <div className="px-5 py-3 flex items-center gap-2" style={{ borderBottom: '1px solid rgba(124,58,237,0.15)' }}>
              <Clock size={14} className="text-violet-400" />
              <span className="text-sm font-semibold text-slate-200">Pending Approval</span>
              <span className="badge-violet ml-1">{totalPending}</span>
              <span className="text-xs text-slate-600 ml-2">— approve to make visible to viewers</span>
            </div>

            <div className="p-4 space-y-3">
              {/* Pending notebooks */}
              {pendingNotebooks.length > 0 && (
                <>
                  <p className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider flex items-center gap-1.5">
                    <BookOpen size={10} /> Notebooks ({pendingNotebooks.length})
                  </p>
                  {pendingNotebooks.map(nb => (
                    <NotebookCard key={`nb-${nb.id}`} nb={nb} onApprove={approveNotebook} />
                  ))}
                </>
              )}

              {/* Pending dashboards */}
              {pendingDashboards.length > 0 && (
                <>
                  <p className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider flex items-center gap-1.5 mt-3">
                    <Layers size={10} /> Dashboards ({pendingDashboards.length})
                  </p>
                  {pendingDashboards.map(dash => (
                    <DashboardCard key={`dash-${dash.id}`} dash={dash} onPublish={publishDashboard} />
                  ))}
                </>
              )}
            </div>
          </div>
        </div>
      )}

      {/* ── Published notebooks ──────────────────────────────────────────── */}
      <div>
        <SectionHeader icon={CheckCircle2} iconClass="text-mint-500" label="Published Reports"
          badge={published.length} badgeClass="badge-mint" />
        {published.length > 0 ? (
          <div className="space-y-3">
            {published.map(nb => <NotebookCard key={nb.id} nb={nb} onApprove={approveNotebook} />)}
          </div>
        ) : (
          <div className="glass rounded-2xl p-10 text-center">
            <Activity size={32} className="text-slate-700 mx-auto mb-3" />
            <p className="text-slate-500 text-sm">No published reports yet</p>
          </div>
        )}
      </div>

      {/* ── All notebooks (superuser) ────────────────────────────────────── */}
      {isSuperuser() && (
        <div>
          <SectionHeader icon={BookOpen} iconClass="text-primary" label="All Notebooks"
            badge={notebooks.length} badgeClass="badge-cyan" />
          <div className="space-y-3">
            {notebooks.map(nb => <NotebookCard key={nb.id} nb={nb} onApprove={approveNotebook} />)}
          </div>
        </div>
      )}
    </div>
  )
}
