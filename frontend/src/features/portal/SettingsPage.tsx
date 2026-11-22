import React, { useState } from 'react'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { RotateCcw, Save } from 'lucide-react'
import { usePortalStore } from '../../store/usePortalStore'
import { ModalDialog } from '../../components/ui/ModalDialog'

const settingsSchema = z.object({
  alert_email: z.string().email('Enter a valid delivery email'),
  telegram_chat_id: z.string(),
})

type SettingsValues = z.infer<typeof settingsSchema>

export const SettingsPage: React.FC = () => {
  const { portal, density, setDensity, saveAlertSettings, resetDemoData } = usePortalStore()
  const [confirmResetOpen, setConfirmResetOpen] = useState(false)

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<SettingsValues>({
    resolver: zodResolver(settingsSchema),
    defaultValues: {
      alert_email: portal.account.alert_email || portal.account.email || 'revenue@hotel.com',
      telegram_chat_id: portal.account.telegram_chat_id || '',
    },
  })

  const onSave = async (vals: SettingsValues) => {
    await saveAlertSettings(vals.alert_email, vals.telegram_chat_id)
  }

  return (
    <div className="space-y-5 max-w-4xl">
      <div>
        <span className="text-[11px] font-extrabold uppercase tracking-wider text-blue-700">
          Property Preferences &amp; Morning Brief Delivery
        </span>
        <h1 className="text-xl sm:text-2xl font-black text-[#0B1B3B] tracking-tight">Portal &amp; Notification Settings</h1>
      </div>

      <div className="ember-card p-6 space-y-4">
        <h2 className="text-sm font-extrabold text-[#0B1B3B]">6:00 AM Daily Brief &amp; Shift Alert Channels</h2>
        <form onSubmit={handleSubmit(onSave)} className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div>
            <label className="block text-[10.5px] font-extrabold uppercase text-[#475B80] mb-1">Daily Brief Email</label>
            <input
              {...register('alert_email')}
              className="w-full px-3 py-2 text-xs rounded-xl border border-[#DCE7F8] bg-[#F7FAFF]"
            />
            {errors.alert_email && <span className="text-[11px] font-bold text-rose-600">{errors.alert_email.message}</span>}
          </div>
          <div>
            <label className="block text-[10.5px] font-extrabold uppercase text-[#475B80] mb-1">Telegram Group / Chat ID</label>
            <input
              {...register('telegram_chat_id')}
              placeholder="@miami_hotel_rates"
              className="w-full px-3 py-2 text-xs rounded-xl border border-[#DCE7F8] bg-[#F7FAFF]"
            />
          </div>
          <div className="sm:col-span-2">
            <button type="submit" className="px-4 py-2 rounded-xl bg-blue-600 text-white text-xs font-bold inline-flex items-center gap-1.5 hover:bg-blue-700">
              <Save className="w-3.5 h-3.5" />
              Save Alert Preferences
            </button>
          </div>
        </form>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <div className="ember-card p-5 space-y-3">
          <h2 className="text-sm font-extrabold text-[#0B1B3B]">Table &amp; Console Density</h2>
          <p className="text-xs text-[#475B80]">Switch between compact Front-Office scan mode and relaxed executive spacing.</p>
          <div className="inline-flex rounded-xl bg-[#F2F6FD] p-1 border border-[#DCE7F8]">
            <button
              type="button"
              onClick={() => setDensity('compact')}
              className={`px-3 py-1.5 rounded-lg text-xs font-bold ${density === 'compact' ? 'bg-blue-600 text-white' : 'text-[#475B80]'}`}
            >
              Compact Desk View
            </button>
            <button
              type="button"
              onClick={() => setDensity('comfortable')}
              className={`px-3 py-1.5 rounded-lg text-xs font-bold ${density === 'comfortable' ? 'bg-blue-600 text-white' : 'text-[#475B80]'}`}
            >
              Comfortable View
            </button>
          </div>
        </div>

        <div className="ember-card p-5 space-y-3">
          <h2 className="text-sm font-extrabold text-[#0B1B3B]">Demo Data &amp; Local Persistence</h2>
          <p className="text-xs text-[#475B80]">
            Edits persist in browser storage across refreshes. Reset cleanly back to the deterministic baseline anytime.
          </p>
          <button
            type="button"
            onClick={() => setConfirmResetOpen(true)}
            className="px-4 py-2 rounded-xl bg-rose-50 text-rose-700 border border-rose-200 text-xs font-bold inline-flex items-center gap-1.5 hover:bg-rose-100"
          >
            <RotateCcw className="w-3.5 h-3.5" />
            Reset Demo Data
          </button>
        </div>
      </div>

      <ModalDialog
        open={confirmResetOpen}
        onClose={() => setConfirmResetOpen(false)}
        title="Reset Demo Data to Baseline?"
        subtitle="All locally edited OOO counts, tags, call logs, and pricing rules will be restored."
        maxWidthClass="max-w-sm"
      >
        <div className="flex justify-end gap-2">
          <button type="button" onClick={() => setConfirmResetOpen(false)} className="px-4 py-2 rounded-xl bg-[#F2F6FD] text-xs font-bold">
            Cancel
          </button>
          <button
            type="button"
            onClick={() => {
              resetDemoData()
              setConfirmResetOpen(false)
            }}
            className="px-4 py-2 rounded-xl bg-rose-600 text-white text-xs font-bold"
          >
            Confirm Reset
          </button>
        </div>
      </ModalDialog>
    </div>
  )
}
