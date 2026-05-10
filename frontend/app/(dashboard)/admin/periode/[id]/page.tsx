"use client"

import { useCallback, useEffect, useMemo, useState } from "react"
import { useParams, useRouter } from "next/navigation"
import {
  AdminPageHeader,
  AdminSurfaceCard,
} from "@/components/admin/shared"
import { Button } from "@/components/ui/button"
import { ArrowLeftIcon, LinkIcon } from "@/components/icons/public-icons"
import {
  formatTanggal,
  formatTanggalDanWaktu,
  isOngoingReviewPeriod,
  type ReviewPeriod,
} from "@/lib/review-periods"

type Assignment = {
  id: string
  periodId: string
  reviewerId: string
  proposalLink: string
  assessmentLink: string
  isCompleted: boolean
  reviewer: string
  reviewerEmail: string
}

type ApiResponse = {
  data?: ReviewPeriod | Assignment[] | Array<{ id: string; nama: string; email?: string }>
  error?: string
}

type Reviewer = {
  id: string
  nama: string
  email: string
  fakultas: string
}

async function readApiResponse(response: Response) {
  const text = await response.text()
  if (!text) return {}
  try {
    return JSON.parse(text) as ApiResponse
  } catch {
    return { error: "Respons server tidak valid." }
  }
}

function InfoBadge({
  label,
  children,
}: {
  label: string
  children: React.ReactNode
}) {
  return (
    <div className="rounded-xl border border-gray-100 bg-gray-50/60 px-4 py-3">
      <p className="text-xs font-medium uppercase tracking-wide text-gray-500">{label}</p>
      <div className="mt-1">{children}</div>
    </div>
  )
}

function StatCard({
  title,
  value,
  highlight,
}: {
  title: string
  value: string | number
  highlight?: boolean
}) {
  return (
    <div
      className={`rounded-xl border px-4 py-3 ${
        highlight
          ? "border-pkm-100 bg-pkm-50/60"
          : "border-gray-100 bg-white"
      }`}
    >
      <p className="text-xs font-medium uppercase tracking-wide text-gray-500">{title}</p>
      <p className={`mt-1 text-lg font-semibold ${highlight ? "text-pkm-700" : "text-gray-800"}`}>
        {value}
      </p>
    </div>
  )
}

function StatCardWithBadge({
  title,
  badge,
  value,
  highlight,
}: {
  title: string
  badge: React.ReactNode
  value?: string | number
  highlight?: boolean
}) {
  return (
    <div
      className={`rounded-xl border px-4 py-3 ${
        highlight
          ? "border-pkm-100 bg-pkm-50/60"
          : "border-gray-100 bg-white"
      }`}
    >
      <p className="text-xs font-medium uppercase tracking-wide text-gray-500">{title}</p>
      <div className="mt-1">{badge}</div>
    </div>
  )
}

export default function ReviewPeriodDetailPage() {
  const params = useParams<{ id: string }>()
  const router = useRouter()
  const [periode, setPeriode] = useState<ReviewPeriod | null>(null)
  const [assignments, setAssignments] = useState<Assignment[]>([])
  const [reviewers, setReviewers] = useState<Reviewer[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [errorMessage, setErrorMessage] = useState<string | null>(null)
  const [isNotFound, setIsNotFound] = useState(false)

  const reviewPeriodId = Array.isArray(params.id) ? params.id[0] : params.id

  const completedCount = useMemo(
    () => assignments.filter((a) => a.isCompleted).length,
    [assignments]
  )

  const loadData = useCallback(async () => {
    if (!reviewPeriodId) {
      setIsLoading(false)
      setIsNotFound(true)
      return
    }

    setIsLoading(true)
    setErrorMessage(null)
    setIsNotFound(false)

    try {
      const [periodRes, assignmentRes, reviewerRes] = await Promise.all([
        fetch(`/api/review-periods/${reviewPeriodId}`, { method: "GET", cache: "no-store" }),
        fetch("/api/assignments", { method: "GET", cache: "no-store" }),
        fetch("/api/reviewers", { method: "GET", cache: "no-store" }),
      ])

      const periodPayload = await readApiResponse(periodRes)
      const assignmentPayload = await readApiResponse(assignmentRes)
      const reviewerPayload = await readApiResponse(reviewerRes)

      if (periodRes.status === 404) {
        setIsNotFound(true)
        return
      }

      if (!periodRes.ok) {
        setErrorMessage((periodPayload as ApiResponse).error ?? "Gagal memuat detail periode review.")
        return
      }

      setPeriode((periodPayload as ApiResponse).data as ReviewPeriod)

      const allAssignments = Array.isArray((assignmentPayload as ApiResponse).data)
        ? ((assignmentPayload as ApiResponse).data as Assignment[])
        : []
      const filteredAssignments = allAssignments.filter((a) => a.periodId === reviewPeriodId)
      setAssignments(filteredAssignments)

      const allReviewers = Array.isArray((reviewerPayload as ApiResponse).data)
        ? ((reviewerPayload as ApiResponse).data as Array<{ id: string; nama: string; email?: string; fakultas?: string }>)
        : []
      setReviewers(
        allReviewers.map((r) => ({
          id: r.id,
          nama: r.nama ?? r.email ?? "",
          email: r.email ?? "",
          fakultas: (r as { fakultas?: string }).fakultas ?? "",
        }))
      )
    } catch {
      setErrorMessage("Tidak bisa terhubung ke server.")
    } finally {
      setIsLoading(false)
    }
  }, [reviewPeriodId])

  useEffect(() => {
    const timeoutId = window.setTimeout(() => void loadData(), 0)
    return () => window.clearTimeout(timeoutId)
  }, [loadData])

  function getReviewerFaculty(reviewerId: string): string {
    const reviewer = reviewers.find((r) => r.id === reviewerId)
    return reviewer?.fakultas ?? "—"
  }

  function getReviewerName(reviewerId: string): string {
    const assignment = assignments.find((a) => a.reviewerId === reviewerId)
    return assignment?.reviewer ?? "—"
  }

  const uniqueReviewerIds = useMemo(() => {
    return [...new Set(assignments.map((a) => a.reviewerId))]
  }, [assignments])

  return (
    <div className="px-8 py-8">
      <div className="mb-6">
        <Button
          type="button"
          variant="ghost"
          onClick={() => router.push("/admin/periode")}
          className="flex items-center gap-2 text-gray-600 hover:text-gray-800 px-0 hover:bg-transparent"
        >
          <ArrowLeftIcon className="size-4" />
          Kembali
        </Button>
      </div>

      <AdminPageHeader
        title={periode?.nama ?? "Detail Periode Review"}
        description="Detail dan daftar tugas periode review PKM"
      />

      {isLoading ? (
        <div className="rounded-2xl border border-gray-100 bg-white px-6 py-10 text-center text-sm text-gray-500 shadow-sm">
          Memuat detail periode review...
        </div>
      ) : null}

      {!isLoading && errorMessage ? (
        <div className="mb-4 rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
          <div className="flex items-center justify-between gap-3">
            <span>{errorMessage}</span>
            <Button type="button" variant="outline" size="sm" onClick={() => void loadData()}>
              Coba Lagi
            </Button>
          </div>
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
        <>
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-5">
            <StatCard title="Tanggal Mulai" value={formatTanggal(periode.tanggalMulai)} />
            <StatCard title="Tanggal Selesai" value={formatTanggal(periode.tanggalSelesai)} />
            <StatCard
              title="Durasi"
              value={`${Math.ceil((new Date(periode.tanggalSelesai).getTime() - new Date(periode.tanggalMulai).getTime()) / (1000 * 60 * 60 * 24))} hari`}
            />
              <StatCard title="Selesai" value={completedCount} highlight={completedCount > 0} />
            <StatCardWithBadge
              title="Status"
              highlight={isOngoingReviewPeriod(periode)}
              badge={
                <span className={`inline-flex items-center gap-1.5 text-sm font-medium ${isOngoingReviewPeriod(periode) ? "text-pkm-700" : "text-gray-500"}`}>
                  <span className={`size-2 rounded-full ${isOngoingReviewPeriod(periode) ? "bg-pkm-600" : "bg-gray-400"}`} />
                  {isOngoingReviewPeriod(periode) ? "Berlangsung" : "Selesai"}
                </span>
              }
            />
          </div>

          <AdminSurfaceCard className="mt-4">
            <div className="border-b border-gray-100 px-5 py-4">
              <h2 className="text-sm font-semibold text-gray-700">Daftar Tugas</h2>
              <p className="mt-0.5 text-xs text-[rgba(0,0,0,0.4)]">
                Penugasan reviewer pada periode ini
              </p>
            </div>

            <div className="overflow-x-auto px-5 py-4">
              {assignments.length === 0 ? (
                <div className="py-8 text-center text-sm text-gray-500">
                  Belum ada tugas pada periode ini.
                </div>
              ) : (
                <table className="w-full min-w-[800px] border-separate border-spacing-0">
                  <thead>
                    <tr className="text-left">
                      <th className="border-b border-gray-100 pb-3 pr-4 text-xs font-semibold text-gray-700">
                        No
                      </th>
                      <th className="border-b border-gray-100 pb-3 pr-4 text-xs font-semibold text-gray-700">
                        Nama Reviewer
                      </th>
                      <th className="border-b border-gray-100 pb-3 pr-4 text-xs font-semibold text-gray-700">
                        Asal Fakultas
                      </th>
                      <th className="border-b border-gray-100 pb-3 pr-4 text-xs font-semibold text-gray-700">
                        Link Proposal
                      </th>
                      <th className="border-b border-gray-100 pb-3 pr-4 text-xs font-semibold text-gray-700">
                        Link Penilaian
                      </th>
                      <th className="border-b border-gray-100 pb-3 text-right text-xs font-semibold text-gray-700">
                        Status
                      </th>
                    </tr>
                  </thead>
                  <tbody>
                    {assignments.map((assignment, index) => (
                      <tr key={assignment.id}>
                        <td className="border-b border-gray-50 py-4 pr-4 text-sm text-gray-500">
                          {index + 1}
                        </td>
                        <td className="border-b border-gray-50 py-4 pr-4 text-sm font-medium text-gray-800">
                          {getReviewerName(assignment.reviewerId)}
                        </td>
                        <td className="border-b border-gray-50 py-4 pr-4">
                          {getReviewerFaculty(assignment.reviewerId) && getReviewerFaculty(assignment.reviewerId) !== "—" ? (
                            <span className="inline-flex rounded-full border border-pkm-200 bg-pkm-50 px-3 py-1 text-xs font-medium text-pkm-700">
                              {getReviewerFaculty(assignment.reviewerId)}
                            </span>
                          ) : (
                            <span className="text-sm text-gray-400">—</span>
                          )}
                        </td>
                        <td className="border-b border-gray-50 py-4 pr-4">
                          {assignment.proposalLink ? (
                            <a
                              href={assignment.proposalLink}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="inline-flex items-center gap-1 text-sm text-blue-600 hover:text-blue-800 hover:underline"
                            >
                              Buka Link
                              <LinkIcon className="h-3 w-3" />
                            </a>
                          ) : (
                            <span className="text-sm text-gray-400">—</span>
                          )}
                        </td>
                        <td className="border-b border-gray-50 py-4 pr-4">
                          {assignment.assessmentLink ? (
                            <a
                              href={assignment.assessmentLink}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="inline-flex items-center gap-1 text-sm text-blue-600 hover:text-blue-800 hover:underline"
                            >
                              Buka Link
                              <LinkIcon className="h-3 w-3" />
                            </a>
                          ) : (
                            <span className="text-sm text-gray-400">—</span>
                          )}
                        </td>
                        <td className="border-b border-gray-50 py-4 text-right">
                          <span
                            className={[
                              "inline-flex rounded-full px-3 py-1 text-xs font-medium",
                              assignment.isCompleted
                                ? "bg-green-100 text-green-700"
                                : "bg-gray-100 text-gray-500",
                            ].join(" ")}
                          >
                            {assignment.isCompleted ? "Selesai" : "Belum Selesai"}
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </div>
          </AdminSurfaceCard>

          {periode.updatedAt ? (
            <p className="mt-4 text-center text-xs text-[rgba(0,0,0,0.35)]">
              Terakhir diperbarui: {formatTanggalDanWaktu(periode.updatedAt)}
            </p>
          ) : null}
        </>
      ) : null}
    </div>
  )
}