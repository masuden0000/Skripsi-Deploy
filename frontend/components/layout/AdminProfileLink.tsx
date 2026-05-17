"use client"

import Link from "next/link"
import { usePathname } from "next/navigation"

export function AdminProfileLink() {
  const pathname = usePathname()
  const isActive = pathname.startsWith("/admin/profil")

  return (
    <Link
      href="/admin/profil"
      className={[
        "flex items-center gap-2.5 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors w-full",
        isActive
          ? "bg-pkm-50 text-pkm-700 ring-1 ring-pkm-100"
          : "text-gray-500 hover:bg-gray-50 hover:text-gray-700",
      ].join(" ")}
    >
      <svg
        className="size-4 flex-none"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth={2}
      >
        <path strokeLinecap="round" strokeLinejoin="round" d="M20 21a8 8 0 0 0-16 0" />
        <circle cx="12" cy="7" r="4" />
      </svg>
      Profil
      {isActive && <span className="ml-auto size-1.5 rounded-full bg-pkm-600" />}
    </Link>
  )
}
