import React, { useMemo, useState } from 'react'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { createColumnHelper, type ColumnDef } from '@tanstack/react-table'
import { Bot, CheckCircle2, Code2, Copy, Lock, PlugZap, RotateCcw, ShieldCheck } from 'lucide-react'
import { usePortalStore } from '../../store/usePortalStore'
import type { PricingActionRecord } from '../../types/hospitality'
import { DataTable } from '../../components/ui/DataTable'
import { ModalDialog } from '../../components/ui/ModalDialog'

const rulesSchema = z.object({
  mode: z.enum(['advisory', 'semi_auto', 'auto_pilot']),
  comp_position_target: z.enum(['match_avg', 'below_avg_5pct', 'above_avg_5pct']),
  min_bar_floor: z.coerce.number().min(49, 'Floor must be at least $49'),
  max_bar_ceiling: z.coerce.number().min(99, 'Ceiling must exceed floor'),
  compression_occ_threshold: z.coerce.number().min(50).max(99),
  compression_lift_pct: z.coerce.number().min(2).max(50),
  telegram_chat_id: z.string(),
})

type RulesFormValues = z.infer<typeof rulesSchema>
const logColHelper = createColumnHelper<PricingActionRecord>()

type PmsConnectorId = 'cloudbeds' | 'mews' | 'channex' | 'ota_xml' | 'webhook'

const PMS_CONNECTORS: Array<{
  id: PmsConnectorId
  name: string
  protocol: string
  auth: string
  endpoint: string
  coverage: string
}> = [
  {
    id: 'cloudbeds',
    name: 'Cloudbeds PMS / Myallocator',
    protocol: 'REST / ARI JSON',
    auth: 'OAuth 2.0 Bearer (property-scoped)',
    endpoint: 'PUT /putRate · ARIupdate',
    coverage: 'Direct PMS + Cloudbeds channel sync',
  },
  {
    id: 'mews',
    name: 'Mews Connector API',
    protocol: 'JSON REST',
    auth: 'ClientToken + AccessToken',
    endpoint: 'POST /api/connector/v1/rates/updatePrice',
    coverage: 'Root rates (BaseRateId: null) by CategoryId',
  },
  {
    id: 'channex',
    name: 'Channex.io Unified OTA Bridge',
    protocol: 'ARI JSON REST',
    auth: 'X-API-Key (encrypted server-side)',
    endpoint: 'POST /api/v1/restrictions',
    coverage: '50+ OTAs (Booking.com, Expedia, Agoda, Airbnb)',
  },
  {
    id: 'ota_xml',
    name: 'SiteMinder / SynXis (Sabre) CRS',
    protocol: 'OpenTravel / HTNG XML',
    auth: 'TLS 1.3 + WS-Security / Mutual Auth',
    endpoint: 'OTA_HotelRateAmountNotifRQ',
    coverage: 'Enterprise CRS & Channel Manager sync',
  },
  {
    id: 'webhook',
    name: 'Custom Signed Webhook',
    protocol: 'HTTPS JSON + HMAC-SHA256',
    auth: 'X-HRI-Signature + Idempotency-Key',
    endpoint: 'POST https://your-pms-bridge/rates',
    coverage: 'Any custom PMS / Zapier / n8n / Make bridge',
  },
]

export const AutoPricingPage: React.FC = () => {
  const { opsPlan, density, saveAutoPricingRules, applyAiPricingNow, pushToast } = usePortalStore()
  const [pmsModalOpen, setPmsModalOpen] = useState(false)
  const [selectedConnector, setSelectedConnector] = useState<PmsConnectorId>('channex')
  const [maxSwingPct, setMaxSwingPct] = useState(15)
  const [dryRunOnly, setDryRunOnly] = useState(true)

  const formattedWirePayload = useMemo(() => {
    const today = new Date().toISOString().slice(0, 10)
    const idemKey = `hri-${opsPlan.hotel_id}-${today}-${opsPlan.recommended_bar}`
    const recs = opsPlan.room_recommendations
    if (selectedConnector === 'mews') {
      return JSON.stringify(
        {
          endpoint: 'POST https://api.mews.com/api/connector/v1/rates/updatePrice',
          headers: { 'Idempotency-Key': idemKey },
          body: {
            ClientToken: '<SERVER_SIDE_ENCRYPTED>',
            AccessToken: '<PROPERTY_SCOPED_TOKEN>',
            RateId: '<ROOT_BAR_RATE_ID>',
            PriceUpdates: recs.map((r) => ({
              CategoryId: r.code,
              Value: r.recommended_bar,
              FirstTimeUnitStartUtc: `${today}T00:00:00Z`,
              LastTimeUnitStartUtc: `${today}T00:00:00Z`,
            })),
          },
        },
        null,
        2
      )
    }
    if (selectedConnector === 'channex') {
      return JSON.stringify(
        {
          endpoint: 'POST https://app.channex.io/api/v1/restrictions',
          headers: { 'user-api-key': '<SERVER_SIDE_ENCRYPTED>', 'Idempotency-Key': idemKey },
          body: {
            values: recs.map((r) => ({
              property_id: `hri_prop_${opsPlan.hotel_id}`,
              rate_plan_id: r.code,
              date_from: today,
              date_to: today,
              rate: String(r.recommended_bar),
              stop_sell: r.stop_sell,
              min_stay_arrival: opsPlan.channel_directive.includes('MIN_LOS') ? 2 : 1,
            })),
          },
        },
        null,
        2
      )
    }
    if (selectedConnector === 'cloudbeds') {
      return JSON.stringify(
        {
          endpoint: 'PUT https://hotels.cloudbeds.com/api/v1.2/putRate',
          headers: { Authorization: 'Bearer <OAUTH2_SCOPED_TOKEN>', 'Idempotency-Key': idemKey },
          body: {
            propertyID: String(opsPlan.hotel_id),
            startDate: today,
            endDate: today,
            rates: recs.map((r) => ({
              roomTypeID: r.code,
              rate: r.recommended_bar,
              stopSell: r.stop_sell,
            })),
          },
        },
        null,
        2
      )
    }
    if (selectedConnector === 'ota_xml') {
      const rateBlocks = recs
        .map(
          (r) =>
            `    <RateAmountMessage>\n      <StatusApplicationControl Start="${today}" End="${today}" InvTypeCode="${r.code}" RatePlanCode="BAR"/>\n      <Rates><Rate><BaseByGuestAmts><BaseByGuestAmt AmountBeforeTax="${r.recommended_bar}.00" CurrencyCode="USD"/></BaseByGuestAmts></Rate></Rates>\n    </RateAmountMessage>`
        )
        .join('\n')
      return `<!-- Endpoint: SiteMinder / SynXis HTNG XML (TLS 1.3 + WS-Security) -->\n<OTA_HotelRateAmountNotifRQ xmlns="http://www.opentravel.org/OTA/2003/05" EchoToken="${idemKey}">\n  <RateAmountMessages HotelCode="${opsPlan.hotel_id}">\n${rateBlocks}\n  </RateAmountMessages>\n</OTA_HotelRateAmountNotifRQ>`
    }
    return JSON.stringify(
      {
        endpoint: 'POST https://<your-pms-bridge>/api/hri-rates',
        headers: {
          'X-HRI-Signature': 'sha256=<HMAC_SHA256_SERVER_SIGNATURE>',
          'Idempotency-Key': idemKey,
        },
        guardrails: {
          min_bar_floor: opsPlan.rules.min_bar_floor,
          max_bar_ceiling: opsPlan.rules.max_bar_ceiling,
          max_daily_swing_pct: maxSwingPct,
          dry_run: dryRunOnly,
        },
        payload: opsPlan.pms_payload,
      },
      null,
      2
    )
  }, [selectedConnector, opsPlan, maxSwingPct, dryRunOnly])

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<RulesFormValues>({
    resolver: zodResolver(rulesSchema),
    defaultValues: {
      mode: opsPlan.rules.mode,
      comp_position_target: opsPlan.rules.comp_position_target,
      min_bar_floor: opsPlan.rules.min_bar_floor,
      max_bar_ceiling: opsPlan.rules.max_bar_ceiling,
      compression_occ_threshold: opsPlan.rules.compression_occ_threshold,
      compression_lift_pct: opsPlan.rules.compression_lift_pct,
      telegram_chat_id: opsPlan.rules.telegram_chat_id || '',
    },
  })

  const onSubmitRules = async (values: RulesFormValues) => {
    if (values.max_bar_ceiling <= values.min_bar_floor) {
      pushToast({ tone: 'error', title: 'Invalid Guardrail Range', detail: 'Max Ceiling BAR must exceed Min Floor BAR.' })
      return
    }
    await saveAutoPricingRules(values)
  }

  const auditColumns = useMemo(
    () =>
      [
        logColHelper.accessor((r) => `${r.old_bar} -> ${r.new_bar}`, {
          id: 'barMove',
          header: 'BAR Transition',
          cell: ({ row }) => (
            <span className="font-black text-[#0B1B3B] tabular-nums">
              ${row.original.old_bar} → <span className="text-blue-700">${row.original.new_bar}</span>
            </span>
          ),
        }),
        logColHelper.accessor('net_occupancy_pct', {
          header: 'Sellable / Net Occ',
          cell: ({ row }) => (
            <span className="tabular-nums font-semibold">
              {row.original.sellable_rooms} rms · {row.original.net_occupancy_pct}%
            </span>
          ),
        }),
        logColHelper.accessor('trigger_tags', {
          header: 'Trigger Tags',
          cell: ({ getValue }) => {
            try {
              const arr = JSON.parse(getValue() || '[]') as string[]
              return <span className="text-[11px] font-bold text-blue-700">{arr.join(' ')}</span>
            } catch {
              return <span className="text-[11px] text-[#6D81A8]">{getValue()}</span>
            }
          },
        }),
        logColHelper.accessor('reason', {
          header: 'Decision Logic',
          cell: ({ getValue }) => <span className="text-[11px] text-[#475B80]">{getValue()}</span>,
        }),
      ] as ColumnDef<PricingActionRecord, unknown>[],
    []
  )

  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <span className="text-[11px] font-extrabold uppercase tracking-wider text-blue-700">
            AI Auto-Pricing Strategy &amp; PMS Payload Engine
          </span>
          <h1 className="text-xl sm:text-2xl font-black text-[#0B1B3B] tracking-tight">
            Guardrailed AI Auto-Pricing &amp; Channel Strategy
          </h1>
        </div>
        <div className="flex flex-wrap gap-2">
          <button
            type="button"
            onClick={() => setPmsModalOpen(true)}
            className="px-3.5 py-2 rounded-xl bg-white border border-[#DCE7F8] text-xs font-bold text-[#0B1B3B] inline-flex items-center gap-1.5"
          >
            <Code2 className="w-3.5 h-3.5 text-blue-600" />
            Inspect PMS JSON
          </button>
          <button
            type="button"
            onClick={() => applyAiPricingNow()}
            className="px-4 py-2 rounded-xl bg-blue-600 text-white text-xs font-bold inline-flex items-center gap-1.5 hover:bg-blue-700"
          >
            <CheckCircle2 className="w-3.5 h-3.5" />
            Apply AI Price Move (${opsPlan.current_bar} → ${opsPlan.recommended_bar})
          </button>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-4">
        {/* Rules Form */}
        <form onSubmit={handleSubmit(onSubmitRules)} className="lg:col-span-5 ember-card p-5 space-y-3.5">
          <h2 className="text-sm font-extrabold text-[#0B1B3B]">Pricing Guardrails &amp; Telegram Thresholds</h2>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <div>
              <label className="block text-[10px] font-extrabold uppercase text-[#475B80] mb-1">Execution Mode</label>
              <select {...register('mode')} className="w-full px-3 py-2 text-xs font-bold rounded-xl border border-[#DCE7F8] bg-[#F7FAFF]">
                <option value="advisory">Advisory Only</option>
                <option value="semi_auto">Semi-Auto (1-Click Apply)</option>
                <option value="auto_pilot">Auto-Pilot (Within Guardrails)</option>
              </select>
            </div>
            <div>
              <label className="block text-[10px] font-extrabold uppercase text-[#475B80] mb-1">Comp Position</label>
              <select {...register('comp_position_target')} className="w-full px-3 py-2 text-xs font-bold rounded-xl border border-[#DCE7F8] bg-[#F7FAFF]">
                <option value="match_avg">Match Corridor Avg</option>
                <option value="below_avg_5pct">-5% Under Corridor</option>
                <option value="above_avg_5pct">+5% Luxury Premium</option>
              </select>
            </div>
            <div>
              <label className="block text-[10px] font-extrabold uppercase text-[#475B80] mb-1">Min BAR Floor ($)</label>
              <input type="number" {...register('min_bar_floor')} className="w-full px-3 py-2 text-xs font-bold rounded-xl border border-[#DCE7F8] bg-[#F7FAFF]" />
              {errors.min_bar_floor && <span className="text-[11px] font-bold text-rose-600">{errors.min_bar_floor.message}</span>}
            </div>
            <div>
              <label className="block text-[10px] font-extrabold uppercase text-[#475B80] mb-1">Max BAR Ceiling ($)</label>
              <input type="number" {...register('max_bar_ceiling')} className="w-full px-3 py-2 text-xs font-bold rounded-xl border border-[#DCE7F8] bg-[#F7FAFF]" />
              {errors.max_bar_ceiling && <span className="text-[11px] font-bold text-rose-600">{errors.max_bar_ceiling.message}</span>}
            </div>
            <div>
              <label className="block text-[10px] font-extrabold uppercase text-[#475B80] mb-1">Compression Trigger (%)</label>
              <input type="number" {...register('compression_occ_threshold')} className="w-full px-3 py-2 text-xs font-bold rounded-xl border border-[#DCE7F8] bg-[#F7FAFF]" />
            </div>
            <div>
              <label className="block text-[10px] font-extrabold uppercase text-[#475B80] mb-1">Compression Lift (+%)</label>
              <input type="number" {...register('compression_lift_pct')} className="w-full px-3 py-2 text-xs font-bold rounded-xl border border-[#DCE7F8] bg-[#F7FAFF]" />
            </div>
          </div>
          <div>
            <label className="block text-[10px] font-extrabold uppercase text-[#475B80] mb-1">Telegram Chat ID / Handle</label>
            <input {...register('telegram_chat_id')} placeholder="@avalon_sobe_rates" className="w-full px-3 py-2 text-xs rounded-xl border border-[#DCE7F8] bg-[#F7FAFF]" />
          </div>
          <button type="submit" className="w-full py-2 rounded-xl bg-[#0D255B] text-white text-xs font-bold hover:bg-blue-800">
            Save Guardrails
          </button>
        </form>

        {/* Live Recommendation Table */}
        <div className="lg:col-span-7 ember-card p-5 space-y-3">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <div>
              <span className="px-2.5 py-0.5 rounded-full bg-blue-50 text-blue-700 text-[10.5px] font-extrabold">
                {opsPlan.action_verdict} · {opsPlan.channel_directive}
              </span>
              <h2 className="text-sm font-extrabold text-[#0B1B3B] mt-1">
                Per-Category Recommended BAR (Comp Avg: ${opsPlan.comp_avg})
              </h2>
            </div>
            <Bot className="w-5 h-5 text-blue-600" />
          </div>

          <div className="ember-subtle-card p-3 text-xs space-y-1">
            {opsPlan.reasons.map((r, i) => (
              <div key={i} className="text-[#0B1B3B]">• {r}</div>
            ))}
          </div>

          <div className="overflow-x-auto rounded-2xl border border-[#DCE7F8]">
            <table className="w-full text-left text-xs border-collapse">
              <thead className="bg-[#F5F9FF] border-b border-[#DCE7F8]">
                <tr>
                  <th className="p-2.5 text-[10px] font-extrabold uppercase text-[#475B80]">Room Category</th>
                  <th className="p-2.5 text-[10px] font-extrabold uppercase text-[#475B80]">Sellable</th>
                  <th className="p-2.5 text-[10px] font-extrabold uppercase text-[#475B80]">Current</th>
                  <th className="p-2.5 text-[10px] font-extrabold uppercase text-[#475B80]">AI Rec</th>
                  <th className="p-2.5 text-[10px] font-extrabold uppercase text-[#475B80]">Channel</th>
                </tr>
              </thead>
              <tbody>
                {opsPlan.room_recommendations.map((rec) => (
                  <tr key={rec.code} className="border-b border-[#EEF4FD] last:border-b-0">
                    <td className="p-2.5 font-bold">{rec.name}</td>
                    <td className="p-2.5 tabular-nums">{rec.sellable} / {rec.total}</td>
                    <td className="p-2.5 tabular-nums">${rec.current_bar}</td>
                    <td className="p-2.5 font-black text-blue-700 tabular-nums">
                      ${rec.recommended_bar} ({rec.delta >= 0 ? `+${rec.delta}` : rec.delta})
                    </td>
                    <td className="p-2.5">
                      <span className={`px-2 py-0.5 rounded-full text-[10px] font-extrabold ${rec.stop_sell ? 'bg-rose-50 text-rose-700' : 'bg-emerald-50 text-emerald-700'}`}>
                        {rec.stop_sell ? 'STOP-SELL' : 'OPEN'}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>

      {/* Secure Live 2-Way PMS & Channel Manager Integration Bridge */}
      <div className="ember-card p-5 space-y-4">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full bg-emerald-50 border border-emerald-200 text-[10px] font-extrabold uppercase text-emerald-700">
              <ShieldCheck className="w-3 h-3" />
              Secure 2-Way Live Rate Push Architecture · Zero Unverified Claims
            </span>
            <h2 className="text-base font-extrabold text-[#0B1B3B] mt-1">
              Direct PMS &amp; Channel Manager API Connectors (Dynamic Live Sync)
            </h2>
            <p className="text-xs text-[#475B80] mt-0.5">
              Start in safe <b>Sandbox Payload Preview</b> today with zero PMS IT. When ready to push BAR, Stop-Sell, and Min-LOS live to OTAs, connect a property-scoped token with hard floor/ceiling clamps, max swing limits, and 1-click rollback.
            </p>
          </div>
          <div className="flex items-center gap-2">
            <span className="px-2.5 py-1 rounded-xl bg-amber-50 border border-amber-200 text-[10.5px] font-extrabold text-amber-800 inline-flex items-center gap-1">
              <Lock className="w-3 h-3" />
              {dryRunOnly ? 'Sandbox Dry-Run Active' : 'Approval Queue Mode'}
            </span>
            <button
              type="button"
              onClick={() => setPmsModalOpen(true)}
              className="px-3 py-1.5 rounded-xl bg-blue-600 text-white text-xs font-bold hover:bg-blue-700 inline-flex items-center gap-1.5"
            >
              <PlugZap className="w-3.5 h-3.5" />
              Inspect Live Wire Payload
            </button>
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-5 gap-2.5">
          {PMS_CONNECTORS.map((c) => {
            const active = selectedConnector === c.id
            return (
              <button
                key={c.id}
                type="button"
                onClick={() => setSelectedConnector(c.id)}
                className={`text-left p-3 rounded-2xl border transition ${
                  active
                    ? 'bg-blue-50/90 border-blue-500 ring-2 ring-blue-500/20'
                    : 'bg-[#F8FBFF] border-[#DCE7F8] hover:bg-blue-50/40'
                }`}
              >
                <div className="text-xs font-extrabold text-[#0B1B3B]">{c.name}</div>
                <div className="text-[10px] font-bold text-blue-700 mt-0.5">{c.protocol}</div>
                <div className="text-[10px] font-mono text-[#475B80] mt-1 truncate" title={c.endpoint}>{c.endpoint}</div>
                <div className="text-[10px] text-[#6D81A8] mt-1 leading-snug">{c.coverage}</div>
              </button>
            )
          })}
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-3 text-xs">
          <div className="ember-subtle-card p-3 space-y-1">
            <div className="text-[10px] font-extrabold uppercase text-blue-700">1. Credential Security</div>
            <div className="text-[#0B1B3B] font-semibold">OAuth 2.0 / Property-Scoped API Keys</div>
            <div className="text-[11px] text-[#475B80]">
              Stored encrypted server-side only (never in browser localStorage). Revocable per property anytime.
            </div>
          </div>
          <div className="ember-subtle-card p-3 space-y-1">
            <div className="text-[10px] font-extrabold uppercase text-blue-700">2. Hard Financial Guardrails</div>
            <div className="flex items-center justify-between gap-2">
              <span className="text-[#0B1B3B] font-semibold">Max Daily Swing Cap:</span>
              <select
                aria-label="Max daily BAR swing cap"
                value={maxSwingPct}
                onChange={(e) => setMaxSwingPct(Number(e.target.value))}
                className="px-2 py-0.5 rounded-lg border border-[#DCE7F8] bg-white text-xs font-bold"
              >
                <option value={10}>±10% max</option>
                <option value={15}>±15% max</option>
                <option value={20}>±20% max</option>
              </select>
            </div>
            <div className="text-[11px] text-[#475B80]">
              Clamped strictly between Floor (${opsPlan.rules.min_bar_floor}) &amp; Ceiling (${opsPlan.rules.max_bar_ceiling}) with Idempotency-Key protection.
            </div>
          </div>
          <div className="ember-subtle-card p-3 space-y-1.5">
            <div className="text-[10px] font-extrabold uppercase text-blue-700">3. Safe Rollout &amp; Rollback</div>
            <label className="flex items-center gap-2 font-semibold text-[#0B1B3B] cursor-pointer">
              <input
                type="checkbox"
                checked={dryRunOnly}
                onChange={(e) => setDryRunOnly(e.target.checked)}
                className="rounded border-blue-300"
              />
              <span>Dry-Run Sandbox Only (No external push)</span>
            </label>
            <button
              type="button"
              onClick={() =>
                pushToast({
                  tone: 'info',
                  title: 'Rollback Snapshot Verified',
                  detail: `Prior BAR ($${opsPlan.current_bar}/nt) is preserved in audit log for instant restore.`,
                })
              }
              className="inline-flex items-center gap-1 text-[11px] font-bold text-blue-700 hover:underline"
            >
              <RotateCcw className="w-3 h-3" />
              Test 1-Click BAR Rollback Guard
            </button>
          </div>
        </div>
      </div>

      {/* Audit Log DataTable */}
      <div className="ember-card p-5">
        <h2 className="text-sm font-extrabold text-[#0B1B3B] mb-3">Applied AI Pricing Audit Log</h2>
        <DataTable
          data={opsPlan.recent_actions}
          columns={auditColumns}
          density={density}
          searchPlaceholder="Filter pricing history..."
          csvFilename="hotelrateintel-ai-pricing-log.csv"
          csvHeaders={['Old BAR', 'New BAR', 'Sellable Rooms', 'Net Occ %', 'Reason']}
          csvRowMapper={(a) => [a.old_bar, a.new_bar, a.sellable_rooms, a.net_occupancy_pct, a.reason]}
        />
      </div>

      <ModalDialog
        open={pmsModalOpen}
        onClose={() => setPmsModalOpen(false)}
        title={`Live API Wire Format — ${PMS_CONNECTORS.find((c) => c.id === selectedConnector)?.name || 'PMS'}`}
        subtitle={`${PMS_CONNECTORS.find((c) => c.id === selectedConnector)?.auth || ''} · Dry-Run Verified`}
      >
        <div className="space-y-3">
          <div className="flex flex-wrap gap-1.5">
            {PMS_CONNECTORS.map((c) => (
              <button
                key={c.id}
                type="button"
                onClick={() => setSelectedConnector(c.id)}
                className={`px-2.5 py-1 rounded-lg text-[11px] font-bold border ${
                  selectedConnector === c.id
                    ? 'bg-blue-600 text-white border-blue-600'
                    : 'bg-[#F5F9FF] text-[#0B1B3B] border-[#DCE7F8]'
                }`}
              >
                {c.name.split(' ')[0]}
              </button>
            ))}
          </div>
          <pre className="p-3.5 rounded-2xl bg-[#06122E] text-blue-100 text-xs overflow-x-auto max-h-[340px]">
            {formattedWirePayload}
          </pre>
          <button
            type="button"
            onClick={() => {
              navigator.clipboard?.writeText(formattedWirePayload)
              pushToast({ tone: 'success', title: 'Copied Live Connector Payload' })
            }}
            className="px-4 py-2 rounded-xl bg-blue-600 text-white text-xs font-bold inline-flex items-center gap-1.5"
          >
            <Copy className="w-3.5 h-3.5" />
            Copy Connector Payload
          </button>
        </div>
      </ModalDialog>
    </div>
  )
}
