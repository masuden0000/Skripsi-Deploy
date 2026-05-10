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

type Assignment = {
  id: string
  periodId: string
  reviewerId: string
  proposalLink: string
  assessmentLink: string
  isCompleted: boolean
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
  data?: Array<{ id: string; nama: string; email?: string }>
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
  periods,
  reviewers,
  isSubmitting,
  errorMessage,
  onClose,
  onSave,
}: {
  assignment: Assignment | null
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
  const [isModalOpen, setIsModalOpen] = useState(false)
  const [editingAssignment, setEditingAssignment] = useState<Assignment | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [loadError, setLoadError] = useState<string | null>(null)
  const [formError, setFormError] = useState<string | null>(null)
  const [isSubmitting, setIsSubmitting] = useState(false)

  const totalAssignments = assignments.length
  const completedCount = useMemo(
    () => assignments.filter((a) => a.isCompleted).length,
    [assignments]
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

      const periodData = periodPayload as { data?: Array<{ id: string; nama: string }> }
      if (Array.isArray(periodData.data)) {
        setPeriods(periodData.data)
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
          periods={periods}
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

        <div className="grid gap-4 md:grid-cols-2">
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
                      Status
                    </th>
                    <th className="border-b border-gray-100 pb-3 text-right text-xs font-semibold text-gray-700">
                      Aksi
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
                            assignment.isCompleted
                              ? "bg-green-100 text-green-700"
                              : "bg-gray-100 text-gray-500",
                          ].join(" ")}
                        >
                          {assignment.isCompleted ? "Selesai" : "Belum Selesai"}
                        </span>
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
        </AdminSurfaceCard>
      </div>
    </>
  )
}