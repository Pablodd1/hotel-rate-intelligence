import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import type {
  AiPricingPlan,
  AutoPricingRules,
  CallLogItem,
  ClientPortalPayload,
  CompetitorInquiryItem,
  DateRangeKey,
  DensityMode,
  RoomEquivalencyResponse,
  RoomOpsState,
  TierId,
  ToastMessage,
} from '../types/hospitality'
import {
  AI_PRICING_PLAN_SEED,
  INQUIRIES_SEED,
  PORTAL_DEMO_SEED,
  ROOM_EQUIVALENCY_SEED,
} from '../data/demoSeed'

interface PortalStoreState {
  isLiveBackend: boolean
  isLoading: boolean
  clientToken: string
  demoHotelId: string | null
  previewTier: TierId | null
  dateRange: DateRangeKey
  density: DensityMode
  globalSearch: string
  portal: ClientPortalPayload
  opsPlan: AiPricingPlan
  roomEquivalency: RoomEquivalencyResponse
  inquiries: CompetitorInquiryItem[]
  toasts: ToastMessage[]

  setGlobalSearch: (q: string) => void
  setDateRange: (range: DateRangeKey) => void
  setDensity: (density: DensityMode) => void
  pushToast: (toast: Omit<ToastMessage, 'id'>) => void
  dismissToast: (id: string) => void
  setAuthParams: (token: string, demoHotelId: string | null) => void

  hydratePortal: (demoHotelOverride?: string | null, tierOverride?: TierId | null) => Promise<void>
  fetchRoomEquivalency: (tier?: string, occ?: string, rollaway?: boolean) => Promise<void>
  saveRoomOps: (nextOps: Partial<RoomOpsState>) => Promise<void>
  saveAutoPricingRules: (nextRules: Partial<AutoPricingRules>) => Promise<void>
  applyAiPricingNow: () => Promise<void>
  sendTelegramAlert: (message: string, tags: string[]) => Promise<string>
  scrapeCompSet: () => Promise<void>
  addTag: (hotelId: number, tag: string, note: string, color?: string) => Promise<void>
  deleteTag: (tagId: number) => Promise<void>
  logCourtesyCall: (payload: Omit<CallLogItem, 'id' | 'called_at' | 'status'>) => Promise<void>
  createCompInquiry: (payload: { targetHotelId?: number | null; targetHotelName: string; targetEmail?: string; inquiryType: string; roomsRequested: number; quotedRate?: number | null }) => Promise<void>
  saveAlertSettings: (alertEmail: string, telegramChatId: string) => Promise<void>
  resetDemoData: () => void
}

function buildAuthQuery(token: string, demoHotelId: string | null, extra?: Record<string, string>): string {
  const params = new URLSearchParams()
  if (demoHotelId) params.set('demo_hotel', demoHotelId)
  else if (!token) params.set('demo', '1')
  if (extra) {
    Object.entries(extra).forEach(([k, v]) => {
      if (v) params.set(k, v)
    })
  }
  const s = params.toString()
  return s ? `?${s}` : ''
}

function recalculateOpsMetrics(ops: RoomOpsState): RoomOpsState {
  const total = Math.max(1, Number(ops.total_rooms || 1))
  const ooo = Math.max(0, Number(ops.ooo_rooms || 0))
  const oos = Math.max(0, Number(ops.oos_rooms || 0))
  const hk = Math.max(0, Number(ops.housekeeping_hold || 0))
  const offline = Math.min(total, ooo + oos + hk)
  const sellable = Math.max(0, total - offline)
  const sold = Math.max(0, Math.min(total, Number(ops.rooms_sold || 0)))
  const remaining = Math.max(0, sellable - sold)
  const grossOcc = Number(((sold / total) * 100).toFixed(1))
  const netOcc = sellable === 0 ? 100 : Number(Math.min(100, (sold / sellable) * 100).toFixed(1))

  return {
    ...ops,
    total_rooms: total,
    rooms_sold: sold,
    ooo_rooms: ooo,
    oos_rooms: oos,
    housekeeping_hold: hk,
    offline_rooms: offline,
    sellable_rooms: sellable,
    remaining_to_sell: remaining,
    gross_occupancy_pct: grossOcc,
    net_occupancy_pct: netOcc,
    occupancy_compression_delta: Number((netOcc - grossOcc).toFixed(1)),
  }
}

export const usePortalStore = create<PortalStoreState>()(
  persist(
    (set, get) => ({
      isLiveBackend: false,
      isLoading: false,
      clientToken: '',
      demoHotelId: null,
      previewTier: null,
      dateRange: 'today',
      density: 'compact',
      globalSearch: '',
      portal: PORTAL_DEMO_SEED,
      opsPlan: AI_PRICING_PLAN_SEED,
      roomEquivalency: ROOM_EQUIVALENCY_SEED,
      inquiries: INQUIRIES_SEED,
      toasts: [],

      setGlobalSearch: (globalSearch) => set({ globalSearch }),
      setDateRange: (dateRange) => set({ dateRange }),
      setDensity: (density) => set({ density }),

      pushToast: (toast) => {
        const id = `${Date.now()}-${Math.random().toString(36).slice(2, 7)}`
        set((s) => ({ toasts: [...s.toasts.slice(-3), { ...toast, id }] }))
        if (typeof window !== 'undefined') {
          setTimeout(() => {
            get().dismissToast(id)
          }, 4200)
        }
      },

      dismissToast: (id) => set((s) => ({ toasts: s.toasts.filter((t) => t.id !== id) })),

      setAuthParams: (clientToken, demoHotelId) => set({ clientToken, demoHotelId }),

      hydratePortal: async (demoHotelOverride, tierOverride) => {
        const state = get()
        const dh = demoHotelOverride !== undefined ? demoHotelOverride : state.demoHotelId
        const pt = tierOverride !== undefined ? tierOverride : state.previewTier
        if (demoHotelOverride !== undefined || tierOverride !== undefined) {
          set({ demoHotelId: dh, previewTier: pt })
        }
        set({ isLoading: true })
        const hdrs: Record<string, string> = state.clientToken ? { 'X-Client-Token': state.clientToken } : {}
        const q = buildAuthQuery(state.clientToken, dh, pt ? { preview_tier: pt } : undefined)
        const qOps = buildAuthQuery(state.clientToken, dh)
        try {
          const [pRes, oRes, eqRes] = await Promise.all([
            fetch(`/api/client/portal${q}`, { headers: hdrs }),
            fetch(`/api/client/ops${qOps}`, { headers: hdrs }),
            fetch(`/api/client/room-compare${qOps}${qOps ? '&' : '?'}tier=suite_vs_suite&occ=double&rollaway=1`, { headers: hdrs }),
          ])
          if (pRes.ok) {
            const pJson = (await pRes.json()) as ClientPortalPayload
            if (pJson?.ok) {
              set({ portal: pJson, isLiveBackend: true })
            }
          }
          if (oRes.ok) {
            const oJson = await oRes.json()
            if (oJson?.ok && oJson.plan) {
              set({ opsPlan: oJson.plan, inquiries: oJson.inquiries || get().inquiries })
            }
          }
          if (eqRes.ok) {
            const eqJson = (await eqRes.json()) as RoomEquivalencyResponse
            if (eqJson?.ok) {
              set({ roomEquivalency: eqJson })
            }
          }
        } catch {
          // Offline / test environment gracefully keeps deterministic Demo Data with explicit badge
        } finally {
          set({ isLoading: false })
        }
      },

      fetchRoomEquivalency: async (tier = 'suite_vs_suite', occ = 'double', rollaway = false) => {
        const s = get()
        const q = buildAuthQuery(s.clientToken, s.demoHotelId, {
          tier,
          occ,
          rollaway: rollaway ? '1' : '0',
        })
        try {
          const res = await fetch(`/api/client/room-compare${q}`, {
            headers: s.clientToken ? { 'X-Client-Token': s.clientToken } : {},
          })
          if (res.ok) {
            const data = (await res.json()) as RoomEquivalencyResponse
            if (data?.ok) {
              set({ roomEquivalency: data, isLiveBackend: true })
              return
            }
          }
        } catch {
          // Local deterministic recalculation fallback
        }

        const multMap: Record<string, { label: string; rule: string; mult: number; roll: boolean }> = {
          standard_king: { label: 'Standard King / Queen (Entry BAR)', rule: 'Standard King vs. Competitor Standard King/Queen', mult: 1.0, roll: false },
          double_double: { label: 'Two Doubles / Two Queens (DD / QQ)', rule: 'Double-Double vs. Competitor Double-Double / Two Queens', mult: 1.14, roll: true },
          suite_vs_suite: { label: 'Junior / 1-Bedroom Suite (Suite vs. Suite)', rule: 'Suite vs. Competitor Equivalent Suite ONLY', mult: 1.48, roll: true },
          ocean_balcony: { label: 'Oceanview / Balcony Corner Upgrade', rule: 'Ocean/Balcony vs. Competitor Ocean/Balcony Category', mult: 1.32, roll: true },
        }
        const cfg = multMap[tier] || multMap.suite_vs_suite
        const extraAdult = occ === 'triple_quad' ? 30 : 0
        const items = ROOM_EQUIVALENCY_SEED.items.map((it) => {
          const catBar = Math.round(it.scraped_base_bar * cfg.mult + extraAdult)
          const rollFee = rollaway && cfg.roll ? 35 : 0
          const tax = Math.round((catBar + it.resort_fee + rollFee) * (it.tax_pct / 100))
          const otd = catBar + it.resort_fee + rollFee + tax
          return {
            ...it,
            matched_category: cfg.label,
            occupancy: occ,
            category_bar: catBar,
            rollaway_allowed: cfg.roll,
            rollaway_fee: rollFee,
            true_otd_total: otd,
          }
        })
        const primaryOtd = items.find((i) => i.is_primary)?.true_otd_total || items[0]?.true_otd_total || 0
        const finalItems = items.map((i) => ({ ...i, spread_vs_my_otd: i.true_otd_total - primaryOtd }))
        const comps = finalItems.filter((i) => !i.is_primary)
        const compAvg = comps.length ? Math.round(comps.reduce((acc, x) => acc + x.true_otd_total, 0) / comps.length) : primaryOtd
        set({
          roomEquivalency: {
            ...get().roomEquivalency,
            occupancy: occ,
            include_rollaway: rollaway,
            room_tier: { ...get().roomEquivalency.room_tier, id: tier, label: cfg.label, match_rule: cfg.rule, mult: cfg.mult, rollaway_supported: cfg.roll },
            my_true_otd: primaryOtd,
            comp_avg_otd: compAvg,
            otd_advantage: compAvg - primaryOtd,
            items: finalItems,
          },
        })
      },

      saveRoomOps: async (nextOps) => {
        const s = get()
        const merged = recalculateOpsMetrics({ ...s.opsPlan.ops, ...nextOps })
        // Optimistically recompute AI verdict locally first
        const rules = s.opsPlan.rules
        const curBar = s.opsPlan.current_bar
        let recBar = curBar
        let verdict = 'HOLD_BAR'
        let directive = 'OPEN_ALL_CHANNELS'
        const reasons: string[] = []

        if (merged.status_flags.includes('SOLD_OUT') || merged.remaining_to_sell <= 0) {
          verdict = 'STOP_SELL_SOLD_OUT'
          directive = 'STOP_SELL_ALL_OTAS'
          recBar = Math.min(rules.max_bar_ceiling, Math.round(curBar * 1.25))
          reasons.push(`0 sellable rooms left (${merged.ooo_rooms} OOO, ${merged.oos_rooms} OOS, ${merged.housekeeping_hold} HK Hold). Trigger Stop-Sell across OTAs.`)
        } else if (merged.net_occupancy_pct >= rules.compression_occ_threshold || merged.remaining_to_sell <= 3) {
          verdict = 'RAISE_BAR_COMPRESSION'
          directive = 'CLOSE_DISCOUNT_OTAS_DIRECT_ONLY'
          recBar = Math.min(rules.max_bar_ceiling, Math.round(Math.max(curBar * (1 + rules.compression_lift_pct / 100), s.opsPlan.comp_avg * 1.05)))
          reasons.push(`True Net Occupancy hit ${merged.net_occupancy_pct}% with ${merged.offline_rooms} offline rooms (${merged.remaining_to_sell} left) -> lift BAR +${rules.compression_lift_pct}% & close discount OTAs.`)
        } else {
          reasons.push(`Sellable inventory is ${merged.sellable_rooms} rooms (${merged.net_occupancy_pct}% net occ) — aligned with ${s.opsPlan.comp_avg} corridor avg.`)
        }
        recBar = Math.max(rules.min_bar_floor, Math.min(rules.max_bar_ceiling, recBar))
        const ratio = recBar / Math.max(1, curBar)
        const roomRecs = (merged.room_types || []).map((rt) => {
          const avail = Math.max(0, rt.total - rt.ooo - rt.oos)
          const rBar = Math.round(rt.bar * ratio)
          return {
            code: rt.code,
            name: rt.name,
            total: rt.total,
            ooo: rt.ooo,
            oos: rt.oos,
            sellable: avail,
            current_bar: rt.bar,
            recommended_bar: rBar,
            delta: rBar - rt.bar,
            stop_sell: rt.stop_sell || avail === 0 || directive === 'STOP_SELL_ALL_OTAS',
          }
        })

        set((prev) => ({
          opsPlan: {
            ...prev.opsPlan,
            ops: merged,
            recommended_bar: recBar,
            delta_dollars: recBar - curBar,
            delta_pct: Number((((recBar - curBar) / Math.max(1, curBar)) * 100).toFixed(1)),
            action_verdict: verdict,
            channel_directive: directive,
            reasons,
            trigger_tags: merged.operational_tags,
            room_recommendations: roomRecs,
          },
        }))

        const q = buildAuthQuery(s.clientToken, s.demoHotelId)
        try {
          const res = await fetch(`/api/client/ops/inventory${q}`, {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
              ...(s.clientToken ? { 'X-Client-Token': s.clientToken } : {}),
            },
            body: JSON.stringify(merged),
          })
          if (res.ok) {
            const d = await res.json()
            if (d?.ok && d.plan) {
              set({ opsPlan: d.plan, isLiveBackend: true })
            }
          }
        } catch {
          // Local persisted state already updated
        }
        get().pushToast({
          tone: 'success',
          title: 'Room Inventory Updated',
          detail: `Sellable: ${merged.sellable_rooms} rms · Net Occ: ${merged.net_occupancy_pct}% · AI Target: $${recBar}`,
        })
      },

      saveAutoPricingRules: async (nextRules) => {
        const s = get()
        const updatedRules = { ...s.opsPlan.rules, ...nextRules }
        set((prev) => ({ opsPlan: { ...prev.opsPlan, rules: updatedRules } }))
        const q = buildAuthQuery(s.clientToken, s.demoHotelId)
        try {
          const res = await fetch(`/api/client/ops/rules${q}`, {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
              ...(s.clientToken ? { 'X-Client-Token': s.clientToken } : {}),
            },
            body: JSON.stringify(updatedRules),
          })
          if (res.ok) {
            const d = await res.json()
            if (d?.ok && d.plan) {
              set({ opsPlan: d.plan, isLiveBackend: true })
            }
          }
        } catch {
          // Offline mode OK
        }
        get().pushToast({
          tone: 'success',
          title: 'Auto-Pricing Guardrails Saved',
          detail: `Mode: ${updatedRules.mode.toUpperCase()} · Floor $${updatedRules.min_bar_floor} / Ceiling $${updatedRules.max_bar_ceiling}`,
        })
      },

      applyAiPricingNow: async () => {
        const s = get()
        const oldBar = s.opsPlan.current_bar
        const newBar = s.opsPlan.recommended_bar
        const newAction = {
          id: Date.now(),
          hotel_id: s.opsPlan.hotel_id,
          room_category: 'All Room Types (BAR)',
          old_bar: oldBar,
          new_bar: newBar,
          sellable_rooms: s.opsPlan.ops.sellable_rooms,
          net_occupancy_pct: s.opsPlan.ops.net_occupancy_pct,
          trigger_tags: JSON.stringify(s.opsPlan.trigger_tags || []),
          reason: s.opsPlan.reasons.join(' | '),
          action_status: 'applied',
          created_at: Math.floor(Date.now() / 1000),
        }
        set((prev) => ({
          opsPlan: {
            ...prev.opsPlan,
            current_bar: newBar,
            delta_dollars: 0,
            delta_pct: 0,
            recent_actions: [newAction, ...(prev.opsPlan.recent_actions || [])].slice(0, 15),
          },
          portal: {
            ...prev.portal,
            primary_hotel: { ...prev.portal.primary_hotel, price: newBar },
            strategy: { ...prev.portal.strategy, my_bar: newBar },
          },
        }))

        const q = buildAuthQuery(s.clientToken, s.demoHotelId)
        try {
          const res = await fetch(`/api/client/ops/apply-pricing${q}`, {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
              ...(s.clientToken ? { 'X-Client-Token': s.clientToken } : {}),
            },
            body: JSON.stringify({ send_telegram: true }),
          })
          if (res.ok) {
            const d = await res.json()
            if (d?.ok && d.plan) {
              set({ opsPlan: d.plan, isLiveBackend: true })
            }
          }
        } catch {
          // Persisted locally
        }
        get().pushToast({
          tone: 'success',
          title: `AI Price Change Applied ($${oldBar} -> $${newBar})`,
          detail: 'PMS payload ready & audit log updated.',
        })
      },

      sendTelegramAlert: async (message, tags) => {
        const s = get()
        const ops = s.opsPlan.ops
        const preview = `HotelRateIntel OPS ALERT · ${s.opsPlan.hotel_name}\nTags: ${tags.join(' ')}\nSellable: ${ops.sellable_rooms}/${ops.total_rooms} (OOO: ${ops.ooo_rooms} · OOS: ${ops.oos_rooms} · HK: ${ops.housekeeping_hold}) | Net Occ: ${ops.net_occupancy_pct}%\nBAR Rec: $${s.opsPlan.recommended_bar} | Note: ${message || ops.notes}`
        const q = buildAuthQuery(s.clientToken, s.demoHotelId)
        try {
          const res = await fetch(`/api/client/ops/telegram-alert${q}`, {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
              ...(s.clientToken ? { 'X-Client-Token': s.clientToken } : {}),
            },
            body: JSON.stringify({ message, tags }),
          })
          if (res.ok) {
            const d = await res.json()
            get().pushToast({
              tone: 'info',
              title: d.telegram_sent ? 'Telegram Alert Dispatched Live' : 'Telegram Shift Alert Staged',
              detail: `${tags.join(' ')} (${ops.sellable_rooms} sellable rooms)`,
            })
            return d.message_preview || preview
          }
        } catch {
          // Offline preview
        }
        get().pushToast({ tone: 'info', title: 'Telegram Shift Alert Ready', detail: tags.join(' ') })
        return preview
      },

      scrapeCompSet: async () => {
        const s = get()
        const q = buildAuthQuery(s.clientToken, s.demoHotelId)
        set({ isLoading: true })
        try {
          const res = await fetch(`/api/client/scrape${q}`, {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
              ...(s.clientToken ? { 'X-Client-Token': s.clientToken } : {}),
            },
            body: JSON.stringify({}),
          })
          if (res.ok) {
            await get().hydratePortal()
          }
        } catch {
          // Local timestamp bump
        } finally {
          set({ isLoading: false })
        }
        get().pushToast({
          tone: 'success',
          title: 'Comp-Set Rate Scrape Refreshed',
          detail: 'Latest public Direct BAR & multi-OTA parity quotes loaded.',
        })
      },

      addTag: async (hotelId, tag, note, color = '#2563EB') => {
        const s = get()
        const hotelName = s.portal.comp_set.find((h) => (h.hotel_id || h.id) === hotelId)?.name || `Hotel #${hotelId}`
        const newTag = {
          id: Date.now(),
          hotel_id: hotelId,
          hotel_name: hotelName,
          tag,
          note,
          color,
          created_at: Math.floor(Date.now() / 1000),
        }
        set((prev) => ({
          portal: {
            ...prev.portal,
            tags: [newTag, ...prev.portal.tags],
            comp_set: prev.portal.comp_set.map((h) =>
              (h.hotel_id || h.id) === hotelId ? { ...h, tags: [newTag, ...(h.tags || [])] } : h
            ),
          },
        }))
        const q = buildAuthQuery(s.clientToken, s.demoHotelId)
        try {
          await fetch(`/api/client/tags${q}`, {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
              ...(s.clientToken ? { 'X-Client-Token': s.clientToken } : {}),
            },
            body: JSON.stringify({ hotel_id: hotelId, tag, note, color }),
          })
        } catch {
          // Local persisted
        }
        get().pushToast({ tone: 'success', title: 'Strategy Tag Saved', detail: `${hotelName}: ${tag}` })
      },

      deleteTag: async (tagId) => {
        const s = get()
        set((prev) => ({
          portal: {
            ...prev.portal,
            tags: prev.portal.tags.filter((t) => t.id !== tagId),
            comp_set: prev.portal.comp_set.map((h) => ({
              ...h,
              tags: (h.tags || []).filter((t) => t.id !== tagId),
            })),
          },
        }))
        const q = buildAuthQuery(s.clientToken, s.demoHotelId)
        try {
          await fetch(`/api/client/tags${q}`, {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
              ...(s.clientToken ? { 'X-Client-Token': s.clientToken } : {}),
            },
            body: JSON.stringify({ delete_id: tagId }),
          })
        } catch {
          // Local persisted
        }
        get().pushToast({ tone: 'info', title: 'Strategy Tag Removed' })
      },

      logCourtesyCall: async (payload) => {
        const s = get()
        const entry: CallLogItem = {
          ...payload,
          id: Date.now(),
          status: 'completed_logged',
          called_at: Math.floor(Date.now() / 1000),
        }
        set((prev) => ({
          portal: {
            ...prev.portal,
            call_logs: [entry, ...prev.portal.call_logs],
          },
        }))
        const q = buildAuthQuery(s.clientToken, s.demoHotelId)
        try {
          await fetch(`/api/client/calls${q}`, {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
              ...(s.clientToken ? { 'X-Client-Token': s.clientToken } : {}),
            },
            body: JSON.stringify({
              hotel_id: payload.hotel_id,
              shift: payload.shift,
              caller_mode: payload.caller_mode,
              reported_occupancy_pct: payload.reported_occupancy_pct,
              rooms_left: payload.rooms_left,
              quoted_walkin_rate: payload.quoted_walkin_rate,
              questions_asked: payload.questions_asked,
              transcript: payload.transcript,
            }),
          })
        } catch {
          // Persisted
        }
        get().pushToast({
          tone: 'success',
          title: 'Overnight Call Logged',
          detail: `${payload.hotel_name || 'Competitor'}: $${payload.quoted_walkin_rate ?? '—'} walk-in BAR`,
        })
      },

      createCompInquiry: async ({ targetHotelId, targetHotelName, targetEmail, inquiryType, roomsRequested, quotedRate }) => {
        const s = get()
        const draft: CompetitorInquiryItem = {
          id: Date.now(),
          requester_hotel_id: s.opsPlan.hotel_id,
          target_hotel_id: targetHotelId || null,
          target_hotel_name: targetHotelName,
          target_email: targetEmail || 'frontdesk@hotel.com',
          inquiry_type: inquiryType,
          rooms_requested: roomsRequested,
          subject: `Quick Miami neighbor check — availability & BAR (${roomsRequested} rm)`,
          body: `Hi ${targetHotelName} Reservations Team, updating our Miami walk-in & overflow referral swap list for ${roomsRequested} room(s).`,
          quoted_rate: quotedRate ?? null,
          status: quotedRate ? 'replied_logged' : 'drafted_ready_to_send',
          created_at: Math.floor(Date.now() / 1000),
        }
        set((prev) => ({ inquiries: [draft, ...prev.inquiries] }))
        const q = buildAuthQuery(s.clientToken, s.demoHotelId)
        try {
          const res = await fetch(`/api/client/ops/comp-inquiry${q}`, {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
              ...(s.clientToken ? { 'X-Client-Token': s.clientToken } : {}),
            },
            body: JSON.stringify({
              target_hotel_id: targetHotelId,
              target_hotel_name: targetHotelName,
              target_email: targetEmail,
              inquiry_type: inquiryType,
              rooms_requested: roomsRequested,
              quoted_rate: quotedRate,
            }),
          })
          if (res.ok) {
            const d = await res.json()
            if (d?.ok && Array.isArray(d.inquiries)) {
              set({ inquiries: d.inquiries, isLiveBackend: true })
            }
          }
        } catch {
          // Local persisted
        }
        get().pushToast({
          tone: 'success',
          title: quotedRate ? 'Competitor Reply Rate Logged' : 'Courtesy Email Inquiry Drafted',
          detail: `${targetHotelName}${quotedRate ? ` · $${quotedRate}/nt` : ''}`,
        })
      },

      saveAlertSettings: async (alertEmail, telegramChatId) => {
        const s = get()
        set((prev) => ({
          portal: {
            ...prev.portal,
            account: { ...prev.portal.account, alert_email: alertEmail, telegram_chat_id: telegramChatId },
          },
          opsPlan: {
            ...prev.opsPlan,
            rules: { ...prev.opsPlan.rules, telegram_chat_id: telegramChatId },
          },
        }))
        const q = buildAuthQuery(s.clientToken, s.demoHotelId)
        try {
          await fetch(`/api/client/settings${q}`, {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
              ...(s.clientToken ? { 'X-Client-Token': s.clientToken } : {}),
            },
            body: JSON.stringify({ action: 'update', alert_email: alertEmail, telegram_chat_id: telegramChatId }),
          })
        } catch {
          // Persisted
        }
        get().pushToast({
          tone: 'success',
          title: '6:00 AM Brief Delivery Updated',
          detail: `${alertEmail} · ${telegramChatId || 'Default bot chat'}`,
        })
      },

      resetDemoData: () => {
        set({
          portal: PORTAL_DEMO_SEED,
          opsPlan: AI_PRICING_PLAN_SEED,
          roomEquivalency: ROOM_EQUIVALENCY_SEED,
          inquiries: INQUIRIES_SEED,
          previewTier: null,
          dateRange: 'today',
          globalSearch: '',
        })
        get().pushToast({
          tone: 'info',
          title: 'Demo Dataset Restored',
          detail: 'All inventory changes, tags, call logs, and pricing actions reset cleanly.',
        })
      },
    }),
    {
      name: 'hri_ember_v20_state',
      partialize: (s) => ({
        clientToken: s.clientToken,
        demoHotelId: s.demoHotelId,
        previewTier: s.previewTier,
        dateRange: s.dateRange,
        density: s.density,
        portal: s.portal,
        opsPlan: s.opsPlan,
        roomEquivalency: s.roomEquivalency,
        inquiries: s.inquiries,
      }),
    }
  )
)
