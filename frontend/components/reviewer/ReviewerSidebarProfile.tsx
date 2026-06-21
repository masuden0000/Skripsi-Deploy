"use client"

import { useEffect, useState } from "react"

type ReviewerProfile = {
  nama: string
  fakultas: string
  fakultasKode: string
}

export function ReviewerSidebarProfile() {
  const [profile, setProfile] = useState<ReviewerProfile | null>(null)

  useEffect(() => {
    fetch("/api/reviewer-profile", { cache: "no-store" })
      .then((r) => r.json())
      .then((payload: { data?: ReviewerProfile }) => {
        if (payload?.data) setProfile(payload.data)
      })
      .catch(() => null)
  }, [])

  if (!profile) {
    return <p className="text-xs" style={{ color: "rgba(0,0,0,0.3)" }}>Panel Reviewer</p>
  }

  return (
    <div className="min-w-0">
      <p className="truncate text-xs font-semibold leading-tight text-pkm-900">{profile.nama}</p>
      <p className="mt-0.5 truncate text-xs leading-tight" style={{ color: "rgba(0,153,102,0.65)" }}>
        {profile.fakultas}
      </p>
    </div>
  )
}
