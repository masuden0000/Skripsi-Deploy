"use client"

import { useCallback, useEffect, useMemo, useState } from "react"
import {
  AdminMetricCard,
  AdminModalShell,
  AdminPageHeader,
  AdminSurfaceCard,
} from "@/components/admin/shared"
import { EditIcon, LinkIcon, PlusIcon, TrashIcon } from "@/components/icons/public-icons"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"

type ReviewStatus = "menunggu_validasi" | "selesai" | null

type Assignment = {
  id: string
  periodId: string
  reviewerId: string
  proposalLink: string
  assessmentLink: string
  isCompleted: boolean
  reviewStatus: ReviewStatus
  createdAt: string
  reviewer: string
  period: string
  fakultas: string
  fakultasKode: string
}

type Reviewer = {
  id: string
  nama: string
  email: string
  fakultas: string
  fakultasKode: string
}

type Period = {
  id: string
  nama: string
  tanggalMulai: string
  tanggalSelesai: string
}

const ITEMS_PER_PAGE = 10

function buildPageNumbers(current: number, total: number): Array<number | "…"> {
  if (total <= 7) return Array.from({ length: total }, (_, i) => i + 1)
  if (current <= 4) return [1, 2, 3, 4, 5, "…", total]
  if (current >= total - 3) return [1, "…", total - 4, total - 3, total - 2, total - 1, total]
  return [1, "…", current - 1, current, current + 1, "…", total]
}

function isPeriodActive(period: Period): boolean {
  const now = new Date()
  const mulai = new Date(period.tanggalMulai)
  const selesai = new Date(period.tanggalSelesai)
  return now >= mulai && now <= selesai
}

type AssignmentFormData = {
  periodId: string
  reviewerId: string
  proposalLink: string
  assessmentLink: string
}

type ApiResponse = {
  data?: Assignment | Assignment[]
  error?: string
  message?: string
}

type DropdownResponse = {
  data?: Array<{ id: string; nama: string; email?: string; fakultas?: string; fakultasKode?: string }>
  error?: string
}

async function readApiResponse(response: Response) {
  const text = await response.text()
  if (!text) return {}
  try {
    return JSON.parse(text) as ApiResponse | DropdownResponse
  } catch {
    return { error: "Respons server tidak valid." }
  }
}

function AssignmentModal({
  assignment,
  assignments,
  periods,
  reviewers,
  isSubmitting,
  errorMessage,
  onClose,
  onSave,
}: {
  assignment: Assignment | null
  assignments: Assignment[]
  periods: Period[]
  reviewers: Reviewer[]
  isSubmitting: boolean
  errorMessage: string | null
  onClose: () => void
  onSave: (data: AssignmentFormData) => Promise<void>
}) {
  const [periodId, setPeriodId] = useState(assignment?.periodId ?? "")
  const [reviewerId, setReviewerId] = useState(assignment?.reviewerId ?? "")
  const [proposalLink, setProposalLink] = useState(assignment?.proposalLink ?? "")
  const [assessmentLink, setAssessmentLink] = useState(assignment?.assessmentLink ?? "")
  const [localError, setLocalError] = useState<string | null>(null)
  const isEditMode = Boolean(assignment)

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault()

    if (!periodId || !reviewerId) {
      setLocalError("Periode dan reviewer wajib dipilih.")
      return
    }

    if (!proposalLink.trim() && !assessmentLink.trim()) {
      setLocalError("Minimal satu link wajib diisi.")
      return
    }

    if (!isEditMode) {
      const sudahDitugaskanDiPeriode = assignments.some(
        (a) => a.reviewerId === reviewerId && a.periodId === periodId
      )
      if (sudahDitugaskanDiPeriode) {
        setLocalError("Reviewer ini sudah ditugaskan pada periode yang sama.")
        return
      }

      const masihAdaTugasBelumSelesai = assignments.some(
        (a) => a.reviewerId === reviewerId && a.reviewStatus !== "selesai"
      )
      if (masihAdaTugasBelumSelesai) {
        setLocalError("Reviewer ini masih memiliki tugas yang belum selesai dan belum bisa ditugaskan kembali.")
        return
      }
    }

    setLocalError(null)
    await onSave({
      periodId,
      reviewerId,
      proposalLink: proposalLink.trim(),
      assessmentLink: assessmentLink.trim(),
    })
  }

  return (
    <AdminModalShell
      title={isEditMode ? "Edit Tugas" : "Tambah Tugas"}
      description={
        isEditMode
          ? "Perbarui link proposal dan pengumpulan penilaian."
          : "Tambahkan penugasan reviewer ke periode review."
      }
      onClose={onClose}
      maxWidthClassName="max-w-lg"
    >
      <form onSubmit={handleSubmit} className="space-y-4 px-6 py-5">
        <div className="space-y-1.5">
          <Label className="text-xs font-medium text-gray-600">Periode Review</Label>
          <Select
            value={periodId || undefined}
            onValueChange={setPeriodId}
            disabled={isSubmitting || isEditMode}
          >
            <SelectTrigger>
              <SelectValue placeholder="Pilih periode review" />
            </SelectTrigger>
            <SelectContent>
              {periods.map((period) => (
                <SelectItem key={period.id} value={period.id}>
                  {period.nama}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        <div className="space-y-1.5">
          <Label className="text-xs font-medium text-gray-600">Reviewer</Label>
          <Select
            value={reviewerId || undefined}
            onValueChange={setReviewerId}
            disabled={isSubmitting || isEditMode}
          >
            <SelectTrigger>
              <SelectValue placeholder="Pilih reviewer" />
            </SelectTrigger>
            <SelectContent>
              {reviewers.map((reviewer) => (
                <SelectItem key={reviewer.id} value={reviewer.id}>
                  {reviewer.nama}{reviewer.fakultasKode ? ` (${reviewer.fakultasKode})` : ""}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        <div className="space-y-1.5">
          <Label htmlFor="proposal-link" className="text-xs font-medium text-gray-600">
            Link Proposal
          </Label>
          <Input
            id="proposal-link"
            type="url"
            value={proposalLink}
            onChange={(event) => setProposalLink(event.target.value)}
            placeholder="https://..."
            disabled={isSubmitting}
          />
        </div>

        <div className="space-y-1.5">
          <Label htmlFor="assessment-link" className="text-xs font-medium text-gray-600">
            Link Pengumpulan Penilaian
          </Label>
          <Input
            id="assessment-link"
            type="url"
            value={assessmentLink}
            onChange={(event) => setAssessmentLink(event.target.value)}
            placeholder="https://..."
            disabled={isSubmitting}
          />
        </div>

        {localError || errorMessage ? (
          <div className="rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-xs text-red-700">
            {localError || errorMessage}
          </div>
        ) : null}

        <div className="flex justify-end gap-2 pt-1">
          <Button type="button" variant="outline" onClick={onClose} disabled={isSubmitting}>
            Batal
          </Button>
          <Button type="submit" disabled={isSubmitting}>
            {isSubmitting ? "Menyimpan..." : isEditMode ? "Simpan Perubahan" : "Tambah Tugas"}
          </Button>
        </div>
      </form>
    </AdminModalShell>
  )
}

export default function AssignmentManagementPage() {
  const [assignments, setAssignments] = useState<Assignment[]>([])
  const [reviewers, setReviewers] = useState<Reviewer[]>([])
  const [periods, setPeriods] = useState<Period[]>([])
  const [activePeriods, setActivePeriods] = useState<Period[]>([])
  const [isModalOpen, setIsModalOpen] = useState(false)
  const [editingAssignment, setEditingAssignment] = useState<Assignment | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [loadError, setLoadError] = useState<string | null>(null)
  const [formError, setFormError] = useState<string | null>(null)
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [currentPage, setCurrentPage] = useState(1)
  const [statusSort, setStatusSort] = useState<"none" | "asc" | "desc">("none")

  const totalAssignments = assignments.length
  const completedCount = useMemo(
    () => assignments.filter((a) => a.reviewStatus === "selesai").length,
    [assignments]
  )
  const menungguValidasiCount = useMemo(
    () => assignments.filter((a) => a.reviewStatus === "menunggu_validasi").length,
    [assignments]
  )
  const pendingCount = useMemo(
    () => assignments.filter((a) => !a.reviewStatus).length,
    [assignments]
  )

  function statusOrder(s: ReviewStatus): number {
    if (s === "selesai") return 2
    if (s === "menunggu_validasi") return 1
    return 0
  }

  const sortedAssignments = useMemo(() => {
    if (statusSort === "none") return assignments
    return [...assignments].sort((a, b) => {
      const diff = statusOrder(a.reviewStatus) - statusOrder(b.reviewStatus)
      return statusSort === "asc" ? -diff : diff
    })
  }, [assignments, statusSort])

  const totalAssignmentPages = Math.ceil(sortedAssignments.length / ITEMS_PER_PAGE)

  const paginatedAssignments = useMemo(
    () => sortedAssignments.slice((currentPage - 1) * ITEMS_PER_PAGE, currentPage * ITEMS_PER_PAGE),
    [sortedAssignments, currentPage]
  )

  const loadDependencies = useCallback(async () => {
    setIsLoading(true)
    setLoadError(null)

    try {
      const [assignmentRes, reviewerRes, periodRes] = await Promise.all([
        fetch("/api/assignments", { method: "GET", cache: "no-store" }),
        fetch("/api/reviewers", { method: "GET", cache: "no-store" }),
        fetch("/api/review-periods", { method: "GET", cache: "no-store" }),
      ])

      const assignmentPayload = await readApiResponse(assignmentRes)
      const reviewerPayload = await readApiResponse(reviewerRes)
      const periodPayload = await readApiResponse(periodRes)

      if (!assignmentRes.ok) {
        setLoadError(
          (assignmentPayload as ApiResponse).error ?? "Gagal memuat data tugas."
        )
        return
      }

      setAssignments(
        Array.isArray((assignmentPayload as ApiResponse).data)
          ? ((assignmentPayload as ApiResponse).data as Assignment[])
          : []
      )

      const reviewerData = reviewerPayload as DropdownResponse
      if (Array.isArray(reviewerData.data)) {
        setReviewers(
          reviewerData.data.map((r) => ({
            id: r.id,
            nama: r.nama ?? r.email ?? "",
            email: r.email ?? "",
            fakultas: (r as { fakultas?: string }).fakultas ?? "",
            fakultasKode: (r as { fakultasKode?: string }).fakultasKode ?? "",
          }))
        )
      }

      const periodData = periodPayload as { data?: Array<{ id: string; nama: string; tanggalMulai: string; tanggalSelesai: string }> }
      if (Array.isArray(periodData.data)) {
        setPeriods(periodData.data)
        setActivePeriods(periodData.data.filter(isPeriodActive))
      }
    } catch {
      setLoadError("Tidak bisa terhubung ke server.")
      setAssignments([])
      setReviewers([])
      setPeriods([])
    } finally {
      setIsLoading(false)
    }
  }, [])

  useEffect(() => {
    const timeoutId = window.setTimeout(() => void loadDependencies(), 0)
    return () => window.clearTimeout(timeoutId)
  }, [loadDependencies])

  useEffect(() => {
    setCurrentPage(1)
  }, [statusSort])

  function handleOpenCreateModal() {
    setEditingAssignment(null)
    setFormError(null)
    setIsModalOpen(true)
  }

  function handleCloseModal() {
    setIsModalOpen(false)
    setEditingAssignment(null)
    setFormError(null)
  }

  function handleEditAssignment(assignment: Assignment) {
    setEditingAssignment(assignment)
    setFormError(null)
    setIsModalOpen(true)
  }

  async function handleDeleteAssignment(id: string) {
    if (!window.confirm("Apakah Anda yakin ingin menghapus tugas ini?")) return

    try {
      const response = await fetch(`/api/assignments/${id}`, { method: "DELETE" })
      const payload = await readApiResponse(response)

      if (!response.ok) {
        alert((payload as ApiResponse).error ?? "Gagal menghapus tugas.")
        return
      }

      await loadDependencies()
      alert((payload as ApiResponse).message ?? "Tugas berhasil dihapus.")
    } catch {
      alert("Tidak bisa terhubung ke server.")
    }
  }

  async function handleValidate(id: string, approved: boolean) {
    try {
      const response = await fetch(`/api/assignments/${id}/validate`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ approved }),
      })
      const payload = await readApiResponse(response)

      if (!response.ok) {
        alert((payload as ApiResponse).error ?? "Gagal memvalidasi tugas.")
        return
      }

      const updated = (payload as ApiResponse).data as Assignment | undefined
      if (updated) {
        setAssignments(prev =>
          prev.map(a => a.id === id ? { ...a, reviewStatus: updated.reviewStatus, isCompleted: updated.isCompleted } : a)
        )
      } else {
        await loadDependencies()
      }
    } catch {
      alert("Tidak bisa terhubung ke server.")
    }
  }

  async function handleSaveAssignment(data: AssignmentFormData) {
    setIsSubmitting(true)
    setFormError(null)

    try {
      const isEditMode = Boolean(editingAssignment)
      const url = isEditMode
        ? `/api/assignments/${editingAssignment!.id}`
        : "/api/assignments"
      const method = isEditMode ? "PUT" : "POST"

      const response = await fetch(url, {
        method,
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(data),
      })
      const payload = await readApiResponse(response)

      if (!response.ok) {
        setFormError((payload as ApiResponse).error ?? "Gagal menyimpan tugas.")
        return
      }

      await loadDependencies()
      handleCloseModal()
    } catch {
      setFormError("Tidak bisa terhubung ke server.")
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <>
      {isModalOpen ? (
        <AssignmentModal
          assignment={editingAssignment}
          assignments={assignments}
          periods={editingAssignment ? periods : activePeriods}
          reviewers={reviewers}
          isSubmitting={isSubmitting}
          errorMessage={formError}
          onClose={handleCloseModal}
          onSave={handleSaveAssignment}
        />
      ) : null}

      <div className="px-8 py-8">
        <AdminPageHeader
          title="Kelola Tugas"
          description="Tugaskan reviewer ke periode review PKM"
          action={
            <Button onClick={handleOpenCreateModal} className="flex items-center gap-2">
              <PlusIcon />
              Tambah Tugas
            </Button>
          }
        />

        {loadError ? (
          <div className="mb-4 rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
            <div className="flex items-center justify-between gap-3">
              <span>{loadError}</span>
              <Button
                type="button"
                variant="outline"
                size="sm"
                onClick={() => void loadDependencies()}
              >
                Coba Lagi
              </Button>
            </div>
          </div>
        ) : null}

        <div className="grid gap-4 md:grid-cols-4">
          <AdminMetricCard
            title="Total Tugas"
            value={String(totalAssignments)}
            accentClassName="bg-pkm-100 text-pkm-700"
            icon={<LinkIcon />}
          />
          <AdminMetricCard
            title="Selesai"
            value={String(completedCount)}
            accentClassName="bg-pkm-100 text-pkm-700"
            icon={<LinkIcon />}
          />
          <AdminMetricCard
            title="Belum Selesai"
            value={String(pendingCount)}
            accentClassName="bg-pkm-100 text-pkm-700"
            icon={<LinkIcon />}
          />
          <AdminMetricCard
            title="Menunggu Validasi"
            value={String(menungguValidasiCount)}
            accentClassName="bg-pkm-100 text-pkm-700"
            icon={<LinkIcon />}
          />
        </div>

        <AdminSurfaceCard className="mt-4">
          <div className="border-b border-gray-100 px-5 py-4">
            <h2 className="text-sm font-semibold text-gray-700">Daftar Tugas</h2>
            <p className="mt-0.5 text-xs text-[rgba(0,0,0,0.4)]">
              Pantau penugasan reviewer dan status review
            </p>
          </div>

          <div className="overflow-x-auto px-5 py-4">
            {isLoading ? (
              <div className="py-8 text-center text-sm text-gray-500">Memuat...</div>
            ) : assignments.length === 0 ? (
              <div className="py-8 text-center text-sm text-gray-500">Belum ada tugas.</div>
            ) : (
              <table className="w-full min-w-[1020px] border-separate border-spacing-0">
                <thead>
                  <tr className="text-left">
                    <th className="border-b border-gray-100 pb-3 pr-4 text-xs font-semibold text-gray-700">
                      No
                    </th>
                    <th className="border-b border-gray-100 pb-3 pr-4 text-xs font-semibold text-gray-700">
                      Reviewer
                    </th>
                    <th className="border-b border-gray-100 pb-3 pr-4 text-xs font-semibold text-gray-700">
                      Fakultas
                    </th>
                    <th className="border-b border-gray-100 pb-3 pr-4 text-xs font-semibold text-gray-700">
                      Link Proposal
                    </th>
                    <th className="border-b border-gray-100 pb-3 pr-4 text-xs font-semibold text-gray-700">
                      Link Penilaian
                    </th>
                    <th className="border-b border-gray-100 pb-3 pr-4 text-xs font-semibold text-gray-700">
                      <button
                        type="button"
                        onClick={() => setStatusSort(s => s === "none" ? "asc" : s === "asc" ? "desc" : "none")}
                        className="flex items-center gap-1 hover:text-gray-900"
                      >
                        Status
                        <span className="text-gray-400">{statusSort === "asc" ? "↑" : statusSort === "desc" ? "↓" : "↕"}</span>
                      </button>
                    </th>
                    <th className="border-b border-gray-100 pb-3 pr-4 text-xs font-semibold text-gray-700">
                      Validasi
                    </th>
                    <th className="border-b border-gray-100 pb-3 text-right text-xs font-semibold text-gray-700">
                      Aksi
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {paginatedAssignments.map((assignment, index) => (
                    <tr key={assignment.id}>
                      <td className="border-b border-gray-50 py-4 pr-4 text-sm text-gray-500">
                        {(currentPage - 1) * ITEMS_PER_PAGE + index + 1}
                      </td>
                      <td className="border-b border-gray-50 py-4 pr-4 text-sm font-medium text-gray-800">
                        {assignment.reviewer || "—"}
                      </td>
                      <td className="border-b border-gray-50 py-4 pr-4">
                        {assignment.fakultasKode ? (
                          <span className="inline-flex rounded-full border border-pkm-200 bg-pkm-50 px-3 py-1 text-xs font-medium text-pkm-700">
                            {assignment.fakultasKode}
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
                      <td className="border-b border-gray-50 py-4 pr-4">
                        <span
                          className={[
                            "inline-flex rounded-full px-3 py-1 text-xs font-medium",
                            assignment.reviewStatus === "selesai"
                              ? "bg-green-100 text-green-700"
                              : assignment.reviewStatus === "menunggu_validasi"
                              ? "bg-amber-100 text-amber-700"
                              : "bg-gray-100 text-gray-500",
                          ].join(" ")}
                        >
                          {assignment.reviewStatus === "selesai"
                            ? "Selesai"
                            : assignment.reviewStatus === "menunggu_validasi"
                            ? "Menunggu Validasi"
                            : "Belum Selesai"}
                        </span>
                      </td>
                      <td className="border-b border-gray-50 py-4 pr-4">
                        {assignment.reviewStatus === "menunggu_validasi" ? (
                          <div className="flex items-center gap-2">
                            <Button
                              type="button"
                              size="sm"
                              onClick={() => void handleValidate(assignment.id, true)}
                              className="h-7 border-0 bg-green-600 text-white hover:bg-green-700 text-xs"
                            >
                              Ya
                            </Button>
                            <Button
                              type="button"
                              size="sm"
                              onClick={() => void handleValidate(assignment.id, false)}
                              className="h-7 border-0 bg-red-600 text-white hover:bg-red-700 text-xs"
                            >
                              Tidak
                            </Button>
                          </div>
                        ) : (
                          <span className="text-sm text-gray-400">—</span>
                        )}
                      </td>
                      <td className="border-b border-gray-50 py-4 text-right">
                        <div className="flex items-center justify-end gap-2">
                          <Button
                            type="button"
                            variant="outline"
                            size="sm"
                            onClick={() => handleEditAssignment(assignment)}
                            className="border-gray-200 text-gray-600 hover:bg-gray-50 hover:text-gray-800"
                          >
                            <EditIcon />
                            Edit
                          </Button>
                          <Button
                            type="button"
                            size="sm"
                            onClick={() => void handleDeleteAssignment(assignment.id)}
                            className="border-0 bg-red-600 text-white hover:bg-red-700"
                          >
                            <TrashIcon />
                            Hapus
                          </Button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
          {totalAssignmentPages > 1 ? (
            <div className="flex items-center justify-between border-t border-gray-100 px-5 py-3">
              <span className="text-xs text-gray-500">
                {(currentPage - 1) * ITEMS_PER_PAGE + 1}–{Math.min(currentPage * ITEMS_PER_PAGE, sortedAssignments.length)} dari {sortedAssignments.length} item
              </span>
              <div className="flex items-center gap-1">
                <button
                  type="button"
                  onClick={() => setCurrentPage(p => p - 1)}
                  disabled={currentPage === 1}
                  className="rounded px-2 py-1.5 text-xs text-gray-600 hover:bg-gray-100 disabled:cursor-not-allowed disabled:opacity-40"
                >
                  ‹
                </button>
                {buildPageNumbers(currentPage, totalAssignmentPages).map((page, i) =>
                  page === "…" ? (
                    <span key={`ellipsis-${i}`} className="px-1 text-xs text-gray-400">…</span>
                  ) : (
                    <button
                      key={page}
                      type="button"
                      onClick={() => setCurrentPage(page as number)}
                      className={["rounded px-2.5 py-1.5 text-xs font-medium", currentPage === page ? "bg-pkm-600 text-white" : "text-gray-600 hover:bg-gray-100"].join(" ")}
                    >
                      {page}
                    </button>
                  )
                )}
                <button
                  type="button"
                  onClick={() => setCurrentPage(p => p + 1)}
                  disabled={currentPage === totalAssignmentPages}
                  className="rounded px-2 py-1.5 text-xs text-gray-600 hover:bg-gray-100 disabled:cursor-not-allowed disabled:opacity-40"
                >
                  ›
                </button>
              </div>
            </div>
          ) : null}
        </AdminSurfaceCard>
      </div>
    </>
  )
}