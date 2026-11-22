import React from 'react'
import { CheckCircle2, Lock } from 'lucide-react'
import { usePortalStore } from '../../store/usePortalStore'
import type { TierId } from '../../types/hospitality'

export const PlansPage: React.FC = () => {
  const { portal, previewTier, hydratePortal, demoHotelId, pushToast } = usePortalStore()
  const activeTierId = previewTier || portal.active_tier.tier_id

  const handlePreviewTier = async (tid: TierId) => {
    await hydratePortal(demoHotelId, tid)
    pushToast({ tone: 'info', title: `Previewing ${tid.toUpperCase()}`, detail: 'Comp-set cap & features adjusted dynamically.' })
  }

  return (
    <div className="space-y-5">
      <div>
        <span className="text-[11px] font-extrabold uppercase tracking-wider text-blue-700">
          Transparent Boutique SaaS Plans · Month-to-Month
        </span>
        <h1 className="text-xl sm:text-2xl font-black text-[#0B1B3B] tracking-tight">
          Compare Tiers Live &amp; Monthly Payroll ROI ($0 – $399/mo)
        </h1>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-4">
        {portal.all_tiers.map((t) => {
          const isCurrent = t.tier_id === activeTierId
          return (
            <div
              key={t.tier_id}
              className={`rounded-2xl p-5 flex flex-col justify-between gap-4 ${
                isCurrent
                  ? 'bg-gradient-to-br from-[#06122E] via-[#0D255B] to-[#1744A6] text-white shadow-emberSidebar'
                  : 'ember-card text-[#0B1B3B]'
              }`}
            >
              <div className="space-y-3">
                <span
                  className={`inline-block px-2.5 py-0.5 rounded-full text-[10px] font-extrabold ${
                    isCurrent ? 'bg-blue-400/25 text-blue-100' : 'bg-blue-50 text-blue-700'
                  }`}
                >
                  {isCurrent ? 'ACTIVE PREVIEW' : t.badge}
                </span>
                <h2 className="text-base font-extrabold">{t.name}</h2>
                <div className="text-3xl font-black tabular-nums">
                  ${t.monthly_price}
                  <span className="text-xs font-semibold opacity-75">/mo</span>
                </div>
                <div className={`text-xs font-bold ${isCurrent ? 'text-emerald-300' : 'text-emerald-700'}`}>
                  Saves {t.staff_hours_saved_mo} hrs/mo (${t.labor_dollars_saved_mo.toLocaleString()} payroll)
                </div>

                <ul className="space-y-1.5 text-[11.5px]">
                  {t.features.map((f, i) => (
                    <li key={i} className="flex items-start gap-1.5">
                      <CheckCircle2 className={`w-3.5 h-3.5 mt-0.5 shrink-0 ${isCurrent ? 'text-emerald-300' : 'text-emerald-600'}`} />
                      <span className={isCurrent ? 'text-blue-50' : 'text-[#475B80]'}>{f}</span>
                    </li>
                  ))}
                  {t.locked_features.map((lf, i) => (
                    <li key={i} className="flex items-start gap-1.5 opacity-60">
                      <Lock className="w-3.5 h-3.5 mt-0.5 shrink-0" />
                      <span>{lf}</span>
                    </li>
                  ))}
                </ul>
              </div>

              <button
                type="button"
                onClick={() => handlePreviewTier(t.tier_id)}
                className={`w-full py-2 rounded-xl text-xs font-bold transition ${
                  isCurrent ? 'bg-white text-[#0B1B3B]' : 'bg-blue-600 text-white hover:bg-blue-700'
                }`}
              >
                {isCurrent ? 'Currently Selected' : `Preview ${t.name}`}
              </button>
            </div>
          )
        })}
      </div>
    </div>
  )
}
