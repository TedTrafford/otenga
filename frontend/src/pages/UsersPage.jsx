import React, { useEffect, useState, useCallback } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { Users, UserCheck, Activity, Clock, Trash2, RefreshCw } from 'lucide-react'
import { usersApi } from '../api/client'
import toast from 'react-hot-toast'
import { formatDistanceToNow } from 'date-fns'

const roleColors = {
  superuser: { text: '#A78BFA', bg: 'rgba(124,58,237,0.12)', border: 'rgba(124,58,237,0.25)' },
  creator:   { text: '#00D4FF', bg: 'rgba(0,212,255,0.10)',  border: 'rgba(0,212,255,0.22)' },
  viewer:    { text: '#06FFA5', bg: 'rgba(6,255,165,0.10)',  border: 'rgba(6,255,165,0.20)' },
}

const statusBadge = (status) => {
  if (status === 'active')   return <span className="badge-mint">Active</span>
  if (status === 'disabled') return <span className="badge-rose">Disabled</span>
  return null
}

export default function UsersPage() {
  const [users,   setUsers]   = useState([])
  const [logs,    setLogs]    = useState([])
  const [loading, setLoading] = useState(true)
  const [tab,     setTab]     = useState('users') // 'users' | 'audit'

  const load = useCallback(() => {
    setLoading(true)
    Promise.all([usersApi.list(), usersApi.auditLogs()])
      .then(([u, l]) => {
        setUsers(u.data)
        setLogs(l.data)
      })
      .catch(() => toast.error('Failed to load user data'))
      .finally(() => setLoading(false))
  }, [])

  useEffect(() => { load() }, [load])

  const changeRole = async (id, role) => {
    try {
      await usersApi.update(id, { role })
      setUsers(u => u.map(x => x.id === id ? { ...x, role } : x))
      toast.success('Role updated')
    } catch { toast.error('Failed to update role') }
  }

  const disableUser = async (id) => {
    try {
      const { data } = await usersApi.disable(id)
      setUsers(u => u.map(x => x.id === id ? data : x))
      toast.success('User disabled')
    } catch { toast.error('Failed to disable user') }
  }

  const enableUser = async (id) => {
    try {
      const { data } = await usersApi.enable(id)
      setUsers(u => u.map(x => x.id === id ? data : x))
      toast.success('User re-enabled')
    } catch { toast.error('Failed to enable user') }
  }

  const deleteUser = async (id, username) => {
    if (!window.confirm(`Permanently delete "${username}"? This cannot be undone.`)) return
    try {
      await usersApi.delete(id)
      setUsers(u => u.filter(x => x.id !== id))
      toast.success('User deleted')
    } catch { toast.error('Failed to delete user') }
  }

  const activeUsers   = users.filter(u => u.status === 'active')
  const disabledUsers = users.filter(u => u.status === 'disabled')

  const TABS = [
    { key: 'users', label: 'Members',  count: users.length },
    { key: 'audit', label: 'Audit Log', count: null        },
  ]

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-lg font-bold text-slate-100">User Management</h1>
          <p className="text-xs text-slate-500 mt-0.5">Manage workspace members and review activity</p>
        </div>
        <button onClick={load} className="btn-ghost p-2" title="Refresh">
          <RefreshCw size={15} className={loading ? 'animate-spin' : ''} />
        </button>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-3 gap-4">
        {[
          { label: 'Total Members', value: users.length,        color: '#00D4FF', icon: Users     },
          { label: 'Active',        value: activeUsers.length,  color: '#06FFA5', icon: UserCheck  },
          { label: 'Disabled',      value: disabledUsers.length, color: '#FF4D6D', icon: Users    },
        ].map(({ label, value, color, icon: Icon }) => (
          <div key={label} className="glass rounded-xl p-4 flex items-center gap-4">
            <div className="w-10 h-10 rounded-xl flex items-center justify-center"
              style={{ background: `${color}12`, border: `1px solid ${color}25` }}>
              <Icon size={18} style={{ color }} />
            </div>
            <div>
              <p className="text-xl font-bold" style={{ color }}>{value}</p>
              <p className="text-xs text-slate-500">{label}</p>
            </div>
          </div>
        ))}
      </div>

      {/* Tab bar */}
      <div className="flex gap-1 p-1 rounded-xl w-fit" style={{ background: 'rgba(255,255,255,0.04)', border: '1px solid rgba(255,255,255,0.07)' }}>
        {TABS.map(({ key, label, count }) => (
          <button key={key} onClick={() => setTab(key)}
            className={`flex items-center gap-2 px-4 py-2 rounded-lg text-xs font-medium transition-all duration-200 ${tab === key ? 'bg-primary/20 text-primary border border-primary/30' : 'text-slate-500 hover:text-slate-300'}`}>
            {label}
            {count != null && (
              <span className="text-[10px] px-1.5 py-0.5 rounded-full font-semibold"
                style={{ background: tab === key ? 'rgba(0,212,255,0.2)' : 'rgba(255,255,255,0.07)', color: tab === key ? '#00D4FF' : '#64748b' }}>
                {count}
              </span>
            )}
          </button>
        ))}
      </div>

      <AnimatePresence mode="wait">

        {/* ── All Members ── */}
        {tab === 'users' && (
          <motion.div key="users" initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -8 }} transition={{ duration: 0.2 }}>
            <div className="glass rounded-2xl overflow-hidden">
              <table className="w-full text-sm">
                <thead>
                  <tr style={{ borderBottom: '1px solid rgba(255,255,255,0.07)' }}>
                    {['User', 'Email', 'Role', 'Status', 'Joined', 'Actions'].map(h => (
                      <th key={h} className="text-left px-5 py-3.5 text-xs font-semibold text-slate-500 uppercase tracking-wider"
                        style={{ background: 'rgba(255,255,255,0.03)' }}>{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {users.map((user, i) => {
                    const rc = roleColors[user.role] || roleColors.viewer
                    return (
                      <motion.tr key={user.id} initial={{ opacity: 0, x: -10 }} animate={{ opacity: 1, x: 0 }} transition={{ delay: i * 0.03 }}
                        className="border-b border-white/5 hover:bg-white/[0.02] transition-colors">
                        <td className="px-5 py-3.5">
                          <div className="flex items-center gap-3">
                            <div className="w-8 h-8 rounded-lg flex items-center justify-center text-xs font-bold text-space-950 flex-shrink-0"
                              style={{ background: user.avatar_color || '#00D4FF' }}>
                              {user.username[0].toUpperCase()}
                            </div>
                            <div>
                              <p className="font-medium text-slate-200">{user.username}</p>
                              {user.full_name && <p className="text-[11px] text-slate-500">{user.full_name}</p>}
                            </div>
                          </div>
                        </td>
                        <td className="px-5 py-3.5 text-slate-400 text-xs">{user.email}</td>
                        <td className="px-5 py-3.5">
                          <select value={user.role} onChange={(e) => changeRole(user.id, e.target.value)}
                            className="text-xs px-2.5 py-1 rounded-lg cursor-pointer outline-none capitalize"
                            style={{ background: rc.bg, color: rc.text, border: `1px solid ${rc.border}` }}>
                            <option value="viewer">viewer</option>
                            <option value="creator">creator</option>
                            <option value="superuser">superuser</option>
                          </select>
                        </td>
                        <td className="px-5 py-3.5">{statusBadge(user.status)}</td>
                        <td className="px-5 py-3.5 text-xs text-slate-500">
                          {formatDistanceToNow(new Date(user.created_at), { addSuffix: true })}
                        </td>
                        <td className="px-5 py-3.5">
                          <div className="flex items-center gap-1.5">
                            {user.status === 'active' ? (
                              <button onClick={() => disableUser(user.id)}
                                className="text-xs px-2.5 py-1.5 rounded-lg text-amber-400 hover:bg-amber-500/10 transition-all duration-200"
                                style={{ border: '1px solid rgba(251,191,36,0.25)' }}>
                                Disable
                              </button>
                            ) : user.status === 'disabled' ? (
                              <button onClick={() => enableUser(user.id)}
                                className="text-xs px-2.5 py-1.5 rounded-lg text-mint-400 hover:bg-mint-500/10 transition-all duration-200"
                                style={{ border: '1px solid rgba(6,255,165,0.25)' }}>
                                Enable
                              </button>
                            ) : null}
                            <button onClick={() => deleteUser(user.id, user.username)}
                              className="p-1.5 rounded-lg text-slate-600 hover:text-rose-400 hover:bg-rose-500/10 transition-all duration-200"
                              title="Delete user">
                              <Trash2 size={13} />
                            </button>
                          </div>
                        </td>
                      </motion.tr>
                    )
                  })}
                  {users.length === 0 && (
                    <tr>
                      <td colSpan={6} className="text-center py-12 text-slate-600 text-sm">No members yet</td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </motion.div>
        )}

        {/* ── Audit Log ── */}
        {tab === 'audit' && (
          <motion.div key="audit" initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -8 }} transition={{ duration: 0.2 }}>
            <div className="glass rounded-2xl overflow-hidden">
              <div className="px-5 py-3.5 border-b border-white/7" style={{ background: 'rgba(255,255,255,0.03)' }}>
                <div className="flex items-center gap-2">
                  <Activity size={14} className="text-primary" />
                  <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Audit Log</span>
                  <span className="badge-cyan ml-auto">{logs.length} entries</span>
                </div>
              </div>
              <div className="max-h-[600px] overflow-y-auto">
                {logs.map((log, i) => (
                  <motion.div key={log.id} initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: i * 0.02 }}
                    className="flex items-start gap-4 px-5 py-3.5 border-b border-white/[0.04] hover:bg-white/[0.02] transition-colors">
                    <div className="w-7 h-7 rounded-lg flex items-center justify-center flex-shrink-0 text-[10px] font-bold text-space-950"
                      style={{ background: log.user?.avatar_color || '#00D4FF', marginTop: '2px' }}>
                      {log.user?.username?.[0]?.toUpperCase() || '?'}
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 flex-wrap">
                        <span className="text-xs font-semibold text-slate-300">{log.user?.username || `#${log.user_id}`}</span>
                        <span className="text-xs text-slate-500">{log.action.replace(/_/g, ' ')}</span>
                        {log.resource_type && <span className="badge-cyan text-[10px] py-0">{log.resource_type} #{log.resource_id}</span>}
                      </div>
                      <p className="text-[11px] text-slate-600 mt-0.5 flex items-center gap-1">
                        <Clock size={9} />
                        {formatDistanceToNow(new Date(log.created_at), { addSuffix: true })}
                      </p>
                    </div>
                  </motion.div>
                ))}
                {logs.length === 0 && (
                  <div className="text-center py-12">
                    <Activity size={28} className="text-slate-700 mx-auto mb-2" />
                    <p className="text-slate-600 text-sm">No audit logs yet</p>
                  </div>
                )}
              </div>
            </div>
          </motion.div>
        )}

      </AnimatePresence>
    </div>
  )
}
