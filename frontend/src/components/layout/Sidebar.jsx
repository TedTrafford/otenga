import React, { useState } from 'react'
import { NavLink, useNavigate } from 'react-router-dom'
import { motion, AnimatePresence } from 'framer-motion'
import {
  LayoutDashboard, BookOpen, BarChart3, Settings, LogOut,
  ChevronLeft, ChevronRight, Database, Users, Activity,
  Sparkles, Bell, Search, Zap,
} from 'lucide-react'
import useAuthStore from '../../store/authStore'

const Logo = ({ collapsed }) => (
  <div className="flex items-center gap-3 px-4 py-5 border-b border-white/5">
    <div className="relative flex-shrink-0">
      <div className="w-9 h-9 rounded-xl flex items-center justify-center"
        style={{ background: 'linear-gradient(135deg, #00D4FF 0%, #7C3AED 100%)' }}>
        <Zap size={18} className="text-white" />
      </div>
      <div className="absolute -top-1 -right-1 w-2.5 h-2.5 rounded-full bg-mint-500 border-2 border-space-950 animate-pulse" />
    </div>
    <AnimatePresence>
      {!collapsed && (
        <motion.div initial={{ opacity: 0, x: -10 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0, x: -10 }} transition={{ duration: 0.2 }}>
          <span className="text-lg font-bold text-gradient-brand">Otenga</span>
          <p className="text-[10px] text-slate-500 -mt-0.5 font-medium tracking-widest uppercase">BI Platform</p>
        </motion.div>
      )}
    </AnimatePresence>
  </div>
)

const NavItem = ({ to, icon: Icon, label, collapsed, badge }) => (
  <NavLink to={to} className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}>
    <Icon size={17} className="flex-shrink-0" />
    <AnimatePresence>
      {!collapsed && (
        <motion.span initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} className="flex-1 text-sm">
          {label}
        </motion.span>
      )}
    </AnimatePresence>
    {badge && !collapsed && (
      <span className="badge-cyan text-[10px] py-0 px-1.5">{badge}</span>
    )}
  </NavLink>
)

export default function Sidebar() {
  const [collapsed, setCollapsed] = useState(false)
  const { user, logout, isSuperuser, isCreator } = useAuthStore()
  const navigate = useNavigate()

  const navItems = [
    { to: '/',           icon: LayoutDashboard, label: 'Overview'      },
    { to: '/editor',     icon: BookOpen,        label: 'Notebooks'     },
    { to: '/dashboards', icon: BarChart3,        label: 'Dashboards'    },
    { to: '/reports',    icon: Activity,         label: 'Reports'       },
    { to: '/data',       icon: Database,         label: 'Data Sources'  },
  ]

  // Settings is visible to superusers and creators; User Management only to superusers
  const canSeeSettings = isSuperuser() || isCreator()

  return (
    <motion.aside
      animate={{ width: collapsed ? 64 : 240 }}
      transition={{ duration: 0.25, ease: 'easeInOut' }}
      className="relative flex flex-col h-screen border-r border-white/5 flex-shrink-0 z-30"
      style={{ background: 'rgba(5,5,21,0.9)', backdropFilter: 'blur(20px)' }}
    >
      {/* Collapse toggle */}
      <button
        onClick={() => setCollapsed(!collapsed)}
        className="absolute -right-3 top-20 z-40 w-6 h-6 rounded-full flex items-center justify-center transition-all duration-200"
        style={{ background: 'rgba(0,212,255,0.2)', border: '1px solid rgba(0,212,255,0.3)' }}
      >
        {collapsed ? <ChevronRight size={12} className="text-primary" /> : <ChevronLeft size={12} className="text-primary" />}
      </button>

      <Logo collapsed={collapsed} />

      {/* Main nav */}
      <nav className="flex-1 overflow-y-auto px-2 py-4 space-y-0.5">
        {!collapsed && (
          <p className="text-[10px] font-semibold text-slate-600 uppercase tracking-wider px-3 mb-2">Main</p>
        )}
        {navItems.map((item) => (
          <NavItem key={item.to} {...item} collapsed={collapsed} />
        ))}

        {canSeeSettings && (
          <>
            {!collapsed && (
              <p className="text-[10px] font-semibold text-slate-600 uppercase tracking-wider px-3 mt-5 mb-2">Admin</p>
            )}
            <NavItem to="/settings" icon={Settings} label="Settings" collapsed={collapsed} />
            {isSuperuser() && (
              <NavItem to="/users" icon={Users} label="User Management" collapsed={collapsed} />
            )}
          </>
        )}
      </nav>

      {/* User section */}
      <div className="px-2 pb-4 border-t border-white/5 pt-3">
        <div className={`flex items-center gap-3 px-3 py-2.5 rounded-lg ${collapsed ? 'justify-center' : ''}`}>
          <div
            className="w-8 h-8 rounded-lg flex-shrink-0 flex items-center justify-center text-xs font-bold text-space-950"
            style={{ background: user?.avatar_color || '#00D4FF' }}
          >
            {user?.username?.[0]?.toUpperCase() || 'U'}
          </div>
          <AnimatePresence>
            {!collapsed && (
              <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} className="flex-1 min-w-0">
                <p className="text-sm font-medium text-slate-200 truncate">{user?.username}</p>
                <p className="text-[11px] text-slate-500 capitalize">{user?.role}</p>
              </motion.div>
            )}
          </AnimatePresence>
          {!collapsed && (
            <button
              onClick={() => { logout(); navigate('/login') }}
              className="p-1.5 rounded-lg text-slate-500 hover:text-rose-400 hover:bg-rose-500/10 transition-all duration-200"
              title="Logout"
            >
              <LogOut size={14} />
            </button>
          )}
        </div>
      </div>
    </motion.aside>
  )
}
