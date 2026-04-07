import React, { useEffect, useState } from 'react'
import { useSearchParams, useNavigate } from 'react-router-dom'
import { motion } from 'framer-motion'
import { CheckCircle2, XCircle, Loader2, Zap, ArrowRight, MailOpen } from 'lucide-react'
import client from '../api/client'

const FloatingOrb = ({ className, style }) => (
  <div className={`absolute rounded-full pointer-events-none ${className}`}
    style={{ filter: 'blur(80px)', ...style }} />
)

export default function VerifyEmailPage() {
  const [searchParams] = useSearchParams()
  const navigate        = useNavigate()
  const token           = searchParams.get('token')

  const [state, setState] = useState('verifying') // 'verifying' | 'success' | 'error'
  const [message, setMessage] = useState('')

  useEffect(() => {
    if (!token) {
      setState('error')
      setMessage('No verification token found in the URL.')
      return
    }

    client.get(`/auth/verify-email?token=${encodeURIComponent(token)}`)
      .then(res => {
        setState('success')
        setMessage(res.data.detail || 'Email verified!')
      })
      .catch(err => {
        setState('error')
        setMessage(err.response?.data?.detail || 'Verification failed. The link may have expired.')
      })
  }, [token])

  return (
    <div className="min-h-screen bg-space-950 flex items-center justify-center relative overflow-hidden">
      <FloatingOrb className="w-[600px] h-[600px] -top-48 -left-24 animate-float"
        style={{ background: 'rgba(124,58,237,0.12)', animationDuration: '10s' }} />
      <FloatingOrb className="w-[500px] h-[500px] -bottom-32 -right-16 animate-float"
        style={{ background: 'rgba(0,212,255,0.1)', animationDuration: '14s', animationDelay: '-5s' }} />

      <div className="absolute inset-0 opacity-[0.015]" style={{
        backgroundImage: 'linear-gradient(rgba(0,212,255,1) 1px, transparent 1px), linear-gradient(90deg, rgba(0,212,255,1) 1px, transparent 1px)',
        backgroundSize: '60px 60px',
      }} />

      <motion.div
        initial={{ opacity: 0, y: 24 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5 }}
        className="relative z-10 w-full max-w-md mx-4"
      >
        {/* Logo */}
        <div className="flex items-center justify-center gap-3 mb-8">
          <div className="w-11 h-11 rounded-2xl flex items-center justify-center"
            style={{ background: 'linear-gradient(135deg, #00D4FF, #7C3AED)' }}>
            <Zap size={22} className="text-white" />
          </div>
          <h1 className="text-2xl font-bold text-gradient-brand">Otenga</h1>
        </div>

        <div className="glass-strong rounded-2xl p-8 text-center">

          {state === 'verifying' && (
            <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="flex flex-col items-center gap-4 py-4">
              <div className="w-16 h-16 rounded-full flex items-center justify-center"
                style={{ background: 'rgba(0,212,255,0.1)', border: '1px solid rgba(0,212,255,0.25)' }}>
                <Loader2 size={28} className="text-primary animate-spin" />
              </div>
              <h2 className="text-lg font-bold text-slate-100">Verifying your email…</h2>
              <p className="text-slate-500 text-sm">Please wait a moment.</p>
            </motion.div>
          )}

          {state === 'success' && (
            <motion.div
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{ duration: 0.3 }}
              className="flex flex-col items-center gap-4 py-2"
            >
              <div className="w-16 h-16 rounded-full flex items-center justify-center"
                style={{ background: 'rgba(6,255,165,0.12)', border: '1px solid rgba(6,255,165,0.3)' }}>
                <CheckCircle2 size={32} className="text-mint-400" />
              </div>
              <h2 className="text-xl font-bold text-slate-100">Email verified!</h2>
              <p className="text-slate-400 text-sm leading-relaxed">{message}</p>

              <div className="mt-2 p-4 rounded-xl w-full text-left"
                style={{ background: 'rgba(0,212,255,0.05)', border: '1px solid rgba(0,212,255,0.15)' }}>
                <div className="flex items-start gap-3">
                  <MailOpen size={16} className="text-primary mt-0.5 flex-shrink-0" />
                  <p className="text-xs text-slate-400 leading-relaxed">
                    Your account is now in the approval queue. An administrator will review it and activate your access. You'll be able to sign in once approved.
                  </p>
                </div>
              </div>

              <button
                onClick={() => navigate('/login')}
                className="btn-primary w-full justify-center py-3 mt-2 text-sm font-semibold"
              >
                Go to Sign In <ArrowRight size={15} />
              </button>
            </motion.div>
          )}

          {state === 'error' && (
            <motion.div
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{ duration: 0.3 }}
              className="flex flex-col items-center gap-4 py-2"
            >
              <div className="w-16 h-16 rounded-full flex items-center justify-center"
                style={{ background: 'rgba(255,77,109,0.12)', border: '1px solid rgba(255,77,109,0.3)' }}>
                <XCircle size={32} className="text-rose-400" />
              </div>
              <h2 className="text-xl font-bold text-slate-100">Verification failed</h2>
              <p className="text-slate-400 text-sm leading-relaxed">{message}</p>

              <button
                onClick={() => navigate('/login')}
                className="btn-primary w-full justify-center py-3 mt-2 text-sm font-semibold"
              >
                Back to Sign In <ArrowRight size={15} />
              </button>
            </motion.div>
          )}

        </div>

        <p className="text-xs text-slate-700 text-center mt-6">
          © 2026 Otenga · Aleza Credit BI Platform
        </p>
      </motion.div>
    </div>
  )
}
