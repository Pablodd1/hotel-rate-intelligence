import React, { useEffect } from 'react'
import { X } from 'lucide-react'

interface ModalDialogProps {
  open: boolean
  title: string
  subtitle?: string
  onClose: () => void
  children: React.ReactNode
  maxWidthClass?: string
}

export const ModalDialog: React.FC<ModalDialogProps> = ({
  open,
  title,
  subtitle,
  onClose,
  children,
  maxWidthClass = 'max-w-xl',
}) => {
  useEffect(() => {
    if (!open) return
    const handleKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose()
    }
    window.addEventListener('keydown', handleKey)
    return () => window.removeEventListener('keydown', handleKey)
  }, [open, onClose])

  if (!open) return null

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-[#06122E]/65 backdrop-blur-sm"
      role="dialog"
      aria-modal="true"
      aria-label={title}
      onClick={(e) => {
        if (e.target === e.currentTarget) onClose()
      }}
    >
      <div className={`w-full ${maxWidthClass} max-h-[90vh] overflow-y-auto rounded-3xl bg-white border border-[#DCE7F8] shadow-emberShell p-5 sm:p-6`}>
        <div className="flex items-start justify-between gap-4 border-b border-[#EAF1FC] pb-3 mb-4">
          <div>
            <h3 className="text-lg font-extrabold text-[#0B1B3B] tracking-tight">{title}</h3>
            {subtitle && <p className="text-xs text-[#475B80] mt-0.5">{subtitle}</p>}
          </div>
          <button
            type="button"
            onClick={onClose}
            aria-label="Close modal"
            className="p-1.5 rounded-xl bg-[#F2F6FD] text-[#475B80] hover:bg-blue-100 hover:text-blue-700 transition"
          >
            <X className="w-4 h-4" />
          </button>
        </div>
        {children}
      </div>
    </div>
  )
}
