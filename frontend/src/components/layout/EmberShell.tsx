import React, { useState } from 'react'
import { NavLink, useNavigate } from 'react-router-dom'
import {
  LayoutDashboard,
  Building2,
  BedDouble,
  Wrench,
  Bot,
  LineChart,
  BookmarkCheck,
  PhoneCall,
  Layers,
  Settings,
  Menu,
  X,
  Search,
  RefreshCw,
  Calendar,
  ExternalLink,
  ShieldCheck,
  ArrowLeft,
} from 'lucide-react'
import { usePortalStore } from '../../store/usePortalStore'
import type { DateRangeKey } from '../../types/hospitality'
import { ModalDialog } from '../ui/ModalDialog'

interface EmberShellProps {
  children: React.ReactNode
}

const PORTAL_NAV_ITEMS = [
  { to: '/portal', label: 'Overview', icon: LayoutDashboard, end: true },
  { to: '/portal/comp-set', label: 'Comp-Set & Rates', icon: Building2 },
  { to: '/portal/room-match', label: 'Suite vs. Suite Match', icon: BedDouble },
  { to: '/portal/room-ops', label: 'Room Ops (OOO/OOS)', icon: Wrench },
  { to: '/portal/auto-pricing', label: 'AI Auto-Pricing', icon: Bot },
  { to: '/portal/analytics', label: 'Yield Analytics', icon: LineChart },
  { to: '/portal/memory', label: 'Memory & Tags', icon: BookmarkCheck },
  { to: '/portal/call-desk', label: 'Night Audit Desk', icon: PhoneCall },
  { to: '/portal/plans', label: 'Plans & ROI', icon: Layers },
  { to: '/portal/settings', label: 'Settings', icon: Settings },
]

export const EmberShell: React.FC<EmberShellProps> = ({ children }) => {
  const navigate = useNavigate()
  const [mobileOpen, setMobileOpen] = useState(false)
  const [switchModalOpen, setSwitchModalOpen] = useState(false)
  const [loginUser, setLoginUser] = useState('avalon')
  const [loginPass, setLoginPass] = useState('demo1234')
  const [loginError, setLoginError] = useState('')

  const {
    portal,
    isLiveBackend,
    isLoading,
    clientToken,
    demoHotelId,
    globalSearch,
    setGlobalSearch,
    dateRange,
    setDateRange,
    scrapeCompSet,
    hydratePortal,
    setAuthParams,
    pushToast,
  } = usePortalStore()

  const handleQuickDemoSwitch = async (demoHid: string, label: string) => {
    setAuthParams('', demoHid)
    await hydratePortal(demoHid, null)
    setSwitchModalOpen(false)
    pushToast({ tone: 'info', title: `Switched Demo Property`, detail: `Viewing ${label}` })
  }

  const handleCredentialLogin = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoginError('')
    try {
      const res = await fetch('/api/client/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username: loginUser, password: loginPass }),
      })
      const d = await res.json()
      if (!d.ok) {
        setLoginError(d.error || 'Account not found.')
        return
      }
      setAuthParams(d.token, null)
      await hydratePortal(null, null)
      setSwitchModalOpen(false)
      pushToast({ tone: 'success', title: 'Signed In to Isolated Account', detail: d.account?.display_name || loginUser })
    } catch {
      setLoginError('Live login unavailable offline — choose a Demo Hotel below.')
    }
  }

  const sidebarContent = (
    <div className="flex flex-col h-full justify-between p-4 text-white">
      <div className="space-y-4">
        {/* Brand Badge */}
        <div className="flex items-center justify-between gap-2 px-2 pt-1">
          <div className="flex items-center gap-2.5 min-w-0">
            <div className="w-9 h-9 rounded-2xl bg-gradient-to-br from-blue-500 to-blue-700 border border-blue-300/30 flex items-center justify-center shrink-0 shadow-lg">
              <img
                src="/assets/logo.png"
                alt="HotelRateIntel"
                className="w-6 h-6 rounded-md object-cover"
                onError={(e) => {
                  ;(e.currentTarget as HTMLImageElement).style.display = 'none'
                }}
              />
            </div>
            <div className="min-w-0">
              <div className="text-sm font-extrabold tracking-tight truncate">HotelRateIntel</div>
              <div className="text-[10px] text-blue-200/80 font-semibold truncate">Made by Hoteliers · V20</div>
            </div>
          </div>
          <button
            type="button"
            onClick={() => setMobileOpen(false)}
            aria-label="Close sidebar"
            className="lg:hidden p-1.5 rounded-xl bg-white/10 text-blue-100"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Active Hotel Isolation Pill */}
        <div className="rounded-2xl bg-white/10 border border-blue-300/20 p-3 space-y-1.5">
          <div className="flex items-center justify-between gap-2">
            <span className="inline-flex items-center gap-1 text-[10px] font-bold uppercase tracking-wider text-blue-200">
              <ShieldCheck className="w-3 h-3 text-emerald-400" />
              {clientToken ? 'Isolated Account' : demoHotelId ? 'Interactive Demo' : 'Isolated Account'}
            </span>
            <span className="px-2 py-0.5 rounded-full bg-blue-500/30 border border-blue-300/30 text-[9.5px] font-extrabold text-blue-100">
              {portal.active_tier.tier_id === 'free'
                ? '$0 FREE'
                : portal.active_tier.tier_id === 'core_99'
                  ? '$99 CORE'
                  : '$199 PRO'}
            </span>
          </div>
          <div className="text-xs font-extrabold truncate text-white">{portal.primary_hotel.name}</div>
          <div className="text-[10.5px] text-blue-200/80 truncate">
            {portal.primary_hotel.area} · {portal.comp_set.length} comps
          </div>
        </div>

        {/* Primary Navigation Links */}
        <nav aria-label="Client Portal Navigation" className="space-y-1">
          {PORTAL_NAV_ITEMS.map((item) => {
            const Icon = item.icon
            return (
              <NavLink
                key={item.to}
                to={item.to}
                end={item.end}
                onClick={() => setMobileOpen(false)}
                className={({ isActive }) =>
                  `flex items-center gap-2.5 px-3 py-2 rounded-xl text-xs font-bold transition-all ${
                    isActive
                      ? 'bg-gradient-to-r from-blue-600 to-blue-500 text-white shadow-[0_8px_20px_rgba(37,99,235,0.40)]'
                      : 'text-blue-100/80 hover:bg-white/10 hover:text-white'
                  }`
                }
              >
                <Icon className="w-4 h-4 shrink-0" />
                <span className="truncate">{item.label}</span>
              </NavLink>
            )
          })}
        </nav>
      </div>

      {/* Bottom Quick Links */}
      <div className="pt-3 border-t border-white/10 space-y-1.5">
        <button
          type="button"
          onClick={() => setSwitchModalOpen(true)}
          className="w-full px-3 py-2 rounded-xl bg-white/10 hover:bg-white/15 text-xs font-bold text-blue-100 flex items-center justify-center gap-1.5 transition"
        >
          Switch Hotel / Login
        </button>
        <button
          type="button"
          onClick={() => {
            setAuthParams('', null)
            navigate('/portal', { replace: true })
          }}
          className="w-full px-3 py-1.5 rounded-xl bg-white/5 hover:bg-white/15 text-[11px] font-bold text-blue-200 flex items-center justify-center gap-1.5 transition"
        >
          Sign Out / Lock Portal
        </button>
        <button
          type="button"
          onClick={() => navigate('/')}
          className="w-full px-3 py-2 rounded-xl border border-blue-300/20 text-xs font-bold text-blue-200 hover:bg-white/10 flex items-center justify-center gap-1.5 transition"
        >
          <ArrowLeft className="w-3.5 h-3.5" />
          Public Website
        </button>
      </div>
    </div>
  )

  return (
    <div className="min-h-screen ember-gradient-bg p-2.5 sm:p-4 lg:p-5 flex gap-4">
      {/* Desktop Floating Rounded Navy Sidebar */}
      <aside className="hidden lg:block w-[252px] shrink-0 rounded-[24px] ember-sidebar-glass sticky top-4 h-[calc(100vh-32px)] overflow-y-auto">
        {sidebarContent}
      </aside>

      {/* Mobile Slide-Over Navigation Drawer */}
      {mobileOpen && (
        <div className="fixed inset-0 z-50 lg:hidden flex">
          <div className="w-[268px] max-w-[85vw] h-full ember-sidebar-glass overflow-y-auto">{sidebarContent}</div>
          <div className="flex-1 bg-black/50 backdrop-blur-xs" onClick={() => setMobileOpen(false)} />
        </div>
      )}

      {/* Main Rounded Light-Blue Ember Content Panel */}
      <div className="flex-1 min-w-0 rounded-[26px] ember-canvas-panel flex flex-col overflow-hidden">
        {/* Top Light Utility Bar */}
        <header className="bg-white/90 backdrop-blur-md border-b border-[#DCE7F8] px-4 sm:px-6 py-3 flex items-center justify-between gap-3 flex-wrap">
          <div className="flex items-center gap-2.5 min-w-0">
            <button
              type="button"
              onClick={() => setMobileOpen(true)}
              aria-label="Open navigation menu"
              className="lg:hidden p-2 rounded-xl bg-[#F2F6FD] border border-[#DCE7F8] text-[#0B1B3B]"
            >
              <Menu className="w-4 h-4" />
            </button>

            <div className="relative w-44 sm:w-64">
              <Search className="w-3.5 h-3.5 text-[#6D81A8] absolute left-3 top-1/2 -translate-y-1/2" />
              <input
                type="text"
                value={globalSearch}
                onChange={(e) => setGlobalSearch(e.target.value)}
                placeholder="Filter competitors or notes..."
                className="w-full pl-8 pr-3 py-1.5 text-xs rounded-xl border border-[#DCE7F8] bg-[#F7FAFF] text-[#0B1B3B] placeholder-[#6D81A8] focus:outline-none focus:ring-2 focus:ring-blue-500/30"
              />
            </div>

            <div className="inline-flex items-center gap-1.5 px-2.5 py-1.5 rounded-xl bg-[#F7FAFF] border border-[#DCE7F8]">
              <Calendar className="w-3.5 h-3.5 text-blue-600" />
              <select
                aria-label="Date range filter"
                value={dateRange}
                onChange={(e) => setDateRange(e.target.value as DateRangeKey)}
                className="bg-transparent text-xs font-bold text-[#0B1B3B] focus:outline-none cursor-pointer"
              >
                <option value="today">Today + Tonight</option>
                <option value="7d">Next 7 Days</option>
                <option value="30d">Next 30 Days</option>
                <option value="art_basel">Art Basel Compression</option>
              </select>
            </div>
          </div>

          <div className="flex items-center gap-2 flex-wrap">
            <span
              className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[11px] font-extrabold border ${
                isLiveBackend
                  ? 'bg-emerald-50 text-emerald-700 border-emerald-200'
                  : 'bg-blue-50 text-blue-700 border-blue-200'
              }`}
            >
              <span className={`w-2 h-2 rounded-full ${isLiveBackend ? 'bg-emerald-500' : 'bg-blue-500'}`} />
              {isLiveBackend ? 'Live Local DB' : 'Demo Data Mode'}
            </span>

            <button
              type="button"
              onClick={() => scrapeCompSet()}
              disabled={isLoading}
              className="inline-flex items-center gap-1.5 px-3.5 py-1.5 rounded-xl bg-gradient-to-r from-blue-600 to-blue-700 text-white text-xs font-bold shadow-sm hover:brightness-110 disabled:opacity-60 transition"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${isLoading ? 'animate-spin' : ''}`} />
              {isLoading ? 'Scanning...' : 'Scrape Comp-Set'}
            </button>
          </div>
        </header>

        {/* Active Page Canvas */}
        <main className="flex-1 p-4 sm:p-6 overflow-x-clip">{children}</main>
      </div>

      {/* Hotel Account Switcher / Login Dialog */}
      <ModalDialog
        open={switchModalOpen}
        onClose={() => setSwitchModalOpen(false)}
        title="Switch Isolated Hotel Portal Account"
        subtitle="Each boutique property only accesses its own rooms, tags, OOO inventory, and assigned corridor competitors."
      >
        <form onSubmit={handleCredentialLogin} className="space-y-3 mb-5">
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <div>
              <label className="block text-[10.5px] font-extrabold uppercase text-[#475B80] mb-1">Username / Email</label>
              <input
                value={loginUser}
                onChange={(e) => setLoginUser(e.target.value)}
                className="w-full px-3 py-2 text-xs rounded-xl border border-[#DCE7F8] bg-[#F7FAFF]"
              />
            </div>
            <div>
              <label className="block text-[10.5px] font-extrabold uppercase text-[#475B80] mb-1">Password</label>
              <input
                type="password"
                value={loginPass}
                onChange={(e) => setLoginPass(e.target.value)}
                className="w-full px-3 py-2 text-xs rounded-xl border border-[#DCE7F8] bg-[#F7FAFF]"
              />
            </div>
          </div>
          {loginError && <div className="text-xs font-bold text-rose-600">{loginError}</div>}
          <button type="submit" className="w-full py-2.5 rounded-xl bg-[#0D255B] text-white text-xs font-bold hover:bg-blue-800 transition">
            Sign In with Hotel Credentials
          </button>
        </form>

        <div className="border-t border-[#EAF1FC] pt-4 space-y-2">
          <div className="text-[11px] font-extrabold uppercase text-[#6D81A8]">1-Click Sample Hotel Sandboxes (Demo Data)</div>
          <button
            type="button"
            onClick={() => handleQuickDemoSwitch('23', 'Avalon Hotel South Beach')}
            className="w-full px-3.5 py-2.5 rounded-xl bg-blue-50 border border-blue-200 text-xs font-bold text-[#0B1B3B] flex items-center justify-between hover:bg-blue-100"
          >
            <span>Avalon Hotel South Beach (Pro $199)</span>
            <span className="text-blue-700">Load Demo →</span>
          </button>
          <button
            type="button"
            onClick={() => handleQuickDemoSwitch('1', 'Seaside All Suites North Beach')}
            className="w-full px-3.5 py-2.5 rounded-xl bg-[#F7FAFF] border border-[#DCE7F8] text-xs font-bold text-[#0B1B3B] flex items-center justify-between hover:bg-blue-50"
          >
            <span>Seaside All Suites North Beach (Vio.com Leak Watch)</span>
            <span className="text-blue-700">Load Demo →</span>
          </button>
          <button
            type="button"
            onClick={() => handleQuickDemoSwitch('38', 'The Betsy Hotel South Beach')}
            className="w-full px-3.5 py-2.5 rounded-xl bg-[#F7FAFF] border border-[#DCE7F8] text-xs font-bold text-[#0B1B3B] flex items-center justify-between hover:bg-blue-50"
          >
            <span>The Betsy Hotel South Beach (Luxury Anchor)</span>
            <span className="text-blue-700">Load Demo →</span>
          </button>
        </div>
      </ModalDialog>
    </div>
  )
}
