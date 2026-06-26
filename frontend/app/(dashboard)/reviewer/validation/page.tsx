"use client"

import { useEffect, useState } from "react"
import { DocumentValidator } from "@/components/reviewer/DocumentValidator"
import { ReviewerPageHeader, ReviewerSurfaceCard } from "@/components/reviewer/shared"
import { getActiveAssignments } from "@/lib/api/reviewer-assignments"
import { CalendarIcon, Loader2Icon } from "@/components/icons/public-icons"

export default function ReviewerValidationPage() {
  const [status, setStatus] = useState<"loading" | "allowed" | "blocked">("loading")

  useEffect(() => {
    getActiveAssignments().then(({ data }) => {
      setStatus(data && data.length > 0 ? "allowed" : "blocked")
    })
  }, [])

  return (
    <div className="px-8 py-8">
      <ReviewerPageHeader
        title="Validasi Dokumen"
        description="Validasi format dokumen DOCX proposal PKM terhadap aturan yang berlaku pada periode aktif"
      />

      {status === "loading" && (
        <div className="flex items-center justify-center py-16 gap-3">
          <Loader2Icon className="size-5 animate-spin text-muted-foreground" />
          <span className="text-muted-foreground text-sm">Memeriksa penugasan...</span>
        </div>
      )}

      {status === "blocked" && (
        <ReviewerSurfaceCard className="mt-6">
          <div className="px-6 py-12 text-center">
            <CalendarIcon className="size-10 mx-auto text-muted-foreground/40 mb-4" />
            <p className="text-sm font-semibold text-gray-700">Tidak ada penugasan aktif</p>
            <p className="mt-2 text-sm text-muted-foreground max-w-sm mx-auto">
              Fitur validasi dokumen hanya tersedia saat kamu memiliki penugasan pada periode review yang sedang berjalan.
            </p>
          </div>
        </ReviewerSurfaceCard>
      )}

      {status === "allowed" && <DocumentValidator />}
    </div>
  )
}
