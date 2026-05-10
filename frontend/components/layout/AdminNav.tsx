"use client"

import Link from "next/link"
import { usePathname } from "next/navigation"

const navItems = [
  {
    label: "Kelola Fakultas",
    href: "/admin/fakultas",
    exact: false,
    icon: (
      <svg className="size-4 flex-none" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2}>
        <path strokeLinecap="round" strokeLinejoin="round" d="M4 20h16" />
        <path strokeLinecap="round" strokeLinejoin="round" d="M6 20V8l6-4 6 4v12" />
        <path strokeLinecap="round" strokeLinejoin="round" d="M9 12h.01M15 12h.01M9 16h.01M15 16h.01" />
      </svg>
    ),
  },
  {
    label: "Kelola Reviewer",
    href: "/admin/reviewer",
    exact: false,
    icon: (
      <svg className="size-4 flex-none" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2}>
        <path strokeLinecap="round" strokeLinejoin="round" d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2" />
        <circle cx="9" cy="7" r="4" />
        <path strokeLinecap="round" strokeLinejoin="round" d="M22 21v-2a4 4 0 0 0-3-3.87" />
        <path strokeLinecap="round" strokeLinejoin="round" d="M16 3.13a4 4 0 0 1 0 7.75" />
      </svg>
    ),
  },
  {
    label: "Periode Review",
    href: "/admin/periode",
    exact: false,
    icon: (
      <svg className="size-4 flex-none" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2}>
        <rect x="3" y="4" width="18" height="18" rx="2" />
        <path strokeLinecap="round" d="M16 2v4M8 2v4M3 10h18" />
      </svg>
    ),
  },
  {
    label: "Kelola Tugas",
    href: "/admin/tugas",
    exact: false,
    icon: (
      <svg className="size-4 flex-none" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2}>
        <path strokeLinecap="round" strokeLinejoin="round" d="M13 10V3L4 14h7v7l9-11h-7Z" />
      </svg>
    ),
  },
  {
    label: "Buat Dokumen Proposal",
    href: "/admin/proposal",
    exact: false,
    icon: (
      <svg className="size-4 flex-none" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2}>
        <path strokeLinecap="round" strokeLinejoin="round" d="M14.5 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7.5L14.5 2z" />
        <polyline points="14 2 14 8 20 8" />
        <line x1="16" x2="8" y1="13" y2="13" />
        <line x1="16" x2="8" y1="17" y2="17" />
      </svg>
    ),
  },
]

export default function AdminNav() {
  const pathname = usePathname()

  return (
    <nav className="flex-1 px-3 py-4 space-y-0.5">
      <p className="px-3 pb-2 text-[10px] font-semibold uppercase tracking-widest" style={{ color: "rgba(0,0,0,0.3)" }}>
        Menu
      </p>
      {navItems.map((item) => {
        const isActive = item.exact
          ? pathname === item.href
          : pathname.startsWith(item.href)

        return (
          <Link
            key={item.href}
            href={item.href}
            className={[
              "flex items-center gap-2.5 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors",
              isActive
                ? "bg-pkm-50 text-pkm-700 ring-1 ring-pkm-100"
                : "text-gray-500 hover:bg-gray-50 hover:text-gray-700",
            ].join(" ")}
          >
            {item.icon}
            {item.label}
            {isActive && (
              <span className="ml-auto size-1.5 rounded-full bg-pkm-600" />
            )}
          </Link>
        )
      })}
    </nav>
  )
}
