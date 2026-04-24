import React, { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { motion } from 'framer-motion'
import { Eye, EyeOff, Zap, ArrowRight, Database, BarChart3, Code2, ExternalLink } from 'lucide-react'
import useAuthStore from '../../store/authStore'
import client from '../../api/client'

const FloatingOrb = ({ className, style }) => (
  <div className={`absolute rounded-full pointer-events-none ${className}`} style={{ filter: 'blur(80px)', ...style }} />
)

const FeaturePill = ({ icon: Icon, label }) => (
  <div className="flex items-center gap-2 px-3 py-1.5 rounded-full text-xs text-slate-400"
    style={{ background: 'rgba(255,255,255,0.05)', border: '1px solid rgba(255,255,255,0.08)' }}>
    <Icon size={12} className="text-primary" />
    {label}
  </div>
)

export default function LoginPage() {
  const [form, setForm]         = useState({ username: '', password: '' })
  const [showPass, setShowPass] = useState(false)
  const [ssoConfig, setSsoConfig] = useState(null)

  const { login, isLoading, isAuthenticated } = useAuthStore()
  const navigate = useNavigate()

  useEffect(() => {
    if (isAuthenticated) navigate('/', { replace: true })
  }, [isAuthenticated, navigate])

  useEffect(() => {
    client.get('/auth/sso/config')
      .then(({ data }) => setSsoConfig(data))
      .catch(() => setSsoConfig({ enabled: false, laravel_app_url: null }))
  }, [])

  const handleLogin = async (e) => {
    e.preventDefault()
    const ok = await login(form.username, form.password)
    if (ok) navigate('/')
  }

  const handleSSORedirect = () => {
    if (!ssoConfig?.laravel_app_url) return
    const returnTo = encodeURIComponent(`${window.location.origin}/sso`)
    window.location.href = `${ssoConfig.laravel_app_url}?return_to=${returnTo}`
  }

  return (
    <div className="min-h-screen bg-space-950 flex items-center justify-center relative overflow-hidden">
      {/* Animated background */}
      <FloatingOrb className="w-[600px] h-[600px] -top-48 -left-24 animate-float" style={{ background: 'rgba(124,58,237,0.12)', animationDuration: '10s' }} />
      <FloatingOrb className="w-[500px] h-[500px] -bottom-32 -right-16 animate-float" style={{ background: 'rgba(0,212,255,0.1)', animationDuration: '14s', animationDelay: '-5s' }} />
      <FloatingOrb className="w-[300px] h-[300px] top-1/3 right-1/4 animate-float" style={{ background: 'rgba(6,255,165,0.07)', animationDuration: '8s', animationDelay: '-2s' }} />

      <div className="absolute inset-0 opacity-[0.015]" style={{
        backgroundImage: 'linear-gradient(rgba(0,212,255,1) 1px, transparent 1px), linear-gradient(90deg, rgba(0,212,255,1) 1px, transparent 1px)',
        backgroundSize: '60px 60px',
      }} />

      <div className="relative z-10 w-full max-w-5xl mx-auto px-4 flex items-center gap-16">
        {/* Left — branding */}
        <motion.div
          initial={{ opacity: 0, x: -40 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ duration: 0.7, ease: 'easeOut' }}
          className="hidden lg:flex flex-col flex-1"
        >
          <div className="flex items-center gap-3 mb-8">
            <div className="w-12 h-12 rounded-2xl flex items-center justify-center" style={{ background: 'linear-gradient(135deg, #00D4FF, #7C3AED)' }}>
              <Zap size={24} className="text-white" />
            </div>
            <div>
              <h1 className="text-3xl font-bold text-gradient-brand">Otenga</h1>
              <p className="text-xs text-slate-500 tracking-widest uppercase">Business Intelligence</p>
            </div>
          </div>

          <h2 className="text-4xl font-bold text-slate-100 leading-tight mb-4">
            Data intelligence,<br />
            <span className="text-gradient-cyan">beautifully crafted.</span>
          </h2>

          <p className="text-slate-400 text-base mb-8 leading-relaxed max-w-md">
            A Python-native BI platform for data creators. Write SQL, transform with Pandas, build interactive dashboards — all in one fluid workspace.
          </p>

          <div className="flex flex-wrap gap-2">
            <FeaturePill icon={Database}  label="SQL + Python cells" />
            <FeaturePill icon={Code2}     label="Pandas & Plotly" />
            <FeaturePill icon={BarChart3} label="Live dashboards" />
          </div>
        </motion.div>

        {/* Right — login card */}
        <motion.div
          initial={{ opacity: 0, y: 30 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, delay: 0.1, ease: 'easeOut' }}
          className="w-full max-w-sm mx-auto lg:mx-0"
        >
          <div className="glass-strong rounded-2xl overflow-hidden">
            {/* Mobile logo */}
            <div className="flex lg:hidden items-center gap-3 px-8 pt-8 mb-6">
              <div className="w-10 h-10 rounded-xl flex items-center justify-center" style={{ background: 'linear-gradient(135deg, #00D4FF, #7C3AED)' }}>
                <Zap size={20} className="text-white" />
              </div>
              <h1 className="text-2xl font-bold text-gradient-brand">Otenga</h1>
            </div>

            <div className="p-8">
              <h3 className="text-xl font-bold text-slate-100 mb-1">Welcome back</h3>
              <p className="text-slate-500 text-sm mb-7">Sign in to your workspace</p>

              <form onSubmit={handleLogin} className="space-y-4">
                <div>
                  <label className="block text-xs font-medium text-slate-400 mb-1.5">Username</label>
                  <input
                    type="text"
                    placeholder="Enter username"
                    value={form.username}
                    onChange={(e) => setForm({ ...form, username: e.target.value })}
                    className="input-field"
                    required autoFocus
                  />
                </div>
                <div>
                  <label className="block text-xs font-medium text-slate-400 mb-1.5">Password</label>
                  <div className="relative">
                    <input
                      type={showPass ? 'text' : 'password'}
                      placeholder="Enter password"
                      value={form.password}
                      onChange={(e) => setForm({ ...form, password: e.target.value })}
                      className="input-field pr-10"
                      required
                    />
                    <button type="button" onClick={() => setShowPass(!showPass)}
                      className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-500 hover:text-slate-300 transition-colors">
                      {showPass ? <EyeOff size={15} /> : <Eye size={15} />}
                    </button>
                  </div>
                </div>
                <button type="submit" disabled={isLoading}
                  className="btn-primary w-full justify-center mt-2 py-3 text-sm font-semibold disabled:opacity-60 disabled:cursor-not-allowed">
                  {isLoading ? (
                    <span className="flex items-center gap-2">
                      <span className="w-4 h-4 border-2 border-space-950/30 border-t-space-950 rounded-full animate-spin" />
                      Signing in...
                    </span>
                  ) : (
                    <span className="flex items-center gap-2">Sign in <ArrowRight size={15} /></span>
                  )}
                </button>
              </form>

              {/* SSO — only shown when configured */}
              {ssoConfig?.enabled && (
                <>
                  <div className="flex items-center gap-3 my-5">
                    <div className="flex-1 h-px bg-white/[0.07]" />
                    <span className="text-xs text-slate-600">or</span>
                    <div className="flex-1 h-px bg-white/[0.07]" />
                  </div>
                  <button
                    type="button"
                    onClick={handleSSORedirect}
                    className="w-full flex items-center justify-center gap-2 py-2.5 rounded-xl text-sm font-medium text-slate-300 transition-all duration-200 hover:text-slate-100"
                    style={{ background: 'rgba(255,255,255,0.05)', border: '1px solid rgba(255,255,255,0.1)' }}
                  >
                    <ExternalLink size={14} className="text-primary" />
                    Continue with Company App
                  </button>
                </>
              )}
            </div>

            <p className="text-xs text-slate-700 text-center pb-5">
              © 2026 Otenga · Aleza Credit BI Platform
            </p>
          </div>
        </motion.div>
      </div>
    </div>
  )
}
