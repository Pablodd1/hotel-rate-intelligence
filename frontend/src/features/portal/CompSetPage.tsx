import React, { useMemo, useState } from 'react'
import { createColumnHelper, type ColumnDef } from '@tanstack/react-table'
import { Eye, Plus, RefreshCw, Tag } from 'lucide-react'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { usePortalStore } from '../../store/usePortalStore'
import type { HotelRateRow } from '../../types/hospitality'
import { DataTable } from '../../components/ui/DataTable'
import { ModalDialog } from '../../components/ui/ModalDialog'
import { exportToCsv } from '../../utils/csv'

const columnHelper = createColumnHelper<HotelRateRow>()

const tagSchema = z.object({
  tag: z.string().min(2, 'Enter a short strategy tag label'),
  note: z.string().min(3, 'Enter an actionable note for your team'),
})

type TagFormValues = z.infer<typeof tagSchema>

export const CompSetPage: React.FC = () => {
  const { portal, density, globalSearch, scrapeCompSet, isLoading, addTag } = usePortalStore()
  const [detailHotel, setDetailHotel] = useState<HotelRateRow | null>(null)
  const [tagTargetHotel, setTagTargetHotel] = useState<HotelRateRow | null>(null)

  const {
    register,
    handleSubmit,
    reset,
    formState: { errors },
  } = useForm<TagFormValues>({
    resolver: zodResolver(tagSchema),
  })

  const filteredByTopSearch = useMemo(() => {
    const q = globalSearch.trim().toLowerCase()
    if (!q) return portal.comp_set
    return portal.comp_set.filter(
      (h) =>
        h.name.toLowerCase().includes(q) ||
        h.area.toLowerCase().includes(q) ||
        (h.pricing_personality || '').toLowerCase().includes(q)
    )
  }, [portal.comp_set, globalSearch])

  const columns = useMemo(
    () =>
      [
        columnHelper.accessor('name', {
          header: 'Property',
          cell: ({ row }) => {
            const h = row.original
            return (
              <div>
                <div className="font-extrabold text-[#0B1B3B] flex items-center gap-1.5">
                  <span>{h.name}</span>
                  {h.is_primary && (
                    <span className="px-1.5 py-0.5 rounded bg-blue-600 text-white text-[9px] font-black">YOURS</span>
                  )}
                </div>
                <div className="text-[10.5px] text-[#6D81A8]">
                  {h.area} · {h.est_rooms || 45} rms · {h.booking_engine || 'Direct'}
                </div>
              </div>
            )
          },
        }),
        columnHelper.accessor((r) => r.price ?? 0, {
          id: 'price',
          header: 'Live BAR',
          cell: ({ row }) => (
            <span className="font-black text-sm tabular-nums text-[#0B1B3B] whitespace-nowrap">
              {row.original.price ? `$${Math.round(row.original.price)}` : '—'}
            </span>
          ),
        }),
        columnHelper.accessor('delta_pct', {
          header: 'Move %',
          cell: ({ getValue }) => {
            const v = Number(getValue() || 0)
            return (
              <span className={`font-bold tabular-nums whitespace-nowrap ${v > 0 ? 'text-emerald-600' : v < 0 ? 'text-rose-600' : 'text-[#6D81A8]'}`}>
                {v >= 0 ? `+${v.toFixed(1)}%` : `${v.toFixed(1)}%`}
              </span>
            )
          },
        }),
        columnHelper.accessor('parity_status', {
          header: 'Parity Status',
          cell: ({ row }) => {
            const st = row.original.parity_status
            const uc = Number(row.original.undercut_pct || 0)
            return (
              <span
                className={`px-2 py-0.5 rounded-full text-[10px] font-extrabold whitespace-nowrap inline-block ${
                  st === 'UNDERCUT'
                    ? 'bg-rose-50 text-rose-700'
                    : st === 'DIRECT_WIN'
                      ? 'bg-emerald-50 text-emerald-700'
                      : 'bg-blue-50 text-blue-700'
                }`}
              >
                {st} {st === 'UNDERCUT' && uc !== 0 ? `(${uc.toFixed(1)}%)` : ''}
              </span>
            )
          },
        }),
        columnHelper.accessor('est_occupancy_pct', {
          header: 'Est. Occ',
          cell: ({ getValue }) => <span className="font-bold tabular-nums whitespace-nowrap">{getValue()}%</span>,
        }),
        columnHelper.accessor('pricing_personality', {
          header: 'Behavior Pattern',
          cell: ({ getValue }) => <span className="text-[11px] font-semibold text-[#475B80]">{getValue()}</span>,
        }),
        columnHelper.display({
          id: 'actions',
          header: 'Actions',
          cell: ({ row }) => (
            <div className="flex items-center gap-1.5">
              <button
                type="button"
                onClick={() => setDetailHotel(row.original)}
                aria-label={`Inspect ${row.original.name}`}
                className="p-1.5 rounded-lg bg-[#F2F6FD] text-blue-700 hover:bg-blue-100"
              >
                <Eye className="w-3.5 h-3.5" />
              </button>
              <button
                type="button"
                onClick={() => {
                  setTagTargetHotel(row.original)
                  reset({ tag: '', note: '' })
                }}
                className="px-2 py-1 rounded-lg bg-blue-50 text-blue-700 text-[10.5px] font-bold hover:bg-blue-100 inline-flex items-center gap-1"
              >
                <Plus className="w-3 h-3" />
                Tag
              </button>
            </div>
          ),
        }),
      ] as ColumnDef<HotelRateRow, unknown>[],
    [reset]
  )

  const handleSaveTag = async (values: TagFormValues) => {
    if (!tagTargetHotel) return
    await addTag(tagTargetHotel.hotel_id || tagTargetHotel.id, values.tag, values.note)
    setTagTargetHotel(null)
    reset()
  }

  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <span className="text-[11px] font-extrabold uppercase tracking-wider text-blue-700">
            Assigned Street Comp-Set · Live Public Rates &amp; Parity Radar
          </span>
          <h1 className="text-xl sm:text-2xl font-black text-[#0B1B3B] tracking-tight">
            Comp-Set Rate &amp; Channel Monitor ({filteredByTopSearch.length} Properties)
          </h1>
        </div>
        <button
          type="button"
          onClick={() => scrapeCompSet()}
          disabled={isLoading}
          className="px-4 py-2 rounded-xl bg-blue-600 text-white text-xs font-bold inline-flex items-center gap-1.5 hover:bg-blue-700 disabled:opacity-60"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${isLoading ? 'animate-spin' : ''}`} />
          Scrape Assigned Comp-Set
        </button>
      </div>

      <div className="ember-card p-5">
        <DataTable
          data={filteredByTopSearch}
          columns={columns}
          searchPlaceholder="Search property, corridor, personality..."
          filterColumnId="parity_status"
          filterOptions={[
            { label: 'All', value: 'ALL' },
            { label: 'Undercut', value: 'UNDERCUT' },
            { label: 'Parity', value: 'PARITY' },
            { label: 'Direct Win', value: 'DIRECT_WIN' },
          ]}
          enableRowSelection
          density={density}
          csvFilename="hotelrateintel-compset.csv"
          csvHeaders={['Property', 'Area', 'Live BAR', 'Parity Status', 'Est Occ %', 'Personality']}
          csvRowMapper={(h) => [h.name, h.area, h.price ?? '', h.parity_status, h.est_occupancy_pct, h.pricing_personality]}
          bulkActionRender={(selected, clear) => (
            <button
              type="button"
              onClick={() => {
                exportToCsv(
                  'selected-compset.csv',
                  ['Property', 'Live BAR', 'Parity Status', 'Occ %'],
                  selected.map((s) => [s.name, s.price ?? '', s.parity_status, s.est_occupancy_pct])
                )
                clear()
              }}
              className="px-2.5 py-1 rounded-lg bg-blue-600 text-white text-[10.5px] font-bold"
            >
              Export Selected
            </button>
          )}
        />
      </div>

      {/* Hotel Detail Inspection Modal */}
      <ModalDialog
        open={Boolean(detailHotel)}
        onClose={() => setDetailHotel(null)}
        title={detailHotel?.name || 'Property Details'}
        subtitle={`${detailHotel?.area || 'Miami'} · ${detailHotel?.booking_engine || 'Direct Engine'}`}
      >
        {detailHotel && (
          <div className="space-y-4 text-xs">
            <div className="grid grid-cols-3 gap-3">
              <div className="ember-subtle-card p-3">
                <div className="text-[10px] font-bold text-[#6D81A8] uppercase">Direct BAR</div>
                <div className="text-lg font-black text-[#0B1B3B] tabular-nums">${detailHotel.price ?? '—'}</div>
              </div>
              <div className="ember-subtle-card p-3">
                <div className="text-[10px] font-bold text-[#6D81A8] uppercase">Est. Occupancy</div>
                <div className="text-lg font-black text-blue-700 tabular-nums">{detailHotel.est_occupancy_pct}%</div>
              </div>
              <div className="ember-subtle-card p-3">
                <div className="text-[10px] font-bold text-[#6D81A8] uppercase">Front Desk</div>
                <div className="text-xs font-bold text-[#0B1B3B] mt-1">{detailHotel.phone || 'Verified On File'}</div>
              </div>
            </div>

            <div>
              <h4 className="text-xs font-extrabold uppercase text-[#475B80] mb-2">Multi-OTA Quote Breakdown</h4>
              <div className="space-y-1.5">
                {(detailHotel.ota_channels || []).map((c, idx) => (
                  <div key={idx} className="flex items-center justify-between px-3 py-2 rounded-xl bg-[#F7FAFF] border border-[#DCE7F8]">
                    <span className="font-bold">{c.name}</span>
                    <span className="font-black tabular-nums">${Math.round(c.rate)}</span>
                  </div>
                ))}
              </div>
            </div>

            <div>
              <h4 className="text-xs font-extrabold uppercase text-[#475B80] mb-2">Private Strategy Tags</h4>
              {(detailHotel.tags || []).length ? (
                <div className="space-y-1.5">
                  {(detailHotel.tags || []).map((t) => (
                    <div key={t.id} className="px-3 py-2 rounded-xl bg-blue-50 border border-blue-200">
                      <div className="font-extrabold text-blue-900">{t.tag}</div>
                      <div className="text-[#475B80]">{t.note}</div>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="text-[#6D81A8]">No custom notes added for this competitor yet.</div>
              )}
            </div>
          </div>
        )}
      </ModalDialog>

      {/* Add Private Tag Modal */}
      <ModalDialog
        open={Boolean(tagTargetHotel)}
        onClose={() => setTagTargetHotel(null)}
        title={`Add Strategy Tag — ${tagTargetHotel?.name || ''}`}
        subtitle="Visible strictly to your isolated hotel team (Reservations & Night Audit shifts)."
      >
        <form onSubmit={handleSubmit(handleSaveTag)} className="space-y-3">
          <div>
            <label className="block text-[10.5px] font-extrabold uppercase text-[#475B80] mb-1">Tag Label</label>
            <input
              {...register('tag')}
              placeholder="e.g. Drops BAR every Thursday 4 PM · Watch Agoda"
              className="w-full px-3 py-2 text-xs rounded-xl border border-[#DCE7F8] bg-[#F7FAFF]"
            />
            {errors.tag && <span className="text-[11px] font-bold text-rose-600">{errors.tag.message}</span>}
          </div>
          <div>
            <label className="block text-[10.5px] font-extrabold uppercase text-[#475B80] mb-1">Action Rule / Note</label>
            <textarea
              {...register('note')}
              rows={3}
              placeholder="e.g. Never chase below $215 unless our net occupancy drops below 70%."
              className="w-full px-3 py-2 text-xs rounded-xl border border-[#DCE7F8] bg-[#F7FAFF]"
            />
            {errors.note && <span className="text-[11px] font-bold text-rose-600">{errors.note.message}</span>}
          </div>
          <div className="flex justify-end gap-2 pt-2">
            <button type="button" onClick={() => setTagTargetHotel(null)} className="px-4 py-2 rounded-xl bg-[#F2F6FD] text-xs font-bold">
              Cancel
            </button>
            <button type="submit" className="px-4 py-2 rounded-xl bg-blue-600 text-white text-xs font-bold inline-flex items-center gap-1.5">
              <Tag className="w-3.5 h-3.5" />
              Save Private Tag
            </button>
          </div>
        </form>
      </ModalDialog>
    </div>
  )
}
