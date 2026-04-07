import React, { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { motion, AnimatePresence } from 'framer-motion'
import { Eye, EyeOff, Zap, ArrowRight, Database, BarChart3, Code2, UserPlus, LogIn, CheckCircle2, Mail, MailOpen } from 'lucide-react'
import useAuthStore from '../../store/authStore'
import client from '../../api/client'
import toast from 'react-hot-toast'

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
  const [tab, setTab]               = useState('login') // 'login' | 'register'
  const [registered, setRegistered] = useState(false)
  const [registeredEmail, setRegisteredEmail] = useState('')
  const [resending, setResending]   = useState(false)

  // login fields
  const [loginForm, setLoginForm] = useState({ username: '', password: '' })
  const [showLoginPass, setShowLoginPass] = useState(false)

  // register fields
  const [regForm, setRegForm]     = useState({ username: '', email: '', full_name: '', password: '', confirm: '' })
  const [showRegPass, setShowRegPass] = useState(false)
  const [regError, setRegError]   = useState('')

  const { login, register, isLoading, isAuthenticated } = useAuthStore()
  const navigate = useNavigate()

  useEffect(() => {
    if (isAuthenticated) navigate('/', { replace: true })
  }, [isAuthenticated, navigate])

  const handleLogin = async (e) => {
    e.preventDefault()
    const ok = await login(loginForm.username, loginForm.password)
    if (ok) navigate('/')
  }

  const handleRegister = async (e) => {
    e.preventDefault()
    setRegError('')
    if (regForm.password !== regForm.confirm) {
      setRegError('Passwords do not match.')
      return
    }
    if (regForm.password.length < 6) {
      setRegError('Password must be at least 6 characters.')
      return
    }
    const ok = await register({
      username:  regForm.username,
      email:     regForm.email,
      full_name: regForm.full_name || undefined,
      password:  regForm.password,
    })
    if (ok) {
      setRegistered(true)
      setRegisteredEmail(regForm.email)
    }
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

          <div className="flex flex-wrap gap-2 mb-10">
            <FeaturePill icon={Database}  label="SQL + Python cells" />
            <FeaturePill icon={Code2}     label="Pandas & Plotly" />
            <FeaturePill icon={BarChart3} label="Live dashboards" />
          </div>

          <div className="rounded-xl p-4" style={{ background: 'rgba(0,212,255,0.05)', border: '1px solid rgba(0,212,255,0.15)' }}>
            <p className="text-xs font-semibold text-primary mb-2">Demo credentials</p>
            <div className="space-y-1 text-xs text-slate-400 font-mono">
              <div><span className="text-slate-500">superuser →</span> admin / admin123</div>
              <div><span className="text-slate-500">creator   →</span> creator / creator123</div>
              <div><span className="text-slate-500">viewer    →</span> viewer / viewer123</div>
            </div>
          </div>
        </motion.div>

        {/* Right — form card */}
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

            {/* Tab switcher */}
            <div className="flex border-b border-white/[0.07]">
              <button
                onClick={() => { setTab('login'); setRegistered(false) }}
                className={`flex-1 flex items-center justify-center gap-2 py-3.5 text-sm font-medium transition-all duration-200 ${tab === 'login' ? 'text-primary border-b-2 border-primary' : 'text-slate-500 hover:text-slate-300'}`}
                style={{ borderBottom: tab === 'login' ? '2px solid #00D4FF' : '2px solid transparent' }}
              >
                <LogIn size={14} /> Sign In
              </button>
              <button
                onClick={() => { setTab('register'); setRegistered(false) }}
                className={`flex-1 flex items-center justify-center gap-2 py-3.5 text-sm font-medium transition-all duration-200 ${tab === 'register' ? 'text-primary' : 'text-slate-500 hover:text-slate-300'}`}
                style={{ borderBottom: tab === 'register' ? '2px solid #00D4FF' : '2px solid transparent' }}
              >
                <UserPlus size={14} /> Register
              </button>
            </div>

            <div className="p-8">
              <AnimatePresence mode="wait">

                {/* ── Sign-in ── */}
                {tab === 'login' && (
                  <motion.div
                    key="login"
                    initial={{ opacity: 0, x: -16 }}
                    animate={{ opacity: 1, x: 0 }}
                    exit={{ opacity: 0, x: 16 }}
                    transition={{ duration: 0.2 }}
                  >
                    <h3 className="text-xl font-bold text-slate-100 mb-1">Welcome back</h3>
                    <p className="text-slate-500 text-sm mb-7">Sign in to your workspace</p>

                    <form onSubmit={handleLogin} className="space-y-4">
                      <div>
                        <label className="block text-xs font-medium text-slate-400 mb-1.5">Username</label>
                        <input
                          type="text"
                          placeholder="Enter username"
                          value={loginForm.username}
                          onChange={(e) => setLoginForm({ ...loginForm, username: e.target.value })}
                          className="input-field"
                          required autoFocus
                        />
                      </div>
                      <div>
                        <label className="block text-xs font-medium text-slate-400 mb-1.5">Password</label>
                        <div className="relative">
                          <input
                            type={showLoginPass ? 'text' : 'password'}
                            placeholder="Enter password"
                            value={loginForm.password}
                            onChange={(e) => setLoginForm({ ...loginForm, password: e.target.value })}
                            className="input-field pr-10"
                            required
                          />
                          <button type="button" onClick={() => setShowLoginPass(!showLoginPass)}
                            className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-500 hover:text-slate-300 transition-colors">
                            {showLoginPass ? <EyeOff size={15} /> : <Eye size={15} />}
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

                    <p className="text-xs text-slate-600 text-center mt-6">
                      Don't have an account?{' '}
                      <button onClick={() => setTab('register')} className="text-primary hover:underline">Register here</button>
                    </p>
                  </motion.div>
                )}

                {/* ── Registration ── */}
                {tab === 'register' && !registered && (
                  <motion.div
                    key="register"
                    initial={{ opacity: 0, x: 16 }}
                    animate={{ opacity: 1, x: 0 }}
                    exit={{ opacity: 0, x: -16 }}
                    transition={{ duration: 0.2 }}
                  >
                    <h3 className="text-xl font-bold text-slate-100 mb-1">Create account</h3>
                    <p className="text-slate-500 text-sm mb-6">
                      You'll be registered as a <span className="text-mint-400 font-medium">viewer</span>. A superuser will approve your request.
                    </p>

                    <form onSubmit={handleRegister} className="space-y-3.5">
                      <div>
                        <label className="block text-xs font-medium text-slate-400 mb-1.5">Username <span className="text-rose-400">*</span></label>
                        <input type="text" placeholder="Choose a username" value={regForm.username}
                          onChange={e => setRegForm({ ...regForm, username: e.target.value })}
                          className="input-field" required autoFocus />
                      </div>
                      <div>
                        <label className="block text-xs font-medium text-slate-400 mb-1.5">Full name</label>
                        <input type="text" placeholder="Your full name (optional)" value={regForm.full_name}
                          onChange={e => setRegForm({ ...regForm, full_name: e.target.value })}
                          className="input-field" />
                      </div>
                      <div>
                        <label className="block text-xs font-medium text-slate-400 mb-1.5">Email <span className="text-rose-400">*</span></label>
                        <input type="email" placeholder="your@email.com" value={regForm.email}
                          onChange={e => setRegForm({ ...regForm, email: e.target.value })}
                          className="input-field" required />
                      </div>
                      <div>
                        <label className="block text-xs font-medium text-slate-400 mb-1.5">Password <span className="text-rose-400">*</span></label>
                        <div className="relative">
                          <input type={showRegPass ? 'text' : 'password'} placeholder="Min. 6 characters" value={regForm.password}
                            onChange={e => setRegForm({ ...regForm, password: e.target.value })}
                            className="input-field pr-10" required />
                          <button type="button" onClick={() => setShowRegPass(!showRegPass)}
                            className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-500 hover:text-slate-300 transition-colors">
                            {showRegPass ? <EyeOff size={15} /> : <Eye size={15} />}
                          </button>
                        </div>
                      </div>
                      <div>
                        <label className="block text-xs font-medium text-slate-400 mb-1.5">Confirm password <span className="text-rose-400">*</span></label>
                        <input type="password" placeholder="Repeat password" value={regForm.confirm}
                          onChange={e => setRegForm({ ...regForm, confirm: e.target.value })}
                          className="input-field" required />
                      </div>

                      {regError && (
                        <p className="text-xs text-rose-400 bg-rose-500/10 px-3 py-2 rounded-lg border border-rose-500/20">{regError}</p>
                      )}

                      <button type="submit" disabled={isLoading}
                        className="btn-primary w-full justify-center mt-1 py-3 text-sm font-semibold disabled:opacity-60 disabled:cursor-not-allowed">
                        {isLoading ? (
                          <span className="flex items-center gap-2">
                            <span className="w-4 h-4 border-2 border-space-950/30 border-t-space-950 rounded-full animate-spin" />
                            Registering...
                          </span>
                        ) : (
                          <span className="flex items-center gap-2"><UserPlus size={15} /> Create account</span>
                        )}
                      </button>
                    </form>

                    <p className="text-xs text-slate-600 text-center mt-5">
                      Already have an account?{' '}
                      <button onClick={() => setTab('login')} className="text-primary hover:underline">Sign in</button>
                    </p>
                  </motion.div>
                )}

                {/* ── Registration success ── */}
                {tab === 'register' && registered && (
                  <motion.div
                    key="success"
                    initial={{ opacity: 0, scale: 0.95 }}
                    animate={{ opacity: 1, scale: 1 }}
                    transition={{ duration: 0.3 }}
                    className="flex flex-col items-center text-center py-2"
                  >
                    <div className="w-16 h-16 rounded-full flex items-center justify-center mb-4"
                      style={{ background: 'rgba(0,212,255,0.1)', border: '1px solid rgba(0,212,255,0.3)' }}>
                      <MailOpen size={30} className="text-primary" />
                    </div>
                    <h3 className="text-xl font-bold text-slate-100 mb-2">Check your inbox!</h3>
                    <p className="text-slate-400 text-sm leading-relaxed mb-4">
                      We've sent a verification link to{' '}
                      <span className="text-primary font-medium">{registeredEmail}</span>.
                      Click the link to verify your email, then wait for an administrator to approve your account.
                    </p>

                    {/* Steps */}
                    <div className="w-full text-left space-y-2 mb-5">
                      {[
                        { n: '1', label: 'Check your email and click the verification link', done: false },
                        { n: '2', label: 'Wait for superuser approval',                      done: false },
                        { n: '3', label: 'Sign in and start using Otenga',                   done: false },
                      ].map(step => (
                        <div key={step.n} className="flex items-center gap-3 px-3 py-2 rounded-lg"
                          style={{ background: 'rgba(0,212,255,0.05)', border: '1px solid rgba(0,212,255,0.1)' }}>
                          <span className="w-5 h-5 rounded-full flex items-center justify-center text-[10px] font-bold text-space-950 flex-shrink-0"
                            style={{ background: '#00D4FF' }}>{step.n}</span>
                          <span className="text-xs text-slate-400">{step.label}</span>
                        </div>
                      ))}
                    </div>

                    <p className="text-xs text-slate-600 mb-4">
                      Didn't receive the email?{' '}
                      <button
                        disabled={resending}
                        onClick={async () => {
                          setResending(true)
                          try {
                            await client.post(`/auth/resend-verification?email=${encodeURIComponent(registeredEmail)}`)
                            toast.success('Verification email resent!')
                          } catch {
                            toast.error('Could not resend — please try again.')
                          } finally {
                            setResending(false)
                          }
                        }}
                        className="text-primary hover:underline disabled:opacity-50"
                      >
                        {resending ? 'Sending…' : 'Resend link'}
                      </button>
                    </p>

                    <button onClick={() => { setTab('login'); setRegistered(false) }}
                      className="btn-primary px-6 py-2.5 text-sm w-full justify-center">
                      Back to Sign In
                    </button>
                  </motion.div>
                )}

              </AnimatePresence>
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
