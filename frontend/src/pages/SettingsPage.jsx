import React from 'react'
import { motion } from 'framer-motion'
import { Settings, Database, Shield, Bell, Palette, User, Key } from 'lucide-react'
import useAuthStore from '../store/authStore'

const Section = ({ icon: Icon, title, children }) => (
  <div className="glass rounded-2xl p-6">
    <div className="flex items-center gap-3 mb-5 pb-4 border-b border-white/5">
      <div className="w-9 h-9 rounded-xl flex items-center justify-center" style={{ background: 'rgba(0,212,255,0.1)', border: '1px solid rgba(0,212,255,0.2)' }}>
        <Icon size={16} className="text-primary" />
      </div>
      <h2 className="text-sm font-bold text-slate-200">{title}</h2>
    </div>
    {children}
  </div>
)

const Row = ({ label, sub, children }) => (
  <div className="flex items-center justify-between py-3 border-b border-white/5 last:border-0">
    <div>
      <p className="text-sm text-slate-300">{label}</p>
      {sub && <p className="text-xs text-slate-600 mt-0.5">{sub}</p>}
    </div>
    <div>{children}</div>
  </div>
)

export default function SettingsPage() {
  const { user } = useAuthStore()

  return (
    <div className="p-6 max-w-3xl mx-auto space-y-6">
      <div className="mb-2">
        <h1 className="text-lg font-bold text-slate-100">Settings</h1>
        <p className="text-xs text-slate-500 mt-0.5">Manage your workspace and preferences</p>
      </div>

      <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.05 }}>
        <Section icon={User} title="Profile">
          <Row label="Username" sub="Your login identifier">
            <span className="text-sm font-mono text-primary">{user?.username}</span>
          </Row>
          <Row label="Email" sub="Account email address">
            <span className="text-sm text-slate-400">{user?.email}</span>
          </Row>
          <Row label="Role" sub="Your access level">
            <span className="badge-cyan capitalize">{user?.role}</span>
          </Row>
          <Row label="Account Status">
            <span className="badge-mint">Active</span>
          </Row>
        </Section>
      </motion.div>

      <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.1 }}>
        <Section icon={Database} title="Data Source">
          <Row label="Host" sub="MySQL server address">
            <span className="text-xs font-mono text-slate-400">139.84.243.180</span>
          </Row>
          <Row label="Port">
            <span className="text-xs font-mono text-slate-400">3306</span>
          </Row>
          <Row label="Database">
            <span className="text-xs font-mono text-primary">Data_Science</span>
          </Row>
          <Row label="Connection Status">
            <div className="flex items-center gap-2">
              <span className="w-2 h-2 rounded-full bg-mint-500 animate-pulse" />
              <span className="text-xs text-mint-500 font-medium">Connected</span>
            </div>
          </Row>
        </Section>
      </motion.div>

      <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.15 }}>
        <Section icon={Shield} title="Security & Governance">
          <Row label="Approval Workflow" sub="Require superuser approval before publishing">
            <div className="w-10 h-6 rounded-full relative cursor-pointer" style={{ background: 'rgba(6,255,165,0.3)', border: '1px solid rgba(6,255,165,0.4)' }}>
              <div className="absolute right-1 top-1 w-4 h-4 rounded-full bg-mint-500" />
            </div>
          </Row>
          <Row label="Audit Logging" sub="Track all user actions">
            <div className="w-10 h-6 rounded-full relative cursor-pointer" style={{ background: 'rgba(6,255,165,0.3)', border: '1px solid rgba(6,255,165,0.4)' }}>
              <div className="absolute right-1 top-1 w-4 h-4 rounded-full bg-mint-500" />
            </div>
          </Row>
          <Row label="Row-Level Security" sub="Filter data by logged-in user identity">
            <div className="w-10 h-6 rounded-full relative cursor-pointer" style={{ background: 'rgba(255,255,255,0.1)', border: '1px solid rgba(255,255,255,0.15)' }}>
              <div className="absolute left-1 top-1 w-4 h-4 rounded-full bg-slate-600" />
            </div>
          </Row>
        </Section>
      </motion.div>

      <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.2 }}>
        <Section icon={Palette} title="Appearance">
          <Row label="Theme" sub="Interface color scheme">
            <span className="badge-cyan">Dark (Space)</span>
          </Row>
          <Row label="Code Font" sub="Monospace font for code cells">
            <span className="text-xs font-mono text-slate-400">JetBrains Mono</span>
          </Row>
          <Row label="Editor Font Size">
            <span className="text-xs text-slate-400">13px</span>
          </Row>
        </Section>
      </motion.div>

      <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.25 }}>
        <Section icon={Key} title="API & Integrations">
          <div className="rounded-xl p-4" style={{ background: 'rgba(0,212,255,0.04)', border: '1px solid rgba(0,212,255,0.1)' }}>
            <p className="text-xs text-slate-400 mb-2">API Base URL</p>
            <code className="text-xs text-primary font-mono">http://localhost:8000/api/v1</code>
          </div>
          <div className="mt-4 rounded-xl p-4" style={{ background: 'rgba(255,255,255,0.03)', border: '1px solid rgba(255,255,255,0.07)' }}>
            <p className="text-xs text-slate-500">
              WebSocket endpoint for real-time cell execution:
              <code className="text-primary ml-1 font-mono">ws://localhost:8000/api/v1/execute/ws/&#123;notebook_id&#125;</code>
            </p>
          </div>
        </Section>
      </motion.div>
    </div>
  )
}
