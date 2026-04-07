import React, { useEffect, useRef } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { Zap } from 'lucide-react'
import useAuthStore from '../store/authStore'

/**
 * Landing page for the Laravel SSO redirect.
 *
 * Laravel redirects to:  <otenga_url>/sso?token=<laravel_jwt>
 *
 * This page silently exchanges the Laravel token for an Otenga session
 * token and then sends the user to the dashboard.
 */
export default function SSOCallbackPage() {
  const [searchParams] = useSearchParams()
  const navigate = useNavigate()
  const { loginWithSSOToken, isAuthenticated } = useAuthStore()
  const attempted = useRef(false)

  useEffect(() => {
    if (isAuthenticated) {
      navigate('/', { replace: true })
      return
    }

    const token = searchParams.get('token')
    if (!token) {
      navigate('/login', { replace: true })
      return
    }

    if (attempted.current) return
    attempted.current = true

    loginWithSSOToken(token).then((ok) => {
      navigate(ok ? '/' : '/login', { replace: true })
    })
  }, []) // eslint-disable-line react-hooks/exhaustive-deps

  return (
    <div className="min-h-screen bg-space-950 flex flex-col items-center justify-center gap-5">
      <div className="w-14 h-14 rounded-2xl flex items-center justify-center"
        style={{ background: 'linear-gradient(135deg, #00D4FF, #7C3AED)' }}>
        <Zap size={26} className="text-white" />
      </div>

      <div className="flex flex-col items-center gap-2 text-center">
        <h2 className="text-xl font-bold text-slate-100">Signing you in…</h2>
        <p className="text-slate-500 text-sm">Verifying your credentials with the company app.</p>
      </div>

      {/* Spinner */}
      <div className="w-8 h-8 border-2 border-primary/30 border-t-primary rounded-full animate-spin mt-2" />
    </div>
  )
}
