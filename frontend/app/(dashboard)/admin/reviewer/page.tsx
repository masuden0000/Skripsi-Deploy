"use client"

import { useCallback, useEffect, useMemo, useState } from "react"
import {
  AdminMetricCard,
  AdminModalShell,
  AdminPageHeader,
  AdminSurfaceCard,
  PasswordInput,
  SearchInput,
} from "@/components/admin/shared"
import {
  EditIcon,
  EmailIcon,
  GraduationIcon,
  PlusIcon,
  TrashIcon,
  UserIcon,
} from "@/components/icons/public-icons"
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

type ReviewerStatus = "Aktif" | "Tidak Aktif"

type Reviewer = {
  id: string
  nama: string
  email: string
  fakultasId: string
  fakultas: string
  isActive: boolean
}

type Faculty = {
  id: string
  code: string
  name: string
}

type ReviewerFormData = {
  nama: string
  email: string
  fakultasId: string
  isActive: boolean
  password?: string
}

type ReviewerApiResponse = {
  data?: Reviewer | Reviewer[] | Faculty[]
  error?: string
  message?: string
}

function getReviewerInitials(nama: string) {
  return nama
    .split(" ")
    .filter(Boolean)
    .slice(0, 2)
    .map((bagian) => bagian[0]?.toUpperCase() ?? "")
    .join("")
}

function mapStatusLabel(isActive: boolean): ReviewerStatus {
  return isActive ? "Aktif" : "Tidak Aktif"
}

async function readApiResponse(response: Response) {
  const text = await response.text()

  if (!text) {
    return {}
  }

  try {
    return JSON.parse(text) as ReviewerApiResponse
  } catch {
    return { error: "Respons server tidak valid." }
  }
}

function ReviewerModal({
  reviewer,
  faculties,
  isSubmitting,
  errorMessage,
  onClose,
  onSave,
}: {
  reviewer: Reviewer | null
  faculties: Faculty[]
  isSubmitting: boolean
  errorMessage: string | null
  onClose: () => void
  onSave: (data: ReviewerFormData) => Promise<void>
}) {
  const [nama, setNama] = useState(reviewer?.nama ?? "")
  const [email, setEmail] = useState(reviewer?.email ?? "")
  const [fakultasId, setFakultasId] = useState(reviewer?.fakultasId ?? "")
  const [status, setStatus] = useState<ReviewerStatus>(mapStatusLabel(reviewer?.isActive ?? true))
  const [password, setPassword] = useState("")
  const [localError, setLocalError] = useState<string | null>(null)
  const isEditMode = Boolean(reviewer)

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault()

    if (!nama.trim() || !email.trim() || !fakultasId) {
      setLocalError("Semua field wajib diisi.")
      return
    }

    if (!isEditMode && password.length < 8) {
      setLocalError("Password reviewer minimal 8 karakter.")
      return
    }

    setLocalError(null)
    await onSave({
      nama: nama.trim(),
      email: email.trim(),
      fakultasId,
      isActive: status === "Aktif",
      password: isEditMode ? undefined : password,
    })
  }

  return (
    <AdminModalShell
      title={isEditMode ? "Edit Reviewer" : "Tambah Reviewer"}
      description={
        isEditMode
          ? "Perbarui data reviewer dan fakultas asalnya."
          : "Tambahkan reviewer baru beserta akun login dan fakultas asalnya."
      }
      onClose={onClose}
      maxWidthClassName="max-w-lg"
    >
      <form onSubmit={handleSubmit} className="space-y-4 px-6 py-5">
        <div className="space-y-1.5">
          <Label htmlFor="nama-reviewer" className="text-xs font-medium text-gray-600">
            Nama Reviewer
          </Label>
          <Input
            id="nama-reviewer"
            value={nama}
            onChange={(event) => setNama(event.target.value)}
            placeholder="cth. Dr. Ahmad Wijaya"
            disabled={isSubmitting}
          />
        </div>

        <div className="space-y-1.5">
          <Label htmlFor="email-reviewer" className="text-xs font-medium text-gray-600">
            Email
          </Label>
          <Input
            id="email-reviewer"
            type="email"
            value={email}
            onChange={(event) => setEmail(event.target.value)}
            placeholder="cth. ahmad.w@university.ac.id"
            disabled={isSubmitting}
          />
        </div>

        {!isEditMode ? (
          <div className="space-y-1.5">
            <Label htmlFor="password-reviewer" className="text-xs font-medium text-gray-600">
              Password Awal
            </Label>
            <PasswordInput
              id="password-reviewer"
              name="password"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              placeholder="Minimal 8 karakter"
              disabled={isSubmitting}
            />
          </div>
        ) : null}

        <div className="space-y-1.5">
          <Label className="text-xs font-medium text-gray-600">Fakultas</Label>
          <Select value={fakultasId || undefined} onValueChange={setFakultasId} disabled={isSubmitting}>
            <SelectTrigger>
              <SelectValue placeholder="Pilih fakultas" />
            </SelectTrigger>
            <SelectContent>
              {faculties.map((faculty) => (
                <SelectItem key={faculty.id} value={faculty.id}>
                  {faculty.name}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        <div className="space-y-1.5">
          <Label className="text-xs font-medium text-gray-600">Status</Label>
          <Select value={status} onValueChange={(value) => setStatus(value as ReviewerStatus)} disabled={isSubmitting}>
            <SelectTrigger>
              <SelectValue placeholder="Pilih status reviewer" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="Aktif">Aktif</SelectItem>
              <SelectItem value="Tidak Aktif">Tidak Aktif</SelectItem>
            </SelectContent>
          </Select>
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
            {isSubmitting ? "Menyimpan..." : isEditMode ? "Simpan Perubahan" : "Tambah Reviewer"}
          </Button>
        </div>
      </form>
    </AdminModalShell>
  )
}

export default function ReviewerManagementPage() {
  const [reviewers, setReviewers] = useState<Reviewer[]>([])
  const [faculties, setFaculties] = useState<Faculty[]>([])
  const [isModalOpen, setIsModalOpen] = useState(false)
  const [editingReviewer, setEditingReviewer] = useState<Reviewer | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [loadError, setLoadError] = useState<string | null>(null)
  const [formError, setFormError] = useState<string | null>(null)
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [searchQuery, setSearchQuery] = useState("")

  const totalAktif = useMemo(
    () => reviewers.filter((reviewer) => reviewer.isActive).length,
    [reviewers]
  )

  const filteredReviewers = useMemo(() => {
    if (!searchQuery.trim()) return reviewers
    const query = searchQuery.toLowerCase()
    return reviewers.filter(
      (reviewer) =>
        reviewer.nama.toLowerCase().includes(query) ||
        reviewer.email.toLowerCase().includes(query) ||
        reviewer.fakultas.toLowerCase().includes(query)
    )
  }, [reviewers, searchQuery])

  const loadReviewerDependencies = useCallback(async () => {
    setIsLoading(true)
    setLoadError(null)

    try {
      const [reviewerResponse, facultyResponse] = await Promise.all([
        fetch("/api/reviewers", {
          method: "GET",
          cache: "no-store",
        }),
        fetch("/api/faculties", {
          method: "GET",
          cache: "no-store",
        }),
      ])

      const reviewerPayload = await readApiResponse(reviewerResponse)
      const facultyPayload = await readApiResponse(facultyResponse)

      if (!reviewerResponse.ok) {
        setLoadError(reviewerPayload.error ?? "Gagal memuat data reviewer.")
        setReviewers([])
        setFaculties([])
        return
      }

      if (!facultyResponse.ok) {
        setLoadError(facultyPayload.error ?? "Gagal memuat data fakultas.")
        setReviewers([])
        setFaculties([])
        return
      }

      setReviewers(Array.isArray(reviewerPayload.data) ? (reviewerPayload.data as Reviewer[]) : [])
      setFaculties(Array.isArray(facultyPayload.data) ? (facultyPayload.data as Faculty[]) : [])
    } catch {
      setLoadError("Tidak bisa terhubung ke server.")
      setReviewers([])
      setFaculties([])
    } finally {
      setIsLoading(false)
    }
  }, [])

  useEffect(() => {
    const timeoutId = window.setTimeout(() => {
      void loadReviewerDependencies()
    }, 0)

    return () => window.clearTimeout(timeoutId)
  }, [loadReviewerDependencies])

  function handleOpenCreateModal() {
    setEditingReviewer(null)
    setFormError(null)
    setIsModalOpen(true)
  }

  function handleCloseModal() {
    setIsModalOpen(false)
    setEditingReviewer(null)
    setFormError(null)
  }

  function handleEditReviewer(reviewer: Reviewer) {
    setEditingReviewer(reviewer)
    setFormError(null)
    setIsModalOpen(true)
  }

  async function handleDeleteReviewer(id: string) {
    if (!window.confirm("Apakah Anda yakin ingin menghapus reviewer ini?")) return

    try {
      const response = await fetch(`/api/reviewers/${id}`, {
        method: "DELETE",
      })
      const payload = await readApiResponse(response)

      if (!response.ok) {
        alert(payload.error ?? "Gagal menghapus reviewer.")
        return
      }

      await loadReviewerDependencies()
      alert(payload.message ?? "Reviewer berhasil dihapus.")
    } catch {
      alert("Tidak bisa terhubung ke server.")
    }
  }

  async function handleSaveReviewer(data: ReviewerFormData) {
    setIsSubmitting(true)
    setFormError(null)

    try {
      const isEditMode = Boolean(editingReviewer)
      const response = await fetch(
        isEditMode ? `/api/reviewers/${editingReviewer!.id}` : "/api/reviewers",
        {
          method: isEditMode ? "PUT" : "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify(data),
        }
      )
      const payload = await readApiResponse(response)

      if (!response.ok) {
        setFormError(payload.error ?? "Gagal menyimpan reviewer.")
        return
      }

      await loadReviewerDependencies()
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
        <ReviewerModal
          reviewer={editingReviewer}
          faculties={faculties}
          isSubmitting={isSubmitting}
          errorMessage={formError}
          onClose={handleCloseModal}
          onSave={handleSaveReviewer}
        />
      ) : null}

      <div className="px-8 py-8">
        <AdminPageHeader
          title="Kelola Reviewer"
          description="Kelola akun reviewer dan informasi terkait"
          action={
            <Button onClick={handleOpenCreateModal} className="flex items-center gap-2">
              <PlusIcon />
              Tambah Reviewer
            </Button>
          }
        />

        {loadError ? (
          <div className="mb-4 rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
            <div className="flex items-center justify-between gap-3">
              <span>{loadError}</span>
              <Button type="button" variant="outline" size="sm" onClick={() => void loadReviewerDependencies()}>
                Coba Lagi
              </Button>
            </div>
          </div>
        ) : null}

        <div className="grid gap-4 md:grid-cols-2">
          <AdminMetricCard
            title="Total Reviewer"
            value={String(reviewers.length)}
            accentClassName="bg-pkm-100 text-pkm-700"
            icon={<UserIcon />}
          />
          <AdminMetricCard
            title="Aktif"
            value={String(totalAktif)}
            accentClassName="bg-pkm-100 text-pkm-700"
            icon={<GraduationIcon />}
          />
        </div>

        <AdminSurfaceCard className="mt-4">
          <div className="flex items-center justify-between border-b border-gray-100 px-5 py-4">
            <div>
              <h2 className="text-sm font-semibold text-gray-700">Daftar Reviewer</h2>
              <p className="mt-0.5 text-xs text-[rgba(0,0,0,0.4)]">
                Kelola dan pantau reviewer yang terdaftar
              </p>
            </div>
            <SearchInput
              value={searchQuery}
              onChange={setSearchQuery}
              placeholder="Cari reviewer..."
              className="w-64"
            />
          </div>

          <div className="overflow-x-auto px-5 py-4">
            {isLoading ? (
              <div className="py-8 text-center text-sm text-gray-500">Memuat reviewer...</div>
            ) : filteredReviewers.length === 0 ? (
              searchQuery.trim() ? (
                <div className="py-8 text-center text-sm text-gray-500">
                  Tidak ada reviewer yang cocok dengan "{searchQuery}"
                </div>
              ) : (
                <div className="py-8 text-center text-sm text-gray-500">Belum ada reviewer.</div>
              )
            ) : (
              <table className="w-full min-w-[920px] border-separate border-spacing-0">
                <thead>
                  <tr className="text-left">
                    <th className="border-b border-gray-100 pb-3 pr-4 text-xs font-semibold text-gray-700">
                      Reviewer
                    </th>
                    <th className="border-b border-gray-100 pb-3 pr-4 text-xs font-semibold text-gray-700">
                      Email
                    </th>
                    <th className="border-b border-gray-100 pb-3 pr-4 text-xs font-semibold text-gray-700">
                      Fakultas
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
                  {filteredReviewers.map((reviewer) => (
                    <tr key={reviewer.id}>
                      <td className="border-b border-gray-50 py-4 pr-4">
                        <div className="flex items-center gap-4">
                          <div className="flex size-12 items-center justify-center rounded-full bg-pkm-100 text-sm font-semibold text-pkm-700">
                            {getReviewerInitials(reviewer.nama)}
                          </div>
                          <span className="text-sm font-medium text-gray-800">{reviewer.nama}</span>
                        </div>
                      </td>
                      <td className="border-b border-gray-50 py-4 pr-4">
                        <div className="flex items-center gap-2 text-sm text-gray-500">
                          <EmailIcon className="text-gray-400" />
                          <span>{reviewer.email}</span>
                        </div>
                      </td>
                      <td className="border-b border-gray-50 py-4 pr-4">
                        <span className="inline-flex rounded-full border border-pkm-200 bg-pkm-50 px-3 py-1 text-xs font-medium text-pkm-700">
                          {reviewer.fakultas}
                        </span>
                      </td>
                      <td className="border-b border-gray-50 py-4 pr-4">
                        <span
                          className={[
                            "inline-flex rounded-full px-3 py-1 text-xs font-medium",
                            reviewer.isActive
                              ? "bg-pkm-100 text-pkm-700"
                              : "bg-gray-100 text-gray-500",
                          ].join(" ")}
                        >
                          {mapStatusLabel(reviewer.isActive)}
                        </span>
                      </td>
                      <td className="border-b border-gray-50 py-4 text-right">
                        <div className="flex items-center justify-end gap-2">
                          <Button
                            type="button"
                            variant="outline"
                            size="sm"
                            onClick={() => handleEditReviewer(reviewer)}
                            className="border-gray-200 text-gray-600 hover:bg-gray-50 hover:text-gray-800"
                          >
                            <EditIcon />
                            Edit
                          </Button>
                          <Button
                            type="button"
                            size="sm"
                            onClick={() => void handleDeleteReviewer(reviewer.id)}
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
