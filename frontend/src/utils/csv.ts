export function exportToCsv(filename: string, headers: string[], rows: Array<Array<string | number | boolean | null | undefined>>): string {
  const escapeCell = (val: string | number | boolean | null | undefined): string => {
    const raw = val === null || val === undefined ? '' : String(val)
    if (/[",\n\r]/.test(raw)) {
      return `"${raw.replace(/"/g, '""')}"`
    }
    return raw
  }

  const lines = [
    headers.map(escapeCell).join(','),
    ...rows.map((row) => row.map(escapeCell).join(',')),
  ]
  const csvContent = lines.join('\r\n')

  if (
    typeof window !== 'undefined' &&
    typeof document !== 'undefined' &&
    typeof URL !== 'undefined' &&
    typeof URL.createObjectURL === 'function'
  ) {
    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' })
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.setAttribute('download', filename)
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    setTimeout(() => URL.revokeObjectURL?.(url), 1000)
  }

  return csvContent
}
