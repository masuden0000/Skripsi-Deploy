"use client"

import { useEffect, useState } from "react"
import { ReviewerSurfaceCard } from "./shared"
import { Loader2Icon, CalendarIcon, UserIcon } from "@/components/icons/public-icons"
import { getActiveAssignments, type Assignment } from "@/lib/api/reviewer-assignments"

function formatDate(dateStr: string): string {
  const date = new Date(dateStr)
  return date.toLocaleDateString("id-ID", {
    day: "numeric",
    month: "long",
    year: "numeric",
  })
}

interface ActivePeriodBannerProps {
  className?: string
}

interface PeriodInfo {
  id: string
  nama: string
  tanggalMulai: string
  tanggalSelesai: string
}

interface EnrichedAssignment extends Assignment {
  periodInfo?: PeriodInfo
}

export function ActivePeriodBanner({ className }: ActivePeriodBannerProps) {
  const [assignments, setAssignments] = useState<EnrichedAssignment[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    async function fetchAssignments() {
      const result = await getActiveAssignments()
      if (result.error) {
        setError(result.error)
      } else {
        setAssignments(result.data || [])
      }
      setLoading(false)
    }

    fetchAssignments()
  }, [])

  if (loading) {
    return (
      <ReviewerSurfaceCard className={className}>
        <div className="flex items-center gap-3 p-4">
          <div className="flex size-10 items-center justify-center rounded-full bg-muted">
            <Loader2Icon className="size-5 animate-spin text-muted-foreground" />
          </div>
          <div className="space-y-1">
            <div className="h-4 w-32 animate-pulse rounded bg-muted" />
            <div className="h-3 w-48 animate-pulse rounded bg-muted" />
          </div>
        </div>
      </ReviewerSurfaceCard>
    )
  }

  if (error) {
    return (
      <ReviewerSurfaceCard className={className}>
        <div className="flex items-center gap-3 p-4">
          <div className="flex size-10 items-center justify-center rounded-full bg-muted">
            <CalendarIcon className="text-muted-foreground" />
          </div>
          <div>
            <p className="text-sm font-medium text-destructive">Gagal memuat data</p>
            <p className="text-xs text-muted-foreground">{error}</p>
          </div>
        </div>
      </ReviewerSurfaceCard>
    )
  }

  if (assignments.length === 0) {
    return (
      <ReviewerSurfaceCard className={className}>
        <div className="flex items-center gap-3 p-4">
          <div className="flex size-10 items-center justify-center rounded-full bg-muted">
            <CalendarIcon className="text-muted-foreground" />
          </div>
          <div>
            <p className="text-sm font-medium text-muted-foreground">
              Tidak ada penugasan aktif
            </p>
            <p className="text-xs text-muted-foreground">
              Anda belum ditugaskan ke periode aktif manapun
            </p>
          </div>
        </div>
      </ReviewerSurfaceCard>
    )
  }

  // Show first active assignment as the main period
  const activeAssignment = assignments[0]

  // The period info might be embedded differently based on backend response
  const periodInfo: PeriodInfo = {
    id: activeAssignment.periodId,
    nama: activeAssignment.period,
    tanggalMulai: "", // Backend doesn't provide this detail in the current schema
    tanggalSelesai: "",
  }

  return (
    <Card className={className}>
      <CardContent className="flex flex-col gap-4 p-4 sm:flex-row sm:items-center sm:gap-6">
        <div className="flex size-12 shrink-0 items-center justify-center rounded-full bg-primary/10">
          <CalendarIcon className="size-5 text-primary" />
        </div>

        <div className="flex-1 space-y-1">
          <h2 className="text-lg font-semibold tracking-tight">{periodInfo.nama}</h2>
          {periodInfo.tanggalMulai && (
            <p className="text-sm text-muted-foreground">
              {formatDate(periodInfo.tanggalMulai)}
              {periodInfo.tanggalSelesai && ` — ${formatDate(periodInfo.tanggalSelesai)}`}
            </p>
          )}
        </div>

        <div className="shrink-0 flex items-center gap-2">
          <span className="inline-flex items-center rounded-full bg-primary/10 px-3 py-1 text-xs font-medium text-primary">
            Penugasan Aktif
          </span>
          {assignments.length > 1 && (
            <span className="inline-flex items-center gap-1 rounded-full bg-muted px-2 py-1 text-xs text-muted-foreground">
              <UserIcon className="size-3" />
              +{assignments.length - 1} lainnya
            </span>
          )}
        </div>
      </CardContent>
    </Card>
  )
}