import React, { useState } from 'react'
import { ArrowLeft, ArrowRight, Lock, PlayCircle, ShieldCheck } from 'lucide-react'
import { useNavigate } from 'react-router-dom'
import { usePortalStore } from '../../store/usePortalStore'

export const PortalLoginGate: React.FC = () => {
  const navigate = useNavigate()
  const { setAuthParams, hydratePortal, pushToast } = usePortalStore()
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!username.trim() || !password.trim()) {
      setError('Enter your hotel portal username and password.')
      return
    }
    setLoading(true)
    setError('')
    try {
      const res = await fetch('/api/client/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username: username.trim(), password: password.trim() }),
      })
      const d = await res.json()
      if (!res.ok || !d.ok || !d.token) {
        setError(d.error || 'Invalid username or password.')
        setLoading(false)
        return
      }
      setAuthParams(d.token, null)
      await hydratePortal(null, null)
      pushToast({
        tone: 'success',
        title: 'Signed In to Isolated Hotel Account',
        detail: d.account?.display_name || username.trim(),
      })
    } catch {
      setError('Unable to verify credentials right now. Try again or explore the sample demo below.')
    } finally {
      setLoading(false)
    }
  }

  const handleLaunchDemo = async () => {
    setAuthParams('', '23')
    await hydratePortal('23', null)
    navigate('/portal?demo_hotel=23')
  }

  return (
    <div className="min-h-screen ember-gradient-bg flex items-center justify-center p-4">
      <div className="w-full max-w-md ember-card p-6 sm:p-8 space-y-5 shadow-emberShell">
        <div className="flex items-center justify-between gap-2">
          <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-blue-50 border border-blue-200 text-[10.5px] font-extrabold uppercase text-blue-800">
            <ShieldCheck className="w-3.5 h-3.5 text-blue-600" />
            Isolated Client Portal
          </span>
          <button
            type="button"
            onClick={() => navigate('/')}
            className="text-xs font-bold text-[#475B80] hover:text-blue-700 inline-flex items-center gap-1"
          >
            <ArrowLeft className="w-3.5 h-3.5" />
            Homepage
          </button>
        </div>

        <div>
          <h1 className="text-2xl font-black text-[#0B1B3B] tracking-tight">Hotel Client Sign In</h1>
          <p className="text-xs text-[#475B80] mt-1 leading-relaxed">
            Each Miami property gets an isolated account for its assigned street competitors, Room Ops (OOO/OOS), and daily AI BAR recommendations.
          </p>
        </div>

        <form onSubmit={handleLogin} className="space-y-3">
          <div>
            <label htmlFor="portal-user" className="block text-[10.5px] font-extrabold uppercase text-[#475B80] mb-1">
              Hotel Username or Work Email
            </label>
            <input
              id="portal-user"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              placeholder="e.g. reservations@yourhotel.com"
              autoComplete="username"
              className="w-full px-3.5 py-2.5 text-xs rounded-xl border border-[#DCE7F8] bg-[#F7FAFF] text-[#0B1B3B]"
            />
          </div>
          <div>
            <label htmlFor="portal-pass" className="block text-[10.5px] font-extrabold uppercase text-[#475B80] mb-1">
              Password
            </label>
            <input
              id="portal-pass"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="Enter password"
              autoComplete="current-password"
              className="w-full px-3.5 py-2.5 text-xs rounded-xl border border-[#DCE7F8] bg-[#F7FAFF] text-[#0B1B3B]"
            />
          </div>

          {error && (
            <div className="p-2.5 rounded-xl bg-rose-50 border border-rose-200 text-xs font-bold text-rose-700">
              {error}
            </div>
          )}

          <button
            type="submit"
            disabled={loading}
            className="w-full py-2.5 rounded-xl bg-[#0D255B] text-white text-xs font-extrabold hover:bg-blue-800 inline-flex items-center justify-center gap-1.5 disabled:opacity-60 transition"
          >
            <Lock className="w-3.5 h-3.5" />
            {loading ? 'Signing In...' : 'Sign In to My Hotel Portal'}
          </button>
        </form>

        <div className="pt-4 border-t border-[#EAF1FC] space-y-2.5">
          <div className="text-[11px] font-extrabold uppercase text-[#6D81A8]">
            Just Evaluating? Try the Live Interactive Sample
          </div>
          <button
            type="button"
            onClick={handleLaunchDemo}
            className="w-full py-2.5 px-4 rounded-xl bg-blue-50 border border-blue-200 text-blue-800 text-xs font-extrabold hover:bg-blue-100 inline-flex items-center justify-between transition"
          >
            <span className="inline-flex items-center gap-1.5">
              <PlayCircle className="w-4 h-4 text-blue-600" />
              Open Interactive Demo (Avalon South Beach)
            </span>
            <ArrowRight className="w-3.5 h-3.5" />
          </button>
          <div className="text-center text-xs text-[#475B80] pt-1">
            New property?{' '}
            <button
              type="button"
              onClick={() => navigate('/pricing#register')}
              className="font-extrabold text-blue-700 hover:underline"
            >
              Create your Free ($0/mo) isolated account →
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
