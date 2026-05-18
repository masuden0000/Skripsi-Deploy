type IconProps = {
  className?: string
}

type ChevronIconProps = IconProps & {
  open: boolean
}

export function ChevronIcon({ open, className }: ChevronIconProps) {
  return (
    <svg
      className={`size-4 transition-transform duration-200 flex-none ${open ? "rotate-180" : ""} ${className ?? ""}`}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={2}
    >
      <path strokeLinecap="round" strokeLinejoin="round" d="M19 9l-7 7-7-7" />
    </svg>
  )
}

export function PlusIcon({ className }: IconProps) {
  return (
    <svg className={`size-4 ${className ?? ""}`} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M12 5v14M5 12h14" />
    </svg>
  )
}

export function CalendarIcon({ className }: IconProps) {
  return (
    <svg
      className={`size-3.5 flex-none opacity-60 ${className ?? ""}`}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={2}
    >
      <rect x="3" y="4" width="18" height="18" rx="2" />
      <path strokeLinecap="round" d="M16 2v4M8 2v4M3 10h18" />
    </svg>
  )
}

export function EditIcon({ className }: IconProps) {
  return (
    <svg className={`size-3.5 ${className ?? ""}`} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M12 20h9" />
      <path strokeLinecap="round" strokeLinejoin="round" d="M16.5 3.5a2.121 2.121 0 1 1 3 3L7 19l-4 1 1-4 12.5-12.5Z" />
    </svg>
  )
}

export function TrashIcon({ className }: IconProps) {
  return (
    <svg className={`size-3.5 ${className ?? ""}`} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M3 6h18M19 6v14a2 2 0 01-2 2H7a2 2 0 01-2-2V6m3 0V4a2 2 0 012-2h4a2 2 0 012 2v2" />
    </svg>
  )
}

export function DetailIcon({ className }: IconProps) {
  return (
    <svg className={`size-3.5 ${className ?? ""}`} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M9 18l6-6-6-6" />
    </svg>
  )
}

export function ArrowLeftIcon({ className }: IconProps) {
  return (
    <svg className={`size-4 ${className ?? ""}`} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M19 12H5M12 19l-7-7 7-7" />
    </svg>
  )
}

export function CloseIcon({ className }: IconProps) {
  return (
    <svg className={`size-4 ${className ?? ""}`} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
    </svg>
  )
}

export function UserIcon({ className }: IconProps) {
  return (
    <svg className={`size-5 ${className ?? ""}`} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M20 21a8 8 0 0 0-16 0" />
      <circle cx="12" cy="7" r="4" />
    </svg>
  )
}

export function GraduationIcon({ className }: IconProps) {
  return (
    <svg className={`size-5 ${className ?? ""}`} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2}>
      <path strokeLinecap="round" strokeLinejoin="round" d="m3 8 9-5 9 5-9 5-9-5Z" />
      <path strokeLinecap="round" strokeLinejoin="round" d="M7 10.5v4.25C7 16.55 9.24 18 12 18s5-1.45 5-3.25V10.5" />
      <path strokeLinecap="round" strokeLinejoin="round" d="M21 9v5" />
    </svg>
  )
}

export function ReviewIcon({ className }: IconProps) {
  return (
    <svg className={`size-5 ${className ?? ""}`} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M3 5h18" />
      <path strokeLinecap="round" strokeLinejoin="round" d="M7 5V3" />
      <path strokeLinecap="round" strokeLinejoin="round" d="M17 5V3" />
      <rect x="3" y="5" width="18" height="16" rx="2" />
      <path strokeLinecap="round" strokeLinejoin="round" d="m9 13 2 2 4-4" />
    </svg>
  )
}

export function StarIcon({ className }: IconProps) {
  return (
    <svg className={`size-5 ${className ?? ""}`} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2}>
      <path strokeLinecap="round" strokeLinejoin="round" d="m12 3 2.8 5.67 6.2.9-4.5 4.38 1.06 6.18L12 17.27l-5.56 2.86 1.06-6.18L3 9.57l6.2-.9L12 3Z" />
    </svg>
  )
}

export function EmailIcon({ className }: IconProps) {
  return (
    <svg className={`size-4 ${className ?? ""}`} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2}>
      <rect x="3" y="5" width="18" height="14" rx="2" />
      <path strokeLinecap="round" strokeLinejoin="round" d="m3 7 9 6 9-6" />
    </svg>
  )
}

export function LinkIcon({ className }: IconProps) {
  return (
    <svg className={`size-4 flex-none ${className ?? ""}`} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71" />
      <path strokeLinecap="round" strokeLinejoin="round" d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71" />
    </svg>
  )
}

export function SearchIcon({ className }: IconProps) {
  return (
    <svg className={`size-4 ${className ?? ""}`} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2}>
      <circle cx="11" cy="11" r="8" />
      <path strokeLinecap="round" d="m21 21-4.35-4.35" />
    </svg>
  )
}

export function EyeIcon({ className }: IconProps) {
  return (
    <svg className={`size-4 ${className ?? ""}`} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8Z" />
      <circle cx="12" cy="12" r="3" />
    </svg>
  )
}

export function EyeOffIcon({ className }: IconProps) {
  return (
    <svg className={`size-4 ${className ?? ""}`} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M9.88 9.88a3 3 0 1 0 4.24 4.24" />
      <path strokeLinecap="round" strokeLinejoin="round" d="M10.73 5.08A10.43 10.43 0 0 1 12 5c7 0 10 7 10 7a13.16 13.16 0 0 1-1.67 2.68" />
      <path strokeLinecap="round" strokeLinejoin="round" d="M6.61 6.61A13.526 13.526 0 0 0 2 12s3 7 10 7a9.74 9.74 0 0 0 5.39-1.61" />
      <line x1="2" x2="22" y1="2" y2="22" />
    </svg>
  )
}

export function DocumentIcon({ className }: IconProps) {
  return (
    <svg className={`size-5 ${className ?? ""}`} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M14.5 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7.5L14.5 2z" />
      <polyline points="14 2 14 8 20 8" />
      <line x1="16" x2="8" y1="13" y2="13" />
      <line x1="16" x2="8" y1="17" y2="17" />
      <line x1="10" x2="8" y1="9" y2="9" />
    </svg>
  )
}

export function FileTextIcon({ className }: IconProps) {
  return (
    <svg className={`size-4 ${className ?? ""}`} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
      <polyline points="14 2 14 8 20 8" />
      <line x1="16" x2="8" y1="13" y2="13" />
      <line x1="16" x2="8" y1="17" y2="17" />
      <polyline points="10 9 9 9 8 9" />
    </svg>
  )
}

export function UploadIcon({ className }: IconProps) {
  return (
    <svg className={`size-5 ${className ?? ""}`} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
      <polyline points="17 8 12 3 7 8" />
      <line x1="12" x2="12" y1="3" y2="15" />
    </svg>
  )
}

export function CheckCircleIcon({ className }: IconProps) {
  return (
    <svg className={`size-5 ${className ?? ""}`} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M22 11.08V12a10 10 0 1 1-5.93-9.14" />
      <polyline points="22 4 12 14.01 9 11.01" />
    </svg>
  )
}

export function AlertCircleIcon({ className }: IconProps) {
  return (
    <svg className={`size-5 ${className ?? ""}`} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2}>
      <circle cx="12" cy="12" r="10" />
      <line x1="12" x2="12" y1="8" y2="12" />
      <line x1="12" x2="12.01" y1="16" y2="16" />
    </svg>
  )
}

export function Loader2Icon({ className }: IconProps) {
  return (
    <svg className={`size-5 ${className ?? ""}`} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2}>
      <path d="M21 12a9 9 0 1 1-6.219-8.56" />
    </svg>
  )
}

export function CopyIcon({ className }: IconProps) {
  return (
    <svg className={`size-4 ${className ?? ""}`} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2}>
      <rect x="9" y="9" width="13" height="13" rx="2" ry="2" />
      <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1" />
    </svg>
  )
}

export function CheckIcon({ className }: IconProps) {
  return (
    <svg className={`size-4 ${className ?? ""}`} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2}>
      <polyline points="20 6 9 17 4 12" />
    </svg>
  )
}

export function XIcon({ className }: IconProps) {
  return (
    <svg className={`size-5 ${className ?? ""}`} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2}>
      <circle cx="12" cy="12" r="10" />
      <path d="m15 9-6 6M9 9l6 6" />
    </svg>
  )
}

export function HistoryIcon({ className }: IconProps) {
  return (
    <svg className={`size-4 ${className ?? ""}`} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round">
      <path d="M3 12a9 9 0 1 0 9-9 9.75 9.75 0 0 0-6.74 2.74L3 8" />
      <path d="M3 3v5h5" />
      <path d="M12 7v5l4 2" />
    </svg>
  )
}

export function DownloadIcon({ className }: IconProps) {
  return (
    <svg className={`size-4 ${className ?? ""}`} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round">
      <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
      <polyline points="7 10 12 15 17 10" />
      <line x1="12" y1="15" x2="12" y2="3" />
    </svg>
  )
}
