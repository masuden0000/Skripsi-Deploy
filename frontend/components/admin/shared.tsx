import type { ReactNode } from "react"
import { CloseIcon } from "@/components/icons/public-icons"
import { cn } from "@/lib/utils"
export { SearchInput } from "./SearchInput"
export { PasswordInput } from "./PasswordInput"

export function AdminPageHeader({
  title,
  description,
  action,
  className,
}: {
  title: string
  description: string
  action?: ReactNode
  className?: string
}) {
  return (
    <div className={cn("mb-7 flex items-start justify-between gap-4", className)}>
      <div>
        <h1 className="text-xl font-semibold text-gray-800">{title}</h1>
        <p className="mt-0.5 text-sm text-[rgba(0,0,0,0.4)]">{description}</p>
      </div>
      {action ? <div className="shrink-0">{action}</div> : null}
    </div>
  )
}

export function AdminSurfaceCard({
  children,
  className,
}: {
  children: ReactNode
  className?: string
}) {
  return (
    <div className={cn("overflow-hidden rounded-xl border border-gray-100 bg-white shadow-sm", className)}>
      {children}
    </div>
  )
}

export function AdminModalShell({
  title,
  description,
  onClose,
  maxWidthClassName = "max-w-md",
  children,
}: {
  title: string
  description: string
  onClose: () => void
  maxWidthClassName?: string
  children: ReactNode
}) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      <button
        type="button"
        aria-label="Tutup modal"
        className="absolute inset-0 bg-black/25 backdrop-blur-[2px]"
        onClick={onClose}
      />

      <div className={cn("relative z-10 w-full rounded-2xl bg-white shadow-2xl", maxWidthClassName)}>
        <div className="border-b border-gray-100 px-6 pb-5 pt-6">
          <div className="flex items-start justify-between gap-4">
            <div>
              <h2 className="text-base font-semibold text-gray-800">{title}</h2>
              <p className="mt-0.5 text-xs text-[rgba(0,0,0,0.4)]">{description}</p>
            </div>
            <button
              type="button"
              onClick={onClose}
              className="flex size-7 flex-none items-center justify-center rounded-lg text-gray-400 transition-colors hover:bg-gray-100 hover:text-gray-600"
            >
              <CloseIcon />
            </button>
          </div>
        </div>
        {children}
      </div>
    </div>
  )
}

export function AdminMetricCard({
  title,
  value,
  icon,
  accentClassName,
}: {
  title: string
  value: string
  icon: ReactNode
  accentClassName: string
}) {
  return (
    <AdminSurfaceCard className="px-5 py-4">
      <div className="flex items-start justify-between gap-4">
        <div>
          <p className="text-xs font-medium text-gray-500">{title}</p>
          <p className="mt-1 text-lg font-semibold text-gray-800">{value}</p>
        </div>
        <div className={cn("flex size-10 items-center justify-center rounded-xl", accentClassName)}>{icon}</div>
      </div>
    </AdminSurfaceCard>
  )
}
