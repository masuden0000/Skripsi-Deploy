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
