import React from 'react'
import { clsx } from 'clsx'

interface MetricCardProps {
  label: string
  value: string | number
  sub: string
  delta?: string
  tone?: 'royal' | 'emerald' | 'rose' | 'amber' | 'slate'
  icon?: React.ReactNode
}

const toneStyles: Record<NonNullable<MetricCardProps['tone']>, { iconBg: string; deltaBg: string; cardAccent: string }> = {
  royal: {
    iconBg: 'bg-blue-50 text-blue-600 border-blue-200',
    deltaBg: 'bg-blue-50 text-blue-700',
    cardAccent: 'border-blue-200/80 bg-gradient-to-br from-white to-blue-50/45',
  },
  emerald: {
    iconBg: 'bg-emerald-50 text-emerald-600 border-emerald-200',
    deltaBg: 'bg-emerald-50 text-emerald-700',
    cardAccent: 'border-[#DCE7F8] bg-white',
  },
  rose: {
    iconBg: 'bg-rose-50 text-rose-600 border-rose-200',
    deltaBg: 'bg-rose-50 text-rose-700',
    cardAccent: 'border-[#DCE7F8] bg-white',
  },
  amber: {
    iconBg: 'bg-amber-50 text-amber-600 border-amber-200',
    deltaBg: 'bg-amber-50 text-amber-700',
    cardAccent: 'border-[#DCE7F8] bg-white',
  },
  slate: {
    iconBg: 'bg-slate-100 text-slate-700 border-slate-200',
    deltaBg: 'bg-slate-100 text-slate-700',
    cardAccent: 'border-[#DCE7F8] bg-white',
  },
}

export const MetricCard: React.FC<MetricCardProps> = ({ label, value, sub, delta, tone = 'slate', icon }) => {
  const st = toneStyles[tone]
  return (
    <div className={clsx('ember-card p-4 sm:p-5 flex flex-col justify-between gap-2', st.cardAccent)}>
      <div className="flex items-start justify-between gap-2">
        <span className="text-[11px] font-bold uppercase tracking-wider text-[#475B80]">{label}</span>
        {icon && (
          <span className={clsx('w-9 h-9 rounded-xl border flex items-center justify-center shrink-0', st.iconBg)}>
            {icon}
          </span>
        )}
      </div>
      <div className="flex items-baseline justify-between gap-2 flex-wrap">
        <div className="text-2xl sm:text-[27px] font-extrabold tracking-tight text-[#0B1B3B] tabular-nums">{value}</div>
        {delta && (
          <span className={clsx('px-2.5 py-0.5 rounded-full text-[11px] font-bold tabular-nums', st.deltaBg)}>{delta}</span>
        )}
      </div>
      <div className="text-xs text-[#6D81A8] font-medium leading-snug">{sub}</div>
    </div>
  )
}
