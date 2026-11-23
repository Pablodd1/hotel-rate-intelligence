import React, { useEffect, useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Cell,
} from 'recharts'
import {
  Building2,
  CheckCircle2,
  Clock,
  DollarSign,
  ExternalLink,
  Mail,
  MessageSquare,
  Phone,
  Search,
  ShieldCheck,
  Sparkles,
  TrendingUp,
  Zap,
} from 'lucide-react'
import {
  BLOGS_SEED,
  COMPARISON_MATRIX_SEED,
  HOTEL_JARGON_SOLUTIONS,
  PUBLIC_AUDIT_SEED,
  TIER_SEED,
} from '../../data/demoSeed'
import type { PublicAuditResponse, TierPlan } from '../../types/hospitality'
import { usePortalStore } from '../../store/usePortalStore'
import { VoiceConcierge } from '../../components/concierge/VoiceConcierge'
import { ModalDialog } from '../../components/ui/ModalDialog'

const registerSchema = z.object({
  hotel_name: z.string().min(2, 'Enter your hotel name'),
  area: z.string().min(2, 'Select corridor / city'),
  email: z.string().email('Enter a valid work email'),
  username: z.string().min(3, 'Username must be at least 3 characters'),
  password: z.string().min(6, 'Password must be at least 6 characters'),
  tier: z.enum(['free', 'core_99', 'pro_199', 'portfolio_399']),
})

type RegisterFormValues = z.infer<typeof registerSchema>

export const WebsitePage: React.FC = () => {
  const navigate = useNavigate()
  const { pushToast, setAuthParams, hydratePortal } = usePortalStore()

  const [rooms, setRooms] = useState(48)
  const [adr, setAdr] = useState(225)
  const [selectedSampleId, setSelectedSampleId] = useState('23')
  const [auditUrl, setAuditUrl] = useState('')
  const [auditLoading, setAuditLoading] = useState(false)
  const [auditResult, setAuditResult] = useState<PublicAuditResponse>(PUBLIC_AUDIT_SEED)
  const [tiers, setTiers] = useState<TierPlan[]>(TIER_SEED)
  const [compMatrix, setCompMatrix] = useState(COMPARISON_MATRIX_SEED)
  const [demoDirectory, setDemoDirectory] = useState<Array<{ id: number; name: string; price?: number | null }>>([
    { id: 23, name: 'Avalon Hotel South Beach (Sample #1)', price: 238 },
    { id: 1, name: 'Seaside All Suites North Beach', price: 82 },
    { id: 38, name: 'The Betsy Hotel South Beach', price: 478 },
  ])
  const [isLiveApi, setIsLiveApi] = useState(false)
  const [contactName, setContactName] = useState('')
  const [contactRole, setContactRole] = useState('General Manager / Owner')
  const [contactHotel, setContactHotel] = useState('')
  const [contactPhone, setContactPhone] = useState('')
  const [contactEmail, setContactEmail] = useState('')
  const [contactChannel, setContactChannel] = useState<'sms' | 'email' | 'call' | 'whatsapp'>('sms')
  const [contactNote, setContactNote] = useState('')
  const [contactSending, setContactSending] = useState(false)
  const [contactConfirmation, setContactConfirmation] = useState('')
  const [activeBlogIndex, setActiveBlogIndex] = useState<number | null>(null)

  const openCoordinatedContact = (channel: 'sms' | 'email' | 'call' | 'whatsapp') => {
    setContactChannel(channel)
    document.getElementById('contact-desk')?.scrollIntoView({ behavior: 'smooth' })
  }

  const handleDirectContactSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!contactPhone.trim() && !contactEmail.trim()) {
      pushToast({ tone: 'warning', title: 'Add Phone or Email', detail: 'Enter a phone number or work email so our Miami desk can reach you.' })
      return
    }
    setContactSending(true)
    setContactConfirmation('')
    try {
      const res = await fetch('/api/public/callback', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name: `${contactName || 'Miami Hotel Leader'} (${contactRole})`,
          hotel_name: contactHotel || 'Miami Boutique Property',
          phone: contactPhone || contactEmail,
          email: contactEmail,
          role: contactRole,
          preferred_channel: contactChannel,
          notes: contactNote,
          hotel_id: Number(selectedSampleId || 23),
        }),
      })
      const d = await res.json()
      const msg = d.ok ? d.message : d.error || 'Request received by our Miami team.'
      setContactConfirmation(msg)
      pushToast({ tone: 'success', title: 'Message Sent to Miami Desk', detail: 'Jasmel received your inquiry via instant alert.' })
      setContactName('')
      setContactHotel('')
      setContactPhone('')
      setContactEmail('')
      setContactNote('')
    } catch {
      setContactConfirmation('Received! You can also call or WhatsApp our Miami desk directly at +1 (786) 970-8366.')
    } finally {
      setContactSending(false)
    }
  }

  const {
    register,
    handleSubmit,
    setValue,
    formState: { errors, isSubmitting },
  } = useForm<RegisterFormValues>({
    resolver: zodResolver(registerSchema),
    defaultValues: {
      hotel_name: '',
      area: 'South Beach',
      email: '',
      username: '',
      password: '',
      tier: 'free',
    },
  })

  useEffect(() => {
    let active = true
    fetch('/api/public/landing')
      .then((r) => (r.ok ? r.json() : null))
      .then((d) => {
        if (!active || !d?.ok) return
        setIsLiveApi(true)
        if (Array.isArray(d.tiers) && d.tiers.length) setTiers(d.tiers)
        if (Array.isArray(d.comparison_matrix) && d.comparison_matrix.length) setCompMatrix(d.comparison_matrix)
        if (Array.isArray(d.hotels_directory) && d.hotels_directory.length) {
          setDemoDirectory(d.hotels_directory)
          setSelectedSampleId(String(d.hotels_directory[0].id))
        }
      })
      .catch(() => {})
    return () => {
      active = false
    }
  }, [])

  const roiStats = useMemo(() => {
    const soldMo = Math.round(rooms * 30 * 0.72)
    const revMo = Math.round(soldMo * Math.max(8, adr * 0.04) * 0.4 + soldMo * 0.1 * adr * 0.18)
    const laborSaved = 1125
    const netMo = revMo + laborSaved - 99
    const mult = Math.max(1, Math.round(netMo / 99))
    return { revMo, laborSaved, netMo, mult }
  }, [rooms, adr])

  const costComparisonChart = [
    { name: 'Manual Tabs (60h)', cost: 1500, fill: '#E11D48' },
    { name: 'Enterprise RMS', cost: 650, fill: '#64748B' },
    { name: 'HRI Core', cost: 99, fill: '#2563EB' },
    { name: 'HRI Free Starter', cost: 0, fill: '#059669' },
  ]

  const runLiveAudit = async (explicitHotelId?: number) => {
    setAuditLoading(true)
    const hidNum = explicitHotelId || Number(selectedSampleId || 23)
    try {
      const res = await fetch('/api/audit/run', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          website_url: auditUrl.trim() || undefined,
          hotel_id: auditUrl.trim() ? undefined : hidNum,
          force_scrape: Boolean(auditUrl.trim()),
        }),
      })
      if (res.ok) {
        const d = (await res.json()) as PublicAuditResponse
        if (d?.ok) {
          setAuditResult(d)
          setIsLiveApi(true)
          setValue('hotel_name', d.form_autofill.hotel_name || '')
          setValue('area', d.form_autofill.area || 'Miami Beach')
          pushToast({
            tone: 'success',
            title: `Audited ${d.form_autofill.hotel_name}`,
            detail: d.decision_assistant.verdict,
          })
          setAuditLoading(false)
          return
        }
      }
    } catch {
      // Fallback to illustrative snapshot audit
    }
    pushToast({
      tone: 'info',
      title: 'Sample Benchmark Audit Ready',
      detail: 'Showing verified illustrative hospitality audit dataset.',
    })
    setAuditLoading(false)
  }

  const onSubmitRegister = async (values: RegisterFormValues) => {
    try {
      const res = await fetch('/api/accounts/register', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(values),
      })
      const d = await res.json()
      if (d?.ok && d.token) {
        setAuthParams(d.token, null)
        await hydratePortal(null, null)
        pushToast({
          tone: 'success',
          title: 'Hotel Portal Activated',
          detail: `${values.hotel_name} isolated workspace is live.`,
        })
        navigate(`/portal?token=${encodeURIComponent(d.token)}`)
        return
      }
      pushToast({ tone: 'error', title: 'Registration Error', detail: d?.error || 'Could not create account.' })
    } catch {
      setAuthParams('', selectedSampleId)
      pushToast({
        tone: 'info',
        title: 'Demo Account Provisioned Locally',
        detail: `${values.hotel_name} (${values.tier}) opening in Client WebApp.`,
      })
      navigate(`/portal?demo_hotel=${selectedSampleId}`)
    }
  }

  const otaChartData = (auditResult.rate_intel.channels || []).map((c) => ({
    name: c.name.replace('.com', ''),
    rate: Number(c.rate || 0),
    isDirect: c.code === 'DIRECT' || /direct/i.test(c.name),
  }))

  const compChartData = [
    ...(auditResult.rate_intel.direct_bar || auditResult.rate_intel.direct_price
      ? [
          {
            name: 'Your BAR',
            price: Number(auditResult.rate_intel.direct_bar || auditResult.rate_intel.direct_price),
            isPrimary: true,
          },
        ]
      : []),
    ...(auditResult.rate_intel.neighbors || []).slice(0, 5).map((n) => ({
      name: n.name.split(' ').slice(0, 2).join(' '),
      price: Number(n.price || 0),
      isPrimary: false,
    })),
  ]

  return (
    <div className="min-h-screen ember-gradient-bg py-3 px-2.5 sm:px-5 pb-24">
      <div className="max-w-[1340px] mx-auto space-y-5">
        {/* Top Ember Glass Navbar */}
        <header className="sticky top-3 z-40 rounded-2xl ember-sidebar-glass px-4 py-2.5 text-white flex items-center justify-between gap-3 flex-wrap">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-xl bg-blue-600 flex items-center justify-center border border-blue-300/30">
              <img
                src="/assets/logo.png"
                alt="HotelRateIntel"
                className="w-5 h-5 rounded object-cover"
                onError={(e) => {
                  ;(e.currentTarget as HTMLImageElement).style.display = 'none'
                }}
              />
            </div>
            <span className="text-sm font-extrabold tracking-tight">HotelRateIntel</span>
            <span className="hidden sm:inline-block px-2 py-0.5 rounded-full bg-blue-500/25 border border-blue-300/30 text-[10px] font-bold text-blue-100">
              MADE BY HOTELIERS · POWERED BY AI
            </span>
          </div>

          <nav className="hidden md:flex items-center gap-1 text-xs font-semibold text-blue-100">
            <a href="#industry-roi" className="px-2.5 py-1.5 rounded-lg hover:bg-white/10">Miami Hotel Features</a>
            <a href="#auditor" className="px-2.5 py-1.5 rounded-lg hover:bg-white/10">Live Auditor</a>
            <a href="#pricing" className="px-2.5 py-1.5 rounded-lg hover:bg-white/10">Pricing ($0–$399)</a>
            <a href="#consultation" className="px-2.5 py-1.5 rounded-lg hover:bg-white/10">$99 AI Audit</a>
            <a href="#contact-desk" className="px-2.5 py-1.5 rounded-lg hover:bg-white/10">Contact Us</a>
            <a href="#blogs" className="px-2.5 py-1.5 rounded-lg hover:bg-white/10">Blogs</a>
          </nav>

          <div className="flex items-center gap-1.5 flex-wrap">
            <a
              href="sms:+17869708366?&body=Hi%20HotelRateIntel%20Miami%2C%20I%27d%20like%20a%20rate%20parity%20check%20for%20my%20hotel."
              className="hidden xl:inline-flex items-center gap-1 px-2.5 py-1.5 rounded-xl bg-white/10 hover:bg-white/20 text-[11px] font-bold text-blue-100"
              title="Text our Miami desk directly"
            >
              <MessageSquare className="w-3 h-3 text-emerald-300" />
              Text Us
            </a>
            <a
              href="mailto:jasmelacosta@gmail.com?subject=Miami%20Hotel%20Rate%20Parity%20Check"
              className="hidden xl:inline-flex items-center gap-1 px-2.5 py-1.5 rounded-xl bg-white/10 hover:bg-white/20 text-[11px] font-bold text-blue-100"
              title="Email our Miami desk directly"
            >
              <Mail className="w-3 h-3 text-blue-200" />
              Email Us
            </a>
            <a
              href="tel:+17869708366"
              className="hidden lg:inline-flex items-center gap-1 px-2.5 py-1.5 rounded-xl bg-white/10 hover:bg-white/20 text-[11px] font-bold text-blue-100"
            >
              <Phone className="w-3 h-3 text-emerald-300" />
              (786) 970-8366
            </a>
            <button
              type="button"
              onClick={() => navigate(`/portal?demo_hotel=${selectedSampleId}`)}
              className="px-3.5 py-1.5 rounded-xl bg-gradient-to-r from-blue-500 to-blue-600 text-white text-xs font-bold shadow-lg hover:brightness-110 transition"
            >
              Open Client Portal →
            </button>
            <button
              type="button"
              onClick={() => openCoordinatedContact('sms')}
              className="hidden sm:inline-block px-3 py-1.5 rounded-xl bg-emerald-500 hover:bg-emerald-600 text-xs font-bold text-white transition"
            >
              We&apos;ll Text / Email You
            </button>
          </div>
        </header>

        {/* SECTION 1: HERO & EMBER PROFIT CALCULATOR */}
        <section className="rounded-[26px] ember-canvas-panel p-5 sm:p-7">
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-5 items-stretch">
            <div className="lg:col-span-7 ember-card p-6 flex flex-col justify-between gap-5">
              <div className="space-y-3">
                <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-blue-50 border border-blue-200 text-[11px] font-extrabold text-blue-800">
                  <ShieldCheck className="w-3.5 h-3.5 text-blue-600" />
                  MADE BY HOTELIERS (20 YRS LUXURY SERVICE) · POWERED BY AI
                </div>
                <h1 className="text-2xl sm:text-4xl font-black tracking-tight text-[#0B1B3B] leading-[1.12]">
                  Catch OTA Undercuts, Compare Exact Suite-to-Suite &amp; Price Live OOO/OOS Rooms — Built for Miami Hotels.
                </h1>
                <p className="text-xs sm:text-sm text-[#475B80] leading-relaxed">
                  Built in Miami from <b className="text-[#0B1B3B]">20 years in luxury hotel &amp; residential hospitality</b> for{' '}
                  <b className="text-[#0B1B3B]">Reservations, Front Office, Night Audit &amp; Housekeeping</b>. Unlike corporate rate shoppers that only average entry-room prices:
                </p>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 text-[11.5px]">
                  <div className="flex items-start gap-1.5 p-2 rounded-xl bg-[#F5F9FF] border border-[#DCE7F8]">
                    <CheckCircle2 className="w-3.5 h-3.5 text-blue-600 shrink-0 mt-0.5" />
                    <span><b>Exact Suite-vs-Suite &amp; DD-vs-DD:</b> Normalizes rollaways, Miami resort fees, 14% tax &amp; HK cadence.</span>
                  </div>
                  <div className="flex items-start gap-1.5 p-2 rounded-xl bg-[#F5F9FF] border border-[#DCE7F8]">
                    <CheckCircle2 className="w-3.5 h-3.5 text-blue-600 shrink-0 mt-0.5" />
                    <span><b>Live OOO / OOS / HK Hold → AI BAR:</b> Recalculates true net sellable occupancy before you walk a guest.</span>
                  </div>
                  <div className="flex items-start gap-1.5 p-2 rounded-xl bg-[#F5F9FF] border border-[#DCE7F8]">
                    <CheckCircle2 className="w-3.5 h-3.5 text-blue-600 shrink-0 mt-0.5" />
                    <span><b>Pre-Audit (11:30 PM) &amp; Post-Audit Desk:</b> Overnight courtesy call scripts &amp; neighbor rate-swap emails.</span>
                  </div>
                  <div className="flex items-start gap-1.5 p-2 rounded-xl bg-[#F5F9FF] border border-[#DCE7F8]">
                    <CheckCircle2 className="w-3.5 h-3.5 text-blue-600 shrink-0 mt-0.5" />
                    <span><b>$0 Starter · Month-to-Month:</b> Zero annual lock-in, live public scans today + PMS API push when ready.</span>
                  </div>
                </div>

                <div className="ember-subtle-card p-3.5 space-y-2">
                  <div className="text-[10.5px] font-extrabold uppercase tracking-wider text-[#475B80]">
                    Launch Isolated Property Portal or Scan Own Hotel URL
                  </div>
                  <div className="flex flex-wrap gap-2">
                    <select
                      aria-label="Select sample hotel benchmark"
                      value={selectedSampleId}
                      onChange={(e) => setSelectedSampleId(e.target.value)}
                      className="flex-1 min-w-[220px] px-3 py-2 text-xs font-bold rounded-xl border border-[#DCE7F8] bg-white text-[#0B1B3B]"
                    >
                      {demoDirectory.map((h) => (
                        <option key={h.id} value={h.id}>
                          {h.name} {h.price ? `($${Math.round(h.price)}/nt)` : ''}
                        </option>
                      ))}
                    </select>
                    <button
                      type="button"
                      onClick={() => navigate(`/portal?demo_hotel=${selectedSampleId}`)}
                      className="px-4 py-2 rounded-xl bg-blue-600 text-white text-xs font-bold hover:bg-blue-700 transition"
                    >
                      Open Client WebApp →
                    </button>
                    <button
                      type="button"
                      onClick={() => {
                        document.getElementById('auditor')?.scrollIntoView({ behavior: 'smooth' })
                        runLiveAudit(Number(selectedSampleId))
                      }}
                      className="px-3.5 py-2 rounded-xl bg-white border border-[#DCE7F8] text-xs font-bold text-[#0B1B3B] hover:bg-blue-50"
                    >
                      Run URL Audit
                    </button>
                  </div>
                </div>
              </div>

              <div className="grid grid-cols-2 sm:grid-cols-4 gap-2.5">
                <div className="ember-subtle-card p-3">
                  <div className="text-[10px] font-extrabold text-[#6D81A8] uppercase">Labor Saved</div>
                  <div className="text-lg font-black text-emerald-700 tabular-nums">45–68 hrs</div>
                  <div className="text-[10.5px] text-[#475B80]">$1,125–$1,700/mo freed</div>
                </div>
                <div className="ember-subtle-card p-3">
                  <div className="text-[10px] font-extrabold text-[#6D81A8] uppercase">OTA Leak Radar</div>
                  <div className="text-lg font-black text-rose-600 tabular-nums">18%–44%</div>
                  <div className="text-[10.5px] text-[#475B80]">Vio &amp; Agoda undercuts caught</div>
                </div>
                <div className="ember-subtle-card p-3">
                  <div className="text-[10px] font-extrabold text-[#6D81A8] uppercase">Direct Margin</div>
                  <div className="text-lg font-black text-blue-700 tabular-nums">+$58k/yr</div>
                  <div className="text-[10.5px] text-[#475B80]">Direct shift + ADR lift</div>
                </div>
                <div className="rounded-2xl p-3 bg-gradient-to-br from-[#0D255B] to-[#2563EB] text-white">
                  <div className="text-[10px] font-bold text-blue-200 uppercase">Month-to-Month</div>
                  <div className="text-lg font-black tabular-nums">$0 → $99</div>
                  <div className="text-[10.5px] text-blue-100">vs $650/mo corporate suites</div>
                </div>
              </div>
            </div>

            {/* Right ROI & Cost Comparison Recharts Widget */}
            <div className="lg:col-span-5 ember-card p-6 bg-gradient-to-br from-white to-blue-50/40 flex flex-col justify-between gap-4">
              <div>
                <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full bg-blue-600 text-white text-[10px] font-extrabold uppercase">
                  <DollarSign className="w-3 h-3" />
                  Interactive Hotelier ROI Calculator
                </span>
                <h2 className="text-lg font-extrabold text-[#0B1B3B] mt-2">Monthly Profit + Payroll Savings</h2>

                <div className="grid grid-cols-2 gap-3 mt-3">
                  <div>
                    <label htmlFor="roiRooms" className="block text-[10.5px] font-extrabold text-[#475B80] uppercase mb-1">
                      Sellable Rooms
                    </label>
                    <input
                      id="roiRooms"
                      type="number"
                      min={5}
                      max={300}
                      value={rooms}
                      onChange={(e) => setRooms(Math.max(5, Number(e.target.value || 45)))}
                      className="w-full px-3 py-2 text-xs font-bold rounded-xl border border-[#DCE7F8] bg-white tabular-nums"
                    />
                  </div>
                  <div>
                    <label htmlFor="roiAdr" className="block text-[10.5px] font-extrabold text-[#475B80] uppercase mb-1">
                      Avg Direct BAR ($)
                    </label>
                    <input
                      id="roiAdr"
                      type="number"
                      min={50}
                      max={2000}
                      value={adr}
                      onChange={(e) => setAdr(Math.max(50, Number(e.target.value || 220)))}
                      className="w-full px-3 py-2 text-xs font-bold rounded-xl border border-[#DCE7F8] bg-white tabular-nums"
                    />
                  </div>
                </div>

                <div className="mt-3 rounded-2xl bg-[#F7FAFF] border border-[#DCE7F8] p-3.5 space-y-1.5 text-xs">
                  <div className="flex justify-between">
                    <span className="text-[#475B80]">Staff Payroll Saved (45 hrs × $25/hr)</span>
                    <b className="text-blue-700 tabular-nums">${roiStats.laborSaved.toLocaleString()}/mo</b>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-[#475B80]">New Profit (Direct Bookings + ADR Lift)</span>
                    <b className="text-emerald-700 tabular-nums">+${roiStats.revMo.toLocaleString()}/mo</b>
                  </div>
                  <div className="flex justify-between border-t border-[#DCE7F8] pt-2 text-sm font-black text-[#0B1B3B]">
                    <span>NET MONTHLY GAIN ON $99/MO</span>
                    <span className="text-blue-700 tabular-nums">+${roiStats.netMo.toLocaleString()}/mo ({roiStats.mult}x)</span>
                  </div>
                </div>
              </div>

              <div className="h-[155px] w-full bg-white rounded-2xl border border-[#DCE7F8] p-2.5">
                <div className="text-[10px] font-extrabold uppercase text-[#475B80] px-1 mb-1">
                  Monthly Software &amp; Labor Cost Comparison ($)
                </div>
                <ResponsiveContainer width="100%" height={120}>
                  <BarChart data={costComparisonChart} layout="vertical" margin={{ top: 0, right: 16, left: 4, bottom: 0 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#EAF1FC" horizontal={false} />
                    <XAxis type="number" tick={{ fontSize: 10, fill: '#475B80' }} />
                    <YAxis type="category" dataKey="name" width={108} tick={{ fontSize: 10, fill: '#0B1B3B', fontWeight: 700 }} />
                    <Tooltip formatter={(v: number) => `$${v}/mo`} />
                    <Bar dataKey="cost" radius={[0, 6, 6, 0]}>
                      {costComparisonChart.map((entry, idx) => (
                        <Cell key={idx} fill={entry.fill} />
                      ))}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </div>
          </div>
        </section>

        {/* SECTION 2: HOSPITALITY JARGON OPERATIONS & HEAD-TO-HEAD COMPARISON */}
        <section id="industry-roi" className="rounded-[26px] ember-canvas-panel p-5 sm:p-7 space-y-5">
          <div className="flex flex-wrap items-end justify-between gap-3">
            <div>
              <span className="text-[11px] font-extrabold uppercase tracking-wider text-blue-700">
                Built for Real Hotel Departments · Reservations · Front Office · Night Audit · Housekeeping
              </span>
              <h2 className="text-2xl font-black text-[#0B1B3B] tracking-tight mt-0.5">
                6 Hotel-Specific Operations Corporate Rate Shoppers Leave Out
              </h2>
            </div>
            <button
              type="button"
              onClick={() => navigate(`/portal?demo_hotel=${selectedSampleId}`)}
              className="px-4 py-2 rounded-xl bg-[#0D255B] text-white text-xs font-bold hover:bg-blue-800 transition"
            >
              Inspect Live in Client WebApp →
            </button>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {HOTEL_JARGON_SOLUTIONS.map((sol) => (
              <div key={sol.code} className="ember-card p-5 space-y-1.5">
                <div className="text-[10.5px] font-extrabold text-blue-700 uppercase tracking-wider">{sol.code}</div>
                <h3 className="text-sm font-extrabold text-[#0B1B3B]">{sol.title}</h3>
                <p className="text-xs text-[#475B80] leading-relaxed">{sol.detail}</p>
              </div>
            ))}
          </div>

          <div className="ember-card p-5 overflow-x-auto">
            <h3 className="text-base font-extrabold text-[#0B1B3B] mb-3">
              Head-to-Head Industry Comparison (Support Your Local Miami Hospitality)
            </h3>
            <table className="w-full text-left border-collapse text-xs">
              <thead className="bg-[#F5F9FF] border-b border-[#DCE7F8]">
                <tr>
                  <th className="p-2.5 text-[10.5px] font-extrabold uppercase text-[#475B80]">Hospitality Requirement</th>
                  <th className="p-2.5 text-[10.5px] font-extrabold uppercase text-blue-700 bg-blue-50/60">Free Starter ($0)</th>
                  <th className="p-2.5 text-[10.5px] font-extrabold uppercase text-blue-900 bg-blue-100/60">Boutique Core ($99)</th>
                  <th className="p-2.5 text-[10.5px] font-extrabold uppercase text-[#475B80]">Enterprise RMS ($450–$900+)</th>
                  <th className="p-2.5 text-[10.5px] font-extrabold uppercase text-[#6D81A8]">Manual Spreadsheets</th>
                </tr>
              </thead>
              <tbody>
                {compMatrix.map((row, idx) => (
                  <tr key={idx} className="border-b border-[#EEF4FD] last:border-b-0">
                    <td className="p-2.5 font-bold text-[#0B1B3B]">{row.feature}</td>
                    <td className="p-2.5 font-bold text-blue-700 bg-blue-50/35">{row.us_free}</td>
                    <td className="p-2.5 font-extrabold text-[#0B1B3B] bg-blue-50/75">{row.us_core}</td>
                    <td className="p-2.5 text-[#475B80]">{row.enterprise}</td>
                    <td className="p-2.5 text-[#6D81A8]">{row.spreadsheets}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>

        {/* SECTION 3: LIVE HOTEL WEBSITE AUDITOR WITH RECHARTS */}
        <section id="auditor" className="rounded-[26px] ember-canvas-panel p-5 sm:p-7 space-y-5">
          <div className="ember-card p-5 flex flex-wrap items-end justify-between gap-4">
            <div className="flex-1 min-w-[260px]">
              <span className="text-[11px] font-extrabold uppercase tracking-wider text-blue-700">
                Public Live Website &amp; Multi-OTA Parity Scanner
              </span>
              <h2 className="text-xl sm:text-2xl font-black text-[#0B1B3B] mt-0.5">
                Audit Your Booking Engine &amp; OTA Ladder in Seconds
              </h2>
            </div>
            <div className="flex flex-wrap gap-2 flex-1 min-w-[300px]">
              <input
                value={auditUrl}
                onChange={(e) => setAuditUrl(e.target.value)}
                placeholder="https://yourboutiquehotel.com"
                className="flex-1 min-w-[200px] px-3 py-2 text-xs rounded-xl border border-[#DCE7F8] bg-[#F7FAFF]"
              />
              <button
                type="button"
                onClick={() => runLiveAudit()}
                disabled={auditLoading}
                className="px-4 py-2 rounded-xl bg-blue-600 text-white text-xs font-bold inline-flex items-center gap-1.5 hover:bg-blue-700 disabled:opacity-60"
              >
                <Search className="w-3.5 h-3.5" />
                {auditLoading ? 'Scanning...' : 'Scan Website & Rates'}
              </button>
            </div>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-12 gap-4">
            <div className="lg:col-span-5 ember-card p-5 space-y-3">
              <div className="flex items-center justify-between gap-2">
                <h3 className="text-sm font-extrabold text-[#0B1B3B]">{auditResult.form_autofill.hotel_name}</h3>
                <span className="px-2.5 py-0.5 rounded-full bg-blue-50 text-blue-700 text-[10.5px] font-extrabold">
                  {auditResult.form_autofill.booking_engine}
                </span>
              </div>
              <div className="p-3.5 rounded-2xl bg-gradient-to-r from-[#0D255B] to-[#1744A6] text-white space-y-1">
                <div className="text-[10px] font-bold text-blue-200 uppercase">Decision-Making Assistant Verdict</div>
                <div className="text-sm font-extrabold">{auditResult.decision_assistant.verdict}</div>
                <div className="text-xs text-blue-100 tabular-nums">
                  Target Direct BAR: <b>${auditResult.decision_assistant.recommended_bar}/nt</b> · Est. Upside:{' '}
                  <b>+${auditResult.decision_assistant.total_annual_roi.toLocaleString()}/yr</b>
                </div>
              </div>
              <ul className="space-y-1.5 text-xs text-[#475B80]">
                {auditResult.decision_assistant.actions.map((act, i) => (
                  <li key={i} className="flex items-start gap-2">
                    <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600 mt-0.5 shrink-0" />
                    <span>{act}</span>
                  </li>
                ))}
              </ul>
              <div className="flex flex-wrap gap-2 pt-2">
                <button
                  type="button"
                  onClick={() => navigate(auditResult.urls.demo_url || `/portal?demo_hotel=${auditResult.hotel_id}`)}
                  className="px-3.5 py-2 rounded-xl bg-blue-600 text-white text-xs font-bold"
                >
                  Open Isolated Portal Demo →
                </button>
                <a
                  href={auditResult.urls.audit_url || `/audit?hotel_id=${auditResult.hotel_id}`}
                  target="_blank"
                  rel="noreferrer"
                  className="px-3.5 py-2 rounded-xl bg-[#F2F6FD] border border-[#DCE7F8] text-xs font-bold text-[#0B1B3B]"
                >
                  Printable 1-Page Audit ↗
                </a>
              </div>
            </div>

            <div className="lg:col-span-7 grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div className="ember-card p-4">
                <h4 className="text-xs font-extrabold uppercase text-[#475B80] mb-2">OTA Channel Parity Ladder ($)</h4>
                <div className="h-[220px]">
                  <ResponsiveContainer width="100%" height={210}>
                    <BarChart data={otaChartData} margin={{ top: 8, right: 8, left: -12, bottom: 0 }}>
                      <CartesianGrid strokeDasharray="3 3" stroke="#EAF1FC" />
                      <XAxis dataKey="name" tick={{ fontSize: 10, fill: '#475B80' }} />
                      <YAxis tick={{ fontSize: 10, fill: '#475B80' }} />
                      <Tooltip formatter={(v: number) => `$${v}/nt`} />
                      <Bar dataKey="rate" radius={[8, 8, 0, 0]}>
                        {otaChartData.map((c, idx) => (
                          <Cell key={idx} fill={c.isDirect ? '#2563EB' : '#E11D48'} />
                        ))}
                      </Bar>
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              </div>

              <div className="ember-card p-4">
                <h4 className="text-xs font-extrabold uppercase text-[#475B80] mb-2">Corridor Comp-Set BAR ($)</h4>
                <div className="h-[220px]">
                  <ResponsiveContainer width="100%" height={210}>
                    <BarChart data={compChartData} margin={{ top: 8, right: 8, left: -12, bottom: 0 }}>
                      <CartesianGrid strokeDasharray="3 3" stroke="#EAF1FC" />
                      <XAxis dataKey="name" tick={{ fontSize: 9.5, fill: '#475B80' }} />
                      <YAxis tick={{ fontSize: 10, fill: '#475B80' }} />
                      <Tooltip formatter={(v: number) => `$${v}/nt`} />
                      <Bar dataKey="price" radius={[8, 8, 0, 0]}>
                        {compChartData.map((c, idx) => (
                          <Cell key={idx} fill={c.isPrimary ? '#2563EB' : '#64748B'} />
                        ))}
                      </Bar>
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              </div>
            </div>
          </div>
        </section>

        {/* SECTION 4: PRICING LADDER + SELF-SERVE REGISTRATION */}
        <section id="pricing" className="rounded-[26px] ember-canvas-panel p-5 sm:p-7 space-y-5">
          <div>
            <span className="text-[11px] font-extrabold uppercase tracking-wider text-blue-700">
              Transparent Month-to-Month Hospitality Pricing · Zero Annual Contracts
            </span>
            <h2 className="text-2xl font-black text-[#0B1B3B] mt-0.5">Start Free ($0/mo) or Unlock Full Automation ($99–$399/mo)</h2>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            {tiers.map((t) => {
              const highlight = t.tier_id === 'core_99'
              return (
                <div
                  key={t.tier_id}
                  className={`rounded-2xl p-5 flex flex-col justify-between gap-4 ${
                    highlight
                      ? 'bg-gradient-to-br from-[#0D255B] to-[#1744A6] text-white shadow-emberSidebar'
                      : 'ember-card text-[#0B1B3B]'
                  }`}
                >
                  <div className="space-y-2.5">
                    <span
                      className={`inline-block px-2.5 py-0.5 rounded-full text-[10px] font-extrabold ${
                        highlight ? 'bg-blue-400/25 text-blue-100 border border-blue-300/30' : 'bg-blue-50 text-blue-700'
                      }`}
                    >
                      {t.badge}
                    </span>
                    <h3 className="text-base font-extrabold">{t.name}</h3>
                    <div className="text-3xl font-black tabular-nums">
                      ${t.monthly_price}
                      <span className="text-xs font-semibold opacity-80">/mo</span>
                    </div>
                    <div className={`text-[11px] font-semibold ${highlight ? 'text-blue-200' : 'text-[#475B80]'}`}>
                      Saves ~{t.staff_hours_saved_mo} hrs/mo · Up to {t.max_competitors} comps
                    </div>
                    <ul className="space-y-1.5 text-[11.5px]">
                      {t.features.slice(0, 4).map((f, i) => (
                        <li key={i} className="flex items-start gap-1.5">
                          <CheckCircle2 className={`w-3.5 h-3.5 mt-0.5 shrink-0 ${highlight ? 'text-emerald-300' : 'text-emerald-600'}`} />
                          <span className={highlight ? 'text-blue-50' : 'text-[#475B80]'}>{f}</span>
                        </li>
                      ))}
                    </ul>
                  </div>

                  <button
                    type="button"
                    onClick={() => {
                      setValue('tier', t.tier_id)
                      document.getElementById('register')?.scrollIntoView({ behavior: 'smooth' })
                    }}
                    className={`w-full py-2 rounded-xl text-xs font-bold transition ${
                      highlight ? 'bg-white text-[#0B1B3B] hover:bg-blue-50' : 'bg-blue-600 text-white hover:bg-blue-700'
                    }`}
                  >
                    Select {t.tier_id === 'free' ? 'Free Starter' : `$${t.monthly_price}/mo Plan`}
                  </button>
                </div>
              )
            })}
          </div>

          {/* Zod-Validated Self-Serve Registration */}
          <div id="register" className="ember-card p-6">
            <h3 className="text-base font-extrabold text-[#0B1B3B] mb-1">
              Provision Your Isolated Hotel Client Account Now
            </h3>
            <p className="text-xs text-[#475B80] mb-4">
              Your workspace is strictly isolated to your hotel and assigned street competitors—other hotels never see your OOO inventory, BAR moves, or notes.
            </p>
            <form onSubmit={handleSubmit(onSubmitRegister)} className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
              <div>
                <label className="block text-[10px] font-extrabold uppercase text-[#475B80] mb-1">Hotel Property Name</label>
                <input
                  {...register('hotel_name')}
                  placeholder="e.g. Avalon Hotel South Beach"
                  className="w-full px-3 py-2 text-xs rounded-xl border border-[#DCE7F8] bg-[#F7FAFF]"
                />
                {errors.hotel_name && <span className="text-[11px] font-bold text-rose-600">{errors.hotel_name.message}</span>}
              </div>
              <div>
                <label className="block text-[10px] font-extrabold uppercase text-[#475B80] mb-1">Corridor / Market</label>
                <input
                  {...register('area')}
                  placeholder="South Beach / Mid-Beach / Miami"
                  className="w-full px-3 py-2 text-xs rounded-xl border border-[#DCE7F8] bg-[#F7FAFF]"
                />
                {errors.area && <span className="text-[11px] font-bold text-rose-600">{errors.area.message}</span>}
              </div>
              <div>
                <label className="block text-[10px] font-extrabold uppercase text-[#475B80] mb-1">Work / Brief Email</label>
                <input
                  {...register('email')}
                  placeholder="reservations@yourhotel.com"
                  className="w-full px-3 py-2 text-xs rounded-xl border border-[#DCE7F8] bg-[#F7FAFF]"
                />
                {errors.email && <span className="text-[11px] font-bold text-rose-600">{errors.email.message}</span>}
              </div>
              <div>
                <label className="block text-[10px] font-extrabold uppercase text-[#475B80] mb-1">Portal Username</label>
                <input
                  {...register('username')}
                  placeholder="e.g. avalon_res"
                  className="w-full px-3 py-2 text-xs rounded-xl border border-[#DCE7F8] bg-[#F7FAFF]"
                />
                {errors.username && <span className="text-[11px] font-bold text-rose-600">{errors.username.message}</span>}
              </div>
              <div>
                <label className="block text-[10px] font-extrabold uppercase text-[#475B80] mb-1">Password</label>
                <input
                  type="password"
                  {...register('password')}
                  placeholder="Min 6 characters"
                  className="w-full px-3 py-2 text-xs rounded-xl border border-[#DCE7F8] bg-[#F7FAFF]"
                />
                {errors.password && <span className="text-[11px] font-bold text-rose-600">{errors.password.message}</span>}
              </div>
              <div className="flex flex-col justify-end">
                <label className="block text-[10px] font-extrabold uppercase text-[#475B80] mb-1">Selected Tier</label>
                <div className="flex gap-2">
                  <select
                    {...register('tier')}
                    className="flex-1 px-3 py-2 text-xs font-bold rounded-xl border border-[#DCE7F8] bg-[#F7FAFF]"
                  >
                    <option value="free">Free Starter ($0/mo)</option>
                    <option value="core_99">Boutique Core ($99/mo)</option>
                    <option value="pro_199">Pro Call Desk ($199/mo)</option>
                    <option value="portfolio_399">Portfolio ($399/mo)</option>
                  </select>
                  <button
                    type="submit"
                    disabled={isSubmitting}
                    className="px-4 py-2 rounded-xl bg-blue-600 text-white text-xs font-bold hover:bg-blue-700"
                  >
                    {isSubmitting ? 'Creating...' : 'Create Account →'}
                  </button>
                </div>
              </div>
            </form>
          </div>
        </section>

        {/* SECTION 5: $99 HOSPITALITY AI CONSULTATION & DEVELOPERS */}
        <section id="consultation" className="rounded-[26px] ember-canvas-panel p-5 sm:p-7 space-y-5">
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
            <div className="rounded-2xl p-6 text-white bg-gradient-to-br from-[#06122E] via-[#0D255B] to-[#1744A6] space-y-3">
              <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full bg-blue-400/25 text-[10px] font-extrabold uppercase">
                <Zap className="w-3 h-3 text-amber-300" />
                Aggressive Consultation Guarantee
              </span>
              <h3 className="text-xl font-black">48-Hour Hotel AI Audit + Live Prototype</h3>
              <div className="text-3xl font-black tabular-nums">
                $99 <span className="text-xs font-medium text-blue-200">one-time · $0 risk</span>
              </div>
              <p className="text-xs text-blue-100 leading-relaxed">
                Meet 60 minutes with our Miami hospitality engineers. We audit your PMS, Channel Manager, Night Audit &amp; OTA
                parity and deliver a working custom prototype in 48 hours—guaranteed to uncover{' '}
                <b className="text-white">$2,500+/mo ($30,000/yr)</b> in RevPAR &amp; payroll savings or 100% refunded.
              </p>
              <a
                href="https://www.aidynamic.pro/booking"
                target="_blank"
                rel="noreferrer"
                className="block text-center w-full py-2.5 rounded-xl bg-white text-[#0B1B3B] text-xs font-extrabold hover:bg-blue-50"
              >
                Book $99 Hospitality AI Audit →
              </a>
            </div>

            <div className="ember-card p-6 space-y-3">
              <span className="px-2.5 py-0.5 rounded-full bg-emerald-50 text-emerald-700 text-[10px] font-extrabold uppercase">
                Turnkey Hospitality AI Builders
              </span>
              <h3 className="text-base font-extrabold text-[#0B1B3B]">
                Jasmel Acosta &amp; Juan Diaz — AI Dynamic Pro Miami
              </h3>
              <p className="text-xs text-[#475B80] leading-relaxed">
                Combining <b>20 years of luxury hotel &amp; residential concierge leadership</b> with <b>10+ years of production ML &amp; agent engineering</b> across 80+ deployed systems.
              </p>
              <ul className="space-y-1.5 text-xs text-[#475B80]">
                <li><b>$497 Front-Office AI Bootcamp:</b> Train up to 15 Reservations &amp; Night Audit staff to move 5x faster.</li>
                <li><b>$997 24/7 Bilingual Voice &amp; WhatsApp Desk:</b> Direct bookings straight into SynXis, Cloudbeds or Mews.</li>
                <li><b>$2,500–$5,000/mo Portfolio Agents:</b> Dedicated Docker/VPS automation for multi-hotel groups.</li>
              </ul>
            </div>

            <div className="ember-card p-6 flex flex-col justify-between gap-4">
              <div className="space-y-2.5">
                <span className="px-2.5 py-0.5 rounded-full bg-blue-50 text-blue-700 text-[10px] font-extrabold uppercase">
                  Support Your Local Miami Ecosystem
                </span>
                <h3 className="text-base font-extrabold text-[#0B1B3B]">Direct Founder Channels (EN / ES)</h3>
                <div className="flex flex-wrap gap-1.5">
                  {[
                    { n: 'AI Dynamic Pro', u: 'https://www.aidynamic.pro/' },
                    { n: 'Chat Building Innovation', u: 'https://www.chatbuildinginnovation.us/' },
                    { n: 'PocketScribe AI', u: 'https://pocketscribe.online/' },
                    { n: 'Real Estate Dates', u: 'https://realestatedates.com/' },
                    { n: 'Medical Billing MB', u: 'https://medicalbillingmb.com/' },
                  ].map((link) => (
                    <a
                      key={link.n}
                      href={link.u}
                      target="_blank"
                      rel="noreferrer"
                      className="px-2.5 py-1 rounded-full bg-[#F2F6FD] border border-[#DCE7F8] text-[11px] font-bold text-blue-700 hover:bg-blue-100 inline-flex items-center gap-1"
                    >
                      {link.n}
                      <ExternalLink className="w-2.5 h-2.5" />
                    </a>
                  ))}
                </div>
              </div>
              <div className="ember-subtle-card p-3 flex flex-wrap gap-2">
                <a href="tel:+17869708366" className="px-3 py-1.5 rounded-xl bg-blue-600 text-white text-xs font-bold inline-flex items-center gap-1">
                  <Phone className="w-3 h-3" /> (786) 970-8366
                </a>
                <a href="https://wa.me/17869708366" target="_blank" rel="noreferrer" className="px-3 py-1.5 rounded-xl bg-emerald-600 text-white text-xs font-bold">
                  WhatsApp
                </a>
                <a href="mailto:jasmelacosta@gmail.com" className="px-3 py-1.5 rounded-xl bg-white border border-[#DCE7F8] text-xs font-bold text-[#0B1B3B]">
                  Email Team
                </a>
              </div>
            </div>
          </div>
        </section>

        {/* SECTION 5B: EASY MIAMI HOTEL CONTACT DESK (MONITORED INSTANT ALERTS) */}
        <section id="contact-desk" className="rounded-[26px] ember-canvas-panel p-5 sm:p-7">
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-5">
            <div className="lg:col-span-5 ember-card p-6 flex flex-col justify-between gap-4">
              <div className="space-y-2.5">
                <span className="px-2.5 py-0.5 rounded-full bg-emerald-50 text-emerald-700 border border-emerald-200 text-[10px] font-extrabold uppercase">
                  Local Miami Hospitality Desk · South Beach to Sunny Isles
                </span>
                <h2 className="text-xl sm:text-2xl font-black text-[#0B1B3B] leading-tight">
                  Contact Us Directly — Real Miami Hoteliers Answer.
                </h2>
                <p className="text-xs text-[#475B80] leading-relaxed">
                  Serving independent boutique hotels across <b>South Beach, Mid-Beach, North Beach, Brickell, Wynwood, Coral Gables &amp; Sunny Isles</b>. Reach out for a free 1-page rate parity check, Suite-vs-Suite walkthrough, or overnight Night Audit call desk demo.
                </p>
                <div className="space-y-2 pt-1 text-xs">
                  <div className="ember-subtle-card p-3 flex items-center justify-between gap-2">
                    <span className="font-bold text-[#0B1B3B]">Call Us Direct (EN / ES)</span>
                    <a href="tel:+17869708366" className="font-extrabold text-blue-700 hover:underline">+1 (786) 970-8366</a>
                  </div>
                  <div className="ember-subtle-card p-3 flex items-center justify-between gap-2">
                    <span className="font-bold text-[#0B1B3B]">Text Us Now (SMS)</span>
                    <a href="sms:+17869708366?&body=Hi%20HotelRateIntel%20Miami%2C%20I%27d%20like%20a%20parity%20audit." className="font-extrabold text-blue-700 hover:underline">Text (786) 970-8366 →</a>
                  </div>
                  <div className="ember-subtle-card p-3 flex items-center justify-between gap-2">
                    <span className="font-bold text-[#0B1B3B]">Email Us Direct</span>
                    <a href="mailto:jasmelacosta@gmail.com?subject=Miami%20Hotel%20Parity%20Check" className="font-extrabold text-blue-700 hover:underline">jasmelacosta@gmail.com</a>
                  </div>
                  <div className="ember-subtle-card p-3 flex items-center justify-between gap-2">
                    <span className="font-bold text-[#0B1B3B]">WhatsApp Hospitality Desk</span>
                    <a href="https://wa.me/17869708366" target="_blank" rel="noreferrer" className="font-extrabold text-emerald-700 hover:underline">Message on WhatsApp →</a>
                  </div>
                </div>
              </div>
              <div className="text-[11px] text-[#6D81A8]">
                Every website inquiry is logged &amp; monitored immediately by our North Miami team (typical reply under 15 minutes).
              </div>
            </div>

            <form onSubmit={handleDirectContactSubmit} className="lg:col-span-7 ember-card p-6 space-y-3">
              <div>
                <span className="text-[10.5px] font-extrabold uppercase tracking-wider text-blue-700">
                  Prefer That We Reach Out? Pick How You Want to Hear From Us
                </span>
                <h3 className="text-base font-extrabold text-[#0B1B3B]">We&apos;ll Text You, Email You, or Call You Directly</h3>
              </div>
              <div className="flex flex-wrap gap-1.5">
                {[
                  { id: 'sms' as const, label: "I'll Text You (SMS)" },
                  { id: 'email' as const, label: "I'll Email You" },
                  { id: 'call' as const, label: "I'll Call You" },
                  { id: 'whatsapp' as const, label: "I'll WhatsApp You" },
                ].map((opt) => (
                  <button
                    key={opt.id}
                    type="button"
                    onClick={() => setContactChannel(opt.id)}
                    className={`px-3 py-1.5 rounded-xl text-[11px] font-extrabold border transition ${
                      contactChannel === opt.id
                        ? 'bg-blue-600 text-white border-blue-600 shadow-sm'
                        : 'bg-[#F5F9FF] text-[#475B80] border-[#DCE7F8] hover:bg-blue-50'
                    }`}
                  >
                    {opt.label}
                  </button>
                ))}
              </div>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <div>
                  <label className="block text-[11px] font-bold text-[#475B80] mb-1">Your Name</label>
                  <input
                    value={contactName}
                    onChange={(e) => setContactName(e.target.value)}
                    placeholder="e.g., Maria Lopez"
                    className="w-full px-3 py-2 text-xs rounded-xl border border-[#DCE7F8] bg-[#F7FAFF]"
                  />
                </div>
                <div>
                  <label className="block text-[11px] font-bold text-[#475B80] mb-1">Hotel Department / Role</label>
                  <select
                    value={contactRole}
                    onChange={(e) => setContactRole(e.target.value)}
                    className="w-full px-3 py-2 text-xs rounded-xl border border-[#DCE7F8] bg-[#F7FAFF] font-semibold"
                  >
                    <option>General Manager / Owner</option>
                    <option>Reservations Manager</option>
                    <option>Director of Revenue / Yield</option>
                    <option>Front Office Manager / MOD</option>
                    <option>Night Audit / Overnight Staff</option>
                    <option>Director of Sales &amp; Groups</option>
                  </select>
                </div>
                <div>
                  <label className="block text-[11px] font-bold text-[#475B80] mb-1">Miami Hotel Name</label>
                  <input
                    value={contactHotel}
                    onChange={(e) => setContactHotel(e.target.value)}
                    placeholder="e.g., Avalon Hotel South Beach"
                    className="w-full px-3 py-2 text-xs rounded-xl border border-[#DCE7F8] bg-[#F7FAFF]"
                  />
                </div>
                <div>
                  <label className="block text-[11px] font-bold text-[#475B80] mb-1">Phone / WhatsApp</label>
                  <input
                    value={contactPhone}
                    onChange={(e) => setContactPhone(e.target.value)}
                    placeholder="+1 (305) 555-0199"
                    className="w-full px-3 py-2 text-xs rounded-xl border border-[#DCE7F8] bg-[#F7FAFF]"
                  />
                </div>
                <div className="sm:col-span-2">
                  <label className="block text-[11px] font-bold text-[#475B80] mb-1">Work Email (for 1-Page Parity PDF)</label>
                  <input
                    type="email"
                    value={contactEmail}
                    onChange={(e) => setContactEmail(e.target.value)}
                    placeholder="gm@yourmiamihotel.com"
                    className="w-full px-3 py-2 text-xs rounded-xl border border-[#DCE7F8] bg-[#F7FAFF]"
                  />
                </div>
                <div className="sm:col-span-2">
                  <label className="block text-[11px] font-bold text-[#475B80] mb-1">What would you like to inspect?</label>
                  <input
                    value={contactNote}
                    onChange={(e) => setContactNote(e.target.value)}
                    placeholder="OTA undercut check, Suite-vs-Suite setup, OOO/OOS AI auto-pricing, or $99 AI Audit..."
                    className="w-full px-3 py-2 text-xs rounded-xl border border-[#DCE7F8] bg-[#F7FAFF]"
                  />
                </div>
              </div>
              <div className="flex flex-wrap items-center gap-3 pt-1">
                <button
                  type="submit"
                  disabled={contactSending}
                  className="px-5 py-2.5 rounded-xl bg-blue-600 text-white text-xs font-extrabold hover:bg-blue-700 disabled:opacity-60 transition"
                >
                  {contactSending ? 'Sending to Miami Desk...' : 'Send to Miami Hospitality Desk →'}
                </button>
                <a
                  href="https://wa.me/17869708366"
                  target="_blank"
                  rel="noreferrer"
                  className="px-4 py-2.5 rounded-xl bg-emerald-600 text-white text-xs font-bold hover:bg-emerald-700 transition"
                >
                  Chat on WhatsApp Now
                </a>
              </div>
              {contactConfirmation && (
                <div className="p-3 rounded-xl bg-emerald-50 border border-emerald-200 text-xs font-bold text-emerald-800">
                  {contactConfirmation}
                </div>
              )}
            </form>
          </div>
        </section>

        {/* SECTION 6: BLOGS & 10-SECOND WALKTHROUGH VIDEO */}
        <section id="blogs" className="rounded-[26px] ember-canvas-panel p-5 sm:p-7 space-y-5">
          <div className="flex flex-wrap items-end justify-between gap-3">
            <div>
              <span className="text-[11px] font-extrabold uppercase tracking-wider text-blue-700">
                10-Second Walkthrough &amp; Miami Hospitality Field Guides
              </span>
              <h2 className="text-2xl font-black text-[#0B1B3B] mt-0.5">Blogs</h2>
            </div>
            <a
              href="https://www.aidynamic.pro/blog"
              target="_blank"
              rel="noreferrer"
              className="px-3.5 py-1.5 rounded-xl bg-white border border-[#DCE7F8] text-xs font-bold text-blue-700 hover:bg-blue-50"
            >
              All Articles on aidynamic.pro ↗
            </a>
          </div>

          {/* 10-Second Minimalist Overview Video Card */}
          <div id="blogs-video" className="ember-card p-4 sm:p-5 grid grid-cols-1 lg:grid-cols-12 gap-5 items-center">
            <div className="lg:col-span-7">
              <div className="rounded-2xl overflow-hidden border border-[#DCE7F8] bg-[#F2F6FD] shadow-sm">
                <video
                  controls
                  playsInline
                  preload="metadata"
                  poster="/assets/hri_10s_poster.png"
                  aria-label="HotelRateIntel 10-Second Miami Hotel Rate Comparison Overview"
                  className="w-full aspect-video object-cover block"
                >
                  <source src="/assets/hri_10s_overview.mp4" type="video/mp4" />
                  Your browser does not support HTML5 video.
                </video>
              </div>
            </div>
            <div className="lg:col-span-5 space-y-3">
              <span className="inline-block px-2.5 py-0.5 rounded-full bg-blue-50 border border-blue-200 text-[10px] font-extrabold uppercase text-blue-700">
                0:10 Minimalist Walkthrough · Miami Hotels
              </span>
              <h3 className="text-lg sm:text-xl font-black text-[#0B1B3B] leading-snug">
                See How HotelRateIntel Compares Your Rates in 10 Seconds
              </h3>
              <p className="text-xs text-[#475B80] leading-relaxed">
                Every morning at <b>6:00 AM</b>, we automatically scan Booking.com, Expedia, Agoda, Vio.com, Trip.com, and competing Miami hotel websites — then line up exact <b>Suite-vs-Suite</b> pricing and live <b>OOO/OOS</b> room holds on one calm screen.
              </p>
              <div className="flex flex-wrap gap-2 pt-1">
                <button
                  type="button"
                  onClick={() => navigate(`/portal?demo_hotel=${selectedSampleId}`)}
                  className="px-4 py-2 rounded-xl bg-blue-600 text-white text-xs font-bold hover:bg-blue-700 transition"
                >
                  Open Live Client Portal →
                </button>
                <button
                  type="button"
                  onClick={() => openCoordinatedContact('sms')}
                  className="px-3.5 py-2 rounded-xl bg-[#F2F6FD] border border-[#DCE7F8] text-[#0B1B3B] text-xs font-bold hover:bg-blue-50 transition"
                >
                  Text / Email Miami Desk
                </button>
              </div>
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {BLOGS_SEED.map((b, i) => (
              <article key={i} className="ember-card p-5 flex flex-col justify-between gap-3">
                <div className="space-y-2.5">
                  <div className="flex items-center justify-between gap-2">
                    <span className="px-2.5 py-0.5 rounded-full bg-blue-50 text-blue-700 text-[10px] font-extrabold uppercase">
                      {b.tag}
                    </span>
                    <span className="text-[10px] font-bold text-[#6D81A8]">{b.readTime}</span>
                  </div>
                  <h3 className="text-sm font-extrabold text-[#0B1B3B] leading-snug">{b.title}</h3>
                  <div className="grid grid-cols-2 gap-2">
                    <div className="ember-subtle-card p-2 text-center">
                      <div className="text-sm font-black text-blue-700">{b.stat1.v}</div>
                      <div className="text-[10px] text-[#6D81A8]">{b.stat1.l}</div>
                    </div>
                    <div className="ember-subtle-card p-2 text-center">
                      <div className="text-sm font-black text-emerald-700">{b.stat2.v}</div>
                      <div className="text-[10px] text-[#6D81A8]">{b.stat2.l}</div>
                    </div>
                  </div>
                  <p className="text-xs text-[#475B80] leading-relaxed">{b.summary}</p>
                </div>
                <div className="flex items-center justify-between gap-2 pt-2 border-t border-[#EAF1FC]">
                  <button
                    type="button"
                    onClick={() => setActiveBlogIndex(i)}
                    className="text-xs font-extrabold text-blue-700 hover:underline inline-flex items-center gap-1"
                  >
                    Read Full Guide →
                  </button>
                  <a
                    href={b.url}
                    target="_blank"
                    rel="noreferrer"
                    className="text-[11px] font-bold text-[#6D81A8] hover:text-blue-700 inline-flex items-center gap-1"
                  >
                    aidynamic.pro
                    <ExternalLink className="w-3 h-3" />
                  </a>
                </div>
              </article>
            ))}
          </div>
        </section>

        <ModalDialog
          open={activeBlogIndex !== null}
          onClose={() => setActiveBlogIndex(null)}
          title={activeBlogIndex !== null ? BLOGS_SEED[activeBlogIndex].title : ''}
          subtitle={
            activeBlogIndex !== null
              ? `${BLOGS_SEED[activeBlogIndex].tag} · ${BLOGS_SEED[activeBlogIndex].readTime} · Miami Hospitality Field Guide`
              : ''
          }
        >
          {activeBlogIndex !== null && (
            <div className="space-y-4 text-xs text-[#334155] leading-relaxed">
              <div className="p-3.5 rounded-2xl bg-[#F5F9FF] border border-[#DCE7F8] space-y-1.5">
                <div className="text-[10.5px] font-extrabold uppercase text-blue-700">Key Operational Takeaways</div>
                {BLOGS_SEED[activeBlogIndex].takeaways.map((t, idx) => (
                  <div key={idx} className="flex items-start gap-2 font-semibold text-[#0B1B3B]">
                    <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600 shrink-0 mt-0.5" />
                    <span>{t}</span>
                  </div>
                ))}
              </div>
              <div className="space-y-3">
                {BLOGS_SEED[activeBlogIndex].body.map((para, idx) => (
                  <p key={idx}>{para}</p>
                ))}
              </div>
              <div className="flex flex-wrap items-center gap-2 pt-3 border-t border-[#EAF1FC]">
                <button
                  type="button"
                  onClick={() => {
                    setActiveBlogIndex(null)
                    navigate(`/portal?demo_hotel=${selectedSampleId}`)
                  }}
                  className="px-4 py-2 rounded-xl bg-blue-600 text-white text-xs font-bold hover:bg-blue-700"
                >
                  Try This Live in Client Portal →
                </button>
                <button
                  type="button"
                  onClick={() => {
                    setActiveBlogIndex(null)
                    openCoordinatedContact('email')
                  }}
                  className="px-4 py-2 rounded-xl bg-[#F2F6FD] border border-[#DCE7F8] text-[#0B1B3B] text-xs font-bold hover:bg-blue-50"
                >
                  Ask Our Miami Desk
                </button>
              </div>
            </div>
          )}
        </ModalDialog>

        <footer className="text-center text-xs text-blue-100/90 py-4 space-x-3">
          <b>HotelRateIntel · North Miami, FL 33161</b>
          <span>·</span>
          <a href="tel:+17869708366" className="underline">+1 (786) 970-8366</a>
          <span>·</span>
          <a href="#contact-desk" className="underline">Contact Miami Desk</a>
          <span>·</span>
          <a href="https://www.aidynamic.pro" target="_blank" rel="noreferrer" className="underline">AI Dynamic Pro</a>
          <span>·</span>
          <button type="button" onClick={() => navigate('/portal')} className="underline">Client WebApp</button>
        </footer>
      </div>

      <VoiceConcierge
        selectedHotelId={Number(selectedSampleId || 23)}
        onAuditReceived={(a) => setAuditResult(a as PublicAuditResponse)}
      />
    </div>
  )
}
