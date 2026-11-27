import React, { useMemo, useState } from 'react'
import { createColumnHelper, type ColumnDef } from '@tanstack/react-table'
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell } from 'recharts'
import { BedDouble, Star } from 'lucide-react'
import { usePortalStore } from '../../store/usePortalStore'
import type { RoomEquivalencyItem } from '../../types/hospitality'
import { DataTable } from '../../components/ui/DataTable'
import { MetricCard } from '../../components/ui/MetricCard'

const colHelper = createColumnHelper<RoomEquivalencyItem>()

export const RoomMatchPage: React.FC = () => {
  const { roomEquivalency, fetchRoomEquivalency, density } = usePortalStore()
  const [tier, setTier] = useState(roomEquivalency.room_tier.id || 'suite_vs_suite')
  const [occ, setOcc] = useState(roomEquivalency.occupancy || 'double')
  const [rollaway, setRollaway] = useState(Boolean(roomEquivalency.include_rollaway))

  const handleParamChange = (nextTier: string, nextOcc: string, nextRoll: boolean) => {
    setTier(nextTier)
    setOcc(nextOcc)
    setRollaway(nextRoll)
    fetchRoomEquivalency(nextTier, nextOcc, nextRoll)
  }

  const columns = useMemo(
    () =>
      [
        colHelper.accessor('name', {
          header: 'Property',
          cell: ({ row }) => (
            <div>
              <div className="font-extrabold text-[#0B1B3B]">
                {row.original.name}{' '}
                {row.original.is_primary && (
                  <span className="ml-1 px-1.5 py-0.5 rounded bg-blue-600 text-white text-[9px]">MY HOTEL</span>
                )}
              </div>
              <div className="text-[10.5px] text-[#6D81A8] inline-flex items-center gap-1">
                <span>{row.original.area} · {row.original.stars}</span>
                <Star className="w-3 h-3 text-amber-500 fill-amber-400" />
              </div>
            </div>
          ),
        }),
        colHelper.accessor('matched_category', {
          header: 'Matched Room Equivalent',
          cell: ({ getValue }) => <span className="text-[11px] font-bold text-[#0B1B3B]">{getValue()}</span>,
        }),
        colHelper.accessor('category_bar', {
          header: 'Category BAR',
          cell: ({ getValue }) => <span className="font-extrabold tabular-nums">${getValue()}</span>,
        }),
        colHelper.accessor('resort_fee', {
          header: 'Resort Fee',
          cell: ({ getValue }) => {
            const v = getValue()
            return v > 0 ? (
              <span className="tabular-nums font-semibold text-[#475B80]">${v}/nt</span>
            ) : (
              <span className="px-2 py-0.5 rounded-full bg-emerald-50 text-emerald-700 text-[10px] font-extrabold">$0 Fee</span>
            )
          },
        }),
        colHelper.accessor('rollaway_fee', {
          header: 'Rollaway Bed',
          cell: ({ row }) =>
            row.original.rollaway_allowed ? (
              <span className="text-[11px] font-semibold tabular-nums">
                {row.original.rollaway_fee > 0 ? `+$${row.original.rollaway_fee}/nt` : 'Optional'}
              </span>
            ) : (
              <span className="text-[11px] text-rose-600 font-bold">Not Allowed</span>
            ),
        }),
        colHelper.accessor('hk_cadence', {
          header: 'Housekeeping (HK)',
          cell: ({ getValue }) => <span className="text-[11px] text-[#475B80]">{getValue()}</span>,
        }),
        colHelper.accessor('true_otd_total', {
          header: 'True Out-the-Door',
          cell: ({ row }) => (
            <div>
              <span className="font-black text-blue-700 tabular-nums">${row.original.true_otd_total}</span>
              <span className="text-[10px] text-[#6D81A8] ml-1">({row.original.tax_pct}% tax)</span>
            </div>
          ),
        }),
        colHelper.accessor('spread_vs_my_otd', {
          header: 'vs. My OTD',
          cell: ({ row }) => {
            if (row.original.is_primary) return <span className="font-bold text-[#6D81A8]">Baseline</span>
            const s = row.original.spread_vs_my_otd
            return (
              <span className={`font-extrabold tabular-nums ${s >= 0 ? 'text-emerald-600' : 'text-rose-600'}`}>
                {s >= 0 ? `+$${s}` : `-$${Math.abs(s)}`}
              </span>
            )
          },
        }),
      ] as ColumnDef<RoomEquivalencyItem, unknown>[],
    []
  )

  const chartData = roomEquivalency.items.map((it) => ({
    name: it.name.split(' ').slice(0, 2).join(' '),
    trueOtd: it.true_otd_total,
    categoryBar: it.category_bar,
    isPrimary: it.is_primary,
  }))

  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <span className="text-[11px] font-extrabold uppercase tracking-wider text-blue-700">
            Apples-to-Apples Room Equivalency · Made by Hoteliers
          </span>
          <h1 className="text-xl sm:text-2xl font-black text-[#0B1B3B] tracking-tight">
            Suite vs. Suite &amp; True Out-the-Door Comparator
          </h1>
          <p className="text-xs text-[#475B80]">
            Compares identical room types only—normalizing Single/Double/Quad occupancy, rollaway beds, Miami resort fees, 14% tax, and Housekeeping cadence.
          </p>
        </div>
      </div>

      {/* Controls Strip */}
      <div className="ember-card p-4 flex flex-wrap items-center gap-3">
        <div className="flex-1 min-w-[220px]">
          <label className="block text-[10px] font-extrabold uppercase text-[#475B80] mb-1">Exact Room Type Equivalent</label>
          <select
            aria-label="Select matched room equivalent"
            value={tier}
            onChange={(e) => handleParamChange(e.target.value, occ, rollaway)}
            className="w-full px-3 py-2 text-xs font-bold rounded-xl border border-[#DCE7F8] bg-[#F7FAFF]"
          >
            <option value="suite_vs_suite">Junior / 1-BR Suite (Suite vs. Suite)</option>
            <option value="double_double">Two Doubles / Two Queens (DD / QQ)</option>
            <option value="standard_king">Standard King / Queen (Entry BAR)</option>
            <option value="ocean_balcony">Oceanview / Balcony Corner Upgrade</option>
          </select>
        </div>

        <div className="min-w-[180px]">
          <label className="block text-[10px] font-extrabold uppercase text-[#475B80] mb-1">Guest Occupancy</label>
          <select
            aria-label="Select occupancy count"
            value={occ}
            onChange={(e) => handleParamChange(tier, e.target.value, rollaway)}
            className="w-full px-3 py-2 text-xs font-bold rounded-xl border border-[#DCE7F8] bg-[#F7FAFF]"
          >
            <option value="single">Single Occ (1 Adult)</option>
            <option value="double">Double Occ (2 Adults)</option>
            <option value="triple_quad">Triple / Quad (3–4 Adults)</option>
          </select>
        </div>

        <label className="inline-flex items-center gap-2 px-3.5 py-2.5 rounded-xl bg-[#F7FAFF] border border-[#DCE7F8] text-xs font-bold text-[#0B1B3B] cursor-pointer mt-4">
          <input
            type="checkbox"
            checked={rollaway}
            onChange={(e) => handleParamChange(tier, occ, e.target.checked)}
            className="rounded border-slate-300 text-blue-600"
          />
          Include Rollaway Bed
        </label>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <MetricCard
          label="My Normalized OTD"
          value={`$${roomEquivalency.my_true_otd ?? 0}`}
          sub={`${roomEquivalency.room_tier.match_rule}`}
          tone="royal"
          icon={<BedDouble className="w-4 h-4" />}
        />
        <MetricCard
          label="Comp-Set Equivalent Avg"
          value={`$${roomEquivalency.comp_avg_otd}`}
          sub={`Includes resort fees, tax${rollaway ? ' & rollaway' : ''}`}
          tone="slate"
        />
        <MetricCard
          label="Out-the-Door Positioning"
          value={`${roomEquivalency.otd_advantage >= 0 ? '+$' : '-$'}${Math.abs(roomEquivalency.otd_advantage)}/nt`}
          delta={roomEquivalency.otd_advantage >= 0 ? 'Room to Lift' : 'Premium'}
          sub={roomEquivalency.room_tier.rollaway_note}
          tone={roomEquivalency.otd_advantage >= 0 ? 'emerald' : 'amber'}
        />
      </div>

      {/* Out-the-Door Recharts Comparison + Table */}
      <div className="ember-card p-5 space-y-4">
        <div className="h-[220px]">
          <ResponsiveContainer width="100%" height={210}>
            <BarChart data={chartData} margin={{ top: 8, right: 12, left: -12, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#EAF1FC" />
              <XAxis dataKey="name" tick={{ fontSize: 11, fill: '#475B80' }} />
              <YAxis tick={{ fontSize: 11, fill: '#475B80' }} />
              <Tooltip formatter={(v: number) => `$${v}/nt`} />
              <Bar dataKey="trueOtd" name="True Out-the-Door" radius={[8, 8, 0, 0]}>
                {chartData.map((entry, idx) => (
                  <Cell key={idx} fill={entry.isPrimary ? '#2563EB' : '#64748B'} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>

        <DataTable
          data={roomEquivalency.items}
          columns={columns}
          density={density}
          searchPlaceholder="Search matched properties..."
          csvFilename="hotelrateintel-room-equivalency.csv"
          csvHeaders={['Property', 'Category', 'BAR', 'Resort Fee', 'Rollaway', 'HK Cadence', 'True OTD', 'Spread']}
          csvRowMapper={(it) => [it.name, it.matched_category, it.category_bar, it.resort_fee, it.rollaway_fee, it.hk_cadence, it.true_otd_total, it.spread_vs_my_otd]}
        />
      </div>
    </div>
  )
}
