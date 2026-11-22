import React, { useMemo } from 'react'
import {
  AreaChart,
  Area,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from 'recharts'
import { Calendar, LineChart as LineChartIcon } from 'lucide-react'
import { usePortalStore } from '../../store/usePortalStore'
import { HISTORICAL_12M_SEED } from '../../data/demoSeed'
import { MetricCard } from '../../components/ui/MetricCard'

export const AnalyticsPage: React.FC = () => {
  const { portal, opsPlan, dateRange } = usePortalStore()

  const chartData = useMemo(() => {
    const mult = dateRange === 'art_basel' ? 1.5 : dateRange === '30d' ? 1.08 : 1.0
    return HISTORICAL_12M_SEED.map((pt, i) => {
      const isLast = i === HISTORICAL_12M_SEED.length - 1
      const bar = isLast ? portal.strategy.my_bar : pt.myBar
      const revPar = Math.round(bar * (opsPlan.ops.net_occupancy_pct / 100))
      return {
        month: pt.month,
        directBar: Math.round(bar * mult),
        compBar: Math.round(pt.compBar * mult),
        revPar: Math.round(revPar * mult),
        directPct: pt.directPct,
        otaBleedSaved: Math.round(pt.otaLeakUsd * (pt.directPct / 50)),
      }
    })
  }, [dateRange, portal.strategy.my_bar, opsPlan.ops.net_occupancy_pct])

  const revParNow = Math.round(portal.strategy.my_bar * (opsPlan.ops.net_occupancy_pct / 100))

  return (
    <div className="space-y-5">
      <div>
        <span className="text-[11px] font-extrabold uppercase tracking-wider text-blue-700">
          Yield, Direct Conversion &amp; Compression Analytics
        </span>
        <h1 className="text-xl sm:text-2xl font-black text-[#0B1B3B] tracking-tight">
          12-Month RevPAR, Direct Booking Share &amp; Compression Calendar
        </h1>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <MetricCard
          label="Live Net RevPAR"
          value={`$${revParNow}`}
          delta={`${opsPlan.ops.net_occupancy_pct}% Net Occ`}
          sub={`Calculated from $${portal.strategy.my_bar} BAR × ${opsPlan.ops.sellable_rooms} sellable rms`}
          tone="royal"
          icon={<LineChartIcon className="w-4 h-4" />}
        />
        <MetricCard
          label="Direct Channel Share"
          value="68%"
          delta="+20% YoY"
          sub="Recovered from Agoda & Vio wholesale parity enforcement"
          tone="emerald"
        />
        <MetricCard
          label="Estimated Annual ROI"
          value={`+$${(portal.strategy.est_revenue_recovered_mo * 12).toLocaleString()}`}
          delta="68 hrs/mo saved"
          sub="Direct shift + weekend compression ADR lifts"
          tone="emerald"
        />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <div className="ember-card p-5">
          <h2 className="text-sm font-extrabold text-[#0B1B3B] mb-1">12-Month Direct BAR vs. Comp Avg &amp; RevPAR</h2>
          <p className="text-[11px] text-[#6D81A8] mb-3">Seasonal Miami cycle reconciled with your live room occupancy</p>
          <div className="h-[250px]">
            <ResponsiveContainer width="100%" height={240}>
              <AreaChart data={chartData} margin={{ top: 8, right: 12, left: -12, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#EAF1FC" />
                <XAxis dataKey="month" tick={{ fontSize: 11, fill: '#475B80' }} />
                <YAxis tick={{ fontSize: 11, fill: '#475B80' }} />
                <Tooltip formatter={(v: number) => `$${v}`} />
                <Area type="monotone" dataKey="compBar" name="Comp Avg" stroke="#64748B" fill="transparent" strokeDasharray="4 4" />
                <Area type="monotone" dataKey="directBar" name="Your BAR" stroke="#2563EB" fill="#DBEAFE" fillOpacity={0.5} strokeWidth={2.5} />
                <Area type="monotone" dataKey="revPar" name="Net RevPAR" stroke="#059669" fill="#D1FAE5" fillOpacity={0.35} strokeWidth={2} />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>

        <div className="ember-card p-5">
          <h2 className="text-sm font-extrabold text-[#0B1B3B] mb-1">Monthly Direct Booking Commission Savings ($)</h2>
          <p className="text-[11px] text-[#6D81A8] mb-3">Commission retained by shifting bookings off high-fee OTAs</p>
          <div className="h-[250px]">
            <ResponsiveContainer width="100%" height={240}>
              <BarChart data={chartData} margin={{ top: 8, right: 12, left: -12, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#EAF1FC" />
                <XAxis dataKey="month" tick={{ fontSize: 11, fill: '#475B80' }} />
                <YAxis tick={{ fontSize: 11, fill: '#475B80' }} />
                <Tooltip formatter={(v: number) => `$${v}`} />
                <Bar dataKey="otaBleedSaved" name="Commission Saved ($)" fill="#2563EB" radius={[6, 6, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>

      {/* Compression Events Table */}
      <div className="ember-card p-5">
        <div className="flex items-center gap-2 mb-3">
          <Calendar className="w-4 h-4 text-blue-600" />
          <h2 className="text-sm font-extrabold text-[#0B1B3B]">Miami Compression Event Radar &amp; Recommended BAR Lifts</h2>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          {portal.compression_events.map((ev, i) => (
            <div key={i} className="ember-subtle-card p-3.5 flex items-center justify-between gap-3">
              <div>
                <div className="text-[11px] font-extrabold text-blue-700">{ev.dates}</div>
                <div className="text-xs font-extrabold text-[#0B1B3B] mt-0.5">{ev.event}</div>
              </div>
              <span className="px-2.5 py-1 rounded-full bg-emerald-50 text-emerald-700 text-[11px] font-extrabold shrink-0">
                {ev.recommended_lift}
              </span>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
