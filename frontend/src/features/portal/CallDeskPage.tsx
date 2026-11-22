import React, { useMemo, useState } from 'react'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { createColumnHelper, type ColumnDef } from '@tanstack/react-table'
import { Clock, Mail, PhoneCall } from 'lucide-react'
import { usePortalStore } from '../../store/usePortalStore'
import type { CallLogItem } from '../../types/hospitality'
import { DataTable } from '../../components/ui/DataTable'

const callSchema = z.object({
  hotel_id: z.coerce.number().min(1),
  shift: z.string().min(3),
  reported_occupancy_pct: z.coerce.number().min(0).max(100),
  rooms_left: z.coerce.number().min(0).max(500),
  quoted_walkin_rate: z.coerce.number().min(39),
  questions_asked: z.string().min(2),
  transcript: z.string().min(3, 'Enter brief summary from overnight receptionist'),
})

type CallFormValues = z.infer<typeof callSchema>
const callColHelper = createColumnHelper<CallLogItem>()

export const CallDeskPage: React.FC = () => {
  const { portal, inquiries, density, logCourtesyCall, createCompInquiry } = usePortalStore()
  const comps = portal.comp_set.filter((h) => !h.is_primary)
  const defaultTarget = comps[0] || portal.primary_hotel

  const [inqTargetId, setInqTargetId] = useState<number>(defaultTarget.hotel_id || defaultTarget.id)
  const [inqType, setInqType] = useState('courtesy_rate_swap')
  const [inqRooms, setInqRooms] = useState(2)
  const [inqQuoted, setInqQuoted] = useState('')

  const {
    register,
    handleSubmit,
    reset,
    formState: { errors },
  } = useForm<CallFormValues>({
    resolver: zodResolver(callSchema),
    defaultValues: {
      hotel_id: defaultTarget.hotel_id || defaultTarget.id,
      shift: 'Pre-Audit (11:30 PM–1:15 AM)',
      reported_occupancy_pct: 86,
      rooms_left: 5,
      quoted_walkin_rate: 259,
      questions_asked: 'Walk-in BAR, Suite left?, Rollaway fee, Resort fee',
      transcript: '',
    },
  })

  const onSubmitCall = async (vals: CallFormValues) => {
    const targetHotel = portal.comp_set.find((h) => (h.hotel_id || h.id) === vals.hotel_id)
    await logCourtesyCall({
      hotel_id: vals.hotel_id,
      hotel_name: targetHotel?.name || 'Corridor Competitor',
      shift: vals.shift,
      caller_mode: 'Courtesy Call-Around',
      phone_dialed: targetHotel?.phone || '+1 (305) 555-0100',
      reported_occupancy_pct: vals.reported_occupancy_pct,
      rooms_left: vals.rooms_left,
      quoted_walkin_rate: vals.quoted_walkin_rate,
      questions_asked: vals.questions_asked,
      transcript: vals.transcript,
    })
    reset({ ...vals, transcript: '' })
  }

  const handleInquirySubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    const target = comps.find((h) => (h.hotel_id || h.id) === inqTargetId) || defaultTarget
    await createCompInquiry({
      targetHotelId: target.hotel_id || target.id,
      targetHotelName: target.name,
      inquiryType: inqType,
      roomsRequested: inqRooms,
      quotedRate: inqQuoted.trim() ? Number(inqQuoted) : null,
    })
    setInqQuoted('')
  }

  const callColumns = useMemo(
    () =>
      [
        callColHelper.accessor('hotel_name', {
          header: 'Property',
          cell: ({ getValue }) => <span className="font-extrabold text-[#0B1B3B]">{getValue() || 'Neighbor Hotel'}</span>,
        }),
        callColHelper.accessor('shift', {
          header: 'Call Window',
          cell: ({ getValue }) => <span className="text-[11px] font-semibold text-blue-700">{getValue()}</span>,
        }),
        callColHelper.accessor('quoted_walkin_rate', {
          header: 'Walk-In BAR',
          cell: ({ getValue }) => <span className="font-black tabular-nums">${getValue() ?? '—'}</span>,
        }),
        callColHelper.accessor('reported_occupancy_pct', {
          header: 'Occ / Left',
          cell: ({ row }) => (
            <span className="tabular-nums">
              {row.original.reported_occupancy_pct ?? '—'}% ({row.original.rooms_left ?? '—'} left)
            </span>
          ),
        }),
        callColHelper.accessor('transcript', {
          header: 'Front-Desk Notes',
          cell: ({ getValue }) => <span className="text-[11px] text-[#475B80]">{getValue()}</span>,
        }),
      ] as ColumnDef<CallLogItem, unknown>[],
    []
  )

  return (
    <div className="space-y-5">
      <div>
        <span className="text-[11px] font-extrabold uppercase tracking-wider text-blue-700">
          20 Yrs Hotelier Playbook · Night Audit &amp; Front-Desk Receptionist Intelligence
        </span>
        <h1 className="text-xl sm:text-2xl font-black text-[#0B1B3B] tracking-tight">
          Overnight Courtesy Call-Around &amp; Competitor Email Inquiry Desk
        </h1>
      </div>

      {/* Pre-Audit vs Post-Audit Timing Windows */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="ember-card p-4 border-l-4 border-l-emerald-600 space-y-1">
          <div className="text-[10.5px] font-extrabold uppercase text-emerald-700 flex items-center gap-1">
            <Clock className="w-3.5 h-3.5" />
            Window #1 (Best) · Before Night Audit
          </div>
          <div className="text-sm font-black text-[#0B1B3B]">11:30 PM – 1:15 AM</div>
          <p className="text-xs text-[#475B80]">
            Best for live tonight walk-in BAR, rooms left before PMS date-roll, Suite availability &amp; same-night overflow swaps.
          </p>
        </div>

        <div className="ember-card p-4 border-l-4 border-l-blue-600 space-y-1">
          <div className="text-[10.5px] font-extrabold uppercase text-blue-700 flex items-center gap-1">
            <Clock className="w-3.5 h-3.5" />
            Window #2 · After Night Audit
          </div>
          <div className="text-sm font-black text-[#0B1B3B]">3:30 AM – 4:45 AM</div>
          <p className="text-xs text-[#475B80]">
            PMS date has rolled &amp; batches closed. Best for swapping clean final occupancy % and tomorrow's 6:00 AM huddle BAR.
          </p>
        </div>

        <div className="ember-card p-4 border-l-4 border-l-rose-600 space-y-1">
          <div className="text-[10.5px] font-extrabold uppercase text-rose-700 flex items-center gap-1">
            <Clock className="w-3.5 h-3.5" />
            Do Not Call Window
          </div>
          <div className="text-sm font-black text-[#0B1B3B]">1:45 AM – 3:15 AM (Audit Roll)</div>
          <p className="text-xs text-[#475B80]">
            Never disturb auditors during active PMS posting &amp; batch close. Use silent 1-Click Competitor Email Inquiry below.
          </p>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-4">
        {/* Call Logger Form */}
        <form onSubmit={handleSubmit(onSubmitCall)} className="lg:col-span-6 ember-card p-5 space-y-3">
          <div className="flex items-center gap-2">
            <PhoneCall className="w-4 h-4 text-blue-600" />
            <h2 className="text-sm font-extrabold text-[#0B1B3B]">Log Overnight Courtesy Call-Around</h2>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <div>
              <label className="block text-[10px] font-extrabold uppercase text-[#475B80] mb-1">Competitor Hotel</label>
              <select {...register('hotel_id')} className="w-full px-3 py-2 text-xs font-bold rounded-xl border border-[#DCE7F8] bg-[#F7FAFF]">
                {comps.map((h) => (
                  <option key={h.id} value={h.hotel_id || h.id}>
                    {h.name}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-[10px] font-extrabold uppercase text-[#475B80] mb-1">Audit Window</label>
              <select {...register('shift')} className="w-full px-3 py-2 text-xs font-bold rounded-xl border border-[#DCE7F8] bg-[#F7FAFF]">
                <option value="Pre-Audit (11:30 PM–1:15 AM)">Pre-Audit (11:30 PM–1:15 AM)</option>
                <option value="Post-Audit (3:30 AM–4:45 AM)">Post-Audit (3:30 AM–4:45 AM)</option>
              </select>
            </div>
            <div>
              <label className="block text-[10px] font-extrabold uppercase text-[#475B80] mb-1">Reported Occ %</label>
              <input type="number" {...register('reported_occupancy_pct')} className="w-full px-3 py-2 text-xs font-bold rounded-xl border border-[#DCE7F8] bg-[#F7FAFF]" />
            </div>
            <div>
              <label className="block text-[10px] font-extrabold uppercase text-[#475B80] mb-1">Rooms Left / Walk-In BAR</label>
              <div className="grid grid-cols-2 gap-2">
                <input type="number" {...register('rooms_left')} placeholder="Left" className="w-full px-2.5 py-2 text-xs font-bold rounded-xl border border-[#DCE7F8] bg-[#F7FAFF]" />
                <input type="number" {...register('quoted_walkin_rate')} placeholder="$ BAR" className="w-full px-2.5 py-2 text-xs font-bold rounded-xl border border-[#DCE7F8] bg-[#F7FAFF]" />
              </div>
            </div>
          </div>

          <div>
            <label className="block text-[10px] font-extrabold uppercase text-[#475B80] mb-1">What Overnight Front Desk Shared</label>
            <textarea
              {...register('transcript')}
              rows={2}
              placeholder="e.g. Suites sold out, 4 Kings left @ $259 + $35 resort fee."
              className="w-full px-3 py-2 text-xs rounded-xl border border-[#DCE7F8] bg-[#F7FAFF]"
            />
            {errors.transcript && <span className="text-[11px] font-bold text-rose-600">{errors.transcript.message}</span>}
          </div>

          <button type="submit" className="w-full py-2 rounded-xl bg-blue-600 text-white text-xs font-bold hover:bg-blue-700">
            Save Overnight Call Intelligence
          </button>
        </form>

        {/* Competitor Email Rate Inquiry Desk */}
        <div className="lg:col-span-6 ember-card p-5 space-y-3">
          <div className="flex items-center gap-2">
            <Mail className="w-4 h-4 text-blue-600" />
            <h2 className="text-sm font-extrabold text-[#0B1B3B]">Competitor Email Rate Inquiry Desk</h2>
          </div>
          <p className="text-xs text-[#475B80]">
            Draft polite neighbor rate-swap or overflow inquiry emails to your assigned comp-set and record their quoted BAR.
          </p>
          <form onSubmit={handleInquirySubmit} className="space-y-3">
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
              <select
                value={inqTargetId}
                onChange={(e) => setInqTargetId(Number(e.target.value))}
                className="w-full px-3 py-2 text-xs font-bold rounded-xl border border-[#DCE7F8] bg-[#F7FAFF]"
              >
                {comps.map((h) => (
                  <option key={h.id} value={h.hotel_id || h.id}>
                    {h.name}
                  </option>
                ))}
              </select>
              <select
                value={inqType}
                onChange={(e) => setInqType(e.target.value)}
                className="w-full px-3 py-2 text-xs font-bold rounded-xl border border-[#DCE7F8] bg-[#F7FAFF]"
              >
                <option value="courtesy_rate_swap">Courtesy Neighbor Rate Swap</option>
                <option value="group_overflow_check">Group / Overflow Inquiry</option>
              </select>
            </div>
            <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
              <input
                type="number"
                min={1}
                value={inqRooms}
                onChange={(e) => setInqRooms(Number(e.target.value || 1))}
                placeholder="Rooms"
                className="px-3 py-2 text-xs font-bold rounded-xl border border-[#DCE7F8] bg-[#F7FAFF]"
              />
              <input
                type="number"
                value={inqQuoted}
                onChange={(e) => setInqQuoted(e.target.value)}
                placeholder="Quoted $ (optional)"
                className="px-3 py-2 text-xs font-bold rounded-xl border border-[#DCE7F8] bg-[#F7FAFF]"
              />
              <button type="submit" className="col-span-2 sm:col-span-1 py-2 px-3 rounded-xl bg-[#0D255B] text-white text-xs font-bold hover:bg-blue-800">
                Draft / Log Email
              </button>
            </div>
          </form>

          <div className="space-y-2 max-h-[160px] overflow-y-auto pt-1">
            {inquiries.map((inq) => (
              <div key={inq.id} className="ember-subtle-card p-2.5 flex items-center justify-between gap-2 text-xs">
                <div className="min-w-0">
                  <div className="font-extrabold text-[#0B1B3B] truncate">{inq.target_hotel_name}</div>
                  <div className="text-[11px] text-[#475B80] truncate">{inq.subject}</div>
                </div>
                <span className={`px-2 py-0.5 rounded-full text-[10px] font-extrabold shrink-0 ${inq.quoted_rate ? 'bg-emerald-50 text-emerald-700' : 'bg-blue-50 text-blue-700'}`}>
                  {inq.quoted_rate ? `$${inq.quoted_rate}` : inq.status}
                </span>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Call Logs History Table */}
      <div className="ember-card p-5">
        <h2 className="text-sm font-extrabold text-[#0B1B3B] mb-3">Overnight Courtesy Call History</h2>
        <DataTable
          data={portal.call_logs}
          columns={callColumns}
          density={density}
          searchPlaceholder="Filter call logs..."
          csvFilename="hotelrateintel-night-audit-calls.csv"
          csvHeaders={['Property', 'Shift', 'Walk-In BAR', 'Occ %', 'Rooms Left', 'Notes']}
          csvRowMapper={(c) => [c.hotel_name || '', c.shift, c.quoted_walkin_rate ?? '', c.reported_occupancy_pct ?? '', c.rooms_left ?? '', c.transcript || '']}
        />
      </div>
    </div>
  )
}
