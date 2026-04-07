import React, { useState, useRef, useEffect, useCallback } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import { createPortal } from 'react-dom'
import { motion, AnimatePresence } from 'framer-motion'
import { Bell, Search, ChevronRight, LogOut, Settings, X, BookOpen, BarChart3, Database, Activity } from 'lucide-react'
import useAuthStore from '../../store/authStore'

const breadcrumbMap = {
  '/':           ['Overview'],
  '/editor':     ['Notebooks'],
  '/dashboards': ['Dashboards'],
  '/reports':    ['Reports'],
  '/data':       ['Data Sources'],
  '/settings':   ['Settings'],
  '/users':      ['Admin', 'Users'],
}

const roleBadgeClass = {
  superuser: 'badge-violet',
  creator:   'badge-cyan',
  viewer:    'badge-mint',
}

const NAV_SEARCH = [
  { label: 'Overview',     path: '/',           icon: BarChart3 },
  { label: 'Notebooks',    path: '/editor',     icon: BookOpen  },
  { label: 'Dashboards',   path: '/dashboards', icon: BarChart3 },
  { label: 'Reports',      path: '/reports',    icon: Activity  },
  { label: 'Data Sources', path: '/data',       icon: Database  },
  { label: 'Settings',     path: '/settings',   icon: Settings  },
]

/* ─── Search modal ─────────────────────────────────────────────────────────── */
function SearchModal({ onClose }) {
  const [query, setQuery] = useState('')
  const navigate          = useNavigate()
  const inputRef          = useRef(null)

  useEffect(() => { inputRef.current?.focus() }, [])
  useEffect(() => {
    const h = (e) => { if (e.key === 'Escape') onClose() }
    window.addEventListener('keydown', h)
    return () => window.removeEventListener('keydown', h)
  }, [onClose])

  const results = query.trim()
    ? NAV_SEARCH.filter(r => r.label.toLowerCase().includes(query.toLowerCase()))
    : NAV_SEARCH

  const go = (path) => { navigate(path); onClose() }

  return createPortal(
    <motion.div
      initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
      className="fixed inset-0 flex items-start justify-center pt-24 px-4"
      style={{ zIndex: 9999, background: 'rgba(3,3,16,0.75)', backdropFilter: 'blur(8px)' }}
      onClick={onClose}
    >
      <motion.div
        initial={{ y: -20, opacity: 0, scale: 0.97 }}
        animate={{ y: 0, opacity: 1, scale: 1 }}
        exit={{ y: -20, opacity: 0, scale: 0.97 }}
        transition={{ duration: 0.18 }}
        className="w-full max-w-lg rounded-2xl overflow-hidden"
        style={{ background: 'rgba(10,10,37,0.98)', border: '1px solid rgba(0,212,255,0.2)', boxShadow: '0 24px 64px rgba(0,0,0,0.6), 0 0 40px rgba(0,212,255,0.08)' }}
        onClick={e => e.stopPropagation()}
      >
        <div className="flex items-center gap-3 px-4 py-3.5" style={{ borderBottom: '1px solid rgba(255,255,255,0.07)' }}>
          <Search size={16} className="text-primary flex-shrink-0" />
          <input
            ref={inputRef}
            value={query}
            onChange={e => setQuery(e.target.value)}
            placeholder="Search pages, notebooks, dashboards..."
            className="flex-1 bg-transparent outline-none text-slate-200 text-sm placeholder-slate-500"
          />
          <button onClick={onClose} className="text-slate-600 hover:text-slate-400 transition-colors">
            <X size={15} />
          </button>
        </div>

        <div className="py-2 max-h-72 overflow-y-auto">
          {results.length === 0 ? (
            <p className="text-slate-600 text-sm text-center py-6">No results</p>
          ) : results.map(({ label, path, icon: Icon }) => (
            <button key={path} onClick={() => go(path)}
              className="w-full flex items-center gap-3 px-4 py-2.5 text-slate-400 hover:text-slate-200 hover:bg-white/5 transition-all duration-150 text-sm text-left">
              <div className="w-7 h-7 rounded-lg flex items-center justify-center flex-shrink-0"
                style={{ background: 'rgba(0,212,255,0.1)' }}>
                <Icon size={13} className="text-primary" />
              </div>
              {label}
            </button>
          ))}
        </div>

        <div className="px-4 py-2.5 border-t border-white/5 flex items-center gap-4 text-[11px] text-slate-600">
          <span><kbd className="px-1.5 py-0.5 rounded text-[10px]" style={{ background: 'rgba(255,255,255,0.07)' }}>↵</kbd> Select</span>
          <span><kbd className="px-1.5 py-0.5 rounded text-[10px]" style={{ background: 'rgba(255,255,255,0.07)' }}>Esc</kbd> Close</span>
        </div>
      </motion.div>
    </motion.div>,
    document.body
  )
}

/* ─── Fixed-position dropdown wrapper ─────────────────────────────────────── */
function FixedDropdown({ anchorRef, onClose, children }) {
  const [pos, setPos] = useState(null)

  useEffect(() => {
    const calculate = () => {
      if (anchorRef.current) {
        const rect = anchorRef.current.getBoundingClientRect()
        setPos({ top: rect.bottom + 8, right: window.innerWidth - rect.right })
      }
    }
    calculate()
    window.addEventListener('resize', calculate)
    window.addEventListener('scroll', calculate, true)
    return () => {
      window.removeEventListener('resize', calculate)
      window.removeEventListener('scroll', calculate, true)
    }
  }, [anchorRef])

  useEffect(() => {
    const handler = (e) => {
      if (anchorRef.current && !anchorRef.current.contains(e.target)) onClose()
    }
    // slight delay so the button click that opened this doesn't immediately close it
    const t = setTimeout(() => document.addEventListener('mousedown', handler), 50)
    return () => { clearTimeout(t); document.removeEventListener('mousedown', handler) }
  }, [anchorRef, onClose])

  if (!pos) return null

  return createPortal(
    <div style={{ position: 'fixed', top: pos.top, right: pos.right, zIndex: 9999 }}>
      {children}
    </div>,
    document.body
  )
}

/* ─── Notifications panel ──────────────────────────────────────────────────── */
function NotificationsPanel({ anchorRef, onClose }) {
  const notifications = [
    { id: 1, type: 'info',    title: 'System ready',      body: 'Connected to Data_Science database',  time: 'Just now', read: false },
    { id: 2, type: 'success', title: 'Welcome to Otenga', body: 'Your workspace is set up and ready.', time: '2m ago',   read: false },
    { id: 3, type: 'warn',    title: 'Approval pending',  body: 'A notebook is awaiting your review.', time: '10m ago',  read: true  },
  ]
  const colors = { info: '#00D4FF', success: '#06FFA5', warn: '#FFB800', error: '#FF4D6D' }

  return (
    <FixedDropdown anchorRef={anchorRef} onClose={onClose}>
      <motion.div
        initial={{ opacity: 0, y: -8, scale: 0.97 }}
        animate={{ opacity: 1, y: 0, scale: 1 }}
        exit={{ opacity: 0, y: -8, scale: 0.97 }}
        transition={{ duration: 0.16 }}
        className="w-80 rounded-2xl overflow-hidden"
        style={{ background: 'rgba(10,10,37,0.98)', border: '1px solid rgba(255,255,255,0.1)', boxShadow: '0 20px 60px rgba(0,0,0,0.6), 0 0 30px rgba(0,212,255,0.08)' }}
      >
        <div className="flex items-center justify-between px-4 py-3.5" style={{ borderBottom: '1px solid rgba(255,255,255,0.07)' }}>
          <div className="flex items-center gap-2">
            <Bell size={14} className="text-primary" />
            <span className="text-sm font-semibold text-slate-200">Notifications</span>
            <span className="badge-rose text-[10px] py-0 px-1.5">{notifications.filter(n => !n.read).length}</span>
          </div>
          <button onClick={onClose} className="text-slate-600 hover:text-slate-400 transition-colors">
            <X size={14} />
          </button>
        </div>

        <div className="divide-y divide-white/[0.04]">
          {notifications.map(n => (
            <div key={n.id} className={`flex gap-3 px-4 py-3 transition-colors hover:bg-white/[0.03] ${!n.read ? 'bg-white/[0.02]' : ''}`}>
              <div className="w-2 h-2 rounded-full mt-1.5 flex-shrink-0"
                style={{ background: colors[n.type] || colors.info, boxShadow: `0 0 6px ${colors[n.type]}60` }} />
              <div className="flex-1 min-w-0">
                <p className="text-xs font-semibold text-slate-200">{n.title}</p>
                <p className="text-[11px] text-slate-500 mt-0.5">{n.body}</p>
                <p className="text-[10px] text-slate-700 mt-1">{n.time}</p>
              </div>
            </div>
          ))}
        </div>

        <div className="px-4 py-3 border-t border-white/5">
          <button className="text-xs text-primary hover:text-primary/80 transition-colors">Mark all as read</button>
        </div>
      </motion.div>
    </FixedDropdown>
  )
}

/* ─── Profile menu ──────────────────────────────────────────────────────────── */
function ProfileMenu({ anchorRef, onClose }) {
  const { user, logout } = useAuthStore()
  const navigate         = useNavigate()

  const doLogout   = () => { logout(); navigate('/login'); onClose() }
  const goSettings = () => { navigate('/settings'); onClose() }

  return (
    <FixedDropdown anchorRef={anchorRef} onClose={onClose}>
      <motion.div
        initial={{ opacity: 0, y: -8, scale: 0.97 }}
        animate={{ opacity: 1, y: 0, scale: 1 }}
        exit={{ opacity: 0, y: -8, scale: 0.97 }}
        transition={{ duration: 0.16 }}
        className="w-56 rounded-2xl overflow-hidden"
        style={{ background: 'rgba(10,10,37,0.98)', border: '1px solid rgba(255,255,255,0.1)', boxShadow: '0 20px 60px rgba(0,0,0,0.6)' }}
      >
        <div className="px-4 py-3.5" style={{ borderBottom: '1px solid rgba(255,255,255,0.07)' }}>
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-xl flex items-center justify-center text-sm font-bold text-space-950 flex-shrink-0"
              style={{ background: user?.avatar_color || '#00D4FF' }}>
              {user?.username?.[0]?.toUpperCase()}
            </div>
            <div className="min-w-0">
              <p className="text-sm font-semibold text-slate-200 truncate">{user?.username}</p>
              <p className="text-[11px] text-slate-500 truncate">{user?.email}</p>
            </div>
          </div>
          <span className={`${roleBadgeClass[user?.role] || 'badge-cyan'} capitalize mt-2 inline-block`}>{user?.role}</span>
        </div>

        <div className="py-1.5">
          <button onClick={goSettings}
            className="w-full flex items-center gap-3 px-4 py-2.5 text-slate-400 hover:text-slate-200 hover:bg-white/5 transition-all duration-150 text-sm">
            <Settings size={14} /> Settings
          </button>
          <button onClick={doLogout}
            className="w-full flex items-center gap-3 px-4 py-2.5 text-rose-400 hover:text-rose-300 hover:bg-rose-500/10 transition-all duration-150 text-sm">
            <LogOut size={14} /> Sign out
          </button>
        </div>
      </motion.div>
    </FixedDropdown>
  )
}

/* ─── TopBar ────────────────────────────────────────────────────────────────── */
export default function TopBar({ title, actions }) {
  const location                      = useLocation()
  const { user }                      = useAuthStore()
  const [showSearch,  setShowSearch]  = useState(false)
  const [showNotifs,  setShowNotifs]  = useState(false)
  const [showProfile, setShowProfile] = useState(false)

  const notifsRef  = useRef(null)
  const profileRef = useRef(null)

  const crumbs = breadcrumbMap[location.pathname] || ['Page']

  // Cmd+K shortcut
  useEffect(() => {
    const h = (e) => {
      if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
        e.preventDefault()
        setShowSearch(true)
        setShowNotifs(false)
        setShowProfile(false)
      }
    }
    window.addEventListener('keydown', h)
    return () => window.removeEventListener('keydown', h)
  }, [])

  const closeNotifs  = useCallback(() => setShowNotifs(false),  [])
  const closeProfile = useCallback(() => setShowProfile(false), [])

  return (
    <>
      <header
        className="h-14 flex items-center justify-between px-6 border-b border-white/5 flex-shrink-0"
        style={{ background: 'rgba(5,5,21,0.8)', backdropFilter: 'blur(12px)', position: 'relative', zIndex: 40 }}
      >
        {/* Breadcrumbs */}
        <div className="flex items-center gap-2 text-sm">
          <span className="text-slate-500 text-xs font-medium">Otenga</span>
          <ChevronRight size={12} className="text-slate-600" />
          {crumbs.map((crumb, i) => (
            <React.Fragment key={crumb}>
              {i > 0 && <ChevronRight size={12} className="text-slate-600" />}
              <span className={i === crumbs.length - 1 ? 'text-slate-200 font-semibold text-sm' : 'text-slate-500 text-xs'}>
                {title && i === crumbs.length - 1 ? title : crumb}
              </span>
            </React.Fragment>
          ))}
        </div>

        {/* Right-side controls */}
        <div className="flex items-center gap-2.5">
          {actions}

          {/* Search */}
          <button
            onClick={() => { setShowSearch(true); setShowNotifs(false); setShowProfile(false) }}
            className="flex items-center gap-2 px-3 py-1.5 rounded-lg text-slate-500 text-xs transition-all duration-200 hover:text-slate-200 hover:border-primary/40"
            style={{ background: 'rgba(255,255,255,0.04)', border: '1px solid rgba(255,255,255,0.07)' }}
          >
            <Search size={13} />
            <span className="hidden sm:inline">Search...</span>
            <kbd className="hidden sm:inline text-[10px] px-1.5 py-0.5 rounded text-slate-700" style={{ background: 'rgba(255,255,255,0.06)' }}>⌘K</kbd>
          </button>

          {/* Notifications button */}
          <button
            ref={notifsRef}
            onClick={() => { setShowNotifs(v => !v); setShowProfile(false) }}
            className={`relative p-2 rounded-lg transition-all duration-200 ${showNotifs ? 'text-primary bg-primary/10' : 'text-slate-500 hover:text-slate-200'}`}
            style={{ border: `1px solid ${showNotifs ? 'rgba(0,212,255,0.3)' : 'rgba(255,255,255,0.07)'}`, background: showNotifs ? 'rgba(0,212,255,0.08)' : 'rgba(255,255,255,0.04)' }}
          >
            <Bell size={15} />
            <span className="absolute top-1 right-1 w-1.5 h-1.5 rounded-full bg-rose-500 border border-space-950" />
          </button>

          {/* Role badge */}
          <span className={`${roleBadgeClass[user?.role] || 'badge-cyan'} capitalize hidden sm:inline-flex`}>
            {user?.role}
          </span>

          {/* Avatar button */}
          <button
            ref={profileRef}
            onClick={() => { setShowProfile(v => !v); setShowNotifs(false) }}
            className={`w-8 h-8 rounded-lg flex items-center justify-center text-xs font-bold text-space-950 transition-all duration-200 ring-2 ${showProfile ? 'ring-primary/60' : 'ring-transparent hover:ring-white/20'}`}
            style={{ background: user?.avatar_color || '#00D4FF' }}
          >
            {user?.username?.[0]?.toUpperCase() || 'U'}
          </button>
        </div>
      </header>

      {/* Portalled dropdowns – rendered outside the backdrop-filter stacking context */}
      <AnimatePresence>
        {showNotifs  && <NotificationsPanel anchorRef={notifsRef}  onClose={closeNotifs}  />}
        {showProfile && <ProfileMenu        anchorRef={profileRef} onClose={closeProfile} />}
        {showSearch  && <SearchModal onClose={() => setShowSearch(false)} />}
      </AnimatePresence>
    </>
  )
}
