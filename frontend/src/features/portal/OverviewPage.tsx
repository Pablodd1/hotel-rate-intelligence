import React, { useMemo } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  AreaChart,
  Area,
  BarChart,
  Bar,
  Cell,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from 'recharts'
import { AlertTriangle, BedDouble, Bot, Clock, DollarSign, PhoneCall, TrendingUp, Wrench } from 'lucide-react'
import { usePortalStore } from '../../store/usePortalStore'
import { HISTORICAL_12M_SEED } from '../../data/demoSeed'
import { MetricCard } from '../../components/ui/MetricCard'

export const OverviewPage: React.FC = () => {
  const navigate = useNavigate()
  const { portal, opsPlan, dateRange } = usePortalStore()
  const { primary_hotel, comp_set, strategy, memory_events } = portal

  const trendSeries = useMemo(() => {
    const mult = dateRange === 'art_basel' ? 1.48 : dateRange === '30d' ? 1.08 : dateRange === '7d' ? 1.03 : 1.0
    const slice = dateRange === 'today' ? HISTORICAL_12M_SEED.slice(-6) : dateRange === '7d' ? HISTORICAL_12M_SEED.slice(-8) : HISTORICAL_12M_SEED
    const myScale = Math.max(0.2, Number(strategy.my_bar || 238) / 238)
    const compScale = Math.max(0.2, Number(strategy.comp_avg_bar || 265) / 265)
    return slice.map((pt, idx) => {
      const isLast = idx === slice.length - 1
      return {
        month: pt.month,
        myBar: Math.round((isLast ? strategy.my_bar : pt.myBar * myScale) * mult),
        compAvg: Math.round((isLast ? strategy.comp_avg_bar : pt.compBar * compScale) * mult),
      }
    })
  }, [dateRange, strategy.my_bar, strategy.comp_avg_bar])

  const recentMoves = useMemo(() => {
    if (memory_events && memory_events.length) return memory_events.slice(0, 4)
    return comp_set.slice(0, 3).map((h, i) => {
      const pNow = Math.round(Number(h.price || strategy.comp_avg_bar))
      const pOld = Math.round(pNow * (h.is_primary ? 0.96 : 1.03))
      return {
        id: 800 + i,
        hotel_id: h.id,
        hotel_name: h.name,
        event_type: h.parity_status || 'PARITY',
        old_price: pOld,
        new_price: pNow,
        delta_pct: Number((((pNow - pOld) / Math.max(1, pOld)) * 100).toFixed(1)),
        est_occupancy_pct: h.est_occupancy_pct || 76,
        competitor_pattern: h.pricing_personality || 'Corridor Benchmark',
        ai_recommendation: `Tracked 6:00 AM EST in ${h.area} (${h.booking_engine || 'Direct'}).`,
        recorded_at: Date.now() / 1000,
      }
    })
  }, [memory_events, comp_set, strategy.comp_avg_bar])

  const otaLadderData = useMemo(() => {
    const chans = primary_hotel.ota_channels || []
    if (!chans.length) {
      return [
        { name: 'Direct BAR', rate: Math.round(strategy.my_bar), isDirect: true },
        { name: 'Booking', rate: Math.round(strategy.my_bar), isDirect: false },
      ]
    }
    const mapped = chans.map((c) => ({
      name: c.name.replace('.com', '').replace(' Website', ''),
      rate: Number(c.rate || strategy.my_bar),
      isDirect: c.code === 'DIRECT' || /direct/i.test(c.name),
    }))
    if (!mapped.some((m) => m.isDirect)) {
      mapped.unshift({ name: 'Direct BAR', rate: Math.round(strategy.my_bar), isDirect: true })
    }
    return mapped
  }, [primary_hotel.ota_channels, strategy.my_bar])

  return (
    <div className="space-y-5">
      {/* Header Row */}
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <span className="text-[11px] font-extrabold uppercase tracking-wider text-blue-700">
            Made by Hoteliers · Powered by AI · Isolated Property Console
          </span>
          <h1 className="text-xl sm:text-2xl font-black text-[#0B1B3B] tracking-tight">
            {primary_hotel.name} — Reservations &amp; Yield Overview
          </h1>
        </div>
        <div className="flex flex-wrap gap-2">
          <button
            type="button"
            onClick={() => navigate('/portal/room-match')}
            className="px-3.5 py-2 rounded-xl bg-white border border-[#DCE7F8] text-xs font-bold text-[#0B1B3B] inline-flex items-center gap-1.5 hover:bg-blue-50"
          >
            <BedDouble className="w-3.5 h-3.5 text-blue-600" />
            Suite vs. Suite Match
          </button>
          <button
            type="button"
            onClick={() => navigate('/portal/room-ops')}
            className="px-3.5 py-2 rounded-xl bg-blue-600 text-white text-xs font-bold inline-flex items-center gap-1.5 hover:bg-blue-700"
          >
            <Wrench className="w-3.5 h-3.5" />
            Adjust OOO / OOS ({opsPlan.ops.offline_rooms} offline)
          </button>
        </div>
      </div>

      {/* 4 Ember Metric KPI Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-4">
        <MetricCard
          label="My Live Direct BAR"
          value={`$${Math.round(strategy.my_bar)}`}
          delta={
            strategy.spread_vs_comp < 0
              ? `-$${Math.abs(strategy.spread_vs_comp)} vs Comp`
              : `+$${strategy.spread_vs_comp} vs Comp`
          }
          sub={`${primary_hotel.area} · Comp Avg: $${Math.round(strategy.comp_avg_bar)}/nt`}
          tone="royal"
          icon={<DollarSign className="w-4 h-4" />}
        />
        <MetricCard
          label="True Sellable & Net Occ"
          value={`${opsPlan.ops.net_occupancy_pct}%`}
          delta={`${opsPlan.ops.remaining_to_sell} left`}
          sub={`${opsPlan.ops.sellable_rooms}/${opsPlan.ops.total_rooms} sellable (${opsPlan.ops.ooo_rooms} OOO · ${opsPlan.ops.oos_rooms} OOS)`}
          tone={opsPlan.ops.net_occupancy_pct >= 85 ? 'amber' : 'emerald'}
          icon={<TrendingUp className="w-4 h-4" />}
        />
        <MetricCard
          label="Comp-Set Parity Leaks"
          value={strategy.undercut_count_in_comp}
          delta={`${comp_set.length} Hotels`}
          sub="Active Agoda / Vio / FIT wholesale undercuts"
          tone={strategy.undercut_count_in_comp > 0 ? 'rose' : 'emerald'}
          icon={<AlertTriangle className="w-4 h-4" />}
        />
        <MetricCard
          label="Front-Office Time Saved"
          value={`${strategy.staff_hours_saved_mo} hrs/mo`}
          delta={`$${strategy.labor_dollars_saved_mo.toLocaleString()}/mo`}
          sub={`Est. Revenue Impact: +$${strategy.est_revenue_recovered_mo.toLocaleString()}/mo`}
          tone="emerald"
          icon={<Clock className="w-4 h-4" />}
        />
      </div>

      {/* AI Decision Banner */}
      <div className="rounded-2xl p-5 bg-gradient-to-r from-[#06122E] via-[#0D255B] to-[#1744A6] text-white flex flex-wrap items-center justify-between gap-4 shadow-emberSidebar">
        <div className="space-y-1 max-w-3xl">
          <div className="inline-flex items-center gap-1.5 text-[10.5px] font-extrabold uppercase tracking-wider text-blue-200">
            <Bot className="w-3.5 h-3.5 text-emerald-400" />
            AI Decision-Making Assistant · Next Target BAR ${opsPlan.recommended_bar}/nt
          </div>
          <div className="text-base sm:text-lg font-extrabold">{strategy.recommended_action}</div>
          <p className="text-xs text-blue-100 leading-relaxed">{strategy.explanation}</p>
        </div>
        <div className="flex flex-wrap gap-2">
          <button
            type="button"
            onClick={() => navigate('/portal/auto-pricing')}
            className="px-4 py-2 rounded-xl bg-white text-[#0B1B3B] text-xs font-extrabold hover:bg-blue-50"
          >
            Review AI Auto-Price →
          </button>
          <button
            type="button"
            onClick={() => navigate('/portal/call-desk')}
            className="px-3.5 py-2 rounded-xl bg-white/10 border border-white/20 text-white text-xs font-bold inline-flex items-center gap-1.5 hover:bg-white/20"
          >
            <PhoneCall className="w-3.5 h-3.5" />
            Night Audit Desk
          </button>
        </div>
      </div>

      {/* Charts Grid: BAR vs Comp Trend + OTA Parity Ladder */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-4">
        <div className="lg:col-span-7 ember-card p-5">
          <div className="flex items-center justify-between mb-3">
            <div>
              <h2 className="text-sm font-extrabold text-[#0B1B3B]">Direct BAR vs. Street Comp-Set Trend ($)</h2>
              <p className="text-[11px] text-[#6D81A8]">Filtered by active date horizon ({dateRange.toUpperCase()})</p>
            </div>
            <span className="px-2.5 py-0.5 rounded-full bg-blue-50 text-blue-700 text-[10.5px] font-bold">
              Royal Blue = Your BAR
            </span>
          </div>
          <div className="h-[245px]">
            <ResponsiveContainer width="100%" height={235}>
              <AreaChart data={trendSeries} margin={{ top: 8, right: 12, left: -12, bottom: 0 }}>
                <defs>
                  <linearGradient id="myBarFill" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#2563EB" stopOpacity={0.28} />
                    <stop offset="95%" stopColor="#2563EB" stopOpacity={0.02} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="#EAF1FC" />
                <XAxis dataKey="month" tick={{ fontSize: 11, fill: '#475B80' }} />
                <YAxis tick={{ fontSize: 11, fill: '#475B80' }} />
                <Tooltip formatter={(v: number) => `$${v}/nt`} />
                <Area type="monotone" dataKey="compAvg" name="Comp Avg" stroke="#64748B" strokeDasharray="4 4" fill="transparent" strokeWidth={2} />
                <Area type="monotone" dataKey="myBar" name="Your Direct BAR" stroke="#2563EB" fill="url(#myBarFill)" strokeWidth={2.5} />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>

        <div className="lg:col-span-5 ember-card p-5">
          <div className="mb-3">
            <h2 className="text-sm font-extrabold text-[#0B1B3B]">Live Multi-OTA Parity Ladder ($)</h2>
            <p className="text-[11px] text-[#6D81A8]">Highlights third-party channels undercutting Direct BAR</p>
          </div>
          <div className="h-[245px]">
            <ResponsiveContainer width="100%" height={235}>
              <BarChart data={otaLadderData} margin={{ top: 8, right: 8, left: -12, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#EAF1FC" />
                <XAxis dataKey="name" tick={{ fontSize: 11, fill: '#475B80' }} />
                <YAxis tick={{ fontSize: 11, fill: '#475B80' }} />
                <Tooltip formatter={(v: number) => `$${v}/nt`} />
                <Bar dataKey="rate" maxBarSize={54} radius={[8, 8, 0, 0]}>
                  {otaLadderData.map((entry, idx) => (
                    <Cell
                      key={idx}
                      fill={entry.isDirect ? '#2563EB' : entry.rate < strategy.my_bar ? '#E11D48' : '#059669'}
                    />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>

      {/* Bottom Split: Top Comp-Set Snapshot & Recent Memory Feed */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <div className="ember-card p-5">
          <div className="flex items-center justify-between gap-2 mb-3">
            <h2 className="text-sm font-extrabold text-[#0B1B3B]">Assigned Corridor Comp-Set Snapshot</h2>
            <button type="button" onClick={() => navigate('/portal/comp-set')} className="text-xs font-bold text-blue-700 hover:underline whitespace-nowrap shrink-0">
              Full Table →
            </button>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs border-collapse">
              <thead className="bg-[#F5F9FF] border-b border-[#DCE7F8]">
                <tr>
                  <th className="p-2 text-[10px] font-extrabold uppercase text-[#475B80]">Property</th>
                  <th className="p-2 text-[10px] font-extrabold uppercase text-[#475B80]">Live BAR</th>
                  <th className="p-2 text-[10px] font-extrabold uppercase text-[#475B80]">Occ Est.</th>
                  <th className="p-2 text-[10px] font-extrabold uppercase text-[#475B80]">Parity</th>
                </tr>
              </thead>
              <tbody>
                {comp_set.slice(0, 5).map((h) => (
                  <tr key={h.id} className={`border-b border-[#EEF4FD] last:border-b-0 ${h.is_primary ? 'bg-blue-50/60 font-bold' : ''}`}>
                    <td className="p-2">
                      {h.name} {h.is_primary && <span className="ml-1 px-1.5 py-0.5 rounded bg-blue-600 text-white text-[9px]">YOU</span>}
                    </td>
                    <td className="p-2 tabular-nums font-extrabold">{h.price ? `$${Math.round(h.price)}` : '—'}</td>
                    <td className="p-2 tabular-nums">{h.est_occupancy_pct}%</td>
                    <td className="p-2">
                      <span
                        className={`px-2 py-0.5 rounded-full text-[10px] font-extrabold ${
                          h.parity_status === 'UNDERCUT'
                            ? 'bg-rose-50 text-rose-700'
                            : h.parity_status === 'DIRECT_WIN'
                              ? 'bg-emerald-50 text-emerald-700'
                              : 'bg-blue-50 text-blue-700'
                        }`}
                      >
                        {h.parity_status}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        <div className="ember-card p-5 space-y-3">
          <div className="flex items-center justify-between gap-2">
            <h2 className="text-sm font-extrabold text-[#0B1B3B]">Recent Rate Moves &amp; Night Audit Activity</h2>
            <button type="button" onClick={() => navigate('/portal/memory')} className="text-xs font-bold text-blue-700 hover:underline whitespace-nowrap shrink-0">
              All Memory →
            </button>
          </div>
          <div className="space-y-2">
            {recentMoves.map((ev) => (
              <div key={ev.id} className="ember-subtle-card p-3 flex items-start justify-between gap-3">
                <div>
                  <div className="text-xs font-extrabold text-[#0B1B3B]">{ev.hotel_name || `Hotel #${ev.hotel_id}`}</div>
                  <div className="text-[11px] text-[#475B80] mt-0.5">{ev.ai_recommendation}</div>
                </div>
                <span className="px-2 py-0.5 rounded-full bg-white border border-[#DCE7F8] text-[10px] font-extrabold text-blue-700 shrink-0 tabular-nums">
                  {ev.old_price && ev.new_price ? `$${ev.old_price}→$${ev.new_price}` : ev.event_type}
                </span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  )
}
