import React, { useMemo, useState } from 'react'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { createColumnHelper, type ColumnDef } from '@tanstack/react-table'
import { BookmarkCheck, Plus, Trash2 } from 'lucide-react'
import { usePortalStore } from '../../store/usePortalStore'
import type { MemoryEvent } from '../../types/hospitality'
import { DataTable } from '../../components/ui/DataTable'
import { ModalDialog } from '../../components/ui/ModalDialog'

const tagFormSchema = z.object({
  hotelId: z.coerce.number().min(1),
  tag: z.string().min(2, 'Enter tag label'),
  note: z.string().min(3, 'Enter strategy rule'),
})

type TagValues = z.infer<typeof tagFormSchema>
const memColHelper = createColumnHelper<MemoryEvent>()

export const MemoryTagsPage: React.FC = () => {
  const { portal, density, addTag, deleteTag } = usePortalStore()
  const [confirmDeleteId, setConfirmDeleteId] = useState<number | null>(null)

  const {
    register,
    handleSubmit,
    reset,
    formState: { errors },
  } = useForm<TagValues>({
    resolver: zodResolver(tagFormSchema),
    defaultValues: {
      hotelId: portal.comp_set[0]?.hotel_id || portal.comp_set[0]?.id || 23,
      tag: '',
      note: '',
    },
  })

  const onSubmit = async (vals: TagValues) => {
    await addTag(vals.hotelId, vals.tag, vals.note)
    reset({ hotelId: vals.hotelId, tag: '', note: '' })
  }

  const columns = useMemo(
    () =>
      [
        memColHelper.accessor('hotel_name', {
          header: 'Competitor',
          cell: ({ getValue }) => <span className="font-extrabold text-[#0B1B3B]">{getValue() || 'Corridor Property'}</span>,
        }),
        memColHelper.accessor('event_type', {
          header: 'Event',
          cell: ({ getValue }) => (
            <span className="px-2 py-0.5 rounded-full bg-blue-50 text-blue-700 text-[10px] font-extrabold uppercase">{getValue()}</span>
          ),
        }),
        memColHelper.accessor((r) => `${r.old_price ?? ''} -> ${r.new_price ?? ''}`, {
          id: 'move',
          header: 'Old → New BAR',
          cell: ({ row }) =>
            row.original.old_price && row.original.new_price ? (
              <span className="font-bold tabular-nums">
                ${row.original.old_price} → ${row.original.new_price}
              </span>
            ) : (
              <span>—</span>
            ),
        }),
        memColHelper.accessor('competitor_pattern', {
          header: 'Pattern',
          cell: ({ getValue }) => <span className="text-[11px] font-bold text-[#475B80]">{getValue() || 'OBSERVED'}</span>,
        }),
        memColHelper.accessor('ai_recommendation', {
          header: 'Strategy Takeaway',
          cell: ({ getValue }) => <span className="text-[11.5px] text-[#475B80]">{getValue()}</span>,
        }),
      ] as ColumnDef<MemoryEvent, unknown>[],
    []
  )

  return (
    <div className="space-y-5">
      <div>
        <span className="text-[11px] font-extrabold uppercase tracking-wider text-blue-700">
          Private Hotel Memory Engine &amp; Shift Handoff Notes
        </span>
        <h1 className="text-xl sm:text-2xl font-black text-[#0B1B3B] tracking-tight">
          Competitor Pricing Memory &amp; Private Strategy Tags
        </h1>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-4">
        <div className="lg:col-span-5 ember-card p-5 space-y-4">
          <div className="flex items-center gap-2">
            <BookmarkCheck className="w-4 h-4 text-blue-600" />
            <h2 className="text-sm font-extrabold text-[#0B1B3B]">Add Private Strategy Tag</h2>
          </div>
          <form onSubmit={handleSubmit(onSubmit)} className="space-y-3">
            <div>
              <label className="block text-[10px] font-extrabold uppercase text-[#475B80] mb-1">Assigned Property</label>
              <select {...register('hotelId')} className="w-full px-3 py-2 text-xs font-bold rounded-xl border border-[#DCE7F8] bg-[#F7FAFF]">
                {portal.comp_set.map((h) => (
                  <option key={h.id} value={h.hotel_id || h.id}>
                    {h.name}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-[10px] font-extrabold uppercase text-[#475B80] mb-1">Tag Label</label>
              <input
                {...register('tag')}
                placeholder="e.g. Weekend Yield Anchor · Watch Agoda"
                className="w-full px-3 py-2 text-xs rounded-xl border border-[#DCE7F8] bg-[#F7FAFF]"
              />
              {errors.tag && <span className="text-[11px] font-bold text-rose-600">{errors.tag.message}</span>}
            </div>
            <div>
              <label className="block text-[10px] font-extrabold uppercase text-[#475B80] mb-1">Strategy Note</label>
              <input
                {...register('note')}
                placeholder="e.g. Hold BAR $10 under them when occ > 80%"
                className="w-full px-3 py-2 text-xs rounded-xl border border-[#DCE7F8] bg-[#F7FAFF]"
              />
              {errors.note && <span className="text-[11px] font-bold text-rose-600">{errors.note.message}</span>}
            </div>
            <button type="submit" className="w-full py-2 rounded-xl bg-blue-600 text-white text-xs font-bold inline-flex items-center justify-center gap-1.5 hover:bg-blue-700">
              <Plus className="w-3.5 h-3.5" />
              Save Tag to My Portal
            </button>
          </form>

          <div className="border-t border-[#EAF1FC] pt-3 space-y-2">
            <div className="text-[11px] font-extrabold uppercase text-[#6D81A8]">Active Saved Tags ({portal.tags.length})</div>
            {portal.tags.map((t) => {
              const hName = portal.comp_set.find((h) => (h.hotel_id || h.id) === t.hotel_id)?.name || t.hotel_name || `Hotel #${t.hotel_id}`
              return (
                <div key={t.id} className="ember-subtle-card p-3 flex items-start justify-between gap-2">
                  <div>
                    <div className="text-xs font-extrabold text-[#0B1B3B]">
                      {t.tag} <span className="text-[10.5px] font-semibold text-blue-700">({hName})</span>
                    </div>
                    {t.note && <div className="text-[11px] text-[#475B80] mt-0.5">{t.note}</div>}
                  </div>
                  <button
                    type="button"
                    aria-label={`Delete tag ${t.tag}`}
                    onClick={() => setConfirmDeleteId(t.id)}
                    className="p-1.5 rounded-lg text-rose-600 hover:bg-rose-50 shrink-0"
                  >
                    <Trash2 className="w-3.5 h-3.5" />
                  </button>
                </div>
              )
            })}
          </div>
        </div>

        <div className="lg:col-span-7 ember-card p-5">
          <h2 className="text-sm font-extrabold text-[#0B1B3B] mb-3">Recorded Competitor Rate Moves &amp; Patterns</h2>
          <DataTable
            data={portal.memory_events}
            columns={columns}
            density={density}
            searchPlaceholder="Search memory events..."
            csvFilename="hotelrateintel-memory.csv"
            csvHeaders={['Competitor', 'Event', 'Old BAR', 'New BAR', 'Pattern', 'Recommendation']}
            csvRowMapper={(m) => [m.hotel_name || '', m.event_type, m.old_price ?? '', m.new_price ?? '', m.competitor_pattern || '', m.ai_recommendation || '']}
          />
        </div>
      </div>

      <ModalDialog
        open={confirmDeleteId !== null}
        onClose={() => setConfirmDeleteId(null)}
        title="Delete Private Strategy Tag?"
        subtitle="This removes the strategy note from your hotel account."
        maxWidthClass="max-w-sm"
      >
        <div className="flex justify-end gap-2">
          <button type="button" onClick={() => setConfirmDeleteId(null)} className="px-4 py-2 rounded-xl bg-[#F2F6FD] text-xs font-bold">
            Cancel
          </button>
          <button
            type="button"
            onClick={async () => {
              if (confirmDeleteId !== null) await deleteTag(confirmDeleteId)
              setConfirmDeleteId(null)
            }}
            className="px-4 py-2 rounded-xl bg-rose-600 text-white text-xs font-bold"
          >
            Confirm Delete
          </button>
        </div>
      </ModalDialog>
    </div>
  )
}
