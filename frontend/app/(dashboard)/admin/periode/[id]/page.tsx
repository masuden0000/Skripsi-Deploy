"use client"

import { useCallback, useEffect, useState } from "react"
import { useParams, useRouter } from "next/navigation"
import { Button } from "@/components/ui/button"
import {
  formatTanggal,
  formatTanggalDanWaktu,
  hasReviewPeriodBeenUpdated,
  isOngoingReviewPeriod,
  type ReviewPeriod,
} from "@/lib/review-periods"

type ReviewPeriodApiResponse = {
  data?: ReviewPeriod
  error?: string
}

async function readReviewPeriodResponse(response: Response) {
  const text = await response.text()

  if (!text) {
    return {}
  }

  try {
    return JSON.parse(text) as ReviewPeriodApiResponse
  } catch {
    return { error: "Respons server tidak valid." }
  }
}

export default function ReviewPeriodDetailPage() {
  const params = useParams<{ id: string }>()
  const router = useRouter()
  const [periode, setPeriode] = useState<ReviewPeriod | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [errorMessage, setErrorMessage] = useState<string | null>(null)
  const [isNotFound, setIsNotFound] = useState(false)

  const reviewPeriodId = Array.isArray(params.id) ? params.id[0] : params.id

  const loadReviewPeriod = useCallback(async () => {
    if (!reviewPeriodId) {
      setIsLoading(false)
      setIsNotFound(true)
      setPeriode(null)
      return
    }

    setIsLoading(true)
    setErrorMessage(null)
    setIsNotFound(false)

    try {
      const response = await fetch(`/api/review-periods/${reviewPeriodId}`, {
        method: "GET",
        cache: "no-store",
      })
      const payload = await readReviewPeriodResponse(response)

      if (response.status === 404) {
        setIsNotFound(true)
        setPeriode(null)
        return
      }

      if (!response.ok) {
        setErrorMessage(payload.error ?? "Gagal memuat detail periode review.")
        setPeriode(null)
        return
      }

      setPeriode(payload.data ?? null)
    } catch {
      setErrorMessage("Tidak bisa terhubung ke server.")
      setPeriode(null)
    } finally {
      setIsLoading(false)
    }
  }, [reviewPeriodId])

  useEffect(() => {
    const timeoutId = window.setTimeout(() => {
      void loadReviewPeriod()
    }, 0)

    return () => window.clearTimeout(timeoutId)
  }, [loadReviewPeriod])

  return (
    <div className="px-8 py-8 max-w-2xl">
      <div className="mb-6 flex items-center justify-between gap-4">
        <div>
          <p className="text-xs font-medium uppercase tracking-[0.2em]" style={{ color: "rgba(0,0,0,0.35)" }}>
            Detail Periode
          </p>
          <h1 className="mt-1 text-xl font-semibold text-gray-800">Periode Review PKM</h1>
        </div>
        <Button type="button" variant="outline" onClick={() => router.push("/admin/periode")}>
          Kembali
        </Button>
      </div>

      {isLoading ? (
        <div className="rounded-2xl border border-gray-100 bg-white px-6 py-10 text-center text-sm text-gray-500 shadow-sm">
          Memuat detail periode review...
        </div>
      ) : null}

      {!isLoading && errorMessage ? (
        <div className="rounded-2xl border border-red-200 bg-red-50 px-6 py-5 text-sm text-red-700">
          <p>{errorMessage}</p>
          <Button type="button" variant="outline" size="sm" className="mt-3" onClick={() => void loadReviewPeriod()}>
            Coba Lagi
          </Button>
        </div>
      ) : null}

      {!isLoading && isNotFound ? (
        <div className="rounded-2xl border border-gray-100 bg-white px-6 py-10 text-center shadow-sm">
          <h2 className="text-base font-semibold text-gray-800">Periode tidak ditemukan</h2>
          <p className="mt-1 text-sm text-gray-500">
            Data yang kamu cari tidak ada atau id periode tidak valid.
          </p>
        </div>
      ) : null}

      {!isLoading && !errorMessage && !isNotFound && periode ? (
        <div className="rounded-2xl border border-gray-100 bg-white shadow-sm overflow-hidden">
          <div className="border-b border-gray-100 px-6 py-5">
            <h2 className="text-lg font-semibold text-gray-800">{periode.nama}</h2>
            <p className="mt-1 text-sm text-gray-500">
              Rentang periode review yang sedang dipakai pada dashboard admin.
            </p>
          </div>

          <div className="space-y-4 px-6 py-5">
            <div className="grid gap-4 sm:grid-cols-2">
              <div className="rounded-xl border border-gray-100 bg-gray-50/60 px-4 py-3">
                <p className="text-xs font-medium uppercase tracking-wide text-gray-500">Tanggal Mulai</p>
                <p className="mt-1 text-sm font-semibold text-gray-800">{formatTanggal(periode.tanggalMulai)}</p>
              </div>
              <div className="rounded-xl border border-gray-100 bg-gray-50/60 px-4 py-3">
                <p className="text-xs font-medium uppercase tracking-wide text-gray-500">Tanggal Selesai</p>
                <p className="mt-1 text-sm font-semibold text-gray-800">{formatTanggal(periode.tanggalSelesai)}</p>
              </div>
            </div>

            <div className="rounded-xl border border-gray-100 bg-white px-4 py-4">
              <p className="text-xs font-medium uppercase tracking-wide text-gray-500">Status</p>
              <div className="mt-2">
                {isOngoingReviewPeriod(periode) ? (
                  <span className="inline-flex items-center gap-1.5 text-xs font-medium px-2.5 py-1 rounded-full bg-pkm-100 text-pkm-700">
                    <span className="size-1.5 rounded-full bg-pkm-600" />
                    Berlangsung
                  </span>
                ) : (
                  <span className="inline-flex items-center gap-1.5 text-xs font-medium px-2.5 py-1 rounded-full bg-gray-100 text-gray-500">
                    <span className="size-1.5 rounded-full bg-gray-400" />
                    Selesai
                  </span>
                )}
              </div>
            </div>

            {hasReviewPeriodBeenUpdated(periode) ? (
              <div className="rounded-xl border border-pkm-100 bg-pkm-50/60 px-4 py-4">
                <p className="text-xs font-medium uppercase tracking-wide text-pkm-700">Terakhir Diperbarui</p>
                <p className="mt-1 text-sm font-semibold text-pkm-800">
                  {formatTanggalDanWaktu(periode.updatedAt)}
                </p>
              </div>
            ) : null}
          </div>
        </div>
      ) : null}
    </div>
  )
}
