export type DateRangeKey = 'today' | '7d' | '30d' | 'art_basel'
export type DensityMode = 'compact' | 'comfortable'
export type TierId = 'free' | 'core_99' | 'pro_199' | 'portfolio_399'
export type ParityStatus = 'UNDERCUT' | 'PARITY' | 'DIRECT_WIN'

export interface OtaChannelQuote {
  name: string
  rate: number
  code?: string
  url?: string
}

export interface StrategyTag {
  id: number
  account_id?: number
  hotel_id: number
  hotel_name?: string
  tag: string
  note?: string
  color?: string
  created_at?: number
}

export interface HotelRateRow {
  id: number
  hotel_id?: number
  name: string
  area: string
  stars?: number
  est_rooms?: number
  booking_engine?: string
  price: number | null
  prev_price?: number | null
  delta_pct: number
  checkin?: string
  parity_status: ParityStatus | string
  undercut_pct: number
  ota_channels: OtaChannelQuote[]
  est_occupancy_pct: number
  pricing_personality: string
  decision_logic?: string
  is_primary?: boolean
  tags?: StrategyTag[]
  phone?: string
}

export interface RoomCategoryItem {
  code: string
  name: string
  total: number
  ooo: number
  oos: number
  bar: number
  stop_sell: boolean
}

export interface RoomOpsState {
  hotel_id: number
  total_rooms: number
  rooms_sold: number
  ooo_rooms: number
  oos_rooms: number
  housekeeping_hold: number
  offline_rooms: number
  sellable_rooms: number
  remaining_to_sell: number
  gross_occupancy_pct: number
  net_occupancy_pct: number
  occupancy_compression_delta: number
  status_flags: string[]
  operational_tags: string[]
  room_types: RoomCategoryItem[]
  notes: string
  updated_by?: string
  updated_at?: number
}

export interface AutoPricingRules {
  hotel_id: number
  mode: 'advisory' | 'semi_auto' | 'auto_pilot'
  min_bar_floor: number
  max_bar_ceiling: number
  compression_occ_threshold: number
  compression_lift_pct: number
  parity_auto_protect: number | boolean
  comp_position_target: 'match_avg' | 'below_avg_5pct' | 'above_avg_5pct'
  telegram_alerts_enabled: number | boolean
  telegram_chat_id: string
  alert_tags: string[]
}

export interface RoomRecommendationItem {
  code: string
  name: string
  total: number
  ooo: number
  oos: number
  sellable: number
  current_bar: number
  recommended_bar: number
  delta: number
  stop_sell: boolean
}

export interface PricingActionRecord {
  id: number
  hotel_id: number
  room_category: string
  old_bar: number
  new_bar: number
  sellable_rooms: number
  net_occupancy_pct: number
  trigger_tags: string
  reason: string
  action_status: string
  pms_payload?: string
  created_at: number
}

export interface AiPricingPlan {
  hotel_id: number
  hotel_name: string
  current_bar: number
  recommended_bar: number
  delta_dollars: number
  delta_pct: number
  comp_avg: number
  action_verdict: string
  channel_directive: string
  reasons: string[]
  trigger_tags: string[]
  ops: RoomOpsState
  rules: AutoPricingRules
  room_recommendations: RoomRecommendationItem[]
  pms_payload: Record<string, unknown>
  recent_actions: PricingActionRecord[]
  status_flag_catalog: { id: string; label: string }[]
  default_ops_tags: string[]
}

export interface RoomEquivalencyItem {
  hotel_id: number
  name: string
  area: string
  stars: number
  is_primary: boolean
  scraped_base_bar: number
  matched_category: string
  occupancy: string
  category_bar: number
  resort_fee: number
  rollaway_allowed: boolean
  rollaway_fee: number
  hk_cadence: string
  tax_pct: number
  true_otd_total: number
  parity_status: string
  spread_vs_my_otd: number
}

export interface RoomEquivalencyResponse {
  ok: boolean
  room_tier: {
    id: string
    label: string
    match_rule: string
    mult: number
    max_occ: number
    rollaway_supported: boolean
    rollaway_note: string
  }
  occupancy: string
  include_rollaway: boolean
  my_true_otd: number | null
  comp_avg_otd: number
  otd_advantage: number
  items: RoomEquivalencyItem[]
}

export interface MemoryEvent {
  id: number
  hotel_id: number
  hotel_name?: string
  area?: string
  event_type: string
  old_price?: number
  new_price?: number
  delta_pct?: number
  est_occupancy_pct?: number
  competitor_pattern?: string
  ai_recommendation?: string
  recorded_at?: number
}

export interface CallLogItem {
  id: number
  hotel_id: number
  hotel_name?: string
  shift: string
  caller_mode: string
  phone_dialed?: string
  reported_occupancy_pct?: number | null
  rooms_left?: number | null
  quoted_walkin_rate?: number | null
  questions_asked?: string
  transcript?: string
  status: string
  called_at: number
}

export interface CompetitorInquiryItem {
  id: number
  requester_hotel_id: number
  target_hotel_id?: number | null
  target_hotel_name: string
  target_email?: string
  inquiry_type: string
  checkin?: string
  rooms_requested?: number
  subject?: string
  body: string
  quoted_rate?: number | null
  status: string
  created_at: number
}

export interface TierPlan {
  tier_id: TierId
  name: string
  badge: string
  monthly_price: number
  intro_price: number
  max_competitors: number
  allow_live_scrape: boolean
  allow_daily_email_telegram: boolean
  allow_memory_engine: boolean
  allow_courtesy_calls: boolean
  allow_instant_sms_alerts: boolean
  allow_custom_tags: boolean
  staff_hours_saved_mo: number
  labor_dollars_saved_mo: number
  est_revenue_recovered_mo: number
  headline: string
  who_for: string
  features: string[]
  locked_features: string[]
}

export interface CompressionEvent {
  dates: string
  event: string
  recommended_lift: string
}

export interface ClientPortalPayload {
  ok: boolean
  isolated_tenant: boolean
  account: {
    id: number
    username: string
    email: string
    display_name: string
    contact_person?: string
    primary_hotel_id: number
    assigned_hotel_ids: number[]
    tier: TierId
    monthly_price: number
    alert_email?: string
    telegram_chat_id?: string
  }
  active_tier: TierPlan
  all_tiers: TierPlan[]
  hidden_by_tier_count: number
  total_assigned_in_account: number
  primary_hotel: HotelRateRow
  comp_set: HotelRateRow[]
  strategy: {
    my_bar: number
    comp_avg_bar: number
    spread_vs_comp: number
    undercut_count_in_comp: number
    recommended_action: string
    recommended_target_bar: number
    explanation: string
    staff_hours_saved_mo: number
    labor_dollars_saved_mo: number
    est_revenue_recovered_mo: number
  }
  memory_events: MemoryEvent[]
  call_logs: CallLogItem[]
  tags: StrategyTag[]
  compression_events: CompressionEvent[]
}

export interface ToastMessage {
  id: string
  tone: 'success' | 'info' | 'warning' | 'error'
  title: string
  detail?: string
}

export interface PublicAuditResponse {
  ok: boolean
  hotel_id: number
  form_autofill: {
    hotel_id: number
    hotel_name: string
    area: string
    website: string
    booking_engine: string
    phone: string
    important_emails: string[]
    important_people: { name: string; title: string }[]
  }
  rate_intel: {
    checkin: string
    direct_price?: number
    direct_bar?: number
    lowest_ota_name?: string
    lowest_ota_price?: number
    undercut_pct?: number
    parity_status?: string
    channels: OtaChannelQuote[]
    neighbors: { name: string; price: number }[]
  }
  decision_assistant: {
    verdict: string
    recommended_bar: number
    total_annual_roi: number
    staff_hours_saved_mo: number
    actions: string[]
    comp_avg_bar?: number
  }
  urls: {
    demo_url: string
    audit_url: string
  }
  executive_summary: string
}
