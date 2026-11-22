import React, { useMemo, useState } from 'react'
import {
  flexRender,
  getCoreRowModel,
  getFilteredRowModel,
  getPaginationRowModel,
  getSortedRowModel,
  useReactTable,
  type ColumnDef,
  type SortingState,
  type RowSelectionState,
} from '@tanstack/react-table'
import { ArrowUpDown, ChevronLeft, ChevronRight, Download, Search } from 'lucide-react'
import { exportToCsv } from '../../utils/csv'

interface FilterOption {
  label: string
  value: string
}

interface DataTableProps<TData> {
  data: TData[]
  columns: ColumnDef<TData, unknown>[]
  searchPlaceholder?: string
  filterColumnId?: string
  filterOptions?: FilterOption[]
  csvFilename?: string
  csvHeaders?: string[]
  csvRowMapper?: (row: TData) => Array<string | number | boolean | null | undefined>
  enableRowSelection?: boolean
  bulkActionRender?: (selectedRows: TData[], clearSelection: () => void) => React.ReactNode
  density?: 'compact' | 'comfortable'
  pageSize?: number
}

export function DataTable<TData>({
  data,
  columns,
  searchPlaceholder = 'Search records...',
  filterColumnId,
  filterOptions,
  csvFilename = 'hotelrateintel-export.csv',
  csvHeaders,
  csvRowMapper,
  enableRowSelection = false,
  bulkActionRender,
  density = 'compact',
  pageSize = 8,
}: DataTableProps<TData>) {
  const [sorting, setSorting] = useState<SortingState>([])
  const [globalFilter, setGlobalFilter] = useState('')
  const [statusFilter, setStatusFilter] = useState('ALL')
  const [rowSelection, setRowSelection] = useState<RowSelectionState>({})

  const filteredData = useMemo(() => {
    if (!filterColumnId || statusFilter === 'ALL') return data
    return data.filter((item) => {
      const val = (item as Record<string, unknown>)[filterColumnId]
      return String(val || '').toUpperCase() === statusFilter.toUpperCase()
    })
  }, [data, filterColumnId, statusFilter])

  const finalColumns = useMemo(() => {
    if (!enableRowSelection) return columns
    const selectCol: ColumnDef<TData, unknown> = {
      id: '_select',
      header: ({ table }) => (
        <input
          type="checkbox"
          aria-label="Select all visible rows"
          checked={table.getIsAllPageRowsSelected()}
          onChange={table.getToggleAllPageRowsSelectedHandler()}
          className="rounded border-slate-300 text-blue-600 focus:ring-blue-500 cursor-pointer"
        />
      ),
      cell: ({ row }) => (
        <input
          type="checkbox"
          aria-label="Select row"
          checked={row.getIsSelected()}
          onChange={row.getToggleSelectedHandler()}
          className="rounded border-slate-300 text-blue-600 focus:ring-blue-500 cursor-pointer"
        />
      ),
      enableSorting: false,
    }
    return [selectCol, ...columns]
  }, [columns, enableRowSelection])

  const table = useReactTable({
    data: filteredData,
    columns: finalColumns,
    state: { sorting, globalFilter, rowSelection },
    onSortingChange: setSorting,
    onGlobalFilterChange: setGlobalFilter,
    onRowSelectionChange: setRowSelection,
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: getSortedRowModel(),
    getFilteredRowModel: getFilteredRowModel(),
    getPaginationRowModel: getPaginationRowModel(),
    initialState: { pagination: { pageSize } },
  })

  const selectedRows = table.getSelectedRowModel().rows.map((r) => r.original)
  const cellPad = density === 'compact' ? 'px-3 py-2.5' : 'px-4 py-3.5'

  const handleExport = () => {
    if (!csvHeaders || !csvRowMapper) return
    const target = selectedRows.length > 0 ? selectedRows : table.getFilteredRowModel().rows.map((r) => r.original)
    exportToCsv(csvFilename, csvHeaders, target.map(csvRowMapper))
  }

  return (
    <div className="space-y-3">
      <div className="flex flex-wrap items-center justify-between gap-2.5">
        <div className="flex flex-wrap items-center gap-2 flex-1 min-w-[220px]">
          <div className="relative flex-1 max-w-xs">
            <Search className="w-3.5 h-3.5 text-[#6D81A8] absolute left-3 top-1/2 -translate-y-1/2" />
            <input
              type="text"
              value={globalFilter}
              onChange={(e) => setGlobalFilter(e.target.value)}
              placeholder={searchPlaceholder}
              className="w-full pl-8 pr-3 py-1.5 text-xs rounded-xl border border-[#DCE7F8] bg-[#F7FAFF] text-[#0B1B3B] placeholder-[#6D81A8] focus:outline-none focus:ring-2 focus:ring-blue-500/30"
            />
          </div>

          {filterOptions && filterOptions.length > 0 && (
            <div className="inline-flex items-center gap-1 bg-[#F2F6FD] p-1 rounded-xl border border-[#DCE7F8]">
              {filterOptions.map((opt) => (
                <button
                  key={opt.value}
                  type="button"
                  onClick={() => {
                    setStatusFilter(opt.value)
                    table.setPageIndex(0)
                  }}
                  className={`px-2.5 py-1 rounded-lg text-[11px] font-bold transition ${
                    statusFilter === opt.value
                      ? 'bg-blue-600 text-white shadow-sm'
                      : 'text-[#475B80] hover:bg-white'
                  }`}
                >
                  {opt.label}
                </button>
              ))}
            </div>
          )}
        </div>

        <div className="flex items-center gap-2 flex-wrap">
          {enableRowSelection && selectedRows.length > 0 && bulkActionRender && (
            <div className="flex items-center gap-2 bg-blue-50 border border-blue-200 px-2.5 py-1 rounded-xl">
              <span className="text-[11px] font-extrabold text-blue-800">{selectedRows.length} selected</span>
              {bulkActionRender(selectedRows, () => setRowSelection({}))}
            </div>
          )}

          {csvHeaders && csvRowMapper && (
            <button
              type="button"
              onClick={handleExport}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-bold bg-[#F7FAFF] border border-[#DCE7F8] text-[#0B1B3B] hover:bg-blue-50 hover:border-blue-200 transition"
            >
              <Download className="w-3.5 h-3.5 text-blue-600" />
              Export CSV
            </button>
          )}
        </div>
      </div>

      <div className="overflow-x-auto rounded-2xl border border-[#DCE7F8] bg-white">
        <table className="w-full text-left border-collapse text-xs">
          <thead className="bg-[#F5F9FF] border-b border-[#DCE7F8]">
            {table.getHeaderGroups().map((hg) => (
              <tr key={hg.id}>
                {hg.headers.map((header) => {
                  const canSort = header.column.getCanSort()
                  return (
                    <th
                      key={header.id}
                      onClick={canSort ? header.column.getToggleSortingHandler() : undefined}
                      className={`${cellPad} text-[10.5px] font-extrabold uppercase tracking-wider text-[#475B80] whitespace-nowrap ${
                        canSort ? 'cursor-pointer select-none hover:text-blue-700' : ''
                      }`}
                    >
                      <div className="inline-flex items-center gap-1">
                        {flexRender(header.column.columnDef.header, header.getContext())}
                        {canSort && <ArrowUpDown className="w-3 h-3 opacity-60" />}
                      </div>
                    </th>
                  )
                })}
              </tr>
            ))}
          </thead>
          <tbody>
            {table.getRowModel().rows.length === 0 ? (
              <tr>
                <td colSpan={finalColumns.length} className="py-8 text-center text-xs text-[#6D81A8] font-medium">
                  No matching records for the current filter.
                </td>
              </tr>
            ) : (
              table.getRowModel().rows.map((row) => (
                <tr
                  key={row.id}
                  className="border-b border-[#EEF4FD] last:border-b-0 hover:bg-[#F7FAFF] transition-colors"
                >
                  {row.getVisibleCells().map((cell) => (
                    <td key={cell.id} className={`${cellPad} text-[#0B1B3B] align-middle`}>
                      {flexRender(cell.column.columnDef.cell, cell.getContext())}
                    </td>
                  ))}
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {table.getPageCount() > 1 && (
        <div className="flex items-center justify-between text-xs text-[#475B80] px-1">
          <span className="font-medium tabular-nums">
            Page {table.getState().pagination.pageIndex + 1} of {table.getPageCount()} · {table.getFilteredRowModel().rows.length} rows
          </span>
          <div className="inline-flex items-center gap-1.5">
            <button
              type="button"
              onClick={() => table.previousPage()}
              disabled={!table.getCanPreviousPage()}
              aria-label="Previous page"
              className="p-1.5 rounded-xl border border-[#DCE7F8] bg-white disabled:opacity-40 hover:bg-blue-50"
            >
              <ChevronLeft className="w-3.5 h-3.5" />
            </button>
            <button
              type="button"
              onClick={() => table.nextPage()}
              disabled={!table.getCanNextPage()}
              aria-label="Next page"
              className="p-1.5 rounded-xl border border-[#DCE7F8] bg-white disabled:opacity-40 hover:bg-blue-50"
            >
              <ChevronRight className="w-3.5 h-3.5" />
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
