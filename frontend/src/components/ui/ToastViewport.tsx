import React from 'react'
import { CheckCircle2, Info, AlertTriangle, X } from 'lucide-react'
import { usePortalStore } from '../../store/usePortalStore'

export const ToastViewport: React.FC = () => {
  const toasts = usePortalStore((s) => s.toasts)
  const dismissToast = usePortalStore((s) => s.dismissToast)

  if (!toasts.length) return null

  return (
    <div className="fixed bottom-4 right-4 z-[80] flex flex-col gap-2 w-[min(360px,calc(100vw-24px))]">
      {toasts.map((t) => {
        const toneCls =
          t.tone === 'success'
            ? 'border-emerald-200 bg-white text-[#0B1B3B]'
            : t.tone === 'error'
              ? 'border-rose-200 bg-white text-[#0B1B3B]'
              : t.tone === 'warning'
                ? 'border-amber-200 bg-white text-[#0B1B3B]'
                : 'border-blue-200 bg-white text-[#0B1B3B]'
        const IconComp = t.tone === 'success' ? CheckCircle2 : t.tone === 'error' || t.tone === 'warning' ? AlertTriangle : Info
        const iconCls =
          t.tone === 'success'
            ? 'text-emerald-600'
            : t.tone === 'error'
              ? 'text-rose-600'
              : t.tone === 'warning'
                ? 'text-amber-600'
                : 'text-blue-600'

        return (
          <div
            key={t.id}
            role="status"
            className={`rounded-2xl border p-3.5 shadow-xl flex items-start gap-2.5 ${toneCls}`}
          >
            <IconComp className={`w-4 h-4 mt-0.5 shrink-0 ${iconCls}`} />
            <div className="flex-1 min-w-0">
              <div className="text-xs font-extrabold">{t.title}</div>
              {t.detail && <div className="text-[11px] text-[#475B80] mt-0.5 leading-snug">{t.detail}</div>}
            </div>
            <button
              type="button"
              onClick={() => dismissToast(t.id)}
              aria-label="Dismiss notification"
              className="text-[#6D81A8] hover:text-[#0B1B3B]"
            >
              <X className="w-3.5 h-3.5" />
            </button>
          </div>
        )
      })}
    </div>
  )
}
