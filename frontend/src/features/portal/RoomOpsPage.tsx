import React, { useEffect, useState } from 'react'
import { Plus, Send, Trash2, Wrench } from 'lucide-react'
import { usePortalStore } from '../../store/usePortalStore'
import type { RoomCategoryItem } from '../../types/hospitality'
import { MetricCard } from '../../components/ui/MetricCard'

export const RoomOpsPage: React.FC = () => {
  const { opsPlan, saveRoomOps, sendTelegramAlert } = usePortalStore()
  const { ops, status_flag_catalog, default_ops_tags } = opsPlan

  const [totalRooms, setTotalRooms] = useState(ops.total_rooms)
  const [roomsSold, setRoomsSold] = useState(ops.rooms_sold)
  const [oooRooms, setOooRooms] = useState(ops.ooo_rooms)
  const [oosRooms, setOosRooms] = useState(ops.oos_rooms)
  const [hkHold, setHkHold] = useState(ops.housekeeping_hold)
  const [flags, setFlags] = useState<string[]>(ops.status_flags || [])
  const [tags, setTags] = useState<string[]>(ops.operational_tags || [])
  const [notes, setNotes] = useState(ops.notes || '')
  const [roomTypes, setRoomTypes] = useState<RoomCategoryItem[]>(ops.room_types || [])
  const [tgPreview, setTgPreview] = useState('')

  useEffect(() => {
    setTotalRooms(ops.total_rooms)
    setRoomsSold(ops.rooms_sold)
    setOooRooms(ops.ooo_rooms)
    setOosRooms(ops.oos_rooms)
    setHkHold(ops.housekeeping_hold)
    setFlags(ops.status_flags || [])
    setTags(ops.operational_tags || [])
    setNotes(ops.notes || '')
    setRoomTypes(ops.room_types || [])
  }, [ops])

  const offlinePreview = Math.min(Math.max(1, totalRooms), Math.max(0, oooRooms) + Math.max(0, oosRooms) + Math.max(0, hkHold))
  const sellablePreview = Math.max(0, Math.max(1, totalRooms) - offlinePreview)
  const remainingPreview = Math.max(0, sellablePreview - Math.max(0, roomsSold))
  const grossOccPreview = Number(((Math.max(0, roomsSold) / Math.max(1, totalRooms)) * 100).toFixed(1))
  const netOccPreview = sellablePreview === 0 ? 100 : Number(Math.min(100, (Math.max(0, roomsSold) / sellablePreview) * 100).toFixed(1))

  const toggleFlag = (id: string) => {
    setFlags((prev) => (prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id]))
  }

  const toggleTag = (tag: string) => {
    setTags((prev) => (prev.includes(tag) ? prev.filter((x) => x !== tag) : [...prev, tag]))
  }

  const updateRoomRow = (idx: number, patch: Partial<RoomCategoryItem>) => {
    setRoomTypes((prev) => prev.map((r, i) => (i === idx ? { ...r, ...patch } : r)))
  }

  const handleAddCategory = () => {
    setRoomTypes((prev) => [
      ...prev,
      {
        code: `RM${prev.length + 1}`,
        name: 'Connecting Family Suite',
        total: 4,
        ooo: 0,
        oos: 0,
        bar: 289,
        stop_sell: false,
      },
    ])
  }

  const handleDeleteCategory = (idx: number) => {
    setRoomTypes((prev) => prev.filter((_, i) => i !== idx))
  }

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault()
    await saveRoomOps({
      total_rooms: totalRooms,
      rooms_sold: roomsSold,
      ooo_rooms: oooRooms,
      oos_rooms: oosRooms,
      housekeeping_hold: hkHold,
      status_flags: flags,
      operational_tags: tags,
      notes,
      room_types: roomTypes,
    })
  }

  const handleTelegram = async () => {
    const preview = await sendTelegramAlert(notes, tags)
    setTgPreview(preview)
  }

  return (
    <div className="space-y-5">
      <div>
        <span className="text-[11px] font-extrabold uppercase tracking-wider text-blue-700">
          Reservations &amp; Housekeeping Control Desk
        </span>
        <h1 className="text-xl sm:text-2xl font-black text-[#0B1B3B] tracking-tight">
          Live Room Ops: OOO, OOS, Housekeeping Holds &amp; Room Switches
        </h1>
        <p className="text-xs text-[#475B80]">
          Adjust physical counts whenever AC fails (OOO), maintenance blocks a room (OOS), housekeeping is short-staffed, or rooms are reconfigured.
        </p>
      </div>

      {/* Live Calculated KPI Strip */}
      <div className="grid grid-cols-2 lg:grid-cols-5 gap-3.5">
        <MetricCard label="Total Physical Rooms" value={totalRooms} sub="Modifiable anytime" tone="slate" />
        <MetricCard
          label="Offline Holds"
          value={offlinePreview}
          sub={`${oooRooms} OOO · ${oosRooms} OOS · ${hkHold} HK Hold`}
          tone={offlinePreview > 0 ? 'rose' : 'slate'}
        />
        <MetricCard
          label="True Sellable Rooms"
          value={sellablePreview}
          delta={`${remainingPreview} left`}
          sub="Available before oversell"
          tone="royal"
        />
        <MetricCard
          label="True Net Occupancy"
          value={`${netOccPreview}%`}
          delta={`+${(netOccPreview - grossOccPreview).toFixed(1)}%`}
          sub={`Gross Occ: ${grossOccPreview}%`}
          tone={netOccPreview >= 85 ? 'amber' : 'emerald'}
        />
        <MetricCard
          label="AI Verdict"
          value={`$${opsPlan.recommended_bar}`}
          sub={opsPlan.action_verdict}
          tone="royal"
          icon={<Wrench className="w-4 h-4" />}
        />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-4">
        <form onSubmit={handleSave} className="lg:col-span-6 ember-card p-5 space-y-4">
          <h2 className="text-sm font-extrabold text-[#0B1B3B]">1. Adjust Property Room Counts &amp; Holds</h2>

          <div className="grid grid-cols-2 sm:grid-cols-5 gap-2.5">
            <div>
              <label htmlFor="ops-total" className="block text-[10px] font-extrabold uppercase text-[#475B80] mb-1">Total</label>
              <input
                id="ops-total"
                type="number"
                min={1}
                value={totalRooms}
                onChange={(e) => setTotalRooms(Math.max(1, Number(e.target.value || 1)))}
                className="w-full px-2.5 py-2 text-xs font-bold rounded-xl border border-[#DCE7F8] bg-[#F7FAFF] tabular-nums"
              />
            </div>
            <div>
              <label htmlFor="ops-sold" className="block text-[10px] font-extrabold uppercase text-[#475B80] mb-1">Sold</label>
              <input
                id="ops-sold"
                type="number"
                min={0}
                value={roomsSold}
                onChange={(e) => setRoomsSold(Math.max(0, Number(e.target.value || 0)))}
                className="w-full px-2.5 py-2 text-xs font-bold rounded-xl border border-[#DCE7F8] bg-[#F7FAFF] tabular-nums"
              />
            </div>
            <div>
              <label htmlFor="ops-ooo" className="block text-[10px] font-extrabold uppercase text-rose-600 mb-1">OOO</label>
              <input
                id="ops-ooo"
                type="number"
                min={0}
                value={oooRooms}
                onChange={(e) => setOooRooms(Math.max(0, Number(e.target.value || 0)))}
                className="w-full px-2.5 py-2 text-xs font-bold rounded-xl border border-rose-200 bg-rose-50/40 tabular-nums"
              />
            </div>
            <div>
              <label htmlFor="ops-oos" className="block text-[10px] font-extrabold uppercase text-amber-700 mb-1">OOS</label>
              <input
                id="ops-oos"
                type="number"
                min={0}
                value={oosRooms}
                onChange={(e) => setOosRooms(Math.max(0, Number(e.target.value || 0)))}
                className="w-full px-2.5 py-2 text-xs font-bold rounded-xl border border-amber-200 bg-amber-50/40 tabular-nums"
              />
            </div>
            <div>
              <label htmlFor="ops-hk" className="block text-[10px] font-extrabold uppercase text-blue-700 mb-1">HK Hold</label>
              <input
                id="ops-hk"
                type="number"
                min={0}
                value={hkHold}
                onChange={(e) => setHkHold(Math.max(0, Number(e.target.value || 0)))}
                className="w-full px-2.5 py-2 text-xs font-bold rounded-xl border border-blue-200 bg-blue-50/40 tabular-nums"
              />
            </div>
          </div>

          <div>
            <div className="text-[10.5px] font-extrabold uppercase text-[#475B80] mb-1.5">Active Hotel Status Flags</div>
            <div className="flex flex-wrap gap-1.5">
              {status_flag_catalog.map((f) => {
                const on = flags.includes(f.id)
                return (
                  <button
                    key={f.id}
                    type="button"
                    onClick={() => toggleFlag(f.id)}
                    className={`px-2.5 py-1 rounded-full text-[11px] font-bold border transition ${
                      on ? 'bg-blue-600 text-white border-blue-600' : 'bg-[#F7FAFF] text-[#475B80] border-[#DCE7F8] hover:bg-blue-50'
                    }`}
                  >
                    {on ? '✓ ' : ''}
                    {f.label}
                  </button>
                )
              })}
            </div>
          </div>

          <div>
            <div className="text-[10.5px] font-extrabold uppercase text-[#475B80] mb-1.5">Telegram Shift Alert Tags</div>
            <div className="flex flex-wrap gap-1.5">
              {default_ops_tags.map((t) => {
                const on = tags.includes(t)
                return (
                  <button
                    key={t}
                    type="button"
                    onClick={() => toggleTag(t)}
                    className={`px-2.5 py-1 rounded-full text-[11px] font-bold border transition ${
                      on ? 'bg-[#0D255B] text-white border-[#0D255B]' : 'bg-[#F7FAFF] text-[#475B80] border-[#DCE7F8]'
                    }`}
                  >
                    {t}
                  </button>
                )
              })}
            </div>
          </div>

          <div>
            <label htmlFor="ops-notes" className="block text-[10.5px] font-extrabold uppercase text-[#475B80] mb-1">
              Shift Handoff Note
            </label>
            <input
              id="ops-notes"
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              placeholder="e.g. Rm 204 AC OOO; 2 HK call-outs -> CTA + close discount OTAs"
              className="w-full px-3 py-2 text-xs rounded-xl border border-[#DCE7F8] bg-[#F7FAFF]"
            />
          </div>

          <div className="flex flex-wrap gap-2 pt-1">
            <button type="submit" className="px-4 py-2 rounded-xl bg-blue-600 text-white text-xs font-bold hover:bg-blue-700">
              Save Inventory &amp; Recalculate AI Pricing
            </button>
            <button
              type="button"
              onClick={handleTelegram}
              className="px-4 py-2 rounded-xl bg-[#0D255B] text-white text-xs font-bold inline-flex items-center gap-1.5 hover:bg-blue-800"
            >
              <Send className="w-3.5 h-3.5" />
              Send Telegram Shift Alert
            </button>
          </div>

          {tgPreview && (
            <pre className="p-3 rounded-2xl bg-[#F7FAFF] border border-[#DCE7F8] text-[11px] whitespace-pre-wrap text-[#0B1B3B] font-mono">
              {tgPreview}
            </pre>
          )}
        </form>

        {/* Room Category Mix Editor */}
        <div className="lg:col-span-6 ember-card p-5 space-y-4">
          <div className="flex items-center justify-between gap-2">
            <div>
              <h2 className="text-sm font-extrabold text-[#0B1B3B]">2. Room Category Switcher &amp; Stop-Sell</h2>
              <p className="text-[11px] text-[#6D81A8]">Add, edit, or delete categories during suite conversions or holds</p>
            </div>
            <button
              type="button"
              onClick={handleAddCategory}
              className="px-3 py-1.5 rounded-xl bg-blue-50 text-blue-700 text-xs font-bold inline-flex items-center gap-1 hover:bg-blue-100"
            >
              <Plus className="w-3.5 h-3.5" />
              Add Category
            </button>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs border-collapse">
              <thead className="bg-[#F5F9FF] border-b border-[#DCE7F8]">
                <tr>
                  <th className="p-2 text-[10px] font-extrabold uppercase text-[#475B80]">Category</th>
                  <th className="p-2 text-[10px] font-extrabold uppercase text-[#475B80]">Total</th>
                  <th className="p-2 text-[10px] font-extrabold uppercase text-[#475B80]">OOO</th>
                  <th className="p-2 text-[10px] font-extrabold uppercase text-[#475B80]">OOS</th>
                  <th className="p-2 text-[10px] font-extrabold uppercase text-[#475B80]">BAR $</th>
                  <th className="p-2 text-[10px] font-extrabold uppercase text-[#475B80]">Stop</th>
                  <th className="p-2" />
                </tr>
              </thead>
              <tbody>
                {roomTypes.map((rt, idx) => (
                  <tr key={idx} className="border-b border-[#EEF4FD] last:border-b-0">
                    <td className="p-1.5">
                      <input
                        aria-label={`Category name row ${idx + 1}`}
                        value={rt.name}
                        onChange={(e) => updateRoomRow(idx, { name: e.target.value })}
                        className="w-full min-w-[115px] px-2 py-1 text-xs font-bold rounded-lg border border-[#DCE7F8] bg-[#F7FAFF]"
                      />
                    </td>
                    <td className="p-1.5">
                      <input
                        type="number"
                        value={rt.total}
                        onChange={(e) => updateRoomRow(idx, { total: Number(e.target.value || 0) })}
                        className="w-14 px-2 py-1 text-xs font-bold rounded-lg border border-[#DCE7F8] tabular-nums"
                      />
                    </td>
                    <td className="p-1.5">
                      <input
                        type="number"
                        value={rt.ooo}
                        onChange={(e) => updateRoomRow(idx, { ooo: Number(e.target.value || 0) })}
                        className="w-12 px-2 py-1 text-xs font-bold rounded-lg border border-[#DCE7F8] tabular-nums"
                      />
                    </td>
                    <td className="p-1.5">
                      <input
                        type="number"
                        value={rt.oos}
                        onChange={(e) => updateRoomRow(idx, { oos: Number(e.target.value || 0) })}
                        className="w-12 px-2 py-1 text-xs font-bold rounded-lg border border-[#DCE7F8] tabular-nums"
                      />
                    </td>
                    <td className="p-1.5">
                      <input
                        type="number"
                        value={rt.bar}
                        onChange={(e) => updateRoomRow(idx, { bar: Number(e.target.value || 49) })}
                        className="w-16 px-2 py-1 text-xs font-bold rounded-lg border border-[#DCE7F8] tabular-nums"
                      />
                    </td>
                    <td className="p-1.5 text-center">
                      <input
                        type="checkbox"
                        checked={rt.stop_sell}
                        onChange={(e) => updateRoomRow(idx, { stop_sell: e.target.checked })}
                      />
                    </td>
                    <td className="p-1.5">
                      <button
                        type="button"
                        aria-label={`Remove ${rt.name}`}
                        onClick={() => handleDeleteCategory(idx)}
                        className="p-1 rounded-lg text-rose-600 hover:bg-rose-50"
                      >
                        <Trash2 className="w-3.5 h-3.5" />
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  )
}
