import React, { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { motion } from 'framer-motion'
import {
  BookOpen, BarChart3, Plus, ArrowRight, TrendingUp,
  Activity, Clock, Zap, Shield, ChevronRight,
} from 'lucide-react'
import useNotebookStore from '../store/notebookStore'
import useAuthStore from '../store/authStore'
import { dashboardsApi } from '../api/client'
import { formatDistanceToNow } from 'date-fns'

// ── Clickable stat card ───────────────────────────────────────────────────────
const StatCard = ({ icon: Icon, label, value, sub, subAlert, color, delay, onClick }) => (
  <motion.div
    initial={{ opacity: 0, y: 20 }}
    animate={{ opacity: 1, y: 0 }}
    transition={{ delay, duration: 0.45 }}
    onClick={onClick}
    className={`glass rounded-2xl p-5 relative overflow-hidden group transition-all duration-200
      ${onClick ? 'cursor-pointer hover:ring-1' : ''}`}
    style={onClick ? { '--tw-ring-color': `${color}40` } : {}}
    whileHover={onClick ? { y: -3, scale: 1.02 } : {}}
  >
    {/* Ambient glow */}
    <div className="absolute inset-0 opacity-[0.05] rounded-2xl transition-opacity duration-200 group-hover:opacity-10"
      style={{ background: `radial-gradient(circle at 80% 20%, ${color}, transparent 70%)` }} />

    <div className="flex items-start justify-between relative">
      <div className="flex-1 min-w-0">
        <p className="text-xs font-medium text-slate-500 mb-1">{label}</p>
        <p className="text-3xl font-bold text-slate-100">{value}</p>
        {sub && (
          <p className={`text-xs mt-1.5 flex items-center gap-1 ${subAlert ? 'font-semibold' : 'text-slate-600'}`}
            style={subAlert ? { color } : {}}>
            {subAlert && <span className="w-1.5 h-1.5 rounded-full animate-pulse flex-shrink-0" style={{ background: color }} />}
            {sub}
          </p>
        )}
      </div>
      <div className="w-11 h-11 rounded-xl flex items-center justify-center flex-shrink-0 ml-3 transition-transform duration-200 group-hover:scale-110"
        style={{ background: `${color}15`, border: `1px solid ${color}30` }}>
        <Icon size={20} style={{ color }} />
      </div>
    </div>

    {/* Navigate arrow that appears on hover */}
    {onClick && (
      <div className="absolute bottom-3 right-4 opacity-0 group-hover:opacity-100 transition-opacity duration-200">
        <ChevronRight size={13} style={{ color }} />
      </div>
    )}
  </motion.div>
)

// ── Recent item card ──────────────────────────────────────────────────────────
const STATUS_COLOR = {
  draft:            '#FFB800',
  published:        '#06FFA5',
  pending_approval: '#A78BFA',
}

const RecentCard = ({ item, onClick }) => {
  const color = STATUS_COLOR[item.status] || '#FFB800'
  return (
    <motion.div
      whileHover={{ scale: 1.01, y: -2 }}
      onClick={onClick}
      className="glass-hover rounded-xl p-4 cursor-pointer"
    >
      <div className="flex items-start justify-between gap-3">
        <div className="flex-1 min-w-0">
          <p className="text-sm font-medium text-slate-200 truncate">{item.name}</p>
          {item.description && <p className="text-xs text-slate-500 mt-0.5 truncate">{item.description}</p>}
          <p className="text-[11px] text-slate-600 mt-1.5">
            {formatDistanceToNow(new Date(item.updated_at || item.created_at), { addSuffix: true })}
          </p>
        </div>
        <div className="flex flex-col items-end gap-2 flex-shrink-0">
          <span className="text-[10px] px-2 py-0.5 rounded-full font-medium capitalize whitespace-nowrap"
            style={{ background: `${color}15`, color, border: `1px solid ${color}30` }}>
            {item.status?.replace('_', ' ')}
          </span>
          <ArrowRight size={13} className="text-slate-600 group-hover:text-primary transition-colors" />
        </div>
      </div>
    </motion.div>
  )
}

// ── Pending review alert banner ───────────────────────────────────────────────
const PendingBanner = ({ count, onClick }) => (
  <motion.div
    initial={{ opacity: 0, y: -8 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.1 }}
    onClick={onClick}
    className="rounded-2xl p-4 cursor-pointer flex items-center gap-4 transition-all duration-200 hover:scale-[1.01]"
    style={{ background: 'rgba(124,58,237,0.08)', border: '1px solid rgba(124,58,237,0.3)' }}
  >
    <div className="w-10 h-10 rounded-xl flex items-center justify-center flex-shrink-0"
      style={{ background: 'rgba(124,58,237,0.15)', border: '1px solid rgba(124,58,237,0.3)' }}>
      <Clock size={18} className="text-violet-400" />
    </div>
    <div className="flex-1">
      <p className="text-sm font-semibold text-slate-200">
        {count} item{count !== 1 ? 's' : ''} pending your review
      </p>
      <p className="text-xs text-slate-500 mt-0.5">Click to view and approve pending notebooks & dashboards</p>
    </div>
    <ChevronRight size={16} className="text-violet-400 flex-shrink-0" />
  </motion.div>
)

// ── Main page ─────────────────────────────────────────────────────────────────
export default function HomePage() {
  const { notebooks, fetchNotebooks, createNotebook } = useNotebookStore()
  const { user, isCreator, isSuperuser }              = useAuthStore()
  const [dashboards,   setDashboards]   = useState([])
  const [pendingDash,  setPendingDash]  = useState(0)
  const [dashLoading,  setDashLoading]  = useState(true)
  const navigate = useNavigate()

  useEffect(() => {
    fetchNotebooks()
    dashboardsApi.list()
      .then(r => setDashboards(r.data))
      .catch(() => {})
      .finally(() => setDashLoading(false))

    // For superusers, also fetch pending dashboard count
    if (isSuperuser()) {
      dashboardsApi.pending()
        .then(r => setPendingDash(r.data.length))
        .catch(() => {})
    }
  }, [isSuperuser])

  const handleNewNotebook = async () => {
    const nb = await createNotebook()
    if (nb) navigate(`/editor/${nb.id}`)
  }

  const publishedNbs   = notebooks.filter(n => n.status === 'published').length
  const pendingNbs     = notebooks.filter(n => n.status === 'pending_approval').length
  const draftNbs       = notebooks.filter(n => n.status === 'draft').length
  const publishedDash  = dashboards.filter(d => d.status === 'published').length
  const pendingDashLocal = dashboards.filter(d => d.status === 'pending_approval').length

  // For superusers use the dedicated pending endpoint count; others use local list
  const totalPending = isSuperuser()
    ? pendingNbs + pendingDash
    : pendingNbs + pendingDashLocal

  // Sub-text and alert logic per card
  const notebookSub    = draftNbs > 0 ? `${draftNbs} draft${draftNbs !== 1 ? 's' : ''}` : 'No drafts'
  const dashboardSub   = publishedDash > 0 ? `${publishedDash} live` : 'None published yet'
  const reportsSub     = totalPending > 0
    ? `${totalPending} pending review`
    : `${publishedNbs} published`
  const reportsAlert   = totalPending > 0

  return (
    <div className="p-6 space-y-6 animate-fade-in">

      {/* Welcome banner */}
      <motion.div
        initial={{ opacity: 0, y: -10 }} animate={{ opacity: 1, y: 0 }}
        className="rounded-2xl p-6 relative overflow-hidden"
        style={{ background: 'linear-gradient(135deg, rgba(0,212,255,0.08) 0%, rgba(124,58,237,0.08) 100%)', border: '1px solid rgba(0,212,255,0.15)' }}
      >
        <div className="absolute inset-0 opacity-[0.03]" style={{
          backgroundImage: 'repeating-linear-gradient(45deg, rgba(0,212,255,0.5) 0, rgba(0,212,255,0.5) 1px, transparent 0, transparent 50%)',
          backgroundSize: '20px 20px',
        }} />
        <div className="relative flex items-center justify-between gap-6">
          <div>
            <h1 className="text-2xl font-bold text-slate-100 mb-1">
              Good {new Date().getHours() < 12 ? 'morning' : new Date().getHours() < 17 ? 'afternoon' : 'evening'},{' '}
              <span className="text-gradient-cyan">{user?.username}</span> 👋
            </h1>
            <p className="text-slate-400 text-sm">Here's what's happening in your workspace today.</p>
          </div>
          {isCreator() && (
            <button onClick={handleNewNotebook} className="btn-primary flex-shrink-0 py-2.5 px-5 gap-2">
              <Plus size={15} /> New Notebook
            </button>
          )}
        </div>
      </motion.div>

      {/* Superuser pending-review alert */}
      {isSuperuser() && totalPending > 0 && (
        <PendingBanner count={totalPending} onClick={() => navigate('/reports')} />
      )}

      {/* Stats grid — all cards are clickable */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard
          icon={BookOpen}   label="Total Notebooks"   value={notebooks.length}
          sub={notebookSub} color="#00D4FF" delay={0.05}
          onClick={() => navigate('/editor')}
        />
        <StatCard
          icon={BarChart3}  label="Dashboards"        value={dashboards.length}
          sub={dashboardSub} color="#7C3AED" delay={0.1}
          onClick={() => navigate('/dashboards')}
        />
        <StatCard
          icon={Activity}   label="Published Reports" value={publishedNbs}
          sub={reportsSub}  subAlert={reportsAlert}   color={reportsAlert ? '#A78BFA' : '#06FFA5'} delay={0.15}
          onClick={() => navigate('/reports')}
        />
        <StatCard
          icon={Shield}     label="Your Role"         value={user?.role}
          sub="View settings & profile" color="#FFB800" delay={0.2}
          onClick={() => navigate('/settings')}
        />
      </div>

      {/* Recent content */}
      <div className="grid lg:grid-cols-2 gap-6">

        {/* Recent notebooks */}
        <motion.div initial={{ opacity: 0, x: -20 }} animate={{ opacity: 1, x: 0 }} transition={{ delay: 0.3 }} className="space-y-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <BookOpen size={16} className="text-primary" />
              <h2 className="text-sm font-semibold text-slate-200">Recent Notebooks</h2>
              {pendingNbs > 0 && isSuperuser() && (
                <span className="badge-violet text-[10px] py-0 px-1.5">{pendingNbs} pending</span>
              )}
            </div>
            <button onClick={() => navigate('/editor')}
              className="text-xs text-slate-500 hover:text-primary flex items-center gap-1 transition-colors">
              View all <ArrowRight size={12} />
            </button>
          </div>

          <div className="space-y-2">
            {notebooks.slice(0, 5).map(nb => (
              <RecentCard key={nb.id} item={nb} onClick={() => navigate(`/editor/${nb.id}`)} />
            ))}
            {notebooks.length === 0 && (
              <div className="glass rounded-xl p-8 text-center">
                <BookOpen size={32} className="text-slate-700 mx-auto mb-3" />
                <p className="text-slate-500 text-sm mb-3">No notebooks yet</p>
                {isCreator() && (
                  <button onClick={handleNewNotebook} className="btn-primary text-xs py-2 px-4 gap-1.5">
                    <Plus size={12} /> Create notebook
                  </button>
                )}
              </div>
            )}
          </div>
        </motion.div>

        {/* Recent dashboards */}
        <motion.div initial={{ opacity: 0, x: 20 }} animate={{ opacity: 1, x: 0 }} transition={{ delay: 0.35 }} className="space-y-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <BarChart3 size={16} className="text-violet-400" />
              <h2 className="text-sm font-semibold text-slate-200">Recent Dashboards</h2>
              {pendingDashLocal > 0 && isSuperuser() && (
                <span className="badge-violet text-[10px] py-0 px-1.5">{pendingDashLocal} pending</span>
              )}
            </div>
            <button onClick={() => navigate('/dashboards')}
              className="text-xs text-slate-500 hover:text-violet-400 flex items-center gap-1 transition-colors">
              View all <ArrowRight size={12} />
            </button>
          </div>

          <div className="space-y-2">
            {dashboards.slice(0, 5).map(dash => (
              <RecentCard key={dash.id} item={dash} onClick={() => navigate('/dashboards')} />
            ))}
            {dashboards.length === 0 && !dashLoading && (
              <div className="glass rounded-xl p-8 text-center">
                <BarChart3 size={32} className="text-slate-700 mx-auto mb-3" />
                <p className="text-slate-500 text-sm mb-3">No dashboards yet</p>
                {isCreator() && (
                  <button onClick={() => navigate('/dashboards')} className="btn-violet text-xs py-2 px-4 gap-1.5">
                    <Plus size={12} /> Create dashboard
                  </button>
                )}
              </div>
            )}
          </div>
        </motion.div>
      </div>

      {/* Quick start tips */}
      <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.5 }}
        className="glass rounded-2xl p-5">
        <div className="flex items-center gap-2 mb-4">
          <Zap size={16} className="text-amber-400" />
          <h2 className="text-sm font-semibold text-slate-200">Quick Start</h2>
        </div>
        <div className="grid sm:grid-cols-3 gap-4">
          {[
            { step: '01', title: 'Connect & Query',    desc: 'Write SQL against the MySQL data source. Results become DataFrames automatically.', color: '#00D4FF', path: '/editor'     },
            { step: '02', title: 'Transform in Python', desc: 'Use Pandas, NumPy, or Plotly to transform data and build rich visualizations.',     color: '#7C3AED', path: '/editor'     },
            { step: '03', title: 'Publish & Share',    desc: 'Submit your notebook or dashboard for review. Superusers approve it for viewers.',   color: '#06FFA5', path: '/reports'    },
          ].map(({ step, title, desc, color, path }) => (
            <div key={step}
              onClick={() => navigate(path)}
              className="flex gap-3 cursor-pointer rounded-xl p-3 transition-all duration-200 hover:bg-white/[0.03]">
              <div className="text-2xl font-black mt-0.5 flex-shrink-0" style={{ color: `${color}40` }}>{step}</div>
              <div>
                <p className="text-sm font-semibold text-slate-300 mb-1">{title}</p>
                <p className="text-xs text-slate-500 leading-relaxed">{desc}</p>
              </div>
            </div>
          ))}
        </div>
      </motion.div>
    </div>
  )
}
